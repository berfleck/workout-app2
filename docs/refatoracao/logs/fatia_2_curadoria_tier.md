# Curadoria da coluna `tier` — Fatia 2 Parte 1

**Data**: 2026-05-23
**Branch/commit**: pendente (a commitar agora)
**Arquivos modificados**: `banco_exercicios.xlsx` (+ coluna `tier` posição 9, 147/147 preenchidas), `banco_exercicios - pre tier.xlsx` (backup)
**Status**: ✅ curadoria concluída em sessão única

---

## O que este documento é

Estado **final** da coluna `tier` no XLSX após curadoria manual do Bernardo sobre o pré-preenchimento heurístico. Serve como:

1. Registro auditável das decisões clínicas tomadas (referência pra Parte 2 e futuras sessões).
2. Fonte de verdade do tier de cada um dos 147 exercícios do banco.
3. Documentação do delta entre a heurística (`gerador_csp.derivar_tier_heuristico`) e a curadoria humana — quantifica quanto a heurística erra e onde.

---

## Distribuição final

| Tier | Quantidade | % |
|---|---:|---:|
| Principal | 52 | 35.4% |
| Intermediário | 26 | 17.7% |
| Acessório | 69 | 46.9% |
| **Total** | **147** | **100.0%** |

## Delta vs heurística

A heurística (`purpose + padrão é âncora + subregião`) pré-preencheu 84 Principal / 0 Intermediário / 63 Acessório. A curadoria humana fez **42 ajustes** (28.6% do banco).

### Tabela-resumo das transições

| De → Para | Quantidade |
|---|---:|
| Acessório → Intermediário | 8 |
| Acessório → Principal | 1 |
| Principal → Acessório | 15 |
| Principal → Intermediário | 18 |

### Cada transição em detalhe

#### Acessório → Intermediário (8)

| Subregião | Padrão | Exercício | purpose |
|---|---|---|---|
| costas | puxadas | Pulldown Braço Estendido | isolation |
| costas | puxadas | Pullover Halteres | isolation |
| costas | puxadas | Pullover Polia | isolation |
| ombro | ombro_isolado | Elevação Lateral | isolation |
| ombro | ombro_isolado | Elevação Lateral Polia | isolation |
| ombro | ombro_isolado | Elevação Lateral Sentado | isolation |
| perna_posterior | knee_flexion | Flexão Joelhos Feijão | isolation |
| perna_posterior | knee_flexion | Flexão Joelhos Slide | isolation |

#### Acessório → Principal (1)

| Subregião | Padrão | Exercício | purpose |
|---|---|---|---|
| perna_posterior | hinge | Hip Thrust | isolation |

#### Principal → Acessório (15)

| Subregião | Padrão | Exercício | purpose |
|---|---|---|---|
| perna_posterior | abduction | Desloc. Lateral c/ Band | compound |
| core_isometrico | flexao_lateral | Prancha Lateral | stability |
| core_isometrico | flexao_quadril | Dead Bug | stability |
| core_isometrico | flexao_quadril | Dead Bug C/ Anilha | stability |
| core_isometrico | flexao_quadril | Dead Bug C/ Bola | stability |
| core_isometrico | flexao_tronco | Hollow Hold | stability |
| core_isometrico | flexao_tronco | Prancha | stability |
| core_isometrico | flexao_tronco | Prancha Alternada | stability |
| core_isometrico | flexao_tronco | Prancha Bola | stability |
| core_isometrico | flexao_tronco | Prancha Feijao | stability |
| core_isometrico | flexao_tronco | Prancha Renegade | stability |
| core_isometrico | flexao_tronco | Prancha Slideboard | stability |
| core_isometrico | flexao_tronco | Roda Abdominal | stability |
| core_isometrico | rotacao_tronco | Pallof Press | stability |
| core_dinamico | flexao_quadril | Canoinha | stability |

#### Principal → Intermediário (18)

