# Guia de redesign — BF Treinamento

> **Para o Claude Code:** este documento + os 4 arquivos HTML em `docs/redesign/` são a fonte da verdade do redesign. Antes de implementar qualquer item, leia este guia inteiro e o mockup HTML correspondente. Os mockups são a referência visual final — qualquer divergência entre o que está descrito aqui e o que está nos mockups, **o mockup vence.**

## Visão geral do sistema

O redesign cobre 6 fluxos do app, organizados em 4 mockups:

| Mockup        | Arquivo                      | Fluxos cobertos                                |
| ------------- | ---------------------------- | ---------------------------------------------- |
| **HUB**       | `mockup_redesign.html` (Versão A — já validada) | Visualização da rotina, mini-header de aluno  |
| **B · Edição**    | `mockup_b_edicao.html`        | Modo edição de treino, prescrição, substituição |
| **A · Gerador**   | `mockup_a_gerador.html`       | Página `/gerador`, modo Hierarquia, modo Template, contexto de substituição |
| **C · Auxiliares**| `mockup_c_extras.html`        | Criação manual, banner de rascunho, lado-a-lado com diff |

Os mockups foram desenhados como sistema coerente — todos compartilham os mesmos tokens visuais. Itens implementados em um lugar (ex: ícones Lucide, chips de região) devem ser reusados em todos os outros sem retrabalho.

## Princípios de design (não-negociáveis)

1. **Zero emojis na interface.** Todos os emojis (✏️ ↺ ✕ 🔄 📌 🗑 🏋️ 👥 📚 💾 🎲 ⠿ 🔥 🔧 etc.) são substituídos por ícones SVG da biblioteca **Lucide**. Os SVGs específicos usados estão inline nos mockups, dentro de `<symbol>` reutilizáveis.
2. **Mobile-first.** O Bernardo trabalha no celular durante atendimentos. Toda decisão é validada primeiro em ~380px de largura.
3. **Não duplicar contexto.** Se o aluno já está identificado pelo mini-header no topo, não repetir o nome dele em outros lugares.
4. **Densidade de informação > poluição visual.** Espaço em branco é caro. Toda hierarquia deve ser feita com tipografia, peso e cor — não com bordas excessivas ou padding gigante.
5. **Estados claros.** Toda interação tem hover, focus, active e disabled. Estados de carregamento e vazio nunca podem ficar "soltos".
6. **Coerência tipográfica.** DM Sans para corpo, JetBrains Mono para números (prescrições, contagens, posições). Nunca misturar mais fontes.

## Sistema de design (tokens)

Todos os mockups usam estas variáveis CSS. Recomendo extrair para um arquivo `static/css/tokens.css` ou injetar no `base.html`.

```css
:root {
    /* Cores da marca */
    --brand-500: #e85d04;   /* laranja principal */
    --brand-600: #d4520a;   /* hover/escuro */
    --brand-50:  #fff7ed;   /* background sutil */
    --brand-100: #fff3e6;   /* tags ativas */

    /* Cinzas */
    --gray-50:  #f9fafb;
    --gray-100: #f3f4f6;
    --gray-200: #e5e7eb;
    --gray-300: #d1d5db;
    --gray-400: #9ca3af;
    --gray-500: #6b7280;
    --gray-600: #4b5563;
    --gray-700: #374151;
    --gray-900: #111827;

    /* Estados (rascunho, sucesso, erro) */
    --green-50:  #f0fdf4;  --green-100: #dcfce7;
    --green-500: #22c55e;  --green-600: #16a34a;  --green-700: #15803d;
    --amber-50:  #fffbeb;  --amber-100: #fef3c7;  --amber-200: #fde68a;
    --amber-500: #f59e0b;  --amber-600: #d97706;  --amber-700: #b45309;
    --red-50:    #fef2f2;  --red-100:   #fee2e2;
    --red-500:   #ef4444;  --red-600:   #dc2626;  --red-700: #b91c1c;

    /* Tipografia */
    --font-body:    'DM Sans', ui-sans-serif, system-ui, sans-serif;
    --font-mono:    'JetBrains Mono', ui-monospace, monospace;
}
```

