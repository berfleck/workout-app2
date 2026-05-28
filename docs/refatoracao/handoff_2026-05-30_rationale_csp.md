# Handoff — Captura de rationale no motor CSP

**Sessão**: próxima após encerramento da frente S-T4 (mergeada em main
2026-05-29, commit `abed2ab`).

**Branch base**: a partir de `main`. Branch sugerida:
`rationale-csp`. Disciplina de merge se aplica (1 branch ativa por
vez, aguardar aprovação Bernardo pra merge FF).

**Bloco**: pendência aberta há mais tempo no roadmap CSP — registrada
desde a Frente C (2026-05-23). Bloco 4 (achados auditoria 2026-05-26)
e refinamentos pós-E.1 estão fechados; rationale CSP é a frente
isolada de mais alto valor visível ao usuário entre as pendências
restantes.

---

## 1. Por que esta sessão existe

### Lacuna funcional

A página `/decisoes` (URL `/hub/rotina/<aluno>/treino/<t>/decisoes`,
botão 🔍 ao lado do chip T1 no HUB) hoje mostra, pra treinos do motor
antigo, **timeline completo** de decisões: pré-alocação, pareamento,
score breakdown, distribuição por âncoras, rejeições por carga. Isso
foi entregue pela **Etapa 8 Explicabilidade** (2026-05-17, mergeada
em main) — captura cobre 3 fases do motor antigo (slot/seleção +
pareamento + pré-alocação) e UI consome via `_rationale_inline.html`.

A Frente C (2026-05-23) substituiu o motor antigo pelo CSP em
`/regerar`, e a Frente E.1 (2026-05-26) estendeu o clean break pro
`/gerar`. **Motor CSP nunca capturou rationale**. Como solução
provisória, o adapter (`app_flask.py:390`, `app_flask.py:705`) marca
cada Exercício com `rationale={"gerador": "csp"}`. A página
`/decisoes` detecta o marker (`app_flask.py:2256-2260`) e renderiza
**mensagem amber** em vez do timeline:

> Este treino foi gerado pelo motor CSP novo. Captura de rationale
> ainda não implementada pra essa rota.

Resultado: usuário hoje NÃO vê *por que* o motor escolheu cada
exercício em treinos pós-Frente E.1 (ou seja, todos os treinos novos).
Pra Bernardo entender decisões clínicas do motor e Claude debugar
auditorias, é frente de alto valor.

### Causa estrutural

Motor antigo e motor CSP têm paradigmas opostos:

- **Antigo (greedy)**: decide slot por slot, em ordem. Cada decisão é
  isolada e pode ser explicada como "escolhi X porque entre os
  candidatos viáveis, X tinha melhor score por essas razões". Captura
  é natural: registra o que foi avaliado em cada passo do greedy.
- **CSP (declarativo)**: solver vê o problema inteiro de uma vez,
  minimiza função objetivo global. Não tem "passos" — tem **estado
  final** com slot→exercício atribuído. Pra explicar, precisa
  reconstruir *post-hoc* qual penalty cada par/slot contribuiu pro
  objetivo, e qual alternativa o solver REJEITOU em cada slot.

Essa diferença força redesign da captura — não dá pra copiar a
estrutura do antigo. Mas a **UI já existe e está pronta** pra
consumir uma estrutura semelhante. O trabalho é (a) decidir o que
faz sentido capturar no paradigma CSP, e (b) preencher a estrutura
que `_rationale_inline.html` espera.

---

## 2. Leitura preparatória (na ordem)

1. **`docs/refatoracao/norte.md`** — princípios e anti-padrões.
   Releia Seção 5 antes de propor trade-offs.
2. **`docs/refatoracao/roadmap_csp.md`** — estado atual + próximas
   frentes. Pendência "Captura de rationale no motor CSP" linha 225.
3. **Etapa 8 Explicabilidade do antigo** (referência pro pattern):
   - Memory: [[project-etapa-8-explicabilidade]] — resumo das 5 fases
     8.E.1-8.E.5.
   - Log: `docs/refatoracao/logs/etapa_8_explicabilidade.md` (se
     existir — checar).
   - **Não esperar paridade 1:1**. O conteúdo do rationale precisa
     ser repensado pro paradigma CSP.
4. **Estado atual de captura CSP** — código que JÁ existe e marca:
   - `app_flask.py:362-410` (`_resultado_csp_pra_sessao` —
     `gerar_treino_csp`).
   - `app_flask.py:690-720` (helper de `gerar_rotina_csp`).
   - `app_flask.py:2253-2260` (detecção do marker `"gerador": "csp"`).
