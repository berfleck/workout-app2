"""Testes unitários puros de calcular_quotas (Sub-PR 1 da Etapa 3).

calcular_quotas é função pura — não depende de banco, não tem efeito colateral.
Recebe (ancoras, vagas) e devolve {chave: qtd} + lista de avisos sobre
o cumprimento das obrigatórias.
"""
from __future__ import annotations

import random

from gerador_treino import calcular_quotas


# ─── Caso simples: peso uniforme ────────────────────────────────────────


def test_quota_costas_4_paritaria():
    """costas(4): remadas:2 puxadas:2 (ambas obrig) → 2:2."""
    ancoras = [
        {"chave": "remadas", "peso": 2, "obrigatoria": True},
        {"chave": "puxadas", "peso": 2, "obrigatoria": True},
    ]
    quotas, avisos = calcular_quotas(ancoras, vagas=4)
    assert quotas == {"remadas": 2, "puxadas": 2}
    assert avisos == []


def test_quota_costas_3_tie_break_sorteado_em_empate_total():
    """costas(3): pesos 2:2 dão tie em (obrig, peso, resto).

    Tie-break final é sorteado (random.random()), não pela ordem de definição.
    Invariantes preserváveis: total = 3; ambas com qtd >= 1; vencedora do +1
    pode ser qualquer uma das duas. Determinismo via seed.
    """
    ancoras = [
        {"chave": "remadas", "peso": 2, "obrigatoria": True},
        {"chave": "puxadas", "peso": 2, "obrigatoria": True},
    ]
    random.seed(0)
    quotas, _ = calcular_quotas(ancoras, vagas=3)
    assert set(quotas.keys()) == {"remadas", "puxadas"}
    assert sum(quotas.values()) == 3
    assert min(quotas.values()) == 1 and max(quotas.values()) == 2


# ─── Hamilton com pesos diferenciados ──────────────────────────────────


def test_quota_perna_posterior_6_distribui_3_2_1():
    """perna_posterior(6) com pesos 3:2:1 → 3:2:1 exato."""
    ancoras = [
        {"chave": "hinge", "peso": 3, "obrigatoria": True},
        {"chave": "knee_flexion", "peso": 2, "obrigatoria": False},
        {"chave": "abduction", "peso": 1, "obrigatoria": False},
    ]
    quotas, avisos = calcular_quotas(ancoras, vagas=6)
    assert quotas == {"hinge": 3, "knee_flexion": 2, "abduction": 1}
    assert avisos == []


def test_quota_perna_anterior_9_distribui_5_4():
    """perna_anterior(3)x3=9 vagas globais com pesos 3:2 → 5:4 (Hamilton)."""
    ancoras = [
        {"chave": "squat_bilateral", "peso": 3, "obrigatoria": True},
        {"chave": "squat_unilateral", "peso": 2, "obrigatoria": False},
    ]
    quotas, _ = calcular_quotas(ancoras, vagas=9)
    # 9 × 3/5 = 5.4; 9 × 2/5 = 3.6 → floor (5,3) resto (0.4, 0.6) → +1 segundo
    assert quotas == {"squat_bilateral": 5, "squat_unilateral": 4}


def test_quota_peito_2_um_de_cada():
    """peito(2) com pesos 3:2 → 1 comp + 1 iso (mínimos contam na proporção)."""
    ancoras = [
        {"chave": "empurrar_compostos", "peso": 3, "obrigatoria": True},
        {"chave": "empurrar_isolados", "peso": 2, "obrigatoria": False},
    ]
    quotas, avisos = calcular_quotas(ancoras, vagas=2)
    # 2 × 3/5 = 1.2; 2 × 2/5 = 0.8 → floor (1, 0) resto (0.2, 0.8) → +1 segundo
    assert quotas == {"empurrar_compostos": 1, "empurrar_isolados": 1}
    assert avisos == []


# ─── Vagas < num_obrigatorias: sorteio + aviso ─────────────────────────