### Chips de região (cores fixas, usar em todo o app)

| Subregião       | Background    | Texto         |
| --------------- | ------------- | ------------- |
| peito           | `#ffe4e6`     | `#9f1239`     |
| costas          | `#e0f2fe`     | `#075985`     |
| ombro           | `#fef3c7`     | `#92400e`     |
| bracos          | `#ede9fe`     | `#5b21b6`     |
| perna_anterior  | `#d1fae5`     | `#065f46`     |
| perna_posterior | `#ccfbf1`     | `#115e59`     |
| core            | `#f3e8ff`     | `#6b21a8`     |
| panturrilha     | `#e0e7ff`     | `#3730a3`     |
| cardio          | `#fef9c3`     | `#854d0e`     |

Sugiro criar um helper Jinja `chip_regiao(slug)` que renderize o chip com o background/cor corretos a partir do slug da subregião.

### Componentes-chave

- **Card de treino:** `border: 1px solid var(--gray-200); border-radius: 14px; padding: 18px;` Em modo edição: `border-color: #fed7aa; box-shadow: 0 0 0 4px rgba(232,93,4,0.06);`
- **Bloco interno:** `background: #fafafa; border-radius: 10px; padding: 10px 12px;`
- **Bloco chip (A/B/C):** círculo de 22-24px laranja sólido, número branco bold em DM Sans
- **Borda lateral laranja** dos exercícios: `border-left: 3px solid var(--brand-500);` é a assinatura visual do app, manter sempre
- **Prescrição:** badge com `background: var(--brand-100); color: var(--brand-600); font-family: var(--font-mono);`

## Estado atual do progresso

✅ Versão A do HUB **já implementada** (commit anterior). Servirá de base para todos os outros itens — a paleta, ícones, chips e mini-header já estão lá. Reaproveitar.

A partir daqui, ordem sugerida de implementação:

---

## Roadmap de implementação

### Fase 1 — Modo edição (Mockup B) · ~3-4 sessões

> Referência visual: `mockup_b_edicao.html` (3 cenários no toggle do topo)
>
> Arquivo afetado principalmente: `templates/_treino_card.html`

**1.1 · Substituir todos os emojis de controle por ícones Lucide**

- Botões de ação no topo do card: `↺ → refresh-cw`, `✏️ → pencil`, `⬇ → download`
- Botões de ação do bloco: `🔄 → refresh-cw`, `↑ → arrow-up`, `↓ → arrow-down`, `🗑 → trash`
- Botões de ação do exercício: `🎲 → shuffle`, `↺ → replace`, `✕ → x`, `💾 → check` (ou remover, ver 1.4)
- Drag handle: `⠿ → grip-vertical` (do Lucide, dois pontos verticais)

Esforço: baixo. É majoritariamente find-and-replace.

**1.2 · Chips de metadados em vez de texto corrido**

Hoje os exercícios mostram `compound · 🔧 barra · bilateral · 🔥4` em texto corrido. Substituir por chips visuais:

- Chip `purpose` (composto/isolado): bg `#eff6ff`, color `#1d4ed8`, ícone `zap`
- Chip `equipamento`: bg `#f5f3ff`, color `#6d28d9`, ícone `tool`
- Chip `lateralidade` (bilateral/unilateral): bg `#f0fdfa`, color `#0f766e`
- Chip `fadiga` (só aparece se ≥ 4): bg `#fef2f2`, color `#dc2626`, ícone `flame`

Cada chip tem `font-size: 10px; padding: 1px 6px; border-radius: 4px; font-weight: 500;`.

Esforço: médio. Requer ajustar o template e talvez o macro/include de exercício.

**1.3 · Drawer lateral de substituição (em vez de painel inline)**

Hoje o painel `_substituicao.html` expande dentro do card e empurra o conteúdo. Trocar por drawer off-canvas que entra da direita.

- Largura no desktop: `max-width: 460px`
- No mobile (< 640px): vira modal cheio
- Header com nome do exercício atual (ex: "A1 · Supino reto barra") + chip de região + meta resumida
- Filtros: campo de busca + 3 selects (categoria / purpose / lateralidade)
- Lista de candidatos como rows clicáveis com radio
- Exercícios com badge "REF" em opacidade reduzida (já existe lógica `na_ref` no backend)
- Footer fixo com Cancelar + Substituir (verde)

