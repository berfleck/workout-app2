# Etapa 6 — Sessão 1 — Transcript completo (2026-05-03 a 2026-05-05)

> Transcript da Sessão 1 da Etapa 6 do refator do gerador. Para auditoria
> de decisões clínicas e arquiteturais. As mensagens estão organizadas
> cronologicamente por grupo/tópico. Decisões importantes destacadas.

---

## Instrução inicial do user

> Etapas 1 a 5 do guia de refatoração estão concluídas no repo.
> Vamos para a Etapa 6: "Trabalho preparatório das tags multi-dimensionais".
>
> [...] esta etapa é diferente de todas as outras. NÃO MUDA CÓDIGO.
> É trabalho de modelagem clínica e arquitetural que produz um
> documento de especificação. O Claude Code aqui atua como facilitador
> de uma discussão, não como implementador.
>
> A etapa produz `docs/refatoracao/dimensoes_proximidade.md` com:
> 1. Lista de 8-12 grupos de exercícios próximos
> 2. Definição final das dimensões
> 3. Tabela de pesos INTRA / INTER / HISTÓRICO
> 4. Estratégia de preenchimento do banco
> 5. Casos de borda explícitos

**Claude propôs plano em 4 fases.** User confirmou.

---

## Decisões metodológicas iniciais

**User:**
- (A) **8 grupos iniciais:** Supinos, Remadas, Puxadas, Agachamentos,
  Hinges, Flexões de joelho, Tríceps, Pranchas. Apoios/Crossovers/
  Bíceps/Ombros ficam no backlog. Fase 1 pode levantar 2-3 extras se
  aparecerem casos.
- (B) **Modo híbrido com viés guiado.** Aberto pra Tríceps e Pranchas.
- **Anexo "consertos pendentes no banco"**: ao longo da Fase 1, anotar
  separadamente coisas que precisam mexer no XLSX além das tags novas.
- **Vinhetas fictícias HISTÓRICO** pra cada grupo, pra calibrar peso
  HISTÓRICO sem partir do zero.

---

## GRUPO 1 — Supinos (7 exercícios)

**Exercícios:** Supino Reto Barra, Reto Halteres, Reto Anilha, Smith
Inclinado, Apoio, Apoio Ajoelhado, Apoio Elevado.

### P1 — Hierarquia das dimensões em Supinos

**User:** (a) **ângulo > equipamento.** Reto Barra + Reto Halteres
incomoda mais que Reto Barra + Smith Inclinado.

### P2 — Granularidade do ângulo

**User:** (a) **2 níveis: reto / inclinado.**

### P3 — Granularidade do equipamento

**User:** (b) **3 níveis: barra / halter / guiado-ou-corporal.**

### P4 — Comportamento INTRA

**User:**
- (i) Reto Barra + Reto Halteres = **Ruim**
- (ii) Reto Barra + Smith Inclinado = **Tolerável**
- (iii) Reto Halteres + Smith Inclinado = **OK**
- (iv) Reto Barra + Com Anilha = **Tolerável**

> Nuance: "Supino barra é mais parecido com supino smith do que supino
> haltere porque haltere é peso livre e modifica mais o exercício, mas
> isso é um detalhe que talvez tenhamos que deixar passar."

> Banco vai crescer (ex: vai adicionar Supino Inclinado Com Anilha).

### P5 — Comportamento INTER

**User:**
- (a) Regra fraca — app deve selecionar pelo menos um inclinado ou outro
  exercício do padrão se 3 supinos retos forem selecionados em 3
  treinos
- (b) 3 supinos retos com equipamentos diferentes = **Ruim**
- (c) 2 retos + 1 inclinado = **OK**
- (d) **Correção conceitual importante:** "Estamos misturando conceitos.
  O usuário não tem como pedir 3 treinos com supino. Ele pede peito ou
  upper. É o app que escolhe os supinos. Caso o app selecione 3 supinos
  em rotina de 3 treinos, sim, deve haver pelo menos 1 inclinado se
  for possível."

### P6 — HISTÓRICO em Supinos

**User:** "Esse treino não aconteceria na prática (peito(2) sozinho).
Para ilustrar: regra leve em conta APENAS R-1 (anterior ao atual) e
seja **penalty alto** (aparecem se indispensáveis). Usuário também deve
poder optar com **toggle ON/OFF**."

