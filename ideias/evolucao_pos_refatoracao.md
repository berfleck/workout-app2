# Evolução pós-refatoração — Visão global e qualidade clínica

> Documento de consultoria para revisita após conclusão das Etapas
> 1-8 da refatoração. Capacidades identificadas como desejáveis
> mas que extrapolam o escopo do guia v4. Não é roadmap operacional
> imediato — é registro de pensamento maduro para retomar quando a
> base atual estiver consolidada.

---

## 1. Princípio central

O gerador de treinos atual (mesmo pós-refatoração) opera com uma
limitação arquitetural que não impede o funcionamento mas afeta a
qualidade clínica do resultado:

**Permissão técnica não é escolha clínica.**

O sistema valida pares e seleciona exercícios respondendo a
pergunta "isso é aceitável?". Um personal trainer experiente
opera num nível diferente: responde "qual o melhor entre os
disponíveis?". A diferença é fundamental.

A consequência é que pares medíocres mas tecnicamente seguros
passam pelo gerador como se fossem tão bons quanto pares
clinicamente ótimos. O sistema hoje não diferencia.

Há um princípio paralelo que captura outra dimensão do mesmo
problema:

**Pool trancado vs pool dinâmico.**

Após a Fase 0 (pré-alocação), os exercícios estão fixados por
treino. A Fase 2 (montagem de blocos) trabalha apenas com o pool
recebido. Se um exercício se mostra mal encaixado durante o
pareamento, o gerador não tem autoridade para puxar substituto
do banco.

Um personal não opera assim. Para ele, todo o banco é pool, e
trocas entre treinos acontecem livremente quando vê que isso
melhora o todo.

---

## 2. Onde a refatoração planejada chega

Vale reconhecer o que as Etapas 1-8 já entregam, porque é
substancial:

**Etapas 2 e 3** colocam o gerador num formato conceitualmente
próximo de Constraint Satisfaction Problem híbrido com otimização:
quotas globais (decisão "quantos") + sorteio local dentro do
padrão (decisão "quais"). Já não é mais o algoritmo míope que
era. Há intenção clínica guiando o espaço de busca.

**Etapa 5** introduz score linear no pareamento de blocos,
substituindo cascata de regras hard. O `_buscar_candidato` opera
com pesos explícitos, não com if/else encadeados. Permite
refinamento da regra anti-2-unilaterais (sensível ao grupo
muscular) e amostragem softmax entre top-K candidatos.

**Etapa 7** introduz sistema de penalidades multi-dimensional com
três contextos (INTRA, INTER, HISTÓRICO). Tags como
familia_estrita, padrao_movimento, musculo_alvo_especifico,
equipamento, posicao_corporal capturam similaridade biomecânica
fina entre exercícios.

Isso é muito. Mas há limites estruturais que essas etapas não
resolvem.

---

## 3. Onde a miopia residual mora

Mesmo após Etapas 1-8, três pontos permanecem locais quando
deveriam considerar a rotina inteira:

### 3.1 Distribuição entre treinos é semi-local

A função `_distribuir_quotas_entre_treinos` toma decisões
heurísticas após calcular as quotas globais, mas essas decisões
não são avaliadas contra critério de qualidade global da rotina.

Pode produzir distribuições válidas pela regra mas subótimas
clinicamente: T1 só bilateral, T2 só unilateral, T3 misto.
Respeita 3:2 globalmente, mas o aluno experimenta dois treinos
extremos e um misto, em vez de três treinos balanceados.

### 3.2 Fase 2 (montagem de blocos) é totalmente local

O pareamento intra-bloco não considera:
- O resto da rotina (outros treinos)
- Fadiga acumulada na semana
- Padrões já dominantes em outros treinos

Um par como leg curl slideboard + Hollow Hold pode passar todos
os filtros (cargas, fadiga, anti-2-unilaterais) e ainda assim ser
clinicamente ruim por sobreposição biomecânica que só fica visível
quando se considera o contexto.

### 3.3 Não existe função de qualidade global

O sistema responde "essa rotina é válida?" mas não "essa rotina é
boa?" e muito menos "essa rotina é melhor que aquela?". Sem isso,
não há como:

- Comparar soluções alternativas
- Iterar melhorias
- Sair de ótimos locais ruins
- Aprender com escolhas humanas (aceitar/rejeitar sugestões)

Esta é provavelmente a peça arquitetural mais ausente. Tudo o que
segue neste documento depende dela existir em alguma forma.

---

