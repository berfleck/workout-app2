# Triagem Fase 4 — Cadastro das 5 Dimensões de Proximidade

> **Gerado em:** 2026-05-14 por `tools/gerar_triagem_fase_4.py`
> **Referência:** Seção 9 + Seção 7 de `docs/refatoracao/dimensoes_proximidade.md`
> **NÃO modifica o XLSX.** Serve de base para as Fases 4.4-4.7.

## Sumário

| Flag | N | Próxima fase |
|---|---|---|
| 🟢 Verde | 124 | 4.4 (YAML) + 4.5 (não-YAML) — Code preenche |
| 🟡 Amarelo | 12 | 4.6 — revisão clínica por critério agrupado |
| 🔴 Vermelho | 0 | 4.7 — revisão clínica completa |
| **Total** | **136** | 125 XLSX + 11 mock_futuros |

## Chave de colunas

- **Fonte** — `YAML` = dims vêm do overlay clínico (Etapa 6); `NOVO` = exercício sem overlay; `MOCK` = mock_futuro (linha nova no XLSX)
- **peg/plan/eq/vp/at** — pegada / plano_corporal / equipamento_grupo / variante_pontual / ativo
- Valores `null` = campo vazio (None) no XLSX
- `🟡 nota` após valor = dim com ambiguidade clínica a resolver na Fase 4.6

---

## PEITO (13 exercícios — 🟢13 🟡0 🔴0)

| Flag | Fonte | Nome | Família | Padrão | peg | plan | eq | vp | at | Notas 🟡 |
|---|---|---|---|---|---|---|---|---|---|---|
| 🟢 | YAML | Apoio | Apoio | empurrar_compostos | pronada | null | corporal | false | true |  |
| 🟢 | YAML | Apoio Ajoelhado | Apoio | empurrar_compostos | pronada | null | corporal | false | true |  |
| 🟢 | YAML | Apoio Elevado | Apoio | empurrar_compostos | pronada | null | corporal | false | true |  |
| 🟢 | MOCK | Apoio Fechado ⟵ mock_futuro | Apoio | empurrar_compostos | pronada | null | corporal | true | true |  |
| 🟢 | YAML | Supino Com Anilha | Supino | empurrar_compostos | pronada | reto | barra | false | true |  |
| 🟢 | YAML | Supino Com Barra | Supino | empurrar_compostos | pronada | reto | barra | false | true |  |
| 🟢 | YAML | Supino Com Halteres | Supino | empurrar_compostos | pronada | reto | halter | false | true |  |
| 🟢 | MOCK | Supino Fechado ⟵ mock_futuro | Supino Reto | empurrar_compostos | pronada | reto | barra | true | true |  |
| 🟢 | MOCK | Supino Inclinado Halteres ⟵ mock_futuro | Supino Inclinado | empurrar_compostos | pronada | inclinado | halter | false | true |  |
| 🟢 | YAML | Supino Smith Inclinado | Supino | empurrar_compostos | pronada | inclinado | barra_guiada | false | true |  |
| 🟢 | YAML | Crossover | crossover | empurrar_isolados | neutra | reto | polia | false | true |  |
| 🟢 | YAML | Crossover Sentado | crossover | empurrar_isolados | neutra | reto | polia | false | true |  |
| 🟢 | YAML | Crucifixo Halteres | crucifixo | empurrar_isolados | neutra | reto | halter | false | true |  |

---

## COSTAS (21 exercícios — 🟢21 🟡0 🔴0)

