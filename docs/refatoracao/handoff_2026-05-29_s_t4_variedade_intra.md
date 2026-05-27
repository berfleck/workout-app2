# Handoff — S-T4 variedade INTRA dentro de subregião (catálogo Seção 2)

**Sessão**: próxima após encerramento da frente S-E1 (mergeada em main
2026-05-28, commit `b5e6beb`).

**Branch base**: a partir de `main`. Branch sugerida:
`frente-s-t4-variedade-intra`. Disciplina de merge se aplica (1 branch
ativa por vez, aguardar aprovação Bernardo pra merge FF).

**Bloco**: 4 do roadmap CSP — refinamentos pós-E.1. Achados 1+2+3 da
auditoria 2026-05-26 fechados; Achado 4 descontinuado. S-T4 fecha a
lacuna deixada pela S-E1: cobertura INTRA-treino do mesmo conceito
(proximidade biomecânica). Catálogo Seção 2 lista S-T4 como
"variedade de eixos dentro de subregião com múltiplos slots".

---

## 1. Por que esta sessão existe

### Lacuna arquitetural

S-E1 (2026-05-28) cobriu **proximidade biomecânica cross-treino**: pares
de slots em treinos diferentes mesma-subregião pagam penalty quando
`pegada / plano_corporal / equipamento_grupo` coincidem. Spec do motor
antigo (`gerador_treino._score_proximidade`) tinha INTRA (`_score_intra`)
+ INTER (`_score_inter`) + HISTÓRICO. CSP novo agora tem INTER (S-E1) +
HISTÓRICO via `familias_proibidas` (Frente E.1, hard cross-rotina) —
**falta a parte INTRA**.

Caso clínico verbalizado por Bernardo durante a preparação da S-E1
(commit `06a56d1`):

> "puxada aberta fixada primeiro → remada aberta penalizada → solver
> do antigo escolhia remada neutra mesmo quando aberta+aberta era ideal"

S-T4 ataca exatamente esse problema. Em `costas(2)` no MESMO treino,
o solver hoje não tem nenhum sinal de objetivo penalizando pegadas
iguais (puxada pronada + remada pronada) ou planos iguais (curvada +
curvada). O cycling do H-A1 entrega cobertura (1 remada + 1 puxada
obrigatórias), mas dentro disso a escolha de pegada/plano é livre.

### Causa estrutural

- **`_compativel_intra`** do antigo (`gerador_treino.py:2158`) é só hard
  (família refinada + variante_pontual + lateralidade contextual costas).
- **`_score_intra`** do antigo (`gerador_treino.py:2236`) tinha a parte
  soft de pegada+plano+eq INTRA (constante por dim, escopo same-sub).
  Migrou pro hard do `_compativel_intra` só as 3 regras hard; soft INTRA
  ficou no `_score_intra`.
- **CSP novo** só tem S-B1 (agonistas same-bloco, peso 10) + S-B5 (regiao
  same-bloco, peso 4). NENHUM soft INTRA-treino de pegada/plano/eq.

Resultado prático: solver pode escolher `Remada Curvada Barra Pronada +
Puxada Frontal Pronada` no MESMO treino sem custo, mesmo havendo
`Remada Curvada Halteres Neutra + Puxada Frontal Aberta` (mesma cobertura
de eixos, mais variedade biomecânica). H-T1/T2/T3 hard não pegam (famílias
diferentes; sem variante_pontual; lateralidade unilateral é o gate hard
em costas, não pegada).

---

## 2. Leitura preparatória (na ordem)

1. **`docs/refatoracao/logs/mvp_se1_proximidade_biomecanica.md`** — log
   da frente anterior. Pattern de implementação a reusar: IntVars com
   sentinela por slot, `same_X` reificação, `same_sub × same_dim` no
   `OnlyEnforceIf`. **TODAS as 5 funções de IntVar de pegada/plano/eq
   no `_construir_modelo` já existem** (criadas pela S-E1, hoje só
   construídas quando algum peso S-E1 > 0). S-T4 reusa.
2. **`docs/refatoracao/catalogo_constraints.md`** — entradas S-T4
   (Seção 2 ESCOPO TREINO) e S-E1 (Seção 2 ESCOPO ROTINA, adicionada
   2026-05-28). Conferir que S-T4 não duplica conceito da S-B1 (S-B1 é
   intra-BLOCO; S-T4 é intra-TREINO mesma-sub).
