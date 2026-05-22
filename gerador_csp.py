# gerador_csp.py
# Spike Fatia 1 do MVP - 2026-05-21
# Engine declarativa minimalista usando CP-SAT do OR-Tools.
#
# Implementa (do catalogo_constraints.md):
#   - H-T4 (vaga única => composto/principal, NÃO Acessório)
#   - S-T1 (tier-order: tier alto antes de tier baixo na ordem do treino)
#   - H-P1 (nível técnico do aluno filtra pool por complexidade)
# Filtra: ativo=True no load (mesmo padrão do gerador_treino.py antigo).
# Tier: heurística TEMPORÁRIA derivada de purpose+padrão (substituir na
#       Fatia 2 por leitura de coluna `tier` cadastrada manualmente).
#
# Roda em PARALELO ao gerador_treino.py antigo. NÃO toca no antigo.

from __future__ import annotations

import time
from collections import defaultdict

from ortools.sat.python import cp_model

# Reusa o banco/dataclass/âncoras do gerador antigo SEM modificá-lo.
# carregar_banco() já filtra ativo=True (gerador_treino.py:991).
from gerador_treino import (
    Exercicio,
    carregar_banco,
    XLSX_PATH,
    ANCORAS_POR_SUBREGIAO,
)


# ---------------------------------------------------------------------------
# Tiers
# ---------------------------------------------------------------------------

# Vocabulário de tier (3 níveis). String pra legibilidade; ordem pra S-T1.
TIER_PRINCIPAL = "Principal"
TIER_INTERMEDIARIO = "Intermediário"
TIER_ACESSORIO = "Acessório"

# Rank numérico: MAIOR = mais "alto" (vem primeiro no treino). Usado por S-T1.
TIER_RANK: dict[str, int] = {
    TIER_PRINCIPAL: 3,
    TIER_INTERMEDIARIO: 2,
    TIER_ACESSORIO: 1,
}

# Conjunto canônico de "padrões âncora" derivado de ANCORAS_POR_SUBREGIAO
# do gerador_treino.py. Decisão fechada com Bernardo (2026-05-22): um padrão
# é âncora ⟺ APARECE em ANCORAS_POR_SUBREGIAO (qualquer obrigatoriedade).
#
# Por que membership e não obrigatoria=True: a estrutura SE CHAMA "âncoras" —
# tudo nela já é âncora; `obrigatoria` é sub-propriedade (must-have vs opcional),
# ortogonal a tier. Usar obrigatoria=True rebaixaria `squat_unilateral`
# (compound) para Intermediário — criando hierarquia bilateral>unilateral que
# NÃO deve existir clinicamente. `squat_unilateral` é, aliás, o ÚNICO padrão
# obrigatoria=False com exercícios compound (os demais — empurrar_isolados,
# ombro_isolado, posterior_ombro, knee_flexion, abduction — são isolation e
# já caem em Acessório pela regra anterior). Logo membership ≡ "obrigatoria=True
# + exceção squat_unilateral", só que sem caso especial hardcoded.
#
# NÃO é lista paralela — é derivado da fonte canônica do gerador antigo.
PADROES_ANCORA: frozenset[str] = frozenset(
    a["padrao"]
    for ancoras in ANCORAS_POR_SUBREGIAO.values()
    for a in ancoras
)


def _padrao_e_ancora(padrao: str) -> bool:
    """Padrão é âncora? (= aparece em ANCORAS_POR_SUBREGIAO).

    Fonte canônica: gerador_treino.ANCORAS_POR_SUBREGIAO. Ver PADROES_ANCORA.
    """
    return padrao in PADROES_ANCORA