| Flag | Fonte | Nome | Família | Padrão | peg | plan | eq | vp | at | Notas 🟡 |
|---|---|---|---|---|---|---|---|---|---|---|
| 🟢 | MOCK | Barra Aberta ⟵ mock_futuro | Barra | puxadas | aberta | null | corporal | false | true |  |
| 🟢 | YAML | Barra Fixa | Barra | puxadas | aberta | null | corporal | false | true |  |
| 🟢 | YAML | Barra Isométrica | Barra | puxadas | aberta | null | corporal | false | true |  |
| 🟢 | MOCK | Barra Supinada ⟵ mock_futuro | Barra | puxadas | supinada | null | corporal | false | true |  |
| 🟢 | YAML | Pullover Halteres | Pullover | puxadas | neutra | pullover | halter | false | true |  |
| 🟢 | YAML | Pullover Polia | Pullover | puxadas | neutra | pullover | polia | false | true |  |
| 🟢 | YAML | Puxada Aberta | Puxada | puxadas | aberta | null | polia | false | true |  |
| 🟢 | YAML | Puxada Neutra | Puxada | puxadas | neutra | null | polia | false | true |  |
| 🟢 | YAML | Puxada Supinada | Puxada | puxadas | supinada | null | polia | false | true |  |
| 🟢 | YAML | Remada Aberta Trx | trx | remadas | aberta | suspensao | null | false | true |  |
| 🟢 | YAML | Remada Apoiado | Remada horizontal | remadas | neutra | apoiada | halter | false | true |  |
| 🟢 | YAML | Remada Baixa Aberta | remada baixa | remadas | aberta | baixa_sentada | polia | false | true |  |
| 🟢 | YAML | Remada Baixa Neutra | Remada horizontal | remadas | neutra | baixa_sentada | polia | false | true |  |
| 🟢 | YAML | Remada Curvada Barra | remada curvada | remadas | pronada | curvada | barra | false | true |  |
| 🟢 | YAML | Remada Curvada Halteres | remada curvada | remadas | pronada | curvada | halter | false | true |  |
| 🟢 | YAML | Remada Curvada Smith | remada curvada | remadas | pronada | curvada | barra_guiada | false | true |  |
| 🟢 | YAML | Remada Landmine | Remada horizontal | remadas | neutra | curvada | barra | false | true |  |
| 🟢 | YAML | Remada Neutra Trx | trx | remadas | neutra | suspensao | null | false | true |  |
| 🟢 | YAML | Remada Seal Halteres | Remada horizontal | remadas | neutra | apoiada | halter | false | true |  |
| 🟢 | YAML | Remada Uni Polia | Remada unilateral | remadas | neutra | unilateral_apoiada | polia | false | true |  |
| 🟢 | YAML | Serrote | Remada unilateral | remadas | neutra | unilateral_apoiada | halter | false | true |  |

---

## OMBRO (13 exercícios — 🟢10 🟡3 🔴0)

| Flag | Fonte | Nome | Família | Padrão | peg | plan | eq | vp | at | Notas 🟡 |
|---|---|---|---|---|---|---|---|---|---|---|
| 🟢 | NOVO | Desenv. Halteres Sentado | Desenvolvimento | ombro_composto | pronada | null | halter | false | true |  |
| 🟢 | NOVO | Desenv. Halteres Uni. | desenv uni | ombro_composto | pronada | null | halter | false | true |  |
| 🟡 | NOVO | Desenv. Landmine | desenv uni | ombro_composto | **neutra** 🟡 | null | barra | false | true | **pegada:** landmine press = 1 mão segurando ponta da barra = grip neutro; alternativa: pronada se considerarmos |
| 🟢 | NOVO | Desenvolvimento Barra | Desenvolvimento | ombro_composto | pronada | null | barra | false | true |  |
| 🟢 | NOVO | Desenvolvimento Smith | Desenvolvimento | ombro_composto | pronada | null | barra_guiada | false | true |  |
| 🟡 | NOVO | Elevação Frontal Anilha | elevação frontal | ombro_isolado | pronada | null | **halter** 🟡 | false | true | **equipamento_grupo:** anilha segurada nas extremidades = free weight análogo a halter; alternativa: null |
| 🟢 | NOVO | Elevação Frontal Halteres | elevação frontal | ombro_isolado | pronada | null | halter | false | true |  |
| 🟢 | NOVO | Elevação Lateral | Elevação lateral | ombro_isolado | neutra | null | halter | false | true |  |
| 🟢 | NOVO | Elevação Lateral Polia | Elevação lateral | ombro_isolado | neutra | null | polia | false | true |  |
| 🟢 | NOVO | Elevação Lateral Sentado | Elevação lateral | ombro_isolado | neutra | null | halter | false | true |  |
| 🟢 | NOVO | Crucifíxo Invertido | — | posterior_ombro | neutra | null | halter | false | true |  |
| 🟡 | NOVO | Face Pull (Polia) | — | posterior_ombro | **aberta** 🟡 | null | polia | false | true | **pegada:** corda de Face Pull = grip aberto (mãos separadas); alternativa: neutra se considerarmos supinação na |
| 🟢 | NOVO | Posterior Ombro Polia | — | posterior_ombro | neutra | null | polia | false | true |  |

