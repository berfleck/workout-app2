# Handoff — Swipe + edição direta (sessão 2026-06-15)

Continuação do `guia_swipe_edicao_direta.md`. Esta sessão fechou os Sub-PRs 1–4
+ um follow-up de redesign do card. Tudo validado no **mobile real** pelo Bernardo.

> **Atualização 2026-06-15 (parte 2): Sub-PR 5 CONCLUÍDO e mergeado FF em `main`.**
> Core (C1-C4) + refino de UI no mobile real (C5-C9, kebab-only + "+" sob demanda).
> Pytest 386 OK. Ver seção "Sub-PR 5 — CONCLUÍDO" no fim. Próximo: Sub-PR 6 (modo
> prescrição como drawer).

## Estado do branch

- Branch: **`feat-card-etiqueta-rascunho`** (pushed em `origin`), histórico **linear**
  sobre `main` (`60a43de`). Os Sub-PRs foram empilhados; o tip contém todos os commits.
- **Mergeado em `main` (fast-forward) e pushado em 2026-06-15.** A próxima sessão pode
  branchar direto de `main` para o Sub-PR 5.

| Commit | Conteúdo |
|---|---|
| `8f85924` | Sub-PR 1 — Alpine.js (plataforma): CDNs + stores `carry`/`highlight` + `hx-ext="alpine-morph"` + `.just-changed` |
| `de7a022` | Sub-PR 2 — Swipe entre treinos (Frente A): body flex 100dvh, chip pager, swipe-track, counter+kebab período na topbar |
| `994f39a` | Sub-PR 3 — Pill modo carregando + swap inter-treino (Frente B): rota unificada, `applyStructuralResult`, highlight |
| `948d7b0` | Sub-PR 4 — Edição estrutural nível exercício (Frente C p1): tap→action sheet, long-press→carry, 4 rotas viz |
| `6821d42` | Card redesign: chip "Rascunho", remoção dos pills, "descrição" autogrow, header reordenado |

## O que falta (guia §9)

- **Sub-PR 5 — Edição estrutural nível BLOCO (Frente C parte 2).**
  - Mini-kebab `…` no header do bloco → action sheet: Adicionar exercício / Regerar bloco / Remover bloco.
    Rotas existentes a reaproveitar: `bloco_regerar`, `bloco_deletar` (estão no contexto `/treino/` antigo — provavelmente
    precisam de versões HUB-viz no rascunho, como fizemos no Sub-PR 4).
  - **Toast undo de 5s** ao remover bloco (§7.4 item 5 / §10.7): infra client-side nova reusável; qualquer mutação
    estrutural na janela expira o toast (snapshot client-side pra reverter).
  - **Reorder de bloco** via long-press no rótulo do bloco → `$store.carry.pegar('bloco', …)` → gaps viram drop zones
    → tap no gap reposiciona (rota `blocos/reordenar`, body `ordem=[...]`). `$store.carry.estaCarregandoBloco` já existe.
  - **Inserir bloco** via "+" entre blocos → picker (modal Alpine + HTMX, `_substituicao.html` adaptado) com 1–2 ex
    (decisão §10.3). "compostos primeiro" decide ex1/ex2.
  - Possível consolidação backend `inserir_bloco` (§7.6).

- **Sub-PR 6 — Modo prescrição como drawer (Frente C parte 3).**
  - Refatorar o modo edição clássico (séries/reps/RIR em lote) como **drawer** que sobe do bottom (~70%).
  - Acesso via kebab do treino card → "Prescrever". Autosave `focusout delay:300ms` (infra já existe).
  - `edicao_hub` ainda ativa quando o drawer abre (autosave depende), mas como é overlay não polui a viz.
  - **Resolve a dívida atual:** hoje editar prescrição inline no mobile cai pro layout empilhado
    (fallback CSS `.hub-swipe-track:not(.focando-edicao)`).

