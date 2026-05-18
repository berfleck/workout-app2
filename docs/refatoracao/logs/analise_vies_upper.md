# Analise de vies — upper(4) x 2 treinos

- Timestamp: 2026-05-18 14:52:36
- Git: `1ac793d`
- N iteracoes: **1000** (seeds 1000..1999)
- relaxar_familia: `True` | historico_r1: `None`
- Slots esperados: 8000 | observados: 8000

## Q1 — Exercicios predominantes

Top-20 por numero de rotinas (de 1000) em que o exercicio apareceu pelo menos 1×.

| # | Exercicio | Padrao | Subreg | n_rot | % rot | freq_slot |
|---|---|---|---|---:|---:|---:|
| 1 | Desenv. Halteres Sentado | ombro_composto | ombro | 581 | 58.1% | 581 |
| 2 | Desenv. Landmine | ombro_composto | ombro | 457 | 45.7% | 457 |
| 3 | Pullover Halteres | puxadas | costas | 456 | 45.6% | 456 |
| 4 | Remada Curvada Barra | remadas | costas | 447 | 44.7% | 447 |
| 5 | Desenv. Halteres Uni. | ombro_composto | ombro | 432 | 43.2% | 432 |
| 6 | Apoio | empurrar_compostos | peito | 408 | 40.8% | 408 |
| 7 | Barra Isométrica | puxadas | costas | 392 | 39.2% | 392 |
| 8 | Barra Fixa | puxadas | costas | 388 | 38.8% | 388 |
| 9 | Apoio Ajoelhado | empurrar_compostos | peito | 371 | 37.1% | 371 |
| 10 | Supino Smith Inclinado | empurrar_compostos | peito | 362 | 36.2% | 362 |
| 11 | Apoio Elevado | empurrar_compostos | peito | 357 | 35.7% | 357 |
| 12 | Supino Inclinado Halteres | empurrar_compostos | peito | 351 | 35.1% | 351 |
| 13 | Crossover Sentado | empurrar_isolados | peito | 338 | 33.8% | 338 |
| 14 | Crucifixo Halteres | empurrar_isolados | peito | 334 | 33.4% | 334 |
| 15 | Crossover | empurrar_isolados | peito | 328 | 32.8% | 328 |
| 16 | Desenvolvimento Barra | ombro_composto | ombro | 313 | 31.3% | 313 |
| 17 | Remada Curvada Halteres | remadas | costas | 280 | 28.0% | 280 |
| 18 | Remada Curvada Smith | remadas | costas | 273 | 27.3% | 273 |
| 19 | Desenvolvimento Smith | ombro_composto | ombro | 217 | 21.7% | 217 |
| 20 | Remada Apoiado | remadas | costas | 158 | 15.8% | 158 |

**Concentracao:** Gini = `0.285` (0=uniforme, 1=concentrado em 1) | Entropia normalizada = `0.956` (1=uniforme entre exs vistos)

## Q2 — Exercicios que nunca apareceram (34 de 62)

Cobertura: **45.2%** (28/62 exercicios upper vistos)

| Exercicio | Padrao | Subreg |
|---|---|---|
| Apoio Fechado | empurrar_compostos | peito |
| Supino Com Barra | empurrar_compostos | peito |
| Supino Com Halteres | empurrar_compostos | peito |
| Supino Fechado | empurrar_compostos | peito |
| Remada LM Aberta | remadas | costas |
| Remada LM Neutra | remadas | costas |
| Remada Seal Halteres | remadas | costas |
| Remada Uni Polia | remadas | costas |
| Serrote | remadas | costas |
| Barra Aberta | puxadas | costas |
| Barra Supinada | puxadas | costas |
| Puxada Supinada | puxadas | costas |
| Elevação Frontal Anilha | ombro_isolado | ombro |
| Elevação Frontal Halteres | ombro_isolado | ombro |
| Elevação Lateral | ombro_isolado | ombro |
| Elevação Lateral Polia | ombro_isolado | ombro |
| Elevação Lateral Sentado | ombro_isolado | ombro |
| Crucifíxo Invertido | posterior_ombro | ombro |
| Face Pull (Polia) | posterior_ombro | ombro |
| Posterior Ombro Polia | posterior_ombro | ombro |
| Bíceps 21S | biceps | bracos |
| Bíceps Banco | biceps | bracos |
| Bíceps Bayesian | biceps | bracos |
| Bíceps Cabo | biceps | bracos |
| Bíceps Halteres | biceps | bracos |
| Bíceps Martelo | biceps | bracos |
| Tríceps Coice Com Halter | triceps | bracos |
| Tríceps Coice Polia | triceps | bracos |
| Tríceps Corda | triceps | bracos |
| Tríceps Francês | triceps | bracos |
| Tríceps Mergulho Banco | triceps | bracos |
| Tríceps Polia Alta | triceps | bracos |
| Tríceps Testa Halteres | triceps | bracos |
| Tríceps Unilateral Polia | triceps | bracos |

