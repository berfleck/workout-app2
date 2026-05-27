"""Testes da S-R1 — distribuição cross-treino de subregião (2026-05-27).

`peso_sr1` em `_construir_modelo` penaliza, pra cada par de treinos (t1, t2)
com demanda nivel `regiao` em ambos, splits IDÊNTICOS de subregião (T1 e T2
com mesma contagem em todas as subregiões de R). Achado 1 da auditoria
2026-05-26 (faceta de simetria): em `regiao lower(3) × 2T`, T1 e T2 caíam
sempre no mesmo split 2ant+1post+0pant. S-R1 desbloqueia alternância natural
cross-treino (T1=2+1 ↔ T2=1+2).

Testa:
(a) peso=0 preserva pré-S-R1 (sem regressão);
(b) peso>0 reduz % splits T1==T2 em config multi-treino com demanda região;
(c) demanda 1 treino só não inviabiliza (skip estrutural);
(d) compatibilidade com S-B5/S-A1/S-B1 ativos juntos.
"""
from __future__ import annotations

import random
from collections import Counter

from gerador_csp import (
    ConfigVariedade,
    gerar_rotina_csp,
)


_SUBS_LOWER = ("perna_anterior", "perna_posterior", "panturrilha", "adutores")


def _split_subregiao_lower(treino) -> tuple[int, ...]:
    """Conta exs por subregião lower no treino."""
    contador: Counter = Counter()
    for bloco in treino["blocos"]:
        for ex in bloco:
            if ex.subregiao in _SUBS_LOWER:
                contador[ex.subregiao] += 1
    return tuple(contador.get(s, 0) for s in _SUBS_LOWER)


# (a) peso=0 preserva pré-S-R1 (sem regressão)
def test_peso_zero_eh_neutro(banco):
    """peso_sr1=0 não muda viabilidade — rotina sai como pré-S-R1."""
    demandas = [("regiao", "lower", 3)]
    r = gerar_rotina_csp(
        [demandas, demandas], banco, nivel_aluno=3, seed=42,
        peso_sr1=0,
    )
    assert r["viavel"] is True
    assert len(r["treinos"]) == 2


# (b) peso>0 reduz % splits T1==T2 cross-treino
def test_peso_alto_alterna_subregiao_cross_treino(banco):
    """`regiao lower(3) × 2T` com peso=10: alvo <30% splits T1==T2 em
    N=10 runs. Baseline em main com peso=0 era ~40-60% (sondagem). Com
    S-R1 ativo: motor força alternância cross-treino."""
    demandas = [("regiao", "lower", 3)]
    n_split_repetido = 0
    n_validos = 0
    for python_seed in range(10):
        r = gerar_rotina_csp(
            [demandas, demandas], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_sr1=10,
        )
        if not r["viavel"]:
            continue
        n_validos += 1
        s1 = _split_subregiao_lower(r["treinos"][0])
        s2 = _split_subregiao_lower(r["treinos"][1])
        if s1 == s2:
            n_split_repetido += 1
    assert n_validos >= 8, (
        f"Esperado ≥8 rotinas viáveis em 10 runs; got {n_validos}"
    )
    # Sondagem 2026-05-27: 60% → 0% com peso=4 em lower_iso. Com peso=10
    # esperamos <=30% margem defensiva.
    pct = 100.0 * n_split_repetido / n_validos
    assert pct <= 30.0, (
        f"S-R1 ativo deveria reduzir splits T1==T2; "
        f"got {n_split_repetido}/{n_validos} = {pct:.1f}% (alvo ≤30%)"
    )


# (c) Rotina com 1 treino só não inviabiliza (skip estrutural)
def test_1_treino_so_eh_neutro(banco):
    """`regiao lower(3) × 1T` com peso=10: S-R1 não dispara (sem
    cross-treino possível). Rotina viável."""
    demandas = [("regiao", "lower", 3)]
    r = gerar_rotina_csp(
        [demandas], banco, nivel_aluno=3, seed=42,
        peso_sr1=10,
    )
    assert r["viavel"] is True
    assert len(r["treinos"]) == 1
    # 3 slots alocados.
    n_exs = sum(len(b) for b in r["treinos"][0]["blocos"])
    assert n_exs == 3


# (d) Compatibilidade com outros softs ativos juntos
def test_sr1_compativel_com_sb5_sa1_sb1(banco):
    """Full Body 2T região com S-R1 + S-B5 + S-A1 + S-B1 ativos juntos:
    viável, sem regressão estrutural."""
    full_body_t = [
        ("regiao", "upper", 3),
        ("regiao", "lower", 3),
        ("regiao", "core", 2),
    ]
    r = gerar_rotina_csp(
        [full_body_t, full_body_t], banco, nivel_aluno=3, seed=42,
        variedade=ConfigVariedade(python_seed=7),
        peso_evitar_agonistas=10,
        tamanho_preferido=2,
        peso_tamanho_bloco=5,
        peso_sa1=12,
        peso_sa1_repet=10,
        peso_sb5=4,
        peso_sr1=4,
    )
    assert r["viavel"] is True
    assert len(r["treinos"]) == 2
    # Verificação adicional: split lower T1 != T2 nesta seed específica
    # (cobertura visual — não asserção do efeito agregado).
    s1 = _split_subregiao_lower(r["treinos"][0])
    s2 = _split_subregiao_lower(r["treinos"][1])
    # Pelo menos 1 subregião com count diferente entre T1 e T2.
    assert s1 != s2, (
        f"S-R1 ativo com todos os softs: esperado alternância; got T1={s1} T2={s2}"
    )
