# Princípios Clínicos do Gerador — documento de trabalho

> **STATUS: RASCUNHO MUTÁVEL.** Compilado durante entrevista guiada
> com o personal trainer (Bernardo) em 2026-05-19, **Lente A** (caso a
> caso) sobre 3 rotinas da Variante B 2x/semana. Conceitos podem ser
> revisados, refinados, divididos, fundidos ou descartados conforme
> avaliação de mais rotinas e configurações.
>
> **Propósito**: capturar a lógica clínica que hoje está implícita no
> greedy + scoring + carve-outs e tornar explícita em texto, sem
> vocabulário técnico do app. Base para decisão estrutural do refator
> (ver `handoff_2026-05-19_decisao_refator.md`).

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

**Implicação clínica**: Pullover NÃO substitui uma puxada completa.
Uma rotina com Pullover + 2 Remadas ainda fica sem "movimento vertical
de costas verdadeiro" (caso real da Rotina 1).

**Implicação pro modelo**: padrão sozinho não captura função clínica.
Precisa de algum eixo adicional — tipo `função_dominante` =
{multi_articular, lat_isolation, scapula_focused, ...} — pra
diferenciar membros dentro do mesmo padrão.

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
4. ⏳ Avaliar perfis de aluno distintos pra extrair as dimensões do
   override 1 do Conceito 1
5. ⏳ Esboço do dashboard de calibração quantitativa (frente
   complementar à entrevista) — extensão dos tools existentes pra
   medir aderência aos conceitos enumerados aqui

---

*Última atualização: 2026-05-19 (criação inicial + princípio
metodológico qualitativo+quantitativo). Atualizar este doc a cada
sessão de avaliação que produzir refinamento ou conceito novo.*
