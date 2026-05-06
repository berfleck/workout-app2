# Etapa 6 — Trabalho preparatório das tags multi-dimensionais

**Status:** parcial — Fase 1 completa + correções pós-auditoria
(2026-05-05) + **Sessão 2 (2026-05-06): refator estrutural CORE
aplicado**. Fase 2 em curso; Fases 3-4 pendentes.

**Branch:** `refator-gerador` · **Sem mudança de código** — etapa de
modelagem clínica e arquitetural que produz especificação para a Etapa 7.

---

## Correções pós-auditoria (2026-05-05)

Auditoria do user identificou 2 erros de consolidação na Sessão 1:

1. **`angulo_movimento` desaparecido** — decidido como dimensão nos
   Supinos (G1 P7) e descartado na consolidação sem justificativa.
2. **Inconsistência INTER em Supinos** — respostas G1 P5 do user
   pressupunham que 3 supinos podem coexistir em rotina de 3 treinos
   (com pelo menos 1 inclinado), incompatível com família `Supino`
   única + hard filter INTER.

**Correção aplicada (Caminho B aprovado pelo user):**

- Família `Supino` refinada em `Supino Reto` + `Supino Inclinado`
  (split por ângulo)
- `plano_corporal` ativado em supinos com valores `reto / inclinado`
  (absorve `angulo_movimento` sem dimensão extra)
- `equipamento_grupo` mantido como dimensão de proximidade com **peso
  BAIXO INTRA (tiebreaker)** — desempata pares iguais em outras
  dimensões
- Set FINAL congelado em **5 dimensões**: `familia_estrita` +
  `lateralidade` + `pegada` + `plano_corporal` + `equipamento_grupo`
- Anexo de consertos ganhou itens 15-bis (split família Supino) e
  15-ter (cadastrar plano_corporal em todos exercícios de peito)

**Lição metodológica registrada — anti-padrão "escopo→rigor"
(2026-05-05):**