## 4. Casos clínicos de referência

Dois casos reais já documentados ilustram os limites residuais e
servem como benchmarks para qualquer evolução futura.

### 4.1 leg curl slideboard + Hollow Hold

Par observado durante validação dos casos clínicos HIB2 (Etapa 4).
Não é bloqueado pelo filtro de cargas — soma de demanda de core e
carga lombar não atingem threshold. Tecnicamente permitido.

Mas sobreposição biomecânica é alta:
- `posicao_corporal`: ambos em decúbito dorsal
- `padrao_movimento`: ambos com componente forte de
  estabilização anti-extensão de tronco
- `musculo_alvo_especifico`: sobreposição em reto abdominal e
  flexores de quadril

Um personal não escolheria esse par por ter alternativas
superiores (leg curl slideboard + pulldown, por exemplo, daria
contraste de região alto). A Etapa 7 vai reduzir a frequência
deste par via penalidades. Mas não vai eliminá-lo se as
alternativas melhores estiverem alocadas em outros treinos —
limite do pool trancado.

### 4.2 V-Up Uni + Hollow Hold + Tríceps Uni

Trio observado em rotina real do app antigo. Pareamento gerado:
V-Up Uni + Hollow Hold (ambos core), Tríceps Uni solo.

Pareamento clinicamente correto seria: V-Up Uni + Tríceps Uni
(contraste muscular core/braço), Hollow Hold solo.

A regra anti-2-unilaterais antiga, sendo cega ao contraste
muscular, dominou indevidamente. A Etapa 5 corrige este caso
via score linear que torna a penalidade anti-uni condicional ao
grupo. Caso resolvido dentro da refatoração planejada.

A diferença entre 4.1 e 4.2 mostra a fronteira do que a
refatoração consegue: 4.2 é problema local (intra-treino) e tem
solução local (regra de score). 4.1 é problema global (entre
treinos) e precisa de mecanismo que extrapola Etapas 1-8.

---

## 5. Caminhos identificados

Listados do menos ambicioso ao mais ambicioso. Cada um endereça
parte do problema. Combinações são possíveis.

### Caminho A — Sugestões inteligentes de substituição (UX)

Não muda o gerador automático. Aceita o pool trancado.
Compensa via interface: ao gerar uma rotina, o app marca pares
com penalidade alta (usando o sistema da Etapa 7) e oferece
sugestões de substituição.

> "Esse par tem sobreposição biomecânica alta. Sugestões:
> trocar Hollow Hold por Pulldown (de T2) ou trocar leg curl
> slideboard por nordic curl (de T3)."

O personal continua decidindo, mas com informação. O app vira
"second opinion" em vez de "decision maker".

**Vantagens:**
- Não exige mudança no gerador
- Aproveita 100% do sistema de penalidades da Etapa 7
- Transparência absoluta — usuário vê o porquê de cada sugestão
- Cria oportunidade de aprendizado: aceitar/rejeitar vira sinal
  para calibração futura
- Custo de implementação concentrado em UI

**Desvantagens:**
- Não melhora a primeira geração
- Depende de o usuário interagir com as sugestões
- Pode virar ruído visual se mal calibrado

**Avaliação:** melhor custo-benefício de curto prazo. Atende
exatamente o caso 4.1 sem reescrever motor.

### Caminho B — Função de qualidade global

A peça mais fundamental que falta arquiteturalmente. Não é caminho
isolado — é **pré-requisito para vários outros caminhos**.

Definir uma função `score_global(rotina)` que pontua a rotina
inteira em dimensões como:

- Equilíbrio entre subregiões por treino (não só na rotina)
- Redundância de padrão na semana (caso 4.1)
- Distribuição de fadiga (grip/lombar/core) ao longo da semana
- Diversidade de padrões (alimenta-se das tags da Etapa 7)
- Qualidade dos pareamentos (penalidades agregadas dos blocos)
- Cobertura biomecânica (planos de movimento, cadeias)

Sozinha, essa função não muda nada — ela só permite **comparar**
rotinas. Mas é o que destrava todos os caminhos seguintes.

**Vantagens:**
- Conceitualmente simples
- Não interfere no gerador atual
- Permite benchmarking objetivo de mudanças futuras
- Pode ser desenvolvida e calibrada gradualmente

**Desvantagens:**
- Calibrar pesos de cada dimensão é trabalho clínico denso
- Função "errada" leva a otimização errada — perigosa se
  mal calibrada e usada como fonte de verdade

