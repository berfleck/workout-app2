# Visão da próxima fase: tags multi-dimensionais + penalidades

> Documento de referência sobre a evolução arquitetural do gerador de treinos.
> Captura conversa entre Bernardo e Claude sobre como tornar a seleção de
> exercícios mais inteligente, simulando o raciocínio de um personal trainer.

---

## Por que essa mudança

O app atual funciona com **filtros + escolha aleatória**: aplica regras hard (padrão, equipamento, complexidade, variacao_de, etc), e depois faz `random.choice` entre os candidatos que sobraram. Isso tem dois limites:

1. **Não captura "preferências"** — só sabe bloquear ou permitir. Não sabe dizer "prefiro X mas aceito Y se X não der".
2. **Não escala para múltiplos critérios** — adicionar 5-10 regras novas (carga lombar, grip, ângulo, nível do aluno, explosividade) com a arquitetura atual vira sopa de filtros conflitando.

A solução é mover de **filtros + sorteio** para **filtros + ranking por penalidade**, alimentado por um vocabulário rico de tags no banco.

---

## Arquitetura em duas camadas

A mudança envolve duas peças que se complementam:

### Camada 1 — Vocabulário (banco de exercícios)

Novas colunas no `banco_exercicios.xlsx` que descrevem dimensões de proximidade entre exercícios. Cada coluna captura **uma** dimensão.

Exemplos prováveis (a serem confirmados na listagem dos casos):

- `tag_angulo`: `reto | inclinado | declinado`
- `tag_equipamento`: `barra | halter | polia | maquina | smith | corporal | trx`
- `tag_estabilidade`: `livre | guiado`
- `tag_lateralidade`: já existe como `unilateral` no banco
- (futuro) `carga_lombar`: 0 / 1 / 2
- (futuro) `carga_grip`: 0 / 1 / 2
- (futuro) `carga_core`: 0 / 1 / 2
- (futuro) `nivel_min`: iniciante / intermediario / avancado

**Regras de preenchimento**:

- Tag vazia significa "essa dimensão não se aplica" — não gera conflito com nenhum outro exercício. Só preencha onde a dimensão discrimina entre exercícios próximos.
- Valores de cada coluna formam uma lista fechada (definida antes do preenchimento), tudo lowercase sem acentos, pra evitar inconsistências de capitalização.
- Cada exercício recebe valor em zero, uma ou várias colunas — o que fizer sentido pra ele.

### Camada 2 — Decisão (gerador de treino)

Cada candidato a ser selecionado passa por um cálculo de **penalidade total**. O gerador escolhe o de menor penalidade em vez de fazer `random.choice`.

Penalidades funcionam em **escalões de magnitude** pra preservar prioridades:

```
+1000  Mesma família (variacao_de) já usada na rotina
  +50  Carga lombar somada > limite
  +10  Mesma tag_angulo já usada na rotina (dimensão importante)
   +3  Mesma tag_equipamento já usada na rotina (dimensão menos importante)
   +1  Mesma similaridade já usada na rotina (genérico)
```

A diferença de magnitude (1000 vs 10 vs 3 vs 1) garante que regras importantes nunca são "compensadas" por regras menos importantes — você pode ter 100 conflitos de equipamento e ainda assim a família vai pesar mais. Mas **se a única alternativa restante tem +1000, o gerador aceita** (porque é melhor que não preencher a demanda).

Os pesos viram constantes no código (`PESO_TAG_ANGULO = 10`, etc) e são fáceis de ajustar.

---

## Como tags e penalidades se relacionam

Tags são vocabulário. Penalidades são gramática. Uma sem a outra não funciona:

- **Sem tags**: penalidades não têm o que comparar
- **Sem penalidades**: tags ficam só descritivas e o gerador não sabe usar

Toda nova "regra fisiológica" que o app for ganhar no futuro segue o mesmo padrão:

1. Adicionar coluna no banco que descreve o atributo
2. Preencher pros exercícios afetados (pode deixar vazio onde não se aplica)
3. Adicionar parcela de penalidade no gerador, com peso apropriado

Isso mantém a arquitetura estável conforme as regras crescem. Sem isso, cada nova regra é um filtro novo que conflita com os outros.

---

## Tags conjuntas vs colunas separadas — decisão tomada

Foi avaliado se o banco deveria ter **uma coluna com múltiplas tags** (ex: `tags_movimento = "reto;barra"`) ou **colunas separadas por dimensão**. Decisão: **colunas separadas**.

