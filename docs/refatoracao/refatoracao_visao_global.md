# Refatoração: visão global na geração de rotinas

> Documento de design para refatoração futura do `gerar_multiplos_treinos`.
> Discute o problema da geração sequencial atual, três níveis de
> sofisticação possíveis, e a recomendação. **Não é um patch para aplicar
> agora** — é planejamento para entrar no roteiro depois das cargas e
> antes das tags multi-dimensionais.

---

## O problema

O gerador hoje opera de forma **estritamente sequencial** entre treinos
de uma mesma rotina:

```
T1: seleciona 10 exercícios → monta blocos → finaliza
T2: seleciona 10 (com bloqueios herdados de T1) → monta → finaliza
T3: seleciona 10 (com bloqueios herdados de T1 + T2) → monta → finaliza
```

Cada treino conhece o que veio antes mas é cego pro que vem depois. T1
pega o que quer, T2 pega entre o que sobrou, T3 fica com migalhas.
Pior ainda: T1 não sabe que está prejudicando T3.

### Sintomas observados nas simulações

Quatro problemas concretos que aparecem por causa dessa arquitetura:

1. **Treinos finais incompletos**: T3 frequentemente fica com menos
   exercícios que o pedido porque os candidatos já foram esgotados em
   T1 e T2. Pra padrões com poucas famílias (ex: tríceps tem 8 ex todos
   com mesmo `variacao_de`), o problema aparece já em T2.

2. **Distribuição ruim entre subregiões dentro de uma região**: quando
   o usuário pede `lower(N)`, o app distribui em média 2.2
   perna_posterior para 1.5 perna_anterior (esperado seria 1:1).
   Adutores e panturrilha quase nunca aparecem. T1 pega os hinges
   "óbvios" antes de pensar no equilíbrio entre subregiões nos próximos
   treinos.

3. **Bloqueios em cadeia mais frequentes**: filtros de cargas e família
   tornam mais provável que T3 não consiga preencher demandas. Se T1
   e T2 escolheram exercícios com cargas altas em determinada dimensão,
   T3 fica sem opções pra parear sem violar limites.

4. **Padrões âncora não cobertos por composto na rotina inteira**:
   quando pede `regiao=upper(3)` por treino, a regra atual de "60%
   compostos" garante quantidade mas não cobertura categórica. Pode
   acontecer de T1 pegar 2 compostos de costas + ombro (zero peito),
   T2 pegar 2 compostos de costas + ombro de novo (zero peito de novo),
   e o único peito da rotina ser o isolado sorteado nas vagas livres
   (ex: Crossover Sentado). Resultado: rotina inteira sem composto de
   peito, e peito representado por exercício que sequer trabalha tríceps
   acessoriamente. **Caso real observado**: rotina upper(3)+lower(2)+
   core(2) × 2 treinos onde o único peito foi Crossover Sentado em T2.

### Diagnóstico arquitetural

A causa-raiz é a **separação rígida entre Fase 1 (seleção) e Fase 2
(montagem)** combinada com **escopo local por treino**:

- Fase 1 pega os exercícios que cumprem demandas, mas não pensa em pareamento
- Fase 2 monta blocos com o que recebeu, sem voltar pro banco
- E nada disso considera os outros treinos da rotina

Um personal trainer experiente faz o oposto: **olha a rotina como um
todo**, distribui os exercícios mais "raros" entre os treinos pra
garantir variedade, e só depois decide o pareamento dentro de cada
treino.

---

## Os custos da mudança

A solução conceitual é clara: **selecionar globalmente antes de
montar**. Mas tem três custos que vale entender antes de decidir:

### Custo 1 — Complexidade computacional

Hoje cada treino é problema independente. Resolver 3 treinos = 3
problemas pequenos.

Selecionar globalmente vira **um problema grande com restrições
cruzadas**:

> "Escolha 30 exercícios (10 por treino) tais que:
> - cada treino satisfaça suas demandas
> - sem variações repetidas entre treinos
> - cada par dentro de cada treino respeite cargas
> - cada bloco respeite fadiga
> - distribuição equilibrada entre subregiões
> - ..."

Esse é um problema NP-difícil em geral. Mas — e aqui está a boa
notícia — não precisamos da solução ótima. Precisamos de "uma solução
boa o suficiente". Heurísticas resolvem em milissegundos.

### Custo 2 — Repensar a aleatoriedade

Hoje a aleatoriedade está em "qual exercício o gerador escolheu pra
preencher cada vaga". Em modo global, fica tentador trocar isso por
algoritmo determinístico (escolhe sempre a configuração de menor
"custo"). Aí perdemos variabilidade — todo mundo recebe o mesmo treino.

**Solução**: sortear entre as N melhores configurações globais, não
escolher a melhor. Mesmo princípio do que foi discutido no
`visao_proxima_fase.md` sobre penalidades.

### Custo 3 — Refatoração não trivial

