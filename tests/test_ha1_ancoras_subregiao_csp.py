"""Testes da Micro-frente H-A1 — âncoras obrigatórias por subregião no CSP.

Spec executável em `docs/refatoracao/catalogo_constraints.md` (seção H-A1).
Origem do bug: Frente E.0 (2026-05-24) — sem H-A1 no CSP, demandas nível
subregião violavam padrão obrigatório em até 100% das rotinas em casos
push-pesados (`ombro(2)` em ABC Day A caía 100% em `posterior_ombro`).

Decisões fechadas no handoff (2026-05-25):
- NÃO ativa em demanda nível padrão (usuário pediu o padrão; respeitar).
- NÃO ativa em demanda nível regiao (slot sem subregião determinística).
- Conflito de cardinalidade (vagas < n_obrig efetivas): constraint
  colaborativa força N obrig DISTINTAS a aparecer. Cada uma é marcada
  `degraded=True` no resultado.
- Graceful degradation por pool vazio: âncora cujo pool foi 100% filtrado
  por H-P1 é PULADA e marcada `degraded=True`.
- Cross-treino: obrigatoriedade vale na rotina inteira (≥1 slot global,
  não por treino).
"""
from __future__ import annotations

from gerador_csp import (
    ConfigVariedade,
    gerar_rotina_csp,
    gerar_treino_csp,
)


# ── Helpers ─────────────────────────────────────────────────────────────

def _padroes_da_rotina(rotina):
    return [
        e.padrao
        for tr in rotina["treinos"]
        for g in tr["grupos"]
        for e in g["exercicios"]
    ]


def _padroes_do_treino(treino):
    return [e.padrao for g in treino["grupos"] for e in g["exercicios"]]


def _meta_h_a1(rotina_ou_treino, subregiao, padrao):
    for entry in rotina_ou_treino.get("h_a1_aplicadas", []):
        if entry["subregiao"] == subregiao and entry["padrao_obrigatorio"] == padrao:
            return entry
    return None


# ── (a) Caso clínico-bloqueador da E.0 — ombro_composto em ABC Day A ────

def test_ombro_composto_obrigatorio_em_ombro_2(banco):
    """Antes do H-A1: 100% das rotinas com `ombro(2)` saíam sem
    `ombro_composto` por minimização cega da S-B1. Pós-H-A1: obrigatório."""
    demandas = [("subregiao", "peito", 3), ("subregiao", "ombro", 2)]
    falhas = []
    for seed in range(10):
        r = gerar_treino_csp(
            demandas, banco, nivel_aluno=3, seed=seed,
            peso_evitar_agonistas=10, peso_tamanho_bloco=5,
        )
        assert r["viavel"], f"seed {seed} inviável"
        padroes = _padroes_do_treino(r)
        if "ombro_composto" not in padroes:
            falhas.append(seed)
    assert not falhas, f"ombro_composto ausente em seeds: {falhas}"


def test_ha1_meta_ombro_nao_degraded(banco):
    """Entrada h_a1_aplicadas[ombro/ombro_composto] não-degraded em ombro(2)."""
    demandas = [("subregiao", "ombro", 2)]
    r = gerar_treino_csp(demandas, banco, nivel_aluno=3, seed=0)
    meta = _meta_h_a1(r, "ombro", "ombro_composto")
    assert meta is not None
    assert meta["degraded"] is False
    assert meta["n_slots"] == 2
    assert meta["n_termos"] > 0


# ── (b) Outro caso clínico — biceps obrigatório em bracos(2) ────────────

def test_biceps_obrigatorio_em_bracos_2(banco):
    """ABC Day B do harness: `bracos(2)` deve ter ≥1 biceps + ≥1 triceps."""
    demandas = [("subregiao", "bracos", 2)]
    falhas_b, falhas_t = [], []
    for seed in range(10):
        r = gerar_treino_csp(
            demandas, banco, nivel_aluno=3, seed=seed,
            peso_evitar_agonistas=10, peso_tamanho_bloco=5,
        )
        assert r["viavel"], f"seed {seed} inviável"
        padroes = _padroes_do_treino(r)
        if "biceps" not in padroes:
            falhas_b.append(seed)
        if "triceps" not in padroes:
            falhas_t.append(seed)
    assert not falhas_b, f"biceps ausente: {falhas_b}"
    assert not falhas_t, f"triceps ausente: {falhas_t}"


# ── (c) hinge obrigatório em perna_posterior(2) ─────────────────────────

def test_hinge_obrigatorio_em_perna_posterior_2(banco):
    """ABC Day C: `perna_posterior(2)` deve ter ≥1 hinge (carve-out já
    forçava no antigo via SUBREGIOES_CARVE_OUT_QUOTAS, mas isso é
    distribuição — H-A1 é obrigatoriedade)."""
    demandas = [("subregiao", "perna_posterior", 2)]
    falhas = []
    for seed in range(10):
        r = gerar_treino_csp(demandas, banco, nivel_aluno=3, seed=seed)
        assert r["viavel"], f"seed {seed} inviável"
        if "hinge" not in _padroes_do_treino(r):
            falhas.append(seed)
    assert not falhas, f"hinge ausente em seeds: {falhas}"