> **DECISÃO ESTRUTURAL:** HISTÓRICO = janela de 1 rotina (apenas R-1),
> peso integral, sem decaimento contínuo. Toggle ON/OFF na UI. **Altera
> o guia v4** que propunha curva 1.0/0.5/0.25/0 nas 6 semanas.

### P7 — Limites do grupo Supinos

**User:** (a) Supino Reto Halteres + Crucifixo Halteres = OK. **Mas
nuance:** "eles conversam por ângulo de inclinação. Crucifixo pode ser
reto ou inclinado e, nesse sentido, é preferível variar os ângulos."

> **DECISÃO:** `angulo_movimento` é dimensão TRANSVERSAL — atravessa
> compostos (`empurrar_compostos`) e isolados (`empurrar_isolados`) de
> peito.

### Cadastros futuros (anexo) - G1

- Apoio Fechado (já em uso pelo personal)
- Supino Fechado (talvez)
- Variantes inclinadas de Crucifixo e Crossover

---

## GRUPO 2 — Remadas (12 exercícios)

**Exercícios:** Curvada Barra, Curvada Halteres, Curvada Smith, Landmine,
Baixa Aberta, Baixa Neutra, Apoiado, Seal Halteres, Uni Polia, Serrote,
Aberta TRX, Neutra TRX.

### Observações iniciais sobre o banco — User confirmou:

- **Remada Landmine = T-Bar Row** = remada curvada. Anexo: reclassificar
  `variacao_de = remada curvada`.
- **Remada Baixa Aberta + Baixa Neutra:** ambas remadas baixas em polia.
  Anexo: unificar `variacao_de`.

### P1 — Hierarquia das dimensões em Remadas

**User:** (b) **pegada > plano corporal > equipamento.** Pegada por
ativação muscular. Equipamento e plano corporal mesmo peso. Plano
"curvada" tem impacto adicional na lombar.

> **Faltou Lateralidade na minha lista** — user adicionou.

### P1.5 — Onde Lateralidade entra?

**User contestou minha pergunta:** "Compara 2 unilaterais com 2
bilaterais de MESMA PEGADA — ideal seria comparar com pegadas
diferentes. NA PRÁTICA eu nunca usaria 2 remadas unilaterais no mesmo
treino (intra). Em treinos diferentes da mesma rotina (inter), com
certeza usaria."

> **DECISÃO:**
> - Hierarquia INTRA: **Lateralidade (~hard) > Pegada > Plano ≈ Equipamento**
> - Hierarquia INTER: **Pegada > Plano ≈ Equipamento**, lateralidade
>   tem peso baixo (regra fraca de diversificação)

### P2 — Granularidade da pegada

**User:** **4 níveis canônicos:**
- aberta (sempre pronada)
- neutra
- supinada (sempre fechada, ainda não tem no banco)
- pronada (pronada-fechada — implícito em "remada curvada barra")

> **Sub-estrutura interna:** distância entre pegadas NÃO é uniforme:
> - aberta ↔ pronada = pequena (mesma orientação, muda largura)
> - pronada ↔ supinada = pequena-média (mesma largura, muda orientação)
> - aberta ↔ supinada = grande (muda tudo)

> "Pronada vs supinada são diferentes mas não MUITO. INTER, eu mudaria
> pra outra remada, não inverteria a pegada."

### Sobre pegada do Landmine

**User:** "Remada Landmine tem 2 opções de pegada na minha academia:
neutra ou aberta."

> **Mais tarde resolvido:** Landmine se divide em 2 cadastros separados
> (Remada LM Neutra + Remada LM Aberta).

### P3 — Granularidade plano corporal e equipamento

**User:** (d) "Remada Landmine deve ser uma variação de barra. Outro
equipamento pode ser **polia**. TRX não sei se merece sua própria
categoria."

### Sobre TRX e refinamento de equipamento

**User:** "guiado_corporal não faz sentido biomecanicamente. Apoio e
supino smith nada têm a ver. TRX pode ficar sem tag por enquanto.
Smith pode ter sua própria categoria **barra guiada**."

**Uni Polia → unilateral_apoiada** (apoio do joelho como Serrote).

