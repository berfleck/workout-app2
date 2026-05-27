# MVP — S-T4 variedade INTRA dentro de subregião

**Data**: 2026-05-29
**Branch**: `frente-s-t4-variedade-intra` (a partir de main, aguarda
merge FF)
**Bloco**: 4 do roadmap CSP (refinamentos pós-E.1) — última frente do
bloco que faltava cobrir
**Catálogo**: Seção 2 ESCOPO TREINO

---

## Por que esta frente existiu

Lacuna verbalizada por Bernardo durante a prep da S-E1 (commit
`06a56d1`, 2026-05-27):

> "puxada aberta fixada primeiro → remada aberta penalizada → solver
> do antigo escolhia remada neutra mesmo quando aberta+aberta era ideal"

S-E1 (mergeada 2026-05-28) cobriu proximidade biomecânica **cross-
treino**. Mas a metade INTRA-treino do mesmo conceito ficou aberta —
em `costas(3)` no MESMO treino, o solver hoje não tinha sinal pra
penalizar 3 puxadas/remadas todas com pegada aberta. H-T1/T2/T3 hard
não pega (famílias distintas). `_score_intra` do motor antigo
(`gerador_treino.py:2236`) tinha exatamente essa parte; CSP novo só
tinha S-B1 (agonistas intra-bloco) e S-B5 (região intra-bloco), nada
de pegada/plano/eq INTRA.

---

## Auditoria PRÉ (2026-05-29)

Antes de codar, rodada auditoria N=30 com config canônica + Jose Silva
(aluno real cadastrado, intermediario, hipertrofia) — `tools/sondar_st4_variedade.py`.

### Setup `subregiao costas(2) × 1T`

| Métrica | PRÉ |
|---|---|
| Pegada repetida | **50.0%** (15/30 pares) |
| Plano repetido | 0% (todos pareados em planos distintos no banco) |
| Equipamento repetido | 46.7% |

### Setup `jose_silva_T1T2` (config real do aluno)

T1: `bracos(1) + peito(2) + ombro(1) + perna_posterior(2) + core_dinamico(1)`
T2: `bracos(1) + costas(3) + perna_anterior(2) + core_isometrico(1)`

| Métrica | PRÉ |
|---|---|
| Pares INTRA-sub total | 180 |
| Pegada repetida geral | 20.6% |
| Plano repetido geral | 10.6% |
| **costas(3) — pegada repetida** | **41.1%** (37/90 pares) |
| **peito(2) — plano repetido** | **63.3%** (19/30 pares) |

100% das 30 rotinas (Jose Silva) tinham ≥1 par sub-ótimo. Baseline
forte. JSON em `logs/st4_variedade_pre.json`.

---

## Sessão clínica pré-código com Bernardo

Pra calibrar a frente, mostrei 10 casos concretos do PRÉ (puxada aberta
+ remada aberta, supino fechado + crucifixo halteres, etc) e pedi
opinião clínica. Bernardo destilou em 3 regras:

- **R1** Pegada repetida em costas entre puxadas/remadas "normais" →
  penalizar.
- **R2** Plano repetido em peito entre supinos/crucifixos → penalizar.
- **R3** Exceções biomecânicas:
  - **Pullover/Pulldown** opta fora de **pegada** (vertical, biomec
    distinta).
  - **Crossover/Crossover Sentado** opta fora de **plano** (cabo,
    biomec distinta do supino/crucifixo livre).

### Marcadores estruturais já existentes no banco

- Pullover Halteres / Pullover Polia / Pulldown Braço Estendido
  têm **`plano_corporal == "pullover"`** (já no XLSX).
- Crossover / Crossover Sentado têm **`variacao_de == "crossover"`**.

### Decisão de modelagem das exceções: **Opção C — apagar células**

Bernardo propôs: "retirar pegada dos exercícios que não devem ser
influenciados por ela". A solução é elegante e nativa do motor — o
helper `_pegada_code_do_ex` (linha 186 do `gerador_csp.py`) já retorna
sentinela única por slot quando `ex.pegada` é falsy: `BASE_VAZIA + sid`.
Slot 1 e slot 2 com pegada vazia recebem codes distintos → `same_pegada`
reifica false → não dispara penalty.

Lista de células a apagar no XLSX (Bernardo edita manualmente):

