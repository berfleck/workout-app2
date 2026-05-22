# Etapa 3 — Âncoras protegidas (região e subregião)

**Branch**: `refator-gerador` · **Sub-PRs**: 1 (constantes+`calcular_quotas`) + 2 (integração+hierarquia+standalone+snapshots) + 3 (avisos+métricas+log)

## O que foi feito

- Adicionadas constantes `ANCORAS_POR_REGIAO` (upper, lower, core) e `ANCORAS_POR_SUBREGIAO` (peito, costas, ombro, perna_anterior, perna_posterior, panturrilha) com pesos clínicos e flag `obrigatoria`. Validação no import via `_validar_ancoras()`.
- Implementada [calcular_quotas](../../../gerador_treino.py) — Hamilton's Largest Remainder Method com tie-break (obrigatórias > peso maior > ordem definição). Vagas < num_obrigatórias → sorteio + aviso `ancora_nao_cumprida`. Mínimos contam na proporção (`peito(2)` peso 3:2 → 1+1).
- Helpers `_quotas_de_regiao` e `_quotas_de_subregiao` traduzem nome de escopo em chamada a `calcular_quotas` com âncoras corretas.
- `_distribuir_quotas_entre_treinos` implementa hierarquia treino > rotina via round-robin sobre fila intercalada por peso. Minimiza concentração de déficit (`perna_anterior(2)×3` com bi:4 uni:2 → cada treino tem ≥1 uni quando possível, em vez de concentrar tudo em T3).
- `_decompor_demanda_regiao` e `_decompor_demanda_subregiao` reescritas pra usar quotas com pesos. Filtro pré-quotas em região preserva regra Etapa 2 D2.1 (acessórias só competem se qtd > 2 × num_obrigatórias). Subregiões/regiões sem âncoras (cardio, core_dinamico, core_isometrico, bracos, adutores) caem em fallback Etapa 2.
- `pre_alocar_rotina` ganha Etapa A.0 (agregação de demandas idênticas across treinos): demandas iguais nos N treinos têm quota calculada UMA VEZ no nível rotina e redistribuída entre treinos, garantindo coerência clínica em rotinas multi-treino. Demandas com travado entram no caminho per-treino (constraint extra não agrega cleanly).
- Caminho standalone (`gerar_sessao_por_demandas` chamada por `/regerar`) também aplica âncoras — consistência clínica.
- `quota_composta` e `requer_composto` aposentados: a regra 60% emerge dos pesos das âncoras subregião (empurrar_compostos:3 vs empurrar_isolados:2 dá ~60% composto em peito). `PROPORCAO_COMPOSTOS` mantida como DEPRECATED, usada APENAS no fallback de regiões sem âncoras.
- Avisos novos:
  - `ancora_nao_cumprida` — vagas < num_obrigatorias (ex: `costas(1)` com remadas+puxadas obrigatórias).
  - `ancora_sem_candidatos` — slot de padrão obrigatório fica sem pool no banco filtrado (ex: equipamentos bloqueados zeram hinge em `perna_posterior(6)`).
  - `proporcao_desviada` — estrutura definida; teste skipado por falta de caso natural.
- 33 testes novos em [tests/test_ancoras.py](../../../tests/test_ancoras.py) (puros, sem banco) + 1 em [tests/test_ancoras_avisos.py](../../../tests/test_ancoras_avisos.py).
- 4 xfail strict da Etapa 3 promovidos pra passes:
  - `test_upper_3x2treinos_tem_composto_de_cada_ancora`
  - `test_perna_anterior_3x3_respeita_quota_3_2`
  - `test_perna_posterior_6_distribui_hinge_kneeflex_abducao_3_2_1`
  - `test_costas_1x1_gera_aviso_ancora_nao_cumprida`
- 8 snapshots de regressão regenerados com diagnóstico individual aprovado pelo usuário (ver [snapshots_diff_etapa3.md](snapshots_diff_etapa3.md)).

## Decisões arquiteturais consolidadas

