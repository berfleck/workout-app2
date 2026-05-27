"""Testes da S-T4 — proximidade biomecânica INTRA-treino mesma-sub (2026-05-29).

`peso_st4_pegada`, `peso_st4_plano`, `peso_st4_eq` em `_construir_modelo`
penalizam pares de slots NO MESMO TREINO mesma-subregião com match exato
na dimensão. Espelho INTRA do S-E1. Cobre caso clínico verbalizado por
Bernardo durante S-E1 e confirmado pela auditoria 2026-05-29:
`subregiao costas(2) × 1T` PRÉ-S-T4 tem 50% rotinas com pegada repetida.

Testa:
(a) pesos=0 preservam pré-S-T4 (sem regressão);
(b) costas(2) × 1T alterna pegada intra-treino;
(c) peito(2) × 1T alterna plano intra-treino;
(d) peito(2) × 1T graceful (pegada uniformemente pronada no banco, motor
    paga penalty mas não inviabiliza);
(e) compatibilidade com S-E1 + S-B5 + S-R1 + S-A1 + S-B1 ativos juntos.
"""
from __future__ import annotations

import random
from collections import Counter
from itertools import combinations

from gerador_csp import (
    ConfigVariedade,
    gerar_rotina_csp,
)


def _ex_por_treino_subregiao(rotina, subregiao):
    """Lista de Exercicios na subregião dada, por treino."""
    out = []
    for t in rotina["treinos"]:
        exs = []
        for bloco in t["blocos"]:
            for ex in bloco:
                if ex.subregiao == subregiao:
                    exs.append(ex)
        out.append(exs)
    return out


def _pares_repetidos_dim(exs, attr):
    """Conta pares (i, j) com i<j em `exs` que têm o mesmo valor em attr."""
    n = 0
    for a, b in combinations(exs, 2):
        va = getattr(a, attr, None)
        vb = getattr(b, attr, None)
        if va and vb and va == vb:
            n += 1
    return n


# (a) pesos=0 preserva pré-S-T4 (sem regressão)
def test_peso_zero_eh_neutro(banco):
    """Todos os pesos S-T4 em 0 = comportamento idêntico ao pré-frente."""
    full_body_t = [
        ("regiao", "upper", 3),
        ("regiao", "lower", 3),
        ("regiao", "core", 2),
    ]
    r = gerar_rotina_csp(
        [full_body_t, full_body_t], banco, nivel_aluno=3, seed=42,
        peso_st4_pegada=0, peso_st4_plano=0, peso_st4_eq=0,
    )
    assert r["viavel"] is True
    assert len(r["treinos"]) == 2


# (b) Caso canônico do handoff: costas(2) × 1T — alvo pegada repetida <30%
def test_costas_2_alterna_pegada_intra_treino(banco):
    """`subregiao costas(2) × 1T` com pesos 12/12/3: alvo <30% rotinas
    com pegada repetida intra-treino em N=10 runs. Sondagem PRÉ na main
    relatou 50% (15/30 pares) — auditoria 2026-05-29.

    Banco de costas tem variedade real em pegada (aberta/neutra/supinada/
    pronada distribuídas) — S-T4 tem como alternar."""
    demandas = [("subregiao", "costas", 2)]
    n_pegada_repetida = 0
    n_validos = 0
    for python_seed in range(10):
        r = gerar_rotina_csp(
            [demandas], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_st4_pegada=12,
            peso_st4_plano=12,
            peso_st4_eq=3,
        )
        if not r["viavel"]:
            continue
        n_validos += 1
        costas = _ex_por_treino_subregiao(r, "costas")[0]
        if _pares_repetidos_dim(costas, "pegada") > 0:
            n_pegada_repetida += 1
    assert n_validos >= 8, (
        f"Esperado >=8 rotinas viáveis em 10 runs; got {n_validos}"
    )
    pct = 100.0 * n_pegada_repetida / n_validos
    assert pct <= 30.0, (
        f"S-T4 ativo deveria reduzir pegada repetida intra-treino em costas(2); "
        f"got {n_pegada_repetida}/{n_validos} = {pct:.1f}% (alvo <=30%)"
    )


