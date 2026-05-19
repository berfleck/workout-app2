"""Valida que calcular_quotas não tem viés de ordem em empates de tie-break.

Quando duas âncoras empatam em (obrigatoriedade, peso, resto), o vencedor da
vaga remanescente deveria ser sorteado, não decidido pela ordem de definição.
"""
import random
import pytest
from gerador_treino import calcular_quotas

# (nome, ancoras, vagas, par_empatado)
CASOS_VIES = [
    ("upper N=4", [
        {"chave": "peito",  "peso": 2, "obrigatoria": True},
        {"chave": "costas", "peso": 2, "obrigatoria": True},
        {"chave": "ombro",  "peso": 1, "obrigatoria": True},
    ], 4, ("peito", "costas")),
    ("lower N=4", [
        {"chave": "perna_anterior",  "peso": 2, "obrigatoria": True},
        {"chave": "perna_posterior", "peso": 2, "obrigatoria": True},
        {"chave": "panturrilha",     "peso": 1, "obrigatoria": False},
    ], 4, ("perna_anterior", "perna_posterior")),
    ("core N=3", [
        {"chave": "core_dinamico",   "peso": 1, "obrigatoria": False},
        {"chave": "core_isometrico", "peso": 1, "obrigatoria": False},
    ], 3, ("core_dinamico", "core_isometrico")),
    ("costas-sub N=3", [
        {"chave": "remadas", "peso": 2, "obrigatoria": True},
        {"chave": "puxadas", "peso": 2, "obrigatoria": True},
    ], 3, ("remadas", "puxadas")),
]

@pytest.mark.parametrize("nome,ancoras,vagas,par", CASOS_VIES)
def test_sem_vies_em_empate_tie_break(nome, ancoras, vagas, par):
    a, b = par
    wins_a = wins_b = 0
    for seed in range(2000):
        random.seed(seed)
        quotas, _ = calcular_quotas(ancoras, vagas)
        qa, qb = quotas.get(a, 0), quotas.get(b, 0)
        if qa > qb:
            wins_a += 1
        elif qb > qa:
            wins_b += 1
    total = wins_a + wins_b
    assert total > 0, f"{nome}: nenhum empate detectado — caso mal construído"
    ratio = wins_a / total
    assert 0.45 <= ratio <= 0.55, (
        f"{nome}: '{a}' venceu {wins_a}/{total} ({ratio:.1%}). "
        f"Esperado ~50%. Viés ativo."
    )
