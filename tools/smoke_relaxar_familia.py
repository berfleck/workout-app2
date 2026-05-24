"""Smoke E2E da Fatia 4.E — relaxar_familia via motor CSP.

Cobre o caminho que o adapter `/treino/<t>/regerar` executa em produção
(motor CSP + ConfigVariedade()), sem precisar do servidor Flask ou
browser. Replica a chamada feita pelo adapter, incluindo os argumentos
`familias_proibidas` e `relaxar_familia` adicionados pela 4.E.

Cenários cobertos (10 runs cada pra mostrar consistência):
1. Estrito viável, relax_ativado=False — familias_proibidas pequeno num
   padrão com várias famílias.
2. Estrito inviável + relax ON — proíbe a única família de
   knee_extension → relax dispara, badge ↻ no único ex retornado.
3. Estrito inviável + relax OFF — mesmo cenário, viável=False, treino
   "mantido" no fluxo real do adapter (smoke só checa o motor).
4. Travado supera familias_proibidas + NÃO conta como relaxado.
5. Sem familias_proibidas (None) — comportamento pré-4.E (relax_ativado
   sempre False, mesmo com flag ON).

Roda standalone:
    python tools/smoke_relaxar_familia.py
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


def _stat(banco, demandas, *, nivel, familias_proibidas, relaxar,
          travados=None, n_runs=10, label=""):
    print(f"\n=== {label} ===")
    print(f"  Demandas: {demandas}")
    print(f"  familias_proibidas: {familias_proibidas}")
    print(f"  relaxar_familia: {relaxar}")
    if travados:
        print(f"  Travados: {[t.nome for t in travados]}")
    print(f"  Nível: {nivel}, N runs: {n_runs}")
    viaveis = 0
    relax_ativadas = 0
    com_relaxados = 0
    n_exs_dist: Counter = Counter()
    primeiro_print = True
    for i in range(n_runs):
        seed = random.randint(0, 2**31 - 1)
        r = gerar_treino_csp(
            demandas, banco, nivel_aluno=nivel,
            seed=seed,
            variedade=ConfigVariedade(),
            travados=travados,
            familias_proibidas=set(familias_proibidas) if familias_proibidas else None,
            relaxar_familia=relaxar,
        )
        if not r["viavel"]:
            if primeiro_print:
                print(f"  [Run 1] INVIÁVEL (status={r['status']}) — esperado neste cenário")
                primeiro_print = False
            continue
        viaveis += 1
        if r.get("relax_ativado"):
            relax_ativadas += 1
        if r.get("relaxados"):
            com_relaxados += 1
        nomes = [e.nome for g in r["grupos"] for e in g["exercicios"]]
        n_exs_dist[len(nomes)] += 1
        if primeiro_print:
            print(f"  [Run 1] Exs ({len(nomes)}): {nomes}")
            print(f"  [Run 1] relax_ativado: {r.get('relax_ativado')}, "
                  f"relaxados: {r.get('relaxados')}")
            primeiro_print = False
    print(f"  Viáveis: {viaveis}/{n_runs}")
    print(f"  relax_ativado=True em: {relax_ativadas}/{n_runs}")
    print(f"  com relaxados não-vazio em: {com_relaxados}/{n_runs}")
    print(f"  Distribuição n_exs: {dict(n_exs_dist)}")


def main():
    banco = carregar_banco_ativo()
    cadeira = _ex_por_nome(banco, "Cadeira Extensora")

    # 1. Estrito viável (puxadas tem 4 famílias, proibir 1 ainda deixa 3)
    _stat(
        banco,
        [("padrao", "puxadas", 2)],
        nivel=3, familias_proibidas={"Pullover"}, relaxar=True,
        label="1. Estrito viável (banco rico — relax NÃO dispara)",
    )

    # 2. Estrito inviável + relax ON → dispara
    _stat(
        banco,
        [("padrao", "knee_extension", 1)],
        nivel=3, familias_proibidas={"Cadeira Extensora"}, relaxar=True,
        label="2. Estrito inviável + relax ON (esperado: 100% relax_ativado)",
    )

    # 3. Estrito inviável + relax OFF → permanece inviável
    _stat(
        banco,
        [("padrao", "knee_extension", 1)],
        nivel=3, familias_proibidas={"Cadeira Extensora"}, relaxar=False,
        label="3. Estrito inviável + relax OFF (esperado: 0% viável)",
    )

    # 4. Travado supera familias_proibidas + NÃO conta como relaxado
    _stat(
        banco,
        [("padrao", "knee_extension", 1)],
        nivel=3, familias_proibidas={"Cadeira Extensora"}, relaxar=True,
        travados=[cadeira],
        label="4. Travado bypassa filtro de família (relax NÃO dispara, sem relaxados)",
    )

    # 5. Sem familias_proibidas → regressão pré-4.E
    _stat(
        banco,
        [("subregiao", "peito", 2), ("subregiao", "costas", 2)],
        nivel=3, familias_proibidas=None, relaxar=True,
        label="5. Sem familias_proibidas (regressão — relax_ativado=False sempre)",
    )

    print("\n[OK] Smoke completo. Verifique que:")
    print("  - Cenário 1: viáveis=10, relax_ativado=0/10, relaxados=0/10")
    print("  - Cenário 2: viáveis=10, relax_ativado=10/10, relaxados=10/10 "
          "(todos com Cadeira Extensora)")
    print("  - Cenário 3: viáveis=0/10 (inviável sem relax)")
    print("  - Cenário 4: viáveis=10, relax_ativado=0/10, relaxados=0/10 "
          "(travado entrou sem precisar relaxar)")
    print("  - Cenário 5: viáveis=10, relax_ativado=0/10, relaxados=0/10")


if __name__ == "__main__":
    main()
