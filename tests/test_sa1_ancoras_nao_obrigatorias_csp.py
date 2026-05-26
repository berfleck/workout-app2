"""Testes da Frente S-A1 — distribuição entre âncoras NÃO-obrigatórias no CSP.

Spec executável em `docs/refatoracao/catalogo_constraints.md` (seção S-A1).
Origem: handoff `handoff_2026-05-25_s_a1.md` — sondagem 40 seeds revelou:
- ombro(2) CSP 100% (composto+posterior_ombro); antigo 100% (composto+isolado).
- perna_posterior(2) CSP 100% (hinge+abduction); antigo 52%/48% (abd/knee).

A frente tem 2 componentes:
- v1: penalty `(peso_max_nao_obrig - peso_da_ancora) * peso_sa1` por slot×candidato.
  Linear sobre pesos curados 3/2/1 em ANCORAS_POR_SUBREGIAO.
- v2: penalty `peso_sa1_repet * mesmo_padrao(s_i, s_j)` por par dentro de uma
  demanda. Fecha buraco arquitetural do v1 (escape pra obrig+obrig).

Decisões fechadas no handoff:
- v1 forma linear (§5.1).
- v1 ativa em demanda subregião (qtd > n_obrig) E em demanda região via
  marker H-A0 (§5.2 / b — "mais pronto").
- v2 ativa por par dentro de qualquer demanda (subregião e região).
- Calibração 2026-05-25: peso_sa1=12, peso_sa1_repet=10.
- peso_sa1=0 (default) preserva motor pré-S-A1 byte-a-byte.
"""
from __future__ import annotations

from collections import Counter

from gerador_csp import (
    ConfigVariedade,
    gerar_rotina_csp,
    gerar_treino_csp,
)


# ── Helpers ─────────────────────────────────────────────────────────────

def _padroes_do_treino(treino):
    return [e.padrao for g in treino["grupos"] for e in g["exercicios"]]


def _padroes_combo(treino):
    return "+".join(sorted(_padroes_do_treino(treino)))


def _distribuicao_padroes(banco, demandas, n_seeds, peso_sa1, peso_sa1_repet=0,
                          peso_evitar_agon=10):
    """Distribuição de combos de padrões em N seeds. Retorna Counter."""
    contador = Counter()
    for seed in range(n_seeds):
        r = gerar_treino_csp(
            demandas, banco, nivel_aluno=3, seed=seed,
            variedade=ConfigVariedade(),
            peso_evitar_agonistas=peso_evitar_agon,
            tamanho_preferido=2, peso_tamanho_bloco=5,
            relaxar_familia=True,
            peso_sa1=peso_sa1,
            peso_sa1_repet=peso_sa1_repet,
        )
        if r["viavel"]:
            contador[_padroes_combo(r)] += 1
    return contador


# ── (a) Componente v1 — pesos curados não-obrig ─────────────────────────

def test_v1_zero_preserva_motor_pre_sa1(banco):
    """peso_sa1=0 reproduz comportamento pré-S-A1 (ombro(2) → posterior)."""
    c = _distribuicao_padroes(banco, [("subregiao", "ombro", 2)], 10, 0)
    # Pré-S-A1: 100% ombro_composto+posterior_ombro (ZERO ombro_isolado).
    assert c["ombro_composto+posterior_ombro"] == 10, (
        f"peso_sa1=0 deveria preservar baseline pre-S-A1, mas saiu: {c}"
    )


def test_v1_ombro_2_volta_isolado_com_peso_dominante(banco):
    """peso_sa1=12 (>S-B1=10): ombro_isolado deve aparecer ≥80% das rotinas."""
    c = _distribuicao_padroes(banco, [("subregiao", "ombro", 2)], 10, 12,
                              peso_sa1_repet=10)
    com_isolado = sum(qtd for combo, qtd in c.items() if "ombro_isolado" in combo)
    # Calibração 2026-05-25: alvo ≥80%; v2 evita escape pra cmp+cmp.
    assert com_isolado >= 8, (
        f"peso_sa1=12 + repet=10 deveria recuperar ≥80% ombro_isolado, saiu {com_isolado}/10: {c}"
    )


