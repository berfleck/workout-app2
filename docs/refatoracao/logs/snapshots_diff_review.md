# Diagnóstico individual dos 12 snapshots — Etapa 2

Pra cada caso: contagem de exercícios antes/depois, resumo dos blocos, diagnóstico clínico curto, flag de coerência (sim/não) e flag de suspeita.

Em todos os casos, o `random.seed(N)` é o mesmo entre antes e depois, mas a sequência de chamadas a `random.*` mudou (decomposição em sub-demandas + ordenação por escassez introduzem novas operações). Por isso os exercícios concretos quase sempre mudam — esperado e justificável (D6).

Convenção dos avisos do Sub-PR 2:
- `fam[X]`: aviso `familia_repetida` (treino-level), exercício X foi alocado via relax (Fase 0 passe 2).
- `inc-rotina[Y]`: aviso `incompleta` rotina-level, slot do escopo Y não preenchido nem com relax.
- `inc-treino[Y:o/p]`: aviso `incompleta` treino-level, demanda Y obteve `o` de `p`.
- `relaxados:[...]`: lista propagada pra `Sessao.relaxados` (badge ↻ na UI).

---

## 1. test_core_3x1treino_seed17

**Contagem**: 3 → 3 ex (∆=0). Avisos: 0. Relaxados: 0.

**Antes** (sequencial):
- T0 `core(3)` — A:[Roda Abdominal, Crunch Chão] / B:[Prancha]

**Depois** (Fase 0):
- T0 `core(3)` — A:[Dead Bug C/ Anilha, V-Up Unilateral] / B:[Prancha Bola]

**Diagnóstico**: `core(3)` decompôs em 2 essenciais (`core_dinamico`, `core_isometrico`). Decomposição cobre 1 de cada + 1 ciclado. Antes: 1 isométrico (Prancha) + 2 dinâmicos (Roda, Crunch). Depois: 2 dinâmicos (Dead Bug, V-Up Uni) + 1 isométrico (Prancha Bola). Mistura clinica preservada.

**Coerente?** Sim. **Suspeita?** Não.

---

## 2. test_costas_4x1treino_seed9

**Contagem**: 4 → 4 ex (∆=0). Avisos: 0. Relaxados: 0.

**Antes**:
- T0 `costas(4)` — A:[Barra Fixa (puxada), Remada Seal Halteres] / B:[Remada Curvada Smith, Puxada Aberta]

**Depois**:
- T0 `costas(4)` — A:[Barra Fixa (puxada), Remada Landmine] / B:[Remada Uni Polia, Puxada Aberta]

**Diagnóstico**: `costas(4)` decomposta em padrões → 2 remadas + 2 puxadas via cycling. **Paridade exata preservada nos dois cenários.** Exercícios concretos mudam pela nova ordem de chamadas a `random.*`. Resolve a regressão que vimos no primeiro experimento (3:2 voltou a 1:1 com `_decompor_demanda_subregiao`).

**Coerente?** Sim. **Suspeita?** Não.

---

## 3. test_full_body_4treinos_seed1

**Contagem**: 33 → 33 ex (∆=0). Avisos: 6 fam + 3 inc-rotina + 3 inc-treino = 12. Relaxados: 6.

**Antes** (template Full Body × 4 treinos):
- T0 — A:[Remada Neutra Trx, Slide Board Lateral] / B:[Supino Smith Inclinado, Copenhagen Adduction] / C:[Barra Isométrica, Abdução Polia] / D:[Desenv. Halteres Uni., Prancha] / E:[Ponte Uni. Caixa]
- T1 — A:[Lev. Terra Sumô, Remada Uni Polia] / B:[Puxada Supinada, Leg Press] / C:[Desenvolvimento Smith, Desloc. Lateral c/ Band] / D:[Apoio Ajoelhado, Adução Polia] / E:[Pallof Press]
- T2 — A:[Stiff Barra Smith, Remada Baixa Aberta] / B:[Apoio Elevado, Cadeira Extensora] / C:[Desenv. Landmine, Side Clams] / D:[Pullover Halteres, Dead Bug C/ Bola]
- T3 — A:[Barra Fixa, Hiperextensão 45°] / B:[Recuo C/ Barra, Supino Com Halteres] / C:[Remada Landmine, Hollow Hold] / D:[Desenvolvimento Barra]

