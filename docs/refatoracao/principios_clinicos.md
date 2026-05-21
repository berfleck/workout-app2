# Princípios Clínicos do Gerador — documento de trabalho

> **STATUS: RASCUNHO MUTÁVEL — observações provisórias, não regras.**
> Compilado durante entrevista guiada com o personal trainer (Bernardo)
> em 2026-05-19, **Lente A** (caso a caso) sobre poucas rotinas. Os
> "conceitos" abaixo são **hipóteses de trabalho** extraídas de pouca
> evidência, não leis estabelecidas. Podem ser revisados, refinados,
> fundidos ou descartados.
>
> **Como ler**: o que importa são os **enunciados gerais** (os
> princípios). Os exemplos de exercício específico (Pullover, Dead Bug,
> Cadeira Extensora, rotinas com seed X) são **andaime/ilustração** —
> serviram pra fazer o princípio emergir, mas não devem ser tratados
> como âncora nem como regra de ouro. Se o banco mudar, os exemplos
> envelhecem; os princípios não. **Não cristalizar caso pontual em
> doutrina.**
>
> **Propósito**: capturar a lógica clínica que hoje está implícita no
> greedy + scoring + carve-outs e tornar explícita em texto, sem
> vocabulário técnico do app. Base para decisão estrutural do refator
> (ver `handoff_2026-05-19_decisao_refator.md`).

---

## Valores do app (lê isto antes dos conceitos)

Citação do usuário (2026-05-19):

> *"Eu sempre quis ter uma tabela/banco com meus exercícios pelo simples
> fato de que ele me ajuda a LEMBRAR das várias variações de exercícios
> e de exercícios diferentes. É por isso que eu temo tanto os vieses:
> app priorizando exercícios que estão em maior quantidade no pool ou
> algum viés de distribuição que, combinado com tags e penalidades,
> acaba extinguindo ou priorizando alguns exercícios."*

O app nasceu **em parte** como apoio de memória — ajudar o personal a
lembrar da amplitude do repertório. Disso decorre um valor importante:
**não esconder exercícios sistematicamente** (e explica o medo de
viés).

Mas isso é **um valor entre vários**, não a coisa central que subordina
todo o resto. O app precisa equilibrar:

- **Acesso à variedade do repertório** (a motivação de memória acima)
- **Qualidade clínica** (não montar treino ruim)
- **Intenção do treinador** (respeitar o que o personal quer pra cada
  aluno)

Esses valores às vezes puxam em direções opostas (ex: variedade pode
empurrar pra um exercício menos "central"; qualidade pode preferir o
clássico). **Nenhum domina o outro de forma absoluta** — o design tem
que balancear, e o ponto do balanço pode até variar por aluno/contexto.

> ⚠️ Correção registrada (2026-05-21): uma versão anterior deste doc
> afirmava que "variedade é O objetivo e correção clínica é só
> constraint", com uma "inversão de design". Isso foi
> **extrapolação** — a fala original era sobre uma motivação, não uma
> hierarquia de objetivos. Variedade tem valor real; não é a métrica
> única e soberana.

**Implicações que seguem valendo (com a ressalva acima):**

1. **Cobertura ao longo do tempo importa.** Variedade não é só dentro
   de 1 rotina — o repertório deveria circular ao longo de semanas. O
   mecanismo de HISTÓRICO (evitar R-1) é relevante pra isso.
2. **Viés sistemático é um problema real a vigiar** — exercícios
   sumindo de forma não-intencional (landmine, etc.) contrariam o valor
   de acesso à variedade.
3. **Centralidade faz sentido como knob ajustável** (roadmap de
   2026-05-18) — quanto o app pende pra "clássicos" vs "variado" pode
   ser parâmetro, não decisão fixa.
4. **Validação quantitativa (dashboard)** é útil pra enxergar viés que
   não aparece a olho — mas é instrumento de diagnóstico, não o juiz
   único de qualidade.

---

## Origem deste documento

Entrevista de 2026-05-19, formato Lente A (caso a caso, 1 pergunta por
vez). 3 rotinas geradas da Variante B do 2x/semana (Sec 2.2 de
`configuracoes_comuns.md`) foram avaliadas pelo usuário como se fossem
propostas de um colega pra um aluno do perfil modal.

