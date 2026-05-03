"""Mede entropia de Shannon dos pareamentos (duplas/trios) gerados pelo motor.

Roda `gerar_multiplos_treinos` N=100 vezes com seeds 1..100 contra configs
representativas. Para cada bloco, registra a tupla ordenada dos nomes dos
exercícios. Calcula entropia da distribuição de duplas/trios e número de
duplas únicas.

A entropia mede a "imprevisibilidade" do pareamento — cascata determinística
da pré-Etapa 5 produz baixa entropia (sempre o mesmo par dada a seed
upstream); softmax pós-Etapa 5 deve subir significativamente.

Uso:
    python tools/medir_entropia_pareamentos.py [--out CAMINHO]

Saída JSON em `docs/refatoracao/logs/etapa_5_baseline.json` (default).
Usar `--out etapa_5_pos.json` ao rodar pós-refator para comparação.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gerador_treino import carregar_banco, gerar_multiplos_treinos  # noqa: E402

XLSX = ROOT / "banco_exercicios.xlsx"
OUT_DEFAULT = ROOT / "docs" / "refatoracao" / "logs" / "etapa_5_baseline.json"

N_ITER = 100

CONFIGS = {
    "core_3_uni_pair": {
        # Caso V-Up Uni — força exercícios travados pra reproduzir o cenário
        # do problema 6 do memoria_projeto.md
        "descricao": "core_isometrico(1) + 2 unilaterais travados (V-Up Uni + Tríceps Uni)",
        "config_factory": lambda banco: {
            "demandas": [("padrao", "core_isometrico", 1)],
            "exercicios_travados": [
                e for e in banco
                if e.nome in {"V-Up Unilateral", "Tríceps Unilateral Polia"}
            ],
            "tamanho_bloco": 2,
        },
        "n_treinos": 1,
        "relaxar_familia": True,
    },
    "lower_4_upper_3": {
        "descricao": "lower(4) + upper(3) — config multi-região representativa",
        "config_factory": lambda banco: {
            "demandas": [("regiao", "lower", 4), ("regiao", "upper", 3)],
            "tamanho_bloco": 2,
            "evitar_agonistas": True,
        },
        "n_treinos": 1,
        "relaxar_familia": True,
    },
}


def _bloco_tupla(bloco) -> tuple[str, ...]:
    """Tupla ordenada dos nomes dos exercícios de um bloco (super série)."""
    nomes = [ex.nome for ex in (bloco.ex1, bloco.ex2, bloco.ex3) if ex]
    return tuple(sorted(nomes))


def _entropia_shannon(contador: Counter) -> float:
    """Entropia de Shannon (base 2) da distribuição em `contador`. Em bits."""
    total = sum(contador.values())
    if total == 0:
        return 0.0
    h = 0.0
    for c in contador.values():
        p = c / total
        if p > 0:
            h -= p * math.log2(p)
    return h


def _coletar_blocos(banco, cfg_def: dict) -> Counter:
    """Roda N_ITER iterações e devolve Counter de blocos (tuplas ordenadas)."""
    contador: Counter = Counter()
    for seed in range(1, N_ITER + 1):
        random.seed(seed)
        cfg = cfg_def["config_factory"](banco)
        n_treinos = cfg_def["n_treinos"]
        sessoes = gerar_multiplos_treinos(
            banco,
            [cfg] * n_treinos,
            relaxar_familia=cfg_def.get("relaxar_familia", False),
        )
        for sessao in sessoes:
            for bloco in sessao.blocos:
                contador[_bloco_tupla(bloco)] += 1
    return contador


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT_DEFAULT,
        help=f"Arquivo de saída JSON (default: {OUT_DEFAULT.relative_to(ROOT)})",
    )
    args = parser.parse_args()

    banco = carregar_banco(str(XLSX))
    print(f"Banco: {len(banco)} exercícios")

    resultados = {}
    for config_id, cfg_def in CONFIGS.items():
        print(f"\n[{config_id}] {cfg_def['descricao']}")
        print(f"  Rodando {N_ITER} iterações...")
        contador = _coletar_blocos(banco, cfg_def)
        total_blocos = sum(contador.values())
        n_unicos = len(contador)
        entropia = _entropia_shannon(contador)
        # Entropia normalizada: H / log2(N) = "uniformidade" entre 0 (sempre o mesmo)
        # e 1 (uniforme entre todos os blocos únicos)
        entropia_max = math.log2(n_unicos) if n_unicos > 1 else 0.0
        entropia_norm = (entropia / entropia_max) if entropia_max > 0 else 0.0
        top_5 = contador.most_common(5)
        resultados[config_id] = {
            "descricao": cfg_def["descricao"],
            "n_iter": N_ITER,
            "total_blocos": total_blocos,
            "blocos_unicos": n_unicos,
            "entropia_bits": round(entropia, 4),
            "entropia_max_bits": round(entropia_max, 4),
            "entropia_normalizada": round(entropia_norm, 4),
            "top_5_pareamentos": [
                {"bloco": list(tup), "frequencia": cnt}
                for tup, cnt in top_5
            ],
        }
        print(f"  Total blocos: {total_blocos}")
        print(f"  Blocos únicos: {n_unicos}")
        print(f"  Entropia: {entropia:.4f} bits (max {entropia_max:.4f}, norm {entropia_norm:.4f})")
        print("  Top 5 pareamentos:")
        for tup, cnt in top_5:
            pct = cnt / total_blocos * 100
            print(f"    {pct:5.1f}% ({cnt:3d}x) {' + '.join(tup)}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResultados salvos em: {args.out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
