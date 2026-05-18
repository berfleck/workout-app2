"""Testes para a Sub-PR 1 da Etapa 2 — pre_alocar_rotina e helpers isolados.

Testes batem direto na função pre_alocar_rotina (não passa por
gerar_multiplos_treinos). Comportamento user-visible permanece inalterado
no Sub-PR 1; só Sub-PR 2 integra a Fase 0 ao fluxo principal.
"""
from __future__ import annotations

import random
from collections import Counter

from gerador_treino import (
    SUBREGIOES_POR_REGIAO,
    _calcular_escassez,
    _decompor_demanda_regiao,
    _decompor_demanda_subregiao,
    _eh_composto,
    _normalizar_config,
    _quotas_por_pool,
    _Slot,
    gerar_multiplos_treinos,
    pre_alocar_rotina,
)


# ─── _normalizar_config ──────────────────────────────────────────────────


def test_normalizar_config_demandas_passa_direto():
    cfg = {"demandas": [("regiao", "lower", 4)]}
    out = _normalizar_config(cfg)
    assert out["demandas"] == [("regiao", "lower", 4)]


def test_normalizar_config_template_simples_vira_demandas_padrao():
    cfg = {
        "padroes": ["remadas", "puxadas", "hinge"],
        "exercicios_por_padrao": {"remadas": 2, "puxadas": 1, "hinge": 1},
    }
    out = _normalizar_config(cfg)
    assert out["demandas"] == [
        ("padrao", "remadas", 2),
        ("padrao", "puxadas", 1),
        ("padrao", "hinge", 1),
    ]


def test_normalizar_config_template_com_squat_legado():
    """Padrão `squat` agregado vira squat_bilateral + squat_unilateral via cycling."""
    random.seed(42)
    cfg = {"padroes": ["squat"], "exercicios_por_padrao": {"squat": 2}}
    out = _normalizar_config(cfg)
    total = sum(qt for _, _, qt in out["demandas"])
    assert total == 2
    padroes_resultado = {esc for _, esc, _ in out["demandas"]}
    assert padroes_resultado <= {"squat_bilateral", "squat_unilateral"}


def test_normalizar_config_epp_dict_lateralidade():
    """EPP em formato dict {bilateral: X, unilateral: Y} é convertido."""
    cfg = {
        "padroes": ["hinge"],
        "exercicios_por_padrao": {"hinge": {"bilateral": 1, "unilateral": 1}},
    }
    out = _normalizar_config(cfg)
    assert out["demandas"] == [("padrao", "hinge", 2)]
    assert out["lateralidade_por_padrao"] == {"hinge": {"bilateral": 1, "unilateral": 1}}


# ─── _decompor_demanda_regiao (Etapa 3: nova assinatura + quotas) ───────


def test_decompor_lower_2_so_obrigatorias():
    """lower(2): pesos 2:2:1. qtd ≤ 2×n_obrig=4 → filtro pré-quotas remove
    panturrilha (acessória). Hamilton 2 vagas com 2:2 → (1, 1)."""
    random.seed(1)
    sub_dems, _ = _decompor_demanda_regiao("lower", 2)
    qtd_por_sub = {sub: qt for _, sub, qt in sub_dems}
    assert qtd_por_sub == {"perna_anterior": 1, "perna_posterior": 1}


def test_decompor_lower_4_acessorias_nao_competem():
    """lower(4): qtd ≤ 2×n_obrig=4 → só obrigatórias. Hamilton 4 vagas com
    2:2 → (2, 2). Comportamento Etapa 2 D2.1 preservado."""
    random.seed(2)
    sub_dems, _ = _decompor_demanda_regiao("lower", 4)
    qtd_por_sub = {sub: qt for _, sub, qt in sub_dems}
    assert qtd_por_sub == {"perna_anterior": 2, "perna_posterior": 2}


def test_decompor_lower_5_acessoria_entra():
    """lower(5): qtd > 2×n_obrig=4 → todas âncoras competem. Hamilton 5
    vagas com 2:2:1 → (2, 2, 1) exato."""
    random.seed(3)
    sub_dems, _ = _decompor_demanda_regiao("lower", 5)
    qtd_por_sub = {sub: qt for _, sub, qt in sub_dems}
    assert qtd_por_sub == {"perna_anterior": 2, "perna_posterior": 2, "panturrilha": 1}