Cobertura: **(v1)** upper/lower split Empurrar/Posterior +
Puxar/Anterior (Variante B 2x, 3 rotinas). **(v2, 2026-05-19)**
Variante A 3x semana (`upper(3)+lower(3)+core(2)`, 1 rotina = 3
treinos full body com viés). Não cobre 1x/semana full body, frequência
maior, perfis não-modais.

---

## Os conceitos

### Conceito 1 — Tier intrínseco do exercício (com overrides)

Cada exercício tem um **tier padrão** (principal / intermediário /
acessório) baseado em propriedades biomecânicas, mas o tier efetivo
no contexto é resultado de:

```
tier_efetivo = f(tier_default, perfil_aluno, posição_na_rotina)
```

**Default por propriedade biomecânica:**
- Compound + carga progressiva alta + amplitude boa → **principal**
- Isolation ou variantes restritas → **acessório**
- Exemplos: Agachamento Livre = principal; Goblet Rampa = acessório;
  Supino com Barra = principal; Crossover/Crucifixo = acessório;
  Desenvolvimento = principal; Elevação Lateral/Frontal = acessório

**Override 1 — Por perfil de aluno:**
- Aluno iniciante pode ter Goblet/Apoio como "principal dele"
- Aluno com foco saúde/emagrecimento → a carga em barra livre deixa
  de ser crítica → o "principal" pode descer pra um exercício menos
  carregado

**Override 2 — Por contexto de rotina:**
- Búlgaro pesado no início → vira o principal do treino
- Agachamento Livre no fim → pode virar "deload" focado em cadência/
  amplitude (assume papel de acessório mesmo sendo intrinsecamente
  principal)

**Implicação operacional**: tier-order **PRINCIPAL ANTES DE ACESSÓRIO**
dentro de subregião foi o achado mais consistente da entrevista —
**3 de 3 rotinas tiveram esse erro** (Goblet antes de Smith, Apoio
antes de "Supino que não veio").

### Conceito 2 — Tolerância a fadiga prévia

Propriedade do exercício: o quanto ele tolera ser feito DEPOIS de outro
que fadigou músculos compartilhados.

**Eixo principal — máquina vs peso livre:**
- Máquina: alta tolerância. Carga regulável + estabilidade externa
  permite ajustar mesmo com fadiga
- Peso livre: baixa tolerância. Fadiga compromete técnica + segurança
  + capacidade de carga

**Exemplos do usuário:**
- Pullover ANTES de Barra Fixa Livre = ❌ (fadiga compromete a Barra)
- Pullover ANTES de Puxada Aberta na máquina = ✓ (máquina estabiliza)

**Implicação operacional**: ordem de exercícios dentro de um treino
deve considerar **carryover de fadiga** entre eles, não só "principal
antes de acessório". Os 2 conceitos interagem.

### Conceito 3 — Sub-categoria dentro do padrão

Padrões agrupam coisas funcionalmente distintas. Exemplo concreto:

`padrao = puxadas` inclui hoje:
- Puxadas "completas": Barra Fixa, Puxada Aberta, etc. (envolvem
  flexão de cotovelo + escápula + dorsal — bíceps + romboides + lat)
- Pullover (Halteres e Polia): movimento vertical, mas **isolado** —
  só dorsal, sem flexão de cotovelo, sem trabalho escapular

**Implicação clínica**: a substituibilidade de Pullover por puxada
completa depende do nível.

- **No nível do treino**: Pullover + 2 remadas dentro de um mesmo
  treino é distribuição válida. Remadas já cobrem romboides, trapézio
  médio e bíceps via flexão de cotovelo + retração escapular — o
  "vertical isolado" do Pullover complementa sem deixar nada órfão.
- **No nível da rotina**: se a rotina inteira (todos os treinos
  somados) tem só Pullover como "vertical de costas" e nenhuma puxada
  multi-articular real, isso é ruim. O aluno passa o microciclo sem
  trabalhar o padrão vertical completo. **Caso real (Rotina 1, Variante
  B 2x)**: T1 + T2 não tiveram nenhuma puxada multi-articular, só
  Pullover Polia em T2.

**Implicação pro modelo**: padrão sozinho não captura função clínica.
Precisa de algum eixo adicional — tipo `função_dominante` =
{multi_articular, lat_isolation, scapula_focused, ...} — pra
diferenciar membros dentro do mesmo padrão. **A constraint resultante
("≥1 puxada multi-articular") é de ROTINA, não de TREINO** — vários
conceitos clínicos vivem nesse nível agregado, e o motor declarativo
(Conceito 12) precisa expressar restrições de rotina como cidadãs de
primeira classe, lado a lado com as de treino e de bloco.

