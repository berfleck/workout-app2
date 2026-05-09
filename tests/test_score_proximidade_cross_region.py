"""Cenário 5.1 da Fase 3 / E.2 — sanity check escopo cross-region.

Valida empiricamente a propriedade de escopo descrita na Seção 1.5 do
`docs/refatoracao/dimensoes_proximidade.md`:

- **`pegada`, `plano_corporal`, `equipamento_grupo`**: aplicam **same-
  subregião only**. Cross-region (e cross-subregião) → penalty 0.
- **`familia_estrita` INTER**: aplica **universal** (cross-subregião).
  Permanece o ÚNICO soft INTER que dispara cross-region — é
  intencional, não violação de escopo.
- **`variante_pontual` INTER**: cross-family + same-subregião only.

Cenário 5.1 estava listado em `docs/refatoracao/dimensoes_proximidade.md`
Seção 8.5 como "movido pra E.2 — só vira testável quando penalties soft
estiverem implementadas (post-D2)". Pós-Fase 7.4 é testável; Fase 7.5
fecha como pytest determinístico (decisão Sessão 12 — alternativa ao
Monte Carlo do harness, mais aderente à natureza determinística do
sanity check).

Pares cross-region escolhidos pra cobrir as 4 regiões com tags reais
do banco mockado (peito, costas, perna_anterior, perna_posterior, core,
panturrilha) — pegada/plano/equipamento_grupo válidos em cada lado.
"""
from __future__ import annotations

import pytest

from gerador_treino import (
    Exercicio,
    _score_proximidade,
)
from pesos_proximidade import PESOS_DEFAULT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ex(
    nome: str,
    *,
    regiao: str,
    subregiao: str,
    variacao_de: str | None = None,
    pegada: str | None = None,
    plano_corporal: str | None = None,
    equipamento_grupo: str | None = None,
    variante_pontual: bool = False,
) -> Exercicio:
    """Constrói Exercicio sintético com tags da Etapa 6/7. Defaults inócuos
    pros campos não usados pelo `_score_proximidade`.
    """
    return Exercicio(
        nome=nome,
        variacao_de=variacao_de,
        eq_primario="",
        eq_secundario=None,
        regiao=regiao,
        subregiao=subregiao,
        padrao="",
        purpose="isolation",
        unilateral="bilateral",
        complexidade=1,
        fadiga=2,
        circuito="não",
        similaridade="",
        musculo_primario="",
        obs=None,
        variante_pontual=variante_pontual,
        pegada=pegada,
        plano_corporal=plano_corporal,
        equipamento_grupo=equipamento_grupo,
    )


# Pares cross-region "patológicos" — tags propositalmente IGUAIS pra forçar
# match em pegada/plano/equipamento_grupo. Se o escopo same-subregião não
# fosse respeitado, o score INTRA dispararia. Como respeita, score = 0.
PARES_CROSS_REGION_TAGS_IGUAIS = [
    # peito (upper) × perna_anterior (lower)
    pytest.param(
        _ex("Supino Reto Barra", regiao="upper", subregiao="peito",
            variacao_de="Supino Reto", pegada="pronada",
            plano_corporal="reto", equipamento_grupo="barra"),
        _ex("Agachamento Livre", regiao="lower", subregiao="perna_anterior",
            variacao_de="Agachamento", pegada="pronada",
            plano_corporal="reto", equipamento_grupo="barra"),
        id="peito_x_perna_anterior",
    ),
    # costas (upper) × core_dinamico (core)
    pytest.param(
        _ex("Remada Curvada Barra", regiao="upper", subregiao="costas",
            variacao_de="Remada Curvada", pegada="pronada",
            plano_corporal="curvada", equipamento_grupo="barra"),
        _ex("V-Up", regiao="core", subregiao="core_dinamico",
            variacao_de="V-Up", pegada="pronada",
            plano_corporal="curvada", equipamento_grupo="barra"),
        id="costas_x_core_dinamico",
    ),
    # ombro (upper) × panturrilha (lower)
    pytest.param(
        _ex("Desenvolvimento Halteres", regiao="upper", subregiao="ombro",
            variacao_de="Desenvolvimento", pegada="neutra",
            plano_corporal="em_pe", equipamento_grupo="halter"),
        _ex("Panturrilha em Pé", regiao="lower", subregiao="panturrilha",
            variacao_de="Panturrilha", pegada="neutra",
            plano_corporal="em_pe", equipamento_grupo="halter"),
        id="ombro_x_panturrilha",
    ),
    # bracos (upper) × perna_posterior (lower)
    pytest.param(
        _ex("Tríceps Pulley", regiao="upper", subregiao="bracos",
            variacao_de="Tríceps", pegada="pronada",
            plano_corporal="em_pe", equipamento_grupo="polia"),
        _ex("Stiff Halteres", regiao="lower", subregiao="perna_posterior",
            variacao_de="Stiff", pegada="pronada",
            plano_corporal="em_pe", equipamento_grupo="halter"),
        id="bracos_x_perna_posterior",
    ),
    # peito (upper) × core_isometrico (core)
    pytest.param(
        _ex("Apoio", regiao="upper", subregiao="peito",
            variacao_de="Apoio", pegada="pronada",
            plano_corporal="reto", equipamento_grupo="corporal"),
        _ex("Prancha Frontal", regiao="core", subregiao="core_isometrico",
            variacao_de="Prancha", pegada="pronada",
            plano_corporal="reto", equipamento_grupo="corporal"),
        id="peito_x_core_isometrico",
    ),
]


