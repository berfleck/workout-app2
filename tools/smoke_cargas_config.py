"""Smoke E2E da Fatia 4.E cargas — `cargas_config` via motor CSP.

Cobre o caminho que o adapter `/treino/<t>/regerar` executa em produção,
sem precisar do servidor Flask ou UI clicável. Modo padrão da rota é
`ConfigVariedade()` (Frente B).

Cenários cobertos (10 runs cada pra estabilidade estatística):
1. Filtro OFF (regressão pré-4.E cargas).
2. Filtro permissivo (thr={'grip':6,'lombar':6,'core':6}): poucos pares
   violam; blocos limpos sem aviso.
3. Filtro restritivo (thr={'grip':4,'lombar':4,'core':4}): vários pares
   violam; alguns blocos desligam OR motor faz mais solos.
4. Filtro muito restritivo (thr={'grip':3,'lombar':3,'core':3}): muitos
   blocos desligam OR motor empurra pra solos com peso de tamanho ativo.
5. Filtro + travado heavy: travado mantém + non-travado adapta;
   par travado-travado violador emite aviso.

Output: tabela com contagem de blocos desligados (filtro OFF por bloco) e
nº de avisos `relaxado_carga` emitidos.

Roda standalone:
    python tools/smoke_cargas_config.py
"""
from __future__ import annotations

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
    gerar_treino_csp,
)


def _ex_por_nome(banco, nome):
    for e in banco:
        if e.nome == nome:
            return e
    raise ValueError(f"{nome} não está no banco")


def _stat(banco, demandas, *, nivel, cargas_config, travados=None,
          tam_pref=2, peso_tam=5, peso_evitar_agon=0, n_runs=10, label=""):
    print(f"\n=== {label} ===")
    print(f"  Demandas: {demandas}")
    print(f"  Nível: {nivel} | cargas_config: {cargas_config}")
    if travados:
        print(f"  Travados: {[t.nome for t in travados]}")
    print(f"  Tam pref: {tam_pref} (peso={peso_tam}) | "
          f"evitar_agon: {peso_evitar_agon}")
    total_blocos = 0
    total_avisos = 0
    avisos_por_dim = Counter()
    runs_com_aviso = 0
    n_exs_dist: Counter = Counter()
    blocos_dist: Counter = Counter()
    primeiro_print = True
    for i in range(n_runs):
        seed = random.randint(0, 2**31 - 1)
        r = gerar_treino_csp(
            demandas, banco, nivel_aluno=nivel,
            seed=seed,
            variedade=ConfigVariedade(),
            cargas_config=cargas_config,
            travados=travados,
            tamanho_preferido=tam_pref,
            peso_tamanho_bloco=peso_tam,
            peso_evitar_agonistas=peso_evitar_agon,
        )
        if not r["viavel"]:
            print(f"  [FAIL] Run {i+1}: inviável (status={r['status']})")
            continue
        nomes = [e.nome for g in r["grupos"] for e in g["exercicios"]]
        blocos = r.get("blocos", [])
        n_exs_dist[len(nomes)] += 1
        blocos_dist[len(blocos)] += 1
        total_blocos += len(blocos)
        avisos = r.get("avisos_carga", [])
        total_avisos += len(avisos)
        if avisos:
            runs_com_aviso += 1
        for av in avisos:
            avisos_por_dim[av["dimensao"]] += 1
        if primeiro_print:
            print(f"  [Run 1] Exs ({len(nomes)}): {nomes}")
            print(f"  [Run 1] Blocos ({len(blocos)}): "
                  f"{[[e.nome for e in b] for b in blocos]}")
            if avisos:
                for av in avisos:
                    print(f"  [Run 1] Aviso: bloco {av['bloco_idx']}, "
                          f"{av['exercicio']} + {av['par_bloqueado']}, "
                          f"{av['dimensao']} {av['soma']}/{av['threshold']}")
            primeiro_print = False
    print(f"  Distribuição n_exs: {dict(n_exs_dist)}")
    print(f"  Distribuição n_blocos: {dict(blocos_dist)}")
    print(f"  Runs com aviso `relaxado_carga`: {runs_com_aviso}/{n_runs}")
    print(f"  Total avisos: {total_avisos}")
    if avisos_por_dim:
        print(f"  Avisos por dim: {dict(avisos_por_dim)}")


def main():
    banco = carregar_banco_ativo()
    lev_terra = _ex_por_nome(banco, "Lev. Terra")
    stiff = _ex_por_nome(banco, "Stiff Barra Livre")

    print("="*70)
    print("Smoke Fatia 4.E cargas — `cargas_config` via motor CSP")
    print("="*70)

    # 1. Filtro OFF (regressão pré-4.E cargas).
    _stat(
        banco,
        [("subregiao", "peito", 2), ("subregiao", "costas", 2)],
        nivel=3, cargas_config=None,
        label="1. Filtro OFF (regressão pré-4.E cargas)",
    )

    # 2. Filtro permissivo: thr=6 (max possível na escala 1-3 é 6, beira).
    _stat(
        banco,
        [("subregiao", "peito", 2), ("subregiao", "costas", 2)],
        nivel=3, cargas_config={"grip": 6, "lombar": 6, "core": 6},
        label="2. Filtro permissivo (thr=6 em todas dims) — pouca pressão",
    )

    # 3. Filtro restritivo: thr=4. Pares heavy começam a violar.
    _stat(
        banco,
        [("subregiao", "peito", 2), ("subregiao", "costas", 2)],
        nivel=3, cargas_config={"grip": 4, "lombar": 4, "core": 4},
        label="3. Filtro restritivo (thr=4) — alguns pares violam",
    )

    # 4. Banco mini de costas + thr restritivo + bloco forçado (peso alto).
    #    Demanda costas(2) com H-R1 exigindo 1 puxada compound + 1 remada
    #    compound. Todos compound têm grip≥2; thr=4 vira inviável pra par
    #    em bloco compartilhado. Tam_pref=2 com peso alto força par.
    banco_costas = [e for e in banco if e.padrao in ("puxadas", "remadas")]
    _stat(
        banco_costas,
        [("subregiao", "costas", 2)],
        nivel=3, cargas_config={"grip": 4, "lombar": 4, "core": 4},
        tam_pref=2, peso_tam=10000,  # força par no mesmo bloco
        label="4. Banco mini costas + thr=4 + par forçado — inviável (avisos esperados)",
    )

    # 5. Filtro + 2 travados heavy: travado-travado violador emite aviso.
    _stat(
        banco,
        [("subregiao", "perna_posterior", 2)],
        nivel=3, cargas_config={"grip": 5, "lombar": 5, "core": 5},
        travados=[lev_terra, stiff],
        tam_pref=2, peso_tam=10000,  # força par no mesmo bloco
        label="5. Filtro + 2 travados heavy no mesmo bloco (par travado-travado)",
    )

    print("\n[OK] Smoke completo. Verifique que:")
    print("  - Cenário 1: 0 avisos (filtro OFF).")
    print("  - Cenário 2: poucos ou 0 avisos (filtro permissivo).")
    print("  - Cenário 3-4: avisos aparecem quando inviável.")
    print("  - Cenário 5: 10/10 runs com aviso (par travado-travado inevitável).")


if __name__ == "__main__":
    main()
