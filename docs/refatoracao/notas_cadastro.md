# Notas de cadastro do banco de exercícios

> **Propósito**: registrar decisões clínicas explícitas sobre cadastro de exercícios que não são óbvias pelos dados, e que poderiam ser confundidas com erro de cadastro por quem ler o banco depois (humano ou agente).
>
> **Quando adicionar entrada aqui**: sempre que uma decisão de cadastro for contraintuitiva, exceção clínica deliberada, ou trade-off discutido em sessão. Não anotar o que é óbvio pelos dados.
>
> **Relação com a coluna `obs` do XLSX**: anotações detalhadas vivem aqui. A coluna `obs` é resumo curto colado ao exercício, com link/referência pra esta seção quando houver detalhe.

---

## Hip Thrust e variações de Ponte — classificação `purpose=isolation`

**Decisão**: as 9 variações de Hip Thrust / Ponte de Glúteo no banco estão cadastradas como `purpose=isolation`, mesmo o movimento sendo tecnicamente um hinge composto.

**Justificativa clínica** (sessão 2026-05-21): Hip Thrust enfatiza glúteo de forma muito isolada na execução prática e não gera fadiga sistêmica significativa que dificulte outros exercícios subsequentes — comportamento típico de exercício isolado, não composto. Classificar como `compound` faria a heurística inicial de tier (compound + padrão âncora → Principal) colocá-lo em posição equivocada na ordem do treino.

**Consequência na heurística inicial da Fatia 1**: Hip Thrust vai ser classificado como tier Acessório. Isso é aproximação inicial.

**Refinamento previsto na Fatia 2**: quando entrar cadastro manual da coluna `tier`, Hip Thrust pode ser explicitamente marcado como **Intermediário** (ou Principal para alunos com foco em glúteo dominante). Esse é exatamente o tipo de caso que justifica o cadastro manual de `tier` existir como dimensão independente de `purpose` — purpose e tier são ortogonais.

---

## `knee_extension` — pool de 1 exercício é por design (2026-05-21)

**Decisão**: criado o padrão `knee_extension` para abrigar Cadeira Extensora (que estava antes em `squat_bilateral`, classificação errada).

**Justificativa clínica**: extensão isolada de joelho é um movimento clinicamente distinto de squat. Cadeira Extensora não compartilha demanda neural, padrão biomecânico nem perfil de fadiga com Agachamento. Cadastrar no mesmo padrão polui o pool e induz pareamentos equivocados.

**Pool de 1 é aceitável**: extensão isolada de quadríceps tem essencialmente uma única expressão prática em equipamento de academia (Cadeira Extensora ou variantes mecanicamente idênticas). Lógica análoga aos pools pequenos de `adutores` (2 exercícios) e `panturrilha` (2 exercícios) — reflete realidade do domínio, não falha de cadastro. Não há necessidade de "encontrar mais exercícios" pra encher esse pool.

---

## Exercícios marcados como `ativo=False` (2026-05-21)

**Decisão**: marcar Box Jump, Air Bike Sprint e Air Bike Steady como inativos.

**Justificativa**: estes exercícios têm `purpose=explosive` (2 deles) e `subregiao=cardio` (2 deles, sobreposição com Air Bike Sprint). Não são usados em rotinas comuns do personal — pertencem a contextos específicos de treino de potência ou condicionamento metabólico que não são o foco do app no momento.

> **Nota (2026-05-22)**: Agach. Lateral foi inicialmente marcado inativo nesta leva, mas reativado em seguida — era erro de cadastro (`purpose=explosive`). É um agachamento lateral compound legítimo; corrigido para `purpose=compound` e mantido ativo.

**Reativação futura**: se o app expandir pra cobrir esses contextos, reverter `ativo` para `True`. Manter no banco em vez de deletar preserva o cadastro pra esse caso.
