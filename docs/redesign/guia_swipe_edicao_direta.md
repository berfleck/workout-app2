# Guia — Swipe entre treinos + edição estrutural direta na visualização

> Iniciativa de UX mobile que sucede o redesign 02. Não é uma "Etapa N" do
> guia de refatoração do motor — é um conjunto coerente de mudanças no
> frontend que compartilham princípio arquitetural, vocabulário de gestos e
> infraestrutura de estado client-side.

---

## 1. Contexto e motivação

O redesign 02 entregou layout drawer + bottom sheets + kebab action sheet,
mas manteve o **modo edição** (`edicao_hub`) como contexto separado da
visualização. Na prática, conforme o app foi sendo usado, ficou claro que:

1. O personal evita entrar em modo edição porque ele é "pesado" — muda
   visualmente toda a tela, e desambigua entre "estou olhando" e "estou
   modificando" de forma que não corresponde ao fluxo real, que é
   misturado.
2. A maior parte das operações que hoje exigem modo edição são
   **estruturais e atômicas** (remover, mover, substituir, transformar) —
   não dependem de formulário com múltiplos campos. O peso visual do modo
   edição é desproporcional ao tamanho real da mudança.
3. A visualização de rotina com múltiplos treinos no mobile é vertical e
   longa — rolar entre T1 e T4 pra comparar ou trocar exercícios entre
   treinos é trabalhoso.

Este guia consolida três frentes de melhoria que respondem a esses pontos:

- **Frente A:** Swipe horizontal entre treinos (mockup já validado).
- **Frente B:** Swap inter-treino de exercícios (extensão natural do
  long-press swap intra-treino que já existe).
- **Frente C:** Edição estrutural completa (exercício e bloco) feita
  direto na tela de visualização, sem entrar em modo edição. Modo edição
  é refatorado em **modo prescrição** (drawer dedicado pra
  séries/reps/RIR), única função sobrevivente.

As frentes compartilham um padrão visual unificado (modo carregando +
highlight pós-mudança), uma decisão arquitetural transversal (adoção de
Alpine.js) e uma simplificação backend (helper de resposta lightweight
que grava rascunho sem ativar `edicao_hub`).

---

## 2. Decisão arquitetural: adotar Alpine.js

A partir desta iniciativa, o stack passa a ser **Flask + HTMX + Alpine.js
+ Tailwind**. Alpine entra como camada de estado reativo client-side,
complementar a HTMX (que continua dono de toda comunicação com o
servidor).

### 2.1 Por que agora

A funcionalidade central que destrava todo o resto é o **modo
carregando**: quando o usuário "pega" um exercício ou bloco e mantém esse
estado enquanto navega pra escolher o destino. Esse estado precisa estar
visível e reativo simultaneamente em três pontos da tela (pill flutuante,
elemento de origem, alvos válidos) e sobreviver a:

- Rolagem horizontal entre treinos
- Swaps de partials via HTMX (quando o servidor retorna HTML novo)
- Re-renders de cards após gravar rascunho

