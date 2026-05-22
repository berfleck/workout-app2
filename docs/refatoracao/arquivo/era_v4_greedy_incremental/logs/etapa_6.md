# Etapa 6 — Trabalho preparatório das tags multi-dimensionais

**Status:** ✅ **CONCLUÍDA em 2026-05-09** (Sessão 7c). Fases 1, 2, 3
fechadas. Fase 4 (preenchimento dos 125 exercícios no XLSX) absorvida
pela Etapa 7 — protocolo Seção 9 do `dimensoes_proximidade.md` aplica
em paralelo com implementação estrutural da Etapa 7.

**Última atualização:** 2026-05-09 (Sessão 7c — fechamento + transição
pra Etapa 7).

**Branch:** `refator-gerador` · **Sem mudança de código no motor** —
etapa de modelagem clínica e arquitetural que produz especificação
para a Etapa 7. Trabalho de código limitado a `tools/calibrar_pesos_dimensoes.py`
(harness empírico) + `tools/mocks/dimensoes_etapa_6.yaml` (overlay de
mocks).

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

### Fase 2 — completa ✅ (Sessão 2 — 2026-05-06)

- [x] Set final de dimensões congelado (5 core + 1 narrow-scope
      `variante_pontual` — pós-Sessão 2 ampliada)
- [x] Regra de cadastro consolidada (Seção 7 do `dimensoes_proximidade.md`)
- [x] Decisões pendentes da Fase 1 resolvidas:
  - [x] Caso 1 (Frontal+Lateral) — refator estrutural CORE
  - [x] Caso 2 (Step Up + Passada Dos Steps) — família `subida_elevada`
  - [x] Sub-pendência supino INTER — redefinição familia_estrita soft
  - [x] Box Jump — `ativo=false` (item 33)
  - [x] Lacuna pegada G1 — Médio em todos
- [x] Cadastros novos confirmados: Russian Twist (Wood Chop NÃO)
- [x] Coluna `ativo` adicionada (item 15-octies)

### Fase 3 — completa ✅ (Sessões 3-7c — 2026-05-07 a 2026-05-09)

- [x] Decomposição metodológica E.0-E.2 + D1-D3 + B + A + C (Sessão 3)
- [x] E.0 — 13 cenários-âncora congelados (Sessão 3)
- [x] E.1.a — pipeline harness validado (Sessão 3)
- [x] D1 — predicado `_compativel_intra` centralizado (Sessão 4)
- [x] E.1.b parcial — 5 cenários no harness (Sessão 5)
- [x] Auditoria E.0 vs uso real + 4 redefinições + 2 notas processo (Sessão 6)
- [x] D2 — composição soft INTRA (Sessão 6)
- [x] 6.2 implementado — happy path Variante B (Sessão 6)
- [x] D3 — INTER soft + HISTÓRICO toggle (Sessão 6)
- [x] B — estrutura de configuração de pesos (Sessão 6)
- [x] A — escala numérica final (Sessão 6)
- [x] C — calibração processo definido (Sessão 6 — execução real pos-Etapa 7)
- [x] E.1.b2 — 8 cenários soft + mocks G2/G3/G4/G8 (Sessões 7a/7b/7c)
- [x] Tabela final de pesos INTRA/INTER/HISTÓRICO por grupo + estrutura
      de configuração — Seções 8.10/8.11 do `dimensoes_proximidade.md`

### Fase 4 — absorvida pela Etapa 7 (executada em paralelo)

Protocolo de preenchimento dos 125+ exercícios registrado em Seção 9
do `dimensoes_proximidade.md`. Acontece em paralelo com Etapa 7
estrutural (mock_futuros do YAML — 11 exercícios — vão pro XLSX
real durante Fase 4). Decisão Sessão 7c: Fase 4 não bloqueia Etapa 7.

### Entregáveis finais (ao final da Etapa 6) ✅

- [x] `docs/refatoracao/dimensoes_proximidade.md` (Seções 1-9 completas)
- [x] `docs/refatoracao/logs/etapa_6.md` (este documento — atualizado
      em 7c cobrindo Sessões 1-7c)
- [x] `tools/calibrar_pesos_dimensoes.py` — harness com 16 cenários
- [x] `tools/mocks/dimensoes_etapa_6.yaml` — 78 mocks (8 grupos +
      11 mock_futuros)
- [x] Header de progresso do `guia_refatoracao_v4.md` atualizado
      (Sessão 7c)
- [x] CLAUDE.md com seções "Etapa 6 Fase 3" + "Etapa 7" (decisões
      fechadas)

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

### Box Jump + coluna `ativo` no XLSX

User decidiu: Box Jump fica no banco mas `ativo=false`. Decisão
estendida pra criar coluna nova `ativo` (boolean, default `true`) no
XLSX. `carregar_banco` filtra `ativo=true` antes de retornar.

Vantagens sobre remover linha:
- Histórico de rotinas antigas preserva referências ao exercício
- Reativação trivial (toggle no XLSX)
- Uma linha por exercício (sem duplicação ao re-cadastrar)
- Permite cadastrar exercícios em desenvolvimento sem afetar gerador

Itens novos no Anexo: 15-octies (coluna `ativo`) + Box Jump como
aplicação imediata. Item 33 do Anexo 4.3 (pendência fica/sai)
✅ resolvido.

### Pegada G1 + tag `variante_pontual`

