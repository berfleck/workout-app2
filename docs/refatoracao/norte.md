# Norte do Projeto — BF Treinamento

**Propósito**: documento curto e normativo que captura *por que* este app
existe e *como* tomamos decisões de design. Lido antes de qualquer
trabalho estrutural. Atualizado raramente.

**Audiência**: próximas sessões de Claude trabalhando no refator e em
features estruturais. Bernardo (criador, único usuário) também lê pra
verificar que o entendimento do agente está alinhado.

---

## 1. O que é o app

App pra personal trainer gerar, editar e exportar rotinas de treino
personalizadas por aluno.

- **Hobby.** Sem usuários em produção. Sem pressão de tempo.
- **Vibe coding.** Custo de programação é irrelevante; custo de manter
  código ruim é alto.
- **Qualidade absoluta como prioridade.** Preferimos atrasar 3 sessões
  e fazer certo a entregar rápido e patchar depois.

---

## 2. O que o app precisa fazer bem (visão clínica)

O personal configura as **demandas** (região corporal, padrão de
movimento, etc) e o **formato** (tamanho de bloco, regras de pareamento).
O app entrega a rotina respeitando essas escolhas, com 5 garantias
clínicas:

**Seleção fiel às demandas configuradas.**
Se o personal pede "perna anterior × 3 exercícios", o app entrega 3
exercícios de perna anterior — não 2 + 1 que "ficou melhor". A
categorização (região / subregião / padrão) é input do personal; o app
não substitui o critério de quem prescreveu.

**Pareamento em blocos do tamanho escolhido.**
Tamanho de bloco é decisão do personal (1, 2, 3 ou mais por bloco;
2 é o mais comum). O app monta os blocos com esse tamanho, não com o
que for mais fácil de resolver. **Sem blocos coerentes, não há rotina —
só lista de exercícios.**

**Evitar agonistas no mesmo bloco.**
Default: não combinar dois exercícios do mesmo grupo agonista num
mesmo bloco. Exceção: personal pode permitir explicitamente (toggle
na UI). O app respeita a flexibilidade — o personal sabe quando faz
sentido juntar.

**Distribuir carga acumulada dentro do bloco.**
Evitar que um mesmo bloco concentre exercícios que demandam muito da
lombar, do core ou do grip. Lógica testada no app antigo é referência;
o novo motor pode portar ou propor melhor, mas o resultado clínico
tem que ser equivalente ou superior.

**Variedade equilibrada entre tipos curados, independente do tamanho do pool.**
Quando há múltiplas famílias clinicamente válidas pra um slot (ex:
remada curvada e remada landmine pra "remada"), o app distribui entre
essas famílias de forma equilibrada. **A quantidade de variações
cadastradas dentro de cada família não pode enviesar a distribuição** —
se uma família tem 10 variações e outra tem 3, o app não escolhe a
primeira mais frequentemente por isso. Dentro de uma família, a escolha
entre variações pode ser uniforme (ou modulada por centralidade/tier
curado). Mas a frequência da própria família é decidida clinicamente,
não emergente do banco.

Este é o caso-teste que motivou o refator inteiro (handoff de
2026-05-19, achados sobre remadas LM): no motor antigo, ordem-por-
escassez e softmax cego pro pool fizeram LMs aparecerem em 13-15%
vs vanillas em 22-24% — diferença puramente algorítmica, sem racional
clínico. **Se aparecer viés desse tipo no motor novo, é regressão
estrutural.**

---

## 3. Por que está sendo refeito (motivação estrutural)

O motor antigo é greedy sequencial: escolhe exercícios um a um, na
ordem da escassez do banco. Isso gera 3 problemas que se realimentam:

1. **Vieses sistemáticos** — exercício escolhido primeiro fica imune
   às regras que comparam pares (ex: puxadas sempre antes de remadas
   porque mais escassas).
2. **Patches em cascata** — cada nova feature briga com as anteriores;
   correções pontuais viram exception tables
   (`SUBREGIOES_CARVE_OUT_QUOTAS`, etc).
3. **Modelagem implícita** — conhecimento clínico fica enterrado em
   ordem de código e magic numbers; difícil revisar, impossível
   auditar.

A decisão estrutural (handoff `2026-05-19_decisao_refator.md`) é
migrar pra um motor declarativo (CSP/ILP via CP-SAT do OR-Tools) onde
**o gerador pensa de forma global** — todos os slots da rotina negociam
ao mesmo tempo, sem ordem privilegiada, com regras explícitas.

---

## 4. O que NÃO fazemos (anti-padrões)

- **Não aceitamos design onde o gerador deixa de pensar globalmente.**
  Pode ter etapas, pode ter fases — mas nenhuma decisão pode ser cega
  pra restrições que ela afeta. Se "exercícios escolhidos primeiro"
  continuam imunes às regras de pareamento, isso é o mesmo problema
  do motor antigo com outra cara.

