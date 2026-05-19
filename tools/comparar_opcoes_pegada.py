"""Compara 4 cenarios: baseline + 3 opcoes de tratamento de pegada.

Setup: rotina upper(4) + lower(2) x 1T, N=2000 iters (seeds 0..1999).
Mede frequencia de TODAS as remadas e TODAS as puxadas em cada cenario.

Cenarios:
  BASELINE — banco atual, _score_intra match-exato (estado pos-fix LM bilateral)
  OPCAO A  — re-tag XLSX: pegada=aberta vira pegada=pronada (em memoria, nao toca arquivo)
  OPCAO B  — matriz: aberta<->pronada = -25 (half), match exato = -50
  OPCAO C  — split em 2 eixos: rotacao + largura, scoring acumula em cada eixo
"""
from __future__ import annotations

import math
import random
import shutil
import sys
from collections import Counter
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gerador_treino as gt
from gerador_treino import carregar_banco, gerar_multiplos_treinos

XLSX_PATH = "banco_exercicios.xlsx"
N_ITER = 2000
LM_NAMES = {"Remada LM Neutra", "Remada LM Aberta"}

CONFIGS = [{"demandas": [("regiao", "upper", 4), ("regiao", "lower", 2)]}]


def _exercicios(sessao):
    for b in sessao.blocos:
        for e in (b.ex1, b.ex2, b.ex3):
            if e is not None:
                yield e


def rodar_simulacao(banco, label, n_iter=N_ITER, seed_base=0):
    """Roda n_iter e retorna Counters de remadas + puxadas + meta."""
    freq_remada: Counter = Counter()
    freq_puxada: Counter = Counter()
    n_lm = 0
    for i in range(n_iter):
        random.seed(seed_base + i)
        sessoes = gerar_multiplos_treinos(banco, CONFIGS, relaxar_familia=True)
        nomes_lm_neste = False
        for s in sessoes:
            for e in _exercicios(s):
                if e.padrao == "remadas":
                    freq_remada[e.nome] += 1
                    if e.nome in LM_NAMES:
                        nomes_lm_neste = True
                elif e.padrao == "puxadas":
                    freq_puxada[e.nome] += 1
        if nomes_lm_neste:
            n_lm += 1
    return {"label": label, "remadas": freq_remada, "puxadas": freq_puxada,
            "n_lm": n_lm, "n_iter": n_iter}


# ---------------------------------------------------------------------------
# OPCAO A — re-tag aberta -> pronada in-memory (sem tocar XLSX)
# ---------------------------------------------------------------------------

def banco_opcao_a(banco):
    """Copia do banco com pegada=aberta convertido pra pegada=pronada."""
    novo = []
    for e in banco:
        if e.pegada == "aberta":
            novo.append(replace(e, pegada="pronada"))
        else:
            novo.append(e)
    return novo


# ---------------------------------------------------------------------------
# OPCAO B — monkey-patch _score_intra com matriz pegada
# ---------------------------------------------------------------------------

_PARTIAL_PEGADA = {("pronada", "aberta"), ("aberta", "pronada")}

def _score_intra_matriz(cand, alocados, pesos_config):
    """Versao B: aberta<->pronada conta como -25 (metade), match exato = -50."""
    total = 0.0
    sub_cand = cand.subregiao
    for outro in alocados:
        if sub_cand != outro.subregiao:
            continue
        if cand.pegada and outro.pegada:
            p_full = pesos_config.pegada.peso_intra(sub_cand)
            if cand.pegada == outro.pegada:
                total += p_full
            elif (cand.pegada, outro.pegada) in _PARTIAL_PEGADA:
                total += p_full * 0.5
        if (cand.plano_corporal and outro.plano_corporal
                and cand.plano_corporal == outro.plano_corporal):
            total += pesos_config.plano_corporal.peso_intra(sub_cand)
        if (cand.equipamento_grupo and outro.equipamento_grupo
                and cand.equipamento_grupo == outro.equipamento_grupo):
            total += pesos_config.equipamento_grupo.peso_intra(sub_cand)
    return total


# ---------------------------------------------------------------------------
# OPCAO C — split em rotacao + largura via campos derivados + scoring 2-eixos
# ---------------------------------------------------------------------------

# Mapeamento pegada -> (rotacao, largura)
_PEGADA_SPLIT = {
    "aberta":   ("pronada", "aberta"),
    "pronada":  ("pronada", "media"),
    "neutra":   ("neutra",  "media"),
    "supinada": ("supinada","media"),
}

def _split_pegada(p):
    return _PEGADA_SPLIT.get(p, (None, None))


