# Guia de refatoração — Workout App v2

> Documento mestre para conduzir a refatoração do gerador de treinos.
> Sintetiza o roteiro de `memoria_projeto.md`, o design de
> `refatoracao_visao_global.md`, e as recomendações da análise externa
> (refatorar vs refazer, ordem de execução, modelagem de proximidade,
> testes formais).
>
> **Não é um patch para aplicar.** É um plano para conduzir N implementações
> sucessivas via Claude Code. Cada etapa tem escopo, critério de aceitação
> e validação próprios — devem virar PRs separados.

---

## 1. Decisão fundamental: refatorar, não refazer

A pergunta inicial era: o gerador de treinos precisa ser reescrito do
zero ou pode ser refatorado? **Refatorar.**

Os problemas identificados (viés posterior > anterior, treinos finais
incompletos, padrões âncora não cobertos por composto, regra
anti-2-unilaterais cega, distribuição entre subregiões) não vêm da
linguagem, da stack, da arquitetura geral do app, ou da modelagem do
banco. Vêm de **uma fonte concentrada**: a abordagem sequencial em
`gerar_multiplos_treinos`, combinada com a sobrecarga semântica do
campo `variacao_de`.

O resto do projeto é ativo valioso e intocável nesta refatoração:

- **`app_flask.py`** — 2.559 linhas, 65 rotas, sistema de rascunho,
  diff visual, swap por long-press, mobile redesign 12/12 etapas.
  Meses de iteração e bugs descobertos.
- **`banco_exercicios.xlsx`** — 125 exercícios curados manualmente,
  com cargas grip/lombar/core já preenchidas. Ativo mais valioso do
  projeto.
- **Acoplamento limpo entre motor e Flask** — `gerador_treino.py` é
  importado mas não conhece nada de Flask. Permite refatorar e testar
  o motor isoladamente.

A refatoração é cirúrgica: alvo principal é `gerar_multiplos_treinos`,
com extensões pontuais em `_buscar_candidato` e adições no
carregamento do banco.

---

## 2. Princípios que guiam todas as etapas

Antes de descrever o roteiro, princípios que valem para cada PR:

**Cada etapa entrega valor isolado.** Nada de "a etapa X só faz sentido
junto com Y". Se a etapa não puder ser merged sozinha, está mal
desenhada.

**Cada etapa tem critério objetivo de "feito".** Não "parece melhor"
— métrica em cima de simulação, ou teste passando, ou comportamento
verificável.

**Não acumular múltiplas mudanças num mesmo PR.** O documento original
empacotava "Nível 2 + âncoras protegidas". Aqui são duas etapas
separadas. Misturar significa que se algo der errado, não dá pra
saber qual mudança causou.

**Simulação como prova, não impressão.** A infra que gerou os 20
casos clínicos HIB/HIB2 deve ser formalizada como testes de regressão
antes de qualquer mudança no motor. Sem isso, "está melhor" vira
intuição.

**Banco e UI são intocáveis nesta refatoração.** Mudanças no banco
(novas colunas, cleanup) entram como etapas próprias. Mudanças na
UI só acontecem na etapa final, quando os controles de variabilidade
já podem ser expostos.

**INTRA, INTER e HISTÓRICO têm prioridades diferentes.** Esse insight
passa por todas as etapas a partir do meio do roteiro. O sistema atual
trata INTRA e INTER com o mesmo mecanismo binário (família bloqueia ou
não), e ignora o histórico longo do aluno. A meta é que cada dimensão
de proximidade tenha pesos diferentes para três contextos:

- **INTRA** — mesmo treino. Prioridade máxima de variabilidade
  biomecânica imediata.
- **INTER** — mesma rotina semanal, entre treinos diferentes.
  Prioridade média.
- **HISTÓRICO** — rotinas anteriores do mesmo aluno. Prioridade
  decrescente com o tempo (uma exposição há 6 semanas pesa menos que
  uma há 2 semanas).

Sem o terceiro contexto, é possível que um exercício apareça em
"semanas alternadas" durante meses — tecnicamente nunca repetindo a
rotina anterior, mas dominante de fato no histórico do aluno. A
infraestrutura para resolver isso já existe parcialmente: o app
mantém histórico de rotinas no SQLite. Falta o motor consultá-lo
com ponderação por recência.

---

## 3. Estado atual: pontos de partida

### O que está funcionando

- Geração multi-treino com hierarquia região → subregião → padrão
- Sistema de avisos (`incompleta`, `familia_repetida`)
- Relax de família inter-treino com badge `↻` na UI
- Filtros hard: nome, `variacao_de`, equipamento, complexidade,
  fadiga, lateralidade
- Cleanup de similaridade já aplicado
- 3 colunas novas no banco (`carga_grip`, `carga_lombar`,
  `demanda_core`) já curadas, mas **ainda não usadas pelo código**
- Calibração HIB2 do filtro de cargas escolhida (threshold 6/5/6),
  pendente avaliação humana dos 20 casos clínicos