def test_decompor_lower_6_proporcional():
    """lower(6): pesos 2:2:1 → Hamilton 6×(2/5,2/5,1/5)=(2.4,2.4,1.2)
    → floor (2,2,1) restante=1; tie-break sorteado entre perna_ant e
    perna_post (ambas com mesmo resto 0.4 e mesmo peso 2) → uma delas
    ganha o +1, panturrilha fica em 1.

    NOTA: adutores NÃO está em ANCORAS_POR_REGIAO['lower'] (decisão clínica:
    adutores entra só quando user pede explicitamente). Mudança vs Etapa 2
    onde adutores aparecia via fallback essencial/acessório.
    """
    random.seed(4)
    sub_dems, _ = _decompor_demanda_regiao("lower", 6)
    qtd_por_sub = {sub: qt for _, sub, qt in sub_dems}
    assert qtd_por_sub.get("panturrilha", 0) == 1
    qa = qtd_por_sub.get("perna_anterior", 0)
    qp = qtd_por_sub.get("perna_posterior", 0)
    assert {qa, qp} == {2, 3}
    assert "adutores" not in qtd_por_sub


def test_decompor_upper_2_vagas_menores_que_obrigatorias():
    """upper(2): n_obrig=3 (peito, costas, ombro), qtd<n_obrig → sorteio +
    aviso. Etapa 3 substitui sample pré-quota por calcular_quotas que sortea
    e emite ancora_nao_cumprida."""
    random.seed(5)
    sub_dems, avisos = _decompor_demanda_regiao("upper", 2)
    qtd_por_sub = {sub: qt for _, sub, qt in sub_dems}
    assert sum(qtd_por_sub.values()) == 2
    assert all(qt == 1 for qt in qtd_por_sub.values())
    assert set(qtd_por_sub.keys()) <= {"peito", "costas", "ombro"}
    assert len(qtd_por_sub) == 2
    # 1 obrigatória ficou de fora → aviso ancora_nao_cumprida
    nao_cumpridas = [a for a in avisos if a.get("tipo") == "ancora_nao_cumprida"]
    assert len(nao_cumpridas) == 1


# ─── pre_alocar_rotina ──────────────────────────────────────────────────


def _all_alocados(alocacao):
    out = []
    for _t, by_d in alocacao.items():
        for _d, exs in by_d.items():
            out.extend(exs)
    return out


def _alocados_treino(alocacao, t_idx):
    out = []
    for _d, exs in alocacao.get(t_idx, {}).items():
        out.extend(exs)
    return out


def test_pre_alocar_lower_2_um_de_cada_essencial(banco):
    random.seed(10)
    cfg = {"demandas": [("regiao", "lower", 2)]}
    alocacao, _avisos, _relax = pre_alocar_rotina(banco, [cfg])
    exs = _all_alocados(alocacao)
    assert len(exs) == 2
    subs = {ex.subregiao for ex in exs}
    assert subs == {"perna_anterior", "perna_posterior"}


def test_pre_alocar_lower_4_dois_e_dois_essenciais(banco):
    """Acessórias não competem em lower(4): 2 perna_ant + 2 perna_post."""
    random.seed(11)
    cfg = {"demandas": [("regiao", "lower", 4)]}
    alocacao, _, _relax = pre_alocar_rotina(banco, [cfg])
    exs = _all_alocados(alocacao)
    assert len(exs) == 4
    cnt_sub = Counter(ex.subregiao for ex in exs)
    assert cnt_sub == {"perna_anterior": 2, "perna_posterior": 2}


def test_pre_alocar_lower_6_proporcional(banco):
    """lower(6) Etapa 3: pesos 2:2:1 (perna_ant, perna_post, panturrilha).
    Hamilton 6×(2/5,2/5,1/5)=(2.4,2.4,1.2) → floor (2,2,1) restante=1;
    tie-break ordem → perna_ant +1 = (3,2,1).

    Adutores NÃO entra (não está em ANCORAS_POR_REGIAO['lower']) — decisão
    clínica da Etapa 3: adutores entra só quando user pede explicitamente.
    """
    random.seed(12)
    cfg = {"demandas": [("regiao", "lower", 6)]}
    alocacao, _, _relax = pre_alocar_rotina(banco, [cfg])
    exs = _all_alocados(alocacao)
    assert len(exs) == 6
    cnt_sub = Counter(ex.subregiao for ex in exs)
    assert cnt_sub.get("perna_anterior", 0) == 3
    assert cnt_sub.get("perna_posterior", 0) == 2
    assert cnt_sub.get("panturrilha", 0) == 1
    assert cnt_sub.get("adutores", 0) == 0


