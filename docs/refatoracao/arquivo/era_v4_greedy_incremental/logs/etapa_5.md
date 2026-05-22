# Etapa 5 — Consolidação do `_buscar_candidato` em sistema de score

**Branch**: `refator-gerador` · **Sub-PRs**: 5.1 (puro + harness baseline) + 5.2 (integração softmax + snapshots regenerados) + 5.3 (cleanup two-pass + log + guia)

## O que foi feito

- **Sub-PR 5.1** — `PESOS_SCORE_PAREAMENTO`, `SOFTMAX_TOP_K=3`, `SOFTMAX_TEMPERATURA=200` adicionados como constantes hardcoded no topo do módulo (após `GRUPO_MUSCULAR_PADRAO`, padrão consistente com `ANCORAS_POR_*` da Etapa 3). Função `_score_pareamento(candidato, bloco_atual, evitar_agonistas)` standalone, não chamada — deixa terreno preparado pra integração em 5.2 sem mudar comportamento. Testes em `tests/test_score_pareamento.py` (21 puros) cobrem cada componente isolado, aditividade, regra anti-uni refinada, edge case de bloco vazio, e o caso clínico real do problema 6 (V-Up Uni + Tríceps Uni vs Hollow Hold). Harness `tools/medir_entropia_pareamentos.py` mede entropia de Shannon das duplas em N=100 iterações × 2 configs representativas; baseline pré-refator capturado em `etapa_5_baseline.json`.

- **Sub-PR 5.2** — `_buscar_candidato` refatorado: cascata determinística de 16 combinações geo×sub substituída por `_score_pareamento` + softmax top-K=3 com `random.choices(weights=...)`. Filtros hard (cargas, fadiga) continuam em `pode_adicionar_ao_bloco`; o second-pass de detecção `relaxado_carga` em `montar_blocos` continua funcionando inalterado (chama `_buscar_candidato` com `cargas_config=None` quando há vazio). 10 dos 13 snapshots de regressão regenerados com diagnóstico individual em `snapshots_diff_etapa5.md` e aprovação clínica do usuário; 3 snapshots ficaram estáveis (configs com pool naturalmente pequeno no top-K). Teste `test_v_up_uni_pareia_com_triceps_uni_nao_com_hollow` convertido de `xfail strict` para must-pass. Teste `test_filtro_carga_realmente_dissolve_par_conhecido` atualizado com novo par violador HIB2 sob seed=1 (Lev. Terra Sumô + Remada Baixa Aberta).

- **Sub-PR 5.3** — Cleanup: removido two-pass de `montar_blocos` (linhas pré-cleanup 1077-1097) e parâmetros redundantes da assinatura de `_buscar_candidato` (`regioes`, `padroes`, `evitar_unilateral`). Variáveis locais `regioes_no_bloco` / `padroes_no_bloco` em `montar_blocos` removidas (eram só pra passar à função). Docstring de `montar_blocos` atualizada pra refletir o novo comportamento (score em vez de cascata). 13 snapshots permanecem estáveis após cleanup (two-pass já era no-op desde 5.2 porque `evitar_unilateral` não fazia nada).

## Pesos finais do score

| Componente | Peso | Quando aplica |
|---|---:|---|
| `regiao_diff` | +1000 | candidato em região diferente do bloco |
| `padrao_diff` | +100 | candidato em padrão diferente |
| `nao_agonista` | +50 | grupo músculo-funcional diferente (só se `evitar_agonistas=True`) |
| `composto` | +25 | candidato com purpose composto/explosivo |
| `anti_uni_mesmo_grupo` | -75 | par uni-uni, mesmo grupo (ex: 2 squats unilaterais) |
| `anti_uni_diff_grupo` | -10 | par uni-uni, grupos diferentes (ex: V-Up Uni + Tríceps Uni) |

Hierarquia mantém ordem da cascata anterior — cada degrau é ~1 ordem de magnitude maior que o próximo, evitando compensações cruzadas (não dá pra somar 10× não-agonista pra superar 1× região diferente).

## K e função de temperatura

