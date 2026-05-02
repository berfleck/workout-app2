# Guia de refatoração — Workout App v2

> **Progresso da Etapa 1** (branch `refator-gerador`):
> - Frente 1 — `subregiao` na dataclass — ✅ concluída
> - Frente 2 — cleanup do banco de tríceps — ✅ concluída
> - Frente 3 — cleanup de core (subregiões) — ✅ concluída
> - Frente 4 — cleanup de squat (padrões refinados) — ✅ concluída
> - Frente 5 — setup pytest + harness de simulação — ✅ concluída
>
> **Progresso da Etapa 2** (branch `refator-gerador`):
> - Sub-PR 1 — `pre_alocar_rotina` + `_calcular_escassez` isolados — ✅ concluído
> - Sub-PR 2 — integração + regeneração de snapshots + métricas — ✅ concluído
> - Sub-PR 3 — caching de pools — não foi necessário (perf 2.24s pra 3000 simulações)
>
> Log detalhado em `docs/refatoracao/logs/etapa_2.md`. Próxima: Etapa 3 (âncoras protegidas com peso/obrigatoriedade).

> Documento mestre para conduzir a refatoração do gerador de treinos.
> Sintetiza o roteiro de `memoria_projeto.md`, o design de
> `refatoracao_visao_global.md`, e as recomendações das análises de
> arquitetura (refatorar vs refazer, ordem de execução, modelagem de
> proximidade, testes formais, separação quota/sorteio).
>
> **Não é um patch para aplicar.** É um plano para conduzir N implementações
> sucessivas via Claude Code. Cada etapa tem escopo, critério de aceitação
> e validação próprios — devem virar PRs separados.
>
> **Versão 4** — incorpora: âncoras protegidas em região E subregião com
> peso/obrigatoriedade; separação explícita entre quota (quantos exercícios
> de cada padrão) e sorteio (qual exercício concreto preenche a vaga);
> cleanup de core e squat na Etapa 1; hierarquia treino > rotina no
> balanceamento; HISTÓRICO como terceiro contexto além de INTRA/INTER;
> Etapa 8 nova (explicabilidade).

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

**Distribuição clínica é decidida por quota, não por sorteio cego.**
Princípio fundamental que atravessa todas as etapas. O banco de
exercícios é inerentemente desbalanceado — alguns padrões têm muito
mais variações cadastradas que outros (ex: 11 squats unilaterais vs
6 bilaterais; 17 hinges vs 6 abducoes; 8 tríceps vs 25 supinos).
Isso reflete a realidade da musculação, não falha de cadastro.

O gerador atual sortea aproximadamente uniforme entre o pool de
candidatos viáveis, o que faz a distribuição final reproduzir a
proporção do banco em vez da intenção clínica do usuário. Caso real:
`perna_anterior(3) × 3 treinos` produziu 6 unilateral + 3 bilateral
+ 0 isolado — distribuição que bate quase exatamente com a proporção
11:6 do banco, sem decisão clínica acontecendo.

A refatoração separa duas decisões que hoje estão colapsadas em uma:

- **Quanto de cada padrão entra na rotina** → decisão clínica,
  expressa como quota proporcional aos pesos das âncoras (Etapa 3).
  Independente do tamanho do banco em cada categoria.
- **Qual exercício concreto preenche cada vaga já alocada por
  padrão** → escolha entre candidatos disponíveis, aí sim sorteio é
  apropriado.

A consequência prática: pesos de âncora definem `5 bilateral + 4
unilateral` em 9 vagas. Depois disso, sorteia-se *dentro* do pool
de bilaterais qual exercício específico preenche cada vaga. O banco
decide qual unilateral aparece, mas não quantos unilaterais aparecem.
A inteligência do gerador é justamente proteger a intenção clínica
contra o desbalanceamento natural do banco.

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
| 1 | Viés posterior > anterior em `lower(N)` | Etapas 2 e 3 |
| 2 | Tríceps com 8 ex todos `variacao_de = "Tríceps"` | Etapas 1 e 6 |
| 3 | `subregiao` não está na dataclass | Etapa 1 |
| 4 | Squat unilateral/bilateral é tapa-buraco | Etapa 1 |
| 5 | Padrões âncora sem composto na rotina (caso região) | Etapa 3 |
| 6 | Regra anti-2-unilaterais força pares ruins | Etapa 5 |
| 7 | Distribuição de subregião reproduz banco em vez de quota | Etapa 3 |
| 8 | Core sem subregiões internas | Etapa 1 |

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
mudar comportamento do motor de forma significativa.

