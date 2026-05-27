"""Testes do filtro de subregiões acessórias em demanda região (CSP).

Frente "Filtro de acessórias CSP" (2026-05-27) — fecha faceta de panturrilha
do Achado 1 da auditoria 2026-05-26. Decisão clínica: panturrilha tem o
mesmo tratamento de adutores — só entra em demanda subregião explícita,
nunca em demanda região `lower(N)`.

Implementação: panturrilha removida de `ANCORAS_POR_REGIAO['lower']` em
`gerador_treino.py`. O filtro upstream `subs_ancora_h_a0` em
`gerador_csp.py:642-646` já bania subregiões não declaradas — ao tirar
panturrilha do dict, ela passa automaticamente a ser banida em demanda
região, sem nova lógica.

Sondagem PRÉ (N=10, Full Body 2T região): pant_presente = 70%.
Sondagem PÓS esperada: 0%.
"""
from __future__ import annotations

from gerador_csp import gerar_treino_csp


def _subs_do_treino_csp(resultado_treino) -> list[str]:
    """Helper: lista de subregiões dos exs em todos os blocos do treino."""
    return [
        e.subregiao
        for g in resultado_treino["grupos"]
        for e in g["exercicios"]
    ]


# ── (a) Panturrilha NUNCA aparece em demanda região lower ────────────────


def test_panturrilha_filtrada_em_lower_3(banco):
    """`regiao lower(3)` × N seeds. Panturrilha NUNCA aparece. Pré-fix
    (pré-2026-05-27) ocorria em ~70% das rotinas via sondagem N=10."""
    falhas = []
    for seed in range(10):
        r = gerar_treino_csp(
            [("regiao", "lower", 3)], banco, nivel_aluno=3, seed=seed,
        )
        if not r["viavel"]:
            continue
        subs = _subs_do_treino_csp(r)
        if "panturrilha" in subs:
            falhas.append((seed, subs))
    assert not falhas, (
        f"panturrilha apareceu em lower(3) em {len(falhas)} seeds: {falhas}"
    )


def test_panturrilha_filtrada_em_lower_5_e_6(banco):
    """Em qualquer demanda região lower (qtd grande inclusa), panturrilha
    não pode aparecer. Diferença vs motor antigo: o antigo incluía
    panturrilha em lower(5+) via Hamilton. CSP pós-fix bane em todo N."""
    falhas = []
    for qtd in (5, 6):
        for seed in range(5):
            r = gerar_treino_csp(
                [("regiao", "lower", qtd)], banco, nivel_aluno=3, seed=seed,
            )
            if not r["viavel"]:
                continue
            subs = _subs_do_treino_csp(r)
            if "panturrilha" in subs:
                falhas.append((qtd, seed, subs))
    assert not falhas, (
        f"panturrilha apareceu em lower(5/6): {falhas}"
    )


# ── (b) Subregião explícita continua funcionando ─────────────────────────


def test_panturrilha_aparece_em_subregiao_explicita(banco):
    """`subregiao panturrilha(N)`: pant continua aparecendo normalmente.
    Sanity check de que a fix afeta apenas demanda região.

    NOTA: usar qtd=1 — qtd=2 é inviável no banco atual (constraints H-A1
    + H-R1 cross-treino apertam o pool pra 1 slot só de panturrilha).
    """
    for seed in range(3):
        r = gerar_treino_csp(
            [("subregiao", "panturrilha", 1)], banco, nivel_aluno=3, seed=seed,
        )
        assert r["viavel"], f"seed {seed}: inviável {r.get('status')}"
        subs = _subs_do_treino_csp(r)
        assert subs == ["panturrilha"], (
            f"seed {seed}: subregião explícita não respeitada: {subs}"
        )


# ── (c) Core não regride — sanity check do dict ──────────────────────────


def test_core_nao_regride(banco):
    """`regiao core(2)`: ANCORAS_POR_REGIAO['core'] tem ambas subs
    (core_isometrico, core_dinamico) com `obrigatoria=False`. Mudança
    em ['lower'] não pode banir core — pool deve continuar produzindo
    subregiões válidas de core, sem regredir pra ANCORAS_POR_REGIAO
    vazio nem incluir subs fora de core.

    O teste NÃO afirma que ambas subs aparecem em N seeds — viés de
    distribuição (core_dinamico dominando) é pré-existente, fora do
    escopo desta frente."""
    n_viaveis = 0
    for seed in range(15):
        r = gerar_treino_csp(
            [("regiao", "core", 2)], banco, nivel_aluno=3, seed=seed,
        )
        if not r["viavel"]:
            continue
        n_viaveis += 1
        subs = _subs_do_treino_csp(r)
        assert len(subs) == 2, f"seed {seed}: qtd diferente de 2: {subs}"
        for s in subs:
            assert s in {"core_isometrico", "core_dinamico"}, (
                f"seed {seed}: sub fora de core: {s}"
            )
    assert n_viaveis >= 10, f"poucos seeds viáveis em core(2): {n_viaveis}"