- **Sub-PR 7 — Saneamento.**
  - Remover **código morto** desta sessão: popup `openExerciseActionPopup` + `_renderPopupContent` +
    `_doPopupSubstituir` + listeners do popup (inertes); rota antiga `hub_swap_visualizar` (intra, não usada);
    CSS `.swap-indicator*` (substituído pela pill); var `sessao_render` morta em `hub_substituir_aleatorio`;
    CSS `.treino-num-badge` (badge T1 removido do card).
  - Auditar `_responder_card_com_banner` vs `_render_swap_cards` (viz). Documentar a divisão no `CLAUDE.md`.
  - Manter `bloco_mover` (setas) como fallback de acessibilidade.

## Operacional (importante!)

- **Porta 5000 tem um socket-fantasma** (processo morto, `Stop-Process`/`taskkill` não matam — só morre com reboot do PC).
  Use **5001**: `FLASK_DEBUG=0 PORT=5001 python app_flask.py` (background). Com `FLASK_DEBUG=0` **não há auto-reload de
  template → reiniciar o servidor após editar `.html`**. Matar por porta:
  `Get-NetTCPConnection -LocalPort 5001 -State Listen | % { Stop-Process -Id $_.OwningProcess -Force }`.
- **Mobile real:** `http://192.168.1.15:5001` (mesma rede; Firewall do Windows pode pedir liberar a porta → Redes privadas).
- **Aluno de teste:** id **18** ("Teste CSP", 2 treinos). Sempre limpar após testar: `descartar-rascunho` + setar etiqueta vazia.
  Maria Santos (10) tem 3 treinos. **Nunca testar mutações no Bernardo (id 3) sem descartar depois.**
- **Gates de validação:** `pytest -q` (376 passed, 2 skips pré-existentes) · braces dos `<style>` balanceados
  (bug histórico de `}` órfã) · `node --check` nos IIFEs extraídos · **smoke mobile obrigatório** (long-press é frágil — protocolo §9).

## Decisões & contexto técnico (não reabrir sem motivo)

- **Alpine**: `$store.carry` espelha o estado do gesto (a detecção de long-press segue JS puro — **não tocar**,
  é o que o protocolo §9 cobre). Pill `.carry-pill` é componente Alpine (`x-show $store.carry.tipo`).
- **Swap unificado**: `POST /hub/rotina/<a>/swap/<ta>/<bia>/<eia>/<tb>/<bib>/<eib>`. Resposta =
  `.swap-card-result[data-treino-idx]` (1–2) + banner OOB. `window.applyStructuralResult(html, highlightPositions)`
  é o aplicador compartilhado (roteia cards, aplica OOB, highlight, refetch da bb). `window.highlightSwapped` exposto.
- **Rotas viz nível exercício** (rascunho, sem `edicao_hub`): `tornar-solo` (bloco ACIMA §10.2), `mover-bloco`,
  `mover-treino` (bloco solo no fim do destino), `remover`; `substituir-aleatorio` unificado pro mesmo formato.
- **Gesto**: tap curto → `window.openExSheet` (action sheet `_mobile_ex_action_sheet.html`); long-press → carry direto.
- **Card**: `Sessao.etiqueta` (campo novo, serializado). "Descrição" = autogrow inline-grid + `::after` espelho
  (`data-value = value || placeholder`), itálico, fundo `gray-100` arredondado. Chip "Rascunho" via `eh_rascunho`
  (`_render_swap_cards` passa `True`). Banner de rascunho mobile escondido no hub (desktop mantém — tem as ações lá).
- **Persistência etiqueta do treino**: in-place — rascunho se houver, senão `atualizar_historico_registro`
  (espelha a etiqueta da rotina; digitar a nota NÃO cria rascunho).
- **Altura do swipe**: `body[data-active-page="hub"].hub-swipe-on` vira flex coluna `100dvh`; cadeia de `flex:1`
  até `.hub-swipe-track`; `.hub-treino-page` é `flex:0 0 100%; min-width:0; overflow-x:hidden`. `--hub-inset` (22px)
  = respiro lateral do texto (fundos full-bleed).

## Arquivos tocados nesta sessão

- `templates/base.html` (CSS + pill + ex action sheet JS + gesto + topbar tools + hub swipe), `templates/hub.html`
  (`initHubSwipe`), `templates/_rotina_hub.html` (pager + classes), `templates/_hub_treino_card.html` (header + descrição),
  `templates/_mobile_ex_action_sheet.html` (novo), `app_flask.py` (rotas swap/exercício/etiqueta + serialização),
  `gerador_treino.py` (`Sessao.etiqueta`).