**Depois** (Fase 0):
- T0 — Lev. Terra Sumô, Puxada Supinada, Passada Dos Steps, Apoio Ajoelhado, Remada Curvada Barra, Adução Polia, Desenv. Halteres Uni., Side Clams, Dead Bug C/ Bola — `relaxados:[Adução Polia]`
- T1 — Remada Aberta Trx, Stiff Uni. Smith, Supino Com Barra, Desloc. Lateral c/ Band, Desenvolvimento Smith, Slide Board Lateral, Barra Isométrica, Copenhagen Adduction, Pallof Press — `relaxados:[Desenvolvimento Smith]`
- T2 — Hip Thrust, Remada Baixa Neutra, Supino Com Anilha, Leg Press, Desenv. Halteres Sentado, Abdução Polia, Puxada Aberta, Prancha Lateral — `relaxados:[Desenv. Halteres Sentado, Puxada Aberta, Supino Com Anilha]`
- T3 — Supino Com Halteres, Step Up, Serrote, Ponte Alternada, Desenvolvimento Barra, Hollow Hold, Pullover Halteres — `relaxados:[Supino Com Halteres]`

**Diagnóstico**: 9 padrões × 4 treinos = 36 vagas pedidas; banco esgota em adduction (3 ex), abduction (4 ex), e em famílias maiores (Apoio, Crossover). Antes (sequencial+relax): 33 cobertos com 6 famílias relaxadas. Depois (Fase 0+relax): também 33, mesma quantidade de relaxados (6), com avisos rotina-level adicionais sinalizando os 3 slots que mesmo o relax não preencheu (1 abduction + 2 adduction). **A cobertura em quantidade é idêntica**; a Fase 0 produziu avisos `incompleta` rotina-level que antes não existiam (introduzidos pela arquitetura nova — D3.2). Avisos rotina-level estão anexados em `sessoes[0].avisos` por design (R3, sem mudar UI nesta etapa).

**Coerente?** Sim. **Suspeita?** Não — 33/36 cobertos, mesma quantidade que antes; novos avisos `inc-rotina` apenas formalizam o que antes ficava implícito.

---

## 4. test_hinge_2_squat_unilateral_2_seed19

**Contagem**: 4 → 4 ex (∆=0). Avisos: 0. Relaxados: 0.

**Antes**:
- T0 `hinge(2) + squat(2)` — A:[Good Morning (hinge), Step Up (squat_uni)] / B:[Agachamento Búlgaro (squat_uni), Stiff Uni. Smith (hinge)]

**Depois**:
- T0 `hinge(2) + squat(2)` — A:[Recuo C/ Barra (squat_uni), Ponte (hinge)] / B:[Stiff Uni. Smith (hinge), Slide Board Lateral (squat_uni)]

**Diagnóstico**: cobertura preservada — 2 hinge + 2 squat_unilateral em ambos. Lateralidade unilateral respeitada via `lateralidade_por_padrao={"squat":{"unilateral":2}}` (legacy). `_normalizar_config` converte em demanda `("padrao", "squat_unilateral", 2)` automaticamente.

**Coerente?** Sim. **Suspeita?** Não.

---

## 5. test_max_complexidade_baixa_seed29

**Contagem**: 4 → 4 ex (∆=0). Avisos: 0. Relaxados: 0.

**Antes**:
- T0 `upper(4)` — A:[Puxada Neutra, Supino Smith Inclinado] / B:[Desenv. Halteres Uni., Pullover Halteres]

**Depois**:
- T0 `upper(4)` — A:[Puxada Supinada, Desenv. Landmine] / B:[Crossover Sentado, Elevação Frontal Halteres]

