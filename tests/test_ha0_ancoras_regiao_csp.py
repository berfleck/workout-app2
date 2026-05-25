"""Testes da Micro-frente H-A0 — âncoras obrigatórias por REGIÃO no CSP.

Spec executável em `docs/refatoracao/catalogo_constraints.md` (seção H-A0).
Origem do bug: auditoria clínica pós-Frente E.1 (2026-05-25) — rotina
Full Body 2T (regiao upper(3) + lower(3) + core(2) × 2T) saiu com
zero exercícios de costas em 16 slots e zero squat em 6 slots de lower.
H-A1 só dispara em demanda nível subregião; demanda nível região passava
sem âncora.

Decisões fechadas no handoff (2026-05-25):
- 4.1 Agregação PER-TREINO (não cross-treino) — "treino de upper" cobre
  upper NAQUELE treino, não na rotina inteira.
- 4.2 Interação H-A0 × H-A1: marker via estrutura paralela
  `subregioes_obrigadas_ha0[(t_idx, R)] = set(subs_ativas)`.
- 4.3 Rejeição de subs não-âncora HARD (Caminho A) — upstream no
  filtro do `pool_default_sem_travados`.
- 4.4 Reuso `ANCORAS_POR_REGIAO` do gerador_treino (não duplicar).
- 4.6 NÃO modelar `PROPORCAO_COMPOSTOS = 0.6` — cobertura de compostos
  vem via H-A1[X] que ativa por marker.
"""
from __future__ import annotations

from gerador_csp import (
    ConfigVariedade,
    gerar_rotina_csp,
    gerar_treino_csp,
)


# ── Helpers ─────────────────────────────────────────────────────────────


def _subs_do_treino(rotina, t_idx):
    return [
        e.subregiao
        for g in rotina["treinos"][t_idx]["grupos"]
        for e in g["exercicios"]
    ]


def _padroes_do_treino(rotina, t_idx):
    return [
        e.padrao
        for g in rotina["treinos"][t_idx]["grupos"]
        for e in g["exercicios"]
    ]


def _meta_h_a0(rotina, t_idx, regiao, sub):
    for entry in rotina.get("h_a0_aplicadas", []):
        if (
            entry.get("treino") == t_idx
            and entry.get("regiao") == regiao
            and entry.get("subregiao_obrigatoria") == sub
        ):
            return entry
    return None


# ── (a) Regressão protetora do achado clínico de 2026-05-25 ──────────────


def test_full_body_2t_seed42_cobertura_completa(banco):
    """Reproduz o setup do achado clínico (`tools/criar_aluno_e_rotina_teste.py`):
    Full Body 2T, demandas regiao upper(3) + lower(3) + core(2) × 2T,
    nivel=2, aderencia=media (peso=0), seed=42.

    Pré-H-A0: T1 e T2 sem costas, sem ombro, sem squat.
    Pós-H-A0: cada treino tem peito + costas + ombro em upper(3);
    perna_anterior + perna_posterior em lower(3)."""
    demandas_t = [("regiao", "upper", 3), ("regiao", "lower", 3), ("regiao", "core", 2)]
    r = gerar_rotina_csp(
        [demandas_t, demandas_t], banco, nivel_aluno=2, seed=42,
        variedade=ConfigVariedade(),
        peso_aderencia=0, peso_evitar_agonistas=10,
        tamanho_preferido=2, peso_tamanho_bloco=5,
        relaxar_familia=True,
    )
    assert r["viavel"], f"inviável: {r.get('status')}"
    for t_idx in (0, 1):
        subs = set(_subs_do_treino(r, t_idx))
        assert "peito" in subs, f"T{t_idx+1}: zero peito"
        assert "costas" in subs, f"T{t_idx+1}: zero costas (achado original)"
        assert "ombro" in subs, f"T{t_idx+1}: zero ombro (achado original)"
        assert "perna_anterior" in subs, f"T{t_idx+1}: zero perna_anterior"
        assert "perna_posterior" in subs, f"T{t_idx+1}: zero perna_posterior"
        # `bracos` deve estar AUSENTE de upper (banimento upstream).
        assert "bracos" not in subs, f"T{t_idx+1}: bracos apareceu em upper(3)"


# ── (b) Banimento hard de subs não-âncora — upstream do pool ─────────────


