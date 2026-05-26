"""Inspecao qualitativa: 1 seed, varios pesos.

Mostra a rotina inteira (16 slots = 2 treinos x 8 slots) gerada com a mesma
seed do CSP em pesos diferentes de aderencia. Pra comparacao visual lado-a-
lado: o que muda no exercicio escolhido por slot quando peso muda?

Roda:
    python tools/inspecionar_rotina_por_peso.py --seed 0 --pesos 0,1,2,4
"""
from __future__ import annotations

import argparse
import sys
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


def _gerar(banco, seed: int, peso: int) -> list[list[list]]:
    """Retorna [[(ex_obj), ...] por bloco] por treino."""
    r = gerar_rotina_csp(
        DEMANDAS, banco, nivel_aluno=NIVEL, seed=seed,
        variedade=ConfigVariedade(),
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


_TIER_SHORT = {
    "Principal": "PRI",
    "Intermediário": "INT",
    "Acessório": "ACE",
}


def _formatar(rotina) -> str:
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
                    f"    {label} [{tier}] {ex.nome:38s} "
                    f"({ex.subregiao}/{ex.padrao})"
                )
    return "\n".join(linhas)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--pesos", type=str, default="0,1,2,4")
    args = parser.parse_args()
    pesos = [int(p) for p in args.pesos.split(",")]
    banco = carregar_banco_ativo()
    for peso in pesos:
        rotina = _gerar(banco, args.seed, peso)
        print(f"\n=== peso_aderencia={peso} (seed={args.seed}) ===")
        print(_formatar(rotina))
    print()


if __name__ == "__main__":
    main()