**Pré-requisitos.** Nenhum.

**O que muda no código:**

A Etapa 1 tem cinco frentes independentes, cada uma virando seu
próprio PR. Podem ser executadas em qualquer ordem entre si.

**Frente 1 — `subregiao` na dataclass.**

Adicionar campo `subregiao: str` na dataclass `Exercicio`. Preencher
no `carregar_banco` derivando de `PADRAO_PARA_SUBREGIAO`. Trocar
consultas ao mapa pelo atributo direto onde aplicável.

**Frente 2 — Cleanup do banco de tríceps.**

Revisar se `variacao_de = "Tríceps"` faz sentido para todos os 8
exercícios. Provavelmente não — Tríceps Francesa, Polia, Coice, Testa
são exercícios independentes, não variações entre si. Refinar para
que famílias `variacao_de` reflitam variações estritas, não categoria
muscular.

**Frente 3 — Cleanup de core (subregiões).**

Hoje core é tratado como região com padrões diretamente, sem
subregião intermediária. A modelagem refinada introduz duas
subregiões: `core_dinamico` e `core_isometrico`.

Implementação:
- Atualizar `PADRAO_PARA_SUBREGIAO` (ou substituir lógica equivalente)
  para que exercícios de core sejam classificados em `core_dinamico`
  ou `core_isometrico`. A informação já existe na coluna `purpose`
  do banco — basta derivar no `carregar_banco`.
- Sem padrões internos por enquanto. As subregiões existem na
  hierarquia, mas a regra de âncoras subregião (Etapa 3) fica
  dormente para core até padrões serem definidos no futuro.
- UI fica como está. A introdução das subregiões é interna; quando
  o usuário pedir `core(N)`, continua funcionando exatamente igual.

**Frente 4 — Cleanup de squat (refinamento de padrão).**

Hoje `squat` é um padrão único, e a distinção bilateral/unilateral é
feita via filtro na coluna `lateralidade`. A UI já tem botões
`squat_bi` e `squat_uni`, mas eles operam como filtros, não como
padrões reais. A refatoração transforma essa distinção em padrões
reais no backend.

Implementação:
- Migrar a coluna `padrao` no banco: cada exercício hoje classificado
  como `squat` ganha classificação refinada (`squat_bilateral` ou
  `squat_unilateral`).
- Atualizar `PADRAO_PARA_SUBREGIAO`: ambos `squat_bilateral` e
  `squat_unilateral` mapeiam para subregião `perna_anterior`.
- Atualizar lógica do gerador: hoje "filtra padrão squat + filtra
  lateralidade" vira "filtra padrão squat_bilateral OU
  squat_unilateral diretamente".
- UI não muda — botões já existentes simplesmente ficam conectados
  aos padrões reais do backend.

Decisão consciente: outros padrões com versões bi/uni (hinge,
remadas, puxadas, supino) **não** migram nesta etapa. Continuam
usando coluna `lateralidade` como filtro. Apenas squat tem essa
estrutura refinada por opção clínica do personal. Anotado como
dívida deliberada — se um dia ficar inconsistente, revisitar.

Cadeira extensora (único exercício "isolado" de perna_anterior)
fica classificado como `squat_bilateral`. Não cria categoria
`squat_isolado` porque com 1 exercício só não justifica.

**Frente 5 — Setup pytest + harness de simulação.**

Adicionar `pytest` ao projeto e criar estrutura de testes:

1. `tests/test_gerador.py` com:
   - **Testes de invariantes** (devem valer em qualquer geração):
     sem nomes duplicados no mesmo treino, fadiga máxima respeitada,
     blocos com tamanho ≤ configurado, exercícios travados aparecem,
     equipamentos bloqueados não aparecem, max_complexidade respeitado.
     Mínimo 8 testes.
   - **Testes de regressão**: 10–12 configurações representativas
     com `random.seed(N)` fixo e snapshot dos outputs atuais. Geram
     baseline pré-refatoração. Lista sugerida no Apêndice B.

2. Harness de simulação em massa (formalização do que gerou os
   relatórios HIB/HIB2). Função que aceita config + N iterações e
   devolve métricas agregadas: distribuição por padrão dentro de
   subregião, distribuição por subregião dentro de região, taxa de
   avisos, blocos solo, cobertura de âncoras.