def test_demanda_upper_3_nao_pode_produzir_bracos(banco):
    """`("regiao","upper",3)` rejeita bracos do pool (não está em
    ANCORAS_POR_REGIAO[upper]). Decisão 4.3 / Caminho A."""
    for seed in range(8):
        r = gerar_treino_csp(
            [("regiao", "upper", 3)], banco, nivel_aluno=3, seed=seed,
        )
        if not r["viavel"]:
            continue
        for g in r["grupos"]:
            for e in g["exercicios"]:
                assert e.subregiao != "bracos", (
                    f"seed {seed}: bracos em slot upper(3) — banimento upstream falhou"
                )


def test_demanda_lower_3_nao_pode_produzir_adutores(banco):
    """`("regiao","lower",3)` rejeita adutores (não está em
    ANCORAS_POR_REGIAO[lower])."""
    for seed in range(8):
        r = gerar_treino_csp(
            [("regiao", "lower", 3)], banco, nivel_aluno=3, seed=seed,
        )
        if not r["viavel"]:
            continue
        for g in r["grupos"]:
            for e in g["exercicios"]:
                assert e.subregiao != "adutores", (
                    f"seed {seed}: adutores em slot lower(3) — banimento falhou"
                )


# ── (c) Per-treino (não cross-treino) — decisão 4.1 ──────────────────────


def test_h_a0_e_per_treino_nao_cross(banco):
    """Decisão 4.1 do handoff: H-A0 agrega PER-TREINO. T1 com upper(3) +
    T2 com upper(3) gera 2 conjuntos de constraints (um por treino).
    `h_a0_aplicadas` tem entradas para AMBOS os treinos."""
    demandas_t = [("regiao", "upper", 3)]
    r = gerar_rotina_csp(
        [demandas_t, demandas_t], banco, nivel_aluno=3, seed=0,
    )
    assert r["viavel"]
    # Cada treino deve ter as 3 obrigatórias declaradas em h_a0_aplicadas.
    for t_idx in (0, 1):
        for sub in ("peito", "costas", "ombro"):
            meta = _meta_h_a0(r, t_idx, "upper", sub)
            assert meta is not None, f"T{t_idx}: faltou entrada {sub}"
            assert not meta["degraded"], f"T{t_idx}/{sub}: degraded={meta}"


# ── (d) Interação H-A0 × H-A1 via marker (decisão 4.2 / 5.2) ─────────────


def test_marker_ha0_ativa_ha1_em_demanda_regiao(banco):
    """Pós-marker H-A0, H-A1 também se aplica aos slots da demanda região.
    Decisão 4.2 / 5.2 / Caminho A (reordenar): H-A0 popula
    `subregioes_obrigadas_ha0[(t_idx, R)] = set(subs)`, H-A1 lê.

    `("regiao","upper",3)` → H-A0 força peito/costas/ombro; H-A1 marker
    força empurrar_compostos (peito), ombro_composto (ombro), e ≥1 de
    {remadas,puxadas} para costas (conflito cardinalidade vagas=1<2)."""
    r = gerar_treino_csp([("regiao", "upper", 3)], banco, nivel_aluno=3, seed=0)
    assert r["viavel"]
    ha1 = r.get("h_a1_aplicadas", [])
    subs_em_ha1 = {a["subregiao"] for a in ha1}
    assert "peito" in subs_em_ha1
    assert "costas" in subs_em_ha1
    assert "ombro" in subs_em_ha1


# ── (e) Conflito de cardinalidade — upper(1) com 3 obrigatórias ──────────


def test_upper_1_dispara_conflito_cardinalidade(banco):
    """`("regiao","upper",1)` com 3 obrigatórias (peito/costas/ombro) e
    1 vaga: constraint colaborativa força 1 das 3 distintas. 2 das 3
    saem `degraded=True` com motivo `conflito_cardinalidade`."""
    r = gerar_treino_csp([("regiao", "upper", 1)], banco, nivel_aluno=3, seed=0)
    assert r["viavel"]
    aplicadas_upper = [a for a in r.get("h_a0_aplicadas", []) if a["regiao"] == "upper"]
    degradadas = [a for a in aplicadas_upper if a["degraded"]]
    nao_degradadas = [a for a in aplicadas_upper if not a["degraded"]]
    assert len(aplicadas_upper) == 3, f"esperava 3 entradas, veio {aplicadas_upper}"
    assert len(degradadas) >= 2, f"esperava ≥2 degraded em conflito vagas<n_obrig: {aplicadas_upper}"
    for a in degradadas:
        assert "conflito_cardinalidade" in (a.get("motivo") or "")
    # A não-degradada (que entra como obrig escolhida) deve corresponder
    # à sub que ocupa o slot único.
    subs_slot = set(_subs_do_treino(
        {"treinos": [{"grupos": r["grupos"]}]}, 0,
    ))
    assert len(subs_slot) == 1, f"upper(1) deve ter 1 sub no slot: {subs_slot}"


