# gerador_csp.py
# MVP do refator declarativo - 2026-05-21 (Fatia 1) / 2026-05-23 (Fatia 2 Parte 2)
# Engine declarativa minimalista usando CP-SAT do OR-Tools.
#
# Implementa (do catalogo_constraints.md):
#   - H-T1 (mesma família refinada não repete no treino) [Fatia 2 P2]
#   - H-T2 (variante pontual cross-família same-subregião) [Fatia 2 P2]
#   - H-T3 (lateralidade contextual em costas) [Fatia 2 P2]
#   - H-T4 (vaga única na subregião ⇒ tier ≠ Acessório) [Fatia 1]
#   - H-R1 (cobertura de eixos via compostos cross-treino) [Fatia 2 P2]
#   - H-A1 (âncoras obrigatórias por subregião) [Micro-frente H-A1, 2026-05-25]
#   - H-P1 (nível técnico do aluno filtra pool por complexidade) [Fatia 1]
#   - S-T1 (tier-order: tier alto antes de tier baixo na ordem do treino) [Fatia 1]
# Filtra: ativo=True no load (gerador_treino.carregar_banco descarta).
# Tier: coluna `tier` curada manualmente no XLSX (Fatia 2 Parte 1, 2026-05-23).
#
# Roda em PARALELO ao gerador_treino.py antigo (apenas o campo `tier` foi
# adicionado ao dataclass `Exercicio` + populado em `carregar_banco`).

from __future__ import annotations

import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from ortools.sat.python import cp_model

# Reusa o banco/dataclass do gerador antigo. carregar_banco filtra ativo=True
# e popula `tier` desde a Fatia 2 Parte 2.
from gerador_treino import (
    Exercicio,
    carregar_banco,
    PADRAO_PARA_SUBREGIAO,
    GRUPO_MUSCULAR_PADRAO,  # Fatia 4.B: agrupamento push/pull/quad/... pro S-B1
    XLSX_PATH,
    _padroes_de_escopo,  # Fatia 4.D: expande escopo de demanda → padrões cobertos
    ANCORAS_POR_SUBREGIAO,  # Micro-frente H-A1: âncoras obrigatórias por subregião
    ANCORAS_POR_REGIAO,  # Micro-frente H-A0: âncoras obrigatórias por região
    REGIAO_PARA_SUBREGIOES,  # S-R1 (2026-05-27): cross-treino subregião dentro de região
    SUBREGIAO_PARA_REGIAO,  # S-R1 (2026-05-27): codificação de subregiões
)
# H-T3 reusa a configuração canônica de subregiões com lateralidade hard.
from pesos_proximidade import SUBREGIOES_LATERALIDADE_HARD


# ---------------------------------------------------------------------------
# Tiers
# ---------------------------------------------------------------------------

# Vocabulário de tier (3 níveis). String pra legibilidade; ordem pra S-T1.
TIER_PRINCIPAL = "Principal"
TIER_INTERMEDIARIO = "Intermediário"
TIER_ACESSORIO = "Acessório"

# Rank numérico: MAIOR = mais "alto" (vem primeiro no treino). Usado por S-T1.
TIER_RANK: dict[str, int] = {
    TIER_PRINCIPAL: 3,
    TIER_INTERMEDIARIO: 2,
    TIER_ACESSORIO: 1,
}


# ---------------------------------------------------------------------------
# Fatia 4.A (2026-05-24) — modelagem estrutural de blocos no CSP
# ---------------------------------------------------------------------------
#
# Slots de um treino são agrupados em BLOCOS (superseries). Cada bloco tem
# entre 1 e TAMANHO_MAX_BLOCO slots. Bloco solo (tamanho=1) sempre permitido
# (caso natural quando há 1 slot OR Centralidade Alta + Aderência Alta no
# H-P2 do catálogo, quando essa hard entrar).
#
# Reformulação de S-T1: ordem de blocos (não de slots) respeita tier alto
# antes. Forma par-a-par equivalente: pra pares (s1, s2) no mesmo treino,
# se bloco_idx[s1] < bloco_idx[s2] e tier_rank[s1] < tier_rank[s2], viol.
#
# Sem soft de pareamento (S-B's) na 4.A — motor agrupa "livre" satisfazendo
# só estrutural + tier-order de blocos. S-B1/S-B4 entram em 4.B/4.C.

TAMANHO_MAX_BLOCO: int = 3  # 4.C torna parâmetro vindo da UI


# ---------------------------------------------------------------------------
# Fatia 4.B (2026-05-24) — S-B1 (distância funcional intra-bloco)
# ---------------------------------------------------------------------------
#
# Codificação dos grupos musculares funcionais (push/pull/quad/...) usada
# em S-B1 pra detectar pares agonistas (mesmo grupo) no mesmo bloco.
# Cada grupo único de GRUPO_MUSCULAR_PADRAO recebe um int único.
# Padrão sem grupo definido → código fallback (não colide com grupos reais).

_GRUPOS_UNICOS = sorted(set(GRUPO_MUSCULAR_PADRAO.values()))
GRUPO_FUNC_CODE: dict[str, int] = {g: i for i, g in enumerate(_GRUPOS_UNICOS, start=1)}
_GRUPO_OUTRO_CODE = 0  # fallback: padrão sem grupo conhecido (par "outro+outro" não conta como agonista — favorável)


def _grupo_code_do_ex(ex: Exercicio) -> int:
    """Código int do grupo funcional do exercício. Padrão não mapeado → 0."""
    return GRUPO_FUNC_CODE.get(GRUPO_MUSCULAR_PADRAO.get(ex.padrao, ""), _GRUPO_OUTRO_CODE)


# ---------------------------------------------------------------------------
# S-B5 (2026-05-26) — diversidade de região INTRA-bloco
# ---------------------------------------------------------------------------
#
# Codificação da região do exercício (upper/lower/core/cardio + fallback)
# usada em S-B5 pra detectar pares same-region no mesmo bloco. Recupera a
# feature P1-P4 do `montar_blocos` greedy antigo, perdida na migração CSP.
# Achado 3 da auditoria 2026-05-26: 4/8 blocos saíam com 2 exs da mesma
# região (upper+upper, lower+lower, core+core), anulando o ponto do
# superset (alternância de grupos musculares).

_REGIOES_UNICAS = ["upper", "lower", "core", "cardio"]
REGIAO_CODE: dict[str, int] = {r: i for i, r in enumerate(_REGIOES_UNICAS, start=1)}
_REGIAO_OUTRO_CODE = 0  # fallback: ex sem região conhecida (não conta como same-region — favorável)


def _regiao_code_do_ex(ex: Exercicio) -> int:
    """Código int da região do exercício. Sem região mapeada → 0."""
    return REGIAO_CODE.get(ex.regiao, _REGIAO_OUTRO_CODE)


# ---------------------------------------------------------------------------
# S-R1 (2026-05-27) — distribuição cross-treino de subregião dentro de região
# ---------------------------------------------------------------------------
#
# Codificação de SUBREGIÃO (peito/costas/.../panturrilha/core_isometrico/...)
# usada em S-R1 pra contar slots por subregião em cada treino com demanda
# nivel `regiao`. Achado 1 da auditoria 2026-05-26: T1 e T2 caem no MESMO
# split em `regiao lower(3)` por sortear independentes. S-R1 modela a
# simetria cross-treino explicitamente no objetivo do CSP.
#
# Lista fechada (todas as subregiões válidas em SUBREGIAO_PARA_REGIAO) pra
# garantir codificação estável across rotinas — diferente do `REGIAO_CODE`
# que tem só 4 valores; aqui temos ~11. Código 0 = fallback "outra".

_SUBREGIOES_UNICAS = sorted(SUBREGIAO_PARA_REGIAO.keys())
SUBREGIAO_CODE: dict[str, int] = {
    s: i for i, s in enumerate(_SUBREGIOES_UNICAS, start=1)
}
_SUBREGIAO_OUTRO_CODE = 0


def _subregiao_code_do_ex(ex: Exercicio) -> int:
    """Código int da subregião do exercício. Sem subregião mapeada → 0."""
    return SUBREGIAO_CODE.get(ex.subregiao, _SUBREGIAO_OUTRO_CODE)


# ---------------------------------------------------------------------------
# Fatia 4.E (2026-05-24) — relaxar_familia (bloqueio cross-treino de família)
# ---------------------------------------------------------------------------
#
# Identidade de família CROSS-treino (mais agressiva que H-T1 intra). Pra
# bloqueio entre treinos da rotina, "pai+filho" conta como mesma família —
# diferente do predicado de H-T1 intra que só agrupa filhos do mesmo pai
# (`variacao_de` de ambos não-vazios e iguais).
#
# Definição: `_familia_cross(ex)` = `ex.variacao_de or ex.nome`. Dois ex
# são "mesma família cross" sse `_familia_cross(a) == _familia_cross(b)`.
# Cobre os 3 casos do filtro pré-existente do adapter (Frente C):
#   (i)   ambos têm o mesmo variacao_de  → mesmo pai
#   (ii)  um é pai (variacao_de vazio) do outro (variacao_de == nome do pai)
#   (iii) caso simétrico de (ii)
#
# Quando `relaxar_familia=False` (estrito), `familias_proibidas` pré-filtra
# pool_slot dos slots non-travados (mesma técnica usada em 4.D pra
# `nomes_travados`). Quando True e estrito é inviável, retry sem o filtro;
# `_identificar_relaxados_por_familia` marca os ex cuja família original
# estava no set proibido (pulando travados — decisão deliberada do user).

def _familia_cross(ex: Exercicio) -> str:
    """Identificador de família pra bloqueio CROSS-treino. Pai concentra
    filhos: ex.variacao_de quando filho, ex.nome quando pai (variacao_de
    vazio). Sempre não-vazio — exercício sempre tem nome."""
    return ex.variacao_de or ex.nome


# ---------------------------------------------------------------------------
# Fatia 4.E cargas (2026-05-24) — H-cargas par-a-par no bloco
# ---------------------------------------------------------------------------
#
# Filtro de carga acumulada no bloco. Réplica do `_DIMS_CARGA` /
# `_bloqueio_cargas` do motor antigo (gerador_treino.py:1186-1211).
# Modelagem par-a-par dentro do bloco — NÃO cumulativa por bloco
# (decisão clínica fechada).
#
# Para cada par (a, b) no mesmo bloco e cada dim d com threshold[d] > 0:
#   bloqueia se carga_d(a) >= 1 AND carga_d(b) >= 1 AND (sum) >= threshold[d]
#
# Mapeia: nome da dim no `cargas_config` (chave do dict) → atributo do
# `Exercicio`. Mantemos o atributo `demanda_core` (não `carga_core`) por
# retrocompat com o banco existente.

_DIMS_CARGA_CSP: tuple[tuple[str, str], ...] = (
    ("grip", "carga_grip"),
    ("lombar", "carga_lombar"),
    ("core", "demanda_core"),
)


def _cargas_config_ativo(cargas_config: Optional[dict[str, int]]) -> bool:
    """True quando ao menos 1 dim tem threshold > 0. Pula constraint inteira
    quando todos zeros — preserva 4.D byte-a-byte."""
    if not cargas_config:
        return False
    for dim, _ in _DIMS_CARGA_CSP:
        thr = cargas_config.get(dim, 0)
        if thr and thr > 0:
            return True
    return False


def _viola_carga_par(
    ex_a: Exercicio, ex_b: Exercicio, cargas_config: dict[str, int]
) -> Optional[tuple[str, int, int]]:
    """Predicado: retorna `(dim, soma, threshold)` da PRIMEIRA dim violada
    ou None se par compatível. Espelha `gerador_treino._bloqueio_cargas`
    com leitura de motivo para decoding de aviso pós-solve."""
    for dim, attr in _DIMS_CARGA_CSP:
        thr = cargas_config.get(dim, 0) or 0
        if thr <= 0:
            continue
        va = getattr(ex_a, attr, 0) or 0
        vb = getattr(ex_b, attr, 0) or 0
        if va >= 1 and vb >= 1 and (va + vb) >= thr:
            return (dim, va + vb, thr)
    return None


def _tier_rank(exercicio: Exercicio) -> int:
    """Rank numérico do tier curado. Default 1 (= Acessório) se vazio.

    Banco real (XLSX) tem `tier` 100% preenchido pós-Fatia 2 Parte 1; o
    fallback é só pra fixtures legacy que constroem Exercicio direto.
    """
    return TIER_RANK.get(exercicio.tier, 1)


# ---------------------------------------------------------------------------
# ConfigVariedade — Frente B da Fatia 3 (2026-05-23)
# ---------------------------------------------------------------------------
#
# Knobs pra ativar variedade INTRA-config no `gerar_rotina_csp`. Sem este
# dataclass passado, o motor opera no modo legado (1 solve com Minimize,
# 1 solução determinística — comportamento da Fatia 2 Parte 2).
#
# Com ConfigVariedade, motor entra em 2 fases:
#   Phase 1: resolve com Minimize pra descobrir o ótimo (valor da função
#            objetivo, ex.: nº de inversões de S-T1).
#   Phase 2: reconstrói o modelo SEM Minimize, adiciona
#            `total_penalidade <= optimal + slack`, enumera todas as
#            soluções dentro do bound via CpSolverSolutionCallback (cap em
#            `max_solucoes`), e amostra uma via softmax.
#
# Softmax: peso de cada solução = exp(-distancia / temperatura), onde
# distancia = inversoes_da_solucao - optimal. Soluções "mais ótimas"
# (distancia menor) têm peso maior. Reprodutibilidade via `python_seed`
# (passado pra `random.Random`, isolado do `random` global).
#
# Decisão Bernardo (2026-05-23): default = opt-in via dataclass (Opção A).
# Quando a integração com a UI Flask acontecer, o wiring DEVE passar
# `variedade=ConfigVariedade()` por default — produto espera variedade,
# não rotina determinística. TODO registrado pra Frente C.

@dataclass
class ConfigVariedade:
    """Configuração de variedade INTRA-config pro `gerar_rotina_csp`.

    Atributos:
        slack: inversões adicionais aceitas acima do ótimo. 0 = só
            soluções ótimas; >0 aceita soluções progressivamente piores
            (com peso menor no softmax).
        temperatura: T do softmax sobre as soluções enumeradas. T alto =
            distribuição mais uniforme (qualquer solução enumerada tem
            chance similar). T baixo = concentra perto do ótimo.
        max_solucoes: cap da enumeração. Callback aborta com StopSearch()
            quando atingido. Evita explosão combinatória em rotinas
            subdeterminadas.
        python_seed: seed do `random.Random` usado no softmax. None =
            não-determinístico (cada chamada vê soluções diferentes).
            Inteiro = reprodutível (mesma seed → mesma escolha).
        alpha_tier: peso da modulação por tier (Frente 2 da Fatia 3).
            0.0 = sem modulação (Frente 1 pura). >0 = desincentiva
            soluções que diferem da referência (1ª solução enumerada)
            em SLOTS de tier alto. Distância Hamming ponderada pelo
            tier_rank do slot (Principal=3, Intermediário=2, Acessório=1).
            Score modificado: `peso = exp(-(d + alpha_tier*H) / T)`,
            onde H = sum_s ref_tier_rank[s] * (k[s] != ref[s]).
            Intenção clínica: "varia em Acessórios, conserva Principais".
    """
    slack: int = 0
    temperatura: float = 1.0
    max_solucoes: int = 100
    python_seed: Optional[int] = None
    alpha_tier: float = 0.0


# ---------------------------------------------------------------------------
# Carregamento do banco (filtro ativo=True embutido em carregar_banco)
# ---------------------------------------------------------------------------

def carregar_banco_ativo(path_xlsx: str = XLSX_PATH) -> list[Exercicio]:
    """Carrega o banco já filtrando ativo=True.

    Wrapper fino sobre gerador_treino.carregar_banco, que JÁ descarta linhas
    com ativo=False (gerador_treino.py:991). Existe pra deixar o filtro
    explícito no namespace do spike e pra documentar o critério.
    """
    return carregar_banco(path_xlsx)


# ---------------------------------------------------------------------------
# H-P1 — Nível técnico do aluno filtra o pool por complexidade
# ---------------------------------------------------------------------------

# Teto de complexidade por nível técnico do aluno (escala real do XLSX = int 1-5).
# Nível 3 (avançado) = sem teto. Filtro HARD: aplicado ANTES do solver começar.
TETO_COMPLEXIDADE_POR_NIVEL: dict[int, int] = {
    1: 2,  # iniciante: só baixa complexidade
    2: 3,  # intermediário: média
    3: 5,  # avançado: sem teto efetivo (5 = máximo da escala)
}


def filtrar_pool_por_nivel(banco: list[Exercicio], nivel_aluno: int) -> list[Exercicio]:
    """H-P1: remove exercícios acima do teto de complexidade do nível.

    Filtro hard de pool (vetor de perfil, dimensão Nível técnico). Roda antes
    do solver — exercício complexo demais simplesmente não vira variável.
    Nível desconhecido → sem teto (fail-open, não esconde exercício à toa).
    """
    teto = TETO_COMPLEXIDADE_POR_NIVEL.get(nivel_aluno, 5)
    return [e for e in banco if e.complexidade <= teto]


# ---------------------------------------------------------------------------
# Engine CP-SAT minimalista
# ---------------------------------------------------------------------------
#
# Modelagem (Fatia 1 — só H-T4 + S-T1):
#   - Uma "demanda" (nivel, escopo, qtd) vira `qtd` SLOTS. O treino é a
#     concatenação dos slots na ORDEM das demandas (subregião A, depois B...).
#   - Cada slot recebe exatamente 1 exercício do seu pool (bool de atribuição).
#   - Nenhum exercício se repete no treino (AllDifferent global por nome).
#   - H-T4 (HARD): slot de demanda `subregiao` com qtd==1 não pode receber
#     tier Acessório. NÃO aplica a demandas `padrao` (intenção explícita).
#   - S-T1 (SOFT/objetivo): dentro de cada grupo de demanda, penaliza pares
#     (i<j na ordem) em que o slot mais cedo tem tier MENOR que o mais tarde.
#     Penalidade proporcional ao gap de tier (inversão). Solver minimiza a soma.
#
# Sem ordem de processamento entre demandas: todos os slots negociam no mesmo
# modelo (princípio do refator declarativo). O agrupamento por demanda é só a
# semântica de saída — o solver resolve tudo simultaneamente.