**Entregáveis.**
- PR Frente 1: `subregiao` na dataclass e usos atualizados
- PR Frente 2: cleanup do banco de tríceps (decisão documentada)
- PR Frente 3: cleanup de core (subregiões)
- PR Frente 4: cleanup de squat (padrões refinados)
- PR Frente 5: setup pytest, testes de invariante (mínimo 8),
  regressão (mínimo 10 configs), harness de simulação

**Como validar.** Todos os testes passando. `pytest` rodando em
menos de 30 segundos. Harness de simulação produzindo relatório
reproduzível com seed fixa. Comportamento do app inalterado nos
fluxos cobertos pelos testes de regressão (frentes 1, 3, 4 podem
mudar levemente os snapshots — esperado e documentado caso a caso).

**Riscos.**
- Cleanup do tríceps pode revelar outras fronteiras de família mal
  desenhadas — manter escopo controlado e documentar o que ficou
  pra depois.
- Snapshots de regressão capturam o comportamento *atual*, incluindo
  bugs conhecidos. Anotar quais snapshots refletem comportamento
  desejado vs comportamento aceito mas a melhorar.
- Cleanup de squat (Frente 4) muda classificação de padrão de
  exercícios existentes no banco. Verificar que histórico de rotinas
  já salvas em SQLite continua sendo lido corretamente (registros
  antigos podem ter o padrão antigo `squat`; se isso aparecer em
  consultas, manter retrocompatibilidade na leitura).
- Cleanup de core (Frente 3) introduz subregiões internas mas não
  deve mudar comportamento visível. Se algum teste de regressão
  quebrar por causa disso, é sinal de que a derivação foi incorreta.

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

### Etapa 3 — Âncoras protegidas (região e subregião)

**Objetivo.** Garantir que padrões âncora estejam representados nas
proporções clínicas corretas, tanto quando o usuário pede no nível
região (`upper`, `lower`, `core`) quanto quando pede no nível
subregião (`peito`, `costas`, `perna_anterior`, etc). Resolve dois
casos paralelos:
- Caso região: rotina `upper(3) × 2` com peito representado só por
  Crossover Sentado (sem composto).
- Caso subregião: rotina `perna_anterior(3) × 3` produzindo 6
  unilaterais + 3 bilaterais + 0 isolados, reproduzindo a proporção
  do banco em vez da intenção clínica.

**Pré-requisitos.** Etapa 2 completa e validada por simulação.

**Conceitos centrais:**

A regra opera em dois níveis paralelos da hierarquia:

- **Nível região.** Quando demanda é `regiao(N)`, garantir cobertura
  entre as subregiões da região (peito + costas + ombro, ou
  perna_anterior + perna_posterior + panturrilha) e — dentro de cada
  subregião âncora — garantir que pelo menos 1 composto esteja
  presente. Mantém a regra 60/40 composto/isolado já existente.

- **Nível subregião.** Quando demanda é `subregiao(N)`, garantir
  cobertura entre os padrões da subregião (peito tem
  empurrar_compostos + peito_isolado; costas tem remadas + puxadas;
  perna_posterior tem hinge + knee_flexion + abducao). A regra 60/40
  **não** se aplica neste nível — o usuário já foi específico ao
  pedir a subregião, e os pesos das âncoras já capturam a proporção
  clínica composto/isolado natural.

**Demandas de nível padrão** (`hinge(2)`, `squat_unilateral(3)`)
ficam imunes à regra. Usuário foi específico, não cabe interferir.

**Estrutura das âncoras com peso e obrigatoriedade:**

Cada âncora carrega dois atributos: peso relativo (define proporção
nas vagas) e flag `obrigatoria` (define se é cobertura mínima ou
opcional).

