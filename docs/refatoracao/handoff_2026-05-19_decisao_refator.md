# Handoff: Investigação Landmine + Decisão Estrutural

**Data**: 2026-05-19
**Branch**: `claude/analyze-landmine-stats-PD5P6` (5 commits, não mergeado)
**Status**: Investigação fechada. Refator estrutural sob deliberação.
**Contexto do usuário**: personal trainer, app feito por **HOBBY** sem
pressão de uso, vibe coding, prioridade absoluta = qualidade. **NÃO usa o
app atualmente.**

---

## TL;DR pra próxima sessão

O usuário está considerando refator estrutural profundo do gerador.
Investigamos uma queixa concreta (remadas landmine sub-representadas)
e o caminho da investigação revelou que **o problema é arquitetural,
não pontual**. As Etapas 6/7/8 (caminho do meio sugerido pela Claude
anterior) viraram cascata de patches; cada nova feature briga com as
anteriores.

**Próximo passo combinado**: construir um **documento de princípios
clínicos** — sem mencionar código, banco, ou vocabulário técnico atual.
Só a visão de personal trainer sobre o que um sistema certo deveria
fazer. A partir disso, decidir nova arquitetura.

Esse handoff existe pra que próximas sessões **não voltem a patchar
dentro do framework atual** sem antes consultar o usuário sobre a
decisão estrutural.

---

## Como a sessão começou

Usuário suspeitou que remadas landmine (LM Neutra, LM Aberta) raramente
apareciam ("não tenho certeza, pode ser viés observacional meu").
Rodamos análise N=10000 em rotina `upper(4) + lower(2) × 1T`:

- LMs aparecem em **9.74% das rotinas** (pré-fix)
- Dentro da família curvada (5 ex, uniforme = 20%):
  - LM Aberta: 13.05% (0.65×)
  - LM Neutra: 15.51% (0.78×)
  - 3 vanillas (Barra/Smith/Halteres): 22-24% cada (1.1-1.2×)
- Viés estatisticamente massivo (χ² p ≈ 10⁻⁴¹)

---

## Achados em ordem cronológica

### 1. `eq_secundario` é dead code (hipótese inicial do usuário)

Aparece em apenas 4 lugares no `gerador_treino.py`:
- linha 874 (dataclass), 1014 (XLSX loader), 4305 + 4396 (display)

**Não entra em nenhum filtro, scoring, predicado, ou pareamento.**
Hipótese inicial do usuário (suspeitava que `Suporte remada landmine`
estaria bloqueando) confirmada como dead code, mas **NÃO era a causa
do viés**.

### 2. Bug de dado (FIX commitado: `6102260`)

LM Neutra e LM Aberta estavam `unilateral=unilateral` no XLSX, mas são
**bilaterais** (T-bar style, 2 mãos no canto carregado). Tag errada
disparava 3 penalidades:

1. **Hard block** via `_compativel_intra` regra 3 (`gerador_treino.py:2157`):
   `costas` está em `SUBREGIOES_LATERALIDADE_HARD` → 2 unilaterais em
   costas mesmo treino → bloqueio total.
2. **`anti_uni_mesmo_grupo` = -75** no pareamento com outro unilateral
   "pull" no bloco.
3. **`anti_uni_diff_grupo` = -10** com qualquer outro unilateral no bloco.

Fix: ambas → `unilateral=bilateral`. Pytest 197 verdes, sem regressão
de snapshot.

**Efeito empírico (N=10000):**
- LM Aberta: 13.05% → 15.51% (0.65× → 0.78×) — **simetria restaurada**
- LM Neutra: 15.51% → 15.45% (basicamente igual)
- Total LMs em rotinas: 9.74% → 10.60% (+0.86 pp)
- Viés residual de 0.77× persistiu — não é mais bug, é design.

### 3. Hipótese do usuário sobre `equipamento_grupo` (REFUTADA)

Usuário propôs mudar `equipamento_grupo` de `barra` pra `landmine`.
Testamos in-memory. **Zero efeito** (bit-idêntico ao baseline). Razões:
- eq_grupo INTRA em costas é `soft_baixo` (-5), 10× menor que pegada (-50)
- LMs e Curvada Barra são MESMA família → `_compativel_intra` regra 1
  bloqueia coexistência intra-treino → colisão nunca dispara
- Nenhuma puxada tem `eq_grupo=barra` (todas corporal/halter/polia)

### 4. ACHADO CENTRAL: pegada como categoria mal-modelada

Usuário lembrou de discussão antiga: "aberta" biomecanicamente É
pronada-wide. Confirmado em `docs/refatoracao/dimensoes_proximidade.md`:

- **linha 575**: `Sub-estrutura: aberta=pronada-wide`
- **linhas 612-621**: tabela com "Curvada Barra + Baixa Aberta = Tolerável
  (ambas pronadas-largas)"