---

## BRACOS (14 exercícios — 🟢14 🟡0 🔴0)

| Flag | Fonte | Nome | Família | Padrão | peg | plan | eq | vp | at | Notas 🟡 |
|---|---|---|---|---|---|---|---|---|---|---|
| 🟢 | NOVO | Bíceps 21S | Rosca bíceps | biceps | supinada | null | barra | false | true |  |
| 🟢 | NOVO | Bíceps Banco | Rosca bíceps | biceps | supinada | null | halter | false | true |  |
| 🟢 | NOVO | Bíceps Bayesian | Rosca bíceps | biceps | supinada | null | polia | false | true |  |
| 🟢 | NOVO | Bíceps Cabo | Rosca bíceps | biceps | supinada | null | polia | false | true |  |
| 🟢 | NOVO | Bíceps Halteres | Rosca bíceps | biceps | supinada | null | halter | false | true |  |
| 🟢 | NOVO | Bíceps Martelo | Rosca bíceps | biceps | neutra | null | halter | false | true |  |
| 🟢 | NOVO | Tríceps Coice Com Halter | Tríceps Coice | triceps | null | null | halter | false | true |  |
| 🟢 | NOVO | Tríceps Coice Polia | Tríceps Coice | triceps | null | null | polia | false | true |  |
| 🟢 | NOVO | Tríceps Corda | Tríceps Pushdown | triceps | null | null | polia | false | true |  |
| 🟢 | NOVO | Tríceps Francês | Tríceps Francês | triceps | null | null | halter | false | true |  |
| 🟢 | NOVO | Tríceps Mergulho Banco | Tríceps Mergulho | triceps | null | null | corporal | false | true |  |
| 🟢 | NOVO | Tríceps Polia Alta | Tríceps Pushdown | triceps | null | null | polia | false | true |  |
| 🟢 | NOVO | Tríceps Testa Halteres | Tríceps Testa | triceps | null | null | halter | false | true |  |
| 🟢 | NOVO | Tríceps Unilateral Polia | Tríceps Pushdown | triceps | null | null | polia | false | true |  |

---

## PERNA_ANTERIOR (18 exercícios — 🟢18 🟡0 🔴0)

| Flag | Fonte | Nome | Família | Padrão | peg | plan | eq | vp | at | Notas 🟡 |
|---|---|---|---|---|---|---|---|---|---|---|
| 🟢 | YAML | Agachamento Goblet | Agachamento | squat_bilateral | null | null | halter | false | true |  |
| 🟢 | YAML | Agachamento Livre | Agachamento | squat_bilateral | null | null | barra | false | true |  |
| 🟢 | YAML | Agachamento Smith | Agachamento | squat_bilateral | null | null | barra_guiada | false | true |  |
| 🟢 | YAML | Box Jump | — | squat_bilateral | null | null | null | false | false |  |
| 🟢 | YAML | Cadeira Extensora | — | squat_bilateral | null | null | maquina | false | true |  |
| 🟢 | YAML | Leg Press | — | squat_bilateral | null | null | maquina | false | true |  |
| 🟢 | YAML | Agach. Lateral | agach. lateral | squat_unilateral | null | null | halter | false | true |  |
| 🟢 | YAML | Agachamento Búlgaro | — | squat_unilateral | null | null | halter | false | true |  |
| 🟢 | YAML | Passada | passada | squat_unilateral | null | null | halter | false | true |  |
| 🟢 | YAML | Passada Dos Steps | passada | squat_unilateral | null | null | caixa | false | true |  |
| 🟢 | YAML | Recuo | Recuo | squat_unilateral | null | null | halter | false | true |  |
| 🟢 | YAML | Recuo Alternado | Recuo | squat_unilateral | null | null | halter | false | true |  |
| 🟢 | YAML | Recuo C/ Barra | Recuo | squat_unilateral | null | null | barra | false | true |  |
| 🟢 | MOCK | Recuo do Estepe ⟵ mock_futuro | subida_elevada | squat_unilateral | null | null | caixa | false | true |  |
| 🟢 | YAML | Slide Board Lateral | agach. lateral | squat_unilateral | null | null | null | false | true |  |
| 🟢 | YAML | Step Up | Step up | squat_unilateral | null | null | caixa | false | true |  |
| 🟢 | YAML | Step Up Alt. | Step up | squat_unilateral | null | null | caixa | false | true |  |
| 🟢 | YAML | Walking Lunges | walking lunges | squat_unilateral | null | null | halter | false | true |  |