```python
ANCORAS_POR_REGIAO = {
    "upper": [
        {"subregiao": "peito",  "peso": 2, "obrigatoria": True},
        {"subregiao": "costas", "peso": 2, "obrigatoria": True},
        {"subregiao": "ombro",  "peso": 1, "obrigatoria": True},
    ],
    "lower": [
        {"subregiao": "perna_anterior",  "peso": 2, "obrigatoria": True},
        {"subregiao": "perna_posterior", "peso": 2, "obrigatoria": True},
        {"subregiao": "panturrilha",     "peso": 1, "obrigatoria": False},
    ],
    "core": [
        {"subregiao": "core_dinamico",   "peso": 1, "obrigatoria": False},
        {"subregiao": "core_isometrico", "peso": 1, "obrigatoria": False},
    ],
}

ANCORAS_POR_SUBREGIAO = {
    "peito": [
        {"padrao": "empurrar_compostos", "peso": 3, "obrigatoria": True},
        {"padrao": "peito_isolado",      "peso": 2, "obrigatoria": False},
    ],
    "costas": [
        {"padrao": "remadas", "peso": 2, "obrigatoria": True},
        {"padrao": "puxadas", "peso": 2, "obrigatoria": True},
    ],
    "ombro": [
        {"padrao": "ombro_composto",  "peso": 3, "obrigatoria": True},
        {"padrao": "ombro_isolado",   "peso": 2, "obrigatoria": False},
        {"padrao": "posterior_ombro", "peso": 1, "obrigatoria": False},
    ],
    "perna_anterior": [
        {"padrao": "squat_bilateral",  "peso": 3, "obrigatoria": True},
        {"padrao": "squat_unilateral", "peso": 2, "obrigatoria": False},
    ],
    "perna_posterior": [
        {"padrao": "hinge",        "peso": 3, "obrigatoria": True},
        {"padrao": "knee_flexion", "peso": 2, "obrigatoria": False},
        {"padrao": "abducao",      "peso": 1, "obrigatoria": False},
    ],
    "panturrilha": [
        {"padrao": "panturrilha", "peso": 1, "obrigatoria": True},
    ],
    # core_dinamico e core_isometrico ficam vazios por enquanto
    # (definir padrões internos em revisão futura)
}
```

Os pesos representam ordens de magnitude clínicas, não medidas
exatas. Vão precisar de calibração via simulação. As listas e os
valores propostos foram validados clinicamente no contexto desta
refatoração.

**Lógica de aplicação — separação quota/sorteio:**

Princípio fundamental (ver Seção 2): o tamanho do banco em cada
categoria não deve influenciar a distribuição final. Pesos definem
quotas; banco define apenas qual exercício específico preenche
cada vaga.

A regra opera em dois passes:

1. **Primeiro passe — obrigatórias.** Garantir 1 representante de
   cada âncora `obrigatoria=True`, na medida em que houver vagas
   suficientes. Em `costas(4) × 1`: remadas e puxadas (ambas
   obrigatórias) ganham 1 vaga cada antes de qualquer outra coisa.
2. **Segundo passe — distribuição proporcional.** Vagas restantes
   são alocadas proporcionalmente aos pesos. Em
   `perna_posterior(6) × 1` com 1 hinge já alocado no primeiro passe:
   restam 5 vagas a distribuir proporcionalmente a hinge:3,
   knee_flexion:2, abducao:1 (total 6 = quotas relativas
   2.5 / 1.7 / 0.8 → arredondamento dá 3 / 2 / 1, mais 1 no hinge
   já alocado = 4 hinges + 2 knee_flexion + 1 abducao em 7 vagas;
   ajustar arredondamento conforme a regra de tie-breaking).
3. **Sortear exercícios concretos dentro de cada padrão.** Uma vez
   fixadas as quotas (ex: 4 hinges, 2 knee_flexion, 1 abducao), o
   sorteio entre candidatos do banco acontece *dentro* de cada
   padrão. Tamanho do banco não muda quotas, só decide qual
   exercício específico preenche cada vaga já alocada.

**Hierarquia treino > rotina:**

Após calcular quotas globais da rotina, distribuí-las entre os N
treinos seguindo a regra:

- Se `vagas_por_treino >= num_padroes_ancora`: balancear dentro do
  treino (cada treino tenta cobrir todos os padrões âncora). Em
  `perna_anterior(3) × 3` com âncoras squat_bilateral e
  squat_unilateral (2 padrões), 3 vagas por treino comportam ambos
  → cada treino fica com mistura.
- Senão: balancear apenas globalmente. Em `perna_anterior(2) × 3`
  com 2 padrões âncora, 2 vagas por treino mal cobrem ambos —
  permitir que treinos individuais sejam concentrados desde que a
  rotina inteira respeite a proporção.

**Casos de borda:**

