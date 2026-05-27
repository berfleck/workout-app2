"""Sondagem S-T4 (proximidade biomecânica INTRA-treino mesma-sub).

Roda N rotinas em 2 setups e mede % de pares INTRA-treino mesma-sub com
pegada/plano/eq repetidos. Usa setup canônico do handoff (`costas(2) ×
1T`) + setup Jose Silva (mistura INTRA e INTER pra confirmar coexistência
com S-E1).

Saída: JSON em docs/refatoracao/logs/st4_variedade_{PRE|POS}.json,
controlado por env STAGE=PRE ou STAGE=POS (default PRE).

Pesos default da frente (§3.3 do handoff): peso_st4_pegada=12,
peso_st4_plano=12, peso_st4_eq=3. PRE roda com pesos=0 (baseline);
POS roda com pesos cravados.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gerador_csp import gerar_rotina_csp, ConfigVariedade  # noqa: E402
from gerador_treino import carregar_banco  # noqa: E402


STAGE = os.environ.get("STAGE", "PRE").upper()
assert STAGE in ("PRE", "POS"), f"STAGE inválido: {STAGE}"

N_ROTINAS = 30
NIVEL_ALUNO = 2

SETUPS = {
    "costas_2x1T": [
        [("subregiao", "costas", 2)],
    ],
    "jose_silva_T1T2": [
        [
            ("subregiao", "bracos", 1),
            ("subregiao", "peito", 2),
            ("subregiao", "ombro", 1),
            ("subregiao", "perna_posterior", 2),
            ("subregiao", "core_dinamico", 1),
        ],
        [
            ("subregiao", "bracos", 1),
            ("subregiao", "costas", 3),
            ("subregiao", "perna_anterior", 2),
            ("subregiao", "core_isometrico", 1),
        ],
    ],
}

PESOS_BASE = dict(
    peso_aderencia=0,
    peso_evitar_agonistas=10,
    peso_tamanho_bloco=5,
    tamanho_preferido=2,
    peso_sa1=12,
    peso_sa1_repet=10,
    peso_sb5=4,
    peso_sr1=4,
    peso_se1_pegada=10,
    peso_se1_plano=10,
    peso_se1_eq=2,
)


def _dim(ex, attr):
    v = getattr(ex, attr, None)
    if v is None:
        return None
    s = str(v).strip().lower()
    if not s or s in ("nan", "none"):
        return None
    return s


def _pares_intra(blocos):
    slots = [ex for b in blocos for ex in b]
    por_sub = defaultdict(list)
    for ex in slots:
        por_sub[ex.subregiao].append(ex)
    pares = []
    for sub, ex_list in por_sub.items():
        if len(ex_list) < 2:
            continue
        for a, b in combinations(ex_list, 2):
            pares.append((sub, a, b))
    return pares


def rodar_setup(banco, nome, demandas_por_treino, pesos):
    t_inicio = time.time()
    contagem = defaultdict(int)
    pares_por_sub = defaultdict(int)
    repet_por_sub_dim = defaultdict(lambda: defaultdict(int))
    casos_pegada = []
    casos_plano = []
    tempos = []
    for k in range(N_ROTINAS):
        t0 = time.time()
        res = gerar_rotina_csp(
            demandas_por_treino, banco, nivel_aluno=NIVEL_ALUNO,
            seed=k, variedade=ConfigVariedade(), **pesos,
        )
        tempos.append(time.time() - t0)
        if res.get("status") not in ("OPTIMAL", "FEASIBLE"):
            continue
        for t_idx, treino in enumerate(res["treinos"]):
            for sub, a, b in _pares_intra(treino["blocos"]):
                contagem["total_pares"] += 1
                pares_por_sub[sub] += 1
                peg_a = _dim(a, "pegada")
                pla_a = _dim(a, "plano_corporal")
                eq_a = _dim(a, "equipamento_grupo")
                peg_b = _dim(b, "pegada")
                pla_b = _dim(b, "plano_corporal")
                eq_b = _dim(b, "equipamento_grupo")
                if peg_a is not None and peg_a == peg_b:
                    contagem["pegada_repetida"] += 1
                    repet_por_sub_dim[sub]["pegada"] += 1
                    casos_pegada.append({
                        "rotina": k, "treino": t_idx + 1, "sub": sub,
                        "ex1": a.nome, "ex2": b.nome, "pegada": peg_a,
                    })
                if pla_a is not None and pla_a == pla_b:
                    contagem["plano_repetido"] += 1
                    repet_por_sub_dim[sub]["plano"] += 1
                    casos_plano.append({
                        "rotina": k, "treino": t_idx + 1, "sub": sub,
                        "ex1": a.nome, "ex2": b.nome, "plano": pla_a,
                    })
                if eq_a is not None and eq_a == eq_b:
                    contagem["equipamento_repetido"] += 1
                    repet_por_sub_dim[sub]["equipamento"] += 1
    return {
        "setup": nome,
        "n_rotinas": N_ROTINAS,
        "contagem": dict(contagem),
        "pares_por_sub": dict(pares_por_sub),
        "repet_por_sub_dim": {sub: dict(d) for sub, d in repet_por_sub_dim.items()},
        "tempo_p50_s": median(tempos),
        "tempo_total_s": time.time() - t_inicio,
        "casos_pegada": casos_pegada,
        "casos_plano": casos_plano,
    }


def main():
    banco = carregar_banco(str(ROOT / "banco_exercicios.xlsx"))
    banco = [e for e in banco if getattr(e, "ativo", True) is not False]

    # PRE: pesos S-T4 ausentes (motor antes da frente não conhece kwargs).
    # POS: pesos cravados (motor pós-implementação aceita kwargs novos).
    if STAGE == "PRE":
        pesos = dict(PESOS_BASE)
    else:
        pesos = dict(PESOS_BASE,
                     peso_st4_pegada=12, peso_st4_plano=12, peso_st4_eq=3)

    print(f"[STAGE={STAGE}] banco={len(banco)} ativos, N={N_ROTINAS}")
    print(f"Pesos S-T4: peg={pesos.get('peso_st4_pegada', 0)} pla={pesos.get('peso_st4_plano', 0)} eq={pesos.get('peso_st4_eq', 0)}")
    print()

    resultados = {}
    for nome, demandas in SETUPS.items():
        print(f"--- Setup {nome} ---")
        r = rodar_setup(banco, nome, demandas, pesos)
        resultados[nome] = r
        c = r["contagem"]
        tot = c.get("total_pares", 0) or 1
        pct = lambda n: f"{100*n/tot:.1f}%"
        print(f"  pares INTRA-sub: {c.get('total_pares', 0)}")
        print(f"  pegada repetida: {c.get('pegada_repetida', 0):4d}  ({pct(c.get('pegada_repetida', 0))})")
        print(f"  plano repetido:  {c.get('plano_repetido', 0):4d}  ({pct(c.get('plano_repetido', 0))})")
        print(f"  eq repetido:     {c.get('equipamento_repetido', 0):4d}  ({pct(c.get('equipamento_repetido', 0))})")
        print(f"  tempo p50: {r['tempo_p50_s']:.2f}s")
        print(f"  por sub:")
        for sub in sorted(r["pares_por_sub"]):
            tot_sub = r["pares_por_sub"][sub]
            d = r["repet_por_sub_dim"].get(sub, {})
            print(f"    {sub:20s}  pares={tot_sub:3d}  peg={d.get('pegada', 0)} ({100*d.get('pegada',0)/tot_sub:.1f}%)  pla={d.get('plano', 0)} ({100*d.get('plano',0)/tot_sub:.1f}%)  eq={d.get('equipamento', 0)} ({100*d.get('equipamento',0)/tot_sub:.1f}%)")
        print()

    out_dir = ROOT / "docs" / "refatoracao" / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"st4_variedade_{STAGE.lower()}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump({
            "stage": STAGE,
            "n_rotinas": N_ROTINAS,
            "nivel_aluno": NIVEL_ALUNO,
            "pesos": pesos,
            "resultados": resultados,
        }, f, indent=2, ensure_ascii=False)
    print(f"Salvo: {out_path}")


if __name__ == "__main__":
    main()
