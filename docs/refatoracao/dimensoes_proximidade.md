# Dimensões de proximidade — especificação para Etapa 7

> **Status:** parcial — Fase 1 (análise dos 8 grupos) completa. Fases 2-4
> pendentes (derivação final, calibração de pesos, estratégia de
> preenchimento). Documento será expandido na próxima sessão.
>
> **Histórico de correções pós-Fase 1 (2026-05-05):**
> Auditoria do user identificou 2 erros de consolidação:
> 1. **`angulo_movimento` desaparecido** — decidido como dimensão nos
>    Supinos (G1) e descartado na consolidação sem justificativa.
> 2. **Inconsistência INTER em Supinos** — respostas G1 P5 do user
>    pressupunham que 3 supinos podem coexistir em rotina de 3 treinos
>    (com pelo menos 1 inclinado), o que é incompatível com família
>    `Supino` única + hard filter INTER.
>
> **Correção aplicada (Caminho B):**
> - Família `Supino` refinada em `Supino Reto` + `Supino Inclinado`
> - `plano_corporal` em supinos = reto / inclinado (absorve
>   `angulo_movimento`; sem dimensão extra)
> - `equipamento_grupo` mantido como dimensão de proximidade com peso
>   BAIXO INTRA (tiebreaker — desempata pares iguais nas outras
>   dimensões)
> - Set final = 5 dimensões: `familia_estrita` + `lateralidade` +
>   `pegada` + `plano_corporal` + `equipamento_grupo`
>
> Este documento substitui o sistema atual de `variacao_de` sobrecarregado
> por dimensões multi-dimensionais explícitas. Especifica:
> 1. Os 8 grupos analisados (Fase 1 — esta versão)
> 2. As 5 dimensões finais (Fase 2 — pendente)
> 3. Pesos INTRA / INTER / HISTÓRICO por dimensão (Fase 3 — pendente)
> 4. Estratégia de preenchimento dos 125+ exercícios (Fase 4 — pendente)
>
> Documento mestre: `docs/refatoracao/guia_refatoracao_v4.md` (Etapa 6).

---

## 1. Princípios e diretrizes consolidados

### 1.1 Princípio do gerador como "base" — ESCOPO, não rigor

O gerador entrega a **melhor base possível**, não decisões perfeitas. O
personal sempre pode (e provavelmente vai) editar o treino para
customizar detalhes específicos. Isso justifica simplificações em vários
grupos: tags que capturam "a maioria dos casos" são suficientes; nuances
raras ficam para customização manual.

**IMPORTANTE — distinção entre escopo e rigor (anti-padrão a evitar):**

O princípio "gerador como base" aplica-se a **escopo** (quais decisões
clínicas modelar), **não a rigor** (quanto investir nas decisões que
escolhemos modelar). Os dois soam parecido em prosa, mas operacionalmente
são opostos:

- **Escopo:** "não vamos modelar a 6ª, 7ª, 8ª nuance — gerador entrega o
  suficiente, personal cobre o resto." ✅ Aplicação correta.
- **Rigor:** "se algo é difícil de modelar, simplifica e vira
  responsabilidade do personal." ❌ Regressão silenciosa.

A diferença operacional:
- **Escopo correto:** "modela bem o que decidimos modelar, e o personal
  cobre o resto."
- **Rigor regressivo:** "modela frouxo o que decidimos modelar, e o
  personal corrige depois."

**Diretriz de registro (anti-luva):**

- Quando o user pede modelagem ativa de um caso, **registrar como
  modelagem ativa** — penalty explícita, dimensão dedicada, ou regra
  estrutural.
- Quando o user aceita não modelar um caso, **registrar explicitamente
  como dívida aceita com justificativa**.
- **Substituir modelagem ativa por "personal edita" silenciosamente é
  regressão**, mesmo se motivada por princípio de simplificação.

**Implicação prática para todas as Fases:** dimensões não precisam
cobrir 100% dos casos clínicos. Cobrir o que decidimos modelar com
**rigor** + cobrir os 20% de borda via edição manual. Não confundir
"cobrir 80%" (escopo) com "cobrir frouxamente" (rigor).

### 1.2 Pesos POR GRUPO/SUBREGIÃO (não globais)

Decisão estrutural validada com evidência clínica em múltiplos grupos:

- **Lateralidade INTRA:** Crítico em remadas, Médio em squats, Médio em
  hinges. Forçar peso global daria "média" inadequada.
- **Plano corporal INTRA:** Alto em hinges (em pé vs deitado), Médio em
  remadas (5 sub-planos), ausente em squats.
- **Pegada:** alta em supinos/remadas/puxadas; não aplica em squats,
  hinges, knee_flex, tríceps, pranchas.

**Implementação na Etapa 7:** estrutura de configuração permite override
de peso por dimensão dentro de cada grupo (provavelmente por
`subregiao` ou `padrao`). Default global existe como fallback.

### 1.3 INTRA, INTER e HISTÓRICO

Três contextos de proximidade com pesos distintos:

- **INTRA** — mesmo treino. Vetor primário de variabilidade biomecânica
  imediata. Pesos altos em dimensões críticas.
- **INTER** — mesma rotina semanal, entre treinos diferentes. Pesos
  médios. Família estrita continua hard. Dimensões menos críticas
  (equipamento, lateralidade) com peso baixo.
- **HISTÓRICO** — rotinas anteriores do aluno. **Decisão tomada nesta
  etapa que ALTERA o guia v4:** janela = apenas R-1 (rotina anterior à
  atual), peso integral, sem decaimento contínuo. Penalty alta com
  fallback por escassez/âncora obrigatória. **UI: toggle ON/OFF**, não
  slider de 4 níveis ("alta/média/baixa/desligado") como o guia v4
  propunha.

  Justificativa: simplifica drasticamente a calibração e a UI. Caso o
  comportamento "lembrar de 4-6 semanas atrás" se mostrar necessário,
  reabre na Etapa 7 — é dívida aceita.

### 1.4 Família estrita é HARD filter

`familia_estrita` (refinamento do `variacao_de` atual) opera como hard
filter em INTRA e INTER. Não é tag de penalidade — bloqueia diretamente.

**Diretriz para curadoria de famílias estritas (Fase 2/Etapa 7):**

- Famílias devem refletir **variações biomecânicas estritas** do mesmo
  exercício (Slide ≈ Feijão), não categoria muscular ampla (não fazer
  todos os tríceps com `variacao_de = "Tríceps"`).
- **Lateralidade NÃO faz parte da família estrita** — é dimensão
  separada. Famílias gêmeas bi/uni unificam (ex: `stiff` + `stiff uni`
  viram `stiff` único; `Recuo` + `Recuo Alternado` já estão unificados).
- Famílias podem ser refinadas para distinguir mecânicas
  significativamente diferentes (ex: separar `prancha frontal` de
  `prancha lateral` — anti-extensão vs anti-lateroflexão).

