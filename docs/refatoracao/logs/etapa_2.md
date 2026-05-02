# Etapa 2 — Refatoração Nível 2 (pré-alocação global)

**Branch**: `refator-gerador` · **Sub-PRs**: 1 (isolada) + 2 (integração+snapshots) · **Sub-PR 3 (caching)**: não foi necessário (perf 2.24s pra 3000 simulações, alvo era < 60s).

## O que foi feito

- Adicionada Fase 0 do gerador (`pre_alocar_rotina` em [gerador_treino.py](../../../gerador_treino.py)) — aloca exercícios entre os N treinos da rotina antes de qualquer um ser montado, ordenando vagas por escassez (slots com poucos candidatos viáveis vão primeiro).
- `gerar_multiplos_treinos` orquestra Fase 0 → Fase 1 → Fase 2; templates legacy convertidos em demandas na borda externa via `_normalizar_config` (D4 opção C). `gerar_sessao` legado intocado (continua entry point pro `/regerar` via `app_flask.py`).
- `gerar_sessao_por_demandas` ganhou parâmetro `exercicios_pre_alocados` — quando preenchido, pula seleção e usa diretamente os exercícios alocados pela Fase 0.
- Decomposição em 2 níveis: região → subregião (essencial/acessório) → padrão (cycling 1-de-cada). Travado-aware em ambos os níveis (D3.1).
- Segundo passe de relax na Fase 0 quando `relaxar_familia=True` (cobre slots que o estrito não preencheu, propagando relaxados pra `Sessao.relaxados` + aviso `familia_repetida`).
- 24 testes novos em [tests/test_pre_alocacao.py](../../../tests/test_pre_alocacao.py); 12 snapshots de regressão regenerados com diagnóstico individual aprovado caso a caso (R7).

## Decisões arquiteturais consolidadas

### Métrica de escassez (D1.1)
Razão `n_candidatos / qtd_pedida` no **modo estrito** (família + nome bloqueados, filtros user aplicados). Ignora `relaxar_familia` (assume pior caso). Não há gate de razão ≤ 2 — o número é usado direto na ordenação.

### Granularidade do slot (D1.2)
1 vaga = 1 slot. Demandas decompostas em sub-demandas (subregião → padrão), e cada sub-demanda gera N slots granulares.

### Equilíbrio essencial/acessório (D2.1)
Estrutura nova `SUBREGIOES_POR_REGIAO`:
- `lower`: essenciais=[perna_anterior, perna_posterior], acessórias=[panturrilha, adutores]
- `upper`: essenciais=[peito, costas, ombro], acessórias=[]
- `core`: essenciais=[core_dinamico, core_isometrico], acessórias=[]

Regra: 1 de cada essencial → ciclar; acessórias só competem se `qtd > 2 × n_essenciais`. Quando `qtd < n_essenciais`, sortear `qtd` essenciais com seed.

Decomposição subregião → padrão segue padrão análogo: 1 de cada padrão → ciclar (preserva paridade que o `_selecionar_ciclando` legacy entregava — ex: costas(4) → 2 remadas + 2 puxadas, em vez de 3:1 puxando pra proporção do banco).

### Quota composto/isolado (D2.2)
60% compostos continua **global por demanda região** (não por subregião). Implementação: flag dinâmica `requer_composto` por slot, decrementada conforme compostos são alocados. Quando não há composto disponível pro padrão do slot, aceita isolado e a quota fica em deficit (resolução clínica fica pra Etapa 3 via âncoras).

### Travados (D3.1)
Travados consomem 1 vaga da primeira demanda compatível (mesmo padrão > sub > região, em ordem). Mudança de comportamento vs. estado anterior, onde travados eram "extras" (somavam vagas sem consumir). Isso é semanticamente mais correto e foi aprovado em D3.1. Decomposição é travado-aware: as funções de decomposição aceitam `padroes_obrigatorios` / `subregioes_obrigatorias` para garantir que cada travado tenha um slot do padrão dele.

