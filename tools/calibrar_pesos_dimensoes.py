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
    """Sobrescreve `variacao_de` em Exercicios cadastrados conforme mock e
    adiciona Exercicios mock_futuro ao banco.

    Apenas `familia_estrita` afeta o gerador atual (via `variacao_de`); demais
    dims ficam disponíveis no dict `dims` pra uso futuro do stub
    `_penalty_proximidade`.
    """
    nomes_cadastrados = {e.nome for e in banco}
    for ex in banco:
        if ex.nome in dims:
            fam = dims[ex.nome].familia_estrita
            if fam is not None:
                ex.variacao_de = fam

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


@dataclass
class Cenario:
    """Definição de um cenário-âncora da E.0.

    `metrica_fn` é o gate de status (primária). `metrica_secundaria_fn` é
    sinal informativo paralelo — quando presente, runner reporta a taxa
    da secundária mas NÃO afeta o status do cenário.
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
    # Métrica secundária opcional. Quando presente, reportada como sinal
    # paralelo no output. Útil pra distinguir "calibração da Etapa 6 over-
    # penalizou" (primária) de "configuração apertada gera trade-offs de
    # âncora — Etapa 3" (secundária). Ex: 6.1 happy path.
    metrica_secundaria_fn: Optional[Callable[[list[Sessao],
                                              dict[str, MockDimensoes]],
                                             tuple[bool, str]]] = None
    metrica_secundaria_descricao: str = ""


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
    metrica_secundaria_fn=_metrica_6_1_secundaria,
    metrica_secundaria_descricao="% com ancora_nao_cumprida (Etapa 3, informativo)",
)


CENARIOS: dict[str, Cenario] = {
    "1.1": CENARIO_1_1,
    "1.2": CENARIO_1_2,
    "1.3": CENARIO_1_3,
    "2.2A": CENARIO_2_2_A,
    "5.2": CENARIO_5_2,
    "6.1": CENARIO_6_1,
    # TODO E.1.b2 (pós-D2/D3): 2.1, 2.2B, 2.3, 3.1, 3.2, 3.3, 4.1, 4.2
    # TODO E.2: 5.1
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def rodar_cenario(banco: list[Exercicio], dims: dict[str, MockDimensoes],
                   cenario: Cenario,
                   n_iter: int) -> tuple[float, Optional[float], list[CenarioResultado]]:
    """Roda `n_iter` iterações e devolve (% primária, % secundária|None, iters)."""
    iteracoes: list[CenarioResultado] = []
    n_violacoes = 0
    n_secundaria = 0
    tem_secundaria = cenario.metrica_secundaria_fn is not None
    for i in range(1, n_iter + 1):
        random.seed(i)
        configs = cenario.config_factory(banco)
        sessoes = gerar_multiplos_treinos(
            banco, configs * cenario.n_treinos,
            relaxar_familia=cenario.relaxar_familia,
        )
        violacao, detalhe = cenario.metrica_fn(sessoes, dims)
        sec_viol: Optional[bool] = None
        sec_det = ""
        if tem_secundaria:
            sec_viol, sec_det = cenario.metrica_secundaria_fn(sessoes, dims)
            if sec_viol:
                n_secundaria += 1
        iteracoes.append(CenarioResultado(
            cenario_id=cenario.id,
            iter_idx=i,
            seed=i,
            seed_hash=_seed_hash(cenario.id, i),
            violacao=violacao,
            detalhe=detalhe,
            secundaria_violacao=sec_viol,
            secundaria_detalhe=sec_det,
        ))
        if violacao:
            n_violacoes += 1
    pct = 100.0 * n_violacoes / n_iter
    pct_sec = (100.0 * n_secundaria / n_iter) if tem_secundaria else None
    return pct, pct_sec, iteracoes


def _imprimir_tabela(resultados: list[tuple[Cenario, float, Optional[float]]]) -> None:
    """Tabela de cenários com expectativa vs observado.

    Quando cenário tem métrica secundária, imprime linha extra com prefixo
    └─ informativa, sem afetar status.
    """
    print()
    print("=" * 100)
    print(f"{'ID':<5} {'Cenário':<45} {'Esperado':<18} {'Observado':<12} {'Status':<8}")
    print("=" * 100)
    for cen, pct, pct_sec in resultados:
        status = "OK" if cen.expectativa_predicate(pct) else "FAIL"
        print(f"{cen.id:<5} {cen.nome:<45} {cen.expectativa_descricao:<18} "
              f"{pct:>6.2f}%     {status:<8}")
        if pct_sec is not None:
            print(f"      >> secundaria: {cen.metrica_secundaria_descricao:<55}"
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

    resultados: list[tuple[Cenario, float, Optional[float]]] = []
    todas_iteracoes: list[CenarioResultado] = []
    for cid in ids:
        cen = CENARIOS[cid]
        print(f"\n[{cid}] {cen.nome}")
        print(f"  Setup       : {cen.setup_descricao}")
        print(f"  Expectativa : {cen.expectativa_descricao}")
        if cen.metrica_secundaria_fn:
            print(f"  Secundária  : {cen.metrica_secundaria_descricao}")
        print(f"  Rodando {args.n_iter} iterações...")
        pct, pct_sec, iteracoes = rodar_cenario(banco, dims, cen, args.n_iter)
        cen.iteracoes = iteracoes
        resultados.append((cen, pct, pct_sec))
        todas_iteracoes.extend(iteracoes)
        n_viol = sum(1 for it in iteracoes if it.violacao)
        print(f"  Violações   : {n_viol}/{args.n_iter} ({pct:.2f}%)")
        if pct_sec is not None:
            n_sec = sum(1 for it in iteracoes if it.secundaria_violacao)
            print(f"  Secundária  : {n_sec}/{args.n_iter} ({pct_sec:.2f}%)")
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