Esforço: médio-alto. Vai exigir refatorar o HTMX da substituição. Vale conferir se HTMX consegue trocar conteúdo de um drawer separado do card pai.

**1.4 · Autosave da prescrição (remover o botão 💾)**

Hoje cada exercício tem form inline com botão 💾. Trocar por autosave on-blur:

- Inputs continuam inline mas dentro de um container visual (badge laranja)
- Quando o usuário sai do campo, dispara o salvamento via HTMX (`hx-trigger="blur"`)
- Toast verde "Prescrição salva" aparece embaixo da tela por 1.5s

Esforço: médio. Mudança de UX importante mas backend não muda.

**1.5 · Diferenciação clara entre "Adicionar exercício" e "Novo bloco"**

Hoje os dois são `<details>` semelhantes e fácil de confundir o escopo. Trocar por:

- **Adicionar exercício:** botão dashed compacto **dentro de cada bloco**, no fim, com texto "Adicionar exercício neste bloco"
- **Novo bloco:** card dashed maior, fora dos blocos, no fim do treino, com ícone grande de `+`, título "Novo bloco" e sub "Adicionar bloco C ao treino" (sub atualiza dinamicamente)

Esforço: baixo, é só restruturar o HTML.

**1.6 · Banner de modo edição no topo**

Quando entra em modo edição, mostrar banner laranja sutil acima dos cards:

> 🖉 Editando Treino 1 · Upper Push  
> Alterações são salvas automaticamente como rascunho  
> [Concluir edição]

Substitui o ícone "olho" perdido entre os outros. Banner some quando sai do modo edição.

Esforço: baixo.

---

### Fase 2 — Gerador de treinos (Mockup A) · ~4-5 sessões

> Referência visual: `mockup_a_gerador.html` (3 cenários no toggle)
>
> Arquivo afetado principalmente: `templates/treinos.html`

**2.1 · Limpeza prévia: remover painéis legados**

Antes de mexer no layout, remover do `treinos.html`:
- Painel de **referências** (não está sendo usado)
- Painel de **dicas** (legado de protótipo)

Isso libera espaço e simplifica o restante.

Esforço: baixo. Tomar cuidado com referências cruzadas no JS/CSS.

**2.2 · Layout de 2 colunas**

Reorganizar para grid `320px 1fr` em desktop, stack em mobile:

- **Esquerda fixa:** card de aluno + card de configurações gerais (sempre visíveis, não colapsadas) + botão Gerar com resumo
- **Direita:** tabs T1-T5 + switch Hierarquia/Template + corpo da configuração

No mobile o botão Gerar vira footer fixo no rodapé.

Esforço: alto. É uma reestruturação grande do `treinos.html`.

**2.3 · Tags interativas no Modo Hierarquia**

Substituir a árvore aninhada (Região → Subregião → Padrão com checkboxes em accordion) por:

- **Card de região** expansível com ícone temático colorido (rosa upper, verde lower, roxo core, amarelo cardio)
- **Subregiões** como seções compactas dentro
- **Padrões como tags clicáveis** (não checkboxes). Tag ativa: bg laranja claro, borda laranja, checkmark + contador de quantidade
- Botão **"+ Todos"** rápido por subregião

Esforço: alto. Requer pensar na estrutura HTML para que o backend continue recebendo os dados certos.

**2.4 · Painel "Demandas configuradas"**

Embaixo do modo hierarquia, painel resumo de tudo que foi marcado:

- Cada padrão selecionado em uma row com chip da região, nome, exemplos de exercícios, contador `−2+` para quantidade individual, botão `×` para remover
- Header com total: "5 exercícios"

Esse é o item de **maior valor de UX** do mockup A. Hoje o usuário não sabe o que será gerado até gerar.

Esforço: alto. Provavelmente exige nova rota/parcial HTMX.

**2.5 · Templates como cards com preview**

No modo Template, cada template vira card com:
- Nome
- Mini-tags dos padrões inclusos
- Contagem total de padrões

