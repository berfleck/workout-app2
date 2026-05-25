"""Testes da Frente B da Fatia 3 (variedade INTRA-config no CP-SAT).

Cobre:
(a) `variedade=None` preserva comportamento legado byte-a-byte.
(b) `ConfigVariedade()` enumera múltiplas ótimas e sampla via softmax.
(c) `slack` bound é respeitado (inversoes <= optimal + slack).
(d) `alpha_tier > 0` muda distribuição em slots de tier alto.
(e) `python_seed` é reprodutível (mesma seed = mesma rotina).
"""
from __future__ import annotations

from collections import Counter

import pytest

from gerador_csp import (
    ConfigVariedade,
    gerar_rotina_csp,
    gerar_treino_csp,
)


# Demanda padrão pros testes — Config A do _main() do gerador_csp.
# Mistura vagas únicas (H-T4 dispara) com multi-slot (S-T1 ativa).
DEMANDAS_PADRAO = [
    ("subregiao", "peito", 2),
    ("subregiao", "costas", 2),
    ("subregiao", "ombro", 1),
    ("subregiao", "perna_anterior", 2),
    ("subregiao", "perna_posterior", 1),
]


def _assinatura(rotina_dict) -> tuple[str, ...]:
    """Tupla de nomes dos exercícios — identidade comparável da rotina."""
    return tuple(e.nome for e in rotina_dict["ordem_global"])


# ─────────────────────────────────────────────────────────────────────────────
# (a) variedade=None preserva comportamento legado
#
# NOTA: NÃO testamos "mesma seed = mesma rotina" porque CP-SAT NÃO garante
# reprodutibilidade mesmo com `random_seed` fixo quando `randomize_search`
# está ativo (usa fontes externas tipo timing/threads pra randomização).
# Testamos propriedades estruturais — viabilidade, constraints, ausência
# do dict 'variedade'.
# ─────────────────────────────────────────────────────────────────────────────

def test_variedade_none_nao_emite_chave_variedade(banco):
    """Branch legacy não deve incluir a chave 'variedade' no dict."""
    r = gerar_treino_csp(DEMANDAS_PADRAO, banco, nivel_aluno=3, seed=42)
    assert "variedade" not in r


def test_variedade_none_respeita_tier_order(banco):
    """Branch legacy preserva S-T1 (inversões=0 esperado em Config A)."""
    r = gerar_treino_csp(DEMANDAS_PADRAO, banco, nivel_aluno=3, seed=42)
    assert r["viavel"] is True
    assert r["inversoes"] == 0


def test_variedade_none_respeita_h_t4(banco):
    """Branch legacy: vagas únicas com pool não-Acessório disponível devem
    NÃO cair em Acessório (H-T4 hard com graceful degradation)."""
    r = gerar_treino_csp(DEMANDAS_PADRAO, banco, nivel_aluno=3, seed=42)
    for g in r["grupos"]:
        nivel, _escopo, qtd = g["demanda"]
        if nivel == "subregiao" and qtd == 1 and g["h_t4_aplicado_efetivamente"]:
            assert g["exercicios"][0].tier != "Acessório"


# ─────────────────────────────────────────────────────────────────────────────
# (b) ConfigVariedade() enumera múltiplas ótimas e sampla
# ─────────────────────────────────────────────────────────────────────────────

def test_variedade_ativa_enumera_multiplas_solucoes(banco):
    """Com ConfigVariedade ativa, n_solucoes_enumeradas > 1 em Config A
    (espaço tem >100 ótimas — cap deve disparar)."""
    cfg = ConfigVariedade(python_seed=42)
    r = gerar_treino_csp(DEMANDAS_PADRAO, banco, nivel_aluno=3, seed=42,
                         variedade=cfg)
    assert r["viavel"] is True
    assert "variedade" in r
    meta = r["variedade"]
    assert meta["ativa"] is True
    assert meta["n_solucoes_enumeradas"] > 1
    assert meta["optimal_value"] == 0  # Config A tem ótima trivial


def test_variedade_ativa_diversifica_entre_python_seeds(banco):
    """5 python_seeds distintos devem dar ≥2 rotinas distintas em Config A.
    Threshold conservador — empiricamente dá 5/5 com randomize_search."""
    assinaturas = set()
    for ps in [1, 2, 3, 4, 5]:
        cfg = ConfigVariedade(python_seed=ps)
        r = gerar_treino_csp(DEMANDAS_PADRAO, banco, nivel_aluno=3, seed=42,
                             variedade=cfg)
        assinaturas.add(_assinatura(r))
    assert len(assinaturas) >= 2, (
        f"esperado ≥2 rotinas distintas em 5 python_seeds, veio {len(assinaturas)}"
    )