| Exercício | Coluna a apagar |
|---|---|
| Pullover Halteres | `pegada` |
| Pullover Polia | `pegada` |
| Pulldown Braço Estendido | `pegada` |
| Crossover | `plano_corporal` |
| Crossover Sentado | `plano_corporal` |

**Implementação não depende do XLSX**: o motor já trata vazio
corretamente. Quando o XLSX for atualizado (e o Google Drive
sincronizar — sessão fechou com o arquivo ainda não-modificado no disco,
provavelmente sincronia pendente), as exceções entram em vigor sem mais
código.

### Pesos cravados

`peso_st4_pegada = 12`, `peso_st4_plano = 12`, `peso_st4_eq = 3`.

Hierarquia INTRA > INTER seguindo Seção 8.9/D3.1 da
`dimensoes_proximidade.md` (multiplicador ~1.25 sobre S-E1=10/10/2).
Bernardo cravou voto via "confiar na sua decisão". Calibrar via
sondagem PÓS se necessário.

### Wire em /regerar — diferente da S-E1

Bernardo questionou: se /regerar tem N-1 treinos já congelados, S-E1
não deveria considerar eles também? Resposta: **sim, é lacuna real,
mas frente separada**. Hoje `treino_regerar` usa `gerar_treino_csp`
(1 treino só), não tem conceito de "slot de outro treino existindo só
pra penalty cross-soft". Estender exige refator (Caminho A: reusar
`gerar_rotina_csp` com slots dos outros treinos travados pool=1 +
flag `participa_cross_soft=True`; ou Caminho B: novo parâmetro
`contexto_fixo` no motor). Registrado em
`memory/project_pendencia_se1_regerar.md`. Atacar junto com S-H1
quando for o caso.

**S-T4 é INTRA-treino** — vive dentro do treino sendo gerado, funciona
em ambas rotas. Ativada em `/gerar` E `/regerar`.

---

## Implementação

### Diff arquitetural

`gerador_csp.py` (~120 linhas tocadas):

1. **Refator IntVars compartilhados S-E1↔S-T4**: extraiu construção
   de `pegada_idx/plano_idx/eq_idx` pra dentro de `if usa_se1 OR
   usa_st4`. Cada IntVar por dim criado uma vez por slot quando
   qualquer das duas frentes usa peso > 0. Pares cross-treino (S-E1) e
   pares intra-treino (S-T4) leem os mesmos IntVars sem duplicação.
2. **Cache `subs_possiveis_por_sid`** também compartilhado.
3. **Bloco S-T4 novo** (`gerador_csp.py:1822-1872`): espelho exato do
   S-E1, predicado mudando de `t1 < t2` (cross) pra `t1 == t2, sid1 <
   sid2` (INTRA). BoolVars `same_sub` distintas por par INTRA (par
   INTER e INTRA são pares disjuntos porque t_idx muda).
4. **Args propagados** em 4 funções: `_construir_modelo`,
   `_resolver_legacy`, `_resolver_com_variedade`, `gerar_rotina_csp`,
   `gerar_treino_csp`. `teto_por_termo` no
   `_resolver_com_variedade` incluiu os 3 pesos S-T4.

`app_flask.py`:

1. 3 constantes `_PESO_ST4_*_DEFAULT = 12/12/3`.
2. Wire em `/gerar` (call-site de `gerar_rotina_csp` linha ~2066).
3. Wire em `treino_regerar` (call-site de `gerar_treino_csp` linha
   ~2440). S-R1 e S-E1 continuam fora desta rota (decisão
   estrutural — cross-treino não dispara com 1 treino).

### Exceções biomecânicas: cobertas pelo banco

Tratamento via dim vazia no XLSX (sentinela única por slot do code
helper) — quando Bernardo apagar as 5 células planejadas, Pullover/
Pulldown deixam de competir em pegada; Crossover deixa de competir
em plano. Zero código adicional no motor — princípio do refator
declarativo: regra clínica curada vive no banco, não no .py.

---

## Sondagem PÓS

Mesmos 2 setups, pesos S-T4 = 12/12/3.

### `subregiao costas(2) × 1T`

| Métrica | PRÉ | PÓS |
|---|---|---|
| Pegada repetida | 50.0% | **0.0%** |
| Equipamento repetido | 46.7% | **0.0%** |

### `jose_silva_T1T2`