- **K = 3** — top-3 candidatos vão pra softmax. Pool em mesma tier costuma ter scores próximos → top-3 dá variedade real sem arriscar pegar candidato de tier inferior. Fácil escalar pra 5 num sub-PR pequeno se entropia ficar baixa demais.
- **Softmax exponencial T=200, normalizada por max**: `exp((s - max_s) / T) / sum(...)`. Com T=200 (~1/5 do peso de regiao_diff): top-K dentro do mesmo tier (gap < 50) distribui ~uniforme; top-1 P1 + top-3 P2 (gap > 1000) → top-1 domina (~99%). **Desejado**: amostragem dentro do mesmo tier, não entre tiers diferentes.

## Resultado do caso `v_up_uni_pair`

Caso clínico real do `memoria_projeto.md` problema 6 (V-Up Uni + Tríceps Uni Polia + Hollow Hold pareando subótimo) **resolvido por margem larga**:

| Métrica | Pré-Etapa 5 | Pós-Etapa 5 |
|---|---:|---:|
| Pareamento V-Up Uni + Tríceps Uni Polia (top-1) | 15% | **42.5%** |
| Tríceps Uni Polia SOLO (top-1) | 27.5% | **sumiu do top-5** |
| Pareamento V-Up + Hollow Hold | dominante | residual |

Teste `test_v_up_uni_pareia_com_triceps_uni_nao_com_hollow` (50 seeds) tinha critério ≥ 50% — passa com folga.

## Métricas de entropia pré vs pós (config representativas)

Harness `tools/medir_entropia_pareamentos.py`, N=100 iterações.

### `core_3_uni_pair` — caso V-Up Uni

| Métrica | Pré | Pós | Δ |
|---|---:|---:|---:|
| Total de blocos | 200 | 200 | — |
| Blocos únicos | 16 | 17 | +1 |
| Entropia (bits) | 3.5334 | 3.1825 | -0.35 |
| Top-1 | Tríceps SOLO 27.5% | V-Up + Tríceps **42.5%** | inversão |

A entropia caiu (mais concentrado) **e isso é o resultado desejado** — concentrar no pareamento clinicamente correto, não dispersar entre soluções subótimas. A métrica simplista "entropia maior é melhor" falha aqui; o que importa é a forma da distribuição (top-1 = pareamento ideal, em vez de SOLO).

### `lower_4_upper_3` — config multi-região

| Métrica | Pré | Pós | Δ |
|---|---:|---:|---:|
| Total de blocos | 401 | 401 | — |
| Blocos únicos | 243 | 263 | **+20 (+8%)** |
| Entropia (bits) | 7.5652 | 7.5531 | -0.01 |

Mais variedade global (20 pareamentos únicos a mais) com entropia praticamente idêntica. Variabilidade ganhou, sem dispersar pra pareamentos ruins.

## Surpresas / desvios do plano

1. **Snapshots estáveis em 5.3**: o plano previa que remover o two-pass poderia mudar alguns snapshots (porque a 1ª chamada com `evitar_unilateral=True` mudava a sequência de chamadas a `random.choices`). Não mudou nada — porque na 5.2 já tinha sido tornada no-op (passar `evitar_unilateral=True` já não fazia nada). Cleanup foi puramente cosmético. **OK** — confirma que a 5.2 cobriu tudo na prática.

2. **Trade-off em `test_upper_3_lower_2_core_2_3treinos_seed42`**: V-Up Uni "puxou" Barra Fixa via score (+1140 vs Goblet+Barra Fixa +1175 — gap pequeno o bastante pra softmax escolher V-Up). Agachamento Goblet (composto pesado) virou solo. **Decisão clínica do usuário**: aceitar como variação válida; observação registrada sobre revisitar curadoria de `carga_core` / `carga_lombar` de Barra Fixa numa próxima revisão de banco — **Barra Fixa demanda mais core e flexores de quadril do que está cadastrado hoje**, então o filtro hard de cargas (Etapa 4) deveria estar bloqueando essa combinação. Diagnóstico completo em `snapshots_diff_etapa5.md`.

3. **Test `test_filtro_carga_realmente_dissolve_par_conhecido` (Etapa 4) precisou atualizar**: com a softmax mudando o pareamento em seed=1, o par antigo "Hiperextensão 45° + Remada Baixa Aberta" não emerge mais — substituído por "Lev. Terra Sumô + Remada Baixa Aberta" (que viola **2 dimensões** HIB2: grip 3+3=6 e lombar 3+2=5). A pré-condição do teste continua robusta; o filtro continua bloqueando o par identificado.