### Conceito 4 — Frequência típica vs regra absoluta

Pra alguns padrões/perfis, existe um default forte que deveria
**dominar a maioria das gerações**, com exceções permitidas em
frequência baixa.

**Exemplo — peito 2 vagas, perfil modal:**
| Combinação | Frequência esperada |
|---|---|
| Supino + Isolado | alta (típica) |
| Supino + Apoio | alta (típica) |
| Apoio + Isolado | baixa (válida, não default) |

**Exemplo — ombro 1 vaga, perfil modal:**
- Desenvolvimento (composto) = padrão dominante esperado
- Elevação Frontal/Lateral isolada como única opção = baixa frequência
  esperada
- Calibração atual do carve-out (70/30 composto/isolado) pode estar
  super-amostrando isolado.

**Implicação pro modelo**: o sistema deveria **amostrar uma
distribuição de padrões típicos com pesos**, não tratar todas as
combinações válidas como igualmente prováveis.

→ Conecta diretamente com o roadmap **centralidade** (sessão de
2026-05-18). Centralidade dentro da família é um caso particular de
"frequência típica" no nível de NOME; este conceito generaliza pra
COMBINAÇÕES e PADRÕES também.

### Conceito 5 — Combinação a nível de rotina (multi-bloco)

Quando uma subregião tem múltiplos slots na mesma rotina (ex: costas
com 3 slots em T2), a combinação deve atender critérios de
**diversidade no nível da subregião inteira**, não só par-a-par.

**Critérios identificados:**
- Mix de **vertical + horizontal** de movimento
- Variação de **pegadas** (supinada + aberta + neutra + pronada
  conforme aplicável)
- Provavelmente outros (a investigar com mais rotinas)

**Caso positivo (Rotina 3)**: Barra Fixa + Puxada Supinada + Remada
Curvada Halteres em T2 → 2 verticais + 1 horizontal, 3 pegadas
diferentes (aberta + supinada + pronada) → ótima diversidade.

**Caso negativo (Rotina 1)**: Remada Curvada Smith + Serrote Aberto +
Pullover Polia em T2 → 2 remadas + 1 pullover isolado, 0 puxada
vertical completa. Movimento vertical real ausente da rotina toda.

**Implicação pro modelo**: hoje a proximidade é avaliada par-a-par
(INTRA local). Falta **policiamento positivo** no nível da subregião
inteira garantindo diversidade. Solução natural = constraint global,
não local.

### Conceito 6 — Balanço de carga acumulada em pares de bloco

Exercícios têm "cargas" implícitas em múltiplos eixos (core/lombar,
ombro estabilizador, sistema nervoso, etc.). Pares de bloco devem
**balancear**, não somar.

**Caso negativo (Rotina 3 T2)**: Remada Curvada Halteres + Agachamento
Smith.
- Smith é agachamento → exige core (lombar+abdomen)
- Remada Curvada → exige core também
- Par = double core demand

**Soluções que o usuário apontou:**
- Trocar Smith por Goblet (menos core demand)
- Parear Remada com Recuo do Estepe (mais equilibrado)

**Estado atual do sistema**: XLSX tem campo `demanda_core` (valores
0-3) mas **não usa na lógica de pareamento**. Feature pré-cadastrada
mas inativa.

**Implicação pro modelo**: pareamento dentro de bloco deve considerar
soma das cargas implícitas. Possíveis eixos: core/lombar, ombro
estabilizador, exigência neural, fadiga global.

### Conceito 7 — Vaga única tem que ser principal/composto

Quando uma região/subregião tem **só 1 slot** na rotina, esse slot
quase nunca deveria ser um exercício isolado.

**Caso negativo (Rotina 1 Var.A, T2)**: único exercício de coxa do
treino era Cadeira Extensora (isolado). *"Se for pra deixar 1
exercício de coxa, esse único quase nunca seria Cadeira Extensora."*

Relaciona com Conceitos 1 (tier) e 4 (frequência) mas é uma regra mais
forte e diretamente acionável: **N=1 slot ⇒ exigir composto/principal**.

### Conceito 8 — Cobertura muscular implícita dos compostos

Exercícios compostos recrutam músculos além do alvo nominal. Isso deve
contar na **cobertura muscular** da rotina, não só a contagem de slots.

