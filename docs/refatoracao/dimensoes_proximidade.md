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

### 1.4 Família estrita — hard INTRA + soft INTER alto

**Decisão revisada na Sessão 2 (2026-05-06).** Versão original
(Sessão 1) registrava `familia_estrita` como hard filter em INTRA e
INTER. Auditoria identificou inconsistência conceitual: a Etapa 6
refinou famílias para granularidade fina (Supino → Reto + Inclinado;
Prancha → frontal + lateral; criação de `subida_elevada` no G4) sem
recalibrar o mecanismo de proteção. Hard duplo era apropriado pra
famílias "categoria muscular ampla" antigas, não pra famílias
refinadas onde os membros são variações próximas mas distintas.

**Definição corrigida:**

- **INTRA: hard filter.** Mesmo treino com 2 membros da mesma família
  refinada continua redundante (Step Up + Passada Dos Steps; 2 supinos
  retos). Hard é proteção limpa que evita depender só do score.
- **INTER: soft com peso alto.** Famílias refinadas justificam
  variabilidade entre treinos da mesma rotina — Step Up segunda +
  Recuo do Estepe sexta é aceitável; 2 supinos retos em treinos
  diferentes é tolerável quando histórico/banco apertam. Score alto
  desencoraja, banco apertado permite.
- **HISTÓRICO: toggle ON/OFF** (peso integral quando ON, zero quando
  OFF). Mecânica diferente — janela R-1 only, sem decaimento.

**Calibração de pesos (categórica — escala numérica final na Etapa 7):**

| Contexto | Peso | Comportamento |
|---|---|---|
| INTRA | Crítico (hard) | Bloqueia diretamente |
| INTER | **Alto (soft)** | ~80% do peso INTRA quando convertido pra escala numérica; gerador prefere variar entre famílias antes de repetir |
| HISTÓRICO (R-1) | Crítico (toggle) | Quando toggle ON, peso integral; quando OFF, zero |

**Alinhamento com guia v4 original:** o guia v4 (Etapa 6, linhas
817-820) propunha pesos numéricos `100 INTRA / 80 INTER / 60
HISTÓRICO`. A Sessão 1 desviou para hard duplo INTRA+INTER sem
justificativa registrada. A redefinição da Sessão 2 retorna ao
espírito original (peso alto soft INTER, não hard binário).

**Implicação na sub-pendência "2 retos + 1 inclinado em 3 treinos"
(registrada na Sessão 1 pós-auditoria):** ✅ **RESOLVIDA.** Cenário
P5(c) do G1 (rotina 3-treinos com 2 retos + 1 inclinado) deixa de
estar bloqueado pelo hard INTER — soft INTER alto desencoraja mas
permite quando outras alternativas se esgotam.

**Implicação no toggle `relaxar_familia` do app (já implementado):**
semântica fica ambígua na nova realidade (INTER já é soft por padrão).
Decisão sobre destino do toggle fica pra Etapa 7 — possíveis caminhos:
(i) toggle desaparece (soft INTER cobre o caso de banco apertado por
si só), (ii) toggle vira ignorar penalty INTER, (iii) toggle vira
slider de peso INTER. Decidir pós-simulação.

**Diretriz para curadoria de famílias estritas (Fase 2/Etapa 7):**

- Famílias devem refletir **variações biomecânicas estritas ou próximas**
  do mesmo exercício (Slide ≈ Feijão; Step Up ≈ Passada Dos Steps —
  ambos com apoio elevado), não categoria muscular ampla (não fazer
  todos os tríceps com `variacao_de = "Tríceps"`).
- **Lateralidade NÃO faz parte da família estrita** — é dimensão
  separada. Famílias gêmeas bi/uni unificam (ex: `stiff` + `stiff uni`
  viram `stiff` único; `Recuo` + `Recuo Alternado` já estão unificados).
- Famílias podem ser refinadas para distinguir mecânicas
  significativamente diferentes (ex: separar `prancha frontal` de
  `prancha lateral` — anti-extensão vs anti-lateroflexão; criação de
  `subida_elevada` no G4 — apoio elevado vs solo).
- Soft INTER alto absorve a "fricção" do refinamento — variação dentro
  da família refinada entre treinos é aceitável quando o banco aperta.

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

### 1.7 Filtros hard INTRA — predicado central (decisão D1, Sessão 4)

**Decisão de D1, Sessão 4 (2026-05-08):** todos os filtros hard de
proximidade INTRA da Etapa 6 são centralizados em um predicado único
`_compativel_intra(cand, alocados, dims)` chamado em `pre_alocar_rotina`
antes de adicionar candidato a um treino. Substitui o atual check
`variacao_pais_intra` por uma chamada que cobre as 3 regras hard.

**Justificativa arquitetural:**

- **Separação semântica** entre proximidade (predicado) e recursos
  físicos (`pode_adicionar_ao_bloco` continua focado em
  carga/fadiga/equipamento bloqueado/complexidade).
- **Lugar único pra ler/auditar** — um predicado por regra, fácil
  estender quando aparecer próximo hard.
- **Backward compat** — soft -75 do `anti_uni_mesmo_grupo` (Etapa 5)
  continua operando em `_score_pareamento` sem mudança.

**3 regras hard INTRA na Etapa 6:**

| Regra | Disparo | Origem |
|---|---|---|
| **Família refinada same-treino** | `cand.variacao_de == outro.variacao_de` (ambas não-vazias) | Seção 1.4 — hard INTRA |
| **`variante_pontual` cross-family same-subregião** | `cand.variante_pontual AND outro.variante_pontual AND cand.subregiao == outro.subregiao AND cand.variacao_de != outro.variacao_de` | Seção 2 G1 + decisão D1.c |
| **Lateralidade contextual (costas)** | `cand.unilateral == "unilateral" AND outro.unilateral == "unilateral" AND cand.subregiao == outro.subregiao AND cand.subregiao in SUBREGIOES_LATERALIDADE_HARD` | Seção 2 G2 + decisão D1.d |

**Constante de configuração inicial (Etapa 7 — implementação):**

```python
SUBREGIOES_LATERALIDADE_HARD = frozenset({"costas"})  # G2 — único Crítico hard
```

Outras subregiões (peito, ombro, perna_anterior, perna_posterior,
adutores, panturrilha, core, braços) continuam com lateralidade soft
via `anti_uni_mesmo_grupo` da Etapa 5 (peso por grupo calibrável em
D2). Promover novas subregiões a hard = adicionar ao frozenset.

**Soft penalties INTRA da Etapa 6** (pegada, plano_corporal,
equipamento_grupo, lateralidade Médio em outras subregiões) NÃO
entram no predicado — vivem em `_score_pareamento` aditivamente,
calibração via D2.

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

**Calibração inicial (Sessão 2 — pegada fixada como Médio + tag `variante_pontual` nova):**

| Dimensão | INTRA | INTER | HISTÓRICO (R-1) |
|---|---|---|---|
| `familia_estrita` | Crítico (hard) | **Alto (soft)** | Crítico (toggle) |
| `plano_corporal` (reto/inclinado) | **Alto** | **Médio-alto** (3 retos = Ruim) | Médio |
| `equipamento_grupo` | **Baixo (tiebreaker)** | Baixo | Baixo |
| `pegada` | Médio | Médio | Médio |
| `lateralidade` | Médio (anti_uni — ocioso hoje, todos bi) | Baixo | 0 |
| **`variante_pontual`** (Supino Fechado, Apoio Fechado — futuros) | **Crítico (hard)** | **Soft Crítico** (~95% bloqueio efetivo, mesma subregião) | Médio |

> **Pegada fixada em "Médio" em todos os contextos** (Sessão 2 —
> 2026-05-06): vetor primário em supinos é ângulo (`plano_corporal`
> reto/inclinado), não pegada. Pegada vira fator desempate adicional.
> Calibração final na Etapa 7 via simulação.

> **Tag `variante_pontual`** nova (Sessão 2): boolean cobrindo "uso
> pontual cross-family" — Supino Fechado + Apoio Fechado têm famílias
> diferentes (`Supino Reto` vs `Apoio`) mas compartilham caráter
> "pontual" e raramente devem coexistir na rotina. Tag opera dentro
> da subregião (peito por enquanto). Detalhes em Seção 3 e Anexo
> item 15-septies.

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
| `familia_estrita` | Crítico (hard) | **Alto (soft)** | Crítico (toggle) |
| `lateralidade` | **Crítico (hard contextual — costas)** | **Baixo (regra fraca)** | 0 |
| `pegada` | Alto | Alto | Médio |
| `plano_corporal` | Médio | Médio-alto (3 iguais = Ruim) | Baixo |
| `equipamento_grupo` | Médio | Baixo | Baixo |