### Pesos finais (não alterados durante implementação)

```python
ANCORAS_POR_REGIAO:
  upper: peito:2 obrig, costas:2 obrig, ombro:1 obrig
  lower: perna_anterior:2 obrig, perna_posterior:2 obrig, panturrilha:1 NÃO-obrig
  core: core_dinamico:1 NÃO-obrig, core_isometrico:1 NÃO-obrig

ANCORAS_POR_SUBREGIAO:
  peito: empurrar_compostos:3 obrig, empurrar_isolados:2 NÃO-obrig
  costas: remadas:2 obrig, puxadas:2 obrig
  ombro: ombro_composto:3 obrig, ombro_isolado:2 NÃO-obrig, posterior_ombro:1 NÃO-obrig
  perna_anterior: squat_bilateral:3 obrig, squat_unilateral:2 NÃO-obrig
  perna_posterior: hinge:3 obrig, knee_flexion:2 NÃO-obrig, abduction:1 NÃO-obrig
  panturrilha: flexao_plantar:1 obrig
```

### Hamilton's Largest Remainder + tie-break

- Empate em resto: obrigatória > peso maior > ordem definição (estável).
- Mínimos contam na proporção (não são adicionais). `peito(2)` com 3:2 → 1 comp + 1 iso (não 2 comp + 0 iso).
- Hamilton puro **não garante** obrigatórias quando uma não-obrigatória tem peso muito superior (ratio > 3:1). Os pesos clínicos definidos (ratio máx 3:1) são seguros — `test_quota_invariante_obrigatoria_cumprida_em_ancoras_reais` itera todas as constantes reais e prova.

### Vagas < num_obrigatórias

Sorteio uniforme entre obrigatórias com seed (preserva variabilidade entre rotinas, evita viés sistemático). Obrigatórias não sorteadas viram aviso `ancora_nao_cumprida`. Caso real: `costas(1)`.

### Filtro pré-quotas em região (preserva D2.1 da Etapa 2)

Acessórias (`obrigatoria=False`) só competem se `qtd > 2 × num_obrigatorias`. Garante que `lower(4)` continua 2:2:0 (sem panturrilha) em vez de 2:1:1 (Hamilton puro). Travado em acessória força inclusão mesmo em qtd pequena.

### Hierarquia treino > rotina

Demandas idênticas (mesmo `nivel/escopo/qtd`) em treinos diferentes são **agregadas**: quota calculada UMA VEZ sobre `qtd × n_treinos`, depois redistribuída via round-robin sobre fila intercalada por peso. Resultado em `perna_anterior(3) × 3`: bi:5 + uni:4 globais, distribuídos como 2:1 / 2:1 / 1:2 garantindo cada treino tem ≥1 bi e ≥1 uni. Demandas com travado entram no caminho per-treino (constraint não agrega cleanly).

### Standalone /regerar

Aplica âncoras Etapa 3 (consistência clínica). `/regerar` de 1 treino respeita as mesmas proporções que o gerador principal pra mesma demanda. Fallback (regiões sem âncoras: cardio) preserva PROPORCAO_COMPOSTOS legado.

### `proporcao_desviada` (R4)

Estrutura prevista; teste skipado por falta de caso natural sem mock. Quando o relax muda a quota efetiva, o aviso deve emitir. Implementação adiada pra etapa futura quando caso natural aparecer.

### Subregiões sem âncoras (R5)

`core_dinamico`, `core_isometrico`, `bracos`, `adutores` caem em fallback Etapa 2 (cycling uniforme via `_decompor_demanda_*`). Quando padrões internos forem definidos no futuro, basta popular `ANCORAS_POR_SUBREGIAO` e o mecanismo passa a operar sobre eles.

## Surpresas / desvios do plano

1. **Adutores não entra em `ANCORAS_POR_REGIAO["lower"]`** (decisão clínica do usuário: "quem quer adutor pede explicitamente"). Mudança vs Etapa 2 onde adutores aparecia via fallback essencial/acessório em `lower(6)`. Teste `test_pre_alocar_lower_6_proporcional` atualizado pra refletir nova realidade (3:2:1 sem adutores em vez de 2:2:1:1).