Implementar isso em JS puro exige um mini-mecanismo de estado reativo na
mão (objeto global + pub/sub + re-bind manual depois de cada
`htmx:afterSwap`), e é exatamente a fonte dos bugs históricos que o
`CLAUDE.md` já cataloga ("script no meio do body", "fetch puro não
dispara afterSwap"). Alpine resolve isso declarativamente, com a peça que
fecha o caso sendo a extensão **`htmx-ext-alpine-morph`**, que preserva
estado Alpine através de swaps HTMX.

### 2.2 Divisão de responsabilidades

**Alpine assume:**
- Store global do modo carregando (`Alpine.store('carry', ...)`)
- Store global de highlight pós-mudança (`Alpine.store('highlight', ...)`)
- Pill flutuante de "Trocando: X" — existir, animar, mostrar nome certo
- Visual reativo nos exercícios (origem esmaecida, alvos destacáveis)
- Visual reativo nos gaps entre blocos (modo "+" vs modo "drop zone")
- Action sheets que abrem no tap curto (no exercício e no mini-kebab do bloco)
- Modal picker que abre quando o usuário toca "+" pra criar bloco ou
  "Adicionar exercício" no mini-kebab
- Drawer do modo prescrição (abrir, fechar, animar)
- Toast de undo (após remover bloco)
- Estado expand/collapse de banners e drawers locais

**HTMX continua dono de:**
- Toda comunicação com o servidor (substituir, mover, remover,
  reordenar, criar bloco, prescrição autosave)
- Render de cards de treino e fragmentos OOB do banner
- Toggle Atual/Anterior (navegação via rotas reais)

**JS puro continua em:**
- Detecção de long-press (timer de 500ms — Alpine não detecta gesto)
- Scroll-snap horizontal entre treinos (CSS nativo `scroll-snap-type: x
  mandatory` + IntersectionObserver pra sincronizar chip ativo)
- SortableJS pra reorder de exercícios **dentro** de um bloco (decisão
  §10.5)

### 2.3 Setup técnico

Primeira tarefa de implementação:

1. Adicionar Alpine + extensão morph ao `base.html` via CDN (ordem
   importa: morph antes do Alpine core).
2. Adicionar `hx-ext="morph"` no body ou nos containers relevantes.
3. Mudar `hx-swap` de `outerHTML` pra `morph` nas rotas onde queremos
   preservar estado Alpine através do swap.
4. Criar `Alpine.store('carry', ...)` e `Alpine.store('highlight', ...)`
   no `Alpine.init` global.

Tamanho do bundle: Alpine core ~15kb min+gzip, morph ~3kb. Sintaxe nova
é pequena (`x-data`, `x-show`, `x-init`, `:class`, `@click`, `$store`).

---

## 3. Princípios unificadores

### 3.1 Visualização = edição

Regra que rege todas as operações estruturais:

> **Se a operação muda só uma coisa por vez e não exige formulário com
> múltiplos campos simultâneos, ela acontece direto na visualização e
> grava rascunho sem ativar modo edição.**
>
> **Se a operação exige revisar um conjunto coerente antes de salvar (ex:
> ajustar séries/reps/RIR de vários exercícios), aí sim entra em modo
> prescrição (drawer dedicado).**

Pelo princípio: substituir, mover, remover, tornar solo, reordenar
bloco, criar bloco, adicionar exercício a bloco — todas **fora** de modo
edição. Só ajuste de prescrição em lote tem modo dedicado, e mesmo assim
como drawer sobreposto, não como navegação pra outra tela.

### 3.2 Helper de resposta lightweight

Hoje quase toda rota de bloco/exercício passa por
`_responder_card_com_banner(t)`, que tem efeito colateral de **ativar
`edicao_hub`** global. Pra todas as operações estruturais deste guia,
precisamos de um helper irmão sem esse efeito colateral:

```python
def _responder_card_viz_com_banner(t, aluno_id):
    """Renderiza _hub_treino_card.html em modo visualizar
    + OOB do banner de rascunho.
    NÃO ativa edicao_hub. Usado por operações estruturais
    lightweight que gravam rascunho sem entrar em modo edição."""
    card_html = render_template("_hub_treino_card.html",
                                sessao=sessoes_ativas[t], idx=t,
                                modo="visualizar", ...)
    banner_oob = render_draft_banner_oob(aluno_id)
    return card_html + banner_oob
```

O helper existente continua sendo usado pelo modo prescrição (drawer).
Coexistência dos dois é por design — a divisão fica clara: viz pra
operações estruturais; clássico pra prescrição.

### 3.3 Compactness vertical em estado de repouso

Regra explícita pra implementação:

> **O estado de repouso da visualização não pode adicionar pixel
> vertical novo. Affordances novas só aparecem em interação
> (hover/long-press/modo carregando) ou em espaço horizontal já
> ocupado.**

Justificativa: o card atual de treino foi otimizado pra ser compacto e
permitir visualização da rotina inteira sem rolagem excessiva. As novas
funcionalidades precisam preservar essa propriedade.

Em prática, isso significa:

- Mini-kebab do bloco (§7.4) vai no espaço horizontal já existente ao
  lado do rótulo "BLOCO A". Custo vertical: zero.
- Gap clicável entre blocos (§7.3) usa o `border-top` já existente como
  hit-target; o "+" só aparece em interação. Custo vertical: zero.
- Pill flutuante de modo carregando (§4) é overlay. Custo vertical: zero.
- Highlight pós-mudança (§4.3) é mudança de cor/borda no próprio
  elemento. Custo vertical: zero.
- Drawer de prescrição (§7.5) é overlay invocado sob demanda. Custo
  vertical: zero.

**Saldo provável da migração:** o card fica **igual ou ligeiramente mais
compacto** que hoje, porque sai mais do que entra. Saem: setas de mover
bloco (cima/baixo), botão "Editar" no kebab do card (modo edição
genérico), ícones inline de remover exercício se existirem. Entra: um
mini-kebab por bloco (~16-20px horizontal, zero vertical).

---

## 4. Padrões visuais compartilhados

Dois mecanismos visuais usados por várias frentes deste guia.

### 4.1 Modo carregando — como funciona

1. **Long-press** num exercício ou no rótulo de um bloco (~500ms) ativa
   o modo carregando. O elemento de origem fica visualmente atenuado
   (opacidade reduzida, borda tracejada).
2. **Pill flutuante** aparece no topo da tela, abaixo da topbar e acima
   do chip pager. Mostra: ícone + "Trocando: [nome do exercício]" ou
   "Movendo: [Bloco B]" + botão X de cancelar.
3. **Alvos válidos** ganham destaque visual:
   - Pra carregamento de exercício: outros exercícios viram
     destacáveis (borda colorida no hover/active).
   - Pra carregamento de bloco: os gaps entre blocos viram drop zones
     visíveis (linha + chip "Soltar aqui").
4. **Navegação livre** entre treinos via swipe ou chip — o modo
   carregando persiste através da navegação.
5. **Tap num alvo válido** completa a operação.
6. **Cancelar** via: X no pill, tap no próprio elemento de origem, ou
   tecla ESC (desktop).

### 4.2 State shape do carry

```javascript
Alpine.store('carry', {
  tipo: null,           // 'exercicio' | 'bloco' | null
  refExercicio: null,   // { treinoIdx, blocoIdx, ei, nome }
  refBloco: null,       // { treinoIdx, blocoIdx, label }
  origemLabel: null,    // string pra mostrar no pill

  pegar(tipo, ref, label) {
    this.tipo = tipo;
    this.refExercicio = tipo === 'exercicio' ? ref : null;
    this.refBloco = tipo === 'bloco' ? ref : null;
    this.origemLabel = label;
  },

  soltar() {
    this.tipo = null;
    this.refExercicio = null;
    this.refBloco = null;
    this.origemLabel = null;
  },

  estaCarregandoExercicio(treinoIdx, blocoIdx, ei) {
    return this.tipo === 'exercicio' &&
           this.refExercicio?.treinoIdx === treinoIdx &&
           this.refExercicio?.blocoIdx === blocoIdx &&
           this.refExercicio?.ei === ei;
  },
});
```

Cada exercício no template usa `:class="$store.carry.estaCarregandoExercicio(...)
&& 'is-source'"`. Cada gap entre blocos usa `x-show="$store.carry.tipo === 'bloco'"`
pra virar drop zone só quando faz sentido.

### 4.3 Highlight pós-mudança

Padrão visual disparado após qualquer operação estrutural concluir
(reorder de bloco, swap, tornar solo, criar bloco, adicionar exercício,
substituir): o elemento recém-modificado recebe um **glow/borda laranja
pulsante de ~600ms** que desaparece sozinho. Sem texto, sem toast, sem
ocupar espaço — só confirma visualmente *qual* elemento mudou.

Implementação:

```javascript
Alpine.store('highlight', {
  ref: null,            // identificador do elemento
  hl(ref) {
    this.ref = ref;
    setTimeout(() => { if (this.ref === ref) this.ref = null; }, 600);
  },
});
```

Cada elemento usa
`:class="$store.highlight.ref === '{{ id }}' && 'just-changed'"`.

A classe CSS `.just-changed` faz uma animação curta:

```css
@keyframes just-changed-pulse {
  0%   { box-shadow: 0 0 0 0 rgba(232, 93, 4, 0.5); }
  100% { box-shadow: 0 0 0 8px rgba(232, 93, 4, 0); }
}
.just-changed {
  animation: just-changed-pulse 600ms ease-out;
}
```

Usos no app:
- Bloco recém-reposicionado em reorder.
- Bloco recém-criado por "+".
- Exercício recém-substituído.
- Bloco que recebeu exercício novo via "Adicionar exercício".
- Exercício recém-extraído pra solo (no bloco novo).
- Exercícios envolvidos num swap inter-treino (ambos).

---

## 5. Frente A — Swipe horizontal entre treinos

### 5.1 Layout

Implementação baseada no mockup `mockup_swipe_treinos.html` já validado.
Decisões já tomadas:

- **Chip pager** no topo (T1 Inferior A · T2 Superior A · …) sempre
  visível e clicável. Resolve a queixa NN/g de "lack of signifiers" pro
  gesto de swipe. Quem aprende swipe ganha velocidade; quem não aprende
  navega pelo chip.
- **Scroll-snap CSS nativo** (`scroll-snap-type: x mandatory`) — não é
  handler de touch custom. Isso elimina qualquer conflito com SortableJS
  (que opera no eixo vertical dentro da lista de exercícios) ou com
  long-press (que é tempo, não direção).
- **Full-bleed** — cada `.treino-page` ocupa 100% da largura, sem chrome
  de card. Conteúdo nunca obscurecido (atende recomendação NN/g).
- **Counter "1/4"** na topbar dá feedback de posição durante swipe.
- **Nudge inicial de 36px** + pill "deslize" ensinam o gesto sem texto
  pesado.
- **IntersectionObserver** sincroniza chip ativo + counter com a página
  mais visível.

### 5.2 Onde mora o banner de rascunho

Decisão: **acima do chip pager**, abaixo da topbar. Banner é estado da
**rotina**, não do treino — repetir em cada `.treino-page` seria
desperdício, e compactar dentro da topbar perde legibilidade.

### 5.3 Toggle Atual / Anterior

**Decisão (§10.6):** dentro do **kebab da topbar**. Uso é pontual (só
quando o personal vai criar ou editar treino), então não justifica
ocupar pixel permanente.

Quando o modo Anterior estiver ativo:
- **Badge "anterior"** discreto próximo ao counter "1/4" na topbar,
  diferenciando visualmente do modo Atual.
- **Fundo do conteúdo levemente mais frio** (cinza um pouco mais
  saturado, não tanto que machuque a leitura) — comunica "isto não é
  editável" sem texto.
- Voltar pra Atual: outro toque no kebab da topbar.

"Lado a lado" desaparece no mobile (não cabe em 2 colunas).

### 5.4 Coexistência com bottom bar

O `.swipe-track` usa `flex: 1` e fica entre o chip pager (em cima) e a
bottom bar fixa (embaixo). O scroll vertical dentro de cada `.treino-page`
acontece dentro da altura disponível.

---

## 6. Frente B — Swap inter-treino de exercícios

Extensão natural do long-press swap intra-treino que já existe. O modelo
mental "long-press pega, toque solta" se mantém; a única mudança é que o
segundo toque agora pode estar em outro treino.

### 6.1 Fluxo

1. Long-press num exercício em T1 → `$store.carry.pegar('exercicio',
   {treinoIdx: 0, blocoIdx, ei, nome}, nome)`.
2. Pill aparece. Exercício de origem fica esmaecido.
3. Usuário desliza pra T2 (ou toca o chip). O scroll-snap leva ele lá.
4. Outros exercícios em T2 estão destacáveis. Tap num deles → request
   pro backend: swap atômico entre (T1, blocoA, eiA) e (T2, blocoB, eiB).
5. Backend grava rascunho (sem ativar edicao_hub), retorna OOB dos dois
   cards afetados.
6. `$store.carry.soltar()`. Pill some.
7. Após o swap completar, **ambos os exercícios trocados recebem
   highlight pulsante de 600ms** (§4.3).

### 6.2 Rota backend

Substituir a rota intra-treino atual por uma assinatura unificada:

```
POST /hub/rotina/<int:aluno>/swap/<int:t_a>/<int:bi_a>/<int:ei_a>/<int:t_b>/<int:bi_b>/<int:ei_b>
```

Quando `t_a == t_b`, comportamento é igual ao swap intra-treino atual
(retorna 1 card via OOB). Quando `t_a != t_b`, swap atômico entre treinos
e retorna 2 cards via OOB.

Lógica interna: idêntica ao `_swap_ex_in_sessao` existente, mas operando
em dois `Sessao` ao invés de um.

### 6.3 Validação clínica pós-swap

**Decisão (§10.4):** sem validação automática. Confia no operador, igual
o swap intra-treino faz hoje. O sistema de avisos (`Sessao.avisos`)
continua rodando só no momento da geração, não em edição manual.

Caminho futuro reativo (não no escopo agora): se com uso real surgir
caso recorrente de "fiz swap e quebrei estrutura sem perceber",
considerar re-avaliação passiva de avisos em background, exibida no
banner de rascunho na próxima abertura da rotina.

---

## 7. Frente C — Edição estrutural direta

Operações que hoje exigem modo edição (ou são limitadas/lentas) e
passam a viver na visualização. Inclui ações no nível **exercício**
(§7.1, §7.2 reuso) e no nível **bloco** (§7.3, §7.4), mais o sucessor do
modo edição: **modo prescrição** como drawer (§7.5).

### 7.1 Tornar exercício solo

**Caso clínico:** o gerador pareou um composto pesado (terra,
agachamento, supino reto) com um parceiro razoável, mas o personal quer
descanso pleno entre séries pra puxar carga real. Solo, sem super-série.
Ou um exercício demorado/tecnicamente complexo que merece destaque.

**UX:**

1. **Tap curto** num exercício abre o action sheet:
   - Substituir
   - Tornar solo
   - Mover para outro bloco (→ submenu com lista de blocos disponíveis)
   - Mover para outro treino (→ submenu com T1/T2/…)
   - Remover

   Long-press continua reservado pra entrar em modo carregando (swap).
   Tap curto = menu; long-press = ação direta por gesto.

2. "Tornar solo" → cria um bloco novo **imediatamente ACIMA** do bloco
   de origem, move o exercício pra lá, re-rotula A/B/C/D/…

**Regra de posicionamento (§10.2):** solo sempre vai **acima** do bloco
de origem. Justificativa: o personal só extrai pra solo aquilo que
merece destaque (composto pesado, exercício complexo, demorado), e isso
clinicamente quer estar cedo no treino, com o sistema neuromuscular
fresco. A regra captura essa intenção literal sem precisar comparar
scores ou pensar — o operador escolhe o exercício certo, a posição
deriva.

**Rota backend:**

```
POST /hub/rotina/<int:aluno>/treino/<int:t>/exercicio/<int:bi>/<int:ei>/tornar-solo
```

Implementação: cria novo `SuperSerie` na posição `bi` (acima do bloco
atual), move o exercício pra lá, re-rotula. Grava rascunho via
`_responder_card_viz_com_banner`. Sem ativar edicao_hub.

Sem confirmação prévia (decisão §10.2). Highlight pulsante de 600ms no
exercício extraído após a operação completar.

### 7.2 Reordenar blocos

**Por que não drag-and-drop:** a lista de blocos não cabe em uma tela só
no mobile (topbar + chip pager + banner consomem ~280px no topo; bottom
bar ~80px na base; sobra ~420px úteis, que comporta 3-4 blocos no
quadro). Auto-scroll durante drag tem problemas ergonômicos conhecidos
(zona de gatilho apertada, velocidade difícil de controlar, dedo
cobre item). Por isso a Apple usa tap-based reorder em apps próprios
com listas longas (Reminders, Notes, Mail).

**Regra mental decorrente:** *drag funciona pra alvos próximos (todos
visíveis sem rolar); long-press + tap funciona pra alvos distantes
(podem exigir rolagem ou navegação)*. Essa divisão guia toda a
arquitetura de gestos do app — não é purismo de consistência, é resposta
a ergonomia real.

**UX:**

1. Long-press no rótulo de um bloco → `$store.carry.pegar('bloco', ...)`.
2. Pill mostra "Movendo: Bloco B — toque entre dois blocos pra
   reposicionar".
3. Os gaps entre blocos viram drop zones visíveis (linha + chip
   "Soltar aqui").
4. Usuário rola verticalmente livremente até encontrar a posição alvo.
5. Tap num gap → bloco move pra aquela posição, re-rotulado.
6. Bloco recém-movido recebe highlight pulsante de 600ms (§4.3).

**Semântica importante:** bloco **reordena** (posicional), exercício
**troca** (swap simétrico). Por isso o alvo de tap quando se está
carregando um bloco é o **gap entre blocos**, não outro bloco.

**Rota backend:**

```
POST /hub/rotina/<int:aluno>/treino/<int:t>/blocos/reordenar
body: ordem=[2,0,1,3]   # nova ordem de índices originais
```

Substitui o uso manual de `bloco_mover` no fluxo de usuário. A rota
`bloco_mover` existente pode continuar pra acessibilidade (quem não
consegue long-press, ainda usa setas — escondidas atrás de toggle de
acessibilidade ou disponíveis só no modo prescrição).

### 7.3 Inserir bloco entre blocos

**Inspiração:** padrão "+" inline do Notion / Linear.

**UX:**

1. Os gaps entre blocos têm dupla função:
   - **Modo normal:** linha discreta com "+" no centro, clicável.
   - **Modo carregando bloco** (§7.2): drop zone "Soltar aqui".
2. Tap no "+" → cria bloco vazio naquela posição **e** abre direto o
   picker de exercícios (modal Alpine + HTMX que carrega
   `_substituicao.html` adaptado).
3. **Picker permite escolher 1 ou 2 exercícios numa só passagem**
   (decisão §10.3). Bloco de 2 é o padrão do app (super-séries em
   duplas), então otimizar pra 2 reduz custo do fluxo. Quem quer 1
   confirma com 1 selecionado — sem fricção adicional.
4. Confirma → exercícios entram no bloco. Picker fecha.
5. Bloco recém-criado recebe highlight pulsante de 600ms (§4.3).

**Ordem dentro do bloco:** se o usuário escolheu 2 exercícios, a regra
"compostos primeiro" do gerador pode rodar automaticamente pra decidir
qual vira ex1 e qual ex2 (reuso de `_score_exercicio` em
`gerador_treino.py`). Operador não precisa pensar na ordem.

**Rota backend:**

```
POST /hub/rotina/<int:aluno>/treino/<int:t>/blocos/inserir/<int:posicao>
body:
  exercicios=[nome1, nome2]     # nomes a adicionar (1 ou 2)
  origem_exercicio={bi, ei}     # opcional: se vier, move da origem
                                # (usado por "tornar solo" e "mover pra novo bloco")
```

### 7.4 Operações no nível do bloco (mini-kebab)

Cobre **três** ações estruturais no nível do bloco:

- **Adicionar exercício a bloco existente** — caso documentado em
  `configuracoes_comuns.md` (aluno chegou em trio na semana, precisa
  expandir bloco de 2 pra 3).
- **Regerar bloco** — sortear novos exercícios mantendo os padrões de
  movimento do bloco original. Rota existente: `bloco_regerar`.
- **Remover bloco inteiro** — distinto de remover exercícios um por um.
  Rota existente: `bloco_deletar`.

**UX:**

Cada bloco ganha um **mini-kebab `…`** no header, à direita do rótulo
"BLOCO A". Tap abre action sheet com as três opções acima.

**Custo vertical:** zero. O mini-kebab vive no espaço horizontal já
existente do header do bloco (respeita §3.3).

**Remover bloco — comportamento especial (§10.7):**

Bloco inteiro tira 2-3 exercícios de uma vez. É qualitativamente mais
destrutivo que remover 1 exercício. Solução:

1. Tap em "Remover bloco" no mini-kebab → bloco some imediatamente,
   re-rotulação acontece.
2. **Toast inline no rodapé** aparece por **5 segundos**: "Bloco B
   removido · Desfazer".
3. Tap em "Desfazer" → bloco reaparece na posição original, com os
   mesmos exercícios e prescrição.
4. Sem toque → toast expira, remoção persiste no rascunho.
5. **Qualquer mutação estrutural durante os 5 segundos** (substituir
   exercício, mover, criar bloco, swap, reordenar — em qualquer treino
   da rotina) **expira o toast instantaneamente** e a remoção persiste.
   Justificativa: o snapshot client-side guardado pra reverter é do
   estado pré-remoção; se outras alterações entraram em paralelo, o
   POST de reversão pisaria nelas. Invalidar é mais simples que
   reconciliar e cobre o caso real. Edição de prescrição (autosave
   focusout) **não** invalida — é mutação de campo, não estrutural.

Caminho intermediário entre nenhuma fricção (que seria perigoso) e
modal de confirmação prévia (que seria ruidoso). Adiciona uma infra
client-side reusável (toast com ação inline) que pode atender outras
operações destrutivas raras no futuro.

**Rotas backend:**

- Adicionar exercício a bloco existente: pode reutilizar a rota de
  inserção (§7.3) com `posicao` igual ao próprio bloco-alvo + flag
  `modo=adicionar_a_existente`, ou criar rota dedicada
  `POST /hub/rotina/<aluno>/treino/<t>/bloco/<bi>/adicionar` —
  decisão técnica do Code.
- Regerar: `bloco_regerar` existe, só passa a ser invocada pelo
  mini-kebab.
- Remover com undo: precisa snapshot do bloco no client antes da
  remoção, pra reverter via POST se "Desfazer" for tocado dentro dos
  5s. Backend só vê a remoção como atômica; o estado pré-remoção é
  responsabilidade do client (Alpine).

### 7.5 Modo prescrição (drawer)

Sucessor do modo edição clássico. Única função sobrevivente: editar
**séries / reps / RIR** em lote, com visão de conjunto.

**UX:**

1. Acesso via **kebab do treino card** (no header do treino) →
   "Prescrever".
2. **Drawer sobe do bottom** ocupando ~70% da altura da tela. Fundo
   (a rotina) continua visível atenuado por trás.
3. Drawer mostra o treino atual com todos os exercícios listados,
   campos de séries/reps/RIR como inputs editáveis grandes (otimizados
   pra mobile, com teclado numérico apropriado).
4. Autosave por focusout (`hx-trigger="focusout delay:300ms"`) — já
   funciona no modo edição atual, infra reusada sem mudança.
5. Fechar drawer → volta exatamente onde estava na visualização.

**Por que drawer em vez de inline:**

- Visão de conjunto: ver volume da sessão inteira, comparar RIR entre
  blocos. Inline (popover por exercício) perde isso.
- Ergonomia mobile: inputs grandes, teclado numérico, espaço dedicado.
  Inline em popover pequeno é difícil.
- Sem risco de toque acidental: trigger explícito ("Prescrever" no
  kebab) em vez de tap em string compacta na visualização.
- Mantém separação visual entre "leitura" (visualização) e "ação de
  prescrever" (drawer).

**Backend:**

Reutiliza as rotas existentes de edição de prescrição — não muda nada
no servidor. O drawer renderiza o equivalente ao que o modo edição
mostrava hoje, mas em layout otimizado e contextualizado pra
prescrição.

`edicao_hub` ainda é ativado quando o drawer abre (porque autosave de
prescrição depende dessa flag pra renderizar campos editáveis e
disparar OOB do banner). Mas como o drawer é overlay temporário, a
ativação não polui a tela de visualização atrás.

### 7.6 Consolidação backend

As operações têm sobreposição lógica que vale considerar:

- "Tornar solo" = "inserir bloco acima" + "mover exercício pra lá".
- "Mover exercício pra novo bloco" = "tornar solo" em outra posição.
- "Inserir bloco vazio" = caso degenerado de "inserir bloco com 0
  exercícios" — embora na prática a UX sempre force pelo menos 1.

Possível consolidação: rota única `inserir_bloco` que aceita
`exercicios=[]`, `origem_exercicio={bi,ei}`, e `posicao` — atende
tornar-solo, mover-pra-novo-bloco, criar-bloco-via-picker numa só
assinatura. Decisão técnica do Code durante `/plan`.

---

## 8. Mapa de gestos consolidado

| Gesto                       | Em quê                | Ação                                              |
|----------------------------|-----------------------|---------------------------------------------------|
| Tap curto                  | Exercício             | Abre action sheet (substituir/solo/mover/remover) |
| Long-press                 | Exercício             | Ativa modo carregando (swap intra ou inter)       |
| Drag vertical              | Exercício             | Reorder intra-bloco (SortableJS, §10.5)           |
| Long-press                 | Rótulo de bloco       | Ativa modo carregando (reorder)                   |
| Tap                        | Mini-kebab do bloco   | Action sheet (adicionar/regerar/remover bloco)    |
| Tap                        | Alvo (modo carregando)| Completa swap (exercício) ou reorder (bloco)      |
| Tap                        | Gap entre blocos      | Insere bloco novo (abre picker)                   |
| Tap                        | X do pill flutuante   | Cancela modo carregando                           |
| Tap                        | "Desfazer" no toast   | Reverte remoção de bloco (5s pra agir)            |
| Swipe horizontal           | Background            | Navega entre treinos (scroll-snap)                |
| Tap                        | Chip do pager         | Vai pro treino correspondente                     |
| Tap                        | Kebab do card         | Ações no nível do treino (Prescrever, Exportar PNG, Remover) |
| Tap                        | Kebab da topbar       | Toggle Atual/Anterior, configurações da rotina    |

**Princípios:**
- *Tap curto* = abre menu de opções (em qualquer nível: exercício, bloco, treino).
- *Long-press* = ação direta por gesto (entra em modo carregando).
- *Drag* = reorganizar coisas próximas (todos visíveis sem rolar).
- *Long-press + tap* = trocar/mover coisas distantes (podem exigir rolagem/navegação).

---

## 9. Ordem sugerida de implementação

> **Status (2026-06-16): TODOS concluídos e mergeados em `main`.** Os Sub-PRs 1-7
> abaixo saíram conforme o plano; surgiu um **Sub-PR 8** não previsto (restaurar a
> substituição manual + seletor de escopo no mobile, regressão descoberta em uso).
> Detalhe de cada entrega + ponteiros de commit na seção **"13. Estado final"** no fim.

Sequência pra `/plan` no Code:

1. **✅ Sub-PR 1 — Adoção do Alpine.** Adicionar Alpine + morph ao
   `base.html`. Criar `Alpine.store('carry', ...)` e
   `Alpine.store('highlight', ...)`. Mudar `hx-swap` pra `morph` nas
   rotas que vão precisar preservar estado. Validar que nada quebra no
   app existente. **Não introduz feature nova** — só plataforma.

2. **✅ Sub-PR 2 — Swipe entre treinos (Frente A).** Reescrever o template
   da rotina no mobile como swipe-track + chip pager, conforme mockup.
   Backend não muda. Validar em mobile real. Mover toggle Atual/Anterior
   pro kebab da topbar.

3. **✅ Sub-PR 3 — Pill de modo carregando + swap inter-treino (Frente B).**
   Implementar o pill flutuante e o estado visual de origem/alvos.
   Migrar a rota de swap pra assinatura unificada (intra + inter).
   Migrar long-press intra-treino atual pra usar o novo `$store.carry`.
   Implementar highlight pulsante pós-mudança (§4.3) — usado a partir
   daqui em diante.

   **Protocolo obrigatório de teste de long-press antes de mergear** —
   long-press em mobile browser tem histórico frágil e o gesto começa
   parecido com scroll touch (dedo pousa, fica parado). Testes manuais
   prioritários, em iOS Safari **e** Chrome Android (não só DevTools
   emulado):

   - (a) Long-press num exercício e segurar parado → pill aparece em
     ~500ms, exercício de origem fica esmaecido.
   - (b) Long-press num exercício e **mover o dedo pra rolar antes dos
     500ms** → não dispara carry, scroll vertical funciona normal.
   - (c) Long-press num exercício e mover o dedo *depois* dos 500ms
     (com carry já ativo) → carry persiste, scroll funciona pra
     navegar até o alvo. (Comportamento esperado: detecção é por tempo
     parado *no início*; depois do timer disparar, dedo livre pra
     mover.)
   - (d) Swipe horizontal entre treinos imediatamente após long-press
     (sem soltar) → swipe funciona, carry permanece ativo, pill
     persiste através da troca de página.
   - (e) Tap rápido (< 500ms) num exercício → abre action sheet (§7.1),
     **não** dispara carry.
   - (f) Long-press dentro da área de drag do SortableJS intra-bloco
     → decidir quem ganha. Provavelmente long-press deve ter
     precedência (ação cross-bloco é mais explícita que reorder), mas
     validar empiricamente que os dois não se cancelam mutuamente.

   Critérios de falha que **bloqueiam** o merge: qualquer caso onde
   (b) dispara carry acidental ou (a)/(d) não persiste o estado.
   Casos (c)/(f) podem virar dívida documentada se forem aceitáveis,
   mas precisam estar resolvidos conscientemente.

   Caso o threshold de 500ms se mostre instável, primeiro recurso é
   subir pra 600ms; segundo é adicionar *cancel-on-move-threshold*
   (cancela carry se o dedo se mover mais de N px antes do timer
   disparar).

4. **✅ Sub-PR 4 — Edição estrutural nível exercício (Frente C parte 1).**
   Action sheet do tap curto. "Tornar solo" com regra "acima do bloco
   de origem". Helper `_responder_card_viz_com_banner` no backend.
   Submenu de mover exercício pra outro bloco/treino.

5. **✅ Sub-PR 5 — Edição estrutural nível bloco (Frente C parte 2).**
   Mini-kebab no header do bloco (adicionar/regerar/remover). Toast de
   undo pra remover bloco (infra reusável). Reorder de bloco via
   long-press + tap em gap. Inserção de bloco via "+" entre blocos com
   picker permitindo 1 ou 2 exercícios.

6. **✅ Sub-PR 6 — Modo prescrição como drawer (Frente C parte 3).**
   Refatorar o modo edição clássico como drawer dedicado. Adicionar
   "Prescrever" ao kebab do treino card. Garantir que autosave de
   prescrição funciona idêntico ao atual.

7. **✅ Sub-PR 7 — Saneamento.** Remover modo edição genérico das
   operações que migraram. Auditar `_responder_card_com_banner` —
   quais rotas ainda precisam dele, quais podem ir pro variante viz.
   Documentar a divisão no `CLAUDE.md`. Garantir que `bloco_mover` por
   setas continua existindo só como fallback de acessibilidade.

Sub-PRs 1 e 2 são independentes — podem rodar em paralelo. Os demais
dependem do 1. Sub-PR 6 depende do 4 e 5 estarem fechados (modo edição
só pode ser refatorado depois que tudo que era dele migrou).

---

## 10. Decisões finais

Pontos discutidos com o personal e fechados. Servem de referência rápida
durante implementação.

### 10.1 Feedback visual em reorder de bloco — **Opção C: highlight pulsante**

Animação de drop + glow/borda laranja pulsante de ~600ms no bloco
recém-movido. Sem toast, sem texto. Padrão reutilizável (§4.3) pra
todas as operações estruturais.

*Por quê:* toast vira ruído em sequência de reorders; só animação corre
risco do operador piscar e perder qual bloco mexeu. Highlight resolve os
dois sem ocupar espaço.

### 10.2 Confirmação em "tornar solo" — **Opção A: executa direto, novo bloco ACIMA**

Sem confirmação modal. Solo vai sempre imediatamente acima do bloco de
origem.

*Por quê:* operação reversível (long-press + tap reverte). Modal
contraria o princípio "visualização = edição sem cerimônia". Regra
"acima" captura a intenção real: o operador só extrai pra solo aquilo
que merece destaque clínico (composto pesado, exercício complexo,
demorado), e esses naturalmente querem estar cedo no treino.

### 10.3 Picker do novo bloco — **Opção B: 1 ou 2 numa só passagem**

Modal permite múltipla seleção até 2. Confirma, bloco já nasce com par
completo. Quem quer 1 confirma com 1 selecionado.

*Por quê:* bloco de 2 é o padrão (super-séries em duplas, documentado em
`configuracoes_comuns.md`). Otimizar pra 1 quando o padrão é 2 inverte
ergonomia. Regra "compostos primeiro" do gerador decide ordem ex1/ex2
automaticamente.

### 10.4 Validação clínica pós-swap inter-treino — **Opção A: confia no operador**

Sem re-avaliação automática de avisos depois de swap manual. Igual swap
intra-treino atual.

*Por quê:* sistema de avisos existe pra validar o algoritmo, não o
operador. Inconsistência seria adicionar validação só no inter-treino,
não no intra. Custo de implementação não-trivial sem evidência de
problema real. Caminho reativo futuro disponível se surgir necessidade.

### 10.5 SortableJS pra reorder intra-bloco — **Opção A: manter**

Drag continua pra reorganizar ex1/ex2/ex3 dentro do bloco. Long-press só
pra swap inter-bloco e inter-treino.

*Por quê:* universo pequeno e visível (2-3 exercícios, sem rolagem) é
exatamente onde drag funciona bem. Regra mental clara: *drag = alvos
próximos; long-press = alvos distantes* (mesmo modelo do iOS).
SortableJS já integrado, sem benefício em migrar.

### 10.6 Toggle Atual/Anterior — **Opção A: kebab da topbar**

Acesso via kebab `…` da topbar. Modo Anterior sinalizado com badge
"anterior" + fundo levemente mais frio.

*Por quê:* uso pontual (só quando vai criar/editar treino). Não
justifica pixel permanente. Convenção de kebab = "ações disponíveis,
mas fora do fluxo principal" se mantém.

### 10.7 Remover bloco inteiro — **Opção B: toast undo de 5s**

Remove direto, toast "Bloco B removido · Desfazer" no rodapé por 5
segundos.

*Por quê:* remover bloco é qualitativamente mais destrutivo que remover
exercício individual (perde 2-3 exercícios + prescrições). Modal
interrompe demais; toast com undo dá segurança sem fricção prévia.
Adiciona infra reusável pra outras destrutivas raras.

**Regra de invalidação do undo:** qualquer mutação estrutural em
qualquer treino da rotina durante a janela de 5s expira o toast
instantaneamente — a remoção persiste e o "Desfazer" some. Autosave
de prescrição (focusout) não invalida (mutação de campo, não
estrutural). Detalhe operacional em §7.4 item 5.

### 10.8 Modo edição → modo prescrição (drawer)

Modo edição clássico refatorado como drawer dedicado à edição de
séries/reps/RIR em lote. Único caso sobrevivente que justifica modo
separado (revisão de conjunto, ergonomia mobile de inputs numéricos).

*Por quê:* todas as outras operações que justificavam modo edição (mover,
remover, substituir, transformar) migraram pra visualização. Sobra só
prescrição em lote — e essa se beneficia de drawer focado em vez de
inline (visão de conjunto, inputs grandes, sem risco de toque acidental).

---

## 11. Riscos e dívidas

- **Performance Alpine + HTMX morph.** A extensão morph faz diff de DOM
  ao invés de replace. Em cards de treino com muitos exercícios pode
  ser mais lento que swap puro. Validar em mobile real com rotina de 5
  treinos × 8 exercícios.
- **Estado Alpine pós-navegação completa.** Se o usuário navegar pra
  outra página (`/historico`, `/alunos`) e voltar, o store global se
  reinicializa. Se houver modo carregando ativo, ele se perde — o que
  é o comportamento correto, mas vale confirmar com teste manual.
- **Snapshot client-side pra undo de remover bloco.** Toast com
  "Desfazer" exige guardar o estado do bloco antes da remoção em Alpine,
  pra POST de reversão se acionado. Bloco com 3 exercícios + prescrição
  é objeto pequeno (~1KB JSON), sem preocupação. Mas validar que o
  POST reverso re-rotula corretamente quando outros blocos foram
  reorganizados em paralelo (caso raro mas possível).
- **Acessibilidade.** Long-press não tem fallback de teclado óbvio.
  Pra usuários que dependem de teclado/leitor de tela (no desktop), o
  action sheet do tap curto e o mini-kebab do bloco cobrem a maioria
  das operações. Reorder via setas pode ser mantido como fallback
  acessível, escondido atrás de toggle ou disponível só no modo
  prescrição.
- **Compatibilidade com mobile-redesign-02.** Esta iniciativa é
  sucessora natural — não conflita com nenhuma das 12 etapas
  concluídas, mas mexe em vários dos mesmos templates
  (`_hub_treino_card.html`, `_mobile_bb_actions_hub.html`,
  `_mobile_treino_kebab_sheet.html`). Coordenar merge com QA pendente
  do redesign 02.

---

## 12. Checklist antes de virar /plan no Code

- [x] Decisão §10.1 — feedback visual de reorder (highlight pulsante).
- [x] Decisão §10.2 — "tornar solo" executa direto, novo bloco acima.
- [x] Decisão §10.3 — picker permite 1 ou 2 exercícios.
- [x] Decisão §10.4 — sem validação automática pós-swap.
- [x] Decisão §10.5 — manter SortableJS intra-bloco.
- [x] Decisão §10.6 — toggle Atual/Anterior no kebab da topbar.
- [x] Decisão §10.7 — remover bloco com toast undo de 5s.
- [x] Regra de invalidação do undo definida — qualquer mutação
      estrutural durante a janela expira o toast (§7.4 item 5, §10.7).
- [x] Decisão §10.8 — modo edição refatorado como drawer de prescrição.
- [x] Adicionar/regerar/remover bloco cobertos via mini-kebab (§7.4).
- [x] Princípio de compactness vertical estabelecido (§3.3).
- [x] Protocolo de teste de long-press registrado em §9 Sub-PR 3 —
      casos (a)-(f) + critérios de falha + plano de degradação.
- [ ] Verificar se `mockup_swipe_treinos.html` está commitado no repo
      como referência junto a este guia.
- [ ] Snapshot do estado atual (branch dedicada, commit limpo) antes do
      Sub-PR 1.
- [ ] Confirmar com Code a granularidade dos sub-PRs (este guia sugere
      7; podem ser mais ou menos a critério dele).

---

## 13. Estado final (2026-06-16) — iniciativa CONCLUÍDA

Todos os sub-PRs mergeados em `main`. Esta é a fonte de verdade do progresso —
o handoff datado (`handoff_swipe_2026-06-15.md`) foi só o prompt de abertura de
sessão e não acumula mais estado. Detalhe técnico de cada entrega vive nos
commits e (pros últimos) nas notas abaixo.

| Sub-PR | Entrega | Commits |
|---|---|---|
| 1 | Plataforma Alpine.js + morph + stores `carry`/`highlight` | `8f85924` |
| 2 | Swipe entre treinos (Frente A): swipe-track + chip pager + counter/kebab topbar | `de7a022` |
| 3 | Pill de modo carregando + swap inter-treino unificado (Frente B) + highlight | `994f39a` |
| 4 | Edição estrutural nível exercício (Frente C p1): tap→action sheet, long-press→carry, rotas viz | `948d7b0` + `6821d42` (card) |
| 5 | Edição estrutural nível bloco (Frente C p2): mini-kebab, toast undo, reorder, inserir bloco | `13e101b`→`692dfd1` (C1-C9) |
| 6 | Modo prescrição como drawer (Frente C p3) + 2 fixes (IIFE DOMContentLoaded, race autosave×fechar) | `ff91d47` `5328463` `318bb8b` |
| 7 | Saneamento: −375 linhas mortas (popup inerte, CSS órfã, rota 4-param, var morta) + doc CLAUDE.md | `bb793a0` |
| **8** | **Restaura substituição no mobile viz** (manual + escopo padrão/subregião) — regressão do Sub-PR 4 | `8be0a03` |

**Notas das últimas entregas (as que não estavam no plano original):**

- **Sub-PR 6 — armadilhas:** IIFE do drawer DEVE rodar em `DOMContentLoaded` (o
  include do shell vem depois no body); backdrop NÃO fecha o drawer (tap de
  dispensar teclado vaza); `close()` faz blur + atrasa o `visualizar-inline` em
  500ms (> debounce 300ms do autosave) — senão a prescrição em edição se perde no
  race com o clear de `edicao_hub`.
- **Sub-PR 7 — divisão de helpers** (documentada no `CLAUDE.md`): `_render_swap_cards`
  (viz, **sem** `edicao_hub`) pra ops estruturais; `_responder_card_com_banner`
  (editar/prescrição, **com** `edicao_hub`). Modo editar inline agora é **desktop-only**;
  `bloco_mover` (setas) = fallback a11y.
- **Sub-PR 8 — substituição:** action sheet do exercício → "Substituir" vira submenu
  (Sortear · mesmo padrão / Sortear · mesma subregião / Escolher da biblioteca…).
  Rotas HUB-viz novas `buscar-substitutos/<bi>/<slot>` (GET) e `substituir-por/<bi>/<slot>`
  (POST); `substituir-aleatorio` já aceitava `escopo`. Picker `_mobile_subst_picker.html`.
  Desktop (`openSubstDrawer`) intocado — substituição manual existe em 2 caminhos
  independentes (possível unificação futura, não urgente).

**Dívidas/limpezas futuras (não bloqueiam):** unificar a substituição manual
desktop (modo editar, `sessoes_ativas`) com a do mobile viz (`hub_substituir_por`,
rascunho); itens não marcados do §12 (mockup commitado / snapshot) são pré-Sub-PR-1,
históricos.
