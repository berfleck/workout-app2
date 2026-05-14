"""Testes específicos de problema — cada um descreve um problema clínico
conhecido que será resolvido por uma etapa futura da refatoração.

Todos marcados `xfail(strict=True)`:
- Falham hoje → status XFAIL (esperado).
- Quando a etapa que os resolve landar, eles passam → strict faz o suite
  quebrar (sinal de promoção pra `must pass` com remoção do decorator).

Quando promover: remover o `@pytest.mark.xfail(...)` do teste e rodar
`pytest` pra confirmar PASS limpo. Commit isolado.
"""
from __future__ import annotations

import random
from collections import Counter

import pytest

from gerador_treino import (
    PURPOSE_COMPOSTO,
    gerar_multiplos_treinos,
)


def _exercicios(sessao):
    for b in sessao.blocos:
        for ex in (b.ex1, b.ex2, b.ex3):
            if ex:
                yield ex


def _all_exercicios(sessoes):
    for s in sessoes:
        yield from _exercicios(s)


# ----- 1: viés posterior > anterior em lower(N) — Etapa 2 (RESOLVIDO) ------


def test_lower_4_distribui_anterior_e_posterior_balanceado(banco):
    """Em 100 rotinas lower(4), a razão posterior/anterior deve ficar
    próxima de 1.0.

    RESOLVIDO na Etapa 2 (pré-alocação global com cobertura essencial):
    `lower(4)` decompõe em 2 perna_anterior + 2 perna_posterior (ambas
    essenciais, acessórias não competem pois 4 NÃO > 2×2). Razão tende a
    1.0 deterministicamente."""
    from tests.harness import simular_rotina

    cfg = {"demandas": [("regiao", "lower", 4)]}
    r = simular_rotina(banco, [cfg], n_iteracoes=100, seed_base=2000)
    media = r["razao_posterior_anterior_lower"]["media"]
    assert media is not None
    assert 0.7 <= media <= 1.4, f"razao posterior/anterior média = {media:.2f}"


# ----- 2: composto de cada âncora em upper(3) × 2 — Etapa 3 ---------------


def test_upper_3x2treinos_tem_composto_de_cada_ancora(banco):
    """Em 100 rotinas upper(3) × 2 treinos, ambos treinos devem ter pelo
    menos 1 composto de peito (empurrar_compostos). Hoje há rotinas onde
    peito aparece só como Crossover (isolado)."""
    falhas = 0
    for seed in range(2000, 2100):
        random.seed(seed)
        cfg = {"demandas": [("regiao", "upper", 3)]}
        sessoes = gerar_multiplos_treinos(banco, [cfg, cfg], relaxar_familia=True)
        for s in sessoes:
            tem_composto_peito = any(
                ex.padrao == "empurrar_compostos" for ex in _exercicios(s)
            )
            if not tem_composto_peito:
                falhas += 1
    assert falhas <= 5, f"{falhas}/200 sessões sem composto de peito"


# ----- 3: quota proporcional 3:2 em perna_anterior(3)x3 — Etapa 3 ---------