Edge case: travado sem demanda compatível vira "extra" (chave especial `-1` no dict de alocação) — preserva backward-compat.

### Avisos com escopo rotina vs treino (D3.2 + R3)
- **Fase 0 estrita** (1º passe): slots sem candidato viram pendentes pro 2º passe.
- **Fase 0 relax** (2º passe, só se `relaxar_familia=True`): slots ainda vazios viram aviso `incompleta` `escopo="rotina"`.
- **Fase 1**: usa pré-alocados. Aviso `incompleta` `escopo_aviso="treino"` é gerado se `n_pre_alocados < qtd_pedida` da demanda (raramente, mas possível).
- **Avisos rotina-level são anexados em `sessoes[0].avisos`** com payload incluindo `treino_idx`. UI mistura visualmente — ajuste de UX é ponto aberto (R3).

### Tie-breaking em ordenação (R6)
Sort key dos slots: `(escassez, peso_nivel, jitter_seeded)`. `peso_nivel`: padrão=0, subregião=1, região=2 (granular ganha em empate). `jitter` é `random.random()` — preserva determinismo dado uma seed e evita viés sistemático que ordem do config introduziria.

### Conversão de templates (D4 opção C)
`_normalizar_config(cfg)` faz pass-through quando há `demandas`; converte `padroes` + `exercicios_por_padrao` em demandas tipo `("padrao", X, qtd_X)`. Trata `_PADROES_LEGADOS` ("squat" → squat_bilateral + squat_unilateral via cycling) e EPP-dict de lateralidade. Os 4 templates do código (Full Body, Full Body+Braços, Empurrar+Posterior, Puxar+Anterior) convertem cleanly sem regra especial.

## Surpresas / desvios do plano

1. **Decomposição subregião → padrão era ausente do plano original.** O plano falava apenas de decomposição região → subregião. Quando rodei os testes, descobri regressões em paridade (`costas(4) remadas:puxadas` 1:1 → 3:2; `perna_anterior(3)×3 bi+uni` 100% → 79%). A causa-raiz era o sorteio uniforme dentro do pool da subregião, que perdia o cycling por padrão que o `_selecionar_ciclando` legacy fazia. Solução: `_decompor_demanda_subregiao` com cycling 1-de-cada, simétrico à decomposição região. Adicionei sem perguntar pq era restauração de comportamento, não nova decisão clínica.

2. **2º passe de relax na Fase 0 também não estava no plano original.** O plano dizia "Fase 0 estrita; Fase 1 relaxa". Mas no modo pré-alocado, a Fase 1 só consome pré-alocados — ela não tem como relaxar nada que a Fase 0 não tenha alocado. Resultado: rotinas com famílias esgotadas (Full Body × 4, peito(3)×2) perdiam exercícios em vez de relaxar como antes. Solução: 2º passe na Fase 0 quando `relaxar_familia=True`, com nomes ainda bloqueados mas famílias liberadas. Slots preenchidos no 2º passe propagam pra `Sessao.relaxados` + aviso `familia_repetida`. Mantém o espírito do D3.2 (relax é responsabilidade da Fase 0/1 quando flag está ativa) e cobre os casos de esgotamento.

3. **Teste `test_t2_incompleto_sem_relax_gera_aviso_e_nao_relaxados[templates-999]` foi adaptado**. O teste pré-Etapa 2 fixava "T2 fica incompleto"; pós-Etapa 2, a Fase 0 redistribui escassez e o aviso pode cair em T1 ou T2 dependendo da seed. Adaptei o assertion pra verificar "qualquer treino tem aviso incompleta de peito" — preserva intenção clínica (regra de família continua detectando) sem amarrar a um treino específico.

