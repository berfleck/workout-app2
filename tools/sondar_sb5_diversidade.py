"""Sondagem S-B5 diversidade de região INTRA-bloco.

Mede a frequência de blocos com 2+ exercícios da mesma região
("circuito do mesmo grupo" — achado 3 da auditoria 2026-05-26).

Métricas por config:
  - pct_blocos_same_region: % blocos com 2+ exs da mesma região (sobre
    blocos com >=2 exs). PRIMÁRIA — alvo <10% pós-S-B5.
  - pct_blocos_solo: % blocos com 1 ex. Regressão da Fatia 4.C —
    sondagem detecta motor "fugindo pra solos" quando S-B5 dominante.
  - tempo_p50_s: tempo de solve mediano (sanity check, não deve regredir muito).

Roda nas 5 configs canônicas do harness E.0:
  1. Full Body 2T (subregião) — composição variada
  2. ABC 3T — push/pull/lower split
  3. upper(3)×2T — single-region, força graceful degradation
  4. perna_ant(3)+perna_post(3) — single-region (lower), graceful
  5. Full Body 2T (região, H-A0) — setup exato da auditoria 2026-05-26

Uso:
    python tools/sondar_sb5_diversidade.py                     # peso=0, N=10
    python tools/sondar_sb5_diversidade.py --peso 10           # peso=10
    python tools/sondar_sb5_diversidade.py --n 20 --out logs/sb5_pre.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gerador_csp import (  # noqa: E402
    ConfigVariedade,
    carregar_banco_ativo,
    gerar_rotina_csp,
)


# Configs canônicas (mesmas do harness E.0).
def _configs() -> list[tuple[str, list[list[tuple[str, str, int]]]]]:
    full_body_t1 = [
        ("subregiao", "peito", 1),
        ("subregiao", "costas", 2),
        ("subregiao", "ombro", 1),
        ("subregiao", "perna_anterior", 2),
        ("subregiao", "perna_posterior", 2),
        ("regiao", "core", 1),
    ]
    full_body_t2 = [
        ("subregiao", "peito", 2),
        ("subregiao", "costas", 1),
        ("subregiao", "bracos", 2),
        ("subregiao", "perna_anterior", 1),
        ("subregiao", "perna_posterior", 2),
        ("regiao", "core", 1),
    ]
    abc_a = [
        ("subregiao", "peito", 3),
        ("subregiao", "ombro", 2),
        ("padrao", "triceps", 2),
    ]
    abc_b = [
        ("subregiao", "costas", 4),
        ("subregiao", "bracos", 2),
        ("regiao", "core", 1),
    ]
    abc_c = [
        ("subregiao", "perna_anterior", 2),
        ("subregiao", "perna_posterior", 2),
        ("subregiao", "adutores", 1),
        ("subregiao", "panturrilha", 1),
        ("regiao", "core", 1),
    ]
    upper_t = [("regiao", "upper", 3)]
    perna = [
        ("subregiao", "perna_anterior", 3),
        ("subregiao", "perna_posterior", 3),
    ]
    full_body_regiao_t = [
        ("regiao", "upper", 3),
        ("regiao", "lower", 3),
        ("regiao", "core", 2),
    ]
    return [
        ("Full Body 2T (sub)", [full_body_t1, full_body_t2]),
        ("ABC 3T", [abc_a, abc_b, abc_c]),
        ("upper(3)x2T", [upper_t, upper_t]),
        ("perna_ant(3)+perna_post(3)", [perna]),
        ("Full Body 2T (regiao, H-A0)", [full_body_regiao_t, full_body_regiao_t]),
    ]


def _rodar_rotina(banco, demandas, seed, peso_sb5):
    kwargs = dict(
        nivel_aluno=3,
        seed=seed,
        variedade=ConfigVariedade(),
        peso_evitar_agonistas=10,
        tamanho_preferido=2,
        peso_tamanho_bloco=5,
        peso_sa1=12,
        peso_sa1_repet=10,
        relaxar_familia=True,
    )
    # peso_sb5 só é aceito quando a feature está implementada (post-frente).
    if peso_sb5 > 0:
        kwargs["peso_sb5"] = peso_sb5
    t0 = time.perf_counter()
    r = gerar_rotina_csp(demandas, banco, **kwargs)
    elapsed = time.perf_counter() - t0
    return r, elapsed


def _analisar_rotina(rotina) -> dict:
    """Conta blocos same-region e blocos solo na rotina inteira.

    rotina["treinos"][t]["blocos"] = list[list[Exercicio]] (blocos do treino t).
    """
    n_blocos = 0
    n_blocos_com_2plus = 0
    n_blocos_same_region = 0
    n_blocos_solo = 0
    exemplos_same_region: list[str] = []
    for t_idx, treino in enumerate(rotina["treinos"]):
        for b_idx, bloco in enumerate(treino["blocos"]):
            n_blocos += 1
            if len(bloco) == 1:
                n_blocos_solo += 1
                continue
            if len(bloco) >= 2:
                n_blocos_com_2plus += 1
                regioes = [ex.regiao for ex in bloco]
                # Same-region = pelo menos 2 exs com a mesma região.
                if len(set(regioes)) < len(regioes):
                    n_blocos_same_region += 1
                    nomes = " + ".join(f"{ex.nome} [{ex.regiao}]" for ex in bloco)
                    exemplos_same_region.append(
                        f"T{t_idx+1} Bloco {chr(65+b_idx)}: {nomes}"
                    )
    return {
        "n_blocos": n_blocos,
        "n_blocos_com_2plus": n_blocos_com_2plus,
        "n_blocos_same_region": n_blocos_same_region,
        "n_blocos_solo": n_blocos_solo,
        "exemplos_same_region": exemplos_same_region,
    }


def sondar(n_seeds: int, peso_sb5: int) -> dict:
    banco = carregar_banco_ativo()
    out: dict[str, dict] = {}
    for nome, demandas in _configs():
        agg_n_blocos = 0
        agg_n_blocos_com_2plus = 0
        agg_n_blocos_same_region = 0
        agg_n_blocos_solo = 0
        tempos: list[float] = []
        inviaveis = 0
        exemplos_collected: list[str] = []
        for seed in range(n_seeds):
            r, elapsed = _rodar_rotina(banco, demandas, seed, peso_sb5)
            tempos.append(elapsed)
            if not r.get("viavel"):
                inviaveis += 1
                continue
            stats = _analisar_rotina(r)
            agg_n_blocos += stats["n_blocos"]
            agg_n_blocos_com_2plus += stats["n_blocos_com_2plus"]
            agg_n_blocos_same_region += stats["n_blocos_same_region"]
            agg_n_blocos_solo += stats["n_blocos_solo"]
            # Junta uns exemplos de same-region pra log (max 3 por config).
            for ex in stats["exemplos_same_region"]:
                if len(exemplos_collected) < 3:
                    exemplos_collected.append(f"seed={seed} | {ex}")
        out[nome] = {
            "n_seeds": n_seeds,
            "inviaveis": inviaveis,
            "n_blocos_total": agg_n_blocos,
            "n_blocos_com_2plus": agg_n_blocos_com_2plus,
            "n_blocos_same_region": agg_n_blocos_same_region,
            "n_blocos_solo": agg_n_blocos_solo,
            "pct_blocos_same_region": (
                100.0 * agg_n_blocos_same_region / agg_n_blocos_com_2plus
                if agg_n_blocos_com_2plus else 0.0
            ),
            "pct_blocos_solo": (
                100.0 * agg_n_blocos_solo / agg_n_blocos if agg_n_blocos else 0.0
            ),
            "tempo_p50_s": statistics.median(tempos) if tempos else 0.0,
            "tempo_max_s": max(tempos) if tempos else 0.0,
            "exemplos_same_region": exemplos_collected,
        }
    return out


def imprimir_relatorio(snapshot, peso_sb5, n_seeds):
    print(f"\n=== Sondagem S-B5 (peso_sb5={peso_sb5}, N={n_seeds}) ===\n")
    print(
        f"{'Config':<32} {'% same-region':>14} {'% solo':>9} "
        f"{'p50 (s)':>9} {'inviav':>7}"
    )
    print("-" * 80)
    for nome, dados in snapshot.items():
        print(
            f"{nome:<32} "
            f"{dados['pct_blocos_same_region']:>13.1f}% "
            f"{dados['pct_blocos_solo']:>8.1f}% "
            f"{dados['tempo_p50_s']:>9.2f} "
            f"{dados['inviaveis']:>7}"
        )
    print("\nExemplos de blocos same-region (até 3 por config):")
    for nome, dados in snapshot.items():
        if dados["exemplos_same_region"]:
            print(f"\n[{nome}]")
            for ex in dados["exemplos_same_region"]:
                print(f"  {ex}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=10, help="N seeds por config (default 10)")
    p.add_argument(
        "--peso", type=int, default=0,
        help="peso_sb5 (default 0 = baseline pré-S-B5)",
    )
    p.add_argument("--out", type=str, default=None, help="Path opcional pra snapshot json")
    args = p.parse_args()

    snapshot = sondar(args.n, args.peso)
    imprimir_relatorio(snapshot, args.peso, args.n)

    if args.out:
        out_path = ROOT / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({
            "n_seeds": args.n,
            "peso_sb5": args.peso,
            "configs": snapshot,
        }, indent=2, ensure_ascii=False))
        print(f"\nSnapshot persistido em {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