### 1.5 Escopo de aplicação das penalidades (importante — não confundir
com "cobertura universal")

Cada dimensão tem um **escopo lógico** dentro do qual a penalidade
dispara. Fora desse escopo, peso = 0. **Cobertura universal** (toda
linha do banco recebe tag) é coisa diferente de **escopo de aplicação**
(quais pares de exercícios sofrem penalidade).

**Proposta de escopos:**

| Dimensão | Escopo de aplicação | Peso INTRA típico |
|---|---|---|
| `familia_estrita` | **Universal (hard global)** — mesma família bloqueia em qualquer combinação, independente de subregião | Hard |
| `equipamento_grupo` | **Mesma subregião** — Supino+Curvada não dispara (peito vs costas); Supino+Crucifixo dispara (ambos peito) | **Baixo (tiebreaker)** |
| `pegada` | **Mesma subregião** — só faz sentido entre exercícios biomecanicamente comparáveis | Alto (com matriz custom) |
| `plano_corporal` | **Mesma subregião** — em pé vs deitado em hinges; curvada vs baixa em remadas; reto vs inclinado em supinos | Alto (em grupos onde aplica) |
| `lateralidade` (anti_uni) | **Mesmo grupo muscular padrão** (já definido em `GRUPO_MUSCULAR_PADRAO` da Etapa 5) — granularidade ainda mais fina que subregião | Crítico/Médio (varia por grupo) |

> **Sobre `equipamento_grupo` como tiebreaker (peso BAIXO INTRA):**
> validação clínica em 12 cenários (4 cross-grupo + 8 dentro-grupo)
> mostrou que equipamento entre exercícios CLINICAMENTE DIVERSOS
> (composto+isolado, padrões diferentes, etc.) NÃO incomoda — outras
> dimensões dominam o score. Mas em pares onde **família, plano e
> pegada empatam** (ex: Reto Halteres vs Reto Barra como candidatos
> após Inclinado Halteres em T1), equipamento é o ÚNICO desempate
> disponível. Peso BAIXO captura essa função sem atrapalhar pares
> diversos.

**Implicação prática:**

- **Supino Reto Barra + Curvada Barra** (peito vs costas, ambos `barra`):
  penalidade equipamento = 0 (subregiões diferentes). OK pelo modelo —
  o fato de ambos usarem barra é coincidência logística, não
  proximidade clínica.
- **Supino Reto Barra + Crucifixo Halteres** (ambos peito): penalidade
  equipamento aplica (subregião igual). Calcula peso × distância.
- **Stiff Halteres + Hip Thrust** (ambos perna_posterior): penalidade
  plano_corporal aplica (mesma subregião). Em pé vs deitado = distância
  máxima = penalidade ≈ 0 (mesmo escopo, mas distância grande).
- **Stiff Halteres + Apoio** (perna_posterior vs peito): nenhuma
  penalidade biomecânica dispara (subregiões diferentes). OK.

**Casos especiais:**

- `angulo_movimento` em supinos foi confirmado como **transversal entre
  compostos e isolados de peito** (mesma subregião) — ainda dentro do
  escopo "mesma subregião".
- Família estrita é o único hard filter realmente global. Se 2
  exercícios têm a mesma família (improvável entre subregiões
  diferentes, mas hipotético), bloqueia em qualquer caso.

### 1.6 Equipamento_grupo — cobertura cross-grupo

Toda linha do banco recebe `equipamento_grupo`. **8 níveis nomeados +
vazio** consolidados ao longo da Fase 1. Cobertura cross-grupo significa
que os MESMOS valores aparecem em diferentes grupos (`barra` em supinos,
remadas, squats, hinges) — facilita curadoria e regra de cadastro.

A penalidade entre exercícios com mesmo equipamento só dispara dentro do
escopo definido em 1.5 (mesma subregião).

| Nível | Identidade clínica | Aparece em |
|---|---|---|
| `barra` | barra olímpica livre | Supinos, Remadas, Puxadas (não), Squats, Hinges |
| `barra_guiada` | Smith e similares (trilho fixo) | Supinos, Remadas, Squats, Hinges |
| `halter` | halteres, peso livre simétrico | Supinos, Remadas, Pullovers, Squats, Hinges, Tríceps |
| `polia` | máquina de polia, cabos | Remadas, Puxadas, Crossovers, Tríceps |
| `corporal` | peso corporal estável (apoios, pontes simples) | Supinos, Hinges, Pranchas, Tríceps Mergulho |
| `maquina` | máquina dedicada (Cadeira, Leg Press, Hiperextensão) | Squats, Hinges, Knee Flex |
| `caixa` | caixa pliométrica / step / estepe | Squats, Hinges (Pontes na caixa) |
| `banda_elastica` | mini-band, glute band | Hinges (Pontes/Hip Thrust com banda) |
| `(vazio)` | tag não preenchida | TRX, Box Jump, Slide Board (Squats), Slide Board (Pranchas) |

**Regra de precedência semântica para múltiplos elementos:** quando o
exercício combina elementos (ex: Step Up usa caixa + halter), elege-se o
elemento que **mais define a proximidade clínica**. Em Step Up, "caixa"
prevalece sobre "halter" — o objetivo clínico de evitar 2 exercícios "em
cima de caixa" supera evitar 2 exercícios "com halter".

**Casos especiais (vazio é correto):** TRX, Box Jump, Slide Board não
têm equipamento que os aproxime de outros via dimensão de equipamento —
a proximidade vem por outras dimensões (família, plano corporal,
lateralidade) ou por nada (caso especial).

---

## 2. Síntese da Fase 1 — análise dos 8 grupos

### Grupo 1 — Supinos (7 exercícios mapeados)

**Exercícios:** Supino Reto Barra, Supino Reto Halteres, Supino Reto
Anilha, Supino Smith Inclinado, Apoio, Apoio Ajoelhado, Apoio Elevado.
Conexão via ângulo: Crucifixo Halteres, Crossover, Crossover Sentado.

**Família estrita refinada por ângulo (Caminho B aprovado):** a família
genérica `Supino` é dividida em **`Supino Reto`** e **`Supino
Inclinado`** (split por ângulo). Justificativa: rotina de 3 treinos
de peito pode ter 3 supinos (1 inclinado + 2 retos com equipamentos
diferentes, P5 do G1) — incompatível com família única + hard filter
INTER. Refinamento resolve.

**Tags por exercício:**

| Dimensão | Aplica | Notas |
|---|---|---|
| `familia_estrita` | ✓ | **`Supino Reto`** (Reto Barra/Halteres/Anilha), **`Supino Inclinado`** (Smith Inclinado), `Apoio`, `Crucifixo`, `crossover` |
| `equipamento_grupo` | ✓ tiebreaker | barra / barra_guiada / halter / corporal — peso BAIXO INTRA, desempata pares iguais nas outras dimensões |
| `lateralidade` | ✓ (todos bi hoje) | bilateral |
| `pegada` | 🟡 | hoje implícito (todos pronada-padrão); cadastros futuros: Apoio Fechado, Supino Fechado |
| `plano_corporal` | ✓ **(absorve `angulo_movimento`)** | **reto / inclinado** (2 níveis); transversal entre compostos e isolados de peito; aceita vazio em Apoios |