# ┌─────────────────────────────────────────────────────────────────────┐
# │ TEMPORÁRIA — substituir na Fatia 2 por leitura da coluna `tier`      │
# │ cadastrada manualmente no XLSX. Esta heurística deriva tier de       │
# │ purpose + padrão como andaime pro spike rodar sem cadastro.          │
# └─────────────────────────────────────────────────────────────────────┘
def derivar_tier_heuristico(exercicio: Exercicio) -> str:
    """Deriva tier (Principal/Intermediário/Acessório) por heurística.

    ⚠️ TEMPORÁRIA (Fatia 1). A coluna `tier` cadastrada à mão na Fatia 2
    substitui esta função inteira. purpose e tier são ortogonais — esta
    heurística é só uma aproximação inicial (ex: Hip Thrust=isolation cai
    em Acessório; refinamento clínico previsto na Fatia 2).

    Regras (cobrindo os 4 valores de purpose do banco):
      compound  + padrão É âncora    → Principal
      compound  + padrão NÃO é âncora → Intermediário
      isolation                       → Acessório
      stability + subregião core      → Principal (dentro de core)
      stability + subregião não-core  → Acessório (fallback)
      explosive                       → Principal (raro; só Agach. Lateral ativo)
    """
    purpose = (exercicio.purpose or "").strip().lower()

    if purpose == "compound":
        return TIER_PRINCIPAL if _padrao_e_ancora(exercicio.padrao) else TIER_INTERMEDIARIO
    if purpose == "isolation":
        return TIER_ACESSORIO
    if purpose == "stability":
        if (exercicio.subregiao or "").startswith("core"):
            return TIER_PRINCIPAL
        return TIER_ACESSORIO
    if purpose == "explosive":
        return TIER_PRINCIPAL

    # purpose vazio/desconhecido: degrau mais baixo (não some do pool, mas
    # nunca ocupa vaga única — H-T4 trata).
    return TIER_ACESSORIO


# ---------------------------------------------------------------------------
# Carregamento do banco (filtro ativo=True embutido em carregar_banco)
# ---------------------------------------------------------------------------

def carregar_banco_ativo(path_xlsx: str = XLSX_PATH) -> list[Exercicio]:
    """Carrega o banco já filtrando ativo=True.

    Wrapper fino sobre gerador_treino.carregar_banco, que JÁ descarta linhas
    com ativo=False (gerador_treino.py:991). Existe pra deixar o filtro
    explícito no namespace do spike e pra documentar o critério.
    """
    return carregar_banco(path_xlsx)


# ---------------------------------------------------------------------------
# H-P1 — Nível técnico do aluno filtra o pool por complexidade
# ---------------------------------------------------------------------------

# Teto de complexidade por nível técnico do aluno (escala real do XLSX = int 1-5).
# Nível 3 (avançado) = sem teto. Filtro HARD: aplicado ANTES do solver começar.
TETO_COMPLEXIDADE_POR_NIVEL: dict[int, int] = {
    1: 2,  # iniciante: só baixa complexidade
    2: 3,  # intermediário: média
    3: 5,  # avançado: sem teto efetivo (5 = máximo da escala)
}


def filtrar_pool_por_nivel(banco: list[Exercicio], nivel_aluno: int) -> list[Exercicio]:
    """H-P1: remove exercícios acima do teto de complexidade do nível.

    Filtro hard de pool (vetor de perfil, dimensão Nível técnico). Roda antes
    do solver — exercício complexo demais simplesmente não vira variável.
    Nível desconhecido → sem teto (fail-open, não esconde exercício à toa).
    """
    teto = TETO_COMPLEXIDADE_POR_NIVEL.get(nivel_aluno, 5)
    return [e for e in banco if e.complexidade <= teto]


# ---------------------------------------------------------------------------
# Engine CP-SAT minimalista
# ---------------------------------------------------------------------------
#
# Modelagem (Fatia 1 — só H-T4 + S-T1):
#   - Uma "demanda" (nivel, escopo, qtd) vira `qtd` SLOTS. O treino é a
#     concatenação dos slots na ORDEM das demandas (subregião A, depois B...).
#   - Cada slot recebe exatamente 1 exercício do seu pool (bool de atribuição).
#   - Nenhum exercício se repete no treino (AllDifferent global por nome).
#   - H-T4 (HARD): slot de demanda `subregiao` com qtd==1 não pode receber
#     tier Acessório. NÃO aplica a demandas `padrao` (intenção explícita).
#   - S-T1 (SOFT/objetivo): dentro de cada grupo de demanda, penaliza pares
#     (i<j na ordem) em que o slot mais cedo tem tier MENOR que o mais tarde.
#     Penalidade proporcional ao gap de tier (inversão). Solver minimiza a soma.
#
# Sem ordem de processamento entre demandas: todos os slots negociam no mesmo
# modelo (princípio do refator declarativo). O agrupamento por demanda é só a
# semântica de saída — o solver resolve tudo simultaneamente.


def _pool_da_demanda(banco: list[Exercicio], nivel: str, escopo: str) -> list[Exercicio]:
    """Exercícios elegíveis para uma demanda, conforme o nível de hierarquia."""
    if nivel == "subregiao":
        return [e for e in banco if e.subregiao == escopo]
    if nivel == "padrao":
        return [e for e in banco if e.padrao == escopo]
    if nivel == "regiao":
        return [e for e in banco if e.regiao == escopo]
    return []


def gerar_treino_csp(
    demandas: list[tuple[str, str, int]],
    banco: list[Exercicio],
    nivel_aluno: int,
    seed: int = 0,
) -> dict:
    """Resolve um treino via CP-SAT. Devolve dict estruturado (ver imprimir_resultado).

    `demandas`: lista de (nivel, escopo, qtd). `banco`: lista já carregada
    (ativo=True). `nivel_aluno`: 1/2/3 (filtra pool por complexidade — H-P1).
    `seed`: semente do solver (pra observar determinismo vs variedade).
    """
    # H-P1: filtra o pool global por complexidade ANTES de montar o modelo.
    banco_nivel = filtrar_pool_por_nivel(banco, nivel_aluno)

    model = cp_model.CpModel()

    # ── Monta grupos (1 por demanda) e slots (qtd por grupo) ────────────────
    grupos: list[dict] = []
    slots: list[dict] = []
    for di, (nivel, escopo, qtd) in enumerate(demandas):
        pool = _pool_da_demanda(banco_nivel, nivel, escopo)
        g = {"di": di, "demanda": (nivel, escopo, qtd), "pool": pool, "slot_ids": []}
        grupos.append(g)
        for _pos in range(qtd):
            sid = len(slots)
            slots.append({"sid": sid, "di": di})
            g["slot_ids"].append(sid)

    # ── Variáveis de atribuição: assign[(sid, cidx)] ────────────────────────
    assign: dict[tuple[int, int], cp_model.IntVar] = {}
    for s in slots:
        pool = grupos[s["di"]]["pool"]
        bvars = []
        for cidx in range(len(pool)):
            b = model.NewBoolVar(f"a_s{s['sid']}_c{cidx}")
            assign[(s["sid"], cidx)] = b
            bvars.append(b)
        if bvars:
            model.AddExactlyOne(bvars)  # cada slot = exatamente 1 exercício

    # ── AllDifferent global (por nome do exercício) ─────────────────────────
    por_nome: dict[str, list] = defaultdict(list)
    for s in slots:
        pool = grupos[s["di"]]["pool"]
        for cidx, ex in enumerate(pool):
            por_nome[ex.nome].append(assign[(s["sid"], cidx)])
    for vars_do_nome in por_nome.values():
        if len(vars_do_nome) > 1:
            model.AddAtMostOne(vars_do_nome)

    # ── tier_rank por slot (IntVar = soma assign × rank) ────────────────────
    tier_rank: dict[int, cp_model.IntVar] = {}
    for s in slots:
        pool = grupos[s["di"]]["pool"]
        ranks = [TIER_RANK[derivar_tier_heuristico(ex)] for ex in pool]
        lo, hi = (min(ranks), max(ranks)) if ranks else (0, 0)
        tr = model.NewIntVar(lo, hi, f"tier_s{s['sid']}")
        model.Add(tr == sum(assign[(s["sid"], c)] * ranks[c] for c in range(len(pool))))
        tier_rank[s["sid"]] = tr

    # ── H-T4 (HARD): subregião + qtd==1 ⇒ não-Acessório ─────────────────────
    for g in grupos:
        nivel, escopo, qtd = g["demanda"]
        if nivel == "subregiao" and qtd == 1:
            sid = g["slot_ids"][0]
            for cidx, ex in enumerate(g["pool"]):
                if derivar_tier_heuristico(ex) == TIER_ACESSORIO:
                    model.Add(assign[(sid, cidx)] == 0)

    # ── S-T1 (SOFT): inversões de tier-order dentro de cada grupo ───────────
    rank_max = max(TIER_RANK.values())
    penalidades = []
    for g in grupos:
        sids = g["slot_ids"]
        for i in range(len(sids)):
            for j in range(i + 1, len(sids)):
                # slot sids[i] vem antes de sids[j] na ordem do treino.
                # viol = max(0, tier[j] - tier[i]): pune tier maior vindo depois.
                viol = model.NewIntVar(0, rank_max, f"viol_{sids[i]}_{sids[j]}")
                model.Add(viol >= tier_rank[sids[j]] - tier_rank[sids[i]])
                penalidades.append(viol)
    if penalidades:
        model.Minimize(sum(penalidades))

    # ── Resolve ─────────────────────────────────────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.random_seed = seed
    solver.parameters.randomize_search = True
    t0 = time.perf_counter()
    status = solver.Solve(model)
    solve_time = time.perf_counter() - t0

    status_nome = solver.StatusName(status)
    resultado: dict = {
        "status": status_nome,
        "viavel": status in (cp_model.OPTIMAL, cp_model.FEASIBLE),
        "nivel_aluno": nivel_aluno,
        "seed": seed,
        "solve_time": solve_time,
        "inversoes": int(round(solver.ObjectiveValue())) if (penalidades and status in (cp_model.OPTIMAL, cp_model.FEASIBLE)) else 0,
        "grupos": [],
        "ordem_global": [],
    }
    if not resultado["viavel"]:
        return resultado

    # ── Decodifica (lê slots em ordem de posição) ───────────────────────────
    for g in grupos:
        nivel, escopo, qtd = g["demanda"]
        exs = []
        for sid in g["slot_ids"]:
            for cidx, ex in enumerate(g["pool"]):
                if solver.Value(assign[(sid, cidx)]) == 1:
                    exs.append(ex)
                    break
        resultado["grupos"].append({
            "demanda": g["demanda"],
            "exercicios": exs,
            "pool_size": len(g["pool"]),
            "h_t4_aplicado": nivel == "subregiao" and qtd == 1,
        })
        resultado["ordem_global"].extend(exs)
    return resultado


# ---------------------------------------------------------------------------
# Output formatado pra leitura humana
# ---------------------------------------------------------------------------

def _tier_ordem_ok(resultado: dict) -> bool:
    """True se, em todo grupo, o tier é não-crescente na ordem dos slots."""
    for g in resultado["grupos"]:
        ranks = [TIER_RANK[derivar_tier_heuristico(e)] for e in g["exercicios"]]
        if any(ranks[k] < ranks[k + 1] for k in range(len(ranks) - 1)):
            return False
    return True


def _vagas_unicas_nao_acessorio(resultado: dict) -> tuple[bool, list[str]]:
    """Confere H-T4: toda vaga única de subregião tem tier != Acessório."""
    ok = True
    detalhes = []
    for g in resultado["grupos"]:
        if not g["h_t4_aplicado"]:
            continue
        nivel, escopo, qtd = g["demanda"]
        for e in g["exercicios"]:
            t = derivar_tier_heuristico(e)
            detalhes.append(f"{escopo}={t}")
            if t == TIER_ACESSORIO:
                ok = False
    return ok, detalhes


def imprimir_resultado(resultado: dict, titulo: str = "") -> None:
    """Imprime uma rotina gerada no formato de leitura humana + validação."""
    cab = f"=== {titulo} ===" if titulo else "=== Rotina ==="
    print(cab)
    if not resultado["viavel"]:
        print(f"  INVIÁVEL (status={resultado['status']}) — pool insuficiente "
              f"pra atender as demandas no nível {resultado['nivel_aluno']}.")
        print()
        return

    i = 1
    for g in resultado["grupos"]:
        nivel, escopo, qtd = g["demanda"]
        for k, ex in enumerate(g["exercicios"]):
            tier = derivar_tier_heuristico(ex)
            marca = ""
            if g["h_t4_aplicado"] and k == 0:
                marca = "   <- vaga única OK" if tier != TIER_ACESSORIO else "   <- ⚠ vaga única ACESSÓRIO"
            print(f"{i}. [{tier:<13}] {ex.nome:<30} ({escopo}){marca}")
            i += 1

    tier_ok = _tier_ordem_ok(resultado)
    ht4_ok, ht4_det = _vagas_unicas_nao_acessorio(resultado)
    print()
    print("Validação:")
    print(f"  Tier-order respeitado?  {'SIM' if tier_ok else 'NÃO'}")
    print(f"  Vagas únicas != Acessório?  {'SIM' if ht4_ok else 'NÃO'}"
          + (f" ({', '.join(ht4_det)})" if ht4_det else " (nenhuma vaga única)"))
    print(f"  Inversões de tier (S-T1): {resultado['inversoes']}")
    print(f"  Tempo de solving: {resultado['solve_time']:.4f}s")
    print()


