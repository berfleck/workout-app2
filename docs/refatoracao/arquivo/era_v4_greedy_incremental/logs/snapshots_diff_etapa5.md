# Snapshots de regressão — Etapa 5 (Sub-PR 5.2)

Diagnóstico individual dos 13 testes em [tests/test_regressao.py](../../tests/test_regressao.py). Padrão: linha "PRE" mostra o pareamento da Etapa 4 (cascata determinística), linha "POS" mostra o pareamento pós-Etapa 5 (softmax top-K=3, T=200).

A Fase 1 (seleção de exercícios por demandas) **não mudou** — todos os testes preservam o conjunto de exercícios escolhidos. O que mudou é a Fase 2 (`montar_blocos` → `_buscar_candidato`), que agora dá pesos explícitos pra qualidade do pareamento e amostra entre top-3 com softmax.

## Sumário

| # | Teste | Status | Observação |
|---|---|---|---|
| 1 | `test_upper_3_lower_2_core_2_3treinos_seed42` | ⚠️ regen + nota | "Agachamento Goblet" virou solo em T1 (era pareado) |
| 2 | `test_full_body_4treinos_seed1` | ✅ regen | Reordenamento de pares; cobertura clínica preservada |
| 3 | `test_template_empurrar_puxar_seed7` | ✅ regen | Reordenamento de pares; sem solo novo |
| 4 | `test_upper_3x2treinos_seed11` | ✅ regen | Trocas internas de par (anchor-puller mais agressivo) |
| 5 | `test_perna_anterior_3x3treinos_seed3` | ✅ regen | Trocas internas; cobertura âncora preservada |
| 6 | `test_perna_posterior_2x2treinos_seed5` | ✅ estável | Pareamento determinístico (poucos candidatos no top-K) |
| 7 | `test_costas_4x1treino_seed9` | ✅ regen | Swap de pares Hip Thrust ↔ Supino Anilha |
| 8 | `test_peito_3x2treinos_seed13` | ✅ regen | Swap interno; sem mudança clínica relevante |
| 9 | `test_core_3x1treino_seed17` | ✅ estável | Pareamento determinístico |
| 10 | `test_hinge_2_squat_unilateral_2_seed19` | ✅ regen | Pequeno reordenamento |
| 11 | `test_triceps_2_filtro_familia_relax_seed23` | ✅ estável | Bloco com 1 candidato natural — sem variação |
| 12 | `test_max_complexidade_baixa_seed29` | ✅ regen | Reordenamento simples (3 candidatos só) |
| 13 | `test_full_body_4treinos_seed1_HIB2` | ✅ regen | Idem #2 mas com filtro HIB2 ativo |

**3 estáveis** (configs com poucos candidatos válidos no top-K — pareamento naturalmente determinístico mesmo com softmax). **10 regenerados**, todos sem regressão clínica significativa exceto o caso #1 (flagged abaixo).

## Diagnóstico individual

### #1 — `test_upper_3_lower_2_core_2_3treinos_seed42` ⚠️

**Trade-off claro:** "Agachamento Goblet" (composto lower, fadiga 2) ANTES estava pareado com "Barra Fixa" (composto upper). AGORA ficou SOLO. V-Up Unilateral "puxou" Barra Fixa pra si (uni-uni cross-region: +1000 + 100 + 50 − 10 = +1140 vs Agachamento Goblet + Barra Fixa: +1000 + 100 + 50 + 25 = +1175 — **mas a softmax sample escolheu V-Up**, não Goblet, mesmo o composto tendo score maior).

```
PRE  T1.A: Barra Fixa + Agachamento Goblet  |  POS  T1.A: Barra Fixa + V-Up Unilateral
PRE  T1.B: Serrote + Ponte C/ Band          |  POS  T1.B: Serrote + Dead Bug
PRE  T1.C: Remada Neutra Trx + V-Up Uni     |  POS  T1.C: Remada Neutra Trx + Ponte C/ Band
PRE  T1.D: Dead Bug (solo)                  |  POS  T1.D: Agachamento Goblet (solo)
```

**Análise:** o teste mostra que a softmax (T=200) deu uma probabilidade mensurável (~1/3) pra V-Up Uni mesmo seu score sendo 35 pontos abaixo do Agachamento Goblet — gap de 35 com T=200 → exp(-0.175) ≈ 0.84 → ~26% prob. Em essência: **a estocasticidade da softmax expressa que V-Up + Barra Fixa é "quase tão bom quanto" Goblet + Barra Fixa**, e às vezes escolhe V-Up.

