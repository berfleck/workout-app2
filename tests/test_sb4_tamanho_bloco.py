"""Testes da Fatia 4.C — S-B4 tamanho preferido do bloco.

`peso_tamanho_bloco` em `_construir_modelo` penaliza blocos em uso com
tamanho diferente do `tamanho_preferido`. Equilibra o trade-off da 4.B
(S-B1 ativo empurra motor pra blocos solo) dando incentivo positivo a
blocos com tamanho desejado.

Testa:
(a) peso=0 preserva 4.B (sem regressão).
(b) tamanho_pref=2 + peso>0: motor faz blocos de 2.
(c) tamanho_pref=3 + peso>0: motor faz blocos de 3.
(d) tamanho_pref=1 + peso>0: motor faz blocos solo (1).
(e) Blocos vazios não geram penalty (motor não força blocos extras só
    pra ter onde botar penalty=0).
(f) S-B1 + S-B4 coexistem: agonistas evitados E tamanho respeitado.
"""
from __future__ import annotations

import random
from collections import Counter

from gerador_csp import (
    ConfigVariedade,
    gerar_rotina_csp,
)
from gerador_treino import GRUPO_MUSCULAR_PADRAO


DEMANDAS_RICA = [
    ("subregiao", "peito", 2),
    ("subregiao", "costas", 2),
    ("subregiao", "perna_anterior", 2),
]


def _conta_agonistas(blocos):
    n = 0
    for b in blocos:
        for i in range(len(b)):
            for j in range(i + 1, len(b)):
                g1 = GRUPO_MUSCULAR_PADRAO.get(b[i].padrao)
                g2 = GRUPO_MUSCULAR_PADRAO.get(b[j].padrao)
                if g1 == g2 and g1:
                    n += 1
    return n


def _tamanhos(blocos):
    return Counter(len(b) for b in blocos)


# (a) peso=0 preserva 4.B
def test_peso_zero_eh_neutro(banco):
    r = gerar_rotina_csp(
        [DEMANDAS_RICA], banco, nivel_aluno=3, seed=42,
        peso_tamanho_bloco=0,
    )
    assert r["viavel"] is True
    assert r["inversoes_totais"] == 0  # S-T1 ainda zerado


# (b) tamanho_pref=2 → blocos viram 2
def test_pref_2_com_peso_motor_faz_blocos_de_2(banco):
    blocos_tam = Counter()
    for ps in range(10):
        r = gerar_rotina_csp(
            [DEMANDAS_RICA], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=ps),
            tamanho_preferido=2,
            peso_tamanho_bloco=5,
        )
        if r["viavel"]:
            blocos_tam.update(_tamanhos(r["treinos"][0]["blocos"]))
    # Esperamos vasta maioria de tamanho 2.
    total = sum(blocos_tam.values())
    pct_2 = 100 * blocos_tam.get(2, 0) / total if total else 0
    assert pct_2 >= 90, (
        f"Esperado >=90% blocos tamanho 2 com pref=2; got {dict(blocos_tam)} "
        f"({pct_2:.1f}%)"
    )


# (c) tamanho_pref=3 → blocos viram 3
def test_pref_3_com_peso_motor_faz_blocos_de_3(banco):
    blocos_tam = Counter()
    for ps in range(10):
        r = gerar_rotina_csp(
            [DEMANDAS_RICA], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=ps),
            tamanho_preferido=3,
            peso_tamanho_bloco=5,
        )
        if r["viavel"]:
            blocos_tam.update(_tamanhos(r["treinos"][0]["blocos"]))
    total = sum(blocos_tam.values())
    pct_3 = 100 * blocos_tam.get(3, 0) / total if total else 0
    assert pct_3 >= 90, (
        f"Esperado >=90% blocos tamanho 3 com pref=3; got {dict(blocos_tam)} "
        f"({pct_3:.1f}%)"
    )


# (d) tamanho_pref=1 → blocos viram solo
def test_pref_1_com_peso_motor_faz_blocos_solo(banco):
    blocos_tam = Counter()
    for ps in range(10):
        r = gerar_rotina_csp(
            [DEMANDAS_RICA], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=ps),
            tamanho_preferido=1,
            peso_tamanho_bloco=5,
        )
        if r["viavel"]:
            blocos_tam.update(_tamanhos(r["treinos"][0]["blocos"]))
    total = sum(blocos_tam.values())
    pct_1 = 100 * blocos_tam.get(1, 0) / total if total else 0
    assert pct_1 >= 90, (
        f"Esperado >=90% blocos solo com pref=1; got {dict(blocos_tam)} "
        f"({pct_1:.1f}%)"
    )


# (e) Total de slots preservado (sem inflar nem encolher blocos vazios)
def test_total_slots_preservado_independente_do_pref(banco):
    n_esperado = sum(qtd for _, _, qtd in DEMANDAS_RICA)
    for pref in (1, 2, 3):
        r = gerar_rotina_csp(
            [DEMANDAS_RICA], banco, nivel_aluno=3,
            seed=42, tamanho_preferido=pref, peso_tamanho_bloco=5,
        )
        assert r["viavel"] is True
        total = sum(len(b) for b in r["treinos"][0]["blocos"])
        assert total == n_esperado, (
            f"pref={pref}: total slots {total} != esperado {n_esperado}"
        )


# (f) S-B1 + S-B4 coexistem
def test_sb1_e_sb4_coexistem(banco):
    """S-B1 + S-B4 coexistem: vasta maioria dos blocos no tamanho preferido.

    Decisão 2026-05-25 (Frente S-A1): S-B1 NÃO atua intra-sub explícita.
    DEMANDAS_RICA é toda intra-sub (peito/costas/perna_anterior), então
    S-B1 intra fica desligada por design e agonistas intra-sub são
    esperados. Foco do teste muda pra coexistência de constraints
    de bloco (tamanho preferido honrado quando S-B1 está ativo)."""
    blocos_tam = Counter()
    for ps in range(15):
        r = gerar_rotina_csp(
            [DEMANDAS_RICA], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=ps),
            peso_evitar_agonistas=10,
            tamanho_preferido=2,
            peso_tamanho_bloco=5,
        )
        if r["viavel"]:
            blocos_tam.update(_tamanhos(r["treinos"][0]["blocos"]))
    total = sum(blocos_tam.values())
    pct_2 = 100 * blocos_tam.get(2, 0) / total if total else 0
    assert pct_2 >= 90, (
        f"S-B1+S-B4: esperado >=90% blocos tamanho 2; got {pct_2:.1f}%"
    )