## Q3 — Categorias dominantes/sub-representadas

### Por padrao (slots, agregado T1+T2)

| Padrao | Obs | % Obs | % Esp | Δ pp | Razao O/E |
|---|---:|---:|---:|---:|---:|
| empurrar_compostos | 2000 | 25.0% | 25.0% | +0.0 | 1.00 |
| empurrar_isolados | 1000 | 12.5% | 25.0% | -12.5 | 0.50 |
| remadas | 1501 | 18.8% | 12.5% | +6.3 | 1.50 |
| puxadas | 1499 | 18.7% | 12.5% | +6.2 | 1.50 |
| ombro_composto | 2000 | 25.0% | 25.0% | +0.0 | 1.00 |
| ombro_isolado | 0 | 0.0% | 0.0% | +0.0 | — |
| posterior_ombro | 0 | 0.0% | 0.0% | +0.0 | — |
| biceps | 0 | 0.0% | 0.0% | +0.0 | — |
| triceps | 0 | 0.0% | 0.0% | +0.0 | — |

### Por subregiao (slots, agregado T1+T2)

| Subregiao | Obs | % Obs | % Esp | Δ pp |
|---|---:|---:|---:|---:|
| peito | 3000 | 37.5% | 50.0% | -12.5 |
| costas | 3000 | 37.5% | 25.0% | +12.5 |
| ombro | 2000 | 25.0% | 25.0% | +0.0 |
| bracos | 0 | 0.0% | 0.0% | +0.0 |

### Composto vs isolado (agregado T1+T2)

| Tipo | Obs | % Obs | % Esp | Δ pp |
|---|---:|---:|---:|---:|
| composto | 6433 | 80.4% | 75.0% | +5.4 |
| isolado | 1567 | 19.6% | 25.0% | -5.4 |

## Q4 — Distribuicao T1 vs T2

### Composto vs isolado por treino

| Tipo | T1 | % T1 | T2 | % T2 | Δ pp |
|---|---:|---:|---:|---:|---:|
| composto | 3629 | 90.7% | 2804 | 70.1% | +20.6 |
| isolado | 371 | 9.3% | 1196 | 29.9% | -20.6 |

χ² (composto vs isolado × T1/T2) = `540.15` (significativo p<0.05)

### Por subregiao por treino

| Subreg | T1 | % T1 | T2 | % T2 | Δ pp | χ² |
|---|---:|---:|---:|---:|---:|---:|
| peito | 1000 | 25.0% | 2000 | 50.0% | -25.0 | 533.33 * |
| costas | 2000 | 50.0% | 1000 | 25.0% | +25.0 | 533.33 * |
| ombro | 1000 | 25.0% | 1000 | 25.0% | +0.0 | 0.00 |
| bracos | 0 | 0.0% | 0 | 0.0% | +0.0 | 0.00 |

### Top 15 exercicios com maior vies posicional T1 vs T2

Top-30 por freq_rotina, ordenado por |T1−T2|. χ² > 3.84 = p<0.05.

| Exercicio | T1 | T2 | Δ pp | χ² | sig |
|---|---:|---:|---:|---:|:---:|
| Crossover Sentado | 0 | 338 | -33.8 | 406.74 | * |
| Crucifixo Halteres | 0 | 334 | -33.4 | 400.96 | * |
| Crossover | 0 | 328 | -32.8 | 392.34 | * |
| Barra Isométrica | 289 | 103 | +18.6 | 109.77 | * |
| Pullover Halteres | 313 | 143 | +17.0 | 82.09 | * |
| Remada Curvada Halteres | 220 | 60 | +16.0 | 106.31 | * |
| Remada Curvada Barra | 301 | 146 | +15.5 | 69.22 | * |
| Barra Fixa | 270 | 118 | +15.2 | 73.88 | * |
| Supino Com Anilha | 151 | 0 | +15.1 | 163.33 | * |
| Remada Curvada Smith | 206 | 67 | +13.9 | 81.96 | * |
| Apoio | 151 | 257 | -10.6 | 34.60 | * |
| Desenv. Halteres Sentado | 309 | 272 | +3.7 | 3.32 |  |
| Desenv. Halteres Uni. | 199 | 233 | -3.4 | 3.41 |  |
| Remada Baixa Neutra | 85 | 60 | +2.5 | 4.65 | * |
| Supino Smith Inclinado | 171 | 191 | -2.0 | 1.35 |  |

Exercicios com χ² significativo (p<0.05) no top-30: **12** / 30

## Anexos

- Rotinas com aviso `incompleta`: 0 (0.0%)
- Rotinas com aviso `familia_repetida`: 0 (0.0%)
- Rotinas com ≥1 exercicio escolhido via relaxamento de familia: 0 (0.0%)
- Sessoes com <4 exercicios: 0 de 2000
- Total exercicios upper no banco: 62