3. **`docs/refatoracao/arquivo/era_v4_greedy_incremental/dimensoes_proximidade.md`**
   — REFERÊNCIA VIVA. Especialmente:
   - **Seção 1.5** (escopo "mesma subregião" — mesmo da S-E1).
   - **Seção 1.7** (filtros hard INTRA — confirma que S-T4 NÃO toca em
     família/variante_pontual/lateralidade, já cobertas hard).
   - **Seção 8.9/D3.1** (multiplicadores INTER 0.8 × INTRA — implica
     INTRA tem pesos ~1.25 × INTER; relevante pra calibração inicial).
   - **Seção 8.11/A.1** (escala numérica: ALTO INTRA = -50; INTER =
     -40; CSP usa peso 10 pra INTER → INTRA ~12-13 proporcional).
4. **`gerador_csp.py`** linhas 779-791 (`subregiao_idx` IntVar — já
   existe) + bloco S-E1 (linhas 1702-1815 aprox — pattern de
   referência). Confirmar que `pegada_idx / plano_idx / eq_idx` são
   construídos hoje só quando S-E1 ativa; S-T4 vai precisar
   compartilhar (refator pra construção condicional cobrir os 2 casos).
5. **`gerador_treino._score_intra`** (linhas 2236-2261 do
   `gerador_treino.py`) — 4 linhas, função antiga que S-T4 replica
   declarativamente. Confirma que é binário (mesma decisão D2.1 da
   S-E1).

---

## 3. Decisões prováveis a fechar com Bernardo (pré-código)

**Texto livre** com sugestões/contraponto (tópico clínico aberto;
[[feedback-askquestion-exploratorio]]).

### 3.1 Granularidade — par INTRA-treino mesma-subregião

**Sugestão**: par `(s1, s2)` com `t_idx(s1) == t_idx(s2)` e
`subregiao_idx[s1] == subregiao_idx[s2]`. Espelho exato da S-E1, só
mudando o predicado de "treinos diferentes" para "mesmo treino". Reusa
`same_sub` BoolVar reificada. Captura o caso clínico verbalizado
(puxada+remada same-treino com pegada igual).

Contraponto: S-B1 (agonistas same-bloco) e S-B5 (regiao same-bloco) já
fazem par-a-par INTRA-bloco. S-T4 expande pra INTRA-TREINO inteiro,
não só intra-bloco. **Diferença clínica**: dentro de um bloco
(superset), pares biomecanicamente próximos podem fazer sentido
(estímulo concentrado); ao longo do treino inteiro, variedade é melhor.

### 3.2 Quais dimensões consumir

Sugestão: **mesmas 3 da S-E1** — `pegada` + `plano_corporal` +
`equipamento_grupo`. Spec antiga (Seção 1.5) tinha exatamente essas
3 com escopo "mesma subregião".

Contraponto: equipamento INTRA pode ser menos relevante que INTER
(em casa, todo mundo usa muito halter — penalizar dentro do treino
talvez force escolha estranha). Spec antiga (Seção 1.5) marca
equipamento como **BAIXO tiebreaker** INTRA — ainda penaliza, mas
pouco. Manter os 3 mas com peso eq baixo (igual S-E1: peso 2).

### 3.3 Pesos — proporcional à S-E1, ajuste pela hierarquia INTRA > INTER

Spec antiga (Seção 8.9/D3.1 e 8.11/A.3): **INTER = 0.8 × INTRA**.
Então:
- S-E1 INTER pegada/plano = 10 → S-T4 INTRA pegada/plano ≈ **12-13**
- S-E1 INTER eq = 2 → S-T4 INTRA eq ≈ **2-3**

**Sugestão inicial**: `peso_st4_pegada = 12`, `peso_st4_plano = 12`,
`peso_st4_eq = 3`. Calibrar via sondagem; alvo análogo à S-E1 (zerar
ou reduzir drasticamente match exato INTRA mesma-sub em config
representativa).