A discussão original previa **matriz 4×4** com `aberta↔pronada` como
colisão parcial. **D2.1 (Etapa 6) fechou em "constante por dim"** mas
deixou nota explícita: *"Se caso concreto aparecer onde Variante a deixa
passar algo claramente diferente, revisita."*

**Este é exatamente esse caso.**

Implicação no scoring atual (`gerador_treino.py:2234`):
```python
if cand.pegada and outro.pegada and cand.pegada == outro.pegada:
    total += pesos_config.pegada.peso_intra(sub_cand)
```

`"aberta" != "pronada"` → 0 colisão. Curvada Barra (pronada) + Puxada
Aberta (aberta) → 0 pena. Biomecanicamente deveria ser -50 ou -25.

### 5. Testamos 3 opções de fix da pegada (script `tools/comparar_opcoes_pegada.py`)

- **A**: re-tag `aberta → pronada` (sem mudar código)
- **B**: matriz 4×4 com `aberta↔pronada = -25` (monkey-patch _score_intra)
- **C**: split em 2 eixos `rotacao + largura`

**Resultados (N=2000):**

| Opção | Rotinas com LM | Família curvada | LM/curvada |
|---|---|---|---|
| Baseline (pós-fix bilateral) | 10.15% | 34.55% | 29.4% |
| A | 11.50% | 27.15% | 42.4% |
| B | **11.50%** | **27.15%** | **42.4%** (idêntico a A) |
| C | 15.00% | 22% | 70%+ (over-correction) |

**Insight crítico**: A e B são bit-idênticas → `SOFTMAX_TOP_K=3` +
`TEMPERATURA=200` fazem qualquer penalty negativa cair fora do top-3
quando há ≥3 candidatos score-0 disponíveis. **Magnitude da penalidade
não importa, só sinal.**

### 6. A + CAP (pegada costas: -50 → -20)

Hipótese: cap reduziria efeito do top-K cutoff.

**CAP é completamente inerte.** Idêntico a A. Mesma razão do item 5 —
enquanto houver ~10 candidatos score-0, top-3 só pega score-0.

### 7. ACHADO CENTRAL: ordem de alocação é problema de design generalizado

Instrumentamos `_selecionar_cand_score_aware` (script
`tools/investigar_ordem_alocacao.py`):

| Subregião | Padrão | % SEM peer | Diagnóstico |
|---|---|---|---|
| costas | puxadas | **100%** | sempre 1º — imune ao INTRA |
| costas | remadas | 34.1% | 2º em 66% (peer puxada) |
| peito | empurrar_isolados | **100%** | sempre 1º |
| peito | empurrar_compostos | 49% | 2º em 51% (peer isolado) |
| ombro/perna_anterior/etc | (1 padrão só) | 100% | não exibe o efeito |

**Em costas=2 (49% das rotinas), puxada SEMPRE alocada primeiro**
(979/979 = 100%). Razão: ordem por escassez. Puxadas tem 12 candidatos,
remadas 14 → puxadas mais escasso → primeiro → sem peer → imune.

Mesmo padrão em peito (10 isolados vs 18 compostos).

**Esta é a FALHA DE DESIGN central que causa os patches em cascata.**

### 8. Distribuição por família de remada

A família **curvada absorve 46.5% dos slots remada** vs share teórico
de 35.7% (5/14). Outras famílias quase uniformes (0.86-1.12×). **Só
curvada tem viés interno significativo** — exatamente porque pegada=pronada
das vanillas é imune ao INTRA quando peer puxada existe.

---

## A discussão estratégica (turno final da sessão)

Usuário expressou frustração: *"a cada geração de treino encontro novos
problemas e temos que encontrar novas formas de tapar buracos"*.
Perguntou sobre CSP/ILP.

### Resposta consolidada

1. O algoritmo greedy sequencial é fundamentalmente o que gera
   ordem-de-alocação, vieses sistemáticos, e patches em cascata.
2. **CSP/ILP (especialmente CP-SAT do OR-Tools)** é a técnica certa:
   declarativa, todos os slots negociam simultaneamente, sem ordem.