def test_quota_costas_1_sorteia_obrigatoria_e_emite_aviso():
    """costas(1): 1 vaga mas remadas+puxadas obrigatórias. Sorteia e avisa."""
    random.seed(7000)
    ancoras = [
        {"chave": "remadas", "peso": 2, "obrigatoria": True},
        {"chave": "puxadas", "peso": 2, "obrigatoria": True},
    ]
    quotas, avisos = calcular_quotas(ancoras, vagas=1)
    assert sum(quotas.values()) == 1
    assert set(quotas.keys()) <= {"remadas", "puxadas"}
    # Exatamente 1 obrigatória ficou de fora
    nao_cumpridas = [a for a in avisos if a["tipo"] == "ancora_nao_cumprida"]
    assert len(nao_cumpridas) == 1
    nome_fora = nao_cumpridas[0]["chave"]
    assert nome_fora in {"remadas", "puxadas"}
    assert nome_fora not in quotas or quotas[nome_fora] == 0


def test_quota_costas_0_zero_quotas_zero_avisos():
    """vagas=0: quotas vazias, sem aviso (caso degenerado)."""
    ancoras = [
        {"chave": "remadas", "peso": 2, "obrigatoria": True},
    ]
    quotas, avisos = calcular_quotas(ancoras, vagas=0)
    assert quotas == {}
    assert avisos == []


# ─── Tie-break: obrigatórias > peso maior > ordem ──────────────────────


def test_quota_tie_break_obrigatoria_ganha_de_opcional():
    """Empate de resto: âncora obrigatória ganha de opcional."""
    # peso 1:1 com 1 vaga: empate de proporção (0.5 vs 0.5)
    # Obrigatória deve ganhar
    ancoras = [
        {"chave": "opcional", "peso": 1, "obrigatoria": False},
        {"chave": "obrig", "peso": 1, "obrigatoria": True},
    ]
    random.seed(42)
    quotas, _ = calcular_quotas(ancoras, vagas=1)
    assert quotas.get("obrig", 0) == 1
    assert quotas.get("opcional", 0) == 0


def test_quota_tie_break_peso_maior_quando_ambas_opcionais():
    """Empate entre não-obrigatórias: peso maior ganha."""
    ancoras = [
        {"chave": "a", "peso": 1, "obrigatoria": False},
        {"chave": "b", "peso": 2, "obrigatoria": False},
        {"chave": "c", "peso": 1, "obrigatoria": False},
    ]
    # vagas=2: 2×(1/4, 2/4, 1/4) = (0.5, 1.0, 0.5)
    # floor (0, 1, 0); resto (0.5, 0.0, 0.5); empate entre a e c.
    # peso_maior tie-break: ambas peso 1 → ordem definição (a vence)
    quotas, _ = calcular_quotas(ancoras, vagas=2)
    assert quotas.get("a", 0) == 1
    assert quotas.get("b", 0) == 1
    assert quotas.get("c", 0) == 0


# ─── Determinismo ──────────────────────────────────────────────────────


def test_quota_determinismo_com_seed():
    """Mesma seed → mesmas quotas (sorteio interno determinístico)."""
    ancoras = [
        {"chave": "remadas", "peso": 2, "obrigatoria": True},
        {"chave": "puxadas", "peso": 2, "obrigatoria": True},
    ]
    random.seed(99)
    q1, _ = calcular_quotas(ancoras, vagas=1)
    random.seed(99)
    q2, _ = calcular_quotas(ancoras, vagas=1)
    assert q1 == q2


def test_quota_seeds_diferentes_em_caso_de_sorteio():
    """Em vagas<obrig (caso sorteio), seeds diferentes podem gerar quotas diferentes."""
    ancoras = [
        {"chave": "remadas", "peso": 2, "obrigatoria": True},
        {"chave": "puxadas", "peso": 2, "obrigatoria": True},
    ]
    obtidos = set()
    for s in range(50):
        random.seed(s)
        q, _ = calcular_quotas(ancoras, vagas=1)
        obtidos.add(tuple(sorted(q.items())))
    # Esperado ver tanto (remadas:1) quanto (puxadas:1) ao longo de 50 seeds
    assert len(obtidos) >= 2


# ─── Edge case: 1 âncora só ────────────────────────────────────────────


def test_quota_panturrilha_sozinha():
    """panturrilha tem 1 âncora só (flexao_plantar). Pega tudo."""
    ancoras = [
        {"chave": "flexao_plantar", "peso": 1, "obrigatoria": True},
    ]
    quotas, _ = calcular_quotas(ancoras, vagas=3)
    assert quotas == {"flexao_plantar": 3}