4. **3 dos 13 snapshots ficaram estáveis** (não regen): `test_perna_posterior_2x2treinos_seed5`, `test_core_3x1treino_seed17`, `test_triceps_2_filtro_familia_relax_seed23`. Configs com pool naturalmente pequeno no top-K — softmax converge no mesmo candidato que a cascata. Boa indicação de que o refator não introduz aleatoriedade onde não há espaço pra ela.

## Pontos abertos pra etapas futuras

- **Etapa 7 (penalidades multi-dimensionais)**: revisitar se cargas viram penalty contínuo no score ou continuam HARD (decisão Etapa 5: continuam HARD; memória `feedback_etapa4_cargas_hard_filter.md` registrada). Quando contextos INTRA / INTER / HISTÓRICO chegarem, reavaliar se faz sentido unificar tudo em um score só.
- **UI de variabilidade**: `PESOS_SCORE_PAREAMENTO` e `SOFTMAX_TEMPERATURA` ficam hardcoded; quando UI da Etapa 7 expor controles ("variabilidade no treino: baixa/média/alta"), promover a parâmetros passáveis (igual `cargas_config`).
- **K dinâmico opcional**: K=3 fixo. Slicing `top = candidatos[:SOFTMAX_TOP_K]` já degrada graciosamente quando há menos de 3 candidatos (top fica menor). Se simulações futuras mostrarem que K=3 limita variabilidade em pools grandes, fácil escalar.
- **Curadoria de cargas de Barra Fixa**: usuário observou que a `carga_core` e `carga_lombar` no banco subestimam a demanda real (flexores de quadril, core). Revisitar o cadastro pra que o filtro hard HIB2 bloqueie pares Barra Fixa + V-Up Uni / Hollow Hold / Dragon Flag. Não é trabalho da Etapa 5; trabalho de curadoria do banco.
- **Ajuste de pesos opcional**: se em produção o caso "V-Up puxa composto upper deixando outro composto solo" aparecer com frequência indesejável, opções de calibração (em ordem de invasividade):
  1. Aumentar `composto` de +25 → +50 (composto+composto vira mais distante)
  2. Reduzir T de 200 → 100 (softmax mais conservadora — top-1 domina mais)
  3. Aumentar `anti_uni_diff_grupo` de -10 → -25 (desincentiva mais a "puxada" do uni)
- **Métrica de entropia**: simplificada (Shannon over tuplas de bloco). Pode evoluir pra "entropia per-anchor" ou "dispersão dimensional" se necessário pra estudos mais finos. Por enquanto, cobre o que precisamos.

## Critério de "feito" — checklist

- [x] Sub-PR 5.1 — `PESOS_SCORE_PAREAMENTO` + `SOFTMAX_TOP_K`/`TEMPERATURA` + `_score_pareamento` puro standalone
- [x] Sub-PR 5.1 — `tests/test_score_pareamento.py` 21 testes puros, 0 falhas
- [x] Sub-PR 5.1 — `tools/medir_entropia_pareamentos.py` + `etapa_5_baseline.json`
- [x] Sub-PR 5.2 — `_buscar_candidato` substituído por scoring + softmax top-K=3 T=200
- [x] Sub-PR 5.2 — 10 snapshots regenerados com diagnóstico individual e aprovação clínica
- [x] Sub-PR 5.2 — `test_v_up_uni_pareia_com_triceps_uni_nao_com_hollow` xfail → must-pass
- [x] Sub-PR 5.2 — `test_filtro_carga_realmente_dissolve_par_conhecido` atualizado com novo par
- [x] Sub-PR 5.2 — `etapa_5_pos.json` capturado pra comparação
- [x] Sub-PR 5.3 — two-pass removido em `montar_blocos`
- [x] Sub-PR 5.3 — assinatura de `_buscar_candidato` simplificada (removidos `regioes`, `padroes`, `evitar_unilateral`)
- [x] `pytest` em < 30s, 0 falhas (atual: 169 passed, 1 skipped, 1.69s)
- [x] Caso V-Up Uni: 42.5% top-1 (target ≥ 50% no teste das 50 seeds, atingido)
- [x] Entropia pós-refator capturada e comparada com baseline
- [x] `docs/refatoracao/logs/etapa_5.md` escrito
- [x] `docs/refatoracao/logs/snapshots_diff_etapa5.md` escrito
- [x] Header de progresso do `guia_refatoracao_v4.md` atualizado
