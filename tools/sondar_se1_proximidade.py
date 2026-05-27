"""Sondagem S-E1 proximidade biomecânica cross-treino (Achado 2 da auditoria 2026-05-26).

Mede repetição de equipamento / pegada / plano_corporal entre slots de
treinos diferentes na MESMA subregião. Setup canônico: Full Body 2T com
`aderencia=alta` (peso_aderencia=2) — exato setup da auditoria.

Métricas por config:
  - pct_supinos_halteres_repetido: peito 1+1 cross-treino, ambos com
    equipamento_grupo=halter. Métrica PRIMÁRIA do caso clínico do Achado 2.
  - pct_desenv_halteres_repetido: ombro 1+1 cross-treino, ambos halter.
    Métrica PRIMÁRIA análoga.
  - pct_pegada_repetida_cross_treino: % rotinas com algum par cross-treino
    mesma-sub com pegada igual (qualquer subregião).
  - pct_plano_repetido_cross_treino: idem pra plano_corporal.
  - pct_eq_repetido_cross_treino: idem pra equipamento_grupo.
  - tempo_p50_s / tempo_max_s: sanity check.

Uso:
    python tools/sondar_se1_proximidade.py                                 # baseline (peso=0)
    python tools/sondar_se1_proximidade.py --peso-pegada 10 --peso-plano 10 --peso-eq 2
    python tools/sondar_se1_proximidade.py --n 10 --out docs/refatoracao/logs/se1_proximidade_pre.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gerador_csp import (  # noqa: E402
    ConfigVariedade,
    carregar_banco_ativo,
    gerar_rotina_csp,
)


# Setup canônico do achado: Full Body 2T região, aderencia=alta.
_DEMANDAS_FULL_BODY_2T = [
    [("regiao", "upper", 3), ("regiao", "lower", 3), ("regiao", "core", 2)],
    [("regiao", "upper", 3), ("regiao", "lower", 3), ("regiao", "core", 2)],
]


def _rodar_rotina(banco, peso_pegada, peso_plano, peso_eq, seed):
    kwargs = dict(
        nivel_aluno=3,
        seed=seed,
        variedade=ConfigVariedade(),
        peso_aderencia=2,           # aderencia=alta (setup auditoria Achado 2)
        peso_evitar_agonistas=10,
        tamanho_preferido=2,
        peso_tamanho_bloco=5,
        peso_sa1=12,
        peso_sa1_repet=10,
        peso_sb5=4,                 # default ON em produção
        peso_sr1=4,                 # default ON em produção
        relaxar_familia=True,
    )
    if peso_pegada > 0:
        kwargs["peso_se1_pegada"] = peso_pegada
    if peso_plano > 0:
        kwargs["peso_se1_plano"] = peso_plano
    if peso_eq > 0:
        kwargs["peso_se1_eq"] = peso_eq
    t0 = time.perf_counter()
    r = gerar_rotina_csp(_DEMANDAS_FULL_BODY_2T, banco, **kwargs)
    elapsed = time.perf_counter() - t0
    return r, elapsed


def _exs_por_treino(rotina):
    """Lista plana de Exercicios em cada treino (ordem dos blocos preservada)."""
    out = []
    for t in rotina.get("treinos", []):
        exs = []
        for bloco in t.get("blocos", []):
            for ex in bloco:
                exs.append(ex)
        out.append(exs)
    return out


def _analisar_rotina(rotina) -> dict:
    """Calcula métricas S-E1 numa rotina."""
    exs_por_t = _exs_por_treino(rotina)
    if len(exs_por_t) < 2:
        return {
            "supinos_halteres_repetido": False,
            "desenv_halteres_repetido": False,
            "pegada_repetida": False,
            "plano_repetido": False,
            "eq_repetido": False,
            "exemplos_pares_repetidos": [],
        }

    pegada_repetida = False
    plano_repetido = False
    eq_repetido = False
    exemplos: list[str] = []
    # Specific clínicos
    peitos_halter: list[list[object]] = [[] for _ in exs_por_t]  # peito × halter por treino
    ombros_halter: list[list[object]] = [[] for _ in exs_por_t]  # ombro × halter por treino

    # Coleta peito/ombro halter por treino
    for t_idx, exs in enumerate(exs_por_t):
        for ex in exs:
            if ex.subregiao == "peito" and ex.equipamento_grupo == "halter":
                peitos_halter[t_idx].append(ex)
            if ex.subregiao == "ombro" and ex.equipamento_grupo == "halter":
                ombros_halter[t_idx].append(ex)

    supinos_halteres_repetido = (
        any(peitos_halter[t1] and peitos_halter[t2]
            for t1, t2 in combinations(range(len(exs_por_t)), 2))
    )
    desenv_halteres_repetido = (
        any(ombros_halter[t1] and ombros_halter[t2]
            for t1, t2 in combinations(range(len(exs_por_t)), 2))
    )

    # Pares cross-treino mesma-sub
    for t1, t2 in combinations(range(len(exs_por_t)), 2):
        for e1 in exs_por_t[t1]:
            for e2 in exs_por_t[t2]:
                if e1.subregiao != e2.subregiao:
                    continue
                same_pegada = bool(e1.pegada) and e1.pegada == e2.pegada
                same_plano = (
                    bool(e1.plano_corporal)
                    and e1.plano_corporal == e2.plano_corporal
                )
                same_eq = (
                    bool(e1.equipamento_grupo)
                    and e1.equipamento_grupo == e2.equipamento_grupo
                )
                if same_pegada:
                    pegada_repetida = True
                if same_plano:
                    plano_repetido = True
                if same_eq:
                    eq_repetido = True
                if (same_pegada or same_plano or same_eq) and len(exemplos) < 3:
                    flags = []
                    if same_pegada:
                        flags.append(f"pegada={e1.pegada}")
                    if same_plano:
                        flags.append(f"plano={e1.plano_corporal}")
                    if same_eq:
                        flags.append(f"eq={e1.equipamento_grupo}")
                    exemplos.append(
                        f"T{t1 + 1}:{e1.nome} <-> T{t2 + 1}:{e2.nome} [{e1.subregiao}] "
                        f"({', '.join(flags)})"
                    )

    return {
        "supinos_halteres_repetido": supinos_halteres_repetido,
        "desenv_halteres_repetido": desenv_halteres_repetido,
        "pegada_repetida": pegada_repetida,
        "plano_repetido": plano_repetido,
        "eq_repetido": eq_repetido,
        "exemplos_pares_repetidos": exemplos,
    }


def sondar(n_seeds: int, peso_pegada: int, peso_plano: int, peso_eq: int) -> dict:
    banco = carregar_banco_ativo()
    n_sup_halter = 0
    n_des_halter = 0
    n_pegada_rep = 0
    n_plano_rep = 0
    n_eq_rep = 0
    tempos: list[float] = []
    inviaveis = 0
    exemplos_rotinas: list[dict] = []
    for seed in range(n_seeds):
        r, elapsed = _rodar_rotina(banco, peso_pegada, peso_plano, peso_eq, seed)
        tempos.append(elapsed)
        if not r.get("viavel"):
            inviaveis += 1
            continue
        stats = _analisar_rotina(r)
        if stats["supinos_halteres_repetido"]:
            n_sup_halter += 1
        if stats["desenv_halteres_repetido"]:
            n_des_halter += 1
        if stats["pegada_repetida"]:
            n_pegada_rep += 1
        if stats["plano_repetido"]:
            n_plano_rep += 1
        if stats["eq_repetido"]:
            n_eq_rep += 1
        if len(exemplos_rotinas) < 3 and stats["exemplos_pares_repetidos"]:
            exemplos_rotinas.append({
                "seed": seed,
                "pares": stats["exemplos_pares_repetidos"],
            })
    n_validos = n_seeds - inviaveis
    return {
        "Full Body 2T (regiao, aderencia=alta)": {
            "n_seeds": n_seeds,
            "inviaveis": inviaveis,
            "n_supinos_halteres_repetido": n_sup_halter,
            "n_desenv_halteres_repetido": n_des_halter,
            "n_pegada_repetida": n_pegada_rep,
            "n_plano_repetido": n_plano_rep,
            "n_eq_repetido": n_eq_rep,
            "pct_supinos_halteres_repetido": (
                100.0 * n_sup_halter / n_validos if n_validos else 0.0
            ),
            "pct_desenv_halteres_repetido": (
                100.0 * n_des_halter / n_validos if n_validos else 0.0
            ),
            "pct_pegada_repetida_cross_treino": (
                100.0 * n_pegada_rep / n_validos if n_validos else 0.0
            ),
            "pct_plano_repetido_cross_treino": (
                100.0 * n_plano_rep / n_validos if n_validos else 0.0
            ),
            "pct_eq_repetido_cross_treino": (
                100.0 * n_eq_rep / n_validos if n_validos else 0.0
            ),
            "tempo_p50_s": statistics.median(tempos) if tempos else 0.0,
            "tempo_max_s": max(tempos) if tempos else 0.0,
            "exemplos_rotinas": exemplos_rotinas,
        }
    }


def imprimir_relatorio(snapshot, peso_pegada, peso_plano, peso_eq, n_seeds):
    print(
        f"\n=== Sondagem S-E1 (peso_pegada={peso_pegada}, peso_plano={peso_plano}, "
        f"peso_eq={peso_eq}, N={n_seeds}) ===\n"
    )
    for nome, dados in snapshot.items():
        print(f"[{nome}]")
        print(f"  pct_supinos_halteres_repetido    : {dados['pct_supinos_halteres_repetido']:5.1f}% (PRIMÁRIA)")
        print(f"  pct_desenv_halteres_repetido     : {dados['pct_desenv_halteres_repetido']:5.1f}% (PRIMÁRIA)")
        print(f"  pct_pegada_repetida_cross_treino : {dados['pct_pegada_repetida_cross_treino']:5.1f}%")
        print(f"  pct_plano_repetido_cross_treino  : {dados['pct_plano_repetido_cross_treino']:5.1f}%")
        print(f"  pct_eq_repetido_cross_treino     : {dados['pct_eq_repetido_cross_treino']:5.1f}%")
        print(f"  tempo_p50_s / tempo_max_s        : {dados['tempo_p50_s']:.2f}s / {dados['tempo_max_s']:.2f}s")
        print(f"  inviaveis                        : {dados['inviaveis']}/{dados['n_seeds']}")
        if dados["exemplos_rotinas"]:
            print("  Exemplos de pares repetidos (até 3 rotinas, até 3 pares cada):")
            for ex in dados["exemplos_rotinas"]:
                print(f"    seed={ex['seed']}:")
                for par in ex["pares"]:
                    print(f"      {par}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=10, help="N seeds (default 10)")
    p.add_argument("--peso-pegada", type=int, default=0)
    p.add_argument("--peso-plano", type=int, default=0)
    p.add_argument("--peso-eq", type=int, default=0)
    p.add_argument("--out", type=str, default=None, help="Path opcional pra snapshot json")
    args = p.parse_args()

    snapshot = sondar(args.n, args.peso_pegada, args.peso_plano, args.peso_eq)
    imprimir_relatorio(snapshot, args.peso_pegada, args.peso_plano, args.peso_eq, args.n)

    if args.out:
        out_path = ROOT / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({
            "n_seeds": args.n,
            "peso_se1_pegada": args.peso_pegada,
            "peso_se1_plano": args.peso_plano,
            "peso_se1_eq": args.peso_eq,
            "configs": snapshot,
        }, indent=2, ensure_ascii=False))
        print(f"\nSnapshot persistido em {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