User identificou problema durante a discussão de "lacuna pegada G1":
variante "fechada" (Supino Fechado, Apoio Fechado — cadastros futuros)
é uso pontual; quer regra "max 1 por rotina cross-family dentro da
subregião peito".

Análise de 4 caminhos:
- (α) refinar pegada em 5º valor `fechada` — quebra matriz 4×4
- (β) tag booleana `variante_pontual` — ✓ escolhida
- (γ) família virtual `peito_fechado` — viola Seção 1.4
- (δ) âncora reversa rotação-level — mecanismo novo

**Decisão: tag `variante_pontual`** (boolean, default `false`):
- Marca `true` em Supino Fechado + Apoio Fechado (futuros)
- Escopo: cross-family **dentro da mesma subregião**
- Calibração: INTRA Alto / INTER Soft Crítico (~95% bloqueio
  efetivo) / HIST Médio
- Generalizável: qualquer "uso pontual cross-family" futuro reusa
  tag dentro do escopo da própria subregião

**Pegada G1 fixada como "Médio" em todos os contextos** (calibração
inicial). Vetor primário em supinos é ângulo (`plano_corporal`); pegada
vira fator desempate.

Set de dimensões: 5 core + 1 narrow-scope booleana = 6 total. Filosofia:
budget de 5 é proxy contra inflação injustificada, não restrição
absoluta. Tags narrow-scope com case clínico forte e cost baixo
passam o critério custo-benefício. `variante_pontual` é o segundo
precedente (após `pegada` e `plano_corporal` serem não-universais).

Item novo no Anexo: 15-septies (tag `variante_pontual`).

### Regra de cadastro consolidada — Seção 7 nova em `dimensoes_proximidade.md`

User aprovou as 22 diretrizes propostas (sem comentários adicionais).
Seção 7 nova adicionada ao documento, organizada em:

- 7.1 Família estrita (5 diretrizes)
- 7.2 Equipamento (4 diretrizes)
- 7.3 Pegada (3 diretrizes)
- 7.4 Plano corporal (2 diretrizes)
- 7.5 Lateralidade (3 diretrizes)
- 7.6 Estrutura subregião/padrão (3 diretrizes)
- 7.7 Tag `variante_pontual` (1 diretriz)
- 7.8 Status `ativo` (1 diretriz)
- 7.9 Dimensões descartadas (5 explicitamente NÃO cadastrar)
- 7.10 Checklist de cadastro pra exercício novo (passo-a-passo)

**Fase 2 fechada.**

### Resumo da Sessão 2 (2026-05-06)

Sessão produziu 7 decisões de design grandes:

1. Refator estrutural CORE (subregião + 4 padrões refinados)
2. Família estrita `subida_elevada` no G4 (Caminho 5 do Caso 2)
3. Redefinição `familia_estrita` = hard INTRA + soft INTER alto
4. Tag `variante_pontual` (#6 narrow-scope)
5. Coluna `ativo` no XLSX + Box Jump inativo
6. Pegada G1 fixada Médio (calibração inicial)
7. Seção 7 — Regra de cadastro consolidada (22 diretrizes)

Resolveu Caso 1, Caso 2, sub-pendência "2 retos + 1 inclinado", item
33 do Anexo (Box Jump), lacuna pegada G1.

Cadastrou Russian Twist (rotacao_tronco dyn) — Wood Chop NÃO
cadastrar.

### Próximos passos

- **Fase 3 (próxima sessão):** calibração numérica de pesos
  (Crítico/Alto/Médio/Baixo/0 → escala 0-1000 ou similar) alinhada
  com sistema de score da Etapa 5. Provavelmente junto com simulação
  inicial pra validar pesos.
- **Fase 4 (subsequente):** estratégia de preenchimento dos 125+
  exercícios + validação cruzada final com 8 problemas conhecidos.

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

## Sessão 3 (2026-05-07) — E.0 + harness pipeline

### Contexto

User pushou pushback construtivo na ordem A→B→D→C→E proposta inicial
da Fase 3, identificando 2 fragilidades:

1. **Bloco D (composição) é mais arriscado** — score atual mistura
   bônus positivo (regiao_diff +1000, padrao_diff +100) com penalty
   (anti_uni). Adicionar 6 dims da Etapa 6 como penalty pode gerar
   double-counting ou cancelamento. Decisão de composição afeta onde
   Crítico/Alto caem na escala (Bloco A) — D antes de A, não depois.
2. **Bloco E (harness) é pré-requisito, não posfácio** — sem harness
   funcional, cada decisão de peso é abstração. Com harness, mudar
   número e medir.

### Decisões grandes

- **Decomposição final aprovada (D em D1/D2/D3, E em E.0/E.1.a/E.1.b/E.2):**
  ordem `E.0 → E.1.a → D1 → E.1.b parcial → D2 → harness INTRA → D3 →
  harness INTER/HIST → B → A → C → E.1.b2 → E.2`. Substitui a A→B→D→C→E
  original.
- **E.0 — 13 cenários-âncora fechados** em 5 categorias + 1 sanity:
  - C1 hard INTRA (1.1 família, 1.2 anti_uni retroativo, 1.3 variante_pontual)
  - C2 soft INTRA composição (2.1 ranking ordinal, 2.2 lateralidade
    por grupo, 2.3 pegada+plano cumulativo)
  - C3 soft INTER (3.1, 3.2, 3.3)
  - C4 HISTÓRICO toggle (4.1, 4.2)
  - C5 escopo + retroativo (5.1, 5.2)
  - C6 sanity over-penalização (6.1)
- **5 exclusões deliberadas** registradas: refator CORE Prancha F+L
  (resolvido por padrao_diff), Tríceps cabeças (musculo_alvo
  descartada G7), Box Jump (filtragem `ativo=false`), `relaxar_familia`
  (decisão pendente Etapa 7), composição com filtro de cargas (escopo
  separado).
- **E.1.a — pipeline harness end-to-end validado:** cenário 1.1 ×
  1000 iters → 0/1000 violações. Confirma que overlay funciona
  (variacao_de reescrito Supino → Supino Reto/Inclinado em 4 supinos)
  e hard filter pré-existente respeita família refinada.

### Surpresas / desvios

- **Decomposição refinada motivada por feedback do user**, não
  prevista no plano inicial. Ordem original A→B→D→C→E ignorava risco
  de composição.
- **Harness empírico em 1000 iters** vs 100 da Etapa 5 (entropia).
  Justificativa: 1000 iters dá faixas clínicas estatisticamente
  estáveis pra cenários soft (esperados <10%, 20-50%, etc.).

### Atualizações em arquivos

- `tools/calibrar_pesos_dimensoes.py` — harness pipeline + cenário 1.1
- `tools/mocks/dimensoes_etapa_6.yaml` — 12 exercícios cadastrados
  (peito) + 2 mock_futuro (Supino Fechado, Apoio Fechado)
- `requirements.txt` — `+pyyaml`
- `dimensoes_proximidade.md` Seções 8.1-8.3 (decomposição + E.0 + E.1.a)

### Pontos abertos pra Sessão 4

- D1 filtros hard centralizados — decidir onde plugar predicado.
- E.1.b parcial — implementar cenários 1.2, 1.3, 6.1, 5.1, 5.2 (que
  não dependem de D2/D3).

---

## Sessão 4 (2026-05-08) — D1 filtros hard centralizados

### Contexto

User abriu Sessão 4 com proposta de D1 (filtros hard) antes de D2
(soft INTRA). Razão: predicado é arquiteturalmente independente do
score; resolver D1 limpa "como" hard funciona antes de D2 calibrar
"quanto" o soft pesa.

### Decisões grandes (4)

- **D1.a — predicado único `_compativel_intra(cand, alocados, dims)`**
  em `pre_alocar_rotina`. Substitui o atual check `variacao_pais_intra`
  por chamada que cobre 3 regras hard. Separa proximidade de recursos
  físicos (`pode_adicionar_ao_bloco` continua focado em
  carga/fadiga/equipamento bloqueado/complexidade).
- **D1.b — família INTRA hard** continua (continuidade — migra do
  `variacao_pais_intra` atual pra dentro do predicado em Etapa 7).
- **D1.c — `variante_pontual` promovido a hard INTRA real** (era
  "Alto soft" na Sessão 2). INTER mantém Soft Crítico (~95% bloqueio
  efetivo).
- **D1.d — lateralidade hard contextual via
  `SUBREGIOES_LATERALIDADE_HARD = frozenset({"costas"})`.** G2 único
  Crítico hard; outras subregiões continuam soft via
  `anti_uni_mesmo_grupo` da Etapa 5 (peso por grupo calibrável em D2).

### Surpresas / desvios

- **`variante_pontual` virou hard INTRA**, não soft Alto como
  proposto na Sessão 2. Razão: predicado central centraliza toda a
  proteção hard num lugar — fica mais limpo. Soft Crítico INTER
  continua via score.
- **`anti_uni_mesmo_grupo` da Etapa 5 NÃO migra pro predicado** —
  fica ortogonal. Hard contextual D1.d cobre só costas; outras
  subregiões usam soft -75 da Etapa 5.

### Atualizações em arquivos

- `dimensoes_proximidade.md` — Seção 1.7 nova (predicado), Seção 2
  G1+G2 tabelas atualizadas, Seções 7.5+7.7, Seção 8 nova (Fase 3
  progress) com 8.1/8.2/8.3/8.4
- Sem mudança de código (Etapa 7 implementa predicado real).

### Pontos abertos pra Sessão 5

- E.1.b parcial — implementar cenários 1.2, 1.3, 6.1, 5.1, 5.2 (todos
  os hard + sanity que não dependem de D2/D3 numérico).

---

## Sessão 5 (2026-05-08) — E.1.b parcial (5 cenários)

### Contexto

Sessão arrancou implementando os 5 cenários do E.1.b parcial
(não-bloqueados por D2/D3 numérico). User pediu também documento
auxiliar `configuracoes_comuns.md` registrando uso projetado do app
(full body 6-8 ex, split Empurrar/Puxar, ciclos A1/A2/B1/B2) — vira
fonte de verdade pra calibração realista.

### Decisões grandes

- **5 cenários implementados:**
  - **1.1 OK** (0.00%) — família refinada hard INTRA confirmada
  - **1.2 OK** (0.00%) — anti_uni soft -75 retroativo Etapa 5 em braços
  - **1.3 FAIL baseline** (5.00%) — variante_pontual hard INTRA,
    predicate não implementado pré-Etapa 7
  - **2.2A FAIL baseline** (4.30%) — lateralidade hard contextual
    costas, predicate não implementado pré-Etapa 7
  - **5.2 OK** (82.80% pareados) — V-Up Uni + Tríceps Uni preferencial
    (não-regressão da Etapa 5)
  - **6.1 OK** (0.00% E6 primária, 100.00% E3 secundária informativa)
- **Refinamento 6.1:** métrica primária só com avisos E6
  (`incompleta`, `familia_repetida`); secundária com
  `ancora_nao_cumprida` (Etapa 3 — informativa, não afeta status).
- **5.1 movido pra E.2** — não testável até penalties soft existirem.
- **Documento `configuracoes_comuns.md` introduzido** — vira fonte de
  verdade pra setup realista (vs patológico) na auditoria E.0 pendente.

### Surpresas / desvios

- **Refinamento 6.1 motivado por achado paralelo `ancora_nao_cumprida`
  (Etapa 3, vagas insuficientes upper(3))** — flagado mas mantido
  como informativo. Não é regressão da Etapa 6, é apertura natural
  do setup `upper(3)` clinicamente.
- **2 cenários FAIL baseline** (1.3, 2.2A) são esperados pré-Etapa 7
  — quantificam gap a fechar quando predicado for implementado.

### Atualizações em arquivos

- `tools/calibrar_pesos_dimensoes.py` — 5 cenários implementados
- `tools/mocks/dimensoes_etapa_6.yaml` — sem mudança (mocks G1
  suficientes pros 5 cenários)
- `docs/refatoracao/configuracoes_comuns.md` — novo documento
- `dimensoes_proximidade.md` Seção 8.5

### Pontos abertos pra Sessão 6

- Auditoria E.0 vs uso real (5 ⚠️ patológicos vs ✓ representativos).
- D2 numérico — composição soft INTRA.
- 6.2 implementação — happy path Variante B 2x.
- D3 numérico — INTER soft + HISTÓRICO toggle.
- B + A + C — estrutura de configuração + escala numérica + processo
  de calibração.

---

## Sessão 6 (2026-05-08) — Fechamento Fase 3 conceitual (7 blocos + 2 notas + 1 bug)

### Contexto

Sessão **excepcional em produtividade**: arrancou com auditoria E.0
e fechou TODOS os 7 blocos de decisão restantes da Fase 3 conceitual
(Auditoria + D2 + 6.2 + D3 + B + A + C) numa virada conceitual única.
Total: 6 horas de trabalho intensivo, 7 decisões grandes, 2 notas
metodológicas, 1 bug paralelo.

### Decisões grandes (7 blocos)

**Bloco 1 — Auditoria E.0 vs uso real (Seção 8.6):**

13 cenários revisados contra `configuracoes_comuns.md`. Distribuição
final: 8 ✓ representativo, 7 ⚠️ patológico necessário, 0 ❓.
**4 redefinições aprovadas:**

1. **6.2 promovido pra pré-D2** — cobre Variante B 2x subregião + vira
   proxy realista pros gotchas de 1.2 e 2.2A via sub-métricas
   a (blocos com 2+ unilaterais de braço) e b (rotinas com 2+
   unilaterais em costas(3)).
2. **2.2B → `perna_anterior(3) × 1 treino`** — era squat_unilateral(2)
   artificial; agora Variante B 2x direto.
3. **3.1 → rotina Variante B 3x A1/A2 com peito em ambos** — era
   "rotina 3T toda de peito" caricatural.
4. **2.3 → timebox 15-30min** — testar `costas(3) × 1 treino`
   realista; ≥5% de "2 ex pegada+plano colidindo" = ✓; senão ⚠️
   densificado.

**Bloco 2 — D2 composição soft INTRA (Seção 8.7):**

- **D2.1 — Variante a** (constante por dim, peso por subregião):
  penalty binária igual/diferente, não matriz de distância
  categórica. Justificativa clínica: sem evidência de que
  pronada-supinada seja mais distante de pronada-neutra; calibrar
  4×4 seria adivinhação.
- **D2.2 — Caminho B com escala provisória ~-100/-50/-20/-5**
  (Crítico/Alto/Médio/Baixo): geo-diversidade é sacrossanta
  (`regiao_diff +1000` não é overridado). Penalty soft atua quando
  geo empata.
- **D2.3 — Par-a-par cumulativa**: gradiente preserva discriminação
  clínica. Set-based achata. Custo O(N²) desprezível.

**Bloco 3 — 6.2 implementado no harness (Seção 8.8):**

Variante B 2x: peito(2)+ombro(1)+perna_post(3)+core_dinamico(1)+
padrão tríceps(1) // costas(3)+perna_ant(3)+core_isometrico(1)+
padrão bíceps(1). Refactor `Cenario` dataclass pra lista de
secundárias. **Resultado 1000 iters:** primária 0.00% OK; sub-a
0.30%; sub-b 3.30%.

**Bloco 4 — D3 INTER soft + HISTÓRICO toggle (Seção 8.9):**

- **D3.1 — INTER multiplicador global 0.8** com overrides
  documentados (família ~0.80, variante_pontual ~0.95).
- **D3.2 — Migração família INTER hard → soft alto: Caminho C**
  (spec agora, migração estrutural Etapa 7). Decisão "A clean
  break vs B coexistência" registrada como ponto de auditoria pra
  Etapa 7.
- **D3.3 — HISTÓRICO toggle ON: granularidade nome + família,
  soma livre com INTER (sem clipping).** R-1 only.
- **D3.4 — Fase 0 (`pre_alocar_rotina`) junto com INTER soft.**

**Bloco 5 — B estrutura de configuração de pesos (Seção 8.10):**

- **B.1 — Módulo separado `pesos_proximidade.py` com dataclass.**
- **B.2 — Hierarquia 2 níveis** (default → subregião) + estrutura
  paralela `anti_uni_mesmo_grupo`.
- **B.3 — Raiz do projeto, arquivo único.**
- **B.4 — Argumento opcional `pesos_override`** em
  `gerar_multiplos_treinos`.
- **B.5 — Labels categóricos em B + mapping numérico em A.**

**Bloco 6 — A escala numérica final (Seção 8.11):**

- **A.1 — Mapping confirmado D2.2 (-100/-50/-20/-5).** Progressão
  custom (2.0×/2.5×/4.0×) reflete papéis funcionais distintos.
- **A.2 — Anti_uni Etapa 5 (-75) fica fora da escala unificada**
  (estrutura paralela, ortogonal).
- **A.3 — Derivados INTER/HISTÓRICO validados.** INTER 0.8 dá
  Crítico-80/Alto-40/Médio-16/Baixo-4 + variante_pontual ×0.95 =
  -95. HISTÓRICO ON multiplicador 1.0 = INTRA peso.

**Bloco 7 — C calibração fina iterativa (Seção 8.12):**

- **C.1 — Manual + coordinate descent.** 1 dim por vez fixando
  outras, baseado em hipótese clínica.
- **C.2 — Ordem das dims:** Família INTER (3.1/3.2/3.3) →
  Plano+Pegada acopladas (2.1/2.3) → Lateralidade soft (2.2B) →
  HISTÓRICO toggle (4.1/4.2) → Equipamento_grupo (tiebreaker, último).
- **C.3 — Critério parar:** todos cenários nas faixas E.0 +
  sub-métricas 6.2 estáveis (<2× alteração) + cap 5-10 rounds/dim.
  **Validação cruzada é a parte mais importante.**
- **C.4 — Sequencial após E.1.b2 + calibrar contra stub harness +
  sanity pós-Etapa 7.**

### 2 notas metodológicas (promovidas pra Seção 1.8)

- **#1 Densificação patológica ≠ anti-padrão escopo→rigor:** setups
  densos como `peito(3)`, `bracos(4)`, `remadas(2)` são necessidade
  empírica (forçar coexistência rara virar mensurável em 1000 iters).
  Diferente de modelar mecanismo fraco. Distinção operacional: se
  calibração é revalidada em setup realista é densificação saudável;
  se não, é regressão silenciosa.
- **#2 Calibrar denso, validar realista:** pesos calibrados contra
  patológico (1.2 `bracos(4)`, 2.2A `remadas(2)`) precisam validação
  contra sub-métricas do 6.2 antes de fechar a calibração da dim.

### 1 bug paralelo registrado

**Bug retrocompat `("subregiao", "core", N)`** falha alocação
(`qtd_obtida=0`). Workaround: usar `core_dinamico`/`core_isometrico`
direto. Débito técnico do refator CORE da Sessão 2 — investigação
separada (fora do escopo da Sessão 6).

### Surpresas / desvios

- **Sessão fechou 7 blocos de uma vez** quando o plano original
  previa 2-3 sessões. Razão: blocos D2 → 6.2 → D3 → B → A → C têm
  dependências naturais que se encadeiam — fechar um habilita o
  próximo sem nova rodada de discussão clínica.
- **6.2 sub-b 3.30% em setup realista vs 2.2A 4.30% em patológico**
  (dentro de 1pp) — valida nota metodológica #2: peso hard
  contextual D1.d calibrado contra patológico provavelmente cobre o
  realista.
- **3 ajustes finais de captura/processo (pré-fechamento):**
  - Seção "Etapa 6 Fase 3 — decisões fechadas" no `CLAUDE.md`
  - Notas processo promovidas Seção 8.6 → Seção 1.8
    (`dimensoes_proximidade.md`)
  - Protocolo Fase 4 registrado em Seção 9 nova

### Atualizações em arquivos

- `tools/calibrar_pesos_dimensoes.py` — 6.2 + refactor
  `metricas_secundarias`
- `dimensoes_proximidade.md` Seções 8.6-8.13 + Seção 1.8 + Seção 9
- `CLAUDE.md` Seção "Etapa 6 Fase 3 — decisões fechadas"

### Pontos abertos pra Sessões 7a/7b/7c (E.1.b2)

- Mocks G2 (remadas + puxadas), G4 (squats + subida_elevada),
  G8 (core).
- 8 cenários soft restantes: 2.1, 2.2B (redefinido), 2.3 (timebox),
  3.1 (redefinido), 3.2, 3.3, 4.1, 4.2.
- Cap até C executado pos-Etapa 7.

---

## Sessão 7a (2026-05-08) — E.1.b2 G2/G3 + 2.2B + timebox 2.3

### Contexto

Primeira sub-sessão do E.1.b2. Escopo focado: G2 (remadas + puxadas) +
cenário 2.2B redefinido + timebox 2.3 conforme decisão da auditoria.
3 entregas em paralelo.

### Decisões grandes

- **G2/G3 cadastrados no YAML** — 12 remadas + 7 puxadas + 2
  mock_futuros (Barra Aberta + Barra Supinada — split da Barra
  genérica per Section 2 G3). Total 33 mocks.
- **Decisões clínicas registradas (triagem Seção 9.1, 4 critérios
  agrupados):**
  - **A:** Curvada Halteres pegada=`pronada` (preferência user);
    Apoiado + Seal=`neutra`.
  - **B:** Seal plano=`apoiada` (par Seal+Apoiado=Ruim, modelagem
    ativa); Landmine plano=`curvada`; Uni Polia plano=
    `unilateral_apoiada` (half-kneeling = apoio do joelho).
  - **C:** Barra Fixa+Iso pegada=`aberta` + equipamento=`corporal`.
  - **D:** `variante_pontual=false` em todos G2+G3.
- **Cenário 2.2B implementado** (`perna_anterior(3) × 1 × 1000`):
  observou **0.00%** vs <70% expectativa.
- **Timebox 2.3 executado** (`costas(3) × 1 × 1000`):
  - A. 2+ ex mesma pegada em costas: 65.80%
  - B. 2+ ex mesmo plano em costas: 1.50%
  - **C. pegada+plano colidindo: 1.50%** < 5% limiar
  - D. 2+ mesma família (sanity hard): 0.00% ✓
- **Verdict 2.3:** **2.3 oficialmente ⚠️ densificado** (decisão
  Seção 8.6 confirmada). 100% das 15 colisões observadas =
  `Remada Apoiado + Remada Seal Halteres` (caso modelado em
  decisão B).

### Surpresas / desvios

- **Achado paralelo crítico Sessão 7a:**
  `_ordenar_padroes_por_prioridade` embaralha squat_bilateral|
  squat_unilateral 50/50 (~497/503), MAS `_selecionar_ciclando` em
  modo subregião com `preferir_composto=True` produz **100%
  2bi+1uni** independente da ordem do shuffle. Resultado:
  **2.2B redefinido NÃO exercita o anti_uni soft em perna_anterior**
  do jeito que auditoria E.0 esperava. Banco efetivamente nunca
  propõe 2 unis em perna_anterior(3).
- **2.2B vira gate de não-regressão** — passa trivialmente <70%.
  Calibração real de lateralidade soft Médio em squats fica adiada
  pra setup mais denso (`perna_anterior(4)` ou `padrão
  squat_unilateral(2)`) — virou Decisão 1 do fechamento Sessão 7a.

### 3 decisões de processo registradas no fechamento (Seção 8.14.2)

1. **Cenário 2.4 dedicado** (`padrão squat_unilateral(2)`) pra
   calibração de lateralidade Médio em squats — implementação em 7b.
2. **Pré-registro 2.3 densificado:** costas(4) faixa 4-12% / costas(5)
   10-25%. Critério de leitura registrado pra evitar viés de
   confirmação.
3. **Dimensões não-aplicáveis = `null`** — confirmação pra G4/G8.
   Anti-padrão "default neutra" registrado.

### Atualizações em arquivos

- `tools/mocks/dimensoes_etapa_6.yaml` — G2 + G3 cadastrados
  (33 mocks total)
- `tools/calibrar_pesos_dimensoes.py` — cenário 2.2B
- `dimensoes_proximidade.md` Seções 8.14.1 + 8.14.2

### Pontos abertos pra Sessão 7b

- Mocks G4 (squats + `subida_elevada`).
- Cenários 3.2 (subida_elevada INTER), 3.3 (Passada + Passada Dos
  Steps INTER), 2.3 densificado, 2.4 (squat_unilateral(2)).

---

## Sessão 7b (2026-05-08) — E.1.b2 G4 + 4 cenários novos

### Contexto

Segunda sub-sessão E.1.b2. Escopo G4 (squats refinados +
`subida_elevada` + Recuo do Estepe mock_futuro) + 4 cenários (2.3
densificado, 2.4 squat_unilateral, 3.2 família INTER, 3.3 famílias
dif). Triagem G4 ágil porque Section 2 G4 já fixou maior parte das
decisões.

### Decisões grandes

- **G4 cadastrado** — 17 cadastrados + 1 mock_futuro (Recuo do
  Estepe). YAML chegou em 51 mocks total. Família `subida_elevada`
  com 4 membros corretos.
- **Decisões clínicas (5 critérios A→E):**
  - **A:** reclassificação `subida_elevada` confirmada (Step Up +
    Step Up Alt + Passada Dos Steps + Recuo do Estepe).
  - **B:** Recuo C/ Barra mantém `Recuo` (caso de borda Sessão 7a
    fechado — solo, sem apoio elevado posterior).
  - **C:** equipamento da `subida_elevada` = `caixa` (Seção 7.2
    diretriz 7 — apoio elevado precede halter).
  - **D:** Recuo do Estepe extras: comp=3, fad=3 (alinha Step Up).
  - **E:** `variante_pontual=false` em todos 18.
- **4 cenários novos:**
  - **2.3** (costas(4) × 1): 1.10% < 4% pré-registrado → escalada
    pra costas(5) → **5.20%** (faixa revisada 2-10%).
  - **2.4** (squat_unilateral(2) × 1): **100.00%** (baseline pre-D2).
  - **3.2** (2 treinos × squat_unilateral(2)): **0.00%** (família
    hard INTER pre-Etapa 7).
  - **3.3** (mesmo setup 3.2): **41.80%** (faixa 20-50% E.0 ✓).

### Surpresas / desvios

- **2.3 densificação revisada de costas(4) → costas(5)** porque
  costas(4) baseline ficou abaixo de 4% (1.10%). Conforme decisão
  de leitura pré-registrada na Sessão 7a.
- **Lição registrada (auto-correção pré-registro 2.3):** após hard
  família INTRA proteger membros mesma família, banco em costas tem
  efetivamente **1 par único mensurável** — `Remada Apoiado + Remada
  Seal Halteres` (pegada=neutra+plano=apoiada). Faixa pré-registrada
  10-25% partia de hipótese "múltiplos pares possíveis"; realidade
  do banco força ajuste pra **2-10%**. **Lesson learned:**
  pré-registros baseados em "múltiplos pares possíveis" devem
  considerar redução pelo hard família — vira Decisão 1 da
  Sessão 7b.
- **3.3 41.80% valida Caminho 5 empiricamente:** trade-off aceito
  (par regular+Dos Steps perde hard de família) está funcionando.

### 4 decisões de processo registradas no fechamento (Seção 8.14.4)

1. **Tabela de pares mensuráveis pré-registro = protocolo
   permanente** pra cenários soft (3.1, 4.1, 4.2 e em diante).
2. **Métrica primária correta pro 2.4 quando C executar** = **%
   rotinas onde os 2 unis aparecem PAREADOS no MESMO bloco**
   (anti_uni atua em pareamento, não em seleção). Adicionar como
   secundária em 7c agora; elevar a primária quando C executar.
3. **R-1 dos cenários 4.x = rotina realista Variante B 2x** (setup
   do 6.2). R-1 fixa entre iters. Vantagem: alinha calibração com
   uso real (vs R-1 sintética).
4. **G8 cadastro respeita refator CORE Sessão 2:** subregiões
   `core_dinamico`/`core_isometrico` (NÃO `core` — bug retrocompat
   registrado). Padrões refinados (`flexao_tronco`/etc) ficam pra
   Etapa 7.

### Pré-registro 2.1 levantado (limitação detectada)

Banco atual tem só 1 Supino Inclinado (Smith) → 3ª faixa "2
Inclinados" não mensurável. **Decisão pendente pro user:** adicionar
`Supino Inclinado Halteres` como mock_futuro G1 (sim — confirmado
em Sessão 7c).

### Atualizações em arquivos

- `tools/mocks/dimensoes_etapa_6.yaml` — G4 cadastrado (51 mocks)
- `tools/calibrar_pesos_dimensoes.py` — 2.3 (costas(5)) + 2.4 + 3.2 + 3.3
- `dimensoes_proximidade.md` Seções 8.14.3 + 8.14.4

### Pontos abertos pra Sessão 7c

- Mocks G8 (core refinado — 25 ex).
- Supino Inclinado Halteres mock_futuro G1.
- Cenários 2.1 (peito 2x2 ranking), 3.1 (Variante B 3x A1/A2),
  4.1 (HIST toggle ON), 4.2 (HIST toggle OFF).
- Métrica secundária pareamento pro 2.4.

---

## Sessão 7c (2026-05-09) — E.1.b2 G8 + 4 cenários + diretriz equipamento_grupo null em core

### Contexto

Terceira sub-sessão E.1.b2. Escopo G8 (core refinado — 20 cadastrados
+ 5 mock_futuros = 25 ex) + Supino Inclinado Halteres mock_futuro G1
+ 4 cenários novos (2.1, 3.1, 4.1, 4.2) + métrica secundária
pareamento pro 2.4. Sessão fecha **E.1.b2 oficialmente** + Etapa 6
inteira.

### Decisões grandes

- **Supino Inclinado Halteres mock_futuro G1** cadastrado.
  Confirmação user: vai pro XLSX real na Fase 4 junto com outros
  mock_futuros.
- **G8 cadastrado** — 25 ex (6 prancha frontal + 1 prancha lateral +
  4 INFRA + outros). YAML chegou em 78 mocks, 11 mock_futuros.
- **Decisões clínicas (6 critérios A→F):**
  - **A:** reclassificação 7 pranchas confirmada (`prancha frontal`
    + `prancha lateral`).
  - **B:** equipamento em superfícies não-padrão = `null` (Bola,
    Feijão, Slide, Ab Wheel, Banco). **Anilha ajustada** de halter
    pra null (uso clínico Dead Bug C/ Anilha = anilha solo nas
    mãos, similar supino fechado mas mais fácil setup).
  - **C:** Prancha Renegade equipamento = `corporal` (proposta 1
    — variante leve sem halter).
  - **D:** INFRAs (Alternado uni+2/2; Suspenso bi+4/3; Chão bi+2/2;
    Roll-Up bi+3/3).
  - **E:** Russian Twist bi+3/3+halteres (eq_primario).
  - **F:** `variante_pontual=false` em todos 25.
- **4 cenários novos + secundária 2.4:**
  - **2.1** (2 treinos × peito(2)): **0.00%** (pre-Etapa 7 hard
    INTER família; sub-Reto 0%, sub-Inclinado 0%).
  - **3.1** (Variante B 3x A1/A2): **0.00%** (família hard INTER).
  - **4.1** (HIST toggle ON, R-1 Variante B fixa): **100.00%** FAIL
    baseline (esperado pre-Etapa 7 — HIST não implementado).
  - **4.2** (HIST toggle OFF): **100.00%** informativo.
  - **2.4 sub-pareamento:** **94.90%** — INSIGHT pra C: anti_uni
    -75 atual reduz pareamento de ~100% pra 94.9% (apenas 5pp
    redução). Calibração C deve considerar peso mais agressivo
    pra lateralidade Médio em squats.

### Diretriz nova (correção retroativa pós-cadastro)

User trouxe correção clínica importante após cadastro G8 inicial:
**equipamento_grupo = `null` por padrão em todo G8 (core)**.

**Razão clínica:**

- equipamento_grupo é tiebreaker Baixo (-5) com semântica "desempata
  pares iguais em outras dims biomecânicas".
- **Em peito/costas equipamento carrega info biomecânica real**
  (halter livre vs Smith vs barra em supinos = estabilização
  independente, ângulo, ROM diferentes; polia vs halter em costas
  = vetor de resistência diferente).
- **Em core, equipamento é só fonte de carga arbitrária** (Russian
  Twist com halter, Pallof Press com polia, INFRA Suspenso com
  barra fixa: nenhum desses tem distinção biomecânica que
  justifique o tiebreaker disparar). Logisticamente também não há
  fricção real (vários halteres/polias na sala).

**Aplicação retroativa:** 17 G8 com equipamento_grupo não-null
ajustados pra `null`. Cadastro final: TODOS 25 com null.

**Diretriz registrada na Seção 7.2 (item 9-bis) do
`dimensoes_proximidade.md`:** "equipamento_grupo em core é null por
padrão; preencher só com justificativa clínica explícita".

### Surpresas / desvios

- **Diretriz "null em core" emergiu durante implementação 7c**
  (não estava na spec original). Insight clínico do user que
  esclarece tiebreaker em escopo cross-grupo. Aplicação retroativa
  + registro na Seção 7.2 evitam que mesmo padrão se repita em
  cadastros futuros.
- **2.1 + 3.1 = 0% pre-Etapa 7** confirma família hard INTER
  bloqueando coexistência. Pos-Etapa 7 (D3.2 Caminho C — soft INTER
  alto) esperar <15% cada faixa.
- **4.2 predicate ajustado** mid-sessão (`pct < 100.0` →
  `pct >= 0.0`) porque cenário "informativo aceita repetição"
  deveria sempre OK.

### Fechamento oficial Etapa 6

Status final harness pós-Sessão 7c (16 cenários):

| ID | Status | Observado |
|---|---|---|
| 1.1 | ✅ OK | 0.00% |
| 1.2 | ✅ OK | 0.00% |
| 1.3 | ⚠️ FAIL baseline | 3.80% |
| 2.1 | ✅ OK | 0.00% |
| 2.2A | ⚠️ FAIL baseline | 4.30% |
| 2.2B | ✅ OK gate | 0.00% |
| 2.3 | ✅ OK | 5.20% (costas(5)) |
| 2.4 | ✅ OK | 100% / sub-pareamento 94.9% |
| 3.1 | ✅ OK | 0.00% |
| 3.2 | ✅ OK | 0.00% |
| 3.3 | ✅ OK | 41.80% |
| 4.1 | ⚠️ FAIL baseline | 100.00% |
| 4.2 | ✅ OK informativo | 100.00% |
| 5.2 | ✅ OK | 17.20% violações |
| 6.1 | ✅ OK | 0.00% (sec. 100% E3) |
| 6.2 | ✅ OK | 0.00% (sub-a 0.20% / sub-b 2.80%) |

**3 FAIL baseline pré-Etapa 7 esperados** (1.3, 2.2A, 4.1) — todos
viram OK quando 7.2 + 7.4 implementarem predicado e HISTÓRICO
toggle.

### Plano Etapa 7 consolidado pré-Sessão 8

Sessão 7c registrou plano em **6 fases** com decisões fechadas
pré-Sessão 8 (não reabrir sem motivo forte):

- **Branch novo** `etapa-7` a partir de `refator-gerador`.
- **Granularidade 7.1:** módulo completo (não incremental). Ressalva:
  parar e perguntar se ambiguidade na Seção 8.10/B aparecer.
- **Ordem A:** 7.2 (predicado hard) → 7.3 (soft INTRA) → 7.4 (INTER +
  HISTÓRICO + migração família).

Plano detalhado em **Seção 8.15** do `dimensoes_proximidade.md`
(8.15.1 plano + 8.15.2 pré-condições + 8.15.3 baseline harness +
8.15.4 pendências).

### Atualizações em arquivos

- `tools/mocks/dimensoes_etapa_6.yaml` — G8 cadastrado (78 mocks,
  11 mock_futuros) + diretriz "null em core" aplicada
- `tools/calibrar_pesos_dimensoes.py` — 2.1 + 3.1 + 4.1 + 4.2 +
  secundária 2.4
- `dimensoes_proximidade.md` Seções 7.2 (item 9-bis) + 8.14.5 + 8.15
- `CLAUDE.md` Seção "Etapa 7 — plano e decisões fechadas"
- `guia_refatoracao_v4.md` header + plano Etapa 7 reescritos
- `memory/project_etapa_6.md` virou referência histórica
- `memory/project_etapa_7.md` criada (plano + pré-condições)
- `memory/MEMORY.md` substituiu entrada Etapa 6 por 2 entradas
- **`logs/etapa_6.md` (este documento) atualizado cobrindo
  Sessões 3-7c** + status "CONCLUÍDA"

### Etapa 6 oficialmente concluída em 2026-05-09

Próxima: Etapa 7 — implementação estrutural no `gerador_treino.py`.
Sessão 8 arranca da Fase 7.1 (módulo `pesos_proximidade.py`
completo).

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
