# Guia de redesign mobile — BF Treinamento (redesign 02)

> **Para o Claude Code:** este documento + os 3 arquivos HTML em `docs/redesign/mobile/` são a fonte da verdade do redesign mobile. Antes de implementar qualquer etapa, leia este guia inteiro e o mockup HTML correspondente. Os mockups são a referência visual final — qualquer divergência entre o que está descrito aqui e o que está nos mockups, **o mockup vence.**
>
> **Pergunte se tiver dúvida.** Antes de começar uma etapa, se você não estiver 100% certo sobre comportamento, posicionamento ou estado, **pare e pergunte ao usuário** em vez de inferir. Não tem problema fazer 2-3 perguntas seguidas para travar a etapa antes de codar.
>
> **Commit ao fim de cada etapa.** Cada etapa deste guia deve terminar com um commit no GitHub seguindo o padrão `mobile(<escopo>): <descrição curta>`. A lista exata de mensagens de commit está em cada etapa.

---

## Visão geral

Este redesign **não substitui o anterior** — ele refina a experiência **mobile (~380px)** sobre o que já foi entregue no redesign 01. O desktop fica como está. O foco é:

- **Bottom bar contextual fixa** com slot esquerdo (menu) + slots dinâmicos à direita
- **Sem sidebar / sem hambúrguer no mobile** — a navegação vai pra um bottom sheet
- **Densidade vertical reduzida** — card do aluno em 1 linha, treino card em 1 linha, banner de rascunho em 1 linha
- **Drawer lateral para escolher demandas** no Gerador (mesmo padrão do drawer de substituição)

### Os 3 mockups

| Mockup            | Arquivo                                    | Fluxos cobertos                                                              |
| ----------------- | ------------------------------------------ | ---------------------------------------------------------------------------- |
| **HUB**           | `docs/redesign/mobile/mockup_mobile_hub.html`     | 4 estados do HUB (sem aluno, visualizando, rascunho, editando)              |
| **Gerador**       | `docs/redesign/mobile/mockup_mobile_gerador.html` | Variante A2 (drawer) + tela de resultado pós-Gerar                          |
| **Auxiliares**    | `docs/redesign/mobile/mockup_mobile_aux.html`     | Bottom sheet de navegação, kebab do treino, lista de alunos, histórico      |

> ⚠ **Importante:** o mockup do Gerador tem 2 variantes (A1 e A2). A decisão validada com o usuário é **A2 (drawer lateral)**. Implemente apenas A2. A1 está no mockup só para referência.

---

## Princípios (não-negociáveis)

1. **Mobile-first NESTE redesign.** O desktop já está pronto. Cada decisão aqui é validada em ~380px primeiro. Use `@media (max-width: 768px)` para isolar o que é mobile, ou flag CSS via container queries quando fizer sentido.
2. **Bottom bar é o único lugar de ação primária no mobile.** Nada de FAB flutuante. Nada de botão "salvar" perdido no scroll. As ações principais sempre na bottom bar.
3. **Slot esquerdo da bottom bar é fixo** — sempre o ícone de menu (grid 4×4) que abre o sheet de navegação. Slots à direita mudam por contexto.
4. **Bottom sheets ao invés de modais centrais no mobile.** Slide-up animado, grabber no topo, max-height 80%.
5. **Cortar antes de adicionar.** Para cada string nova, perguntar: o personal precisa ler isso enquanto está atendendo um aluno? Se a resposta for "não", remove.
6. **Não duplicar elementos do desktop.** A barra inferior antiga do `/gerador` (Gerar/Configurar/Ver treinos) some no mobile e vira a nova bottom bar contextual.

---

## Sistema de design (mantido do redesign 01)

Os tokens de cor, tipografia e ícones são **idênticos** ao redesign 01. Não invente nada novo. Os mockups dessa etapa usam:

- **Fontes:** `DM Sans` (corpo), `JetBrains Mono` (números/prescrições/meta), e **opcionalmente** `Bricolage Grotesque` para títulos de display dentro do app — só adicione se isso já estiver no `base.html`. Caso contrário, mantém DM Sans nos títulos.
- **Cores:** `--brand-500` (#e85d04) e família, cinzas, âmbar (rascunho), verde (sucesso), vermelho (perigo)
- **Ícones:** Lucide via `<symbol>` reutilizáveis (mesmo sistema do redesign 01)

---

## Tokens novos (adicionar)

Adicione estes ao bloco existente de tokens (provavelmente em `base.html` ou `tokens.css`):

```css
:root {
    /* Bottom bar e sheets (mobile) */
    --bb-height: 70px;          /* altura total da bottom bar com safe-area */
    --bb-action-h: 46px;        /* altura dos botões dentro da bottom bar */
    --bb-radius: 12px;          /* raio dos botões */
    --sheet-max-h: 80%;         /* max-height do bottom sheet */
    --sheet-radius: 24px;       /* raio top do sheet */
    --drawer-width: 92%;        /* largura do drawer lateral (mobile) */
    --drawer-radius: 24px;      /* raio left do drawer */

    /* Z-index */
    --z-bottom-bar: 40;
    --z-drawer: 60;
    --z-sheet-overlay: 70;
    --z-sheet: 71;
}
```

---

## Plano de execução (12 etapas)

> Cada etapa é **independente e pequena o suficiente para review por commit**. Faça uma etapa por vez. **Pergunte ao usuário antes de pular ou agrupar etapas.**

### 📋 Como executar cada etapa

1. Leia a seção da etapa **e o mockup correspondente**.
2. Liste para o usuário o que você vai fazer (3-5 bullets) e **pergunte qualquer dúvida** antes de codar.
3. Implemente.
4. Teste em mobile (DevTools, viewport 380×760, toque ativado).
5. Faça commit com a mensagem padrão da etapa.
6. Marque a etapa como ✅ aqui no guia (edite este arquivo, não esqueça).
7. Pergunte ao usuário se quer prosseguir para a próxima etapa ou validar a atual em produção.

---

## Etapa 1 · Limpeza da topbar mobile ✅

**Mockup:** `mockup_mobile_hub.html` · todos os cenários

**Objetivo:** Tirar o hambúrguer e os títulos decorativos do mobile, deixando só a logo BF + pill do aluno.

**O que fazer:**
- No `base.html`, esconder no mobile (`@media max-width: 768px`):
  - Botão hambúrguer (sidebar toggle)
  - Sidebar lateral inteira
  - Eyebrow "Painel principal" e título "Gerenciamento das rotinas de treino"
- Substituir a topbar do mobile por: `[logo BF 32px] [pill do aluno full-width]`
- A pill do aluno já existe no app — adapte para ocupar `flex: 1` no mobile e ter `border-radius: 999px`
- Ao tocar na pill no mobile, abre o seletor de aluno (mesmo modal/sheet que já existe — não criar novo)

**Perguntas para fazer ao usuário antes de começar:**
- "O seletor de aluno hoje abre como dropdown ou modal? Quer que no mobile vire um bottom sheet (estilo iOS) ou mantém o comportamento atual?"
- "A logo BF deve linkar pra `/` ou pro hub do aluno atual?"

**Critério de aceite:**
- Em 380px, o topo mostra apenas: logo + pill + 0 outros elementos
- Hambúrguer e sidebar invisíveis no mobile
- Em desktop (≥768px), nada muda

**Commit:** `mobile(topbar): simplifica topbar para logo + pill do aluno`

---

## Etapa 2 · Bottom bar contextual (estrutura base) ✅

**Mockup:** `mockup_mobile_hub.html` · cenário B (visualizando)

**Objetivo:** Criar o componente da bottom bar fixa que vai ser usado em todas as páginas mobile.

**O que fazer:**
- Criar um novo template parcial: `templates/_mobile_bottom_bar.html`
- Estrutura:
  ```html
  <nav class="bb" data-bb>
    <button class="bb-nav" data-open-nav-sheet>
      <svg>...</svg>  <!-- icon: grid -->
    </button>
    <div class="bb-actions" data-bb-actions>
      <!-- slot dinâmico — inserido pelas páginas via {% block bb_actions %} -->
    </div>
  </nav>
  ```
- Estilizar conforme mockup: `position: fixed`, `bottom: 0`, `backdrop-filter: blur(16px)`, `padding: 10px 12px 14px` (com safe-area-inset-bottom)
- Slot esquerdo: botão de 46×46 com ícone grid, sempre presente
- Slot direito (`bb-actions`): aceita 1-3 botões via block Jinja
- Adicionar `padding-bottom: calc(var(--bb-height) + 16px)` no `<main>` mobile pra não esconder conteúdo atrás da bar
- Por enquanto, **não ligar a navegação ainda** — só estrutura visual + slot funcional

**Perguntas para fazer ao usuário antes de começar:**
- "Devemos manter a bottom bar mesmo em desktop (>=768px)? Minha sugestão é só mobile — no desktop ela some e as ações voltam pro topo da página, como hoje."
- "Você quer o backdrop-filter blur (mais moderno, Safari OK) ou background sólido branco (mais leve)?"

**Critério de aceite:**
- Componente reutilizável que aceita slots
- Visível só em mobile
- Botões da bb medem 46×46 (alvo de toque iOS)

**Commit:** `mobile(bottom-bar): adiciona estrutura base da bottom bar contextual`

---

## Etapa 3 · Bottom sheet de navegação ✅

**Mockup:** `mockup_mobile_aux.html` · Auxiliar 1

**Objetivo:** Implementar o sheet que aparece ao tocar no slot esquerdo da bottom bar — com Hub, Alunos, Histórico, Sair.

**O que fazer:**
- Criar `templates/_mobile_nav_sheet.html`
- Estrutura conforme mockup: overlay escuro + sheet branco com grabber + header (eyebrow "Navegar" / título "BF Treinamento" / botão close) + lista de itens
- Itens (sempre 4):
  1. **Hub** → `url_for('hub')` — ícone home
  2. **Alunos** → `url_for('alunos')` — ícone users (mostrar contagem ativa no sub: "12 ativos · 3 sem rotina")
  3. **Histórico** → `url_for('historico')` — ícone archive
  4. (divider)
  5. **Sair** → `url_for('logout')` — ícone bar-chart (sub: "Encerrar sessão")
- Item da página atual fica com `class="active"` (background `--brand-50`, texto `--brand-700`, ícone com gradient laranja sólido)
- Ao tocar fora ou no botão close, fecha o sheet
- Animação: slide-up com `cubic-bezier(0.32, 0.72, 0, 1)` em 320ms
- Trigger: o botão `[data-open-nav-sheet]` da etapa 2

**Perguntas para fazer ao usuário antes de começar:**
- "Onde vou pegar a contagem dinâmica de alunos ('12 ativos · 3 sem rotina') — tem essa info no contexto Jinja já, ou precisa criar um endpoint/context processor?"
- "Quando o sheet está aberto e o usuário troca de página, o sheet deve fechar com transição ou só desaparecer no carregamento da nova página?"
- "Vamos usar HTMX para abrir o sheet (carrega via AJAX) ou já renderizar inline e só toggar `display`?"

**Critério de aceite:**
- Sheet abre/fecha suavemente
- Item ativo destacado corretamente
- Toque fora fecha o sheet
- Funciona em viewport 380×760

**Commit:** `mobile(nav): adiciona bottom sheet de navegação (Hub/Alunos/Histórico)`

---

## Etapa 4 · Compactação do card do aluno (HUB)

**Mockup:** `mockup_mobile_hub.html` · cenário B

**Objetivo:** Reduzir o card aluno do HUB pra 1 linha só no mobile.

**O que fazer:**
- No template `_rotina_hub.html` (ou onde está o card aluno hoje), criar uma variante mobile:
  - Avatar 38×38 + nome + chip da etiqueta inline + meta condensada + toggle de período
  - Meta condensada: `interm. · 4 treinos · 2d` (em `font-mono`, font-size 11px)
  - Toggle de período: 3 ícones sem label (eye / clock / columns) num grupo segmented compacto à direita
- Esconder no mobile:
  - Botões grandes "+ Treino" e "Nova rotina" (vão pra bottom bar — etapa 5)
  - Subtítulo do card aluno
- O nível de detalhe completo (idade, peso, objetivo escrito, etc.) só aparece se o usuário tocar no card e abrir um sheet/drawer com detalhes — **mas isso fica fora desta etapa.**

**Perguntas para fazer ao usuário antes de começar:**
- "A meta '`interm. · 4 treinos · 2d`' — confirme a ordem e os campos. Hoje vem de quais propriedades do model `Aluno`?"
- "O toggle de período (Atual/Anterior/Diff) hoje funciona com query string ou estado JS? Como devo manter no mobile?"
- "Quando a etiqueta da rotina é longa (ex: 'Hipertrofia Avançada 2024'), prefere truncar com ellipsis ou ela quebra para baixo do nome?"

**Critério de aceite:**
- Card aluno em 1 linha (~58px de altura, antes era ~120px)
- Toggle de período como ícones, sem label
- Em desktop, nada muda

**Commit:** `mobile(hub): compacta card do aluno para 1 linha`

---

## Etapa 5 · Bottom bar contextual no HUB (estado: visualizando)

**Mockup:** `mockup_mobile_hub.html` · cenário B

**Objetivo:** Conectar a bottom bar (etapa 2) ao HUB com as ações certas para o estado "rotina ativa, sem rascunho".

**O que fazer:**
- No template do HUB, dentro do block `bb_actions`, renderizar:
  - **Split button** "+ Treino" (laranja) com chevron à direita
    - Tap principal → abre o gerador no modo "adicionar treino" (mesmo botão que existe hoje)
    - Tap no chevron → menu pop-up com "Adicionar manual" (substitui o split button atual do desktop)
  - **Botão isolado** "Nova rotina" (ícone refresh-cw, fundo branco com borda) → comportamento atual de criar nova rotina
- Quando **não há aluno selecionado**, a `bb-actions` mostra um hint cinza "selecione um aluno para ver as ações" (cenário A do mockup)

**Perguntas para fazer ao usuário antes de começar:**
- "O split button de '+ Treino' hoje tem outras opções no desktop? Mantenho só Manual no mobile ou tem mais?"
- "Posso reusar o partial existente do botão '+ Treino' do desktop, ou crio um separado?"

**Critério de aceite:**
- HUB mobile mostra "+ Treino" como split + "Nova rotina" como ícone na bb
- Ações funcionam (acionam o mesmo comportamento que tinham no desktop)
- Estado vazio (sem aluno) mostra o hint cinza

**Commit:** `mobile(hub): adiciona ações contextuais na bottom bar (visualizando)`

---

## Etapa 6 · Treino card mobile · header em 1 linha + 3 ações

**Mockup:** `mockup_mobile_hub.html` · cenário B + `mockup_mobile_aux.html` · Auxiliar 2

**Objetivo:** Treino card no mobile fica com header em 1 linha só. As 3 ações (Editar · Substituir · Kebab) ficam visíveis. Kebab abre uma action sheet com Regerar · Baixar PNG · Duplicar · Remover.

**O que fazer:**
- Adaptar `_hub_treino_card.html` (e qualquer outro lugar que renderize o treino card):
  - Header em 1 linha: `[T1] [Upper Push] [chips de região] [margin-left: auto] [3 ícones]`
  - Os chips de região com `flex-wrap: nowrap; overflow: hidden` — se passarem, o último é cortado (não quebra linha)
  - 3 ícones: Editar (pencil), Substituir (rotate-ccw), Kebab (more-vertical)
- Criar `_mobile_treino_kebab_sheet.html`:
  - Bottom sheet com 4 itens:
    1. **Regerar treino** — ícone refresh-cw — aciona endpoint atual de regerar
    2. **Baixar PNG** — ícone image — aciona o gerador de PNG existente
    3. **Duplicar para outro treino** — ícone columns — aciona endpoint de duplicar (criar se não existir, ou perguntar antes)
    4. (divider)
    5. **Remover treino** (vermelho) — ícone trash — confirmação inline ou outro sheet
- Quando a sheet está aberta, o botão kebab no card fica com `class="active"` (background preto sólido, texto branco)

**Perguntas para fazer ao usuário antes de começar:**
- "A ação 'Duplicar para outro treino' já existe no desktop? Se não, devo implementar nesta etapa ou deixar fora por enquanto?"
- "Quando o usuário toca em 'Remover treino', mostro confirmação inline (mesmo sheet) ou abro um modal de confirmação separado?"
- "O 'Baixar PNG' já está implementado? Reuso o mesmo endpoint?"

**Critério de aceite:**
- Header do treino em 1 linha (mesmo com 3 chips de região)
- Action sheet do kebab abre, fecha e tem todas as 4 ações
- Estado active do kebab visível enquanto sheet aberta

**Commit:** `mobile(treino-card): header em 1 linha + kebab com action sheet`

---

## Etapa 7 · Banner de rascunho compacto + ações na bottom bar

**Mockup:** `mockup_mobile_hub.html` · cenário C

**Objetivo:** Quando há rascunho ativo, o banner ocupa 1 linha só. Os botões "Salvar" e "Descartar" sobem para a bottom bar.

**O que fazer:**
- Em `_draft_banner.html`, criar variante mobile:
  - 1 faixa só: `[ícone amber pulsante] [Rascunho · 3 alterações] [chevron pra expandir]`
  - O input de etiqueta + botões Salvar/Descartar **somem** do banner no mobile
  - Ao tocar no chevron, banner expande e mostra: input de etiqueta + lista de alterações
- Na bottom bar do HUB (quando há rascunho):
  - Slot 1 (esquerda): menu (sempre)
  - Slot 2: botão **Descartar** (fantasma vermelho, só ícone trash, ~46×46)
  - Slot 3: split button verde **Salvar** (preenche o resto da largura) + chevron à direita
- O chevron do split button "Salvar" abre menu com: "Salvar como cópia" (se aplicável) ou outras opções relacionadas

**Perguntas para fazer ao usuário antes de começar:**
- "Quais opções devem aparecer no chevron do split 'Salvar'? Hoje tem 'Salvar' e 'Salvar como cópia'? Quer manter as duas?"
- "O input de etiqueta da rotina hoje é editável inline ou em modal? No mobile, devo manter inline (dentro do banner expandido) ou abrir bottom sheet de edição?"
- "A lista de alterações ('3 alterações') já é renderizada hoje? Tem endpoint que retorna o detalhe?"

**Critério de aceite:**
- Banner de rascunho ocupa só 1 linha no mobile
- Toque no chevron expande/fecha o detalhe
- Bottom bar mostra Descartar + Salvar quando há rascunho
- Confirmação de descartar não pode ser por engano (alvo de toque + confirmação modal/sheet)

**Commit:** `mobile(rascunho): banner compacto + ações na bottom bar`

---

## Etapa 8 · Modo edição inline · banner substitui card aluno

**Mockup:** `mockup_mobile_hub.html` · cenário D

**Objetivo:** Quando o personal entra em modo edição de um treino, um banner laranja substitui o card aluno (foco). O card editado tem borda laranja sutil. Bottom bar fica só com "Concluir edição".

**O que fazer:**
- Criar `_mobile_edit_banner.html`:
  - Banner laranja com ícone pencil + título "Editando T1 · Upper Push" + sub "Salvo automaticamente como rascunho"
  - Renderizado no topo do `<main>`, **antes** do card de aluno (que fica oculto no mobile durante edição)
- O treino card editado recebe `class="editing"`:
  - Borda `--brand-200`
  - Box-shadow externo `0 0 0 4px rgba(232,93,4,0.06)` para destacar foco
  - **Esconde** os 3 ícones do header do card editado (eles eram para sair do modo edição? — confirme com o usuário)
- Cada exercício no modo edição mostra:
  - Drag handle (grip-vertical) à esquerda — para reordenar
  - Conteúdo do exercício
  - Kebab à direita (more-vertical) — para opções (regerar este, substituir, remover)
- Botão "Adicionar exercício" como linha tracejada abaixo dos exercícios do bloco
- Botão "Novo bloco" (card grande tracejado) abaixo dos blocos existentes
- Bottom bar: só **Concluir edição** (laranja, full-width)

**Perguntas para fazer ao usuário antes de começar:**
- "Como o modo edição é ativado hoje? Toque no ícone pencil do header do card?"
- "No desktop, o que aparece no header do card durante edição? Há um botão 'Sair sem salvar'? Como migro pra mobile?"
- "A reordenação por drag-and-drop está implementada hoje no desktop? Se sim, devo usar a mesma lib (Sortable.js?)? Se não, deixo fora desta etapa e marco como TODO?"
- "O kebab por exercício abre que opções? Listei 'Regerar este · Substituir · Remover' — confirma?"

**Critério de aceite:**
- Modo edição substitui o card aluno por banner
- Card editado tem borda laranja
- Drag & drop funciona (ou marcado como TODO se não tiver no desktop)
- Bottom bar limpa, só "Concluir edição"

**Commit:** `mobile(hub): modo edição inline com banner + bottom bar focada`

---

## Etapa 9 · Gerador mobile · estrutura tela única (Aluno + Configs)

**Mockup:** `mockup_mobile_gerador.html` · variante A2 estado 1

**Objetivo:** Adaptar a página `/gerador` para o layout mobile. Aluno e Configurações gerais como seções colapsáveis no topo. Os treinos T1-T5 ficam pra etapa 10.

**O que fazer:**
- No template do gerador, criar layout mobile:
  - Topbar com botão back (seta) + eyebrow "Gerador · Nova rotina" + título com nome do aluno
  - Seções colapsáveis (componente reutilizável `_mobile_section.html`):
    - Estrutura: `[ícone] [título + sub] [counter (opcional)] [chevron]`
    - Estado fechado: só o head (toque expande)
    - Estado aberto: head + body
    - `class="has-content"` quando preenchido (ícone fica laranja)
  - Seção 1: **Aluno**
    - Aberta por padrão (ou fechada se já tem dados? — pergunte)
    - Campos: select de aluno (sempre), select "Evitar exercícios dos últimos N períodos"
  - Seção 2: **Configurações gerais**
    - Fechada por padrão
    - Campos: Nº treinos (select), Exerc. por bloco (select), Complexidade máx. (range), Toggles (Evitar similaridade, Evitar agonistas)
  - Sub mostra resumo quando fechada: "3 treinos · superset · cx 5"
- Bottom bar com **Gerar treinos** (full-width laranja) — desabilita se faltar info essencial

**Perguntas para fazer ao usuário antes de começar:**
- "Quando o usuário entra no gerador a partir do botão 'Nova rotina', as Configurações gerais devem vir abertas ou fechadas? E quando vem do botão '+ Treino' (adicionar treino isolado)?"
- "O select 'Evitar exercícios dos últimos N períodos' é parte da seção Aluno ou Configurações? Hoje fica onde?"
- "O botão 'Gerar' deve estar desabilitado até quando? Quando há aluno + pelo menos 1 demanda em 1 treino? Ou ele pode ser apertado e dar erro?"

**Critério de aceite:**
- Componente `_mobile_section.html` reutilizável (vai ser usado nos treinos também)
- Aluno e Configs renderizando + colapsáveis
- Bottom bar com Gerar (mesmo desabilitado por enquanto)

**Commit:** `mobile(gerador): adiciona estrutura tela única com seções colapsáveis`

---

## Etapa 10 · Gerador mobile · seções de treinos T1-T5 + drawer lateral

**Mockup:** `mockup_mobile_gerador.html` · variante A2 estados 1 e 2

**Objetivo:** Adicionar as seções T1-T5 ao gerador mobile, cada uma com lista de demandas + botão grande "Adicionar demandas" que abre um drawer lateral.

> **DECISÃO:** vamos com a **Variante A2 (drawer lateral)**, conforme mockup. **Não implementar A1** (tags inline na tela única).

**O que fazer:**
- Adicionar seções de treino na página do gerador:
  - 1 seção por treino (T1, T2, ..., conforme `Nº treinos` selecionado em Configurações)
  - Cada seção é colapsável (mesmo componente da etapa 9)
  - Sub: "Hierarquia · 5 padrões" ou "Sem configuração"
  - Counter: número total de exercícios no treino
- Body de cada seção (variante A2):
  - **Lista de demandas configuradas** (componente `_mobile_demandas_list.html`):
    - Cada item: `[chip de região] [nome do padrão] [counter -/+] [botão remover]`
    - Counter -/+ ajusta a quantidade de exercícios desse padrão
    - Total no header: "Demandas configuradas · 5 ex"
  - **Botão grande "Adicionar demandas"** (CTA):
    - Card com borda tracejada
    - Ícone laranja + título "Adicionar demandas" + sub "Hierarquia ou template"
    - Toque abre o **drawer lateral**
- Criar `templates/_mobile_demands_drawer.html`:
  - Slide-in da direita (largura 92% da tela)
  - Header: ícone + eyebrow "Treino N · demandas" + título "Hierarquia" + close
  - Faixa de contador laranja: "Total selecionado · 5 ex"
  - Body scrollável:
    - Mode switch (Hierarquia / Template) — segmented control
    - Cards de região (Upper, Lower, Core, Cardio) — colapsáveis
    - Card aberto mostra subregiões com tags de padrão clicáveis (multi-select)
  - Footer fixo: **Cancelar** (cinza) + **Aplicar (5)** (laranja)
- Drawer **reusa** o componente do drawer de substituição existente — verifique antes de criar do zero

**Perguntas para fazer ao usuário antes de começar:**
- "O drawer de substituição existente está em qual template? Quero reusar a estrutura/animação. Confirme o caminho."
- "Quando o usuário clica em 'Aplicar' no drawer, ele aplica e fecha, ou aplica e fica aberto? Hoje no desktop como funciona o equivalente?"
- "Modo Template — como ele difere de Hierarquia visualmente? Tem template já cadastrado ou ele só lista templates salvos?"
- "Os endpoints atuais que recebem as demandas mudam? Ou eu mando exatamente o mesmo payload que o desktop manda?"

**Critério de aceite:**
- Cada treino renderiza como seção colapsável
- Lista de demandas funciona (add via drawer, remove, ajustar quantidade)
- Drawer abre, escolhe padrões, aplica, fecha
- Total de exercícios atualizado em tempo real

**Commit:** `mobile(gerador): adiciona drawer lateral para escolha de demandas`

---

## Etapa 11 · Lista de alunos mobile

**Mockup:** `mockup_mobile_aux.html` · Auxiliar 3

**Objetivo:** Adaptar a página `/alunos` para mobile com busca, filtros chip-based e cards de alunos.

**O que fazer:**
- No template `alunos.html`, criar layout mobile:
  - Topbar: logo + search bar (input com ícone search dentro de pill cinza)
  - Barra de filtros chip horizontal (scroll horizontal sem scrollbar):
    - "Todos (12)", "Ativos (9)", "Sem rotina (3)", "Hipertrofia (7)", "Iniciante (4)" etc
    - Chip ativo fica preto (`--canvas-ink`)
  - Seções com título: "Atual (1)", "Outros ativos (8)", "Sem rotina (3)"
  - Cards de aluno (`_mobile_aluno_card.html`):
    - Avatar 38×38 (cor por inicial: marrom, azul, verde, âmbar, cinza)
    - Nome + status dot (verde / âmbar / cinza)
    - Meta condensada: "interm. · 4 treinos · há 2d"
    - Tags: "Hipertrofia", "Abr · 24" etc
    - Chevron à direita (toda a área do card é clicável)
  - Aluno atual (selecionado no contexto) fica destacado em laranja no topo
- Bottom bar: menu + **+ Aluno** (laranja, full-width)

**Perguntas para fazer ao usuário antes de começar:**
- "Quais filtros chip devo mostrar? Listei 'Todos / Ativos / Sem rotina / Hipertrofia / Iniciante'. Esses são os reais ou tem outros?"
- "O agrupamento (Atual / Outros ativos / Sem rotina) é fixo ou dinâmico? Se um aluno não tem rotina, ele cai automaticamente em 'Sem rotina'?"
- "A busca é client-side ou server-side (HTMX)? Tem endpoint de search hoje?"
- "Quando toca num aluno na lista, ele fica selecionado e volta pro Hub, ou abre uma página de detalhes do aluno?"

**Critério de aceite:**
- Lista renderiza com cards
- Busca funciona (filtra por nome)
- Filtros chip funcionam (filtra por status/objetivo)
- + Aluno na bottom bar abre o fluxo de criação existente

**Commit:** `mobile(alunos): adapta lista para mobile com filtros e busca`

---

## Etapa 12 · Histórico mobile · timeline por período

**Mockup:** `mockup_mobile_aux.html` · Auxiliar 4

**Objetivo:** Adaptar a página `/historico` para mobile com timeline cronológica.

**O que fazer:**
- No template `historico.html`, criar layout mobile:
  - Topbar: logo + pill do aluno (mesmo da Hub)
  - Filtros chip: "Todos", "2024", "2023", "Filtros" (último com ícone funnel)
  - Headers de período (não cards):
    - `[ano em badge preto/laranja] [mês em display font] [tag "Atual" se aplicável] [data em mono]`
    - Período atual com badge laranja + tag "Atual"
  - Cards de período (`_mobile_hist_card.html`):
    - Header: ícone (P1, P2... em mono) + nome + meta (data range, contagem de ajustes)
    - Stats em chips compactos: "4 treinos", "22 ex", "cx 5"
    - Mini pills dos treinos: "T1 Upper Push", "T2 Upper Pull"... (preview rápido)
  - Card do período atual: borda laranja, fundo creme sutil
- Bottom bar: menu + **Filtrar** (ícone funnel) + **Comparar** (ícone columns) + hint "toque num período"

**Perguntas para fazer ao usuário antes de começar:**
- "Os períodos hoje vêm da API agrupados por mês? Ou preciso agrupar no template?"
- "O 'Comparar' na bottom bar tem comportamento já implementado no desktop? Se sim, como funciona — abre seleção dos 2 períodos? Mantenho?"
- "As mini pills mostram só o nome do treino (T1 Upper Push) ou também as regiões? Confirme densidade desejada."
- "Tocar num período (card) abre detalhe inline ou nova página `/historico/<id>`?"

**Critério de aceite:**
- Timeline agrupada por mês
- Período atual destacado em laranja
- Cards mostram stats + mini pills
- Bottom bar contextual com Filtrar + Comparar

**Commit:** `mobile(historico): adapta para timeline com cards por período`

---

## Etapa 13 (opcional) · Gerador modo "Substituir treino"

**Mockup:** `mockup_mobile_gerador.html` (não tem cenário específico no mockup atual — usar referência da variante A2 + observação)

**Objetivo:** Quando o gerador é aberto a partir do botão "Substituir" de um treino (não "Nova rotina"), ajustar:
- Topbar: eyebrow vira "Gerador · Substituir", título vira "Treino N"
- Banner laranja no topo: "Substituindo Treino N · outros preservados"
- Seção Aluno fica "fixa" (não pode trocar) — mostra um chip com `lock` icon
- Configurações: campo "Nº de treinos" travado em 1 (com badge "1 lock")
- Só renderiza 1 seção de treino (T1) — não 5

**Perguntas para fazer ao usuário antes de começar:**
- "Esse fluxo já existe hoje no desktop ('Substituir treino' → /gerador com contexto)? Como o backend identifica o modo?"
- "Posso reusar o mesmo template de `/gerador` com flag `mode='replace'` ou prefere template separado?"

**Critério de aceite:**
- Modo replace identificado por query param ou estado
- Banner + chip lock + campo travado funcionam
- Só 1 treino renderizado

**Commit:** `mobile(gerador): suporte ao modo substituir treino`

> Esta etapa pode ser feita antes ou depois da etapa 12 — não tem dependência rígida. Sugiro fazer **depois** das 1-12 para não dispersar o foco.

---

## Limpeza final · checklist de QA

Após as 12 etapas (+ opcional 13), passe por este checklist em viewport 380×760 com toque ativado:

- [ ] Bottom bar visível em todas as páginas mobile (Hub, Alunos, Histórico, Gerador)
- [ ] Botão menu (esquerdo) sempre presente, abre o sheet de navegação
- [ ] Toque fora dos sheets/drawers fecha eles
- [ ] Backdrop blur ou fade funcionando em iOS Safari (testar no Simulator se possível)
- [ ] Scroll do `<main>` não fica atrás da bottom bar (padding-bottom calculado certo)
- [ ] Safe-area-inset-bottom respeitado em iPhones com notch
- [ ] Nenhum elemento desktop visível em mobile (hambúrguer, sidebar, títulos decorativos)
- [ ] Nenhum elemento mobile visível em desktop (bottom bar fixa, etc.)
- [ ] Pill do aluno trunca corretamente em nomes longos
- [ ] Treino card com 4+ chips de região não quebra linha (overflow hidden)
- [ ] Modo edição mostra banner laranja e oculta card aluno
- [ ] Drawer do gerador abre/fecha suavemente
- [ ] Sheets têm grabber de 36×4px no topo
- [ ] Cores e tipografia consistentes com o redesign 01

**Commit final:** `mobile: QA pass + ajustes finais do redesign mobile`

---

## Como abrir os mockups durante o desenvolvimento

Os mockups são auto-contidos — basta abrir os HTMLs no navegador:

```bash
# Abrir todos os mockups numa página
open docs/redesign/mobile/mockup_mobile_hub.html
open docs/redesign/mobile/mockup_mobile_gerador.html
open docs/redesign/mobile/mockup_mobile_aux.html
```

A barra superior tem links cruzados para alternar entre os 3 mockups. Cada mockup contém ~4 frames de iPhone lado a lado mostrando os diferentes estados.

---

## Coisas que **não** estão neste redesign

Para não inflar o escopo, estas coisas **ficam fora** desta rodada (mas podem entrar numa próxima):

- Onboarding/tutorial de primeiro uso
- Modo escuro (dark mode)
- Notificações push / badges no menu
- PWA / Offline mode
- Compartilhamento direto pro WhatsApp do aluno (link/botão dedicado)
- Animações de transição entre páginas (page transitions)
- Estados de skeleton loading detalhados
- Acessibilidade (VoiceOver/TalkBack/aria-live) — fica como TODO

Se identificar necessidade durante a implementação, **anote como TODO no código** (`<!-- TODO mobile-v2: ... -->`) em vez de implementar agora.

---

## Resumo executivo (TL;DR)

12 etapas + 1 opcional. Cada etapa é pequena, isolada, com perguntas de pré-implementação e commit no fim. Decisões já validadas:

- **Bottom bar fixa** com slot esquerdo (menu) + slots dinâmicos
- **Bottom sheet** para navegação (Hub/Alunos/Histórico) e action sheets
- **Drawer lateral** (variante A2) para escolha de demandas no gerador
- **Mockups são a verdade** — em qualquer dúvida, ele vence o texto deste guia

Quando terminar tudo: commit final de QA, push pra branch, abre PR pra revisão. 🎯