def test_v1_perna_posterior_2_volta_knee(banco):
    """peso_sa1=12: knee_flexion deve aparecer (era 0% pré-S-A1)."""
    c = _distribuicao_padroes(banco, [("subregiao", "perna_posterior", 2)], 10,
                              12, peso_sa1_repet=10)
    com_knee = sum(qtd for combo, qtd in c.items() if "knee_flexion" in combo)
    assert com_knee >= 8, (
        f"peso_sa1=12 + repet=10 deveria recuperar ≥80% knee_flexion, saiu {com_knee}/10: {c}"
    )


def test_v1_peito_2_volta_isolado(banco):
    """peso_sa1=12 + v2=10: empurrar_isolados em pelo menos 80% das rotinas."""
    c = _distribuicao_padroes(banco, [("subregiao", "peito", 3)], 10, 12,
                              peso_sa1_repet=10)
    com_isolado = sum(
        qtd for combo, qtd in c.items() if "empurrar_isolados" in combo
    )
    # peito(3) = 2 obrig (emp_comp) + 1 não-obrig (emp_iso). Mas só 1 obrig:
    # 1 emp_comp obrig + 2 livres. v1 prefere emp_iso (peso 2) sobre nada.
    assert com_isolado >= 8, f"emp_isolados ausente em ≥80%: {c}"


def test_v1_perna_anterior_preservado(banco):
    """perna_anterior(2): bi+uni 100% (antigo e CSP). S-A1 não muda."""
    c = _distribuicao_padroes(banco, [("subregiao", "perna_anterior", 2)], 10,
                              12, peso_sa1_repet=10)
    # Esperado: 100% squat_bilateral+squat_unilateral
    assert c["squat_bilateral+squat_unilateral"] >= 9, (
        f"perna_anterior(2) regrediu: {c}"
    )


# ── (b) Componente v1 não ativa em demanda padrão ───────────────────────

def test_v1_nao_ativa_em_demanda_padrao(banco):
    """Demanda padrão é pedido explícito do user — S-A1 não interfere.

    Em ('padrao', 'posterior_ombro', 2), user pediu 2 posterior_ombro
    explicitamente; solver deve cumprir mesmo com S-A1 ativo. Não há
    'vaga sobrando' a otimizar.
    """
    r = gerar_treino_csp(
        [("padrao", "posterior_ombro", 2)], banco, nivel_aluno=3, seed=0,
        peso_sa1=12, peso_sa1_repet=10,
    )
    assert r["viavel"]
    padroes = _padroes_do_treino(r)
    assert padroes.count("posterior_ombro") == 2, (
        f"demanda padrão deve ser respeitada mesmo com S-A1: {padroes}"
    )


# ── (c) Componente v2 — padrão repetido na mesma demanda ────────────────

def test_v2_zera_hinge_repetido_em_perna_post_2(banco):
    """Buraco arquitetural do v1: solver podia escapar pra hinge+hinge
    (cost S-B1=10 + S-A1=0, igual hinge+knee). v2 com peso=10 zera isso."""
    c = _distribuicao_padroes(banco, [("subregiao", "perna_posterior", 2)], 10,
                              peso_sa1=12, peso_sa1_repet=10)
    assert c.get("hinge+hinge", 0) == 0, (
        f"v2=10 deveria zerar hinge+hinge, mas saiu: {c}"
    )


def test_v2_zera_composto_repetido_em_peito_2(banco):
    """peito(2) sem v2: solver permite empurrar_compostos+empurrar_compostos
    (50% das rotinas em testes). v2=10 zera isso."""
    c = _distribuicao_padroes(banco, [("subregiao", "peito", 2)], 10, 12,
                              peso_sa1_repet=10)
    assert c.get("empurrar_compostos+empurrar_compostos", 0) == 0, (
        f"v2=10 deveria zerar comp+comp: {c}"
    )


