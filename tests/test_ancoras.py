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


def test_quotas_de_subregiao_perna_posterior_6_3_2_1():
    """perna_posterior(6): hinge:3 knee:2 abd:1 → Hamilton 3:2:1 exato."""
    from gerador_treino import _quotas_de_subregiao
    random.seed(1)
    quotas, _ = _quotas_de_subregiao("perna_posterior", 6)
    assert quotas == {"hinge": 3, "knee_flexion": 2, "abduction": 1}


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
