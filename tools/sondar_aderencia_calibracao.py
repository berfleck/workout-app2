"""Sondagem pre/pos calibracao de `_PESO_ADERENCIA_POR_PERFIL`.

Achado 4 da auditoria 2026-05-26: default `{alta:2, media:0, baixa:0}` faz
0/16 slots Principal em Full Body 2T com aderencia media (default UI),
11/16 com alta. `media==baixa==0` torna perfis indistinguiveis. Calibracao
nunca foi formal — Frente D foi tunada em 1 smoke (hinge(1)).

Espelha pattern do `sondar_sa1_baseline.py`. Roda config canonica da
auditoria (Aluno Teste, nivel=intermediario, demanda
`regiao upper(3)+lower(3)+core(2)` × 2 treinos = 16 slots por rotina) pra
cada peso candidato em {0,1,2,3,4} com N seeds fixas (default 20).

Mede:
- % slots tier Principal / Intermediario / Acessorio (agregado sobre
  16 × N slots por peso)
- nomes distintos no total (16 × N slots = pool de variedade)
- nomes distintos dentre os Principal (variedade dentro do tier alto)
- frequencia do nome mais comum (proxy de concentracao)

Roda:
    python tools/sondar_aderencia_calibracao.py
    python tools/sondar_aderencia_calibracao.py --n 20 \
        --out docs/refatoracao/logs/aderencia_calibracao_pre.json
    python tools/sondar_aderencia_calibracao.py --pesos 0,1,2,3,4 \
        --out docs/refatoracao/logs/aderencia_calibracao_pos.json
"""
from __future__ import annotations

import argparse
import json
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


DEMANDAS_POR_TREINO = [
    [("regiao", "upper", 3), ("regiao", "lower", 3), ("regiao", "core", 2)],
    [("regiao", "upper", 3), ("regiao", "lower", 3), ("regiao", "core", 2)],
]
NIVEL_ALUNO_CSP = 2  # intermediario, conforme auditoria 2026-05-26
PESOS_DEFAULT = [0, 1, 2, 3, 4]


def _rodar_uma_seed(banco, seed: int, peso_aderencia: int) -> list[dict]:
    """Retorna lista de dicts {nome, tier, subregiao, regiao} pros 16 slots."""
    r = gerar_rotina_csp(
        DEMANDAS_POR_TREINO,
        banco,
        nivel_aluno=NIVEL_ALUNO_CSP,
        seed=seed,
        variedade=ConfigVariedade(),
        peso_aderencia=peso_aderencia,
        peso_evitar_agonistas=0,   # default UI = OFF (per auditoria)
        tamanho_preferido=2,
        peso_tamanho_bloco=5,
        relaxar_familia=True,
    )
    if not r.get("viavel"):
        return []
    slots = []
    for treino in r["treinos"]:
        for grupo in treino["grupos"]:
            for ex in grupo["exercicios"]:
                slots.append({
                    "nome": ex.nome,
                    "tier": ex.tier or "(vazio)",
                    "subregiao": ex.subregiao,
                    "regiao": ex.regiao,
                })
    return slots


def sondar(n_seeds: int, pesos: list[int]) -> dict:
    banco = carregar_banco_ativo()
    out: dict[int, dict] = {}
    for peso in pesos:
        tier_counter: Counter = Counter()
        nome_counter: Counter = Counter()
        principais_counter: Counter = Counter()
        n_slots_total = 0
        n_inviavel = 0
        for seed in range(n_seeds):
            slots = _rodar_uma_seed(banco, seed, peso)
            if not slots:
                n_inviavel += 1
                continue
            n_slots_total += len(slots)
            for s in slots:
                tier_counter[s["tier"]] += 1
                nome_counter[s["nome"]] += 1
                if s["tier"] == "Principal":
                    principais_counter[s["nome"]] += 1
        out[peso] = {
            "n_seeds": n_seeds,
            "n_inviavel": n_inviavel,
            "n_slots_total": n_slots_total,
            "tier_dist": dict(tier_counter),
            "nomes_distintos": len(nome_counter),
            "principais_distintos": len(principais_counter),
            "top_nome_freq": nome_counter.most_common(1)[0][1] if nome_counter else 0,
            "top_nome": nome_counter.most_common(1)[0][0] if nome_counter else "",
        }
    return out


def _formatar_tabela(snapshot: dict) -> str:
    linhas = []
    cab = (
        f"{'peso':>5} | {'Principal':>10} | {'Intermed.':>10} | "
        f"{'Acessorio':>10} | {'nomes_dist':>11} | {'princ_dist':>11} | "
        f"{'top':>5}"
    )
    linhas.append(cab)
    linhas.append("-" * len(cab))
    for peso, d in sorted(snapshot.items()):
        total = d["n_slots_total"] or 1
        p_pct = 100.0 * d["tier_dist"].get("Principal", 0) / total
        i_pct = 100.0 * d["tier_dist"].get("Intermediário", 0) / total
        a_pct = 100.0 * d["tier_dist"].get("Acessório", 0) / total
        linhas.append(
            f"{peso:>5} | {p_pct:>9.1f}% | {i_pct:>9.1f}% | {a_pct:>9.1f}% | "
            f"{d['nomes_distintos']:>11} | {d['principais_distintos']:>11} | "
            f"{d['top_nome_freq']:>5}"
        )
    return "\n".join(linhas)


def imprimir_relatorio(snapshot: dict, n_seeds: int) -> None:
    print(f"\n=== Sondagem aderencia (config canonica auditoria 2026-05-26) ===")
    print(f"Demanda: regiao upper(3)+lower(3)+core(2) x 2 treinos = 16 slots/rotina")
    print(f"nivel_aluno={NIVEL_ALUNO_CSP} (intermediario), n_seeds={n_seeds}")
    print(f"Cada linha = {n_seeds} rotinas = {n_seeds * 16} slots agregados.\n")
    print(_formatar_tabela(snapshot))
    print()
    # Detalhe top nome por peso (pra ver concentracao):
    print("Top-1 nome por peso (proxy de concentracao):")
    for peso, d in sorted(snapshot.items()):
        if d["top_nome"]:
            pct = 100.0 * d["top_nome_freq"] / (d["n_slots_total"] or 1)
            print(f"  peso={peso}: {d['top_nome']} = {d['top_nome_freq']}/{d['n_slots_total']} ({pct:.1f}%)")
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20,
                        help="Numero de seeds por peso (default: 20)")
    parser.add_argument("--pesos", type=str, default=None,
                        help="Lista CSV de pesos a sondar. Default: 0,1,2,3,4")
    parser.add_argument("--out", type=str, default=None,
                        help="Path opcional pra persistir snapshot json")
    args = parser.parse_args()

    pesos = (
        [int(p) for p in args.pesos.split(",")]
        if args.pesos else PESOS_DEFAULT
    )

    snapshot = sondar(n_seeds=args.n, pesos=pesos)
    imprimir_relatorio(snapshot, args.n)

    if args.out:
        out_path = ROOT / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({
            "n_seeds": args.n,
            "pesos": pesos,
            "demandas_por_treino": [
                [list(d) for d in demanda] for demanda in DEMANDAS_POR_TREINO
            ],
            "nivel_aluno_csp": NIVEL_ALUNO_CSP,
            "resultado": {str(k): v for k, v in snapshot.items()},
        }, indent=2, ensure_ascii=False))
        print(f"Snapshot persistido em {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