2. **Hamilton puro não garante obrigatórias em todos os pesos.** Caso construído com ratio 5:1 (peso construído pra teste de invariante) violou. Os pesos clínicos definidos são seguros — invariante validado iterativamente sobre `ANCORAS_POR_REGIAO` e `ANCORAS_POR_SUBREGIAO`. Documentado no docstring de `calcular_quotas`.

3. **Demandas com travado não agregam.** Tentativas iniciais de agregar com travado forçando inclusão extra ficaram complicadas pela diferença de constraints por treino. Decisão: travado entra no caminho per-treino (mais simples, comportamento ainda correto pq caso é raro).

4. **`upper(N)` com filtro pré-quotas em qtd≤6 produz aviso `ancora_nao_cumprida`.** Em `upper(3) × 2 = 6 vagas`: filtro mantém só obrigatórias (qtd=3≤2×3=6 — boundary), Hamilton 6×(2/5,2/5,1/5)=(2.4,2.4,1.2)→(3,2,1). Mas se o usuário pedir 3 vagas POR TREINO esperando peito+costas+ombro um de cada, a quota global pode dar 3 peito + 2 costas + 1 ombro (concentra peito). O aviso sinaliza explicitamente. Comportamento correto, mas vale revisitar pesos se o efeito for indesejado clinicamente em produção.

## Pontos abertos pra etapas futuras

- **`proporcao_desviada` validado em caso natural**: implementação minimalista pode ser adicionada, mas teste só será confiável quando aparecer um cenário real onde estrito esgota família e relax substitui por outro padrão. Adiado.
- **UI dos avisos `ancora_*`**: mistura visualmente com `incompleta` no modal. R3 da Etapa 2 já é ponto aberto; Etapa 3 adiciona 2 tipos novos. Coordenar com Etapa 4 ou refator de UX dedicado.
- **Pesos clínicos**: `upper(3) × 2` revela tensão entre peso de ombro (1) e desejo clínico de cobertura uniforme. Se prática mostrar concentração indesejada em peito, considerar revisar pra `upper: peito:2, costas:2, ombro:2`.
- **Padrões em core_dinamico e core_isometrico**: definir padrões internos pra ativar âncoras subregião nesse caso. Hoje cai em fallback Etapa 2.
- **Performance**: 2.24s pra 4000 simulações (~0.56ms/sim). Caching de pools NÃO foi necessário.
- **`/regerar` 1 treino sem agregação**: by design (regerar é cirúrgico). Continua aplicando âncoras mas sem hierarquia treino>rotina (não há outros treinos pra agregar). Documentado.

## Métricas pós-Etapa 3 (4 configs × 1000 iter)

Captura completa em [baseline_pos_etapa3.json](baseline_pos_etapa3.json). Tempo total: 2.24s.

### A — `lower(4) × 3 treinos` (regressão Etapa 2)

| Métrica | Pré-Etapa 2 | Pós-Etapa 2 | Pós-Etapa 3 | Direção |
|---|---|---|---|---|
| razão post/ant (mediana) | 1.00 | 1.00 | **1.00** | mantida |
| razão post/ant (média) | 0.94 | 1.00 | **1.00** | mantida |
| freq adut+pant | 18.3% | 0.0% | **0.0%** | mantida |
| dist perna_anterior bi:uni | — | (banco) | **50%:50%** | quota Hamilton |
| dist perna_posterior hinge:knee | — | — | **50%:50%** | qtd=2 com pesos 3:2 dá Hamilton (1,1,0) |

### B — `perna_posterior(6) × 1 treino` (caso âncora subregião 3:2:1)

| Métrica | Pré-Etapa 3 | Pós-Etapa 3 | Direção |
|---|---|---|---|
| dist hinge:knee_flex:abduction | 2:2:2 (cycling Etapa 2) | **3:2:1** (Hamilton puro) | **objetivo cumprido** |