def _pool_da_demanda(banco: list[Exercicio], nivel: str, escopo: str) -> list[Exercicio]:
    """Exercícios elegíveis para uma demanda, conforme o nível de hierarquia."""
    if nivel == "subregiao":
        return [e for e in banco if e.subregiao == escopo]
    if nivel == "padrao":
        return [e for e in banco if e.padrao == escopo]
    if nivel == "regiao":
        return [e for e in banco if e.regiao == escopo]
    return []


# ---------------------------------------------------------------------------
# H-R1 — Cobertura de eixos via compostos cross-treino
# ---------------------------------------------------------------------------
#
# Decisão fechada com Bernardo (2026-05-23): H-R1 usa `purpose == "compound"`
# (composição biomecânica), NÃO `tier != Acessório` (centralidade clínica
# curada). Tier e purpose são ortogonais — Apoio é Intermediário curado mas
# composto biomecânico, conta como cobertura horizontal de peito. Hip Thrust
# é Principal mas isolation, NÃO conta como composto.
#
# Cada regra: subregião precisa de N >= min_slots slots na ROTINA pra ativar.
# Aí, pra cada eixo, soma de assign nos slots de subregião == X >= 1.

H_R1_REGRAS: dict[str, dict] = {
    "costas": {
        "min_slots": 2,
        "eixos": [
            ("puxadas_composto",
             lambda e: e.padrao == "puxadas" and e.purpose == "compound"),
            ("remadas_composto",
             lambda e: e.padrao == "remadas" and e.purpose == "compound"),
        ],
    },
    "peito": {
        "min_slots": 2,
        "eixos": [
            ("horizontal_composto",
             lambda e: e.padrao == "empurrar_compostos" and e.purpose == "compound"),
        ],
    },
    "perna_anterior": {
        "min_slots": 2,
        "eixos": [
            ("bilateral_composto",
             lambda e: (e.subregiao == "perna_anterior"
                        and e.unilateral == "bilateral"
                        and e.purpose == "compound")),
            ("unilateral_composto",
             lambda e: (e.subregiao == "perna_anterior"
                        and e.unilateral == "unilateral"
                        and e.purpose == "compound")),
        ],
    },
}


def _subregioes_da_demanda(nivel: str, escopo: str) -> set[str]:
    """Subregiões que uma demanda DETERMINISTICAMENTE contribui.

    - `subregiao`: trivialmente {escopo}.
    - `padrao`: via mapa canônico `PADRAO_PARA_SUBREGIAO` do gerador antigo
      (1:N pós-Etapa 8 — padrões CORE refinados retornam set de 2). Se 1:N,
      H-R1 ignora (slot não tem subregião determinística pré-solver).
    - `regiao`: ignorada (não modelado na Fatia 2 P2).
    """
    if nivel == "subregiao":
        return {escopo}
    if nivel == "padrao":
        subs = PADRAO_PARA_SUBREGIAO.get(escopo, set())
        return subs if len(subs) == 1 else set()
    return set()


# ---------------------------------------------------------------------------
# Engine CP-SAT — helpers (Frente B Fatia 3 extraiu pra suportar enumeração)
# ---------------------------------------------------------------------------