| Subregião | Padrão | Exercício | purpose |
|---|---|---|---|
| peito | empurrar_compostos | Apoio | compound |
| peito | empurrar_compostos | Apoio Ajoelhado | compound |
| peito | empurrar_compostos | Apoio Elevado | compound |
| peito | empurrar_compostos | Apoio Fechado | compound |
| peito | empurrar_compostos | Supino Com Anilha | compound |
| peito | empurrar_compostos | Supino Fechado | compound |
| costas | puxadas | Barra C/ Borracha | compound |
| costas | puxadas | Barra Isométrica | compound |
| ombro | ombro_composto | Desenv. Halteres Uni. | compound |
| ombro | ombro_composto | Desenv. Landmine | compound |
| ombro | ombro_composto | Desenvolvimento Smith | compound |
| perna_anterior | squat_bilateral | Agachamento Goblet | compound |
| perna_anterior | squat_bilateral | Agachamento Goblet Rampa | compound |
| perna_anterior | squat_bilateral | Agachamento Smith | compound |
| perna_anterior | squat_bilateral | Agachamento Smith Rampa | compound |
| perna_anterior | squat_unilateral | Agach. Lateral | compound |
| perna_anterior | squat_unilateral | Slide Board Lateral | compound |
| perna_posterior | hinge | Lev. Terra Anilha | compound |


### Padrões de decisão observados

- **Core stability rebaixado em bloco para Acessório** (15 exercícios — todos `flexao_tronco`, `flexao_quadril`, `flexao_lateral`, `rotacao_tronco` + `Desloc. Lateral c/ Band`). Decisão estrutural: `purpose=stability` mesmo em subregião core não justifica tier Principal pela régua clínica do Bernardo.
- **Variantes assistidas / equipamento limitante migraram para Intermediário** (Apoios, Goblet, Smith em squat_bilateral e ombro_composto, Anilha, Borracha, Isométrica, Slide Board Lateral). Tier intermediário recebe seu uso "natural" — compound preservado mas teto de carga estruturalmente menor que o clássico do padrão.
- **Pullover / Pulldown Braço Estendido / Elevação Lateral subiram de Acessório para Intermediário** (8 exercícios). Justificativa clínica em `principios_clinicos.md` Conceito 3 (Pullover é "vertical isolado de costas" — não é multi-articular completo mas também não é mero acessório).
- **Hip Thrust (puro) subiu para Principal**, mas as 8 variantes (Band, Uni., Ponte, Ponte Alternada, etc.) mantiveram Acessório. Decisão específica documentada no `notas_cadastro.md` — Hip Thrust standard é central para alunos com foco glúteo dominante.
- **Smith em hinge e remadas permaneceu Principal** (Stiff Barra Smith, Stiff Uni. Smith, Remada Curvada Smith, Supino Smith Inclinado). Smith só foi rebaixado em squat_bilateral e ombro_composto — decisão por padrão, não global.
- **TRX, Landmine de remadas, e várias variantes unilaterais permaneceram Principal** (Remada Aberta/Neutra Trx, Remada LM Aberta/Neutra, Remada Uni Polia, Puxada Unilateral Polia, etc.). Decisão de não-rebaixar — o tier intrínseco é Principal mesmo, o vetor de aluno modula efetivamente o uso.

---

## Tabela completa — agrupada por tier → subregião → padrão → nome

### Principal (52)

