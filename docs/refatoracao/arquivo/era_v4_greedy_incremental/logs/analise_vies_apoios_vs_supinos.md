# Análise — viés Apoios vs Supinos no padrão `empurrar_compostos`

Data: 2026-05-18
Origem: investigação follow-up do relatório inicial `analise_vies_upper.md`.
Determinismo: rodado com `PYTHONHASHSEED=0` (sem isso, ordem de `set()` varia
e contagens marginais flutuam entre execuções — investigado antes desta análise).
Defaults: `relaxar_familia=True`, `historico_r1=None`, sem exercícios travados,
N=1000 iterações com seeds 1000..1999.

## Problema

O gerador atual produz uma rotina onde **Apoios dominam** o padrão
`empurrar_compostos` (peito composto) sobre Supinos. Variantes clinicamente
fundamentais como **Supino com Barra** quase nunca aparecem, mesmo estando
no banco e sendo elegíveis. O viés tem múltiplas camadas e piora em rotinas
de mais treinos.

## Configurações testadas

| Cenário | Treinos | Demandas por treino |
|---|---:|---|
| A. Baseline (relatório inicial) | 2 | `[("regiao","upper",4)]` |
| **B. Uso real** | 3 | `[("regiao","upper",3), ("regiao","lower",3), ("regiao","core",2)]` |
| C. Comparação | 2 | mesmas demandas de B |

## Resultados — slots de empurrar_compostos

| Métrica | A | **B (uso real)** | C |
|---|---:|---:|---:|
| Total slots empurrar_compostos | 2000 | 3000 | 2000 |
| **% Apoios** | 61.3% | **69.4%** | 64.5% |
| % Supinos (total) | 38.7% | 30.6% | 35.5% |
| **% Supino com Barra** | 3.8% | **0.6%** | 0.9% |
| Razão Apoios/Supinos | 1.58× | **2.27×** | 1.81× |

## Resultados — frequência por rotina

| Métrica | A | **B (uso real)** | C |
|---|---:|---:|---:|
| ≥1 Apoio em algum treino | 100.0% | 100.0% | 100.0% |
| ≥1 Supino em algum treino | 77.4% | 90.8% | 71.1% |
| **≥1 Supino com Barra** | 7.6% | **1.9%** | 1.9% |
| Só Apoios (zero Supinos na rotina) | 22.6% | 9.2% | 28.9% |

**Leitura clínica do cenário B:** em ~1 a cada 53 rotinas (1.9%) o aluno
vê Supino com Barra. Em ~1 a cada 11 rotinas (9.2%) o aluno não vê
nenhum Supino, só Apoios.

## Decomposição dentro de empurrar_compostos (cenário A, N=1000)

Slots T1 + T2 por exercício:

| Família | Exercício | Slots | % do padrão |
|---|---|---:|---:|
| Apoio | Apoio | 489 | 24.4% |
| Apoio | Apoio Ajoelhado | 412 | 20.6% |
| Apoio | Apoio Elevado | 325 | 16.2% |
| Apoio | Apoio Fechado (VP) | 0 | 0.0% |
| Supino Reto | Supino Com Anilha | 76 | 3.8% |
| Supino Reto | Supino Com Barra | 76 | 3.8% |
| Supino Reto | Supino Com Halteres | 0 | 0.0% |
| Supino Reto | Supino Fechado (VP) | 90 | 4.5% |
| Supino Inclinado | Supino Smith Inclinado | 259 | 13.0% |
| Supino Inclinado | Supino Inclinado Halteres | 273 | 13.7% |

Anomalias: Apoio Fechado e Supino Com Halteres em 0 absoluto; Supino Fechado
aparece **mais** que Supino com Barra (variação técnica > exercício básico).

## Diagnóstico de raíz

