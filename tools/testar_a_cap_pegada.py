"""Testa combinacao de:
  - Opcao A: re-tag pegada=aberta -> pegada=pronada (in-memory)
  - Cap:     reduzir peso INTRA da pegada em costas de soft_alto (-50)
             pra soft_medio (-20) via pesos_override

4 cenarios:
  1. BASELINE (estado atual)
  2. A apenas
  3. CAP apenas
  4. A + CAP combinados

Output: distribuicao por familia, dentro de curvada, e por exercicio.
"""
from __future__ import annotations

import random
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gerador_treino import carregar_banco, gerar_multiplos_treinos
from pesos_proximidade import (
    ConfigPesosProximidade,
    PesoDim,
    PESOS_DEFAULT,
    _config_default,
)

XLSX_PATH = "banco_exercicios.xlsx"
N_ITER = 2000
LM_NAMES = {"Remada LM Neutra", "Remada LM Aberta"}
CONFIGS = [{"demandas": [("regiao", "upper", 4), ("regiao", "lower", 2)]}]


def _exercicios(sessao):
    for b in sessao.blocos:
        for e in (b.ex1, b.ex2, b.ex3):
            if e is not None:
                yield e


def banco_opcao_a(banco):
    """Aberta -> pronada em todo o banco (in-memory)."""
    return [replace(e, pegada="pronada") if e.pegada == "aberta" else e
            for e in banco]


def config_com_cap_pegada_costas():
    """Pesos defaults + override INTRA pegada em costas: soft_alto -> soft_medio."""
    cfg = _config_default()
    cfg.pegada.intra_overrides = dict(cfg.pegada.intra_overrides)
    cfg.pegada.intra_overrides["costas"] = "soft_medio"
    return cfg


def rodar(banco, pesos_override, label, n_iter=N_ITER):
    freq_remada: Counter = Counter()
    freq_puxada: Counter = Counter()
    n_lm = 0
    n_curv = 0
    fam_count: Counter = Counter()
    fam = {e.nome: (e.variacao_de or e.nome) for e in banco}
    for i in range(n_iter):
        random.seed(i)
        sessoes = gerar_multiplos_treinos(
            banco, CONFIGS, relaxar_familia=True,
            pesos_override=pesos_override,
        )
        tem_lm = False
        tem_curv = False
        for s in sessoes:
            for e in _exercicios(s):
                if e.padrao == "remadas":
                    freq_remada[e.nome] += 1
                    fam_count[fam[e.nome]] += 1
                    if e.nome in LM_NAMES:
                        tem_lm = True
                    if fam[e.nome] == "curvada":
                        tem_curv = True
                elif e.padrao == "puxadas":
                    freq_puxada[e.nome] += 1
        if tem_lm:
            n_lm += 1
        if tem_curv:
            n_curv += 1
    return {
        "label": label,
        "remadas": freq_remada,
        "puxadas": freq_puxada,
        "fam": fam_count,
        "n_lm": n_lm,
        "n_curv": n_curv,
        "n_iter": n_iter,
    }