def _construir_modelo(
    demandas_por_treino: list[list[tuple[str, str, int]]],
    banco: list[Exercicio],
    nivel_aluno: int,
    peso_aderencia: int = 0,
    peso_evitar_agonistas: int = 0,
    tamanho_preferido: int = 2,
    peso_tamanho_bloco: int = 0,
    travados_por_treino: Optional[dict[int, list[Exercicio]]] = None,
    familias_proibidas: Optional[set[str]] = None,
    cargas_config: Optional[dict[str, int]] = None,
    peso_cargas_off: int = 1000,
    peso_sa1: int = 0,
    peso_sa1_repet: int = 0,
    peso_sb5: int = 0,
    peso_sr1: int = 0,
) -> dict:
    """Constrói o CpModel completo (constraints H-T1/T2/T3/T4 + H-R1 +
    penalidades de S-T1, Aderência ao Tier, S-B1 distância funcional
    e S-B4 tamanho preferido do bloco) MAS sem chamar `Minimize`. Caller
    decide se minimiza (Phase 1 / modo legado) ou adiciona bound +
    enumera (Phase 2 da Frente B / Fatia 3).

    `peso_aderencia` (Frente D Fatia 3, 2026-05-24): modulação da dimensão
    "Aderência ao Tier" do vetor de perfil do aluno. 0 (default) = sem
    efeito (preserva byte-a-byte Frente B). >0 adiciona, por SLOT, uma
    penalidade proporcional a `(rank_max - tier_rank[slot]) * peso`. Solver
    minimiza tudo junto → empurra tier alto em qualquer slot, INCLUSIVE
    slots únicos onde S-T1 sozinho não produz par (slot solo = 0 inversões
    qualquer tier escolhido). Resolve o achado #1 da Frente C (slots de
    padrão único caindo em Acessório por sorteio).

    `peso_evitar_agonistas` (Fatia 4.B, 2026-05-24): S-B1 distância
    funcional intra-bloco. 0 (default) = sem efeito (preserva 4.A). >0
    adiciona penalty fixo por par no MESMO BLOCO com MESMO GRUPO
    funcional (push/pull/quad/...). Solver minimiza → motor evita parear
    agonistas. Antagonistas (push+pull) e cross-region (upper+lower)
    saem sem penalty, então naturalmente preferidos.

    `peso_sb5` (S-B5, 2026-05-26): diversidade de região INTRA-bloco.
    0 (default) = sem efeito. >0 adiciona penalty fixo por par no MESMO
    BLOCO com MESMA REGIÃO (upper/lower/core/cardio). Recupera a
    feature P1-P4 do `montar_blocos` greedy antigo (achado 3 da auditoria
    2026-05-26). Default ON via adapter (Bernardo: vale pra qualquer
    rotina multi-região, sem toggle UI). Em demandas single-region (ex:
    `upper(4)` sozinha), motor aceita pareamento same-region pagando
    penalty — graceful degradation natural.

    `peso_sr1` (S-R1, 2026-05-27): distribuição cross-treino de
    subregião dentro de uma demanda nivel `regiao`. 0 (default) = sem
    efeito. >0 adiciona, pra cada par de treinos (t1, t2) com demanda
    mesma região R em ambos e cada subregião S possível em R, penalty
    proporcional a `peso_sr1 * |count_S_t1 - count_S_t2|`. Solver
    minimiza → motor prefere splits simétricos cross-treino (ex: T1=2
    perna_ant + 1 perna_post ↔ T2=1 perna_ant + 2 perna_post em vez de
    ambos no mesmo split). Achado 1 da auditoria 2026-05-26 (faceta de
    simetria). Skip estrutural quando rotina tem <2 treinos. Default ON
    via adapter (sem toggle UI). Não interfere em demandas nivel
    `subregiao` ou `padrao` (não há "região" pra alternar).

    `tamanho_preferido` + `peso_tamanho_bloco` (Fatia 4.C, 2026-05-24):
    S-B4 tamanho preferido do bloco. Default tamanho=2, peso=0 (sem
    efeito; preserva 4.B). Quando peso>0, penaliza desvio do tamanho
    preferido por bloco EM USO (vazios não contam). Equilibra trade-off
    da 4.B (S-B1 ativo empurra motor pra blocos solo) dando incentivo
    positivo a blocos com tamanho desejado pelo user.

    `familias_proibidas` (Fatia 4.E, 2026-05-24): set de identificadores
    `_familia_cross(ex)` de exercícios que NÃO podem aparecer (hard
    cross-treino). Pré-filtra `pool_slot` dos slots non-travados — slot
    travado bypassa (decisão deliberada do user supera regra automática,
    igual 4.D). Em /regerar, adapter calcula este set a partir dos ex já
    nos outros treinos da rotina. Default None = sem filtro extra (preserva
    4.D byte-a-byte). Quando o caller quer "relaxar família se
    necessário", `gerar_rotina_csp` faz 2 chamadas: 1ª com este set, 2ª
    sem caso 1ª seja inviável (caller marca os relaxados).

    `cargas_config` + `peso_cargas_off` (Fatia 4.E cargas, 2026-05-24): H-cargas
    par-a-par dentro do bloco. `cargas_config` é dict `{"grip", "lombar",
    "core"} → threshold int`. Pra cada par (a,b) NO MESMO BLOCO e cada dim d
    com `thr[d] > 0`: bloqueia se `carga_d(a) >= 1 AND carga_d(b) >= 1 AND
    carga_d(a) + carga_d(b) >= thr[d]`. Réplica fiel do antigo
    (`gerador_treino._bloqueio_cargas`), não é cumulativa por bloco.

    **Graceful degradation por bloco**: BoolVar `cargas_off_b[b]` por bloco
    (default False) é forçada a True quando o solver não consegue evitar par
    violador dentro do bloco. Objetivo: `peso_cargas_off * sum(cargas_off_b)`
    (default peso=1000) — solver só desliga quando inviável. Caller decodifica
    `cargas_off_por_bloco` por treino e gera avisos `relaxado_carga` analíticos
    pós-solve (mirror de `gerador_treino:1469-1516`).

    **Travados ENTRAM nos pares** (divergência intencional do antigo).
    Travado tem `pool_slot=[ex]` (Fatia 4.D), então par travado+non-travado
    violador força non-travado a mudar — "travado nunca some" preservado
    naturalmente sem precisar de bypass extra.

    `cargas_config=None` ou `{}` ou todas dims em 0 = constraint inteira
    pulada (preserva 4.D byte-a-byte). `peso_cargas_off` é parametrizável
    pra harness de calibração — manter alto pra garantir prioridade do
    filtro sobre softs equivalentes.

    `travados_por_treino` (Fatia 4.D, 2026-05-24): dict `{t_idx: [Exercicio]}`
    de exercícios fixados pelo personal. Decisão clínica: travado é
    deliberação do user e supera regras automáticas. Cada travado tenta
    consumir uma vaga da PRIMEIRA demanda do treino cujo escopo cobre o
    padrão do travado (mesma lógica do motor antigo); sem demanda
    compatível, vira demanda virtual extra `("padrao", ex.padrao, 1)` —
    treino sai com N+1 exercícios. Slot do travado tem pool de 1
    elemento (o próprio travado), participa de TODAS as constraints
    soft (S-T1, S-B1, S-B4, Aderência) e das hard intra-treino (H-T1/T2/T3
    aplicam se relevante; H-T4 bypassa pra slots travados pois travado
    supera regra "vaga única ≠ Acessório"). Travados bypassam:
    H-P1 (complexidade do nível), AllDifferent global cross-treino entre
    travados (mesmo travado pode aparecer em treinos diferentes — análogo
    ao antigo). Nomes travados são REMOVIDOS dos pools dos slots
    non-travados, garantindo unicidade sem conflito.

    Devolve dict com:
      - model: CpModel sem objetivo definido
      - assign: dict[(sid, cidx)] -> BoolVar
      - slots_globais, treinos, grupo_por_idx: metadados pra decodificação
      - h_r1_aplicadas: lista de aplicações H-R1 com flag degraded
      - h_a1_aplicadas: lista de aplicações H-A1 (âncoras obrigatórias por
        subregião). Cada entrada `{subregiao, padrao_obrigatorio, n_termos,
        n_slots, degraded, motivo?}`. `degraded=True` quando constraint foi
        pulada (pool vazio pós-H-P1) ou aplicada via constraint colaborativa
        de conflito de cardinalidade (`vagas < n_obrig_efetivo`).
      - h_a0_aplicadas: lista de aplicações H-A0 (âncoras obrigatórias por
        região, per-treino). Cada entrada `{treino, regiao,
        subregiao_obrigatoria, n_slots, degraded, motivo?}`. Mesmo padrão de
        degraded da H-A1 (pool vazio | conflito de cardinalidade).
      - penalidades: list[IntVar] de S-T1 + Aderência (quando peso > 0)
        + S-B1 (quando peso_evitar_agonistas > 0).
        Caller decide se vira `Minimize(sum(penalidades))` (legacy + Phase 1)
        ou IntVar de soma + bound `<= optimal + slack` (Phase 2).
    """
    # H-P1: filtra o pool global por complexidade ANTES de montar o modelo.
    banco_nivel = filtrar_pool_por_nivel(banco, nivel_aluno)

    model = cp_model.CpModel()

    # ── Fatia 4.D: pré-processamento de travados ────────────────────────────
    # Pra cada travado, identifica primeira demanda compatível (cujo escopo
    # cobre `ex.padrao`); sem compatível, cria demanda virtual extra.
    # Resultado: `demandas_finais_por_treino` (originais + virtuais) +
    # `travados_por_slot_meta` que mapeia (t_idx, di, pos) -> Exercicio
    # pra reservar o slot daquele travado.
    travados_por_treino = travados_por_treino or {}
    nomes_travados: set[str] = set()
    for travs in travados_por_treino.values():
        for ex in travs:
            nomes_travados.add(ex.nome)

    # Fatia 4.E: famílias proibidas pré-filtram pools dos slots non-travados.
    # Slot travado bypassa (igual 4.D — decisão do user supera regra).
    fams_proibidas: set[str] = set(familias_proibidas or [])

    demandas_finais_por_treino: list[list[tuple[str, str, int]]] = []
    travados_por_slot_meta: dict[tuple[int, int, int], Exercicio] = {}
    for t_idx, demandas_orig in enumerate(demandas_por_treino):
        travados_t = list(travados_por_treino.get(t_idx, []))
        demandas_t = list(demandas_orig)
        reservados: dict[int, int] = defaultdict(int)
        for ex in travados_t:
            encaixou = False
            for di, (nv, esc, qt) in enumerate(demandas_t):
                # Só considera demandas originais (não as virtuais que já adicionamos)
                if di >= len(demandas_orig):
                    continue
                if reservados[di] >= qt:
                    continue
                padroes_cobertos = set(_padroes_de_escopo(nv, esc))
                if ex.padrao in padroes_cobertos:
                    pos = reservados[di]
                    travados_por_slot_meta[(t_idx, di, pos)] = ex
                    reservados[di] += 1
                    encaixou = True
                    break
            if not encaixou:
                # Demanda virtual extra (nivel padrao, qtd 1)
                di_extra = len(demandas_t)
                demandas_t.append(("padrao", ex.padrao, 1))
                travados_por_slot_meta[(t_idx, di_extra, 0)] = ex
        demandas_finais_por_treino.append(demandas_t)

    # ── Monta treinos → grupos → slots (sid_global único cross-treino) ──────
    # Pool POR SLOT (Fatia 4.D): slot travado tem pool de 1 elemento (o
    # próprio travado); slot non-travado tem pool default da demanda menos
    # nomes que estão travados em qualquer treino (evita conflito de
    # unicidade entre slot travado e slot non-travado com mesma opção).
    treinos: list[list[dict]] = []
    slots_globais: list[dict] = []
    for t_idx, demandas in enumerate(demandas_finais_por_treino):
        grupos_t: list[dict] = []
        for di, (nivel, escopo, qtd) in enumerate(demandas):
            pool_default = _pool_da_demanda(banco_nivel, nivel, escopo)
            # Filtra nomes travados do pool default (slot non-travado nunca
            # repete um nome que está travado em algum slot da rotina).
            # Fatia 4.E: também filtra famílias proibidas (cross-treino hard
            # quando set não-vazio). `_familia_cross` cobre pai+filho.
            # H-A0 (decisão 4.3 / 5.1): filtro upstream de subregiões não-âncora
            # quando demanda nível região com âncoras declaradas. Ex:
            # `("regiao","upper",3)` rejeita `bracos` do pool (não está em
            # ANCORAS_POR_REGIAO[upper]). Slot só pode escolher subregião
            # âncora — branching menor, modelo mais limpo (replica H-P1 que
            # filtra pool antes do solver).
            subs_ancora_h_a0: set[str] = set()
            if nivel == "regiao" and escopo in ANCORAS_POR_REGIAO:
                subs_ancora_h_a0 = {
                    a["subregiao"] for a in ANCORAS_POR_REGIAO[escopo]
                }
            pool_default_sem_travados = [
                e for e in pool_default
                if e.nome not in nomes_travados
                and _familia_cross(e) not in fams_proibidas
                and (not subs_ancora_h_a0 or e.subregiao in subs_ancora_h_a0)
            ]
            g = {
                "t_idx": t_idx, "di": di,
                "demanda": (nivel, escopo, qtd),
                "pool": pool_default,  # default original, usado por H-T4 (não dispara em travados)
                "slot_ids": [],
            }
            grupos_t.append(g)
            for pos in range(qtd):
                sid = len(slots_globais)
                ex_travado = travados_por_slot_meta.get((t_idx, di, pos))
                if ex_travado is not None:
                    pool_slot = [ex_travado]
                else:
                    pool_slot = pool_default_sem_travados
                slots_globais.append({
                    "sid": sid, "t_idx": t_idx, "di": di,
                    "pool_slot": pool_slot,
                    "travado": ex_travado is not None,
                })
                g["slot_ids"].append(sid)
        treinos.append(grupos_t)

    # Lookup grupo por (t_idx, di) pra uso nas constraints.
    grupo_por_idx: dict[tuple[int, int], dict] = {
        (g["t_idx"], g["di"]): g for grupos_t in treinos for g in grupos_t
    }
    # Lookup slot por sid pra uso nas constraints (pool_slot, travado flag).
    slot_por_sid: dict[int, dict] = {s["sid"]: s for s in slots_globais}

    # ── Fatia 4.A: variáveis estruturais de bloco por treino ────────────────
    # X[(t, sid, b)] BoolVar = "slot sid está no bloco b do treino t".
    # bloco_idx[sid] IntVar = bloco do slot (derivado de X via soma ponderada).
    # max_blocos_t = n_slots_t (limite trivial: cada slot pode virar solo).
    slot_to_bloco_vars: dict[int, dict[int, cp_model.IntVar]] = {}
    bloco_idx: dict[int, cp_model.IntVar] = {}
    slots_por_treino: dict[int, list[int]] = defaultdict(list)
    for s in slots_globais:
        slots_por_treino[s["t_idx"]].append(s["sid"])

    for t_idx, sids_t in slots_por_treino.items():
        max_b = len(sids_t)  # bloco solo sempre permitido
        for sid in sids_t:
            vars_b = {}
            for b in range(max_b):
                v = model.NewBoolVar(f"x_t{t_idx}_s{sid}_b{b}")
                vars_b[b] = v
            slot_to_bloco_vars[sid] = vars_b
            model.AddExactlyOne(vars_b.values())
            # bloco_idx[sid] = sum(b * X[sid, b])
            bidx = model.NewIntVar(0, max_b - 1, f"bidx_t{t_idx}_s{sid}")
            model.Add(bidx == sum(b * vars_b[b] for b in range(max_b)))
            bloco_idx[sid] = bidx

        # Constraint de tamanho: por bloco b do treino, soma dos X <= TAMANHO_MAX_BLOCO.
        for b in range(max_b):
            model.Add(
                sum(slot_to_bloco_vars[sid][b] for sid in sids_t) <= TAMANHO_MAX_BLOCO
            )

    # ── assign[(sid, cidx)] + AddExactlyOne por slot ────────────────────────
    # Fatia 4.D: pool agora é por-slot (s["pool_slot"]) — travado tem pool
    # de 1 (só ele); non-travado tem pool default da demanda menos nomes
    # travados em qualquer slot da rotina.
    assign: dict[tuple[int, int], cp_model.IntVar] = {}
    for s in slots_globais:
        pool = s["pool_slot"]
        bvars = []
        for cidx in range(len(pool)):
            b = model.NewBoolVar(f"a_t{s['t_idx']}_s{s['sid']}_c{cidx}")
            assign[(s["sid"], cidx)] = b
            bvars.append(b)
        if bvars:
            model.AddExactlyOne(bvars)
        else:
            # Pool vazio (filtro extremo — ex: familias_proibidas da 4.E
            # esvaziou o pool e não há travado pra este slot). Força
            # inviabilidade trivial — gerar_rotina_csp lida com retry
            # via `relaxar_familia` se aplicável.
            model.AddBoolOr([])

    # ── AllDifferent global (por nome do exercício) — cross-treino.
    # Mantém comportamento do gerador antigo (nomes_exatos_globais).
    # Fatia 4.D: slots travados BYPASSAM AllDifferent — mesmo travado pode
    # aparecer em treinos diferentes. Garantido sem conflito porque nomes
    # travados já foram removidos dos pools dos slots non-travados.
    por_nome: dict[str, list] = defaultdict(list)
    for s in slots_globais:
        if s["travado"]:
            continue
        pool = s["pool_slot"]
        for cidx, ex in enumerate(pool):
            por_nome[ex.nome].append(assign[(s["sid"], cidx)])
    for vars_do_nome in por_nome.values():
        if len(vars_do_nome) > 1:
            model.AddAtMostOne(vars_do_nome)

    # ── Fatia 4.B: grupo_func[s] IntVar derivado do ex escolhido ────────────
    # grupo_func[s] = sum_c (assign[s,c] * GRUPO_CODE[pool[c].padrao]).
    # AddExactlyOne já força sum(assign[s,c])=1, então grupo_func[s] = code
    # do grupo do ex escolhido. Usado em S-B1 pra detectar pares agonistas.
    # Criado SEMPRE (mesmo com peso_evitar_agonistas=0) porque é leve e
    # serve de gancho pra futuras constraints; CP-SAT simplifica IntVars
    # não referenciadas no objetivo.
    max_grupo_code = max(GRUPO_FUNC_CODE.values())
    grupo_func: dict[int, cp_model.IntVar] = {}
    for s in slots_globais:
        pool = s["pool_slot"]
        codes = [_grupo_code_do_ex(ex) for ex in pool]
        lo, hi = (min(codes), max(codes)) if codes else (0, 0)
        gf = model.NewIntVar(lo, hi, f"grupo_t{s['t_idx']}_s{s['sid']}")
        model.Add(gf == sum(assign[(s["sid"], c)] * codes[c] for c in range(len(pool))))
        grupo_func[s["sid"]] = gf

    # ── S-B5 (2026-05-26): regiao_idx[s] IntVar derivado do ex escolhido ────
    # Mesmo pattern do grupo_func: regiao_idx[s] = sum_c (assign[s,c] *
    # REGIAO_CODE[pool[c].regiao]). Usado em S-B5 pra detectar pares
    # same-region. Criado SEMPRE (leve, gancho pra futuras constraints).
    regiao_idx: dict[int, cp_model.IntVar] = {}
    for s in slots_globais:
        pool = s["pool_slot"]
        codes = [_regiao_code_do_ex(ex) for ex in pool]
        lo, hi = (min(codes), max(codes)) if codes else (0, 0)
        ri = model.NewIntVar(lo, hi, f"regiao_t{s['t_idx']}_s{s['sid']}")
        model.Add(ri == sum(assign[(s["sid"], c)] * codes[c] for c in range(len(pool))))
        regiao_idx[s["sid"]] = ri

    # ── S-R1 (2026-05-27): subregiao_idx[s] IntVar derivado do ex escolhido ──
    # Espelho exato do regiao_idx pra granularidade de subregião. Usado em
    # S-R1 cross-treino pra contar slots de cada subregião em cada treino
    # (achado 1 da auditoria 2026-05-26 — faceta de simetria T1↔T2).
    # Criado SEMPRE (leve, gancho pra futuras constraints).
    subregiao_idx: dict[int, cp_model.IntVar] = {}
    for s in slots_globais:
        pool = s["pool_slot"]
        codes = [_subregiao_code_do_ex(ex) for ex in pool]
        lo, hi = (min(codes), max(codes)) if codes else (0, 0)
        si = model.NewIntVar(lo, hi, f"subreg_t{s['t_idx']}_s{s['sid']}")
        model.Add(si == sum(assign[(s["sid"], c)] * codes[c] for c in range(len(pool))))
        subregiao_idx[s["sid"]] = si

    # ── H-T1 / H-T2 / H-T3 (HARD intra-treino): aplicam por t_idx ──────────
    for t_idx, grupos_t in enumerate(treinos):
        slots_do_treino = [s for s in slots_globais if s["t_idx"] == t_idx]

        # H-T1: mesma família refinada (variacao_de) — predicado clássico
        # `cand.variacao_de == outro.variacao_de` ambos não-vazios.
        por_familia: dict[str, list] = defaultdict(list)
        for s in slots_do_treino:
            pool = s["pool_slot"]
            for cidx, ex in enumerate(pool):
                if ex.variacao_de:
                    por_familia[ex.variacao_de].append(assign[(s["sid"], cidx)])
        for vars_da_familia in por_familia.values():
            if len(vars_da_familia) > 1:
                model.AddAtMostOne(vars_da_familia)

        # H-T2: variante_pontual cross-família same-subregião.
        vp_por_subregiao: dict[str, list] = defaultdict(list)
        for s in slots_do_treino:
            pool = s["pool_slot"]
            for cidx, ex in enumerate(pool):
                if ex.variante_pontual:
                    vp_por_subregiao[ex.subregiao].append(
                        (assign[(s["sid"], cidx)], ex.variacao_de)
                    )
        for lista in vp_por_subregiao.values():
            for i in range(len(lista)):
                var_a, fam_a = lista[i]
                for j in range(i + 1, len(lista)):
                    var_b, fam_b = lista[j]
                    if fam_a != fam_b:
                        model.AddAtMostOne([var_a, var_b])

        # H-T3: lateralidade contextual (costas).
        uni_por_subregiao: dict[str, list] = defaultdict(list)
        for s in slots_do_treino:
            pool = s["pool_slot"]
            for cidx, ex in enumerate(pool):
                if (
                    ex.unilateral == "unilateral"
                    and ex.subregiao in SUBREGIOES_LATERALIDADE_HARD
                ):
                    uni_por_subregiao[ex.subregiao].append(assign[(s["sid"], cidx)])
        for vars_uni in uni_por_subregiao.values():
            if len(vars_uni) > 1:
                model.AddAtMostOne(vars_uni)

    # ── tier_rank por slot (IntVar = soma assign × rank) — usado por S-T1 ───
    tier_rank: dict[int, cp_model.IntVar] = {}
    for s in slots_globais:
        pool = s["pool_slot"]
        ranks = [_tier_rank(ex) for ex in pool]
        lo, hi = (min(ranks), max(ranks)) if ranks else (0, 0)
        tr = model.NewIntVar(lo, hi, f"tier_t{s['t_idx']}_s{s['sid']}")
        model.Add(tr == sum(assign[(s["sid"], c)] * ranks[c] for c in range(len(pool))))
        tier_rank[s["sid"]] = tr

    # ── H-T4 (HARD, graceful degradation): por grupo, scoped ao treino ──────
    # Fatia 4.D: travado supera H-T4 — slots travados não recebem a
    # constraint (decisão deliberada do user > regra automática).
    for grupos_t in treinos:
        for g in grupos_t:
            nivel, escopo, qtd = g["demanda"]
            if nivel == "subregiao" and qtd == 1:
                sid = g["slot_ids"][0]
                if slot_por_sid[sid]["travado"]:
                    g["h_t4_aplicado_efetivamente"] = False
                    continue
                tem_nao_acessorio = any(ex.tier != TIER_ACESSORIO for ex in g["pool"])
                if tem_nao_acessorio:
                    for cidx, ex in enumerate(g["pool"]):
                        if ex.tier == TIER_ACESSORIO:
                            model.Add(assign[(sid, cidx)] == 0)
                g["h_t4_aplicado_efetivamente"] = tem_nao_acessorio

    # ── H-R1 (HARD cross-treino): cobertura de eixos via compostos ──────────
    # Conta slots por subregião na ROTINA INTEIRA (via demandas DETERMINÍSTICAS:
    # nivel=subregiao OU padrao→subregião 1:1). Se ≥ min_slots, exige cobertura
    # por eixo: soma das vars assign sobre candidatos que satisfazem o
    # predicado do eixo, sobre TODOS os slots da rotina cujo grupo declara
    # essa subregião, deve ser ≥ 1.
    slots_por_subregiao_rotina: dict[str, list[int]] = defaultdict(list)
    for grupos_t in treinos:
        for g in grupos_t:
            nivel, escopo, qtd = g["demanda"]
            subs_demanda = _subregioes_da_demanda(nivel, escopo)
            if len(subs_demanda) == 1:
                (sub,) = subs_demanda
                slots_por_subregiao_rotina[sub].extend(g["slot_ids"])

    # Decisão fechada (Bernardo, 2026-05-23): graceful degradation quando
    # pool não tem candidato pra um eixo (caso real: nível 1 iniciante +
    # perna_anterior, sem unilateral composto disponível). Eixo é pulado
    # e marcado `degraded=True` — UI deve sinalizar ao usuário.
    h_r1_aplicadas: list[dict] = []
    for sub, regra in H_R1_REGRAS.items():
        sids_da_sub = slots_por_subregiao_rotina.get(sub, [])
        if len(sids_da_sub) < regra["min_slots"]:
            continue
        for label, predicado in regra["eixos"]:
            termos = []
            for sid in sids_da_sub:
                slot_info = slot_por_sid[sid]
                pool = slot_info["pool_slot"]
                for cidx, ex in enumerate(pool):
                    if predicado(ex):
                        termos.append(assign[(sid, cidx)])
            if termos:
                model.Add(sum(termos) >= 1)
                h_r1_aplicadas.append({
                    "subregiao": sub, "eixo": label,
                    "n_termos": len(termos),
                    "n_slots": len(sids_da_sub),
                    "degraded": False,
                })
            else:
                h_r1_aplicadas.append({
                    "subregiao": sub, "eixo": label,
                    "n_termos": 0,
                    "n_slots": len(sids_da_sub),
                    "degraded": True,
                    "motivo": "pool sem candidato (provavelmente filtrado por H-P1)",
                })

    # ── H-A0 (HARD per-treino): âncoras obrigatórias por REGIÃO ─────────────
    # Para cada demanda `("regiao", R, qtd)` com R em ANCORAS_POR_REGIAO,
    # agregar PER-TREINO (não cross-treino — decisão 4.1 do handoff): para
    # cada subregião com `obrigatoria=True`, exigir ≥1 slot daquele treino
    # com `ex.subregiao == sub_obrig`. Subregiões não declaradas em
    # ANCORAS_POR_REGIAO[R] já foram BANIDAS upstream do pool_slot (decisão
    # 4.3 / Caminho A / pendente 5.1).
    #
    # Variável CSP nova: `sub_idx[s]` IntVar canalizado por assign via soma
    # ponderada (mesma técnica de `grupo_func` e `tier_rank`). Indexação
    # estável: `subs_ancora_por_regiao[R] = list[str]` ordenado igual à
    # tabela curada em ANCORAS_POR_REGIAO; sub_id = idx nessa lista.
    #
    # Decisões fechadas (handoff 2026-05-25, Seção 4):
    # - 4.1 Agregação PER-TREINO (não cross-treino) — semântica de "treino
    #   de upper" cobre upper NAQUELE treino, não na rotina inteira.
    # - 4.2 Interação H-A0 × H-A1: marker via estrutura paralela
    #   `subregioes_obrigadas_ha0[(t_idx, R)] = set(subs_ativas)` lida pelo
    #   bloco H-A1 abaixo (decisão pendente 5.2 / Caminho A: reordenar).
    # - 4.3 Rejeição de subs não-âncora HARD (Caminho A) — já feito upstream
    #   no filtro de `pool_default_sem_travados`.
    # - 4.4 Reuso `ANCORAS_POR_REGIAO` do gerador_treino (não duplicar).
    # - 4.6 NÃO modelar `PROPORCAO_COMPOSTOS = 0.6` aqui — cobertura de
    #   compostos vem via H-A1[X] que ativa por marker.
    # - 4.8 Sufixo 0 = "âncora mais primitiva" (decide subregião antes de
    #   H-A1 decidir padrão dentro da subregião).
    #
    # Graceful degradation análoga à H-A1:
    # - Pool sem candidato: alguma sub obrigatória sem nenhum cand no pool
    #   dos slots daquele (treino, região) → constraint daquela sub pulada,
    #   marcada `degraded=True` no resultado.
    # - Conflito de cardinalidade (vagas < n_obrig efetivas): constraint
    #   colaborativa `sum(obrig_usada) >= vagas` força N distintas. Caso
    #   `("regiao","upper",1)` com 3 obrigatórias → 1 das 3 entra; solver
    #   decide qual (sem favorecer).
    h_a0_aplicadas: list[dict] = []
    subregioes_obrigadas_ha0: dict[tuple[int, str], set[str]] = {}
    slots_demanda_regiao_por_treino: dict[tuple[int, str], list[int]] = (
        defaultdict(list)
    )
    subs_ancora_por_regiao: dict[str, list[str]] = {}
    sub_idx: dict[int, cp_model.IntVar] = {}

    for grupos_t in treinos:
        for g in grupos_t:
            nivel, escopo, _qtd = g["demanda"]
            if nivel != "regiao" or escopo not in ANCORAS_POR_REGIAO:
                continue
            subs_ancora = [a["subregiao"] for a in ANCORAS_POR_REGIAO[escopo]]
            subs_ancora_por_regiao[escopo] = subs_ancora
            for sid in g["slot_ids"]:
                slots_demanda_regiao_por_treino[(g["t_idx"], escopo)].append(sid)
                pool = slot_por_sid[sid]["pool_slot"]
                if not pool:
                    # Pool vazio (degenerado). sub_idx pode ser 0 fixo —
                    # AddBoolOr([]) já força inviabilidade trivial.
                    continue
                # Canalização via soma ponderada: sub_idx[s] = sum(assign * sub_id).
                # AddExactlyOne já força sum(assign[s,c]) = 1, então
                # sub_idx[s] == subs_ancora.index(ex_escolhido.subregiao).
                lo, hi = 0, len(subs_ancora) - 1
                si = model.NewIntVar(
                    lo, hi, f"sub_idx_t{g['t_idx']}_s{sid}",
                )
                model.Add(si == sum(
                    assign[(sid, c)] * subs_ancora.index(ex.subregiao)
                    for c, ex in enumerate(pool)
                ))
                sub_idx[sid] = si

    for (t_idx, R), sids in slots_demanda_regiao_por_treino.items():
        if not sids:
            continue
        subs_ancora = subs_ancora_por_regiao[R]
        obrigatorias = [
            a["subregiao"] for a in ANCORAS_POR_REGIAO[R] if a.get("obrigatoria")
        ]
        if not obrigatorias:
            continue

        # Detecta degraded-por-pool: sub obrigatória sem nenhum candidato no
        # pool dos slots dessa (treino, região).
        ativas: list[str] = []
        degradadas_pool: list[str] = []
        for sub in obrigatorias:
            tem_candidato = any(
                ex.subregiao == sub
                for sid in sids
                for ex in slot_por_sid[sid]["pool_slot"]
            )
            (ativas if tem_candidato else degradadas_pool).append(sub)

        for sub in degradadas_pool:
            h_a0_aplicadas.append({
                "treino": t_idx, "regiao": R, "subregiao_obrigatoria": sub,
                "n_slots": len(sids), "degraded": True,
                "motivo": "pool sem candidato (provavelmente filtrado por H-P1)",
            })

        if not ativas:
            continue

        vagas = len(sids)
        n_ativas = len(ativas)

        # Estrutura paralela pra H-A1 ler (decisão 4.2 / 5.2 / Caminho A).
        # SÓ popular no caso NORMAL (vagas >= n_ativas) — onde cada sub
        # ativa é GARANTIDA individualmente pela constraint hard.
        # No caso CONFLITO (vagas < n_ativas), só vagas-distintas coletivas
        # são garantidas — não há sub específica garantida → H-A1 marker
        # não pode forçar padrão obrigatório de cada uma (solver poderia
        # não escolher essa sub). Marker fica vazio nesse caso e a
        # cobertura de subregião é o que H-A0 ainda fornece.
        if vagas >= n_ativas:
            subregioes_obrigadas_ha0[(t_idx, R)] = set(ativas)
        else:
            subregioes_obrigadas_ha0[(t_idx, R)] = set()

        if vagas >= n_ativas:
            # Caso normal: 1 constraint por sub obrigatória ativa.
            for sub in ativas:
                sub_id_local = subs_ancora.index(sub)
                bools = []
                for sid in sids:
                    b = model.NewBoolVar(f"ha0_{R}_{sub}_t{t_idx}_s{sid}")
                    model.Add(sub_idx[sid] == sub_id_local).OnlyEnforceIf(b)
                    model.Add(sub_idx[sid] != sub_id_local).OnlyEnforceIf(b.Not())
                    bools.append(b)
                model.Add(sum(bools) >= 1)
                h_a0_aplicadas.append({
                    "treino": t_idx, "regiao": R, "subregiao_obrigatoria": sub,
                    "n_slots": vagas, "degraded": False,
                })
        else:
            # Conflito de cardinalidade (vagas < n_obrig efetivas):
            # constraint colaborativa "vagas subs obrigatórias DISTINTAS
            # devem aparecer". Cria BoolVar `obrig_usada_X` reificada com
            # `sum(slots_X) >= 1`; soma >= vagas força N obrig distintas.
            obrig_usadas_vars = []
            for sub in ativas:
                sub_id_local = subs_ancora.index(sub)
                usada = model.NewBoolVar(f"ha0_usada_{R}_{sub}_t{t_idx}")
                bools_sub = []
                for sid in sids:
                    b = model.NewBoolVar(f"ha0_{R}_{sub}_t{t_idx}_s{sid}")
                    model.Add(sub_idx[sid] == sub_id_local).OnlyEnforceIf(b)
                    model.Add(sub_idx[sid] != sub_id_local).OnlyEnforceIf(b.Not())
                    bools_sub.append(b)
                model.Add(sum(bools_sub) >= 1).OnlyEnforceIf(usada)
                model.Add(sum(bools_sub) == 0).OnlyEnforceIf(usada.Not())
                obrig_usadas_vars.append(usada)
            model.Add(sum(obrig_usadas_vars) >= vagas)
            motivo_conflito = (
                f"conflito_cardinalidade vagas={vagas}<n_obrig_efetivo={n_ativas}"
            )
            for sub in ativas:
                h_a0_aplicadas.append({
                    "treino": t_idx, "regiao": R, "subregiao_obrigatoria": sub,
                    "n_slots": vagas, "degraded": True,
                    "motivo": motivo_conflito,
                })

    # ── H-A1 (HARD cross-treino): âncoras obrigatórias por subregião ────────
    # Para cada demanda EXPLÍCITA `("subregiao", X, qtd)` com qtd >= 1 e X em
    # ANCORAS_POR_SUBREGIAO, pra cada âncora com `obrigatoria=True`, exigir
    # ≥1 slot da rotina (cross-treino) com `padrao == âncora.padrao`.
    #
    # Decisões fechadas (handoff 2026-05-25):
    # - NÃO ativa em demanda nível padrão (usuário pediu o padrão; respeitar).
    # - NÃO ativa em demanda nível regiao DIRETAMENTE — mas ATIVA via marker
    #   da estrutura paralela `subregioes_obrigadas_ha0` (decisão 4.2): pra
    #   cada (t_idx, R) com sub obrig ativa, agrega os slot_ids da demanda
    #   região como se fossem demanda subregião. Combinado com H-A0 (que
    #   força ≥1 slot com sub_idx==X), o slot que cumpre H-A1 (padrão
    #   âncora de X) também cumpre H-A0 (subregião X) — interseção viável
    #   porque PADRAO_PARA_SUBREGIAO é 1:1 pros padrões âncora obrigatórios
    #   das subregiões de upper/lower.
    # - Cross-treino: vagas = total de slots da subregião X em TODAS as
    #   demandas explícitas da rotina (independente do treino).
    # - Conflito cardinalidade (vagas < n_obrigatorias com pool viável):
    #   constraint colaborativa `sum(obrig_usada) >= vagas` força N obrigatórias
    #   DISTINTAS a aparecer; solver decide quais. Replica o `random.sample`
    #   do antigo (`calcular_quotas` quando vagas < n_obrig) declarativamente.
    # - Graceful degradation por pool vazio (espelha H-R1): se nenhum candidato
    #   da âncora obrigatória sobrar pós-H-P1, constraint daquela âncora é
    #   pulada e marcada `degraded=True` no resultado.
    h_a1_aplicadas: list[dict] = []
    slots_subregiao_explicita: dict[str, list[int]] = defaultdict(list)
    # `vagas_por_sub` separa contagem de vagas GARANTIDAS por sub da
    # contagem `len(slots_subregiao_explicita[sub])`. Necessário pra H-A0
    # marker: cada (t_idx, R) adiciona TODOS os sids da demanda região à
    # lista (porque sub_idx[sid] decide quem vira X em runtime), mas só
    # 1 desses sids está GARANTIDO para a sub X. Detecção de conflito de
    # cardinalidade (vagas < n_ativas) deve usar vagas garantidas reais —
    # do contrário, demandas `("regiao","upper",3)` quebram em costas
    # (vagas=1 garantida ≥1 marker; mas n_ativas=2 = remadas+puxadas).
    vagas_garantidas_por_sub: dict[str, int] = defaultdict(int)
    for grupos_t in treinos:
        for g in grupos_t:
            nivel, escopo, qtd = g["demanda"]
            if nivel == "subregiao" and escopo in ANCORAS_POR_SUBREGIAO:
                slots_subregiao_explicita[escopo].extend(g["slot_ids"])
                vagas_garantidas_por_sub[escopo] += qtd

    # Estende com os slots da demanda região cujas subregiões estão
    # obrigadas por H-A0 (decisão 4.2 / 5.2 / Caminho A — reordenar).
    # Marker contribui +1 vaga garantida por (t_idx, R, sub_obrig) — H-A0
    # garante ≥1 slot daquela sub naquele treino.
    for (t_idx, R), subs_obrig in subregioes_obrigadas_ha0.items():
        sids_demanda_regiao = slots_demanda_regiao_por_treino.get((t_idx, R), [])
        for sub in subs_obrig:
            if sub in ANCORAS_POR_SUBREGIAO:
                slots_subregiao_explicita[sub].extend(sids_demanda_regiao)
                vagas_garantidas_por_sub[sub] += 1

    for sub, sids in slots_subregiao_explicita.items():
        if not sids:
            continue
        obrigatorias = [
            a for a in ANCORAS_POR_SUBREGIAO[sub] if a.get("obrigatoria")
        ]
        if not obrigatorias:
            continue

        # Coleta termos por âncora obrigatória (cross-treino).
        termos_por_obrig: list[tuple[str, list]] = []
        for ancora in obrigatorias:
            pad = ancora["padrao"]
            termos = []
            for sid in sids:
                pool = slot_por_sid[sid]["pool_slot"]
                for cidx, ex in enumerate(pool):
                    if ex.padrao == pad:
                        termos.append(assign[(sid, cidx)])
            termos_por_obrig.append((pad, termos))

        ativas = [(p, t) for p, t in termos_por_obrig if t]
        degradadas_pool = [p for p, t in termos_por_obrig if not t]

        # Avisos de degraded-por-pool (constraint daquela âncora é pulada).
        for pad in degradadas_pool:
            h_a1_aplicadas.append({
                "subregiao": sub, "padrao_obrigatorio": pad,
                "n_termos": 0, "n_slots": len(sids),
                "degraded": True,
                "motivo": "pool sem candidato (provavelmente filtrado por H-P1)",
            })

        if not ativas:
            continue

        # Vagas garantidas = demandas subregião explícitas (qtd) + +1 por
        # marker H-A0 (cada (t_idx, R) garante ≥1 slot da sub naquele treino).
        # NÃO usa `len(sids)` porque marker adiciona TODOS os sids da
        # demanda região (heterogêneos), mas só 1 deles vira de fato a sub.
        vagas = vagas_garantidas_por_sub.get(sub, len(sids))
        n_ativas = len(ativas)

        if vagas >= n_ativas:
            # Caso normal: 1 constraint por âncora obrigatória ativa.
            for pad, termos in ativas:
                model.Add(sum(termos) >= 1)
                h_a1_aplicadas.append({
                    "subregiao": sub, "padrao_obrigatorio": pad,
                    "n_termos": len(termos), "n_slots": vagas,
                    "degraded": False,
                })
        else:
            # Conflito de cardinalidade (vagas < n_obrig efetivas):
            # constraint colaborativa "vagas obrigatórias DISTINTAS devem
            # aparecer". Cria BoolVar `obrig_usada_X` reificada com
            # `sum(termos_X) >= 1`; soma >= vagas força N obrig distintas.
            obrig_usadas_vars = []
            for pad, termos in ativas:
                usada = model.NewBoolVar(f"ha1_usada_{sub}_{pad}")
                model.Add(sum(termos) >= 1).OnlyEnforceIf(usada)
                model.Add(sum(termos) == 0).OnlyEnforceIf(usada.Not())
                obrig_usadas_vars.append(usada)
            model.Add(sum(obrig_usadas_vars) >= vagas)
            motivo_conflito = (
                f"conflito_cardinalidade vagas={vagas}<n_obrig_efetivo={n_ativas}"
            )
            for pad, termos in ativas:
                h_a1_aplicadas.append({
                    "subregiao": sub, "padrao_obrigatorio": pad,
                    "n_termos": len(termos), "n_slots": vagas,
                    "degraded": True,
                    "motivo": motivo_conflito,
                })

    # ── Lista compartilhada de penalidades do objetivo ──────────────────────
    # Inicializada antes do bloco S-A1 (que pode adicionar termos) e
    # consumida pelas seções S-T1/S-B1/S-B4/Aderência/cargas abaixo.
    penalidades = []

    # ── S-A1 (SOFT): distribuição entre âncoras NÃO-obrigatórias ────────────
    # Consome o `peso` curado em ANCORAS_POR_SUBREGIAO (3/2/1) que H-A0/H-A1
    # ignoram. Resolve regressão CSP vs antigo: `ombro(2)` saía 100% (composto +
    # posterior_ombro) — ZERO `ombro_isolado` (vs antigo 100% composto + isolado);
    # `perna_posterior(2)` saía 100% (hinge + abduction) — ZERO `knee_flexion`.
    #
    # Forma (decisão 5.1 do handoff S-A1, linear):
    #   pen = (peso_max_nao_obrig(sub) - peso_da_ancora(padrão)) * peso_sa1
    # Aplicado por SLOT × CANDIDATO. `assign[(sid, cidx)] == 0` anula custo;
    # solver minimiza → vaga sobrando prefere padrão de peso alto.
    #
    # Ativação (decisões 4.1 + 5.2 do handoff S-A1):
    #  - Caso 1 (demanda subregião EXPLÍCITA): condicionado a `qtd > n_obrig`
    #    pra isolar trade-off com S-B1 (Etapa 7 Fase 7.6 canibalização de pesos).
    #  - Caso 2 (demanda região via marker H-A0, decisão 5.2 / b "mais pronto"):
    #    ativa SEMPRE pros candidatos não-obrig. Efeito "vagas-livres-only" é
    #    automático: slot obrigatório tem assign=1 em obrig (cuja `padrao` não
    #    está em `nao_obrigatorias`, custo skipado); slot livre que escolhe
    #    não-obrig paga.
    #
    # peso_sa1=0 (default) skipa o bloco inteiro (preserva H-A0 byte-a-byte).
    if peso_sa1 > 0:
        sa1_dados_por_sub: dict[str, dict] = {}
        for sub_, ancoras_ in ANCORAS_POR_SUBREGIAO.items():
            nao_obrig_ = [a for a in ancoras_ if not a.get("obrigatoria")]
            if not nao_obrig_:
                continue
            sa1_dados_por_sub[sub_] = {
                "peso_max": max(a["peso"] for a in nao_obrig_),
                "peso_por_padrao": {a["padrao"]: a["peso"] for a in nao_obrig_},
                "n_obrig": sum(
                    1 for a in ancoras_ if a.get("obrigatoria")
                ),
            }

        # Caso 1: demanda subregião explícita. Sub fixa pre-solve; condicionar
        # a `qtd > n_obrig` (decisão 4.1).
        for grupos_t in treinos:
            for g in grupos_t:
                nv, esc, qt = g["demanda"]
                if nv != "subregiao" or esc not in sa1_dados_por_sub:
                    continue
                dados = sa1_dados_por_sub[esc]
                vagas_extras = qt - dados["n_obrig"]
                if vagas_extras < 1:
                    continue
                peso_max = dados["peso_max"]
                peso_por_padrao = dados["peso_por_padrao"]
                for sid in g["slot_ids"]:
                    pool = slot_por_sid[sid]["pool_slot"]
                    for cidx, ex in enumerate(pool):
                        if ex.padrao not in peso_por_padrao:
                            continue
                        custo = (peso_max - peso_por_padrao[ex.padrao]) * peso_sa1
                        if custo <= 0:
                            continue
                        sa1 = model.NewIntVar(
                            0, custo, f"sa1_sub_{esc}_{sid}_{cidx}",
                        )
                        model.Add(sa1 == custo * assign[(sid, cidx)])
                        penalidades.append(sa1)

        # Caso 2: demanda região (decisão 5.2 / b). Slot tem sub_idx variável;
        # penalty atua via assign[(sid, cidx)] — se o candidato for escolhido,
        # sua subregião e padrão são determinados, e penalty se materializa.
        for (_t_idx, _R), sids_reg in slots_demanda_regiao_por_treino.items():
            for sid in sids_reg:
                pool = slot_por_sid[sid]["pool_slot"]
                for cidx, ex in enumerate(pool):
                    dados = sa1_dados_por_sub.get(ex.subregiao)
                    if dados is None:
                        continue
                    peso = dados["peso_por_padrao"].get(ex.padrao)
                    if peso is None:
                        continue
                    custo = (dados["peso_max"] - peso) * peso_sa1
                    if custo <= 0:
                        continue
                    sa1 = model.NewIntVar(
                        0, custo, f"sa1_reg_{ex.subregiao}_{sid}_{cidx}",
                    )
                    model.Add(sa1 == custo * assign[(sid, cidx)])
                    penalidades.append(sa1)

    # ── S-A1 v2 (SOFT): penaliza padrão repetido na mesma demanda ────────────
    # Fecha o buraco arquitetural do S-A1 v1 (sondagem 2026-05-25):
    #   S-A1 v1 só penaliza não-obrigatórias de peso baixo, mas o solver
    #   pode escapar empatando com "repetir obrigatória" — `hinge+hinge`,
    #   `composto+composto`. O componente v2 penaliza padrões iguais em
    #   pares (slot_a, slot_b) da mesma demanda (subregião direta E região).
    #
    # Forma: pra cada par (s1, s2) dentro da MESMA demanda, BoolVar
    # `same_padrao` reifica "padrão escolhido em s1 == padrão escolhido
    # em s2". Penalty `peso_sa1_repet * same_padrao` no objetivo.
    #
    # Construção da BoolVar: pra cada padrão P possível no par, BoolVar
    # `eq_P[s1,s2]` = `(sum(assign[s1, c] para c com pool[c].padrao==P) == 1
    #                  AND sum(assign[s2, c] para c com pool[c].padrao==P) == 1)`.
    # `same_padrao = OR(eq_P pra todo P)`. Equivalente a "existe um padrão
    # P escolhido por ambos slots".
    #
    # Restrição de escopo: só aplica entre slots da MESMA demanda original
    # (não cross-demanda no mesmo treino). Razão: 2 slots em demandas
    # distintas (ex: `("padrao","squat",1)` + `("subregiao","perna_anterior",2)`)
    # já são intencionalmente separados pela escolha do user; repetir
    # padrão entre eles é decisão deles, não viés do solver.
    #
    # peso_sa1_repet=0 (default) skipa o bloco inteiro (preserva v1 byte-a-byte).
    if peso_sa1_repet > 0:
        for grupos_t in treinos:
            for g in grupos_t:
                sids_d = g["slot_ids"]
                if len(sids_d) < 2:
                    continue
                # Coleta padrões possíveis nos pools dos slots desta demanda.
                # Pra cada padrão P, lista de cidxs por slot.
                padroes_por_slot: dict[int, dict[str, list[int]]] = {}
                for sid in sids_d:
                    pool = slot_por_sid[sid]["pool_slot"]
                    pad_map: dict[str, list[int]] = defaultdict(list)
                    for cidx, ex in enumerate(pool):
                        pad_map[ex.padrao].append(cidx)
                    padroes_por_slot[sid] = pad_map

                for i in range(len(sids_d)):
                    for j in range(i + 1, len(sids_d)):
                        s1, s2 = sids_d[i], sids_d[j]
                        pads_s1 = padroes_por_slot[s1]
                        pads_s2 = padroes_por_slot[s2]
                        # Padrões em comum entre os 2 pools.
                        comuns = set(pads_s1.keys()) & set(pads_s2.keys())
                        if not comuns:
                            continue
                        # BoolVar `same_padrao` = exists P: ambos escolheram P.
                        eq_vars = []
                        for pad in comuns:
                            eq_p = model.NewBoolVar(
                                f"sa1v2_eq_{pad}_{s1}_{s2}",
                            )
                            s1_em_P = sum(
                                assign[(s1, c)] for c in pads_s1[pad]
                            )
                            s2_em_P = sum(
                                assign[(s2, c)] for c in pads_s2[pad]
                            )
                            # eq_p ↔ (s1_em_P == 1 AND s2_em_P == 1)
                            model.Add(s1_em_P + s2_em_P >= 2).OnlyEnforceIf(eq_p)
                            model.Add(s1_em_P + s2_em_P <= 1).OnlyEnforceIf(eq_p.Not())
                            eq_vars.append(eq_p)
                        same_padrao = model.NewBoolVar(
                            f"sa1v2_same_{s1}_{s2}",
                        )
                        # OR sobre todos os eq_p — same_padrao=1 se algum eq_p=1.
                        model.AddBoolOr(eq_vars).OnlyEnforceIf(same_padrao)
                        for eq_p in eq_vars:
                            model.AddImplication(eq_p, same_padrao)
                        # Penalty escalar.
                        pen_repet = model.NewIntVar(
                            0, peso_sa1_repet, f"sa1v2_pen_{s1}_{s2}",
                        )
                        model.Add(pen_repet == peso_sa1_repet * same_padrao)
                        penalidades.append(pen_repet)

    # ── S-T1 (SOFT, Fatia 4.A reformulada): tier-order por BLOCO no treino ──
    # Antes (pré-4.A): pares (i,j) dentro de cada grupo de demanda, ordem dos
    # slots na lista. Agora: pares (s1, s2) no mesmo treino, ordem definida
    # por bloco_idx[s] (variável de decisão). Equivalente clinicamente a
    # "tier máximo do bloco vem antes" — se todo slot de tier alto está em
    # bloco com idx menor que slots de tier baixo, soma = 0.
    #
    # Forma par-a-par: pra cada par (s1, s2) no mesmo treino com s1 < s2
    # (ordem de sid pra evitar duplicar pares), cria:
    #   lt = bloco_idx[s1] < bloco_idx[s2]   (BoolVar via OnlyEnforceIf)
    #   gt = bloco_idx[s1] > bloco_idx[s2]
    #   viol IntVar [0, rank_max]:
    #     >= tier_rank[s2] - tier_rank[s1]  se lt
    #     >= tier_rank[s1] - tier_rank[s2]  se gt
    # Pares no mesmo bloco (lt=0, gt=0) não geram viol.
    rank_max = max(TIER_RANK.values())
    # `penalidades` já inicializado acima (antes do bloco S-A1).

    # S-B1 NÃO atua intra-sub explícita (decisão clínica 2026-05-25 com
    # Bernardo): em demanda `("subregiao", X, qtd)`, user pediu a sub
    # explicitamente — pares dentro dela são esperados serem da mesma
    # categoria muscular. Agonistas intra-sub não são bug. S-B1 continua
    # atuando cross-sub no mesmo bloco. Calcula set de pares (s1, s2) que
    # vêm da MESMA demanda subregião pra skipar penalty.
    pares_intra_sub: set[tuple[int, int]] = set()
    for grupos_t in treinos:
        for g in grupos_t:
            nv, _esc, _qt = g["demanda"]
            if nv != "subregiao":
                continue
            sids_g = g["slot_ids"]
            for i in range(len(sids_g)):
                for j in range(i + 1, len(sids_g)):
                    a, b = sorted((sids_g[i], sids_g[j]))
                    pares_intra_sub.add((a, b))

    # S-B5 (2026-05-26): desativa em treinos onde TODOS os slots têm pool
    # restrito a UMA ÚNICA região (treino single-region). Nessas configs
    # o motor não pode escolher cross-region em nenhum bloco — S-B5 só
    # penalizaria por penalizar, e CP-SAT explode o tempo enumerando
    # soluções equivalentes na Phase 2 da variedade. Ex: ABC 3T Day A
    # (peito+ombro+triceps, 7 slots todos `upper`) sem este fix levava
    # ~8 minutos mediana e até 1 hora no pior caso. Com este fix volta
    # a tempos comparáveis ao baseline.
    # Critério: união dos pools de todos os slots do treino = singleton.
    treinos_single_region: set[int] = set()
    for t_idx, sids_t in slots_por_treino.items():
        regioes_treino: set[str] = set()
        for sid in sids_t:
            slot = slot_por_sid[sid]
            for ex in slot["pool_slot"]:
                regioes_treino.add(ex.regiao)
        if len(regioes_treino) <= 1:
            treinos_single_region.add(t_idx)

    for t_idx, sids_t in slots_por_treino.items():
        for i in range(len(sids_t)):
            for j in range(i + 1, len(sids_t)):
                s1, s2 = sids_t[i], sids_t[j]
                lt = model.NewBoolVar(f"lt_{s1}_{s2}")
                gt = model.NewBoolVar(f"gt_{s1}_{s2}")
                # bloco_idx[s1] - bloco_idx[s2] < 0   sse  lt
                model.Add(bloco_idx[s1] - bloco_idx[s2] <= -1).OnlyEnforceIf(lt)
                model.Add(bloco_idx[s1] - bloco_idx[s2] >= 0).OnlyEnforceIf(lt.Not())
                # bloco_idx[s1] - bloco_idx[s2] > 0   sse  gt
                model.Add(bloco_idx[s1] - bloco_idx[s2] >= 1).OnlyEnforceIf(gt)
                model.Add(bloco_idx[s1] - bloco_idx[s2] <= 0).OnlyEnforceIf(gt.Not())
                # lt + gt <= 1 (não podem ser ambos true)
                model.Add(lt + gt <= 1)

                viol = model.NewIntVar(0, rank_max, f"viol_{s1}_{s2}")
                # se lt (s1 antes de s2): penaliza tier[s2] > tier[s1]
                model.Add(
                    viol >= tier_rank[s2] - tier_rank[s1]
                ).OnlyEnforceIf(lt)
                # se gt (s2 antes de s1): penaliza tier[s1] > tier[s2]
                model.Add(
                    viol >= tier_rank[s1] - tier_rank[s2]
                ).OnlyEnforceIf(gt)
                penalidades.append(viol)

                # ── Fatia 4.B: S-B1 (distância funcional intra-bloco) ─────
                # same_bloco = NOT(lt OR gt). Reusa lt/gt já criados pra S-T1.
                # Penalty se same_bloco AND same_grupo (par agonista no
                # mesmo bloco). Quando peso=0, NÃO cria as vars (preserva
                # 4.A byte-a-byte).
                # SKIP pares intra-sub explícita (decisão 2026-05-25):
                # user pediu a sub, agonistas dentro dela são esperados.
                # S-B5 (2026-05-26): mesma reformulação, com same_regiao em
                # vez de same_grupo. Se ambos pesos>0, `same_bloco` é
                # criado UMA vez e reusado pelos dois penalties.
                sb1_aplica = (
                    peso_evitar_agonistas > 0
                    and (s1, s2) not in pares_intra_sub
                )
                sb5_aplica = (
                    peso_sb5 > 0
                    and t_idx not in treinos_single_region
                )
                precisa_same_bloco = sb1_aplica or sb5_aplica
                if precisa_same_bloco:
                    same_bloco = model.NewBoolVar(f"sb_{s1}_{s2}")
                    # same_bloco + lt + gt == 1 (exatamente um dos três é true)
                    model.Add(same_bloco + lt + gt == 1)

                    if sb1_aplica:
                        same_grupo = model.NewBoolVar(f"sg_{s1}_{s2}")
                        model.Add(
                            grupo_func[s1] == grupo_func[s2]
                        ).OnlyEnforceIf(same_grupo)
                        model.Add(
                            grupo_func[s1] != grupo_func[s2]
                        ).OnlyEnforceIf(same_grupo.Not())

                        # AND lógico: ambos true → ativa penalty.
                        viol_sb1 = model.NewIntVar(
                            0, peso_evitar_agonistas, f"sb1_{s1}_{s2}",
                        )
                        model.Add(viol_sb1 >= peso_evitar_agonistas).OnlyEnforceIf(
                            [same_bloco, same_grupo],
                        )
                        penalidades.append(viol_sb1)

                    if sb5_aplica:
                        same_regiao = model.NewBoolVar(f"sr_{s1}_{s2}")
                        model.Add(
                            regiao_idx[s1] == regiao_idx[s2]
                        ).OnlyEnforceIf(same_regiao)
                        model.Add(
                            regiao_idx[s1] != regiao_idx[s2]
                        ).OnlyEnforceIf(same_regiao.Not())

                        viol_sb5 = model.NewIntVar(
                            0, peso_sb5, f"sb5_{s1}_{s2}",
                        )
                        model.Add(viol_sb5 >= peso_sb5).OnlyEnforceIf(
                            [same_bloco, same_regiao],
                        )
                        penalidades.append(viol_sb5)

    # ── S-R1 (2026-05-27): distribuição cross-treino de subregião dentro ────
    # de região. Achado 1 da auditoria 2026-05-26 (faceta de simetria
    # T1↔T2): em `regiao lower(3) × 2T`, T1 e T2 caem no mesmo split
    # 2ant+1post+0pant porque cada treino sorteia independente. S-R1 modela
    # explicitamente no objetivo: pra cada par de treinos (t1, t2) com
    # demanda mesma região R, penaliza splits IDÊNTICOS (T1 e T2 com a
    # mesma contagem em TODAS as subregiões de R).
    #
    # Modelagem (BoolVar `splits_iguais` por par + região):
    #   pra cada subregião S em R: count_S_t1, count_S_t2 IntVars + diff_S
    #   same_S = (diff_S == 0)
    #   splits_iguais = AND(same_S) sobre todas as S
    #   penalty = peso_sr1 * splits_iguais
    #
    # CONTRA-INTUITIVO mas correto: minimizar `sum(|diff_t1_t2|)` (versão
    # ingênua) empurra pra T1==T2 (espelho matemático = mesmo split), o
    # OPOSTO do objetivo clínico. Penalizar `splits_iguais` é a forma certa
    # — premia que pelo menos UMA subregião tenha contagem diferente entre
    # os 2 treinos da rotina. Motor naturalmente escolhe alternância
    # (ex.: T1=2ant+1post / T2=1ant+2post) em vez de T1==T2.
    #
    # Skip estrutural: rotina com <2 treinos é neutra (sem cross-treino).
    # BoolVars criadas SÓ quando peso_sr1 > 0 (otimização — pulamos quando
    # peso=0, mesmo pattern de outras softs).
    if peso_sr1 > 0 and len(treinos) >= 2:
        grupos_regiao_por_treino: dict[tuple[int, str], list[int]] = {}
        for t_idx, grupos_t in enumerate(treinos):
            for g in grupos_t:
                nv, esc, _qt = g["demanda"]
                if nv == "regiao":
                    grupos_regiao_por_treino[(t_idx, esc)] = list(g["slot_ids"])

        regiao_para_tidxs: dict[str, list[int]] = defaultdict(list)
        for (t_idx, R), _sids in grupos_regiao_por_treino.items():
            regiao_para_tidxs[R].append(t_idx)

        for R, t_idxs in regiao_para_tidxs.items():
            if len(t_idxs) < 2:
                continue
            subs_possiveis = REGIAO_PARA_SUBREGIOES.get(R, [])
            # counts_por_t[t_idx][sub] = IntVar (qtd slots de sub em (t_idx, R)).
            counts_por_t: dict[int, dict[str, cp_model.IntVar]] = defaultdict(dict)
            for sub in subs_possiveis:
                sub_code = SUBREGIAO_CODE.get(sub)
                if sub_code is None:
                    continue
                for t_idx in t_idxs:
                    sids_tR = grupos_regiao_por_treino[(t_idx, R)]
                    if not sids_tR:
                        continue
                    indicators = []
                    for sid in sids_tR:
                        is_sub = model.NewBoolVar(
                            f"sr1_is_{R}_{sub}_t{t_idx}_s{sid}",
                        )
                        model.Add(
                            subregiao_idx[sid] == sub_code
                        ).OnlyEnforceIf(is_sub)
                        model.Add(
                            subregiao_idx[sid] != sub_code
                        ).OnlyEnforceIf(is_sub.Not())
                        indicators.append(is_sub)
                    count_var = model.NewIntVar(
                        0, len(sids_tR),
                        f"sr1_count_{R}_{sub}_t{t_idx}",
                    )
                    model.Add(count_var == sum(indicators))
                    counts_por_t[t_idx][sub] = count_var

            # Pares (t1, t2) com BoolVar splits_iguais.
            t_list = sorted(t_idxs)
            for i in range(len(t_list)):
                for j in range(i + 1, len(t_list)):
                    t1, t2 = t_list[i], t_list[j]
                    subs_comuns = [
                        s for s in subs_possiveis
                        if s in counts_por_t[t1] and s in counts_por_t[t2]
                    ]
                    if not subs_comuns:
                        continue
                    # same_S por subregião — true sse count_S_t1 == count_S_t2.
                    same_vars = []
                    for sub in subs_comuns:
                        same_S = model.NewBoolVar(
                            f"sr1_same_{R}_{sub}_t{t1}_t{t2}",
                        )
                        model.Add(
                            counts_por_t[t1][sub] == counts_por_t[t2][sub]
                        ).OnlyEnforceIf(same_S)
                        model.Add(
                            counts_por_t[t1][sub] != counts_por_t[t2][sub]
                        ).OnlyEnforceIf(same_S.Not())
                        same_vars.append(same_S)

                    # splits_iguais = AND(same_S) — true sse TODAS as subs
                    # têm a mesma contagem em t1 e t2.
                    splits_iguais = model.NewBoolVar(
                        f"sr1_eq_{R}_t{t1}_t{t2}",
                    )
                    # Reverse implication: NOT splits_iguais → algum same_S é
                    # False. Forward: splits_iguais → todos same_S True.
                    model.AddBoolAnd(same_vars).OnlyEnforceIf(splits_iguais)
                    model.AddBoolOr([v.Not() for v in same_vars]).OnlyEnforceIf(
                        splits_iguais.Not()
                    )

                    pen = model.NewIntVar(
                        0, peso_sr1, f"sr1_pen_{R}_t{t1}_t{t2}",
                    )
                    model.Add(pen == peso_sr1 * splits_iguais)
                    penalidades.append(pen)

    # ── S-B4 (Fatia 4.C): tamanho preferido do bloco ────────────────────────
    # Pra cada bloco b do treino t:
    #   tamanho_b = sum(X[(t,sid,b)] for sid)
    #   usado_b   = (tamanho_b > 0)
    #   desvio_b  = |tamanho_b - tamanho_preferido|  (só se usado_b; 0 vazio)
    #   pen_b     = peso_tamanho_bloco * desvio_b
    # Equilibra trade-off da 4.B: motor com S-B1 ativo prefere blocos solo
    # pra evitar penalty; S-B4 dá incentivo positivo a blocos com tamanho
    # desejado pelo user. peso=0 (default) skipa toda criação — preserva 4.B.
    if peso_tamanho_bloco > 0:
        for t_idx, sids_t in slots_por_treino.items():
            max_b = len(sids_t)
            for b in range(max_b):
                tamanho_b = model.NewIntVar(
                    0, TAMANHO_MAX_BLOCO, f"tam_t{t_idx}_b{b}",
                )
                model.Add(tamanho_b == sum(
                    slot_to_bloco_vars[sid][b] for sid in sids_t
                ))

                usado_b = model.NewBoolVar(f"used_t{t_idx}_b{b}")
                model.Add(tamanho_b >= 1).OnlyEnforceIf(usado_b)
                model.Add(tamanho_b == 0).OnlyEnforceIf(usado_b.Not())

                desvio_b = model.NewIntVar(
                    0, TAMANHO_MAX_BLOCO, f"desv_t{t_idx}_b{b}",
                )
                # |tamanho_b - tamanho_preferido| quando usado_b; senão 0.
                model.Add(
                    desvio_b >= tamanho_b - tamanho_preferido
                ).OnlyEnforceIf(usado_b)
                model.Add(
                    desvio_b >= tamanho_preferido - tamanho_b
                ).OnlyEnforceIf(usado_b)
                model.Add(desvio_b == 0).OnlyEnforceIf(usado_b.Not())

                pen_b = model.NewIntVar(
                    0, peso_tamanho_bloco * TAMANHO_MAX_BLOCO,
                    f"sb4_t{t_idx}_b{b}",
                )
                model.Add(pen_b == peso_tamanho_bloco * desvio_b)
                penalidades.append(pen_b)

    # ── H-cargas (Fatia 4.E cargas): par-a-par dentro do bloco ──────────────
    # Pra cada par (s1, s2) no mesmo treino e par de candidatos (c1, c2)
    # violador em alguma dimensão, e cada bloco possível b do treino:
    #   assign[s1,c1] + assign[s2,c2] + X[s1,b] + X[s2,b] - 3 <= cargas_off_b[b]
    # Linearização do AND (4 BoolVars): quando os 4 são True (lado esquerdo=1),
    # força `cargas_off_b[b] = 1`. Quando ≤3 True (lado esquerdo ≤ 0),
    # restrição trivial (cargas_off_b livre = 0 por padrão pelo objetivo).
    #
    # Default: `cargas_off_b[b]` = 0 (filtro ativo). Solver desliga (=1) só
    # quando inviável satisfazer todos os pares; penalty `peso_cargas_off`
    # (default 1000) no objetivo garante isso.
    #
    # Travados ENTRAM nos pares: ex_travado tem pool_slot=[ex_travado] (4.D),
    # então par travado+non-travado violador força non-travado a mudar.
    # Travado vs travado (mesmo treino, ambos pool de 1): só relevante se
    # estiverem no mesmo bloco — aí cargas_off_b vira True (decisão do user
    # supera regra automática, comportamento esperado).
    #
    # Pré-processamento (out-of-loop): identificar pares violadores
    # `pares_violadores_por_treino[t_idx]` = list[(s1, c1, s2, c2, motivo)].
    # Motivo = (dim, soma, threshold) da PRIMEIRA dim violada — usado pra
    # gerar aviso pós-solve. Evita produto cartesiano repetido dentro do
    # add-constraint loop.
    cargas_off_b: dict[tuple[int, int], cp_model.IntVar] = {}
    pares_violadores_por_treino: dict[int, list[tuple]] = {}
    cargas_ativo = _cargas_config_ativo(cargas_config)
    if cargas_ativo:
        for t_idx, sids_t in slots_por_treino.items():
            max_b = len(sids_t)
            pares_violadores: list[tuple] = []

            # Detecta pares (s1, s2, c1, c2, motivo) violadores no treino.
            for ai in range(len(sids_t)):
                for bj in range(ai + 1, len(sids_t)):
                    s1 = sids_t[ai]
                    s2 = sids_t[bj]
                    pool1 = slot_por_sid[s1]["pool_slot"]
                    pool2 = slot_por_sid[s2]["pool_slot"]
                    for c1, ex_a in enumerate(pool1):
                        for c2, ex_b in enumerate(pool2):
                            motivo = _viola_carga_par(ex_a, ex_b, cargas_config)
                            if motivo is None:
                                continue
                            pares_violadores.append((s1, c1, s2, c2, motivo))
            pares_violadores_por_treino[t_idx] = pares_violadores

            if not pares_violadores:
                continue  # nenhum par violador no treino: não cria cargas_off_b

            # Cria cargas_off_b por bloco do treino.
            for b in range(max_b):
                v = model.NewBoolVar(f"cargas_off_t{t_idx}_b{b}")
                cargas_off_b[(t_idx, b)] = v

            # Adiciona restrição por par violador × bloco.
            for s1, c1, s2, c2, _motivo in pares_violadores:
                for b in range(max_b):
                    model.Add(
                        assign[(s1, c1)]
                        + assign[(s2, c2)]
                        + slot_to_bloco_vars[s1][b]
                        + slot_to_bloco_vars[s2][b]
                        - 3
                        <= cargas_off_b[(t_idx, b)]
                    )

            # Penalty no objetivo: peso_cargas_off * sum(cargas_off_b).
            for b in range(max_b):
                pen_carga = model.NewIntVar(
                    0, peso_cargas_off, f"cargas_pen_t{t_idx}_b{b}",
                )
                model.Add(pen_carga == peso_cargas_off * cargas_off_b[(t_idx, b)])
                penalidades.append(pen_carga)

    # ── Aderência ao Tier (SOFT, Frente D Fatia 3): por slot ────────────────
    # `aderencia_pen[s] = (rank_max - tier_rank[s]) * peso_aderencia`
    # Slot com Principal (rank=3): pen = 0. Acessório (rank=1): pen = 2*peso.
    # Quando peso=0 (Média/Baixa neutras), bloco inteiro skipado — preserva
    # byte-a-byte o comportamento da Frente B (legacy + variedade).
    if peso_aderencia > 0:
        for s in slots_globais:
            ader_pen = model.NewIntVar(
                0, rank_max * peso_aderencia,
                f"ader_t{s['t_idx']}_s{s['sid']}",
            )
            model.Add(ader_pen == (rank_max - tier_rank[s["sid"]]) * peso_aderencia)
            penalidades.append(ader_pen)

    return {
        "model": model,
        "assign": assign,
        "slots_globais": slots_globais,
        "treinos": treinos,
        "grupo_por_idx": grupo_por_idx,
        "h_r1_aplicadas": h_r1_aplicadas,
        # Micro-frente H-A1: lista de aplicações de âncoras obrigatórias por
        # subregião (análoga a h_r1_aplicadas, com flag `degraded` e motivo
        # quando a constraint daquela âncora foi pulada por pool vazio ou
        # conflito de cardinalidade).
        "h_a1_aplicadas": h_a1_aplicadas,
        # Micro-frente H-A0: âncoras obrigatórias por REGIÃO, agregação
        # per-treino. Cada entrada `{treino, regiao, subregiao_obrigatoria,
        # n_slots, degraded, motivo?}`. Mesma semântica de degraded da H-A1.
        "h_a0_aplicadas": h_a0_aplicadas,
        "penalidades": penalidades,
        # Fatia 4.A: vars estruturais de bloco — caller usa pra decodificar
        # blocos da solução (via solver.Value(bloco_idx[s])).
        "bloco_idx": bloco_idx,
        "slots_por_treino": dict(slots_por_treino),
        # Fatia 4.B: grupo funcional do ex escolhido (gancho pra futuras
        # constraints baseadas em grupo).
        "grupo_func": grupo_func,
        # Fatia 4.D: lookup slot por sid (inclui pool_slot por slot + flag
        # `travado`). Caller usa em _decode_solucao pra resolver o ex
        # escolhido pelo cidx (pool por slot ≠ pool por grupo).
        "slot_por_sid": slot_por_sid,
        # Fatia 4.E cargas: BoolVar `cargas_off_b[(t_idx, b)]` indicando
        # quando o filtro foi desligado naquele bloco (graceful degradation).
        # Caller decode lê via `solver.Value(...)` pra gerar avisos
        # `relaxado_carga` analíticos pós-solve. Dict vazio quando
        # cargas_config inativo (preserva 4.D byte-a-byte).
        "cargas_off_b": cargas_off_b,
        # Lista por treino de (s1, c1, s2, c2, motivo) violadores — usada
        # pelo decoder pra emitir aviso `relaxado_carga` quando bloco
        # desligado contém pares violadores efetivamente atribuídos.
        "pares_violadores_por_treino": pares_violadores_por_treino,
        # Reflete `cargas_config` recebido — caller usa pra decidir se gera
        # avisos pós-solve.
        "cargas_config": cargas_config,
    }