5. **`templates/_rationale_inline.html`** + **`base.html`** (CSS) —
   estrutura que a UI espera. Identifica quais campos do `rationale`
   dict são renderizados.
6. **`gerador_csp.py`** — `_construir_modelo` (penalidades),
   `_resolver_com_variedade` (Phase 1 optimal + Phase 2 enumeração),
   `_decode_solucao`. Pontos onde captura faz sentido.

---

## 3. Pontos de decisão pendentes (perguntar antes de codar)

Texto livre com sugestões/contraponto. [[feedback-askquestion-exploratorio]].

### 3.1 Granularidade da captura — o que faz sentido capturar no CSP?

**Sugestão (caminho mínimo viável)**: capturar 4 informações por
exercício escolhido, espelhando o que o antigo entrega:

1. **Pool do slot** — quais exercícios foram considerados como
   candidatos pra este slot (após filtros hard H-P1/H-T1/T2/T3/H-A0/
   H-A1 etc). Permite responder "por que não X?".
2. **Penalidades agregadas por fonte** (S-T1, S-A1, S-B1, S-B5, S-R1,
   S-E1, S-T4, Aderência ao Tier, cargas_off): qual cada uma
   contribuiu pro objetivo do treino. Não precisa decompor por slot;
   agregação por treino já dá visibilidade.
3. **Alternativas próximas via enumeração** — `ConfigVariedade` já
   enumera soluções dentro do `slack` no Phase 2 (campo
   `n_solucoes_enumeradas` no retorno). Coletar as top-K e marcar
   delta de objetivo. Permite responder "qual seria a 2ª melhor
   solução?".
4. **Marker de quais constraints "salvaram"** — H-R1 / H-A0 / H-A1
   degradação (já capturado em `h_a0_aplicadas`, `h_a1_aplicadas`,
   `h_r1_aplicadas`) — só propagar pra o rationale por treino.

Contraponto: capturar TUDO (penalty por slot, por par, etc) inflaria
o modelo e exigiria callbacks no solver — sai do escopo curto.
Caminho mínimo viável foca no que a UI já consegue renderizar.

### 3.2 Onde capturar — em que função do `gerador_csp.py`?

**Sugestão**: novo helper `_capturar_rationale(md, solver, solucao,
slot_to_ex)` que roda **depois** do solve, lê os valores das
BoolVars/IntVars de penalty (`viol` de cada S-X), agrega por fonte,
identifica top-K alternativas pela `collector.solucoes` (já existe
em `_SolucoesCollector`), e devolve dict por slot.

Ponto de chamada: `_resolver_legacy` (linha ~2540) e
`_resolver_com_variedade` (linha ~2742) — ambos depois do solver
terminar. Resultado anexado em `treino_dict["rationale"]` no decode
ou direto no dict de retorno.

### 3.3 Estrutura do dict — espelhar antigo ou redesenhar?

**Sugestão**: espelhar até onde fizer sentido (UI reaproveita), criar
chaves novas onde paradigma muda. Proposta:

```python
ex.rationale = {
    "gerador": "csp",  # marker (já existe)
    "slot": {
        "treino_idx": int,
        "nivel_demanda": str,        # "regiao" / "subregiao" / "padrao"
        "escopo_demanda": str,
        "pool_size": int,
        "filtros_hard_aplicados": list[str],  # ex: ["H-P1", "H-T1"]
    },
    "penalidades_atribuidas": [
        {"fonte": "S-E1", "dim": "pegada", "com_slot": int, "peso": int},
        # ... uma entrada por viol > 0 envolvendo este slot
    ],
    "alternativas": [
        {"nome": str, "objetivo_delta": int, "n_dims_diferentes": int},
        # top-K (K=3?) das soluções enumeradas Phase 2
    ],
    "constraint_degradada": str | None,  # "H-A1" / "H-R1" se este slot
                                         # foi afetado por degradação
}
```

**Penalidades por slot vs por treino**: capturar por slot
(cardinalidade O(n_slots × n_dims_ativas)) tem custo mas é o que UI
quer renderizar. Por treino é mais barato mas pouco informativo.

### 3.4 Custo de tempo — quanto cresce o solve?

