# Sessão 2026-05-18 — Cadastros pullover-mitigation + tag plano nos Apoios + tiebreaker aleatório

Data: 2026-05-18
Branch: `feat/cadastros-pullover-mitigation`
Commits: `1ed8217` (cadastros + Apoios) + `f45a7f9` (tiebreaker)
Status: branch pronta para revisão / PR para `main`

Contexto inicial: usuário reportou que Pullover aparecia em "100% das
rotinas" geradas no app (4-10 rotinas testadas manualmente na UI). A
investigação descobriu dois problemas distintos que pareciam um só, e
expandiu pra incluir o viés Apoio×Supino em peito (documentado em
`analise_vies_apoios_vs_supinos.md`).

---

## 1. Investigação inicial — diagnóstico do Pullover

### 1.1 Primeira hipótese errada (rejeitada pelo próprio usuário)

Sugeri inicialmente que o problema estava no `plano_corporal=pullover`
funcionando como "âncora soft INTER" descrita na Seção 2 G3 da
`dimensoes_proximidade.md`. Sondagem empírica desmentiu: a tag
`plano_corporal=pullover` só dispara quando 2 exercícios têm ambos a
mesma tag, e isso só rola entre Pullover Halteres + Pullover Polia
(ambos família `Pullover`, bloqueados pelo hard INTRA família antes do
score chegar). Plano_corporal é efetivamente NO-OP pra Pullover.

### 1.2 Diagnóstico correto — pigeonhole das famílias de puxadas

Padrão `puxadas` tinha 3 famílias (`Barra`, `Puxada`, `Pullover`).
Mecanismo:

- Cycling do `_decompor_demanda_subregiao` distribui 1 puxada por
  treino em `costas(2)×2` (4 slots costas → 2 remadas + 2 puxadas).
- No T2 slot puxada, score INTER família `-40` penaliza repetir família
  alocada em T1.
- Com 3 famílias e pressão pra "espalhar", Pullover entra como 3ª
  caixa em ~50-60% das rotinas.

### 1.3 Tentativa malsucedida — Solução 3 (peso INTER ponderado por tamanho)

Implementei atenuação do peso INTER `familia_estrita` em função do
tamanho do pool da família. Defaults `{4: 0.3, 3: 0.6, 1: 1.0}`:
famílias com ≥4 variantes têm penalty INTER atenuada (era -40, vira
-12), incentivando o gerador a repetir família grande entre treinos em
vez de buscar uma 3ª família pequena.

Resultado empírico:
- `puxadas(2)×2`: -10pp (efeito real)
- `costas(2)×2`: 0pp (NO-OP — Pullover não muda)

Análise: a Sol 3 só atua em REPETIÇÃO INTER. Quando o cand é Pullover,
não há repetição → score 0 → continua no top-K como antes. Reduzir
penalty dos repetidores não puxa eles pro top-K.

Usuário rejeitou conceitualmente: "ter mais variações não significa
que o exercício é mais importante e deve aparecer mais". Concordou
parcialmente: tamanho de família é proxy enviesado de centralidade
clínica.

Solução 3 foi **revertida** no commit `1ed8217`.

---

## 2. Descoberta do segundo problema — Apoio dominando Supinos em peito

Durante a sondagem em peito (cenário diferente do Pullover), descobri
viés grave: em `peito(2)×2`, Supino Reto aparecia em **0 das 300
rotinas** testadas, enquanto Apoio aparecia em 512 slots compostos.

### 2.1 Causa raiz — diferente do Pullover

Apoios têm `plano_corporal=NaN` (omissão de cadastro). Supinos têm
`plano=reto` (Supino Reto/Fechado/Com Anilha/Com Barra/Com Halteres)
ou `plano=inclinado`. Isolados de peito (Crossover, Crucifixo
Halteres) também têm `plano=reto`.

Quando o gerador escolhe o composto do T1 depois do isolado (Crossover
Sentado já alocado, plano=reto):

