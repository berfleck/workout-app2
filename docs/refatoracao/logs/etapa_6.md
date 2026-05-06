# Etapa 6 — Trabalho preparatório das tags multi-dimensionais

**Status:** parcial — Fase 1 completa **+ correções pós-auditoria
aplicadas (2026-05-05)**. Fase 2 em grande parte resolvida; Fases 3-4
pendentes próxima sessão.

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
