# Viés de distribuição — bookmark pra implementação

Diagnóstico feito em 2026-05-17 a partir de 2 rotinas reais (Bernardo + Jose, configs idênticas: `upper(2) + lower(2) + core(2)`, 2 treinos).

## Problemas

1. **Phase lock subregião** — PA sempre em T1, PP em T2 (lower); peito sempre em T2 (upper). Determinístico, reproduzível.
2. **Greedy de blocos** — 2 core_iso no mesmo bloco quando existia pareamento 3×P1 perfeito.

Causa-raiz comum: cycling determinístico sobre estruturas simétricas → distribuição não-uniforme.

**Fora de escopo deste .md** (frentes paralelas):
- Mono-ex bias (Pallof concentrado) — resolvido em 2026-05-17 via B escopada (commit 8715910, mergeado em main)
- Iso/dyn leak no selector (Crunch em demanda core_isometrico) — frente separada, .md próprio quando atacar

## Solução 1 — Phase lock: Bresenham por chave

Substituir o algoritmo de `_distribuir_quotas_entre_treinos` em [gerador_treino.py:345-411](gerador_treino.py:345).

Algoritmo novo:
```
ordenar chaves por quota descendente (tiebreak alfabético)
acumulador = 0
para cada chave:
    offset = acumulador mod n_treinos
    distribuir suas vagas via round-robin começando em offset
    pular treinos com capacidade esgotada
    acumulador += quota da chave
```

Validado mentalmente nos 4 casos críticos (lower×2, upper×2, core×2, lower×4). Todos balanceiam sem aleatoriedade.

Tamanho: ~20 linhas. Mantém determinismo (auditável).

## Solução 2 — Greedy de blocos: matching enumerativo

Em `montar_blocos` ([gerador_treino.py:1163+](gerador_treino.py:1163)): quando `tamanho_bloco=2`, enumerar todos emparelhamentos perfeitos e escolher o de maior soma de qualidade.

- 6 ex → 15 emparelhamentos
- 8 ex → 105
- 10 ex → 945 (limite prático, ainda trivial)

Pra `tamanho_bloco=3`: manter greedy atual (uso raro no app).

**Função objetivo precisa ser multi-dimensional, não só P1-P4:**
```
score_par = base_P1_P4 (regiao_diff + padrao_diff)
          - penalty_dois_unilaterais
          - penalty_mesmo_purpose (ex: 2 explosivos juntos)
          + bonus_complementaridade (opcional)
```

Reusar `anti_uni_mesmo_grupo` que já existe na config de pesos da Etapa 7 (Seção 8.15.9). Começar conservador (P1-P4 + anti-uni), expandir depois se necessário.

**Caso de teste alvo**: Jose T1 com 3 uni + 3 bi (Desenv Landmine, Slide Board, V-Up Uni vs Barra Isom, Goblet, Russian Twist). Ótimo é 3×P1 com cada uni pareado com bi.

Tamanho: ~40-60 linhas. Ótimo global garantido para o pool dado.

**Limitação conhecida**: quando o pool é estruturalmente impossível (ex: 4 uni + 2 bi em 3 blocos), o matching faz o melhor possível mas não pode evitar 1 bloco uni+uni. Resolver isso exigiria Camada 3.5 (substituição com banco) — fora do escopo atual.

## Ordem de execução

1. Phase lock
2. Matching de blocos
3. Rodar pytest + harness — regenerar snapshots quebrados (esperado, 5-15 deles)
4. Gerar 5-10 rotinas reais (Bernardo, Jose, variações de demanda) e validar visualmente

## Restrições

- Não introduzir aleatoriedade (manter algoritmo auditável)
- Não mexer em pesos, âncoras, ou quotas (só na **atribuição** delas)
- Defaults da Etapa 7.1 dos pesos de proximidade ficam intocados