> **Nota:** `angulo_movimento` (proposto inicialmente como dimensão
> separada) foi **absorvido em `plano_corporal`** com valores específicos
> em supinos (`reto` / `inclinado`). Mantém set de 5 dimensões e captura
> a transversalidade (Crucifixo Reto + Supino Reto = mais incomoda que
> Crucifixo Reto + Supino Inclinado).

**Calibração inicial:**

| Dimensão | INTRA | INTER | HISTÓRICO (R-1) |
|---|---|---|---|
| `familia_estrita` | Crítico (hard) | Crítico (hard) | Crítico (toggle) |
| `plano_corporal` (reto/inclinado) | **Alto** | **Médio-alto** (3 retos = Ruim) | Médio |
| `equipamento_grupo` | **Baixo (tiebreaker)** | Baixo | Baixo |
| `pegada` | (a definir) | (a definir) | (a definir) |
| `lateralidade` | Médio (anti_uni — ocioso hoje, todos bi) | Baixo | 0 |

**Cenário de validação (caso supino-inclinado-em-T1):**

- T1 tem **Supino Inclinado Halteres** (família `Supino Inclinado`,
  plano `inclinado`, eq `halter`)
- App escolhe próximo peito de T1 ou T2:
  - **Supino Reto Halteres**: família ≠ ✓; plano ≠ (penalty alta) ✓;
    pegada igual; eq igual → score médio
  - **Supino Reto Barra**: família ≠ ✓; plano ≠ ✓; pegada igual; eq
    diferente → **score MELHOR (eq diferente desempata)**
- App escolhe Reto Barra preferencialmente. **Clinicamente correto.**

**Decisões clínicas registradas:**

- **Hierarquia INTRA:** ângulo > equipamento. Reto Barra + Reto Halteres
  = Ruim (mesmo ângulo). Reto Halteres + Smith Inclinado = OK (ambos
  diferem).
- **`angulo_movimento` é dimensão TRANSVERSAL** — atravessa
  `empurrar_compostos` e `empurrar_isolados`. Crucifixo Reto + Supino
  Reto incomoda mais que Crucifixo Reto + Supino Inclinado, mesmo entre
  composto e isolado.
- **`angulo_movimento` aceita vazio.** Apoios não usam (Apoio Elevado é
  tecnicamente "inclinado" mas distinção não é clinicamente relevante
  para apoios).

**Nuances aceitas como dívida:**

- **Barra ≈ Smith** mais que Barra ≈ Halter (estabilidade livre vs
  guiado não capturada). Aceitável omitir na 1ª iteração.

**Caso clínico INTRA — tabela validada:**

| Par | Diferença (ângulo, eq) | Veredicto |
|---|---|---|
| Reto Barra + Reto Halteres | (0, 1) | Ruim |
| Reto Barra + Smith Inclinado | (1, 2) | Tolerável (nuance barra≈smith) |
| Reto Halteres + Smith Inclinado | (1, 1) | OK |
| Reto Barra + Reto Anilha | (0, 2) | Tolerável |

---

### Grupo 2 — Remadas (12 exercícios mapeados)

**Exercícios:** Curvada Barra, Curvada Halteres, Curvada Smith, Landmine
(→ split LM Neutra + LM Aberta após conserto), Baixa Aberta, Baixa
Neutra, Apoiado, Seal Halteres, Uni Polia, Serrote, Aberta TRX, Neutra
TRX.

**Tags por exercício:**

| Dimensão | Valores em Remadas | Notas |
|---|---|---|
| `familia_estrita` | curvada (após consertos), baixa (unificada), apoiado, seal, unilateral, trx | Landmine→curvada; Baixa Aberta+Neutra unificam |
| `pegada` | aberta / neutra / pronada / supinada (até 4 níveis) | Sub-estrutura: aberta=pronada-wide |
| `plano_corporal` | curvada / baixa_sentada / apoiada / unilateral_apoiada / suspensao | 5 níveis |
| `equipamento_grupo` | barra / barra_guiada / halter / polia / (vazio TRX) | herda 8-níveis universal |
| `lateralidade` | bilateral / unilateral | Serrote, Uni Polia, Landmine = uni |

**Calibração inicial:**

| Dimensão | INTRA | INTER | HISTÓRICO (R-1) |
|---|---|---|---|
| `familia_estrita` | Crítico (hard) | Crítico (hard) | Crítico (toggle) |
| `lateralidade` | **Crítico (~hard)** | **Baixo (regra fraca)** | 0 |
| `pegada` | Alto | Alto | Médio |
| `plano_corporal` | Médio | Médio-alto (3 iguais = Ruim) | Baixo |
| `equipamento_grupo` | Médio | Baixo | Baixo |

**Decisões clínicas registradas:**

- **Hierarquia INTRA:** Lateralidade (crítico, ~hard) > Pegada (alto) >
  Plano corporal ≈ Equipamento (médios).
- **Lateralidade INTRA é regra quase-hard:** "NUNCA 2 unilaterais do
  mesmo grupo no mesmo treino, independente de pegada." Implementação
  na Etapa 7 pode unificar com `anti_uni_mesmo_grupo` da Etapa 5.
- **Lateralidade INTER ≈ baixo:** Serrote em T1 + Uni Polia em T2 = OK.
  Variação entre treinos é desejável. Mas regra fraca de
  diversificação: rotina multi-treino "deveria ter ≥1 unilateral".
- **Pegada > Plano corporal biomecanicamente** (hierarquia "real" das
  dimensões), mas lateralidade tem regra operacional INTRA mais
  rígida.
- **`plano_corporal = curvada` tem componente de carga lombar/core já
  capturado pelo filtro hard da Etapa 4** — peso INTRA de plano não
  precisa cobrir esse aspecto. Boa descoberta arquitetural: dimensões
  não devem duplicar trabalho do filtro de cargas.
- **Pegada com sub-estrutura interna** (insight central):
  `aberta = pronada-wide`; pronada = pronada-fechada. Pareamento
  Curvada Barra + Baixa Aberta (ambas "pronadas-largas") = Tolerável
  apesar de diferirem em plano + equipamento.

**Caso clínico INTRA validado:**

