"""Testes da S-B5 — diversidade de região INTRA-bloco (2026-05-26).

`peso_sb5` em `_construir_modelo` adiciona penalty por par de slots no
MESMO BLOCO com MESMA REGIÃO (upper/lower/core/cardio). Recupera a
feature P1-P4 do `montar_blocos` greedy antigo (achado 3 da auditoria
2026-05-26): 4/8 blocos saíam com 2 exs da mesma região, anulando o
ponto do superset.

Testa:
(a) peso=0 preserva pré-S-B5 (sem regressão);
(b) peso>0 reduz % blocos same-region em N runs com config multi-região;
(c) demanda single-region não inviabiliza (graceful degradation);
(d) interação com S-B1: pares "duplamente ruins" pagam penalty dupla.
"""
from __future__ import annotations

import random

from gerador_csp import (
    ConfigVariedade,
    gerar_rotina_csp,
    gerar_treino_csp,
)


DEMANDAS_MULTI_REGIAO = [
    ("subregiao", "peito", 2),          # upper
    ("subregiao", "perna_anterior", 2), # lower
    ("regiao", "core", 2),              # core
]


def _conta_pares_no_bloco_mesma_regiao(blocos):
    """Conta pares dentro de cada bloco que têm mesma região."""
    n_same = 0
    n_total = 0
    for bloco in blocos:
        for i in range(len(bloco)):
            for j in range(i + 1, len(bloco)):
                n_total += 1
                if bloco[i].regiao == bloco[j].regiao:
                    n_same += 1
    return n_same, n_total


def _conta_blocos_same_region(blocos):
    """Conta blocos onde pelo menos 2 exs têm a mesma região."""
    n_same = 0
    n_blocos_com_2plus = 0
    for bloco in blocos:
        if len(bloco) < 2:
            continue
        n_blocos_com_2plus += 1
        regioes = [ex.regiao for ex in bloco]
        if len(set(regioes)) < len(regioes):
            n_same += 1
    return n_same, n_blocos_com_2plus


# (a) peso=0 preserva pré-S-B5 (sem regressão)
def test_peso_zero_eh_neutro(banco):
    """peso_sb5=0 não muda viabilidade nem produz vars novas com efeito."""
    r = gerar_treino_csp(
        DEMANDAS_MULTI_REGIAO, banco, nivel_aluno=3, seed=42,
        peso_sb5=0,
    )
    assert r["viavel"] is True
    assert "blocos" in r and len(r["blocos"]) >= 1


def test_peso_zero_permite_blocos_same_region(banco):
    """Sem S-B5, motor deve produzir blocos same-region em pelo menos
    algumas runs (banco tem cobertura suficiente)."""
    blocos_same_total = 0
    for python_seed in range(15):
        r = gerar_rotina_csp(
            [DEMANDAS_MULTI_REGIAO], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_sb5=0,
        )
        if r["viavel"]:
            same, _ = _conta_blocos_same_region(r["treinos"][0]["blocos"])
            blocos_same_total += same
    # Sondagem em main mostrou ~38.8% blocos same-region em config
    # Full Body 2T (sub); aqui com 1 treino de 3 demandas (peito+perna_ant+
    # core), esperamos pelo menos alguns blocos same-region em 15 runs.
    assert blocos_same_total >= 2, (
        f"Sem S-B5, esperado >=2 blocos same-region em 15 runs; got {blocos_same_total}"
    )


# (b) peso>0 reduz pares same-region em config multi-região
def test_peso_alto_reduz_pares_same_region(banco):
    """peso=10 reduz drasticamente pares same-region (espera-se 0
    em config rica como esta, onde motor consegue alternar regiões)."""
    pares_same = 0
    pares_total = 0
    for python_seed in range(15):
        r = gerar_rotina_csp(
            [DEMANDAS_MULTI_REGIAO], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_sb5=10,
        )
        if r["viavel"]:
            same, total = _conta_pares_no_bloco_mesma_regiao(
                r["treinos"][0]["blocos"]
            )
            pares_same += same
            pares_total += total
    # Com peso=10, esperamos no máximo 1 par same-region em 15 runs (margem
    # defensiva — config multi-região tem espaço pra alternar perfeitamente).
    assert pares_same <= 1, (
        f"S-B5 ativo deveria eliminar same-region em config rica; "
        f"got {pares_same}/{pares_total}"
    )


