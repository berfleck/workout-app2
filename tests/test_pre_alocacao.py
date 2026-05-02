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
    _eh_composto,
    _normalizar_config,
    _Slot,
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


# ─── _decompor_demanda_regiao ────────────────────────────────────────────


def test_decompor_lower_2_so_essenciais():
    random.seed(1)
    sub_dems = _decompor_demanda_regiao("lower", 2)
    qtd_por_sub = {sub: qt for _, sub, qt in sub_dems}
    assert qtd_por_sub == {"perna_anterior": 1, "perna_posterior": 1}


def test_decompor_lower_4_acessorias_nao_competem():
    """qtd=4, n_ess=2, 4 NÃO > 2×2=4. Acessórias não competem."""
    random.seed(2)
    sub_dems = _decompor_demanda_regiao("lower", 4)
    qtd_por_sub = {sub: qt for _, sub, qt in sub_dems}
    assert qtd_por_sub == {"perna_anterior": 2, "perna_posterior": 2}


def test_decompor_lower_5_acessorias_competem():
    """qtd=5, n_ess=2, 5 > 2×2=4. Acessórias entram no ciclo."""
    random.seed(3)
    sub_dems = _decompor_demanda_regiao("lower", 5)
    qtd_por_sub = {sub: qt for _, sub, qt in sub_dems}
    assert qtd_por_sub.get("perna_anterior", 0) >= 1
    assert qtd_por_sub.get("perna_posterior", 0) >= 1
    assert sum(qtd_por_sub.values()) == 5


def test_decompor_lower_6_um_de_cada():
    """qtd=6, n_ess=2, 6 > 4. 1+1 essenciais + ciclo de 4 → 1 de cada (2+2+1+1)."""
    random.seed(4)
    sub_dems = _decompor_demanda_regiao("lower", 6)
    qtd_por_sub = {sub: qt for _, sub, qt in sub_dems}
    assert qtd_por_sub.get("perna_anterior", 0) == 2
    assert qtd_por_sub.get("perna_posterior", 0) == 2
    assert qtd_por_sub.get("panturrilha", 0) == 1
    assert qtd_por_sub.get("adutores", 0) == 1


def test_decompor_upper_2_vagas_menores_que_essenciais():
    """qtd=2, n_ess=3 (peito, costas, ombro). Sortea 2 das 3 com seed."""
    random.seed(5)
    sub_dems = _decompor_demanda_regiao("upper", 2)
    qtd_por_sub = {sub: qt for _, sub, qt in sub_dems}
    assert sum(qtd_por_sub.values()) == 2
    assert all(qt == 1 for qt in qtd_por_sub.values())
    assert set(qtd_por_sub.keys()) <= {"peito", "costas", "ombro"}
    assert len(qtd_por_sub) == 2


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
    alocacao, _avisos = pre_alocar_rotina(banco, [cfg])
    exs = _all_alocados(alocacao)
    assert len(exs) == 2
    subs = {ex.subregiao for ex in exs}
    assert subs == {"perna_anterior", "perna_posterior"}


def test_pre_alocar_lower_4_dois_e_dois_essenciais(banco):
    """Acessórias não competem em lower(4): 2 perna_ant + 2 perna_post."""
    random.seed(11)
    cfg = {"demandas": [("regiao", "lower", 4)]}
    alocacao, _ = pre_alocar_rotina(banco, [cfg])
    exs = _all_alocados(alocacao)
    assert len(exs) == 4
    cnt_sub = Counter(ex.subregiao for ex in exs)
    assert cnt_sub == {"perna_anterior": 2, "perna_posterior": 2}


def test_pre_alocar_lower_6_um_de_cada_subregiao(banco):
    """lower(6): 2+2 essenciais + 1+1 acessórias = 6."""
    random.seed(12)
    cfg = {"demandas": [("regiao", "lower", 6)]}
    alocacao, _ = pre_alocar_rotina(banco, [cfg])
    exs = _all_alocados(alocacao)
    assert len(exs) == 6
    cnt_sub = Counter(ex.subregiao for ex in exs)
    assert cnt_sub.get("perna_anterior", 0) == 2
    assert cnt_sub.get("perna_posterior", 0) == 2
    assert cnt_sub.get("panturrilha", 0) == 1
    assert cnt_sub.get("adutores", 0) == 1


def test_pre_alocar_subregiao_e_padrao_sem_decomposicao(banco):
    """Demandas de subregião e padrão viram slots diretos sem decomposição."""
    random.seed(13)
    cfg_sub = {"demandas": [("subregiao", "peito", 3)]}
    alocacao, _ = pre_alocar_rotina(banco, [cfg_sub])
    exs = _all_alocados(alocacao)
    assert len(exs) == 3
    assert all(ex.subregiao == "peito" for ex in exs)

    random.seed(14)
    cfg_pad = {"demandas": [("padrao", "hinge", 2)]}
    alocacao, _ = pre_alocar_rotina(banco, [cfg_pad])
    exs = _all_alocados(alocacao)
    assert len(exs) == 2
    assert all(ex.padrao == "hinge" for ex in exs)


