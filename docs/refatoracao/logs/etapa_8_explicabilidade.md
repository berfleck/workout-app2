# Etapa 8 — Explicabilidade do gerador

**Status:** ✅ **CONCLUÍDA em 2026-05-17** (sessão única, fases 8.E.1 a
8.E.5 + validação browser pelo user). Pronta pra merge em `main`.

**Última atualização:** 2026-05-17 (validação browser confirmada).

**Branch:** `etapa-8-explicabilidade` (a partir de `main`).

**Não confundir com `etapa_8.md`** — aquele é o refator estrutural CORE
(itens 1+2 da 8.15.7), trabalho diferente. Esta é a Etapa 8 numerada
do `guia_refatoracao_v4.md` (linha 1045), a última etapa do guia.

**Escopo (decidido via AskUserQuestion no início):**

- **Captura:** só na seleção de exercício (`_selecionar_cand_score_aware`)
  — pareamento em blocos e pré-alocação global ficam fora do MVP.
- **Armazenamento:** campo `rationale: Optional[dict] = None` no dataclass
  `Exercicio` (não estrutura paralela em `Sessao`).
- **UI:** expand inline (não drawer, não modal). Mobile-first — botão ⓘ
  ao lado do nome do ex, click expande painel logo abaixo dentro do card.
  Decisão do user: "app deve ser mobile first, então otimização para mobile
  é o que mais importa".

---

## Fase 8.E.1 — Estrutura + decomposição por dim

### Mudanças aplicadas

- Campo `rationale: Optional[dict] = None` adicionado ao `Exercicio`
  (após `ativo: bool = True`).
- 4 funções novas em `gerador_treino.py` (logo após `_score_historico`):
  - `_componentes_intra(cand, alocados, pesos_config)` — retorna lista de
    eventos `{contexto, dim, peso, com}` para o branch INTRA.
  - `_componentes_inter(cand, alocados, pesos_config)` — idem INTER
    (família universal cross-subregião + pegada/plano/equip same-sub +
    variante_pontual cross-family).
  - `_componentes_historico(cand, historico_r1, pesos_config)` — idem
    HISTÓRICO; `com` carrega `"nome"` ou `"familia"` (granularidade D3.3).
  - `_montar_rationale(escolhido, cands_scored, slot_info, ...)` — monta o
    dict completo com slot + score + componentes + top 3 alternativas.

### Decisão arquitetural — funções paralelas, não modificar `_score_*`

Para evitar regressão no motor de score (autoridade do comportamento), as
funções `_componentes_*` são paralelas às `_score_*` existentes. A escolha
do exercício continua pelo score total das funções originais; a decomposição
só roda para o escolhido + top 3 alternativas. Custo: dupla avaliação só em
K=4 (não sobre o pool inteiro).

### Validação

- `pytest tests/` → **175 passed**, 1 skip pré-existente.
- Snapshots de regressão verdes — comportamento de seleção determinístico
  preservado (rationale é dado novo, não muda escolha).

---

## Fase 8.E.2 — Captura no `_selecionar_cand_score_aware`

### Mudanças aplicadas

- Assinatura ganhou parâmetro opcional `slot_info: Optional[dict] = None`.
- Quando `slot_info` passado, o exercício retornado é **cópia via
  `dataclasses.replace`** com `rationale` populado. Sem `slot_info`,
  retorna referência do banco como antes (compatibilidade retroativa).
- Import `replace` adicionado em `from dataclasses import dataclass, field`.
- 2 call-sites em `pre_alocar_rotina` (passe estrito + passe relax)
  agora passam `slot_info = {treino_idx, nivel, escopo,
  escopo_demanda_original, passe}` derivado do `_Slot`.

### Decisão arquitetural — `replace()` em vez de mutar

`_candidatos_estritos` retorna **referências do banco** (lista única lida do
XLSX no startup). Mutar `escolhido.rationale` diretamente contaminaria o
banco, vazando rationale velho entre gerações. `dataclasses.replace` cria
instância nova mantendo todos os outros campos — solução padrão.

### Validação

- `pytest tests/` → **175 passed**, 1 skip.
- Snapshots verdes — `dataclasses.replace` preserva campos relevantes pra
  `sessao_para_estrutura_clinica` (que só lê nome).
- Smoke test manual via `python -c` confirmou:
  - 100% dos exs em rotina recém-gerada têm `rationale != None`
  - Estrutura tem todos os campos (slot, score, componentes, alternativas)
  - Caso com colisões INTER (3 treinos de peito) gera componentes ricos:
    "Apoio" com 7 eventos INTER somando -208, alternativa "Apoio Fechado"
    com Δ=0 (empate).

---

## Fase 8.E.3 — Serialização (round-trip)

