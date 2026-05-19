"""Gera N rotinas da Variante B do 2x semana (configuracoes_comuns Sec 2.2)
e imprime lado-a-lado pra avaliacao clinica.

T1: peito(2) + ombro(1) + perna_posterior(3) + core(1) + triceps(1) = 8
T2: costas(3) + perna_anterior(3) + core(1) + biceps(1) = 8
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gerador_treino import carregar_banco, gerar_multiplos_treinos

CONFIG_T1 = {"demandas": [
    ("subregiao", "peito", 2),
    ("subregiao", "ombro", 1),
    ("subregiao", "perna_posterior", 3),
    ("subregiao", "core", 1),
    ("padrao",    "triceps", 1),
]}
CONFIG_T2 = {"demandas": [
    ("subregiao", "costas", 3),
    ("subregiao", "perna_anterior", 3),
    ("subregiao", "core", 1),
    ("padrao",    "biceps", 1),
]}


def _exs(sessao):
    for b in sessao.blocos:
        for e in (b.ex1, b.ex2, b.ex3):
            if e is not None:
                yield e


def fmt_treino(sessao, label):
    linhas = [f"  {label}"]
    for i, bloco in enumerate(sessao.blocos):
        prefix = chr(ord("A") + i)
        nomes = []
        for e in (bloco.ex1, bloco.ex2, bloco.ex3):
            if e is None:
                continue
            tag = ""
            if e.purpose in ("compound", "explosive"):
                tag = ""  # composto = default, deixa limpo
            else:
                tag = " (iso)"
            nomes.append(f"{e.nome}{tag}")
        linhas.append(f"    {prefix}: {' + '.join(nomes)}")
    return "\n".join(linhas)


def main(n_rotinas=3, seed_base=42):
    banco = carregar_banco("banco_exercicios.xlsx")
    for i in range(n_rotinas):
        random.seed(seed_base + i)
        sessoes = gerar_multiplos_treinos(
            banco, [CONFIG_T1, CONFIG_T2], relaxar_familia=True,
        )
        print(f"\n=== ROTINA {i+1} (seed={seed_base+i}) ===")
        print(fmt_treino(sessoes[0], "T1 (Empurrar + Posterior)"))
        print(fmt_treino(sessoes[1], "T2 (Puxar + Anterior)"))


if __name__ == "__main__":
    main()