def test_perna_anterior_3x3_respeita_quota_3_2(banco):
    """Em 100 rotinas perna_anterior(3) × 3, distribuição
    bilateral:unilateral deve aproximar 3:2 (proporção dos pesos),
    não 1:2 (proporção do banco).

    Etapa 7 Fase 7.2: razão observada caiu de ~1.5 pra ~1.2 quando o
    predicado D1 fixou família INTRA hard mesmo no relax. Antes, o
    relax permitia 2 "Agachamento" no mesmo treino (over-permissivo),
    inflando bilaterals via repetição da mesma família. Agora a
    Hamilton em 9 vagas (3 treinos × 3) com peso 3:2 entrega 5 bi + 4
    uni = ratio 1.25, mais próximo da quota verdadeira."""
    bi_total = 0
    uni_total = 0
    for seed in range(3000, 3100):
        random.seed(seed)
        cfg = {"demandas": [("subregiao", "perna_anterior", 3)]}
        sessoes = gerar_multiplos_treinos(banco, [cfg, cfg, cfg], relaxar_familia=True)
        for ex in _all_exercicios(sessoes):
            # Frente 4: padrão refinado em squat_bilateral / squat_unilateral
            if ex.padrao == "squat_bilateral":
                bi_total += 1
            elif ex.padrao == "squat_unilateral":
                uni_total += 1
    razao = bi_total / max(uni_total, 1)
    # Esperado pós-Etapa 7 Fase 7.2: ~ 5/4 = 1.25 (Hamilton em 9 vagas).
    # Range tolera flutuação de seed; antes era ~1.5 com over-permissivo relax.
    assert 1.0 <= razao <= 1.8, (
        f"bi:uni = {bi_total}:{uni_total} (razao={razao:.2f}), "
        "esperado ~1.25 (Hamilton 9 vagas peso 3:2)"
    )


# ----- 4: distribuição 3:2:1 em perna_posterior(6) — Etapa 3 --------------


def test_perna_posterior_6_distribui_hinge_kneeflex_abducao_3_2_1(banco):
    """Em 100 rotinas perna_posterior(6) × 1, distribuição
    hinge:knee_flexion:abduction deve aproximar 3:2:1."""
    cont = Counter()
    for seed in range(4000, 4100):
        random.seed(seed)
        cfg = {"demandas": [("subregiao", "perna_posterior", 6)]}
        sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
        for ex in _all_exercicios(sessoes):
            cont[ex.padrao] += 1
    h, k, a = cont["hinge"], cont["knee_flexion"], cont["abduction"]
    total = h + k + a
    assert total > 0
    # Razões esperadas: h/total ≈ 0.5, k/total ≈ 0.33, a/total ≈ 0.17
    assert 0.40 <= h / total <= 0.60, f"hinge fração = {h/total:.2f}"
    assert 0.25 <= k / total <= 0.40, f"knee_flexion fração = {k/total:.2f}"
    assert 0.10 <= a / total <= 0.25, f"abduction fração = {a/total:.2f}"


# ----- 5: paridade remadas vs puxadas em costas(4) — JÁ SATISFEITO --------


def test_costas_4_distribui_remadas_e_puxadas_paritarias(banco):
    """Em 100 rotinas costas(4) × 1, razão remadas:puxadas próxima de 1:1.

    NOTA: medição em 500 seeds mostrou (2,2) em 100% dos casos — o cycle
    de Opção C com 2 padrões já alterna naturalmente. A Etapa 3 (âncoras
    costas paritárias) vai *formalizar* esse comportamento; este teste
    fica como guarda contra regressão durante a refatoração."""
    rem = 0
    puxa = 0
    for seed in range(5000, 5100):
        random.seed(seed)
        cfg = {"demandas": [("subregiao", "costas", 4)]}
        sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
        for ex in _all_exercicios(sessoes):
            if ex.padrao == "remadas":
                rem += 1
            elif ex.padrao == "puxadas":
                puxa += 1
    razao = rem / max(puxa, 1)
    assert 0.80 <= razao <= 1.25, (
        f"remadas:puxadas = {rem}:{puxa} (razao={razao:.2f}), esperado ~1.0"
    )


# ----- 6: cobertura bi+uni dentro de cada treino — Frente 4 (RESOLVIDO) ---