| Tier | Subregião | Padrão | Exercício | Purpose | Notas |
|---|---|---|---|---|---|
| Principal | peito | empurrar_compostos | Supino Com Barra | compound |  |
| Principal | peito | empurrar_compostos | Supino Com Halteres | compound |  |
| Principal | peito | empurrar_compostos | Supino Inclinado Halteres | compound |  |
| Principal | peito | empurrar_compostos | Supino Smith Inclinado | compound |  |
| Principal | costas | puxadas | Barra Aberta | compound |  |
| Principal | costas | puxadas | Barra Fixa | compound |  |
| Principal | costas | puxadas | Barra Supinada | compound |  |
| Principal | costas | puxadas | Puxada Aberta | compound |  |
| Principal | costas | puxadas | Puxada Neutra | compound |  |
| Principal | costas | puxadas | Puxada Supinada | compound |  |
| Principal | costas | puxadas | Puxada Unilateral Polia | compound |  |
| Principal | costas | remadas | Remada Aberta Trx | compound |  |
| Principal | costas | remadas | Remada Apoiado | compound |  |
| Principal | costas | remadas | Remada Baixa Aberta | compound |  |
| Principal | costas | remadas | Remada Baixa Neutra | compound |  |
| Principal | costas | remadas | Remada Curvada Barra | compound |  |
| Principal | costas | remadas | Remada Curvada Halteres | compound |  |
| Principal | costas | remadas | Remada Curvada Smith | compound |  |
| Principal | costas | remadas | Remada LM Aberta | compound |  |
| Principal | costas | remadas | Remada LM Neutra | compound |  |
| Principal | costas | remadas | Remada Neutra Trx | compound |  |
| Principal | costas | remadas | Remada Seal Halteres | compound |  |
| Principal | costas | remadas | Remada Uni Polia | compound |  |
| Principal | costas | remadas | Serrote | compound |  |
| Principal | costas | remadas | Serrote Aberto | compound |  |
| Principal | ombro | ombro_composto | Desenv. Halteres Sentado | compound |  |
| Principal | ombro | ombro_composto | Desenvolvimento Barra | compound |  |
| Principal | perna_anterior | squat_bilateral | Agachamento Livre | compound |  |
| Principal | perna_anterior | squat_bilateral | Box Jump | explosive | inativo |
| Principal | perna_anterior | squat_bilateral | Leg Press | compound |  |
| Principal | perna_anterior | squat_unilateral | Agachamento Búlgaro | compound |  |
| Principal | perna_anterior | squat_unilateral | Passada | compound |  |
| Principal | perna_anterior | squat_unilateral | Passada Dos Steps | compound |  |
| Principal | perna_anterior | squat_unilateral | Recuo | compound |  |
| Principal | perna_anterior | squat_unilateral | Recuo Alternado | compound |  |
| Principal | perna_anterior | squat_unilateral | Recuo C/ Barra | compound |  |
| Principal | perna_anterior | squat_unilateral | Recuo do Estepe | compound |  |
| Principal | perna_anterior | squat_unilateral | Step Up | compound |  |
| Principal | perna_anterior | squat_unilateral | Step Up Alt. | compound |  |
| Principal | perna_anterior | squat_unilateral | Walking Lunges | compound |  |
| Principal | perna_posterior | hinge | Good Morning | compound |  |
| Principal | perna_posterior | hinge | Hip Thrust | isolation | curado de Acessório |
| Principal | perna_posterior | hinge | Hiperextensão 45° | compound |  |
| Principal | perna_posterior | hinge | Lev. Terra | compound |  |
| Principal | perna_posterior | hinge | Lev. Terra Sumô | compound |  |
| Principal | perna_posterior | hinge | Stiff B-Stance | compound |  |
| Principal | perna_posterior | hinge | Stiff Barra Livre | compound |  |
| Principal | perna_posterior | hinge | Stiff Barra Smith | compound |  |
| Principal | perna_posterior | hinge | Stiff Halteres | compound |  |
| Principal | perna_posterior | hinge | Stiff Uni. Halteres | compound |  |
| Principal | perna_posterior | hinge | Stiff Uni. Smith | compound |  |
| Principal | cardio | cardio | Air Bike (Sprint) | explosive | inativo |

### Intermediário (26)

| Tier | Subregião | Padrão | Exercício | Purpose | Notas |
|---|---|---|---|---|---|
| Intermediário | peito | empurrar_compostos | Apoio | compound | curado de Principal |
| Intermediário | peito | empurrar_compostos | Apoio Ajoelhado | compound | curado de Principal |
| Intermediário | peito | empurrar_compostos | Apoio Elevado | compound | curado de Principal |
| Intermediário | peito | empurrar_compostos | Apoio Fechado | compound | curado de Principal |
| Intermediário | peito | empurrar_compostos | Supino Com Anilha | compound | curado de Principal |
| Intermediário | peito | empurrar_compostos | Supino Fechado | compound | curado de Principal |
| Intermediário | costas | puxadas | Barra C/ Borracha | compound | curado de Principal |
| Intermediário | costas | puxadas | Barra Isométrica | compound | curado de Principal |
| Intermediário | costas | puxadas | Pulldown Braço Estendido | isolation | curado de Acessório |
| Intermediário | costas | puxadas | Pullover Halteres | isolation | curado de Acessório |
| Intermediário | costas | puxadas | Pullover Polia | isolation | curado de Acessório |
| Intermediário | ombro | ombro_composto | Desenv. Halteres Uni. | compound | curado de Principal |
| Intermediário | ombro | ombro_composto | Desenv. Landmine | compound | curado de Principal |
| Intermediário | ombro | ombro_composto | Desenvolvimento Smith | compound | curado de Principal |
| Intermediário | ombro | ombro_isolado | Elevação Lateral | isolation | curado de Acessório |
| Intermediário | ombro | ombro_isolado | Elevação Lateral Polia | isolation | curado de Acessório |
| Intermediário | ombro | ombro_isolado | Elevação Lateral Sentado | isolation | curado de Acessório |
| Intermediário | perna_anterior | squat_bilateral | Agachamento Goblet | compound | curado de Principal |
| Intermediário | perna_anterior | squat_bilateral | Agachamento Goblet Rampa | compound | curado de Principal |
| Intermediário | perna_anterior | squat_bilateral | Agachamento Smith | compound | curado de Principal |
| Intermediário | perna_anterior | squat_bilateral | Agachamento Smith Rampa | compound | curado de Principal |
| Intermediário | perna_anterior | squat_unilateral | Agach. Lateral | compound | curado de Principal |
| Intermediário | perna_anterior | squat_unilateral | Slide Board Lateral | compound | curado de Principal |
| Intermediário | perna_posterior | hinge | Lev. Terra Anilha | compound | curado de Principal |
| Intermediário | perna_posterior | knee_flexion | Flexão Joelhos Feijão | isolation | curado de Acessório |
| Intermediário | perna_posterior | knee_flexion | Flexão Joelhos Slide | isolation | curado de Acessório |