**Decisões clínicas registradas:**

- **Hierarquia INTRA:** Lateralidade (crítico hard) > Pegada (alto) >
  Plano corporal ≈ Equipamento (médios).
- **Lateralidade INTRA é hard contextual** (decidido em D1.d, Sessão 4
  — 2026-05-08): subregião `costas` entra em
  `SUBREGIOES_LATERALIDADE_HARD` no predicado central
  `_compativel_intra` (Seção 1.7). Regra: "max 1 unilateral por treino
  dentro de costas". Outras subregiões (squats, hinges, tríceps, core)
  permanecem soft via `anti_uni_mesmo_grupo` da Etapa 5 (peso por
  grupo calibrável em D2).
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
| `familia_estrita` | Crítico (hard) | **Alto (soft)** | Crítico (toggle) |
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

### Grupo 4 — Agachamentos (17 atuais + Recuo do Estepe futuro = 18 exercícios)

> **Refinamento de família aplicado na Sessão 2 (2026-05-06).** Caminho 5
> aprovado: criação de família estrita nova **`subida_elevada`** que
> agrupa Step Up + Step Up Alt + Passada Dos Steps + Recuo do Estepe
> (cadastro futuro). Resolve **estruturalmente o Caso 2**
> ("Step Up + Passada Dos Steps INTRA") via modelagem ativa de proximidade
> biomecânica, sem refinar padrão nem dual-weight em equipamento.

**Exercícios:** Agachamento Livre, Goblet, Smith, Leg Press, Cadeira
Extensora, Box Jump (6 bilaterais); Búlgaro, Passada, Passada Dos
Steps, Recuo, Recuo Alternado, Recuo C/ Barra, Step Up, Step Up Alt.,
Walking Lunges, Agach. Lateral, Slide Board Lateral (11 unilaterais)
+ Recuo do Estepe (cadastro novo, item 26 do Anexo).

**Tags por exercício (após refinamento de família):**

| Dimensão | Aplica | Notas |
|---|---|---|
| `familia_estrita` | ✓ | `Agachamento` (bi: Livre/Goblet/Smith), `passada` (só Passada normal — Passada Dos Steps movida pra subida_elevada), `Recuo` (regular/Alternado/C Barra), **`subida_elevada`** (Step Up + Step Up Alt + Passada Dos Steps + Recuo do Estepe), `walking lunges`, `agach. lateral` (regular + Slide Board), sem família (Box Jump, Cadeira, Búlgaro, Leg Press) |
| `equipamento_grupo` | ✓ | barra, barra_guiada, halter, maquina, caixa, vazio (Box Jump, Slide Board) |
| `lateralidade` | ✓ | já é padrão refinado (`squat_bilateral` / `squat_unilateral`); peso INTRA = MÉDIO |
| `pegada` | ❌ | não cabe em squats |
| `plano_corporal` | ❌ | lateralidade + família já cobrem |

**Calibração inicial (revisada Sessão 2 — INTER soft):**

| Dimensão | INTRA | INTER | HISTÓRICO (R-1) |
|---|---|---|---|
| `familia_estrita` | Crítico (hard) | **Alto (soft)** | Crítico (toggle) |
| `lateralidade` | **Médio** (não crítico — bi+uni complementares) | Baixo (regra fraca diversificar) | 0 |
| `equipamento_grupo` | Médio | Baixo | Baixo |

**Decisões clínicas registradas:**

- **Bilateral + unilateral são complementares** em squats (combinação
  recomendada em treinos de perna). Diferente de remadas. Lateralidade
  INTRA = médio, não crítico.
- **Step Up + Passada Dos Steps + Recuo do Estepe = subgrupo "ainda
  mais parecido"** dentro dos unilaterais (Sessão 2). Mecânica comum:
  pé em apoio elevado, ROM de quadril ampliado, demanda de equilíbrio
  pela superfície. **Justifica família estrita própria
  `subida_elevada`** — captura "variação biomecânica próxima",
  consistente com Seção 1.4 (famílias devem refletir variações
  biomecânicas, não nome semântico).
- **Caminho 5 escolhido sobre alternativas:**
  - Caminho 1 (dual-weight em equipamento_grupo): rejeitado — complica
    calibração e compromete validação cross-grupo dos 12 cenários
  - Caminho 4 (split padrão `squat_unilateral` em step/chão): rejeitado
    — adiciona padrão novo, mexe em UI/configs/templates, retrocompat
    ruim
  - Caminho 5 (família `subida_elevada`): escolhido — mecânica
    biomecânica explícita; padrão e equipamento intactos; menor
    mudança de banco (1 valor novo + 4 reclassificações)
- **Reclassificação de família estrita decidida (Sessão 2):**
  - Step Up: `Step up` → `subida_elevada`
  - Step Up Alt.: `Step up` → `subida_elevada`
  - Passada Dos Steps: `passada` → `subida_elevada`
  - Recuo do Estepe (cadastro futuro): `subida_elevada` desde já
- **Trade-off aceito:** par "Passada (regular) + Passada Dos Steps"
  perde hard de família (saem de famílias diferentes agora). Anti_uni
  -75 INTRA continua penalizando o par. Clinicamente é correção, não
  regressão — Passada normal e Passada Dos Steps são biomecanicamente
  diferentes (presença da caixa muda mecânica fundamental).
- **Box Jump é caso especial de timing, não proximidade** — "explosivo
  exige musculatura fresca" é regra de sequenciamento, não modelada
  via tags. Box Jump fica em `squat_bilateral` SEM família — apesar
  de usar caixa, o uso clínico é diferente dos 4 unilaterais de
  `subida_elevada`. Decisão sobre remover do banco fica pendente
  separadamente (item 33 do Anexo 4.3).
- **Sub-distinção uni-estático vs uni-deslocamento** (Búlgaro+Passada =
  Ruim; Búlgaro+Walking Lunges = "menos pior") **NÃO é modelada** —
  aceito como dívida. Sistema atual (`anti_uni_mesmo_grupo`) trata
  ambos como Ruim, sem capturar a nuance "menos pior".
- **Posição_carga não modelada** — já capturada pelo filtro de cargas
  (Etapa 4).

**Validação cruzada Caminho 5 + redefinição familia_estrita:**

| Cenário | Mecanismo de proteção | Resultado |
|---|---|---|
| Step Up + Passada Dos Steps INTRA | hard família `subida_elevada` | bloqueado ✓ |
| Step Up + Step Up Alt INTRA | hard família | bloqueado ✓ |
| Step Up T1 + Recuo do Estepe T2 | soft INTER alto família | desincentivado; permite quando banco aperta ✓ |
| Step Up + Búlgaro INTRA | famílias dif, mesmo padrão, anti_uni -75 | comportamento atual ✓ |
| Passada (reg) + Passada Dos Steps INTRA | famílias dif, mesmo padrão, anti_uni -75 | mudança de comportamento (era hard); correção clínica ✓ |
| Passada (reg) T1 + Passada Dos Steps T2 | famílias dif → soft INTER não aplica | OK pelo modelo; correção clínica ✓ |
| Box Jump + Step Up INTRA | famílias dif (Box Jump sem), padrões dif (bi vs uni), padrao_diff +100 | comportamento atual ✓ |

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
| `familia_estrita` | Crítico (hard) | **Alto (soft)** | Crítico (toggle) |
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
| `familia_estrita` | Crítico (hard, resolve Slide+Feijão) | **Alto (soft)** | Crítico (toggle) |
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
| `familia_estrita` | Crítico (hard) | **Alto (soft)** | Crítico (toggle) |
| `equipamento_grupo` | Médio | Baixo | Baixo |
| `lateralidade` | Médio (anti_uni) | Baixo | 0 |

**Decisão estrutural:**

- **`musculo_alvo_especifico` (cabeça do tríceps) NÃO entra como
  dimensão.** Famílias estritas resolvem o problema. Uma das 5
  dimensões propostas pelo guia v4 (linha 810-811) é **descartada
  nesta etapa**. Boa simplificação — libera orçamento.

---

### Grupo 8 — Core (20 atuais + 5 cadastros novos = 25 exercícios)

> **Refator estrutural aplicado na Sessão 2 (2026-05-06).** Estrutura
> antiga (1 subregião `core` + 2 padrões `core_isometrico`/`core_dinamico`)
> substituída por hierarquia mais expressiva. Resolve **estruturalmente
> o Caso 1** ("Pranchas Frontal+Lateral INTRA") via modelagem ativa —
> sem dimensão nova.

**Promoção subregião:** `core` → **`core_isometrico` + `core_dinamico`**
(promovidos de padrão).