Razões:

1. **Pesos diferentes por dimensão**: tags conjuntas não permitem dizer "ângulo pesa mais que equipamento". Colunas separadas permitem.
2. **Adicionar/remover dimensões**: com colunas separadas, é só adicionar coluna nova. Com tags conjuntas, viraria reescrita.
3. **Preencher é mais natural**: olhar pra um exercício e pensar "qual o ângulo? qual o equipamento?" funciona melhor que "que tags eu coloco?".
4. **Auditoria fica fácil**: olhando a planilha com colunas separadas, dá pra ver inconsistências na hora.

---

## Hierarquia de granularidade no banco

A coluna `variacao_de` continua existindo, mas com semântica mais clara que coexiste com as tags novas. A hierarquia de proximidade fica:

| Camada | Granularidade | Tratamento intra-treino | Tratamento inter-treino |
|---|---|---|---|
| `nome` | Exercício individual | Hard block | Hard block |
| `variacao_de` | Família mecânica idêntica | Hard block | Hard block (penalidade muito alta, ~1000) |
| `tags_*` (novas) | Dimensões de proximidade | Hard block (combinado) | Penalidade média (3-50, depende da tag) |
| `similaridade` | Categoria genérica | Penalidade leve | Penalidade leve |

**Caso prático que ilustra a diferença `variacao_de` vs `tags_*`**:

- Crossover ↔ Crossover Sentado: mesma família mecânica idêntica → `variacao_de = "crossover"` em ambos. Bloqueio forte.
- Flexão Slideboard ↔ Flexão Feijão: movimento idêntico, mas exercícios distinguíveis → mesmas tags em todas as dimensões relevantes (`tag_equipamento`, etc), mas `variacao_de` diferentes. Penalidade alta inter-treino, mas aceitável se for a única alternativa.
- Cadeira Flexora ↔ Flexão Slideboard: mesmo padrão (knee_flexion), mas dimensões diferentes (equipamento, mecânica) → poucas ou nenhuma tag em comum, penalidade baixa, fácil de coexistirem na rotina.

---

## Tag vazia: comportamento

Vazio significa "essa dimensão não se aplica a esse exercício". Regra de comparação:

```python
def conflito_tag(ex1_tag, ex2_tag):
    if not ex1_tag or not ex2_tag:
        return False
    return ex1_tag == ex2_tag
```

Não preencher uma tag pra um exercício é **decisão válida e esperada**. Cada coluna só precisa estar preenchida onde discrimina entre exercícios próximos. Exemplos:

- `tag_angulo`: só se preenche em supinos, puxadas, remadas, etc onde "reto/inclinado" é distinção real. Pra leg press fica vazio.
- `tag_estabilidade`: só onde livre vs guiado importa (agachamento, supino livre vs smith). Pra isolamento de braço fica vazio.

---

## Plano de migração — etapas

A ordem importa. Cada etapa depende da anterior.

**Etapa 1 — Patch atual** (em andamento)
- Fix do bug `variacao_pais` em `gerar_multiplos_treinos`
- Modal de avisos de demanda incompleta
- Já documentado em prompt separado pro Claude Code

**Etapa 2 — Listar 8-12 casos de proximidade do banco**
- Trabalho de personal trainer, não de código
- Pra cada grupo de exercícios próximos, identificar quais dimensões definem a proximidade
- Exemplos a investigar: variantes de supino, remada baixa, extensão de tríceps, elevação lateral, stiff, agachamento, flexão de joelhos
- Resultado esperado: lista de casos com dimensões que se repetem (universais) e específicas

**Etapa 3 — Definir vocabulário das colunas**
- A partir dos casos da etapa 2, decidir quais colunas criar
- Pra cada coluna, definir lista fechada de valores possíveis
- Definir pesos relativos (peso do ângulo > peso do equipamento, etc)
- Documentar regras de preenchimento

**Etapa 4 — Migrar o banco**
- Preencher as colunas novas pros exercícios existentes
- Pode deixar vazio onde não se aplica
- Validar consistência (nenhum valor fora da lista fechada)
- Etapa demorada não pelo volume mas pela atenção

