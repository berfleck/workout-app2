# Handoff — Swipe + edição direta (sessão 2026-06-15)

Continuação do `guia_swipe_edicao_direta.md`. Esta sessão fechou os Sub-PRs 1–4
+ um follow-up de redesign do card. Tudo validado no **mobile real** pelo Bernardo.

## Estado do branch

- Branch: **`feat-card-etiqueta-rascunho`** (pushed em `origin`), histórico **linear**
  sobre `main` (`60a43de`). Os Sub-PRs foram empilhados; o tip contém todos os commits.
- **Não mergeado em `main`** ainda (decisão de merge é do Bernardo).

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