| Métrica | PRÉ | PÓS |
|---|---|---|
| Pegada repetida (geral) | 20.6% | **0.0%** |
| Plano repetido (geral) | 10.6% | **0.0%** |
| Pegada repetida em costas | 41.1% | **0.0%** |
| Plano repetido em peito | 63.3% | **0.0%** |
| Tempo p50 | 3.20s | 3.93s (+23%) |

**Todas as métricas zeraram**. Tempo cresceu dentro do esperado pelo
handoff (~2x = teto previsto). JSONs em `st4_variedade_pre.json` e
`st4_variedade_pos.json`.

---

## Gate de fechamento

- **Pytest**: 376 passed + 1 skip (baseline 370 + 6 testes novos).
- **Snapshots**: 13 verdes.
- **Harness comparativo**: 16/16 OK. 4.1 mantido em 17.07% (6º NO-OP
  pós-CORE, informativo); 2.4 mantido 100% (NO-OP banco-limitado). Sem
  regressão estrutural.
- **Smoke E2E `/gerar`** (config Jose Silva, seed aleatório):
  - T1 peito(2): `Supino Fechado [pronada/reto/barra]` × `Crucifixo
    Inclinado Halteres [neutra/inclinado/halter]` — 3 dims distintas.
  - T2 costas(3): `Remada Apoiado [neutra/apoiada]` × `Puxada Supinada
    [supinada/—]` × `Remada LM Aberta [aberta/curvada]` — **3 pegadas
    distintas** (caso clínico verbalizado pelo Bernardo resolvido).

---

## Lições / achados

1. **Sentinela por slot é mecanismo curado, não acidente**: o helper
   `_pegada_code_do_ex` foi desenhado pela S-E1 (commit `b5e6beb`)
   pensando em dim ausente. Bernardo redescobriu independentemente o
   uso pra exceções biomecânicas em sessão clínica. Reaproveitar
   código existente paga dividendos.
2. **Norte §3 + §5**: S-T4 implementou em ~90 minutos porque
   `subregiao_idx` (S-R1), `_pegada_code_do_ex` (S-E1) e o pattern
   `same_sub × same_dim` (S-E1) já existiam. Mecanismos declarativos
   compostam — entrega marginal cresce com a maturidade do motor.
3. **Curadoria no banco > flags hardcoded**: opção "apagar célula"
   (Opção C) bateu Opção A (helpers `_opta_fora_pegada` no .py) e
   Opção B (coluna `proximidade_excecao` no XLSX) por simplicidade.
   Regra clínica fica no XLSX onde Bernardo lê/edita sem código.
4. **Hierarquia INTRA > INTER recuperada**: peso 12/12/3 = 1.2× S-E1
   honra Seção 8.9/D3.1 da `dimensoes_proximidade.md`. Spec antiga
   sobrevive declarativamente.
5. **Tempo p50 cresceu +23%, dentro do esperado**: S-E1 mergeada cresceu
   2x; somar S-T4 ao mesmo modelo adicionou ~25% adicional. Aceitável
   pra produção (3.93s p50 em Full Body 2T config Jose Silva).

---

## Pendências pós-S-T4

- **Sincronização do XLSX de exceções**: quando o Drive sincronizar
  o arquivo editado por Bernardo (5 células planejadas — Pullover ×3
  pegada + Crossover ×2 plano), as exceções entram em vigor sem mais
  código. Não bloqueia uso real — motor hoje paga penalty inerente
  em Pullover/Crossover quando pareados com outros da mesma sub, mas
  não inviabiliza.
- **S-E1 / S-R1 em /regerar**: ver
  `memory/project_pendencia_se1_regerar.md`. Caminho A pré-traçado
  (reusar `gerar_rotina_csp` com travados pool=1 + flag
  `participa_cross_soft=True`). Atacar com S-H1.
- **Captura de rationale no motor CSP**: aberta desde 2026-05-23
  (Frente C). UI `/decisoes` mostra mensagem amber pra treinos CSP.
  Análogo à Etapa 8 Explicabilidade do antigo. Não bloqueia uso real.
- **Bloco 4 do roadmap CSP fechado**: achados 1+2+3 da auditoria
  2026-05-26 resolvidos (S-R1 + S-E1 + S-B5); achado 4 descontinuado;
  S-T4 (lacuna INTRA do achado 2) fechada. Próximo bloco: Bloco 5
  (vetor de perfil — Centralidade Compostos, Densidade Pareamento, etc).
