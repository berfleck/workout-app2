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
