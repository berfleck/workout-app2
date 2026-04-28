# CLAUDE.md — BF Treinamento (Flask + HTMX)

App para personal trainer gerar, editar e exportar sessões de treino. Roda localmente. Dados em SQLite + XLSX.

## Stack

Flask + Jinja2 + HTMX 2.0.4 + Tailwind CDN (`cdn.tailwindcss.com` com `@apply` em `<style type="text/tailwindcss">`) + SortableJS 1.15.3. Fonte: DM Sans. Cores: laranja `#e85d04`, fundo `#f9fafb`.

## Arquivos

```
app_flask.py              — Backend: todas as rotas
database.py               — SQLite CRUD (alunos + histórico)
gerador_treino.py         — Lógica de geração de treinos
gerar_imagem.py           — Exportação PNG (Pillow + DejaVu)
banco_exercicios.xlsx     — Banco de exercícios (aba "Exercícios")

templates/
  base.html               — Layout base: sidebar, CSS, scripts compartilhados
  hub.html                — Página principal: seletor de aluno + rotina ativa
  treinos.html            — Página do gerador: config 3 colunas + resultado + JS
  _rotina_hub.html        — Partial: rotina do aluno no HUB (atual/anterior/comparar)
  _resultado.html         — Partial: treinos gerados (auto-ref, comparação, salvar)
  _treino_card.html       — Partial: card de 1 treino (visualizar/editar) + initSortable
  _draft_banner.html      — Partial: banner de rascunho (atualizar/nova, etiqueta autosave, intent)
  _changes_list.html      — Partial: lista de alterações do rascunho (added/removed/edited)
  _substituicao.html      — Partial: lista de exercícios para substituição/adição
  _aluno_dropdown.html    — Partial: select de aluno (hx-swap-oob)
  _historico_aluno.html   — Partial: histórico filtrado por aluno
  _historico_detalhe.html — Partial: exercícios de um registro
  _historico_lista.html   — Partial: lista agrupada de registros
  _historico_item.html    — Partial: card individual de registro
  _referencia.html        — Partial: painel de referência colapsável
  _comparacao.html        — Partial: diff visual ref vs ativo
  alunos.html             — Partial: CRUD de alunos
  alunos_page.html        — Página completa: wrapper de alunos
  historico.html          — Partial: filtros + lista do histórico
  historico_page.html     — Página completa: wrapper de histórico
  _avisos_modal.html      — Partial: modal auto-abre após geração com avisos da rotina
                            (demanda incompleta + flexibilização de família). Incluído
                            em _resultado.html (fluxo gerador) e hub.html (após redirect)

  # Mobile (redesign 02 — branch mobile-redesign-02, etapas 1-8 de 12 concluídas)
  _mobile_bottom_bar.html       — Referência standalone do bottom bar mobile (não usado em runtime)
  _mobile_nav_sheet.html        — Bottom sheet de navegação (Hub/Alunos/Histórico)
  _mobile_treino_kebab_sheet.html — Action sheet do kebab do treino card (Editar/Substituir/PNG/Remover)
  _mobile_bb_actions_hub.html   — Slot direito da bb no HUB (estados: vazio/visualizando/rascunho/edição)

Gerados (gitignored): bf_treinamento.db, sessoes_salvas.json
```

## Estruturas de dados

- **`Exercicio`** (dataclass): nome, variacao_de, eq_primario, eq_secundario, regiao, subregiao, padrao, purpose, unilateral, complexidade (1-5), fadiga (1-5), circuito, similaridade, musculo_primario, obs + prescrição: series, reps (str), rir (0-4)
- **`SuperSerie`**: label (A/B/C...), ex1, ex2?, ex3?
- **`Sessao`**: tipo (string de padrões), blocos (lista de SuperSerie), `avisos` (list[dict] com `tipo: "incompleta" | "familia_repetida"` + metadata por demanda/exercício), `relaxados` (list[str] de nomes escolhidos via flexibilização de família)
- **SQLite**: tabela `alunos` (id, nome, nivel, objetivo, restricoes JSON, obs, rotina_ativa_id, rascunho_rotina JSON, rascunho_etiqueta, rascunho_intent) e `historico` (id, data_salvo, data_atualizada, aluno, etiqueta, n_treinos, sessoes JSON, configs JSON)

## Estado do servidor (variáveis globais em app_flask.py)

- `sessoes_ativas` — lista de Sessao (buffer de trabalho para gerador/edição)
- `configs_geradas` — config por treino (salva no histórico)
- `opcoes_globais` — n_treinos, max_complexidade, tamanho_bloco, variar_entre, evitar_agonistas, relaxar_familia
- `referencias` — lista de `{"sessao": Sessao, "origem": {...}, "id_ref": str}`. Auto-preenchidas ao gerar com histórico
- `edicao_hub` — dict com `aluno_id` e `rotina_id` quando editando rotina do HUB
- `criacao_manual` — dict com `aluno_id` e `novo_idx` quando há treino sendo criado manualmente
- Persistência via `sessoes_salvas.json` (auto-save + auto-restore)