def test_v2_zero_preserva_v1_byte_a_byte(banco):
    """peso_sa1_repet=0 + peso_sa1=12 reproduz só v1 (com regressão hinge+hinge)."""
    c = _distribuicao_padroes(banco, [("subregiao", "perna_posterior", 2)], 20,
                              peso_sa1=12, peso_sa1_repet=0)
    # v1 sem v2: hinge+hinge dominante (regressão calibrada — ≥50%).
    hinges = c.get("hinge+hinge", 0)
    assert hinges >= 8, (
        f"v2=0 deveria deixar hinge+hinge predominante, saiu {hinges}/20: {c}"
    )


def test_v2_nao_penaliza_par_cross_demanda(banco):
    """v2 só atua dentro da MESMA demanda. Demandas distintas (mesmo padrão
    coincidindo) não pagam penalty — decisão arquitetural do escopo."""
    # 2 demandas distintas (`peito`+`ombro`) — não há repetição intra-demanda.
    r = gerar_treino_csp(
        [("subregiao", "peito", 1), ("subregiao", "ombro", 1)],
        banco, nivel_aluno=3, seed=0,
        peso_sa1=12, peso_sa1_repet=10,
    )
    assert r["viavel"]


# ── (d) Demanda região (decisão §5.2 / b — "mais pronto") ───────────────

def test_v2_zera_hinge_repetido_em_demanda_regiao(banco):
    """Em demanda região (Full Body / ABC / use real default), v2 também
    deve zerar hinge+hinge no lower."""
    contagem_hinges = 0
    n = 10
    for seed in range(n):
        r = gerar_treino_csp(
            [("regiao", "lower", 4)], banco, nivel_aluno=3, seed=seed,
            variedade=ConfigVariedade(),
            peso_evitar_agonistas=10, tamanho_preferido=2,
            peso_tamanho_bloco=5, peso_sa1=12, peso_sa1_repet=10,
        )
        if not r["viavel"]:
            continue
        padroes = _padroes_do_treino(r)
        if padroes.count("hinge") >= 2:
            contagem_hinges += 1
    # Sem v2: ~55% dos rotinas saíam hinge+hinge.
    # Com v2=10: alvo 0.
    assert contagem_hinges == 0, (
        f"v2=10 em região deveria zerar hinge+hinge, mas saiu em {contagem_hinges}/{n}"
    )


# ── (e) Propagação do argumento pelas 4 saídas do motor ─────────────────

def test_argumentos_propagam_em_gerar_rotina_csp(banco):
    """peso_sa1 e peso_sa1_repet aceitos por gerar_rotina_csp."""
    r = gerar_rotina_csp(
        [[("subregiao", "ombro", 2)]], banco, nivel_aluno=3, seed=0,
        peso_sa1=12, peso_sa1_repet=10,
    )
    assert r["viavel"]


def test_argumentos_propagam_em_gerar_treino_csp(banco):
    """peso_sa1 e peso_sa1_repet aceitos por gerar_treino_csp."""
    r = gerar_treino_csp(
        [("subregiao", "ombro", 2)], banco, nivel_aluno=3, seed=0,
        peso_sa1=12, peso_sa1_repet=10,
    )
    assert r["viavel"]


def test_argumentos_propagam_com_variedade(banco):
    """peso_sa1 propaga pelo branch _resolver_com_variedade (Frente B)."""
    r = gerar_rotina_csp(
        [[("subregiao", "ombro", 2)]], banco, nivel_aluno=3, seed=0,
        variedade=ConfigVariedade(),
        peso_sa1=12, peso_sa1_repet=10,
    )
    assert r["viavel"]