### O que está pendente

| # | Problema | Resolvido em |
|---|----------|--------------|
| 1 | Viés posterior > anterior em `lower(N)` | Etapa 2 |
| 2 | Tríceps com 8 ex todos `variacao_de = "Tríceps"` | Etapas 1 e 6 |
| 3 | `subregiao` não está na dataclass | Etapa 1 |
| 4 | Squat unilateral/bilateral é tapa-buraco | Etapa 1 (parcial) |
| 5 | Padrões âncora sem composto na rotina | Etapa 3 |
| 6 | Regra anti-2-unilaterais força pares ruins | Etapa 5 |

### Alteração relevante de ordem em relação ao plano original

O `memoria_projeto.md` propõe: cargas → Nível 2 + âncoras → tags.
Este guia propõe: **fundação de testes → Nível 2 → âncoras → cargas
→ score consolidado → tags**.

A inversão (Nível 2 antes de cargas) é deliberada. Cargas operam
dentro de `pode_adicionar_ao_bloco` (Fase 2 do gerador). A
refatoração Nível 2 muda o que chega na Fase 2 (porque a Fase 1
passa a ser globalmente coordenada). Aplicar HIB2 antes de Nível 2
significa calibrar duas vezes: uma agora, outra depois que a base
mudou. Os 20 casos clínicos validados em cima do motor sequencial
não cobrem o cenário pós-refatoração.

**Trade-off legítimo da inversão:** se o Nível 2 demorar muito, o
benefício imediato das cargas fica represado. Se preferir destravar
esse valor primeiro, é razoável manter a ordem original (Etapa 4
antes da Etapa 2). Mas espera-se nesse caso que a calibração HIB2
seja revisitada após a Etapa 2.

---

## 4. Roteiro de execução

### Etapa 1 — Patch defensivo + fundação de testes

**Objetivo.** Estabelecer o cinto de segurança para todas as
refatorações seguintes, e fazer cleanup de dívida técnica leve. Sem
mudar comportamento do motor.

**Pré-requisitos.** Nenhum.

**O que muda no código:**

1. Adicionar campo `subregiao: str` na dataclass `Exercicio`. Preencher
   no `carregar_banco` derivando de `PADRAO_PARA_SUBREGIAO`. Trocar
   consultas ao mapa pelo atributo direto onde aplicável.
2. Cleanup do banco de tríceps: revisar se `variacao_de = "Tríceps"`
   faz sentido para todos os 8 exercícios. Provavelmente não — Tríceps
   Francesa, Polia, Coice, Testa são exercícios independentes, não
   variações entre si. Refinar para que famílias `variacao_de`
   reflitam variações estritas, não categoria muscular.
3. Adicionar `pytest` ao projeto e criar `tests/test_gerador.py` com:
   - **Testes de invariantes** (devem valer em qualquer geração):
     sem nomes duplicados no mesmo treino, fadiga máxima respeitada,
     blocos com tamanho ≤ configurado, etc.
   - **Testes de regressão**: 10–20 configs representativas com
     `random.seed(N)` fixo e snapshot dos outputs atuais. Geram
     baseline pré-refatoração.
4. Adicionar harness de simulação em massa (formalização do que
   gerou os relatórios HIB/HIB2). Função que aceita config + N
   iterações e devolve métricas agregadas: distribuição
   subregião/região, taxa de avisos, blocos solo, cobertura de
   âncoras.

**Entregáveis.**
- PR com `subregiao` na dataclass e usos atualizados
- PR com cleanup do banco de tríceps (decisão documentada)
- PR com setup pytest, testes de invariante (mínimo 8) e testes de
  regressão (mínimo 10 configs)
- PR com harness de simulação em massa

**Como validar.** Todos os testes passando. `pytest` rodando em
menos de 30 segundos. Harness de simulação produzindo relatório
reproduzível com seed fixa.

**Riscos.**
- Cleanup do tríceps pode revelar outras fronteiras de família mal
  desenhadas — manter escopo controlado e documentar o que ficou
  pra depois.
- Snapshots de regressão capturam o comportamento *atual*, incluindo
  bugs conhecidos. Anotar quais snapshots refletem comportamento
  desejado vs comportamento aceito mas a melhorar.

---

### Etapa 2 — Refatoração Nível 2 (pré-alocação global, sem âncoras)

**Objetivo.** Resolver os problemas de viés posterior > anterior,
treinos finais incompletos, e bloqueios em cadeia. Mantém Fase 2
(montagem de blocos) intocada.

**Pré-requisitos.** Etapa 1 completa.

**O que muda no código:**

1. Refatorar `gerar_multiplos_treinos`:
   - Fase 0 (nova): pré-alocar exercícios entre os N treinos antes
     de qualquer um ser montado. Ordenar slots por escassez (slots
     com menos candidatos disponíveis no banco vão primeiro).
   - Fase 1 (modificada): `gerar_sessao_por_demandas` passa a operar
     sobre uma fatia já alocada, em vez de competir por candidatos
     globais.
   - Fase 2 (intocada): `montar_blocos` continua igual.