**Sugestão**: captura roda DEPOIS do solve, lendo valores finais.
Zero impacto no Phase 1 (Minimize). Phase 2 (enumeração) já roda
hoje; captura só lê o `collector.solucoes` que já existe.

Contraponto: pra ter "alternativas por slot" (não por solução
inteira), precisaria de N enumerações filtradas (uma por slot
"forçando outro ex"). Caro. Caminho mínimo viável: pegar top-K
soluções inteiras enumeradas naturalmente e marcar deltas.

### 3.5 Compatibilidade com motor antigo — coexistem?

**Sim, fechado.** Marker `"gerador": "csp"` no rationale distingue.
UI `/decisoes` faz branch: se `treino_csp == True` → renderiza
template novo (a desenhar/adaptar); senão → renderiza template
antigo já pronto. Não mexe no antigo.

### 3.6 Wire — captura em `/gerar`, `/regerar` ou ambos?

**Sugestão: ambos**, default ON. Custo marginal de tempo é pequeno
(pós-solve). UI consome do `Sessao.blocos[i].ex.rationale`
serializado igual hoje.

---

## 4. Spec técnica (rascunho — depende das decisões §3)

### 4.1 Mudança em `gerador_csp.py`

**(a) Helper novo `_capturar_rationale_por_slot`** (~80 linhas):
- Recebe `md` (dict do `_construir_modelo`), `solver`, `slot_por_sid`,
  `assign`, `penalidades`, IntVars de dim (S-E1/S-T4), `collector`
  (top-K soluções), `h_*_aplicadas` listas.
- Pra cada slot, retorna dict com pool_size, filtros aplicados,
  penalidades envolvendo o slot, top-K alternativas via collector.
- Helper retorna `{sid: rationale_dict}` consumido no `_decode_solucao`.

**(b) Modificação em `_decode_solucao`** (linha ~2019):
- Aceita arg `rationale_por_slot` opcional.
- Atacha `rationale_por_slot[sid]` em cada exercício via
  `dataclasses.replace(ex, rationale=<dict>)` (preservando marker
  `"gerador": "csp"`).

**(c) Chamadas em `_resolver_legacy` e `_resolver_com_variedade`**:
- Após `_decode_solucao`, chama `_capturar_rationale_por_slot`,
  propaga.

### 4.2 Mudança em `app_flask.py`

`_resultado_csp_pra_sessao` (linha 362) e helper similar para
`gerar_rotina_csp` (linha 690): em vez de sobrescrever rationale com
`{"gerador": "csp"}`, **preservar** o rationale capturado pelo motor
e adicionar (não sobrescrever) o marker.

```python
existing = ex.rationale or {}
existing["gerador"] = "csp"
exs_marker.append(_dc_replace(ex, rationale=existing))
```

### 4.3 Mudança em `templates/_rationale_inline.html`

Adicionar branch CSP no template:
- Se `ex.rationale.gerador == "csp"`: renderiza seções "Pool", "Penalidades",
  "Alternativas", "Constraint degradada" (estrutura do §3.3).
- Senão: renderiza estrutura antiga (timeline pré-alocação + pareamento
  + score breakdown).

Pode ser feito via novo partial `_rationale_csp_inline.html` incluído
condicionalmente, mantendo o original intacto.

### 4.4 Mudança em `app_flask.py` rota `/decisoes`

Linha ~2260: o branch `treino_csp` hoje aborta o render e mostra
mensagem amber. Trocar pra renderizar `_rationale_csp_inline.html`.

### 4.5 Testes novos

`tests/test_rationale_csp.py`:

1. `test_rationale_capturado_em_gerar_rotina`: após
   `gerar_rotina_csp`, cada exercício de cada treino tem rationale
   não-vazio com chaves `slot`, `penalidades_atribuidas`,
   `alternativas`.
2. `test_pool_size_match_realidade`: `rationale.slot.pool_size`
   bate com o tamanho do pool real do slot (sanity).
3. `test_penalidades_envolvendo_slot`: pra config Jose Silva, pelo
   menos 1 slot de costas deve ter penalidade S-E1 ou S-T4
   capturada (após auditoria PRÉ-S-T4 / cross-treino zero, motor
   resolve sem penalty — então este teste deve ser sob config que
   FORÇA penalty inerente, ex: peito com pegada uniforme).
4. `test_alternativas_top_k_distintas`: top-K alternativas têm pelo
   menos 2 nomes distintos do escolhido.
5. `test_marker_csp_preservado`: depois do adapter, o marker
   `gerador=csp` continua presente no rationale.