def _score_intra_2eixos(cand, alocados, pesos_config):
    """Versao C: rotacao e largura como 2 sub-dimensoes da pegada.

    Match em rotacao: meio peso (-25). Match em ambas: peso cheio (-50).
    Match so em largura sem rotacao: nao ocorre na pratica (aberta sempre pronada).
    """
    total = 0.0
    sub_cand = cand.subregiao
    rot_c, larg_c = _split_pegada(cand.pegada)
    for outro in alocados:
        if sub_cand != outro.subregiao:
            continue
        rot_o, larg_o = _split_pegada(outro.pegada)
        if rot_c and rot_o:
            p_full = pesos_config.pegada.peso_intra(sub_cand)
            rot_match = (rot_c == rot_o)
            larg_match = (larg_c == larg_o and larg_c is not None)
            if rot_match and larg_match:
                total += p_full          # exato: -50
            elif rot_match:
                total += p_full * 0.5    # so rotacao: -25
            elif larg_match:
                total += p_full * 0.25   # so largura (raro): -12.5
        if (cand.plano_corporal and outro.plano_corporal
                and cand.plano_corporal == outro.plano_corporal):
            total += pesos_config.plano_corporal.peso_intra(sub_cand)
        if (cand.equipamento_grupo and outro.equipamento_grupo
                and cand.equipamento_grupo == outro.equipamento_grupo):
            total += pesos_config.equipamento_grupo.peso_intra(sub_cand)
    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    banco = carregar_banco(XLSX_PATH)

    # Salvar referencia ao original
    orig_score_intra = gt._score_intra

    print(f"Rodando N={N_ITER} por cenario...")
    print()

    # BASELINE
    print("[1/4] BASELINE...")
    res_baseline = rodar_simulacao(banco, "BASELINE")

    # OPCAO A
    print("[2/4] OPCAO A (re-tag aberta->pronada)...")
    banco_a = banco_opcao_a(banco)
    res_a = rodar_simulacao(banco_a, "A: aberta->pronada")

    # OPCAO B
    print("[3/4] OPCAO B (matriz aberta<->pronada=-25)...")
    gt._score_intra = _score_intra_matriz
    res_b = rodar_simulacao(banco, "B: matriz 4x4")
    gt._score_intra = orig_score_intra

    # OPCAO C
    print("[4/4] OPCAO C (split rotacao + largura)...")
    gt._score_intra = _score_intra_2eixos
    res_c = rodar_simulacao(banco, "C: 2 eixos")
    gt._score_intra = orig_score_intra

    todos = [res_baseline, res_a, res_b, res_c]

    # Lista canonica de remadas + puxadas (pra alinhar a tabela)
    todas_remadas = sorted({n for r in todos for n in r["remadas"]},
                            key=lambda n: -res_baseline["remadas"].get(n, 0))
    todas_puxadas = sorted({n for r in todos for n in r["puxadas"]},
                            key=lambda n: -res_baseline["puxadas"].get(n, 0))

    print()
    print("=" * 90)
    print(f"COMPARATIVO N={N_ITER} (upper(4)+lower(2) x 1T)")
    print("=" * 90)

    # Top-line summary
    print()
    print("--- Rotinas com qualquer LM (% de N) ---")
    for r in todos:
        pct = 100 * r["n_lm"] / r["n_iter"]
        print(f"  {r['label']:25s}  {r['n_lm']:4d}/{r['n_iter']}  =  {pct:6.2f}%")

    # Remadas
    print()
    print("--- REMADAS: contagem por nome (slots totais) ---")
    header = f"  {'Exercicio':28s} | " + " | ".join(f"{r['label'][:13]:>13s}" for r in todos)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for nome in todas_remadas:
        marker = " ⭐" if nome in LM_NAMES else "  "
        row = f"  {marker}{nome:26s} | " + " | ".join(
            f"{r['remadas'].get(nome, 0):13d}" for r in todos)
        print(row)

    # Familia curvada — % dentro da familia
    print()
    print("--- Familia curvada — % dentro da familia ---")
    curvada_names = ["Remada Curvada Barra", "Remada Curvada Smith",
                     "Remada Curvada Halteres", "Remada LM Neutra",
                     "Remada LM Aberta"]
    for nome in curvada_names:
        marker = " ⭐" if nome in LM_NAMES else "  "
        pcts = []
        for r in todos:
            tot_curv = sum(r["remadas"].get(n, 0) for n in curvada_names)
            ct = r["remadas"].get(nome, 0)
            p = 100 * ct / tot_curv if tot_curv else 0
            pcts.append(f"{p:12.2f}%")
        row = f"  {marker}{nome:26s} | " + " | ".join(f"{p:>13s}" for p in pcts)
        print(row)

    # Puxadas
    print()
    print("--- PUXADAS: contagem por nome (slots totais) ---")
    header = f"  {'Exercicio':28s} | " + " | ".join(f"{r['label'][:13]:>13s}" for r in todos)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for nome in todas_puxadas:
        row = f"   {nome:27s} | " + " | ".join(
            f"{r['puxadas'].get(nome, 0):13d}" for r in todos)
        print(row)

    # Sanity totais
    print()
    print("--- Sanity: total slots por categoria ---")
    for r in todos:
        tot_r = sum(r["remadas"].values())
        tot_p = sum(r["puxadas"].values())
        print(f"  {r['label']:25s}  remadas={tot_r:4d}  puxadas={tot_p:4d}  total={tot_r+tot_p}")


if __name__ == "__main__":
    main()
