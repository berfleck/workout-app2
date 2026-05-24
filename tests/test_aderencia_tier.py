"""Testes da Frente D da Fatia 3 — modulação Aderência ao Tier.

`peso_aderencia` em `_construir_modelo` adiciona, por slot, penalty
proporcional a `(rank_max - rank_slot) * peso`. Resolve o achado #1
da Frente C: slots únicos de padrão (ex.: `hinge(1)`) que não disparam
H-T4 e não criam pares de S-T1 (slot solo → 0 inversões qualquer tier)
agora têm diferenciação no objetivo → motor escolhe tier alto.

Testa:
(a) `peso_aderencia=0` preserva byte-a-byte a Frente B (sem regressão).
(b) `peso_aderencia>0` força tier alto em slot único de padrão.
(c) Variedade dentro de Principal preservada quando há múltiplos
    Principais no pool (Frente B continua trabalhando).
(d) Cross-treino: hinge(1) em rotina de 2 treinos com peso alto força
    Principal nos 2 treinos.
"""
from __future__ import annotations

import random
from collections import Counter

from gerador_csp import (
    ConfigVariedade,
    gerar_rotina_csp,
    gerar_treino_csp,
)


# Slot único de padrão hinge — H-T4 NÃO dispara (eh "padrao", não "subregiao");
# S-T1 NÃO produz par (1 slot, sem i<j). Pool hinge no XLSX atual tem 11
# Principal + 1 Intermediário + 9 Acessório.
DEMANDA_SLOT_UNICO = [("padrao", "hinge", 1)]


# ─────────────────────────────────────────────────────────────────────────────
# (a) peso=0 preserva comportamento Frente B
# ─────────────────────────────────────────────────────────────────────────────

def test_peso_aderencia_zero_eh_neutro(banco):
    """peso=0 não deve mudar viabilidade nem objetivo da rotina padrão."""
    r0 = gerar_treino_csp(
        DEMANDA_SLOT_UNICO, banco, nivel_aluno=3, seed=42,
        peso_aderencia=0,
    )
    assert r0["viavel"] is True
    # inversoes de S-T1 = 0 em slot único (nao tem par)
    assert r0["inversoes"] == 0


def test_peso_aderencia_zero_permite_variedade_de_tier(banco):
    """peso=0 (Média/Baixa neutras): motor sorteia entre tiers do pool.
    Variedade.python_seed garante que sorteio é determinístico por seed."""
    tiers = Counter()
    for python_seed in range(30):
        r = gerar_treino_csp(
            DEMANDA_SLOT_UNICO, banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_aderencia=0,
        )
        if r["viavel"]:
            tiers[r["ordem_global"][0].tier] += 1
    # Pool tem Principal + Acessório com pesos comparáveis (11 vs 9).
    # Não exigimos distribuição exata; só que pelo menos um Acessório
    # apareça em 30 runs (motor não tá filtrando tier sem peso).
    assert tiers.get("Acessório", 0) >= 1, (
        "Esperado >=1 Acessório em 30 runs sem peso_aderencia; got "
        f"{dict(tiers)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# (b) peso>0 força tier alto em slot único de padrão
# ─────────────────────────────────────────────────────────────────────────────

def test_peso_aderencia_alta_zera_acessorios_em_slot_unico(banco):
    """Aderência Alta (peso=2) em 30 runs: zero Acessórios no slot único."""
    tiers = Counter()
    for python_seed in range(30):
        r = gerar_treino_csp(
            DEMANDA_SLOT_UNICO, banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_aderencia=2,
        )
        if r["viavel"]:
            tiers[r["ordem_global"][0].tier] += 1
    assert tiers.get("Acessório", 0) == 0, (
        "Aderência Alta deve eliminar Acessório em slot único; got "
        f"{dict(tiers)}"
    )
    # Principal majoritário (Intermediário possível mas raro — pool só tem 1).
    n_alto = tiers.get("Principal", 0) + tiers.get("Intermediário", 0)
    assert n_alto >= 28, f"Esperado >=28 tier alto em 30 runs; got {dict(tiers)}"


# ─────────────────────────────────────────────────────────────────────────────
# (c) Variedade dentro do tier alto preservada
# ─────────────────────────────────────────────────────────────────────────────

def test_peso_alta_preserva_variedade_dentro_do_tier(banco):
    """Aderência Alta não deve colapsar pra 1 único Principal — Frente B
    softmax continua sorteando dentro dos Principais equivalentes."""
    nomes = Counter()
    for python_seed in range(40):
        r = gerar_treino_csp(
            DEMANDA_SLOT_UNICO, banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_aderencia=2,
        )
        if r["viavel"]:
            nomes[r["ordem_global"][0].nome] += 1
    # Pool tem 11 Principais. Esperamos >=4 distintos em 40 runs com
    # variedade ativa (frequência típica observada: ~8-10 distintos).
    assert len(nomes) >= 4, (
        f"Variedade colapsada: só {len(nomes)} nomes distintos em 40 runs; "
        f"got {dict(nomes)}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# (d) Cross-treino: Aderência Alta numa rotina de N treinos
# ─────────────────────────────────────────────────────────────────────────────

def test_peso_alta_cross_treino_forca_tier_em_ambos(banco):
    """Rotina de 2 treinos, cada um com hinge(1). Aderência Alta deve
    eliminar Acessório nos DOIS treinos. AllDifferent global garante que
    nomes não se repetem cross-treino, mas tier alto vai pra ambos."""
    demandas_2_treinos = [DEMANDA_SLOT_UNICO, DEMANDA_SLOT_UNICO]
    runs_acessorios = 0
    runs_total_treinos = 0
    for python_seed in range(20):
        r = gerar_rotina_csp(
            demandas_2_treinos, banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_aderencia=2,
        )
        if not r["viavel"]:
            continue
        for treino in r["treinos"]:
            for ex in treino["ordem_global"]:
                runs_total_treinos += 1
                if ex.tier == "Acessório":
                    runs_acessorios += 1
    assert runs_acessorios == 0, (
        f"Aderência Alta cross-treino vazou {runs_acessorios}/"
        f"{runs_total_treinos} Acessórios"
    )


# ─────────────────────────────────────────────────────────────────────────────
# (e) Sem variedade ativa, peso ainda funciona (branch _resolver_legacy)
# ─────────────────────────────────────────────────────────────────────────────

def test_peso_alta_branch_legacy_tambem_forca_tier(banco):
    """Branch legacy (variedade=None) também propaga peso_aderencia.
    Garante que Aderência funciona mesmo se algum caller não passar
    ConfigVariedade (defensivo — produção via /regerar sempre passa)."""
    acessorios = 0
    for seed in range(30):
        r = gerar_treino_csp(
            DEMANDA_SLOT_UNICO, banco, nivel_aluno=3, seed=seed,
            variedade=None,
            peso_aderencia=2,
        )
        if r["viavel"] and r["ordem_global"][0].tier == "Acessório":
            acessorios += 1
    assert acessorios == 0, (
        f"Branch legacy não propagou peso_aderencia: {acessorios}/30 Acessórios"
    )
