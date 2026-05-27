"""Auditoria S-T4 (proximidade biomecânica INTRA-treino mesma-sub)
usando a config da rotina ativa de Jose Silva (intermediario).

Roda N rotinas via gerar_rotina_csp e mede:
  - pegada repetida intra-treino mesma-sub
  - plano_corporal repetido intra-treino mesma-sub
  - equipamento_grupo repetido intra-treino mesma-sub

Mostra os piores casos (pares concretos) pra Bernardo decidir sobre S-T4.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gerador_csp import gerar_rotina_csp, ConfigVariedade  # noqa: E402
from gerador_treino import carregar_banco  # noqa: E402


# --- Config Jose Silva (inferida do tipo da rotina ativa) ---------------
# T1: triceps(1) + peito(2) + ombro(1) + perna_posterior(2) + core_dinamico(1)
# T2: biceps(1) + costas(3) + perna_anterior(2) + core_isometrico(1)
DEMANDAS_JOSE = [
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
]

NIVEL_ALUNO = 2  # intermediario
N_ROTINAS = 30

# Pesos de produção em main (ver _PESO_* em app_flask.py)
PESOS = dict(
    peso_aderencia=0,        # média/baixa = 0 (Jose é intermediario sem dim)
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


def _dim_value(ex, attr):
    v = getattr(ex, attr, None)
    if v is None:
        return None
    s = str(v).strip().lower()
    if not s or s in ("nan", "none"):
        return None
    return s


def _pares_intra_treino_mesma_sub(treino_blocos):
    """treino_blocos: list[list[Exercicio]]. Retorna lista de (ex1, ex2)
    pares slot-a-slot dentro do mesmo treino, MESMA subregião."""
    slots = [ex for bloco in treino_blocos for ex in bloco]
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


def main():
    banco = carregar_banco(str(ROOT / "banco_exercicios.xlsx"))
    banco = [e for e in banco if getattr(e, "ativo", True)]
    print(f"Banco: {len(banco)} ativos\n")

    casos_pegada = []      # (rotina_idx, treino_idx, sub, ex1, ex2, valor)
    casos_plano = []
    casos_eq = []
    total_pares = 0

    casos_triplo = []      # match nas 3 dims ao mesmo tempo (pior caso)
    casos_duplo = []       # pegada+plano

    for k in range(N_ROTINAS):
        res = gerar_rotina_csp(
            DEMANDAS_JOSE, banco, nivel_aluno=NIVEL_ALUNO,
            seed=k, variedade=ConfigVariedade(), **PESOS,
        )
        if res.get("status") not in ("OPTIMAL", "FEASIBLE"):
            print(f"[rotina {k}] status={res.get('status')} — pulando")
            continue
        for t_idx, treino in enumerate(res["treinos"]):
            blocos = treino["blocos"]
            pares = _pares_intra_treino_mesma_sub(blocos)
            for sub, a, b in pares:
                total_pares += 1
                peg_a = _dim_value(a, "pegada")
                peg_b = _dim_value(b, "pegada")
                pla_a = _dim_value(a, "plano_corporal")
                pla_b = _dim_value(b, "plano_corporal")
                eq_a  = _dim_value(a, "equipamento_grupo")
                eq_b  = _dim_value(b, "equipamento_grupo")

                match_peg = peg_a is not None and peg_a == peg_b
                match_pla = pla_a is not None and pla_a == pla_b
                match_eq  = eq_a  is not None and eq_a  == eq_b

                if match_peg:
                    casos_pegada.append((k, t_idx, sub, a.nome, b.nome, peg_a))
                if match_pla:
                    casos_plano.append((k, t_idx, sub, a.nome, b.nome, pla_a))
                if match_eq:
                    casos_eq.append((k, t_idx, sub, a.nome, b.nome, eq_a))

                if match_peg and match_pla and match_eq:
                    casos_triplo.append((k, t_idx, sub, a.nome, b.nome,
                                         peg_a, pla_a, eq_a))
                elif match_peg and match_pla:
                    casos_duplo.append((k, t_idx, sub, a.nome, b.nome,
                                        peg_a, pla_a))

    print(f"=== Resumo {N_ROTINAS} rotinas, {total_pares} pares intra-treino mesma-sub ===\n")
    pct = lambda n: f"{100*n/total_pares:.1f}%"
    print(f"  Pegada repetida:           {len(casos_pegada):4d}  ({pct(len(casos_pegada))})")
    print(f"  Plano repetido:            {len(casos_plano):4d}  ({pct(len(casos_plano))})")
    print(f"  Equipamento repetido:      {len(casos_eq):4d}  ({pct(len(casos_eq))})")
    print(f"  Pegada+Plano (sub-ótimo):  {len(casos_duplo) + len(casos_triplo):4d}  ({pct(len(casos_duplo) + len(casos_triplo))})")
    print(f"  Triplo match (catastrof.): {len(casos_triplo):4d}  ({pct(len(casos_triplo))})")

    # Detalhar por subregião
    print("\n--- Pegada repetida por subregião ---")
    por_sub_peg = defaultdict(int)
    pares_por_sub = defaultdict(int)
    for (k, ti, sub, a, b, v) in casos_pegada:
        por_sub_peg[sub] += 1
    # Calcular total de pares por sub (precisamos refazer contagem)
    total_pares_por_sub = defaultdict(int)
    for k in range(N_ROTINAS):
        res = gerar_rotina_csp(
            DEMANDAS_JOSE, banco, nivel_aluno=NIVEL_ALUNO,
            seed=k, variedade=ConfigVariedade(), **PESOS,
        )
        if res.get("status") not in ("OPTIMAL", "FEASIBLE"):
            continue
        for treino in res["treinos"]:
            blocos = treino["blocos"]
            pares = _pares_intra_treino_mesma_sub(blocos)
            for sub, _, _ in pares:
                total_pares_por_sub[sub] += 1

    for sub in sorted(total_pares_por_sub):
        n_match = por_sub_peg[sub]
        tot = total_pares_por_sub[sub]
        print(f"  {sub:18s}  pegada: {n_match:3d}/{tot:3d} ({100*n_match/tot:5.1f}%)")

    # Mostrar TOP 15 piores casos (pegada+plano OU triplo)
    print("\n=== TOP 15 piores casos (pegada+plano OU triplo match) ===\n")
    todos_piores = []
    for tup in casos_triplo:
        k, ti, sub, a, b, peg, pla, eq = tup
        todos_piores.append((3, k, ti, sub, a, b, f"peg={peg} pla={pla} eq={eq}"))
    for tup in casos_duplo:
        k, ti, sub, a, b, peg, pla = tup
        todos_piores.append((2, k, ti, sub, a, b, f"peg={peg} pla={pla}"))
    todos_piores.sort(key=lambda r: (-r[0], r[1], r[2]))
    for sev, k, ti, sub, a, b, det in todos_piores[:15]:
        tag = "TRIPLO" if sev == 3 else "duplo"
        print(f"  [{tag}] rotina={k:2d} T{ti+1} sub={sub:18s}")
        print(f"          {a}  ×  {b}")
        print(f"          {det}\n")

    # Plano repetido — mostrar amostra
    print("=== Amostra 10 casos PLANO repetido ===\n")
    for k, ti, sub, a, b, v in casos_plano[:10]:
        print(f"  rotina={k:2d} T{ti+1} sub={sub:18s} plano={v}")
        print(f"    {a}  ×  {b}\n")

    # Quantas rotinas têm AO MENOS 1 par sub-ótimo (qualquer dim)
    rotinas_com_problema = set()
    for casos in (casos_pegada, casos_plano, casos_eq):
        for tup in casos:
            rotinas_com_problema.add(tup[0])
    print(f"=== Rotinas com >=1 par sub-ótimo (qualquer dim): "
          f"{len(rotinas_com_problema)}/{N_ROTINAS} ===\n")

    # Mostrar amostra de pegada-only (sem plano match) — casos mais comuns
    print("=== Amostra 10 casos pegada-only (sem plano match) ===\n")
    pegada_only = []
    duplo_set = {(k, ti, a, b) for (k, ti, sub, a, b, *_r) in casos_duplo}
    triplo_set = {(k, ti, a, b) for (k, ti, sub, a, b, *_r) in casos_triplo}
    for (k, ti, sub, a, b, v) in casos_pegada:
        if (k, ti, a, b) in duplo_set or (k, ti, a, b) in triplo_set:
            continue
        pegada_only.append((k, ti, sub, a, b, v))
    for k, ti, sub, a, b, v in pegada_only[:10]:
        print(f"  rotina={k:2d} T{ti+1} sub={sub:18s} pegada={v}")
        print(f"    {a}  ×  {b}\n")


if __name__ == "__main__":
    main()