# ─── Edge case: lista vazia (subregião sem âncoras) ────────────────────


def test_quota_lista_vazia():
    """Sem âncoras definidas (core_dinamico/core_isometrico) → vazio."""
    quotas, avisos = calcular_quotas([], vagas=3)
    assert quotas == {}
    assert avisos == []


# ─── Invariantes (devem valer pra qualquer config) ─────────────────────


def test_quota_invariante_soma_igual_a_vagas():
    """Sum(quotas.values()) == vagas (exceto quando lista de âncoras vazia)."""
    casos = [
        ([{"chave": "a", "peso": 1, "obrigatoria": True}], 5),
        ([
            {"chave": "a", "peso": 3, "obrigatoria": True},
            {"chave": "b", "peso": 2, "obrigatoria": False},
        ], 7),
        ([
            {"chave": "a", "peso": 2, "obrigatoria": True},
            {"chave": "b", "peso": 2, "obrigatoria": True},
            {"chave": "c", "peso": 1, "obrigatoria": True},
        ], 11),
    ]
    for ancoras, vagas in casos:
        random.seed(1)
        quotas, _ = calcular_quotas(ancoras, vagas)
        assert sum(quotas.values()) == vagas, (
            f"ancoras={ancoras} vagas={vagas} quotas={quotas}"
        )


def test_quota_invariante_chaves_subset_das_ancoras():
    """Toda chave em quotas vem de uma âncora."""
    ancoras = [
        {"chave": "a", "peso": 3, "obrigatoria": True},
        {"chave": "b", "peso": 1, "obrigatoria": False},
    ]
    chaves_validas = {a["chave"] for a in ancoras}
    for vagas in range(0, 20):
        random.seed(vagas)
        quotas, _ = calcular_quotas(ancoras, vagas)
        assert set(quotas.keys()) <= chaves_validas


def test_quota_invariante_obrigatoria_cumprida_em_ancoras_reais():
    """Para os pesos clínicos reais (ANCORAS_POR_*), obrigatórias têm qtd >= 1
    quando vagas >= num_obrigatorias.

    NOTA: Hamilton puro NÃO garante obrigatórias em todos os pesos — uma
    não-obrigatória com peso muito superior pode dominar todas as vagas.
    Os pesos clínicos definidos (ratio máximo 3:1) não disparam esse edge
    case. Este teste prova que a calibração real é segura.
    """
    from gerador_treino import ANCORAS_POR_REGIAO, ANCORAS_POR_SUBREGIAO

    grupos = []
    for regiao, ancoras_raw in ANCORAS_POR_REGIAO.items():
        grupos.append((
            f"regiao={regiao}",
            [
                {"chave": a["subregiao"], "peso": a["peso"], "obrigatoria": a["obrigatoria"]}
                for a in ancoras_raw
            ],
        ))
    for sub, ancoras_raw in ANCORAS_POR_SUBREGIAO.items():
        grupos.append((
            f"subregiao={sub}",
            [
                {"chave": a["padrao"], "peso": a["peso"], "obrigatoria": a["obrigatoria"]}
                for a in ancoras_raw
            ],
        ))

    for nome, ancoras in grupos:
        n_obrig = sum(1 for a in ancoras if a["obrigatoria"])
        if n_obrig == 0:
            continue
        for vagas in range(n_obrig, 15):
            random.seed(vagas)
            quotas, avisos = calcular_quotas(ancoras, vagas)
            for a in ancoras:
                if a["obrigatoria"]:
                    assert quotas.get(a["chave"], 0) >= 1, (
                        f"{nome} vagas={vagas}: obrig {a['chave']} tem "
                        f"qtd={quotas.get(a['chave'])}; quotas={quotas}"
                    )
            # Sem avisos quando vagas >= n_obrig
            avisos_nc = [v for v in avisos if v["tipo"] == "ancora_nao_cumprida"]
            assert avisos_nc == [], f"{nome} vagas={vagas}: avisos={avisos_nc}"


# ─── Helpers de aplicação à hierarquia ─────────────────────────────────