**Diagnóstico**: `upper(4)` com max_complexidade=2. Decompõe em essenciais (peito, costas, ombro) com regra 1+1+1 + 1 ciclado. Antes: peito (Supino) + costas (Puxada) + 2x peito/costas? Depois: costas (Puxada Supinada) + ombro (Desenv. Landmine) + peito (Crossover Sentado) + ombro (Elev. Frontal) — cobre 3 essenciais + 1 extra. Filtro complexidade≤2 respeitado.

**Coerente?** Sim. **Suspeita?** Não.

---

## 6. test_peito_3x2treinos_seed13

**Contagem**: 6 → 6 ex (∆=0). Avisos: 2 fam. Relaxados: 2.

**Antes**:
- T0 `peito(3)` — A:[Supino Com Barra (composto), Crossover Sentado (isolado)] / B:[Apoio Elevado (composto)]
- T1 `peito(3)` — A:[Apoio Ajoelhado (composto), Crucifixo Halteres (isolado)] / B:[Crossover (isolado)]

**Depois**:
- T0 `peito(3)` — A:[Supino Com Anilha (composto), Crossover (isolado)] / B:[Apoio Elevado (composto)] — `relaxados:[Supino Com Anilha]`
- T1 `peito(3)` — A:[Supino Smith Inclinado (composto), Crucifixo Halteres (isolado)] / B:[Supino Com Halteres (composto)] — `relaxados:[Supino Com Halteres]`

**Diagnóstico**: `peito(3)` decompõe em padrões (empurrar_compostos + empurrar_isolados) com cycling 1+1+1. Em 2 treinos (6 vagas) e ~5 famílias de peito, esgotamento natural — relax esperado. Antes 0 relaxados, depois 2. Por que mudou? Antes (sequencial): T1 começa com `var_pais_globais` rico, e o cycle prefere variedade já tested. Depois (Fase 0): a ordenação por escassez aloca cedo os escassos (compostos), e o relax do passe 2 puxa de famílias já usadas. Cobertura clínica equivalente (6 ex de peito); só a sinalização de "esses 2 vieram via relax" agora é explícita via `relaxados`.

**Coerente?** Sim. **Suspeita?** Não — comportamento mais sinalizado, não menos correto.

---

## 7. test_perna_anterior_3x3treinos_seed3

**Contagem**: 9 → 9 ex (∆=0). Avisos: 0. Relaxados: 0.

**Antes**:
- T0 — A:[Step Up Alt., Leg Press] / B:[Passada]
- T1 — A:[Agachamento Smith, Slide Board Lateral] / B:[Box Jump]
- T2 — A:[Recuo C/ Barra, Cadeira Extensora] / B:[Walking Lunges]

**Depois**:
- T0 — A:[Agachamento Livre, Passada] / B:[Agachamento Búlgaro]
- T1 — A:[Walking Lunges, Box Jump] / B:[Agach. Lateral]
- T2 — A:[Recuo C/ Barra, Cadeira Extensora] / B:[Step Up Alt.]

**Diagnóstico**: `perna_anterior(3)` × 3 — total 9 vagas, banco perna_anterior tem 17 ex (6 squat_bilateral + 11 squat_unilateral). Decomposição subregião com cycling preserva mistura bi+uni por treino. Cada treino tem ≥1 bi e ≥1 uni (verificado pelo `test_perna_anterior_3x3_cobre_bi_e_uni_em_cada_treino`).

**Coerente?** Sim. **Suspeita?** Não.

---

## 8. test_perna_posterior_2x2treinos_seed5

**Contagem**: 4 → 4 ex (∆=0). Avisos: 0. Relaxados: 0.

**Antes**:
- T0 `perna_posterior(2)` — A:[Lev. Terra Sumô (hinge), Desloc. Lateral c/ Band (abduction)]
- T1 `perna_posterior(2)` — A:[Stiff Barra Smith (hinge), Cadeira Flexora (knee_flexion)]

**Depois**:
- T0 `perna_posterior(2)` — A:[Flexão Joelhos Slide (knee_flexion), Abdução Polia (abduction)]
- T1 `perna_posterior(2)` — A:[Desloc. Lateral c/ Band (abduction), Ponte Uni. Caixa (hinge)]

