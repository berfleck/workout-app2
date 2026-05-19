"""Analise estatistica de aparicao das remadas landmine.

Setup: rotina com 1 treino = upper(4) + lower(2). Roda N iteracoes,
mede frequencia de aparicao de "Remada LM Neutra" e "Remada LM Aberta".

Uso:
    python tools/analisar_remada_lm.py [--n-iter 2000] [--seed 0]
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gerador_treino import carregar_banco, gerar_multiplos_treinos

XLSX_PATH = "banco_exercicios.xlsx"
LM_NAMES = {"Remada LM Neutra", "Remada LM Aberta"}


def _exercicios_da_sessao(sessao):
    for bloco in sessao.blocos:
        for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
            if ex is not None:
                yield ex


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval para proporcao k/n."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / denom
    margem = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, centro - margem), min(1.0, centro + margem))


def analisar(n_iter: int, seed_base: int = 0, relaxar: bool = True):
    banco = carregar_banco(XLSX_PATH)

    configs = [
        {"demandas": [("regiao", "upper", 4), ("regiao", "lower", 2)]},
    ]

    # Contagens
    n_rotinas_com_lm = 0          # rotinas que tem >=1 LM
    n_rotinas_com_lm_neutra = 0
    n_rotinas_com_lm_aberta = 0
    n_rotinas_com_qualquer_remada = 0
    n_rotinas_com_curvada = 0     # rotina com alguma da familia curvada

    freq_remadas_por_nome: Counter = Counter()
    freq_familia_curvada: Counter = Counter()    # qual ex da fam. curvada apareceu
    total_slots_remadas = 0
    total_slots = 0
    n_sessoes_incompletas = 0
    n_rotinas_com_aviso_incompleta = 0
    n_rotinas_com_relaxados = 0
    n_rotinas_com_lm_relaxado = 0

    # Lookup pra var_de
    info = {e.nome: e for e in banco}

    for i in range(n_iter):
        random.seed(seed_base + i)
        sessoes = gerar_multiplos_treinos(banco, configs, relaxar_familia=relaxar)
        assert len(sessoes) == 1, f"iter {i}: esperava 1 sessao, vi {len(sessoes)}"
        sessao = sessoes[0]

        exs = list(_exercicios_da_sessao(sessao))
        total_slots += len(exs)
        if len(exs) < 6:
            n_sessoes_incompletas += 1

        nomes_remadas = [e.nome for e in exs if e.padrao == "remadas"]
        if nomes_remadas:
            n_rotinas_com_qualquer_remada += 1
            total_slots_remadas += len(nomes_remadas)
            for n in nomes_remadas:
                freq_remadas_por_nome[n] += 1
                if info[n].variacao_de == "curvada":
                    freq_familia_curvada[n] += 1

        tem_curvada = any(info[n].variacao_de == "curvada" for n in nomes_remadas)
        if tem_curvada:
            n_rotinas_com_curvada += 1

        tem_lm = any(n in LM_NAMES for n in nomes_remadas)
        if tem_lm:
            n_rotinas_com_lm += 1
        if "Remada LM Neutra" in nomes_remadas:
            n_rotinas_com_lm_neutra += 1
        if "Remada LM Aberta" in nomes_remadas:
            n_rotinas_com_lm_aberta += 1

        if any(a.get("tipo") == "incompleta" for a in sessao.avisos):
            n_rotinas_com_aviso_incompleta += 1
        if sessao.relaxados:
            n_rotinas_com_relaxados += 1
            if any(r in LM_NAMES for r in sessao.relaxados):
                n_rotinas_com_lm_relaxado += 1

    return {
        "n_iter": n_iter,
        "n_rotinas_com_lm": n_rotinas_com_lm,
        "n_rotinas_com_lm_neutra": n_rotinas_com_lm_neutra,
        "n_rotinas_com_lm_aberta": n_rotinas_com_lm_aberta,
        "n_rotinas_com_qualquer_remada": n_rotinas_com_qualquer_remada,
        "n_rotinas_com_curvada": n_rotinas_com_curvada,
        "freq_remadas_por_nome": freq_remadas_por_nome,
        "freq_familia_curvada": freq_familia_curvada,
        "total_slots_remadas": total_slots_remadas,
        "total_slots": total_slots,
        "n_sessoes_incompletas": n_sessoes_incompletas,
        "n_rotinas_com_aviso_incompleta": n_rotinas_com_aviso_incompleta,
        "n_rotinas_com_relaxados": n_rotinas_com_relaxados,
        "n_rotinas_com_lm_relaxado": n_rotinas_com_lm_relaxado,
    }


def imprimir_relatorio(res: dict) -> None:
    n = res["n_iter"]

    def pct(k: int, total: int = n) -> str:
        if total == 0:
            return "0.00% (n=0)"
        p = 100 * k / total
        lo, hi = wilson_ci(k, total)
        return f"{p:6.2f}%  [{100*lo:5.2f}%-{100*hi:5.2f}%]  ({k}/{total})"

    print()
    print("=" * 78)
    print(f"ANALISE: Remadas Landmine em rotina upper(4) + lower(2) x 1T")
    print(f"N = {n} iteracoes (relaxar_familia=True, seeds 0..{n-1})")
    print("=" * 78)

    print()
    print("--- Pergunta central: as LM aparecem? ---")
    print(f"Rotinas com ALGUMA remada LM      : {pct(res['n_rotinas_com_lm'])}")
    print(f"  com 'Remada LM Neutra'          : {pct(res['n_rotinas_com_lm_neutra'])}")
    print(f"  com 'Remada LM Aberta'          : {pct(res['n_rotinas_com_lm_aberta'])}")

    print()
    print("--- Contexto (pra interpretar a magnitude) ---")
    print(f"Rotinas com qualquer 'remadas'    : {pct(res['n_rotinas_com_qualquer_remada'])}")
    print(f"Rotinas com familia 'curvada'     : {pct(res['n_rotinas_com_curvada'])}")

    n_rem = res["n_rotinas_com_qualquer_remada"]
    n_curv = res["n_rotinas_com_curvada"]
    if n_rem > 0:
        print()
        print(f"--- Condicional: dado que ha remada (n={n_rem}) ---")
        k_lm = res["n_rotinas_com_lm"]
        print(f"  P(LM | tem remada)              : {pct(k_lm, n_rem)}")
    if n_curv > 0:
        k_lm = res["n_rotinas_com_lm"]
        print(f"  P(LM | tem curvada) (n={n_curv}): {pct(k_lm, n_curv)}")

    print()
    print("--- Distribuicao por nome (entre remadas escolhidas) ---")
    total_r = res["total_slots_remadas"]
    print(f"  Total de slots remadas        : {total_r}")
    for nome, ct in res["freq_remadas_por_nome"].most_common():
        marker = " *** LM ***" if nome in LM_NAMES else ""
        print(f"  {nome:30s} {ct:5d}  {100*ct/total_r:5.2f}%{marker}")

    print()
    print("--- Distribuicao dentro da familia 'curvada' (5 ex) ---")
    total_c = sum(res["freq_familia_curvada"].values())
    print(f"  Total de slots 'curvada'      : {total_c}")
    if total_c > 0:
        for nome, ct in res["freq_familia_curvada"].most_common():
            marker = " *** LM ***" if nome in LM_NAMES else ""
            print(f"  {nome:30s} {ct:5d}  {100*ct/total_c:5.2f}%{marker}")

    print()
    print("--- Baselines teoricos pra comparar ---")
    print(f"  Uniforme por nome entre 14 remadas (1 LM)  : {100*1/14:5.2f}%")
    print(f"  Uniforme por nome (2 LM = qualquer LM)     : {100*2/14:5.2f}%")
    print(f"  Uniforme por familia (1/6) x uniforme LM   : {100*(1/6)*(2/5):5.2f}%")

    print()
    print("--- Sanity ---")
    print(f"  Sessoes incompletas (<6 slots): {res['n_sessoes_incompletas']}/{n}")
    print(f"  Aviso 'incompleta'            : {res['n_rotinas_com_aviso_incompleta']}/{n}")
    print(f"  Rotinas com relaxados         : {res['n_rotinas_com_relaxados']}/{n}")
    print(f"  Relaxados que cairam em LM    : {res['n_rotinas_com_lm_relaxado']}/{n}")
    total_esperado = 6 * n
    print(f"  Slots totais: {res['total_slots']}/{total_esperado}  "
          f"({100*res['total_slots']/total_esperado:5.2f}%)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-iter", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sem-relax", action="store_true",
                    help="rodar com relaxar_familia=False")
    args = ap.parse_args()

    res = analisar(args.n_iter, args.seed, relaxar=not args.sem_relax)
    imprimir_relatorio(res)


if __name__ == "__main__":
    main()