- Apoio: score INTRA = 0 (NaN não dispara penalty)
- Supino Reto: score INTRA = -50 (plano=reto compartilhado com isolado)
- Supino Inclinado: score INTRA = 0 (plano=inclinado ≠ reto)

Top-K=3 = [Apoio, Apoio Ajoelhado, Apoio Elevado] (pela ordem do
XLSX) — Supino Reto fica fora porque está em -50, Apoio sempre vence.

**Mesmo mecanismo do Pullover (top-K + ordem XLSX + empate) mas com
duas camadas:** (i) Apoios escapam do penalty `plano` por terem tag
vazia; (ii) Supinos Reto levam penalty espúrio do isolado e ficam
fora do top-K.

### 2.2 Validação cruzada com doc existente

Descobri que esse problema já tinha sido investigado em
`docs/refatoracao/logs/analise_vies_apoios_vs_supinos.md` (2026-05-18).
O doc oficial chegou ao **mesmo diagnóstico** e propôs a **mesma
solução** (Opção 1: preencher `plano_corporal=reto` nos 4 Apoios). O
doc também testou empiricamente — S1, n=1000 — e mostrou que essa única
mudança resolve o caso:

| Métrica | Baseline | S1 (Apoios=reto) |
|---|---:|---:|
| % Apoios slots compostos peito | 69.4% | 33.3% |
| % Supinos Reto | 2.3% | 27.5% |
| Rotinas com ≥1 Supino com Barra | 1.9% | 34.1% |
| Rotinas só com Apoios | 9.2% | 0.0% |

Minha sondagem **reproduziu exatamente esses números** após cadastrar
a tag — validação cruzada perfeita.

### 2.3 Decisão de design — confirmação clínica

Conceito: tag `plano_corporal=reto` no Apoio **não serve pra
discriminar dentro da família Apoio** (hard INTRA família já bloqueia).
Serve pra que Apoios participem do mesmo eixo "reto vs inclinado" que
Supinos. Biomecanicamente, Apoio É movimento de peito reto (tronco
horizontal/quase horizontal, push horizontal).

Decisão de Apoio Elevado (usuário): versão padrão é mãos elevadas (mais
fácil) → tag `reto` (tronco mais ereto, peito inferior).

---

## 3. Avaliação de proposta paralela (outra sessão)

Usuário colou análise de outra sessão Claude que diagnosticava ambos
problemas como **um único pigeonhole sistêmico** em 8 padrões com 2-3
famílias, e propunha **reduzir peso INTER família global** de -40 pra
-20.

### 3.1 Onde a outra sessão acertou

- Mapeamento dos 8 padrões com 2-3 famílias é observação sistêmica útil
- Argumento contra split de família por pegada (correto — pegada não
  muda família em nenhum outro lugar do app)
- Princípio de mudança mínima e reversível

### 3.2 Onde a outra sessão errou (validado empiricamente)

- **Erro categorial**: agrupou peito + puxadas como "mesmo viés". Não
  são — peito é INTRA cross-padrão (plano), puxadas é INTER pigeonhole.
- **Predição quantitativa falha**: "Pullover puxadas(2)×2 ~40%" não
  se confirmou (ficou em 84% empírico com INTER 0.4).
- **Não resolve peito**: empíricamente, reduzir INTER global mantém
  Supino Reto em 0 em `peito(2)×2`. Doc analise_vies já tinha
  estabelecido que peito precisa de fix de DADO (tag), não algoritmo.
- **Cleanup proposto** (remover `plano_corporal=pullover` dos
  Pullovers) ignora uso clínico cross-família com Pulldown.

### 3.3 Síntese

A análise paralela tem valor metodológico (mapa dos 8 padrões) mas
erra no diagnóstico de peito. A solução final adotada combina:

- Doc analise_vies (peito): tag `plano=reto` nos Apoios — adotado
- Minha investigação (Pullover): tiebreaker aleatório no softmax — adotado
- Cadastros novos (10 ex): aceito pelo usuário antes da sessão de fix