Contraponto: pesos INTRA mais altos podem inviabilizar config onde
subregião tem pool restrito numa pegada/plano específico. Sondagem
PRÉ × PÓS detecta — se inviabilidade subir, baixar peso ou aceitar
piso estrutural ([[tamanho-familia-nao-e-centralidade-clinica]] como
analogia: não forçar mecanismo onde banco não permite).

### 3.4 Escopo "mesma subregião" — preservar?

**Sim, fechado.** Mesmo argumento da S-E1. Reificado via `same_sub`
(que já existe — `subregiao_idx` criado pela S-R1, compartilhado por
S-E1 e S-T4).

### 3.5 Default ON sem toggle UI

**Sugestão: sim**, igual S-E1/S-R1/S-B5/S-A1.

### 3.6 Pegada uniformemente pronada em peito — repete problema da S-E1?

**Confirmado durante S-E1**: todos os supinos do banco têm
`pegada=pronada`. Isso significa que em `peito(2)` mesmo treino, S-T4
pegada DISPARA SEMPRE — penalty paga sempre, sem alternativa. Igual
no INTER (S-E1 b descobriu isso, refatorou teste pra medir
equipamento).

**Decisão a tomar**: aceitar penalty inerente (motor paga sempre, mas
não inviabiliza — graceful degradation natural) ou banir essa
dimensão pra subregiões onde pool é uniforme (over-engineering tipo
[[tamanho-familia-nao-e-centralidade-clinica]])?

Sugestão: **aceitar penalty inerente**. Motor paga; é sinal CORRETO
de que o banco tem limitação biomecânica (peito é só pronado). Se
quiser variedade real em peito, precisaria de exercícios com pegada
neutra (Crossover Sentado tem mas é purpose=isolation; supinos
compostos são todos pronados). Solução é cadastro, não código.

---

## 4. Spec técnica (rascunho — depende das decisões §3)

### 4.1 Mudança em `gerador_csp.py`

Análogo direto da S-E1, com 3 mudanças:

**(a) Compartilhamento dos IntVars `pegada_idx/plano_idx/eq_idx` entre
S-E1 e S-T4.** Hoje construídos no bloco S-E1 (linhas ~1702-1735 do
gerador_csp). Refator: extrair pra construção condicional fora do
bloco S-E1, criada quando `(usa_se1 OR usa_st4)`. Construir os 3
IntVars **uma vez por slot** (não 2x quando ambas ativas).

**(b) Bloco S-T4 novo, espelho do S-E1**:

```python
usa_st4 = (peso_st4_pegada > 0 or peso_st4_plano > 0 or peso_st4_eq > 0)
if usa_st4:
    # Loop sobre pares INTRA-treino (não cross-treino).
    for t_idx in range(len(treinos)):
        sids_t = slots_por_treino.get(t_idx, [])
        # Pares (s1, s2) dentro do MESMO treino, sid1 < sid2.
        for i in range(len(sids_t)):
            sid1 = sids_t[i]
            subs1 = {ex.subregiao for ex in slot_por_sid[sid1]["pool_slot"]}
            for j in range(i + 1, len(sids_t)):
                sid2 = sids_t[j]
                subs2 = {ex.subregiao for ex in slot_por_sid[sid2]["pool_slot"]}
                if not (subs1 & subs2):
                    continue
                # same_sub: reusa se já criado pelo S-E1 (mesmo par
                # cross-treino), mas pra pares INTRA o par é diferente
                # (t1 == t2). Criar nova BoolVar.
                same_sub = model.NewBoolVar(f"st4_samesub_{sid1}_{sid2}")
                # ... reificação idêntica à S-E1 ...
                for dim_tag, peso, idx_dict in (
                    ("peg", peso_st4_pegada, pegada_idx),
                    ("pla", peso_st4_plano, plano_idx),
                    ("eq", peso_st4_eq, eq_idx),
                ):
                    if peso <= 0:
                        continue
                    same_dim = model.NewBoolVar(f"st4_same{dim_tag}_{sid1}_{sid2}")
                    # ... mesmo pattern S-E1 ...
                    viol = model.NewIntVar(0, peso, f"st4_pen_{dim_tag}_{sid1}_{sid2}")
                    model.Add(viol >= peso).OnlyEnforceIf([same_sub, same_dim])
                    penalidades.append(viol)
```

