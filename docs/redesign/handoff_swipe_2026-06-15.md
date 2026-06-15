# Handoff — Swipe + edição direta (sessão 2026-06-15)

Continuação do `guia_swipe_edicao_direta.md`. Esta sessão fechou os Sub-PRs 1–4
+ um follow-up de redesign do card. Tudo validado no **mobile real** pelo Bernardo.

> **Atualização 2026-06-15 (parte 2): Sub-PR 5 implementado** no branch
> `feat-sub-pr5-bloco` (a partir de `main`), commits 1–4 abaixo. **Pendente:
> smoke mobile real do Bernardo + merge.** Pytest 386 + smoke de servidor (curl)
> de todas as 6 rotas OK. Ver seção "Sub-PR 5 — implementado" no fim.

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

# Sub-PR 5 — implementado (2026-06-15 parte 2 · Frente C parte 2 · §7.2-7.4, §10.7)

Branch **`feat-sub-pr5-bloco`** (de `main`). **Falta:** smoke mobile real (§9, agora
inclui handle ⠿ de bloco) + merge FF. Plano em `.claude/plans/swift-discovering-twilight.md`.

| Commit | Conteúdo |
|---|---|
| `13e101b` | C1 — rotas de bloco HUB-viz (backend) + refactor `hub_regerar_bloco` + 11 pytest |
| `c5d4f2e` | C2 — mini-kebab + handle ⠿ + gaps dual-mode + partials + CSS (templates) |
| `5af9b53` | C3 — gesto de bloco + sheet + picker + carry-pill generalizada + `highlightBloco` (JS) |
| `a5dd784` | C4 — toast undo de remover bloco (§10.7) |

## Decisões desta parte
- **Pegar bloco = AMBOS** (Bernardo): handle ⠿ (long-press) **E** "Mover bloco" no
  kebab. O card de viz **não tem header de bloco** ("BLOCO A" é `display:none` no
  modo-visualizar; o rótulo é "A1/A2" dentro do exercício) — então a premissa §3.3
  "kebab ao lado de BLOCO A" não existe. Solução: **overlay absoluto** (handle ⠿ +
  kebab …) no canto sup. dir. do `.bloco-wrap`, custo vertical zero.
- **NÃO consolidei** na mega-rota `inserir_bloco` da §7.6 (reuso fica nos helpers dict,
  não nas rotas — `hub_ex_tornar_solo`/`mover_treino` já funcionam e têm testes).
- **Reorder = `mover-para/<pos>`** (não `ordem=[...]`): 1 origem na URL + 1 destino,
  off-by-one `dest = pos<=bi?pos:pos-1` no helper puro `_mover_bloco_dict`.

## Rotas novas (app_flask.py, todas HUB-viz → `_render_swap_cards`, sem `edicao_hub`)
- `POST .../treino/<t>/blocos/<bi>/remover` — devolve cards + `<script id="removed-bloco-snapshot">` (JSON do bloco cru) pro toast undo.
- `POST .../treino/<t>/blocos/<bi>/mover-para/<pos>` — reorder (helper `_mover_bloco_dict`).
- `POST .../treino/<t>/blocos/inserir/<pos>` — body `exercicios[]` (1-2); `ordenar_compostos_primeiro` → ex1.
- `POST .../treino/<t>/blocos/<bi>/adicionar` — body `exercicios[]` (1); falha se bloco cheio.
- `POST .../treino/<t>/blocos/inserir-existente` — undo (JSON `{posicao, bloco}`, preserva prescrição).
- `GET /buscar-exercicios-picker?texto=` — linhas multi-select (`_bloco_picker_rows.html`).
- Refactor: `hub_regerar_bloco` agora devolve `_render_swap_cards` (highlight, sem reload).

## Client (base.html)
- Gesto: `touchstart` testa `[data-carry-bloco]` ANTES de `[data-swap-ex]` (precedência
  §9 caso f). Estado `carryBloco` + `pressKind`. `cancelSwapMode` limpa ex E bloco.
  `enterCarryBloco`, `performReorder`, `highlightBloco`.
- `applyStructuralResult(html, hl, opts)` ganha 3º arg; chama `expireBlocoUndoToast()`
  no topo exceto `opts.isUndo` (§10.7 — autosave de prescrição não passa aqui, então
  não invalida, por construção). Sem heurística de path.
- 2 IIFEs novas: action sheet do bloco + picker (delegação multi-select). Toast IIFE
  redefine `window.removerBlocoFlow` (extrai snapshot → applyStructuralResult → show).
- carry-pill generalizada (ex "Trocando:" / bloco "Movendo:").
- `.bloco-gap` macro (`_hub_treino_card.html`): "+" inserir em repouso / "Soltar aqui"
  só carregando bloco do MESMO treino, ocultando os 2 gaps adjacentes (no-op). `md:hidden`.

## Verificação feita
- **pytest 386** (375 base + 11 novos em `tests/test_blocos_hub_viz.py`), 2 skips. Cobre
  off-by-one do `_mover_bloco_dict` nos 2 sentidos + no-ops + prescrição default.
- **`node --check`** OK nos IIFEs novos; braces dos 2 `<style>` balanceados.
- **Smoke de servidor (curl, aluno 18)**: reorder+relabel, remover+snapshot island,
  inserir 1/2 ex (compostos primeiro), adicionar, undo round-trip (bloco volta na posição
  com prescrição), regerar — todas → `.swap-card-result` + banner OOB. Rascunho descartado.

## Smoke mobile pendente (Bernardo · `http://192.168.1.15:5001`, aluno 18)
Servidor já rodando em background (PID em `server.pid`). Casos críticos:
- (handle) long-press no ⠿ pega o bloco; pill "Movendo: Bloco X"; gaps viram "Soltar aqui".
- (precedência §9-f) long-press no ⠿ NÃO dispara carry de exercício adjacente.
- reorder via handle **e** via kebab → "Mover bloco"; gaps de drop só no MESMO treino;
  gaps adjacentes ao bloco carregado ocultos.
- "+" entre blocos abre picker; selecionar 1-2 → "Adicionar (N)" → bloco novo + highlight.
- kebab do bloco: Adicionar/Regerar/Remover; remover → toast 5s; Desfazer reverte;
  fazer outra mutação na janela → toast expira; prescrição (focusout) NÃO expira.