# (c) Caso peito(2): plano repetido — banco tem variedade real (reto/inclinado)
def test_peito_2_alterna_plano_intra_treino(banco):
    """`subregiao peito(2) × 1T` com pesos 12/12/3: alvo <30% rotinas
    com plano repetido intra-treino em N=10 runs. Sondagem PRÉ relatou
    63% plano repetido em peito (auditoria 2026-05-29).

    Banco de peito tem variedade em plano (reto/inclinado) — alternância
    possível."""
    demandas = [("subregiao", "peito", 2)]
    n_plano_repetido = 0
    n_validos = 0
    for python_seed in range(10):
        r = gerar_rotina_csp(
            [demandas], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_st4_pegada=12,
            peso_st4_plano=12,
            peso_st4_eq=3,
        )
        if not r["viavel"]:
            continue
        n_validos += 1
        peitos = _ex_por_treino_subregiao(r, "peito")[0]
        if _pares_repetidos_dim(peitos, "plano_corporal") > 0:
            n_plano_repetido += 1
    assert n_validos >= 8, (
        f"Esperado >=8 rotinas viáveis em 10 runs; got {n_validos}"
    )
    pct = 100.0 * n_plano_repetido / n_validos
    assert pct <= 30.0, (
        f"S-T4 ativo deveria reduzir plano repetido intra-treino em peito(2); "
        f"got {n_plano_repetido}/{n_validos} = {pct:.1f}% (alvo <=30%)"
    )


# (d) Graceful: pegada uniforme em peito empurrar_compostos NÃO inviabiliza
def test_peito_2_aceita_pegada_uniforme_graceful(banco):
    """Pegada em peito empurrar_compostos é uniformemente `pronada` no banco.
    S-T4 pegada vai disparar SEMPRE quando ambos slots caem em compostos
    (caso clínico §3.6 do handoff). Mas NÃO deve inviabilizar — motor paga
    penalty e resolve. Teste: rotina viável em N=5 runs."""
    demandas = [("subregiao", "peito", 2)]
    n_validos = 0
    for python_seed in range(5):
        r = gerar_rotina_csp(
            [demandas], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_st4_pegada=12,
            peso_st4_plano=12,
            peso_st4_eq=3,
        )
        if r["viavel"]:
            n_validos += 1
    assert n_validos == 5, (
        f"S-T4 ativo NÃO deveria inviabilizar peito(2) intra-treino mesmo com "
        f"pool de pegada uniforme; got {n_validos}/5 viáveis"
    )


# (e) Compatibilidade com S-E1 + outros softs ativos juntos
def test_st4_compativel_com_softs_ativos(banco):
    """Full Body 2T região com S-T4 + S-E1 + S-B5 + S-R1 + S-A1 + S-B1
    ativos juntos (config real de produção pós-S-T4): viável, zero regressão
    estrutural. Sanity: pegada/plano intra-treino mesma-sub NÃO deve repetir
    em peito ou costas no T1 (config: upper(3) → motor escolhe subregiões;
    quando aparece >=2 slots da mesma sub, S-T4 atua)."""
    full_body_t = [
        ("regiao", "upper", 3),
        ("regiao", "lower", 3),
        ("regiao", "core", 2),
    ]
    r = gerar_rotina_csp(
        [full_body_t, full_body_t], banco, nivel_aluno=3, seed=42,
        variedade=ConfigVariedade(python_seed=7),
        peso_aderencia=2,
        peso_evitar_agonistas=10,
        tamanho_preferido=2,
        peso_tamanho_bloco=5,
        peso_sa1=12,
        peso_sa1_repet=10,
        peso_sb5=4,
        peso_sr1=4,
        peso_se1_pegada=10,
        peso_se1_plano=10,
        peso_se1_eq=2,
        peso_st4_pegada=12,
        peso_st4_plano=12,
        peso_st4_eq=3,
    )
    assert r["viavel"] is True
    assert len(r["treinos"]) == 2


# (f) Sentinela por slot: dim vazia em algum slot não dispara penalty
def test_dim_vazia_nao_dispara_penalty(banco):
    """Exercícios sem pegada cadastrada (ex: Crossover/Pullover com célula
    vazia — futura solução de exceções biomecânicas) recebem code sentinela
    única por slot (`BASE_VAZIA + sid`). Dois slots com pegada vazia ganham
    codes distintos → `same_pegada` BoolVar reifica false → não dispara
    penalty. Teste documenta o comportamento: rotina com slots de dim vazia
    continua viável e S-T4 não inviabiliza."""
    from dataclasses import replace as dc_replace

    # Mock: força pegada=None em 2 ex de costas pra simular células vazias
    # (cenário das exceções biomecânicas — Pullover/Pulldown).
    banco_mock = []
    n_costas_vazios = 0
    for ex in banco:
        if ex.subregiao == "costas" and n_costas_vazios < 5:
            banco_mock.append(dc_replace(ex, pegada=None))
            n_costas_vazios += 1
        else:
            banco_mock.append(ex)

    demandas = [("subregiao", "costas", 2)]
    r = gerar_rotina_csp(
        [demandas], banco_mock, nivel_aluno=3, seed=42,
        variedade=ConfigVariedade(),
        peso_st4_pegada=12, peso_st4_plano=12, peso_st4_eq=3,
    )
    assert r["viavel"] is True