## Navegação (rotas principais)

| URL | Página |
|-----|--------|
| `/` | HUB — seletor de aluno + rotina ativa + toggle Atual/Anterior |
| `/gerador` | Gerador — config hierarquia/template + resultado |
| `/gerador?aluno_id=X&acao=substituir&treino=N` | Gerador com contexto do HUB |
| `/alunos` | CRUD de alunos |
| `/historico` | Histórico de treinos |

Sidebar fixa à esquerda (60px, ícones) no desktop. Mobile: navegação horizontal no topo.

## Hierarquia de exercícios

| Região | Subregiões | Padrões |
|--------|------------|---------|
| upper | peito | empurrar_compostos, empurrar_isolados |
| | costas | remadas, puxadas |
| | ombro | ombro_composto, ombro_isolado, posterior_ombro |
| | bracos | biceps, triceps |
| lower | perna_anterior | squat |
| | perna_posterior | hinge, knee_flexion, abduction |
| | adutores | adduction |
| | panturrilha | flexao_plantar |
| core | core | core_isometrico, core_dinamico |
| cardio | cardio | cardio |

## Geração (gerador_treino.py)

Dois modos: **`gerar_sessao()`** (Templates, padrões + EPP) e **`gerar_sessao_por_demandas()`** (Hierarquia, demandas `[(nivel, escopo, qtd)]`, 60% compostos para região).

Fluxo: selecionar exercícios (similaridade) → ordenar compostos primeiro → montar blocos (geo-diversidade P1-P4, regra fadiga max 4) → ordenar blocos por score → gerar_multiplos_treinos (3 camadas bloqueio: nomes, variacao_de, similaridade).

**Bloqueio inter-treino (gerar_multiplos_treinos)**: dois sets globais separados — `nomes_exatos_globais` (apenas ex.nome, filtra `banco_filtrado`) e `variacao_pais_globais` (ex.nome + ex.variacao_de, controla bloqueio por família). Essa separação permite que pais concretos como "Apoio" sejam ressuscitados pelo relax quando só um filho foi usado. **Internamente** em `_selecionar_ciclando` e `selecionar_sem_repeticao_similaridade`, var_pais é dividido em `var_pais_inter` (read-only, herdado) e `var_pais_intra` (mutado within-session) — só `var_pais_inter` pode ser relaxado.

**Relaxamento de família** (`relaxar_familia: bool`, default ON na UI): quando uma demanda não pode ser preenchida no estrito, tenta 3 níveis em ordem: estrito → relaxa similaridade → relaxa família entre treinos (preserva intra). Exercícios escolhidos no relax 3 vão pra `Sessao.relaxados` (badge `↻` no UI) e geram aviso `tipo: "familia_repetida"`. Se mesmo relaxado faltar exercício (limite intra-família), gera aviso `tipo: "incompleta"`. Avisos são serializados na sessão e propagados via `flask.session['avisos_pendentes']` quando a rota /gerar redireciona pro HUB (substituir/adicionar/nova_rotina), pra que o modal apareça depois do redirect.

## Layout

**HUB** (`hub.html`) — seletor compacto de aluno no topo. Dois split buttons "+ Treino ▾" e "Nova rotina ▾" (cada um com sub-opções "Com gerador" / "Manual"). Toggle Atual/Anterior/Lado a lado dentro do badge do aluno (ícones i-eye, i-clock, i-columns). Grid de treino cards com ações (substituir, remover, regerar bloco). Banner de rascunho aparece automaticamente em qualquer alteração.

**Gerador** (`treinos.html`) — grid 3 colunas (lg): sidebar esquerda (aluno + histórico + config geral + botão gerar), main (abas T1-T5 com hierarquia/template), sidebar direita (referências). Context-aware via query params (`aluno_id`, `acao`, `treino`).

**Resultado** — grid auto-fit de treino cards. Foco de edição: card editado expande, demais colapsam.

**Mobile** — barra fixa inferior com Gerar + Ver treinos lado a lado (quando há treinos), ou Configurar (na tela de resultado).

## Convenções técnicas