---

## PERNA_POSTERIOR (26 exercícios — 🟢20 🟡6 🔴0)

| Flag | Fonte | Nome | Família | Padrão | peg | plan | eq | vp | at | Notas 🟡 |
|---|---|---|---|---|---|---|---|---|---|---|
| 🟢 | NOVO | Abdução Polia | Abdução quadril | abduction | null | null | polia | false | true |  |
| 🟢 | NOVO | Desloc. Lateral c/ Band | — | abduction | null | null | banda_elastica | false | true |  |
| 🟢 | NOVO | Side Clams | — | abduction | null | null | banda_elastica | false | true |  |
| 🟢 | NOVO | Good Morning | — | hinge | null | em_pe | barra | false | true |  |
| 🟢 | NOVO | Hip Thrust | Hip thrust | hinge | null | deitado | barra | false | true |  |
| 🟢 | NOVO | Hip Thrust C/ Band | Hip thrust | hinge | null | deitado | banda_elastica | false | true |  |
| 🟡 | NOVO | Hip Thrust Uni. | Hip thrust | hinge | null | deitado | **corporal** 🟡 | false | true | **equipamento_grupo:** eq_primario NaN — sem equipamento (peso corporal)? Confirmar se usa barra/band ou bodyweight |
| 🟡 | NOVO | Hiperextensão 45° | — | hinge | null | **em_pe** 🟡 | caixa | false | true | **plano_corporal:** banco romano 45° ≈ em_pe mas ângulo intermediário — não é nem em_pe puro nem deitado; proposta: em_p |
| 🟢 | NOVO | Lev. Terra | Levantamento terra | hinge | null | em_pe | barra | false | true |  |
| 🟡 | NOVO | Lev. Terra Anilha | Levantamento terra | hinge | null | em_pe | **halter** 🟡 | false | true | **equipamento_grupo:** eq_primario='suporte anilhas' → anilha livre na mão ≈ halter (free weight); ou null se sem analogia |
| 🟢 | NOVO | Lev. Terra Sumô | Levantamento terra | hinge | null | em_pe | barra | false | true |  |
| 🟢 | NOVO | Ponte | ponte | hinge | null | deitado | banda_elastica | false | true |  |
| 🟢 | NOVO | Ponte Alternada | ponte | hinge | null | deitado | caixa | false | true |  |
| 🟢 | NOVO | Ponte C/ Band | ponte | hinge | null | deitado | banda_elastica | false | true |  |
| 🟢 | NOVO | Ponte Na Caixa | ponte | hinge | null | deitado | caixa | false | true |  |
| 🟢 | NOVO | Ponte Uni. Caixa | ponte | hinge | null | deitado | caixa | false | true |  |
| 🟡 | NOVO | Ponte Unilateral | ponte | hinge | null | deitado | **corporal** 🟡 | false | true | **equipamento_grupo:** eq_primario NaN — bodyweight com suporte? |
| 🟢 | NOVO | Stiff Barra Livre | stiff | hinge | null | em_pe | barra | false | true |  |
| 🟢 | NOVO | Stiff Barra Smith | stiff | hinge | null | em_pe | barra_guiada | false | true |  |
| 🟢 | NOVO | Stiff Halteres | stiff | hinge | null | em_pe | halter | false | true |  |
| 🟢 | NOVO | Stiff Uni. Halteres | stiff uni | hinge | null | em_pe | halter | false | true |  |
| 🟢 | NOVO | Stiff Uni. Smith | stiff uni | hinge | null | em_pe | barra_guiada | false | true |  |
| 🟢 | NOVO | Cadeira Flexora | — | knee_flexion | null | null | maquina | false | true |  |
| 🟡 | NOVO | Flexão Joelhos Feijão | flexao joelhos | knee_flexion | null | null | **corporal** 🟡 | false | true | **equipamento_grupo:** feijão = rolo de espuma/feijão de espuma sob pé; próximo de corporal; não tem analogia exata nos 8 g |
| 🟡 | NOVO | Flexão Joelhos Slide | flexao joelhos | knee_flexion | null | null | **corporal** 🟡 | false | true | **equipamento_grupo:** slide board sob pé; não é nenhum dos 8 grupos exatos; corporal é o mais próximo |
| 🟢 | NOVO | Nordic Curl | — | knee_flexion | null | null | corporal | false | true |  |