# ── (f) Demanda nível padrão NÃO ativa H-A0 ──────────────────────────────


def test_demanda_padrao_nao_ativa_h_a0(banco):
    """Decisão do handoff: H-A0 só ativa em demanda nível regiao com R
    em ANCORAS_POR_REGIAO. Demanda padrão é respeitada como pedida."""
    r = gerar_treino_csp([("padrao", "empurrar_isolados", 2)], banco, nivel_aluno=3, seed=0)
    assert r["viavel"]
    aplicadas = r.get("h_a0_aplicadas", [])
    assert aplicadas == [], f"H-A0 não deveria ativar em demanda padrão: {aplicadas}"


# ── (g) Demanda nível subregião NÃO ativa H-A0 ───────────────────────────


def test_demanda_subregiao_nao_ativa_h_a0(banco):
    """Demanda subregião direta é responsabilidade da H-A1.
    H-A0 fica vazio."""
    r = gerar_treino_csp([("subregiao", "peito", 2)], banco, nivel_aluno=3, seed=0)
    assert r["viavel"]
    aplicadas = r.get("h_a0_aplicadas", [])
    assert aplicadas == [], f"H-A0 não deveria ativar em demanda subregião: {aplicadas}"


# ── (h) Região sem âncoras declaradas (core) — H-A0 sem obrigatórias ─────


def test_demanda_regiao_core_sem_obrigatorias_nao_dispara_hard(banco):
    """`ANCORAS_POR_REGIAO[core]` tem core_dinamico + core_isometrico
    AMBAS com obrigatoria=False. H-A0 NÃO deve forçar nenhuma; entrada
    em h_a0_aplicadas vazia OU com 0 obrigatórias. Banimento hard de
    subs fora de ANCORAS_POR_REGIAO[core] continua valendo."""
    r = gerar_treino_csp([("regiao", "core", 2)], banco, nivel_aluno=3, seed=0)
    assert r["viavel"]
    aplicadas_core = [
        a for a in r.get("h_a0_aplicadas", []) if a["regiao"] == "core"
    ]
    assert aplicadas_core == [], f"H-A0 não deve gerar entradas pra core: {aplicadas_core}"


# ── (i) Cobertura de subregiões obrigatórias em upper(3) ─────────────────


def test_upper_3_cobre_todas_obrigatorias(banco):
    """upper(3) com 3 obrigatórias (peito/costas/ombro) DEVE produzir 1
    slot de cada sub. 5 seeds — todos satisfazem."""
    falhas = []
    for seed in range(5):
        r = gerar_treino_csp(
            [("regiao", "upper", 3)], banco, nivel_aluno=3, seed=seed,
        )
        if not r["viavel"]:
            falhas.append((seed, r.get("status")))
            continue
        subs = set(_subs_do_treino({"treinos": [{"grupos": r["grupos"]}]}, 0))
        if {"peito", "costas", "ombro"} - subs:
            falhas.append((seed, sorted(subs)))
    assert not falhas, f"seeds com cobertura incompleta: {falhas}"


# ── (j) lower(3) — perna_anterior + perna_posterior obrigatórias ─────────


def test_lower_3_cobre_perna_anterior_e_posterior(banco):
    """`ANCORAS_POR_REGIAO[lower]`: perna_anterior obrig + perna_posterior
    obrig + panturrilha NÃO obrig. lower(3) deve cobrir as 2 obrigatórias.
    Panturrilha pode ou não aparecer."""
    falhas = []
    for seed in range(5):
        r = gerar_treino_csp(
            [("regiao", "lower", 3)], banco, nivel_aluno=3, seed=seed,
        )
        if not r["viavel"]:
            falhas.append((seed, r.get("status")))
            continue
        subs = set(_subs_do_treino({"treinos": [{"grupos": r["grupos"]}]}, 0))
        if "perna_anterior" not in subs or "perna_posterior" not in subs:
            falhas.append((seed, sorted(subs)))
        # adutores deve estar banido
        assert "adutores" not in subs, f"seed {seed}: adutores em lower(3)"
    assert not falhas, f"seeds com cobertura incompleta: {falhas}"


# ── (k) Pool sem candidato pra sub obrigatória — graceful degradation ────