def test_pre_alocar_subregiao_e_padrao_sem_decomposicao(banco):
    """Demandas de subregião e padrão viram slots diretos sem decomposição."""
    random.seed(13)
    cfg_sub = {"demandas": [("subregiao", "peito", 3)]}
    alocacao, _, _relax = pre_alocar_rotina(banco, [cfg_sub])
    exs = _all_alocados(alocacao)
    assert len(exs) == 3
    assert all(ex.subregiao == "peito" for ex in exs)

    random.seed(14)
    cfg_pad = {"demandas": [("padrao", "hinge", 2)]}
    alocacao, _, _relax = pre_alocar_rotina(banco, [cfg_pad])
    exs = _all_alocados(alocacao)
    assert len(exs) == 2
    assert all(ex.padrao == "hinge" for ex in exs)


def test_pre_alocar_quota_composto_em_regiao_via_pesos(banco):
    """lower(5) Etapa 3: quota composta emerge dos pesos das âncoras.

    Hamilton aloca: perna_ant 2 (pesos squat_bi:3, squat_uni:2 → 1 bi + 1
    uni), perna_post 2 (pesos hinge:3, knee:2, abd:1 → 1 hinge + 1 knee),
    panturrilha 1 (flexao_plantar). Compostos: bi+hinge ≥ 2 garantidos.

    NOTA: a regra dura 60% (PROPORCAO_COMPOSTOS) foi aposentada na Etapa 3.
    Pesos das âncoras decidem composto/iso (empurrar_compostos:3 vs
    empurrar_isolados:2 dá ~60% composto em peito naturalmente).
    """
    # Roda 100 seeds e checa que MEDIANA tem >= 2 compostos (não regra dura)
    contagens = []
    for s in range(100):
        random.seed(s)
        cfg = {"demandas": [("regiao", "lower", 5)]}
        alocacao, _, _relax = pre_alocar_rotina(banco, [cfg])
        exs = _all_alocados(alocacao)
        contagens.append(sum(1 for ex in exs if _eh_composto(ex)))
    media = sum(contagens) / len(contagens)
    assert media >= 1.8, f"média compostos em lower(5) = {media:.2f} (esperado >= 1.8)"


def test_pre_alocar_travado_consome_vaga(banco):
    """Travado em perna_anterior em lower(3) → 3 ex totais (não 4)."""
    random.seed(16)
    travado = next(e for e in banco if e.padrao == "squat_bilateral")
    cfg = {
        "demandas": [("regiao", "lower", 3)],
        "exercicios_travados": [travado],
    }
    alocacao, _, _relax = pre_alocar_rotina(banco, [cfg])
    exs = _all_alocados(alocacao)
    assert len(exs) == 3
    assert travado.nome in {ex.nome for ex in exs}


def test_pre_alocar_multi_treino_sem_repetir_nomes(banco):
    """3 treinos lower(3): nenhum exercício se repete entre treinos."""
    random.seed(17)
    cfg = {"demandas": [("regiao", "lower", 3)]}
    alocacao, _, _relax = pre_alocar_rotina(banco, [cfg, cfg, cfg])
    todos_nomes = [ex.nome for ex in _all_alocados(alocacao)]
    duplicados = [n for n, c in Counter(todos_nomes).items() if c > 1]
    assert not duplicados, f"duplicados entre treinos: {duplicados}"


def test_pre_alocar_aviso_incompleta_rotina_level(banco):
    """Banco curto em peito + peito(3)×2 → maioria dos slots vira aviso.

    Etapa 3: peito tem âncora obrigatória empurrar_compostos, então
    slots desse padrão sem candidato viram `ancora_sem_candidatos`
    (não `incompleta` genérico). Testa ambos os tipos como avisos
    rotina-level válidos.
    """
    random.seed(18)
    banco_curto = [
        e for e in banco
        if e.subregiao != "peito" or e.nome == "Crossover Sentado"
    ]
    cfg = {"demandas": [("subregiao", "peito", 3)]}
    alocacao, avisos, _relax = pre_alocar_rotina(banco_curto, [cfg, cfg])
    avisos_rot = [
        a for a in avisos
        if a.get("escopo") == "rotina"
        and a.get("tipo") in ("incompleta", "ancora_sem_candidatos")
    ]
    assert len(avisos_rot) >= 4, f"avisos: {avisos}"
    for av in avisos_rot:
        assert av["escopo"] == "rotina"
        assert "escopo_demanda" in av
        assert "treino_idx" in av