> **DECISÃO:** Equipamento_grupo expandido para 5 níveis nomeados +
> vazio: `barra / barra_guiada / halter / polia / corporal` + (vazio
> pra TRX). Mais tarde adicionado `maquina`, `caixa`, `banda_elastica`.

### P4 — Cenários INTRA Remadas

**User (com prefacio importante):** "Se for um único treino, app deve
selecionar 1 puxada e 1 remada. Se forem diversos treinos (com
costas(2)) de uma rotina, pode ser aceitável a condição de 2 remadas."

- (i) Curvada Barra + Curvada Halteres = **Ruim**
- (ii) Curvada Barra + Baixa Aberta = **Tolerável** (ambas pegada
  pronada, similar exigência core)
- (iii) Baixa Aberta + Baixa Neutra = **Ruim**
- (iv) Serrote + Uni Polia = **Ruim**
- (v) Curvada Halteres + Apoiado = **Ruim** (trocaria pegada de uma)
- (vi) Aberta TRX + Curvada Barra = **Tolerável** (ambas pegada pronada)

### P5 — Cenários INTER Remadas

**User:**
- (a) 3 curvadas = **Ruim/péssimo**
- (b) Baixa + Apoiado (com Curvada Halteres em T1) = **OK**
- (c) Curvada Barra + Aberta TRX (com Curvada Halteres em T1) = **Ruim**
  (faltou unilateral)
- (d) Serrote + Curvada Smith (mistura uni com bi) = **Tolerável**

### HISTÓRICO em Remadas

**User:** (i) Mantém igual a Supinos. Tag evita com filtro soft, podendo
aliviar se necessário.

> **Confirmação:** regra HISTÓRICO universal (R-1, peso integral, soft,
> toggle ON/OFF).

### Insights de G2 destacados

> **Lateralidade INTER ≠ 0:** "Faltou uma remada unilateral" em rotina
> de 3 treinos. Lateralidade tem peso BAIXO mas NÃO ZERO INTER —
> "regra fraca de diversificação".

> **Pegada com sub-estrutura confirmada:** aberta+pronada são variantes
> de pronada (orientação igual, largura diferente).

### Cadastros futuros (anexo) - G2

- Variantes pegada em unilaterais (Serrote Pronada Wide, Uni Polia
  Pronada Wide) — opcional
- Remada Curvada Supinada (Yates) — não há nenhuma supinada no banco

---

## GRUPO 3 — Puxadas (7 exercícios + 5 cadastros futuros)

**Exercícios atuais:** Barra Fixa, Barra Isométrica, Pullover Halteres,
Pullover Polia, Puxada Aberta, Puxada Neutra, Puxada Supinada.

### Cadastros futuros importantes (user listou antes de iniciar)

> "Vou precisar alimentar o banco. Já vou deixar aqui:
> - **Barra c/ borracha** (banda elástica nos pés para alunos mais fracos)
> - **Puxada Unilateral Polia**
> - **Pulldown braço estendido** (na polia ajustável)
> - **Barra Aberta** + **Barra Supinada** (substituem `Barra` genérica)"

> Pergunta meta importante: "**O que seria 'plano' nas puxadas?** Acho
> que essa tag não faz sentido em puxadas."

### P1 — Hierarquia em Puxadas

**User:** (c) **Pegada > Equipamento = Lateralidade**

> **DESCOBERTA ESTRUTURAL:** Hierarquia varia POR GRUPO. Puxadas
> diferente de Remadas. **Justifica decisão "pesos por grupo".**

### P2 — Granularidade da pegada em Puxadas

**User:** (a) **3 níveis** (aberta / neutra / supinada). "Aberta só
pode ser executada com pegada pronada."

### P3 — Plano corporal em Puxadas

**User:** "Plano parece desnecessário em puxadas. vertical_livre e
vertical_polia só se diferenciam por equipamento. Pullover sim é plano
diferenciado, mas não sei se justifica tag. Se não for problema,
podemos cadastrar tag de plano para diferenciar pullovers (é bem
diferente). **Pulldown braço estendido entraria junto com pullover.**
**Tenho medo que comece a aparecer demais nos treinos se tiver sua
própria tag.**"

> **DECISÃO:** `plano_corporal` é dimensão NÃO-UNIVERSAL. Em puxadas,
> só Pullover/Pulldown ganham `plano_corporal = pullover`; demais
> ficam vazios.