### Mudanças aplicadas

- `_exercicio_to_dict` em `app_flask.py:299` ganhou serialização condicional:
  só inclui `rationale` no dict quando `ex.rationale is not None`. Mantém
  payloads de exs do banco (sem rationale) compactos.
- `_dict_to_exercicio` em `app_flask.py:309` lê `d.get("rationale")` →
  default None preserva retrocompat com sessões antigas.

### Teste novo — `tests/test_rationale.py` (9 testes)

1. `test_geracao_popula_rationale_em_exs_escolhidos` — todos os exs em
   rotina recém-gerada têm rationale.
2. `test_rationale_tem_estrutura_esperada` — slot, score, componentes,
   alternativas, tamanho_pool com tipos certos.
3. `test_banco_nao_e_contaminado_por_rationale` — banco-fonte continua
   limpo após geração (sanity da decisão `replace`).
4. `test_round_trip_serializacao_preserva_rationale` — dict → JSON
   → dict → Exercicio mantém rationale idêntico (JSON-serializável).
5. `test_retrocompat_sessao_sem_rationale_no_json` — sessão antiga sem
   campo `rationale` no JSON deserializa com `ex.rationale = None`.
6. `test_alternativas_excluem_o_proprio_escolhido` — top alts não incluem
   o ex escolhido.
7. `test_score_total_bate_com_soma_dos_componentes` — invariante numérico.
8. `test_rationale_revela_papel_composto_vs_isolado_via_slot` — caso
   clínico do guia v4 §1093 ("Crossover Sentado solo"): rationale do
   slot identifica `empurrar_compostos` vs `empurrar_isolados`, tornando
   rastreável que a Etapa 3 (âncoras) atuou.
9. `test_rationale_em_rotina_estressada_captura_historia_completa` —
   3 treinos de peito → último treino mostra componentes INTER.

### Validação

- `pytest tests/test_rationale.py` → **9 passed**.
- `pytest tests/` (suíte completa) → **184 passed** (175 base + 9 novos),
  1 skip.

---

## Fase 8.E.4 — UI inline

### Mudanças aplicadas

**Endpoints novos** (`app_flask.py` após `treino_visualizar`):

- Helper `_ex_do_slot(sessao, bi, ei)` — retorna `Exercicio` na posição.
- `GET /treino/<int:t>/rationale/<int:bi>/<int:ei>` — modo gerador,
  lê de `sessoes_ativas`.
- `GET /hub/rotina/<int:aluno_id>/treino/<int:t>/rationale/<int:bi>/<int:ei>`
  — modo HUB, lê do rascunho (prioridade) ou rotina ativa via `carregar_rascunho` /
  `carregar_registro`.

**Partial novo** `templates/_rationale_inline.html`:

- Header com "Por que `{nome}`?" + botão fechar.
- Meta-linha: slot (escopo + nível em pt), passe, pool, score.
- Seção "Penalizações que pesaram" — lista de eventos com tag colorida
  por contexto (intra=amber, inter=orange, historico=red), dim em pt
  ("família", "pegada", "plano corporal", "equipamento", "variante pontual"),
  peso monospace, parceiro de colisão em bold.
- Seção "Alternativas consideradas (top 3)" — nome + score + Δ colorido
  (verde=escolhido melhor, vermelho=alternativa melhor [softmax sorteou],
  cinza=empate).
- Footer explicando o sinal do Δ.
- Cobre 3 sub-casos: `rationale=None` (mensagem amigável), `componentes=[]`
  (mensagem "sem conflitos — candidato neutro"), caso normal.

**Mudanças nos templates de card** (`_treino_card.html` + `_hub_treino_card.html`):

- Botão `<button class="btn-rationale">` (SVG `i-info`) injetado dentro
  de `.exercicio-nome` após os badges existentes — só renderiza quando
  `ex.rationale` populado.
- Container `<div class="rationale-container" id="rationale-...">` injetado
  como irmão de `.exercicio` (dentro de `.exercicio-wrapper` no
  `_treino_card`, dentro de `.exercicio` no `_hub_treino_card`).
- `hx-get` aponta pro endpoint apropriado (gerador vs hub).

**base.html:**

- Symbol SVG novo `i-info` (lucide-style: circle + linha + ponto).
- CSS extenso para `.btn-rationale`, `.rationale-panel`, `.rationale-head`,
  `.rationale-meta`, `.rationale-section`, `.rationale-list`,
  `.rationale-item`, `.rationale-alts`, `.rationale-alt`,
  `.rationale-tag`, `.rationale-peso`, `.rationale-alt-delta` (com
  variantes pior/melhor/empate). Paleta amber/orange consistente.