**Etapa 5 — Refatorar o gerador para penalidades**
- Substituir `random.choice(elegiveis)` por `escolher_por_penalidade(elegiveis, contexto)`
- Função `calcular_penalidade(candidato, exercicios_ja_usados)` soma penalidades parciais
- A função de escolha **mantém aleatoriedade**: identifica o tier de menor penalidade e sorteia dentro dele (ver seção "Variabilidade preservada" abaixo)
- Adicionar testes que cobrem cenários conhecidos
- Outras regras futuras (lombar, grip, nível) entram pelo mesmo mecanismo, sem refatoração nova

---

## Variabilidade preservada — não é "escolher o melhor"

Ponto importante levantado em conversa: tirar o `random.choice` poderia tornar o gerador determinístico e sempre escolher os mesmos exercícios "campeões de penalidade baixa". Isso seria regresso, não avanço — variabilidade entre treinos é parte do valor do app.

A solução é não escolher o melhor: é **sortear entre os melhores**.

```python
def escolher_por_penalidade(candidatos, contexto, margem=5):
    com_penalidade = [(ex, calcular_penalidade(ex, contexto)) for ex in candidatos]
    min_pen = min(p for _, p in com_penalidade)
    melhores = [ex for ex, p in com_penalidade if p <= min_pen + margem]
    return random.choice(melhores)
```

Comportamento por cenário:

| Cenário | Comportamento |
|---|---|
| Vários candidatos sem conflito (penalidade 0) | Sorteia entre todos — variabilidade total |
| Alguns candidatos melhores que outros | Sorteia entre os do tier de melhor qualidade |
| Apenas 1 candidato bom, resto ruim | Sempre pega o bom |
| Só sobrou candidato ruim | Pega o que tem (nunca trava) |

A `margem` controla quão estrito é o ranking. Valor inicial sugerido: 5. Pode ser ajustado conforme observação do comportamento real.

**Risco residual**: alguns exercícios podem ter penalidades estruturalmente altas e nunca serem escolhidos. Isso é sintoma de cadastro inconsistente ou de exercícios genuinamente raros (ex: Apoio Ajoelhado pra avançados, que faz sentido nunca aparecer). Solução: rodar simulação periódica que conta aparições por exercício; investigar os com 0 aparições.

---

## Por que essa ordem (dados → motor, não motor → dados)

Foi avaliado fazer a refatoração do gerador antes de preencher o banco. Decisão: **dados primeiro, motor depois**.

Razões:

1. **Risco de subdimensionar o motor**: projetar as penalidades sem ver os casos reais leva a um motor que não captura tudo que é necessário. Os casos da etapa 2 vão expor dimensões que não foram previstas.
2. **Refatorar duas vezes é caro**: se o motor é refeito antes de saber as colunas finais, ele provavelmente vai precisar ser refeito de novo quando as colunas chegarem.
3. **Dados primeiro permite testar com cenários reais**: depois das etapas 2-4, dá pra escrever testes de regressão concretos pro gerador.

---

## Estado atual do projeto (referência rápida)

**Bugs corrigidos** (etapa 1, em andamento no Claude Code):
- `variacao_pais_globais` agora recebe o pai (`ex.variacao_de`) em vez do nome do filho
- Sessão ganha campo `avisos` com info sobre demandas não atendidas
- Modal no front exibe esses avisos quando rotina é gerada

**Bugs conhecidos ainda não tratados**:
- Checkbox "evitar similaridade" não funciona — flag é set, mas valor nunca é lido como filtro. Ver discussão original sobre `sims_globais` write-only.
- Inconsistências de capitalização no banco (alguns `variacao_de` em CapitalCase, outros em lowercase). Tratar como cleanup futuro.
- Nomes com espaço extra (`"Crossover "` vs `"Crossover"`). Cleanup futuro.

**Decisões de design já tomadas**:
- Colunas separadas por dimensão (não tags conjuntas)
- Pesos por dimensão são constantes no código, ajustáveis
- Tag vazia = "não se aplica" (não conflita com nada)
- Lista fechada de valores por coluna, lowercase sem acentos
- Hierarquia de granularidade: nome > variacao_de > tags > similaridade

**Decisões pendentes** (a tomar nas etapas 2-3):
- Quais colunas criar de fato
- Quais valores cada coluna aceita
- Pesos relativos das colunas
- Se alguma penalidade deve ser "absoluta" (tipo +1000) ou só "preferência forte" (tipo +50)

---

*Documento de visão. Revisar quando começar a etapa 2 da migração.*