2. Implementar métrica de "escassez de slot": número absoluto de
   candidatos no banco filtrado / quantidade pedida. Slots com razão
   ≤ 2 vão primeiro.
3. Modelar equilíbrio entre subregiões dentro de uma região como
   parte da pré-alocação. Quando a demanda é `regiao(N)`, pré-alocar
   garantindo distribuição minimamente equilibrada entre subregiões
   disponíveis (sem regra rígida ainda — só evitando concentração).

**Entregáveis.**
- PR com `gerar_multiplos_treinos` refatorado
- PR ou commit separado com função utilitária de cálculo de escassez

**Como validar.**
1. Suíte pytest da Etapa 1 continua passando (testes de invariantes
   não podem quebrar).
2. Testes de regressão *vão mudar* — esperado. Documentar quais
   snapshots mudaram e por quê.
3. Rodar harness de simulação com 1.000 iterações de configurações
   representativas e comparar pré vs pós:
   - Distribuição subregião dentro de região: razão posterior/anterior
     deve cair de ~1.5 para próximo de 1.0 em demandas `lower(N)`
   - Adutores e panturrilha aparecem em > 30% das rotinas com
     `lower(4+)` (vs quase nunca atualmente)
   - Treinos finais incompletos: redução significativa em rotinas
     com 3+ treinos

**Riscos.**
- Pré-alocação por escassez pode escolher exercícios "raros" demais
  cedo e deixar um treino com candidatos demais e outro com poucos.
  Mitigação: incluir no critério de escassez também a demanda do
  slot, não só o número de candidatos.
- Performance: 1.000 simulações precisam rodar em tempo razoável
  (alvo: < 1 minuto). Se ficar lento, considerar caching dos pools
  de candidatos por padrão.
- Interação com `relaxar_familia` e `exercicios_travados` precisa
  ser revisada — a pré-alocação global afeta ambos.

---

### Etapa 3 — Regra de âncoras protegidas

**Objetivo.** Garantir que padrões âncora estejam representados por
pelo menos 1 composto na rotina (resolve problema 5: rotina com peito
representado só por Crossover Sentado).

**Pré-requisitos.** Etapa 2 completa e validada por simulação.

**O que muda no código:**

1. Definir constantes:
   ```python
   ANCORAS_POR_REGIAO = {
       "upper": ["empurrar_compostos", "remadas", "puxadas", "ombro_composto"],
       "lower": ["squat", "hinge"],
   }
   ```
   Validar a lista com casos reais antes de fixar (e.g., `posterior_ombro`
   deve entrar como âncora? `knee_flexion` em lower?).

2. Adicionar à pré-alocação da Etapa 2: quando a demanda é nível
   `regiao` e há vagas suficientes para compostos (regra 60/40),
   distribuir esses compostos pelas âncoras antes de sortear vagas
   livres.

3. Aplicar **somente em demandas de nível `regiao`**. Se o usuário
   pediu `subregiao` ou `padrao` específico, ele já foi explícito e
   a regra não cabe.

4. Casos de borda:
   - Vagas < número de âncoras: cobrir as vagas com âncoras sorteadas
     uniformemente
   - Vagas > número de âncoras: cobrir todas + sortear o resto

**Entregáveis.**
- PR único, focado, em cima da base estabelecida na Etapa 2.

