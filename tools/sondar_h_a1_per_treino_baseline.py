"""Sondagem baseline pre/pos cobertura per-treino H-A1 marker.

Reproduz setup do achado clinico Filipe Santos (id=17, rotina
`20260525_195735_bb15`, 2026-05-25):

Demanda: `regiao upper(3) + regiao lower(3) + regiao core(2)` x 2T.

Mede % rotinas com cobertura por padrao obrigatorio de subregiao
PER-TREINO (T1 e T2 cada um deve ter o padrao obrigatorio das
subregioes obrigadas pelo H-A0).

Antes do fix esperado (com `subregioes_obrigadas_ha0` ativando H-A1
cross-rotina):
- T1 squat_bilateral: ~50% (cross-rotina garante 1 na rotina, nao por
  treino — solver pode botar so em T2);
- T2 squat_bilateral: ~complemento de T1;
- agregado "ambos os treinos com squat_bilateral": <100%.

Pos-fix esperado: cada treino com cada padrao obrigatorio das subs
obrigadas. Alvo: >=80% (handoff Secao 6.1).

Roda:
    python tools/sondar_h_a1_per_treino_baseline.py
    python tools/sondar_h_a1_per_treino_baseline.py --n 20
    python tools/sondar_h_a1_per_treino_baseline.py --out logs/h_a1_per_treino_baseline_pre.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gerador_csp import (  # noqa: E402
    ConfigVariedade,
    carregar_banco_ativo,
    gerar_rotina_csp,
)
from gerador_treino import ANCORAS_POR_REGIAO, ANCORAS_POR_SUBREGIAO  # noqa: E402


DEMANDAS_FILIPE = [
    [("regiao", "upper", 3), ("regiao", "lower", 3), ("regiao", "core", 2)],
    [("regiao", "upper", 3), ("regiao", "lower", 3), ("regiao", "core", 2)],
]


def _padroes_obrigatorios_por_regiao() -> dict[str, list[tuple[str, str]]]:
    """Pra cada regiao com ancoras, lista de (subregiao_obrig, padrao_obrig)."""
    out: dict[str, list[tuple[str, str]]] = {}
    for R, ancoras_R in ANCORAS_POR_REGIAO.items():
        pares: list[tuple[str, str]] = []
        for a in ancoras_R:
            if not a.get("obrigatoria"):
                continue
            sub = a["subregiao"]
            for sub_ancora in ANCORAS_POR_SUBREGIAO.get(sub, []):
                if sub_ancora.get("obrigatoria"):
                    pares.append((sub, sub_ancora["padrao"]))
        out[R] = pares
    return out


PADROES_OBRIG_POR_REGIAO = _padroes_obrigatorios_por_regiao()


def _gerar_rotina(banco, seed: int):
    return gerar_rotina_csp(
        DEMANDAS_FILIPE,
        banco,
        nivel_aluno=3,
        seed=seed,
        variedade=ConfigVariedade(),
        peso_evitar_agonistas=10,
        tamanho_preferido=2,
        peso_tamanho_bloco=5,
        relaxar_familia=True,
        peso_sa1=12,
        peso_sa1_repet=10,
    )


def _padroes_do_treino(rotina_treino: dict) -> list[str]:
    out: list[str] = []
    for bloco in rotina_treino["blocos"]:
        for ex in bloco:
            out.append(ex.padrao)
    return out


def sondar(n_seeds: int) -> dict:
    banco = carregar_banco_ativo()
    # Pares unicos (regiao, sub_obrig, padrao_obrig) que o setup do Filipe ativa.
    pares_obrig = []
    for R in {"upper", "lower"}:  # core nao tem obrig
        for sub, pad in PADROES_OBRIG_POR_REGIAO.get(R, []):
            pares_obrig.append((R, sub, pad))

    # Por (treino_idx, R, sub, pad) -> contador de rotinas em que aparece.
    aparicoes_per_treino: dict[tuple[int, str, str, str], int] = defaultdict(int)
    aparicoes_cross_rotina: dict[tuple[str, str, str], int] = defaultdict(int)
    rotinas_com_cobertura_completa = 0
    rotinas_inviaveis = 0
    n_rotinas_validas = 0

    for seed in range(n_seeds):
        r = _gerar_rotina(banco, seed)
        if not r.get("viavel"):
            rotinas_inviaveis += 1
            continue
        n_rotinas_validas += 1
        # Padroes por treino.
        padroes_por_treino = [_padroes_do_treino(t) for t in r["treinos"]]
        cobertura_completa_rotina = True
        for R, sub, pad in pares_obrig:
            tem_em_cada_treino = True
            tem_em_pelo_menos_um = False
            for t_idx, padroes_t in enumerate(padroes_por_treino):
                if pad in padroes_t:
                    aparicoes_per_treino[(t_idx, R, sub, pad)] += 1
                    tem_em_pelo_menos_um = True
                else:
                    tem_em_cada_treino = False
            if tem_em_pelo_menos_um:
                aparicoes_cross_rotina[(R, sub, pad)] += 1
            if not tem_em_cada_treino:
                cobertura_completa_rotina = False
        if cobertura_completa_rotina:
            rotinas_com_cobertura_completa += 1

    # Monta relatorio.
    n_treinos = len(DEMANDAS_FILIPE)
    rel = {
        "n_seeds": n_seeds,
        "n_rotinas_validas": n_rotinas_validas,
        "n_rotinas_inviaveis": rotinas_inviaveis,
        "rotinas_com_cobertura_completa_per_treino": rotinas_com_cobertura_completa,
        "pct_cobertura_completa_per_treino": (
            100 * rotinas_com_cobertura_completa / max(n_rotinas_validas, 1)
        ),
        "por_padrao_obrigatorio": [],
    }
    for R, sub, pad in pares_obrig:
        entry = {
            "regiao": R,
            "subregiao": sub,
            "padrao_obrigatorio": pad,
            "cross_rotina_pct": (
                100 * aparicoes_cross_rotina.get((R, sub, pad), 0)
                / max(n_rotinas_validas, 1)
            ),
            "per_treino": [],
        }
        for t_idx in range(n_treinos):
            n_appears = aparicoes_per_treino.get((t_idx, R, sub, pad), 0)
            entry["per_treino"].append({
                "treino_idx": t_idx,
                "n_rotinas_com_padrao_no_treino": n_appears,
                "pct": 100 * n_appears / max(n_rotinas_validas, 1),
            })
        rel["por_padrao_obrigatorio"].append(entry)
    return rel


def imprimir_relatorio(rel: dict) -> None:
    print(f"\n=== Sondagem H-A1 per-treino (Filipe Santos setup, n={rel['n_seeds']}) ===\n")
    print(f"Rotinas validas: {rel['n_rotinas_validas']}/{rel['n_seeds']} "
          f"(inviaveis: {rel['n_rotinas_inviaveis']})")
    print(f"Cobertura completa per-treino: "
          f"{rel['rotinas_com_cobertura_completa_per_treino']}/{rel['n_rotinas_validas']} "
          f"({rel['pct_cobertura_completa_per_treino']:.1f}%)\n")
    print(f"{'regiao':<8} {'sub':<18} {'padrao':<24} {'T1%':>6} {'T2%':>6} {'cross%':>7}")
    print(f"{'-'*8} {'-'*18} {'-'*24} {'-'*6} {'-'*6} {'-'*7}")
    for entry in rel["por_padrao_obrigatorio"]:
        t1_pct = entry["per_treino"][0]["pct"] if len(entry["per_treino"]) > 0 else 0
        t2_pct = entry["per_treino"][1]["pct"] if len(entry["per_treino"]) > 1 else 0
        print(f"{entry['regiao']:<8} {entry['subregiao']:<18} "
              f"{entry['padrao_obrigatorio']:<24} "
              f"{t1_pct:>5.0f}% {t2_pct:>5.0f}% {entry['cross_rotina_pct']:>6.0f}%")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10, help="Numero de seeds (default 10).")
    ap.add_argument("--out", type=str, default=None,
                    help="Path para persistir relatorio JSON (opcional).")
    args = ap.parse_args()

    rel = sondar(args.n)
    imprimir_relatorio(rel)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            json.dump(rel, f, ensure_ascii=False, indent=2)
        print(f"\n-> salvo em {out}")


if __name__ == "__main__":
    main()