def main():
    banco = carregar_banco(XLSX_PATH)
    banco_a = banco_opcao_a(banco)
    cfg_cap = config_com_cap_pegada_costas()

    print(f"Rodando 4 cenarios x N={N_ITER}...")
    print()
    print("[1/4] BASELINE...")
    res_baseline = rodar(banco, None, "BASELINE")
    print("[2/4] OPCAO A (aberta->pronada)...")
    res_a = rodar(banco_a, None, "A: tag")
    print("[3/4] CAP (pegada costas: alto->medio)...")
    res_cap = rodar(banco, cfg_cap, "CAP: -50->-20")
    print("[4/4] A + CAP...")
    res_ac = rodar(banco_a, cfg_cap, "A + CAP")

    todos = [res_baseline, res_a, res_cap, res_ac]

    # Top-line
    print()
    print("=" * 100)
    print(f"COMPARATIVO N={N_ITER} (upper(4)+lower(2) x 1T)")
    print("=" * 100)

    print()
    print("--- Top-line: rotinas com qualquer LM / com familia curvada ---")
    print(f"  {'cenario':25s}  {'com LM':>15s}  {'com curvada':>15s}  {'LM/curvada':>10s}")
    for r in todos:
        pct_lm = 100 * r["n_lm"] / r["n_iter"]
        pct_curv = 100 * r["n_curv"] / r["n_iter"]
        ratio = (r["n_lm"] / r["n_curv"]) if r["n_curv"] else 0
        print(f"  {r['label']:25s}  {pct_lm:6.2f}% ({r['n_lm']:4d})  {pct_curv:6.2f}% ({r['n_curv']:4d})  {100*ratio:9.2f}%")

    # Familia distribution
    print()
    print("--- REMADAS por FAMILIA (% do total de slots remada) ---")
    fams = ["curvada", "unilateral", "trx", "baixa", "apoiado", "seal"]
    fam_members = {"curvada": 5, "unilateral": 3, "trx": 2, "baixa": 2, "apoiado": 1, "seal": 1}
    print(f"  {'familia':12s}  ({'mem':>3s}) " + " | ".join(f"{r['label'][:12]:>13s}" for r in todos))
    print("  " + "-" * (24 + 16 * len(todos)))
    for f in fams:
        n_mem = fam_members[f]
        baseline_uniform = 100 * n_mem / 14  # share teorica por banco
        row = f"  {f:12s}  ({n_mem:>3d})  "
        for r in todos:
            tot = sum(r["fam"].values())
            ct = r["fam"][f]
            pct = 100 * ct / tot if tot else 0
            row += f"{pct:5.1f}%  ({ct:4d})  "
        print(row)
    print(f"  {'  banco share=':25s}", " | ".join(f"{100*fam_members[f]/14:5.1f}%        " for f in fams))

    # Dentro da familia curvada
    print()
    print("--- DENTRO DA FAMILIA CURVADA (5 ex, uniforme = 20%) ---")
    curvada_names = [
        "Remada Curvada Barra", "Remada Curvada Smith", "Remada Curvada Halteres",
        "Remada LM Neutra", "Remada LM Aberta",
    ]
    print(f"  {'exercicio':28s} " + " | ".join(f"{r['label'][:13]:>14s}" for r in todos))
    for nome in curvada_names:
        marker = " ⭐" if nome in LM_NAMES else "  "
        row = f"  {marker}{nome:26s} "
        for r in todos:
            tot_c = sum(r["remadas"].get(n, 0) for n in curvada_names)
            ct = r["remadas"].get(nome, 0)
            pct = 100 * ct / tot_c if tot_c else 0
            razao = pct / 20
            row += f"{pct:5.2f}% ({razao:.2f}x)  "
        print(row)

    # TODAS as remadas (full table)
    print()
    print("--- TODAS REMADAS (contagem absoluta) ---")
    todas_rem = sorted({n for r in todos for n in r["remadas"]},
                       key=lambda n: -res_baseline["remadas"].get(n, 0))
    print(f"  {'exercicio':28s} " + " | ".join(f"{r['label'][:13]:>13s}" for r in todos))
    for nome in todas_rem:
        marker = " ⭐" if nome in LM_NAMES else "  "
        row = f"  {marker}{nome:26s} " + " | ".join(
            f"{r['remadas'].get(nome, 0):13d}" for r in todos)
        print(row)

    # Puxadas (sanity)
    print()
    print("--- PUXADAS (sanity check — devem ser estaveis) ---")
    todas_pux = sorted({n for r in todos for n in r["puxadas"]},
                       key=lambda n: -res_baseline["puxadas"].get(n, 0))
    print(f"  {'exercicio':28s} " + " | ".join(f"{r['label'][:13]:>13s}" for r in todos))
    for nome in todas_pux:
        row = f"   {nome:27s} " + " | ".join(
            f"{r['puxadas'].get(nome, 0):13d}" for r in todos)
        print(row)

    # Totais
    print()
    print("--- Sanity totais ---")
    for r in todos:
        tot_r = sum(r["remadas"].values())
        tot_p = sum(r["puxadas"].values())
        print(f"  {r['label']:25s}  remadas={tot_r:4d}  puxadas={tot_p:4d}")


if __name__ == "__main__":
    main()