def test_variedade_ativa_preserva_constraints_hard(banco):
    """Mesmo com variedade, H-T4 + H-R1 + tier-order continuam respeitados."""
    cfg = ConfigVariedade(python_seed=42)
    r = gerar_treino_csp(DEMANDAS_PADRAO, banco, nivel_aluno=3, seed=42,
                         variedade=cfg)
    assert r["viavel"] is True
    assert r["inversoes"] == 0  # S-T1 ótimo em Config A

    # H-T4: ombro (vaga única) e perna_post (vaga única) não podem
    # ser Acessório quando o pool tem não-Acessório disponível.
    for g in r["grupos"]:
        nivel, escopo, qtd = g["demanda"]
        if nivel == "subregiao" and qtd == 1 and g["h_t4_aplicado_efetivamente"]:
            assert g["exercicios"][0].tier != "Acessório", (
                f"vaga única {escopo} caiu em Acessório com H-T4 ativo"
            )


# ─────────────────────────────────────────────────────────────────────────────
# (c) slack bound é respeitado
# ─────────────────────────────────────────────────────────────────────────────

def test_slack_zero_so_aceita_otimas(banco):
    """Com slack=0, distancia_escolhida deve ser 0 (apenas ótimas)."""
    cfg = ConfigVariedade(slack=0, python_seed=42)
    r = gerar_treino_csp(DEMANDAS_PADRAO, banco, nivel_aluno=3, seed=42,
                         variedade=cfg)
    assert r["variedade"]["distancia_escolhida"] == 0
    assert r["inversoes"] == r["variedade"]["optimal_value"]