- **Não derivamos frequência clínica de tamanho de pool.** O número
  de exercícios cadastrados dentro de uma família, padrão ou categoria
  é acidente de cadastro — não diretriz clínica. Mecanismos que
  enviesam distribuição por pool (ordem-por-escassez, ponderação
  proporcional ao share, softmax cego à curadoria) são exatamente o
  bug que motivou o refator. Centralidade clínica vem de tag curada
  (tier), não emerge do banco.

  **Exemplos do anti-padrão:**
  - **Apoio** tem 3 variações cadastradas mas não vale 3× mais que
    outros exercícios de empurrar.
  - **Bíceps e tríceps** devem se equilibrar mesmo se um tiver mais
    exercícios cadastrados que o outro.
  - **Core dinâmico vs isométrico** — frequência relativa decidida
    clinicamente, não pelo número de cadastros em cada lado.
  - **Pontes** (muitas variações no banco) não devem dominar a
    categoria hinges / posterior / glúteos.
  - **Remadas curvada vs landmine** — caso original que motivou o
    refator (handoff 2026-05-19).

- **Não adicionamos layer de patch quando o problema é modelagem.**
  Exception tables, carve-outs, monkey-patches — só com data, e
  sempre acompanhados de tarefa pra refletir na modelagem.

- **Não escolhemos pragmatismo que reintroduz problema arquitetural
  já decidido.** A justificativa "é só MVP, refator depois" só vale
  se o débito for explícito e tiver dono.

- **Não decidimos por gut feel quando dá pra medir.** "Pode ficar
  lento", "talvez funcione" — quando há dúvida técnica, medimos
  antes de bater martelo.

- **Não preservamos o motor antigo dentro do app como fallback.**
  Quando o novo estiver completo e validado, o antigo sai do app.
  **Mas é preservado em branch/tag git permanente pra comparação
  histórica.** "Deletado" significa fora do código rodando, não fora
  da história.

- **Não tratamos viés ou edge case novo patchando o motor antigo.**
  Avaliamos se cabe como constraint no catálogo novo. Antigo vive
  até ser substituído; não recebe features novas.

---

## 5. Como decidimos quando há trade-off

- **Coerência com a tese declarativa > pragmatismo.** Caminho mais
  "simples" que mantém o problema arquitetural está fora.

- **Princípio clínico tem precedência sobre conveniência técnica.**
  Se a regra clínica certa exige modelagem mais cara, modelagem mais
  cara.

- **Sendo hobby, podemos arriscar.** Preferimos caminho B custoso e
  coerente a caminho A seguro e incoerente.

- **Medir antes de assumir custo.** Quando a dúvida é técnica (tempo
  de solve, complexidade), spike rápido com escala realista antes de
  descartar.

- **Sem usuários = sem retrocompat obrigatória.** Não carregamos peso
  de migração, fallback, ou deprecation gradual. Clean break é a
  opção default.

- **Doc-first em decisões estruturais.** Mudanças de arquitetura
  passam pelo handoff/catálogo antes do código.

---

## 6. Onde vamos parar (estado-alvo)

O refator está completo quando:

- `/gerar` e `/regerar` usam o motor CSP. Motor antigo removido do app.
- Pareamento real (Fatia 4) implementado — rotinas saem com blocos
  coerentes.
- 4 dimensões do vetor de perfil ativas e moduladoras (Aderência ao
  Tier já entregue na Frente D).
- Dashboard quantitativo (passo 5 do fluxo) rodando — permite calibrar
  pesos com dados em vez de gut feel.
- Cadastros completos no XLSX (tier, estabilidade externa, demanda
  lombar — passo 3 do fluxo).
- Motor antigo preservado em branch/tag git pra comparação histórica
  sob demanda.

Depois desse marco, retornamos ao ciclo normal: adicionar features de
produto (fixos na UI, ZIP, pausados por aluno, etc) com a confiança
de que o motor abaixo não vai gerar patches em cascata.

---

## 7. Para a próxima Claude

Antes de tocar em qualquer coisa estrutural (motor, banco, rotas do
gerador):

1. **Ler este doc inteiro.** Cabe em 5 minutos.
2. **Ler o handoff estrutural** (`handoff_2026-05-19_decisao_refator.md`)
   e o catálogo de constraints (`catalogo_constraints.md`).
3. **Quando enfrentar trade-off não óbvio**, consultar Seção 5 antes
   de perguntar ao usuário. Se a Seção 5 responde, decida sozinho e
   explique o raciocínio. Se não responde, é decisão estrutural nova —
   aí pergunta.
4. **Anti-padrão clássico**: recomendar caminho "mais simples / menos
   código / sem regressão" sem checar se ele reintroduz problema da
   Seção 3. Esse é o vício específico que motivou este doc.
5. **Se for tentar justificar algo baseado em "tamanho do pool",
   "share no banco" ou "proporcional ao número de cadastros" — pare.**
   Releia Seção 4, segundo bullet. Esse é o anti-padrão mais
   recorrente e o mais difícil de pegar sem o doc aberto.