### C — `upper(3) × 2 treinos` (caso âncora região + composto de cada)

| Métrica | Pré-Etapa 2 | Pós-Etapa 2 | Pós-Etapa 3 | Direção |
|---|---|---|---|---|
| cobertura compostos peito | 100% | 96.2% | **100%** | recuperada |
| cobertura compostos costas | 100% | 100% | **100%** | mantida |
| cobertura compostos ombro | 100% | 84.3% | **100%** | recuperada |
| dist peito comp:iso | — | — | **67%:33%** | peso 3:2 emerge |
| dist costas remadas:puxadas | — | — | **49%:51%** | paridade preservada |
| dist ombro composto:iso:posterior | — | — | **100%:0%:0%** | peso 3:2:1 com filtro pré-quotas em qtd=3≤6 só tem obrig (composto) |

### D — `perna_anterior(3) × 3 treinos` (caso quota proporcional 3:2)

| Métrica | Pré-Etapa 3 | Pós-Etapa 3 | Direção |
|---|---|---|---|
| dist bi:uni | 33%:67% (banco 6:11) | **56%:44%** (Hamilton 5:4) | **objetivo cumprido** |
| razão bi:uni | 0.50 | **1.25** | bate o teste 1.2-1.8 |

### Performance

| Métrica | Pós-Etapa 2 | Pós-Etapa 3 | Direção |
|---|---|---|---|
| Tempo 4000 sims | — | **2.24s** | < 60s ✓ alvo |
| ms/sim | ~0.75 (3000 iter) | ~0.56 (4000 iter) | Caching NÃO necessário |

## Snapshots regenerados — diagnóstico individual

Diff completo + diagnóstico clínico em [snapshots_diff_etapa3.md](snapshots_diff_etapa3.md). Resumo:

| # | Snapshot | Coerente | Observação |
|---|----------|----------|-----------|
| 1 | upper_3_lower_2_core_2_3treinos_seed42 | sim | Distribuição peito/costas/ombro pelos pesos |
| 2 | upper_3x2treinos_seed11 | sim | **Resolve crossover_sentado_only** |
| 3 | perna_anterior_3x3treinos_seed3 | sim | **Resolve perna_anterior_sem_isolado** (5:4 em vez de 6:3) |
| 4 | perna_posterior_2x2treinos_seed5 | sim | Distribuição clínica respeitada |
| 5 | costas_4x1treino_seed9 | sim | Paridade 2:2 preservada |
| 6 | peito_3x2treinos_seed13 | sim | Composto:iso = 4:2 (peso 3:2) |
| 7 | core_3x1treino_seed17 | sim | Sem âncoras em core_* (fallback) |
| 8 | max_complexidade_baixa_seed29 | sim | Aviso `ancora_nao_cumprida` por cx baixa |

Cobertura clínica preservada em 8/8 cenários. Aprovação caso a caso recebida.

## Critério de "feito" — checklist

- [x] Sub-PR 1 — constantes + `calcular_quotas` + helpers + `_distribuir_quotas_entre_treinos`
- [x] Sub-PR 2 — `_decompor_demanda_*` com quotas + hierarquia treino>rotina + standalone + 8 snapshots regenerados
- [x] Sub-PR 3 — avisos `ancora_nao_cumprida` + `ancora_sem_candidatos` + métricas + log
- [x] `pytest` em < 30s, 0 falhas (atual: 121 passed, 1 skipped, 1 xfailed em 2.42s)
- [x] Harness 4000 iter × 4 configs em < 60s (atual: 2.24s)
- [x] 4 testes XFAIL strict da Etapa 3 promovidos pra passes
- [x] User aprovou regeneração dos 8 snapshots
- [x] Caso real `crossover_sentado_only` regenerado com composto de peito presente
- [x] Caso real `perna_anterior_sem_isolado` regenerado com distribuição respeitando quota
- [x] `docs/refatoracao/logs/etapa_3.md` escrito
- [x] Atualização do guia v4 (header de progresso)