---

# Sub-PR 5 — CONCLUÍDO (2026-06-15 parte 2 · Frente C parte 2 · §7.2-7.4, §10.7)

Branch **`feat-sub-pr5-bloco`** (de `main`) → **mergeado FF em `main` + pushado**.
Core (C1-C4) + refino de UI no mobile real do Bernardo (C5-C9). Plano em
`.claude/plans/swift-discovering-twilight.md`.

| Commit | Conteúdo |
|---|---|
| `13e101b` | C1 — rotas de bloco HUB-viz (backend) + refactor `hub_regerar_bloco` + 11 pytest |
| `c5d4f2e` | C2 — mini-kebab + gaps dual-mode + partials + CSS (templates) |
| `5af9b53` | C3 — gesto de bloco + sheet + picker + carry-pill generalizada + `highlightBloco` (JS) |
| `a5dd784` | C4 — toast undo de remover bloco (§10.7) |
| `34b1b3c` | C5 — fix "+" (overflow:visible/z-index) + tirar prescrição default + folga badge |
| `3d7bb31` | C6 — gutter do bloco (ferramentas = bloco inteiro; separadores param antes da direita) |
| `864e3ca` | C7 — fix kebab vazando pra fora da tela (largura auto, sem caixa fixa) |
| `15ce1b8` | C8 — **handle ⠿ removido** (reorder só via kebab) + mais respiro (`--hub-inset` 28) |
| `692dfd1` | C9 — **"+" sob demanda** via "Novo bloco" no kebab do TREINO (store `insertBloco`) |

## Decisões finais (algumas revisadas no mobile real)
- **Pegar bloco = KEBAB-ONLY** (revisado em C8; antes era handle+kebab). O handle ⠿ de
  long-press foi **removido**; reorder vive só no kebab do bloco → "Mover bloco" → entra
  em carry → gaps viram "Soltar aqui". Menos colisão de gesto, mais limpo.
- **"+" de inserir = SOB DEMANDA** (revisado em C9; antes sempre visível). Escondidos por
  padrão; aparecem só após "Novo bloco" no kebab do TREINO (store Alpine `insertBloco.treino`).
  Tap num "+" abre picker e desliga o modo; tap fora cancela.
- **Card de viz não tem header de bloco** → ferramentas num **gutter à direita** que cobre a
  altura do bloco (não a 1ª linha). Separadores entre exercícios param antes do gutter (`::before`
  com inset à direita). `--hub-inset` 22→28 (respiro esq/dir simétrico).
- **Sem prescrição default** em exercício novo (C5) — entra sem séries/reps/RIR (igual add manual).
- **NÃO consolidei** na mega-rota `inserir_bloco` da §7.6 (reuso nos helpers dict).
- **Reorder = `mover-para/<pos>`** (não `ordem=[...]`): off-by-one `dest = pos<=bi?pos:pos-1`
  no helper puro `_mover_bloco_dict`.

## Rotas novas (app_flask.py, todas HUB-viz → `_render_swap_cards`, sem `edicao_hub`)
- `POST .../treino/<t>/blocos/<bi>/remover` — devolve cards + `<script id="removed-bloco-snapshot">` (JSON do bloco cru) pro toast undo.
- `POST .../treino/<t>/blocos/<bi>/mover-para/<pos>` — reorder (helper `_mover_bloco_dict`).
- `POST .../treino/<t>/blocos/inserir/<pos>` — body `exercicios[]` (1-2); `ordenar_compostos_primeiro` → ex1.
- `POST .../treino/<t>/blocos/<bi>/adicionar` — body `exercicios[]` (1); falha se bloco cheio.
- `POST .../treino/<t>/blocos/inserir-existente` — undo (JSON `{posicao, bloco}`, preserva prescrição).
- `GET /buscar-exercicios-picker?texto=` — linhas multi-select (`_bloco_picker_rows.html`).
- Refactor: `hub_regerar_bloco` devolve `_render_swap_cards` (highlight, sem reload).