Reduzir INTER global foi **descartado** (efeito comparável à Sol 3 que
já estava sendo revertida, mais risco em padrões com 4+ famílias).

---

## 4. Solução final — Caminho C (tiebreaker aleatório)

### 4.1 Diagnóstico

`_selecionar_cand_score_aware` usa `scored.sort(key=lambda t: t[1],
reverse=True)`. Sort estável + ordem do XLSX = candidatos com score
igual mantêm a ordem original. `SOFTMAX_TOP_K = 3` pega os 3 primeiros
do empate.

Concretamente: Pullover Halteres (row 80) + Pullover Polia (row 81)
ficam nas 2 primeiras posições do empate em score 0 → entram no top-K
de forma determinística → sorteio softmax dá ~50% Pullover por slot.

### 4.2 Fix — 1 linha modificada

```python
# Antes
scored.sort(key=lambda t: t[1], reverse=True)
# Depois
scored.sort(key=lambda t: (-t[1], random.random()))
```

A tupla `(-score, random)` preserva ranking por score e desempata
uniformemente em ties.

### 4.3 Por que isso é "fix de viés" e não "mudança de modelagem"

Não introduz lógica nova. Quando o sistema diz "esses N candidatos têm
mesmo score", hoje ele tendencia pros primeiros do XLSX por
side-effect do sort estável. Com fix, sorteia uniformemente — o
comportamento que o softmax já deveria ter por princípio.

---

## 5. Mudanças finais no banco — 10 cadastros

10 novos exercícios cadastrados no XLSX (137 → 147 linhas):

### 5.1 Itens do Anexo 4.2 (6 cadastros)

| # | Item | Família | Padrão | Subregião |
|---|---|---|---|---|
| 18 | Crucifixo Inclinado Halteres | crucifixo | empurrar_isolados | peito |
| 21 | Serrote Aberto (pegada=aberta) | unilateral | remadas | costas |
| 22 | Barra c/ Borracha | Barra | puxadas | costas |
| 23 | Puxada Unilateral Polia | Puxada | puxadas | costas |
| 24 | Pulldown Braço Estendido | **Pulldown** (nova) | puxadas | costas |
| 27 | Tríceps Francês Corda | Tríceps Francês | triceps | bracos |

### 5.2 Cadastros fora do Anexo (4 novos)

| Item | Família | Padrão | Subregião | Lateralidade |
|---|---|---|---|---|
| Stiff B-Stance | stiff | hinge | perna_posterior | unilateral |
| Agachamento Goblet Rampa | **calcanhar_elevado** (nova) | squat_bilateral | perna_anterior | bilateral |
| Agachamento Smith Rampa | **calcanhar_elevado** | squat_bilateral | perna_anterior | bilateral |
| Kickback Polia | **Kickback** (nova) | hinge | perna_posterior | unilateral |

3 famílias novas no banco: `Pulldown`, `calcanhar_elevado`, `Kickback`.

### 5.3 Famílias em puxadas após cadastros

| Família | ANTES | DEPOIS |
|---|---|---|
| Barra | 4 (Fixa, Iso, Aberta, Supinada) | **5** (+ c/ Borracha) |
| Puxada | 3 (Aberta, Neutra, Supinada) | **4** (+ Uni Polia) |
| Pullover | 2 (Halteres, Polia) | 2 |
| Pulldown | — | **1** (Braço Estendido) |

### 5.4 Apoios atualizados

4 Apoios receberam `plano_corporal=reto`:
- Apoio (row 12)
- Apoio Ajoelhado (row 13)
- Apoio Elevado (row 14) — decisão: mãos elevadas (mais fácil)
- Apoio Fechado (row 128)

---

## 6. Resultados empíricos finais (500 iters por cenário)

### 6.1 Pullover em puxadas (evolução por etapa)