# ---------------------------------------------------------------------------
# 5.1.a — INTRA cross-region não dispara
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cand,outro", PARES_CROSS_REGION_TAGS_IGUAIS)
def test_intra_cross_region_score_zero(cand: Exercicio,
                                        outro: Exercicio) -> None:
    """INTRA: pegada/plano/equipamento_grupo são same-subregião only
    (Seção 1.5). Cross-region implica cross-subregião — score = 0
    mesmo com tags iguais nos 3 dims.
    """
    score = _score_proximidade(cand, [outro], "intra", PESOS_DEFAULT)
    assert score == 0.0, (
        f"INTRA cross-region disparou ({score}) — escopo same-subregião "
        f"violado. cand={cand.subregiao}, outro={outro.subregiao}"
    )


# ---------------------------------------------------------------------------
# 5.1.b — INTER cross-region: dims same-subregião não disparam
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cand,outro", PARES_CROSS_REGION_TAGS_IGUAIS)
def test_inter_cross_region_dims_same_subregiao_score_zero(
    cand: Exercicio, outro: Exercicio
) -> None:
    """INTER: pegada/plano/equipamento_grupo + variante_pontual são
    same-subregião only (Seção 1.5). Cross-region → essas dims = 0.
    Famílias dos pares são DIFERENTES por construção, então familia_estrita
    INTER (única dim universal cross-subregião) também não dispara.
    """
    assert cand.variacao_de != outro.variacao_de, (
        "Pré-condição do teste: famílias devem diferir pra isolar dims "
        "same-subregião"
    )
    score = _score_proximidade(cand, [outro], "inter", PESOS_DEFAULT)
    assert score == 0.0, (
        f"INTER cross-region (famílias dif) disparou ({score}) — escopo "
        f"same-subregião violado em pegada/plano/equipamento_grupo ou "
        f"variante_pontual. cand={cand.subregiao}, outro={outro.subregiao}"
    )


# ---------------------------------------------------------------------------
# 5.1.c — INTER família estrita: universal cross-region (intencional)
#
# Documenta que família INTER É a exceção ao escopo same-subregião. Não é
# bug — Seção 1.5: "Família estrita é o único hard filter realmente global.
# Se 2 exercícios têm a mesma família (improvável entre subregiões
# diferentes, mas hipotético), bloqueia em qualquer caso." Caminho A da
# Fase 7.4 migrou família INTER de hard pra soft, mas o ESCOPO permaneceu
# universal.
# ---------------------------------------------------------------------------

def test_inter_familia_estrita_universal_cross_region() -> None:
    """Família INTER é universal (Seção 1.5) — caso patológico cross-region
    com mesma família dispara penalty. Sanity de que esse comportamento
    é intencional, não regressão de escopo.
    """
    cand = _ex("Supino Reto Halteres", regiao="upper", subregiao="peito",
               variacao_de="Supino Reto",
               pegada="neutra", plano_corporal="reto",
               equipamento_grupo="halter")
    # Mesma família "Supino Reto" mas em subregião diferente — caso
    # hipotético improvável no banco real, mas válido pra isolar a dim.
    outro = _ex("Stiff Halteres Familia Supino Reto",
                regiao="lower", subregiao="perna_posterior",
                variacao_de="Supino Reto",
                pegada="neutra", plano_corporal="em_pe",
                equipamento_grupo="halter")
    score = _score_proximidade(cand, [outro], "inter", PESOS_DEFAULT)
    # peso INTER família = soft_alto × 0.8 = -50 × 0.8 = -40
    assert score < 0, (
        f"Família INTER deveria disparar cross-region (universal — "
        f"Seção 1.5). Score observado: {score}"
    )


# ---------------------------------------------------------------------------
# 5.1.d — HISTÓRICO match cross-region: granularidade é nome/família,
# não subregião (intencional — D3.3)
# ---------------------------------------------------------------------------

def test_historico_match_familia_independente_de_subregiao() -> None:
    """HISTÓRICO branch (D3.3) é match em SET de nomes/famílias da R-1 —
    não tem escopo cross-region. Sanity de que esse comportamento é
    intencional: granularidade nome OR família, penalty única.
    """
    cand = _ex("Tríceps Pulley", regiao="upper", subregiao="bracos",
               variacao_de="Tríceps")
    # R-1 com exercício de outra região com a mesma família — match dispara
    historico = [
        _ex("Tríceps Frances Halter", regiao="upper", subregiao="bracos",
            variacao_de="Tríceps"),
    ]
    score = _score_proximidade(cand, historico, "historico", PESOS_DEFAULT)
    assert score < 0, (
        f"HIST deveria disparar quando família coincide (D3.3). "
        f"Score observado: {score}"
    )


def test_historico_sem_match_score_zero() -> None:
    """HIST sem match nome nem família → score = 0, mesmo pra alocados
    em qualquer região/subregião. Sanity simétrica do 5.1.d.
    """
    cand = _ex("Supino Reto Barra", regiao="upper", subregiao="peito",
               variacao_de="Supino Reto")
    # R-1 com exercícios totalmente diferentes (nome e família)
    historico = [
        _ex("Stiff Halteres", regiao="lower", subregiao="perna_posterior",
            variacao_de="Stiff"),
        _ex("Agachamento Livre", regiao="lower", subregiao="perna_anterior",
            variacao_de="Agachamento"),
    ]
    score = _score_proximidade(cand, historico, "historico", PESOS_DEFAULT)
    assert score == 0.0, (
        f"HIST sem match nome/família deveria ser 0; observado: {score}"
    )