4. **2 testes XFAIL strict viraram passes**. `test_lower_4_distribui_anterior_e_posterior_balanceado` (Etapa 2) e `test_costas_4_distribui_remadas_e_puxadas_paritarias` (Etapa 3) tinham bar de aceitação que a Etapa 2 já cumpre. Removidos os decorators `xfail` correspondentes. Já confirmei que `test_upper_3x2treinos_tem_composto_de_cada_ancora` (Etapa 3) **continua xfail** — a melhoria atual é parcial; o caso determinístico chega só com âncoras `obrigatoria=True`.

## Pontos abertos pra etapas futuras

- **UI dos avisos `incompleta` rotina-level (R3)**: modal `_avisos_modal.html` mistura avisos rotina + treino visualmente. Precisa ajuste de UX (separar em seções, ícone diferente). Não bloqueia merge.
- **Determinismo da Fase 0 no payload do aviso**: avisos `incompleta` rotina-level são anexados em `sessoes[0].avisos` com `treino_idx` no payload. Frontend pode usar isso pra agrupar por treino, mas hoje não faz. Coordenar com Etapa 3.
- **`posterior_ombro` em essenciais vs acessórias**: hoje não está em `SUBREGIOES_POR_REGIAO["upper"]["essenciais"]` nem em acessórias. Decidir junto com Etapa 3 (provavelmente vira essencial com peso baixo via âncoras).
- **`/regerar` 1 treino não passa por Fase 0**: by design (regerar é cirúrgico). Continua usando `gerar_sessao_por_demandas` standalone, e `gerar_sessao` legacy. Documentado em CLAUDE.md.
- **Pesos clínicos**: hoje a decomposição usa "1 de cada + ciclar" sem peso. Em casos como `perna_posterior(2)` com 3 padrões (hinge, knee_flexion, abduction), a distribuição é uniforme (2 dos 3 sorteados). Pesos `3:2:1` clínicos chegam na Etapa 3 via `ANCORAS_POR_SUBREGIAO`.
- **Quota composta em deficit**: quando o padrão de um slot não tem composto disponível, slot vira isolado e a quota composta da região-mãe não é cumprida totalmente. Sub-PR 2 não emite aviso por isso (resolução vem na Etapa 3 via âncoras com `obrigatoria=True`).

## Métricas pré vs pós (3 configs × 1000 iterações)

Captura completa em `docs/refatoracao/logs/baseline_pre_etapa2.json` e `docs/refatoracao/logs/baseline_pos_etapa2.json`.

| Métrica | Config | Pré-Etapa 2 | Pós-Etapa 2 | Direção |
|---|---|---|---|---|
| razão post/ant lower (mediana) | A_lower4x3 | 1.00 | **1.00** | mantida |
| razão post/ant lower (média) | A_lower4x3 | 0.94 | **1.00** | melhor |
| razão post/ant lower (mediana) | B_lower6x1 | 1.50 | **1.00** | **muito melhor** |
| razão post/ant lower (média) | B_lower6x1 | 1.38 | **1.00** | **muito melhor** |
| freq adut+pant | A_lower4x3 | 18.3% | **0.0%** | crit. ajustado D2.1 ✓ |
| freq adut+pant | B_lower6x1 | 5.3% | **100.0%** | crit. ajustado D2.1 ✓ |
| taxa aviso incompleta | A_lower4x3 | 0.0% | 0.0% | mantida |
| taxa aviso incompleta | B_lower6x1 | 0.0% | 0.0% | mantida |
| taxa aviso incompleta | C_upper4x3 | 0.0% | 0.0% | mantida |
| taxa aviso família | C_upper4x3 | 0.0% | 64.1% | sinalização explícita do que era silencioso |
| taxa blocos solo | A_lower4x3 | 2.5% | 4.5% | leve aumento |
| taxa blocos solo | B_lower6x1 | 0.4% | 0.4% | mantida |
| cobertura compostos peito | C_upper4x3 | 100% | 96.2% | levemente menor |
| cobertura compostos costas | C_upper4x3 | 100% | 100% | mantida |
| cobertura compostos ombro | C_upper4x3 | 100% | 84.3% | levemente menor |
| **Tempo total** (3 configs × 1000 iter) | | **1.21s** | **2.24s** | < 60s ✓ |