def test_quotas_de_regiao_upper_6():
    """upper(6): pesos 2:2:1 (peito, costas, ombro) → Hamilton 3:2:1.

    6 × (2/5, 2/5, 1/5) = (2.4, 2.4, 1.2) → floor (2, 2, 1); resto
    (0.4, 0.4, 0.2). Restante=1. Top resto empate entre peito/costas;
    tie-break ordem definição → peito ganha +1. Final: (3, 2, 1).
    """
    from gerador_treino import _quotas_de_regiao
    random.seed(1)
    quotas, avisos = _quotas_de_regiao("upper", 6)
    assert quotas == {"peito": 3, "costas": 2, "ombro": 1}
    assert avisos == []


def test_quotas_de_regiao_upper_5_paritaria():
    """upper(5): pesos 2:2:1 → 2:2:1 exato (sem resto)."""
    from gerador_treino import _quotas_de_regiao
    random.seed(1)
    quotas, _ = _quotas_de_regiao("upper", 5)
    # 5 × (2/5, 2/5, 1/5) = (2, 2, 1) — limpo
    assert quotas == {"peito": 2, "costas": 2, "ombro": 1}


def test_quotas_de_regiao_lower_2_um_de_cada_essencial():
    """lower(2): perna_ant + perna_post (obrig). Acessória panturrilha NÃO compete."""
    from gerador_treino import _quotas_de_regiao
    random.seed(1)
    # Esse helper aplica Hamilton puro sobre TODAS as âncoras da região.
    # O filtro pré-quotas (acessórias só em qtd > 2 × num_obrig) é
    # responsabilidade do CALLER (_decompor_demanda_regiao). Aqui só
    # testamos o helper puro: lower(2) com pesos 2:2:1 → 1:1:0 via Hamilton.
    quotas, _ = _quotas_de_regiao("lower", 2)
    # 2 × (2/5, 2/5, 1/5) = (0.8, 0.8, 0.4) → floor (0,0,0); restos
    # ordenados (perna_ant 0.8, perna_post 0.8, panturrilha 0.4); top 2.
    # Tie-break peso_maior + ordem: perna_ant (peso 2, idx 0), perna_post
    # (peso 2, idx 1) ganham +1 cada. Final: (1, 1, 0).
    assert quotas == {"perna_anterior": 1, "perna_posterior": 1}


def test_quotas_de_regiao_lower_5_panturrilha_pode_aparecer():
    """lower(5): peso 2:2:1 → Hamilton 2:2:1. Panturrilha entra."""
    from gerador_treino import _quotas_de_regiao
    random.seed(1)
    quotas, _ = _quotas_de_regiao("lower", 5)
    # 5 × (2/5, 2/5, 1/5) = (2, 2, 1) → floor (2,2,1) sum=5 ✓
    assert quotas == {"perna_anterior": 2, "perna_posterior": 2, "panturrilha": 1}


def test_quotas_de_regiao_sem_ancoras_devolve_vazio():
    """Região sem âncoras (cardio) → quotas vazias, sem aviso."""
    from gerador_treino import _quotas_de_regiao
    quotas, avisos = _quotas_de_regiao("cardio", 3)
    assert quotas == {}
    assert avisos == []


def test_quotas_de_subregiao_peito_2():
    """peito(2): empurrar_compostos:3 (obrig) + empurrar_isolados:2 → 1+1."""
    from gerador_treino import _quotas_de_subregiao
    random.seed(1)
    quotas, _ = _quotas_de_subregiao("peito", 2)
    assert quotas == {"empurrar_compostos": 1, "empurrar_isolados": 1}


def test_quotas_de_subregiao_perna_anterior_3():
    """perna_anterior(3): bi:3 (obrig) + uni:2 → Hamilton (2,1)."""
    from gerador_treino import _quotas_de_subregiao
    random.seed(1)
    quotas, _ = _quotas_de_subregiao("perna_anterior", 3)
    # 3 × 3/5 = 1.8; 3 × 2/5 = 1.2 → floor (1,1) resto (0.8, 0.2) → +1 primeiro
    assert quotas == {"squat_bilateral": 2, "squat_unilateral": 1}