3. Preocupação do usuário (*"sistema esconder sistematicamente o que
   dá menor penalidade"*) é legítima MAS resolvível: **fairness como
   first-class na função objetivo** (ou constraint dura: ex "exercício
   X aparece no mínimo Y% num histórico de N rotinas").
4. Refator é 3 dimensões independentes:
   - **Algoritmo**: greedy vs declarativo
   - **Modelo conceitual**: portar regras atuais vs repensar a partir
     dos princípios clínicos
   - **Escopo**: slice (só `pre_alocar_rotina`) vs full rewrite

### Contexto novo revelado pelo usuário no fim da sessão

- Personal trainer, app por **HOBBY**
- **NÃO usa o app atualmente**
- Sem pressão de tempo, sem usuários em produção
- Quer qualidade absoluta, não meio-termo
- Vibe coding — custo/tempo de programação irrelevante

**Isso muda o cálculo.** O conselho anterior de "caminho do meio" (que
gerou Etapas 6/7/8 todas como patches incrementais) presumia restrições
que não existem. **Refator estrutural é o caminho certo.**

Sinais de que o modelo conceitual atual (não só o algoritmo) precisa
revisão, todos vindos do usuário nesta sessão:

- *"acredito que isso foi discutido na refatoração"* (sobre pegada
  aberta=pronada — usuário lembrava, código tinha desviado)
- *"o tipo de pegada é MENOS importante do que a família específica"*
  (intuição clínica diverge do scoring codificado)
- *"esse é um problema de design do app e deve influenciar várias
  categorias"* (percepção de generalização que o sistema não modela)

---

## Próximo passo combinado: documento de princípios clínicos

**NÃO escrever código ainda.**

O passo certo é um documento sem nenhuma menção a "padrão", "subregião",
"ANCORAS", "pegada", "família estrita", "Hamilton", "EPP", etc. **Só a
visão de personal trainer** sobre o que um sistema certo deveria fazer:

- O que é um bom treino de upper?
- Quando 2 remadas são redundantes?
- Quando é OK repetir família entre treinos?
- Como decidiria entre Apoio e Supino se tivesse que escolher 1?
- Quais exercícios são "obrigatórios" no mês? Em que frequência mínima?
- Que decisões hoje toma como personal mas o sistema não captura?
- O que NUNCA pode acontecer (hard) vs preferência (soft)?

A partir desse documento, mapear pra constraints duras, soft, função
objetivo. Aí ver quanto do framework atual sobrevive e quanto é
descartável.

**Método sugerido pra próxima sessão**: Claude faz perguntas guiadas em
sequência, usuário responde em texto, Claude compila em documento novo.

---

## Tools criadas (todas em `tools/`, branch atual)

| Arquivo | Propósito |
|---|---|
| `analisar_remada_lm.py` | Análise base — % aparição das LMs, dist por nome, dist por família curvada, Wilson CI |
| `comparar_opcoes_pegada.py` | Compara baseline + 3 opções A/B/C de fix da pegada |
| `investigar_ordem_alocacao.py` | Instrumenta `_selecionar_cand_score_aware` pra logar ordem + peers |
| `testar_a_cap_pegada.py` | Testa A (re-tag) + CAP (override pesos costas) combinados |

Todas usam seeds 0..N-1 pra reprodutibilidade. Tempos típicos:
~7-12s pra N=2000, ~50s pra N=10000.

---

## Commits no branch (não mergeado)

```
3d548f4  tools: testar A (re-tag) + CAP combinados
4f0493c  tools: investigar ordem de alocação
b7f232c  tools: comparativo das 3 opções de pegada
6102260  fix(banco): LM Neutra + LM Aberta — unilateral → bilateral  [ÚNICO FIX REAL]
b86744c  tools: script de análise estatística para aparição de LMs
```

Único commit que mexe em produção: `6102260` (correção bilateral no XLSX).
Os demais são scripts em `tools/`. Branch pode ser mergeado em main mesmo
durante o refator (o fix bilateral está bem, scripts não fazem mal).

---

## Para a próxima Claude

1. **LER ESTE DOC PRIMEIRO**, depois o `CLAUDE.md`. O `CLAUDE.md`
   descreve a arquitetura atual; este doc descreve por que ela tá em
   reavaliação.

2. **NÃO patchar dentro do framework atual sem checar com o usuário.**
   Se ele trouxer um viés novo ou edge case, lembrar que a decisão
   estrutural está sob deliberação. Resposta certa: *"isso pode ser
   sintoma do que já discutimos no handoff; quer patchar ou aguardar
   o refator?"*

3. **Próximo passo concreto se o usuário pedir pra continuar**: ajudar
   a estruturar o documento de princípios clínicos via entrevista guiada.

4. **Sugestão de abertura pra entrevista**:
   > "Imagine um aluno novo, 35 anos, treinado, 4 treinos/semana. Pense
   > num upper que você desenharia pra ele — no papel, sem pensar em
   > código. Que padrões de movimento você quer cobrir? Por quê esses?
   > E o que NÃO pode acontecer nesse upper?"
   
   Fazer **uma pergunta por vez**, esperar resposta, depois aprofundar.
   Não dump de 10 perguntas — vira survey, não conversa.

5. **Compilar respostas em documento novo** separado deste handoff
   (proposta: `docs/refatoracao/principios_clinicos.md`). Atualizar
   este handoff com link quando o doc de princípios começar a existir.

6. **Não invente vocabulário técnico do usuário.** Se ele diz "pegada
   é menos importante que família", anote essa frase exata. Não traduza
   pra "soft_alto vs hard" sem confirmar.

---

## Atalhos pra checagem rápida

- Estado pós-fix bilateral, N=10000: `python tools/analisar_remada_lm.py --n-iter 10000`
- Confirmar que ordem-de-alocação ainda é o problema: `python tools/investigar_ordem_alocacao.py`
- Lista de famílias de remada no banco: ver achado #8 ou rodar `analisar_remada_lm.py`