- Sidebar fixa à esquerda com ícones; navegação via rotas reais (não tabs client-side)
- Partials (prefixo `_`) injetados via HTMX; `treinos.html` e pages estendem `base.html`
- `alunos.html`/`historico.html` são partials, wrappers `*_page.html` estendem base
- `hx-include` exige atributo `name` nos inputs
- `initSortable(t)` em `_treino_card.html` re-roda a cada HTMX swap
- Campos de formulário sufixados por treino: `modo_{t}`, `dem_nivel_{t}_{i}`, `dem_escopo_{t}_{i}`, `dem_qtd_{t}_{i}`, `epp_{t}_{padrao}`, `squat_bi_{t}`, `squat_uni_{t}`, `fixos_{t}`
- Rotina ativa: `rotina_ativa_id` na tabela alunos aponta para registro no histórico. Auto-setado ao salvar.
- **Rascunho/edição**: editar inline ativa rascunho automaticamente. Banner reativo via `hx-swap-oob` (helper `_responder_card_com_banner` adiciona OOB do banner em ~14 rotas `/treino/*` durante `edicao_hub`). Salvar tem dois modos: `atualizar` (sobrescreve registro mantendo id; preenche `data_atualizada`) e `nova` (cria registro novo, vira rotina ativa). Quando `rascunho_intent='nova-rotina'` (split "Nova rotina · Manual"), banner esconde "Atualizar rotina" para evitar sobrescrita acidental. Mini-header do aluno mostra "criada/atualizada há X" usando `data_atualizada` quando existe.
- **Diff rascunho × publicada**: helper `diff_rascunho_vs_publicada(aluno_id)` detecta `added` / `removed` / `edited` (prescrição) / `moved` (troca de posição). Para `moved`, pares simétricos (A↔B) viram um único registro de swap; movimentos avulsos (raros) viram registros individuais. Lazy-load via `/hub/rotina/<id>/alteracoes`. "Lado a lado" usa `classificar_exercicios_diff(atuais, anteriores)` com 4 estados visuais.
- **Estado por posição (rascunho)**: helper `_estados_rascunho_por_posicao(rascunho, publicada)` retorna `{(treino_idx, bloco_label, ei): estado}` com 4 estados — `mantido` / `swap` (mesmo nome em outra posição) / `substituido` (posição existia com outro nome) / `novo`. Passado como `estados_rascunho` para `_hub_treino_card.html` em 3 rotas (HUB principal, swap, visualizar-inline). Rendeiriza pills `.ex-pill-{mantido,swap,substituido,novo}` (ícone-only, sem texto) ao lado do nome quando há rascunho ativo.
- **Swap intra-treino por long-press (mobile)**: rota `POST /hub/rotina/<aluno>/treino/<t>/swap/<bi_a>/<ei_a>/<bi_b>/<ei_b>` faz swap atômico entre 2 exercícios do MESMO treino e persiste como rascunho **sem ativar `edicao_hub`** (escreve direto via `salvar_rascunho`). Long-press 500ms ativa modo swap, tap em outro exercício completa. JS usa `fetch` puro (não `htmx.ajax`) e por isso precisa chamar manualmente `htmx.ajax('GET', '/_mobile_bb_actions')` no callback pra atualizar a bottom bar. Atributos `data-swap-ex` + `data-aluno-id`/`data-treino-idx`/`data-bloco-idx`/`data-ei` em `.exercicio` em `_hub_treino_card.html` são obrigatórios pro JS funcionar.
- **Mobile bb (rascunho)**: `_mobile_bb_actions_hub.html` mostra "Atualizar" sempre que `_topbar_tem_rotina and _topbar_intent != 'nova-rotina'` — espelha o banner desktop. NÃO depende de `_topbar_alteracoes > 0` (que ignora moves; usar essa condição esconderia "Atualizar" após swaps).
- **Toggle Anterior**: quando há rascunho, "Anterior" passa a mostrar a rotina ativa publicada (não a anterior à ativa).
- **Autosave de prescrição**: `hx-trigger="focusout delay:300ms"` na form. Salva ao sair do form, não enquanto digita. Rota `/limpar` zera prescrição.
- **Badge `↻` (família repetida)**: classe `.badge-relaxado` em `base.html`. Renderizado em `_treino_card.html` e `_hub_treino_card.html` quando `ex.nome in sessao.relaxados`. Persiste através de serialização (`_sessao_to_dict`/`_dict_to_sessao` incluem o campo `relaxados`).
- **Modal de avisos** (`_avisos_modal.html`): auto-abre via IIFE inline. Distingue por tipo — `incompleta` mostra "ficou incompleto" + sugestões; `familia_repetida` mostra lista de exercícios relaxados. Botão "ver detalhes" reabre. Em fluxos de redirect (HUB), `session['avisos_pendentes']` é populada em `/gerar` e popped no `/` (index) — modal aparece no HUB após o setTimeout do snippet de redirect.

## Pendências (curto prazo)

- UI de exercícios fixos (backend suporta `exercicios_travados`, falta UI)
- Botão download ZIP na UI (rota existe)
- Lista de exercícios pausados por aluno
- Sistema de referências manuais legado (`_referencia.html`, `_comparacao.html`) — remover quando confirmado que toggle de período + lado a lado cobrem todos os casos