`gerar_multiplos_treinos` hoje é simples (loop sobre
`gerar_sessao_por_demandas`). Em modo global, ela vira o coração do
sistema, e `gerar_sessao_por_demandas` vira função auxiliar que opera
sobre uma sub-fatia já resolvida. Isso é refatoração substancial, não
ajuste pequeno.

---

## Três níveis de sofisticação

Apresentados do mais simples ao mais ambicioso. Cada um tem trade-offs
diferentes.

### Nível 1 — Lookahead simples

**Esforço**: médio. Estima ~70% do ganho.

Mantém a lógica sequencial mas ensina T1 a "pensar em T2 e T3". Em vez
de pegar Crossover na primeira oportunidade, calcula:

> "Se eu pegar Crossover agora, T2 e T3 ainda têm como cumprir suas
> demandas? Se não, prefere outro candidato."

**Implementação**: antes de fixar uma escolha em T1, simula uma
seleção rápida de T2 e T3 com o que sobraria. Se algum não consegue
cumprir, recusa a escolha.

**Vantagens**:
- Aproveita 90% do código existente
- Risco baixo de quebrar o que já funciona
- Mudança incremental que pode ser revertida facilmente

**Desvantagens**:
- Ainda é míope localmente — pode tomar decisões subótimas que só
  seriam vistas como ruins de uma perspectiva global
- **Não resolve o viés de distribuição entre subregiões** (problema
  importante que apareceu nas simulações)
- Performance: simular T2+T3 a cada decisão de T1 multiplica o tempo
  de geração

### Nível 2 — Pool global de exercícios

**Esforço**: médio-alto. Estima ~85% do ganho.

Antes de montar treinos, **pré-aloca** os exercícios entre os 3 treinos.

**Algoritmo**:

1. Para cada treino, lista quais slots ele precisa preencher
   (peito-composto, peito-isolado, costas-composta, etc.)

2. Para cada slot, lista quantos candidatos disponíveis no banco

3. **Slots mais escassos primeiro**: o slot com menos opções
   disponíveis ganha prioridade na escolha. Isso evita o caso em que
   T1 e T2 "comem" exercícios escassos e T3 fica sem.

4. Distribui exercícios entre treinos respeitando demandas, regra de
   não-repetir-família, e equilíbrio entre subregiões dentro de cada
   região pedida.

5. Depois disso, cada treino faz sua montagem de blocos normalmente
   (Fase 2 atual continua igual).

**Vantagens**:
- Resolve diretamente o problema do "T3 fica com migalhas" porque os
  slots escassos foram alocados primeiro
- Resolve o viés posterior > anterior dentro de uma região
- Ainda gerenciável tecnicamente
- A Fase 2 (montagem de blocos) continua igual, então não impacta
  pareamento de cargas

**Desvantagens**:
- Refatoração real do `gerar_multiplos_treinos`
- Precisa testes novos (a fase clínica de cargas vai ter que ser
  refeita pra confirmar que continua válida)
- Lógica de "slot escasso" precisa de calibração — o que conta como
  escasso varia conforme o banco

### Nível 3 — CSP completo

**Esforço**: alto. Estima 95-100% do ganho.

Selecionar os 30 exercícios juntos, com todas as restrições cruzadas
(incluindo cargas e pareamento), e só depois montar os blocos.

**Algoritmos possíveis**: backtracking com forward checking,
min-conflicts, simulated annealing. São técnicas conhecidas de IA
clássica, há bibliotecas Python (`python-constraint`, `OR-tools`).

**Vantagens**:
- Solução "ótima" (no sentido de respeitar tudo simultaneamente)
- Permite restrições muito mais sofisticadas no futuro

**Desvantagens**:
- Refatoração grande
- Performance precisa ser cuidada (pode ficar lento, especialmente
  quando o filtro for ainda mais rico)
- Debugar fica difícil — quando algo dá errado, o sistema é opaco
  ("por que ele escolheu isso?" vira pergunta sem resposta clara)
- Adiciona dependência (biblioteca externa)
- Ganho marginal sobre Nível 2 dificilmente justifica o custo

---

## Recomendação

**Nível 2 é o sweet spot.**

Razões:

- Nível 1 não resolve o viés de distribuição entre subregiões, que é
  um dos problemas mais visíveis hoje
- Nível 3 é exagero pra um app de geração de treino — ganho marginal
  sobre Nível 2 não justifica complexidade adicional
- Nível 2 ataca diretamente os 3 primeiros problemas observados
  (treinos finais incompletos, distribuição desequilibrada, bloqueios
  em cadeia)

---

## Complemento à refatoração: regra de âncoras protegidas

A refatoração Nível 2 sozinha **não resolve** o problema 4 (padrões
âncora não cobertos por composto). Ela melhora distribuição, mas não
muda o critério de seleção dos compostos. Pra resolver esse caso, é
necessária uma regra adicional.

### Conceito

Cada região tem **padrões âncora** — categorias musculares que devem
estar representadas por pelo menos 1 exercício composto na rotina,
sempre que houver vagas suficientes:

```
upper:  empurrar_compostos, remadas, puxadas, ombro_composto
lower:  squat, hinge
core:   (nenhum — região sem âncoras)
```

### Quando aplicar

**Apenas em demandas de nível `regiao`**. Em demandas de subregião ou
padrão, o usuário já está sendo específico sobre o que quer — não cabe
o app forçar âncoras. A regra 60/40 atual também opera só nesse nível,
então a regra de âncoras é uma extensão natural do mecanismo existente.

Especificamente:

- ✅ `("regiao", "upper", 3)` → aplica regra de âncoras
- ❌ `("subregiao", "peito", 2)` → NÃO aplica (usuário pediu peito
  explicitamente)
- ❌ `("padrao", "remadas", 2)` → NÃO aplica

### Como funciona (combinada com Nível 2)

1. Antes de gerar treinos, calcular vagas totais por região na rotina:
   "rotina pediu `upper(3)` × 2 treinos = 6 vagas de upper"
2. Aplicar proporção 60/40: das 6 vagas, 4 devem ser compostos
3. **Distribuir esses 4 compostos pelos padrões âncora da região**:
   pelo menos 1 representante de cada âncora antes de sortear livre
4. Sobrar 1 composto livre (porque foram 4 e tem 4 âncoras — ou seja,
   nesse caso específico cada âncora ganha 1 e zero sobra)
5. Os 2 isolados restantes seguem regra antiga (sorteio livre)
6. Distribuir todos os exercícios entre treinos respeitando demandas
   por treino

### Casos de borda

- **Vagas < número de âncoras**: se rotina pede só 2 compostos e a
  região tem 4 âncoras, cobrir 2 das 4 (sorteio uniforme entre âncoras
  para evitar viés sistemático)
- **Vagas > número de âncoras**: cobrir todas as âncoras + sortear o
  resto livre
- **Lower com squat+hinge**: rotina pequena pode pegar 1 squat + 1
  hinge e fechar. Garante distribuição quad/post-coxa balanceada
  naturalmente — resolve parte do viés posterior > anterior também

### Por que essa regra precisa de Nível 2

Sem pré-alocação global (Nível 2), a regra de âncoras só consegue
operar dentro de cada chamada de `gerar_sessao_por_demandas`. Resultado:
T1 pode cobrir todas as âncoras, T2 pode cobrir todas de novo —
gerando rotina com cobertura mas duplicação. A pré-alocação global
permite distribuir as âncoras entre treinos (T1 fica com peito+costas,
T2 fica com ombro+puxadas), gerando rotina **balanceada e variada**.

---

## Onde isso entra no roteiro

Esta refatoração **não cabe junto do patch das cargas** (HIB2).
Misturar os 3 grandes blocos em um único PR vira projeto sem fim.

**Ordem sugerida**:

1. **Primeiro**: terminar a Fase B do filtro de cargas (HIB2) — está
   pronta pra ir, traz benefício imediato e visível
2. **Depois**: refatoração Nível 2 (pool global)
3. **Por último**: tags multi-dimensionais + sistema de penalidades
   (descrito em `visao_proxima_fase.md`)

A refatoração Nível 2 é **independente** das cargas. HIB2 vai
continuar funcionando depois dela — apenas vai operar dentro de uma
seleção globalmente equilibrada em vez de uma sequencial.

---

## Pontos abertos para decidir antes de implementar

Quando chegar a hora de implementar o Nível 2 + âncoras, vai ser
preciso definir:

1. **Como medir "escassez" de slot**: número absoluto de candidatos?
   Razão entre candidatos e demanda? Considerando filtros já aplicados
   (equipamento, complexidade)?

2. **Como modelar equilíbrio entre subregiões**: distribuição uniforme
   estrita? Tolerância à variação (60/40, 70/30)? Configurável pelo
   personal?

3. **Lista exata de padrões âncora por região**: a proposta atual é
   `upper = {empurrar_compostos, remadas, puxadas, ombro_composto}` e
   `lower = {squat, hinge}`. Validar se faz sentido. Posterior_ombro
   entra como âncora de upper? Knee_flexion entra como âncora de lower
   ou continua secundário?

4. **Comportamento quando vagas < número de âncoras**: sorteio uniforme
   (sugestão atual) ou priorizar por popularidade clínica
   (peito > ombro > costas...)?

5. **Como interagir com `relaxar_familia`**: o pool global precisa
   considerar o flag pra decidir quando relaxar?

6. **Compatibilidade com `exercicios_travados`**: travados continuam
   sendo prioridade absoluta, mas como informam a alocação global?

7. **Performance**: aceita levar 1-2 segundos pra gerar uma rotina de
   3 treinos (Nível 2 vai ser mais lento que o atual)?

Essas decisões vão precisar de mais simulação pra calibrar. A boa
notícia é que a infraestrutura de simulação já existe e foi validada.

---

*Documento de design. Não aplicar como patch. Revisar antes da
refatoração.*
