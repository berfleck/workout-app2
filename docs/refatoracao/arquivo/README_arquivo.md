# Documentos arquivados

Esta pasta contém documentos de design e análise anteriores que
motivaram ou contribuíram para o guia de refatoração atual, mas
que **não refletem mais as decisões finais** e não devem ser
usados como referência operacional.

## Fonte de verdade

A fonte de verdade para a refatoração em andamento é:

- `../guia_refatoracao_v4.md` — roteiro operacional completo,
  decisões finais e ordem de execução.

## Por que estes documentos foram arquivados

Cada documento aqui foi consumido e/ou superado pelo guia v4.
As decisões evoluíram durante a discussão de design e o estado
final está consolidado lá.

Em particular, divergências conhecidas entre os documentos
arquivados e o guia v4:

- **Âncoras protegidas.** Documentos antigos descrevem âncoras
  apenas em nível região. O guia v4 estende a regra para
  subregião também, com estrutura de peso e flag de
  obrigatoriedade.
- **Empacotamento de etapas.** Documentos antigos empacotam
  "Nível 2 + âncoras protegidas" como pacote único. O guia v4
  separa em Etapa 2 (pré-alocação Nível 2) e Etapa 3 (âncoras),
  com critérios de aceitação independentes.
- **Princípio quota vs sorteio.** Não está formalizado nos
  documentos antigos. O guia v4 introduz como princípio que
  atravessa as Etapas 2 e 3.
- **Lista de etapas.** Documentos antigos listam 10 etapas. O
  guia v4 reorganizou em 8 etapas com escopo redefinido.

## Por que estão preservados

Estes documentos contêm o raciocínio histórico que justifica as
decisões finais. Se em algum momento for preciso entender "por
que escolhemos Nível 2 e não Nível 3?", "por que invertemos a
ordem cargas → Nível 2?", ou similares, o contexto está aqui.

Também podem conter ideias que ainda não foram incorporadas mas
podem ser revisitadas no futuro.

## Aviso para Claude Code e outros agentes

**Não consultar esta pasta para planejar implementações.** Use
exclusivamente `../guia_refatoracao_v4.md` como referência
operacional. Os documentos aqui podem indicar caminhos
abandonados ou parcialmente revisados que se aplicados gerarão
inconsistências com o guia atual.

---

## Era v4 — refator greedy incremental (arquivada em 2026-05-21)

A subpasta `era_v4_greedy_incremental/` contém o `guia_refatoracao_v4.md` e seus satélites (`memoria_projeto.md`, `dimensoes_proximidade.md`, logs `etapa_2.md` a `etapa_6.md`, baselines JSON).

Esta era cobriu o planejamento e execução parcial das Etapas 1-7 do refator por caminho do meio — paradigma greedy sequencial com scoring + carve-outs + filtros em camadas. Foi superada em 2026-05-19 pela decisão de migrar pra paradigma declarativo (CSP/ILP), documentada em `../handoff_2026-05-19_decisao_refator.md`.

### Por que foi superada

Diagnóstico do handoff: o algoritmo greedy sequencial gera vieses de ordem-de-alocação (ex: puxadas caem antes de remadas em 100% das rotinas com costas=2) que não são removíveis com mais scoring ou mais carve-outs. Cada nova feature briga com as anteriores; cada problema vira patch em cascata. A solução não é mais uma Etapa — é mudar o paradigma de "preencher na ordem" pra "negociar simultaneamente via constraint solver".

### O que sobrevive desta era

Várias decisões e dados continuam válidos no novo paradigma:

- O **banco de exercícios** e suas colunas (subregiao, padrao, familia_estrita, etc.)
- Decisões de cadastro consolidadas na Etapa 6 Fase 3 (`familia_estrita`, `variante_pontual`, `lateralidade` hard em costas, matriz de pegada)
- Conceitos clínicos extraídos durante a era (consolidados em `../principios_clinicos.md`)
- Calibração de pesos da Etapa 7 (vai virar input pros pesos iniciais da função objetivo nova)

### O que NÃO sobrevive

- A estrutura de Etapas 1-8 do `guia_refatoracao_v4.md` (incluindo Etapa 7 já fechada e Etapa 8 que estava planejada)
- O algoritmo greedy + scoring + carve-outs do `gerador_treino.py` (vai conviver com o `gerador_csp.py` novo durante o MVP, depois é substituído)
- Vários "tapa-buracos" reconhecidos (ex: `squat_bilateral`/`squat_unilateral` como padrões separados — débito técnico documentado)

### Aviso para agentes

NÃO consultar `era_v4_greedy_incremental/` para planejar implementação do gerador novo. A fonte de verdade está em `../handoff_2026-05-19_decisao_refator.md`, `../principios_clinicos.md`, `../catalogo_constraints.md`.