def test_quotas_de_subregiao_perna_posterior_6_paritaria():
    """perna_posterior(6): pesos 3:2:2 (pós-2026-05-25) → Hamilton 2:2:2.

    Decisão 2026-05-25 (Frente S-A1): peso curado de abduction subiu de 1
    pra 2, refletindo equivalência clínica com knee_flexion (ambos
    'segunda escolha' depois do hinge obrigatório, sem hierarquia entre si)."""
    from gerador_treino import _quotas_de_subregiao
    random.seed(1)
    quotas, _ = _quotas_de_subregiao("perna_posterior", 6)
    assert quotas == {"hinge": 2, "knee_flexion": 2, "abduction": 2}


def test_quotas_de_subregiao_costas_4_paritaria():
    """costas(4): remadas:2 puxadas:2 → 2:2."""
    from gerador_treino import _quotas_de_subregiao
    random.seed(1)
    quotas, _ = _quotas_de_subregiao("costas", 4)
    assert quotas == {"remadas": 2, "puxadas": 2}


def test_quotas_de_subregiao_costas_1_emite_aviso():
    """costas(1): 1 vaga, 2 obrigatórias → sorteio + aviso ancora_nao_cumprida."""
    from gerador_treino import _quotas_de_subregiao
    random.seed(7000)
    quotas, avisos = _quotas_de_subregiao("costas", 1)
    assert sum(quotas.values()) == 1
    nao_cumpridas = [a for a in avisos if a["tipo"] == "ancora_nao_cumprida"]
    assert len(nao_cumpridas) == 1
    assert nao_cumpridas[0]["nivel"] == "subregiao"
    assert nao_cumpridas[0]["escopo"] == "costas"


def test_quotas_de_subregiao_sem_ancoras_devolve_vazio():
    """Subregião sem âncoras (core_dinamico) → vazio (fallback Etapa 2)."""
    from gerador_treino import _quotas_de_subregiao
    quotas, _ = _quotas_de_subregiao("core_dinamico", 3)
    assert quotas == {}


# ─── Distribuição treino > rotina ──────────────────────────────────────


def test_distribuir_perna_anterior_2x3_espalha_uni():
    """perna_anterior(2)x3 com quota global bi:4 uni:2 → espalhar uni."""
    from gerador_treino import _distribuir_quotas_entre_treinos
    quotas_global = {"squat_bilateral": 4, "squat_unilateral": 2}
    pesos = {"squat_bilateral": 3, "squat_unilateral": 2}
    random.seed(1)
    por_treino = _distribuir_quotas_entre_treinos(
        quotas_global, n_treinos=3, vagas_por_treino=[2, 2, 2], pesos=pesos
    )
    # Cada treino tem 2 vagas; total bi=4 + uni=2 = 6 ✓
    for t in por_treino:
        assert sum(t.values()) == 2
    total_bi = sum(t.get("squat_bilateral", 0) for t in por_treino)
    total_uni = sum(t.get("squat_unilateral", 0) for t in por_treino)
    assert total_bi == 4
    assert total_uni == 2
    # Nenhum treino deve concentrar 2 uni; espalhamento é a regra
    treinos_com_uni = [i for i, t in enumerate(por_treino) if t.get("squat_unilateral", 0) > 0]
    assert len(treinos_com_uni) == 2, f"esperado 2 treinos com uni, obtido {por_treino}"


def test_distribuir_perna_anterior_3x3_cobertura_intra_treino():
    """perna_anterior(3)x3 com bi:5 uni:4 → cada treino tem ≥1 bi E ≥1 uni."""
    from gerador_treino import _distribuir_quotas_entre_treinos
    quotas_global = {"squat_bilateral": 5, "squat_unilateral": 4}
    pesos = {"squat_bilateral": 3, "squat_unilateral": 2}
    random.seed(2)
    por_treino = _distribuir_quotas_entre_treinos(
        quotas_global, n_treinos=3, vagas_por_treino=[3, 3, 3], pesos=pesos
    )
    for t in por_treino:
        assert t.get("squat_bilateral", 0) >= 1
        assert t.get("squat_unilateral", 0) >= 1


def test_distribuir_costas_4x1_um_treino_so():
    """costas(4)x1 com remadas:2 puxadas:2 → 1 treino com 2+2."""
    from gerador_treino import _distribuir_quotas_entre_treinos
    quotas_global = {"remadas": 2, "puxadas": 2}
    pesos = {"remadas": 2, "puxadas": 2}
    por_treino = _distribuir_quotas_entre_treinos(
        quotas_global, n_treinos=1, vagas_por_treino=[4], pesos=pesos
    )
    assert por_treino == [{"remadas": 2, "puxadas": 2}]