| Cenário | Original | + Cadastros | + Apoios=reto | + Tiebreaker | Δ total |
|---|---:|---:|---:|---:|---:|
| `costas(2)×2` | 60.0% | 49.3% | 49.8% | **38.8%** | -21.2pp |
| `puxadas(2)×2` | 97.5% | 93.3% | 91.4% | **81.8%** | -15.7pp |
| `puxadas(1)×2` | 66.0% | 53.3% | 52.0% | **37.8%** | -28.2pp |
| `upper(4)×2` | 53.5% | 58.0% | 57.6% | **27.6%** | -25.9pp |
| `upper(6)×2` | 78.0% | 77.0% | 76.4% | **39.6%** | -38.4pp |

Pulldown ganha presença consistente: 9-12% nos cenários (era 0% em
upper antes do tiebreaker).

### 6.2 Apoio × Supino em peito (cenário B do doc — uso real 3T)

Reproduziu **exatamente** os números do S1 do doc analise_vies + leve
melhora pelo tiebreaker:

| Métrica | Baseline | + Apoios=reto (commit 1) | + Tiebreaker (commit 2) |
|---|---:|---:|---:|
| % Apoios slots compostos peito | 69.4% | 33.3% | **30.7%** |
| % Supinos Reto | 2.3% | 27.5% | **31.3%** |
| % Supinos Inclinado | 28.3% | 39.2% | **38.0%** |
| Rotinas com ≥1 Supino com Barra | 1.9% | 34.1% | **34.8%** |
| Rotinas só com Apoios | 9.2% | 0.0% | 0.0% |

Distribuição final entre 3 famílias compostos peito: ~31% Apoio /
31% Supino Reto / 38% Supino Inclinado — equilíbrio que o personal
espera clinicamente.

---

## 7. Validações

- **pytest**: 202 passed + 1 skipped + 13 snapshots OK
- **harness**: 16/16 OK (4.1 = 14.93%, 4.2 = 43.97%)

Mudanças nos testes:

- `test_filtro_carga_realmente_dissolve_par_conhecido`: fixture HIB2
  atualizada 2× nesta sessão (banco mudou + tiebreaker mudou sequência
  aleatória). Estado final: **seed=358**, par `{Stiff Barra Smith,
  Remada Baixa Aberta}`.
- `test_crossover_sentado_coexistencia_INTER_e_rara_pos_caminho_A`:
  Migrado de `SEEDS` (n=5) pra nova **`SEEDS_ESTATISTICAS`** (n=50).
  Tiebreaker introduziu variância maior — n=5 com granularidade 20%
  por seed ficou frágil (1-2 coexistências extras saltavam acima do
  cap). Distribuição real medida em n=200 é ~8%, bem abaixo do cap 40%.
- 19 snapshots de regressão regenerados (7 no commit dos cadastros +
  12 no commit do tiebreaker). Shifts benignos por mudança de seed,
  sem regressão funcional.

---

## 8. Decisões fechadas (não reabrir sem motivo forte)

### 8.1 Tamanho de família NÃO é proxy de centralidade clínica

Rejeitado conceitualmente pelo usuário durante a sessão. Atenuação do
peso INTER em função do tamanho (Solução 3) e bias positivo por
tamanho (Solução 4A) foram **descartados**. Implicação: se a próxima
sessão considerar mexer em peso por família, **precisa ser por
curadoria explícita** (ex: coluna `peso_frequencia` no XLSX) ou
critério clínico estabelecido — não derivar do banco.

### 8.2 `plano_corporal=pullover` no Pulldown Braço Estendido

Mantido conforme Anexo 4.1 item 24 (Seção 2 G3). Captura afinidade
biomecânica cross-família entre Pullover (Halteres/Polia) e Pulldown
Braço Estendido (todos extensão de ombro com braço estendido). Não é
"redundante com familia_estrita" — é exatamente o uso da dim
não-universal definido no Anexo.

### 8.3 Pulldown Braço Estendido como família estrita SEPARADA

Mantido. Justificativas:
- Equipamento diferente (polia ajustável vs halter livre)
- Posição do tronco diferente (em pé vs deitado)
- Curva de resistência diferente (variável vs constante)
- Purpose diferente (Pulldown=isolation; Pullover=compound)