Após selecionar, painel embaixo mostra cada padrão com input de quantidade individual (mesma UI do Painel de Demandas).

Esforço: médio.

**2.6 · Banner de contexto pronunciado**

Quando vem do HUB com ação contextual ("substituir T2", "adicionar treino"), banner laranja proeminente no topo da página:

> ↻ Substituindo Treino 2 · Upper Pull  
> Os outros treinos da rotina serão preservados · Aluno: Bernardo Fleck  
> [← Cancelar]

E número de treinos fica **bloqueado** visualmente (só pode ser 1 quando substituindo). Aluno fica fixo (não pode trocar).

Esforço: baixo-médio.

**2.7 · Tabs T1-T5 com indicador de configuração**

Cada tab mostra `Treino 1 [5]` onde 5 é o número de exercícios já configurados. Tab ativa em preto. Botão `+ Treino` dashed separado no fim.

Esforço: baixo.

**2.8 · Botão "Copiar de outro treino"**

Substituir o ícone 📋 perdido entre as tabs por botão compacto no header da tab atual: `📋 Copiar de outro treino` (com ícone Lucide `copy`).

Esforço: baixo.

---

### Fase 3 — Auxiliares (Mockup C) · ~2-3 sessões

> Referência visual: `mockup_c_extras.html` (3 cenários no toggle)
>
> Arquivos afetados: `templates/_rotina_hub.html`, `_comparacao.html`, e novos templates

**3.1 · Estado vazio guiado na criação manual**

Quando usuário clica "Criar treino manual" no HUB, página entra em modo edição com treino vazio. Em vez de bloco A em branco:

- **Banner laranja contextual** no topo: "Criando treino manual · Treino 4" com botões Cancelar e Salvar
- **Card do treino com nome editável inline** (input que parece texto)
- **Estado vazio do bloco** com ilustração: ícone circular grande, título "Comece adicionando o primeiro exercício", sub mencionando estratégia do aluno, dois CTAs ("Buscar exercício" laranja primário, "Adicionar bloco vazio" default)
- **Quick-pick** de 6 exercícios sugeridos baseados no perfil do aluno

Esforço: médio. Exige novo template para estado vazio + lógica de sugestões (pode aproveitar a mesma do gerador).

**3.2 · Banner de rascunho refinado**

Substituir o banner amber atual por estrutura de duas faixas:

- **Faixa superior:** ícone com indicador pulsante (animação CSS), título "Rascunho ativo" com badge "3 alterações", sub "Salvo automaticamente · não publicado", e três ações: Ver alterações (toggle), Descartar (vermelho ghost), Salvar rotina (verde)
- **Faixa inferior:** input de etiqueta com label visual (ícone tag), placeholder claro, hint discreto

Esforço: baixo.

**3.3 · Painel expansível de mudanças no rascunho**

Clica em "Ver alterações" → expande lista detalhada:
- Linha por mudança com ícone colorido (verde + para adição, azul ✎ para edição, vermelho − para remoção)
- Descrição: "Treino 1 · A1 Supino reto barra: prescrição alterada de 3×10 para 4×8"
- Timestamp: "há 5 min"

Backend precisa rastrear o histórico de mudanças no rascunho. Pode ser via diff entre snapshot anterior e atual.

Esforço: alto (precisa novo backend) — pode ficar para depois se quiser priorizar UI.

**3.4 · Lado-a-lado com diff visual**

O backend já calcula `mantidos`, `removidos`, `adicionados` em `_comparacao.html`. Refazer o template para:

- **Switch de visualização** (Atual / Anterior / Lado a lado) no topo
- **Sumário de diff** com badges coloridas: ✓ 8 mantidos · + 3 adicionados · − 2 removidos
- **Filtro:** Todos · Apenas mudanças · Mantidos · Adicionados · Removidos
- **Headers de coluna distintos:** Atual com borda laranja, Anterior com borda cinza
- **Estados visuais dos exercícios:**
  - Mantido: bg verde sutil + badge "= mantido"
  - Adicionado: bg verde forte + box-shadow + badge "+ novo"
  - Removido: bg vermelho sutil + strikethrough + badge "− removido"