def test_perna_anterior_3x3_cobre_bi_e_uni_em_cada_treino(banco):
    """Em 100 rotinas perna_anterior(3) × 3, ≥ 80% dos treinos individuais
    devem ter pelo menos 1 squat bilateral E 1 squat unilateral.

    RESOLVIDO na Frente 4 da Etapa 1: squat virou 2 padrões reais
    (squat_bilateral + squat_unilateral), e o cycling do `_selecionar_ciclando`
    em demandas de subregião naturalmente cobre os 2 padrões antes de repetir.
    A Etapa 3 (hierarquia treino > rotina) vai *formalizar* isso via quotas;
    este teste fica como guarda contra regressão durante a refatoração."""
    treinos_completos = 0
    treinos_total = 0
    for seed in range(6000, 6100):
        random.seed(seed)
        cfg = {"demandas": [("subregiao", "perna_anterior", 3)]}
        sessoes = gerar_multiplos_treinos(banco, [cfg, cfg, cfg], relaxar_familia=True)
        for s in sessoes:
            treinos_total += 1
            tem_bi = any(
                ex.padrao == "squat_bilateral" for ex in _exercicios(s)
            )
            tem_uni = any(
                ex.padrao == "squat_unilateral" for ex in _exercicios(s)
            )
            if tem_bi and tem_uni:
                treinos_completos += 1
    fracao = treinos_completos / treinos_total
    assert fracao >= 0.80, (
        f"{treinos_completos}/{treinos_total} treinos cobrem bi+uni "
        f"({fracao:.0%})"
    )


# ----- 7: aviso ancora_nao_cumprida em costas(1) — Etapa 3 ----------------