| Par | Veredicto | Motivo |
|---|---|---|
| Curvada Barra + Curvada Halteres | Ruim | só equipamento difere; ambos curvada+pronada |
| Curvada Barra + Baixa Aberta | Tolerável | quase tudo difere mas ambos pronada-larga |
| Baixa Aberta + Baixa Neutra | Ruim | só pegada (após conserto: mesma família) |
| Serrote + Uni Polia | Ruim | 2 unis (anti_uni hard) |
| Curvada Halteres + Apoiado | Ruim | mesma pegada+equipamento, plano diferente |
| Aberta TRX + Curvada Barra | Tolerável | ambos pronada-larga |

---

### Grupo 3 — Puxadas (7 exercícios + 5 cadastros futuros)

**Exercícios atuais:** Barra Fixa, Barra Isométrica, Pullover Halteres,
Pullover Polia, Puxada Aberta, Puxada Neutra, Puxada Supinada.

**Cadastros futuros:** Barra c/ borracha (assistida), Puxada Unilateral
Polia, Pulldown Braço Estendido, Barra Aberta + Barra Supinada
(substituem `Barra` genérica).

**Tags por exercício:**

| Dimensão | Valores em Puxadas | Notas |
|---|---|---|
| `familia_estrita` | `Barra` / `Puxada` / `Pullover` (+ futuras) | Barra Fixa+Iso = mesma família |
| `pegada` | aberta / neutra / supinada (3 níveis aplicáveis) | sem `pronada` fechada em puxadas |
| `equipamento_grupo` | corporal / polia / halter | herda universal |
| `lateralidade` | bilateral (todos hoje); unilateral após cadastros futuros | regra fraca INTER |
| `plano_corporal` | vazio (default) / `pullover` | NÃO universal — só Pullover/Pulldown |

**Calibração inicial:**

| Dimensão | INTRA | INTER | HISTÓRICO (R-1) |
|---|---|---|---|
| `familia_estrita` | Crítico | Crítico | Crítico (toggle) |
| `pegada` | Alto | Alto | Médio |
| `equipamento_grupo` | Médio | Baixo | Baixo |
| `lateralidade` | Médio | Baixo (regra fraca) | 0 |
| `plano_corporal` | Baixo | **Médio (âncora soft "diversificar com pullover")** | Baixo |

**Decisões clínicas registradas:**

- **Hierarquia INTRA:** Pegada > Equipamento ≈ Lateralidade > Plano.
  **Hierarquia DIFERENTE de Remadas** — em puxadas pegada é o vetor
  primário, lateralidade não no topo. Confirma necessidade de pesos
  por grupo.
- **`plano_corporal` é dimensão NÃO-UNIVERSAL.** Pode ter tag vazia em
  grupos onde não diferencia. Em puxadas, só Pullover/Pulldown ganham
  `plano_corporal = pullover`; demais ficam vazios.
- **Pullover/Pulldown como "âncora soft INTER"** — funciona como
  diversificador (3 puxadas verticais com 3 pegadas ainda é Ruim
  porque "faltou unilateral ou pullover"). Mesma família semântica de
  "regra fraca de diversificação" que apareceu em Remadas com
  lateralidade.
- **Família Barra Fixa + Barra Isométrica = mesma família** → hard
  filter cobre. Sem sub-tag de `modo_execucao` (dinâmico vs
  isométrico). Override pedagógico (aluno em progressão para barra
  fixa) é decisão manual, não automatizada.
- **Ordem dos exercícios no bloco/treino é fora do escopo das tags** —
  resolvida por `ordenar_compostos_primeiro` / `ordenar_blocos`.

---

### Grupo 4 — Agachamentos (17 exercícios mapeados)

**Exercícios:** Agachamento Livre, Goblet, Smith, Leg Press, Cadeira
Extensora, Box Jump (6 bilaterais); Búlgaro, Passada, Passada Dos
Steps, Recuo, Recuo Alternado, Recuo C/ Barra, Step Up, Step Up Alt.,
Walking Lunges, Agach. Lateral, Slide Board Lateral (11 unilaterais).

**Tags por exercício:**

| Dimensão | Aplica | Notas |
|---|---|---|
| `familia_estrita` | ✓ | `Agachamento`, `passada`, `Recuo`, `Step up`, `walking lunges`, `agach. lateral`, sem família (Box Jump, Cadeira, Búlgaro, Leg Press) |
| `equipamento_grupo` | ✓ | barra, barra_guiada, halter, maquina, caixa, vazio (Box Jump, Slide Board) |
| `lateralidade` | ✓ | já é padrão refinado (`squat_bilateral` / `squat_unilateral`); peso INTRA = MÉDIO |
| `pegada` | ❌ | não cabe em squats |
| `plano_corporal` | ❌ | lateralidade + família já cobrem |

**Calibração inicial:**

| Dimensão | INTRA | INTER | HISTÓRICO (R-1) |
|---|---|---|---|
| `familia_estrita` | Crítico | Crítico | Crítico (toggle) |
| `lateralidade` | **Médio** (não crítico — bi+uni complementares) | Baixo (regra fraca diversificar) | 0 |
| `equipamento_grupo` | Médio (alto p/ par caixa+caixa) | Baixo | Baixo |

**Decisões clínicas registradas:**

- **Bilateral + unilateral são complementares** em squats (combinação
  recomendada em treinos de perna). Diferente de remadas. Lateralidade
  INTRA = médio, não crítico.
- **Step Up + Passada Dos Steps = Ruim** porque ambos com `caixa` e
  "objetivo da caixa em ambos é o mesmo: aumentar ROM do quadril".
  Confirma a tag `caixa` como tag de equipamento clínica.
- **Box Jump é caso especial de timing, não proximidade** — "explosivo
  exige musculatura fresca" é regra de sequenciamento, não modelada
  via tags. Box Jump pode sair do banco (decisão pendente do user).
- **Sub-distinção uni-estático vs uni-deslocamento** (Búlgaro+Passada =
  Ruim; Búlgaro+Walking Lunges = "menos pior") **NÃO é modelada** —
  aceito como dívida. Sistema atual (`anti_uni_mesmo_grupo`) trata
  ambos como Ruim, sem capturar a nuance "menos pior".
- **Posição_carga não modelada** — já capturada pelo filtro de cargas
  (Etapa 4).

---

### Grupo 5 — Extensão de Quadril (19 exercícios mapeados)

> Renomeado de "Hinges" para nome clinicamente mais preciso. Pontes/Hip
> Thrusts não são tecnicamente hinges, mas todos compartilham extensão
> de quadril como movimento primário.

**Exercícios:** Stiff Barra Livre/Smith/Halteres, Stiff Uni
Halteres/Smith, Lev. Terra (regular/Sumô/Anilha), Hip Thrust (regular/C
Band/Uni), Ponte (regular/Alternada/C Band/Na Caixa/Uni Caixa/Unilateral),
Good Morning, Hiperextensão 45°.

**Tags por exercício:**