**(c) Args novos**: `peso_st4_pegada / peso_st4_plano / peso_st4_eq`
em `_construir_modelo`, `_resolver_legacy`, `_resolver_com_variedade`
(+ `teto_por_termo`), `gerar_rotina_csp`, `gerar_treino_csp`.

### 4.2 Decisão arquitetural: nomenclatura

S-T4 do catálogo é "variedade de eixos dentro de subregião com
múltiplos slots". Confirmar com Bernardo se o nome técnico
(`peso_st4_*`) está OK ou se prefere algo descritivo (ex:
`peso_variedade_intra_pegada`). Sugestão: manter S-T4 pra
consistência com S-E1/S-R1/S-B5/S-A1.

### 4.3 Wire em `app_flask.py`

3 constantes `_PESO_ST4_PEGADA_DEFAULT = 12`,
`_PESO_ST4_PLANO_DEFAULT = 12`, `_PESO_ST4_EQ_DEFAULT = 3` (sugestão
inicial). Passar via kwarg em `gerar_rotina_csp` em `/gerar`. SEM
wire em `treino_regerar` — S-T4 é INTRA-treino, então faz sentido em
regerar tb. **Diferente da S-E1** (que era cross-treino, sem sentido
em regerar 1 treino isolado). Bernardo decide se quer ativo em
`/regerar` também.

### 4.4 Testes novos

`tests/test_csp_st4_variedade_intra.py`:

1. **`test_peso_zero_eh_neutro`** — pesos 0 preservam pré-frente.
2. **`test_costas_2_alterna_pegada_intra_treino`** — `subregiao
   costas(2) × 1T`. N=10 seeds. Esperado <30% pegada repetida intra
   (baseline pre-S-T4 é alto — sondagem confirma).
3. **`test_costas_2_alterna_plano_intra_treino`** — análogo plano.
4. **`test_peito_2_aceita_pegada_uniforme_graceful`** — `subregiao
   peito(2) × 1T`. Pegada é uniformemente pronada no banco; S-T4 paga
   penalty mas NÃO inviabiliza. N=5, todas viáveis.
5. **`test_st4_compativel_com_softs_ativos`** — Full Body 2T com
   S-E1 + S-T4 + S-B5 + S-R1 + S-A1 + S-B1 ativos juntos: viável,
   sem regressão estrutural.

### 4.5 Sondagem

`tools/sondar_st4_variedade.py`. Setup canônico: `subregiao costas(2)
× 1T` (caso clínico do Bernardo). Métricas:
- `pct_pegada_repetida_intra_costas` — alvo PRIMÁRIA <30% (baseline
  provavelmente 70-100%).
- `pct_plano_repetido_intra_costas` — alvo PRIMÁRIA <30%.
- `pct_eq_repetido_intra_costas` — alvo secundário.
- `tempo_p50_s`.

Config opcional: Full Body 2T com `subregiao costas(2)` em ambos
treinos (combina INTRA e INTER) — confirma S-E1 + S-T4 ativos juntos.

---

## 5. Validação esperada (gate de fechamento)

### 5.1 Sondagem PRÉ × PÓS

Análogo à S-E1: PRÉ peso=0 em main mostra repetição; PÓS pesos
12/12/3 zera (ou reduz <30%) pegada/plano repetidos intra-treino.

### 5.2 Pytest

Baseline 370 + 5 novos = 375 (estimativa). Snapshots podem regenerar
se rotinas snapshot-protegidas mudam pra distribuir pegada/plano
intra-treino.

### 5.3 Harness 16/16

Sem regressão. Motor antigo intocado (S-T4 vive só no CSP).

### 5.4 Smoke E2E

`POST /gerar` Full Body 2T região (mesmo setup S-E1) ou `subregiao
costas(2) × 1T`. Verificar visualmente que costas 2 slots têm
pegada/plano distintos no mesmo treino.

---

## 6. Arquivos a mexer

- `gerador_csp.py` — refator condicional dos IntVars
  pegada/plano/eq_idx (compartilhamento S-E1 × S-T4) + bloco S-T4
  + 3 args novos em 5 funções. ~70-90 linhas (menos que S-E1 porque
  IntVars já existem).