O score INTRA/INTER em `_score_proximidade` ([gerador_treino.py:2023](../../gerador_treino.py#L2023))
aplica penalty quando 2 exercícios no mesmo bloco/rotina compartilham tags
de proximidade. As tags atuais nos `empurrar_compostos`:

| Exercício | pegada | plano | eq_grupo |
|---|---|---|---|
| Apoio* | pronada | **`-`** | corporal |
| Supino Reto* | pronada | reto | barra/halter/`-` |
| Supino Inclinado* | pronada | inclinado | halter/barra_guiada |

Apoios têm **`plano="-"` (vazio → dim N/A no score, penalty 0)**. Supinos
têm `plano="reto/inclinado"` (penalty -50 entre exs com mesmo valor).
Resultado: Apoios são "invisíveis" à dim `plano_corporal` e ganham qualquer
disputa onde haja outro exercício com `plano` definido no bloco.

Sondagem confirmando (banco mutado in-memory, Apoios com `plano="reto"`):

| Família | Baseline | Apoios c/ plano=reto | Δ |
|---|---:|---:|---:|
| Apoio | 1226 | 1000 | **−18%** |
| Supino Reto | 242 | 257 | +6% |
| Supino Inclinado | 532 | 743 | **+40%** |

A mutação **funcionou parcialmente** — Apoios caíram, mas o ganho foi pra
Supino Inclinado (passa a ser o único "plano diferente" disponível), não pra
Supino Reto (que continua competindo consigo mesmo via família hard INTRA).
**Solução de só preencher tags é insuficiente.**

## Por que piora com mais treinos (cenário B)?

Em `upper(3)`, Hamilton dá peito=1 vaga por treino. Em 3 treinos = 3 slots
peito por rotina. Família INTRA é hard (1 família distinta por treino),
mas família INTER é soft com penalty atenuada (-12 quando família tem 4
filhos). Como **Apoios têm tags neutras (`plano="-"`)**, repetir família
Apoio em 3 treinos diferentes só acumula penalty leve (-12 família INTER
× 2 pares = -24). Repetir Supinos acumula penalty `plano` (-40 atenuado a
-32 INTER) + família + eq_grupo. Score total prefere "Apoio+Apoio+Apoio"
sobre "Apoio+Supino+Supino" em rotinas multi-treino.

**Quanto mais treinos, mais pares cumulativos, mais Apoios dominam.**

## Anomalias específicas

**Supino com Halteres = 0 em todos os cenários:** mesma família que Anilha
(76) e Barra (76), não é variante_pontual. Provável causa: `eq_grupo=halter`
colide via INTER (penalty -4) com Supino Inclinado Halteres (também halter)
ou outros exercícios upper com mesmo grupo, deslocando Halteres
sistematicamente. Vale investigar separado.

**Apoio Fechado = 0:** `variante_pontual=True` é hard INTRA. Bloqueado
sempre que há outro `empurrar_compostos` no mesmo treino — em upper(4)/upper(3)
sempre há. Comportamento desejado.

## Opções de solução algorítmica (além da UI de exercícios fixos)

Opções discutidas a seguir não são mutuamente exclusivas. Cada uma tem
tradeoff diferente.

### Opção 1 — Recodificar tags faltantes como classes próprias

Em vez de `plano="-"` (= dim N/A, sem penalty), criar valores explícitos:
`plano="corporal_horizontal"` nos Apoios, `eq_grupo="corporal"` mantém.
Score INTRA passa a penalizar 2 Apoios juntos no mesmo bloco — exatamente
como já penaliza 2 Supinos juntos. Apoio + Supino fica neutro (planos
diferentes).

**Prós:** filosoficamente correto (tag faltante é dado faltante, não classe);
correção pontual no XLSX; algoritmo já está pronto pra ler.

**Contras:** aumenta penalty intra-Apoios → menos Apoios juntos em rotinas
multi-treino, mas como Apoio é família dominante hoje, pode causar
Apoios=Supinos só em volume sem mover Supino com Barra individualmente
(o problema dentro da família Supino Reto permanece — Anilha e Barra
empatados sem critério).

**Esforço:** baixo (1 commit XLSX), risco médio (afeta outros padrões).

### Opção 2 — Sorteio ponderado por essencialidade

Adicionar coluna `prioridade` (float, default 1.0) no XLSX. Trocar
`random.choice(pool)` por `random.choices(pool, weights=...)` no caminho
de seleção. PT define: Supino com Barra=2.0, Apoio=1.0, Apoio Ajoelhado=0.7,
Apoio Fechado=0.3, etc.

**Prós:** controle granular pelo PT, intuitivo, expressivo. Resolve o
problema dentro da família (Supino com Barra > Anilha > Halteres > Fechado).
Não muda lógica de score — só altera distribuição do sorteio final.

**Contras:** novo campo a manter (~140 exercícios pra calibrar); risco
de "engenharia social" (PT vieses pessoais sobrepõem clínica); precisa
mexer no caminho de seleção do gerador.

**Esforço:** médio (coluna XLSX + mudança no gerador + UX pra editar
prioridade), risco baixo (default 1.0 preserva comportamento).

### Opção 3 — Tier hierárquico por padrão

Subdividir cada padrão em "classes biomecânicas" (tiers). Ex:
`empurrar_compostos` → tier "supino_padrao" (Barra/Halter/Anilha),
tier "apoio" (Apoio/Ajoelhado/Elevado), tier "supino_inclinado",
tier "fechado_VP". Cycling entre tiers antes de sortear dentro.

**Prós:** corrige o problema estrutural — Apoios e Supinos passam a
competir como classes paralelas, não como exercícios independentes.
Distribuição de tiers fica balanceada por design.

**Contras:** estrutura nova no banco (novo campo) + lógica nova no
gerador (`_decompor_demanda_padrao` precisa virar tier-aware) + impacta
toda a Etapa 7 da refatoração (score INTRA/INTER preciso revisitar
pra tier-awareness). Mudança grande.

**Esforço:** alto, risco alto, mas cirurgicamente correto.

### Opção 4 — UI de exercícios fixos (solução D já discutida)

Backend já aceita `exercicios_travados` ([gerador_treino.py:3977](../../gerador_treino.py#L3977)).
Falta UX no app pro PT fixar Supino com Barra (e outros) na hora de gerar.

**Prós:** zero risco no algoritmo; previsível; o PT decide o que entra.

**Contras:** vira responsabilidade manual recorrente; não resolve o
viés sistêmico — só contorna por treino específico.

**Esforço:** baixo-médio (só UI), risco zero (backend pronto).

## Sondagem de validação — Opção 1 vs Opção 1+2 (2026-05-18)

Rodado in-memory no cenário B (3T full body), N=1000, `PYTHONHASHSEED=0`.

- **S1**: preencher `plano_corporal="reto"` nos 4 Apoios. Sem outras mudanças.
- **S2**: S1 + proxy de prioridade 2× via duplicação de Supino com Barra
  no banco (clone com nome distinto, mesma família).

| Métrica | Baseline (B) | S1 | S2 |
|---|---:|---:|---:|
| % Apoios (slots empurrar_compostos) | **69.4%** | 33.3% | 33.3% |
| % Supinos Reto | 2.3% | **27.5%** | 27.9% |
| % Supinos Inclinado | 28.3% | 39.2% | 38.8% |
| Supino com Barra (slots) | 19 (0.6%) | **341 (11.4%)** | 329 (11.0%) |
| Supino com Anilha (slots) | 31 | 386 | 392 |
| Supino com Halteres (slots) | 0 | 57 | 73 |
| Supino Fechado (slots) | 20 | 41 | 42 |
| **Rotinas com ≥1 Supino com Barra** | **1.9%** | **34.1%** | 32.9% |
| Rotinas com ≥1 Supino Reto qualquer | 7.0% | **78.6%** | 80.2% |
| Rotinas só com Apoios | 9.2% | **0.0%** | 0.0% |
| Razão Apoios/Supinos | 2.27× | 0.50× | 0.50× |

### Leitura

- **S1 sozinho resolve o viés.** Supino com Barra entra em 34.1% das
  rotinas (vs 1.9% baseline) — **multiplicou por 18×** só preenchendo a
  tag `plano_corporal`. Distribuição entre famílias passa a Apoio 33% /
  Supino Reto 28% / Supino Inclinado 39%, próximo do "1/3 cada" justo
  entre as 3 famílias.
- **Zero rotinas só com Apoios** (vs 9.2% baseline). Toda rotina passa
  a ter ao menos 1 Supino.
- **S2 não adiciona valor.** Duplicação como proxy de prioridade 2× dá
  resultado quase idêntico a S1 (Supino com Barra 32.9% vs 34.1%, até
  marginalmente pior). Sorteio uniforme dentro da família já é
  "justo" o suficiente uma vez que o viés estrutural foi removido.
- Anomalias residuais: Supino com Halteres (57 slots) e Supino Fechado
  (41 slots) ainda baixos, mas em proporção razoável agora. Supino
  Fechado é `variante_pontual=True` (hard INTRA), comportamento esperado.

### Conclusão

**A solução é exclusivamente Opção 1** — completar tags `plano_corporal`
nos Apoios (e potencialmente em outros exercícios upper com tags
faltantes). Sem Opção 2 (sorteio ponderado), sem Opção 3 (tier
hierárquico), sem mudança no algoritmo. Cadastro de dado, não
refatoração estrutural.

**Por que isso funciona, conceitualmente:** o sistema de penalty não
penaliza "ter tags". Ele penaliza "compartilhar tags com outro
exercício do bloco/rotina" — design correto pra garantir variedade no
treino. Apoio biomecanicamente é plano horizontal/reto; quando a tag
está vazia, o exercício fica invisível à dim `plano_corporal` e foge
da penalty injustamente. Preencher a tag não muda o algoritmo, **corrige
o dado**: Apoio + Supino com Barra passa a acumular penalty igual a
2 Supinos juntos (mesma pegada, mesmo plano, equipamento diferente),
e a competição entre famílias fica justa.

### Opções 2 e 3 — descartadas (por enquanto)

- **Opção 2 (sorteio ponderado por essencialidade)**: descartada como
  primária. S2 mostrou que após Opção 1, a distribuição entre filhos
  da família já fica razoável (Supino com Barra 341, Anilha 386 — não
  igualados em 76 como no baseline). Pode ser revisitada se aparecerem
  outros casos onde "exercício canônico vs variante" ainda enviesa.
- **Opção 3 (tier hierárquico)**: descartada — mudança estrutural
  grande pra resolver problema que se resolve com 4 células no XLSX.

### Opção 4 (UI de exercícios fixos) — em paralelo

Continua útil mas vira "luxo" em vez de "necessidade urgente". Após
Opção 1, o aluno passa a ver Supinos em quase toda rotina; a UI de
fixos serve só pra casos específicos (PT querendo garantir um
exercício específico naquele dia, não pra contornar viés sistêmico).

## Próximo passo proposto (pós-sondagem)

1. **Auditoria das tags vazias indevidas** — listar todos os exercícios
   upper com `plano_corporal`, `pegada` ou `equipamento_grupo` vazios e
   classificar quais devem ser preenchidos vs quais são genuinamente N/A.
2. **Edição do XLSX** — preencher tags faltantes (estimativa: 5-15
   exercícios upper, possivelmente mais em outras regiões).
3. **Re-rodar análise** — confirmar que a distribuição observada em
   rotinas reais bate com a sondagem in-memory.
4. **UI de exercícios fixos (Opção 4)** — em paralelo, sem urgência.

---

## Resolução (2026-05-18)

Implementada em branch `feat/cadastros-pullover-mitigation` (commits
`1ed8217` + `f45a7f9`). Log de sessão completo:
[sessao_2026-05-18_cadastros_e_tiebreaker.md](sessao_2026-05-18_cadastros_e_tiebreaker.md).

### O que foi adotado

1. **Opção 1 (deste doc) — tag `plano_corporal=reto` nos 4 Apoios** —
   Apoio, Apoio Ajoelhado, Apoio Elevado (decisão: versão padrão é mãos
   elevadas, tronco mais ereto), Apoio Fechado. Cadastro de dado, sem
   mudança de algoritmo, como previsto.

2. **Tiebreaker aleatório no softmax do score-aware** (achado de outra
   sessão, não previsto neste doc): `_selecionar_cand_score_aware` usava
   `scored.sort(key=lambda t: t[1], reverse=True)` — sort estável + ordem
   do XLSX gerava viés sistemático em empates de score 0 (caso comuníssimo).
   Fix de 1 linha: `key=lambda t: (-t[1], random.random())`. Preserva
   ranking, desempata uniformemente. **Causa independente do dado faltante**
   — esta análise atribuiu 100% do viés à tag vazia; havia uma segunda
   camada de viés algorítmico que potencializava a primeira.

3. **10 cadastros novos no XLSX** (137 → 147 exercícios) — 6 itens do
   Anexo 4.2 + 4 fora do anexo. Famílias novas: `Pulldown` (4ª caixa em
   puxadas — ataca pigeonhole estruturalmente), `calcanhar_elevado`,
   `Kickback`.

### O que foi descartado

- **Opção 2 (sorteio ponderado por essencialidade)** — confirmado
  desnecessário pela sondagem S2 deste doc. Com Opção 1 + tiebreaker,
  distribuição dentro da família Supino Reto ficou equilibrada
  (Anilha, Barra, Halteres, Fechado todos representados).
- **Opção 3 (tier hierárquico)** — overengineering, como previsto aqui.
- **Solução 3 da outra sessão (peso INTER ponderado por tamanho de
  família)** — revertida durante a implementação. Princípio rejeitado
  pelo usuário: "ter mais variações não significa que o exercício é
  mais importante e deve aparecer mais".

### Números finais (cenário B — uso real 3T full body, N=500-1000)

| Métrica | Baseline | Final (tag + tiebreaker) | Δ |
|---|---:|---:|---:|
| % Apoios slots compostos peito | 69.4% | **30.7%** | −38.7pp |
| % Supinos Reto | 2.3% | **31.3%** | +29.0pp |
| % Supinos Inclinado | 28.3% | 38.0% | +9.7pp |
| **Rotinas com ≥1 Supino com Barra** | **1.9%** | **34.8%** | **+32.9pp (×18)** |
| Rotinas só com Apoios | 9.2% | 0.0% | −9.2pp |

Efeito colateral positivo do tiebreaker — Pullover em puxadas (problema
distinto investigado em paralelo):

| Cenário | Original | Final | Δ |
|---|---:|---:|---:|
| `costas(2)×2` | 60.0% | 38.8% | −21.2pp |
| `puxadas(2)×2` | 97.5% | 81.8% | −15.7pp |
| `upper(4)×2` | 53.5% | 27.6% | −25.9pp |
| `upper(6)×2` | 78.0% | 39.6% | **−38.4pp** |

Pulldown (família nova) ganha presença consistente ~10% nos cenários
upper (era 0% antes).

### Validações

- pytest: 202 passed + 1 skipped + 13 snapshots OK
- harness: 16/16 OK (4.1 = 14.93% — abaixo do alvo histórico <15%
  pela 2ª vez)
- 19 snapshots de regressão regenerados (shifts benignos por mudança de
  seed pós-tiebreaker, sem regressão funcional)
- 2 testes ajustados: fixture HIB2 (seed=358) + migração `SEEDS` (n=5)
  pra `SEEDS_ESTATISTICAS` (n=50) em teste estatístico que ficou frágil
  com a variância aumentada do tiebreaker

### Aprendizado retroativo deste doc

A análise daqui chegou ao diagnóstico **parcialmente correto**: a
solução de dado (Opção 1) era necessária mas insuficiente sozinha pra
explicar toda a magnitude do viés. Faltava enxergar o segundo viés
no `sort` estável do softmax score-aware — só visível investigando em
cenários onde **a tag não era a única variável** (Pullover em puxadas,
por exemplo, onde Pullover Halteres + Pullover Polia sempre entravam
no top-K por ordem de cadastro).

Lição metodológica: quando uma análise atribui 100% de um efeito a uma
causa, vale sondar se a mesma causa explica casos **adjacentes** — se
não explicar, há provavelmente uma segunda camada em jogo.
