"""Snapshots de regressão.

Cada teste fixa uma configuração + seed e compara o resultado contra um
snapshot armazenado em `__snapshots__/`. O snapshot captura a estrutura
clínica derivada (tipo, blocos, nomes, avisos, relaxados) — ignora
metadata cosmético como `padrao`, `purpose`, `complexidade` (que são
derivados do nome).

## Fluxo de regeneração

Quando uma etapa futura mudar comportamento esperado:

1. `pytest tests/test_regressao.py -v` — vê quais snapshots quebram.
2. Para cada snapshot quebrado, inspecionar o diff impresso pelo syrupy.
   Decidir:
   - **(a) Regressão indesejada** → consertar o código.
   - **(b) Mudança esperada** →
     `pytest tests/test_regressao.py::nome_do_teste --snapshot-update`
     regenera só esse. Commit isolado, mensagem explicando porquê.
3. **Nunca rodar `--snapshot-update` em massa sem revisar.**
4. A coluna "expectativa" no docstring de cada teste indica se a mudança
   já é esperada em alguma frente futura.
"""
from __future__ import annotations

import random

from gerador_treino import gerar_multiplos_treinos
from tests.conftest import sessao_para_estrutura_clinica


def _rotina_clinica(sessoes):
    return [sessao_para_estrutura_clinica(s) for s in sessoes]


# ----- 1: multi-região, 3 treinos -----------------------------------------

def test_upper_3_lower_2_core_2_3treinos_seed42(banco, snapshot):
    """Expectativa: estável (Frentes 2-4 não devem mudar)."""
    random.seed(42)
    cfg = {
        "demandas": [
            ("regiao", "upper", 3),
            ("regiao", "lower", 2),
            ("regiao", "core", 2),
        ]
    }
    sessoes = gerar_multiplos_treinos(banco, [cfg, cfg, cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 2: template Full Body × 4 ------------------------------------------

def test_full_body_4treinos_seed1(banco, snapshot):
    """Expectativa: estável (Frente 4 pode mudar `tipo` se squat aparecer
    como squat_bilateral; nomes em si não mudam)."""
    random.seed(1)
    from gerador_treino import TEMPLATES, TEMPLATE_EPP

    cfg = {
        "padroes": TEMPLATES["Full Body"],
        "exercicios_por_padrao": dict(TEMPLATE_EPP["Full Body"]),
    }
    sessoes = gerar_multiplos_treinos(banco, [cfg] * 4, relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 3: template Empurrar + Posterior ------------------------------------

def test_template_empurrar_puxar_seed7(banco, snapshot):
    """Expectativa: pode mudar com Frente 2 (variacao_de tríceps)."""
    random.seed(7)
    from gerador_treino import TEMPLATES, TEMPLATE_EPP

    cfg = {
        "padroes": TEMPLATES["Empurrar + Posterior"],
        "exercicios_por_padrao": dict(TEMPLATE_EPP["Empurrar + Posterior"]),
    }
    sessoes = gerar_multiplos_treinos(banco, [cfg] * 2, relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 4: caso peito_sem_composto (Etapa 3) -------------------------------

def test_upper_3x2treinos_seed11(banco, snapshot):
    """Expectativa: muda na Etapa 3 (âncoras protegidas vão garantir
    composto de peito em ambos treinos)."""
    random.seed(11)
    cfg = {"demandas": [("regiao", "upper", 3)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg, cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 5: caso 6uni_3bi_0iso (Etapa 3) ------------------------------------

def test_perna_anterior_3x3treinos_seed3(banco, snapshot):
    """Expectativa: muda na Frente 4 (squat refinado em padrões reais) e
    de novo na Etapa 3 (quotas proporcionais)."""
    random.seed(3)
    cfg = {"demandas": [("subregiao", "perna_anterior", 3)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg, cfg, cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 6: viés posterior > anterior (Etapa 2) -----------------------------

def test_perna_posterior_2x2treinos_seed5(banco, snapshot):
    """Expectativa: estável (não atinge a regra de 60% região)."""
    random.seed(5)
    cfg = {"demandas": [("subregiao", "perna_posterior", 2)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg, cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 7: subregião isolada -----------------------------------------------

def test_costas_4x1treino_seed9(banco, snapshot):
    """Expectativa: estável."""
    random.seed(9)
    cfg = {"demandas": [("subregiao", "costas", 4)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 8: peito multi-treino ----------------------------------------------

def test_peito_3x2treinos_seed13(banco, snapshot):
    """Expectativa: estável."""
    random.seed(13)
    cfg = {"demandas": [("subregiao", "peito", 3)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg, cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 9: caso prancha (Etapa 7) ------------------------------------------

def test_core_3x1treino_seed17(banco, snapshot):
    """Expectativa: deve ficar estável após Frente 3 (introdução de
    subregiões internas em core não muda comportamento visível)."""
    random.seed(17)
    cfg = {"demandas": [("regiao", "core", 3)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 10: padrão específico — Frente 4 vai mudar -------------------------

def test_hinge_2_squat_unilateral_2_seed19(banco, snapshot):
    """Expectativa: muda na Frente 4 — `squat` filtrado por lateralidade
    vira `squat_unilateral` direto. `tipo` da sessão e estrutura podem
    mudar; nomes idealmente não."""
    random.seed(19)
    cfg = {
        "demandas": [("padrao", "hinge", 2), ("padrao", "squat", 2)],
        "lateralidade_por_padrao": {"squat": {"unilateral": 2}},
    }
    sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 11: tríceps com relax — Frente 2 vai mudar -------------------------

def test_triceps_2_filtro_familia_relax_seed23(banco, snapshot):
    """Expectativa: muda na Frente 2. Hoje todos os 8 tríceps têm
    `variacao_de = "Tríceps"`, então pedir 2 sem relax falha; com relax,
    seleciona 2 mas marca como `relaxados`. Após Frente 2, ambos vão
    aparecer sem relaxamento."""
    random.seed(23)
    cfg = {"demandas": [("padrao", "triceps", 2)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 12: borda — max_complexidade baixa ----------------------------------

def test_max_complexidade_baixa_seed29(banco, snapshot):
    """Expectativa: estável (filtro hard, não muda nas frentes restantes
    da Etapa 1)."""
    random.seed(29)
    cfg = {"demandas": [("regiao", "upper", 4)], "max_complexidade": 2}
    sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot
