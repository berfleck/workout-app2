"""Smoke E2E da Fatia 4.D — exercícios travados via motor CSP.

Cobre o caminho que o adapter `/treino/<t>/regerar` executa em produção,
sem precisar do servidor Flask ou UI clicável (UI de travar é pendência
listada no CLAUDE.md).

Cenários cobertos (10 runs cada pra mostrar consistência):
1. Travado em demanda compatível — Apoio em peito × 2.
2. Travado off-script — Apoio em treino só de pernas (vira extra).
3. Travado supera nível iniciante — Apoio (cx=3) com aluno nivel=1.
4. Travado supera H-T4 — Crossover (Acessório) em peito × 1.
5. Sem travados — sanity de regressão (mesma rotina que pré-4.D).

Roda standalone:
    python tools/smoke_travados.py
"""
from __future__ import annotations

import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gerador_csp import (  # noqa: E402
    ConfigVariedade,
    carregar_banco_ativo,
    gerar_treino_csp,
)


def _ex_por_nome(banco, nome):
    for e in banco:
        if e.nome == nome:
            return e
    raise ValueError(f"{nome} não está no banco")


def _stat(banco, demandas, *, nivel, travados, n_runs=10, label=""):
    print(f"\n=== {label} ===")
    print(f"  Demandas: {demandas}")
    print(f"  Travados: {[t.nome for t in (travados or [])]}")
    print(f"  Nível: {nivel}, N runs: {n_runs}")
    travados_presentes = 0
    n_exs_dist: Counter = Counter()
    primeiro_print = True
    for i in range(n_runs):
        seed = random.randint(0, 2**31 - 1)
        r = gerar_treino_csp(
            demandas, banco, nivel_aluno=nivel,
            seed=seed,
            variedade=ConfigVariedade(),  # modo padrão do /regerar
            travados=travados,
        )
        if not r["viavel"]:
            print(f"  [FAIL] Run {i+1}: inviável (status={r['status']})")
            continue
        nomes = [e.nome for g in r["grupos"] for e in g["exercicios"]]
        n_exs_dist[len(nomes)] += 1
        for t in (travados or []):
            if t.nome in nomes:
                travados_presentes += 1
        if primeiro_print:
            print(f"  [Run 1] Exs ({len(nomes)}): {nomes}")
            print(f"  [Run 1] Blocos: {[[e.nome for e in b] for b in r.get('blocos', [])]}")
            primeiro_print = False
    print(f"  Travados presentes: {travados_presentes}/{n_runs * max(1, len(travados or []))}")
    print(f"  Distribuição n_exs: {dict(n_exs_dist)}")


def main():
    banco = carregar_banco_ativo()
    apoio = _ex_por_nome(banco, "Apoio")
    crossover = _ex_por_nome(banco, "Crossover")

    # 1. Travado em demanda compatível
    _stat(
        banco,
        [("subregiao", "peito", 2), ("subregiao", "costas", 2)],
        nivel=3, travados=[apoio], label="1. Travado em demanda compatível",
    )

    # 2. Travado off-script (vira extra)
    _stat(
        banco,
        [("subregiao", "perna_anterior", 2)],
        nivel=3, travados=[apoio],
        label="2. Travado off-script (esperado 3 exs = 2 pernas + 1 extra)",
    )

    # 3. Travado supera nível iniciante
    _stat(
        banco,
        [("subregiao", "peito", 2)],
        nivel=1, travados=[apoio],
        label="3. Travado supera H-P1 (Apoio cx=3, aluno nível 1 teto cx=2)",
    )

    # 4. Travado Acessório supera H-T4
    _stat(
        banco,
        [("subregiao", "peito", 1)],
        nivel=3, travados=[crossover],
        label="4. Travado supera H-T4 (Crossover Acessório em vaga única)",
    )

    # 5. Sem travados — regressão
    _stat(
        banco,
        [("subregiao", "peito", 2), ("subregiao", "costas", 2)],
        nivel=3, travados=None,
        label="5. Sem travados (regressão — esperado 4 exs sempre)",
    )

    print("\n[OK] Smoke completo. Verifique que:")
    print("  - Cenários 1-4: travado aparece nos runs (presentes >= n_runs)")
    print("  - Cenário 2: distribuição n_exs = {3: N} (travado virou extra)")
    print("  - Cenário 5: distribuição n_exs = {4: N} (sem travado)")


if __name__ == "__main__":
    main()