# ---------------------------------------------------------------------------
# Script de teste standalone
# ---------------------------------------------------------------------------

# Config A — rotina padrão com vagas únicas (testa H-T4 em ombro + perna_post)
DEMANDAS_A: list[tuple[str, str, int]] = [
    ("subregiao", "peito", 2),
    ("subregiao", "costas", 2),
    ("subregiao", "ombro", 1),              # vaga única — H-T4 dispara
    ("subregiao", "perna_anterior", 2),
    ("subregiao", "perna_posterior", 1),    # vaga única — H-T4 dispara
]

# Config B — inclui knee_extension explicitamente (testa pool de 1 + padrão)
DEMANDAS_B: list[tuple[str, str, int]] = [
    ("subregiao", "peito", 2),
    ("padrao", "knee_extension", 1),        # padrão explícito: só Cadeira Extensora
    ("subregiao", "perna_posterior", 1),
]


def _main() -> None:
    banco = carregar_banco_ativo()
    inativos_esperados = {"Box Jump", "Air Bike Sprint", "Air Bike Steady"}
    nomes_no_pool = {e.nome for e in banco}
    print(f"Banco ativo carregado: {len(banco)} exercícios")
    vazou = inativos_esperados & nomes_no_pool
    print(f"Filtro ativo=True: "
          + ("OK (0 inativos no pool — Box Jump, Air Bike Sprint/Steady ausentes)"
             if not vazou else f"⚠ VAZOU: {vazou}"))
    print()

    # ── Config A — 5 rodadas com seeds diferentes ───────────────────────────
    print("#" * 70)
    print("# Config A — nível 3 (avançado), 5 rodadas (seeds 42..46)")
    print("#" * 70)
    print()
    assinaturas = []
    for n, seed in enumerate([42, 43, 44, 45, 46], start=1):
        r = gerar_treino_csp(DEMANDAS_A, banco, nivel_aluno=3, seed=seed)
        imprimir_resultado(r, f"Rotina {n} (Config A, nível 3, seed={seed})")
        assinaturas.append(tuple(e.nome for e in r["ordem_global"]))
    distintas = len(set(assinaturas))
    print(f">> Variedade entre as 5 rotinas: {distintas} distintas de 5 "
          f"({'solver explora soluções' if distintas > 1 else 'solver determinístico — mesma solução'}).")
    print()

    # ── Config B — 1 rodada (knee_extension) ────────────────────────────────
    print("#" * 70)
    print("# Config B — nível 3, knee_extension explícito (pool de 1)")
    print("#" * 70)
    print()
    rb = gerar_treino_csp(DEMANDAS_B, banco, nivel_aluno=3, seed=42)
    imprimir_resultado(rb, "Rotina (Config B, nível 3, seed=42)")
    nomes_b = [e.nome for g in rb["grupos"] for e in g["exercicios"]]
    print(f">> Cadeira Extensora presente? "
          f"{'SIM' if any('Extensora' in n for n in nomes_b) else 'NÃO'}")
    print()

    # ── Bônus — Config A no nível 1, mostrando encolhimento de pool ──────────
    print("#" * 70)
    print("# Bônus — Config A no nível 1 (iniciante): filtro de complexidade")
    print("#" * 70)
    print()
    pool_n3 = filtrar_pool_por_nivel(banco, 3)
    pool_n1 = filtrar_pool_por_nivel(banco, 1)
    print(f"Pool global: nível 3 = {len(pool_n3)} exercícios → nível 1 = {len(pool_n1)} "
          f"(−{len(pool_n3) - len(pool_n1)} de complexidade > 2)")
    sumidos = sorted({e.nome for e in pool_n3} - {e.nome for e in pool_n1})
    print(f"Exemplos que somem no nível 1 ({len(sumidos)} no total): {sumidos[:8]}")
    print()
    r1 = gerar_treino_csp(DEMANDAS_A, banco, nivel_aluno=1, seed=42)
    imprimir_resultado(r1, "Rotina (Config A, nível 1, seed=42)")


if __name__ == "__main__":
    _main()