def _decode_solucao(
    treinos: list[list[dict]],
    sid_to_cidx: dict[int, int],
    sid_to_bloco: Optional[dict[int, int]] = None,
    slot_por_sid: Optional[dict[int, dict]] = None,
) -> list[dict]:
    """Decodifica `{sid -> cidx}` (+ opcional `{sid -> bloco_idx}` da
    Fatia 4.A) na estrutura de saída `list[dict]` que `gerar_rotina_csp`
    devolve em `resultado['treinos']`.

    Compartilhado entre o branch legacy (extrai do solver) e o branch
    variedade (extrai do callback). Garante mesma forma de saída.

    Pós-4.A, cada treino ganha chave nova `blocos: list[list[Exercicio]]`
    (estruturado pelo motor). `ordem_global` continua existindo (concat dos
    blocos em ordem de bloco_idx) por retrocompat de callers antigos.
    Quando `sid_to_bloco is None` (não deveria acontecer pós-4.A), bloco_idx
    derivado por slot_id (cada slot vira seu próprio bloco).

    `slot_por_sid` (Fatia 4.D): quando presente, o ex escolhido é resolvido
    via pool_slot do slot (necessário pra slots travados, cujo pool difere
    do pool default da demanda). Quando None, cai no comportamento pré-4.D
    (usa g["pool"]) — preserva callers antigos sem travados.
    """
    out = []
    for grupos_t in treinos:
        treino_dict: dict = {"grupos": [], "ordem_global": [], "blocos": []}
        slots_do_treino: list[int] = []

        def _ex_do_slot(sid: int, g: dict) -> Exercicio:
            if slot_por_sid is not None:
                return slot_por_sid[sid]["pool_slot"][sid_to_cidx[sid]]
            return g["pool"][sid_to_cidx[sid]]

        for g in grupos_t:
            nivel, _escopo, qtd = g["demanda"]
            exs = [_ex_do_slot(sid, g) for sid in g["slot_ids"]]
            treino_dict["grupos"].append({
                "demanda": g["demanda"],
                "exercicios": exs,
                "pool_size": len(g["pool"]),
                "h_t4_aplicado": nivel == "subregiao" and qtd == 1,
                "h_t4_aplicado_efetivamente": g.get("h_t4_aplicado_efetivamente", False),
            })
            slots_do_treino.extend(g["slot_ids"])

        # Agrupa slots por bloco_idx, ordena por idx asc.
        blocos_dict: dict[int, list[int]] = defaultdict(list)
        for sid in slots_do_treino:
            b = sid_to_bloco[sid] if sid_to_bloco is not None else sid
            blocos_dict[b].append(sid)
        # Mapa sid → exercício pra lookup
        sid_to_ex: dict[int, Exercicio] = {}
        for g in grupos_t:
            for sid in g["slot_ids"]:
                sid_to_ex[sid] = _ex_do_slot(sid, g)
        for b in sorted(blocos_dict.keys()):
            sids_bloco = blocos_dict[b]
            treino_dict["blocos"].append([sid_to_ex[sid] for sid in sids_bloco])

        # ordem_global = concatenação dos blocos em ordem.
        for bloco_exs in treino_dict["blocos"]:
            treino_dict["ordem_global"].extend(bloco_exs)
        out.append(treino_dict)
    return out


