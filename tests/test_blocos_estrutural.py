"""Testes da Fatia 4.A — modelagem estrutural de blocos no CSP.

Cobre:
(a) Motor retorna `blocos: list[list[Exercicio]]` em cada treino.
(b) Tamanho de cada bloco em [1, TAMANHO_MAX_BLOCO].
(c) Soma dos slots dos blocos == soma dos slots da rotina.
(d) Tier-order por bloco (reformulação de S-T1):
    se inversoes==0, tier máximo do bloco N >= tier máximo do bloco N+1.
(e) ordem_global continua sendo concatenação dos blocos.
(f) `blocos` propagado em gerar_treino_csp (wrapper 1-treino).
(g) Cross-treino: blocos por treino estruturados corretamente.
"""
from __future__ import annotations

import random

from gerador_csp import (
    ConfigVariedade,
    TAMANHO_MAX_BLOCO,
    TIER_RANK,
    gerar_rotina_csp,
    gerar_treino_csp,
)


DEMANDAS_PEQUENA = [
    ("subregiao", "peito", 2),
    ("subregiao", "costas", 2),
    ("subregiao", "perna_anterior", 2),
]


def _tier_max(bloco_exs):
    return max(TIER_RANK.get(e.tier, 1) for e in bloco_exs)


# (a) + (b) + (c) — estrutura de blocos
def test_motor_retorna_blocos_estruturados(banco):
    r = gerar_rotina_csp([DEMANDAS_PEQUENA], banco, nivel_aluno=3, seed=42)
    assert r["viavel"] is True
    treino = r["treinos"][0]
    assert "blocos" in treino, "Pós-4.A treino precisa ter chave 'blocos'"
    assert len(treino["blocos"]) >= 1
    n_slots_treino = sum(len(b) for b in treino["blocos"])
    n_esperado = sum(qtd for _, _, qtd in DEMANDAS_PEQUENA)
    assert n_slots_treino == n_esperado, (
        f"Soma de slots nos blocos ({n_slots_treino}) != demanda total ({n_esperado})"
    )
    for bloco in treino["blocos"]:
        assert 1 <= len(bloco) <= TAMANHO_MAX_BLOCO, (
            f"Bloco com tamanho fora de [1, {TAMANHO_MAX_BLOCO}]: {len(bloco)}"
        )


# (d) — tier-order por bloco (S-T1 reformulada)
def test_tier_order_por_bloco_quando_inversoes_zero(banco):
    """Quando inversoes_totais == 0, tier máximo do bloco N+1 <= bloco N."""
    r = gerar_rotina_csp([DEMANDAS_PEQUENA], banco, nivel_aluno=3, seed=42)
    assert r["viavel"] is True
    if r["inversoes_totais"] != 0:
        return  # só faz sentido quando ótimo zerado
    treino = r["treinos"][0]
    blocos = treino["blocos"]
    for i in range(len(blocos) - 1):
        tier_max_i = _tier_max(blocos[i])
        tier_max_next = _tier_max(blocos[i + 1])
        assert tier_max_i >= tier_max_next, (
            f"Inversão em pos {i}: tier_max({tier_max_i}) < tier_max_next({tier_max_next})"
        )


# (e) — ordem_global é concat dos blocos
def test_ordem_global_eh_concat_dos_blocos(banco):
    r = gerar_rotina_csp([DEMANDAS_PEQUENA], banco, nivel_aluno=3, seed=42)
    assert r["viavel"] is True
    treino = r["treinos"][0]
    ordem_via_blocos = []
    for bloco in treino["blocos"]:
        ordem_via_blocos.extend(bloco)
    nomes_concat = [e.nome for e in ordem_via_blocos]
    nomes_global = [e.nome for e in treino["ordem_global"]]
    assert nomes_global == nomes_concat


# (f) — wrapper gerar_treino_csp propaga blocos
def test_gerar_treino_csp_propaga_blocos(banco):
    r = gerar_treino_csp(DEMANDAS_PEQUENA, banco, nivel_aluno=3, seed=42)
    assert r["viavel"] is True
    assert "blocos" in r
    assert len(r["blocos"]) >= 1
    n_esperado = sum(qtd for _, _, qtd in DEMANDAS_PEQUENA)
    n_slots = sum(len(b) for b in r["blocos"])
    assert n_slots == n_esperado


# (g) — cross-treino: cada treino tem blocos próprios
def test_cross_treino_blocos_separados(banco):
    demandas_2 = [
        [("subregiao", "peito", 2), ("subregiao", "costas", 2)],
        [("subregiao", "perna_anterior", 2), ("subregiao", "ombro", 1)],
    ]
    r = gerar_rotina_csp(demandas_2, banco, nivel_aluno=3, seed=42)
    assert r["viavel"] is True
    assert len(r["treinos"]) == 2
    for t_idx, treino in enumerate(r["treinos"]):
        assert "blocos" in treino
        n_esperado = sum(qtd for _, _, qtd in demandas_2[t_idx])
        n_slots = sum(len(b) for b in treino["blocos"])
        assert n_slots == n_esperado, (
            f"Treino {t_idx}: {n_slots} slots vs {n_esperado} esperado"
        )


# Variedade ativa também propaga blocos
def test_variedade_ativa_propaga_blocos(banco):
    r = gerar_rotina_csp(
        [DEMANDAS_PEQUENA], banco, nivel_aluno=3,
        seed=random.randint(0, 2**31 - 1),
        variedade=ConfigVariedade(python_seed=123),
    )
    assert r["viavel"] is True
    treino = r["treinos"][0]
    assert "blocos" in treino
    n_slots = sum(len(b) for b in treino["blocos"])
    n_esperado = sum(qtd for _, _, qtd in DEMANDAS_PEQUENA)
    assert n_slots == n_esperado


# Aderência (Frente D) continua funcionando + estrutura de blocos preservada
def test_aderencia_alta_preserva_estrutura_de_blocos(banco):
    demanda = [("padrao", "hinge", 1)]
    r = gerar_treino_csp(
        demanda, banco, nivel_aluno=3, seed=42,
        variedade=ConfigVariedade(),
        peso_aderencia=2,
    )
    assert r["viavel"] is True
    assert "blocos" in r
    # 1 slot = 1 bloco de tamanho 1
    assert len(r["blocos"]) == 1
    assert len(r["blocos"][0]) == 1
    # Aderência Alta force tier alto
    assert r["blocos"][0][0].tier in ("Principal", "Intermediário")