**4 padrões refinados** atravessando as 2 subregiões (iso = anti-X,
dyn = X):

| Padrão | iso (anti-X) | dyn (X) |
|---|---|---|
| `flexao_tronco` | anti-flexão (Pranchas, Hollow, Roda) | flexão (Crunch, Abd Bicicleta) |
| `flexao_lateral` | anti-lateroflexão (Prancha Lateral) | lateroflexão (futuro) |
| `rotacao_tronco` | anti-rotação (Pallof Press) | rotação (Russian Twist — cadastro novo) |
| `flexao_quadril` | controle estabilizatório (Dead Bug ×3) | flexão dinâmica (V-Up, Canoinha, INFRA ×4) |

**Mapeamento completo (25 exercícios — 20 atuais + Russian Twist + 4
INFRA novos):**

| Padrão / Subregião | core_isometrico | core_dinamico |
|---|---|---|
| `flexao_tronco` | Prancha (regular/Alternada/Bola/Feijão/Slide/Renegade), Hollow Hold, Roda Abdominal | Crunch (Chão/Bola/Cabo), Abd Bicicleta |
| `flexao_lateral` | Prancha Lateral | (vazio — futuro) |
| `rotacao_tronco` | Pallof Press | **Russian Twist** (cadastro novo) |
| `flexao_quadril` | Dead Bug, Dead Bug C/ Anilha, Dead Bug C/ Bola | V-Up, V-Up Unilateral, **Canoinha** (reclassificada), INFRA Alternado/Suspenso/Chão/Roll-Up (4 novos) |

**Reclassificações decididas:**

- **Canoinha:** padrão `core_dinamico` (antigo) → `flexao_quadril` dyn
  (pareia com V-Up/INFRA)
- **Roda Abdominal:** subregião `core_isometrico` mantida; padrão →
  `flexao_tronco` (componente concêntrico de flexão + excêntrico de
  anti-extensão; foco anti-extensão dominante)
- **Prancha Renegade:** padrão → `flexao_tronco` (família "prancha
  frontal" agrupa; componente anti-rotação reconhecido mas curadoria
  simplificada)
- **Abd Bicicleta:** padrão → `flexao_tronco` dyn (foco visual é
  crunch; rotação é tempero, não dominante)
- **V-Up / V-Up Uni:** padrão → `flexao_quadril` dyn (alinha com
  INFRAs; protege par "V-Up + INFRA Suspenso" de sair OK pelo modelo)
- **Lateralidades** (verificadas no banco, sem mudança):
  - Dead Bug regular: `unilateral` (alterna membros)
  - Dead Bug C/ Anilha: `bilateral` (movimentos simultâneos com peso)
  - Dead Bug C/ Bola: `unilateral` (alterna membros)
  - V-Up: `bilateral`; V-Up Uni: `unilateral`

**Tags de proximidade por exercício (após refator):**

| Dimensão | Aplica | Notas |
|---|---|---|
| `familia_estrita` | ✓ chave | `prancha frontal`, `prancha lateral`, `Dead bug`, `INFRA`, `crunch`, `v-up`, **`russian twist`** (novo); sem família (Hollow Hold, Pallof Press, Roda Abdominal, Canoinha) |
| `equipamento_grupo` | ✓ | corporal, bola, feijão, polia, ab_wheel, barra (Infra Suspenso), vazio (Slide, Russian Twist a definir) |
| `lateralidade` | ✓ | bi/uni; anti_uni vale |
| `pegada` | ❌ | — |
| `plano_corporal` | ❌ | NÃO modelar (decisão mantida) |
| `plano_estabilizacao` (anti-ext/lat/rot) | ❌ DESCARTADA | refator estrutural absorve via padrão |

**Calibração inicial (sem mudança):**

| Dimensão | INTRA | INTER | HISTÓRICO (R-1) |
|---|---|---|---|
| `familia_estrita` | Crítico (hard) | **Alto (soft)** | Crítico (toggle) |
| `equipamento_grupo` | Baixo (instabilidade conta mas não justifica granularidade) | Baixo | Baixo |
| `lateralidade` | Médio (anti_uni padrão) | Baixo | 0 |

**Resolução estrutural do Caso 1 (Prancha Frontal + Lateral INTRA):**

Após refator, Prancha Frontal e Prancha Lateral têm:

- **Famílias estritas separadas** (`prancha frontal` ≠ `prancha lateral`)
- **Padrões diferentes** (`flexao_tronco` ≠ `flexao_lateral`) — score
  `padrao_diff` da Etapa 5 desincentiva o par
- **Mesma subregião** (`core_isometrico`) — única dimensão coincidente

Resultado: par recebe penalidade no score (modelagem ativa) +
abundância de famílias dyn (Crunch, V-Up, INFRA, Russian Twist) faz
gerador preferir iso+dyn mix em `core(2)` via cycling natural da Etapa
3. **Caso 1 sai da seção "Decisões a re-validar".**

**Decisão sobre dimensão `tipo_core` (considerada e descartada):**

> Sessão 2 considerou adicionar dimensão narrow-scope `tipo_core`
> (iso/dyn) ao invés do refator estrutural. Descartada porque o refator
> de subregião+padrão **captura o mesmo efeito via mecanismos
> existentes** (Etapa 5 score `regiao_diff`/`padrao_diff` + Etapa 3
> demanda hierárquica) — sem custar dimensão nova. Set de 5 dimensões
> mantido.

---

## 3. Dimensões consolidadas

**Set final: 5 dimensões core + 1 narrow-scope booleana (Sessão 2 ampliada).**

**Dimensões core (5):**

| # | Dimensão | Tipo | Valores | Aceita vazio? |
|---|---|---|---|---|
| 1 | `familia_estrita` | hard INTRA + soft INTER alto | curado pelo personal (refinada por ângulo/mecânica onde necessário: Supino Reto vs Inclinado; subida_elevada agrupando exercícios em apoio elevado) | ✓ |
| 2 | `equipamento_grupo` | enum 8+vazio (tiebreaker) | barra, barra_guiada, halter, polia, corporal, maquina, caixa, banda_elastica | ✓ |
| 3 | `lateralidade` | enum 2 | bilateral, unilateral | ❌ (sempre uma das duas) |
| 4 | `pegada` | enum 4 + matriz custom 4×4 | aberta, neutra, pronada, supinada | ✓ (em squats, hinges, knee_flex, tríceps, pranchas) |
| 5 | `plano_corporal` | enum não-universal | varia por grupo: reto/inclinado (supinos), curvada/baixa/apoiada/etc (remadas), em_pe/deitado (hinges), pullover/vazio (puxadas), vazio (squats/knee_flex/tríceps/pranchas) | ✓ |

**Dimensão narrow-scope adicional (Sessão 2):**

| # | Dimensão | Tipo | Valores | Escopo |
|---|---|---|---|---|
| 6 | `variante_pontual` | boolean (default false) | true/false | Cross-family **dentro da mesma subregião**; `true` em exercícios de uso pontual que raramente devem coexistir na rotina (Supino Fechado, Apoio Fechado — peito); calibração inicial INTRA Alto / INTER Soft Crítico (~95% bloqueio) / HIST Médio. Generalizável: qualquer "uso pontual" cross-family futuro reusa a tag dentro do escopo da própria subregião. |

> **Filosofia de "narrow-scope":** budget de 5 dimensões (Sessão 1) é
> proxy contra inflação injustificada, não restrição absoluta. Tags
> narrow-scope com case clínico forte e cost baixo (data simples,
> escopo restrito) passam o critério custo-benefício. `variante_pontual`
> é o segundo precedente (após `pegada` e `plano_corporal` serem
> não-universais). Se aparecer outro caso similar no futuro, mesma
> análise se aplica.

> **Nota — absorção de `angulo_movimento`:** dimensão proposta
> originalmente no guia v4 como separada. Após validação, foi
> **absorvida em `plano_corporal`** com valores específicos por
> subregião. Em supinos, `plano_corporal = reto/inclinado` cobre o que
> `angulo_movimento` cobriria, sem custar uma dimensão extra.

> **Nota — `musculo_alvo_especifico` descartada:** dimensão proposta
> no guia v4 (cabeça do tríceps). User confirmou em G7 que famílias
> resolvem. Não entra no set.