Análise meta da Sessão 1 identificou um padrão estrutural problemático.
O princípio "gerador como base" (introduzido no G8 Pranchas) foi
invocado como diretriz de **escopo** ("não modelar a 6ª, 7ª, 8ª
nuance"), mas operacionalmente foi convertido em diretriz de **rigor**
("se algo é difícil de modelar, simplifica e vira responsabilidade do
personal"). Os dois soam parecido em prosa, mas são opostos.

**Casos identificados de regressão silenciosa:**

1. **Pranchas Frontal + Lateral INTRA** — user pediu mecanismo
   explícito ("precisamos de uma forma de evitar"); registrado como
   "abundância probabilística + personal edita".
2. **Step Up + Passada Dos Steps INTRA** — user marcou Ruim por causa
   da caixa; equipamento virou tiebreaker BAIXO depois, regredindo
   esse caso para "OK pelo modelo".

**Diretriz preventiva adicionada à Seção 1.1 do
`dimensoes_proximidade.md`:** quando o user pede modelagem ativa de um
caso, registrar como modelagem ativa; quando o user aceita não modelar,
registrar explicitamente como dívida aceita com justificativa.
Substituir modelagem ativa por "personal edita" silenciosamente é
regressão.

**Lição metodológica de processo:** sessões longas de modelagem têm
custo cognitivo real. Tentar fechar antes de cansar abre janela onde o
"vamos simplificar" do user vira salvo-conduto pra dúvidas pendentes
em outros pontos. Próximas sessões devem quebrar em mais blocos com
pausas (ex: Fase 1 deveria ter sido 2 sessões — 4 grupos cada — em
vez de comprimir tudo em uma).

Os 2 casos identificados acima estão registrados na seção "Decisões a
re-validar" do `dimensoes_proximidade.md` para validação na próxima
sessão antes de avançar para Fase 3.

---

**Sub-pendência registrada (não resolvida — decisão pra Etapa 7):**

Com Caminho B aplicado, `Supino Reto` virou família única englobando
Reto Barra + Reto Halteres + Reto Anilha. Como `familia_estrita` é hard
INTER, **rotina não pode ter 2 supinos retos diferentes em treinos
diferentes**. Mas o user marcou em P5(c) do G1 que "2 retos + 1
inclinado = OK". Esse cenário fica operacionalmente bloqueado pelo
hard INTER. Resíduo do mesmo problema em escala menor.

Três caminhos de resolução possíveis (decisão fica pra Etapa 7, depois
de simulação):

- **(a) Refinamento extremo** — `Supino Reto Barra`, `Supino Reto
  Halteres`, `Supino Reto Anilha` como famílias separadas. Libera (c)
  totalmente mas esvazia o hard filter (cada exercício vira sua família).
- **(b) Aceitar como dívida** — argumento: rotina típica raramente tem
  2+ peito por treino; sistema gera 1 reto + 1 inclinado + Crucifixo/
  Crossover/Apoio, comportamento que diversifica bem. (c) é caso de
  borda raro.
- **(c) Soft INTER** — remover hard INTER de família e deixar score
  resolver. Aí o cenário "2 retos diferentes em treinos diferentes"
  flui naturalmente: penalidade alta mas não bloqueio. Provavelmente
  fica resolvido naturalmente quando o destino final do hard INTER for
  decidido na Etapa 7.

Vai ser tratada junto com a decisão maior sobre hard INTER de família
na Etapa 7.

---

---

## O que foi feito (sessão 1 — 2026-05-03 a 2026-05-05)

### Decisões metodológicas iniciais

- **Lista de grupos:** 8 grupos iniciais (Supinos, Remadas, Puxadas,
  Agachamentos, Hinges→Extensão de Quadril, Flexões de Joelho, Tríceps,
  Pranchas). Apoios/Crossovers/Bíceps/Ombros vão para backlog. Espaço
  pra 2-3 extras se emergissem (não emergiram).
- **Modo de condução:** híbrido com viés guiado (múltipla escolha
  estruturada). Modo aberto (prosa) para Tríceps e Pranchas.
- **Anexo de "consertos pendentes no banco"**: capturados ao longo da
  Fase 1 como side-effect das discussões. Vai como anexo do documento
  principal, alimenta a Etapa 7.
- **Vinhetas fictícias HISTÓRICO:** para cada grupo, uma vinheta
  ilustrativa ("aluno X com 4-6 rotinas anteriores"). Usadas para
  calibrar peso HISTÓRICO sem o personal ter que imaginar do zero.

### Fase 1 — análise dos 8 grupos (todos os 8 fechados nesta sessão)

Para cada grupo, processo padrão:

1. Listagem nominal dos exercícios extraída do `banco_exercicios.xlsx`
2. Perguntas dirigidas (P1 hierarquia, P2-P3 granularidade, P4-P5
   cenários INTRA/INTER, P6 vinheta HISTÓRICO)
3. Síntese intermediária (tags + tabela de pesos)
4. Validação user → grupo fechado

**Grupos fechados:**

- ✅ Grupo 1 — Supinos (7 exercícios)
- ✅ Grupo 2 — Remadas (12 exercícios)
- ✅ Grupo 3 — Puxadas (7 exercícios + 5 cadastros futuros)
- ✅ Grupo 4 — Agachamentos (17 exercícios)
- ✅ Grupo 5 — Extensão de Quadril (19 exercícios) — renomeado de Hinges
- ✅ Grupo 6 — Flexões de Joelho (4 exercícios)
- ✅ Grupo 7 — Tríceps (8 exercícios + 1 cadastro novo)
- ✅ Grupo 8 — Pranchas / Core Isométrico (11 exercícios + 4 cadastros
  novos família INFRA)

Total: **85 exercícios discutidos diretamente** (≈ 70% do banco de 125)
+ **31 cadastros novos sugeridos** + **15 reclassificações pendentes**.

### Decisões estruturais consolidadas

1. **Pesos POR GRUPO/SUBREGIÃO** (não globais) — evidência clínica em
   múltiplos grupos: lateralidade INTRA varia de Crítico (remadas) a
   Médio (squats); plano corporal INTRA varia de Alto (hinges) a Médio
   (remadas) a ausente (squats).

2. **Princípio "gerador como base"** — diretriz de design registrada:
   "o gerador entrega a melhor base possível, não decisões perfeitas. O
   personal sempre pode (e provavelmente vai) editar pra customizar
   detalhes." Justifica simplificações em vários grupos.

3. **HISTÓRICO simplificado para janela de 1 rotina (R-1) com toggle
   ON/OFF** — ALTERA o guia v4 que propunha curva de decaimento
   1.0/0.5/0.25/0 nas 6 semanas. Justificativa: simplifica drasticamente
   calibração e UI; comportamento de "lembrar 4-6 semanas atrás" pode
   ser reaberto na Etapa 7 se necessário (dívida aceita).

4. **Famílias gêmeas bi/uni unificam** — `stiff` + `stiff uni` viram
   `stiff` único. Lateralidade é tag separada. Aplicar a outros pares.

5. **`equipamento_grupo` cross-grupo com 8 níveis** —
   `barra/barra_guiada/halter/polia/corporal/maquina/caixa/banda_elastica`
   + vazio. Mais granular do que precisaria, mas cada nível tem
   identidade clínica clara.

6. **Regra de precedência semântica para múltiplos elementos de
   equipamento** — Step Up = `caixa` (não `halter`), porque caixa define
   a característica clínica de proximidade.

7. **Pegada como tag única com 4 valores enumerados + matriz de
   distâncias custom 4×4** — opção A escolhida. Captura sub-estrutura
   (aberta=pronada-wide; pronada-fechada vs supinada-fechada) sem
   estourar orçamento de dimensões.

### Dimensões descartadas nesta etapa

Três dimensões que apareciam na proposta inicial do guia v4 foram
**descartadas** com base nas discussões:

- **`musculo_alvo_especifico`** (cabeça do tríceps) — Tríceps confirmou
  que famílias resolvem o problema. Desnecessário.
- **`posicao_carga`** (axial vs frontal vs distal) — Squats: já
  capturada por filtro de cargas (Etapa 4). Duplicaria trabalho.
- **`padrao_execucao`** — Squats: lateralidade + família já cobrem.
- **`plano_estabilizacao`** (anti-extensão / lateroflexão / rotação) —
  Pranchas: princípio "personal edita" justifica não modelar.

**Resultado:** **5 dimensões dentro do orçamento** (família, equipamento,
lateralidade, pegada, plano_corporal). Limite rígido respeitado.

### Surpresas / desvios do plano original

1. **Hierarquia de dimensões varia POR GRUPO de forma significativa.**
   Esperava-se que os pesos fossem similares entre grupos com pequenos
   ajustes; descobriu-se que, por exemplo, lateralidade INTRA é
   absolutamente crítica em remadas e apenas média em squats. Mudou a
   decisão arquitetural (pesos por grupo, não globais).

2. **`plano_corporal` é não-universal** — em alguns grupos (squats,
   knee_flex, tríceps, pranchas), não diferencia. Aceita vazio. Solução
   elegante mas não estava prevista no guia v4.

3. **HISTÓRICO simplificado drasticamente** — guia v4 propunha curva
   contínua; user preferiu janela=R-1 + toggle. Decisão tomada já no
   Grupo 1 (Supinos) e validada/repetida nos demais.

4. **Box Jump como caso especial** — não é problema de proximidade, é
   problema de timing/sequenciamento (explosivo precisa de musculatura
   fresca). User está considerando remover do banco.

5. **Cadastros novos massivos** — particularmente em Pranchas/Core, a
   família INFRA inteira (4 exercícios) precisa ser cadastrada. Anexo
   de consertos cresceu para 31 itens.

### Decisões pendentes pro user

- **Box Jump fica ou sai do banco?** Caso de timing não modelado.
- **Validar matriz de distâncias da pegada** (sec. 3.1 do
  `dimensoes_proximidade.md`) — calibração via simulação na Etapa 7,
  mas a forma da matriz já está congelada nesta etapa.
- **Sub-pendência "2 retos + 1 inclinado bloqueado pelo hard INTER"**
  (registrada acima na seção "Correções pós-auditoria") — decisão
  pra Etapa 7, junto com destino final do hard INTER de família.
- **Lacuna da pegada na tabela do G1** (linhas "a definir" INTRA/
  INTER/HISTÓRICO) — resolver na Fase 3 via simulação, mas pode
  receber estimativas iniciais na Fase 2 residual.

### Pontos abertos pra próxima sessão (Fase 2 residual)

- ~~Validar/congelar set de 5 dimensões~~ — ✅ resolvido na auditoria
  (Caminho B; `angulo_movimento` absorvido em `plano_corporal`).
- Consolidar regra de cadastro para futuros exercícios.
- Refinar diretrizes parciais (famílias gêmeas, precedência semântica,
  etc.) num documento de "manual de cadastro".
- **Decisão sobre Box Jump** — fica ou sai do banco? (caso especial
  de timing/sequenciamento, não modelado).
- Resolver lacuna da pegada na tabela de calibração do G1 (atualmente
  "(a definir)" INTRA/INTER/HISTÓRICO).

### Pontos abertos pra Fase 3

- Calibrar pesos numéricos (Crítico/Alto/Médio/Baixo/0 → escala
  numérica) alinhada com o sistema de score da Etapa 5.
- Estrutura de configuração de pesos por grupo (provavelmente dict por
  `subregiao`/`padrao` com fallback global).
- Refinar matriz de distâncias da pegada via simulação.

### Pontos abertos pra Fase 4

- Priorização de dimensões para preenchimento (quais 100%, quais
  parciais).
- Validação cruzada final com 8 problemas conhecidos (esboço já feito
  na Seção 6 do `dimensoes_proximidade.md`; consolidar).

---

## Critério de "feito" — checklist parcial

### Fase 1 — completa nesta sessão ✅

- [x] Lista de grupos validada (8 grupos)
- [x] Modo de condução escolhido (híbrido)
- [x] 8 grupos analisados grupo por grupo
- [x] Anexo de consertos no banco capturado (31 itens)
- [x] Vinhetas HISTÓRICO usadas para calibrar peso temporal
- [x] Síntese parcial gravada em `dimensoes_proximidade.md`

### Fase 2 — em grande parte resolvida

- [x] Set final de dimensões congelado (5 dimensões canônicas — pós-auditoria)
- [ ] Regra de cadastro consolidada
- [ ] Decisões pendentes da Fase 1 resolvidas (Box Jump, lacuna pegada)

### Fase 3 — pendente

- [ ] Tabela final de pesos INTRA/INTER/HISTÓRICO por grupo
- [ ] Pesos numéricos calibrados (escala numérica vs categorias)
- [ ] Estrutura de configuração de pesos por grupo

### Fase 4 — pendente

- [ ] Estratégia de preenchimento documentada
- [ ] Validação cruzada com 8 problemas conhecidos completa
- [ ] Documento revisado e aprovado pelo user

### Entregáveis finais (ao final da Etapa 6)

- [x] `docs/refatoracao/dimensoes_proximidade.md` (parcial)
- [x] `docs/refatoracao/logs/etapa_6.md` (parcial)
- [ ] Header de progresso do `guia_refatoracao_v4.md` atualizado (no
      final da etapa)
- [ ] Aprovação do user para avançar para Etapa 7

---

## Sessão 2 (2026-05-06) — Refator estrutural CORE

### Contexto

Iniciada para tackle dos 5 itens residuais da Fase 2 enumerados na
memória `project_etapa_6_fase_1.md`. Ordem proposta: Caso 1 → Caso 2 →
Box Jump → lacuna pegada → regra de cadastro.

Durante o tackle do Caso 1 (Pranchas Frontal+Lateral INTRA), user
identificou e propôs **solução estruturalmente superior** que tornou
todos os 3 caminhos discutidos originalmente (a/b/c) obsoletos.

### Decisão estrutural — refator CORE

**Problema diagnosticado (user):** o "budget de 5 dimensões" estava
funcionando como bloqueio injustificado a modelagens clínicas
adequadas. CORE tinha estrutura achatada (1 subregião, 2 padrões),
diferente das outras regiões que têm múltiplas subregiões.

**Reframe:** o budget era proxy contra inflação injustificada de
dimensões — não restrição absoluta. Critério real é cost-benefit por
dimensão. E mais: parte do que parecia "dimensão nova" pode ser
expressa via refator estrutural reusando mecanismos existentes.

**Refator aplicado (item 15-quater do Anexo):**

- **Subregião:** `core` → **`core_isometrico`** + **`core_dinamico`**
  (promovidos de padrão)
- **Padrão:** 2 antigos → **4 refinados** atravessando ambas
  subregiões (iso = anti-X, dyn = X):
  - `flexao_tronco`
  - `flexao_lateral`
  - `rotacao_tronco`
  - `flexao_quadril`

**Mapeamento de 25 exercícios** (20 atuais + Russian Twist + 4 INFRA
novos) detalhado em G8 do `dimensoes_proximidade.md`.

**Reclassificações decididas durante a sessão:**

- Canoinha: padrão (mantém core_dinamico) → `flexao_quadril` dyn
  (pareia com V-Up/INFRA)
- Roda Abdominal: subregião iso mantida; padrão → `flexao_tronco`
- Prancha Renegade: padrão → `flexao_tronco` (componente
  anti-rotação reconhecido mas curadoria simplificada)
- Abd Bicicleta: padrão → `flexao_tronco` dyn
- V-Up / V-Up Uni: padrão → `flexao_quadril` dyn
- Item 14 do Anexo (Dead Bug C/Anilha + C/Bola → família INFRA)
  SUPERSEDIDO — Dead Bugs ficam em família `Dead bug`; padrão
  `flexao_quadril` em iso captura a parte de flexão de quadril

**Lateralidades verificadas no banco** (sem mudança):

- Dead Bug regular: unilateral (alterna)
- Dead Bug C/ Anilha: bilateral (peso unificado)
- Dead Bug C/ Bola: unilateral (alterna)
- V-Up: bilateral; V-Up Uni: unilateral
- Pallof Press: unilateral (executa um lado por vez)

**Cadastro novo decidido:** Russian Twist (subregiao=core_dinamico,
padrao=rotacao_tronco). Wood Chop **NÃO** cadastrar (decisão user).

### Por que isso é melhor que os 3 caminhos da Sessão 1

Os 3 caminhos discutidos para Caso 1 eram:

- (a) Tag `categoria_core` — adicionaria dimensão nova
- (b) Âncoras na subregião core_isometrico — mecanismo extra
- (c) Aceitar como dívida — regressão silenciosa explícita

O refator estrutural:

1. **Não custa dimensão nova** — set de 5 mantido
2. **Reusa mecanismos existentes** — score `regiao_diff`/`padrao_diff`
   da Etapa 5 e demanda hierárquica da Etapa 3 já implementam o
   comportamento desejado
3. **Resolve mais que o Caso 1** — também captura "rotina só-iso"
   ou "só-dyn" via cycling natural em `regiao core(N)`
4. **É modelagem ativa** — Caso 1 sai de "abundância probabilística +
   personal edita" para "score desincentiva par" + "abundância amplifica"

### Decisão também considerada e descartada

**Dimensão `tipo_core` (iso/dyn) narrow-scope.** Proposta inicial
durante a sessão. User contra-propôs o refator estrutural (mais
limpo). `tipo_core` torna-se redundante com o refator porque a
informação iso/dyn já vive na subregião e o mecanismo de penalty por
subregião igual já existe no score.

### Caso 2 — Caminho 5 (família estrita biomecânica `subida_elevada`)

Após o refator CORE, user reabriu a discussão do Caso 2 (Step Up +
Passada Dos Steps INTRA). Discutimos 4 caminhos da Sessão 1 + Caminho
4 (split padrão squat_unilateral) e o user propôs **Caminho 5**:
criar família estrita nova capturando a mecânica biomecânica comum
(pé em apoio elevado + ROM hip ampliado).

**Decisão aprovada:** família **`subida_elevada`** agrupando:

- Step Up
- Step Up Alt.
- Passada Dos Steps
- Recuo do Estepe (cadastro futuro)

Padrão `squat_unilateral` intacto. Equipamento_grupo intacto. Box
Jump fica em `squat_bilateral` SEM família (uso clínico distinto).

**Trade-off aceito:** par "Passada (regular) + Passada Dos Steps"
perde hard de família (saem de famílias diferentes agora). Anti_uni
INTRA continua penalizando. Clinicamente é correção, não regressão
— Passada normal e Passada Dos Steps são biomecanicamente diferentes
(presença da caixa muda mecânica fundamental).

**Por que Caminho 5 venceu:**

- Padrão e equipamento intactos (sem regressão de configs/templates)
- Captura mecânica biomecânica explicitamente (alinha com Seção 1.4)
- Menor mudança de banco entre as opções (1 valor novo +
  4 reclassificações de família estrita)
- Cobre Recuo do Estepe naturalmente (cadastro futuro herda família)
- Box Jump fica isolado (caso especial de timing, não proximidade)

### Redefinição `familia_estrita` — hard INTRA + soft INTER alto

User identificou inconsistência conceitual durante a discussão do
Caminho 5: a Etapa 6 refinou famílias para granularidade fina (Supino
→ Reto + Inclinado; Prancha → frontal + lateral; criação de
`subida_elevada`) sem recalibrar o mecanismo de proteção. Hard duplo
INTRA+INTER era apropriado pra famílias "categoria muscular ampla"
antigas, não pra famílias refinadas.

Auditoria do histórico:

- **Guia v4 original (Etapa 6)** propunha pesos numéricos
  `100 INTRA / 80 INTER / 60 HISTÓRICO` — soft com peso alto.
- **Sessão 1 desviou para hard duplo** sem justificativa registrada.
- **Refinamento posterior das famílias** ignorou o desvio.

**Decisão aprovada (Sessão 2):** redefinir `familia_estrita` como:

- **INTRA: hard filter** (mantém — mesmo treino com 2 membros é
  redundância)
- **INTER: soft com peso alto** (~80% do INTRA)
- **HISTÓRICO: toggle ON/OFF** (sem mudança)

Aplicada uniformemente a todas as 8 tabelas de calibração dos grupos.

**Sub-pendência "2 retos + 1 inclinado bloqueado pelo hard INTER"
(P5(c) do G1, registrada na Sessão 1 pós-auditoria) — RESOLVIDA**
pela redefinição. Caminho (c) original confirmado.

**Implicação no toggle `relaxar_familia` do app:** semântica fica
ambígua na nova realidade (INTER já é soft por padrão). Decisão
sobre destino do toggle fica pra Etapa 7 (pós-simulação).

### Lição metodológica reforçada

A Sessão 2 confirmou e estendeu a lição da Sessão 1 sobre
**escopo vs rigor**:

- "Budget de N dimensões" funciona como proxy contra inflação
  injustificada, não como restrição absoluta.
- Quando user identifica modelagem clinicamente justificada,
  considerar:
  1. **Refator estrutural reusando mecanismos existentes**
     (subregião/padrão/score) — ex: refator CORE
  2. **Refinamento de família estrita** quando há proximidade
     biomecânica clara — ex: `subida_elevada`
  3. **Recalibração de mecanismos existentes** quando o refinamento
     prévio criou friction — ex: redefinição
     `familia_estrita = hard INTRA + soft INTER`
  4. **Adicionar dimensão narrow-scope** apenas se 1-3 não cobrem

### Itens da Fase 2 ainda pendentes

- Box Jump (decisão fica/sai)
- Lacuna pegada G1 (estimativa inicial INTRA/INTER/HIST)
- Regra de cadastro consolidada

### Atualizações em arquivos

- `dimensoes_proximidade.md`:
  - G8 reescrito (refator CORE) + G4 reescrito (Caminho 5)
  - Seção 1.4 redefinida (hard INTRA + soft INTER alto)
  - 8 tabelas de calibração atualizadas (INTER de família = "Alto
    (soft)")
  - Caso 1 e Caso 2 marcados ✅ em "Decisões a re-validar"
  - Sub-pendência "2 retos + 1 inclinado" marcada ✅ resolvida
  - Anexo de Consertos: itens 14 (supersedido), 15-quater (refator
    CORE), 15-quinquies (subida_elevada G4), 15-sexies (redefinição
    família), 26 (Recuo do Estepe atualizado), 32 (Russian Twist),
    33 (Box Jump renumerado)
  - Status do documento atualizado
- `logs/etapa_6.md`: esta seção (Sessão 2 ampliada).

---

## Métricas da Sessão 1

- **Duração estimada:** ~166k tokens nas mensagens (sessão longa,
  típico de etapa de modelagem)
- **8 grupos analisados** com profundidade clínica
- **31 itens** no anexo de consertos (15 reclassificações + 16
  cadastros novos + 0 decisões pendentes)
- **3 dimensões descartadas** (musculo_alvo_especifico, posicao_carga,
  padrao_execucao, plano_estabilizacao — na verdade 4)
- **5 dimensões mantidas** dentro do orçamento

*Log parcial. Próxima atualização ao fechar Fase 2.*
