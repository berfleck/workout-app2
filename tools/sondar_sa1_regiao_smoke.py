"""Smoke: confirma se regressao 'padrao repetido' aparece em demanda regiao.

Roda `regiao lower(4)` (1 vaga sobrando apos 3 obrigatorias) 20 seeds.
Mede: a vaga sobrando vira knee_flexion (alvo S-A1) ou hinge (repeticao)?
"""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gerador_csp import ConfigVariedade, carregar_banco_ativo, gerar_rotina_csp


def sondar_lower4(peso_sa1: int, peso_sa1_repet: int = 0,
                  n_seeds: int = 20) -> Counter:
    banco = carregar_banco_ativo()
    contador: Counter = Counter()
    for seed in range(n_seeds):
        r = gerar_rotina_csp(
            [[("regiao", "lower", 4)]],
            banco,
            nivel_aluno=3,
            seed=seed,
            variedade=ConfigVariedade(),
            peso_evitar_agonistas=10,
            tamanho_preferido=2,
            peso_tamanho_bloco=5,
            relaxar_familia=True,
            peso_sa1=peso_sa1,
            peso_sa1_repet=peso_sa1_repet,
        )
        if not r.get("viavel"):
            continue
        treino = r["treinos"][0]["blocos"]
        padroes = []
        for bloco in treino:
            for ex in bloco:
                padroes.append(ex.padrao)
        chave = "+".join(sorted(padroes))
        contador[chave] += 1
    return contador


for p, pr in [(0, 0), (12, 0), (12, 10)]:
    print(f"\n--- regiao lower(4), peso_sa1={p}, peso_sa1_repet={pr}, n=20 ---")
    c = sondar_lower4(p, pr)
    for combo, qtd in sorted(c.items(), key=lambda kv: -kv[1]):
        print(f"  {combo}: {qtd}/20 ({100*qtd/20:.0f}%)")