| Dimensão | Aplica | Valores |
|---|---|---|
| `familia_estrita` | ✓ chave | `stiff` (após unificação bi+uni), `Levantamento terra`, `Hip thrust`, `ponte`, `stiff` (Good Morning), `Hiperextensão` |
| `pegada` | ❌ | — |
| `plano_corporal` | ✓ | `em_pe` (Stiffs, Lev Terra, Good Morning, Hiperextensão) / `deitado` (Hip Thrusts, Pontes) |
| `equipamento_grupo` | ✓ | barra / barra_guiada / halter / corporal / **banda_elastica** (NOVO) / caixa / maquina |
| `lateralidade` | ✓ | bi/uni |

**Calibração inicial:**

| Dimensão | INTRA | INTER | HISTÓRICO (R-1) |
|---|---|---|---|
| `familia_estrita` | Crítico | Crítico | Crítico (toggle) |
| `plano_corporal` | **Alto** (vetor primário) | **Alto** (3 mesmos = Ruim) | Médio |
| `equipamento_grupo` | Médio | Baixo | Baixo |
| `lateralidade` | Médio | Baixo (regra fraca) | 0 |

**Decisões clínicas registradas:**

- **Plano corporal é vetor primário em hinges** (em pé vs deitado). Em
  outros grupos plano teve peso menor — reforça pesos por grupo.
- **`banda_elastica` introduzida como nível novo de equipamento_grupo**
  (cross-grupo). Aparece em Pontes/Hip Thrust C Band; provável que
  apareça em outros isolados de glúteo, abducão.
- **Diretriz emergente para famílias gêmeas bi/uni:** unificar
  `variacao_de` (lateralidade é tag separada). Aplica a `stiff` +
  `stiff uni` (unificar) e validar para outros pares.
- **Hiperextensão 45° → `plano_corporal = em_pe`** (decisão de
  agrupamento, não cria nível `suspenso_45`).
- **Hip Thrust + Ponte C/ Band = Ruim mesmo com equipamentos+famílias
  diferentes** porque ambos `deitado`. Plano corporal é dimensão
  suficientemente forte INTRA pra puxar pra Ruim.

---

### Grupo 6 — Flexões de Joelho (4 exercícios mapeados)

**Exercícios:** Cadeira Flexora, Flexão Joelhos Feijão, Flexão Joelhos
Slide, Nordic Curl. Grupo mais simples — `familia_estrita` carrega o
trabalho.

**Tags por exercício:**

| Dimensão | Aplica | Valor |
|---|---|---|
| `familia_estrita` | ✓ chave | `flexao deitado` (Feijão+Slide após conserto), vazio (Cadeira, Nordic) |
| `equipamento_grupo` | ✓ | maquina (Cadeira), corporal (Nordic), vazio (Feijão, Slide) |
| `lateralidade` | ✓ (ociosa, todos bi hoje) | bilateral |
| `pegada` | ❌ | — |
| `plano_corporal` | ❌ | sub-distinção quadril flex vs estendido fica como dívida |

**Calibração inicial:**

| Dimensão | INTRA | INTER | HISTÓRICO (R-1) |
|---|---|---|---|
| `familia_estrita` | Crítico (resolve Slide+Feijão) | Crítico | Crítico (toggle) |
| `equipamento_grupo` | Médio | Baixo | Baixo |
| `lateralidade` | Médio (anti_uni mantida, ociosa hoje) | Baixo | 0 |

**Decisões clínicas registradas:**

- **Caso clínico Slide ≈ Feijão JÁ ESTÁ RESOLVIDO por `familia_estrita`**
  (ambos `flexao joelhos`, renomeada para `flexao deitado`). Não
  precisa de dimensão nova. Confirma a importância da curadoria correta
  de família estrita.
- **Sub-distinção quadril flexionado (Cadeira) vs estendido
  (Feijão/Slide/Nordic)** não é modelada — capturada indiretamente por
  equipamento + família. Aceitável dívida.

---

### Grupo 7 — Tríceps (8 exercícios + 1 cadastro novo)

**Exercícios:** Tríceps Coice (Halter + Polia), Tríceps Pushdown
(renomeado de Polia Alta), Tríceps Corda, Tríceps Unilateral Polia,
Tríceps Francês, Tríceps Mergulho Banco, Tríceps Testa Halteres.

**Cadastro novo:** Tríceps Francês Corda (família `Tríceps Francês`,
equipamento corda).

**Tags por exercício:**

| Dimensão | Aplica | Notas |
|---|---|---|
| `familia_estrita` | ✓ chave | Coice / Pushdown / Francês / Mergulho / Testa (5 famílias após cleanup Etapa 1) |
| `equipamento_grupo` | ✓ | polia, halter, corporal/banco |
| `lateralidade` | ✓ | bi/uni |
| `pegada` | ❌ | não aplica |
| `plano_corporal` | ❌ | não aplica |
| `musculo_alvo_especifico` (cabeça) | ❌ DESCARTADA | famílias resolvem |

**Calibração inicial:**

| Dimensão | INTRA | INTER | HISTÓRICO (R-1) |
|---|---|---|---|
| `familia_estrita` | Crítico | Crítico | Crítico (toggle) |
| `equipamento_grupo` | Médio | Baixo | Baixo |
| `lateralidade` | Médio (anti_uni) | Baixo | 0 |

**Decisão estrutural:**

- **`musculo_alvo_especifico` (cabeça do tríceps) NÃO entra como
  dimensão.** Famílias estritas resolvem o problema. Uma das 5
  dimensões propostas pelo guia v4 (linha 810-811) é **descartada
  nesta etapa**. Boa simplificação — libera orçamento.

---

### Grupo 8 — Pranchas / Core Isométrico (11 atuais + 4 INFRA novos)

**Exercícios atuais:** Prancha (regular/Alternada/Bola/Feijão/Renegade/
Slideboard), Prancha Lateral, Dead Bug (regular/C Anilha/C Bola), Hollow
Hold, Pallof Press, Roda Abdominal.

**Cadastros novos massivos — família INFRA:**

- Infra Alternado
- Infra Suspenso (na barra fixa)
- Infra Chão (bilateral)
- Infra Roll-Up (flexão quadril + rolagem tronco)
- **Reclassificar:** Dead Bug C/ Anilha + Dead Bug C/ Bola → mover para
  família **INFRA** (mecânica de flexão de quadril, não anti-extensão
  clássica)

**Separação de família estrita:**

- `prancha frontal` (Frontal regular + Bola + Feijão + Slide + Renegade
  + Alternada)
- `prancha lateral` (apenas Prancha Lateral)

**Tags por exercício:**

| Dimensão | Aplica | Notas |
|---|---|---|
| `familia_estrita` | ✓ chave | `prancha frontal`, `prancha lateral`, `Dead bug`, `INFRA`, `crunch`, `v-up`, sem família (Hollow, Pallof, Roda) |
| `equipamento_grupo` | ✓ | corporal, bola, feijão, polia, ab_wheel, barra (Infra Suspenso), vazio (Slide) |
| `lateralidade` | ✓ | bi/uni, anti_uni vale |
| `pegada` | ❌ | — |
| `plano_corporal` | ❌ | NÃO modelar (diretriz user) |
| `plano_estabilizacao` (anti-ext/lat/rot) | ❌ DESCARTADA | personal-edita |