**Avaliação:** prioridade alta como infraestrutura. Sem ela, os
caminhos D, E e F operam às cegas.

### Caminho C — Pool fluido na pré-alocação

Refatoração focada da Fase 0 e Fase 1. A Fase 0 não fixa
exercícios concretos por treino — fixa apenas **quotas por padrão
e por treino**. A escolha do exercício específico que ocupa cada
slot acontece durante a Fase 1, com awareness do que já foi
escolhido em treinos anteriores.

Em vez de "T1: leg curl slideboard, T2: leg curl bola, T3: nordic
curl", a Fase 0 entrega "T1, T2, T3 cada um precisa de 1
knee_flexion". Cada treino então escolhe seu knee_flexion
considerando os outros exercícios do mesmo treino.

**Vantagens:**
- Ataca a origem do problema do pool trancado
- Mantém paradigma do Nível 2
- Não exige função de qualidade global — operação local com
  awareness de história

**Desvantagens:**
- Refatoração não trivial da Fase 0/Fase 1
- Pode ter implicações de performance
- Requer novos testes de regressão

**Avaliação:** ataque cirúrgico ao problema arquitetural sem ir
para Nível 3. Resolve grande parte dos casos similares ao 4.1.

### Caminho D — Busca local com refinamento iterativo

Após o gerador produzir uma rotina (pelos caminhos atuais), uma
camada de polimento opera por cima:

1. Calcular `score_global(rotina)` (requer Caminho B)
2. Identificar os N pares de pior score local
3. Para cada par ruim, tentar trocas:
   - Substituir um exercício por outro do banco (mesma família,
     subregião compatível)
   - Mover um exercício para outro treino e trazer outro de lá
4. Se a troca aumenta `score_global`, manter
5. Iterar até não encontrar melhoria ou atingir limite de
   iterações

É busca local clássica (hill climbing). Compatível com o gerador
atual — opera em cima do output.

**Vantagens:**
- Não muda o gerador
- Pode resolver casos como 4.1 ao fazer a troca entre treinos
- Implementação direta uma vez que o Caminho B existe
- Termina rápido (poucos passos de melhoria geralmente)

**Desvantagens:**
- Depende criticamente da função de qualidade global estar bem
  calibrada
- Pode entrar em ótimos locais
- Comportamento determinístico precisa de cuidado para não virar
  monotônico

**Avaliação:** o "pulo do gato" sugerido pela análise externa.
Camada fina por cima do que existe. Vale considerar após
Caminhos A e B estarem maduros.

### Caminho E — Geração com lookahead limitado

Em vez de Fase 0 sequencial (T1, depois T2, depois T3), o gerador
usa beam search ou backtracking limitado: tenta diferentes
alocações iniciais e escolhe a que produz a rotina com melhor
`score_global`.

**Vantagens:**
- Pode encontrar alocações superiores às heurísticas atuais
- Compatível com a estrutura existente

**Desvantagens:**
- Custo computacional cresce com largura do beam
- Ganho marginal sobre Caminho C + Caminho D pode ser pequeno
- Mais difícil de debugar

**Avaliação:** baixa prioridade. Provavelmente desnecessário se
os caminhos anteriores estiverem implementados.

### Caminho F — Weighted CSP completo

Reescrever a geração como problema de Constraint Satisfaction
ponderado: solver decide alocação e pareamento juntos otimizando
`score_global` sob constraints duras (cargas, exclusões, etc.).

**Vantagens:**
- Solução teoricamente ótima
- Permite restrições muito mais sofisticadas no futuro

**Desvantagens:**
- Refatoração radical
- Performance precisa ser cuidada
- Debugar fica difícil — sistema fica opaco
- Adiciona dependência (biblioteca externa)
- Ganho marginal sobre combinação A+B+C+D dificilmente justifica

**Avaliação:** continua sendo overkill, conforme decidido no
guia v4. Não recomendado.

---

## 6. Loop de aprendizado humano-máquina

Há uma dimensão que não aparece nos caminhos individuais mas
emerge de combiná-los. Se o app oferece sugestões de substituição
(Caminho A) e o personal aceita ou rejeita, isso é dado clínico.

Cada decisão registrada vira sinal:
- Sugestão aceita → função de qualidade estava certa neste caso
- Sugestão rejeitada → função de qualidade estava errada ou
  havia contexto que o app não capturou

Acumulado ao longo do tempo, esse dado pode:
- Calibrar pesos da função de qualidade global automaticamente
- Detectar padrões pessoais do personal (ele sempre rejeita
  sugestões envolvendo determinado equipamento, por exemplo)