def test_costas_1x1_gera_aviso_ancora_nao_cumprida(banco):
    """Em costas(1) × 1, só uma vaga mas remadas e puxadas são ambas
    obrigatórias. Deve gerar aviso `ancora_nao_cumprida` (tipo de aviso
    introduzido na Etapa 3)."""
    random.seed(7000)
    cfg = {"demandas": [("subregiao", "costas", 1)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    avisos = sum(([a for a in s.avisos if a.get("tipo") == "ancora_nao_cumprida"]
                  for s in sessoes), [])
    assert avisos, "esperado aviso 'ancora_nao_cumprida'"


# ----- 8: nunca 3 pranchas em core(3) — JÁ SATISFEITO ---------------------


def test_core_3_nao_gera_3_pranchas_iguais(banco):
    """Em 1000 rotinas core(3) × 1, nenhuma deve ter 3 exercícios cujo
    nome começa com 'Prancha'.

    NOTA: medição em 1000 seeds mostrou 0/1000 — variacao_de='Prancha'
    no banco já bloqueia o caso via filtro estrito de família. A Etapa 7
    (tags multi-dimensionais) vai modelar isso de forma mais expressiva,
    mas o invariante atual já vale. Guarda contra regressão se o filtro
    estrito for relaxado durante refator."""
    rotinas_com_3_pranchas = 0
    for seed in range(8000, 9000):
        random.seed(seed)
        cfg = {"demandas": [("regiao", "core", 3)]}
        sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
        for s in sessoes:
            n_pranchas = sum(
                1 for ex in _exercicios(s) if ex.nome.lower().startswith("prancha")
            )
            if n_pranchas >= 3:
                rotinas_com_3_pranchas += 1
    assert rotinas_com_3_pranchas == 0, (
        f"{rotinas_com_3_pranchas}/1000 rotinas com 3 pranchas"
    )


# ----- 9: tríceps Francesa + Polia em triceps(2) — Frente 2 (RESOLVIDO) --


def test_triceps_2_aceita_francesa_e_polia(banco):
    """Em 100 rotinas triceps(2) × 1 modo estrito (sem relax), deve
    sempre conseguir 2 tríceps distintos.

    RESOLVIDO na Frente 2 da Etapa 1: `variacao_de` foi refinado dos
    8 tríceps em 5 famílias estritas (Pushdown, Coice, Francês, Testa,
    Mergulho), tornando matematicamente possível pegar 2 sem relax."""
    falhas = 0
    for seed in range(9000, 9100):
        random.seed(seed)
        cfg = {"demandas": [("padrao", "triceps", 2)]}
        sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=False)
        nomes = [ex.nome for ex in _all_exercicios(sessoes)]
        if len(nomes) < 2:
            falhas += 1
    assert falhas == 0, f"{falhas}/100 rotinas falharam em obter 2 tríceps"


# ----- 10: pareamento V-Up Uni + Tríceps Uni — Etapa 5 -------------------


def test_v_up_uni_pareia_com_triceps_uni_nao_com_hollow(banco):
    """Cenário: 2 unilaterais (V-Up Unilateral + Tríceps Unilateral Polia)
    + 1 isométrico extra. Pareamento ideal: V-Up Uni ↔ Tríceps Uni
    (regiões diferentes, contraste muscular), isométrico solo.

    Resolvido na Etapa 5 (Sub-PR 5.2): score de pareamento substituiu a
    cascata determinística + regra anti-uni cega. Anti-uni virou penalty
    sensível a contraste muscular: -75 mesmo grupo, -10 grupos diferentes.
    V-Up Uni + Tríceps Uni: +1000 (regiao diff) +100 (pad diff) +50
    (não-agonista) -10 (uni-uni cross-group) = +1140 vs Hollow Hold +50."""
    nomes_alvo = {"V-Up Unilateral", "Tríceps Unilateral Polia"}
    travados_dispon = [e for e in banco if e.nome in nomes_alvo]
    if len(travados_dispon) < 2:
        pytest.skip(
            f"banco não tem todos: {nomes_alvo} (achou {[e.nome for e in travados_dispon]})"
        )

    aciertos = 0
    for seed in range(10000, 10050):
        random.seed(seed)
        cfg = {
            "demandas": [("padrao", "core_isometrico", 1)],
            "exercicios_travados": travados_dispon,
            "tamanho_bloco": 2,
        }
        sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
        for s in sessoes:
            for b in s.blocos:
                nomes_b = {ex.nome for ex in (b.ex1, b.ex2, b.ex3) if ex}
                if nomes_alvo.issubset(nomes_b):
                    aciertos += 1
                    break
    fracao = aciertos / 50
    assert fracao >= 0.50, (
        f"{aciertos}/50 rotinas pareiam V-Up Uni + Tríceps Uni "
        f"({fracao:.0%}); esperado ≥ 50%"
    )


# ----- 11: ('subregiao', 'core', N) retrocompat — Frente 3 + Etapa 8.3 ----


def test_subregiao_core_legada_aloca_qtd_pedida(banco):
    """Demanda legada `("subregiao", "core", N)` aloca N exercícios entre
    core_isometrico + core_dinamico — sem aviso `qtd_obtida=0`.

    Bug item 1 da 8.15.7: pré-Etapa 8.3 a demanda falhava com qtd_obtida=0
    porque `_decompor_demanda_subregiao("core", N)` consultava
    `SUBREGIAO_PARA_PADROES["core"]` que não existe (só core_iso/core_din
    separadas). Etapa 8.3 introduziu `_SUBREGIOES_LEGADAS = {"core":
    ("core_isometrico", "core_dinamico")}` + tratamento no decompositor
    que divide N entre as filhas via Hamilton ceil/floor + cycling.

    Workaround inline em `_padroes_de_escopo` consolidado via mesma
    estrutura `_SUBREGIOES_LEGADAS`. Configs antigas salvas em SQLite ou
    cenários do harness com `("subregiao", "core", N)` continuam funcionando.
    """
    for N in (1, 2, 3, 4):
        for seed in (7, 42, 123):
            random.seed(seed)
            cfg = {"demandas": [("subregiao", "core", N)]}
            sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
            s = sessoes[0]
            n_obtido = sum(1 for _ in _exercicios(s))
            assert n_obtido == N, (
                f"N={N} seed={seed}: alocou {n_obtido} ex (esperado {N}). "
                f"Avisos: {s.avisos}"
            )
            # Nenhum aviso de incompleta pra demanda core legada
            avisos_incompleta = [a for a in s.avisos if a.get("tipo") == "incompleta"]
            assert avisos_incompleta == [], (
                f"N={N} seed={seed}: avisos incompleta inesperados: "
                f"{avisos_incompleta}"
            )