**Calibração inicial:**

| Dimensão | INTRA | INTER | HISTÓRICO (R-1) |
|---|---|---|---|
| `familia_estrita` | Crítico | Crítico | Crítico (toggle) |
| `equipamento_grupo` | Baixo (instabilidade conta mas não justifica granularidade) | Baixo | Baixo |
| `lateralidade` | Médio (anti_uni padrão) | Baixo | 0 |

**Tensão Frontal+Lateral resolvida pragmaticamente:**

> **Separar famílias** (`prancha frontal` + `prancha lateral`) — isso
> permite que **INTER** ambas possam aparecer (treinos diferentes).
> **INTRA**, o sistema NÃO bloqueia o pareamento Frontal+Lateral, mas a
> abundância de outras famílias em core (Dead Bug, INFRA, Crunch,
> Hollow, Pallof, Roda, V-Up) faz o gerador naturalmente preferir
> diversificar. Se eventualmente sair Frontal+Lateral juntas, **personal
> edita** (princípio 1.1). Sem dimensão nova.

---

## 3. Dimensões consolidadas (preliminar — Fase 2 vai congelar)

**Set FINAL congelado de 5 dimensões (após correções pós-Fase 1):**

| # | Dimensão | Tipo | Valores | Aceita vazio? |
|---|---|---|---|---|
| 1 | `familia_estrita` | hard filter | curado pelo personal (refinada por ângulo onde necessário, ex: Supino Reto vs Supino Inclinado) | ✓ |
| 2 | `equipamento_grupo` | enum 8+vazio (tiebreaker) | barra, barra_guiada, halter, polia, corporal, maquina, caixa, banda_elastica | ✓ |
| 3 | `lateralidade` | enum 2 | bilateral, unilateral | ❌ (sempre uma das duas) |
| 4 | `pegada` | enum 4 + matriz custom 4×4 | aberta, neutra, pronada, supinada | ✓ (em squats, hinges, knee_flex, tríceps, pranchas) |
| 5 | `plano_corporal` | enum não-universal | varia por grupo: reto/inclinado (supinos), curvada/baixa/apoiada/etc (remadas), em_pe/deitado (hinges), pullover/vazio (puxadas), vazio (squats/knee_flex/tríceps/pranchas) | ✓ |

> **Nota — absorção de `angulo_movimento`:** dimensão proposta
> originalmente no guia v4 como separada. Após validação, foi
> **absorvida em `plano_corporal`** com valores específicos por
> subregião. Em supinos, `plano_corporal = reto/inclinado` cobre o que
> `angulo_movimento` cobriria, sem custar uma dimensão extra.

> **Nota — `musculo_alvo_especifico` descartada:** dimensão proposta
> no guia v4 (cabeça do tríceps). User confirmou em G7 que famílias
> resolvem. Não entra no set.

> **Nota — equipamento como tiebreaker:** peso BAIXO INTRA reflete que
> equipamento NÃO incomoda entre exercícios clinicamente diversos, mas
> serve como desempate quando família+plano+pegada empatam (caso
> supino-inclinado-T1).

### 3.1 Pegada — modelo escolhido

**Opção A: tag única `pegada` com 4 valores enumerados + matriz de
distâncias custom 4×4.**

Matriz de distâncias:

|  | aberta | neutra | pronada | supinada |
|---|---|---|---|---|
| **aberta** | 0 | 2 | 1 | 3 |
| **neutra** | 2 | 0 | 2 | 2 |
| **pronada** | 1 | 2 | 0 | 1 |
| **supinada** | 3 | 2 | 1 | 0 |

**Casos clínicos cobertos:**

- `aberta ↔ pronada` = 1: "próximas, mesma orientação, muda só largura"
  (caso Curvada Barra + Baixa Aberta = Tolerável)
- `pronada ↔ supinada` = 1: "pequena-média, mesma largura, muda
  orientação"
- `aberta ↔ supinada` = 3: "muda tudo"
- `neutra ↔ qualquer` = 2: "intermediário"

**Penalidade INTRA proposta** (calibração final na Etapa 7):

```
penalty_pegada = peso_pegada × (max_dist - dist) / max_dist
```

Pares com distância 0 (mesma pegada) recebem penalidade máxima;
distância 3 (aberta↔supinada) recebem penalidade ~0.

**Alternativas consideradas e descartadas:**

- Quebrar em `largura_pegada` + `orientacao_pegada` (estoura
  orçamento, vira 6 dimensões)
- Tag única com 3 valores (juntar pronada+supinada — perde nuance
  confirmada)
- Distância binária (igual/diferente — perde sub-estrutura)

---

## 4. Anexo — Consertos pendentes no banco

Lista consolidada para a Etapa 7 (que faz a migração efetiva do XLSX).
**Esta etapa NÃO mexe no banco.**

### 4.1 Reclassificações

| # | Item | Mudança |
|---|---|---|
| 1 | Remada Landmine | Split em **Remada LM Neutra + Remada LM Aberta**, ambas `variacao_de = remada curvada` (era `Remada horizontal`) |
| 2 | Remada Baixa Aberta + Baixa Neutra | Unificar `variacao_de` (mesma família — ambas em polia baixa) |
| 3 | Slide Board Lateral | `purpose=compound` (era `explosive`); `padrao=squat_unilateral` (era `squat_bilateral`); equipamento vazio; nome sugerido "Agachamento Unilateral Slideboard" |
| 4 | Apoios (Apoio, Ajoelhado, Elevado) | `equipamento_grupo = corporal` |
| 5 | Smith Inclinado / Curvada Smith / Agachamento Smith | `equipamento_grupo = barra_guiada` |
| 6 | Reto Halteres | `equipamento_grupo = halter` (refinamento retroativo) |
| 7 | Stiff Halteres + Stiff Uni Halteres + Stiff Uni Smith | Unificar `variacao_de = stiff` (lateralidade é tag separada) |
| 8 | Good Morning | `variacao_de = stiff` (mecanicamente é stiff com barra nas costas) |
| 9 | Lev. Terra Anilha | `equipamento_grupo = barra` (consistência com família terra) |
| 10 | Hiperextensão 45° | `plano_corporal = em_pe` (não cria nível `suspenso_45`) |
| 11 | Flexão Joelhos Feijão + Flexão Joelhos Slide | Renomear `variacao_de = flexao deitado` (era `flexao joelhos` — todos exercícios são flexão de joelhos; nome novo une movimento + posição) |
| 12 | Tríceps Polia Alta | Renomear para **Tríceps Pushdown** |
| 13 | Pranchas | Separar família: `prancha frontal` (Frontal + Bola + Feijão + Slide + Renegade + Alternada) e `prancha lateral` (apenas Prancha Lateral) |
| 14 | Dead Bug C/ Anilha + Dead Bug C/ Bola | Mover para família **INFRA** (mecânica de flexão de quadril, não anti-extensão) |
| 15 | Step Up + Step Up Alt + Passada Dos Steps | `equipamento_grupo = caixa` (caixa prevalece sobre halter pela regra de precedência semântica) |
| 15-bis | **Supino — refinar família por ângulo** | **`Supino` → `Supino Reto`** (Reto Barra/Halteres/Anilha) **+ `Supino Inclinado`** (Smith Inclinado e cadastros futuros). Caminho B aprovado pelo user. Justificativa: G1 P5 INTER pressupõe 3 supinos coexistindo (1 inclinado + 2 retos), incompatível com família única + hard INTER. |
| 15-ter | **Cadastrar `plano_corporal` em todos exercícios de peito** | Supinos (reto/inclinado), Crucifixos (reto/inclinado), Crossovers (reto/inclinado conforme cadastro), Apoios (vazio — não diferencia clinicamente). Substitui `angulo_movimento` proposto inicialmente. |

