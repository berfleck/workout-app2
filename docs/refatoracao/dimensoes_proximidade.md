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

### 1.8 Diretrizes de processo metodológico (registradas Sessão 6)

Duas diretrizes que emergiram da Fase 3 e valem como **princípios
gerais do projeto**, não específicos da auditoria onde foram
identificadas. Promovidas pra esta seção pra que sessões futuras
tratem como diretriz pro projeto inteiro, não como observação
contextual da Sessão 6.

#### 1.8.1 Densificação patológica ≠ anti-padrão escopo→rigor

Setups patológicos em cenários de calibração (`peito(3)` em 1.1/1.3/
2.1, `bracos(4)` em 1.2, `remadas(2)` em 2.2A) **não são regressão**
do princípio "escopo, não rigor" da Seção 1.1. São **densidade
artificial necessária** pra forçar coexistência rara virar mensurável
em 1000 iters — sem isso, gates hard e penalties soft simplesmente
não disparam frequência detectável.

**Distinção operacional:**

- **Densificação patológica:** o **setup do cenário** é denso pra
  observar o mecanismo; a **calibração resultante** ainda é validada
  contra setups realistas via 6.1/6.2. Pesquisa empírica saudável.
- **Anti-padrão escopo→rigor (Seção 1.1):** o **mecanismo** é modelado
  fraco ("personal corrige depois"), independente de setup. Regressão
  silenciosa.

**Como reconhecer cada caso:**

- Se a expectativa numérica do cenário descreve **comportamento do
  gate** (ex: 0% pra hard, faixa pra soft) **e a calibração que cai
  dela é revalidada em setup realista**, é densificação. ✅
- Se a expectativa é "quase nunca importa, deixa acontecer" e nenhuma
  validação realista é feita, é regressão. ❌

Esta diretriz fica registrada porque qualquer revisão futura vai ler
os setups patológicos e questionar — corretamente, sem este registro.

#### 1.8.2 Calibrar denso, validar realista (gotcha de calibração)

Pesos calibrados contra cenários patológicos (1.2 `bracos(4)`,
2.2A `remadas(2)`) precisam ser **revalidados contra sub-métricas em
setup realista** antes de fechar a calibração da dim. Sem isso, peso
calibrado em densidade artificial pode over-corrigir o uso real.

**Procedimento operacional (aplica em D2 / A / C):**

1. Calibrar peso candidato contra cenário patológico (densidade alta
   → violação observável → ajuste mensurável).
2. **Antes de fechar a dim**, rodar mesma versão do peso contra
   sub-métricas em setup realista — proxies da Variante B 2x semana
   no cenário 6.2 (sub-métrica a: `% blocos com 2+ unilaterais mesmo
   grupo`; sub-métrica b: `% rotinas com 2+ unilaterais em costas T2`).
3. Se peso calibrado em patológico over-corrige no realista
   (ex: vira 0% num setup que aceitaria 5-10% como tolerável),
   ajustar antes de fechar.

**Mesma lógica vale pra outros pares denso/realista:**

- 2.1 (densificado `peito(3)`) → validar peso `plano_corporal` em
  `peito(2)` realista (Variante B T1).
- 2.2B (já redefinido pra `perna_anterior(3)` realista — não precisa
  proxy).
- 2.3 (timebox `costas(3)` realista pendente — desbloqueia pós-mocks
  G2).

Esta diretriz é **complementar** à 1.8.1 — densificação é OK desde
que a calibração resultante passe pelo loop de validação realista.

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

**Notas de processo #1 e #2 — promovidas pra Seção 1.8.**

As 2 notas de processo identificadas durante a auditoria foram
**promovidas pra Seção 1.8 (diretrizes de processo metodológico)**
após reconhecimento de que valem como princípios gerais do projeto,
não como observações contextuais desta auditoria.

- **#1 — Densificação patológica ≠ anti-padrão escopo→rigor:**
  ver Seção 1.8.1. Setups densos pra observar mecanismo são OK desde
  que a calibração resultante seja revalidada em setup realista —
  diferente de modelagem fraca de mecanismo (anti-padrão Seção 1.1).
- **#2 — Calibrar denso, validar realista (gotcha):** ver Seção 1.8.2.
  Pesos calibrados em patológico (1.2, 2.2A) precisam validação
  contra sub-métricas do 6.2 antes de fechar D2/A. Mesma lógica pra
  2.1 (validar em `peito(2)` realista) e 2.2B (redefinido direto).

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

### 8.7 D2 — composição soft INTRA (fechado — Sessão 6, 2026-05-08)

3 sub-questões fechadas. Calibração numérica final fica pra C
(loop iterativo com harness).

**D2.1 — Forma da penalty: constante por dim (Variante a).**

Penalty binária "igual/diferente" com peso por subregião (Seção 1.2),
não matriz de "distância categórica". Justificativa clínica: não há
evidência de que pronada-supinada seja mais distante de pronada-neutra
em prescrição de variedade — todas cumprem o papel de variar estímulo.
Calibrar matriz 4×4 seria adivinhação travestida de precisão. Se caso
concreto aparecer onde Variante a deixa passar algo claramente
diferente, revisita.