- JS novo (após `_atualizarBodyEmEdicao`):
  - `htmx:beforeRequest` — quando outro `.btn-rationale` é clicado,
    limpa innerHTML dos outros `.rationale-container` (só 1 aberto).
  - `htmx:afterSwap` — marca botão como `.is-open` quando o painel chega.
  - Click delegation em `[data-rationale-close]` — limpa container +
    remove `.is-open` do botão.

### Validação parcial via curl

```
POST /gerar  → HTTP 200, 4 botões btn-rationale na resposta (2 treinos × 2 exs)
GET  /treino/0/rationale/0/0 → HTTP 200, partial renderizado
  Por que Supino Smith Inclinado?
  Slot: empurrar_compostos (padrão), passe estrito, Pool: 6 candidatos, Score: -50
  Penalizações: pegada -50 com Apoio Ajoelhado (INTRA)
  Alternativas: Supino Inclinado Halteres (-54, Δ +4), Supino Com Anilha (-130, Δ +80)
```

### Validação no browser — confirmada pelo user (2026-05-17)

Walkthrough manual cobriu: botão ⓘ visível ao lado do nome do ex; click
expande painel inline; JS "só 1 aberto" funciona entre exs do mesmo treino
e entre treinos; X fecha; visual mobile OK; modo edição preserva o botão.
Aplicação no HUB (`/hub/rotina/.../rationale/...`) idem.

### Decisão de design — botão ⓘ separado, não nome clicável

Razão: HUB tem long-press no nome pra swap; modo edição tem drag-handle.
Botão ⓘ separado evita conflito com gestos existentes e marca a feature
como "inspeção" (não ação primária).

---

## Fase 8.E.5 — Validação clínica + harness

### Validação clínica

- Caso clínico do guia v4 §1093 (Crossover Sentado solo) virou teste
  pytest determinístico em `tests/test_rationale.py` (test 8). Confirma
  que o rationale identifica o slot `empurrar_compostos` vs
  `empurrar_isolados`, tornando rastreável que a Etapa 3 (âncoras) atuou
  ao garantir 1 composto + 1 isolado em peito(2).
- Caso "rotina estressada" (3 treinos peito) virou teste 9. Confirma que
  componentes INTER aparecem no Treino 3 quando o pool sobra restrito.

### Validação do harness

```
python tools/calibrar_pesos_dimensoes.py
→ 16/16 OK preservados (2 FAIL benignas baseline da Etapa 7 — 2.3 + 4.1)
```

Comportamento de seleção preservado byte-a-byte.

### Gate de fechamento

- ✅ `pytest tests/` → 184 passed (175 base + 9 novos), 1 skip pré-existente
- ✅ 13 snapshots de regressão verdes
- ✅ Harness 16/16 OK (sem regressão)
- ✅ Smoke test endpoint via curl
- ✅ Validação manual no browser (user confirmou 2026-05-17 — botão,
  expand, "só 1 aberto", X, mobile, modo edição, HUB)

### Pendências pós-Etapa 8

1. **Extensão futura (não bloqueia)** — captura de rationale no pareamento
   de blocos (`_buscar_candidato`) e na pré-alocação global. MVP só cobre
   seleção do exercício no slot. Decisão arquitetural: estrutura `dict`
   genérica do rationale permite estender sem mudar o shape exposto na UI
   (adicionar chave `pareamento: {...}` etc).
3. **Outros itens da 8.15.7** que continuam abertos pós-Etapa 8
   numerada (referência histórica — não bloqueiam uso real):
   - UI de Histórico exposed (item 6)
   - Setup B do 4.1 (item 7)
   - Escalada setup 2.3 (item 8)
   - Cycling determinístico de subregião (item 5)
   - Cleanup YAML overlay

---

## Documentos fonte de verdade pós-Etapa 8 Explicabilidade

- `gerador_treino.py:`
  - `Exercicio.rationale: Optional[dict]` (linha ~757)
  - `_componentes_intra/inter/historico` + `_componentes_totais` +
    `_montar_rationale` (após `_score_historico`)
  - `_selecionar_cand_score_aware` com parâmetro `slot_info`
  - `pre_alocar_rotina` — 2 call-sites passando `slot_info`
- `app_flask.py:`
  - `_exercicio_to_dict` / `_dict_to_exercicio` — serialização condicional
  - `treino_rationale` + `hub_treino_rationale` + `_ex_do_slot`
- `templates/_rationale_inline.html` — partial novo
- `templates/_treino_card.html` + `templates/_hub_treino_card.html` —
  botão ⓘ + container
- `templates/base.html` — symbol `i-info`, CSS, JS
- `tests/test_rationale.py` — 9 testes cobrindo motor + serialização + clínico