> **Nota — `tipo_core` (iso/dyn) considerada e descartada:** Sessão 2
> propôs como narrow-scope; refator estrutural CORE absorve via
> mecanismos existentes (subregião + padrão refinados). Não entra no
> set.

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
| 14 | ~~Dead Bug C/ Anilha + Dead Bug C/ Bola → família INFRA~~ | **SUPERSEDIDO pelo item 15-quater** (refator estrutural CORE — Dead Bugs ficam em família `Dead bug` + padrão `flexao_quadril` em iso; INFRAs em família `INFRA` + padrão `flexao_quadril` em dyn). |
| 15 | Step Up + Step Up Alt + Passada Dos Steps | `equipamento_grupo = caixa` (caixa prevalece sobre halter pela regra de precedência semântica) |
| 15-bis | **Supino — refinar família por ângulo** | **`Supino` → `Supino Reto`** (Reto Barra/Halteres/Anilha) **+ `Supino Inclinado`** (Smith Inclinado e cadastros futuros). Caminho B aprovado pelo user. Justificativa: G1 P5 INTER pressupõe 3 supinos coexistindo (1 inclinado + 2 retos), incompatível com família única + hard INTER. |
| 15-ter | **Cadastrar `plano_corporal` em todos exercícios de peito** | Supinos (reto/inclinado), Crucifixos (reto/inclinado), Crossovers (reto/inclinado conforme cadastro), Apoios (vazio — não diferencia clinicamente). Substitui `angulo_movimento` proposto inicialmente. |
| 15-quater | **Refator estrutural CORE** (Sessão 2 — 2026-05-06) | Promove subregião e refina padrão. Mudanças: (i) **Subregião:** `core` → **`core_isometrico` + `core_dinamico`** (promovidos de padrão); (ii) **Padrão:** 2 antigos → **4 refinados** (`flexao_tronco`, `flexao_lateral`, `rotacao_tronco`, `flexao_quadril`) atravessando as 2 subregiões; (iii) **Reclassificações de padrão:** Canoinha (subregião dyn mantida; padrão → `flexao_quadril` dyn), Roda Abdominal (iso mantida; padrão → `flexao_tronco`), Prancha Renegade (`flexao_tronco`), Abd Bicicleta (`flexao_tronco` dyn), V-Up/V-Up Uni (`flexao_quadril` dyn). Afeta ~22 linhas no banco + atualização de `PADRAO_PARA_SUBREGIAO`/`SUBREGIAO_PARA_REGIAO` em `gerador_treino.py` + compat via `_PADROES_LEGADOS` (`core_isometrico`/`core_dinamico` legado expandem nos 4 novos padrões refinados conforme a subregião). UI não muda (subregião continua selecionável). **Resolve estruturalmente o Caso 1** (Prancha Frontal+Lateral INTRA). Detalhes na Seção 2 G8. |
| 15-quinquies | **Família estrita `subida_elevada` no G4** (Sessão 2 — 2026-05-06) | Caminho 5 aprovado para o Caso 2. Cria família estrita nova **`subida_elevada`** agrupando exercícios com mecânica de pé em apoio elevado + ROM hip ampliado. Reclassificações: Step Up (`Step up` → `subida_elevada`), Step Up Alt. (`Step up` → `subida_elevada`), Passada Dos Steps (`passada` → `subida_elevada`), Recuo do Estepe (cadastro futuro item 26 — entra com família `subida_elevada` desde já). Afeta 4 linhas no banco. Padrão `squat_unilateral` intacto. Equipamento_grupo intacto. Box Jump fica em `squat_bilateral` SEM família (uso clínico distinto — explosivo, não modelado por proximidade). **Resolve estruturalmente o Caso 2** (Step Up + Passada Dos Steps INTRA). Trade-off aceito: par "Passada (regular) + Passada Dos Steps" perde hard de família — anti_uni -75 INTRA continua penalizando; soft INTER alto desincentiva. Correção clínica, não regressão. Detalhes na Seção 2 G4. |
| 15-sexies | **Redefinição `familia_estrita` = hard INTRA + soft INTER alto** (Sessão 2 — 2026-05-06) | Sessão 1 registrou família como hard INTRA+INTER sem justificativa registrada, divergindo do guia v4 original (`100 INTRA / 80 INTER / 60 HISTÓRICO`). Refinamento posterior das famílias (Supino Reto/Inclinado, prancha frontal/lateral, subida_elevada, etc.) não recalibrou o mecanismo de proteção. **Redefinição uniforme:** INTRA hard (mesmo treino com 2 membros da mesma família refinada continua redundante); **INTER soft com peso ~80% do INTRA** (variação dentro de família refinada entre treinos é aceitável quando banco aperta). HISTÓRICO mantém toggle ON/OFF. Implica em código: (i) `_buscar_candidato`/`montar_blocos` precisam aplicar família como soft penalty no INTER (não filtro hard); (ii) toggle `relaxar_familia` atual (default ON) fica com semântica ambígua — decisão sobre destino fica pra Etapa 7 pós-simulação (caminhos: desaparecer, virar binário ignorar/respeitar penalty INTER, ou virar slider de peso). **Resolve sub-pendência "2 retos + 1 inclinado bloqueado pelo hard INTER"** (P5(c) do G1). Detalhes na Seção 1.4. |
| 15-septies | **Tag `variante_pontual`** (Sessão 2 — 2026-05-06) | Adicionar coluna `variante_pontual` (boolean, default `false`) ao XLSX. Marca `true` em: Supino Fechado (cadastro futuro), Apoio Fechado (cadastro futuro). Cobre uso pontual cross-family dentro da subregião peito (e generalizável a outras subregiões no futuro). Calibração inicial: INTRA Alto / INTER Soft Crítico (~95% bloqueio efetivo) / HIST Médio. Semântica clínica: max 1 exercício com `variante_pontual=true` por rotina dentro da subregião. Implementação Etapa 7: `carregar_banco` lê coluna; score INTRA/INTER aplica penalty alta quando ambos têm `variante_pontual=true` E mesma subregião. Dimensão #6 do set (narrow-scope, ver Seção 3). |
| 15-octies | **Coluna `ativo` no XLSX** (Sessão 2 — 2026-05-06) | Adicionar coluna boolean `ativo` (default `true`). `carregar_banco` filtra `ativo=true` antes de retornar exercícios. Permite "exercícios na geladeira" — cadastrados mas não em uso pelo gerador. Vantagens sobre remover linhas: histórico de rotinas antigas preserva referências; reativação trivial; uma linha por exercício (sem duplicação ao re-cadastrar). Aplicação imediata: **Box Jump → `ativo=false`** (item 33 do Anexo 4.3 resolvido — fica no banco mas inativo, não entra na geração). |

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
| 26 | Recuo do Estepe | Cadastro novo: `padrao=squat_unilateral`, `familia_estrita=subida_elevada` (item 15-quinquies), `equipamento_grupo=caixa`, `lateralidade=unilateral`. |
| 27 | Tríceps Francês Corda | Família `Tríceps Francês`, equipamento corda |
| 28 | Infra Alternado | Nova família INFRA |
| 29 | Infra Suspenso (na barra fixa) | Nova família INFRA |
| 30 | Infra Chão (bilateral) | Nova família INFRA |
| 31 | Infra Roll-Up | Nova família INFRA — flexão quadril + rolagem tronco |
| 32 | **Russian Twist** | Cadastro novo (Sessão 2): `subregiao=core_dinamico`, `padrao=rotacao_tronco`, `familia_estrita=russian twist`, `equipamento_grupo=(a definir — corporal/halter/medicine ball)`, `lateralidade=bilateral`. Wood Chop foi considerado e **NÃO será cadastrado**. |

### 4.3 Decisões pendentes pro user

| # | Item | Aguarda decisão |
|---|---|---|
| ~~33~~ | ~~Box Jump~~ | ✅ **RESOLVIDO (Sessão 2):** fica no banco com `ativo=false` (item 15-octies). |

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

**Caso 1 — Pranchas Frontal + Lateral INTRA (G8) — ✅ RESOLVIDO ESTRUTURALMENTE (Sessão 2 — 2026-05-06)**