- `app_flask.py` — 3 constantes `_PESO_ST4_*_DEFAULT` + wire em
  `/gerar`. Decidir se entra em `treino_regerar` (diferente da S-E1).
- `tests/test_csp_st4_variedade_intra.py` — novo, 5 testes.
- `tools/sondar_st4_variedade.py` — novo.
- `docs/refatoracao/logs/st4_variedade_pre.json` / `pos.json`.
- `docs/refatoracao/logs/mvp_st4_variedade_intra.md` — log.
- `docs/refatoracao/roadmap_csp.md` — marcar S-T4 ✅.
- `docs/refatoracao/catalogo_constraints.md` — atualizar entrada S-T4
  da Seção 2 com detalhes de implementação (pesos, escopo, modelagem
  par-a-par).
- `MEMORY.md` — 1 linha apontando pro memory file novo.

---

## 7. Restrições / não-fazer

- **NÃO mergear em main sem aprovação explícita do Bernardo**
  (disciplina de merge — 1 branch ativa por vez).
- **NÃO usar `--no-verify`** ou flags que pulem hooks.
- **Commit seletivo** (`git add <arquivo>`, NUNCA `-A` — ver
  [[feedback-sessoes-paralelas-git]]). Atenção: há 2 untracked
  pré-existentes em main que NÃO são seus (`relatorios/E0_2026-05-25.md`,
  `tools/sondar_sa1_baseline_log.txt`).
- **NÃO usar AskUserQuestion** pras decisões clínicas §3 — texto
  livre com sugestões e contraponto.
- **NÃO mexer no motor antigo** `gerador_treino._score_intra` —
  referência arquitetural, mas implementação CSP fica independente
  (norte §3).
- **Modelagem simétrica par-a-par OBRIGATÓRIA** — registrada no commit
  `06a56d1` (handoff S-E1). BoolVar `same_X[s1, s2]` simétrica por
  construção. NÃO modelar como "slot A é referência, slot B é variante"
  (reintroduz viés greedy verbalizado: puxada fixada primeiro consumia
  dimensões; remada sofria todas penalties). Solver CP-SAT vê todos os
  slots de uma subregião simultaneamente.
- **NÃO duplicar dims já cobertas hard INTRA** (família, variante_pontual,
  lateralidade contextual costas). Confirmar lendo `_compativel_intra`
  do antigo + H-T1/T2/T3 do CSP.