## Client (base.html) — estado final
- Stores Alpine: `carry` (ex/bloco), `highlight`, **`insertBloco { treino }`** (modo "Novo bloco").
- Reorder de bloco: kebab "Mover bloco" → `enterCarryBloco({alunoId,t,bi,label})` (recebe contexto,
  não elemento). `touchstart` voltou a mirar só exercício (sem handle de bloco).
- `applyStructuralResult(html, hl, opts)`: chama `expireBlocoUndoToast()` no topo exceto
  `opts.isUndo` (§10.7 — autosave de prescrição não passa aqui → não invalida).
- IIFEs: action sheet do bloco + picker (multi-select por delegação) + toast undo (redefine
  `window.removerBlocoFlow`). carry-pill generalizada (ex "Trocando:" / bloco "Movendo:").
- `.bloco-gap` macro: "+" x-show `$store.insertBloco.treino === t_idx`; "Soltar aqui" só
  carregando bloco do MESMO treino, ocultando os 2 gaps adjacentes. `md:hidden`.

## Verificação
- **pytest 386** (375 base + 11 em `tests/test_blocos_hub_viz.py`), 2 skips.
- **`node --check`** OK; braces dos 2 `<style>` balanceados (661/661, 396/396).
- **Smoke de servidor (curl, aluno 18)**: reorder, remover+snapshot, inserir 1/2 ex (compostos
  primeiro), adicionar, undo round-trip, regerar — todas OK. Rascunho descartado.
- **Validação no mobile real** (Bernardo, durante a sessão) guiou os refinos C5-C9.

---

# Sub-PR 6 — CONCLUÍDO (2026-06-16 · Frente C parte 3 · §7.5, §10.8)

Branch **`feat-sub-pr6-prescricao-drawer`** (de `main`) — validado no mobile real
do Bernardo. Modo edição clássico vira **drawer de prescrição** no mobile.

