"""Verifica predominância empírica de Pullover (família de puxadas) e Pallof Press
(núcleo) numa rotina típica de 2 treinos `upper(3) + lower(3) + core(2)`.

Contexto histórico (Seção 8.15.14 + log
`sessao_2026-05-18_cadastros_e_tiebreaker.md`): Pullover dominava puxadas
até o fix `feat/cadastros-pullover-mitigation` (tag `plano=reto` nos Apoios
+ tiebreaker aleatório em `_selecionar_cand_score_aware` + 3 cadastros
novos em puxadas). Pallof Press é o único exercício de `rotacao_tronco`
até a Fase 4 cadastrar Russian Twist; o cycling `flexao_tronco/lateral/
quadril/rotacao_tronco` em `core_isometrico` torna ele potencialmente
sobre-representado.

O teste é *regression guard*: cravar thresholds bem acima dos valores
atuais mas bem abaixo da zona de regressão (Pullover ~60% pré-fix,
Pallof ~25% num cenário só de rotacao_tronco).
"""
from __future__ import annotations

import random
from collections import Counter

import pytest

from gerador_treino import gerar_multiplos_treinos


N_ROTINAS = 300  # granularidade ~0.3pp em pct slots, ~0.5pp em pct rotinas

CFG = {
    "demandas": [
        ("regiao", "upper", 3),
        ("regiao", "lower", 3),
        ("regiao", "core", 2),
    ]
}


def _coletar_exs(sessoes):
    """Devolve a lista achatada de Exercicio de uma rotina."""
    return [
        ex
        for sessao in sessoes
        for bloco in sessao.blocos
        for ex in (bloco.ex1, bloco.ex2, bloco.ex3)
        if ex is not None
    ]


@pytest.fixture(scope="module")
def amostragem(banco):
    """Gera N_ROTINAS rotinas seed=0..N-1 e devolve estatísticas agregadas.

    Module-scoped pra rodar a amostragem uma única vez e compartilhar entre
    os asserts de Pullover e Pallof Press (cada chamada de
    `gerar_multiplos_treinos` é o custo dominante).
    """
    puxadas_familia = Counter()
    core_nome = Counter()
    rotinas_com_pullover = 0
    rotinas_com_pallof = 0

    for seed in range(N_ROTINAS):
        random.seed(seed)
        sessoes = gerar_multiplos_treinos(banco, [CFG, CFG], relaxar_familia=True)
        exs = _coletar_exs(sessoes)
        nomes_rotina = {ex.nome for ex in exs}

        for ex in exs:
            if ex.padrao == "puxadas":
                puxadas_familia[ex.variacao_de or ex.nome] += 1
            if ex.regiao == "core":
                core_nome[ex.nome] += 1

        if any(nome.startswith("Pullover") for nome in nomes_rotina):
            rotinas_com_pullover += 1
        if "Pallof Press" in nomes_rotina:
            rotinas_com_pallof += 1

    resultado = {
        "puxadas_familia": puxadas_familia,
        "core_nome": core_nome,
        "rotinas_com_pullover": rotinas_com_pullover,
        "rotinas_com_pallof": rotinas_com_pallof,
        "total_puxadas_slots": sum(puxadas_familia.values()),
        "total_core_slots": sum(core_nome.values()),
    }

    # Relatório (visível com `pytest -s`). Asserts abaixo travam regressão;
    # esse bloco só dá visibilidade pro número atual.
    total_pux = resultado["total_puxadas_slots"]
    total_core = resultado["total_core_slots"]
    print()
    print(f"=== Predominância em {N_ROTINAS} rotinas (upper(3)+lower(3)+core(2) × 2T) ===")
    print()
    print(f"Puxadas — {total_pux} slots totais")
    for fam, c in puxadas_familia.most_common():
        print(f"  {fam:10s} {c:4d}  ({c/total_pux*100:5.1f}%)")
    print(f"  Rotinas com >=1 Pullover: "
          f"{rotinas_com_pullover}/{N_ROTINAS} "
          f"({rotinas_com_pullover/N_ROTINAS*100:.1f}%)")
    print()
    print(f"Core — {total_core} slots totais — top 8 abdominais:")
    for nome, c in core_nome.most_common(8):
        marca = "  <- Pallof" if nome == "Pallof Press" else ""
        print(f"  {nome:25s} {c:4d}  ({c/total_core*100:5.1f}%){marca}")
    if "Pallof Press" not in dict(core_nome.most_common(8)):
        c = core_nome.get("Pallof Press", 0)
        print(f"  {'Pallof Press':25s} {c:4d}  ({c/total_core*100:5.1f}%)  <- Pallof")
    print(f"  Rotinas com >=1 Pallof Press: "
          f"{rotinas_com_pallof}/{N_ROTINAS} "
          f"({rotinas_com_pallof/N_ROTINAS*100:.1f}%)")
    print()

    return resultado