### P4 — Caso Barra Fixa vs Barra Isométrica

**User:** (a) Hard filter já basta (mesma família).

### P5 — Cenários INTRA/INTER Puxadas

**User INTRA:**
- (i) Puxada Neutra + Puxada Aberta = **Ruim**
- (ii) Puxada Neutra + Barra Fixa = **Tolerável** (irrelevante pra
  pergunta sobre ordem dentro do bloco)
- (iii) Puxada Neutra + Pullover Halteres = **OK**

**User INTER:**
- (a) 3 puxadas (Aberta + Supinada com Barra Fixa em T1) = **Ruim**
  ("faltou unilateral OU pullover/pulldown em algum dos treinos")
- (b) Puxada + Pullover (com Barra Fixa em T1) = **OK**
- (c) Barra Iso + Puxada (com Barra Fixa em T1) = **Ruim** (repete
  família Barra; só usaria caso de aluno em progressão de barra fixa)

**HISTÓRICO:** Mantém universal.

> **INSIGHT NOVO:** Pullover/Pulldown como "âncora soft INTER" —
> diversificador. Mesma família semântica de "regra fraca" que
> apareceu com lateralidade em Remadas.

---

## GRUPO 4 — Agachamentos (17 exercícios)

**Exercícios:** Agachamento Livre, Goblet, Smith, Leg Press, Cadeira
Extensora, Box Jump (6 bilaterais); Búlgaro, Passada, Passada Dos
Steps, Recuo, Recuo Alternado, Recuo C/ Barra, Step Up, Step Up Alt.,
Walking Lunges, Agach. Lateral, Slide Board Lateral (11 unilaterais).

### P1 — Quais dimensões aplicam em squats

**User correções:**
- **Slide Board Lateral**: reclassificar `purpose=compound` (não
  `explosive`); padrão `squat_unilateral`.
- **Pegada:** OK, não aplica.
- **Equipamento:** Box Jump fica sem tag. **Adicionar tag `caixa`** que
  deve ser usada em Step Up, Passada Dos Steps, Recuo do Estepe (não
  está no banco ainda).
- **Pergunta meta importante:** "Um exercício pode ter 2 tags? Nos
  agachamentos é possível usar barra ou haltere E usar ou não uma
  caixa/estepe."
- **Plano corporal:** Não usar — `padrao_execucao` classifica melhor.
- **`posicao_carga`:** Não usar.
- **`padrao_execucao`:** "Acredito que não seja necessário: bilaterais
  sempre são agachar e unilaterais são variações de passadas/recuos.
  Deslizar no slide board (agachamento unilateral slideboard) pode ficar
  junto das passadas."

**Pergunta de fundo:** Agachamento Livre + Búlgaro são complementares.
"Inclusive são uma combinação bem recomendada em treinos de perna."

### Resposta Claude sobre múltiplas tags equipamento

> **SOLUÇÃO PROVISÓRIA:** Tag única com regra de precedência semântica.
> Step Up = `caixa` (não `halter`), porque caixa define a característica
> clínica de proximidade.

### P2 — Cenários INTRA/INTER Squats

**User INTRA:**
- (i) Agachamento Livre + Búlgaro = **OK** (complementares)
- (ii) Agachamento Livre + Cadeira Extensora = **OK**
- (iii) Búlgaro + Passada = **Ruim** (muito similares — uni estáticos)
- (iv) Búlgaro + Walking Lunges = **Ruim** (mas menos pior — Walking
  é deslocamento, Búlgaro é parado)
- (v) Step Up + Passada Dos Steps = **Ruim** (objetivo da caixa em
  ambos é o mesmo)
- (vi) Agachamento Livre + Leg Press = **Tolerável** (melhor evitar)
- (vii) Agachamento Livre + Box Jump = **Ruim** (Box Jump talvez saia
  do banco)

**User INTER:**
- (a) 3 da família Agachamento = **Ruim/péssimo**
- (b) Bi + 2 Uni distintos = **OK**
- (c) Cadeira + Leg Press = **OK**
- (d) Box Jump + Cadeira Extensora = **OK**

**HISTÓRICO:** igual a Supinos.

### Confirmações finais de G4

- A. **Lateralidade INTRA em squats = MÉDIO** (não Crítico como em
  remadas)