**Como validar.**
1. Pytest passando (incluindo novo teste: "rotina `upper(3) × 2` tem
   pelo menos 1 composto de cada âncora upper").
2. Simulação: em 1.000 rotinas `upper(3) × 2 treinos`, taxa de
   "rotina sem composto de peito" deve cair de ~baseline atual
   (estimar na Etapa 2) para < 5%.
3. Caso real do `crossover_sentado_only`: regenerar a rotina que
   originalmente exibia o problema e verificar que agora aparece
   composto de peito.

**Riscos.**
- Regra muito rígida pode forçar âncoras quando a configuração não
  suporta (e.g., usuário bloqueou todos os equipamentos de remada).
  Comportamento esperado: gerar aviso e prosseguir, não travar.
- Em rotinas pequenas (`upper(2) × 1`), a regra pode tomar todas as
  vagas e deixar zero espaço para isolados úteis. Definir piso
  razoável de vagas livres.

---

### Etapa 4 — Filtro de cargas (Fase B / HIB2)

**Objetivo.** Aplicar o filtro de cargas grip/lombar/core já
calibrado, agora sobre a base estável das Etapas 2 e 3.

**Pré-requisitos.** Etapas 2 e 3 completas. Avaliação humana dos 20
casos clínicos finalizada (pode acontecer em paralelo às Etapas 2 e 3).

**O que muda no código:**

1. Adicionar campos `carga_grip`, `carga_lombar`, `demanda_core` na
   dataclass `Exercicio` e no `carregar_banco`.
2. Implementar `_bloqueio_cargas(ex_a, ex_b, thresholds)` que retorna
   True se a soma das cargas em qualquer dimensão atinge o threshold
   E ambos os exercícios têm valor ≥ 1.
3. Integrar em `pode_adicionar_ao_bloco` antes da regra de fadiga.
4. Adicionar 3 dropdowns na UI (config geral): threshold por
   dimensão, valores 3-6, default 6/5/6 (HIB2).
5. Adicionar tipo de aviso `relaxado_carga` no sistema de avisos
   (paralelo a `familia_repetida`).

**Entregáveis.**
- PR de motor (campos + função + integração)
- PR de UI (dropdowns + aviso)

**Como validar.**
1. Recalibração HIB2 sobre base nova: regenerar os 20 casos clínicos
   pós-Etapa 3 e confirmar que continuam clinicamente justificados.
   Ajustar thresholds se necessário.
2. Pytest passando.
3. Simulação: blocos solo legítimos preservados, blocos solo forçados
   limitados a < 5% das rotinas.

**Riscos.**
- Pode ser necessário ajustar thresholds pós-Etapa 3 se a
  distribuição de exercícios chegando à Fase 2 mudou
  significativamente.
- Sobrecarga de avisos: se relaxado_carga + familia_repetida +
  incompleta aparecem juntos no modal, planejar UX para não
  poluir.

---

### Etapa 5 — Consolidação do `_buscar_candidato` em sistema de score

**Objetivo.** Transformar a cascata de 16 combinações geo×sub na
função `_buscar_candidato` em um sistema de score explícito, com
amostragem softmax. Preparação direta para a Etapa 7 (penalidades
multi-dimensionais), mas já entrega ganho próprio: variabilidade
real e parâmetros ajustáveis. Resolve também o problema 6 (regra
anti-2-unilaterais cega).

**Pré-requisitos.** Etapas 2, 3 e 4 completas.

**O que muda no código:**

1. Substituir o loop:
   ```python
   for geo in [p1, p2, p3, p4]:
       for sub in [sub1, sub2, sub3, sub4]:
           ...
   ```
   por scoring linear:
   ```python
   def _score_pareamento(candidato, ancora, contexto):
       score = 0
       score += 1000 * (candidato.regiao != ancora.regiao)
       score += 100  * (candidato.padrao != ancora.padrao)
       score += 50   * not_agonista(candidato, ancora, contexto)
       score += 25   * (candidato.purpose == "compound")
       # nova lógica anti-unilateral, sensível ao contraste muscular
       if ja_tem_uni and candidato.unilateral == "unilateral":
           if candidato.regiao == ancora.regiao:
               score -= 75   # 2 unilaterais do mesmo grupo: caro
           else:
               score -= 10   # 2 unilaterais de grupos diferentes: ok
       return score
   ```
2. Substituir "primeiro que passa" por amostragem softmax entre os
   top-K candidatos (K=3 a 5). Isso dá variabilidade real em vez do
   shuffle atual.
3. Expor pesos como constantes nomeadas no topo do módulo (preparação
   para virarem parâmetros do usuário no futuro).

**Entregáveis.**
- PR com refatoração do `_buscar_candidato` e função de scoring
- PR com testes específicos de pareamento (incluindo o caso real
  V-Up Uni + Tríceps Uni + Hollow Hold)

**Como validar.**
1. Caso real do `v_up_uni_pair`: o trio deve ser pareado V-Up Uni +
   Tríceps Uni (regiões diferentes, contraste muscular ideal) +
   Hollow Hold solo, em vez de V-Up + Hollow Hold + Tríceps solo.
2. Diversidade de pareamentos: rodar mesma config 100 vezes com
   seeds diferentes e medir entropia das duplas. Deve subir
   significativamente em relação ao "primeiro que passa".
3. Pytest passando, simulação sem regressão em invariantes.

**Riscos.**
- Os pesos iniciais são chutes informados pela cascata original.
  Vão precisar de calibração via simulação. Não tentar acertar de
  primeira — iterar.
- Amostragem softmax muda comportamento "determinístico-com-shuffle"
  para "estocástico-controlado". Documentar em changelog para o
  usuário entender por que rotinas com mesma config dão pareamentos
  diferentes em proporções diferentes.

---

### Etapa 6 — Trabalho preparatório das tags multi-dimensionais

**Objetivo.** Definir as dimensões de proximidade que vão substituir
a sobrecarga semântica do `variacao_de`. Não muda código — é
trabalho de modelagem que produz especificação para a Etapa 7.

**Pré-requisitos.** Etapas 1–5 completas (estabilizam o motor antes
de mudar o modelo de dados).

**Contexto da etapa:**

Hoje o campo `variacao_de` faz o trabalho de pelo menos três conceitos
diferentes:

1. **Variação estrita** — Supino Reto Halter ↔ Supino Reto Barra:
   mesmo padrão, mesma musculatura, equipamento diferente. Aqui
   `variacao_de` faz sentido literal.
2. **Similaridade funcional** — Prancha Frontal, Prancha Bola, Prancha
   Slideboard: variações entre si. Mas Prancha Lateral é *outro
   exercício* (plano frontal, oblíquos). Empacotar todas como
   `variacao_de = "prancha"` funde duas coisas: variações estritas e
   categoria isométrica de tronco.
3. **Categoria muscular ampla** — todos os 8 tríceps com
   `variacao_de = "Tríceps"`. Não são variações entre si: Francesa,
   Coice, Polia, Testa atacam cabeças diferentes.

O resultado: o mesmo mecanismo (filtro de família) faz três coisas
distintas, e algumas mal. Apertar pra resolver pranchas quebra
tríceps. Relaxar pra resolver tríceps libera pranchas redundantes.

**Insight INTRA, INTER e HISTÓRICO:**

A regra "evitar repetição de família" tem objetivos diferentes em
três contextos:

- **INTRA**: variabilidade biomecânica imediata dentro de um treino.
  Penalidade alta para qualquer proximidade — variação estrita,
  padrão de movimento, plano, equipamento.
- **INTER**: variabilidade entre treinos da mesma rotina semanal.
  Penalidade alta só para variação estrita; média para padrão de
  movimento; baixa para equipamento.
- **HISTÓRICO**: variabilidade ao longo do tempo, considerando
  rotinas passadas do aluno. Penalidade ponderada por recência —
  exposição recente pesa mais que antiga, decaindo gradualmente.
  Resolve o problema de "exercícios alternados que parecem variar
  mas dominam o histórico".

Hoje INTRA e INTER são tratados com o mesmo mecanismo binário, e
HISTÓRICO é considerado apenas via flag de "evitar exercícios da
rotina anterior". A migração para tags multi-dimensionais permite
pesos diferentes por contexto e ponderação temporal no histórico.

**O que produzir nesta etapa:**

1. **Lista de 8–12 grupos de exercícios próximos**, cobrindo os casos
   problemáticos:
   - Pranchas e isométricos de tronco
   - Tríceps (separar por cabeça)
   - Bíceps (separar por inclinação/grip)
   - Supinos (separar por ângulo/equipamento)
   - Remadas (separar por ângulo/grip)
   - Puxadas (separar por grip/posição)
   - Squats (separar por carga axial vs frontal vs unilateral)
   - Hinges (separar por joelho rígido vs flexionado)
   - Etc.

2. **Definição final das dimensões** que entram no banco como colunas
   novas. Proposta de partida (refinar com base nos grupos acima):
   - `familia_estrita` — refinar `variacao_de` para que reflita
     apenas variações biomecânicas do mesmo exercício
   - `padrao_movimento` — granularidade entre `padrao` e
     `familia_estrita` (ex: `iso_anti_extensao` vs
     `iso_anti_lateroflexao`)
   - `musculo_alvo_especifico` — granularidade dentro do mesmo grupo
     (ex: `triceps_cabeca_longa` vs `triceps_cabeca_lateral`)
   - `equipamento_grupo` — agrupamento de equipamentos similares
     (barra livre vs smith vs halter vs polia)
   - `posicao_corporal` — em pé / sentado / deitado / 4-apoios

3. **Tabela de pesos INTRA, INTER e HISTÓRICO** (calibração inicial,
   refina com simulação na Etapa 7):
   ```
                       INTRA     INTER    HISTÓRICO*
   familia_estrita       100       80       60
   padrao_movimento       80       20       30
   musculo_especifico     60       10       15
   equipamento_grupo      20        0        0
   posicao_corporal       30        5        5
   ```
   `*` Pesos do HISTÓRICO sofrem decaimento por recência. Exemplo:
   peso integral para exposições nas últimas 2 semanas, 50% para
   3–4 semanas, 25% para 5–6 semanas, zero para mais antigas. A
   curva de decaimento é parâmetro a calibrar.

4. **Estratégia de preenchimento do banco** para os 125 exercícios.
   Não tudo de uma vez: priorizar as 2–3 dimensões com mais impacto
   (provavelmente `familia_estrita` refinada e `padrao_movimento`).
   Permitir tags vazias ("não se aplica") sem causar erro no motor.

**Entregáveis.**
- Documento `dimensoes_proximidade.md` com os 8–12 grupos, dimensões
  finais, pesos iniciais, e estratégia de preenchimento.
- Atualização do `template_grupos_proximidade.md` (já existe no
  projeto) com decisões.

**Como validar.**
- Cada um dos 6 problemas conhecidos da memória mapeado para uma
  combinação de dimensões + pesos que o resolveria.
- Casos de borda explícitos: prancha frontal vs prancha lateral,
  tríceps francesa vs tríceps polia, supino halter vs supino barra.

**Riscos.**
- Scope creep: tentar definir 10 dimensões em vez de 4. Limite
  rígido: máximo 5 dimensões na primeira iteração.
- Subjetividade da curadoria: pode ser difícil decidir se "Supino
  Inclinado Halter" e "Supino Inclinado Smith" têm o mesmo
  `padrao_movimento` ou não. Documentar a regra de decisão para
  consistência ao preencher os 125 exercícios.

---

### Etapa 7 — Migração do banco e refatoração para sistema de penalidades

**Objetivo.** Preencher os 125 exercícios com as novas tags definidas
na Etapa 6, e migrar o gerador de filtros hard + score linear (Etapa
5) para sistema de penalidades multi-dimensional com pesos
diferenciados nos três contextos: INTRA (mesmo treino), INTER (mesma
rotina) e HISTÓRICO (rotinas anteriores do aluno, ponderado por
recência).

**Pré-requisitos.** Etapa 6 completa.

**O que muda no código:**

1. Adicionar colunas no XLSX e atualizar `carregar_banco` para os
   novos campos.
2. Preencher os 125 exercícios com as tags (curadoria humana com
   regra de decisão documentada da Etapa 6).
3. Substituir o sistema de score da Etapa 5 por sistema de
   penalidades multi-dimensional. A função `_score_pareamento` ganha
   componente de penalidade calculado contra as tags.
4. Implementar os três contextos INTRA, INTER e HISTÓRICO: a função
   de score recebe como parâmetro qual contexto está ativo e usa os
   pesos apropriados.
5. Implementar consulta ao histórico do aluno com ponderação por
   recência:
   - Função `coletar_exposicoes_historico(aluno_id, janela_semanas)`
     que lê do SQLite todas as rotinas do aluno na janela e devolve
     dict `{nome_exercicio: peso_decadente}`. Peso decai conforme a
     curva calibrada (ex: 1.0 nas últimas 2 semanas, 0.5 em 3–4,
     0.25 em 5–6, 0 antes).
   - Esse dict é passado ao `_score_pareamento` quando contexto =
     HISTÓRICO, e penaliza candidatos cujas tags casam com
     exposições recentes.
   - Janela de consulta default: 6 semanas. Configurável.
6. Aposentar (ou reduzir drasticamente o peso de) o filtro hard de
   família. Manter como fallback para compatibilidade, mas a regra
   principal vira penalidade.
7. Expor controles de variabilidade na UI (sliders ou dropdowns):
   - "Variabilidade na semana": baixa / média / alta (ajusta peso
     INTER)
   - "Variabilidade no treino": baixa / média / alta (ajusta peso
     INTRA)
   - "Variabilidade no histórico": baixa / média / alta / desligado
     (ajusta peso HISTÓRICO e janela de consulta)
   - "Evitar repetição de equipamento": ligado / leve / desligado

**Entregáveis.**
- PR de migração do banco (XLSX + `carregar_banco`)
- PR de motor (sistema de penalidades)
- PR de UI (controles de variabilidade)
- Documentação do mapeamento entre controles UI e pesos internos

**Como validar.**
1. Todos os testes pytest passando, incluindo testes específicos
   para cada combinação INTRA/INTER/HISTÓRICO que resolve um problema
   conhecido.
2. Caso real prancha em `core(3)`: nunca deve gerar 3 pranchas
   frontais; deve preferir trio com padrões de movimento distintos.
3. Caso real tríceps em `triceps(2)`: deve aceitar Francesa + Polia
   (cabeças diferentes); deve evitar Polia + Coice (mesma cabeça).
4. Caso de HISTÓRICO: aluno com 6 rotinas anteriores onde Supino
   Inclinado Halter aparece em 4 delas (semanas 1, 3, 5 e a atual
   anterior). Nova geração deve evitar Supino Inclinado Halter
   mesmo se a rotina anterior estrita não o tinha.
5. Simulação A/B: rodar mesmas configs no sistema antigo (Etapa 5)
   e novo (Etapa 7) e comparar diversidade e cobertura.

**Riscos.**
- Etapa grande. Considerar dividir em sub-PRs (migração do banco;
  motor sem UI; UI por cima; HISTÓRICO por cima).
- Calibração dos pesos vai exigir várias rodadas de simulação. Não
  tentar acertar de primeira.
- O filtro hard de família existente pode entrar em conflito com
  penalidades suaves. Ter clareza sobre qual prevalece em cada
  contexto.
- Performance da consulta de HISTÓRICO: aluno com longo histórico
  pode ter dezenas de rotinas. Cachear a consulta por `aluno_id` ao
  longo da geração (a janela não muda durante uma única geração).
- Curva de decaimento do HISTÓRICO é parâmetro sensível. Decaimento
  muito lento engessa rotinas; muito rápido vira "lembra só da
  última semana", redundante com INTER. Calibrar com simulação.
- Mudança de comportamento percebida pelo personal: rotinas vão
  parecer diferentes mesmo em configs antigas. Documentar bem.

---

### Etapa 8 — Explicabilidade do gerador

**Objetivo.** Permitir que o personal audite as decisões do motor.
Cada exercício escolhido carrega o "porquê" — quais critérios
pesaram, quais alternativas foram consideradas, qual foi descartada
e por quê. Vira ferramenta de aprendizado e debugging clínico.

**Pré-requisitos.** Etapa 7 completa. O sistema de penalidades já
calcula scores explícitos por dimensão; basta capturá-los e expô-los.

**O que muda no código:**

1. Adicionar campo `rationale: dict` ao dataclass `Exercicio` (ou ao
   resultado da seleção, dependendo da granularidade desejada). O
   campo guarda:
   - Critérios usados na seleção (lista de dimensões com pesos
     aplicados)
   - Score final do exercício escolhido
   - Top 2–3 alternativas consideradas com seus scores e o motivo
     do descarte (ex: "Supino Inclinado Halter — score 145, descartado
     por penalidade HISTÓRICO 60: aparição há 2 semanas")
   - Slot que esse exercício preencheu (ex: "âncora composta de peito
     em T1")
2. Modificar as funções de seleção (`gerar_sessao_por_demandas`,
   `_buscar_candidato`, função de penalidades) para popular o
   rationale durante a decisão, em vez de descartar a informação.
3. Serializar o rationale junto com `Sessao` (incluir em
   `_sessao_to_dict` / `_dict_to_sessao` no `app_flask.py`).
4. UI: ao clicar em um exercício no card do treino, abrir um modal
   ou drawer que exibe o rationale de forma legível.
   - Versão simples: lista bullet com critérios e alternativas
   - Versão refinada: visualização das alternativas com seus scores
     em barras ou tabela

**Entregáveis.**
- PR de motor (rationale capturado e propagado)
- PR de UI (visualização do rationale)

**Como validar.**
1. Para cada exercício de uma rotina gerada, o rationale deve responder
   "por que esse e não outro" de forma rastreável até as constantes
   de peso usadas.
2. Casos de teste: gerar uma rotina, escolher 5 exercícios aleatórios,
   verificar que o rationale de cada um:
   - Lista as dimensões consideradas
   - Mostra ao menos 2 alternativas com scores
   - Identifica o slot que preencheu
3. Caso de aprendizado clínico: regenerar uma das rotinas problemáticas
   históricas (ex: aquela com Crossover Sentado solo) e usar o
   rationale para confirmar que a Etapa 3 (âncoras) está atuando.

**Riscos.**
- Sobrecarga de informação: rationale completo pode ter dezenas de
  itens. UI deve resumir por padrão e expandir sob demanda.
- Performance: capturar rationale durante a seleção adiciona overhead.
  Manter desativável via flag de configuração (default: ligado em dev,
  configurável em produção).
- Estabilidade do contrato: se o rationale ficar exposto em UI, mudar
  sua estrutura depois quebra a UI. Definir versão estável da
  estrutura antes de expor.

---

## 5. Apêndices

### A. Estratégia de testes formais (detalhamento da Etapa 1)

**Setup.**
- `pip install pytest`
- Arquivo `tests/test_gerador.py` na raiz
- Comando único: `pytest` (alvo: < 30 segundos)

**Categorias de teste:**

**Invariantes** — devem valer em qualquer geração, sob qualquer
configuração:
```python
def test_nenhum_exercicio_aparece_duas_vezes_no_mesmo_treino()
def test_blocos_respeitam_fadiga_maxima()
def test_blocos_respeitam_tamanho_configurado()
def test_exercicios_travados_aparecem_no_resultado()
def test_exercicios_em_equipamentos_bloqueados_nao_aparecem()
def test_max_complexidade_respeitado()
```

**Regressão** — fixar comportamento atual antes de refatorar:
```python
def test_upper_3_lower_2_core_2_3treinos_seed42_snapshot()
def test_full_body_4treinos_seed1_snapshot()
def test_template_empurrar_posterior_seed7_snapshot()
# ... 10–20 configurações representativas
```

**Específicos de problema** — cada problema conhecido vira um teste
que falha hoje e passa depois da etapa que o resolve:
```python
def test_lower_4_distribui_anterior_e_posterior_balanceado()  # Etapa 2
def test_upper_3x2treinos_tem_composto_de_cada_ancora()  # Etapa 3
def test_core_3_nao_gera_3_pranchas_iguais()  # Etapa 7
def test_triceps_2_aceita_francesa_e_polia()  # Etapa 7
def test_v_up_uni_pareia_com_triceps_uni_nao_com_hollow()  # Etapa 5
```

**Princípio.** Quando a etapa que resolve um problema for
implementada, o teste correspondente é movido de "skip" / "expected
fail" para "must pass". Isso documenta progresso objetivamente.

### B. Métricas de validação por simulação

**Harness.** Função que roda o gerador N vezes (default: 1.000) com
uma configuração e retorna métricas agregadas.

**Métricas-chave por etapa:**

- **Etapa 2** (Nível 2):
  - Razão posterior/anterior em `lower(N)` (esperado: ≈ 1.0)
  - Frequência de adutores e panturrilha em `lower(4+)` (esperado: > 30%)
  - Treinos com avisos `incompleta` em rotinas de 3+ treinos (esperado: redução)

- **Etapa 3** (âncoras):
  - Rotinas `upper(3)+` sem composto de peito (esperado: < 5%)
  - Rotinas `lower(2)+` sem squat OU hinge (esperado: < 5%)

- **Etapa 4** (cargas):
  - Blocos solo forçados (não-legítimos): < 5%
  - Bloqueios de carga clinicamente justificados: regenerar e
    revalidar 20 casos clínicos

- **Etapa 5** (score):
  - Entropia de pareamentos (mesma config, seeds diferentes): aumentar
  - Casos específicos: V-Up Uni com Tríceps Uni > 50% das vezes

- **Etapa 7** (penalidades):
  - Diversidade dentro do treino: distância média entre exercícios
    nas dimensões padrao_movimento e familia_estrita
  - Diversidade entre treinos da rotina: idem para INTER
  - Diversidade ao longo do histórico: dado um aluno fictício com 6
    rotinas anteriores, frequência de exercícios "alternados" (que
    aparecem em 3+ rotinas das últimas 6) deve cair vs baseline
    pré-Etapa 7

**Princípio.** Métricas comparam **antes e depois** da etapa, sob a
mesma configuração e mesmas seeds. Não há "resultado bom" absoluto —
só "movimento na direção certa".

### C. Riscos transversais e dívidas conhecidas

**Estado global em `app_flask.py`.** Variáveis globais
(`sessoes_ativas`, `referencias`, `historico_substituicoes`, etc.)
são fonte potencial de bugs sutis. Não é problema enquanto o app é
single-user. Anotar como dívida para revisitar quando o app virar
multi-user.

**Acoplamento sutil entre motor e avisos.** O motor popula
`Sessao.avisos`, serializado e renderizado no frontend. Refatorações
do motor podem mudar estrutura ou número de avisos — o frontend
precisa acomodar. Não é bloqueio, é coordenação.

**XLSX como banco.** Para 125 exercícios e single-user, é adequado.
Para crescimento futuro (multi-user, edição concorrente, mais
metadados), considerar SQLite ou Postgres. Fora de escopo desta
refatoração.

**Performance.** Simulações de 1.000 iterações precisam rodar em
tempo razoável. Se algum estágio ficar lento, considerar caching
dos pools de candidatos por padrão (são imutáveis durante uma
simulação).

### D. Princípio de fallback gracioso

Em qualquer etapa, configurações impossíveis (e.g., `triceps(8)`
único + bloqueio de família estrita) devem:

1. Detectar a impossibilidade na fase de pré-alocação (antes de
   gastar processamento)
2. Avisar o usuário com mensagem específica
3. Flexibilizar uma soft constraint sinalizando explicitamente o
   que foi flexibilizado

Nunca: travar silenciosamente, gerar treino incompleto sem aviso,
ou retornar erro técnico ao usuário final.

### E. Ordem de execução resumida

```
Etapa 1  →  Patch defensivo + testes
   ↓
Etapa 2  →  Nível 2 (pré-alocação global)
   ↓
Etapa 3  →  Âncoras protegidas
   ↓
Etapa 4  →  Filtro de cargas (HIB2)
   ↓
Etapa 5  →  Score consolidado em _buscar_candidato
   ↓
Etapa 6  →  Modelagem de tags (sem código)
   ↓
Etapa 7  →  Migração do banco + sistema de penalidades
            (INTRA / INTER / HISTÓRICO)
   ↓
Etapa 8  →  Explicabilidade do gerador
```

Cada seta é um ponto de validação. Não avançar sem que a etapa
anterior tenha critério de aceitação cumprido e simulação validando
o ganho.

---

## Checklist de leitura antes de iniciar

Antes de transformar este guia em `/plan` no Claude Code:

- [ ] Conferir se a ordem invertida (Nível 2 antes de cargas) é
      aceitável, ou se prefere manter ordem original do
      `memoria_projeto.md`
- [ ] Avaliar os 20 casos clínicos HIB2 (pré-requisito da Etapa 4
      em qualquer ordem)
- [ ] Decidir granularidade dos PRs: cada etapa = 1 PR, ou subdividir
      etapas grandes (Etapa 7 é candidata óbvia a subdivisão)
- [ ] Confirmar que não há mudança em curso no app_flask ou na UI
      mobile que conflite com o motor (a refatoração do motor não
      muda contratos de função, mas pode mudar estrutura de avisos)
- [ ] Snapshot do estado atual (commit limpo, branch dedicada) antes
      da Etapa 1