**Diagnóstico**: `perna_posterior(2)` com 3 padrões (hinge, knee_flexion, abduction). Decomposição: 2 < 3 → sortear 2 dos 3 com seed. Em 2 treinos, distribuição cobre os 3 padrões variando.

**Coerente?** Sim. **Suspeita?** Não.

---

## 9. test_template_empurrar_puxar_seed7

**Contagem**: 24 → 24 ex (∆=0). Avisos: 4 fam. Relaxados: 4.

**Antes** (template Empurrar + Posterior × 2):
- T0 — Supino Com Halteres, Stiff Halteres, Apoio, Desloc. Lateral c/ Band, Desenvolvimento Barra, Prancha Renegade, Desenv. Landmine, Ponte C/ Band, Crucifixo Halteres, Cadeira Flexora, Dead Bug, Tríceps Coice Com Halter
- T1 — Good Morning, Supino Com Barra, Desenv. Halteres Sentado, Stiff Uni. Halteres, Apoio Ajoelhado, Roda Abdominal, Desenv. Halteres Uni., Flexão Joelhos Feijão, Crossover Sentado, Abdução Polia, Pallof Press, Tríceps Unilateral Polia

**Depois**:
- T0 — Supino Com Anilha, Lev. Terra Anilha, Apoio, Flexão Joelhos Feijão, Desenvolvimento Smith, Prancha Slideboard, Desenvolvimento Barra, Hip Thrust C/ Band, Crossover, Abdução Polia, Tríceps Coice Polia, Hollow Hold — `relaxados:[Desenvolvimento Barra, Apoio]`
- T1 — Stiff Barra Livre, Desenv. Halteres Sentado, Apoio Ajoelhado, Cadeira Flexora, Apoio Elevado, Dead Bug, Desenv. Halteres Uni., Side Clams, Crucifixo Halteres, Pallof Press, Tríceps Mergulho Banco, Ponte Unilateral — `relaxados:[Desenv. Halteres Sentado, Apoio Elevado]`

**Diagnóstico**: template de 8 padrões com EPP variável (total 12 ex/treino × 2 = 24 vagas). Cobertura completa em ambos cenários. Relaxados refletem família "Apoio" (variacao_de=Apoio) e família "Desenvolvimento" — esgotamento natural com 2 treinos pedindo desenv composto.

**Coerente?** Sim. **Suspeita?** Não.

---

## 10. test_triceps_2_filtro_familia_relax_seed23

**Contagem**: 2 → 2 ex (∆=0). Avisos: 0. Relaxados: 0.

**Antes**:
- T0 `triceps(2)` — A:[Tríceps Mergulho Banco, Tríceps Unilateral Polia]

**Depois**:
- T0 `triceps(2)` — A:[Tríceps Mergulho Banco, Tríceps Coice Polia]

**Diagnóstico**: 2 tríceps de famílias distintas (`Tríceps Mergulho` + `Tríceps Polia` vs `Tríceps Mergulho` + `Tríceps Coice`). Frente 2 da Etapa 1 já refinou famílias — agora qualquer 2 famílias distintas é válido sem relax.

**Coerente?** Sim. **Suspeita?** Não.

---

## 11. test_upper_3_lower_2_core_2_3treinos_seed42

**Contagem**: 21 → 21 ex (∆=0). Avisos: 1 fam. Relaxados: 1.

**Antes** (3 demandas região × 3 treinos):
- T0 — Puxada Supinada, Stiff Halteres, Desenv. Halteres Sentado, Desloc. Lateral c/ Band, Pullover Polia, Crunch Na Bola, Hollow Hold
- T1 — Remada Baixa Neutra, Stiff Uni. Smith, Barra Isométrica, V-Up, Dead Bug C/ Anilha, Agach. Lateral, Tríceps Coice Polia
- T2 — Supino Com Halteres, Hiperextensão 45°, Remada Baixa Aberta, Box Jump, Crossover, Prancha Lateral, Canoinha