- **Vagas < número de obrigatórias.** Em `costas(1) × 1`: só uma
  vaga, mas remadas e puxadas são ambas obrigatórias. Resolver por
  sorteio uniforme entre as obrigatórias com seed (preserva
  variabilidade entre rotinas, evita viés sistemático). Gerar aviso
  específico: "âncora X não pôde ser cumprida — sorteio escolheu Y".
- **Âncora obrigatória sem candidatos viáveis.** Usuário bloqueou
  todos os equipamentos de hinge → âncora obrigatória de
  perna_posterior fica sem pool. Gerar aviso explícito ("âncora
  obrigatória de hinge não pôde ser cumprida — substituída por X")
  e prosseguir. Nunca travar.
- **Subregiões com 1 padrão só** (panturrilha, atualmente
  core_dinamico e core_isometrico). Regra é vacuosa: 1 padrão âncora
  = sortear livre dentro dele.

**O que muda no código:**

1. Definir as constantes `ANCORAS_POR_REGIAO` e
   `ANCORAS_POR_SUBREGIAO` com a estrutura acima.
2. Implementar função `calcular_quotas(demanda, vagas)` que recebe
   uma demanda do usuário e devolve dict
   `{padrao: num_vagas_alocadas}` aplicando os dois passes
   (obrigatórias + proporcional).
3. Integrar à pré-alocação da Etapa 2: antes de selecionar
   exercícios concretos, aplicar `calcular_quotas` para fixar
   quantidades por padrão.
4. Implementar distribuição treino > rotina conforme regra acima.
5. Adicionar tipos de aviso específicos: `ancora_nao_cumprida`
   (quando obrigatória vira sorteada por falta de vagas) e
   `ancora_sem_candidatos` (quando obrigatória sem pool viável).
6. Sortear exercícios concretos *dentro* dos padrões já alocados,
   não sobre o pool global.

**Entregáveis.**
- PR único, focado, em cima da base estabelecida na Etapa 2.
- Constantes podem ser carregadas de arquivo de configuração
  (sugestão: YAML) para facilitar calibração futura sem mexer no
  código.

**Como validar.**
1. Pytest passando, incluindo testes específicos:
   - "rotina `upper(3) × 2` tem pelo menos 1 composto de cada
     subregião âncora"
   - "rotina `perna_posterior(2) × 2` tem hinge, knee_flexion e
     abducao com ao menos 1 cada em > 95% dos casos"
   - "rotina `perna_anterior(3) × 3` produz pelo menos 1 squat
     bilateral por treino quando hierarquia treino > rotina ativa"
   - "rotina `costas(1) × 1` gera aviso `ancora_nao_cumprida`"
2. Simulação:
   - Em 1.000 rotinas `upper(3) × 2 treinos`, taxa de "rotina sem
     composto de peito" deve cair para < 5%.
   - Em 1.000 rotinas `perna_anterior(3) × 3 treinos`, distribuição
     bilateral:unilateral deve aproximar 3:2 (proporção dos pesos)
     em vez de 6:11 (proporção do banco).
   - Em 1.000 rotinas `perna_posterior(6) × 1 treino`, distribuição
     hinge:knee_flexion:abducao deve aproximar 3:2:1.
3. Caso real do `crossover_sentado_only`: regenerar a rotina que
   originalmente exibia o problema e verificar que agora aparece
   composto de peito.
4. Caso real do `perna_anterior_sem_isolado`: regenerar a rotina
   `perna_anterior(3) × 3` que produziu 6 uni + 3 bi e verificar
   que distribuição passou a respeitar a quota.

**Riscos.**
- Pesos iniciais são chutes informados pela visão clínica do
  personal. Vão precisar de calibração via simulação. Não tentar
  acertar de primeira — iterar.
- Regra muito rígida pode forçar âncoras quando a configuração não
  suporta. Comportamento esperado: gerar aviso e prosseguir, nunca
  travar.
- Em rotinas pequenas (`upper(2) × 1`), as âncoras obrigatórias
  podem tomar todas as vagas e deixar zero espaço para variação.
  Definir piso razoável de vagas livres ou aceitar comportamento
  determinístico nesses casos.
- Arredondamento de quotas proporcionais precisa de regra clara de
  tie-breaking (ex: priorizar âncora com peso maior em caso de
  empate, ou âncora obrigatória sobre opcional). Documentar.
- Interação com `relaxar_familia`: a regra de âncoras opera em cima
  da pré-alocação por escassez. Quando a flag de relaxar família
  está ativa, isso pode mudar o pool viável de candidatos por
  padrão. Validar que a regra de quotas continua coerente nesse
  caso.

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

**Regressão** — fixar comportamento atual antes de refatorar.
Lista sugerida (10-12 configs cobrindo o leque do app):
```python
# Configurações por região (caso original âncoras protegidas)
def test_upper_3_lower_2_core_2_3treinos_seed42_snapshot()
def test_full_body_4treinos_seed1_snapshot()
def test_template_empurrar_puxar_seed7_snapshot()
def test_upper_3x2treinos_seed11_snapshot()  # caso peito_sem_composto

# Configurações por subregião (caso novo de quota proporcional)
def test_perna_anterior_3x3_seed3_snapshot()  # caso 6uni_3bi_0iso
def test_perna_posterior_2x2_seed5_snapshot()  # viés posterior > anterior
def test_costas_4x1_seed9_snapshot()
def test_peito_3x2_seed13_snapshot()
def test_core_3_seed17_snapshot()  # caso prancha

# Configurações por padrão específico (imune às âncoras)
def test_hinge_2_squat_unilateral_2_seed19_snapshot()
def test_triceps_2_filtro_familia_relax_seed23_snapshot()

# Casos de borda
def test_max_complexidade_baixa_seed29_snapshot()
def test_exercicios_travados_populados_seed31_snapshot()
```

**Específicos de problema** — cada problema conhecido vira um teste
que falha hoje e passa depois da etapa que o resolve:
```python
def test_lower_4_distribui_anterior_e_posterior_balanceado()  # Etapa 2
def test_upper_3x2treinos_tem_composto_de_cada_ancora()  # Etapa 3
def test_perna_anterior_3x3_respeita_quota_3_2()  # Etapa 3
def test_perna_posterior_6_distribui_hinge_kneeflex_abducao_3_2_1()  # Etapa 3
def test_costas_4_distribui_remadas_e_puxadas_paritarias()  # Etapa 3
def test_perna_anterior_3x3_cobre_bi_e_uni_em_cada_treino()  # Etapa 3
def test_costas_1x1_gera_aviso_ancora_nao_cumprida()  # Etapa 3
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
  - Razão posterior/anterior em `lower(N)` (esperado: ≈ 1.0). **Concluído**:
    `lower(4)×3` 0.94 → 1.0; `lower(6)×1` 1.38 → 1.0 deterministicamente.
  - Frequência de adutores e panturrilha em `lower(N)`: critério **ajustado**
    em D2.1 final do user. Comportamento esperado:
    - `lower(2-4)`: NÃO aparecem (acessórias não competem em `qtd ≤ 2 × n_essenciais`).
    - `lower(5+)`: aparecem com frequência crescente.
    - Nunca dominam sobre essenciais (peito + costas + ombro / perna_ant + perna_post).
    **Concluído**: `lower(4)×3` 18.3% → 0%; `lower(6)×1` 5.3% → 100%.
  - Treinos com avisos `incompleta` em rotinas de 3+ treinos: redução **ou
    sinalização explícita**. Pré-Etapa 2 a Fase 1 antiga relaxava silenciosamente
    quando família esgotava — não havia aviso. Pós-Etapa 2 a Fase 0 emite
    avisos `incompleta` rotina-level (slot que nem o relax preencheu) e a
    Fase 0 marca `relaxados` explícitos com badge ↻. Cobertura em quantidade
    não diminuiu, mas a sinalização ficou mais rica.

- **Etapa 3** (âncoras região e subregião):
  - Rotinas `upper(3)+` sem composto de peito (esperado: < 5%)
  - Rotinas `lower(2)+` sem squat_bilateral E sem hinge (esperado: < 5%)
  - Distribuição em `perna_anterior(3) × 3 treinos`: razão
    bilateral:unilateral deve ficar próxima de 3:2 (proporção dos
    pesos), não 6:11 (proporção do banco)
  - Distribuição em `perna_posterior(6) × 1 treino`: razão
    hinge:knee_flexion:abducao deve ficar próxima de 3:2:1
  - Distribuição em `costas(4) × 1 treino`: razão remadas:puxadas
    deve ficar próxima de 1:1
  - Cobertura intra-treino quando vagas comportam: em
    `perna_anterior(3) × 3`, ≥ 80% dos treinos individuais devem
    conter ao menos 1 squat_bilateral E 1 squat_unilateral

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