- B. **Slideboard:** "Não sei se merece próprio nível. Ideia: deixar
  sem tag."

> **DECISÃO IMPORTANTE:** Lateralidade INTRA varia por grupo (Crítico
> em remadas, Médio em squats). Confirma forte a necessidade de
> **pesos POR GRUPO**.

> **Insight uni-estático vs uni-deslocamento** (Búlgaro vs Walking
> Lunges) — distinção real mas user não quer modelar. **Aceito como
> dívida.**

> **Box Jump como caso especial** — não é problema de proximidade, é
> timing/sequenciamento (explosivo precisa de musculatura fresca).

---

## GRUPO 5 — Extensão de Quadril (renomeado de Hinges, 19 exercícios)

> **Renomeação meta:** "Chamei de Hinges o grupo todo mas na verdade o
> correto seria 'extensão de quadril'. As pontes e hip thrusts não são
> propriamente hinges, mas todos são primariamente extensão de quadril."

### Sobre as observações iniciais

**User confirmou:**
- Good Morning: cadastrar `variacao_de = stiff`
- Hiperextensão 45°: pode ir para `em_pe`
- Lev. Terra Anilha: equipamento `barra` ou vazio (Claude propôs `barra`)
- Hip Thrust vs Ponte: distinção é ROM (Hip Thrust = tronco elevado,
  Ponte = tronco no chão)

### P1 — Validação proposta

**User:** Hiperextensão vai para `em_pe`. Lev terra anilha pode ficar
sem tag ou entrar em `barra`.

### P2 — Hierarquia em hinges

**User:** (a) **Plano corporal > familia > equipamento > lateralidade**

### P3 — Cenários INTRA/INTER Hinges

**User INTRA:**
- (i) Lev. Terra + Stiff Barra Livre = **Tolerável** (melhor evitar
  usando outro plano ou equipamento)
- (ii) Lev. Terra + Hip Thrust = **OK**
- (iii) Hip Thrust + Ponte C/ Band = **Ruim** (muito similares)
- (iv) Stiff Halteres + Stiff Uni Halteres = **Ruim** (muito similares)
- (v) Hiperextensão 45° + Lev. Terra Anilha = **Tolerável**
- (vi) Lev. Terra + Lev. Terra Anilha = **Ruim** (mesma família)

**User INTER:**
- (a) 3 stiffs (Stiff Halteres + Stiff Uni Halteres + Lev Terra) =
  **Ruim** (duas variações do mesmo, todos hinge em pé)
- (b) Hip Thrust + Ponte Unilateral (com Lev Terra em T1) = **Tolerável**
  (Ponte Uni é fraco como representante de hinge — depende do nível
  do aluno)
- (c) Stiff Uni + Hip Thrust = **Ótimo**
- (d) Hiperextensão + Hip Thrust C/ Band = **Ótimo**

**HISTÓRICO:** Manter universal.

> **DECISÃO IMPORTANTE de G5:** Famílias gêmeas bi/uni unificam.
> `stiff` + `stiff uni` viram `stiff` único. Lateralidade é tag
> separada. **Diretriz emergente** para outros pares no banco.

> Plano corporal `deitado` em hinges é dimensão suficientemente forte
> INTRA pra puxar pra Ruim mesmo com equipamentos+famílias diferentes
> (Hip Thrust + Ponte C/ Band).

---

## GRUPO 6 — Flexões de Joelho (4 exercícios)

**Exercícios:** Cadeira Flexora, Flexão Joelhos Feijão, Flexão Joelhos
Slide, Nordic Curl.

### Pergunta sobre caso clínico

**User pediu:** "qual era o caso clínico do slide e feijão? não lembro"

**Claude esclareceu:** referência ao template original (Grupo 8 do
template_grupos_proximidade.md), sem cenário concreto detalhado.

### P1 + P2 + HIST em bloco

**User:**
- (a) Aceito proposta minimalista. Mas precisamos de outra nomenclatura
  para `flexao joelhos` (todos exercícios são de flexão de joelhos).
  Sugestão: **`flexao deitado`** (une movimento + posição).

> **Insight biomecânico do user:** "A flexão no feijão e no slide é uma
> espécie de ponte isométrica (quadril fica estendido) junto com
> movimento de flexão de quadril. Cadeira Flexora é única com quadril
> em flexão (sentada)."