# ── (d) Conflito de cardinalidade — bracos(1) ───────────────────────────

def test_bracos_1_pelo_menos_uma_obrigatoria(banco):
    """bracos(1): vagas=1, n_obrig=2 (biceps+triceps). Constraint
    colaborativa força ≥1 das 2 obrigatórias. Sem forçar qual."""
    demandas = [("subregiao", "bracos", 1)]
    distribuicao = {"biceps": 0, "triceps": 0, "outro": 0}
    for seed in range(20):
        r = gerar_treino_csp(demandas, banco, nivel_aluno=3, seed=seed)
        assert r["viavel"], f"seed {seed} inviável"
        padroes = _padroes_do_treino(r)
        assert len(padroes) == 1, f"seed {seed}: esperava 1 ex, veio {len(padroes)}"
        p = padroes[0]
        if p == "biceps":
            distribuicao["biceps"] += 1
        elif p == "triceps":
            distribuicao["triceps"] += 1
        else:
            distribuicao["outro"] += 1
    assert distribuicao["outro"] == 0, (
        f"bracos(1) deve ter biceps ou triceps; veio outro: {distribuicao}"
    )
    # Pelo menos um dos dois deve aparecer em alguma seed (sem forçar qual)
    assert distribuicao["biceps"] + distribuicao["triceps"] == 20


def test_bracos_1_marca_degraded_conflito(banco):
    """bracos(1): h_a1_aplicadas marca AMBAS biceps e triceps com
    degraded=True (conflito de cardinalidade)."""
    demandas = [("subregiao", "bracos", 1)]
    r = gerar_treino_csp(demandas, banco, nivel_aluno=3, seed=0)
    meta_b = _meta_h_a1(r, "bracos", "biceps")
    meta_t = _meta_h_a1(r, "bracos", "triceps")
    assert meta_b is not None and meta_t is not None
    assert meta_b["degraded"] is True
    assert meta_t["degraded"] is True
    assert "conflito_cardinalidade" in meta_b["motivo"]
    assert "vagas=1" in meta_b["motivo"]


# ── (e) Cross-treino — costas(1)+costas(1) deve cobrir remadas+puxadas ──

def test_cross_treino_costas_1_mais_1(banco):
    """Rotina com costas(1) no treino A e costas(1) no treino B: vagas
    cross-treino = 2 ≥ n_obrig (puxadas+remadas) = 2. H-A1 deve forçar
    1 de cada padrão na rotina inteira."""
    demandas_por_treino = [
        [("subregiao", "costas", 1), ("subregiao", "peito", 1)],
        [("subregiao", "costas", 1), ("subregiao", "peito", 1)],
    ]
    for seed in range(10):
        r = gerar_rotina_csp(
            demandas_por_treino, banco, nivel_aluno=3, seed=seed,
        )
        assert r["viavel"], f"seed {seed} inviável"
        padroes_costas = [
            e.padrao
            for tr in r["treinos"]
            for g in tr["grupos"]
            for e in g["exercicios"]
            if e.subregiao == "costas"
        ]
        assert "remadas" in padroes_costas, f"seed {seed}: sem remadas"
        assert "puxadas" in padroes_costas, f"seed {seed}: sem puxadas"


# ── (f) Demanda nível padrão NÃO ativa H-A1 ─────────────────────────────

def test_demanda_padrao_nao_ativa_ha1(banco):
    """`("padrao", "posterior_ombro", 2)`: H-A1 NÃO deve exigir
    ombro_composto (decisão do handoff). h_a1_aplicadas vazio pra ombro."""
    demandas = [("padrao", "posterior_ombro", 2)]
    r = gerar_treino_csp(demandas, banco, nivel_aluno=3, seed=0)
    assert r["viavel"]
    # Confirma que ombro_composto NÃO aparece (slots todos posterior_ombro)
    padroes = _padroes_do_treino(r)
    assert all(p == "posterior_ombro" for p in padroes)
    # h_a1_aplicadas não inclui entrada pra ombro nesse caso
    meta = _meta_h_a1(r, "ombro", "ombro_composto")
    assert meta is None


# ── (g) Demanda nível regiao NÃO ativa H-A1 ─────────────────────────────