**D2.2 — Composição com bônus existentes: Caminho B com escala
Crítico ~-100 / Alto ~-50 / Médio ~-20 / Baixo ~-5 (provisório).**

Geo-diversidade (`regiao_diff +1000`) é sacrossanta — nenhuma penalty
soft INTRA deve sobrescrever. Quando geo empata (2 candidatos cumprem
a mesma vaga geográfica), penalty soft escolhe o que varia mais.
Crítico ~-100 já rivaliza com `padrao_diff +100`, então cobre
parcialmente o que Caminho C alternativo cobriria sem comprometer a
hierarquia conceitual. Caso 2.1 (ranking ordinal supino-inclinado-T1)
fica coberto pq dentro do mesmo padrão `empurrar_compostos`,
`plano_corporal` Crítico vence o tie.

Mapeamento Crítico/Alto/Médio/Baixo ↔ dims segue Seções 2-3-7 (peso
por subregião). Calibração numérica final em C — números atuais são
pontos de partida.

**D2.3 — Par-a-par cumulativa.**

Cada par de exercícios alocados no treino soma penalty de cada dim
que colide. 3 supinos retos no mesmo treino = 3 pares × penalty
cumulativa. Justificativa clínica: preserva gradiente discriminante —
1 reto + 1 inclinado < 2 retos < 3 retos < 4 retos, todos
progressivamente piores. Set-based achata (2 = 3 = 4) e perde a
capacidade de discriminar caso 2.1.

Custo computacional desprezível: 8 ex/treino = 28 pares por iteração.

**3 tracking items do stub `_penalty_proximidade` (status pós-D2):**

1. ⏳ Branches INTER + HISTÓRICO no stub — pendente em **D3**
2. 🟡 Dimensões `lateralidade` + `variante_pontual` no stub — hard
   parts fechadas em D1 (`_compativel_intra`); soft parts (lateralidade
   Médio em outras subregiões; variante_pontual Soft Crítico INTER)
   ainda dependem de D2 implementação efetiva em Etapa 7
3. ✅ Decisão par-a-par vs set-based — fechado em D2.3 (par-a-par
   cumulativa)

**Próximas ações pós-D2:**