### 4.2 Cadastros novos sugeridos

| # | Item | Motivo |
|---|---|---|
| 16 | Apoio Fechado | Já em uso pelo personal |
| 17 | Supino Fechado | Possível variação futura |
| 18 | Crucifixo Inclinado Halteres + variantes | Cobrir ângulo inclinado em isolados de peito |
| 19 | Crossover Inclinado / variantes | Cobrir ângulo em crossovers |
| 20 | Remada Curvada Supinada (Yates) | Pegada supinada inexistente em remadas hoje |
| 21 | Serrote Pronada Wide / Uni Polia Pronada Wide | Variantes de pegada em unilaterais (opcional) |
| 22 | Barra c/ borracha | Variação assistida da Barra Fixa (banda elástica nos pés) |
| 23 | Puxada Unilateral Polia | Resolve a lacuna "lateralidade=0 em puxadas hoje" |
| 24 | Pulldown Braço Estendido | Polia ajustável, isolation (`plano_corporal = pullover`) |
| 25 | Barra Aberta + Barra Supinada | Substituem `Barra` genérica como família mãe |
| 26 | Recuo do Estepe | `equipamento_grupo = caixa` |
| 27 | Tríceps Francês Corda | Família `Tríceps Francês`, equipamento corda |
| 28 | Infra Alternado | Nova família INFRA |
| 29 | Infra Suspenso (na barra fixa) | Nova família INFRA |
| 30 | Infra Chão (bilateral) | Nova família INFRA |
| 31 | Infra Roll-Up | Nova família INFRA — flexão quadril + rolagem tronco |

### 4.3 Decisões pendentes pro user

| # | Item | Aguarda decisão |
|---|---|---|
| 32 | Box Jump | Fica ou sai do banco? Caso de "timing/sequenciamento" não modelado. |

---

## 5. Decisões PENDENTES para Fase 2/3/4

### Para Fase 2 residual (set de dimensões já congelado)

- ~~Validar/congelar set de dimensões~~ — ✅ resolvido na auditoria
  pós-Fase 1: 5 dimensões finais (`familia_estrita`, `lateralidade`,
  `pegada`, `plano_corporal`, `equipamento_grupo`). `angulo_movimento`
  absorvido em `plano_corporal`.
- **Regra de cadastro consolidada** — diretrizes parciais já existem
  (famílias gêmeas bi/uni unificam; precedência semântica em
  equipamento; refinamento por ângulo onde necessário a la Supinos).
  Consolidar em um documento de cadastro para futuros exercícios.
- **Múltiplas tags em equipamento_grupo** — provisório: tag única com
  precedência semântica. Reabrir se aparecer caso onde tag única não
  basta.
- **Decisão sobre Box Jump** — fica ou sai do banco? (caso de timing/
  sequenciamento, não modelado).
- **Resolver lacuna da pegada na tabela de calibração do G1** —
  atualmente "(a definir)" INTRA/INTER/HISTÓRICO. Estimativas iniciais
  podem ser fixadas; refinamento via simulação na Fase 3/Etapa 7.

### Decisões a re-validar (auditoria do anti-padrão escopo→rigor)

Aplicação retroativa da diretriz da Seção 1.1: identificar casos onde
modelagem ativa pedida pelo user pode ter sido substituída
silenciosamente por "abundância probabilística + personal edita".

**Caso 1 — Pranchas Frontal + Lateral INTRA (G8)**

- **User pediu (modelagem ativa):** *"precisamos de uma forma de evitar
  que o app junte 2 pranchas (até mesmo frontal/comum + lateral) se o
  usuário pedir core(2). app deve priorizar inserir um abdominal de
  outro tipo"*
- **Como ficou registrado (regressão silenciosa):** *"sistema NÃO
  bloqueia o pareamento Frontal+Lateral, mas a abundância de outras
  famílias em core (Dead Bug, INFRA, Crunch, Hollow, Pallof, Roda,
  V-Up) faz o gerador naturalmente preferir diversificar. Personal
  edita."*
- **Status:** ⚠️ REGRESSÃO. Re-validar.
- **Tensão com decisão clara do user:** mais à frente em G8 Q2, user
  disse "(2) não modelar plano_estabilizacao — adiciona complexidade
  desnecessária". As duas afirmações estão em tensão. Ele quer o
  efeito (evitar 2 pranchas frontal+lateral) sem criar a dimensão
  formal (anti-extensão / anti-lateroflexão / anti-rotação como tag).
- **Caminhos possíveis para re-validar:**
  - **(a)** Criar tag `categoria_core` (sub-categorias dentro de
    core_isometrico: ventral / lateral / anti-rotação / dorsal /
    flexão de tronco / flexão de quadril) com peso INTRA alto.
    Estrutura mais "limpa" mas adiciona dimensão (estoura orçamento
    se for dimensão; ou vira valor de `plano_corporal` em core).
  - **(b)** Estender mecanismo de âncoras (Etapa 3) para operar dentro
    da subregião `core_isometrico` em granularidade fina (ex:
    "rotina com core(2) deve diversificar entre 2 categorias").
    Reaproveita infra existente.
  - **(c)** Aceitar como dívida e mover pra Etapa 7 — registrar que
    fica bloqueado na simulação, calibrar lá.

**Caso 2 — Step Up + Passada Dos Steps INTRA (G4)**

- **User pediu (modelagem ativa):** *"(v) Ruim - muito similares e o
  objetivo da caixa em ambos é o mesmo: aumentar amplitude de
  movimento do quadril no exercício (profundidade)"*
- **Como ficou registrado (regressão indireta):** quando equipamento
  virou tiebreaker peso BAIXO INTRA (após validação dos 12 cenários
  cross-grupo), o caso Step Up + Passada Dos Steps virou "OK pelo
  modelo" — outras dimensões empatam, equipamento é só desempate.