def test_demanda_regiao_nao_ativa_ha1(banco):
    """`("regiao", "upper", 3)`: H-A1 NÃO ativa em demanda nível regiao
    (slot sem subregião determinística pré-solver — mesma regra do H-R1)."""
    demandas = [("regiao", "upper", 3)]
    r = gerar_treino_csp(demandas, banco, nivel_aluno=3, seed=0)
    assert r["viavel"]
    # h_a1_aplicadas pode estar vazio OU não conter nenhuma subregião
    # que viria SÓ da expansão da região (sem demanda subregião explícita).
    ha1 = r.get("h_a1_aplicadas", [])
    # Nenhuma entrada — demanda é nível regiao, sem subregião explícita.
    assert ha1 == [], f"h_a1_aplicadas deveria estar vazio, veio {ha1}"


# ── (h) Subregião sem âncoras (core_dinamico) — sem H-A1 ────────────────

def test_subregiao_sem_ancoras_sem_ha1(banco):
    """core_dinamico não tem entrada em ANCORAS_POR_SUBREGIAO. Demanda
    desse tipo não deve gerar entrada em h_a1_aplicadas."""
    demandas = [("subregiao", "core_dinamico", 2)]
    r = gerar_treino_csp(demandas, banco, nivel_aluno=3, seed=0)
    assert r["viavel"]
    ha1 = r.get("h_a1_aplicadas", [])
    # Pode ter entradas de outras subregiões da rotina (nenhuma aqui), mas
    # NENHUMA pode mencionar core_dinamico.
    assert all(e["subregiao"] != "core_dinamico" for e in ha1)


# ── (i) Convivência H-A1 + H-R1 em peito(2) — sem patologia ─────────────

def test_convivencia_ha1_h_r1_peito(banco):
    """H-R1 em peito(2) exige horizontal composto (purpose=='compound').
    H-A1 em peito(2) exige padrao=='empurrar_compostos'. H-R1 mais
    estrita; ambas devem ser satisfeitas sem conflito."""
    demandas = [("subregiao", "peito", 2)]
    for seed in range(5):
        r = gerar_treino_csp(demandas, banco, nivel_aluno=3, seed=seed)
        assert r["viavel"], f"seed {seed} inviável"
        exs = [e for g in r["grupos"] for e in g["exercicios"]]
        # H-R1: pelo menos 1 empurrar_compostos compound
        assert any(
            e.padrao == "empurrar_compostos" and e.purpose == "compound"
            for e in exs
        ), f"seed {seed}: violou H-R1 peito"
        # H-A1: pelo menos 1 empurrar_compostos (qualquer purpose)
        assert any(e.padrao == "empurrar_compostos" for e in exs), (
            f"seed {seed}: violou H-A1 peito"
        )
    # Meta da H-A1 não-degraded
    meta = _meta_h_a1(r, "peito", "empurrar_compostos")
    assert meta is not None and meta["degraded"] is False


# ── (j) Sanity: subregião com 1 âncora obrigatória (panturrilha) ────────

def test_panturrilha_unica_ancora(banco):
    """panturrilha tem só `flexao_plantar` como obrigatória (peso 1).
    Caso simples: 1 vaga, 1 obrig → constraint normal aplica."""
    demandas = [("subregiao", "panturrilha", 1)]
    r = gerar_treino_csp(demandas, banco, nivel_aluno=3, seed=0)
    assert r["viavel"]
    padroes = _padroes_do_treino(r)
    assert padroes == ["flexao_plantar"]
    meta = _meta_h_a1(r, "panturrilha", "flexao_plantar")
    assert meta is not None and meta["degraded"] is False


# ── (k) Caso ABC Day A completo (3T) — preserva config E.0 com fix ──────

def test_abc_day_a_completo_sem_violacao_ancora(banco):
    """ABC 3T Day A original do harness E.0:
    `[peito(3), ombro(2), triceps(2)]`. Pré-H-A1: 100% das rotinas sem
    ombro_composto. Pós-H-A1: 0% violação."""
    demandas_por_treino = [
        [("subregiao", "peito", 3), ("subregiao", "ombro", 2), ("padrao", "triceps", 2)],
        [("subregiao", "costas", 4), ("subregiao", "bracos", 2), ("subregiao", "core_isometrico", 1)],
        [("subregiao", "perna_anterior", 2), ("subregiao", "perna_posterior", 2),
         ("subregiao", "adutores", 1), ("subregiao", "panturrilha", 1), ("subregiao", "core_dinamico", 1)],
    ]
    falhas = []
    for seed in range(5):
        r = gerar_rotina_csp(
            demandas_por_treino, banco, nivel_aluno=3, seed=seed,
            peso_evitar_agonistas=10, peso_tamanho_bloco=5,
        )
        assert r["viavel"], f"seed {seed} inviável"
        pads = _padroes_da_rotina(r)
        if "ombro_composto" not in pads:
            falhas.append(("ombro_composto", seed))
        if "biceps" not in pads:
            falhas.append(("biceps", seed))
        if "hinge" not in pads:
            falhas.append(("hinge", seed))
    assert not falhas, f"violações de âncora obrigatória pós-H-A1: {falhas}"