def test_distribuir_perna_posterior_6_um_treino():
    """perna_posterior(6)x1 com hinge:3 knee:2 abd:1 → 1 treino com 3+2+1."""
    from gerador_treino import _distribuir_quotas_entre_treinos
    quotas_global = {"hinge": 3, "knee_flexion": 2, "abduction": 1}
    pesos = {"hinge": 3, "knee_flexion": 2, "abduction": 1}
    por_treino = _distribuir_quotas_entre_treinos(
        quotas_global, n_treinos=1, vagas_por_treino=[6], pesos=pesos
    )
    assert por_treino == [{"hinge": 3, "knee_flexion": 2, "abduction": 1}]


def test_distribuir_zero_treinos():
    """Caso degenerado: n_treinos=0 → lista vazia."""
    from gerador_treino import _distribuir_quotas_entre_treinos
    out = _distribuir_quotas_entre_treinos({}, n_treinos=0, vagas_por_treino=[], pesos={})
    assert out == []


def test_distribuir_quota_vazia():
    """Quotas vazias → cada treino recebe dict vazio."""
    from gerador_treino import _distribuir_quotas_entre_treinos
    out = _distribuir_quotas_entre_treinos(
        {}, n_treinos=3, vagas_por_treino=[2, 2, 2], pesos={},
    )
    assert out == [{}, {}, {}]


# ─── Carve-out de quotas por subregião (2026-05-18) ────────────────────


def test_ombro_vaga_unica_sorteia_70_30_composto_isolado():
    """Ombro vagas=1: 70% composto / 30% isolado / 0% posterior."""
    from gerador_treino import _quotas_de_subregiao
    N = 2000
    contagem = {"ombro_composto": 0, "ombro_isolado": 0, "posterior_ombro": 0}
    for seed in range(N):
        random.seed(seed)
        quotas, _ = _quotas_de_subregiao("ombro", 1)
        assert sum(quotas.values()) == 1
        for padrao in quotas:
            contagem[padrao] += 1
    assert contagem["posterior_ombro"] == 0
    pct_composto = contagem["ombro_composto"] / N
    assert 0.65 <= pct_composto <= 0.75, (
        f"composto = {pct_composto:.1%} (esperado ~70%). Dist: {contagem}"
    )


def test_ombro_vagas_2_volta_para_hamilton_normal():
    """Ombro vagas≥2: sem carve-out, Hamilton normal opera."""
    from gerador_treino import _quotas_de_subregiao
    random.seed(42)
    quotas, _ = _quotas_de_subregiao("ombro", 2)
    assert quotas.get("ombro_composto", 0) == 1
    assert quotas.get("ombro_isolado", 0) == 1
    assert quotas.get("posterior_ombro", 0) == 0

    quotas, _ = _quotas_de_subregiao("ombro", 6)
    assert quotas == {"ombro_composto": 3, "ombro_isolado": 2, "posterior_ombro": 1}


def test_perna_posterior_vaga_unica_sorteia_60_20_20():
    """Perna_posterior vagas=1: 60% hinge / 20% kn / 20% ab."""
    from gerador_treino import _quotas_de_subregiao
    N = 3000
    contagem = {"hinge": 0, "knee_flexion": 0, "abduction": 0}
    for seed in range(N):
        random.seed(seed)
        quotas, _ = _quotas_de_subregiao("perna_posterior", 1)
        assert sum(quotas.values()) == 1
        for padrao in quotas:
            contagem[padrao] += 1
    pct_hinge = contagem["hinge"] / N
    pct_kn    = contagem["knee_flexion"] / N
    pct_ab    = contagem["abduction"] / N
    assert 0.55 <= pct_hinge <= 0.65, f"hinge = {pct_hinge:.1%} (esperado ~60%)"
    assert 0.15 <= pct_kn    <= 0.25, f"kn    = {pct_kn:.1%} (esperado ~20%)"
    assert 0.15 <= pct_ab    <= 0.25, f"ab    = {pct_ab:.1%} (esperado ~20%)"