**Caso (Rotina 1 Var.A, T2)**: glúteo ficou fraco porque o único
exercício de coxa era isolado (Cadeira Extensora não pega glúteo). Se
fosse um composto de coxa (que *"quase sempre trabalha glúteo junto"*),
complementar com Side Clams + Ponte seria aceitável.

**Implicação pro modelo**: "demanda" não é só contagem de slots por
grupo. Um composto de coxa cobre glúteo implicitamente; o sistema
deveria saber disso ao avaliar se a rotina cobre glúteo. Precisa de
**mapa de recrutamento muscular** (primário + secundários) por
exercício, não só `musculo_primario` textual.

### Conceito 9 — Distribuição entre treinos da rotina (múltiplos eixos)

Numa rotina multi-treino (ex: 3 full body com viés), propriedades
importantes devem ser **distribuídas entre os treinos**, não
concentradas em um só.

**Eixos identificados:**
- **Força/tier**: não concentrar 2 pernas fortes em T3 e deixar T2 só
  com isolado (caso real Rotina 1 Var.A — solução: trocar Cadeira
  Extensora do T2 com Smith/Step Up do T3)
- **Tipo de movimento**: os 2 verticais de costas (puxadas)
  concentraram em T3; T1 e T2 só com remadas. Vertical/horizontal
  deveria distribuir (caso real Rotina 1 Var.A)
- Provavelmente outros (a investigar)

**Nuance**: com N treinos repetindo grupos musculares, *"não tem como
esperar 3 treinos muito fortes em todas as áreas"* — há rotação de
ênfase esperada (o "viés" da Variante A). Distribuir ≠ igualar; é
espalhar pra nenhum treino ficar órfão de uma propriedade.

### Conceito 10 — Proporção e variedade esperadas por região