6. `test_constraint_degradada_propagada`: cenário H-A1 com pool vazio
   marcado em `constraint_degradada`.

---

## 5. Validação esperada (gate de fechamento)

### 5.1 Smoke visual

Abrir `/decisoes` num treino CSP no HUB — ver timeline/cards
renderizados, não mensagem amber.

### 5.2 Pytest

Baseline 376 + ~6 novos = 382. Snapshots podem regenerar se rotinas
snapshot-protegidas serializam rationale agora (verificar
`_exercicio_to_dict` / `_dict_to_exercicio` — provavelmente já
serializa pq Etapa 8 fez isso pro antigo).

### 5.3 Harness 16/16

Sem regressão. Captura é pós-solve, não afeta valores.

### 5.4 Tempo p50

Esperado +5-10%. Captura agrega dados que já existem (penalidades já
construídas, collector já populado). Sem novas constraints.

---

## 6. Arquivos a mexer

- `gerador_csp.py` — helper `_capturar_rationale_por_slot` + propagação
  em `_decode_solucao` + chamada em `_resolver_legacy` /
  `_resolver_com_variedade`. ~150 linhas.
- `app_flask.py` — preservar rationale em vez de sobrescrever;
  trocar branch CSP de mensagem amber pro template novo.
- `templates/_rationale_inline.html` — adicionar branch CSP
  (ou criar partial separado).
- `tests/test_rationale_csp.py` — novo, ~6 testes.
- `docs/refatoracao/logs/rationale_csp.md` — log.
- `docs/refatoracao/roadmap_csp.md` — marcar ✅.
- `MEMORY.md` — 1 linha apontando pro memory file novo.

---

## 7. Restrições / não-fazer

- **NÃO mergear em main sem aprovação explícita do Bernardo**
  (disciplina de merge — 1 branch ativa por vez).
- **NÃO usar `--no-verify`** ou flags que pulem hooks.
- **Commit seletivo** (`git add <arquivo>`, NUNCA `-A` — ver
  [[feedback-sessoes-paralelas-git]]). Atenção: 2 untracked
  pré-existentes em main que NÃO são desta sessão
  (`docs/refatoracao/relatorios/E0_2026-05-25.md`,
  `tools/sondar_sa1_baseline_log.txt`).
- **NÃO usar AskUserQuestion** pras decisões §3 — texto livre.
- **NÃO mexer em `gerador_treino.py`** (motor antigo). Captura do
  CSP é independente.
- **NÃO espelhar 1:1 a Etapa 8 Explicabilidade do antigo** — o
  paradigma é diferente, força redesenho de estrutura. Leia o memory
  resumo pra entender o pattern conceitual mas adapte.
- **NÃO degradar tempo p50**: pra evitar isso, captura DEVE rodar
  pós-solve, sem callbacks no solver nem reenumerações por slot.

---

## 8. Alternativas (caso Bernardo prefira outra direção nesta sessão)

Rationale CSP é minha aposta principal porque é alto valor visível e
sem dependências de cadastro novo. Mas há frentes igualmente
defensáveis:

- **S-H1 + S-E1/S-R1 em /regerar** (cross-treino soft com treinos
  congelados). Pendência registrada em
  [[pendencia-se1-regerar]]. Caminho A pré-traçado. Frente
  arquitetural — mexer no adapter `treino_regerar` pra reusar
  `gerar_rotina_csp` com travados pool=1. Médio esforço.
- **Gate de avaliação clínica semântica** (pré-requisito Bloco 5).
  Auditar N rotinas de configs comuns e cruzar com princípios
  clínicos verbalizados. Bernardo precisa rodar junto.
- **S-B2** (carga implícita) ou **S-B3** (fadiga prévia bloco) —
  exigem cadastrar `demanda_lombar` ou `estabilidade_externa` no
  XLSX. Bloqueado em cadastro novo (Bernardo precisa preencher).
- **Sincronização XLSX exceções S-T4** — apenas confirmar que as 5
  células planejadas (Pullover ×3 pegada + Crossover ×2 plano) foram
  apagadas + smoke E2E confirmando que exceções entram em vigor.
  Frente curta (~15min). Pode rolar como aquecimento antes de
  qualquer outra.

---

## 9. Como abrir a sessão

1. **Confirmar leitura**: norte.md (§3-§5) + roadmap_csp.md (estado
   atual) + Memory [[project-etapa-8-explicabilidade]] +
   `_rationale_inline.html` (estrutura UI atual) + `gerador_csp.py`
   pontos de captura (§4.1).

