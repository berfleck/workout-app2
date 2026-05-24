"""Testes da Fatia 4.B — S-B1 distância funcional intra-bloco.

`peso_evitar_agonistas` em `_construir_modelo` adiciona penalty por par
de slots no MESMO BLOCO com MESMO GRUPO funcional (push/pull/quad/...).
Resolve achado da 4.A: blocos com 2 Principais agonistas (ex.: Recuo +
Remada Uni) que aconteciam por sorteio livre.

Testa:
(a) peso=0 preserva 4.A (sem regressão).
(b) peso>0 reduz % pares agonistas em N runs.
(c) Antagonistas (push+pull, upper+lower) continuam permitidos.
(d) Não inviabiliza rotinas (graceful: cai pra bloco solo se preciso).
"""
from __future__ import annotations

import random
from collections import Counter

from gerador_csp import (
    ConfigVariedade,
    gerar_rotina_csp,
    gerar_treino_csp,
)
from gerador_treino import GRUPO_MUSCULAR_PADRAO


DEMANDAS_RICA = [
    ("subregiao", "peito", 2),     # 2 push (empurrar_compostos/isolados)
    ("subregiao", "costas", 2),    # 2 pull (remadas/puxadas)
    ("subregiao", "perna_anterior", 2),  # 2 quad/glute
]


def _conta_pares_no_bloco_mesmo_grupo(blocos):
    """Itera todos os pares dentro de cada bloco, conta quantos têm
    mesmo GRUPO_MUSCULAR_PADRAO."""
    n_agon = 0
    n_total = 0
    for bloco in blocos:
        for i in range(len(bloco)):
            for j in range(i + 1, len(bloco)):
                n_total += 1
                g1 = GRUPO_MUSCULAR_PADRAO.get(bloco[i].padrao)
                g2 = GRUPO_MUSCULAR_PADRAO.get(bloco[j].padrao)
                if g1 == g2 and g1 is not None:
                    n_agon += 1
    return n_agon, n_total


# (a) peso=0 preserva 4.A
def test_peso_zero_eh_neutro(banco):
    """peso_evitar_agonistas=0 não muda viabilidade nem objetivo."""
    r = gerar_treino_csp(DEMANDAS_RICA, banco, nivel_aluno=3, seed=42,
                          peso_evitar_agonistas=0)
    assert r["viavel"] is True
    # 4.A baseline: blocos viáveis, S-T1 inversoes=0 esperado
    assert r["inversoes"] == 0
    assert "blocos" in r and len(r["blocos"]) >= 1


def test_peso_zero_aceita_agonistas_no_mesmo_bloco(banco):
    """Sem peso ativo, motor deve produzir pares agonistas em pelo menos
    algumas runs (banco tem cobertura suficiente)."""
    pares_agon_total = 0
    for python_seed in range(20):
        r = gerar_rotina_csp(
            [DEMANDAS_RICA], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_evitar_agonistas=0,
        )
        if r["viavel"]:
            agon, _ = _conta_pares_no_bloco_mesmo_grupo(r["treinos"][0]["blocos"])
            pares_agon_total += agon
    # Sem ativar S-B1, esperamos pelo menos alguns pares agonistas.
    # Smoke empírico mostrou ~18 em 20 runs; usamos limite baixo defensivo.
    assert pares_agon_total >= 3, (
        f"Sem S-B1, esperado >=3 pares agonistas em 20 runs; got {pares_agon_total}"
    )


# (b) peso>0 reduz drasticamente pares agonistas
def test_peso_alto_elimina_pares_agonistas(banco):
    """peso=10 deve zerar (ou quase) pares agonistas."""
    pares_agon = 0
    pares_total = 0
    for python_seed in range(20):
        r = gerar_rotina_csp(
            [DEMANDAS_RICA], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_evitar_agonistas=10,
        )
        if r["viavel"]:
            agon, total = _conta_pares_no_bloco_mesmo_grupo(r["treinos"][0]["blocos"])
            pares_agon += agon
            pares_total += total
    # Com peso=10, esperamos <= 1 par agonista em 20 runs (margem 5%).
    # Smoke empírico mostrou 0/58.
    assert pares_agon <= 1, (
        f"S-B1 ativa deveria eliminar agonistas; got {pares_agon}/{pares_total}"
    )


# (c) Antagonistas continuam permitidos
def test_peso_alto_permite_pares_antagonistas(banco):
    """Pares de grupos diferentes (push+pull, upper+lower) não são penalizados."""
    pares_diff_grupo = 0
    for python_seed in range(20):
        r = gerar_rotina_csp(
            [DEMANDAS_RICA], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_evitar_agonistas=10,
        )
        if r["viavel"]:
            for bloco in r["treinos"][0]["blocos"]:
                for i in range(len(bloco)):
                    for j in range(i + 1, len(bloco)):
                        g1 = GRUPO_MUSCULAR_PADRAO.get(bloco[i].padrao)
                        g2 = GRUPO_MUSCULAR_PADRAO.get(bloco[j].padrao)
                        if g1 != g2 and g1 and g2:
                            pares_diff_grupo += 1
    # Esperamos pelo menos algum par de grupos diferentes (motor não vira
    # todo solo). Se ficou 0, sinal de regressão (motor recusou todo par).
    assert pares_diff_grupo > 0, (
        "S-B1 com peso=10 zerou todo pareamento — deveria permitir antagonistas"
    )


# (d) Não inviabiliza
def test_peso_alto_nao_inviabiliza(banco):
    """Mesmo com peso alto (50), motor sempre devolve rotina viável
    (graceful: cai pra bloco solo se preciso)."""
    for python_seed in range(10):
        r = gerar_rotina_csp(
            [DEMANDAS_RICA], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_evitar_agonistas=50,
        )
        assert r["viavel"] is True, (
            f"S-B1 com peso=50 inviabilizou (python_seed={python_seed})"
        )


# Interação com Aderência (Frente D): ambos ativos preservam estrutura
def test_sb1_compativel_com_aderencia_alta(banco):
    """Aderência Alta + S-B1 ativo: rotina viável, sem regressão."""
    r = gerar_rotina_csp(
        [DEMANDAS_RICA], banco, nivel_aluno=3,
        seed=42,
        variedade=ConfigVariedade(python_seed=7),
        peso_aderencia=2,
        peso_evitar_agonistas=10,
    )
    assert r["viavel"] is True
    assert "blocos" in r["treinos"][0]