Cada região tem uma **proporção típica composto:isolado** e desvios em
qualquer direção soam errados:
- Peito 3 vagas, 0 isolado = atípico (*"provavelmente teria inserido
  um isolado, não sempre mas muitas vezes"*)
- Braço 2 isolados de 8 = atípico no outro extremo (Lente A Var.B)

**Variedade tem múltiplos eixos** — não só composto/isolado:
- composto / isolado
- **unilateral / bilateral** (2 desenvolvimentos de ombro foi tolerável
  porque um era unilateral — Landmine — *"dá variedade interessante"*)
- tipo de movimento
- pegada
- posição

**Implicação pro modelo**: variedade/redundância precisa ser avaliada
em vários eixos simultâneos, não num só.

### Conceito 11 — Sub-propriedades de ênfase não capturadas (reforça 3)

`empurrar_compostos` é heterogêneo igual `puxadas` e `core`. Tem
pressing chest-dominant (Supino/Apoio normais) e triceps-dominant
(Supino Fechado, Apoio Fechado, Supino com Anilha).

**Caso (Rotina 1 Var.A)**: Apoio Fechado (T1) ≈ Supino com Anilha (T3)
— ambos pegada fechada, ênfase tríceps. Redundância **cross-treino**
que o scoring INTER **não pegou**, porque a propriedade compartilhada
(ênfase tríceps / pegada fechada) **não tem tag no banco** (pegada só
tem aberta/neutra/pronada/supinada — não "fechada").

**Diagnóstico técnico**: o mecanismo de evitar repetição entre treinos
existe, mas é cego pra propriedades não-tagueadas. Tag ausente =
proximidade invisível.

**Implicação pro modelo**: padrões precisam de sub-classificação por
**ênfase muscular / função**, não só por movimento. Vale pra:
- `empurrar_compostos`: chest-dominant vs triceps-dominant
- `puxadas`: vertical completo vs lat-isolation (Pullover — Conceito 3)
- `core`: flexão quadril / flexão tronco / anti-extensão / anti-rotação,
  por posição (supino/prancha/...) — ver Conceito 3 reforçado abaixo

### Conceito 3 reforçado — CORE é fortemente heterogêneo

Além de `puxadas` e `empurrar_compostos`, `core` precisa de
sub-classificação fina. Redundâncias que o sistema não pegou (Rotina 1
Var.A):
- T1: Canoinha + Infra Chão (ambos flexão de quadril; Canoinha ainda
  soma movimento de tronco)
- T3: Dead Bug + Hollow Hold (ambos supino, anti-extensão, uso
  muscular parecido)

**Eixos de variação de core citados pelo usuário:**
- flexão de quadril vs não (Infra tem; crunch não)
- movimento de tronco vs não
- posição (supino / prancha / em pé / ...)
- uso muscular dominante

*"Abdominal pede variedade."* A refatoração CORE da Etapa 8 (padrões
flexao_tronco/flexao_quadril/etc) é um começo, mas claramente não está
prevenindo essas redundâncias na prática.

**Achado contundente (Rotina 2 Var.A)**: o eixo de classificação está
ERRADO, não ausente. Dados reais:

```
Dead Bug        | padrao=flexao_quadril  | purpose=stability
Hollow Hold     | padrao=flexao_tronco   | purpose=stability
Abd Bicicleta   | padrao=flexao_tronco   | purpose=isolation
Infra Alternado | padrao=flexao_quadril  | purpose=isolation
```

O sistema acha que Dead Bug ≠ Hollow (padrões diferentes) → coloca
juntos achando que diversificou. Mas o usuário vê os dois como
"supino + anti-extensão + uso muscular parecido". Mesma coisa com
Abd Bicicleta + Infra ("ambos flexão de quadril alternada"). →
**a tag de padrão CORE não bate com a percepção clínica de
semelhança.** Eixos clínicos reais: posição + padrão de movimento +
tipo de execução (alternado/bilateral/estático).

### Conceito 12 — Seleção e arranjo são INSEPARÁVEIS (meta-arquitetural)

Citação do usuário (2026-05-19):

> *"Para encontrar o melhor par, às vezes o exercício não vai ficar na
> melhor posição. Por isso, o ideal não é selecionar o pool e depois
> ter que trabalhar com os exercícios escolhidos sem poder trocá-los.
> O personal nunca pensa assim de forma fixa."*

É o defeito de design central do motor atual, dito em linguagem
clínica. O sistema hoje: (1) seleciona o pool, (2) arruma em blocos
sem poder trocar os escolhidos. Daí a tensão: Goblet foi pro bloco A
(cedo) porque calhou de parear bem com a Remada — não porque deveria
vir cedo.

**A decisão de QUAL exercício e a decisão de ONDE ele vai têm que ser
tomadas JUNTAS**, não em fases separadas e irreversíveis. É o argumento
do CSP/ILP (decisão global) traduzido pra clínica — e a confirmação
mais forte, vinda espontaneamente do usuário, de que o problema é
arquitetural.

**Corolário — papel é contextual** (refina Conceitos 1/7): Cadeira
Extensora como finisher depois de Terra+Passada = OK (Rotina 2 T2);
como ÚNICO de coxa = ruim (Rotina 1 T2). Mesmo exercício, papéis
opostos. Tier/papel não é fixo no exercício — depende do conjunto do
treino, o que reforça que escolha+arranjo são inseparáveis.

### Conceito 9 refinado² — distribuição pondera intervalos de descanso

Além de força e tipo de movimento, a distribuição entre treinos deve
considerar o **gap temporal do ciclo**. Ex seg/qua/sex: T3→T1 tem o
maior intervalo (fim de semana), T1→T2 o menor. Logo, 2 estímulos
similares (2 remadas) em T1+T2 (próximos) é pior que espaçá-los.
Distribuir ≠ "espalhar igual"; é "espalhar ponderando os gaps".

**Viés sistemático de ombro** (Rotinas 1 e 2 Var.A): ombro caiu em
desenvolvimento nas 2× que apareceu na rotina, 0 elevação/posterior.
Carve-out 70/30 aplicado 2× independente → ~49% de 2 compostos.
Quando um grupo aparece em múltiplos treinos, o TIPO deveria variar
(coordenação entre treinos, não sorteio independente). Tensão: usuário
quer `posterior_ombro` disponível, mas carve-out de 2026-05-18 o
excluiu ("específico demais") — exclusão talvez prematura.

---

## Coisas que o sistema acertou (não quebrar no refator)

Capturado pra evitar que o refator regrida em pontos que já funcionam:

- **Pares composto → isolado dentro de subregião**: Stiff Uni →
  Cadeira Flexora; Tríceps Francês + Side Clams; Stiff Livre + Flexão
  Joelhos (Var.A T1, "excelente")
- **Acessórios genuínos no final**: abdução, abdominais, panturrilha
  como complementos no terceiro/quarto bloco
- **Diversidade vert+horiz+pegada em costas (Var.B Rotina 3)**: emergiu
  organicamente, deveria ser PROJETADA não acidental
- **Empurrar + Posterior pareados em mesmo treino**: combina
  naturalmente (confirma rationale da Variante B)
- **Puxar + Anterior pareados em mesmo treino**: idem
- **Agachamento Livre como abertura (Var.A T1)**: principal pesado
  abrindo o treino, correto
- **Variedade por unilateralidade**: Desenv. Landmine unilateral
  mitigou a repetição de 2 desenvolvimentos de ombro

---

## Calibrações mal-ajustadas observadas

- **Carve-out ombro 1 vaga: 70% composto / 30% isolado** (sessão de
  2026-05-18). Sinal da entrevista sugere 30% isolado é frequência
  alta demais pro perfil modal. Refinar quando o modelo de "frequência
  típica" (Conceito 4) for definido.
- **Apoio como opener de peito**: 2 das 3 rotinas tiveram Apoio
  abrindo, contra a preferência de Supino. Distribuição interna do
  padrão `empurrar_compostos` parece sub-representar Supinos clássicos.
- **Goblet/acessório antes do principal**: 3 de 3 rotinas (Var.B) +
  reincidente na Var.A (Smith Rampa antes de Step Up). Tier-order não é
  enforçado em lugar nenhum.
- **Vaga única caindo em isolado**: Cadeira Extensora como único de
  coxa (Var.A T2). Viola Conceito 7.
- **Concentração de movimento**: 2 puxadas em T3 (Var.A), T1/T2 sem
  vertical. Viola Conceito 9.
- **Redundância de core não detectada**: Canoinha+Infra, Dead
  Bug+Hollow (Var.A). Viola Conceito 3 reforçado.
- **Redundância cross-treino de ênfase**: Apoio Fechado + Supino Anilha
  (Var.A). INTER cego por falta de tag (Conceito 11).

---

## Frases-âncora do usuário (literais, não traduzir indevidamente)

Manter essas frases visíveis pra resistir à tentação de "modelar"
elas em vocabulário técnico antes da hora.

- *"Em geral, o próprio exercício já tem uma classificação conhecida
  como principal ou acessório"*
- *"O tipo de aluno pode alterar essas condições"*
- *"O contexto da rotina também pode importar"*
- *"O tipo de pegada é MENOS importante do que a família específica"*
  (de turno anterior)
- *"Não deve acontecer"* (sobre rotina sem movimento vertical de costas)
- *"Não pode ser algo que domine a criação dos treinos"*
- *"Pode variar aleatoriamente ou também variar conforme tipo de aluno"*
- *"Pares com demanda mais equilibrada de core"*
- *"Pullover é vertical de costas mas é um isolado"*
- *"Puxadas exigem flexão de cotovelo e exigem mais da escápula
  também"*
- *"Se for pra deixar apenas 1 exercício de coxa, esse único exercício
  quase nunca seria cadeira extensora"*
- *"Um exercício composto de coxa quase sempre trabalha glúteo junto"*
- *"São 3 treinos que repetem os grupos musculares, então não tem como
  esperar 3 treinos muito fortes em todas as áreas"*
- *"Abdominal pede variedade"*
- *"Um desenvolvimento é unilateral, o que dá uma variedade
  interessante"*

---

## Conceitos ainda mal-formados ou parciais (pendências)

- **Perfil de aluno**: até agora apareceu como "iniciante / hipertrofia /
  saúde+emagrecimento / homem". Precisa de definição das **dimensões**
  (não só listar exemplos). Provavelmente vai sair quando avaliarmos
  rotinas pra alunos hipotéticos distintos.
- **Função clínica dentro do padrão** (Conceito 3): identifiquei que
  `puxadas` é heterogêneo. Provável que `empurrar_compostos`, `hinge`,
  outros também sejam. Mapear depois.
- **Cargas implícitas** (Conceito 6): identifiquei core/lombar. Provável
  que existam: ombro estabilizador, exigência neural, fadiga global.
  Mapear depois.
- **Como combinar Conceitos 1+2**: tier-order + tolerância a fadiga
  interagem. Como exatamente?

---

## Princípio metodológico — validação qualitativa + quantitativa

Observação levantada pelo usuário em 2026-05-19:

> *"O banco é grande e não tenho como avaliar se algum exercício ou
> grupo de exercícios está aparecendo demais ou de menos. Isso é
> trabalho estatístico mas talvez tenhamos que fazer para calibrar o
> novo refator do app."*

Essa entrevista de Lente A capturou bem **erros de combinação e
ordenação** (tier-order, par de core, falta de movimento vertical) —
sintomas que aparecem em **rotinas individuais**.

Mas existem vieses sistêmicos que **não são visíveis em 3 rotinas**:
aparição de exercícios específicos sub ou super-representados,
combinações de bloco que se repetem, exercícios "escondidos" pela
mecânica do gerador. Isso só aparece em N=1000+ rotinas.

**Implicação pra refator**: a validação do novo sistema precisa de
duas frentes complementares.

**Frente qualitativa (esta entrevista, Lente A/B/C):**
- Detecta combinações ruins, ordem errada, regras clínicas violadas
- Funciona em escala humana (poucas rotinas)
- Identifica o QUE deveria ser regra

**Frente quantitativa (tools/ existentes + extensões):**
- Detecta aparição estatística anômala (sub/super-representação)
- Identifica vieses sistêmicos invisíveis em escala humana
- Requer N=1000+ rotinas geradas
- Tools já existentes que servem de base:
  - `tools/analisar_remada_lm.py` — % de aparição de exs específicos
    com Wilson CI
  - `tools/analisar_vies_upper.py` — análise descritiva de viés por
    categoria
  - `tools/investigar_ordem_alocacao.py` — instrumentação de ordem
    de seleção

**Ferramenta que provavelmente precisa ser construída antes/durante
o refator: dashboard de calibração**, que rode N rotinas das
configurações comuns (`configuracoes_comuns.md`) e reporte:

- Frequência de aparição de cada exercício do banco
- Flag de exercícios fora do range esperado (sub-representação ou
  super-representação vs uniforme, ou vs target clínico se definido)
- Frequência de combinações de bloco mais comuns
- Aderência aos conceitos clínicos enumerados acima (ex: % de rotinas
  com pelo menos 1 movimento vertical de costas verdadeiro;
  tier-order respeitado em N% das rotinas; etc.)

Sem isso, não conseguimos saber se o refator está **resolvendo** os
problemas qualitativos sem **criar** novos vieses quantitativos.

---

## Próximos passos no roadmap da entrevista

1. ✅ Lente A com Variante B 2x semana (3 rotinas) — **feito 2026-05-19**
2. ✅ Lente A com Variante A 3x semana / `upper(3)+lower(3)+core(2)`
   (1 rotina) — **feito 2026-05-19** — emergiram Conceitos 7-11 +
   reforço do 3 (core) e do 9 (distribuição multi-eixo)
3. ⏳ Conversa de síntese pendente (usuário pediu antes de seguir)
4. ✅ Vetor de perfil de aluno extraído via entrevista (2026-05-21) —
   ver seção "Perfil de aluno — vetor de 4 dimensões" abaixo. Substitui
   a abordagem de "rascunhar 3 alunos hipotéticos" por entrevista com 3
   alunos contrastantes reais.
5. ⏳ Esboço do dashboard de calibração quantitativa (frente
   complementar à entrevista) — extensão dos tools existentes pra
   medir aderência aos conceitos enumerados aqui

---

## Perfil de aluno — vetor de 4 dimensões

> **Origem**: entrevista guiada de 2026-05-21 com 3 alunos reais contrastantes (Fernanda força/hipertrofia, Turma das 7h metabólica em grupo, perfil saúde/condicionamento geral). Resolve a pendência #4 do roadmap.

### Estrutura

O perfil do aluno é um **vetor de 4 dimensões ortogonais**:

#### 1. Nível técnico (1/2/3)

Filtra o pool de exercícios viáveis por `complexidade` antes do motor entrar. Não modula pesos — é hard.

- **Nível 1** (iniciante): teto técnico baixo. Exercícios de baixa complexidade. Pareamento liberal (agachamento bilateral pode pareado, porque sem peso pesado).
- **Nível 2** (intermediário): teto técnico médio. Barra livre e variedade entram no pool. Carga prevista é decisão separada do filtro — um intermediário aceita exercício complexo mas não necessariamente com peso pesado.
- **Nível 3** (avançado): sem teto técnico. Qualquer exercício pode entrar. Carga depende do objetivo (vetor + contexto), não do nível.

**Insight da sessão**: nível e carga são ortogonais. Nível filtra o pool técnico; intenção de uso (carga, proximidade da falha) é decisão das outras dimensões + contexto da rotina.

#### 2. Centralidade dos compostos pesados (alta/média/baixa)

Quão "estrelas" são os compostos básicos (terra, agachamento, supino, etc.) na rotina.

- **Alta**: compostos são objetivo de progressão; protegidos contra substituição; ativam constraint hard de cobertura e bloco solo.
- **Média**: bem-vindos mas não centrais.
- **Baixa**: exercícios entre outros, sem proteção especial.

#### 3. Densidade de pareamento (alta/média/baixa)

Quão "denso" é o desenho dos blocos.

- **Alta**: bi-sets/tri-sets agressivos, pode parear agonistas, blocos grandes (turma 7h, formato quase-circuito).
- **Média**: pareamentos limpos, antagonistas/distantes (saúde).
- **Baixa**: tolerância a blocos solo, pareamento conservador (Fernanda quando treinando força).

#### 4. Aderência ao tier (alta/média/baixa)

Quanto a rotina protege exercícios de tier alto contra substituição por tier mais baixo.

- **Alta**: mantém-se no núcleo da família (Supino Barra/Halteres OK, Apoio não).
- **Baixa**: tolera periferia da família (Apoio, Crossover OK).

**Importante**: funde com o roadmap de "centralidade dentro da família" de 2026-05-18 — é a mesma dimensão olhada pelo lado do aluno. Centralidade dentro da família ≡ tier alto dentro da família.

### Tabela de referência (3 alunos contrastantes)

| | Nível técnico | Centralidade compostos | Densidade pareamento | Aderência ao tier |
|---|---|---|---|---|
| **Fernanda** (força/hipertrofia) | 3 | Alta | Baixa | Alta |
| **Turma 7h** (metabólica em grupo) | 2-3 | Baixa | Alta | Baixa |
| **Saúde** (condicionamento geral) | 1-2 | Média | Média | Média |

### Decisão arquitetural — presets, sliders, override

Vetor é representação **interna**, não interface:

- **Presets nomeados** ("Força/hipertrofia clássico", "Metabólico em grupo", "Saúde geral", etc.) correspondem a vetores comuns. Tu escolhe um preset por aluno.
- **Tweak fino** disponível atrás de botão "personalizar" pros casos de cauda (ex: aluno força que gosta de variedade alta).
- **Override por geração** — flag manual na hora de gerar uma rotina sobrepõe o vetor do aluno só pra essa geração específica. Útil pra casos pontuais (Fernanda quer fazer um treino metabólico antes da viagem). Não persiste, não vira novo perfil.

### Como o vetor afeta o motor

Duas formas distintas:

- **Filtro hard (Nível técnico)** — filtra o pool antes do solver começar. Exercício com complexidade acima do teto do aluno não entra.
- **Modulador de peso (3 outras dimensões)** — multiplica o peso de constraints soft específicas na função objetivo. Detalhamento em `catalogo_constraints.md` (passo 2 do fluxo).

### Princípio do "papel é contextual" (revalidação do Conceito 12)

A entrevista revalidou o Conceito 12 num caso prático específico:

- Terra com **Fernanda** (Nível 3 + Centralidade Alta + Aderência Alta) vira bloco solo
- Terra com **turma 7h** (mesmo Nível 3, mas Centralidade Baixa + Densidade Alta) pode ser pareado em tri-set metabólico

**Não é o exercício que tem demanda neural alta — é a intersecção tier do exercício × vetor do aluno**. Implementado como constraint hard derivada (tier Principal + Centralidade Alta + Aderência Alta → bloco solo), em vez de coluna `demanda_neural` fixa no XLSX.

### Pendências do perfil

- **Restrições físicas/dor** ainda não modeladas. Direcionamento: filtros hard sobre pool por aluno (lista de exercícios proibidos / padrões a evitar por causa de lesão), separados do vetor. Discutir em sessão futura.

---

*Última atualização: 2026-05-21 (vetor de perfil de aluno de 4 dimensões
extraído via entrevista com 3 alunos contrastantes reais — nova seção
"Perfil de aluno — vetor de 4 dimensões"; pendência #4 do roadmap marcada
concluída). Atualizar este doc a cada sessão de avaliação que produzir
refinamento ou conceito novo.*