2. **Confirmar sincronização XLSX S-T4**: rodar
   `python -c "import pandas as pd; df=pd.read_excel('banco_exercicios.xlsx', sheet_name='Exercícios');
   print(df[df.nome.isin(['Pullover Halteres','Pullover Polia','Pulldown Braço Estendido','Crossover','Crossover Sentado'])][['nome','pegada','plano_corporal']])"`.
   Se ainda não sincronizou, registrar no log da sessão (não bloqueia).

3. **Confirmar entendimento** das 6 perguntas §3 e propor sugestões
   + contraponto em texto livre.

4. **Coletar decisões do Bernardo** antes de qualquer código.

5. **Implementar na ordem**: §4.1 (helper de captura + decode) →
   §4.2 (preservar rationale no adapter) → §4.3 + §4.4 (UI).

6. **Testes** §4.5.

7. **Gate**: pytest + harness + smoke visual /decisoes.

8. **Atualizar docs**: log + roadmap + MEMORY.

9. **Commit seletivo + push** + aguardar aprovação Bernardo pra
   merge FF.

**Tempo estimado**: ~90-120min. Maior incerteza: redesign do dict
de rationale (decisão clínica) + branch novo no template HTML +
custo de captura pós-solve. Mais lento que S-T4 (que reaproveitou
infra) porque é frente original em paradigma novo.

---

## 10. Contexto importante da sessão anterior (S-T4, 2026-05-29)

Mergeada em main commit `abed2ab`. Bloco 4 do roadmap CSP totalmente
fechado (achados 1+2+3 da auditoria 2026-05-26 resolvidos via
S-R1+S-E1+S-B5+S-T4; achado 4 descontinuado).

**O que entregou**:
- Soft CSP nova: pares INTRA-treino mesma-sub com penalty em pegada/
  plano/eq match. Espelho INTRA do S-E1 (cross-treino).
- Refator de IntVars compartilhados S-E1↔S-T4 (`pegada_idx/plano_idx/
  eq_idx` construídos uma vez quando qualquer das duas usa peso > 0).
- Exceções biomecânicas tratadas via dim vazia no XLSX (Pullover/
  Pulldown + Crossover — Bernardo edita células manualmente).
- Wire em /gerar E /regerar.
- Pesos 12/12/3 (hierarquia INTRA > INTER ~1.25× S-E1).
- Pytest 376 + 1 skip + harness 16/16 + sondagem PRÉ × PÓS zerou
  todas métricas.

**O que aprender** (lições metodológicas relevantes pra rationale CSP):

1. **Mecanismos declarativos compostam** — S-T4 herdou
   `subregiao_idx` da S-R1 + `_pegada_code_do_ex` da S-E1 + pattern
   `same_sub × same_dim`. Norte §3+§5 paga dividendos. Captura de
   rationale também deve reusar estrutura existente
   (`md["penalidades"]`, `collector.solucoes`, `h_*_aplicadas`).

2. **Sondagem PRÉ × PÓS é gate forte** — definir métrica baseline
   antes de codar, medir após. Captura de rationale tem
   métrica diferente (smoke visual + cobertura dos testes), mas
   princípio se mantém: definir o que "funcionar" significa antes
   de implementar.

3. **Curadoria no banco > flags no código** — opção C (dim vazia)
   da S-T4 bateu A (helper Python) e B (coluna nova) por
   simplicidade. Pra rationale CSP, análogo seria: dado já capturado
   em estruturas existentes do `_construir_modelo` > criar
   instrumentação nova. Reaproveitar `md["penalidades"]` (lista
   de IntVars já criadas) > callback no solver.

4. **Discrepância handoff vs implementação real** — handoff S-E1
   falava de "matriz pegada 4×4"; spec real era binária. Mesmo
   pattern pode aparecer aqui — validar pressupostos pré-código
   lendo o que o motor REALMENTE faz, não só docs evolutivos.
   Especificamente: olhar `_construir_modelo` e contar quantas
   IntVars de penalty existem hoje antes de propor estrutura.

5. **Pendência paralela registrada**: S-E1/S-R1 em /regerar
   (cross-treino soft com travados). Caminho A traçado em
   [[pendencia-se1-regerar]]. Pode ser frente seguinte (após
   rationale CSP) ou ser bateda em paralelo se rationale for mais
   curto que o esperado.