**INTRA:**
- (i) Cadeira Flexora + Flexão Feijão = **OK** (melhor combinação;
  Cadeira é única com quadril em flexão)
- (ii) Feijão + Slide = **Ruim** (movimentos quase idênticos)
- (iii) Cadeira + Nordic = **OK**
- (iv) Feijão + Nordic = **Tolerável** (movimentos similares mas
  posição diferente; ideal seria Cadeira)
- (v) Cadeira + Slide = **OK**

**INTER:**
- (a) Cadeira + Feijão + Slide = **Ruim** (evitar ao máximo)
- (b) Cadeira + Feijão + Nordic = **OK**
- (c) Cadeira + Nordic + Slide = **OK**

**HIST:** mantém.

> Sub-distinção quadril flexionado (Cadeira) vs estendido
> (Feijão/Slide/Nordic) **não modelada** — capturada indiretamente por
> equipamento+família. Aceitável dívida.

---

## GRUPO 7 — Tríceps (modo aberto)

**Exercícios:** 8 exercícios em 5 famílias após cleanup Etapa 1.

### Resposta abreviada do user

**User SIMPLIFICOU BASTANTE:**
- Cabeça muscular **NÃO é vetor primário.** Famílias resolvem.
- **Adicionar Tríceps Francês Corda** (variação família Francês)
- **Renomear Tríceps Polia Alta → Tríceps Pushdown**

> **DECISÃO ESTRUTURAL:** `musculo_alvo_especifico` (cabeça do tríceps)
> NÃO entra como dimensão. **Descartada uma das 5 dimensões propostas
> pelo guia v4.**

### Validação INTRA/INTER

**User:** "OK confirmo tudo" — modelo simplificado validado.

---

## GRUPO 8 — Pranchas (modo aberto)

**Exercícios:** 11 isométricos de core (7 pranchas + Dead Bug × 3 +
Hollow + Pallof + Roda).

### Respostas em prosa

**User decisões:**

**1. Família `prancha` muito ampla:**
- (a) **Separar família** (`prancha frontal` + `prancha lateral`)
- **MAS** "precisamos de uma forma de evitar que app junte 2 pranchas
  (até mesmo frontal+lateral) se usuário pedir core(2). App deve
  priorizar inserir abdominal de outro tipo."
- **CADASTROS NOVOS MASSIVOS — Família INFRA:**
  - Infra Alternado
  - Infra Suspenso (na barra fixa)
  - Infra Chão (bilateral)
  - Infra Roll-Up (flexão de quadril com rolagem/flexão de tronco)
- **Reclassificar:** Dead Bug C/ Anilha + Dead Bug C/ Bola → mover
  para família INFRA

**2. Plano de estabilização (anti-extensão/lateroflexão/rotação):**
- **NÃO MODELAR.** "É interessante a separação mas adiciona
  complexidade desnecessária."

> **DIRETRIZ DE DESIGN — PRINCÍPIO IMPORTANTE:** "Devemos relembrar
> durante esta refatoração que o **Personal sempre pode (e
> provavelmente vai) editar o treino para customizar os detalhes que
> precisa**. O gerador deve entregar a melhor 'base' possível."

**3. Equipamento em pranchas:** "Equipamentos contam, mas não o
suficiente para adicionar mais granularidade."

**4. Lateralidade:** "O exemplo que você deu seria o suficiente. Não é
necessária maior diversificação."

---

## CONSOLIDAÇÃO DA FASE 1

Claude consolidou os 8 grupos. User pediu (c) — ajustar antes de
seguir:

### Decisões pendentes esclarecidas pelo user:

1. **Pegada:** "Preciso da sua opinião. Se possível, vamos simplificar."
   - **Claude recomendou Opção A:** tag única com 4 valores + matriz
     custom 4×4. User: "**opção A**".

2. **Sub-distinção unilaterais:** **Não será necessário.**

3. **Step-up:** **Manter apenas com `caixa`** (caixa define a
   característica).

4. **Decisão de pausar:** (b) Gravar parcial, retomar Fase 2 noutra
   sessão.

---

## PERGUNTAS DO USER PÓS-GRAVAÇÃO (re-abertura)

### Pergunta 1 — "Equipamento universal?"