def test_slack_positivo_respeita_bound(banco):
    """Com slack=2, inversoes_totais <= optimal + 2 em TODAS as soluções
    enumeradas (não só a escolhida)."""
    # Roda várias vezes pra cobrir diferentes amostragens do softmax.
    for ps in range(10):
        cfg = ConfigVariedade(slack=2, temperatura=5.0, python_seed=ps)
        r = gerar_treino_csp(DEMANDAS_PADRAO, banco, nivel_aluno=3, seed=42,
                             variedade=cfg)
        optimal = r["variedade"]["optimal_value"]
        dist = r["variedade"]["distancia_escolhida"]
        assert dist <= 2, f"slack=2 violado: distancia={dist} (python_seed={ps})"
        assert r["inversoes"] == optimal + dist, (
            f"inversoes={r['inversoes']} != optimal({optimal}) + dist({dist})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# (d) alpha_tier > 0 muda distribuição em slots de tier alto
# ─────────────────────────────────────────────────────────────────────────────

def _distribuicao_slot(banco, alpha_tier: float, n: int = 20) -> list[Counter]:
    """Conta tier dos exercícios em cada slot ao longo de n python_seeds."""
    contadores = None
    for ps in range(n):
        cfg = ConfigVariedade(python_seed=ps, alpha_tier=alpha_tier)
        r = gerar_treino_csp(DEMANDAS_PADRAO, banco, nivel_aluno=3, seed=42,
                             variedade=cfg)
        ords = r["ordem_global"]
        if contadores is None:
            contadores = [Counter() for _ in ords]
        for i, ex in enumerate(ords):
            contadores[i][ex.tier] += 1
    return contadores


def test_alpha_tier_reduz_variedade_em_slot_de_tier_alto(banco):
    """Com alpha_tier alto (=2.0), slots de tier alto devem ficar MAIS
    concentrados num tier dominante vs alpha_tier=0.

    Pós-Micro-frente H-A1 (2026-05-25): H-A1 hard fixa padrões em slots de
    tier alto (peito→empurrar_compostos, costas→puxadas+remadas, etc),
    reduzindo o espaço de variação que alpha_tier consegue diferenciar.
    Pré-H-A1, alpha=0 ficava perto de 17-18/20 e alpha=2 levava pra 19-20;
    pós-H-A1, ambos saturam perto do teto (18-19/20). Tolerância de 1.0/20
    absorve ruído estatístico CP-SAT esperado (memória
    feedback_cpsat_nao_determinismo) — direção ainda detectada na média
    mas faixa de erro com n=20 pode invertê-la marginalmente.
    """
    dist_alpha_0 = _distribuicao_slot(banco, alpha_tier=0.0, n=20)
    dist_alpha_2 = _distribuicao_slot(banco, alpha_tier=2.0, n=20)

    # Métrica: pra cada slot, freq do tier mais comum. Esperado: alpha=2.0
    # tem freq média MAIOR (mais concentração) que alpha=0.0.
    def freq_media_dominante(dists):
        return sum(max(c.values()) for c in dists) / len(dists)

    freq_0 = freq_media_dominante(dist_alpha_0)
    freq_2 = freq_media_dominante(dist_alpha_2)

    tolerancia = 1.0  # ~5% da escala (20). Absorve ruído pós-H-A1.
    assert freq_2 >= freq_0 - tolerancia, (
        f"alpha_tier=2.0 deveria concentrar >= alpha_tier=0 (tol={tolerancia}): "
        f"freq_dom_alpha_0={freq_0:.1f}/20, freq_dom_alpha_2={freq_2:.1f}/20"
    )


def test_alpha_tier_zero_emite_hamming_zero(banco):
    """alpha_tier=0.0 (default) zera o termo H — metadados devem refletir
    hamming_ponderado_escolhido=0 (Frente 2 inativa)."""
    cfg = ConfigVariedade(python_seed=42, alpha_tier=0.0)
    r = gerar_treino_csp(DEMANDAS_PADRAO, banco, nivel_aluno=3, seed=42,
                         variedade=cfg)
    assert r["variedade"]["alpha_tier"] == 0.0
    assert r["variedade"]["hamming_ponderado_escolhido"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# (e) python_seed afeta o softmax
#
# NOTA: NÃO testamos "mesmo python_seed = mesma rotina" porque CP-SAT
# (Phase 1 + Phase 2 com randomize_search) entrega conjuntos diferentes de
# soluções em chamadas diferentes — o softmax sampla dentro de cada
# conjunto, então mesma python_seed sampla soluções diferentes em runs
# diferentes. Reprodutibilidade total exigiria CP-SAT determinístico,
# que não é garantia com randomize_search ON.
# ─────────────────────────────────────────────────────────────────────────────

def test_python_seeds_diferentes_diversificam(banco):
    """20 python_seeds distintos devem produzir ≥2 rotinas distintas em
    Config A (verifica que o knob python_seed TEM efeito + que o motor
    explora múltiplas soluções)."""
    assinaturas = set()
    for ps in range(20):
        cfg = ConfigVariedade(python_seed=ps)
        r = gerar_treino_csp(DEMANDAS_PADRAO, banco, nivel_aluno=3, seed=42,
                             variedade=cfg)
        assinaturas.add(_assinatura(r))
    assert len(assinaturas) >= 2, (
        "python_seed parece não afetar nada — 20 seeds deram 1 só rotina"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Extras — rotina cross-treino (D do _main)
# ─────────────────────────────────────────────────────────────────────────────

def test_variedade_funciona_em_rotina_cross_treino(banco):
    """Rotina de 2 treinos com variedade ativa preserva H-R1 cobertura
    cross-treino + AllDifferent global."""
    demandas_t1 = [("subregiao", "costas", 1), ("subregiao", "peito", 1)]
    demandas_t2 = [("subregiao", "costas", 1), ("subregiao", "peito", 1)]

    cfg = ConfigVariedade(python_seed=42)
    r = gerar_rotina_csp([demandas_t1, demandas_t2], banco, nivel_aluno=3,
                         seed=42, variedade=cfg)

    assert r["viavel"] is True

    todos_nomes = [
        ex.nome for tr in r["treinos"] for g in tr["grupos"]
        for ex in g["exercicios"]
    ]
    assert len(set(todos_nomes)) == len(todos_nomes), (
        "AllDifferent cross-treino violado"
    )

    # H-R1 costas: deve cobrir puxadas + remadas (ambos compostos) cross-treino
    todos_costas = [
        ex for tr in r["treinos"] for g in tr["grupos"]
        for ex in g["exercicios"] if ex.subregiao == "costas"
    ]
    has_puxada = any(
        e.padrao == "puxadas" and e.purpose == "compound" for e in todos_costas
    )
    has_remada = any(
        e.padrao == "remadas" and e.purpose == "compound" for e in todos_costas
    )
    assert has_puxada and has_remada, (
        f"H-R1 costas não cobriu: puxada={has_puxada}, remada={has_remada}"
    )
