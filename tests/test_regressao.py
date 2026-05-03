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
    """Atualizado na Etapa 2 (Sub-PR 2): pré-alocação global muda a sequência
    de chamadas a random.* (decomposição em sub-demandas + ordenação por
    escassez), então exercícios concretos mudam apesar da seed igual.
    Cobertura clínica preservada (21/21 ex; 1 relax adicional)."""
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
    """Atualizado na Etapa 2 (Sub-PR 2): template Full Body × 4 = 36 vagas
    pedidas; banco esgota em adduction/abduction. Cobertura 33/36 mantida
    (igual antes); novos avisos `incompleta` rotina-level (3) sinalizam os
    3 slots não preenchidos mesmo com relax — antes esses limites eram
    silenciosos. `tipo` da sessão agora reflete demandas convertidas
    (squat → squat_bilateral/squat_unilateral via _normalizar_config)."""
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
    """Atualizado na Etapa 2 (Sub-PR 2): template convertido em demandas
    via _normalizar_config; cobertura 24/24 preservada; 4 relaxados
    (família Apoio + Desenvolvimento esgotam com 2 treinos)."""
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
    """Atualizado na Etapa 2 (Sub-PR 2): cobertura essencial (peito + costas
    + ombro por treino) já garante mais consistência clínica que antes.
    T1 agora tem `Apoio` (composto de peito) — melhoria parcial em direção
    à Etapa 3 (âncoras com obrigatoria=True vão tornar isso determinístico)."""
    random.seed(11)
    cfg = {"demandas": [("regiao", "upper", 3)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg, cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 5: caso 6uni_3bi_0iso (Etapa 3) ------------------------------------

def test_perna_anterior_3x3treinos_seed3(banco, snapshot):
    """Atualizado na Etapa 2 (Sub-PR 2): 9/9 ex preservados; cycling de
    padrões da subregião perna_anterior (squat_bilateral + squat_unilateral)
    cobre bi+uni em cada treino (verificado por
    test_perna_anterior_3x3_cobre_bi_e_uni_em_cada_treino). Etapa 3 vai
    aplicar quotas proporcionais 3:2 via âncoras."""
    random.seed(3)
    cfg = {"demandas": [("subregiao", "perna_anterior", 3)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg, cfg, cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 6: viés posterior > anterior (Etapa 2) -----------------------------

def test_perna_posterior_2x2treinos_seed5(banco, snapshot):
    """Atualizado na Etapa 2 (Sub-PR 2): perna_posterior(2) com 3 padrões
    cai no caso `qtd < n_padroes` da decomposição → sortei 2 dos 3 com seed.
    Distribuição uniforme entre hinge/knee_flexion/abduction (sem peso clínico
    ainda; pesos 3:2:1 chegam na Etapa 3 via ANCORAS_POR_SUBREGIAO)."""
    random.seed(5)
    cfg = {"demandas": [("subregiao", "perna_posterior", 2)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg, cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 7: subregião isolada -----------------------------------------------

def test_costas_4x1treino_seed9(banco, snapshot):
    """Atualizado na Etapa 2 (Sub-PR 2): paridade remadas:puxadas preservada
    (2:2) via _decompor_demanda_subregiao com cycling. Exercícios concretos
    mudam por nova ordem de chamadas a random.*."""
    random.seed(9)
    cfg = {"demandas": [("subregiao", "costas", 4)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 8: peito multi-treino ----------------------------------------------

def test_peito_3x2treinos_seed13(banco, snapshot):
    """Atualizado na Etapa 2 (Sub-PR 2): 6/6 ex cobertos. 2 relaxados
    explicitamente sinalizados (badge ↻) — antes eram silenciosos.
    Mistura composto/isolado mudou (4/2 vs antes 2/4) por causa do cycling
    1+1+1 entre empurrar_compostos e empurrar_isolados."""
    random.seed(13)
    cfg = {"demandas": [("subregiao", "peito", 3)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg, cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 9: caso prancha (Etapa 7) ------------------------------------------

def test_core_3x1treino_seed17(banco, snapshot):
    """Atualizado na Etapa 2 (Sub-PR 2): core(3) decompõe em
    core_dinamico + core_isometrico (1+1+1 ciclado). Mistura din/iso
    preservada; exercícios concretos mudam pela aleatoriedade nova."""
    random.seed(17)
    cfg = {"demandas": [("regiao", "core", 3)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 10: padrão específico — Frente 4 vai mudar -------------------------

def test_hinge_2_squat_unilateral_2_seed19(banco, snapshot):
    """Atualizado na Etapa 2 (Sub-PR 2): demanda padrão (não decomposta);
    `_normalizar_config` traduz `squat` legado em `squat_unilateral` via
    `lateralidade_por_padrao`. Cobertura 2 hinge + 2 squat_uni preservada;
    exercícios concretos mudam."""
    random.seed(19)
    cfg = {
        "demandas": [("padrao", "hinge", 2), ("padrao", "squat", 2)],
        "lateralidade_por_padrao": {"squat": {"unilateral": 2}},
    }
    sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 11: tríceps com relax — Frente 2 vai mudar -------------------------

def test_triceps_2_filtro_familia_relax_seed23(banco, snapshot):
    """Atualizado na Etapa 2 (Sub-PR 2): 2/2 tríceps de famílias distintas
    (refinadas na Frente 2 da Etapa 1), sem relax. Exercícios concretos
    mudam pela nova aleatoriedade."""
    random.seed(23)
    cfg = {"demandas": [("padrao", "triceps", 2)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 12: borda — max_complexidade baixa ----------------------------------

def test_max_complexidade_baixa_seed29(banco, snapshot):
    """Atualizado na Etapa 2 (Sub-PR 2): cobertura essencial em upper(4)
    com max_complexidade=2; exercícios concretos mudam pela aleatoriedade
    nova; filtro complexidade≤2 respeitado em todos."""
    random.seed(29)
    cfg = {"demandas": [("regiao", "upper", 4)], "max_complexidade": 2}
    sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot


# ----- 13: Etapa 4 — full body com filtro HIB2 ON ---------------------------

def test_full_body_4treinos_seed1_HIB2(banco, snapshot):
    """Etapa 4 — congela comportamento com filtro de cargas HIB2 (6/5/6) ATIVO.

    Mesma config do snapshot full_body_4treinos_seed1 mas com cargas_config
    apertando lombar e core. Esperado: pares com lombar 5+ ou core 6 ficam
    bloqueados, alguns blocos podem virar solo (exercício pesado sem par
    pareável). Cobertura clínica avaliada caso-a-caso na regeneração."""
    random.seed(1)
    from gerador_treino import TEMPLATES, TEMPLATE_EPP

    cfg = {
        "padroes": TEMPLATES["Full Body"],
        "exercicios_por_padrao": dict(TEMPLATE_EPP["Full Body"]),
        "cargas_config": {"grip": 6, "lombar": 5, "core": 6},
    }
    sessoes = gerar_multiplos_treinos(banco, [cfg] * 4, relaxar_familia=True)
    assert _rotina_clinica(sessoes) == snapshot
