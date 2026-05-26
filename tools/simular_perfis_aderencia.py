"""Simulacao qualitativa + quantitativa de perfis de aderencia.

Decisao Bernardo (2026-05-26): granularidade SUAVE entre alta/media/baixa
via probabilidade ponderada (softmax da Frente B + penalty da Frente D
combinadas), NAO via decisao hard "peso=0 sorteio, peso>=1 PRI sempre".

Para cada CONFIG candidata, mostra:
  1. Rotina concreta (1 seed) com tier marcado por slot — pra ele julgar
     clinicamente se eh um treino que faria.
  2. Distribuicao de tier agregada (N=20 seeds) — pra estabilizar a
     intuicao numerica.
  3. Variedade (nomes distintos cross-rotina).

Roda:
    python tools/simular_perfis_aderencia.py
    python tools/simular_perfis_aderencia.py --seed 7 --n 20
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gerador_csp import (  # noqa: E402
    ConfigVariedade,
    carregar_banco_ativo,
    gerar_rotina_csp,
)


DEMANDAS = [
    [("regiao", "upper", 3), ("regiao", "lower", 3), ("regiao", "core", 2)],
    [("regiao", "upper", 3), ("regiao", "lower", 3), ("regiao", "core", 2)],
]
NIVEL = 2  # intermediario

# Configs candidatas pra calibracao:
#   (label, peso_aderencia, slack, temperatura)
# peso=0..N: forca de preferencia por PRI no objetivo
# slack: solucoes ate `optimal+slack` enumeradas (alarga conjunto sorteio)
# temperatura: softmax sobre solucoes. T baixo concentra otimo; T alto
#              espalha. Combinado, peso=0+slack alto+T alto = sorteio
#              quase uniforme entre rotinas viaveis (independente de tier).
CONFIGS = [
    # Baseline pra comparar (alta atual rigida):
    ("BASELINE_alta_rigida_p2_s0",   2, 0,   1.0),

    # ALTA: prioriza PRI mas com variedade DENTRO do tier PRI:
    ("alta_variada_p2_s10_T3",       2, 10,  3.0),
    ("alta_variada_p2_s15_T3.5",     2, 15,  3.5),

    # MEDIA: 40-55% PRI com variedade ampla:
    ("media_variada_p1_s15_T3.5",    1, 15,  3.5),
    ("media_variada_p1_s20_T4",      1, 20,  4.0),

    # BAIXA: 20-35% PRI, repertorio aberto:
    ("baixa_aberta_p0_s20_T5",       0, 20,  5.0),
    ("baixa_aberta_p0_s30_T6",       0, 30,  6.0),
]


_TIER_SHORT = {
    "Principal": "PRI",
    "Intermediário": "INT",
    "Acessório": "ACE",
}


def _gerar(banco, seed: int, peso: int, slack: int, T: float):
    variedade = ConfigVariedade(
        slack=slack, temperatura=T, python_seed=seed, max_solucoes=100,
    )
    r = gerar_rotina_csp(
        DEMANDAS, banco, nivel_aluno=NIVEL, seed=seed,
        variedade=variedade,
        peso_aderencia=peso,
        peso_evitar_agonistas=0,
        tamanho_preferido=2,
        peso_tamanho_bloco=5,
        relaxar_familia=True,
    )
    if not r.get("viavel"):
        return []
    out = []
    for treino in r["treinos"]:
        blocos = []
        for grupo in treino["grupos"]:
            blocos.append(list(grupo["exercicios"]))
        out.append(blocos)
    return out


def _formatar_rotina(rotina) -> str:
    if not rotina:
        return "    (INVIAVEL)"
    linhas = []
    for t_idx, treino in enumerate(rotina, start=1):
        linhas.append(f"  Treino {t_idx}:")
        for b_idx, bloco in enumerate(treino):
            label = chr(ord("A") + b_idx)
            for ex in bloco:
                tier = _TIER_SHORT.get(ex.tier, "???")
                linhas.append(
                    f"    {label} [{tier}] {ex.nome}"
                )
    return "\n".join(linhas)


def _dist_tier(rotinas: list) -> dict:
    counter: Counter = Counter()
    nomes: Counter = Counter()
    n_slots = 0
    for r in rotinas:
        for treino in r:
            for bloco in treino:
                for ex in bloco:
                    counter[ex.tier or "(vazio)"] += 1
                    nomes[ex.nome] += 1
                    n_slots += 1
    return {
        "n_slots": n_slots,
        "pct_pri": 100.0 * counter.get("Principal", 0) / max(n_slots, 1),
        "pct_int": 100.0 * counter.get("Intermediário", 0) / max(n_slots, 1),
        "pct_ace": 100.0 * counter.get("Acessório", 0) / max(n_slots, 1),
        "nomes_distintos": len(nomes),
        "top_freq": nomes.most_common(1)[0][1] if nomes else 0,
        "top_nome": nomes.most_common(1)[0][0] if nomes else "",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=str, default="1,7,23",
                        help="Seeds (CSV) para rotinas concretas (default 1,7,23)")
    parser.add_argument("--n", type=int, default=20,
                        help="N seeds para distribuicao agregada (default 20)")
    parser.add_argument("--so-agregado", action="store_true",
                        help="So mostra tabela agregada, pula rotina concreta")
    args = parser.parse_args()

    banco = carregar_banco_ativo()

    # Tabela agregada N=20:
    print(f"\n=== Distribuicao agregada (N={args.n} seeds por config) ===")
    cab = (
        f"{'label':>30} | peso | slk |  T  | {'PRI':>6} | {'INT':>6} | "
        f"{'ACE':>6} | {'nomes':>6} | {'top':>4}"
    )
    print(cab)
    print("-" * len(cab))
    snapshots = {}
    for label, peso, slack, T in CONFIGS:
        rotinas = []
        for seed in range(args.n):
            r = _gerar(banco, seed, peso, slack, T)
            if r:
                rotinas.append(r)
        d = _dist_tier(rotinas)
        snapshots[label] = (peso, slack, T, d)
        print(
            f"{label:>30} | {peso:>4} | {slack:>3} | {T:>3.1f} | "
            f"{d['pct_pri']:>5.1f}% | {d['pct_int']:>5.1f}% | "
            f"{d['pct_ace']:>5.1f}% | {d['nomes_distintos']:>6} | {d['top_freq']:>4}"
        )

    if args.so_agregado:
        return

    # Rotinas concretas (varias seeds):
    seeds = [int(s) for s in args.seeds.split(",")]
    for seed in seeds:
        print(f"\n\n{'#' * 70}")
        print(f"# SEED = {seed}")
        print(f"{'#' * 70}")
        for label, peso, slack, T in CONFIGS:
            rotina = _gerar(banco, seed, peso, slack, T)
            print(f"\n--- {label} (peso={peso}, slack={slack}, T={T}) ---")
            print(_formatar_rotina(rotina))


if __name__ == "__main__":
    main()