def _avisos_carga_por_treino(
    sid_to_cidx: dict[int, int],
    sid_to_bloco: dict[int, int],
    cargas_off_por_tb: dict[tuple[int, int], int],
    pares_violadores_por_treino: dict[int, list[tuple]],
    slot_por_sid: dict[int, dict],
    n_treinos: int,
) -> dict[int, list[dict]]:
    """Decodifica avisos `relaxado_carga` a partir da solução.

    Para cada treino, percorre `pares_violadores_por_treino[t]` e verifica
    se o par está EFETIVAMENTE atribuído (cidx correto em ambos slots) E
    no mesmo bloco efetivo. Se sim, e o bloco tem `cargas_off_b=True`,
    emite aviso espelhando o formato do antigo (`gerador_treino:1505-1516`):

        {
            "tipo": "relaxado_carga",
            "bloco_idx": int (1-based no log do antigo? aqui 0-based,
                consistente com `Sessao.blocos`),
            "exercicio": str  (nome do ex_a — primeiro do par),
            "par_bloqueado": str (nome do ex_b — segundo),
            "dimensao": str,
            "soma": int,
            "threshold": int,
        }

    O `bloco_idx` retornado é o `bloco_idx` LÓGICO (0..max_b-1) do treino.
    Decoder consumidor pode remapear pra 0..N_blocos_usados-1 pra alinhar
    com `Sessao.blocos` (ordem cronológica) se quiser.

    Dedup por `(bloco_efetivo, frozenset({ex_a, ex_b}))` — múltiplos motivos
    de dim no mesmo par viram 1 aviso só (primeiro motivo wins, igual antigo).

    Retorna `{t_idx: [avisos]}` apenas pros treinos com avisos.
    """
    out: dict[int, list[dict]] = {}
    for t_idx in range(n_treinos):
        pares = pares_violadores_por_treino.get(t_idx, [])
        if not pares:
            continue
        avisos: list[dict] = []
        emitidos: set[tuple] = set()
        for s1, c1, s2, c2, motivo in pares:
            if sid_to_cidx.get(s1) != c1:
                continue
            if sid_to_cidx.get(s2) != c2:
                continue
            b1 = sid_to_bloco.get(s1)
            b2 = sid_to_bloco.get(s2)
            if b1 is None or b2 is None or b1 != b2:
                continue  # par caiu em blocos diferentes — sem violação
            b = b1
            if cargas_off_por_tb.get((t_idx, b), 0) != 1:
                continue  # filtro não foi desligado nesse bloco (não deveria
                          # acontecer se constraint correta, mas defensivo)
            ex_a = slot_por_sid[s1]["pool_slot"][c1]
            ex_b = slot_por_sid[s2]["pool_slot"][c2]
            key = (b, frozenset({ex_a.nome, ex_b.nome}))
            if key in emitidos:
                continue
            emitidos.add(key)
            dim, soma, thr = motivo
            avisos.append({
                "tipo": "relaxado_carga",
                "bloco_idx": b,
                "exercicio": ex_a.nome,
                "par_bloqueado": ex_b.nome,
                "dimensao": dim,
                "soma": soma,
                "threshold": thr,
            })
        if avisos:
            out[t_idx] = avisos
    return out


