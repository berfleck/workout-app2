# Snapshots de regressão — diff individual da Etapa 3

8 dos 12 snapshots regenerados após a Etapa 3. Diagnóstico individual
aprovado pelo usuário antes da regeneração via `--snapshot-update`.

## Resumo

| # | Snapshot | Mudança principal | Coerente | Observação |
|---|----------|-------------------|----------|-----------|
| 1 | `upper_3_lower_2_core_2_3treinos_seed42` | peito=4, costas=3, ombro=2 (peso 2:2:1 com filtro pré-quotas mantém só obrigatórias em qtd=3≤6) | sim | Lower e core como na Etapa 2 |
| 2 | `upper_3x2treinos_seed11` | T1 "Supino Com Halteres" e T2 "Apoio" (compostos de peito); 2 avisos `ancora_nao_cumprida` | sim | **Resolve `crossover_sentado_only`** — Etapa 3 garante composto de peito em ambos os treinos |
| 3 | `perna_anterior_3x3treinos_seed3` | 5 bi + 4 uni (Hamilton 3:2 com hierarquia treino>rotina), cada treino com bi+uni | sim | **Resolve `perna_anterior_sem_isolado`** — distribuição respeita pesos em vez de banco (6:3 → 5:4) |
| 4 | `perna_posterior_2x2treinos_seed5` | hinge=2 knee=1 abd=1 (Hamilton 3:2:1 com 4 vagas) | sim | Distribuição clínica antes da Etapa 3 era 1:2:1 |
| 5 | `costas_4x1treino_seed9` | 2 remadas + 2 puxadas (paridade preservada via Hamilton 2:2 com 4 vagas) | sim | Mesmo resultado da Etapa 2 (2:2 era acidente do cycling; agora é deliberado) |
| 6 | `peito_3x2treinos_seed13` | 4 compostos + 2 isolados (Hamilton 3:2 com 6 vagas → 4:2) | sim | Proporção composto/iso clinicamente correta |
| 7 | `core_3x1treino_seed17` | core_dinamico=2 + core_isometrico=1 (Hamilton 1:1 com 3 vagas → 2:1 via tie-break) | sim | Sem âncoras em core_* (caem em fallback Etapa 2) |
| 8 | `max_complexidade_baixa_seed29` | 5 ex (1 de cada essencial); 1 aviso `ancora_nao_cumprida` | sim | Cx baixa restringe pool de candidatos; aviso sinaliza explicitamente |

## Detalhamento

### 1. `upper_3_lower_2_core_2_3treinos_seed42`
- **Antes (Etapa 2):** distribuição peito/costas/ombro variável conforme cycling
- **Depois (Etapa 3):** `upper(3) × 3 treinos = 9 vagas`. Hierarquia treino>rotina aplica filtro pré-quotas (qtd=3 ≤ 2×3=6 → só obrigatórias) e Hamilton sobre upper=peito:2, costas:2, ombro:1. Quotas globais 9×(2/5,2/5,1/5)=(3.6,3.6,1.8)→Hamilton (4,3,2). Distribuídas entre 3 treinos: peito=4, costas=3, ombro=2.

### 2. `upper_3x2treinos_seed11`
- **Antes:** T2 podia ter Crossover Sentado (isolado) sem composto de peito
- **Depois:** Hierarquia treino>rotina aplica `upper(3) × 2 = 6 vagas`. Filtro pré-quotas mantém só obrigatórias (qtd=3≤6). Hamilton 6×(2/5,2/5,1/5)=(2.4,2.4,1.2)→(3,2,1). Distribuído: T1 ombro+peito+costas, T2 peito+peito+costas. Ambos têm composto de peito (Supino Com Halteres / Apoio).
- **Avisos `ancora_nao_cumprida`** sinalizam que ombro só apareceu em 1 treino (peso 1 contra 2:2 — natural).

### 3. `perna_anterior_3x3treinos_seed3`
- **Antes:** banco enviesado 6 uni:3 bi (proporção do banco 11:6)
- **Depois:** `perna_anterior(3) × 3 = 9 vagas` agregadas. Hamilton sobre peso 3:2 (squat_bi:3, squat_uni:2) → 9×(3/5,2/5)=(5.4,3.6)→(5,4). Distribuído via round-robin: cada treino tem 1 bi + 1 uni + 1 outro.

### 4. `perna_posterior_2x2treinos_seed5`
- **Antes:** distribuição uniforme essencial → 1 hinge 2 abd 1 knee em 2 treinos
- **Depois:** `perna_posterior(2) × 2 = 4 vagas` agregadas. Hamilton 3:2:1 com 4 vagas → 4×(3/6,2/6,1/6)=(2,1.33,0.67)→floor(2,1,0)→resto(0,0.33,0.67)→top abd → (2,1,1). Distribuído: T1 hinge+abd, T2 hinge+knee.

### 5. `costas_4x1treino_seed9`
- **Antes:** 2:2 via cycling (acidente)
- **Depois:** Hamilton 2:2 com 4 vagas → exato (2,2). Mesmo resultado, agora deliberado.

### 6. `peito_3x2treinos_seed13`
- **Antes:** distribuição emergente do cycling (sem garantia de proporção)
- **Depois:** `peito(3) × 2 = 6 vagas` agregadas. Hamilton 3:2 com 6 vagas → (4,2)→4 compostos + 2 isolados. Distribuição clínica respeitada.

### 7. `core_3x1treino_seed17`
- **Antes:** cycling uniforme entre core_dinamico e core_isometrico
- **Depois:** core não tem ANCORAS_POR_REGIAO (sem peso). Cai em fallback Etapa 2 (cycling essencial). Hamilton aplicado nas regiões com âncoras só. Distribuição visível (2:1) emerge do cycling do `_decompor_demanda_regiao` fallback.

### 8. `max_complexidade_baixa_seed29`
- **Antes:** distribuição mais ampla
- **Depois:** filtro de complexidade restringe candidatos antes da pré-alocação. Quotas Hamilton geram aviso `ancora_nao_cumprida` quando uma obrigatória fica sem candidato — sinalização explícita de que cx restringe.

## Aprovação

Diagnóstico apresentado ao usuário em formato de tabela + visão clínica
de cada snapshot. Aprovação recebida pra regeneração via
`pytest tests/test_regressao.py --snapshot-update`.