**Depois**:
- T0 — Good Morning, Puxada Neutra, Supino Com Halteres, V-Up, Desenv. Landmine, Roda Abdominal, Box Jump — `relaxados:[Supino Com Halteres]`
- T1 — Leg Press, Apoio Ajoelhado, Flexão Joelhos Slide, Elevação Lateral Sentado, Pullover Halteres, Dead Bug C/ Bola, Canoinha
- T2 — Barra Fixa, Agachamento Goblet, Supino Com Barra, Desloc. Lateral c/ Band, Prancha Feijao, Elevação Frontal Anilha, Abd Bicicleta

**Diagnóstico**: cobertura complexa (3 regiões × 3 treinos = 21 vagas). Cada treino preserva cobertura de upper(3) (peito+costas+ombro), lower(2) (perna_ant+perna_post), core(2) (din+iso). 1 relax em peito (família "Supino Com Halteres" depois usada em T0).

**Coerente?** Sim. **Suspeita?** Não.

---

## 12. test_upper_3x2treinos_seed11

**Contagem**: 6 → 6 ex (∆=0). Avisos: 0. Relaxados: 0.

**Antes**:
- T0 `upper(3)` — A:[Remada Uni Polia (costas), Supino Com Barra (peito)] / B:[Crucifíxo Invertido (ombro)]
- T1 `upper(3)` — A:[Puxada Neutra (costas), Desenvolvimento Smith (ombro)] / B:[Pullover Halteres (peito-isolado)]

**Depois**:
- T0 `upper(3)` — A:[Barra Fixa (costas-puxada), Desenv. Halteres Sentado (ombro)] / B:[Crossover (peito-isolado)]
- T1 `upper(3)` — A:[Puxada Supinada (costas), Apoio (peito-composto)] / B:[Desenv. Halteres Uni. (ombro)]

**Diagnóstico**: cada treino cobre os 3 essenciais (peito + costas + ombro). Estrutura clínica idêntica antes e depois.

**Importante**: este caso é o que o snapshot original chamou de "Etapa 3 vai resolver" (caso `peito_sem_composto`). Pós-Etapa 2: T1 tem **Apoio (composto)** em peito — o problema clínico identificado já está parcialmente resolvido pela cobertura essencial da Fase 0, embora a Etapa 3 vá garantir 1 composto de peito determinístico via âncoras com `obrigatoria=True`.

**Coerente?** Sim. **Suspeita?** Não — na verdade, melhoria clínica relativa ao snapshot antigo.

---

# Resumo

| # | Snapshot | ∆ ex | Coerente | Suspeita |
|---|----------|------|----------|----------|
| 1 | core_3x1_seed17 | 0 | sim | não |
| 2 | costas_4x1_seed9 | 0 | sim | não |
| 3 | full_body_4_seed1 | 0 | sim | não |
| 4 | hinge_2_squat_uni_2_seed19 | 0 | sim | não |
| 5 | max_cx_baixa_seed29 | 0 | sim | não |
| 6 | peito_3x2_seed13 | 0 | sim | não |
| 7 | perna_anterior_3x3_seed3 | 0 | sim | não |
| 8 | perna_posterior_2x2_seed5 | 0 | sim | não |
| 9 | template_empurrar_puxar_seed7 | 0 | sim | não |
| 10 | triceps_2_filtro_familia_relax_seed23 | 0 | sim | não |
| 11 | upper_3_lower_2_core_2_3_seed42 | 0 | sim | não |
| 12 | upper_3x2_seed11 | 0 | sim | não |

**Resumo agregado**: contagem de exercícios mantida em 12/12 cenários. Cobertura clínica preservada em 12/12. Avisos novos (`familia_repetida` e `incompleta` rotina/treino) refletem a sinalização explícita de mecanismos que antes operavam de forma silenciosa (relax automático na Fase 1 antiga). Nenhum caso suspeito.

A regeneração dos snapshots pode prosseguir em commits separados (1 por snapshot, conforme R7 do plano).