# ─── Pullover sobre as variações de puxadas ───────────────────────────────


def test_pullover_nao_domina_puxadas_slots(amostragem):
    """% de slots `puxadas` ocupados pela família Pullover.

    Pré-fix (60.0% em `costas(2)×2`, 53.5% em `upper(4)×2`); pós-fix esperado
    < 25% nesta config. Cap = 30% (~12pp de buffer).
    """
    total = amostragem["total_puxadas_slots"]
    pullover_slots = amostragem["puxadas_familia"].get("Pullover", 0)
    pct = pullover_slots / total
    assert total > 0, "config não gerou slots puxadas — caso mal construído"
    assert pct < 0.30, (
        f"Pullover ocupou {pullover_slots}/{total} ({pct:.1%}) dos slots de "
        f"puxadas — esperado < 30%. Distribuição: "
        f"{dict(amostragem['puxadas_familia'].most_common())}"
    )


def test_pullover_nao_domina_rotinas(amostragem):
    """% de rotinas (de 2 treinos) que contêm ≥1 Pullover.

    Pré-fix: ~80-100% nos cenários puxadas-only. Pós-fix esperado ~20% nesta
    config. Cap = 40%.
    """
    pct = amostragem["rotinas_com_pullover"] / N_ROTINAS
    assert pct < 0.40, (
        f"Pullover apareceu em {amostragem['rotinas_com_pullover']}/{N_ROTINAS} "
        f"rotinas ({pct:.1%}) — esperado < 40%."
    )


# ─── Pallof Press sobre outros abdominais ─────────────────────────────────


def test_pallof_nao_domina_core_slots(amostragem):
    """% de slots `core` ocupados por Pallof Press.

    Pallof é 1 de ~25 abdominais no banco; uniform seria ~4%. Cycling de
    padrões em core_isometrico (4 padrões, sendo `rotacao_tronco` um deles)
    e pré-Fase 4 ele é candidato único de rotacao_tronco iso. Cap = 15%.
    """
    total = amostragem["total_core_slots"]
    pallof_slots = amostragem["core_nome"].get("Pallof Press", 0)
    pct = pallof_slots / total
    assert total > 0, "config não gerou slots core — caso mal construído"
    assert pct < 0.15, (
        f"Pallof Press ocupou {pallof_slots}/{total} ({pct:.1%}) dos slots "
        f"de core — esperado < 15%. Top abdominais: "
        f"{dict(amostragem['core_nome'].most_common(5))}"
    )


def test_pallof_nao_domina_rotinas(amostragem):
    """% de rotinas (de 2 treinos) que contêm ≥1 Pallof Press.

    Atual ~15% (n=300). Cap = 30% pra acomodar flutuação estatística sem
    deixar regressão passar.
    """
    pct = amostragem["rotinas_com_pallof"] / N_ROTINAS
    assert pct < 0.30, (
        f"Pallof Press apareceu em {amostragem['rotinas_com_pallof']}/{N_ROTINAS} "
        f"rotinas ({pct:.1%}) — esperado < 30%."
    )