class _SolucoesCollector(cp_model.CpSolverSolutionCallback):
    """Callback que coleta todas as soluções enumeradas até `max_solucoes`.

    Cada solução vira `(sid_to_cidx: dict[int, int], inversoes: int)`.
    Aborta a busca com `StopSearch()` quando o cap é atingido — evita
    explosão combinatória em rotinas subdeterminadas.
    """

    def __init__(
        self,
        assign: dict[tuple[int, int], cp_model.IntVar],
        var_total_penalidade: Optional[cp_model.IntVar],
        max_solucoes: int,
        bloco_idx: Optional[dict[int, cp_model.IntVar]] = None,
        cargas_off_b: Optional[dict[tuple[int, int], cp_model.IntVar]] = None,
    ) -> None:
        super().__init__()
        self._assign_por_sid: dict[int, list[tuple[int, object]]] = defaultdict(list)
        for (sid, cidx), v in assign.items():
            self._assign_por_sid[sid].append((cidx, v))
        self._var_total = var_total_penalidade
        self._max = max_solucoes
        self._bloco_idx = bloco_idx  # Fatia 4.A: capturado por solução
        self._cargas_off_b = cargas_off_b or {}  # Fatia 4.E cargas
        self.solucoes: list[dict[int, int]] = []
        self.inversoes: list[int] = []
        self.blocos: list[dict[int, int]] = []  # Fatia 4.A: sid → bloco_idx
        # Fatia 4.E cargas: por solução, mapa (t_idx, b) → 0/1.
        self.cargas_off: list[dict[tuple[int, int], int]] = []

    def on_solution_callback(self) -> None:
        sol: dict[int, int] = {}
        for sid, lst in self._assign_por_sid.items():
            for cidx, v in lst:
                if self.Value(v) == 1:
                    sol[sid] = cidx
                    break
        self.solucoes.append(sol)
        inv = int(self.Value(self._var_total)) if self._var_total is not None else 0
        self.inversoes.append(inv)
        # Fatia 4.A: extrai bloco_idx por slot pra estruturação na decode.
        if self._bloco_idx is not None:
            self.blocos.append({sid: int(self.Value(v)) for sid, v in self._bloco_idx.items()})
        else:
            self.blocos.append({})
        # Fatia 4.E cargas: extrai cargas_off_b por (t_idx, b) pra decoder
        # gerar avisos `relaxado_carga`.
        if self._cargas_off_b:
            self.cargas_off.append({
                tb: int(self.Value(v)) for tb, v in self._cargas_off_b.items()
            })
        else:
            self.cargas_off.append({})
        if len(self.solucoes) >= self._max:
            self.StopSearch()


# ---------------------------------------------------------------------------
# Engine CP-SAT — rotina inteira (N treinos negociados no mesmo modelo)
# ---------------------------------------------------------------------------

def _identificar_relaxados_por_familia(
    rotina: dict,
    familias_originais: set[str],
    travados_por_treino: Optional[dict[int, list[Exercicio]]],
) -> dict[int, list[str]]:
    """Pra cada treino da rotina viável, identifica os ex cuja família
    estava no set proibido pré-relax. Esses são os "relaxados" que vão
    receber badge ↻ na UI e gerar aviso `familia_repetida`.

    Travados são pulados — travado é decisão deliberada do user (princípio
    da 4.D), não conta como "relaxamento de regra automática".

    Retorna `{t_idx: [nome_ex, ...]}` apenas pros treinos que tiveram
    pelo menos 1 relaxado.
    """
    travados_set: set[tuple[int, str]] = set()
    for t_idx, exs in (travados_por_treino or {}).items():
        for ex in exs:
            travados_set.add((t_idx, ex.nome))

    out: dict[int, list[str]] = {}
    for t_idx, treino in enumerate(rotina.get("treinos", [])):
        nomes_rel: list[str] = []
        for grupo in treino["grupos"]:
            for ex in grupo["exercicios"]:
                if (t_idx, ex.nome) in travados_set:
                    continue
                if _familia_cross(ex) in familias_originais:
                    nomes_rel.append(ex.nome)
        if nomes_rel:
            out[t_idx] = nomes_rel
    return out


def gerar_rotina_csp(
    demandas_por_treino: list[list[tuple[str, str, int]]],
    banco: list[Exercicio],
    nivel_aluno: int,
    seed: int = 0,
    variedade: Optional[ConfigVariedade] = None,
    peso_aderencia: int = 0,
    peso_evitar_agonistas: int = 0,
    tamanho_preferido: int = 2,
    peso_tamanho_bloco: int = 0,
    travados_por_treino: Optional[dict[int, list[Exercicio]]] = None,
    familias_proibidas: Optional[set[str]] = None,
    relaxar_familia: bool = False,
    cargas_config: Optional[dict[str, int]] = None,
    peso_cargas_off: int = 1000,
    peso_sa1: int = 0,
    peso_sa1_repet: int = 0,
    peso_sb5: int = 0,
    peso_sr1: int = 0,
) -> dict:
    """Resolve uma ROTINA (N treinos) via CP-SAT. Slots dos N treinos
    negociam no mesmo modelo — necessário pra H-R1 cross-treino.

    `demandas_por_treino[t]`: lista de (nivel, escopo, qtd) do treino t.
    `banco`: lista já carregada (ativo=True). `nivel_aluno`: 1/2/3 (H-P1).
    `seed`: semente do CP-SAT (afeta exploração de busca).
    `variedade`: None preserva comportamento Fatia 2 P2 (1 solve com
    Minimize, 1 solução determinística por seed). ConfigVariedade ativa
    enumeração + softmax — ver docstring de ConfigVariedade.
    `peso_aderencia` (Frente D Fatia 3): modulação da dimensão "Aderência
    ao Tier" do vetor de perfil. 0 (default) = sem efeito (preserva
    byte-a-byte Frente B). >0 adiciona penalty por slot proporcional a
    `(rank_max - rank_slot) * peso` — ver `_construir_modelo`.

    `familias_proibidas` (Fatia 4.E, 2026-05-24): set de identificadores
    `_familia_cross(ex)` que não podem aparecer (hard cross-treino, pré-
    filtra pools dos slots non-travados). Quando o adapter de /regerar
    chama este motor pra regerar 1 treino, calcula este set a partir
    dos ex já nos OUTROS treinos da rotina — substitui o filtro extra-
    solver da Frente C. None ou vazio = preserva 4.D byte-a-byte.

    `relaxar_familia` (Fatia 4.E, 2026-05-24): quando True E o solve com
    `familias_proibidas` é inviável, refaz o solve com `familias_proibidas
    = set()` (relaxa). Identifica os ex relaxados via
    `_identificar_relaxados_por_familia` e expõe em `relaxados_por_treino`
    do retorno (caller propaga pra `Sessao.relaxados` + gera aviso
    `familia_repetida`). Default False = comportamento estrito (motor
    devolve inviável quando family hard não passa, igual pré-4.E).

    Retorna dict com:
      - top-level: `viavel`, `status`, `nivel_aluno`, `seed`, `solve_time`,
        `inversoes_totais` (soma cross-treino de S-T1).
      - `treinos: list[dict]` — cada treino tem `grupos`, `ordem_global`.
      - `h_r1_aplicadas`: lista de aplicações H-R1 (com flag degraded).
      - `h_a1_aplicadas`: lista de aplicações H-A1 (âncoras obrigatórias por
        subregião). Análoga a `h_r1_aplicadas` — degraded=True quando pool
        vazio (pulada) ou conflito de cardinalidade (constraint colaborativa).
      - `h_a0_aplicadas`: lista de aplicações H-A0 (âncoras obrigatórias por
        REGIÃO, agregação per-treino). Cada entrada `{treino, regiao,
        subregiao_obrigatoria, n_slots, degraded, motivo?}`. Mesmo padrão de
        graceful degradation da H-A1.
      - `variedade` (só quando ConfigVariedade ativa): metadados da
        enumeração (n_solucoes, distancia_escolhida, optimal_value,
        enumeracao_limitada, tempo por fase).
      - `relaxados_por_treino` (Fatia 4.E): dict `{t_idx: [nome, ...]}`
        dos ex relaxados (vazio quando relax não foi acionado).
      - `relax_ativado` (Fatia 4.E): True só quando 1ª tentativa estrita
        falhou E relaxar_familia=True E 2ª tentativa relaxada teve sucesso.
      - `avisos_carga_por_treino` (Fatia 4.E cargas): dict `{t_idx: [aviso]}`
        de avisos `relaxado_carga` emitidos pós-solve (apenas treinos com
        ao menos 1 bloco com filtro desligado). Vazio quando cargas_config
        inativo ou nenhum bloco precisou desligar.

    `cargas_config` + `peso_cargas_off` (Fatia 4.E cargas, 2026-05-24):
    H-cargas par-a-par no bloco (réplica do filtro antigo). Ver docstring
    de `_construir_modelo`. None / dict vazio / todas dims 0 = constraint
    inteira pulada (preserva 4.D byte-a-byte).
    """
    def _resolver(fams_arg: Optional[set[str]]) -> dict:
        if variedade is None:
            return _resolver_legacy(
                demandas_por_treino, banco, nivel_aluno, seed,
                peso_aderencia, peso_evitar_agonistas,
                tamanho_preferido, peso_tamanho_bloco,
                travados_por_treino,
                familias_proibidas=fams_arg,
                cargas_config=cargas_config,
                peso_cargas_off=peso_cargas_off,
                peso_sa1=peso_sa1,
                peso_sa1_repet=peso_sa1_repet,
                peso_sb5=peso_sb5,
                peso_sr1=peso_sr1,
            )
        return _resolver_com_variedade(
            demandas_por_treino, banco, nivel_aluno, seed, variedade,
            peso_aderencia, peso_evitar_agonistas,
            tamanho_preferido, peso_tamanho_bloco,
            travados_por_treino,
            familias_proibidas=fams_arg,
            cargas_config=cargas_config,
            peso_cargas_off=peso_cargas_off,
            peso_sa1=peso_sa1,
            peso_sa1_repet=peso_sa1_repet,
            peso_sb5=peso_sb5,
            peso_sr1=peso_sr1,
        )

    fams_originais = set(familias_proibidas or [])

    # 1ª passagem: estrito (com familias_proibidas se houver).
    rotina = _resolver(fams_originais if fams_originais else None)

    # Não precisa relax: viável OR sem famílias pra proibir OR toggle off.
    if rotina["viavel"] or not fams_originais or not relaxar_familia:
        rotina["relaxados_por_treino"] = {}
        rotina["relax_ativado"] = False
        rotina.setdefault("avisos_carga_por_treino", {})
        return rotina

    # 2ª passagem: relax. Refaz sem o filtro de família.
    rotina_relax = _resolver(None)
    if not rotina_relax["viavel"]:
        # Mesmo relaxado, inviável — devolve a 1ª (também inviável).
        rotina["relaxados_por_treino"] = {}
        rotina["relax_ativado"] = False
        rotina.setdefault("avisos_carga_por_treino", {})
        return rotina

    relaxados = _identificar_relaxados_por_familia(
        rotina_relax, fams_originais, travados_por_treino
    )
    rotina_relax["relaxados_por_treino"] = relaxados
    rotina_relax["relax_ativado"] = True
    rotina_relax.setdefault("avisos_carga_por_treino", {})
    return rotina_relax


