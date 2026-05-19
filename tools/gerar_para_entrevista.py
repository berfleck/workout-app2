"""Gera rotinas pra avaliacao clinica em entrevistas guiadas.

Configs disponiveis (CLI flag --config):
  varB-2x : Variante B do 2x semana (Sec 2.2 configuracoes_comuns)
            T1: peito(2)+ombro(1)+perna_post(3)+core(1)+triceps(1) = 8
            T2: costas(3)+perna_ant(3)+core(1)+biceps(1) = 8
  varA-3x : Variante A do 3x semana (Sec 2.3) — 3 full body com vies
            T1/T2/T3: upper(3)+lower(3)+core(2) = 8 ex cada

Uso:
  python tools/gerar_para_entrevista.py [--config varB-2x|varA-3x]
                                        [--n-rotinas N] [--seed BASE]
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gerador_treino import carregar_banco, gerar_multiplos_treinos

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------

CONFIGS = {
    "varB-2x": {
        "label": "Variante B do 2x semana (Empurrar+Posterior / Puxar+Anterior)",
        "treinos": [
            {
                "label": "T1 (Empurrar + Posterior)",
                "demandas": [
                    ("subregiao", "peito", 2),
                    ("subregiao", "ombro", 1),
                    ("subregiao", "perna_posterior", 3),
                    ("subregiao", "core", 1),
                    ("padrao",    "triceps", 1),
                ],
            },
            {
                "label": "T2 (Puxar + Anterior)",
                "demandas": [
                    ("subregiao", "costas", 3),
                    ("subregiao", "perna_anterior", 3),
                    ("subregiao", "core", 1),
                    ("padrao",    "biceps", 1),
                ],
            },
        ],
    },
    "varA-3x": {
        "label": "Variante A do 3x semana — 3 full body com viés",
        "treinos": [
            {
                "label": f"T{i+1} (full body)",
                "demandas": [
                    ("regiao", "upper", 3),
                    ("regiao", "lower", 3),
                    ("regiao", "core", 2),
                ],
            }
            for i in range(3)
        ],
    },
}


def fmt_treino(sessao, label):
    linhas = [f"  **{label}**"]
    for i, bloco in enumerate(sessao.blocos):
        prefix = chr(ord("A") + i)
        nomes = []
        for e in (bloco.ex1, bloco.ex2, bloco.ex3):
            if e is None:
                continue
            tag = ""
            if e.purpose not in ("compound", "explosive"):
                tag = " (isolado)"
            nomes.append(f"{e.nome}{tag}")
        linhas.append(f"  - {prefix}: {' + '.join(nomes)}")
    return "\n".join(linhas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", choices=list(CONFIGS.keys()), default="varB-2x")
    ap.add_argument("--n-rotinas", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    cfg = CONFIGS[args.config]
    configs_treinos = [{"demandas": t["demandas"]} for t in cfg["treinos"]]
    labels = [t["label"] for t in cfg["treinos"]]

    banco = carregar_banco("banco_exercicios.xlsx")

    print(f"## Configuração: {cfg['label']}")
    print(f"## {args.n_rotinas} rotinas, seeds {args.seed}..{args.seed + args.n_rotinas - 1}")

    for i in range(args.n_rotinas):
        random.seed(args.seed + i)
        sessoes = gerar_multiplos_treinos(
            banco, configs_treinos, relaxar_familia=True,
        )
        print(f"\n### Rotina {i+1} (seed={args.seed+i})")
        for sessao, label in zip(sessoes, labels):
            print()
            print(fmt_treino(sessao, label))


if __name__ == "__main__":
    main()
