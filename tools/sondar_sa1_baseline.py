"""Sondagem baseline pre/pos S-A1.

Item 0 do handoff S-A1 (decisão 4.4): re-rodar a tabela comparativa antigo
vs CSP em demandas diretas `("subregiao", X, 2)` antes de codar, persistir
snapshot, comparar pos-S-A1.

Reproduz o achado que motivou a frente:
- ombro(2): CSP 100% (composto + posterior_ombro) -- ZERO ombro_isolado;
  antigo 100% (composto + isolado).
- perna_posterior(2): CSP 100% (hinge + abduction); antigo ~52/48
  hinge+abduction / hinge+knee_flexion.

Subregioes alvo (do handoff):
- ombro: composto OBR(3) + isolado NAO-OBR(2) + posterior_ombro NAO-OBR(1)
- perna_posterior: hinge OBR(3) + knee_flexion NAO-OBR(2) + abduction NAO-OBR(1)
- peito: composto OBR(3) + isolado NAO-OBR(2) -- 1 nao-obrig: trivial
- perna_anterior: bilateral OBR(3) + unilateral NAO-OBR(2) -- 1 nao-obrig: trivial

Roda:
    python tools/sondar_sa1_baseline.py
    python tools/sondar_sa1_baseline.py --n 40 --out logs/sa1_baseline_pre.json
    python tools/sondar_sa1_baseline.py --peso-sa1 8 --out logs/sa1_pos.json
"""
from __future__ import annotations

import argparse
import json
import random
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
from gerador_treino import gerar_multiplos_treinos  # noqa: E402


SUBREGIOES_ALVO = ["ombro", "perna_posterior", "peito", "perna_anterior"]


def _rodar_csp_uma_seed(banco, sub: str, seed: int, peso_sa1: int,
                        peso_sa1_repet: int = 0) -> list[str]:
    """Retorna lista de padroes do treino gerado, em ordem."""
    kwargs = dict(
        nivel_aluno=3,
        seed=seed,
        variedade=ConfigVariedade(),
        peso_evitar_agonistas=10,
        tamanho_preferido=2,
        peso_tamanho_bloco=5,
        relaxar_familia=True,
    )
    if peso_sa1 > 0:
        kwargs["peso_sa1"] = peso_sa1
    if peso_sa1_repet > 0:
        kwargs["peso_sa1_repet"] = peso_sa1_repet
    r = gerar_rotina_csp(
        [[("subregiao", sub, 2)]],
        banco,
        **kwargs,
    )
    if not r.get("viavel"):
        return []
    treino = r["treinos"][0]["blocos"]
    padroes = []
    for bloco in treino:
        for ex in bloco:
            padroes.append(ex.padrao)
    return padroes


def _rodar_antigo_uma_seed(banco, sub: str, seed: int) -> list[str]:
    random.seed(seed)
    configs = [
        {
            "demandas": [("subregiao", sub, 2)],
            "max_complexidade": 3,
            "tamanho_bloco": 2,
            "evitar_agonistas": True,
        }
    ]
    sessoes = gerar_multiplos_treinos(
        banco, configs, relaxar_familia=True,
    )
    s = sessoes[0]
    padroes = []
    for bloco in s.blocos:
        for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
            if ex is not None:
                padroes.append(ex.padrao)
    return padroes


def _combo(padroes: list[str]) -> str:
    """Chave canonica da combinacao ignorando ordem."""
    return "+".join(sorted(padroes)) if padroes else "INVIAVEL"


def sondar(n_seeds: int = 40, peso_sa1: int = 0,
           peso_sa1_repet: int = 0) -> dict:
    banco = carregar_banco_ativo()
    out: dict[str, dict] = {}
    for sub in SUBREGIOES_ALVO:
        ant_counter: Counter = Counter()
        csp_counter: Counter = Counter()
        for seed in range(n_seeds):
            padroes_ant = _rodar_antigo_uma_seed(banco, sub, seed)
            ant_counter[_combo(padroes_ant)] += 1
            padroes_csp = _rodar_csp_uma_seed(
                banco, sub, seed, peso_sa1, peso_sa1_repet,
            )
            csp_counter[_combo(padroes_csp)] += 1
        out[sub] = {
            "antigo": dict(ant_counter),
            "csp": dict(csp_counter),
        }
    return out


def _formatar_pct(counter: dict, n: int) -> str:
    if not counter:
        return "(sem dados)"
    linhas = []
    for combo, qtd in sorted(counter.items(), key=lambda kv: -kv[1]):
        pct = 100.0 * qtd / n
        linhas.append(f"  {combo}: {qtd}/{n} ({pct:.0f}%)")
    return "\n".join(linhas)


def imprimir_relatorio(snapshot: dict, n_seeds: int, peso_sa1: int) -> None:
    cabec = (
        f"\n=== Sondagem S-A1 (n_seeds={n_seeds}, peso_sa1={peso_sa1}) ===\n"
    )
    print(cabec)
    for sub, dados in snapshot.items():
        print(f"--- {sub}(2) ---")
        print("Motor antigo:")
        print(_formatar_pct(dados["antigo"], n_seeds))
        print("Motor CSP:")
        print(_formatar_pct(dados["csp"], n_seeds))
        print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=40,
                        help="Numero de seeds por subregiao (default: 40)")
    parser.add_argument("--peso-sa1", type=int, default=0,
                        help="Peso S-A1 v1 (linear pesos) (default: 0)")
    parser.add_argument("--peso-sa1-repet", type=int, default=0,
                        help="Peso S-A1 v2 (padrao repetido) (default: 0)")
    parser.add_argument("--out", type=str, default=None,
                        help="Path opcional pra persistir snapshot json")
    args = parser.parse_args()

    snapshot = sondar(n_seeds=args.n, peso_sa1=args.peso_sa1,
                     peso_sa1_repet=args.peso_sa1_repet)
    print(f"\n[peso_sa1_repet={args.peso_sa1_repet}]")
    imprimir_relatorio(snapshot, args.n, args.peso_sa1)

    if args.out:
        out_path = ROOT / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({
            "n_seeds": args.n,
            "peso_sa1": args.peso_sa1,
            "subregioes": snapshot,
        }, indent=2))
        print(f"Snapshot persistido em {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