def _resolver_legacy(
    demandas_por_treino: list[list[tuple[str, str, int]]],
    banco: list[Exercicio],
    nivel_aluno: int,
    seed: int,
    peso_aderencia: int = 0,
    peso_evitar_agonistas: int = 0,
    tamanho_preferido: int = 2,
    peso_tamanho_bloco: int = 0,
    travados_por_treino: Optional[dict[int, list[Exercicio]]] = None,
    familias_proibidas: Optional[set[str]] = None,
    cargas_config: Optional[dict[str, int]] = None,
    peso_cargas_off: int = 1000,
    peso_sa1: int = 0,
    peso_sa1_repet: int = 0,
    peso_sb5: int = 0,
    peso_sr1: int = 0,
) -> dict:
    """Branch legado: 1 solve com Minimize → 1 solução determinística por
    seed. Preserva byte-a-byte o comportamento da Fatia 2 P2 quando
    todos os pesos opcionais (peso_aderencia, peso_evitar_agonistas,
    peso_tamanho_bloco) == 0."""
    md = _construir_modelo(
        demandas_por_treino, banco, nivel_aluno,
        peso_aderencia, peso_evitar_agonistas,
        tamanho_preferido, peso_tamanho_bloco,
        travados_por_treino=travados_por_treino,
        familias_proibidas=familias_proibidas,
        cargas_config=cargas_config,
        peso_cargas_off=peso_cargas_off,
        peso_sa1=peso_sa1,
        peso_sa1_repet=peso_sa1_repet,
        peso_sb5=peso_sb5,
        peso_sr1=peso_sr1,
    )
    if md["penalidades"]:
        md["model"].Minimize(sum(md["penalidades"]))

    solver = cp_model.CpSolver()
    solver.parameters.random_seed = seed
    solver.parameters.randomize_search = True
    t0 = time.perf_counter()
    status = solver.Solve(md["model"])
    solve_time = time.perf_counter() - t0

    status_nome = solver.StatusName(status)
    viavel = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    resultado: dict = {
        "status": status_nome,
        "viavel": viavel,
        "nivel_aluno": nivel_aluno,
        "seed": seed,
        "solve_time": solve_time,
        "inversoes_totais": (
            int(round(solver.ObjectiveValue()))
            if (md["penalidades"] and viavel) else 0
        ),
        "h_r1_aplicadas": md["h_r1_aplicadas"],
        "h_a1_aplicadas": md["h_a1_aplicadas"],
        "h_a0_aplicadas": md["h_a0_aplicadas"],
        "treinos": [],
        "avisos_carga_por_treino": {},
    }
    if not viavel:
        return resultado

    sid_to_cidx: dict[int, int] = {}
    for s in md["slots_globais"]:
        pool = s["pool_slot"]
        for cidx in range(len(pool)):
            if solver.Value(md["assign"][(s["sid"], cidx)]) == 1:
                sid_to_cidx[s["sid"]] = cidx
                break
    # Fatia 4.A: extrai bloco_idx por slot pro decode estruturar blocos.
    sid_to_bloco: dict[int, int] = {
        sid: int(solver.Value(v)) for sid, v in md["bloco_idx"].items()
    }
    resultado["treinos"] = _decode_solucao(
        md["treinos"], sid_to_cidx, sid_to_bloco,
        slot_por_sid=md["slot_por_sid"],
    )
    # Fatia 4.E cargas: decodifica avisos `relaxado_carga` pós-solve.
    cargas_off_por_tb: dict[tuple[int, int], int] = {
        tb: int(solver.Value(v)) for tb, v in md["cargas_off_b"].items()
    }
    resultado["avisos_carga_por_treino"] = _avisos_carga_por_treino(
        sid_to_cidx, sid_to_bloco, cargas_off_por_tb,
        md["pares_violadores_por_treino"], md["slot_por_sid"],
        n_treinos=len(md["treinos"]),
    )
    return resultado


def _resolver_com_variedade(
    demandas_por_treino: list[list[tuple[str, str, int]]],
    banco: list[Exercicio],
    nivel_aluno: int,
    seed: int,
    variedade: ConfigVariedade,
    peso_aderencia: int = 0,
    peso_evitar_agonistas: int = 0,
    tamanho_preferido: int = 2,
    peso_tamanho_bloco: int = 0,
    travados_por_treino: Optional[dict[int, list[Exercicio]]] = None,
    familias_proibidas: Optional[set[str]] = None,
    cargas_config: Optional[dict[str, int]] = None,
    peso_cargas_off: int = 1000,
    peso_sa1: int = 0,
    peso_sa1_repet: int = 0,
    peso_sb5: int = 0,
    peso_sr1: int = 0,
) -> dict:
    """Branch variedade (Frente B Fatia 3): 2 fases.

    Phase 1 (solver com Minimize): descobre `optimal` = valor mínimo da
    função objetivo (nº de inversões de S-T1 + termos de Aderência ao
    Tier quando `peso_aderencia > 0`).

    Phase 2 (modelo reconstruído, sem Minimize): cria IntVar `var_total`
    = sum(penalidades), adiciona bound `var_total <= optimal + slack`,
    ativa `enumerate_all_solutions`, coleta soluções via callback até
    `max_solucoes`. Softmax sobre as
    soluções coletadas: peso = exp(-(inversoes - optimal) / temperatura).
    Amostra uma com `random.Random(python_seed)`.

    `peso_aderencia` (Frente D Fatia 3): propagado pras 2 fases via
    `_construir_modelo`. Comportamento esperado: pra Aderência Alta,
    Phase 1 sobe o ótimo (rotinas com Acessório em slot único agora
    pagam penalty), e Phase 2 enumera só as soluções dentro do mesmo
    `slack` no novo ótimo — entrega Aderência Alta de fato sem perder
    variedade interna às opções de tier alto equivalente.
    """
    # ── Phase 1: descobre o ótimo ───────────────────────────────────────────
    md1 = _construir_modelo(
        demandas_por_treino, banco, nivel_aluno,
        peso_aderencia, peso_evitar_agonistas,
        tamanho_preferido, peso_tamanho_bloco,
        travados_por_treino=travados_por_treino,
        familias_proibidas=familias_proibidas,
        cargas_config=cargas_config,
        peso_cargas_off=peso_cargas_off,
        peso_sa1=peso_sa1,
        peso_sa1_repet=peso_sa1_repet,
        peso_sb5=peso_sb5,
        peso_sr1=peso_sr1,
    )
    if md1["penalidades"]:
        md1["model"].Minimize(sum(md1["penalidades"]))

    solver1 = cp_model.CpSolver()
    solver1.parameters.random_seed = seed
    solver1.parameters.randomize_search = True
    t0 = time.perf_counter()
    status1 = solver1.Solve(md1["model"])
    time_p1 = time.perf_counter() - t0

    viavel_p1 = status1 in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    if not viavel_p1:
        return {
            "status": solver1.StatusName(status1),
            "viavel": False,
            "nivel_aluno": nivel_aluno,
            "seed": seed,
            "solve_time": time_p1,
            "inversoes_totais": 0,
            "h_r1_aplicadas": md1["h_r1_aplicadas"],
            "h_a1_aplicadas": md1["h_a1_aplicadas"],
            "h_a0_aplicadas": md1["h_a0_aplicadas"],
            "treinos": [],
            "avisos_carga_por_treino": {},
            "variedade": _meta_variedade(variedade, n=0, dist=None, opt=None,
                                         lim=False, t1=time_p1, t2=0.0),
        }

    optimal = (
        int(round(solver1.ObjectiveValue()))
        if md1["penalidades"] else 0
    )

    # ── Phase 2: enumera dentro do slack ────────────────────────────────────
    # IntVar `var_total` criado AQUI (não no helper) porque só esta fase
    # precisa de bound `<= optimal + slack` + leitura via callback.
    md2 = _construir_modelo(
        demandas_por_treino, banco, nivel_aluno,
        peso_aderencia, peso_evitar_agonistas,
        tamanho_preferido, peso_tamanho_bloco,
        travados_por_treino=travados_por_treino,
        familias_proibidas=familias_proibidas,
        cargas_config=cargas_config,
        peso_cargas_off=peso_cargas_off,
        peso_sa1=peso_sa1,
        peso_sa1_repet=peso_sa1_repet,
        peso_sb5=peso_sb5,
        peso_sr1=peso_sr1,
    )
    var_total: Optional[cp_model.IntVar] = None
    if md2["penalidades"]:
        # Fatia 4.E cargas: teto agora precisa incluir peso_cargas_off por
        # bloco (pode ser muito maior que rank_max * len). Usa upper bound
        # do número de termos × maior peso possível por termo.
        # S-A1: termo max = (peso_max_nao_obrig - peso_min) * peso_sa1.
        # peso_max é 2 e peso_min é 1 nas subs com não-obrig hoje → diff=1.
        # Margem defensiva: 2 * peso_sa1.
        teto_por_termo = max(
            max(TIER_RANK.values()),
            peso_cargas_off if cargas_config else 0,
            peso_evitar_agonistas,
            peso_aderencia * max(TIER_RANK.values()) if peso_aderencia else 0,
            peso_tamanho_bloco * TAMANHO_MAX_BLOCO if peso_tamanho_bloco else 0,
            2 * peso_sa1 if peso_sa1 else 0,
            peso_sa1_repet,
            peso_sb5,
            # S-R1 (2026-05-27): cada par (t1, t2, R) gera 1 termo escalar
            # 0 ou peso_sr1 (BoolVar `splits_iguais`). Max por termo = peso_sr1.
            peso_sr1,
        )
        teto = max(1, teto_por_termo) * len(md2["penalidades"])
        var_total = md2["model"].NewIntVar(0, teto, "var_total")
        md2["model"].Add(var_total == sum(md2["penalidades"]))
        md2["model"].Add(var_total <= optimal + variedade.slack)

    collector = _SolucoesCollector(
        md2["assign"], var_total, variedade.max_solucoes,
        bloco_idx=md2["bloco_idx"],  # Fatia 4.A: captura blocos por solução
        cargas_off_b=md2["cargas_off_b"],  # Fatia 4.E cargas
    )
    solver2 = cp_model.CpSolver()
    solver2.parameters.random_seed = seed
    solver2.parameters.enumerate_all_solutions = True
    # enumerate_all_solutions exige busca single-thread (auto-imposto em
    # versões modernas, mas setamos explicitamente pra evitar warnings).
    solver2.parameters.num_search_workers = 1
    # Amostragem aleatória do CP-SAT (decisão Bernardo, 2026-05-23):
    # sem randomize_search + random_branches_ratio, CP-SAT visita as
    # soluções na ordem heurística "natural" — quando há >100 ótimas e
    # cap em max_solucoes, as 100 primeiras concentram-se numa região
    # do espaço (viés de exploração). Ativar randomização força o solver
    # a fazer escolhas aleatórias nos branches, espalhando as 100
    # soluções coletadas pelo espaço total de ótimas equivalentes.
    solver2.parameters.randomize_search = True
    solver2.parameters.random_branches_ratio = 1.0
    t0 = time.perf_counter()
    solver2.Solve(md2["model"], collector)
    time_p2 = time.perf_counter() - t0

    if not collector.solucoes:
        # Inesperado: Phase 1 viável mas Phase 2 não enumerou nada.
        # Fallback pro modo legado (não bloqueia o caller).
        return _resolver_legacy(
            demandas_por_treino, banco, nivel_aluno, seed,
            peso_aderencia, peso_evitar_agonistas,
            tamanho_preferido, peso_tamanho_bloco,
            travados_por_treino,
            familias_proibidas=familias_proibidas,
            cargas_config=cargas_config,
            peso_cargas_off=peso_cargas_off,
        ) | {
            "variedade": _meta_variedade(variedade, n=0, dist=None, opt=optimal,
                                         lim=False, t1=time_p1, t2=time_p2),
        }

    distancias = [inv - optimal for inv in collector.inversoes]

    # ── Frente 2: Hamming ponderado por tier vs referência ──────────────────
    # Referência = 1ª solução enumerada. Pra cada solução k, soma sobre slots
    # de `ref_tier_rank[s] * (k[s] != ref[s])`. Mudar slot Principal (rank=3)
    # custa 3× mais que mudar Acessório (rank=1). Score final do softmax:
    # peso = exp(-(distancia_objetivo + alpha_tier * H) / T).
    # `alpha_tier == 0` (default) zera H → comportamento Frente 1 puro.
    if variedade.alpha_tier > 0 and collector.solucoes:
        ref_sol = collector.solucoes[0]
        # Tier rank por slot na referência (consulta pool por slot — pós-4.D
        # respeita pool_slot do travado).
        ref_tier_rank: dict[int, int] = {}
        for sid, cidx_ref in ref_sol.items():
            slot_info = md2["slot_por_sid"][sid]
            pool = slot_info["pool_slot"]
            ref_tier_rank[sid] = _tier_rank(pool[cidx_ref])
        hamming = []
        for sol_k in collector.solucoes:
            h = sum(
                ref_tier_rank[sid]
                for sid, cidx_k in sol_k.items()
                if cidx_k != ref_sol[sid]
            )
            hamming.append(h)
    else:
        hamming = [0] * len(collector.solucoes)

    # Softmax numericamente estável (subtrai max log antes do exp).
    # Score composto: distancia objetivo + alpha_tier * Hamming ponderado.
    pesos_log = [
        -(d + variedade.alpha_tier * h) / variedade.temperatura
        for d, h in zip(distancias, hamming)
    ]
    max_log = max(pesos_log)
    exps = [math.exp(lp - max_log) for lp in pesos_log]
    total_w = sum(exps)
    pesos = [e / total_w for e in exps]

    rng = random.Random(variedade.python_seed)
    chosen_idx = rng.choices(range(len(collector.solucoes)), weights=pesos, k=1)[0]
    chosen_sol = collector.solucoes[chosen_idx]
    chosen_inv = collector.inversoes[chosen_idx]
    chosen_dist = distancias[chosen_idx]
    chosen_hamming = hamming[chosen_idx]
    chosen_blocos = collector.blocos[chosen_idx]  # Fatia 4.A
    chosen_cargas_off = collector.cargas_off[chosen_idx]  # Fatia 4.E cargas

    # Fatia 4.E cargas: decodifica avisos `relaxado_carga` pós-solve.
    avisos_carga = _avisos_carga_por_treino(
        chosen_sol, chosen_blocos, chosen_cargas_off,
        md2["pares_violadores_por_treino"], md2["slot_por_sid"],
        n_treinos=len(md2["treinos"]),
    )

    return {
        "status": solver1.StatusName(status1),
        "viavel": True,
        "nivel_aluno": nivel_aluno,
        "seed": seed,
        "solve_time": time_p1 + time_p2,
        "inversoes_totais": chosen_inv,
        "h_r1_aplicadas": md2["h_r1_aplicadas"],
        "h_a1_aplicadas": md2["h_a1_aplicadas"],
        "h_a0_aplicadas": md2["h_a0_aplicadas"],
        "treinos": _decode_solucao(
            md2["treinos"], chosen_sol, chosen_blocos,
            slot_por_sid=md2["slot_por_sid"],
        ),
        "avisos_carga_por_treino": avisos_carga,
        "variedade": _meta_variedade(
            variedade,
            n=len(collector.solucoes),
            dist=chosen_dist,
            opt=optimal,
            lim=len(collector.solucoes) >= variedade.max_solucoes,
            t1=time_p1, t2=time_p2,
            hamming=chosen_hamming,
        ),
    }


def _meta_variedade(
    cfg: ConfigVariedade,
    n: int,
    dist: Optional[int],
    opt: Optional[int],
    lim: bool,
    t1: float,
    t2: float,
    hamming: Optional[int] = None,
) -> dict:
    """Empacota os metadados da enumeração no dict de retorno.

    `hamming` (Frente 2): Hamming ponderado por tier da solução escolhida
    em relação à 1ª enumerada (referência). None se alpha_tier=0.
    """
    return {
        "ativa": True,
        "slack": cfg.slack,
        "temperatura": cfg.temperatura,
        "max_solucoes": cfg.max_solucoes,
        "python_seed": cfg.python_seed,
        "alpha_tier": cfg.alpha_tier,
        "n_solucoes_enumeradas": n,
        "distancia_escolhida": dist,
        "optimal_value": opt,
        "enumeracao_limitada": lim,
        "hamming_ponderado_escolhido": hamming,
        "tempo_phase_1": t1,
        "tempo_phase_2": t2,
    }