**Notas sobre as métricas**:
- Razão posterior/anterior em `lower(N)`: caso B (lower(6)×1) era exatamente o caso clínico problemático identificado no guia (mediana 1.5). Pós-Etapa 2 ficou **determinístico em 1.0** (decomposição lower(6) → 2+2+1+1).
- freq adut+pant: critério **ajustado** em D2.1 final do user. Comportamento esperado: NÃO aparecem em lower(2-4) (acessórias não competem), aparecem com freq crescente em lower(5+). Pós-Etapa 2 satisfaz exatamente: 0% em lower(4), 100% em lower(6).
- Cobertura de compostos em ombro caiu de 100% pra 84.3% em upper(4)×3 — efeito da decomposição essencial. Em ombro, alguns slots ficam com `ombro_isolado` ou `posterior_ombro` (que têm purpose=isolation) em vez de `ombro_composto`. Etapa 3 vai resolver via âncora `peso=3` em ombro_composto.
- Taxa de avisos `familia_repetida` em upper(4)×3 saltou de 0% pra 64.1% — **isso é sinalização explícita do que antes era silencioso** (Fase 1 antiga relaxava sem badge). Pós-Etapa 2, cada exercício alocado via relax recebe badge ↻ na UI, dando ao personal visibilidade do esgotamento.
- Tempo: 2.24s pra 3000 simulações = ~0.75ms por simulação. Caching de pools (Sub-PR 3) **NÃO** foi necessário.

## Snapshots regenerados — diagnóstico individual

Diff completo + diagnóstico clínico em [snapshots_diff_review.md](snapshots_diff_review.md). Resumo:

| # | Snapshot | ∆ ex | Coerente | Suspeita |
|---|----------|------|----------|----------|
| 1 | core_3x1_seed17 | 0 | sim | não |
| 2 | costas_4x1_seed9 | 0 | sim | não |
| 3 | full_body_4_seed1 | 0 (33→33) | sim | não |
| 4 | hinge_2_squat_uni_2_seed19 | 0 | sim | não |
| 5 | max_cx_baixa_seed29 | 0 | sim | não |
| 6 | peito_3x2_seed13 | 0 | sim | não |
| 7 | perna_anterior_3x3_seed3 | 0 | sim | não |
| 8 | perna_posterior_2x2_seed5 | 0 | sim | não — mudou hinge:abduction:knee_flex de 2:1:1 pra 1:2:1; resolução vem na Etapa 3 via pesos 3:2:1 |
| 9 | template_empurrar_puxar_seed7 | 0 | sim | não |
| 10 | triceps_2_filtro_familia_relax_seed23 | 0 | sim | não |
| 11 | upper_3_lower_2_core_2_3_seed42 | 0 | sim | não |
| 12 | upper_3x2_seed11 | 0 | sim | não — **melhoria clínica**: T1 agora tem `Apoio` (composto de peito) |

Cobertura clínica preservada em 12/12 cenários. Avisos novos refletem sinalização explícita de mecanismos antes silenciosos. Aprovação caso a caso recebida (R7).

## Critério de "feito" — checklist

- [x] Sub-PR 1 merged (commit `9fdf448`): `pre_alocar_rotina` e escassez testadas em isolamento
- [x] Sub-PR 2 merged: integração feita, 12 snapshots regenerados com diagnóstico aprovado
- [x] `pytest` em < 30s, 0 falhas (atual: 83 passed, 5 xfailed, 1.58s)
- [x] Harness 1000 iter × 3 configs em < 60s (atual: 2.24s)
- [x] `docs/refatoracao/logs/etapa_2.md` escrito
- [x] Validação manual: configs A, B e C produzem cobertura esperada
- [x] User aprovou regeneração dos snapshots
- [x] Atualização do guia v4 (Apêndice B critério adut/pant)