- **NÃO desativar S-B1 intra-sub durante S-T4** — S-B1 já tem skip
  intra-sub explícita (decisão 2026-05-25 da S-A1: "user pediu a sub,
  agonistas dentro dela são esperados"). S-T4 atua em PEGADA/PLANO/EQ,
  não em agonismo — escopos ortogonais, podem coexistir.

---

## 8. Pendências NÃO incluídas

- **Gate de avaliação clínica semântica** (Bloco 4, pré-requisito
  Bloco 5). Continua aberto. Pode ser rodado em paralelo a esta
  frente ou logo após.
- **Captura de rationale no motor CSP** — destrava UI `/decisoes`
  pra treinos CSP (hoje mostra mensagem amber). Análogo à Etapa 8
  Explicabilidade do antigo. Pode ser feito pré- ou pós- S-T4.
- **S-B2, S-B3, S-T2, S-T3** — exigem cadastros novos no XLSX
  (`estabilidade_externa` + S-T3 demanda neural). Fora de escopo.
- **Centralidade Compostos / Densidade Pareamento** (2ª/3ª dims do
  vetor) — exigem refatoração do perfil de aluno.
- **Otimização da suíte de testes** — pytest-xdist, frente própria.

---

## 9. Como abrir a sessão

1. **Confirmar leitura**: norte.md (§3-§5) + log S-E1
   (`mvp_se1_proximidade_biomecanica.md`) + catalogo_constraints.md
   (entradas S-T4 + S-E1) + dimensoes_proximidade.md (Seções 1.5, 1.7,
   8.9/D3.1, 8.11/A.1) + `_score_intra` em gerador_treino.py:2236.

2. **Confirmar entendimento** das 6 perguntas clínicas em aberto
   (§3.1 a §3.6) e propor sugestões + contraponto em texto livre.

3. **Coletar decisões do Bernardo** antes de qualquer código.

4. **Rodar sondagem PRÉ** em main ANTES da implementação. Setup:
   `subregiao costas(2) × 1T` + opcional Full Body 2T região (combina
   INTRA + INTER). Persistir `logs/st4_variedade_pre.json`.

5. **Implementar na ordem** §4.1 (refator IntVars compartilhados) →
   §4.1 (bloco S-T4) → §4.3 (wire app_flask) → §4.4 (testes).

6. **Calibrar pesos** via sondagem (rodar PÓS com pesos sugeridos
   §3.3; ajustar se métricas não fecharem alvo).

7. **Gate**: pytest + harness + smoke E2E.

8. **Atualizar docs**: log + roadmap + catálogo + MEMORY.md.

9. **Commit seletivo + push** + aguardar aprovação Bernardo pra
   merge FF.

**Tempo estimado**: ~45-60min (mais rápido que S-E1 porque infra
existe). Sondagem PRÉ ~5min + refator IntVars compartilhados ~10min
+ bloco S-T4 ~15min + sondagem PÓS+calibração ~10min + testes ~5min
+ smoke ~5min + docs ~10min.

---

## 10. Contexto importante da sessão anterior (S-E1, 2026-05-28)

Mergeada em main commit `b5e6beb`. Achado 2 totalmente fechado.

**O que entregou**:

- Soft CSP nova: 3 BoolVars binárias par-a-par cross-treino mesma-sub
  via reificação `same_sub × same_dim`.
- Sentinela por slot pra dim ausente (`BASE_VAZIA + sid` único por
  slot) — `same_X` reifica false naturalmente sem BoolVar de validade.
- Pesos default 10/10/2 (consistência com escala do projeto).
- Pytest 370 + harness 16/16 + smoke E2E confirmando equipamentos
  distintos cross-treino em peito.

**O que aprender** (lições metodológicas relevantes pra S-T4):

1. **Pegada em peito empurrar_compostos é uniformemente pronada** —
   teste original media pegada repetida em peito 1+1, falhou com 100%
   (pegada não tem como alternar). Refatorado pra medir equipamento.
   **Aplicação aqui**: em `peito(2)` INTRA mesma sub, S-T4 pegada
   vai disparar SEMPRE. Aceitar como penalty inerente do banco
   (graceful degradation natural). Testar com `costas(2)` que tem
   variedade real (pronada/aberta/neutra distribuídas).

2. **Auditoria N=1 capturou casualidade nas métricas SPECIFIC** —
   "supinos halteres repetido" 100% N=1 vs 10% N=10. Foco em métricas
   AGREGADAS (pegada/plano repetida em qualquer par mesma-sub),
   secundário em casos clínicos específicos. Mesmo padrão na S-R1.

3. **Discrepância handoff vs spec real** — handoff S-E1 falava de
   "matriz pegada 4×4"; spec real (D2.1, 2026-05-09) é binária. Validar
   pressupostos pré-código lendo `_score_intra` / `_score_inter` reais,
   não só docs evolutivos. Mesma armadilha pode aparecer aqui — confirmar
   que `_score_intra` é binário (4 linhas em
   `gerador_treino.py:2247-2261`).

4. **Norte §3 paga dividendos** — S-E1 implementou em <50min porque
   `subregiao_idx` (criado pela S-R1) e `_pegada_code_do_ex` (criado
   pela S-E1) já estavam disponíveis. S-T4 vai herdar isso direto +
   reaproveitar os IntVars de dim via refator condicional. Mecanismos
   declarativos compostam.

5. **Calibração: pesos maiores melhoram tempo** — paradoxo da Phase 2
   da variedade: pesos baixos ampliam slack, mais soluções enumeradas,
   mais lento. S-T4 calibrar com pesos relativamente altos (12/12/3
   inicial) e deixar tempo p50 guiar ajuste, não brute-force baixar
   peso.

6. **Tempo p50 cresceu ~2x na S-E1** (0.79s → 1.65s em Full Body 2T).
   S-T4 vai somar mais BoolVars/IntVars no mesmo modelo — esperar
   crescimento adicional. Aceitável até ~3-4s p50; se passar disso,
   considerar otimizações (skip pares cross-treino vs intra-treino
   redundantes, cache de same_sub entre S-E1 e S-T4).