- **Status:** ⚠️ REGRESSÃO INDIRETA. Re-validar.
- **Por que aconteceu:** os 12 cenários da validação não incluíram
  esse par específico (mesma subregião + mesmo equipamento `caixa` +
  famílias diferentes + ambos unilaterais). User pode não ter
  percebido que "equipamento BAIXO" iria contradizer "Step Up +
  Passada Dos Steps = Ruim".
- **Caminhos possíveis para re-validar:**
  - **(a)** Modelo híbrido — `equipamento_grupo` tem peso BAIXO
    "logístico" (barra/halter/polia/etc.) mas peso ALTO em valores
    "específicos" (`caixa`, `banda_elastica`). Mais complexo de
    calibrar, mas captura a intuição clínica de "caixa repetida =
    propósito clínico repetido".
  - **(b)** Mover `caixa` (e talvez `banda_elastica`) pra fora de
    `equipamento_grupo` e tratar como **sub-tag de plano_corporal** ou
    família estrita (Step Up, Passada Dos Steps, Step Up Alt, Recuo
    do Estepe ganham `familia_estrita = exercicio_em_caixa` — unifica
    em família única que hard bloqueia).
  - **(c)** Aceitar como dívida — argumento: a regra `anti_uni` da
    Etapa 5 já cobre parcialmente Step Up + Passada Dos Steps (ambos
    unilaterais). O par fica desincentivado pela lateralidade, ainda
    que não pelo equipamento. Avaliar via simulação na Etapa 7.

**Caso 3 — Sub-distinção uni-estático vs uni-deslocamento (G4)**

- User pediu inicialmente que (iii) Búlgaro+Passada fosse Ruim e (iv)
  Búlgaro+Walking Lunges fosse "menos pior".
- User explicitamente abriu mão depois: *"sub-distinção de
  unilaterais - não será necessário"*.
- **Status:** ✅ Não é regressão — user aceitou explicitamente como
  dívida com justificativa.

### Sub-pendência registrada (decisão para Etapa 7)

**"2 retos + 1 inclinado bloqueado pelo hard INTER"** — caso de borda
residual do Caminho B. Com `Supino Reto` como família única (Reto
Barra + Reto Halteres + Reto Anilha juntos) e `familia_estrita` hard
INTER, o cenário "2 retos diferentes em treinos diferentes" (P5(c)
do G1, marcado OK pelo user) fica operacionalmente bloqueado.

Três caminhos possíveis (sem decisão urgente — fica pra Etapa 7,
junto com destino final do hard INTER):

- **(a)** Refinamento extremo: cada exercício vira sua família.
  Esvazia o hard filter.
- **(b)** Aceitar como dívida: rotina típica raramente tem 2+ peito
  por treino; sistema diversifica via Crucifixo/Crossover/Apoio.
- **(c)** Soft INTER: remover hard INTER de família, deixar score
  resolver. Fica naturalmente coerente.

Provavelmente fica resolvido naturalmente quando o destino do hard
INTER for decidido após simulação na Etapa 7.

### Para Fase 3 (calibração de pesos)

- **Pesos por grupo: como configurar?** Estrutura sugerida: dict por
  `subregiao` ou `padrao`, com fallback global. Etapa 7 implementa.
- **Refinar matriz de pegada** — calibração via simulação na Etapa 7.
  Valores propostos (0/1/2/3) são ordens de magnitude clínicas, não
  finais.
- **Calibrar pesos numéricos** — categorias clínicas são "Crítico",
  "Alto", "Médio", "Baixo", "0". Conversão para números numéricos
  (escala 0-100? 0-1000?) acontece na Etapa 7 alinhada com o sistema
  de score da Etapa 5.

### Para Fase 4 (estratégia de preenchimento)

- **Priorização de dimensões para preenchimento** — quais precisam de
  100% do banco preenchido pra Etapa 7 funcionar, quais podem ter 50%
  e ir crescendo.
- **Validação cruzada com 8 problemas conhecidos** — cada problema do
  guia v4 (Seção 3) recebe linha "esse problema é resolvido por
  (dimensão X com peso Y no contexto Z)".

---

## 6. Validação cruzada com problemas conhecidos (PARCIAL)

Mapeamento dos 8 problemas conhecidos (Seção 3 do guia v4) para
dimensão + peso. Esta seção será expandida na Fase 4.

| # | Problema | Resolvido por |
|---|---|---|
| 1 | Viés posterior > anterior em `lower(N)` | Etapa 2 (pré-alocação) — não é problema de tags |
| 2 | Tríceps todos `variacao_de = "Tríceps"` | Resolvido na Etapa 1 (cleanup) — `familia_estrita` refinada |
| 3 | `subregiao` na dataclass | Etapa 1 — não é problema de tags |
| 4 | Squat unilateral/bilateral | Etapa 1 — não é problema de tags |
| 5 | Padrões âncora sem composto | Etapa 3 (âncoras) — não é problema de tags |
| 6 | Regra anti-2-unilaterais cega | Etapa 5 (`anti_uni_mesmo_grupo`) — refinada na Etapa 7 via `lateralidade` (peso por grupo) |
| 7 | Distribuição reproduz banco | Etapa 3 (quotas) — não é problema de tags |
| 8 | Core sem subregiões | Etapa 1 — não é problema de tags |

**Conclusão preliminar:** os 8 problemas declarados estão ENDEREÇADOS em
etapas anteriores. A Etapa 7 (penalidades multi-dim) trata problemas
NOVOS que emergem ao longo do uso — variabilidade biomecânica fina,
diversidade temporal, controle do personal sobre variabilidade.

---

## Status do documento

- ✅ **Fase 1 — análise dos 8 grupos** — completa
- ✅ **Correções pós-Fase 1 (auditoria do user)** — aplicadas:
  - `angulo_movimento` re-introduzido (absorvido em `plano_corporal`)
  - Família `Supino` refinada (`Supino Reto` + `Supino Inclinado`)
  - `equipamento_grupo` esclarecido como tiebreaker (peso BAIXO INTRA)
  - Set de 5 dimensões congelado (Caminho B aprovado)
- ⏳ **Fase 2 — derivação final das dimensões** — em grande parte
  resolvida; restam consolidar regra de cadastro e decidir pendências
  menores
- ⏳ **Fase 3 — calibração de pesos** — pendente próxima sessão
- ⏳ **Fase 4 — estratégia de preenchimento** — pendente próxima sessão

**Próximos passos:**

1. Personal revisa este documento revisado + transcript de auditoria
2. Próxima sessão arranca consolidando Fase 2 (regra de cadastro,
   decisões pendentes residuais como Box Jump) e partindo para Fase 3
3. Documento será atualizado in-place a cada fase

*Documento parcial. Última atualização: 2026-05-05 (correções pós-auditoria).*