1. Implementar 6.2 no harness com sub-métricas a/b (gate antes da
   calibração C; permite validar peso anti_uni / hard contextual em
   setup realista — Nota de processo #2 da Seção 8.6)
2. Aplicar redefinições 2.2B / 3.1 quando E.1.b2 abrir
3. Timebox 2.3 (`costas(3) × 1 treino`) — depende de mocks G2 (remadas
   + puxadas com pegada/plano) que estão TODO. Adiado pra E.1.b2
   junto com 2.2A
4. D3 — INTER soft + HISTÓRICO toggle

### 8.8 6.2 implementado no harness (Sessão 6 — 2026-05-08)

Cenário 6.2 adicionado em `tools/calibrar_pesos_dimensoes.py` com
métrica primária + 2 sub-métricas (a/b) da Nota de processo #2 da
Seção 8.6. Refactor mínimo do `Cenario` dataclass: substituiu
`metrica_secundaria_fn` singular por lista `metricas_secundarias` —
permite múltiplas sub-métricas paralelas (mantém CSV back-compat).

**Resultado de 1000 iterações:**

| Métrica | Observado | Notas |
|---|---|---|
| Primária (avisos E6) | **0.00%** OK | Calibração Etapa 6 não over-penaliza Variante B realista |
| Sub-a (% blocos 2+ unis mesmo grupo) | **0.30%** | Proxy realista do 1.2 — anti_uni raro naturalmente em Variante B (1 uni por subregião por treino é o normal) |
| Sub-b (% rotinas 2+ unis costas T2) | **3.30%** | Proxy realista do 2.2A patológico (4.30%) — números próximos validam que setup denso não diverge dramaticamente do realista |

**Achado paralelo registrado — bug retrocompat `subregiao=core`:**

Ao montar 6.2 com `("subregiao", "core", 1)` (como descrito em
`configuracoes_comuns.md` Seção 2.2 Variante B), o gerador retornou
aviso `incompleta` com `qtd_obtida=0` em todas as iterações. Causa:
a subregião legacy `core` foi refatorada na Sessão 2 da Fase 1 (item
15-quater) em `core_dinamico` + `core_isometrico`. Retrocompat existe
em `_padroes_de_escopo` (linha 1382 do `gerador_treino.py`) mas **não**
é aplicada no caminho de alocação principal (`pre_alocar_rotina`),
fazendo `("subregiao", "core", N)` falhar com 0 selecionados.

**Workaround aplicado em 6.2:** usar `core_dinamico(1)` em T1 e
`core_isometrico(1)` em T2 (alternância clínica natural). Comentário
inline em `_cfg_6_2` documenta o workaround.

**TODO separado** (não bloqueia Fase 3): investigar caminho de
retrocompat em alocação. Caminhos: (i) estender retrocompat pra cobrir
caminho principal, (ii) atualizar UI/templates pra usar nomes
refatorados, (iii) deprecar `subregiao=core` legacy. Não é parte da
Etapa 6 — é débito técnico do refator CORE da Sessão 2 que ficou
parcial. Reabrir quando 6.2 ou outras configurações realistas forem
expandidas.

**Sub-métrica b confirma proxy do gotcha "calibrar denso, validar
realista":** baseline patológico do 2.2A (4.30%) e proxy realista do
6.2 (3.30%) ficaram **dentro de 1 ponto percentual**. Validação leve,
mas indica que setup denso não over-amplifica a coexistência de unis
em costas — peso final do hard contextual D1.d calibrado contra
patológico provavelmente cobre o realista sem ajuste extra.
Sub-métrica a (0.30%) é tão baixa que vira pouco informativa pra
calibrar peso anti_uni — confirma que anti_uni em Variante B só
dispara em casos de exception (V-Up Uni + Tríceps Uni do 5.2 etc.).

### 8.9 D3 — INTER soft + HISTÓRICO toggle (fechado — Sessão 6, 2026-05-08)

4 sub-questões fechadas. Calibração numérica final fica pra C.

**D3.1 — Estrutura INTER soft: multiplicador global 0.8 com overrides
documentados (Variante a).**

Default INTER = 0.8 × peso INTRA por dim. Mantém calibração enxuta
(1 número por dim + 1 fator global) e preserva hierarquia INTRA > INTER
da Seção 1.4. Overrides explícitos (registrados em sessões anteriores):

| Dim | Multiplicador INTER | Origem |
|---|---|---|
| `familia_estrita` | ~0.80 | Seção 1.4 (Sessão 2) |
| `variante_pontual` | ~0.95 (Soft Crítico, quase hard) | D1.c (Sessão 4) |
| Resto (`lateralidade`, `pegada`, `plano_corporal`, `equipamento_grupo`) | 0.80 default | D3.1 (Sessão 6) |

Se calibração final em A/C revelar dim onde 0.8 destoa fortemente,
abre override pontual com justificativa clínica. Sem evidência hoje
pra peso INTER independente em todo o set — adicionar 5 parâmetros
sem ganho proporcional.

**D3.2 — Migração família INTER de hard pra soft alto: Caminho C
(spec agora, migração estrutural em Etapa 7).**

Hoje `pre_alocar_rotina` mantém `variacao_pais_globais: set[str]` que
**bloqueia hard** candidatos cuja família já foi usada em outros
treinos. Decisão Sessão 2 (Seção 1.4) move pra **soft alto via score**.

D3 é especificação. Migração estrutural real (remoção do set hard +
adição de penalty score) acontece na Etapa 7. Caminho A (clean break
agora) força refator estrutural prematuro; Caminho B (coexistência
hard+soft via toggle) polui calibração com 2 semânticas. Caminho C
preserva código atual durante D3 e deixa decisão "A vs B" registrada
como **ponto de auditoria pra Etapa 7**.

Implicação no toggle `relaxar_familia` do app: ambiguidade já
registrada em Seção 1.4 (decisão Etapa 7). D3 não muda nada.

**D3.3 — HISTÓRICO toggle ON: granularidade nome + família, soma
livre com INTER (sem clipping).**

Quando toggle ON, penalty alta dispara quando:

```
cand.nome ∈ R-1.nomes  OR  cand.variacao_de ∈ R-1.familias
```

Granularidade (a) "só nome" deixaria passar variação cosmética sem
variação funcional (Supino Reto Barra na R-1, Reto Halteres na nova →
mesmo estímulo mecânico, escapa). Granularidade (c) "+ variante_pontual"
sobrepõe Soft Crítico INTER que já cobre o caso via composição.

**Composição com INTER sem clipping:** candidato que repete família
em outro treino da rotina atual E na R-1 é o pior caso (~180% Alto =
~80% INTER + ~100% HISTÓRICO). Soma livre faz sentido — desincentivo
proporcional ao "duplo erro". Clipping aplainaria essa diferença
clínica importante.

Granularidade (b) Nome + família final. Variantes pontuais cruzando
subregião: cobertas via composição INTER (Soft Crítico) + HISTÓRICO
(Alto), não via regra dedicada. Mais simples.

**D3.4 — Localização: HISTÓRICO entra na Fase 0 (`pre_alocar_rotina`)
junto com INTER soft.**

INTER soft e HISTÓRICO são penalties de **seleção global**, não de
pareamento. Penalty em Fase 2 (`montar_blocos`) seria estranho — quando
chega lá, exercícios já estão escolhidos. Unifica localização e
simplifica função de score: uma chamada recebe `alocados_intra`,
`alocados_inter`, `historico_r1` como args opcionais e devolve penalty
composta. Fase 2 fica focada em pareamento INTRA puro.

**Implementação Etapa 7 (esboço):**

```python
def gerar_multiplos_treinos(
    banco, configs,
    relaxar_familia: bool = False,  # legacy — decisão final Etapa 7
    historico_r1: list[Sessao] | None = None,  # toggle OFF = None
):
    ...
    # Fase 0: pre_alocar_rotina chama _score_proximidade(cand,
    #         alocados_intra, alocados_inter, historico_r1, dims, pesos)
    # Score acumula INTRA (D2 par-a-par) + INTER (multiplicador 0.8) +
    # HISTÓRICO (peso integral se historico_r1 ≠ None)
```

**Cenários afetados (E.1.b2 quando D3 implementação real fechar):**

| ID | Mecanismo testado | Expectativa |
|---|---|---|
| 3.1 | Variante B 3x A1/A2 com peito em ambos — INTER família soft Alto | 10-15% (desencoraja mas permite) |
| 3.2 | Step Up + Recuo do Estepe — INTER família `subida_elevada` | <10% (banco não aperta) |
| 3.3 | Passada + Passada Dos Steps — mesma família, banco mais aperta | 20-50% |
| 4.1 | HISTÓRICO toggle ON, R-1 — nome + família | <3% |
| 4.2 | HISTÓRICO toggle OFF | sem expectativa rigorosa (sanity) |

**3 tracking items do stub `_penalty_proximidade` (status pós-D3):**

1. ✅ Branches INTER + HISTÓRICO no stub — fechado em D3 (spec; impl
   Etapa 7)
2. ✅ Dimensões `lateralidade` + `variante_pontual` no stub — hard
   parts D1; soft parts D2; INTER multiplicador D3
3. ✅ Decisão final par-a-par vs set-based — fechado em D2.3

### 8.10 B — estrutura de configuração de pesos (fechado — Sessão 6, 2026-05-08)

5 sub-questões fechadas. Layout final do módulo + interface de
override.

**B.1 — Forma de armazenamento: módulo separado `pesos_proximidade.py`
com dataclass.**

Tira inflação do `gerador_treino.py` (~3000 linhas), formaliza
estrutura via dataclass com type checking, mantém defaults em runtime
sem overhead de parsing externo. YAML externo seria over-engineering
pro tamanho do projeto (single-user, configuração via edição de
código). Module-level constants no gerador misturariam "como funciona"
com "quais valores usa", dificultando auditoria.

**B.2 — Hierarquia de override: 2 níveis (default → subregião) +
estrutura paralela `anti_uni`.**

Lookup pra cada (dim, contexto):

```
peso(dim, contexto, subregião) =
  override_subregião[dim][contexto][subregião]   ← se existe
  ou default[dim][contexto]                       ← caso contrário
```

Sem override por padrão — Seção 1.5 ancora escopos em subregião.
Hipotético override por padrão seria over-engineering sem evidência
clínica.

`anti_uni_mesmo_grupo` da Etapa 5 (peso por grupo muscular, não por
subregião) vive em estrutura paralela ortogonal — não forçar duas
semânticas distintas na mesma estrutura.

**B.3 — Localização: raiz do projeto, arquivo único.**

Coerente com padrão atual (`gerador_treino.py`, `database.py`,
`gerar_imagem.py` todos na raiz). Subpasta sem múltiplos arquivos
relacionados é estrutura sem conteúdo.

**B.4 — Interface de override pro harness em C: argumento opcional
`pesos_override: ConfigPesosProximidade | None = None`.**

```python
def gerar_multiplos_treinos(
    banco, configs,
    relaxar_familia: bool = False,
    historico_r1: list[Sessao] | None = None,
    pesos_override: ConfigPesosProximidade | None = None,  # B.4
):
    pesos = pesos_override or PESOS_DEFAULT
    ...
```

Sem efeito colateral global. Cada chamada isolada. C varre variações
em sequência ou paralelo sem contaminação cruzada. Global mutável é
anti-pattern; env var acopla a SO desnecessariamente.

**B.5 — Categóricos em B, mapping em A.**

B contém labels categóricos (`"soft_critico"`, `"soft_alto"`,
`"soft_medio"`, `"soft_baixo"`). A define mapping
`{"soft_critico": -100, ...}`. Gerador resolve label → número via
mapping ao calcular score.

Mexer em escala (que C provavelmente vai fazer várias vezes na
calibração fina) vira editar 1 lugar (mapping em A) em vez de N
entradas (cada subregião × dim em B). Custo de indireção em debugging
é pequeno comparado à flexibilidade ganha.

**Estrutura final do módulo (esboço pra Etapa 7):**

```python
# pesos_proximidade.py

from dataclasses import dataclass, field
from typing import Optional

# Labels categóricos (resolução numérica em A — ver mapping abaixo)
ESCALA_NUMERICA = {
    "soft_critico": -100,  # ← A define magnitude
    "soft_alto":    -50,
    "soft_medio":   -20,
    "soft_baixo":    -5,
    # "anti_uni_etapa5" definido separadamente (Seção 8.11 A.2)
}

@dataclass
class PesoDim:
    """Peso categórico de uma dimensão por contexto.
    Override por subregião opcional (None = usa default global).
    """
    intra_default: str  # label categórico
    intra_overrides: dict[str, str] = field(default_factory=dict)
    inter_multiplicador: float = 0.8  # D3.1
    inter_override: Optional[float] = None  # ex: variante_pontual=0.95
    historico_r1_multiplicador: float = 1.0  # D3.3

@dataclass
class ConfigPesosProximidade:
    pegada: PesoDim
    plano_corporal: PesoDim
    equipamento_grupo: PesoDim
    # Hard parts (família, variante_pontual hard, lateralidade hard
    # contextual costas) NÃO entram aqui — vivem no predicado
    # `_compativel_intra` (Seção 1.7).
    # Soft parts dessas dims que entram são variante_pontual INTER
    # (Soft Crítico ~0.95) e família INTER (Soft Alto ~0.80) — campos
    # adicionais a definir.
    anti_uni_mesmo_grupo_pesos: dict[str, float]  # B.2 ortogonal

PESOS_DEFAULT = ConfigPesosProximidade(...)  # ← A define defaults
```

A escala numérica e os defaults concretos ficam pra A. B fixou
**onde e como** os pesos são representados.

### 8.11 A — escala numérica final (fechado — Sessão 6, 2026-05-08)

3 sub-questões fechadas. Mapping numérico final pra B referenciar.

**A.1 — Magnitude + progressão INTRA confirmadas: D2.2 (-100/-50/
-20/-5).**

Mapping definitivo (referenciado por B.5):

```python
# pesos_proximidade.py
ESCALA_NUMERICA = {
    "soft_critico": -100,
    "soft_alto":     -50,
    "soft_medio":    -20,
    "soft_baixo":     -5,
}
```

Progressão custom (2.0× / 2.5× / 4.0×) reflete papéis funcionais
distintos, não escala matemática limpa. Justificativas registradas:

- **Crítico -100**: rivaliza com `padrao_diff +100` (Caminho B da
  D2.2) — quando padrão empata, soft Crítico decide; quando padrão
  difere, geo vence.
- **Baixo -5**: deliberadamente tiny — equipamento_grupo é tiebreaker
  (Seção 1.5), nunca acumula.
- **Alternativas descartadas**: linear inflaria Baixo demais
  (acumula); log puro subutilizaria Médio; Crítico -150 quebraria
  hierarquia geo > soft.

C pode iterar fino sobre estes números, mas baseline = D2.2.

**A.2 — Anti_uni Etapa 5 (-75) fica fora da escala unificada (Variante
c).**

`anti_uni_mesmo_grupo = -75` continua como peso fixo da Etapa 5.
Encaixa em estrutura paralela `anti_uni_mesmo_grupo_pesos` da B.2,
ortogonal à escala categórica unificada.

3 reforços da decisão:
1. Mecanismo já validado empiricamente (cenário 5.2 passa em 1000
   iters).
2. B.2 já tratou anti_uni como ortogonal.
3. Re-mapear sem evidência clínica = modificar mecanismo validado por
   estética (anti-padrão).

Risco real das variantes a/b: mover pareamento desejado V-Up Uni +
Tríceps Uni pra fora do >50% target sem ganho proporcional.

**A.3 — Derivados INTER e HISTÓRICO confirmados.**

**INTER (multiplicador global 0.8 + overrides):**

| Categoria | INTRA | INTER (×0.8) | INTER override |
|---|---|---|---|
| Crítico | -100 | -80 | — |
| Alto | -50 | -40 | família ×0.80 = -40 (mesmo) |
| Médio | -20 | -16 | — |
| Baixo | -5 | -4 | — |
| variante_pontual | -100 | — | ×0.95 = **-95** (quase hard, D1.c) |

**HISTÓRICO toggle ON (multiplicador 1.0):**

| Categoria | INTRA | HISTÓRICO ON |
|---|---|---|
| Crítico | -100 | -100 |
| Alto | -50 | -50 |
| Médio | -20 | -20 |
| Baixo | -5 | -5 |

**Pior caso família INTER + HISTÓRICO** (D3.3 soma livre):
candidato repete família entre treinos E aparece na R-1 →
INTER família (-40) + HISTÓRICO família (-50) = **-90**.

Comparado com `padrao_diff +100`: penalty pior caso (-90) **não
supera** o bônus geo (+100). É exatamente a semântica de "soft alto"
da Seção 1.4: desencoraja fortemente mas permite quando banco aperta.
Se -90 superasse +100, família INTER viraria hard de fato e perderia
a flexibilidade que motivou tirar do hard em primeiro lugar (Sessão
2). Cenário 3.3 (Passada+Passada Dos Steps com banco apertado,
expectativa 20-50%) é o teste empírico: se estourar pra 60-70% em C,
revisitar; mas estrutura está coerente.

### 8.12 C — calibração fina iterativa via harness (fechado — Sessão 6, 2026-05-08)

4 sub-questões fechadas. C fecha o **processo** de calibração; os
números finais saem do processo (executado em sessão futura após
E.1.b2 + Etapa 7).

**C.1 — Estratégia: manual + coordinate descent.**

Dev calibra 1 dim por vez fixando outras, baseado em hipótese clínica,
observa cenários do harness, ajusta. Toda a fundamentação D1/D2/D3
estabeleceu papel funcional explícito por peso — calibração aqui é
afinamento informado, não exploração no escuro. Automação (grid/
random/bayesiano) seria adequada se faltasse direcionamento; aqui
sobra. Coordinate descent evita over-parameterização e mantém
auditabilidade (quando algo melhora/piora, fica claro qual mudança
causou).

**C.2 — Ordem das dims: priorizada por cobertura + acoplamento clínico.**

| Ordem | Dim | Cenários cobertos | Razão |
|---|---|---|---|
| 1 | Família INTER (multiplicador 0.80) | 3.1, 3.2, 3.3 | 3 cenários — mais informativo |
| 2 | Plano_corporal + Pegada (acopladas) | 2.1, 2.3 | Em peito, supinos engajam ambas simultâneo — clínica diz que estão ligadas |
| 3 | Lateralidade soft (Médio padrão) | 2.2B (perna_anterior) | 1 cenário; anti_uni -75 Etapa 5 já fixo ortogonal — auditoria mais que calibração |
| 4 | HISTÓRICO toggle ON (multiplicador 1.0) | 4.1, 4.2 | Validar peso integral é adequado pra <3% R-1 e OFF sanity |
| 5 | Equipamento_grupo (tiebreaker Baixo -5) | nenhum direto | Calibrar último — só atua quando tudo o mais já decidiu |

**C.3 — Critério de parada: todos cenários nas faixas + cap 5-10 rounds/dim.**

C termina quando:
- Cenários hard (1.x, 2.2A): 0% (depende de Etapa 7 implementar
  predicado, não de C)
- Cenários soft caem nas faixas E.0 esperadas
- Cenários sanity (5.x, 6.x) continuam OK
- Sub-métricas 6.2 (a/b) ficam dentro de range similar a baselines
  (<2× alteração)

**Validação cruzada como salvaguarda:** ajustar peso pra fechar X não
pode quebrar Y. Se quebrar, é signal de **calibração inconsistente**
— revisita B ou A em vez de brute-force. Esta é a parte mais
importante do critério.

**Cap 5-10 rounds/dim:** salvaguarda contra oscilação infinita em
torno de ponto onde estrutura não permite convergência. Sem cap,
calibração pode virar gasto desnecessário de tempo.

**C.4 — Timing: sequencial após E.1.b2 + calibrar contra stub harness
+ sanity pós-Etapa 7.**

**Pré-condições:**
1. Stub `_penalty_proximidade` no harness com 3 branches (INTRA +
   INTER + HISTÓRICO)
2. Mocks G2/G4/G8 com pegada/plano/equipamento populated (E.1.b2)
3. Cenários 2.x/3.x/4.x implementados no harness (E.1.b2)

**Sequencial após E.1.b2:** calibração de cada dim depende de todos
os cenários que a testam — fragmentar (paralelo) gera retrabalho que
excede o ganho de tempo. C arranca quando E.1.b2 fecha.

**Calibrar contra stub harness:** stub é "a spec executável" — fiel
ao predicado da Seção 1.7 + score soft das Seções 8.7+8.9. Se stub
divergir do código real depois, é bug do stub/spec/código, não da
calibração.

**Sanity pós-Etapa 7:** após código real implementado, re-rodar
harness pra confirmar que produz mesmas métricas que stub. Salvaguarda
explícita que detecta divergência se houver.

**Saída de C:**
- Pesos numéricos finais em `pesos_proximidade.PESOS_DEFAULT` (B)
- Registro de auditoria (CSV de iterações + justificativa por dim)
- `pesos_override` continua disponível pra revisões futuras

### 8.13 Fase 3 conceitual fechada — milestone Sessão 6

Todas as decisões da Fase 3 fechadas em Sessão 6 (2026-05-08):

| Bloco | Status | Sessão | Seção |
|---|---|---|---|
| E.0 — 13 cenários-âncora | ✅ | 3 | 8.2 |
| E.1.a — pipeline harness | ✅ | 3 | 8.3 |
| D1 — filtros hard centralizados | ✅ | 4 | 1.7 + 8.4 |
| E.1.b parcial — 5 cenários | ✅ | 5 | 8.5 |
| Auditoria E.0 vs uso real | ✅ | 6 | 8.6 |
| D2 — composição soft INTRA | ✅ | 6 | 8.7 |
| 6.2 happy path Variante B | ✅ | 6 | 8.8 |
| D3 — INTER soft + HISTÓRICO toggle | ✅ | 6 | 8.9 |
| B — estrutura configuração pesos | ✅ | 6 | 8.10 |
| A — escala numérica final | ✅ | 6 | 8.11 |
| C — calibração processo | ✅ | 6 | 8.12 |

**O que falta pra Fase 3 fechar 100%:**

- ⏳ **E.1.b2 — implementação dos 8 cenários soft restantes**
  (2.1, 2.2B, 2.3, 3.1, 3.2, 3.3, 4.1, 4.2) + expansão de mocks
  G2 (remadas+puxadas), G4 (squats refinados+subida_elevada),
  G8 (core completo). Trabalho considerável (não-trivial em escopo
  clínico — cada exercício precisa de pegada/plano/equipamento/
  variante_pontual cadastrado).
- ⏳ **C executado** — calibração real após E.1.b2 + Etapa 7
- ⏳ **E.2 — validação completa**: 13 cenários + 8 problemas
  conhecidos + re-rodar 1.3 e 2.2A pós-Etapa 7

**Etapa 7** (implementação real no `gerador_treino.py`) acontece em
paralelo ou após Fase 3 100% fechar. Etapa 7 implementa:
- Predicado `_compativel_intra` (Seção 1.7)
- Score soft INTRA (Seção 8.7 / D2)
- Score INTER + HISTÓRICO (Seção 8.9 / D3)
- Módulo `pesos_proximidade.py` (Seção 8.10 / B)
- Mapping numérico (Seção 8.11 / A)
- Migração família INTER hard → soft (D3.2 — decisão A vs B em Etapa 7)

### 8.14 E.1.b2 / E.2 — pendentes

A serem documentados conforme cada bloco fechar.

---

## 9. Fase 4 — estratégia de preenchimento dos 125+ exercícios

> **Status:** protocolo registrado (Sessão 6 — 2026-05-08), execução
> pendente. Acontece após Fase 3 fechar 100% (E.1.b2 + C executado +
> E.2) e idealmente em paralelo com Etapa 7.

A Fase 4 cadastra **as 5 dimensões de proximidade + variante_pontual**
em todos os ~125 exercícios do banco. O risco principal não é
volume — é **inconsistência entre exercícios análogos cadastrados em
momentos diferentes** (ex: Stiff Halteres recebe `plano_corporal=
"em_pe"` numa sessão; Stiff Smith recebe `plano_corporal="em_pe_guiado"`
numa outra — divergência sem critério explícito).

Pra evitar isso, Fase 4 segue **protocolo semi-automatizado** de
revisão clínica estruturada — não "Code preenche tudo sozinho".

### 9.1 Protocolo de preenchimento

**Etapa 1 — Triagem inicial (Code automatizado).**

Code classifica os ~125 exercícios em 3 categorias:

- **🟢 Verde** — todas as 5 dimensões resolvem direto pelas 22
  diretrizes da Seção 7 (Regra de Cadastro Consolidada). Sem
  ambiguidade clínica. Ex: Supino Reto Halteres (família Supino Reto,
  pegada pronada, plano reto, equipamento halter, lateralidade
  bilateral, variante_pontual false — todas determinadas pela
  diretriz).
- **🟡 Amarelo** — 1-2 dimensões precisam de decisão clínica não
  coberta pelas diretrizes. Ex: exercício com pegada que poderia ser
  "neutra" ou "mista" dependendo da execução.
- **🔴 Vermelho** — múltiplas zonas cinzentas. Tipicamente
  exercícios novos sem análogo claro entre os já cadastrados.

Triagem é output em tabela commitada (`docs/refatoracao/
triagem_fase_4.md` ou similar), com decisão preliminar do Code +
flag de zona cinzenta + exercícios análogos relevantes.

**Etapa 2 — Preenchimento automático dos verdes (Code).**

Code aplica as diretrizes da Seção 7 e cadastra todos os 🟢 verdes
em XLSX. Output: tabela commitada das atribuições + diretriz aplicada
em cada caso (rastreabilidade).

**Etapa 3 — Conversa estruturada nos amarelos/vermelhos
(personal + Code).**

Code agrupa perguntas **por critério clínico**, não por exercício.
Ex: em vez de "Stiff Halteres tem plano em_pe?" + "Stiff Smith tem
plano em_pe_guiado?" + ..., agrupa: "Stiffs com guia (Smith, máquina,
trilho fixo) — qual `plano_corporal`?" — uma pergunta resolve N
exercícios.

**Formato fixo de pergunta:**

```
[Critério/Subgrupo] — [N exercícios afetados]

Proposta: [valor X com justificativa]
Alternativa: [valor Y com cenário em que valeria]

Pergunta concreta: [pergunta específica]
```

User responde uma vez genericamente; Code aplica em todos os
exercícios afetados.

**Etapa 4 — Registro de decisões cinzentas
(`docs/refatoracao/decisoes_cadastro_etapa_7.md`).**

Cada caso ambíguo decidido na Etapa 3 fica registrado:

```
## [Critério] — [data]

**Caso:** [descrição da ambiguidade]
**Decisão:** [valor escolhido]
**Critério usado:** [justificativa clínica]
**Exercícios afetados:** [lista]
**Análogos futuros:** [como aplicar em cadastros novos]
```

Esse registro vira **fonte de verdade pra cadastros futuros** —
exercícios novos que caem nas mesmas zonas cinzentas seguem o
critério já decidido em vez de re-abrir a discussão.

**Etapa 5 — Confirmação bloco a bloco antes de salvar no XLSX
(preferencialmente Plan Mode).**

Code apresenta diff proposto (XLSX antes / XLSX depois) em blocos
por subregião (peito → costas → ombro → pernas → core → braços).
User confirma cada bloco antes de salvar. Plan Mode evita rollback
grande se decisão preliminar estiver errada — divergência aparece
no diff antes de virar mudança commitada.

### 9.2 Observação importante

**Anti-padrão a evitar:** "Code preenche tudo sozinho seguindo as
diretrizes" — sem revisão clínica estruturada, decisões marginais
(que as diretrizes cobrem só parcialmente) viram acúmulo silencioso
de inconsistência. As diretrizes da Seção 7 são *bom guia*, não
*algoritmo determinístico exaustivo*.

A 22ª diretriz é "quando em dúvida, pergunte" — Etapa 3 do protocolo
acima implementa isso de forma escalável (perguntas agrupadas, não
N×125 perguntas).

### 9.3 Pré-condições antes de Fase 4 arrancar

1. ✅ Set final de dimensões + diretrizes (Fase 1+2 — completo)
2. ⏳ Estrutura `pesos_proximidade.py` (Etapa 7 — implementação real)
3. ⏳ E.1.b2 + C + E.2 fechados (Fase 3 100%)

Fase 4 pode arrancar quando Etapa 7 implementação estrutural fechar.
Calibração refinada (C) pode acontecer em paralelo com Fase 4 se
mocks já cobrirem dims de exercícios mais relevantes — desacoplar
quando possível.

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
  - ✅ **D2 — composição soft INTRA** (Sessão 6 — Seção 8.7) —
    D2.1 Variante a (constante por dim); D2.2 Caminho B com escala
    provisória ~-100/-50/-20/-5; D2.3 par-a-par cumulativa
  - ✅ **6.2 implementado** (Sessão 6 — Seção 8.8) — primária 0.00%
    OK; sub-a 0.30% / sub-b 3.30% baseline pre-Etapa 7. Refactor
    Cenario dataclass pra suportar lista de secundárias. Achado
    paralelo registrado (bug retrocompat `subregiao=core`).
  - ✅ **D3 — INTER soft + HISTÓRICO toggle** (Sessão 6 — Seção 8.9)
    — D3.1 multiplicador global 0.8 com overrides documentados
    (família ~0.80, variante_pontual ~0.95); D3.2 Caminho C (spec
    agora, migração estrutural Etapa 7); D3.3 granularidade nome +
    família, soma livre com INTER; D3.4 localização Fase 0
    (`pre_alocar_rotina`). 3 tracking items do stub fechados.
  - ✅ **B — estrutura de configuração de pesos** (Sessão 6 — Seção
    8.10) — B.1 módulo separado `pesos_proximidade.py` com dataclass;
    B.2 hierarquia 2 níveis (default → subregião) + anti_uni
    ortogonal; B.3 raiz do projeto arquivo único; B.4 argumento
    opcional `pesos_override` na função geradora; B.5 labels
    categóricos em B + mapping numérico em A.
  - ✅ **A — escala numérica final** (Sessão 6 — Seção 8.11) — A.1
    confirmou D2.2 (-100/-50/-20/-5); A.2 anti_uni -75 fora da escala
    unificada (estrutura paralela); A.3 derivados INTER/HISTÓRICO
    validados — pior caso família soft (-90) < bônus padrao_diff
    (+100), preserva semântica "desencoraja mas permite".
  - ✅ **C — calibração fina iterativa** (Sessão 6 — Seção 8.12) —
    C.1 manual + coordinate descent; C.2 ordem família INTER →
    Plano+Pegada → Lateralidade → HISTÓRICO → Equipamento; C.3
    parar quando todos cenários nas faixas + cap 5-10 rounds/dim
    + validação cruzada como salvaguarda; C.4 sequencial após
    E.1.b2, calibrar contra stub harness, sanity pós-Etapa 7.
  - 🎯 **Fase 3 conceitual 100% fechada** (Sessão 6 — Seção 8.13)
    — todos blocos de decisão concluídos. Resta E.1.b2 (impl) +
    C executado + E.2 (validação).
  - ⏳ **Timebox 2.3** adiado pra E.1.b2 (depende de mocks G2)
  - ⏳ **E.1.b2 — 8 cenários soft + mocks G2/G4/G8**
  - ⏳ **C executado** (após E.1.b2 + Etapa 7)
  - ⏳ **E.2 — validação completa**
- 🟡 **Fase 4 — estratégia de preenchimento** — protocolo registrado
  (Seção 9, Sessão 6); execução pendente após Etapa 7 estrutural

**Próximos passos:**

1. **E.1.b2 — implementação dos 8 cenários soft + expansão de mocks
   G2/G4/G8.** Trabalho considerável (escopo clínico — cada exercício
   precisa pegada/plano/equipamento/variante_pontual cadastrado +
   8 metric/config functions no harness).
2. Aplicar redefinições 2.2B (perna_anterior(3)) e 3.1 (Variante B
   3x A1/A2) no harness conforme E.1.b2 implementa
3. C executado — calibração real contra cenários soft completos
4. E.2 — validação completa (13 cenários + 8 problemas conhecidos +
   re-rodar 1.3 e 2.2A pós-Etapa 7)
5. Investigar bug retrocompat `subregiao=core` em alocação principal
   (Seção 8.8 — débito técnico)

*Documento com Fases 1+2 fechadas e **Fase 3 conceitual 100% fechada**
em Sessão 6 (2026-05-08 — Seção 8.13). Última atualização: 2026-05-08
(Sessão 6 — todas decisões da Fase 3 fechadas; E.1.b2 + C execução +
E.2 pendentes; Etapa 7 implementação real no gerador acontece em
paralelo).*