> **Resolução:** refator estrutural CORE aplicado (item 15-quater do
> Anexo). `core` virou 2 subregiões + 4 padrões refinados. Prancha
> Frontal (`flexao_tronco`) e Prancha Lateral (`flexao_lateral`) agora
> têm padrões diferentes — `padrao_diff` da Etapa 5 desincentiva o
> par. Modelagem ativa, não regressão. Detalhes na Seção 2 G8.
>
> **Histórico (preservado para auditoria):** user pediu modelagem
> ativa ("precisamos de uma forma de evitar que o app junte 2
> pranchas"); Sessão 1 registrou como "abundância probabilística +
> personal edita" (regressão silenciosa). Sessão 2 reabriu e
> resolveu via refator estrutural. Os 3 caminhos discutidos
> originalmente (a/b/c — `categoria_core`, âncoras, dívida) foram
> SUPERSEDIDOS pelo refator (caminho não-listado, mais limpo que os 3).

**Caso 2 — Step Up + Passada Dos Steps INTRA (G4) — ✅ RESOLVIDO ESTRUTURALMENTE (Sessão 2 — 2026-05-06)**

> **Resolução:** Caminho 5 aprovado — criação de família estrita nova
> **`subida_elevada`** (item 15-quinquies do Anexo) que agrupa Step
> Up + Step Up Alt + Passada Dos Steps + Recuo do Estepe (cadastro
> futuro). Hard INTRA bloqueia o par. Detalhes na Seção 2 G4.
>
> **Histórico (preservado para auditoria):** Sessão 1 marcou Step Up +
> Passada Dos Steps como Ruim com justificativa clínica explícita; com
> equipamento_grupo virando tiebreaker BAIXO INTRA, este par virou "OK
> pelo modelo" (regressão indireta). Sessão 2 reabriu e resolveu via
> família estrita biomecânica.
>
> **Caminhos discutidos e descartados em favor do Caminho 5:**
> - (1) Dual-weight em equipamento_grupo (BAIXO logístico / ALTO
>   específico) — complica calibração, compromete validação
>   cross-grupo dos 12 cenários
> - (2) `caixa` vira família estrita ou plano_corporal — mistura
>   conceitos
> - (3) Dívida pra Etapa 7 — anti-padrão escopo→rigor
> - (4) Split padrão `squat_unilateral` (step/chão) — mexe em UI/
>   configs/templates, retrocompat ruim, padrão_diff = 0 não resolve
>   o par crítico
> - **(5) Família estrita biomecânica `subida_elevada`** ✓ — escolhido

**Caso 3 — Sub-distinção uni-estático vs uni-deslocamento (G4)**

- User pediu inicialmente que (iii) Búlgaro+Passada fosse Ruim e (iv)
  Búlgaro+Walking Lunges fosse "menos pior".
- User explicitamente abriu mão depois: *"sub-distinção de
  unilaterais - não será necessário"*.
- **Status:** ✅ Não é regressão — user aceitou explicitamente como
  dívida com justificativa.

### Sub-pendência "2 retos + 1 inclinado bloqueado pelo hard INTER" — ✅ RESOLVIDA (Sessão 2 — 2026-05-06)

> **Resolução:** redefinição de `familia_estrita` como **hard INTRA +
> soft INTER alto** (Seção 1.4). Caminho (c) original confirmado e
> aplicado uniformemente a todas as famílias refinadas da Etapa 6.
>
> **Por que estava bloqueado:** Sessão 1 registrou `familia_estrita`
> como hard duplo (INTRA + INTER) sem justificativa registrada,
> divergindo do guia v4 original que propunha pesos numéricos
> `100 INTRA / 80 INTER / 60 HISTÓRICO`. Refinamento posterior das
> famílias (Supino Reto/Inclinado, prancha frontal/lateral, etc.) não
> recalibrou o mecanismo de proteção, deixando hard INTER excessivo
> para famílias que agora agrupam variações próximas mas distintas.
>
> **Como soft INTER resolve P5(c):** com Supino Reto agrupando 3
> equipamentos (Barra/Halteres/Anilha), rotina 3-treinos com 2 retos
> + 1 inclinado é desincentivada pelo soft (gerador prefere variar)
> mas permitida quando outras alternativas se esgotam. Comportamento
> alinhado com a aprovação do user em P5(c) ("OK").
>
> Detalhes na Seção 1.4 redefinida.

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

## 7. Regra de Cadastro Consolidada

> **Adicionada na Sessão 2 (2026-05-06).** Consolidação das diretrizes
> que emergiram ao longo da Etapa 6. Serve de referência ao cadastrar
> exercícios novos (na Etapa 7 e adiante) e ao avaliar refinamentos
> futuros do banco.

### 7.1 Família estrita (`familia_estrita`)

1. **Reflete variações biomecânicas estritas ou próximas** do mesmo
   exercício — não categoria muscular ampla. Ex: NÃO cadastrar todos
   os tríceps com `variacao_de = "Tríceps"`. Cada cabeça/movimento
   ganha família própria (Coice, Pushdown, Francês, Mergulho, Testa).
2. **Famílias gêmeas bi/uni unificam** — lateralidade é dimensão
   separada. Ex: `stiff` + `stiff uni` = `stiff` único; Recuo + Recuo
   Alternado já estão unificados.
3. **Refinamento por ângulo** quando ROM/cadeia muscular muda
   significativamente. Ex: Supino Reto vs Supino Inclinado.
4. **Refinamento por mecânica próxima** quando proximidade
   biomecânica é forte mesmo entre famílias atualmente diferentes.
   Ex: `subida_elevada` no G4 (Step Up + Step Up Alt + Passada Dos
   Steps + Recuo do Estepe — pé em apoio elevado, ROM hip ampliado).
5. **Opera hard INTRA + soft INTER alto** (Seção 1.4). Default
   uniforme em todas as famílias refinadas da Etapa 6.

### 7.2 Equipamento (`equipamento_grupo`)

6. **8 níveis nomeados + vazio:**
   `barra/barra_guiada/halter/polia/corporal/maquina/caixa/banda_elastica`.
7. **Precedência semântica** quando o exercício combina elementos —
   escolher o que mais define proximidade clínica. Ex: Step Up =
   `caixa` (não `halter`); Recuo do Estepe = `caixa` (não `halter`).
8. **Aceita vazio** quando nenhum equipamento aproxima de outros via
   essa dimensão. Ex: TRX, Box Jump, Slide Board.
9. **Peso BAIXO INTRA (tiebreaker)** — não inflar pra resolver casos
   clínicos. Quando aparecer caso onde equipamento parece "vetor
   primário", usar refinamento de família ou padrão (caso `caixa` →
   família `subida_elevada`, NÃO dual-weight em equipamento).

### 7.3 Pegada (`pegada`)

10. **4 valores enumerados:** `aberta`, `neutra`, `pronada`, `supinada`.
11. **Distância via matriz custom 4×4** (Seção 3.1) — não binária.
    Captura sub-estrutura: `aberta = pronada-wide`; `pronada =
    pronada-fechada`; `aberta ↔ pronada = 1`; `aberta ↔ supinada = 3`.
12. **Aceita vazio** em grupos onde não diferencia: squats, hinges,
    knee_flex, tríceps, pranchas. Em puxadas tem 3 valores efetivos
    (sem pronada-fechada).

### 7.4 Plano corporal (`plano_corporal`)

13. **Não-universal — valores variam por grupo:**
    - **Supinos:** `reto` / `inclinado` (absorve `angulo_movimento`)
    - **Remadas:** `curvada` / `baixa_sentada` / `apoiada` /
      `unilateral_apoiada` / `suspensao`
    - **Hinges (extensão de quadril):** `em_pe` / `deitado`
    - **Puxadas:** vazio (default) / `pullover`
    - **Squats / knee_flex / tríceps / pranchas / core:** vazio
14. **Aceita vazio** em grupos onde não diferencia.

### 7.5 Lateralidade (`lateralidade`)

15. **Cobertura universal** — sempre `bilateral` ou `unilateral`,
    nunca vazio.
16. **Não faz parte de família estrita** — é dimensão separada
    (regra simétrica à diretriz 2). Famílias gêmeas bi/uni unificam.
17. **Pesos por grupo** — Crítico em remadas (hard contextual via
    `SUBREGIOES_LATERALIDADE_HARD = {"costas"}`, decisão D1.d Sessão 4);
    Médio em squats/hinges; Médio (anti_uni padrão -75) em outros.
    Soft `anti_uni_mesmo_grupo` da Etapa 5 continua operando em todas
    as subregiões NÃO listadas como hard.

### 7.6 Estrutura subregião/padrão

18. **CORE refinado** (item 15-quater do Anexo): subregião
    `core_isometrico`/`core_dinamico` (de padrão); padrão
    `flexao_tronco`/`flexao_lateral`/`rotacao_tronco`/`flexao_quadril`
    (cross-subregião).
19. **Squats refinados** (Etapa 1): `squat_bilateral` /
    `squat_unilateral`.
20. **Antes de adicionar dimensão narrow-scope, considerar nessa
    ordem:**
    1. **Refator estrutural** reusando subregião/padrão (ex: refator
       CORE absorveu `tipo_core`)
    2. **Refinamento de família estrita** quando há proximidade
       biomecânica clara (ex: `subida_elevada`)
    3. **Recalibração de mecanismo existente** quando refinamento
       prévio criou friction (ex: redefinição
       `familia_estrita = hard INTRA + soft INTER`)
    4. **Adicionar dimensão narrow-scope** apenas se 1-3 não cobrem
       (ex: `variante_pontual` — uso pontual cross-family same-subregião)