def test_pre_alocar_determinismo_com_seed(banco):
    """Mesmo seed → mesma alocação."""
    cfg = {"demandas": [("regiao", "lower", 4)]}
    random.seed(99)
    aloc_a, _, _ = pre_alocar_rotina(banco, [cfg, cfg])
    random.seed(99)
    aloc_b, _, _ = pre_alocar_rotina(banco, [cfg, cfg])

    def _serialize(aloc):
        return {t: {d: tuple(e.nome for e in exs) for d, exs in by_d.items()}
                for t, by_d in aloc.items()}

    assert _serialize(aloc_a) == _serialize(aloc_b)


def test_pre_alocar_seeds_diferentes_produzem_alocacoes_diferentes(banco):
    """Tie-break sorteado: seeds diferentes geram alocações diferentes."""
    cfg = {"demandas": [("regiao", "lower", 4)]}
    random.seed(100)
    aloc_a, _, _ = pre_alocar_rotina(banco, [cfg, cfg])
    random.seed(200)
    aloc_b, _, _ = pre_alocar_rotina(banco, [cfg, cfg])

    def _serialize(aloc):
        return {t: {d: tuple(e.nome for e in exs) for d, exs in by_d.items()}
                for t, by_d in aloc.items()}

    assert _serialize(aloc_a) != _serialize(aloc_b)


def test_pre_alocar_cobertura_essencial_intra_treino_multi(banco):
    """lower(2) × 3 treinos: cada treino tem 1 perna_ant + 1 perna_post."""
    random.seed(101)
    cfg = {"demandas": [("regiao", "lower", 2)]}
    alocacao, _, _relax = pre_alocar_rotina(banco, [cfg, cfg, cfg])
    for t_idx in range(3):
        exs = _alocados_treino(alocacao, t_idx)
        subs = {ex.subregiao for ex in exs}
        assert subs == {"perna_anterior", "perna_posterior"}, (
            f"treino {t_idx}: subs={subs}, "
            f"exs={[(e.nome, e.subregiao) for e in exs]}"
        )


# ─── _calcular_escassez ────────────────────────────────────────────────


def test_calcular_escassez_modo_estrito(banco):
    """Escassez sem nada bloqueado = nº total de candidatos no banco filtrado."""
    slot = _Slot(
        treino_idx=0, d_idx_original=0,
        nivel="padrao", escopo_alocacao="hinge",
        escopo_demanda_original="hinge",
        requer_composto=False,
    )
    cfg = {"max_complexidade": 5, "equipamentos_bloqueados": []}
    n_total = sum(1 for e in banco if e.padrao == "hinge")
    n = _calcular_escassez(slot, banco, cfg, set(), set())
    assert n == n_total


def test_calcular_escassez_decresce_com_bloqueios(banco):
    """Bloquear nomes → escassez diminui."""
    slot = _Slot(
        treino_idx=0, d_idx_original=0,
        nivel="padrao", escopo_alocacao="hinge",
        escopo_demanda_original="hinge",
        requer_composto=False,
    )
    cfg = {"max_complexidade": 5, "equipamentos_bloqueados": []}
    nomes_hinge = [e.nome for e in banco if e.padrao == "hinge"][:3]
    n0 = _calcular_escassez(slot, banco, cfg, set(), set())
    n1 = _calcular_escassez(slot, banco, cfg, set(nomes_hinge), set())
    assert n1 == n0 - 3


def test_calcular_escassez_filtra_complexidade_e_equipamento(banco):
    """Filtros user (eq, complexidade) reduzem escassez."""
    slot = _Slot(
        treino_idx=0, d_idx_original=0,
        nivel="padrao", escopo_alocacao="hinge",
        escopo_demanda_original="hinge",
        requer_composto=False,
    )
    n_default = _calcular_escassez(
        slot, banco, {"max_complexidade": 5, "equipamentos_bloqueados": []}, set(), set()
    )
    n_baixa_cx = _calcular_escassez(
        slot, banco, {"max_complexidade": 1, "equipamentos_bloqueados": []}, set(), set()
    )
    assert n_baixa_cx <= n_default


# ─── _quotas_por_pool (refator cycling fallback — Seção 8.15.12) ──────


def test_quotas_por_pool_qtd_zero_retorna_vazio():
    """Edge case: qtd=0 → dict vazio."""
    out = _quotas_por_pool(["a", "b"], 0, {"a": 5, "b": 3})
    assert out == {}