def gerar_treino_csp(
    demandas: list[tuple[str, str, int]],
    banco: list[Exercicio],
    nivel_aluno: int,
    seed: int = 0,
    variedade: Optional[ConfigVariedade] = None,
    peso_aderencia: int = 0,
    peso_evitar_agonistas: int = 0,
    tamanho_preferido: int = 2,
    peso_tamanho_bloco: int = 0,
    travados: Optional[list[Exercicio]] = None,
    familias_proibidas: Optional[set[str]] = None,
    relaxar_familia: bool = False,
    cargas_config: Optional[dict[str, int]] = None,
    peso_cargas_off: int = 1000,
    peso_sa1: int = 0,
    peso_sa1_repet: int = 0,
    peso_sb5: int = 0,
    peso_sr1: int = 0,
) -> dict:
    """Wrapper retrocompatível — resolve 1 treino via `gerar_rotina_csp`.

    Devolve dict no formato antigo (chaves `grupos`, `ordem_global`,
    `inversoes` top-level). H-R1 vai disparar se a demanda atender o
    min_slots — pode mudar o resultado vs Fatia 1.

    `variedade` é repassado pra `gerar_rotina_csp` (Frente B Fatia 3).
    Quando ativo, a saída ganha a chave `variedade` com metadados da
    enumeração.

    `peso_aderencia` (Frente D Fatia 3): modulação da dimensão "Aderência
    ao Tier" do perfil do aluno. 0 (default) = sem efeito.

    `peso_evitar_agonistas` (Fatia 4.B): S-B1 distância funcional. 0
    (default) = sem efeito (preserva 4.A). >0 penaliza pares no mesmo
    bloco com mesmo grupo funcional (push/pull/quad/...).

    `tamanho_preferido` + `peso_tamanho_bloco` (Fatia 4.C): S-B4 tamanho
    preferido. peso=0 (default) sem efeito; peso>0 penaliza desvio do
    tamanho preferido por bloco em uso.

    `travados` (Fatia 4.D): lista de exercícios fixados pelo personal
    para este treino. None ou lista vazia preserva comportamento pré-4.D.

    `familias_proibidas` (Fatia 4.E): set de identificadores
    `_familia_cross(ex)` que NÃO podem aparecer (bloqueio hard cross-treino
    quando o adapter chama este wrapper pra regerar 1 treino isolado).
    None ou vazio preserva comportamento pré-4.E.

    `relaxar_familia` (Fatia 4.E): quando True E o solve estrito for
    inviável, motor refaz sem o filtro de família. Retorna chave
    `relaxados: list[str]` com nomes dos ex que violaram a regra original
    (caller propaga pra `Sessao.relaxados` + gera aviso `familia_repetida`).

    `cargas_config` + `peso_cargas_off` (Fatia 4.E cargas): H-cargas
    par-a-par no bloco. Dict `{"grip"/"lombar"/"core" → threshold int}`.
    Retorna chave `avisos_carga: list[dict]` com avisos `relaxado_carga`
    deste treino (vazio quando nenhum bloco precisou desligar o filtro).
    None ou dict vazio preserva comportamento pré-4.E cargas (filtro OFF).
    """
    travados_por_treino_arg = {0: list(travados)} if travados else None
    rotina = gerar_rotina_csp(
        [demandas], banco, nivel_aluno, seed,
        variedade=variedade,
        peso_aderencia=peso_aderencia,
        peso_evitar_agonistas=peso_evitar_agonistas,
        tamanho_preferido=tamanho_preferido,
        peso_tamanho_bloco=peso_tamanho_bloco,
        travados_por_treino=travados_por_treino_arg,
        familias_proibidas=familias_proibidas,
        relaxar_familia=relaxar_familia,
        cargas_config=cargas_config,
        peso_cargas_off=peso_cargas_off,
        peso_sa1=peso_sa1,
        peso_sa1_repet=peso_sa1_repet,
        peso_sb5=peso_sb5,
        peso_sr1=peso_sr1,
    )
    if not rotina["viavel"]:
        out = {
            "status": rotina["status"],
            "viavel": False,
            "nivel_aluno": nivel_aluno,
            "seed": seed,
            "solve_time": rotina["solve_time"],
            "inversoes": 0,
            "grupos": [],
            "ordem_global": [],
            "avisos_carga": [],
            "h_a1_aplicadas": rotina.get("h_a1_aplicadas", []),
            "h_a0_aplicadas": rotina.get("h_a0_aplicadas", []),
        }
        if "variedade" in rotina:
            out["variedade"] = rotina["variedade"]
        return out
    t0 = rotina["treinos"][0]
    out = {
        "status": rotina["status"],
        "viavel": True,
        "nivel_aluno": nivel_aluno,
        "seed": seed,
        "solve_time": rotina["solve_time"],
        "inversoes": rotina["inversoes_totais"],
        "grupos": t0["grupos"],
        "ordem_global": t0["ordem_global"],
        # Fatia 4.A: propaga blocos pra o adapter consumir.
        "blocos": t0.get("blocos", []),
        "h_r1_aplicadas": rotina["h_r1_aplicadas"],
        "h_a1_aplicadas": rotina.get("h_a1_aplicadas", []),
        # Micro-frente H-A0: propaga lista filtrada pelo treino=0 (gerar_treino_csp
        # serve a um único treino — entradas com `treino != 0` são desconsideradas
        # naturalmente porque rotina foi construída com 1 treino).
        "h_a0_aplicadas": rotina.get("h_a0_aplicadas", []),
        # Fatia 4.E: lista de nomes relaxados deste treino (treino_idx=0).
        "relaxados": rotina.get("relaxados_por_treino", {}).get(0, []),
        "relax_ativado": rotina.get("relax_ativado", False),
        # Fatia 4.E cargas: avisos deste treino (treino_idx=0).
        "avisos_carga": rotina.get("avisos_carga_por_treino", {}).get(0, []),
    }
    if "variedade" in rotina:
        out["variedade"] = rotina["variedade"]
    return out


# ---------------------------------------------------------------------------
# Output formatado pra leitura humana
# ---------------------------------------------------------------------------

def _tier_ordem_ok(resultado: dict) -> bool:
    """True se, em todo grupo, o tier é não-crescente na ordem dos slots."""
    for g in resultado["grupos"]:
        ranks = [_tier_rank(e) for e in g["exercicios"]]
        if any(ranks[k] < ranks[k + 1] for k in range(len(ranks) - 1)):
            return False
    return True


def _vagas_unicas_nao_acessorio(resultado: dict) -> tuple[bool, list[str]]:
    """Confere H-T4: toda vaga única de subregião com pool não-Acessório
    disponível tem tier != Acessório. Se o pool inteiro for Acessório
    (degradação aceita), a vaga é ignorada na validação."""
    ok = True
    detalhes = []
    for g in resultado["grupos"]:
        if not g["h_t4_aplicado"]:
            continue
        nivel, escopo, qtd = g["demanda"]
        if not g.get("h_t4_aplicado_efetivamente", False):
            # Degradação graceful: pool inteiro Acessório, vaga aceita Acessório.
            for e in g["exercicios"]:
                detalhes.append(f"{escopo}={e.tier} (pool 100% Acessório, OK)")
            continue
        for e in g["exercicios"]:
            t = e.tier
            detalhes.append(f"{escopo}={t}")
            if t == TIER_ACESSORIO:
                ok = False
    return ok, detalhes


def imprimir_resultado(resultado: dict, titulo: str = "") -> None:
    """Imprime uma rotina gerada no formato de leitura humana + validação."""
    cab = f"=== {titulo} ===" if titulo else "=== Rotina ==="
    print(cab)
    if not resultado["viavel"]:
        print(f"  INVIÁVEL (status={resultado['status']}) — pool insuficiente "
              f"pra atender as demandas no nível {resultado['nivel_aluno']}.")
        print()
        return

    i = 1
    for g in resultado["grupos"]:
        nivel, escopo, qtd = g["demanda"]
        for k, ex in enumerate(g["exercicios"]):
            tier = ex.tier or "?"
            marca = ""
            if g["h_t4_aplicado"] and k == 0:
                if not g.get("h_t4_aplicado_efetivamente", False):
                    marca = "   <- vaga única (degraded: pool 100% Acessório)"
                elif tier != TIER_ACESSORIO:
                    marca = "   <- vaga única OK"
                else:
                    marca = "   <- ⚠ vaga única ACESSÓRIO"
            print(f"{i}. [{tier:<13}] {ex.nome:<30} ({escopo}){marca}")
            i += 1

    tier_ok = _tier_ordem_ok(resultado)
    ht4_ok, ht4_det = _vagas_unicas_nao_acessorio(resultado)
    print()
    print("Validação:")
    print(f"  Tier-order respeitado?  {'SIM' if tier_ok else 'NÃO'}")
    print(f"  Vagas únicas != Acessório?  {'SIM' if ht4_ok else 'NÃO'}"
          + (f" ({', '.join(ht4_det)})" if ht4_det else " (nenhuma vaga única)"))
    print(f"  Inversões de tier (S-T1): {resultado['inversoes']}")
    h_r1 = resultado.get("h_r1_aplicadas", [])
    if h_r1:
        print(f"  H-R1 (cobertura cross-treino):")
        for a in h_r1:
            if a.get("degraded"):
                print(f"    ⚠ {a['subregiao']}/{a['eixo']}: degraded "
                      f"({a.get('motivo','sem candidato')})")
            else:
                print(f"    ✓ {a['subregiao']}/{a['eixo']}: "
                      f"{a['n_termos']} candidatos em {a['n_slots']} slots")
    print(f"  Tempo de solving: {resultado['solve_time']:.4f}s")
    print()


def imprimir_rotina_resultado(rotina: dict, titulo: str = "") -> None:
    """Imprime uma ROTINA (N treinos) com saída humana + validação."""
    cab = f"=== {titulo} ===" if titulo else "=== Rotina ==="
    print(cab)
    if not rotina["viavel"]:
        print(f"  INVIÁVEL (status={rotina['status']}) — pool insuficiente.")
        print()
        return
    for t_idx, treino in enumerate(rotina["treinos"], start=1):
        print(f"--- Treino {t_idx} ---")
        i = 1
        for g in treino["grupos"]:
            nivel, escopo, qtd = g["demanda"]
            for k, ex in enumerate(g["exercicios"]):
                tier = ex.tier or "?"
                marca = ""
                if g["h_t4_aplicado"] and k == 0:
                    if not g.get("h_t4_aplicado_efetivamente", False):
                        marca = "   <- vaga única (degraded: pool 100% Acessório)"
                    elif tier != TIER_ACESSORIO:
                        marca = "   <- vaga única OK"
                    else:
                        marca = "   <- ⚠ vaga única ACESSÓRIO"
                print(f"  {i}. [{tier:<13}] {ex.nome:<30} ({escopo}){marca}")
                i += 1
    print()
    print("Validação:")
    print(f"  Inversões totais (S-T1 cross-treino): {rotina['inversoes_totais']}")
    h_r1 = rotina.get("h_r1_aplicadas", [])
    if h_r1:
        print(f"  H-R1 (cobertura cross-treino):")
        for a in h_r1:
            if a.get("degraded"):
                print(f"    ⚠ {a['subregiao']}/{a['eixo']}: degraded "
                      f"({a.get('motivo','sem candidato')})")
            else:
                print(f"    ✓ {a['subregiao']}/{a['eixo']}: "
                      f"{a['n_termos']} candidatos em {a['n_slots']} slots")
    else:
        print("  H-R1: nenhuma regra ativa (subregiões com < min_slots)")
    print(f"  Tempo de solving: {rotina['solve_time']:.4f}s")
    print()


# ---------------------------------------------------------------------------
# Script de teste standalone
# ---------------------------------------------------------------------------

# Config A — rotina padrão com vagas únicas (testa H-T4 em ombro + perna_post)
DEMANDAS_A: list[tuple[str, str, int]] = [
    ("subregiao", "peito", 2),
    ("subregiao", "costas", 2),
    ("subregiao", "ombro", 1),              # vaga única — H-T4 dispara
    ("subregiao", "perna_anterior", 2),
    ("subregiao", "perna_posterior", 1),    # vaga única — H-T4 dispara
]

# Config B — inclui knee_extension explicitamente (testa pool de 1 + padrão)
DEMANDAS_B: list[tuple[str, str, int]] = [
    ("subregiao", "peito", 2),
    ("padrao", "knee_extension", 1),        # padrão explícito: só Cadeira Extensora
    ("subregiao", "perna_posterior", 1),
]


def _main() -> None:
    # Garante que stdout aceite acentos/setas no Windows (cp1252 default quebra).
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    banco = carregar_banco_ativo()
    inativos_esperados = {"Box Jump", "Air Bike Sprint", "Air Bike Steady"}
    nomes_no_pool = {e.nome for e in banco}
    print(f"Banco ativo carregado: {len(banco)} exercícios")
    vazou = inativos_esperados & nomes_no_pool
    print(f"Filtro ativo=True: "
          + ("OK (0 inativos no pool — Box Jump, Air Bike Sprint/Steady ausentes)"
             if not vazou else f"⚠ VAZOU: {vazou}"))
    print()

    # ── Config A — 5 rodadas com seeds diferentes ───────────────────────────
    print("#" * 70)
    print("# Config A — nível 3 (avançado), 5 rodadas (seeds 42..46)")
    print("#" * 70)
    print()
    assinaturas = []
    for n, seed in enumerate([42, 43, 44, 45, 46], start=1):
        r = gerar_treino_csp(DEMANDAS_A, banco, nivel_aluno=3, seed=seed)
        imprimir_resultado(r, f"Rotina {n} (Config A, nível 3, seed={seed})")
        assinaturas.append(tuple(e.nome for e in r["ordem_global"]))
    distintas = len(set(assinaturas))
    print(f">> Variedade entre as 5 rotinas: {distintas} distintas de 5 "
          f"({'solver explora soluções' if distintas > 1 else 'solver determinístico — mesma solução'}).")
    print()

    # ── Config B — 1 rodada (knee_extension) ────────────────────────────────
    print("#" * 70)
    print("# Config B — nível 3, knee_extension explícito (pool de 1)")
    print("#" * 70)
    print()
    rb = gerar_treino_csp(DEMANDAS_B, banco, nivel_aluno=3, seed=42)
    imprimir_resultado(rb, "Rotina (Config B, nível 3, seed=42)")
    nomes_b = [e.nome for g in rb["grupos"] for e in g["exercicios"]]
    print(f">> Cadeira Extensora presente? "
          f"{'SIM' if any('Extensora' in n for n in nomes_b) else 'NÃO'}")
    print()

    # ── Config C — graceful degradation H-T4 em vaga única de core ──────────
    print("#" * 70)
    print("# Config C — core_isometrico em vaga única (graceful degradation H-T4)")
    print("# Pool 100% Acessório pós-curadoria Parte 1: vaga única DEVE aceitar")
    print("# Acessório em vez de virar INFEASIBLE.")
    print("#" * 70)
    print()
    DEMANDAS_C = [("subregiao", "core_isometrico", 1)]
    rc = gerar_treino_csp(DEMANDAS_C, banco, nivel_aluno=3, seed=42)
    imprimir_resultado(rc, "Rotina (Config C, nível 3, seed=42)")
    print(f">> Viável? {'SIM' if rc['viavel'] else 'NÃO'}")
    if rc["viavel"]:
        ex = rc["ordem_global"][0]
        print(f">> Exercício escolhido: {ex.nome} (tier={ex.tier!r})")
        print(f">> H-T4 aplicado efetivamente? "
              f"{rc['grupos'][0].get('h_t4_aplicado_efetivamente')} "
              f"(esperado False — pool 100% Acessório).")
    print()

    # ── Config D — rotina de 2 treinos: exercita H-R1 cross-treino ──────────
    print("#" * 70)
    print("# Config D — ROTINA 2 treinos × costas(1) cada. Total 2 slots de")
    print("# costas na rotina inteira (1 em cada treino). H-R1 deve forçar")
    print("# vertical+horizontal compostos distribuídos cross-treino.")
    print("#" * 70)
    print()
    DEMANDAS_D_T1 = [("subregiao", "costas", 1), ("subregiao", "peito", 1)]
    DEMANDAS_D_T2 = [("subregiao", "costas", 1), ("subregiao", "peito", 1)]
    rd = gerar_rotina_csp(
        [DEMANDAS_D_T1, DEMANDAS_D_T2],
        banco, nivel_aluno=3, seed=42,
    )
    imprimir_rotina_resultado(rd, "Rotina D — 2 treinos × costas(1)+peito(1)")
    # Validação manual: cobertura cross-treino de costas
    todos_costas = [
        ex for tr in rd["treinos"] for g in tr["grupos"]
        for ex in g["exercicios"] if ex.subregiao == "costas"
    ]
    has_puxada = any(e.padrao == "puxadas" and e.purpose == "compound" for e in todos_costas)
    has_remada = any(e.padrao == "remadas" and e.purpose == "compound" for e in todos_costas)
    print(f">> Cobertura costas cross-treino: vertical={'SIM' if has_puxada else 'NÃO'}, "
          f"horizontal={'SIM' if has_remada else 'NÃO'}")
    # Validação AllDifferent cross-treino
    todos_nomes = [
        ex.nome for tr in rd["treinos"] for g in tr["grupos"]
        for ex in g["exercicios"]
    ]
    print(f">> AllDifferent cross-treino? "
          f"{'SIM' if len(set(todos_nomes)) == len(todos_nomes) else 'NÃO (repetiu!)'} "
          f"({len(todos_nomes)} ex no total)")
    print()

    # ── Bônus — Config A no nível 1, mostrando encolhimento de pool ──────────
    print("#" * 70)
    print("# Bônus — Config A no nível 1 (iniciante): filtro de complexidade")
    print("#" * 70)
    print()
    pool_n3 = filtrar_pool_por_nivel(banco, 3)
    pool_n1 = filtrar_pool_por_nivel(banco, 1)
    print(f"Pool global: nível 3 = {len(pool_n3)} exercícios → nível 1 = {len(pool_n1)} "
          f"(−{len(pool_n3) - len(pool_n1)} de complexidade > 2)")
    sumidos = sorted({e.nome for e in pool_n3} - {e.nome for e in pool_n1})
    print(f"Exemplos que somem no nível 1 ({len(sumidos)} no total): {sumidos[:8]}")
    print()
    r1 = gerar_treino_csp(DEMANDAS_A, banco, nivel_aluno=1, seed=42)
    imprimir_resultado(r1, "Rotina (Config A, nível 1, seed=42)")


if __name__ == "__main__":
    _main()