### 7.7 Tag narrow-scope `variante_pontual`

21. **Boolean default `false`.** Marca `true` em exercícios com uso
    pontual cross-family dentro da subregião. Hoje: Supino Fechado,
    Apoio Fechado (cadastros futuros). Calibração (revisada D1.c
    Sessão 4): **INTRA Crítico (hard)** / INTER Soft Crítico (~95%
    bloqueio efetivo) / HIST Médio. Hard INTRA opera no predicado
    central `_compativel_intra` (Seção 1.7). Escopo: cross-family
    **dentro da mesma subregião**. Generalizável a outros "usos
    pontuais" futuros sem precisar refinar a tag.

### 7.8 Status `ativo`

22. **Coluna `ativo`** (boolean default `true`). Marca `false` em
    exercícios cadastrados mas não em uso pelo gerador (item 15-octies
    do Anexo). `carregar_banco` filtra `ativo=true`. Aplicação imediata:
    Box Jump.

### 7.9 Dimensões descartadas (NÃO cadastrar)

| Dimensão descartada | Motivo |
|---|---|
| `musculo_alvo_especifico` (cabeça do tríceps) | Famílias estritas refinadas resolvem |
| `posicao_carga` (axial/frontal/distal) | Filtro de cargas Etapa 4 já cobre |
| `padrao_execucao` | Lateralidade + família já cobrem |
| `plano_estabilizacao` (anti-ext/lat/rot) | Refator estrutural CORE absorve via padrão |
| `tipo_core` (iso/dyn) | Refator estrutural CORE absorve via subregião |

### 7.10 Checklist de cadastro pra exercício novo

Ao cadastrar um exercício novo no XLSX, preencher na ordem:

1. `nome` — único no banco
2. `subregiao` — qual das ~12 subregiões (peito, costas, ombro, etc.)
3. `padrao` — qual padrão dentro da subregião (com refinamentos da
   Etapa 6 onde aplicável: squat_bilateral/unilateral; flexao_tronco
   etc. em CORE)
4. `variacao_de` (= `familia_estrita`) — família refinada conforme
   diretrizes 1-5; pode ser vazio se exercício é "solo" (Hollow Hold,
   Pallof Press, Búlgaro, etc.)
5. `lateralidade` — bilateral ou unilateral (sempre preenchido)
6. `purpose` — compound / isolation / explosive / stability
7. `complexidade` (1-5) e `fadiga` (1-5)
8. `eq_primario` (texto livre) e `equipamento_grupo` (8 níveis +
   vazio, conforme diretrizes 6-9)
9. `pegada` — quando aplicável (diretrizes 10-12); vazio em
   squats/hinges/knee_flex/tríceps/pranchas
10. `plano_corporal` — quando aplicável (diretriz 13); vazio em
    grupos onde não diferencia
11. `variante_pontual` — boolean (default `false`); `true` em casos
    pontuais cross-family same-subregião
12. `ativo` — boolean (default `true`)
13. `musculo_primario`, `obs` — texto descritivo

**Validação cruzada antes de cadastrar:** percorrer diretrizes 1-22 e
confirmar que o cadastro proposto:

- Não cria família "categoria muscular ampla" (diretriz 1)
- Não duplica conceito já modelado (diretriz 20)
- Tem cobertura coerente com escopo das dimensões (Seção 1.5)
- Não viola decisões prévias (Seção 2 dos 8 grupos)

---

## 8. Fase 3 — calibração de pesos (em curso)

> **Adicionada na Sessão 3 (2026-05-07) e expandida na Sessão 4
> (2026-05-08).** Documenta progresso da Fase 3 (calibração numérica
> dos pesos categóricos das Seções 2-3-7) à medida que os blocos de
> decisão fecham.

### 8.1 Decomposição metodológica (Sessão 3)

Fase 3 dividida em blocos de decisão independentes, ordenados pra
permitir iteração empírica:

```
E.0 — Cenários-âncora (sem código, congelado em 13 cenários)
E.1.a — Harness pipeline com 1 cenário (validação esqueleto)
E.1.b parcial — 5-6 cenários sem dependência de D2/D3
D1 — Filtros hard: onde plugar (decisão estrutural)
D2 — Penalties soft INTRA: composição com bônus existentes
D3 — INTER soft + HISTÓRICO toggle: arquitetura
B — Estrutura de configuração de pesos (informada por D)
A — Escala numérica (informada por D)
C — Calibração fina iterativa (loop com harness)
E.1.b2 — Cenários soft pós-D2/D3
E.2 — Validação completa: 13 cenários + 8 problemas conhecidos
```

Ordem aprovada na Sessão 3: `E.0 → E.1.a → D1 → E.1.b parcial → D2 →
calibração harness INTRA → D3 → calibração harness INTER/HIST → B →
A → C → E.1.b2 → E.2`. Princípio: instrumentar antes de medir; decidir
estrutura sem componente numérico antes; calibrar empiricamente com
harness rodando.

### 8.2 E.0 — 13 cenários-âncora congelados (Sessão 3)

5 categorias + 1 sanity check. Lista resumida (especificação completa
em conversa de Sessão 3 — material pra harness):

| ID | Cenário | Categoria | Status |
|---|---|---|---|
| 1.1 | Família estrita hard INTRA | C1 — Hard INTRA | E.1.a ✅ (0/1000) |
| 1.2 | anti_uni retroativo Etapa 5 | C1 — Hard INTRA | E.1.b parcial |
| 1.3 | variante_pontual hard INTRA (pós-D1.c) | C1 — Hard INTRA | E.1.b parcial |
| 2.1 | Caso supino-inclinado-T1 (ranking ordinal) | C2 — Soft INTRA | E.1.b2 (D2) |
| 2.2 A | Lateralidade hard contextual costas (pós-D1.d) | C2 → C1 (promovido) | E.1.b parcial |
| 2.2 B | Lateralidade Médio em squats | C2 — Soft INTRA | E.1.b2 (D2) |
| 2.3 | Pegada+plano cumulando | C2 — Soft INTRA | E.1.b2 (D2) |
| 3.1 | 2 retos em rotina 3T (10-15%) | C3 — INTER soft | E.1.b2 (D3) |
| 3.2 | Step Up + Recuo do Estepe (<10%) | C3 — INTER soft | E.1.b2 (D3) |
| 3.3 | Passada + Passada Dos Steps (20-50%) | C3 — INTER soft | E.1.b2 (D3) |
| 4.1 | HISTÓRICO toggle ON (<3%) | C4 — HISTÓRICO | E.1.b2 (D3) |
| 4.2 | HISTÓRICO toggle OFF | C4 — HISTÓRICO | E.1.b2 (D3) |
| 5.1 | Escopo regiões dif não disparam | C5 — Escopo | E.1.b parcial |
| 5.2 | Retroativo v_up_uni Etapa 5 | C5 — Retroativo | E.1.b parcial |
| 6.1 | Happy path upper(3)+lower(3)+core(2)×2 | C6 — Sanity | E.1.b parcial |

5 exclusões deliberadas: refator CORE Prancha F+L (resolvido por
`padrao_diff` Etapa 5), Tríceps cabeças (musculo_alvo descartada G7),
Box Jump (filtragem `ativo=false`), `relaxar_familia` (decisão Etapa 7),
composição com filtro de cargas Etapa 4 (escopo separado).

### 8.3 E.1.a — Harness pipeline validado (Sessão 3)

**Arquivos:**

- `tools/calibrar_pesos_dimensoes.py` — harness de calibração (separado
  de `medir_entropia_pareamentos.py` da Etapa 5; mede coisa diferente:
  faixas clínicas vs entropia)
- `tools/mocks/dimensoes_etapa_6.yaml` — overlay in-memory das
  dimensões Etapa 6 (NÃO altera XLSX). Campo `origem` distingue
  `cadastrado` (overlay sobre Exercicio existente) vs `mock_futuro`
  (cria Exercicio in-memory pra cadastros futuros)
- CSV de auditoria: `seed_hash = SHA256[:8]("cenario_id|seed")`
  reproduzível — qualquer rodada falha pode ser re-executada

**Cenário 1.1 resultado:** 0/1000 violações. Valida que (i) overlay
de família funciona, (ii) hard pré-existente respeita família refinada
da Etapa 6.

**3 tracking items pra fechar antes de E.1.b2** (stub
`_penalty_proximidade` provisório):

1. Branches INTER + HISTÓRICO no stub (cenários 3.x, 4.x dependem)
2. Dimensões `lateralidade` + `variante_pontual` no stub (cenários
   1.2, 1.3, 2.2 dependem — lateralidade hard fica no predicado
   `_compativel_intra` decidido em D1.a)