### Acessório (69)

| Tier | Subregião | Padrão | Exercício | Purpose | Notas |
|---|---|---|---|---|---|
| Acessório | peito | empurrar_isolados | Crossover | isolation |  |
| Acessório | peito | empurrar_isolados | Crossover Sentado | isolation |  |
| Acessório | peito | empurrar_isolados | Crucifixo Halteres | isolation |  |
| Acessório | peito | empurrar_isolados | Crucifixo Inclinado Halteres | isolation |  |
| Acessório | ombro | ombro_isolado | Elevação Frontal Anilha | isolation |  |
| Acessório | ombro | ombro_isolado | Elevação Frontal Halteres | isolation |  |
| Acessório | ombro | posterior_ombro | Crucifíxo Invertido | isolation |  |
| Acessório | ombro | posterior_ombro | Face Pull (Polia) | isolation |  |
| Acessório | ombro | posterior_ombro | Posterior Ombro Polia | isolation |  |
| Acessório | bracos | biceps | Bíceps 21S | isolation |  |
| Acessório | bracos | biceps | Bíceps Banco | isolation |  |
| Acessório | bracos | biceps | Bíceps Bayesian | isolation |  |
| Acessório | bracos | biceps | Bíceps Cabo | isolation |  |
| Acessório | bracos | biceps | Bíceps Halteres | isolation |  |
| Acessório | bracos | biceps | Bíceps Martelo | isolation |  |
| Acessório | bracos | triceps | Tríceps Coice Com Halter | isolation |  |
| Acessório | bracos | triceps | Tríceps Coice Polia | isolation |  |
| Acessório | bracos | triceps | Tríceps Corda | isolation |  |
| Acessório | bracos | triceps | Tríceps Francês | isolation |  |
| Acessório | bracos | triceps | Tríceps Francês Corda | isolation |  |
| Acessório | bracos | triceps | Tríceps Mergulho Banco | isolation |  |
| Acessório | bracos | triceps | Tríceps Polia Alta | isolation |  |
| Acessório | bracos | triceps | Tríceps Testa Halteres | isolation |  |
| Acessório | bracos | triceps | Tríceps Unilateral Polia | isolation |  |
| Acessório | perna_anterior | knee_extension | Cadeira Extensora | isolation |  |
| Acessório | perna_posterior | abduction | Abdução Polia | isolation |  |
| Acessório | perna_posterior | abduction | Desloc. Lateral c/ Band | compound | curado de Principal |
| Acessório | perna_posterior | abduction | Side Clams | isolation |  |
| Acessório | perna_posterior | hinge | Hip Thrust C/ Band | isolation |  |
| Acessório | perna_posterior | hinge | Hip Thrust Uni. | isolation |  |
| Acessório | perna_posterior | hinge | Kickback Polia | isolation |  |
| Acessório | perna_posterior | hinge | Ponte | isolation |  |
| Acessório | perna_posterior | hinge | Ponte Alternada | isolation |  |
| Acessório | perna_posterior | hinge | Ponte C/ Band | isolation |  |
| Acessório | perna_posterior | hinge | Ponte Na Caixa | isolation |  |
| Acessório | perna_posterior | hinge | Ponte Uni. Caixa | isolation |  |
| Acessório | perna_posterior | hinge | Ponte Unilateral | isolation |  |
| Acessório | perna_posterior | knee_flexion | Cadeira Flexora | isolation |  |
| Acessório | perna_posterior | knee_flexion | Nordic Curl | isolation |  |
| Acessório | adutores | adduction | Adução Polia | isolation |  |
| Acessório | adutores | adduction | Copenhagen Adduction | isolation |  |
| Acessório | panturrilha | flexao_plantar | Elevação De Panturrilha Em Pé | isolation |  |
| Acessório | panturrilha | flexao_plantar | Elevação Unilateral Panturrilha | isolation |  |
| Acessório | core_isometrico | flexao_lateral | Prancha Lateral | stability | curado de Principal |
| Acessório | core_isometrico | flexao_quadril | Dead Bug | stability | curado de Principal |
| Acessório | core_isometrico | flexao_quadril | Dead Bug C/ Anilha | stability | curado de Principal |
| Acessório | core_isometrico | flexao_quadril | Dead Bug C/ Bola | stability | curado de Principal |
| Acessório | core_isometrico | flexao_tronco | Hollow Hold | stability | curado de Principal |
| Acessório | core_isometrico | flexao_tronco | Prancha | stability | curado de Principal |
| Acessório | core_isometrico | flexao_tronco | Prancha Alternada | stability | curado de Principal |
| Acessório | core_isometrico | flexao_tronco | Prancha Bola | stability | curado de Principal |
| Acessório | core_isometrico | flexao_tronco | Prancha Feijao | stability | curado de Principal |
| Acessório | core_isometrico | flexao_tronco | Prancha Renegade | stability | curado de Principal |
| Acessório | core_isometrico | flexao_tronco | Prancha Slideboard | stability | curado de Principal |
| Acessório | core_isometrico | flexao_tronco | Roda Abdominal | stability | curado de Principal |
| Acessório | core_isometrico | rotacao_tronco | Pallof Press | stability | curado de Principal |
| Acessório | core_dinamico | flexao_quadril | Canoinha | stability | curado de Principal |
| Acessório | core_dinamico | flexao_quadril | Infra Alternado | isolation |  |
| Acessório | core_dinamico | flexao_quadril | Infra Chão | isolation |  |
| Acessório | core_dinamico | flexao_quadril | Infra Roll-Up | isolation |  |
| Acessório | core_dinamico | flexao_quadril | Infra Suspenso | isolation |  |
| Acessório | core_dinamico | flexao_quadril | V-Up | isolation |  |
| Acessório | core_dinamico | flexao_quadril | V-Up Unilateral | isolation |  |
| Acessório | core_dinamico | flexao_tronco | Abd Bicicleta | isolation |  |
| Acessório | core_dinamico | flexao_tronco | Crunch Chão | isolation |  |
| Acessório | core_dinamico | flexao_tronco | Crunch Na Bola | isolation |  |
| Acessório | core_dinamico | flexao_tronco | Crunch No Cabo | isolation |  |
| Acessório | core_dinamico | rotacao_tronco | Russian Twist | isolation |  |
| Acessório | cardio | cardio | Air Bike (Steady State) | stability | inativo |

---

## Validação técnica

- 147/147 linhas preenchidas (0 vazias)
- 0 valores fora do vocabulário (`Principal` / `Intermediário` / `Acessório`)
- `gerador_treino.carregar_banco()` continua carregando 144 ativos sem regressão (coluna `tier` ignorada pelo gerador antigo, esperado)
- `gerador_csp.carregar_banco_ativo()` carrega os mesmos 144 ativos

## Próximo passo (Fatia 2 Parte 2)

Implementar H-T1, H-T2, H-T3, H-R1 em `gerador_csp.py`, substituindo `derivar_tier_heuristico` por leitura direta da coluna `tier` agora curada. O dataclass `Exercicio` precisa ganhar campo `tier: str`; `gerador_treino.carregar_banco` precisa popular esse campo. Detalhes pendentes pra essa sessão.