---

## ADUTORES (2 exercícios — 🟢1 🟡1 🔴0)

| Flag | Fonte | Nome | Família | Padrão | peg | plan | eq | vp | at | Notas 🟡 |
|---|---|---|---|---|---|---|---|---|---|---|
| 🟢 | NOVO | Adução Polia | Adução quadril | adduction | null | null | polia | false | true |  |
| 🟡 | NOVO | Copenhagen Adduction | Adução quadril | adduction | null | null | **corporal** 🟡 | false | true | **equipamento_grupo:** banco reto como ancoragem = bodyweight; alternativa: null pois o banco não é o vetor de carga |

---

## PANTURRILHA (2 exercícios — 🟢0 🟡2 🔴0)

| Flag | Fonte | Nome | Família | Padrão | peg | plan | eq | vp | at | Notas 🟡 |
|---|---|---|---|---|---|---|---|---|---|---|
| 🟡 | NOVO | Elevação De Panturrilha Em Pé | Panturrilha | flexao_plantar | **null** 🟡 | null | barra | false | true | **pegada:** barbell sobre ombros, mãos seguram barra = pronada. Mas panturrilha não está na lista null da Seção  |
| 🟡 | NOVO | Elevação Unilateral Panturrilha | Panturrilha | flexao_plantar | **null** 🟡 | null | barra | false | true | **pegada:** idem acima |

---

## CORE_ISOMETRICO (13 exercícios — 🟢13 🟡0 🔴0)

| Flag | Fonte | Nome | Família | Padrão | peg | plan | eq | vp | at | Notas 🟡 |
|---|---|---|---|---|---|---|---|---|---|---|
| 🟢 | YAML | Prancha Lateral | prancha | flexao_lateral | null | null | null | false | true |  |
| 🟢 | YAML | Dead Bug | Dead bug | flexao_quadril | null | null | null | false | true |  |
| 🟢 | YAML | Dead Bug C/ Anilha | Dead bug | flexao_quadril | null | null | null | false | true |  |
| 🟢 | YAML | Dead Bug C/ Bola | Dead bug | flexao_quadril | null | null | null | false | true |  |
| 🟢 | YAML | Hollow Hold | — | flexao_tronco | null | null | null | false | true |  |
| 🟢 | YAML | Prancha | prancha | flexao_tronco | null | null | null | false | true |  |
| 🟢 | YAML | Prancha Alternada | prancha | flexao_tronco | null | null | null | false | true |  |
| 🟢 | YAML | Prancha Bola | prancha | flexao_tronco | null | null | null | false | true |  |
| 🟢 | YAML | Prancha Feijao | prancha | flexao_tronco | null | null | null | false | true |  |
| 🟢 | YAML | Prancha Renegade | prancha | flexao_tronco | null | null | null | false | true |  |
| 🟢 | YAML | Prancha Slideboard | prancha | flexao_tronco | null | null | null | false | true |  |
| 🟢 | YAML | Roda Abdominal | — | flexao_tronco | null | null | null | false | true |  |
| 🟢 | YAML | Pallof Press | — | rotacao_tronco | null | null | null | false | true |  |

---

## CORE_DINAMICO (12 exercícios — 🟢12 🟡0 🔴0)