def test_quotas_por_pool_chaves_vazias_retorna_vazio():
    out = _quotas_por_pool([], 5, {})
    assert out == {}


def test_quotas_por_pool_pool_zero_global_retorna_vazio():
    """Pool global = 0 → sem vagas alocadas (degenera)."""
    out = _quotas_por_pool(["a", "b"], 3, {"a": 0, "b": 0})
    assert out == {}


def test_quotas_por_pool_obrigatoria_garante_uma_vaga():
    """Obrigatórias ganham 1 vaga antes do sorteio ponderado."""
    random.seed(42)
    # Pool: a=8, b=1. Obrigatória: b. qtd=2.
    # b ganha 1 garantida, depois sortear 1 com pesos restantes (7,0) → a.
    out = _quotas_por_pool(["a", "b"], 2, {"a": 8, "b": 1}, obrigatorias=["b"])
    assert out == {"a": 1, "b": 1}


def test_quotas_por_pool_distribuicao_proporcional_ao_pool():
    """qtd=1 sobre pool [8,1,1,3] dá P(a)≈8/13, P(b)≈1/13, P(c)≈1/13, P(d)≈3/13.

    Mono-ex (b, c, pool=1) NÃO recebe 1/4=25% como cycling legado faria —
    recebe 1/13≈7.7% (Seção 8.15.12 — resolução do 6º NO-OP).
    """
    counts = Counter()
    n = 4000
    for seed in range(n):
        random.seed(seed)
        out = _quotas_por_pool(["a", "b", "c", "d"], 1, {"a": 8, "b": 1, "c": 1, "d": 3})
        for k, v in out.items():
            counts[k] += v
    # Esperado: a≈61.5%, b≈7.7%, c≈7.7%, d≈23.1%
    assert 0.55 <= counts["a"] / n <= 0.68, f"P(a)={counts['a']/n:.3f}, esperado ~0.615"
    assert 0.04 <= counts["b"] / n <= 0.12, f"P(b)={counts['b']/n:.3f}, esperado ~0.077"
    assert 0.04 <= counts["c"] / n <= 0.12, f"P(c)={counts['c']/n:.3f}, esperado ~0.077"
    assert 0.18 <= counts["d"] / n <= 0.28, f"P(d)={counts['d']/n:.3f}, esperado ~0.231"


def test_core_isometrico_1_pallof_press_nao_concentra(banco):
    """Regressão Seção 8.15.12 (6º NO-OP pós-CORE): cycling fallback antigo
    dava P(Pallof Press em core_iso(1)) ≈ 25% via 1-de-cada padrão uniforme.

    Pós-refator (quota ponderada por pool), P(Pallof) cai pra ~1/N_pool,
    proporcional ao tamanho do pool de core_isometrico no banco. Alvo
    conservador: <12% (legado era 25%; uniforme-por-ex seria 7.7% em
    banco mock de 13 ex, menos no banco real).
    """
    n = 500
    hits = 0
    for seed in range(n):
        random.seed(seed)
        cfg = {"demandas": [("subregiao", "core_isometrico", 1)]}
        sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
        for s in sessoes:
            for bloco in s.blocos:
                for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
                    if ex and ex.nome == "Pallof Press":
                        hits += 1
                        break
    pct = hits / n
    assert pct < 0.12, (
        f"P(Pallof em core_iso(1)) = {pct:.2%} >= 12% — regressão do "
        f"viés mono-ex resolvido na Seção 8.15.12"
    )


# ─── Sanity / smoke ────────────────────────────────────────────────────


def test_estrutura_subregioes_por_regiao_alinha_com_padrao_para_subregiao():
    """Toda subregião listada em SUBREGIOES_POR_REGIAO existe em SUBREGIAO_PARA_REGIAO."""
    from gerador_treino import SUBREGIAO_PARA_REGIAO
    for regiao, estrutura in SUBREGIOES_POR_REGIAO.items():
        for sub in estrutura["essenciais"] + estrutura["acessorias"]:
            assert sub in SUBREGIAO_PARA_REGIAO, (
                f"sub '{sub}' em SUBREGIOES_POR_REGIAO[{regiao}] não existe em SUBREGIAO_PARA_REGIAO"
            )
            assert SUBREGIAO_PARA_REGIAO[sub] == regiao, (
                f"sub '{sub}' em SUBREGIOES_POR_REGIAO[{regiao}] aponta pra "
                f"regiao '{SUBREGIAO_PARA_REGIAO[sub]}' em SUBREGIAO_PARA_REGIAO"
            )