**User:** "O que isso significa na prática? Não quero que EQUIPAMENTO
interfira na seleção ou combinação entre exercícios de categorias
diferentes. Exemplo: Supino Barra ou Remada Curvada (ambos usam barra)
mas o filtro não deve interferir em nada nesta seleção (supondo que os
2 estão INTRA ou até no mesmo bloco). Correto?"

**Claude reconheceu confusão na redação.** Esclareceu:
- "Universal" = cobertura (toda linha taggeada)
- ≠ Escopo de aplicação (quando dispara penalidade)
- Propôs escopo: **mesma subregião** para penalidade biomecânica
  (equipamento, pegada, plano_corporal); família estrita = hard global;
  lateralidade = mesmo grupo muscular padrão

**User pediu exemplo prático.**

### Pergunta 2 — 4 cenários cross-grupo

**Claude apresentou 4 casos:**
- (i) Supino Halteres + Curvada Halteres (push+pull, mesmo halter)
- (ii) Supino Halteres + Crucifixo Halteres (composto+isolado peito)
- (iii) Goblet + Búlgaro (bi+uni quad)
- (iv) Goblet + Stiff Halteres (quad+hamstring)

**User: TODOS OK.**

> **Conclusão preliminar:** equipamento NÃO é dimensão de proximidade.
> Pode sair, libera 1 vaga das 5 dimensões.

### Pergunta 3 — 8 cenários adicionais

**Claude apresentou 8 cenários diversos** (costas, ombro, hinges,
tríceps).

**User TODOS OK**, com nuances:
- (6) Stiff Barra + Lev Terra: "OK. Equipamento não é determinante.
  Poderia combinar outro exercício, como hip thrust, mas ambos em
  intra é OK."
- (7) Hip Thrust C/ Band + Ponte C/ Band: "**Equipamento não é
  determinante.** Não combinaria pois exercícios são muito parecidos.
  Equipamento colabora para ficarem ainda mais parecidos (Band aumenta
  demanda dos abdutores), mas não é o que determina."

> **Claude propôs:** equipamento sai como dimensão de proximidade.
> Vira tag descritiva apenas (UI/filtros).

### Pergunta 4 — User contestou: caso Supino Inclinado Halteres

**User:** "Espere, tem algo errado. Confirme: T1 tem supino inclinado
halteres. App vai selecionar o próximo 'peito' → supino reto halteres
terá score menor (pior) do que supino reto barra, correto? Ou essa
última decisão altera isso?"

**Claude respondeu:** o cenário só faz sentido se família `Supino` for
refinada (Supino Reto ≠ Supino Inclinado). Apresentou 2 caminhos:
- (A) Manter família única — equipamento irrelevante (mas Inclinado em
  T1 e Reto em T2 é hard bloqueado INTER)
- (B) Refinar família por ângulo + manter equipamento como tiebreaker

### Pergunta 5 — User questionou angulo_movimento

**User:** "Outra pergunta: angulo_movimento estava sendo usada quando
finalizamos a sessão dos supinos/peito não? Você desistiu dela depois?"

**Claude reconheceu erro:**
- SIM, `angulo_movimento` foi decidido nos Supinos como dimensão.
- Erro de consolidação — efetivamente desistiu sem justificativa.
- **Solução proposta:** absorver em `plano_corporal` (em supinos,
  plano_corporal = reto/inclinado). Não cria dimensão extra.

### Combinação final proposta

**Set de 5 dimensões:**

| # | Dimensão | Em supinos | Função |
|---|---|---|---|
| 1 | `familia_estrita` | Supino Reto, Supino Inclinado (refinadas) | Hard filter |
| 2 | `lateralidade` | bilateral | Anti_uni mesmo grupo |
| 3 | `pegada` | aberta/neutra/pronada/supinada | Penalty matriz custom |
| 4 | `plano_corporal` | reto/inclinado (absorve angulo) | Penalty alta intra subregião |
| 5 | `equipamento_grupo` | barra/barra_guiada/halter/corporal | Tiebreaker peso baixo |

**Anexo de consertos cresce:**
- Refinar família `Supino` em `Supino Reto` e `Supino Inclinado`
- Cadastrar `plano_corporal` em todos exercícios de peito (Supinos +
  Crucifixos + Crossovers + Apoios)

### User pediu auditoria