- **Em mobile:** colunas empilham mas header de cada uma fica sticky

Esforço: médio. Backend não muda, é template + CSS.

---

### Fase 4 — Refinamento pós-redesign · ~1-2 sessões

> Itens identificados durante a implementação das Fases 1-3, que dependem do redesign principal estar fechado.
>
> Pré-requisitos: Fases 1-3 concluídas.

**4.1 · Reorganização dos botões de criação de treino (split buttons)**

#### Diagnóstico

Hoje há 3 entradas para "criar treino" misturadas:

| Botão atual | Onde aparece | O que faz |
|---|---|---|
| **Gerar treino** (HUB sem rotina) | HUB vazio | abre `/gerador` em modo "nova rotina" |
| **Criar manualmente** | HUB com rotina | adiciona treino vazio inline (sem gerador) |
| **Adicionar treino** | HUB com rotina | abre `/gerador?acao=adicionar` (com gerador) |

Problemas:
1. **Verbo errado**: "Gerar treino" sugere uma sessão, mas o efeito é uma rotina inteira (1-5 sessões).
2. **Confusão semântica**: "Criar manualmente" vs "Adicionar treino" — ambos adicionam um treino. A diferença é o método (manual vs gerador), mas o nome do botão expressa propósito.
3. **Fluxos paralelos espalhados**: o personal pode querer criar manual ou pelo gerador em qualquer cenário (rotina nova ou adicionando à existente). Hoje só o caso "rotina nova" não oferece manual, e só o caso "adicionar à rotina existente" oferece os dois.

#### Modelo mental

Toda criação de treino tem **duas dimensões independentes**:

- **Escopo**: "rotina nova" (substitui toda rotina) ou "adicionar treino" (mantém os existentes)
- **Método**: "automático" (gerador) ou "manual" (do zero)

Hoje o usuário escolhe a combinação clicando em botões diferentes e o app inferindo. Melhor: deixar isso explícito.

#### Proposta — split button por escopo

**HUB sem rotina:**
```
[ Nova rotina ▾ ]   ← split button
   ├─ Com gerador (default)
   └─ Manual
```

**HUB com rotina:**
```
[ + Treino ▾ ]      [ Nova rotina ▾ ]
   ├─ Com gerador      ├─ Com gerador
   └─ Manual           └─ Manual
```

Cada botão é um **split button**: clique direto no corpo executa o default (sempre o gerador, que é o caso comum); clique na seta abre menu com a alternativa "Manual".

##### Vantagens
- **1 clique** para o caminho mais comum (gerador) — sem regressão.
- **2 cliques** para manual (abrir menu + escolher). Aceitável porque é minoria.
- **Tela limpa**: 1 ou 2 botões no HUB, em vez de 2 ou 3 botões soltos.
- **Verbos corretos**: "Nova rotina" deixa claro que substitui; "+ Treino" deixa claro que acresce.
- **Simétrico**: as duas opções de método estão sempre disponíveis nos dois escopos. Personal trainer constrói o mental model uma vez.

##### Onde os fluxos vão dar
- **Nova rotina · Com gerador** → `/gerador` (rotina nova)
- **Nova rotina · Manual** → entra direto no modo edição com 1 treino vazio (extensão do "Criar manualmente" atual, mas para rotina inteira). Pode oferecer "adicionar mais treinos" depois.
- **+ Treino · Com gerador** → `/gerador?acao=adicionar&aluno_id=X` (já existe)
- **+ Treino · Manual** → adiciona treino vazio inline (atual "Criar manualmente")

##### Gerador

O `/gerador` em si não muda. O banner contextual (item 2.6) já distingue "Gerando nova rotina" vs "Adicionando treino" e isso é suficiente.

##### Detalhe de UX

O split button tem dois cliques alvo distintos:
- Corpo do botão (nome) → ação default
- Caret (`▾`) à direita → abre menu

Visualmente: borda separadora vertical entre nome e caret, ambos clicáveis. Hover destaca a metade que o cursor está em.

##### Alternativa mais minimalista

Se preferir evitar split buttons, dois botões soltos por escopo, mas com hierarquia visual clara — **gerador como primário (laranja sólido), manual como secundário (default ghost)**:

```
[ Nova rotina ]  [ Manual ]      ← rotina nova
[ + Treino ] [ Manual ]          ← rotina existente
```

Custa 1 botão a mais por escopo, mas elimina a complexidade do split. A desvantagem é que "Manual" sozinho fica ambíguo ("manual o quê?"). Mitigação: tooltip ou label completo "Adicionar manual" / "Nova rotina manual" — mas aí volta a poluir.

**Recomendação:** **split button**. Resolve o trade-off cliques×poluição melhor.

##### Acessibilidade do split

- `aria-haspopup="menu"` no caret
- Tab navega para o corpo, depois para o caret
- Enter no corpo executa default; Enter no caret abre menu; setas navegam itens; Esc fecha

##### Implementação rough

- Componente Tailwind reutilizável (`.split-btn`, `.split-btn-main`, `.split-btn-caret`, `.split-btn-menu`)
- Menu como `<div>` absolute, fechado por padrão; abre via JS (toggle classe `.open`)
- Click fora fecha (listener no document)
- Atalho de teclado opcional: <kbd>M</kbd> com botão focado abre menu

##### Migração

Sem breaking change no backend — todas as rotas continuam (`/gerador?acao=*`, `/hub/rotina/X/criar-manual/iniciar`, etc.). É só reorganizar UI no `hub.html` / `_rotina_hub.html`.

Esforço: médio. UI-only, sem backend.

---

## Estimativa total

| Fase | Esforço aproximado | Itens |
| ---- | ------------------ | ----- |
| Fase 1 (Edição)        | 3-4 sessões | 6 itens |
| Fase 2 (Gerador)       | 4-5 sessões | 8 itens |
| Fase 3 (Auxiliares)    | 2-3 sessões | 4 itens |
| Fase 4 (Refinamento)   | 1-2 sessões | 1 item |
| **Total**              | **10-14 sessões** | **19 itens** |

A ordem é importante: Fase 1 estabelece padrões (chips de metadados, ícones, drawer) que serão reutilizados nas Fases 2 e 3. A Fase 4 só faz sentido depois das anteriores fechadas, porque depende dos componentes consolidados.

## Recomendações operacionais

1. **Trabalhe em uma branch separada** (`redesign/v2`) para conseguir comparar com o app atual rodando.
2. **Um item por commit.** Mesmo dentro de uma fase, cada item do roadmap merece commit isolado para facilitar revisão e revert.
3. **Faça `git stash` antes de pedir mudanças grandes.** Se o Claude Code propor algo que destoa do mockup, é mais fácil descartar.
4. **Sempre confirme o plano antes de executar.** Padrão a usar com o Claude Code:
   > "Vamos implementar o item X.Y. Antes de mexer, me mostre o plano: arquivos que vai tocar, componentes que vai criar, e como vai testar. Aguarde aprovação."
5. **Teste em ~380px sempre.** O Bernardo trabalha no celular, ignorar mobile é furar a feature.
6. **Não introduza dependências sem necessidade.** Os mockups usam apenas SVGs inline + Tailwind/CSS. Se o Claude Code sugerir adicionar Alpine.js, Vue, etc., questione antes de aceitar.

## Glossário

- **HUB:** página principal de visualização da rotina do aluno (`/hub` ou similar)
- **Gerador:** página `/gerador` onde se configura e gera novos treinos
- **Rotina:** conjunto de 1-5 sessões de treino vigentes para um aluno
- **Sessão / Treino:** uma das sessões da rotina (T1, T2, T3...)
- **Bloco:** subdivisão dentro de uma sessão (A, B, C...) — pode ser super série, tri-set ou simples
- **Padrão:** padrão de movimento (ex: "remadas", "empurrar_compostos", "squat")
- **Subregião:** área muscular (peito, costas, perna_anterior...)
- **Região:** agrupamento de subregiões (upper, lower, core, cardio)
- **Demanda:** par (padrão, quantidade) configurado para um treino antes da geração
- **Rascunho:** estado intermediário com alterações não salvas — tem auto-persistência mas não é "publicado"
- **REF:** exercício que apareceu na rotina anterior — backend marca para o gerador evitar repetição