3. Decisão final par-a-par vs set-based em D2 (provisório no stub:
   par-a-par cumulativa)

### 8.4 D1 — Filtros hard centralizados (Sessão 4 — 2026-05-08)

Decisão arquitetural composta de 4 sub-questões:

- **D1.a — Lugar arquitetural:** predicado único
  `_compativel_intra(cand, alocados, dims)` em `pre_alocar_rotina`
  centraliza hard de proximidade INTRA. `pode_adicionar_ao_bloco`
  continua focado em recursos físicos (carga/fadiga/equipamento/
  complexidade). Detalhes na Seção 1.7 nova.
- **D1.b — Família refinada:** continuidade — hard INTRA já existe
  via `variacao_pais_intra`; migra pra dentro do predicado quando
  Etapa 7 implementar. Sem mudança semântica.
- **D1.c — `variante_pontual` hard ou soft:** promover INTRA pra
  hard real (não soft Alto). Mantém INTER Soft Crítico. Justificativa:
  (i) simetria com família, (ii) semântica clínica `max 1 por rotina
  por subregião` é gate-shaped não gradiente, (iii) custo de
  implementação trivial dentro do predicado. Calibração G1 atualizada
  na Seção 2 e Seção 7.7.
- **D1.d — Lateralidade Crítico em remadas:** hard contextual via
  `SUBREGIOES_LATERALIDADE_HARD = frozenset({"costas"})`. Outras
  subregiões permanecem soft via `anti_uni_mesmo_grupo` da Etapa 5
  (peso por grupo calibrável em D2). Justificativa: G2 é o único
  Crítico; "NUNCA" clínico é gate; soft -75 universal continua sem
  regressão. Calibração G2 atualizada na Seção 2.

**Implicações em cenários da E.0:**

- Cenário 1.3 (variante_pontual): expectativa `<5%` → **0%** (hard real)
- Cenário 2.2 Setup A (lateralidade costas): expectativa `<5%` →
  **0%** (hard contextual). Promovido de C2 → C1 (categoria mudou
  de soft INTRA pra hard INTRA).
- Cenário 2.2 Setup B (lateralidade squats): inalterado, soft 25-35%.

**Implementação Etapa 7:** quando o predicado for criado, contar com:

```python
def _compativel_intra(cand, alocados, dims):
    cand_d = dims.get(cand.nome)
    for outro in alocados:
        outro_d = dims.get(outro.nome)
        # 1. Família refinada same-treino
        if (cand.variacao_de and
                cand.variacao_de == outro.variacao_de):
            return False
        # 2. variante_pontual cross-family same-subregião
        if (cand_d and outro_d and
                cand_d.variante_pontual and outro_d.variante_pontual and
                cand.subregiao == outro.subregiao and
                cand.variacao_de != outro.variacao_de):
            return False
        # 3. Lateralidade contextual (costas)
        if (cand.unilateral == "unilateral" and
                outro.unilateral == "unilateral" and
                cand.subregiao == outro.subregiao and
                cand.subregiao in SUBREGIOES_LATERALIDADE_HARD):
            return False
    return True
```

**D1 fechado.** Próximo: E.1.b parcial (5-6 cenários sem dependência
de D2/D3 + 2.2 Setup A promovido), depois D2 (composição soft INTRA).

### 8.5 E.1.b parcial — 5 cenários no harness (Sessão 5 — 2026-05-08)

Implementados em `tools/calibrar_pesos_dimensoes.py` + mocks em
`tools/mocks/dimensoes_etapa_6.yaml`. Resultados de 1000 iterações
cada:

| ID | Status | Observado | Notas |
|---|---|---|---|
| 1.1 | OK | 0.00% | Família refinada hard INTRA (Etapa 1+2) |
| 1.2 | OK | 0.00% | anti_uni soft -75 retroativo Etapa 5 (em braços, fora do hard contextual de costas) |
| **1.3** | **FAIL (baseline pre-Etapa 7)** | **5.00%** | variante_pontual hard INTRA — predicado não implementado ainda. Pós-Etapa 7 esperado: 0%. |
| **2.2A** | **FAIL (baseline pre-Etapa 7)** | **4.30%** | Lateralidade hard contextual costas — predicado não implementado ainda. Pós-Etapa 7 esperado: 0%. |
| 5.2 | OK | 17.20% violações = **82.80% pareados** | V-Up Uni + Tríceps Uni preferencialmente pareados (>50% target) |
| 6.1 | OK (primária) | **0.00% E6** | Calibração da Etapa 6 não over-penaliza; refator CORE da Sessão 2 sem fricção em `core(2)` |
| 6.1 sec | informativo | **100.00% E3** | Achado paralelo: `ancora_nao_cumprida` por vagas insuficientes em `upper(3)`. Não é problema de calibração — escopo Etapa 3. Caracterizar com configurações realistas de `configuracoes_comuns.md`. |

**Cenário 5.1 (escopo regiões dif não disparam soft) movido pra E.2**
— só vira testável quando penalties soft estiverem implementadas
(post-D2). Cenários soft INTRA (2.x), INTER (3.x) e HISTÓRICO (4.x)
ficam pra E.1.b2 pós-D2/D3.

**Refinamento do 6.1 (decidido na Sessão 5):** métrica primária
gateia status só com avisos da Etapa 6 (`incompleta`,
`familia_repetida`); `ancora_nao_cumprida` (escopo Etapa 3 — vagas
insuficientes pra obrigatórias) vira métrica secundária informativa.
Decomposição por região será ativada quando configurações realistas
de `configuracoes_comuns.md` substituírem o setup atual.

**1.3 e 2.2A baseline pre-Etapa 7 documentados** — quantificam o gap
que a implementação do predicado `_compativel_intra` (decidido em
D1.a) deve fechar. Pós-Etapa 7, esses cenários re-rodam e devem
flipar pra OK 0%.

### 8.6 Auditoria E.0 vs uso real (Sessão 6 — gate antes de D2 fechado)

Auditoria fechada em 2026-05-08 contra `configuracoes_comuns.md`.
Cada cenário marcado como ✓ (representativo), ⚠️ (patológico
necessário) ou ❓ (revisar). Produziu **4 redefinições** + **2 notas
de processo** + ações de implementação antes de D2.

**Resultado:**

