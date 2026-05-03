"""Testes da função pura `_score_pareamento` (Etapa 5).

Score linear de quão bom é parear um candidato com o bloco já montado.
Componentes aditivos definidos em `PESOS_SCORE_PAREAMENTO`. Estes testes
isolam cada componente com Exercicios sintéticos e validam o caso clínico
real (V-Up Uni + Tríceps Uni) com o banco.
"""
from __future__ import annotations

import pytest

from gerador_treino import (
    Exercicio,
    GRUPO_MUSCULAR_PADRAO,
    PESOS_SCORE_PAREAMENTO,
    SOFTMAX_TEMPERATURA,
    SOFTMAX_TOP_K,
    _score_pareamento,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ex(
    nome: str,
    *,
    regiao: str = "upper",
    padrao: str = "empurrar_compostos",
    purpose: str = "isolation",
    unilateral: str = "bilateral",
    fadiga: int = 2,
) -> Exercicio:
    """Constrói um Exercicio sintético com defaults inócuos."""
    return Exercicio(
        nome=nome,
        variacao_de=None,
        eq_primario="",
        eq_secundario=None,
        regiao=regiao,
        subregiao="",  # irrelevante pra _score_pareamento
        padrao=padrao,
        purpose=purpose,
        unilateral=unilateral,
        complexidade=1,
        fadiga=fadiga,
        circuito="não",
        similaridade="",
        musculo_primario="",
        obs=None,
    )


def _por_nome(banco, nome: str) -> Exercicio:
    for e in banco:
        if e.nome == nome:
            return e
    raise KeyError(f"exercício '{nome}' não encontrado no banco")


# ---------------------------------------------------------------------------
# Constantes do módulo
# ---------------------------------------------------------------------------

def test_pesos_score_pareamento_tem_todas_as_chaves():
    chaves_esperadas = {
        "regiao_diff", "padrao_diff", "nao_agonista", "composto",
        "anti_uni_mesmo_grupo", "anti_uni_diff_grupo",
    }
    assert set(PESOS_SCORE_PAREAMENTO.keys()) == chaves_esperadas


def test_pesos_seguem_hierarquia_de_ordem_de_grandeza():
    """regiao_diff >> padrao_diff >> nao_agonista > composto.
    Hierarquia evita compensações cruzadas (não dá pra somar 10x não-agonista
    pra superar 1x região diferente)."""
    p = PESOS_SCORE_PAREAMENTO
    assert p["regiao_diff"] >= 10 * p["padrao_diff"]
    assert p["padrao_diff"] >= 2 * p["nao_agonista"]
    assert p["nao_agonista"] >= p["composto"]


def test_anti_uni_mesmo_grupo_eh_mais_severo_que_diff_grupo():
    p = PESOS_SCORE_PAREAMENTO
    assert p["anti_uni_mesmo_grupo"] < p["anti_uni_diff_grupo"] < 0


def test_softmax_constantes_existem():
    assert SOFTMAX_TOP_K == 3
    assert SOFTMAX_TEMPERATURA == 200.0


# ---------------------------------------------------------------------------
# Componentes isolados
# ---------------------------------------------------------------------------

def test_bloco_vazio_aplica_componentes_geo_max():
    """Edge case: bloco vazio. Como candidato.regiao/padrao não estão em
    set vazio, recebe +regiao_diff +padrao_diff. Não acontece em produção
    (bloco sempre tem âncora antes de buscar candidato), mas o
    comportamento é defensável e documentado aqui."""
    cand = _ex("X", regiao="upper", padrao="empurrar_compostos", purpose="isolation")
    # +1000 (regiao não está em {}) +100 (padrao não está em {}) +0 (isolation)
    assert _score_pareamento(cand, [], evitar_agonistas=False) == 1100


def test_regiao_diferente_soma_1000():
    ancora = _ex("A", regiao="upper", padrao="empurrar_compostos")
    cand = _ex("C", regiao="lower", padrao="squat_bilateral")
    score = _score_pareamento(cand, [ancora], evitar_agonistas=False)
    # +1000 (regiao_diff) +100 (padrao_diff) +0 (isolation default)
    assert score == 1100


def test_padrao_diferente_mesma_regiao_soma_100():
    ancora = _ex("A", regiao="upper", padrao="empurrar_compostos")
    cand = _ex("C", regiao="upper", padrao="remadas")
    score = _score_pareamento(cand, [ancora], evitar_agonistas=False)
    assert score == 100


def test_mesma_regiao_e_mesmo_padrao_soma_zero():
    ancora = _ex("A", regiao="upper", padrao="empurrar_compostos")
    cand = _ex("C", regiao="upper", padrao="empurrar_compostos")
    score = _score_pareamento(cand, [ancora], evitar_agonistas=False)
    assert score == 0


def test_composto_soma_25():
    ancora = _ex("A", regiao="upper", padrao="empurrar_compostos")
    cand = _ex("C", regiao="upper", padrao="empurrar_compostos", purpose="compound")
    assert _score_pareamento(cand, [ancora], evitar_agonistas=False) == 25


def test_purpose_explosive_tambem_conta_como_composto():
    """`_eh_composto` aceita compound + explosive."""
    ancora = _ex("A", regiao="upper", padrao="empurrar_compostos")
    cand = _ex("C", regiao="upper", padrao="empurrar_compostos", purpose="explosive")
    assert _score_pareamento(cand, [ancora], evitar_agonistas=False) == 25


# ---------------------------------------------------------------------------
# Não-agonista (depende do flag)
# ---------------------------------------------------------------------------

def test_nao_agonista_soma_50_quando_flag_ativa():
    # empurrar_compostos = "push", remadas = "pull" → não-agonistas
    ancora = _ex("A", regiao="upper", padrao="empurrar_compostos")
    cand = _ex("C", regiao="upper", padrao="remadas")
    score = _score_pareamento(cand, [ancora], evitar_agonistas=True)
    # +100 (padrao_diff) +50 (não-agonista)
    assert score == 150


def test_nao_agonista_zero_quando_flag_desativada():
    ancora = _ex("A", regiao="upper", padrao="empurrar_compostos")
    cand = _ex("C", regiao="upper", padrao="remadas")
    score = _score_pareamento(cand, [ancora], evitar_agonistas=False)
    # +100 (padrao_diff) apenas
    assert score == 100


def test_agonista_nao_recebe_50_mesmo_com_flag():
    # empurrar_compostos e ombro_composto são ambos "push"
    ancora = _ex("A", regiao="upper", padrao="empurrar_compostos")
    cand = _ex("C", regiao="upper", padrao="ombro_composto")
    score = _score_pareamento(cand, [ancora], evitar_agonistas=True)
    # +100 (padrao_diff) apenas, sem bonus de não-agonista
    assert score == 100


# ---------------------------------------------------------------------------
# Anti-unilateral refinado (sensível a contraste muscular)
# ---------------------------------------------------------------------------

def test_uni_uni_mesmo_grupo_penalty_75():
    # Ambos squat_unilateral → grupo "quad"
    ancora = _ex("A", regiao="lower", padrao="squat_unilateral", unilateral="unilateral")
    cand = _ex("C", regiao="lower", padrao="squat_unilateral", unilateral="unilateral")
    score = _score_pareamento(cand, [ancora], evitar_agonistas=False)
    # +0 (mesmo regiao, mesmo padrao) -75 (anti_uni_mesmo_grupo)
    assert score == -75


def test_uni_uni_grupos_diferentes_penalty_10():
    # core_dinamico (grupo core) vs triceps (grupo push), regiões diferentes
    ancora = _ex("A", regiao="core", padrao="core_dinamico", unilateral="unilateral")
    cand = _ex("C", regiao="upper", padrao="triceps", unilateral="unilateral")
    score = _score_pareamento(cand, [ancora], evitar_agonistas=False)
    # +1000 (regiao_diff) +100 (padrao_diff) -10 (anti_uni_diff_grupo)
    assert score == 1090


def test_bilateral_candidato_nao_recebe_penalty_anti_uni():
    ancora = _ex("A", regiao="core", padrao="core_dinamico", unilateral="unilateral")
    cand = _ex("C", regiao="core", padrao="core_isometrico", unilateral="bilateral")
    score = _score_pareamento(cand, [ancora], evitar_agonistas=False)
    # +0 (mesma regiao) +100 (padrao_diff) +0 (bilateral, sem penalty)
    assert score == 100


def test_uni_candidato_com_bloco_so_de_bilaterais_zero_penalty():
    ancora = _ex("A", regiao="upper", padrao="empurrar_compostos", unilateral="bilateral")
    cand = _ex("C", regiao="lower", padrao="squat_unilateral", unilateral="unilateral")
    score = _score_pareamento(cand, [ancora], evitar_agonistas=False)
    # +1000 +100, sem penalty (não há outro uni no bloco)
    assert score == 1100


def test_anti_uni_acumula_em_bloco_de_3():
    """Em bloco de 3 com 2 unilaterais já presentes (mesmo grupo), o terceiro
    candidato unilateral mesmo grupo recebe 2× -75 = -150."""
    ancora1 = _ex("A1", regiao="lower", padrao="squat_unilateral", unilateral="unilateral")
    ancora2 = _ex("A2", regiao="lower", padrao="squat_unilateral", unilateral="unilateral")
    cand = _ex("C", regiao="lower", padrao="squat_unilateral", unilateral="unilateral")
    score = _score_pareamento(cand, [ancora1, ancora2], evitar_agonistas=False)
    # +0 (mesma regiao) +0 (mesmo padrao) -75 -75 = -150
    assert score == -150


# ---------------------------------------------------------------------------
# Aditividade (todos os componentes ligados ao mesmo tempo)
# ---------------------------------------------------------------------------

def test_p1_ideal_aditividade_completa():
    """P1 da cascata original: regiao_diff + padrao_diff + não-agonista + composto.
    1000 + 100 + 50 + 25 = 1175."""
    ancora = _ex("A", regiao="upper", padrao="empurrar_compostos")
    cand = _ex(
        "C", regiao="lower", padrao="squat_bilateral",
        purpose="compound",
    )
    score = _score_pareamento(cand, [ancora], evitar_agonistas=True)
    assert score == 1175


def test_composto_vence_isolado_quando_resto_iguais():
    """Garantia que o composto-primeiro implícito do `ordenar_compostos_primeiro`
    é coberto pelo peso +25. Mesmo padrão, mesma região, só muda purpose."""
    ancora = _ex("A", regiao="upper", padrao="empurrar_compostos")
    cand_comp = _ex("Cc", regiao="upper", padrao="remadas", purpose="compound")
    cand_iso  = _ex("Ci", regiao="upper", padrao="remadas", purpose="isolation")
    s_comp = _score_pareamento(cand_comp, [ancora], evitar_agonistas=False)
    s_iso  = _score_pareamento(cand_iso,  [ancora], evitar_agonistas=False)
    assert s_comp == s_iso + 25


# ---------------------------------------------------------------------------
# Caso clínico real — V-Up Uni + Tríceps Uni vs Hollow Hold (problema 6)
# ---------------------------------------------------------------------------

def test_caso_v_up_uni_triceps_uni_vence_hollow_hold(banco):
    """Cenário real do `memoria_projeto.md` problema 6:
    âncora V-Up Unilateral → entre Tríceps Unilateral Polia (regiao diff,
    uni-uni cross-group) e Hollow Hold (mesma regiao, bilateral), o
    Tríceps deve vencer por larga margem."""
    nomes_alvo = {"V-Up Unilateral", "Tríceps Unilateral Polia", "Hollow Hold"}
    achados = {e.nome: e for e in banco if e.nome in nomes_alvo}
    if set(achados.keys()) != nomes_alvo:
        pytest.skip(f"banco sem todos: {nomes_alvo} (achou {set(achados.keys())})")

    ancora = achados["V-Up Unilateral"]
    triceps = achados["Tríceps Unilateral Polia"]
    hollow  = achados["Hollow Hold"]

    s_triceps = _score_pareamento(triceps, [ancora], evitar_agonistas=True)
    s_hollow  = _score_pareamento(hollow,  [ancora], evitar_agonistas=True)

    # Tríceps Uni: regiao_diff (1000) + padrao_diff (100) + não-agonista (50)
    # − anti_uni_diff_grupo (10) [+ composto se purpose for compound]
    # Hollow Hold: mesmo regiao + mesmo padrão (ambos core_dinamico/isometrico
    # depende da curadoria) + não-agonista talvez +50 + bilateral (sem penalty)
    assert s_triceps > s_hollow + 500, (
        f"Tríceps Uni ({s_triceps}) deveria vencer Hollow Hold ({s_hollow}) "
        "por mais de 500 pontos — caso V-Up Uni"
    )