| Flag | Fonte | Nome | Família | Padrão | peg | plan | eq | vp | at | Notas 🟡 |
|---|---|---|---|---|---|---|---|---|---|---|
| 🟢 | YAML | Canoinha | — | flexao_quadril | null | null | null | false | true |  |
| 🟢 | MOCK | INFRA Alternado ⟵ mock_futuro | INFRA | flexao_quadril | null | null | null | false | true |  |
| 🟢 | MOCK | INFRA Chão ⟵ mock_futuro | INFRA | flexao_quadril | null | null | null | false | true |  |
| 🟢 | MOCK | INFRA Roll-Up ⟵ mock_futuro | INFRA | flexao_quadril | null | null | null | false | true |  |
| 🟢 | MOCK | INFRA Suspenso ⟵ mock_futuro | INFRA | flexao_quadril | null | null | null | false | true |  |
| 🟢 | YAML | V-Up | v-up | flexao_quadril | null | null | null | false | true |  |
| 🟢 | YAML | V-Up Unilateral | v-up | flexao_quadril | null | null | null | false | true |  |
| 🟢 | YAML | Abd Bicicleta | crunch | flexao_tronco | null | null | null | false | true |  |
| 🟢 | YAML | Crunch Chão | crunch | flexao_tronco | null | null | null | false | true |  |
| 🟢 | YAML | Crunch Na Bola | crunch | flexao_tronco | null | null | null | false | true |  |
| 🟢 | YAML | Crunch No Cabo | crunch | flexao_tronco | null | null | null | false | true |  |
| 🟢 | MOCK | Russian Twist ⟵ mock_futuro | russian twist | rotacao_tronco | null | null | null | false | true |  |

---

## CARDIO (2 exercícios — 🟢2 🟡0 🔴0)

| Flag | Fonte | Nome | Família | Padrão | peg | plan | eq | vp | at | Notas 🟡 |
|---|---|---|---|---|---|---|---|---|---|---|
| 🟢 | NOVO | Air Bike (Sprint) | Air bike | cardio | null | null | null | false | true |  |
| 🟢 | NOVO | Air Bike (Steady State) | Air bike | cardio | null | null | null | false | true |  |

---

## Casos 🟡 agrupados por critério (Fase 4.6)

> Perguntas agrupadas por critério clínico (Seção 9.1 Etapa 3).
> Uma resposta genérica resolve N exercícios. Será respondido por Bernardo na Fase 4.6.

### equipamento_grupo em adutores (1 exercícios)

- **Copenhagen Adduction** — proposta: `corporal`. Dúvida: banco reto como ancoragem = bodyweight; alternativa: null pois o banco não é o vetor de carga

### equipamento_grupo em ombro (1 exercícios)

- **Elevação Frontal Anilha** — proposta: `halter`. Dúvida: anilha segurada nas extremidades = free weight análogo a halter; alternativa: null

### equipamento_grupo em perna_posterior (5 exercícios)

- **Flexão Joelhos Feijão** — proposta: `corporal`. Dúvida: feijão = rolo de espuma/feijão de espuma sob pé; próximo de corporal; não tem analogia exata nos 8 grupos
- **Flexão Joelhos Slide** — proposta: `corporal`. Dúvida: slide board sob pé; não é nenhum dos 8 grupos exatos; corporal é o mais próximo
- **Hip Thrust Uni.** — proposta: `corporal`. Dúvida: eq_primario NaN — sem equipamento (peso corporal)? Confirmar se usa barra/band ou bodyweight
- **Lev. Terra Anilha** — proposta: `halter`. Dúvida: eq_primario='suporte anilhas' → anilha livre na mão ≈ halter (free weight); ou null se sem analogia
- **Ponte Unilateral** — proposta: `corporal`. Dúvida: eq_primario NaN — bodyweight com suporte?

### pegada em ombro (2 exercícios)

- **Desenv. Landmine** — proposta: `neutra`. Dúvida: landmine press = 1 mão segurando ponta da barra = grip neutro; alternativa: pronada se considerarmos pressing pattern
- **Face Pull (Polia)** — proposta: `aberta`. Dúvida: corda de Face Pull = grip aberto (mãos separadas); alternativa: neutra se considerarmos supinação na puxada

### pegada em panturrilha (2 exercícios)

- **Elevação De Panturrilha Em Pé** — proposta: `null`. Dúvida: barbell sobre ombros, mãos seguram barra = pronada. Mas panturrilha não está na lista null da Seção 7.3; clinicamente a pegada não diferencia exercícios de panturrilha → proposta: null
- **Elevação Unilateral Panturrilha** — proposta: `null`. Dúvida: idem acima

### plano_corporal em perna_posterior (1 exercícios)

- **Hiperextensão 45°** — proposta: `em_pe`. Dúvida: banco romano 45° ≈ em_pe mas ângulo intermediário — não é nem em_pe puro nem deitado; proposta: em_pe