def test_perna_posterior_vaga_dupla_hinge_fixo_50_50():
    """Perna_posterior vagas=2: hinge sempre presente; 2º slot 50/50 kn/ab."""
    from gerador_treino import _quotas_de_subregiao
    N = 2000
    com_kn = com_ab = 0
    for seed in range(N):
        random.seed(seed)
        quotas, _ = _quotas_de_subregiao("perna_posterior", 2)
        assert sum(quotas.values()) == 2
        assert quotas.get("hinge", 0) == 1, f"hinge faltando: {quotas}"
        if quotas.get("knee_flexion", 0) == 1:
            com_kn += 1
        elif quotas.get("abduction", 0) == 1:
            com_ab += 1
    pct_kn = com_kn / N
    pct_ab = com_ab / N
    assert 0.45 <= pct_kn <= 0.55, f"% kn = {pct_kn:.1%} (esperado ~50%)"
    assert 0.45 <= pct_ab <= 0.55, f"% ab = {pct_ab:.1%} (esperado ~50%)"


def test_perna_posterior_vagas_3_prioriza_hinge_levemente():
    """Perna_posterior vagas=3: 60% cobertura completa (1+1+1),
    40% prioriza hinge (2+1+0 ou 2+0+1) com kn/ab simétricas.
    Slot-level esperado: hinge ~47%, kn ~27%, ab ~27%."""
    from gerador_treino import _quotas_de_subregiao
    N = 3000
    contagem = {"hinge": 0, "knee_flexion": 0, "abduction": 0}
    cobertura_completa = 0
    for seed in range(N):
        random.seed(seed)
        quotas, _ = _quotas_de_subregiao("perna_posterior", 3)
        assert sum(quotas.values()) == 3
        assert quotas.get("hinge", 0) >= 1, f"hinge ausente: {quotas}"
        for padrao, qtd in quotas.items():
            contagem[padrao] += qtd
        if quotas == {"hinge": 1, "knee_flexion": 1, "abduction": 1}:
            cobertura_completa += 1
    total = sum(contagem.values())
    pct_hinge = contagem["hinge"] / total
    pct_kn    = contagem["knee_flexion"] / total
    pct_ab    = contagem["abduction"] / total
    pct_cc    = cobertura_completa / N
    assert 0.43 <= pct_hinge <= 0.51, f"hinge slot = {pct_hinge:.1%} (esperado ~47%)"
    assert 0.23 <= pct_kn    <= 0.31, f"kn slot    = {pct_kn:.1%} (esperado ~27%)"
    assert 0.23 <= pct_ab    <= 0.31, f"ab slot    = {pct_ab:.1%} (esperado ~27%)"
    # Simetria kn/ab (diff < 4pp)
    assert abs(pct_kn - pct_ab) < 0.04, f"kn-ab diff = {abs(pct_kn-pct_ab):.1%} (esperado simétrico)"
    assert 0.55 <= pct_cc <= 0.65, f"cobertura completa = {pct_cc:.1%} (esperado ~60%)"


def test_perna_posterior_vagas_4_volta_para_hamilton():
    """Perna_posterior vagas≥4: sem carve-out, Hamilton normal opera.

    Pesos pós-2026-05-25: 3:2:2 (abduction subiu de 1 pra 2 por correção
    clínica — Frente S-A1)."""
    from gerador_treino import _quotas_de_subregiao
    random.seed(0)
    quotas, _ = _quotas_de_subregiao("perna_posterior", 4)
    assert quotas == {"hinge": 2, "knee_flexion": 1, "abduction": 1}

    quotas, _ = _quotas_de_subregiao("perna_posterior", 6)
    assert quotas == {"hinge": 2, "knee_flexion": 2, "abduction": 2}


def test_peito_nao_afetado_pelos_carveouts():
    """Peito não tem carve-out — Hamilton normal em todas as vagas.
    Crítico: vagas=3 continua 2 compostos + 1 isolado (ortodoxia clínica)."""
    from gerador_treino import _quotas_de_subregiao
    quotas, _ = _quotas_de_subregiao("peito", 1)
    assert quotas == {"empurrar_compostos": 1}

    quotas, _ = _quotas_de_subregiao("peito", 3)
    assert quotas == {"empurrar_compostos": 2, "empurrar_isolados": 1}