Isso é comportamento esperado da softmax. Trade-off:
- **Pareamento clínico ideal**: composto+composto pesado (Goblet+Barra Fixa) abre o treino com bloco intenso
- **Pareamento alternativo aceito**: cross-region uni (V-Up+Barra Fixa) ganha contraste muscular; Goblet vira solo (válido — composto pesado)

**Decisão (aprovada pelo usuário):** aceitar como variação clinicamente válida — ambos os pareamentos são defensáveis. Se simulações futuras mostrarem que essa "concessão" acontece com frequência indesejável, opções:
1. Aumentar `composto` peso de +25 pra +50 (composto+composto fica mais distante)
2. Reduzir T pra 100 (softmax mais conservadora — top-1 domina mais)
3. Aumentar `anti_uni_diff_grupo` de -10 pra -25 (desincentivar mais a "puxada" do V-Up)

**Observação clínica do usuário sobre o caso específico:** Barra Fixa tem demanda de core e flexores de quadril maior do que o cadastrado no banco — pareá-la com V-Up Uni (que demanda muito core) sobrecarrega. **Isso é caso pra ajustar os hard filters via curadoria de `carga_core` / `carga_lombar` de Barra Fixa**, não pra mexer no score. Registrado em "pontos abertos" do log da etapa pra próxima revisão de banco.

**OK regen.**

### #2 — `test_full_body_4treinos_seed1` ✅

10 swaps de pares ao longo dos 4 treinos. Todos os exercícios da Fase 1 preservados; só a ordem de pareamento mudou. Cobertura clínica idêntica.

### #3 — `test_template_empurrar_puxar_seed7` ✅

Pareamentos reorganizados em T1 (4 swaps). Sem solo novo. Sem regressão clínica.

### #4 — `test_upper_3x2treinos_seed11` ✅

Anchor-puller mais agressivo: Supino Com Halteres + Step Up vira Desenvolvimento Barra + Step Up (Desenvolvimento ganha pelo +1000 regiao_diff vs Step Up; Supino vai pra outro bloco com Hollow Hold).

### #5 — `test_perna_anterior_3x3treinos_seed3` ✅

Quotas de âncora `squat_bilateral` / `squat_unilateral` (Etapa 3) preservadas. Mudanças são internas ao pareamento.

### #6, 9, 11 — Estáveis (sem regen necessário)

Configs com pool naturalmente pequeno no top-K → softmax converge no mesmo candidato que a cascata.

### #7 — `test_costas_4x1treino_seed9` ✅

Swap simples: PRE Hip Thrust + Remada Baixa Neutra ↔ Supino Anilha + Leg Press. POS: Hip Thrust + Supino Anilha (regiao_diff!) ↔ Remada Baixa Neutra + Leg Press (regiao_diff). Pareamento POS é objetivamente melhor (cobertura cross-region em ambos blocos).

### #8 — `test_peito_3x2treinos_seed13` ✅

Trocas internas. Sem regressão.

### #10 — `test_hinge_2_squat_unilateral_2_seed19` ✅

Pequeno reordenamento. Sem regressão.

### #12 — `test_max_complexidade_baixa_seed29` ✅

Cenário restrito (3 candidatos). Reordenamento simples. Sem regressão.

### #13 — `test_full_body_4treinos_seed1_HIB2` ✅

Equivalente ao #2 mas com filtro HIB2 ativo. Mudanças idênticas em forma; filtro continua bloqueando os mesmos pares de carga.

## Caso clínico positivo: V-Up Uni resolvido

Embora não esteja entre os snapshots de regressão, o caso real do `memoria_projeto.md` (problema 6) virou pass:

```
PRE  V-Up Uni + Tríceps Uni Polia pareados em ~15% das gerações (seeds 10000-10049)
POS  V-Up Uni + Tríceps Uni Polia pareados em > 50% das gerações ✅
```

Confirmado também pela métrica de entropia: na config `core_3_uni_pair`, o pareamento "Tríceps Unilateral Polia + V-Up Unilateral" passou de 15% (top-2) para **42.5% (top-1)**, e "Tríceps Uni SOLO" sumiu do top-5.

## Ponto aberto

**Item flagged: pesos do anti-uni cross-region (-10) podem ser leves demais** quando o âncora é unilateral em região oposta — V-Up Uni "puxa" o composto upper mais atrativo, deixando outras coisas potencialmente solo. Por enquanto o comportamento está dentro do esperado clinicamente; **revisitar se simulações futuras mostrarem solos forçados** atribuíveis a esse caso. Possível ajuste: -25 cross-region em vez de -10.