- Identificar lacunas no banco de exercícios (sugestões
  rejeitadas frequentemente porque "falta exercício X")

Isso é tipo de inteligência que extrapola o escopo de "gerador de
treinos" e entra em "assistente clínico que aprende com o
profissional". Vale registrar como visão de longo prazo, não como
roadmap imediato.

---

## 7. Roadmap sugerido pós-refatoração

Em ordem de prioridade, considerando custo-benefício e
dependências:

### Fase pós-1 — Função de qualidade global (Caminho B)

Trabalho de modelagem clínica + implementação simples. Sem ela,
caminhos D e seguintes operam às cegas. Sem ela, Caminho A
funciona mas não evolui.

Entregáveis:
- Definição das dimensões a pontuar
- Pesos iniciais por dimensão (chutes informados)
- Função `score_global(rotina) -> float` plugável
- Instrumentação para medir score em rotinas históricas e
  comparar com avaliação clínica humana (calibração)

### Fase pós-2 — Sugestões de substituição na UI (Caminho A)

Aproveita o sistema de penalidades da Etapa 7 e a função de
qualidade da Fase pós-1. Entrega valor clínico imediato sem mexer
no gerador.

Entregáveis:
- Detecção de pares com penalidade alta na rotina gerada
- Geração de sugestões alternativas (trocar exercício X por Y
  de outro treino)
- UI para exibir, aceitar, rejeitar sugestões
- Registro de decisões para futuro aprendizado

### Fase pós-3 — Pool fluido (Caminho C)

Refatoração focada da Fase 0/Fase 1 do gerador. Ataca a origem do
problema sem ir para Nível 3.

Entregáveis:
- Refatoração da Fase 0 para fixar quotas, não exercícios
- Refatoração da Fase 1 para escolher exercício concreto com
  awareness de outros treinos
- Novos testes de regressão
- Métricas de validação (caso 4.1 deve melhorar)

### Fase pós-4 (opcional) — Busca local (Caminho D)

Camada de polimento sobre o output do gerador. Só vale se
caminhos anteriores não cobrirem o suficiente.

Entregáveis:
- Algoritmo de hill climbing usando `score_global`
- Limite de iterações e critério de parada
- Modo "polimento" ativável/desativável

### Fora do roadmap — Caminhos E e F

Lookahead e WCSP completo ficam fora a menos que necessidade
clínica futura justifique.

---

## 8. Dependências e ordem

Resumo visual das dependências:

```
Função de qualidade global (B)
   ↓
   ├── Sugestões de substituição (A) — pode operar antes mas
   │   evolui melhor com B
   ├── Busca local iterativa (D)
   ├── Lookahead (E)
   └── WCSP (F)

Pool fluido (C) — independente, pode ser implementado em paralelo
                  com qualquer um dos acima
```

A é o único que pode entregar valor antes de B existir, mas
beneficia muito de B. C é independente e ataca dimensão diferente
do problema.

---

## 9. Observações finais

Este documento é registro, não compromisso. Pode ser revisitado
após a refatoração estar concluída, com a perspectiva do uso real
do app pós-Etapas 1-8. Decisões de prioridade e escopo provavelmente
mudarão conforme o uso revelar quais limitações pesam mais.

Princípios que devem guiar revisita:

**Não confundir "completar refatoração" com "terminar o trabalho".**
A refatoração resolve problemas conhecidos hoje. O uso vai
revelar problemas novos. Os caminhos aqui descritos são candidatos
para responder a esses problemas futuros, não certezas operacionais.

**Função de qualidade global é multiplicador.** Se for implementada
e bem calibrada, cada caminho subsequente fica viável. Se ficar
mal calibrada, otimização sobre ela leva ao lugar errado.
Investir tempo no Caminho B é investimento de alta alavancagem.

**Sugestões transparentes são preferíveis a automação opaca.**
Caminho A entrega muito valor com risco baixo justamente porque
mantém o personal no centro da decisão. Soluções que tentam
substituir o julgamento clínico (em vez de ampliá-lo) tendem a
falhar em casos de borda e a perder a confiança do usuário.

**Não saltar etapas.** A refatoração planejada (Etapas 1-8) é
pré-requisito implícito para tudo aqui. Tentar implementar
qualquer um destes caminhos em cima da arquitetura antiga seria
gambiarra. Sobre a base estável pós-refatoração, são extensões
naturais.