def test_h_a0_pool_vazio_degrada(banco):
    """Quando o pool de uma sub obrigatória fica 100% filtrado por H-P1,
    a constraint daquela sub é PULADA e marcada `degraded=True` com motivo
    `pool sem candidato`. Construímos o cenário: banco sem peito ativo."""
    # Cria banco filtrado: remove todos os exercícios de subregião peito.
    banco_sem_peito = [e for e in banco if e.subregiao != "peito"]
    r = gerar_treino_csp(
        [("regiao", "upper", 3)], banco_sem_peito, nivel_aluno=3, seed=0,
    )
    # Pode ser viável (sem peito mas com costas+ombro garantidos) ou
    # inviável (depende do solver). Em ambos os casos, deve haver entrada
    # degraded pra peito com motivo "pool sem candidato".
    entradas_peito = [
        a for a in r.get("h_a0_aplicadas", [])
        if a["regiao"] == "upper" and a["subregiao_obrigatoria"] == "peito"
    ]
    assert len(entradas_peito) == 1
    assert entradas_peito[0]["degraded"] is True
    assert "pool sem candidato" in entradas_peito[0].get("motivo", "")


# ── (l) Pareamento de avisos com Sessao.avisos via adapter ───────────────


def test_adapter_distribui_h_a0_degradado_no_treino_correto(banco):
    """Em rotina 2T com upper(3) + lower(3) em T1 e só core(2) em T2, o
    aviso h_a0_degradado por conflito (se houver) deve cair no treino
    correto via `aviso['treino']`."""
    from app_flask import _distribuir_avisos_rotina_csp, _treino_dict_csp_pra_sessao
    demandas_por_treino = [
        [("regiao", "upper", 1)],  # T1: conflito cardinalidade garantido
        [("regiao", "core", 2)],   # T2: sem H-A0 hard
    ]
    r = gerar_rotina_csp(
        demandas_por_treino, banco, nivel_aluno=3, seed=0,
        variedade=ConfigVariedade(),
    )
    assert r["viavel"]
    sessoes = [
        _treino_dict_csp_pra_sessao(t_dict, f"T{ti+1}")
        for ti, t_dict in enumerate(r["treinos"])
    ]
    _distribuir_avisos_rotina_csp(r, sessoes, demandas_por_treino)
    # T1: deve ter avisos h_a0_degradado (conflito).
    avisos_t1 = [a for a in sessoes[0].avisos if a.get("tipo") == "h_a0_degradado"]
    assert len(avisos_t1) >= 2, f"T1 deveria ter ≥2 avisos h_a0_degradado: {avisos_t1}"
    # T2: NÃO deve ter avisos h_a0_degradado (core obrigatorias=False).
    avisos_t2 = [a for a in sessoes[1].avisos if a.get("tipo") == "h_a0_degradado"]
    assert avisos_t2 == [], f"T2 não deveria ter avisos h_a0_degradado: {avisos_t2}"


# ── (m) Não regredir H-A1 quando demanda subregião explícita ─────────────


def test_h_a0_nao_quebra_h_a1_em_subregiao_pura(banco):
    """Demanda só subregião (sem nenhuma região) — H-A1 funciona igual ao
    Bloco 2.5. Regressão protetora."""
    r = gerar_treino_csp([("subregiao", "ombro", 2)], banco, nivel_aluno=3, seed=0)
    assert r["viavel"]
    padroes = _padroes_do_treino({"treinos": [{"grupos": r["grupos"]}]}, 0)
    assert "ombro_composto" in padroes
    aplicadas = r.get("h_a0_aplicadas", [])
    assert aplicadas == [], f"H-A0 vazio em demanda subregião pura: {aplicadas}"


# ── (n) Smoke perfis variados: Filipe (aderencia alta) ───────────────────


def test_smoke_perfil_aderencia_alta_cobertura_preservada(banco):
    """Aderência ao tier alta (peso_aderencia=2) NÃO deve interferir na
    cobertura H-A0. Slots seguem subs obrigatórias; aderência empurra
    pra Principal/Intermediário."""
    demandas_t = [("regiao", "upper", 3), ("regiao", "lower", 3), ("regiao", "core", 2)]
    r = gerar_rotina_csp(
        [demandas_t, demandas_t], banco, nivel_aluno=3, seed=1,
        variedade=ConfigVariedade(),
        peso_aderencia=2, peso_evitar_agonistas=10,
        tamanho_preferido=2, peso_tamanho_bloco=5,
        relaxar_familia=True,
    )
    assert r["viavel"], f"inviável: {r.get('status')}"
    for t_idx in (0, 1):
        subs = set(_subs_do_treino(r, t_idx))
        for obrig in ("peito", "costas", "ombro", "perna_anterior", "perna_posterior"):
            assert obrig in subs, f"T{t_idx+1}: sem {obrig} (aderência alta)"