Afinidade biomecânica capturada pela dim `plano_corporal=pullover` —
mecanismo correto, não exige fundir família.

### 8.4 Princípio "dado primeiro, algoritmo depois"

Doc `analise_vies_apoios_vs_supinos.md` estabeleceu: "A solução é
exclusivamente Opção 1 — sem mudança no algoritmo. Cadastro de dado,
não refatoração estrutural." Esta sessão **honra** o princípio pro
caso peito (só preencheu tag) **e estende** pra incluir tiebreaker
algorítmico só onde dado não resolve (caso Pullover — todos os
exercícios em puxadas já têm tags preenchidas, viés vem da ordem do
XLSX).

### 8.5 Caso peito 100% resolvido por dado; Pullover residual ~38%

Pra cair pra <30% em Pullover precisaria mecanismo adicional. Opções
abertas (não tomadas nesta sessão):

- Remover `plano_corporal=pullover` do Pulldown — destrava ele como
  4ª caixa, mas perde sinal clínico cross-família
- Curadoria de pesos clínicos por exercício (`peso_frequencia`)
- Aumentar `SOFTMAX_TOP_K` quando há mais N candidatos empatados

Decidir só se aparecer reclamação real do usuário pós-deploy.

---

## 9. Estado final da branch `feat/cadastros-pullover-mitigation`

2 commits acima de `main`:

```
f45a7f9 Tiebreaker aleatório no softmax do score-aware
1ed8217 Cadastros peito/puxadas/perna + tag plano_corporal nos Apoios
```

Arquivos modificados líquidos:

- `banco_exercicios.xlsx` — +10 cadastros + 4 Apoios c/ plano=reto
- `gerador_treino.py` — 1 linha (tiebreaker no `_selecionar_cand_score_aware`)
- `tests/test_carga_filter.py` — fixture HIB2 atualizada (seed=358)
- `tests/test_demanda_incompleta.py` — `SEEDS_ESTATISTICAS` separada
- `tests/__snapshots__/test_regressao.ambr` — 19 snapshots regenerados
- `tools/cadastrar_10_exercicios.py` — script one-shot (registro
  de auditoria, conforme convenção `tools/` do projeto)

Net effect: **mudanças minimais em algoritmo** (1 linha) +
**correções de dados** (XLSX) + **ajustes de teste obrigatórios**.

---

## 10. Próximos passos / follow-ups abertos

1. **Abrir PR pra `main`** — quando o usuário decidir mergear
2. **Investigar Supino com Halteres = 57 slots** (anomalia residual
   após Apoios=reto, identificada no doc analise_vies §7). Provável
   conflito de `eq_grupo=halter` com Supino Inclinado Halteres via
   INTER (-4 penalty). Não bloqueia, fica como item de manutenção.
3. **Pullover residual ~38%** — se aparecer reclamação real pós-deploy,
   considerar Opções 8.5. Não bloqueia.
4. **Validação clínica em uso real** — usuário gerar rotinas reais
   pós-merge e confirmar que Supino com Barra agora aparece em ~1/3
   das rotinas (vs 1.9% antes) e Pullover deixou de saturar.

---

## Cross-references

- `docs/refatoracao/logs/analise_vies_apoios_vs_supinos.md` — análise
  oficial do caso Apoio×Supino (mesma conclusão validada cruzadamente)
- `docs/refatoracao/logs/analise_vies_upper.md` — investigação inicial
  do viés upper (predecessor de analise_vies_apoios)
- `docs/refatoracao/dimensoes_proximidade.md` — Seção 2 G3 (Pulldown,
  Pullover, plano_corporal não-universal), Anexo 4.1 itens 18-27
  (cadastros novos), Seção 8.15 (status pós-Etapa 8)
- `tools/cadastrar_10_exercicios.py` — script de cadastro com todas as
  dimensões dos 10 exercícios novos
- `gerador_treino.py:2564-2573` — `_selecionar_cand_score_aware` com
  tiebreaker aleatório
- `pesos_proximidade.py` — intocado nesta sessão (Sol 3 revertida)