| Commit | Conteúdo |
|---|---|
| `ff91d47` | Drawer (séries/reps/RIR) via kebab → "Prescrever"; rota GET .../prescrever; templates + IIFE + CSS |
| `5328463` | fix — IIFE em DOMContentLoaded (shell #prescr-drawer é incluído depois no body) |
| `318bb8b` | fix — race do autosave com o fechamento (backdrop não fecha + visualizar-inline atrasado 500ms) |

## Arquitetura
- **Acesso:** kebab do treino card → **"Prescrever"** (`data-kebab-prescrever`,
  ícone `i-clipboard-list`). Substituiu "Editar treino" no mobile — substituir/
  mover/remover/regerar já migraram pra viz nos Sub-PRs 4-5. Desktop mantém o
  lápis → `editar-inline` (modo edição clássico) intocado.
- **Drawer** (`_mobile_prescricao_drawer.html` shell + `_prescricao_lista.html`
  conteúdo): sobe ~72%, overlay sobre a viz. NÃO renderiza card `modo-editar` →
  `body--em-edicao`/`focando-edicao` ficam off → swipe atrás intacto.
- **Backend reusado:** save por focusout usa `/treino/<t>/prescricao/<bi>/<ei>`
  existente (`hx-swap="none"` → só OOB do banner; toast de autosave dispara
  sozinho). Limpar reusa `/limpar` + re-busca o drawer (`refreshPrescricaoDrawer`).
- **Rota nova (única):** `GET .../treino/<t>/prescrever` — ativa `edicao_hub`
  (autosave depende) e renderiza a lista. **NÃO grava** — abrir o drawer sozinho
  não cria rascunho (≠ `editar-inline`, que chamava `salvar_sessoes_disco`).
- **Concluir** (botão / ESC): `visualizar-inline` re-renderiza o card de viz
  (badges atualizados) e zera `edicao_hub`; bb refetcha via listener de `#treino-*`.

## Decisões / armadilhas (não reabrir sem motivo)
- **IIFE em DOMContentLoaded** (não parse-time): o include do shell vem DEPOIS do
  `<script>` no body. (Mesma classe de bug do CLAUDE.md "script no meio do body".)
- **Backdrop NÃO fecha o drawer** — só "Concluir"/ESC. No mobile, o tap que
  dispensa o teclado vaza pro overlay e fechava sem querer.
- **Autosave × fechamento (race crítico):** focusout tem `delay:300ms`; fechar
  chamava `visualizar-inline` na hora, zerando `edicao_hub` antes do POST atrasado
  → `salvar_sessoes_disco` pulava o rascunho → prescrição perdida (a pré-existente,
  vinda da publicada, sobrevivia). Fix: `close()` faz blur do input ativo (dispara
  o autosave) e atrasa o `visualizar-inline` em **500ms** (> 300ms do debounce).
  Servidor single-thread serializa requests → o POST persiste antes do clear.

## Verificação
- **pytest 386** passed, 2 skips (sem teste novo — rota é wrapper fino, lógica
  pura toda reusada; cobertura via smoke).
- **`node --check`** OK no IIFE; braces dos `<style>` balanceados (682/396).
- **Smoke curl (aluno 18)**: open → save B2 → save C2 → reopen mostra ambos;
  limpar zera + esconde botão; visualizar-inline reflete badge. Rascunho descartado.
- **Mobile real** (Bernardo): drawer abre, edita múltiplos exercícios numa
  abertura, Concluir persiste tudo. Os 2 fixes saíram dessa validação.

## Resta (Sub-PR 7 — Saneamento, guia §9 item 7) — ✅ CONCLUÍDO abaixo

---

# Sub-PR 7 — CONCLUÍDO (2026-06-16 · Saneamento · guia §9 item 7)

Branch **`feat-sub-pr7-saneamento`** (de `main`). Remoção de código morto
acumulado nos Sub-PRs 3-6 — **net −375 linhas**. Sem mudança funcional.

| Commit | Conteúdo |
|---|---|
| `bb793a0` | Remove popup inerte + CSS órfã + rota 4-param + var morta; doc da divisão no CLAUDE.md |

## Removido
- **Mini-popup de ações por exercício** (`base.html`): `openExerciseActionPopup`
  (nunca chamado — substituído pelo action sheet do Sub-PR 4) + `_renderPopupContent`
  + `_doPopupSubstituir` + `_positionPopup` + `_reanchorPopup` + `closeExerciseActionPopup`
  + `popupState` + `_slotFromEi` + os 4 listeners (click/ESC/scroll/beforeSwap) +
  o guard `.ex-action-popup` no `touchstart` live.
- **CSS órfã** (`base.html`): `.ex-action-popup*`, `body.action-popup-open`,
  `.exercicio.action-popup-target` (popup); `.swap-indicator*` (virou a `.carry-pill`
  Alpine); `.treino-num-badge` (badge T1 saiu do card).
  **Preservados:** `.exercicio.swap-selected` + `@keyframes swapPulse` (live).
- **Rota `hub_swap_visualizar`** (`app_flask.py`, 4-param `/swap/`) — substituída
  pela unificada de 6 params (intra+inter) no Sub-PR 3; sem caller.
- **Var morta `sessao_render`** em `hub_substituir_aleatorio` (o return relê
  `sessoes_dicts`, então a var não fazia nada).

## Documentado (CLAUDE.md)
- Tabela da divisão `_render_swap_cards` (viz, **sem** `edicao_hub`) vs
  `_responder_card_com_banner` (editar/prescrição, **com** `edicao_hub`).
- Modo editar inline (`editar-inline` + `_treino_card.html`) agora é **desktop-only**.
- `bloco_mover` (setas) = fallback de acessibilidade desktop.

## Verificação
- **pytest 386** passed, 2 skips · `py_compile` OK.
- **Sem refs pendentes** aos símbolos removidos (grep limpo).
- **braces `<style>`** 647/396 · **`node --check`** no swap IIFE OK.
- **Smoke curl (aluno 18)**: page 200, swap unificado 200, substituir-aleatorio 200,
  prescrever 200; **rota antiga 4-param → 404** (confirma remoção). Rascunho descartado.

---

# 🎉 Iniciativa swipe + edição direta — COMPLETA (Sub-PRs 1-7)

Todos os 7 sub-PRs mergeados em `main`. Frente A (swipe), Frente B (swap
inter-treino), Frente C (edição estrutural viz + drawer de prescrição) e o
saneamento final concluídos. Modo editar clássico sobrevive só no desktop.