| ID | Marcação | Ação |
|---|---|---|
| 1.1 | ⚠️ | Manter (gate test do hard de família — densidade necessária) |
| 1.2 | ⚠️ | Manter + gotcha calibração (Nota de processo #2) |
| 1.3 | ⚠️ | Manter (mesmo argumento de 1.1) |
| 2.1 | ⚠️ | Manter (densificação obrigatória pra ranking ordinal) + validar peso final em `peito(2)` antes de fechar D2 |
| 2.2A | ⚠️ | Manter + sub-métrica em 6.2 (gotcha) |
| 2.2B | ❓ → ✓ | **Redefinido: `perna_anterior(3) × 1 treino`** (Variante B 2x; mais informativo que `squat_unilateral(2)` artificial) |
| 2.3 | ⚠️ ou ✓ | **Timebox 15-30min: testar `costas(3) × 1 treino` realista. Se ≥5% rotinas com 2 ex pegada+plano colidindo, vira ✓; senão cai pra ⚠️ densificado.** |
| 3.1 | ⚠️ → ✓ | **Redefinido: rotina Variante B 3x com peito em A1 e A2** (era "rotina 3T toda de peito" caricatural; agora bate com `configuracoes_comuns.md` Seção 2.3) |
| 3.2 | ✓ | Manter |
| 3.3 | ✓ | Manter |
| 4.1 | ✓ | Manter (caminho principal — toggle ON evita repetir R-1) |
| 4.2 | ✓ | Manter (toggle OFF aceita repetição deliberada) |
| 5.1 | ✓ | Manter (sanity escopo cross-region; alta prioridade quando D2 fechar) |
| 5.2 | ✓ | Manter (retroativo Etapa 5 com travados) |
| 6.1 | ✓ | Manter (Variante A 2x — full body região) |
| **6.2** | **✓** | **Promovido: implementar antes de D2** (não só "antes de fechar Fase 3"). Cobre Variante B 2x subregião + vira proxy realista pros gotchas de 1.2 e 2.2A. |

**Distribuição final:** 8 ✓ representativo (com 6.2 promovido + 2.2B
e 3.1 redefinidos), 7 ⚠️ patológico necessário (1 com timebox a
resolver — 2.3), 0 ❓ pós-redefinições.

**Nota de processo #1 — densificação patológica ≠ anti-padrão escopo→rigor:**

Setups patológicos (`peito(3)` em 1.1/1.3/2.1, `bracos(4)` em 1.2,
`remadas(2)` em 2.2A) **não são regressão** do princípio "escopo, não
rigor" da Seção 1.1. São densidade artificial necessária pra forçar
coexistência rara virar mensurável em 1000 iters — sem isso, gates
hard e penalties soft simplesmente não disparam frequência detectável.

Distinção operacional:

- **Densificação patológica:** o **setup do cenário** é denso pra
  observar o mecanismo; a **calibração resultante** ainda é validada
  contra setups realistas via 6.1/6.2. Pesquisa empírica saudável.
- **Anti-padrão escopo→rigor (Seção 1.1):** o **mecanismo** é modelado
  fraco ("personal corrige depois"), independente de setup. Regressão
  silenciosa.

Como reconhecer cada caso:

- Se a expectativa numérica do cenário descreve **comportamento do
  gate** (ex: 0% pra hard, faixa pra soft) **e a calibração que cai
  dela é revalidada em setup realista**, é densificação. ✅
- Se a expectativa é "quase nunca importa, deixa acontecer" e nenhuma
  validação realista é feita, é regressão. ❌

Esta nota fica registrada porque qualquer revisão futura vai ler os
setups patológicos e questionar — corretamente, sem este registro.

**Nota de processo #2 — gotcha "calibrar denso, validar realista" (1.2 + 2.2A):**

Quando peso final do anti_uni soft -75 (Etapa 5) e do hard contextual
costas (D1.d) forem definidos / ajustados em D2:

1. Calibrar primeiro contra `bracos(4) × 1 treino` (1.2 patológico) e
   `remadas(2) × 1 treino` (2.2A patológico) pra ter densidade
   observável da violação.
2. **Antes de fechar D2**, validar peso resultante contra sub-métricas
   do 6.2 em setup realista:
   - **Sub-métrica a:** "% blocos com 2+ unilaterais de braço quando
     bíceps(1) e tríceps(1) coexistem em Variante B" → mede impacto
     do anti_uni em cenário onde 1 unilateral por treino é o normal.
   - **Sub-métrica b:** "% rotinas com 2+ unilaterais em `costas(3)`
     do treino T2 da Variante B" → mede hard contextual em uso real
     (vs `remadas(2)` denso).
3. Se peso calibrado em patológico over-corrige no realista (ex:
   vira 0% num setup que aceitaria 5-10% como tolerável), ajustar
   antes de fechar D2.

Mesma lógica vale pra 2.1 (validar peso `plano_corporal` em `peito(2)`
realista) e 2.2B (redefinido pra `perna_anterior(3)` realista direto;
não precisa proxy).

**Próximas ações antes de D2 fechar:**

1. **Implementar 6.2 no harness** (`tools/calibrar_pesos_dimensoes.py`)
   com métrica primária (avisos E6 — `incompleta`/`familia_repetida`)
   + sub-métricas a/b da Nota de processo #2 + decomposição por
   subregião.
2. **Timebox 2.3 (15-30min):** rodar harness exploratório `costas(3) ×
   1 treino` × 1000 iters; medir frequência de "2 ex com pegada+plano
   colidindo" no banco atual (peito + costas mockados). Se ≥5%, 2.3
   vira ✓ realista; senão cai pra ⚠️ densificado e seguimos.
3. **Aplicar redefinições no harness quando 2.2B e 3.1 forem
   adicionados em E.1.b2:**
   - 2.2B → `("subregiao", "perna_anterior", 3)`, métrica "2+
     unilaterais em perna_anterior"
   - 3.1 → rotina 3 treinos com `peito(2)` em T1 (=A1) e T3 (=A2)
     ciclando A-B-A; métrica INTER "2 retos em A1 e A2 cumulativo"
     (~10-15%)
4. Re-rodar 6.1 + 6.2 + (1.2 e 2.2A patológicos) lado-a-lado quando
   peso anti_uni / hard contextual for ajustado em D2.

**Caracterização do `ancora_nao_cumprida` (item #3 da Sessão 5):**
permanece pausada. Quando reaberta, usar configurações de 6.1 + 6.2
+ Variante B 3x A1/A2; descartar `upper(5)+lower(5)+core(2)` (fora
de escopo per `configuracoes_comuns.md` Seção 5).

### 8.7 D2 — composição soft INTRA — em curso

A ser documentado conforme decisões fecharem. Sub-questões abertas:
filtros hard (já resolvidos em D1, recap), penalty soft INTRA
composição com bônus existentes (`regiao_diff +1000`, `padrao_diff
+100`), decisão par-a-par vs set-based (provisório no stub: par-a-par
cumulativa). 3 tracking items do stub `_penalty_proximidade`
permanecem (Seção 8.5).

---

## Status do documento

- ✅ **Fase 1 — análise dos 8 grupos** — completa
- ✅ **Correções pós-Fase 1 (auditoria do user)** — aplicadas:
  - `angulo_movimento` re-introduzido (absorvido em `plano_corporal`)
  - Família `Supino` refinada (`Supino Reto` + `Supino Inclinado`)
  - `equipamento_grupo` esclarecido como tiebreaker (peso BAIXO INTRA)
  - Set de 5 dimensões congelado (Caminho B aprovado)
- ✅ **Fase 2 — completa** — Sessão 2 (2026-05-06):
  - ✅ **Caso 1 (Frontal+Lateral)** resolvido por refator estrutural
    CORE (subregião + 4 padrões refinados, item 15-quater do Anexo)
  - ✅ **Dimensão `tipo_core`** considerada e descartada (refator
    estrutural absorve via mecanismos existentes)
  - ✅ **Russian Twist** cadastrado; Wood Chop NÃO cadastrar
  - ✅ **Caso 2 (Step Up + Passada Dos Steps)** resolvido por família
    estrita biomecânica `subida_elevada` (Caminho 5; item 15-quinquies
    do Anexo)
  - ✅ **Redefinição `familia_estrita` = hard INTRA + soft INTER**
    aplicada uniformemente (item 15-sexies; resolve sub-pendência "2
    retos + 1 inclinado bloqueado pelo hard INTER")
  - ✅ **Tag `variante_pontual`** (#6 narrow-scope) — Supino Fechado +
    Apoio Fechado, hard cross-family efetivo INTER (item 15-septies)
  - ✅ **Coluna `ativo`** + Box Jump como `ativo=false` (item 15-octies;
    item 33 do Anexo 4.3 resolvido)
  - ✅ **Pegada G1** fixada em Médio (calibração inicial)
  - ✅ **Regra de cadastro consolidada** (Seção 7 — 22 diretrizes +
    checklist de cadastro)
- 🟡 **Fase 3 — calibração de pesos** — em curso (Seção 8):
  - ✅ **E.0** — 13 cenários-âncora congelados (Sessão 3)
  - ✅ **E.1.a** — harness pipeline validado, cenário 1.1 OK (Sessão 3)
  - ✅ **D1** — filtros hard centralizados em `_compativel_intra`
    predicado (Sessão 4 — Seção 1.7 + 8.4)
  - ✅ **E.1.b parcial** — 5 cenários no harness (Sessão 5 — Seção 8.5):
    1.1, 1.2, 5.2, 6.1 OK; 1.3 e 2.2A FAIL com baseline documentado;
    5.1 movido pra E.2; 6.1 com split primária/secundária
  - ✅ **Auditoria E.0 vs uso real** (Sessão 6 — Seção 8.6) —
    4 redefinições (6.2 promovido pra pré-D2; 2.2B → `perna_anterior(3)`;
    3.1 → Variante B 3x A1/A2; 2.3 timebox); 2 notas de processo
    (densificação ≠ regressão; gotcha calibração denso/realista)
  - ⏳ **6.2 implementação + timebox 2.3** (gate antes de D2)
  - 🟡 **D2** — composição soft INTRA (em curso)
  - ⏳ **D3 / B / A / C / E.1.b2 / E.2** — pendentes
- ⏳ **Fase 4 — estratégia de preenchimento** — pendente

**Próximos passos:**

1. Implementar 6.2 no harness com sub-métricas a/b da Nota de processo #2
2. Timebox 2.3 (15-30min) `costas(3) × 1 treino`
3. D2 — composição soft INTRA + 3 tracking items do stub
4. Aplicar redefinições 2.2B e 3.1 no harness (em E.1.b2)
5. D3, B, A, C, E.1.b2, E.2 conforme calendário

*Documento com Fases 1+2 fechadas e Fase 3 em curso. Última
atualização: 2026-05-08 (Sessão 6 — auditoria E.0 fechada com 4
redefinições + 2 notas de processo; 6.2 promovido pra pré-D2; D2
aberto).*