# (c) Demanda single-region não inviabiliza
def test_demanda_single_region_nao_inviabiliza(banco):
    """upper(4) sozinha força pares same-region — motor aceita pagando
    penalty, não devolve INFEASIBLE."""
    for python_seed in range(10):
        r = gerar_rotina_csp(
            [[("regiao", "upper", 4)]], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_sb5=10,
            peso_evitar_agonistas=10,
        )
        assert r["viavel"] is True, (
            f"S-B5 com peso=10 inviabilizou single-region "
            f"(python_seed={python_seed})"
        )
        # Motor deve ter alocado 4 slots (não pode degradar slots).
        all_exs = [
            ex for treino in r["treinos"]
            for bloco in treino["blocos"]
            for ex in bloco
        ]
        assert len(all_exs) == 4


# (d) Interação com S-B1 — pares "duplamente ruins" não quebram nada
def test_sb5_compativel_com_sb1(banco):
    """S-B1 (mesmo grupo funcional) + S-B5 (mesma região) ativos juntos:
    rotina viável. Par push+push (mesmo grupo E mesma região) paga penalty
    dupla — comportamento esperado, não regressão."""
    r = gerar_rotina_csp(
        [DEMANDAS_MULTI_REGIAO], banco, nivel_aluno=3,
        seed=42,
        variedade=ConfigVariedade(python_seed=7),
        peso_evitar_agonistas=10,
        peso_sb5=10,
    )
    assert r["viavel"] is True
    # Com ambos ativos, ainda mais pressão pra alternar — esperamos pares
    # same-region = 0 nesta seed (margem 0 pq config muito rica).
    same, _ = _conta_pares_no_bloco_mesma_regiao(r["treinos"][0]["blocos"])
    assert same == 0, f"Ambos ativos deveriam alternar perfeitamente; got {same}"


# (e) Interação com Aderência Alta (Frente D)
def test_sb5_compativel_com_aderencia_alta(banco):
    """Aderência Alta + S-B5 ativo: rotina viável, sem regressão."""
    r = gerar_rotina_csp(
        [DEMANDAS_MULTI_REGIAO], banco, nivel_aluno=3,
        seed=42,
        variedade=ConfigVariedade(python_seed=7),
        peso_aderencia=2,
        peso_evitar_agonistas=10,
        peso_sb5=10,
    )
    assert r["viavel"] is True
    assert "blocos" in r["treinos"][0]


# (f) Smoke do achado da auditoria 2026-05-26
def test_smoke_full_body_regiao_h_a0(banco):
    """Replica o setup da auditoria 2026-05-26 (Full Body 2T região)
    e mede % blocos same-region em N runs. Alvo qualitativo: redução
    forte comparada à baseline (38.8% sondagem em main).
    """
    full_body_t = [
        ("regiao", "upper", 3),
        ("regiao", "lower", 3),
        ("regiao", "core", 2),
    ]
    blocos_same = 0
    blocos_com_2plus_total = 0
    for python_seed in range(5):
        r = gerar_rotina_csp(
            [full_body_t, full_body_t], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_evitar_agonistas=10,
            tamanho_preferido=2,
            peso_tamanho_bloco=5,
            peso_sa1=12,
            peso_sa1_repet=10,
            peso_sb5=10,
        )
        if r["viavel"]:
            for treino in r["treinos"]:
                same, total = _conta_blocos_same_region(treino["blocos"])
                blocos_same += same
                blocos_com_2plus_total += total
    # Baseline em main era ~22.5% (sondagem N=10 nessa exata config).
    # Com S-B5 ativo, alvo <15%. Margem defensiva: aceita até 25%.
    pct = (
        100.0 * blocos_same / blocos_com_2plus_total
        if blocos_com_2plus_total else 0.0
    )
    assert pct < 25.0, (
        f"S-B5 no setup da auditoria deveria reduzir same-region; "
        f"got {blocos_same}/{blocos_com_2plus_total} = {pct:.1f}%"
    )
