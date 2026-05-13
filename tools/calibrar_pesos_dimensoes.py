"""Harness de calibração de pesos para dimensões de proximidade (Etapa 6 — Fase 3).

Mede frequência de violações clínicas em cenários-âncora (E.0 da Fase 3) sob
diferentes configurações de peso. Substitui especulação numérica por iteração
empírica.

Diferente de `medir_entropia_pareamentos.py` (Etapa 5), que mede entropia de
distribuição de blocos, este harness mede **% de rotinas que satisfazem cada
expectativa clínica** dos 13 cenários-âncora definidos em
`docs/refatoracao/dimensoes_proximidade.md` (Fase 3 / E.0).

Mocks de dimensão da Etapa 6 vêm de `tools/mocks/dimensoes_etapa_6.yaml`
(NÃO altera o XLSX — overlay in-memory).

Uso:
    python tools/calibrar_pesos_dimensoes.py [--cenario 1.1] [--n-iter 1000]
                                             [--csv saida.csv]

E.1.a — escopo atual: pipeline end-to-end com cenário 1.1 só (família hard
INTRA). Outros 12 cenários implementados em E.1.b.

Tracking items (TODOs antes de E.1 fechar):
  - Stub `_penalty_proximidade` cobre hoje só INTRA família + (placeholder)
    pegada/plano/equipamento same-subregião. Faltam:
      * Branches INTER + HISTÓRICO (cenários 3.x, 4.x)
      * Dimensões lateralidade + variante_pontual (cenários 1.3, 2.2, 1.2)
      * Decisão final par-a-par vs set-based em D2 (provisório: par-a-par)
  - Suporte a mock_futuro (Exercicio criado in-memory) — implementado, mas
    não usado em cenário 1.1.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gerador_treino import (  # noqa: E402
    Exercicio,
    GRUPO_MUSCULAR_PADRAO,
    Sessao,
    carregar_banco,
    gerar_multiplos_treinos,
)

XLSX = ROOT / "banco_exercicios.xlsx"
YAML_MOCKS = ROOT / "tools" / "mocks" / "dimensoes_etapa_6.yaml"

N_ITER_DEFAULT = 1000


# ---------------------------------------------------------------------------
# Mock loader — overlay de dimensões da Etapa 6
# ---------------------------------------------------------------------------

@dataclass
class MockDimensoes:
    """Dimensões de proximidade da Etapa 6 pra um exercício (mock)."""
    familia_estrita: Optional[str] = None
    plano_corporal: Optional[str] = None
    pegada: Optional[str] = None
    equipamento_grupo: Optional[str] = None
    variante_pontual: bool = False


def _carregar_mocks() -> tuple[dict[str, MockDimensoes], list[dict]]:
    """Lê YAML e devolve (dims_por_nome, mock_futuros).

    `dims_por_nome` cobre TODOS os exercícios mockados (cadastrados +
    mock_futuro). `mock_futuros` é lista crua dos exercícios futuros (com
    campo `extras`) pra criação de Exercicio in-memory.
    """
    if not YAML_MOCKS.exists():
        raise FileNotFoundError(f"YAML de mocks não encontrado: {YAML_MOCKS}")
    with open(YAML_MOCKS, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    dims: dict[str, MockDimensoes] = {}
    futuros: list[dict] = []
    for item in (data or {}).get("exercicios", []):
        nome = item["nome"]
        d = item.get("dimensoes", {}) or {}
        dims[nome] = MockDimensoes(
            familia_estrita=d.get("familia_estrita"),
            plano_corporal=d.get("plano_corporal"),
            pegada=d.get("pegada"),
            equipamento_grupo=d.get("equipamento_grupo"),
            variante_pontual=bool(d.get("variante_pontual", False)),
        )
        if item.get("origem") == "mock_futuro":
            futuros.append(item)
    return dims, futuros


def _aplicar_overlay(banco: list[Exercicio], dims: dict[str, MockDimensoes],
                     futuros: list[dict]) -> list[Exercicio]:
    """Sobrescreve dims da Etapa 6 em Exercicios cadastrados conforme mock
    e adiciona Exercicios mock_futuro ao banco.

    Etapa 7 Fases 7.2 + 7.3: `variante_pontual`, `pegada`, `plano_corporal`
    e `equipamento_grupo` são campos do `Exercicio` (default `None` /
    `False`) e o gerador (predicado `_compativel_intra` + função
    `_score_proximidade`) lê deles direto. Overlay propaga as tags do mock
    pra Exercicio em-memória — banco real (XLSX) ainda não tem colunas;
    Fase 4 cadastra.
    """
    nomes_cadastrados = {e.nome for e in banco}
    for ex in banco:
        if ex.nome in dims:
            mock = dims[ex.nome]
            if mock.familia_estrita is not None:
                ex.variacao_de = mock.familia_estrita
            ex.variante_pontual = mock.variante_pontual
            ex.pegada = mock.pegada
            ex.plano_corporal = mock.plano_corporal
            ex.equipamento_grupo = mock.equipamento_grupo

    # Cria Exercicios pra mock_futuros não cadastrados.
    for item in futuros:
        nome = item["nome"]
        if nome in nomes_cadastrados:
            continue  # já existe — overlay aplicado acima
        ex_dims = dims[nome]
        extras = item.get("extras", {})
        novo = Exercicio(
            nome=nome,
            variacao_de=ex_dims.familia_estrita,
            eq_primario=extras.get("eq_primario", ""),
            eq_secundario=None,
            regiao=extras["regiao"],
            subregiao=extras["subregiao"],
            padrao=extras["padrao"],
            purpose=extras.get("purpose", "compound"),
            unilateral=extras.get("unilateral", "bilateral"),
            complexidade=int(extras.get("complexidade", 3)),
            fadiga=int(extras.get("fadiga", 3)),
            circuito="",
            similaridade="",
            musculo_primario=extras.get("musculo_primario", ""),
            obs=None,
            variante_pontual=ex_dims.variante_pontual,
            pegada=ex_dims.pegada,
            plano_corporal=ex_dims.plano_corporal,
            equipamento_grupo=ex_dims.equipamento_grupo,
        )
        banco.append(novo)
    return banco


# ---------------------------------------------------------------------------
# Stub _penalty_proximidade — provisório, cobre 1.1 apenas indiretamente
# (1.1 mede hard de família já existente; stub não é chamado nesse cenário).
#
# TODO E.1 antes de ativar cenários 2.x-5.x:
#   1. Branch INTER + HISTÓRICO (`contexto in {"INTRA","INTER","HIST"}`)
#   2. Dimensões `lateralidade` + `variante_pontual`
#   3. Confirmar decisão par-a-par cumulativa em D2 (provisório aqui)
# ---------------------------------------------------------------------------

def _penalty_proximidade(
    cand: Exercicio,
    bloco_atual: list[Exercicio],
    dims: dict[str, MockDimensoes],
    pesos: dict[str, float],
    contexto: str = "INTRA",  # noqa: ARG001 (TODO E.1)
) -> float:
    """Stub provisório. Composição par-a-par cumulativa.

    Retorna penalty TOTAL pra cand vs cada exercício do bloco (somatório).
    Hard de família retorna -inf (gerador trata como bloqueio).
    """
    if contexto != "INTRA":
        return 0.0  # TODO E.1: branches INTER/HIST

    cand_d = dims.get(cand.nome)
    if cand_d is None:
        return 0.0

    total = 0.0
    for outro in bloco_atual:
        outro_d = dims.get(outro.nome)
        if outro_d is None:
            continue
        # Hard INTRA família (mesma família refinada)
        if (cand_d.familia_estrita and
                cand_d.familia_estrita == outro_d.familia_estrita):
            return float("-inf")
        # Penalties soft INTRA — só dentro de mesma subregião
        if cand.subregiao != outro.subregiao:
            continue
        # Plano corporal (Alto em hinges, Médio em remadas, etc — placeholder)
        if (cand_d.plano_corporal and
                cand_d.plano_corporal == outro_d.plano_corporal):
            total -= pesos.get("plano_corporal", 0.0)
        # Equipamento (tiebreaker BAIXO INTRA)
        if (cand_d.equipamento_grupo and
                cand_d.equipamento_grupo == outro_d.equipamento_grupo):
            total -= pesos.get("equipamento_grupo", 0.0)
        # Pegada — placeholder peso simples; matriz 4x4 vem em D2
        if cand_d.pegada and cand_d.pegada == outro_d.pegada:
            total -= pesos.get("pegada", 0.0)
        # variante_pontual cross-family same-subregião
        if (cand_d.variante_pontual and outro_d.variante_pontual and
                cand_d.familia_estrita != outro_d.familia_estrita):
            total -= pesos.get("variante_pontual", 0.0)
    return total


# ---------------------------------------------------------------------------
# Definição de cenários
# ---------------------------------------------------------------------------

@dataclass
class CenarioResultado:
    """Resultado por iteração para o CSV de auditoria."""
    cenario_id: str
    iter_idx: int
    seed: int
    seed_hash: str
    violacao: bool
    detalhe: str = ""
    # Métrica secundária (opcional) — sinal informativo paralelo, não afeta status
    secundaria_violacao: Optional[bool] = None
    secundaria_detalhe: str = ""


SecundariaFn = Callable[[list[Sessao], dict[str, MockDimensoes]],
                        tuple[bool, str]]

# Etapa 7 Fase 7.5: assinatura da métrica contínua agregada. Per-iter devolve
# `(slots_violando, slots_total, detalhe)`; runner soma o numerador e o
# denominador cross-iter e gateia status no `pct` resultante. Usada em 4.1/4.2
# pra capturar mecanismo HIST além do gate binário pré-7.4 (Seção 8.15.6 —
# "% slots com overlap" da opção A do refinamento da métrica 4.1).
ContinuaFn = Callable[[list[Sessao], dict[str, MockDimensoes]],
                       tuple[int, int, str]]


@dataclass
class Cenario:
    """Definição de um cenário-âncora da E.0.

    `metrica_fn` é o gate de status (primária) **modo binário** — runner
    conta % iterações com violação. `metrica_continua_fn` (Fase 7.5) é o
    gate de status **modo contínuo agregado** — runner soma slots_violando
    e slots_total cross-iter e gateia em `pct = sum(viol)/sum(total)`.
    Quando ambos definidos, contínua tem precedência (binária só popula CSV).
    `metricas_secundarias` é uma lista opcional de sinais informativos
    paralelos — runner reporta a taxa de cada uma mas NÃO afeta o status
    do cenário.

    Útil pra distinguir "calibração da Etapa 6 over-penalizou" (primária)
    de "trade-offs de âncora — Etapa 3" ou "validação realista do anti_uni
    em setup Variante B" (secundárias). Ex: 6.1 (1 secundária E3); 6.2
    (2 secundárias — sub-métricas a e b da Nota de processo #2 da
    Seção 8.6).

    CSV de auditoria persiste só a PRIMEIRA secundária pra back-compat;
    extras aparecem só no output impresso.
    """
    id: str
    nome: str
    setup_descricao: str
    expectativa_descricao: str
    expectativa_predicate: Callable[[float], bool]  # (% violacao) → ✓?
    config_factory: Callable[[list[Exercicio]], list[dict]]
    n_treinos: int
    metrica_fn: Callable[[list[Sessao], dict[str, MockDimensoes]],
                          tuple[bool, str]]  # (violacao?, detalhe)
    relaxar_familia: bool = False
    iteracoes: list[CenarioResultado] = field(default_factory=list)
    metricas_secundarias: list[tuple[str, SecundariaFn]] = field(
        default_factory=list)
    # Etapa 7 Fase 7.4: factory que devolve a R-1 (rotina anterior) pra
    # passar em `gerar_multiplos_treinos(historico_r1=...)`. None = toggle
    # OFF (default). Cenário 4.1 usa pra ativar HISTÓRICO; 4.2 deixa None.
    historico_r1_factory: Optional[Callable[[list[Exercicio]],
                                              list[Sessao]]] = None
    # Etapa 7 Fase 7.5: métrica contínua agregada (opcional). Quando
    # presente, o runner ignora `metrica_fn` pra gate de status e usa
    # razão agregada cross-iter. Refinamento métrica 4.1 (Seção 8.15.6
    # achado pós-7.4 — opção A do user na Sessão 12).
    metrica_continua_fn: Optional[ContinuaFn] = None


def _seed_hash(cenario_id: str, seed: int) -> str:
    """Hash curto reproduzível pra identificar uma rodada específica."""
    h = hashlib.sha256(f"{cenario_id}|{seed}".encode()).hexdigest()
    return h[:8]


# ---------------------------------------------------------------------------
# Cenário 1.1 — Família estrita hard INTRA
# ---------------------------------------------------------------------------

def _cfg_1_1(banco: list[Exercicio]) -> list[dict]:  # noqa: ARG001
    return [{
        "demandas": [("subregiao", "peito", 3)],
        "tamanho_bloco": 2,
        "evitar_agonistas": True,
        "max_complexidade": 5,
    }]


def _metrica_1_1(sessoes: list[Sessao],
                 dims: dict[str, MockDimensoes]) -> tuple[bool, str]:
    """Detecta 2+ exercícios da mesma família refinada no mesmo treino.

    Família refinada = `Exercicio.variacao_de` pós-overlay. Considera apenas
    famílias não-vazias (None → exercício "solo", não conta como repetição).
    """
    for sessao in sessoes:
        familias: dict[str, list[str]] = {}
        for bloco in sessao.blocos:
            for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
                if ex is None:
                    continue
                fam = ex.variacao_de
                if fam:
                    familias.setdefault(fam, []).append(ex.nome)
        for fam, nomes in familias.items():
            if len(nomes) >= 2:
                return True, f"familia '{fam}' tem {len(nomes)}: {nomes}"
    return False, ""


CENARIO_1_1 = Cenario(
    id="1.1",
    nome="Família estrita hard INTRA",
    setup_descricao="peito(3) × 1 treino, 1000 rotinas",
    expectativa_descricao="0% (hard filter)",
    expectativa_predicate=lambda pct: pct == 0.0,
    config_factory=_cfg_1_1,
    n_treinos=1,
    metrica_fn=_metrica_1_1,
)


# ---------------------------------------------------------------------------
# Cenário 1.2 — anti_uni retroativo Etapa 5 (não-regressão soft -75)
#
# Setup REVISADO pós-D1.d (Sessão 4): originalmente em costas(3), mas costas
# virou hard contextual via D1.d. Movido pra braços (subregião não-hard) pra
# preservar o propósito original de testar o soft -75 da Etapa 5 que continua
# operando em todas as subregiões NÃO listadas em SUBREGIOES_LATERALIDADE_HARD.
# ---------------------------------------------------------------------------

def _cfg_1_2(banco: list[Exercicio]) -> list[dict]:  # noqa: ARG001
    return [{
        "demandas": [("subregiao", "bracos", 4)],
        "tamanho_bloco": 2,
        "evitar_agonistas": True,
        "max_complexidade": 5,
    }]


def _metrica_1_2(sessoes: list[Sessao],
                 dims: dict[str, MockDimensoes]) -> tuple[bool, str]:  # noqa: ARG001
    """Detecta bloco com 2 unilaterais do mesmo grupo musculo-funcional.

    Anti_uni soft -75 da Etapa 5 deve desincentivar (sem bloquear).
    Métrica positiva = violação detectada.
    """
    for sessao in sessoes:
        for bloco in sessao.blocos:
            unis_por_grupo: dict[str, list[str]] = {}
            for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
                if ex is None or ex.unilateral != "unilateral":
                    continue
                grupo = GRUPO_MUSCULAR_PADRAO.get(ex.padrao, "?")
                unis_por_grupo.setdefault(grupo, []).append(ex.nome)
            for grupo, nomes in unis_por_grupo.items():
                if len(nomes) >= 2:
                    return True, f"bloco {bloco.label} grupo='{grupo}' 2+ unis: {nomes}"
    return False, ""


CENARIO_1_2 = Cenario(
    id="1.2",
    nome="anti_uni retroativo Etapa 5 (soft -75 braços)",
    setup_descricao="bracos(4) × 1 treino, tamanho_bloco=2, 1000 rotinas",
    expectativa_descricao="<10% (soft -75)",
    expectativa_predicate=lambda pct: pct < 10.0,
    config_factory=_cfg_1_2,
    n_treinos=1,
    metrica_fn=_metrica_1_2,
)


# ---------------------------------------------------------------------------
# Cenário 1.3 — variante_pontual hard INTRA (BASELINE pre-Etapa 7)
#
# Mede taxa atual de coexistência de 2 mock_futuro com variante_pontual=true
# mesma subregião + diff família. Pré-Etapa 7 (sem predicado): baseline > 0.
# Pós-Etapa 7 (com predicado): expectativa 0%.
# Status atual: FAIL informativo — quantifica gap a fechar.
# ---------------------------------------------------------------------------

def _cfg_1_3(banco: list[Exercicio]) -> list[dict]:  # noqa: ARG001
    return [{
        "demandas": [("subregiao", "peito", 3)],
        "tamanho_bloco": 2,
        "evitar_agonistas": True,
        "max_complexidade": 5,
    }]


def _metrica_1_3(sessoes: list[Sessao],
                 dims: dict[str, MockDimensoes]) -> tuple[bool, str]:
    """Detecta 2+ exercícios variante_pontual=true mesma subregião diff família."""
    for sessao in sessoes:
        # Coletar variante_pontual=true por subregião
        vps_por_sub: dict[str, list[Exercicio]] = {}
        for bloco in sessao.blocos:
            for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
                if ex is None:
                    continue
                d = dims.get(ex.nome)
                if d and d.variante_pontual:
                    vps_por_sub.setdefault(ex.subregiao, []).append(ex)
        for sub, exs in vps_por_sub.items():
            # Family hard já bloqueia mesma família INTRA — só conta diff família
            familias = {e.variacao_de for e in exs}
            if len(familias) >= 2:
                nomes = [e.nome for e in exs]
                return True, f"sub={sub} 2+ variante_pontual cross-family: {nomes}"
    return False, ""


CENARIO_1_3 = Cenario(
    id="1.3",
    nome="variante_pontual hard INTRA (baseline)",
    setup_descricao="peito(3) × 1 treino, mocks SF+AF, 1000 rotinas",
    expectativa_descricao="0% (post-Etapa 7)",
    expectativa_predicate=lambda pct: pct == 0.0,
    config_factory=_cfg_1_3,
    n_treinos=1,
    metrica_fn=_metrica_1_3,
)


# ---------------------------------------------------------------------------
# Cenário 2.2 A — Lateralidade hard contextual costas (BASELINE pre-Etapa 7)
#
# Setup AJUSTADO: original era costas(2) que naturalmente dá ~0% (puxadas hoje
# têm 0 unis, então 2 unis em costas via cycling subregião é improvável).
# Usa padrão remadas(2) onde 3/12 são unilateral, dando baseline mensurável.
# Pré-Etapa 7: baseline > 0. Pós-Etapa 7 (predicado costas hard): 0%.
# ---------------------------------------------------------------------------

def _cfg_2_2_a(banco: list[Exercicio]) -> list[dict]:  # noqa: ARG001
    return [{
        "demandas": [("padrao", "remadas", 2)],
        "tamanho_bloco": 2,
        "evitar_agonistas": True,
        "max_complexidade": 5,
    }]


def _metrica_2_2_a(sessoes: list[Sessao],
                    dims: dict[str, MockDimensoes]) -> tuple[bool, str]:  # noqa: ARG001
    """Detecta 2+ unilaterais em mesma subregião costas no mesmo treino."""
    for sessao in sessoes:
        unis_costas: list[str] = []
        for bloco in sessao.blocos:
            for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
                if ex is None:
                    continue
                if ex.subregiao == "costas" and ex.unilateral == "unilateral":
                    unis_costas.append(ex.nome)
        if len(unis_costas) >= 2:
            return True, f"costas 2+ unis: {unis_costas}"
    return False, ""


CENARIO_2_2_A = Cenario(
    id="2.2A",
    nome="Lateralidade hard contextual costas (baseline)",
    setup_descricao="remadas(2) × 1 treino, 1000 rotinas",
    expectativa_descricao="0% (post-Etapa 7)",
    expectativa_predicate=lambda pct: pct == 0.0,
    config_factory=_cfg_2_2_a,
    n_treinos=1,
    metrica_fn=_metrica_2_2_a,
)


# ---------------------------------------------------------------------------
# Cenário 2.2B — Lateralidade soft Médio perna_anterior (realista)
#
# Setup REDEFINIDO pela auditoria E.0 (Sessão 6, Seção 8.6): de
# `squat_unilateral(2)` artificial pra `perna_anterior(3) × 1 treino` realista
# (Variante B T2 do `configuracoes_comuns.md` Seção 2.2). perna_anterior é
# subregião NÃO-hard contextual — lateralidade soft Médio via
# `anti_uni_mesmo_grupo -75` (Etapa 5, ortogonal à escala unificada Etapa 6).
#
# **ACHADO PARALELO Sessão 7a (2026-05-08):** baseline observado = 0.00%
# em 1000 iterações. Investigação confirmou que `_ordenar_padroes_por_prioridade`
# embaralha squat_bilateral|squat_unilateral 50/50 (~497/503), mas
# `_selecionar_ciclando` em modo subregião com `preferir_composto=True`
# produz consistentemente 2bi+1uni — viés determinístico independente
# da ordem do shuffle. Resultado prático: 2.2B redefinido NÃO exercita
# o anti_uni soft em perna_anterior do jeito esperado (banco efetivamente
# nunca propõe 2 unis em perna_anterior(3)). Predicate <70% passa
# trivialmente; cenário continua útil como gate de "não regressão" mas
# não calibra peso Médio. Calibração de lateralidade soft Médio em
# squats provavelmente precisa de `perna_anterior(4)` ou
# `padrão squat_unilateral(2)` em E.1.b2/D2 — investigar separado.
# ---------------------------------------------------------------------------

def _cfg_2_2_b(banco: list[Exercicio]) -> list[dict]:  # noqa: ARG001
    return [{
        "demandas": [("subregiao", "perna_anterior", 3)],
        "tamanho_bloco": 2,
        "evitar_agonistas": True,
        "max_complexidade": 5,
    }]


def _metrica_2_2_b(sessoes: list[Sessao],
                    dims: dict[str, MockDimensoes]) -> tuple[bool, str]:  # noqa: ARG001
    """Detecta 2+ unilaterais em mesma subregião perna_anterior na rotina."""
    for sessao in sessoes:
        unis_pa: list[str] = []
        for bloco in sessao.blocos:
            for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
                if ex is None:
                    continue
                if (ex.subregiao == "perna_anterior" and
                        ex.unilateral == "unilateral"):
                    unis_pa.append(ex.nome)
        if len(unis_pa) >= 2:
            return True, f"perna_anterior 2+ unis: {unis_pa}"
    return False, ""


CENARIO_2_2_B = Cenario(
    id="2.2B",
    nome="Lateralidade soft Médio perna_anterior (realista, baseline)",
    setup_descricao="perna_anterior(3) × 1 treino, 1000 rotinas",
    expectativa_descricao="<70% (baseline pre-D2)",
    expectativa_predicate=lambda pct: pct < 70.0,
    config_factory=_cfg_2_2_b,
    n_treinos=1,
    metrica_fn=_metrica_2_2_b,
)


# ---------------------------------------------------------------------------
# Cenário 2.3 — Pegada+plano cumulativa em costas (gate de não-regressão)
#
# **Status pós-Etapa 7 (2026-05-09):** Dim 2 (pegada+plano) é o **5º NO-OP**
# documentado da sondagem de calibração — paralelo aos 4 NO-OPs da Seção
# 8.15.9, descoberto via escalada de setup em vez de coordinate descent.
#
# Sondagem de escalada (Sessão posterior à 13, item 8 da 8.15.7):
#   costas(5) → 0%   costas(7) → 0%   costas(8) → 0%   costas(9) → 23.30%
#
# Comportamento binário do banco mock atual: costas pós hard-família tem
# 9 famílias distintas; em N≤8 o softmax score-aware sempre escapa o
# único par mensurável (`Remada Apoiado + Remada Seal Halteres`,
# pegada=neutra plano=apoiada — Decisão B Sessão 7a); em N=9 força
# preencher todas as 9 famílias e captura ~23% do tempo. Não há ponto
# intermédio — ou pula 100%, ou força ~23%.
#
# **Decisão (Sessão de fechamento item 8):** aceitar 2.3 em over-correção
# benigna. Não calibrar pesos contra banco que não exercita a dim
# (mesma régua dos 4 NO-OPs originais). Cenário fica como gate de
# não-regressão + observador da frequência. Validação real da Dim 2
# pegada+plano fica gateada pela Fase 4 (XLSX 125+ exercícios) — ver
# Seção 9 / nota Dim 2.
#
# Métrica: 2+ ex em costas com pegada+plano AMBOS iguais e não-vazios.
# ---------------------------------------------------------------------------

def _cfg_2_3(banco: list[Exercicio]) -> list[dict]:  # noqa: ARG001
    # costas(5) mantido. Sondagem de escalada (5/7/8/9) revelou que o banco
    # mock atual só tem 1 par Dim 2 mensurável pós hard-família (Apoiado+Seal)
    # — comportamento binário (0% até N=8, 23% em N=9). Ver header acima
    # + Seção 8.15.10 do dimensoes_proximidade.md (5º NO-OP).
    return [{
        "demandas": [("subregiao", "costas", 5)],
        "tamanho_bloco": 2,
        "evitar_agonistas": True,
        "max_complexidade": 5,
    }]


def _metrica_2_3(sessoes: list[Sessao],
                  dims: dict[str, MockDimensoes]) -> tuple[bool, str]:
    """Detecta 2+ ex em costas com pegada+plano AMBOS iguais e não-vazios."""
    for sessao in sessoes:
        ex_costas = [
            (e, dims.get(e.nome))
            for b in sessao.blocos
            for e in (b.ex1, b.ex2, b.ex3)
            if e is not None and e.subregiao == "costas"
        ]
        for i, (e1, d1) in enumerate(ex_costas):
            if d1 is None:
                continue
            for (e2, d2) in ex_costas[i + 1:]:
                if d2 is None:
                    continue
                if (d1.pegada and d1.pegada == d2.pegada and
                        d1.plano_corporal and
                        d1.plano_corporal == d2.plano_corporal):
                    return True, (f"{e1.nome}+{e2.nome} "
                                  f"pegada={d1.pegada} plano={d1.plano_corporal}")
    return False, ""


CENARIO_2_3 = Cenario(
    id="2.3",
    nome="Pegada+plano cumulativa em costas (gate de não-regressão)",
    setup_descricao="costas(5) × 1 treino, 1000 rotinas",
    expectativa_descricao=("informativo (5º NO-OP — banco mock só tem 1 par "
                           "mensurável; validação Dim 2 fica pra Fase 4)"),
    expectativa_predicate=lambda pct: pct >= 0.0,  # informativo, sempre OK
    config_factory=_cfg_2_3,
    n_treinos=1,
    metrica_fn=_metrica_2_3,
)


# ---------------------------------------------------------------------------
# Cenário 2.4 — Lateralidade Médio em squats (calibração dedicada)
#
# Cenário NOVO (Decisão 1 Sessão 7a — Seção 8.14.2): substituto operacional
# do 2.2B (que virou gate de não-regressão por causa do cycling determinístico
# 2bi+1uni em perna_anterior). 2.4 isola o mecanismo de lateralidade soft
# Médio em squats forçando 2 unis no padrão `squat_unilateral`.
#
# Setup: `padrão squat_unilateral(2) × 1 treino`. Padrão tem 12 candidatos
# (incluindo Recuo do Estepe mock_futuro), todos uni. Hard família protege
# coexistência intra entre membros da mesma família refinada (Agachamento,
# Recuo, subida_elevada, passada, walking lunges, agach. lateral, sem família
# Búlgaro). Mas todos os 12 são uni — então 100% das rotinas têm 2 unis em
# squat_unilateral.
#
# Categoria ⚠️ patológico necessário (família semântica de 2.1).
# Pre-D2: ~100% baseline. Pos-D2 calibrado: depende do peso Médio na seleção;
# faixa-alvo a registrar quando D2 numérico fechar.
# ---------------------------------------------------------------------------

def _cfg_2_4(banco: list[Exercicio]) -> list[dict]:  # noqa: ARG001
    return [{
        "demandas": [("padrao", "squat_unilateral", 2)],
        "tamanho_bloco": 2,
        "evitar_agonistas": True,
        "max_complexidade": 5,
    }]


def _metrica_2_4(sessoes: list[Sessao],
                  dims: dict[str, MockDimensoes]) -> tuple[bool, str]:  # noqa: ARG001
    """Métrica primária — % rotinas com 2+ unis no padrão squat_unilateral.

    Mede PRESENÇA dos 2 unis (gate de mecanismo confirmado pre-D2).
    Quando C executar, sec-a (pareamento mesmo bloco) vira primária —
    Decisão 2 da Sessão 7b (Seção 8.14.4)."""
    for sessao in sessoes:
        unis_squat: list[str] = []
        for bloco in sessao.blocos:
            for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
                if ex is None:
                    continue
                if (ex.padrao == "squat_unilateral" and
                        ex.unilateral == "unilateral"):
                    unis_squat.append(ex.nome)
        if len(unis_squat) >= 2:
            return True, f"2+ unis squat: {unis_squat}"
    return False, ""


def _metrica_2_4_sub_a(sessoes: list[Sessao],
                        dims: dict[str, MockDimensoes]) -> tuple[bool, str]:  # noqa: ARG001
    """Sub-métrica a — % rotinas onde os 2 unis squat aparecem PAREADOS no
    MESMO bloco (= alvo real da calibração de lateralidade Médio em squats).

    `anti_uni_mesmo_grupo -75` (Etapa 5) atua em `_score_pareamento`, não na
    seleção de subregião/padrão — então mecanismo opera só quando 2 unis
    coincidem no mesmo bloco. Métrica vira primária quando C calibrar
    lateralidade Médio em squats (Decisão 2 Sessão 7b).
    """
    for sessao in sessoes:
        for bloco in sessao.blocos:
            unis_squat_bloco: list[str] = []
            for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
                if ex is None:
                    continue
                if (ex.padrao == "squat_unilateral" and
                        ex.unilateral == "unilateral"):
                    unis_squat_bloco.append(ex.nome)
            if len(unis_squat_bloco) >= 2:
                return True, (f"bloco {bloco.label} com 2+ unis squat: "
                              f"{unis_squat_bloco}")
    return False, ""


CENARIO_2_4 = Cenario(
    id="2.4",
    nome="Lateralidade Médio em squats (densificado, baseline)",
    setup_descricao="padrão squat_unilateral(2) × 1 treino, 1000 rotinas",
    expectativa_descricao="~100% (baseline pre-D2)",
    expectativa_predicate=lambda pct: pct >= 95.0,
    config_factory=_cfg_2_4,
    n_treinos=1,
    metrica_fn=_metrica_2_4,
    metricas_secundarias=[
        ("% rotinas com 2 unis pareados no MESMO bloco (alvo C)",
         _metrica_2_4_sub_a),
    ],
)


# ---------------------------------------------------------------------------
# Cenário 3.2 — subida_elevada coexist INTER (família refinada nova)
#
# E.0 expectativa: <10% rotinas onde 2+ membros da família `subida_elevada`
# coexistem em treinos diferentes. Pre-Etapa 7 (família INTER ainda hard via
# `variacao_pais_globais`): esperado ~0% (hard bloqueia coexistência).
# Pos-Etapa 7 (família INTER soft alto via score, D3.2 Caminho C): esperado
# <10% (desincentiva mas permite quando banco aperta).
#
# Setup: 2 treinos × `padrão squat_unilateral(2)` cada (4 unis na rotina).
# Banco squat_unilateral: 12 candidatos com 4 em subida_elevada (Step Up,
# Step Up Alt., Passada Dos Steps, Recuo do Estepe mock_futuro).
# ---------------------------------------------------------------------------

def _cfg_3_2(banco: list[Exercicio]) -> list[dict]:  # noqa: ARG001
    return [{
        "demandas": [("padrao", "squat_unilateral", 2)],
        "tamanho_bloco": 2,
        "evitar_agonistas": True,
        "max_complexidade": 5,
    }]


def _metrica_3_2(sessoes: list[Sessao],
                  dims: dict[str, MockDimensoes]) -> tuple[bool, str]:
    """Detecta 2+ ex distintos da família `subida_elevada` na rotina total."""
    nomes_se: list[str] = []
    for sessao in sessoes:
        for bloco in sessao.blocos:
            for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
                if ex is None:
                    continue
                d = dims.get(ex.nome)
                if d and d.familia_estrita == "subida_elevada":
                    nomes_se.append(ex.nome)
    nomes_distintos = set(nomes_se)
    if len(nomes_distintos) >= 2:
        return True, f"2+ subida_elevada na rotina: {sorted(nomes_distintos)}"
    return False, ""


CENARIO_3_2 = Cenario(
    id="3.2",
    nome="subida_elevada coexist INTER (família refinada)",
    setup_descricao="2 treinos × squat_unilateral(2), 1000 rotinas",
    expectativa_descricao="<10% (pre-Etapa 7 ~0%; pos <10%)",
    expectativa_predicate=lambda pct: pct < 10.0,
    config_factory=_cfg_3_2,
    n_treinos=2,
    metrica_fn=_metrica_3_2,
)


# ---------------------------------------------------------------------------
# Cenário 3.3 — Passada + Passada Dos Steps INTER (famílias dif)
#
# E.0 expectativa: 20-50% rotinas onde Passada (família `passada`) coexiste
# com QUALQUER membro de `subida_elevada` (incl. Passada Dos Steps) entre
# treinos. Famílias DIFERENTES após reclassificação Sessão 2 — soft INTER
# família NÃO atua (só dentro da mesma família). Frequência natural sem
# penalty.
#
# Validação clínica do Caminho 5 (Seção 2 G4): trade-off aceito da
# refinamento — Passada+Passada Dos Steps perde hard de família, mas
# correção é clínica (mecanicas diferentes). Cenário confirma que o setup
# funciona como esperado: famílias dif → coexistência permitida.
#
# Setup: idêntico ao 3.2 (2 treinos × squat_unilateral(2)).
# Predicate: `pct < 80.0` (faixa wide pra catch absurdos; 20-50% é
# referência E.0, baseline informativo).
# ---------------------------------------------------------------------------

def _cfg_3_3(banco: list[Exercicio]) -> list[dict]:  # noqa: ARG001
    return [{
        "demandas": [("padrao", "squat_unilateral", 2)],
        "tamanho_bloco": 2,
        "evitar_agonistas": True,
        "max_complexidade": 5,
    }]


def _metrica_3_3(sessoes: list[Sessao],
                  dims: dict[str, MockDimensoes]) -> tuple[bool, str]:
    """Detecta Passada (família `passada`) + qualquer subida_elevada
    coexistindo na rotina (em treinos quaisquer)."""
    todos_nomes: set[str] = set()
    for sessao in sessoes:
        for bloco in sessao.blocos:
            for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
                if ex is not None:
                    todos_nomes.add(ex.nome)
    has_passada = "Passada" in todos_nomes
    subidas_pres = [
        n for n in todos_nomes
        if dims.get(n) and dims[n].familia_estrita == "subida_elevada"
    ]
    if has_passada and subidas_pres:
        return True, f"Passada + subida_elevada: {sorted(subidas_pres)}"
    return False, ""


CENARIO_3_3 = Cenario(
    id="3.3",
    nome="Passada + Passada Dos Steps INTER (famílias dif)",
    setup_descricao="2 treinos × squat_unilateral(2), 1000 rotinas",
    expectativa_descricao="20-50% (referência E.0, baseline)",
    expectativa_predicate=lambda pct: pct < 80.0,
    config_factory=_cfg_3_3,
    n_treinos=2,
    metrica_fn=_metrica_3_3,
)


# ---------------------------------------------------------------------------
# Cenário 5.2 — Retroativo v_up_uni (não-regressão Etapa 5)
#
# Replica o cenário do tools/medir_entropia_pareamentos.py. Mede % de pareamento
# V-Up Uni + Tríceps Uni (esperado preferencial) vs V-Up Uni + Hollow Hold.
# ---------------------------------------------------------------------------

def _cfg_5_2(banco: list[Exercicio]) -> list[dict]:
    travados = [e for e in banco
                if e.nome in {"V-Up Unilateral", "Tríceps Unilateral Polia"}]
    return [{
        "demandas": [("padrao", "core_isometrico", 1)],
        "exercicios_travados": travados,
        "tamanho_bloco": 2,
        "evitar_agonistas": True,
        "max_complexidade": 5,
    }]


def _metrica_5_2(sessoes: list[Sessao],
                 dims: dict[str, MockDimensoes]) -> tuple[bool, str]:  # noqa: ARG001
    """Detecta se V-Up Uni e Tríceps Uni NÃO foram pareados no mesmo bloco.

    Métrica positiva (violacao=True) = par esperado NÃO ocorreu.
    Expectativa: <50% violações (= >50% pareados como esperado).
    """
    for sessao in sessoes:
        for bloco in sessao.blocos:
            nomes = {ex.nome for ex in (bloco.ex1, bloco.ex2, bloco.ex3) if ex}
            if {"V-Up Unilateral", "Tríceps Unilateral Polia"} <= nomes:
                return False, ""  # par esperado encontrado
    return True, "V-Up Uni + Tríceps Uni NÃO pareados no mesmo bloco"


CENARIO_5_2 = Cenario(
    id="5.2",
    nome="Retroativo v_up_uni (não-regressão Etapa 5)",
    setup_descricao="core_iso(1) + travados V-Up Uni + Tríceps Uni, 1000 rotinas",
    expectativa_descricao="<50% (par esp >50%)",
    expectativa_predicate=lambda pct: pct < 50.0,
    config_factory=_cfg_5_2,
    n_treinos=1,
    metrica_fn=_metrica_5_2,
    relaxar_familia=True,
)


# ---------------------------------------------------------------------------
# Cenário 6.1 — Happy path (sanity check over-penalização + refator CORE)
#
# upper(3) + lower(3) + core(2) × 2 treinos. Decomposto por região: avisos
# globais + por região. Testa que (i) calibração não vaza em rotina realista,
# (ii) refator estrutural CORE da Sessão 2 não cria fricção em core(2).
# ---------------------------------------------------------------------------

def _cfg_6_1(banco: list[Exercicio]) -> list[dict]:  # noqa: ARG001
    return [{
        "demandas": [
            ("regiao", "upper", 3),
            ("regiao", "lower", 3),
            ("regiao", "core", 2),
        ],
        "tamanho_bloco": 2,
        "evitar_agonistas": True,
        "max_complexidade": 5,
    }]


_AVISOS_ETAPA_6 = frozenset({"incompleta", "familia_repetida"})
_AVISOS_ETAPA_3 = frozenset({"ancora_nao_cumprida"})


def _metrica_6_1_primaria(sessoes: list[Sessao],
                          dims: dict[str, MockDimensoes]) -> tuple[bool, str]:  # noqa: ARG001
    """Métrica primária — gate de status: % rotinas com aviso de calibração
    da Etapa 6 (incompleta, familia_repetida).

    Exclui `ancora_nao_cumprida` (escopo Etapa 3 — vagas insuficientes pra
    âncoras obrigatórias). Esse achado paralelo é tracked na métrica
    secundária.
    """
    avisos_etapa_6: list[str] = []
    regs_afetadas: set[str] = set()
    for sessao in sessoes:
        for av in sessao.avisos:
            tipo = av.get("tipo", "?")
            if tipo in _AVISOS_ETAPA_6:
                avisos_etapa_6.append(tipo)
                esc = av.get("escopo_demanda", "")
                if esc:
                    regs_afetadas.add(esc)
    if not avisos_etapa_6:
        return False, ""
    return True, (f"avisos_E6={avisos_etapa_6[:3]} "
                  f"regioes={sorted(regs_afetadas)}")


def _metrica_6_1_secundaria(sessoes: list[Sessao],
                            dims: dict[str, MockDimensoes]) -> tuple[bool, str]:  # noqa: ARG001
    """Métrica secundária — informativa: % rotinas com `ancora_nao_cumprida`.

    Achado paralelo: vagas insuficientes em rotinas apertadas (`upper(3)`
    com 4 obrigatórias subregião) força sorteio uniforme entre obrigatórias.
    Mecanismo da Etapa 3 funcionando conforme spec; a frequência alta é
    sinal de que setup `upper(3)` é apertado clinicamente, não falha.
    Caracterização realista deve usar configurações de
    `configuracoes_comuns.md` quando essa frente for retomada.
    """
    avisos_e3: list[tuple[str, str]] = []
    for sessao in sessoes:
        for av in sessao.avisos:
            tipo = av.get("tipo", "?")
            if tipo in _AVISOS_ETAPA_3:
                avisos_e3.append((tipo, av.get("chave", "?")))
    if not avisos_e3:
        return False, ""
    chaves = sorted({c for _, c in avisos_e3})
    return True, f"ancoras_falhas={chaves}"


CENARIO_6_1 = Cenario(
    id="6.1",
    nome="Happy path (sanity over-penalização + refator CORE)",
    setup_descricao="upper(3)+lower(3)+core(2) × 2 treinos, 1000 rotinas",
    expectativa_descricao="<5% (E6 only)",
    expectativa_predicate=lambda pct: pct < 5.0,
    config_factory=_cfg_6_1,
    n_treinos=2,
    metrica_fn=_metrica_6_1_primaria,
    metricas_secundarias=[
        ("% com ancora_nao_cumprida (Etapa 3, informativo)",
         _metrica_6_1_secundaria),
    ],
)


# ---------------------------------------------------------------------------
# Cenário 6.2 — Happy path Variante B (Empurrar/Puxar split, granularidade
# subregião). Promovido pra pré-D2 na Sessão 6 (auditoria E.0). Cobre a
# metade do uso real 2x semana que 6.1 não cobre + vira proxy realista pros
# gotchas de 1.2 e 2.2A via 2 sub-métricas (Nota de processo #2 da Seção 8.6).
#
# Configuração (configuracoes_comuns.md Seção 2.2 Variante B):
#   T1 (Empurrar + perna posterior):
#       peito(2) + ombro(1) + perna_posterior(3) + core(1) + tríceps(1)
#   T2 (Puxar + perna anterior):
#       costas(3) + perna_anterior(3) + core(1) + bíceps(1)
#
# Métricas:
#   - Primária : avisos E6 (incompleta + familia_repetida) — gate <5%
#   - Sub-a   : % blocos com 2+ unilaterais do mesmo grupo musculo-funcional
#                (proxy realista pra calibração do anti_uni soft -75)
#   - Sub-b   : % rotinas com 2+ unilaterais em costas no T2
#                (proxy realista pra calibração do hard contextual D1.d)
# ---------------------------------------------------------------------------

def _cfg_6_2(banco: list[Exercicio]) -> list[dict]:  # noqa: ARG001
    # Tríceps em T1 e bíceps em T2 são fixos via granularidade padrão (não
    # subregião `bracos`, que cycla entre os dois sem garantir o split do
    # uso real Variante B descrito em `configuracoes_comuns.md` Seção 2.2).
    #
    # Core: usa `core_dinamico` em T1 e `core_isometrico` em T2 (alternância
    # clínica natural). A subregião legacy `core` (que `configuracoes_comuns.md`
    # menciona como `core(1)`) foi refatorada na Sessão 2 da Fase 1 (item
    # 15-quater) em `core_dinamico` + `core_isometrico`. Retrocompat existe
    # em `_padroes_de_escopo` mas NÃO no caminho de alocação principal —
    # `("subregiao", "core", 1)` falha com `qtd_obtida=0`. Bug paralelo
    # registrado pra investigação separada (fora do escopo Sessão 6).
    base_t1 = {
        "demandas": [
            ("subregiao", "peito", 2),
            ("subregiao", "ombro", 1),
            ("subregiao", "perna_posterior", 3),
            ("subregiao", "core_dinamico", 1),
            ("padrao", "triceps", 1),
        ],
        "tamanho_bloco": 2,
        "evitar_agonistas": True,
        "max_complexidade": 5,
    }
    base_t2 = {
        "demandas": [
            ("subregiao", "costas", 3),
            ("subregiao", "perna_anterior", 3),
            ("subregiao", "core_isometrico", 1),
            ("padrao", "biceps", 1),
        ],
        "tamanho_bloco": 2,
        "evitar_agonistas": True,
        "max_complexidade": 5,
    }
    return [base_t1, base_t2]


def _metrica_6_2_primaria(sessoes: list[Sessao],
                          dims: dict[str, MockDimensoes]) -> tuple[bool, str]:  # noqa: ARG001
    """Métrica primária — gate de status: % rotinas com aviso de calibração
    da Etapa 6 (incompleta, familia_repetida). Mesma lógica do 6.1.
    """
    avisos_etapa_6: list[str] = []
    subregioes_afetadas: set[str] = set()
    for sessao in sessoes:
        for av in sessao.avisos:
            tipo = av.get("tipo", "?")
            if tipo in _AVISOS_ETAPA_6:
                avisos_etapa_6.append(tipo)
                esc = av.get("escopo_demanda", "")
                if esc:
                    subregioes_afetadas.add(esc)
    if not avisos_etapa_6:
        return False, ""
    return True, (f"avisos_E6={avisos_etapa_6[:3]} "
                  f"subregioes={sorted(subregioes_afetadas)}")


def _metrica_6_2_sub_a(sessoes: list[Sessao],
                        dims: dict[str, MockDimensoes]) -> tuple[bool, str]:  # noqa: ARG001
    """Sub-métrica a — % rotinas com bloco contendo 2+ unilaterais do mesmo
    grupo musculo-funcional. Generaliza a métrica do 1.2 pra setup realista
    Variante B (onde anti_uni só pode disparar entre exercícios de subregiões
    diferentes que coexistam num bloco — ex: V-Up Uni + Tríceps Uni).
    Tracking pro gotcha "calibrar denso, validar realista".
    """
    for sessao in sessoes:
        for bloco in sessao.blocos:
            unis_por_grupo: dict[str, list[str]] = {}
            for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
                if ex is None or ex.unilateral != "unilateral":
                    continue
                grupo = GRUPO_MUSCULAR_PADRAO.get(ex.padrao, "?")
                unis_por_grupo.setdefault(grupo, []).append(ex.nome)
            for grupo, nomes in unis_por_grupo.items():
                if len(nomes) >= 2:
                    return True, f"bloco {bloco.label} grupo='{grupo}' 2+ unis: {nomes}"
    return False, ""


def _metrica_6_2_sub_b(sessoes: list[Sessao],
                        dims: dict[str, MockDimensoes]) -> tuple[bool, str]:  # noqa: ARG001
    """Sub-métrica b — % rotinas com 2+ unilaterais em costas (treino T2,
    `costas(3)` da Variante B). Tracking pro gotcha do hard contextual D1.d
    em setup realista (vs `remadas(2)` patológico do 2.2A).
    """
    for sessao in sessoes:
        unis_costas: list[str] = []
        for bloco in sessao.blocos:
            for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
                if ex is None:
                    continue
                if ex.subregiao == "costas" and ex.unilateral == "unilateral":
                    unis_costas.append(ex.nome)
        if len(unis_costas) >= 2:
            return True, f"costas 2+ unis: {unis_costas}"
    return False, ""


CENARIO_6_2 = Cenario(
    id="6.2",
    nome="Happy path Variante B (subregião, Empurrar/Puxar)",
    setup_descricao="peito(2)+ombro(1)+perna_post(3)+core(1)+bracos(1) // "
                    "costas(3)+perna_ant(3)+core(1)+bracos(1), 1000 rotinas",
    expectativa_descricao="<5% (E6 only)",
    expectativa_predicate=lambda pct: pct < 5.0,
    config_factory=_cfg_6_2,
    n_treinos=2,
    metrica_fn=_metrica_6_2_primaria,
    metricas_secundarias=[
        ("% blocos com 2+ unis mesmo grupo (proxy 1.2 realista)",
         _metrica_6_2_sub_a),
        ("% rotinas com 2+ unis em costas T2 (proxy 2.2A realista)",
         _metrica_6_2_sub_b),
    ],
)


# ---------------------------------------------------------------------------
# Cenário 2.1 — Ranking ordinal Reto vs Inclinado (peito 2x2)
#
# Setup pre-registrado Sessão 7b (Seção 8.14.4 Pré-registro 2.1): 2 treinos
# × peito(2) cada. Mock_futuro Supino Inclinado Halteres adicionado em 7c
# (Decisão user) pra completar 3ª faixa mensurável.
#
# **Tabela de pares mensuráveis pós-hard INTRA família (protocolo Decisão 1):**
# Banco peito após overlay: 4 Retos (3 cadastrados + 1 mock_futuro Supino
# Fechado) + 2 Inclinados (Smith + Halteres mock_futuro) + 4 Apoios
# (3 cadastrados + 1 mock_futuro Apoio Fechado) + 1 crucifixo + 2 crossover
# = 13 cadastros válidos.
#
# Pares Reto+Reto INTER e Inclinado+Inclinado INTER: ambos bloqueados
# pre-Etapa 7 por hard INTER família (`variacao_pais_globais` set). Pos-Etapa 7
# (D3.2 Caminho C — soft INTER alto): expectativa <15% cada.
# ---------------------------------------------------------------------------

def _cfg_2_1(banco: list[Exercicio]) -> list[dict]:  # noqa: ARG001
    return [{
        "demandas": [("subregiao", "peito", 2)],
        "tamanho_bloco": 2,
        "evitar_agonistas": True,
        "max_complexidade": 5,
    }]


def _metrica_2_1(sessoes: list[Sessao],
                  dims: dict[str, MockDimensoes]) -> tuple[bool, str]:
    """Métrica primária — % rotinas com 2+ ex da MESMA família refinada peito
    coexistindo entre treinos (Reto-Reto OU Inclinado-Inclinado).

    Pre-Etapa 7: ~0% (hard INTER família via variacao_pais_globais).
    Pos-Etapa 7: <30% somando ambas faixas (soft INTER alto desincentiva).
    """
    fams_peito_por_treino: list[set[str]] = []
    for sessao in sessoes:
        fams: set[str] = set()
        for bloco in sessao.blocos:
            for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
                if ex is None or ex.subregiao != "peito":
                    continue
                d = dims.get(ex.nome)
                if d and d.familia_estrita in ("Supino Reto", "Supino Inclinado"):
                    fams.add(d.familia_estrita)
        fams_peito_por_treino.append(fams)
    # Mesma família (Reto OU Inclinado) em 2+ treinos
    for fam in ("Supino Reto", "Supino Inclinado"):
        treinos_com_fam = sum(1 for f in fams_peito_por_treino if fam in f)
        if treinos_com_fam >= 2:
            return True, f"familia '{fam}' em {treinos_com_fam} treinos"
    return False, ""


def _metrica_2_1_sub_reto(sessoes: list[Sessao],
                           dims: dict[str, MockDimensoes]) -> tuple[bool, str]:
    """Sub-métrica — % rotinas com 2+ Supino Reto inter-treinos."""
    treinos_com_reto = 0
    for sessao in sessoes:
        tem_reto = any(
            dims.get(ex.nome) and dims[ex.nome].familia_estrita == "Supino Reto"
            for bloco in sessao.blocos
            for ex in (bloco.ex1, bloco.ex2, bloco.ex3)
            if ex is not None
        )
        if tem_reto:
            treinos_com_reto += 1
    if treinos_com_reto >= 2:
        return True, f"Supino Reto em {treinos_com_reto} treinos"
    return False, ""


def _metrica_2_1_sub_inclinado(sessoes: list[Sessao],
                                dims: dict[str, MockDimensoes]) -> tuple[bool, str]:
    """Sub-métrica — % rotinas com 2+ Supino Inclinado inter-treinos."""
    treinos_com_inc = 0
    for sessao in sessoes:
        tem_inc = any(
            dims.get(ex.nome) and dims[ex.nome].familia_estrita == "Supino Inclinado"
            for bloco in sessao.blocos
            for ex in (bloco.ex1, bloco.ex2, bloco.ex3)
            if ex is not None
        )
        if tem_inc:
            treinos_com_inc += 1
    if treinos_com_inc >= 2:
        return True, f"Supino Inclinado em {treinos_com_inc} treinos"
    return False, ""


CENARIO_2_1 = Cenario(
    id="2.1",
    nome="Ranking ordinal Supino Reto vs Inclinado (peito 2x2)",
    setup_descricao="2 treinos × peito(2), 1000 rotinas",
    expectativa_descricao="<30% (pre-Etapa 7 ~0%)",
    expectativa_predicate=lambda pct: pct < 30.0,
    config_factory=_cfg_2_1,
    n_treinos=2,
    metrica_fn=_metrica_2_1,
    metricas_secundarias=[
        ("% rotinas com 2+ Supino Reto inter-treinos",
         _metrica_2_1_sub_reto),
        ("% rotinas com 2+ Supino Inclinado inter-treinos",
         _metrica_2_1_sub_inclinado),
    ],
)


# ---------------------------------------------------------------------------
# Cenário 3.1 — Variante B 3x com peito em A1 e A2 (família INTER refinada)
#
# Setup REDEFINIDO pela auditoria E.0 (Sessão 6, Seção 8.6): de "rotina 3T
# toda de peito" caricatural pra rotina realista Variante B 3x A1/A2 do
# `configuracoes_comuns.md` Seção 2.3. Ciclo A-B-A: T1 (A1) e T3 (A2)
# repetem peito; T2 (B) é puxar+anterior.
#
# Métrica: % rotinas onde Supino Reto coexiste em T1 (A1) E T3 (A2).
# Pre-Etapa 7: ~0% (hard INTER família). Pos-Etapa 7: 10-15% (E.0
# expectativa — soft INTER alto desincentiva mas permite quando aperta).
# ---------------------------------------------------------------------------

def _cfg_3_1(banco: list[Exercicio]) -> list[dict]:  # noqa: ARG001
    # T1 = A1 (Empurrar + perna_post)
    a1 = {
        "demandas": [
            ("subregiao", "peito", 2),
            ("subregiao", "ombro", 1),
            ("subregiao", "perna_posterior", 3),
            ("subregiao", "core_dinamico", 1),
            ("padrao", "triceps", 1),
        ],
        "tamanho_bloco": 2,
        "evitar_agonistas": True,
        "max_complexidade": 5,
    }
    # T2 = B (Puxar + perna_anterior)
    b = {
        "demandas": [
            ("subregiao", "costas", 3),
            ("subregiao", "perna_anterior", 3),
            ("subregiao", "core_isometrico", 1),
            ("padrao", "biceps", 1),
        ],
        "tamanho_bloco": 2,
        "evitar_agonistas": True,
        "max_complexidade": 5,
    }
    # T3 = A2 (mesmo molde do A1)
    a2 = dict(a1)
    return [a1, b, a2]


def _metrica_3_1(sessoes: list[Sessao],
                  dims: dict[str, MockDimensoes]) -> tuple[bool, str]:
    """% rotinas com Supino Reto em T1 (A1) E T3 (A2) simultaneamente."""
    if len(sessoes) < 3:
        return False, ""
    t1, _, t3 = sessoes[0], sessoes[1], sessoes[2]
    def _tem_reto(s):
        return any(
            dims.get(ex.nome) and dims[ex.nome].familia_estrita == "Supino Reto"
            for bloco in s.blocos
            for ex in (bloco.ex1, bloco.ex2, bloco.ex3)
            if ex is not None
        )
    if _tem_reto(t1) and _tem_reto(t3):
        return True, "Supino Reto em A1 (T1) E A2 (T3)"
    return False, ""


CENARIO_3_1 = Cenario(
    id="3.1",
    nome="Variante B 3x A1/A2 — Reto INTER (família refinada)",
    setup_descricao="A1 + B + A2 (peito(2) em A1 e A2), 1000 rotinas",
    expectativa_descricao="<20% (pre-Etapa 7 ~0%; pos 10-15%)",
    expectativa_predicate=lambda pct: pct < 20.0,
    config_factory=_cfg_3_1,
    n_treinos=3,
    metrica_fn=_metrica_3_1,
)


# ---------------------------------------------------------------------------
# Cenários 4.1 + 4.2 — HISTÓRICO toggle ON/OFF
#
# **Setup B** (Sessão pós-13 — item 7 da 8.15.7, 2026-05-09): R-1 vira
# Variante A 2x (full-body região), rotina nova mantém Variante B 2x
# (subregião). Estruturas DIFERENTES — banco efetivo da R-1 cobre região
# inteira (upper(N)/lower(N)), liberando "ar" pra mecanismo HIST trabalhar
# sem violar invariante INTER+HIST > -100. Substitui setup pré-13, que
# usava R-1 = R-2 = Variante B 2x e prendia 4.1 em ~22% (banco apertado
# demais — Seção 8.15.7 item 7 / 8.15.8 Reconciliação).
#
# Variante A 2x = `configuracoes_comuns.md` Seção 2.2:
#   - Treino A1 (viés upper): upper(5) + lower(2) + core_dinamico(1) = 8 ex
#   - Treino A2 (viés lower): lower(5) + upper(2) + core_isometrico(1) = 8 ex
#   Ambos full-body; cada um com volume maior em metade complementar.
#
# Rotina nova (R-2) mantém Variante B 2x — split subregião (peito+ombro+
# perna_post / costas+perna_ant). Estruturas diferentes = banco efetivo
# de R-1 expõe set amplo (regiões); banco efetivo de R-2 concentra em
# subregiões. Score HIST tem mais alternativas pra escolher exercícios
# diferentes da R-1.
#
# 4.1 (toggle ON, esperado <10% slots pós-setup B): **% slots com
#   overlap** agregado cross-iter (refinamento contínuo Fase 7.5 — opção
#   A do user na Sessão 12; Seção 8.15.6 achado pós-7.4). Harness PASSA
#   list[Sessao] da R-1 pra `gerar_multiplos_treinos(historico_r1=...)`
#   — score HIST aplica penalty quando candidato match nome ou família
#   com R-1.
# 4.2 (toggle OFF, esperado alto): aceita repetição. `historico_r1=None`
#   (default) = comportamento sem score HIST. Predicate informativo.
#   Mesma métrica contínua de 4.1 — comparação significativa é o GAP
#   4.2 - 4.1 = magnitude do efeito do toggle HIST.
# ---------------------------------------------------------------------------

_R1_SEED = 99999  # Seed fixa pra rotina semana anterior


def _gerar_sessoes_r1_variante_a(banco: list[Exercicio]) -> list[Sessao]:
    """Gera sessões da R-1 fixa (Variante A 2x — full-body com viés).
    Cacheável por banco porque mesma seed 99999 + mesmo banco sempre dá
    mesma R-1.

    Setup B do refinamento métrica 4.1 (item 7 da 8.15.7) — R-1 vira
    Variante A enquanto R-2 (rotina nova) mantém Variante B. Estruturas
    diferentes liberam "ar" pra mecanismo HIST trabalhar sem violar
    invariante INTER+HIST > -100.

    Usado em 2 contextos:
    - **Métrica** 4.1/4.2 (extrai nomes+famílias pra detectar overlap).
    - **Score HIST** Fase 7.4: cenário 4.1 passa essa lista pra
      `gerar_multiplos_treinos(historico_r1=...)` via `historico_r1_factory`.
    """
    random.seed(_R1_SEED)
    # Setup B oficial pós-sondagem Nota #5 (Sessão pós-fechamento item 8,
    # 2026-05-13): C3 vencedor de 5 candidatos sondados (ver Seção 8.15.11
    # tabela). R-1 = regiões separadas + core: T1 upper(7)+core_din(1),
    # T2 lower(7)+core_iso(1). Cada treino concentra densidade em UMA
    # região (~1.75/subregião), enquanto R-2 (Variante B) tem picos
    # densos em subregiões específicas (peito 2, costas 3) — banco
    # efetivo distinto = "ar" pro score HIST escolher exercícios
    # diferentes. Resultado: 22.18% (baseline) → 12.85% (queda 9.3pp).
    config_r1 = [
        {
            "demandas": [
                ("regiao", "upper", 7),
                ("subregiao", "core_dinamico", 1),
            ],
            "tamanho_bloco": 2,
            "evitar_agonistas": True,
            "max_complexidade": 5,
        },
        {
            "demandas": [
                ("regiao", "lower", 7),
                ("subregiao", "core_isometrico", 1),
            ],
            "tamanho_bloco": 2,
            "evitar_agonistas": True,
            "max_complexidade": 5,
        },
    ]
    return gerar_multiplos_treinos(banco, config_r1, relaxar_familia=False)


def _gerar_r1_variante_a(banco: list[Exercicio]) -> tuple[set[str], set[str]]:
    """Devolve (nomes, famílias) da R-1 fixa pra métricas 4.1/4.2."""
    sessoes_r1 = _gerar_sessoes_r1_variante_a(banco)
    nomes_r1: set[str] = set()
    fams_r1: set[str] = set()
    for s in sessoes_r1:
        for b in s.blocos:
            for ex in (b.ex1, b.ex2, b.ex3):
                if ex is None:
                    continue
                nomes_r1.add(ex.nome)
                if ex.variacao_de:
                    fams_r1.add(ex.variacao_de)
    return nomes_r1, fams_r1


def _cfg_4_x(banco: list[Exercicio]) -> list[dict]:  # noqa: ARG001
    """R-2 (rotina nova) = Variante B 2x (split subregião). R-1 vive em
    `_gerar_sessoes_r1_variante_a` (full-body região) — estruturas
    DIFERENTES é a essência do setup B do refinamento métrica 4.1."""
    return [
        {
            "demandas": [
                ("subregiao", "peito", 2),
                ("subregiao", "ombro", 1),
                ("subregiao", "perna_posterior", 3),
                ("subregiao", "core_dinamico", 1),
                ("padrao", "triceps", 1),
            ],
            "tamanho_bloco": 2,
            "evitar_agonistas": True,
            "max_complexidade": 5,
        },
        {
            "demandas": [
                ("subregiao", "costas", 3),
                ("subregiao", "perna_anterior", 3),
                ("subregiao", "core_isometrico", 1),
                ("padrao", "biceps", 1),
            ],
            "tamanho_bloco": 2,
            "evitar_agonistas": True,
            "max_complexidade": 5,
        },
    ]


# Cache lazy da R-1 — calculada na primeira chamada da métrica.
_R1_CACHE: dict[str, tuple[set[str], set[str]]] = {}


def _metrica_4_x_continua_factory(banco_ref: list[Exercicio]):
    """Factory contínua (Fase 7.5 — refinamento métrica 4.1, opção A).

    Devolve `(slots_overlap, slots_total, detalhe)` por iteração — o runner
    soma cross-iter e gateia em `pct = sum(overlap)/sum(total)` agregado.

    Substitui o gate binário "≥1 slot overlap dispara violação" identificado
    como estruturalmente impossível ficar <5% no setup R-1=rotina nova
    (Seção 8.15.6 — achado Fase 7.4). Mecanismo HIST entrega ~1.34
    overlap/rotina ÷ ~18 slots ≈ 7.4% pré-calibração.

    Granularidade nome OR família alinhada a D3.3 (penalty única por
    candidato no `_score_proximidade` HIST).
    """
    def _m(sessoes: list[Sessao],
           dims: dict[str, MockDimensoes]) -> tuple[int, int, str]:  # noqa: ARG001
        if "r1" not in _R1_CACHE:
            _R1_CACHE["r1"] = _gerar_r1_variante_a(banco_ref)
        nomes_r1, fams_r1 = _R1_CACHE["r1"]
        slots_total = 0
        slots_overlap = 0
        amostra_nomes: list[str] = []
        amostra_fams: list[str] = []
        for s in sessoes:
            for bloco in s.blocos:
                for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
                    if ex is None:
                        continue
                    slots_total += 1
                    name_match = ex.nome in nomes_r1
                    fam_match = bool(ex.variacao_de) and ex.variacao_de in fams_r1
                    if name_match or fam_match:
                        slots_overlap += 1
                        if name_match and len(amostra_nomes) < 3:
                            amostra_nomes.append(ex.nome)
                        if (fam_match and ex.variacao_de
                                and len(amostra_fams) < 3):
                            amostra_fams.append(ex.variacao_de)
        if slots_overlap == 0:
            return 0, slots_total, ""
        partes = [f"{slots_overlap}/{slots_total} slots"]
        if amostra_nomes:
            partes.append(f"nomes={amostra_nomes}")
        if amostra_fams:
            partes.append(f"fams={amostra_fams}")
        return slots_overlap, slots_total, "; ".join(partes)
    return _m


def _metrica_4_x_stub(sessoes: list[Sessao],  # noqa: ARG001
                       dims: dict[str, MockDimensoes]  # noqa: ARG001
                       ) -> tuple[bool, str]:
    """Stub do `metrica_fn` pra 4.x — não chamado quando contínua está setada
    (runner usa `metrica_continua_fn` direto). Existe só pra satisfazer o
    contrato required do dataclass `Cenario.metrica_fn`.
    """
    return False, ""


# Cenários instanciados em main() depois de `banco` estar disponível.
# Usa-se factory pattern pra capturar referência. Cenário 4.1 e 4.2 dividem
# mesma métrica (medem mesma coisa); diferença é só predicate + descrição.

def _make_cenario_4_x(cenario_id: str, nome: str, expectativa: str,
                       predicate: Callable[[float], bool],
                       banco: list[Exercicio],
                       toggle_on: bool) -> Cenario:
    """Constrói cenário 4.1 ou 4.2.

    `toggle_on=True` → 4.1: passa `historico_r1=` pra ativar score HIST
    no gerador. Score HIST aplica penalty quando candidato match nome ou
    família com R-1.
    `toggle_on=False` → 4.2: `historico_r1_factory=None` mantém toggle
    OFF (default sem score HIST).

    R-1 cacheada em `_R1_SESSOES_CACHE` pra evitar regerar a cada iter.

    Fase 7.5 — métrica contínua "% slots com overlap" agregada cross-iter
    (refinamento opção A da Sessão 12). `metrica_fn` fica como stub
    (não chamado pelo runner quando `metrica_continua_fn` setada).
    """
    hist_factory: Optional[Callable[[list[Exercicio]], list[Sessao]]] = None
    if toggle_on:
        def _hist_r1(_banco: list[Exercicio]) -> list[Sessao]:
            if "r1_sessoes" not in _R1_SESSOES_CACHE:
                _R1_SESSOES_CACHE["r1_sessoes"] = _gerar_sessoes_r1_variante_a(banco)
            return _R1_SESSOES_CACHE["r1_sessoes"]
        hist_factory = _hist_r1

    return Cenario(
        id=cenario_id,
        nome=nome,
        setup_descricao=("R-2 Variante B 2x, R-1 fixa Variante A 2x "
                         "(seed 99999), 1000 rotinas"),
        expectativa_descricao=expectativa,
        expectativa_predicate=predicate,
        config_factory=_cfg_4_x,
        n_treinos=2,
        metrica_fn=_metrica_4_x_stub,
        metrica_continua_fn=_metrica_4_x_continua_factory(banco),
        historico_r1_factory=hist_factory,
    )


# Cache lazy das sessões R-1 (lista, não só nomes/famílias).
_R1_SESSOES_CACHE: dict[str, list[Sessao]] = {}


# Cenários 4.1 e 4.2 são instanciados dinâmicamente em main() — placeholders
# aqui pra registrá-los no dict CENARIOS antes da inicialização.
# Substituídos por instâncias reais via _patch_cenarios_4_x(banco) abaixo.

CENARIO_4_1: Cenario = None  # type: ignore  # set em _patch_cenarios_4_x
CENARIO_4_2: Cenario = None  # type: ignore


def _patch_cenarios_4_x(banco: list[Exercicio]) -> None:
    """Inicializa CENARIO_4_1 e CENARIO_4_2 com banco real. Chamar em main().

    Fase 7.5 — métrica contínua "% slots com overlap" (opção A da Sessão 12).
    Alvo refinado pós-sondagem Nota #5 (Seção 8.15.11 — fechamento item 7
    da 8.15.7, 2026-05-13): `<15%` reflete piso estrutural do banco mock
    com setup B oficial C3 (~12.85% observado). Mecanismo HIST funcional
    (queda de 9.3pp do baseline 22.18%); fechamento <10% gateado pela
    Fase 4 (XLSX 125+ pode reduzir piso). Gate continua com dentes —
    regressão saltaria pra ~22% se HIST quebrar.
    """
    global CENARIO_4_1, CENARIO_4_2
    CENARIO_4_1 = _make_cenario_4_x(
        cenario_id="4.1",
        nome="HISTÓRICO toggle ON evita R-1",
        expectativa="<15% slots (piso estrutural pós-Nota #5 / setup B C3)",
        predicate=lambda pct: pct < 15.0,
        banco=banco,
        toggle_on=True,
    )
    CENARIO_4_2 = _make_cenario_4_x(
        cenario_id="4.2",
        nome="HISTÓRICO toggle OFF aceita repetição",
        expectativa="alto (informativo — toggle OFF aceita)",
        # Predicate informativo — sempre passa (cenário só registra
        # baseline pós-Etapa 7; comparação significativa é o gap entre
        # 4.1 e 4.2 = magnitude do efeito do toggle HIST).
        predicate=lambda pct: pct >= 0.0,
        banco=banco,
        toggle_on=False,
    )
    # Registra nas posições do dict.
    CENARIOS["4.1"] = CENARIO_4_1
    CENARIOS["4.2"] = CENARIO_4_2


CENARIOS: dict[str, Cenario] = {
    "1.1": CENARIO_1_1,
    "1.2": CENARIO_1_2,
    "1.3": CENARIO_1_3,
    "2.1": CENARIO_2_1,
    "2.2A": CENARIO_2_2_A,
    "2.2B": CENARIO_2_2_B,
    "2.3": CENARIO_2_3,
    "2.4": CENARIO_2_4,
    "3.1": CENARIO_3_1,
    "3.2": CENARIO_3_2,
    "3.3": CENARIO_3_3,
    # 4.1 e 4.2 são adicionados por _patch_cenarios_4_x(banco) em main()
    # (precisam de banco real pra factory da métrica)
    "5.2": CENARIO_5_2,
    "6.1": CENARIO_6_1,
    "6.2": CENARIO_6_2,
    # 5.1 vive em `tests/test_score_proximidade_cross_region.py` como
    # pytest determinístico (decisão Fase 7.5 / Sessão 12 — Seção 8.15.8).
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def rodar_cenario(banco: list[Exercicio], dims: dict[str, MockDimensoes],
                   cenario: Cenario,
                   n_iter: int) -> tuple[float, list[tuple[str, float]],
                                          list[CenarioResultado]]:
    """Roda `n_iter` iterações e devolve (% primária, [(label, %)], iters).

    **Modo binário (default)** — `pct = 100 * n_violacoes / n_iter`.
    **Modo contínuo (Fase 7.5)** — quando `cenario.metrica_continua_fn` é
    setada, `pct = 100 * sum(slots_violando) / sum(slots_total)` agregado
    cross-iter. Per-iter `violacao` no CSV é `slots_violando > 0` (sinal
    binário paralelo pra auditoria).

    Lista de secundárias preserva ordem da declaração no Cenario. Vazia
    quando cenário não tem secundárias.
    """
    iteracoes: list[CenarioResultado] = []
    n_violacoes = 0
    n_secundarias = [0] * len(cenario.metricas_secundarias)
    cont_overlap_total = 0
    cont_slots_total = 0
    eh_continua = cenario.metrica_continua_fn is not None
    for i in range(1, n_iter + 1):
        random.seed(i)
        configs = cenario.config_factory(banco)
        # Quando factory retorna 1 config, replica n_treinos vezes (mesma config
        # em todos os treinos — caso 1.1, 6.1, etc.). Quando retorna lista com
        # len == n_treinos, usa direto (caso 6.2 — Variante B com configs
        # diferentes por treino).
        if len(configs) == 1:
            configs_treinos = configs * cenario.n_treinos
        elif len(configs) == cenario.n_treinos:
            configs_treinos = configs
        else:
            raise ValueError(
                f"Cenário {cenario.id}: config_factory retornou "
                f"{len(configs)} configs, esperado 1 ou {cenario.n_treinos}")
        hist_r1 = (
            cenario.historico_r1_factory(banco)
            if cenario.historico_r1_factory is not None
            else None
        )
        sessoes = gerar_multiplos_treinos(
            banco, configs_treinos,
            relaxar_familia=cenario.relaxar_familia,
            historico_r1=hist_r1,
        )
        if eh_continua:
            slots_o, slots_t, detalhe = cenario.metrica_continua_fn(  # type: ignore[misc]
                sessoes, dims)
            cont_overlap_total += slots_o
            cont_slots_total += slots_t
            violacao = slots_o > 0
        else:
            violacao, detalhe = cenario.metrica_fn(sessoes, dims)
        # Primeira secundária persiste no CSV (back-compat); extras só na tela.
        sec_viol_csv: Optional[bool] = None
        sec_det_csv = ""
        for j, (_label, fn) in enumerate(cenario.metricas_secundarias):
            sv, sd = fn(sessoes, dims)
            if sv:
                n_secundarias[j] += 1
            if j == 0:
                sec_viol_csv = sv
                sec_det_csv = sd
        iteracoes.append(CenarioResultado(
            cenario_id=cenario.id,
            iter_idx=i,
            seed=i,
            seed_hash=_seed_hash(cenario.id, i),
            violacao=violacao,
            detalhe=detalhe,
            secundaria_violacao=sec_viol_csv,
            secundaria_detalhe=sec_det_csv,
        ))
        if violacao:
            n_violacoes += 1
    if eh_continua:
        pct = (100.0 * cont_overlap_total / cont_slots_total
               if cont_slots_total > 0 else 0.0)
    else:
        pct = 100.0 * n_violacoes / n_iter
    pcts_sec = [(label, 100.0 * n / n_iter)
                 for (label, _fn), n in zip(cenario.metricas_secundarias,
                                             n_secundarias)]
    return pct, pcts_sec, iteracoes


def _imprimir_tabela(resultados: list[tuple[Cenario, float,
                                                list[tuple[str, float]]]]) -> None:
    """Tabela de cenários com expectativa vs observado.

    Cada métrica secundária do cenário vira uma linha informativa com prefixo
    `>> secundaria:`, sem afetar status.
    """
    print()
    print("=" * 100)
    print(f"{'ID':<5} {'Cenário':<45} {'Esperado':<18} {'Observado':<12} {'Status':<8}")
    print("=" * 100)
    for cen, pct, pcts_sec in resultados:
        status = "OK" if cen.expectativa_predicate(pct) else "FAIL"
        print(f"{cen.id:<5} {cen.nome:<45} {cen.expectativa_descricao:<18} "
              f"{pct:>6.2f}%     {status:<8}")
        for label, pct_sec in pcts_sec:
            print(f"      >> secundaria: {label:<55}"
                  f"{pct_sec:>6.2f}%     [info]")
    print("=" * 100)


def _exportar_csv(path: Path, todas: list[CenarioResultado]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cenario_id", "iter_idx", "seed", "seed_hash",
                    "violacao", "detalhe",
                    "secundaria_violacao", "secundaria_detalhe"])
        for r in todas:
            sec = "" if r.secundaria_violacao is None else int(r.secundaria_violacao)
            w.writerow([r.cenario_id, r.iter_idx, r.seed, r.seed_hash,
                        int(r.violacao), r.detalhe,
                        sec, r.secundaria_detalhe])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cenario", default="all",
                        help="ID do cenário (ex: 1.1) ou 'all' (default).")
    parser.add_argument("--n-iter", type=int, default=N_ITER_DEFAULT,
                        help=f"Iterações por cenário (default: {N_ITER_DEFAULT})")
    parser.add_argument("--csv", type=Path, default=None,
                        help="Caminho opcional pra CSV de auditoria por iteração.")
    args = parser.parse_args()

    banco = carregar_banco(str(XLSX))
    dims, futuros = _carregar_mocks()
    banco = _aplicar_overlay(banco, dims, futuros)
    _patch_cenarios_4_x(banco)  # 4.1/4.2 dependem de banco real (R-1 fixa)
    print(f"Banco: {len(banco)} exercícios "
          f"({len(dims)} mockados, {len(futuros)} mock_futuro)")
    print(f"Iterações por cenário: {args.n_iter}")

    if args.cenario == "all":
        ids = list(CENARIOS.keys())
    else:
        if args.cenario not in CENARIOS:
            print(f"Cenário '{args.cenario}' não encontrado. Disponíveis: "
                  f"{list(CENARIOS.keys())}", file=sys.stderr)
            sys.exit(1)
        ids = [args.cenario]

    resultados: list[tuple[Cenario, float, list[tuple[str, float]]]] = []
    todas_iteracoes: list[CenarioResultado] = []
    for cid in ids:
        cen = CENARIOS[cid]
        print(f"\n[{cid}] {cen.nome}")
        print(f"  Setup       : {cen.setup_descricao}")
        print(f"  Expectativa : {cen.expectativa_descricao}")
        for label, _fn in cen.metricas_secundarias:
            print(f"  Secundária  : {label}")
        print(f"  Rodando {args.n_iter} iterações...")
        pct, pcts_sec, iteracoes = rodar_cenario(banco, dims, cen, args.n_iter)
        cen.iteracoes = iteracoes
        resultados.append((cen, pct, pcts_sec))
        todas_iteracoes.extend(iteracoes)
        n_viol = sum(1 for it in iteracoes if it.violacao)
        if cen.metrica_continua_fn is not None:
            print(f"  Iters c/ overlap : {n_viol}/{args.n_iter}")
            print(f"  % slots overlap  : {pct:.2f}% (agregado cross-iter)")
        else:
            print(f"  Violações   : {n_viol}/{args.n_iter} ({pct:.2f}%)")
        for label, pct_sec in pcts_sec:
            print(f"  >> {label}: {pct_sec:.2f}%")
        if n_viol and n_viol <= 5:
            print("  Detalhes das violações:")
            for it in iteracoes:
                if it.violacao:
                    print(f"    seed={it.seed} hash={it.seed_hash} :: {it.detalhe}")

    _imprimir_tabela(resultados)

    if args.csv:
        _exportar_csv(args.csv, todas_iteracoes)
        print(f"\nCSV exportado: {args.csv}")


if __name__ == "__main__":
    main()