## Redesign mobile (em progresso · branch `mobile-redesign-02`)

**Etapas 1-12 de 12 concluídas** 🎉. Ver `docs/redesign/guia_redesign_mobile.md` (seção "🚦 Estado atual") para handoff completo + lista de commits + decisões importantes. Próxima: QA pass final + abrir PR pra `main` (ou Etapa 13 opcional: modo "Substituir treino" no gerador).

### O que mudou já no app (impacto fora do mobile)

- **Endpoints novos:**
  - `GET /_mobile_bb_actions` — re-fetch das ações da bb (HUB only)
  - `POST /hub/rotina/<id>/etiqueta` — autosave da etiqueta da rotina (rascunho ou histórico)
  - `POST /hub/rotina/<id>/concluir-edicao` — sai modo edição mantendo rascunho
- **`descartar-rascunho`** agora também limpa `edicao_hub` global
- **Função `database.atualizar_etiqueta_historico(reg_id, etiqueta)`** — UPDATE só da etiqueta
- **Context processor `_inject_topbar_aluno`** (em `app_flask.py`) injeta em TODOS os templates: `_topbar_alunos`, `_topbar_aluno`, `_topbar_tem_rotina`, `_topbar_eh_rascunho`, `_topbar_intent`, `_topbar_alteracoes`, `_topbar_em_edicao`, `_nav_alunos_total`, `_nav_sem_rotina`
- **`before_request` `_track_aluno_selecionado`:** `?aluno_id=X` na URL persiste na session; `?aluno_id=` (vazio) limpa
- **`_hub_treino_card.html`:** header reescrito — agora badge "T1" + nome customizado (ou "Treino N" como fallback) + 1 único botão kebab `...` à direita (estado kebab no mobile via `body.body--em-edicao`)
- **`_rotina_hub.html`:** card aluno simplificado — só nome + etiqueta editável inline (input com autosave). Removido nivel/objetivo/N treinos/data
- **`base.html`:** body recebe `data-active-page="{{ active_page or '' }}"`. Tokens novos no `:root`: `--bb-height`, `--bb-action-h`, `--bb-radius`, `--sheet-*`, `--drawer-*`, `--z-*`. Mobile breakpoint = `768px` (sidebar/hambúrguer escondidos no mobile real)
- **`_draft_banner.html`:** ganhou variante mobile compacta (1 linha amber com chevron expand pra alterações)
- **`_treino_card.html`:** removido `<span class="edit-mode-sub">Alterações são salvas automaticamente</span>` (texto redundante no banner do card editado)

### Bugs históricos a evitar (pra próximas etapas)

- **`:has()` quebra drag do SortableJS** — re-avalia CSS a cada mudança de classe (`sortable-ghost`, `sortable-chosen`). Use classe JS no body.
- **`}` órfã em `<style>`** fecha a tag prematuramente, descarta TUDO depois. Conferir abertura/fechamento ao adicionar blocos CSS.
- **Blocks dentro de `{% include %}`** não são overridables pelo template extending (Jinja). Pra slots dinâmicos, defina `{% block %}` direto em base.html.
- **Script no meio do body** roda no parse-time, antes do DOM completo. Use `DOMContentLoaded` ou delegação.
- **`fetch` puro não dispara `htmx:afterSwap`** — listeners que dependem disso (ex: refetch de `.bb-actions` mobile) precisam ser chamados manualmente no callback do `.then()`. Vale também pro inverso: se trocar `htmx.ajax` por `fetch` numa rota existente, mapear todos os listeners de `htmx:afterSwap` que reagem àquele target.
- **`hidden md:inline-flex` do Tailwind CDN às vezes perde** pra `.btn { @apply ... inline-flex }` por ordem de CSS. Se botões desktop "voltarem a aparecer" no mobile, adicionar `display: none !important` defensivo dentro de `@media (max-width: 768px)`.
- **`_responder_card_com_banner` ativa `edicao_hub`** — não usar pra ações que devem só salvar rascunho sem entrar em modo edição (ex: swap por long-press). Pra esses casos, escrever rascunho direto via `salvar_rascunho()` e renderizar `_hub_treino_card.html` (visualizar) + `render_draft_banner_oob()`.

## Como rodar

```bash
python app_flask.py
# http://localhost:5000
```

### Regra para iniciar o servidor

1. Checar porta 5000 com `Get-NetTCPConnection` antes de iniciar
2. Matar processo existente na porta antes de reiniciar
3. Usar `run_in_background` do Bash tool (nunca `&`)
4. Salvar o PID em `server.pid` na raiz do projeto: `echo $! > server.pid`
5. **Ao final da sessão**: sempre matar o servidor antes de encerrar, usando o PID salvo ou `Get-NetTCPConnection`. Processos órfãos ficam invisíveis ao OS e só morrem com reinício do PC.