def test_pre_alocar_quota_composto_em_regiao(banco):
    """lower(5): pelo menos ceil(5×0.6)=3 compostos."""
    random.seed(15)
    cfg = {"demandas": [("regiao", "lower", 5)]}
    alocacao, _ = pre_alocar_rotina(banco, [cfg])
    exs = _all_alocados(alocacao)
    n_compostos = sum(1 for ex in exs if _eh_composto(ex))
    assert n_compostos >= 3, f"esperado >= 3 compostos, obtido {n_compostos}"


def test_pre_alocar_travado_consome_vaga(banco):
    """Travado em perna_anterior em lower(3) → 3 ex totais (não 4)."""
    random.seed(16)
    travado = next(e for e in banco if e.padrao == "squat_bilateral")
    cfg = {
        "demandas": [("regiao", "lower", 3)],
        "exercicios_travados": [travado],
    }
    alocacao, _ = pre_alocar_rotina(banco, [cfg])
    exs = _all_alocados(alocacao)
    assert len(exs) == 3
    assert travado.nome in {ex.nome for ex in exs}


def test_pre_alocar_multi_treino_sem_repetir_nomes(banco):
    """3 treinos lower(3): nenhum exercício se repete entre treinos."""
    random.seed(17)
    cfg = {"demandas": [("regiao", "lower", 3)]}
    alocacao, _ = pre_alocar_rotina(banco, [cfg, cfg, cfg])
    todos_nomes = [ex.nome for ex in _all_alocados(alocacao)]
    duplicados = [n for n, c in Counter(todos_nomes).items() if c > 1]
    assert not duplicados, f"duplicados entre treinos: {duplicados}"


def test_pre_alocar_aviso_incompleta_rotina_level(banco):
    """Banco curto em peito + peito(3)×2 → maioria dos slots vira aviso."""
    random.seed(18)
    # Mantém só 1 ex de peito (sem variacao_de pra evitar bloqueio em cadeia)
    banco_curto = [
        e for e in banco
        if e.subregiao != "peito" or e.nome == "Crossover Sentado"
    ]
    cfg = {"demandas": [("subregiao", "peito", 3)]}
    alocacao, avisos = pre_alocar_rotina(banco_curto, [cfg, cfg])
    # 1 ex será alocado (no T1, ordem aleatória), e 5 slots ficam sem candidato
    # → 5 avisos rotina-level. Mas com seed pode haver ≤ 5 (se 0 alocados, 6 avisos).
    avisos_rot = [a for a in avisos if a.get("tipo") == "incompleta" and a.get("escopo") == "rotina"]
    assert len(avisos_rot) >= 4, f"avisos: {avisos}"
    # Cada aviso tem `escopo` e `escopo_demanda` populados
    for av in avisos_rot:
        assert av["escopo"] == "rotina"
        assert "escopo_demanda" in av
        assert "treino_idx" in av


def test_pre_alocar_determinismo_com_seed(banco):
    """Mesmo seed → mesma alocação."""
    cfg = {"demandas": [("regiao", "lower", 4)]}
    random.seed(99)
    aloc_a, _ = pre_alocar_rotina(banco, [cfg, cfg])
    random.seed(99)
    aloc_b, _ = pre_alocar_rotina(banco, [cfg, cfg])

    def _serialize(aloc):
        return {t: {d: tuple(e.nome for e in exs) for d, exs in by_d.items()}
                for t, by_d in aloc.items()}

    assert _serialize(aloc_a) == _serialize(aloc_b)


def test_pre_alocar_seeds_diferentes_produzem_alocacoes_diferentes(banco):
    """Tie-break sorteado: seeds diferentes geram alocações diferentes."""
    cfg = {"demandas": [("regiao", "lower", 4)]}
    random.seed(100)
    aloc_a, _ = pre_alocar_rotina(banco, [cfg, cfg])
    random.seed(200)
    aloc_b, _ = pre_alocar_rotina(banco, [cfg, cfg])

    def _serialize(aloc):
        return {t: {d: tuple(e.nome for e in exs) for d, exs in by_d.items()}
                for t, by_d in aloc.items()}

    assert _serialize(aloc_a) != _serialize(aloc_b)


def test_pre_alocar_cobertura_essencial_intra_treino_multi(banco):
    """lower(2) × 3 treinos: cada treino tem 1 perna_ant + 1 perna_post."""
    random.seed(101)
    cfg = {"demandas": [("regiao", "lower", 2)]}
    alocacao, _ = pre_alocar_rotina(banco, [cfg, cfg, cfg])
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
