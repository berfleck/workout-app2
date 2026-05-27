"""Sondagem S-R1 distribuição cross-treino de subregião dentro de região.

Mede a assimetria cross-treino do split de subregião em rotinas com demanda
nivel `regiao` em ≥2 treinos (achado 1 da auditoria 2026-05-26, faceta de
simetria T1↔T2).

Métricas por config:
  - pct_rotinas_split_repetido_lower: % rotinas em que T1 e T2 caem no
    MESMO split de subregião em `regiao lower(*)`. PRIMÁRIA — alvo
    significativa queda pós-S-R1.
  - pct_rotinas_vol_lower_assim: % rotinas com volume total
    (rotina) ant != post em demanda lower (achado original: 4ant+2post).
    Secundária — corrigido junto com a primária.
  - pct_rotinas_panturrilha: % rotinas com pelo menos 1 slot panturrilha
    (out-of-scope da frente, mas registrado).
  - tempo_p50_s: tempo de solve mediano (sanity check).

Corte 2026-05-27: N=5, 1 config default (Full Body 2T região = setup
exato do achado). Flag `--config=lower_iso` adiciona lower(3)×2T isolado.
Flag `--config=ambos` roda os 2.

Uso:
    python tools/sondar_sr1_cross_treino.py                          # peso=0, N=5
    python tools/sondar_sr1_cross_treino.py --peso 4                 # peso calibrado
    python tools/sondar_sr1_cross_treino.py --peso 4 --config ambos  # +lower(3)x2T
    python tools/sondar_sr1_cross_treino.py --n 10 --out logs/sr1_pos.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
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


def _configs(escopo: str) -> list[tuple[str, list[list[tuple[str, str, int]]]]]:
    """Configs canônicas pra S-R1. `escopo`: 'default' (só Full Body 2T) ou
    'lower_iso' (só lower(3)×2T) ou 'ambos'."""
    full_body_regiao_t = [
        ("regiao", "upper", 3),
        ("regiao", "lower", 3),
        ("regiao", "core", 2),
    ]
    lower_iso_t = [("regiao", "lower", 3)]
    full_body = ("Full Body 2T (regiao, achado)", [full_body_regiao_t, full_body_regiao_t])
    lower_iso = ("lower(3)x2T isolado", [lower_iso_t, lower_iso_t])
    if escopo == "default":
        return [full_body]
    if escopo == "lower_iso":
        return [lower_iso]
    return [full_body, lower_iso]


def _rodar_rotina(banco, demandas, seed, peso_sr1):
    kwargs = dict(
        nivel_aluno=3,
        seed=seed,
        variedade=ConfigVariedade(),
        peso_evitar_agonistas=10,
        tamanho_preferido=2,
        peso_tamanho_bloco=5,
        peso_sa1=12,
        peso_sa1_repet=10,
        peso_sb5=4,  # já em produção (default ON)
        relaxar_familia=True,
    )
    if peso_sr1 > 0:
        kwargs["peso_sr1"] = peso_sr1
    t0 = time.perf_counter()
    r = gerar_rotina_csp(demandas, banco, **kwargs)
    elapsed = time.perf_counter() - t0
    return r, elapsed


# Subregiões da região lower (ordem canônica pra split estável).
_SUBS_LOWER = ("perna_anterior", "perna_posterior", "panturrilha", "adutores")


def _split_subregiao_lower_no_treino(treino) -> tuple[int, ...]:
    """Conta exs por subregião lower no treino. Retorna tupla na ordem de
    _SUBS_LOWER pra comparação."""
    contador: Counter = Counter()
    for bloco in treino["blocos"]:
        for ex in bloco:
            if ex.subregiao in _SUBS_LOWER:
                contador[ex.subregiao] += 1
    return tuple(contador.get(s, 0) for s in _SUBS_LOWER)


def _analisar_rotina(rotina) -> dict:
    """Mede assimetria cross-treino do split de subregião lower."""
    treinos = rotina.get("treinos", [])
    splits = [_split_subregiao_lower_no_treino(t) for t in treinos]

    split_t1_eq_t2 = (
        len(splits) >= 2 and splits[0] == splits[1]
    )
    # Volume rotina ant vs post
    total_ant = sum(s[0] for s in splits)
    total_post = sum(s[1] for s in splits)
    total_pant = sum(s[2] for s in splits)
    vol_lower_assim = total_ant != total_post
    pant_presente = total_pant > 0

    return {
        "splits_lower_por_treino": [list(s) for s in splits],
        "split_t1_eq_t2": split_t1_eq_t2,
        "vol_lower_assim": vol_lower_assim,
        "pant_presente": pant_presente,
        "total_ant": total_ant,
        "total_post": total_post,
        "total_pant": total_pant,
    }


def sondar(n_seeds: int, peso_sr1: int, escopo: str) -> dict:
    banco = carregar_banco_ativo()
    out: dict[str, dict] = {}
    for nome, demandas in _configs(escopo):
        n_split_repetido = 0
        n_vol_assim = 0
        n_pant_presente = 0
        tempos: list[float] = []
        inviaveis = 0
        exemplos: list[str] = []
        for seed in range(n_seeds):
            r, elapsed = _rodar_rotina(banco, demandas, seed, peso_sr1)
            tempos.append(elapsed)
            if not r.get("viavel"):
                inviaveis += 1
                continue
            stats = _analisar_rotina(r)
            if stats["split_t1_eq_t2"]:
                n_split_repetido += 1
            if stats["vol_lower_assim"]:
                n_vol_assim += 1
            if stats["pant_presente"]:
                n_pant_presente += 1
            if len(exemplos) < 3:
                exemplos.append(
                    f"seed={seed} splits_lower={stats['splits_lower_por_treino']} "
                    f"(ant={stats['total_ant']}, post={stats['total_post']}, "
                    f"pant={stats['total_pant']})"
                )
        n_validos = n_seeds - inviaveis
        out[nome] = {
            "n_seeds": n_seeds,
            "inviaveis": inviaveis,
            "n_split_t1_eq_t2": n_split_repetido,
            "n_vol_lower_assim": n_vol_assim,
            "n_pant_presente": n_pant_presente,
            "pct_split_t1_eq_t2": (
                100.0 * n_split_repetido / n_validos if n_validos else 0.0
            ),
            "pct_vol_lower_assim": (
                100.0 * n_vol_assim / n_validos if n_validos else 0.0
            ),
            "pct_pant_presente": (
                100.0 * n_pant_presente / n_validos if n_validos else 0.0
            ),
            "tempo_p50_s": statistics.median(tempos) if tempos else 0.0,
            "tempo_max_s": max(tempos) if tempos else 0.0,
            "exemplos": exemplos,
        }
    return out


def imprimir_relatorio(snapshot, peso_sr1, n_seeds):
    print(f"\n=== Sondagem S-R1 (peso_sr1={peso_sr1}, N={n_seeds}) ===\n")
    print(
        f"{'Config':<32} {'% split T1=T2':>14} {'% vol asym':>12} "
        f"{'% pant':>8} {'p50 (s)':>9} {'inviav':>7}"
    )
    print("-" * 90)
    for nome, dados in snapshot.items():
        print(
            f"{nome:<32} "
            f"{dados['pct_split_t1_eq_t2']:>13.1f}% "
            f"{dados['pct_vol_lower_assim']:>11.1f}% "
            f"{dados['pct_pant_presente']:>7.1f}% "
            f"{dados['tempo_p50_s']:>9.2f} "
            f"{dados['inviaveis']:>7}"
        )
    print("\nExemplos de rotinas (até 3 por config):")
    for nome, dados in snapshot.items():
        if dados["exemplos"]:
            print(f"\n[{nome}]")
            for ex in dados["exemplos"]:
                print(f"  {ex}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=5, help="N seeds por config (default 5)")
    p.add_argument(
        "--peso", type=int, default=0,
        help="peso_sr1 (default 0 = baseline pré-S-R1)",
    )
    p.add_argument(
        "--config", type=str, default="default",
        choices=["default", "lower_iso", "ambos"],
        help="qual config rodar (default = só Full Body 2T)",
    )
    p.add_argument("--out", type=str, default=None, help="Path opcional pra snapshot json")
    args = p.parse_args()

    snapshot = sondar(args.n, args.peso, args.config)
    imprimir_relatorio(snapshot, args.peso, args.n)

    if args.out:
        out_path = ROOT / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({
            "n_seeds": args.n,
            "peso_sr1": args.peso,
            "config_escopo": args.config,
            "configs": snapshot,
        }, indent=2, ensure_ascii=False))
        print(f"\nSnapshot persistido em {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