**User:** "Exporte as mensagens desta sessão em um arquivo .md. Vou
precisar fazer uma auditoria de todo histórico de conversas. Respondi
muitas perguntas e dei muitas instruções nesta fase. Não podemos
deixar passar uma decisão importante como essa do supino."

---

## PONTOS DE AUDITORIA SUGERIDOS

Lista de decisões importantes que precisam ser RE-VALIDADAS pelo user
contra o documento `dimensoes_proximidade.md` atual:

### Decisões clínicas por grupo

1. **Supinos G1 — `angulo_movimento`** — decidido como dimensão
   transversal; foi (erroneamente) descartado na consolidação;
   re-introduzido absorvido em `plano_corporal` (reto/inclinado).
   **CONFIRMAR no documento.**
2. **Remadas G2 — Lateralidade INTRA crítica (~hard)** vs Squats G4
   Lateralidade INTRA = MÉDIO. Confirmar pesos por grupo.
3. **Remadas G2 — Pegada com sub-estrutura interna** (matriz custom
   4×4 — Opção A escolhida). Confirmar valores da matriz.
4. **Puxadas G3 — `plano_corporal = pullover`** como "âncora soft INTER"
   (regra fraca de diversificação).
5. **Squats G4 — `caixa` como tag de equipamento** — mas equipamento
   não é dimensão de proximidade (decisão pós-Fase 1). Tag continua no
   banco pra filtros, mas peso = ?
6. **Hinges G5 — `stiff` + `stiff uni` unificam** (lateralidade é tag
   separada). Diretriz para outras famílias gêmeas.
7. **Knee Flex G6 — Renomear `flexao joelhos` → `flexao deitado`.**
8. **Tríceps G7 — `musculo_alvo_especifico` DESCARTADA** como dimensão.
9. **Pranchas G8 — Família `prancha` separada em `prancha frontal` +
   `prancha lateral`.**
10. **Pranchas G8 — Família INFRA criada com 4 cadastros novos.**

### Decisões estruturais

11. **HISTÓRICO simplificado** — janela R-1 only, peso integral, toggle
    ON/OFF. **Altera o guia v4.**
12. **Pesos POR GRUPO/SUBREGIÃO** (não globais).
13. **Princípio "gerador como base"** — personal edita; gerador não
    precisa ser perfeito.
14. **Caminho B — refinar família Supino por ângulo + equipamento como
    tiebreaker.** AINDA PENDENTE confirmação final do user.
15. **Set final de 5 dimensões:** família, lateralidade, pegada,
    plano_corporal (absorvendo ângulo), equipamento (tiebreaker).
    AINDA PENDENTE confirmação.

### Anexo de consertos no banco (31 itens originais + cadastros novos)

Todos listados na seção 4 do `dimensoes_proximidade.md`. Auditar para
confirmar cada item.

### Cadastros futuros

- Apoio Fechado, Supino Fechado
- Variantes inclinadas Crucifixo/Crossover
- Remada Curvada Supinada (Yates)
- Variantes pegada em unilaterais (Serrote/Uni Polia Pronada Wide) —
  opcional
- Barra c/ borracha, Puxada Unilateral Polia, Pulldown Braço Estendido
- Barra Aberta + Barra Supinada (substituem Barra genérica)
- Recuo do Estepe
- Tríceps Francês Corda
- Família INFRA: Infra Alternado, Infra Suspenso, Infra Chão, Infra
  Roll-Up
- (Box Jump pendente decisão fica/sai)

---

## STATUS NO MOMENTO DA EXPORTAÇÃO

- ✅ Fase 1 — análise dos 8 grupos: **completa**
- ⏳ Fase 2 — derivação final das dimensões: **em andamento, com
  decisões pendentes** (incluindo o caso supinos/equipamento)
- ⏳ Fase 3 — calibração de pesos: pendente
- ⏳ Fase 4 — estratégia de preenchimento: pendente

**Documento principal:** `docs/refatoracao/dimensoes_proximidade.md`
(versão parcial gravada; precisa atualização com decisões pós-Fase 1
sobre equipamento, ângulo, e Caminho B)

**Próximo passo:** user audita transcript + documento, valida ou
contesta decisões pendentes, depois Fase 2 retoma com set de 5
dimensões finalizado.

---

*Transcript gerado em 2026-05-05 para auditoria da Sessão 1 da
Etapa 6.*
