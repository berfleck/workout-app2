# Análise de design — BF Treinamento

> Análise feita em 24/04/2026 com base na leitura do `CLAUDE.md`, `base.html`, `hub.html`, `treinos.html`, `_rotina_hub.html`, `_hub_treino_card.html`, `_resultado.html` e `_treino_card.html`.

## Estado atual

Stack: Flask + Jinja2 + HTMX 2.0.4 + Tailwind CDN + SortableJS, DM Sans, paleta laranja `#e85d04` + cinza em fundo `#f9fafb`.

Layout minimalista consistente: sidebar fixa de 60px com 3 ícones (🏋️ 👥 📚), cards brancos com `rounded-xl`, assinatura visual de borda lateral laranja de 3px nos exercícios. HUB em `max-w-5xl` centralizado; Gerador em grid de 3 colunas (config esquerda / abas T1-T5 no meio / referências direita).

## O que está bom

- **Linguagem visual coerente e sóbria** — parece produto, não protótipo.
- **Borda lateral laranja nos exercícios** é uma assinatura forte e imediatamente reconhecível.
- **Segmented control** no toggle Atual/Anterior/Lado-a-lado é a escolha certa (melhor que tabs).
- **HTMX + partials** mantém o HTML enxuto e a experiência fluida.
- **Foco de edição** (expande card editado, colapsa os outros) é um detalhe de UX sofisticado.
- **Barra fixa inferior no mobile** é boa prática e contextual.

## Oportunidades de design

### 1. Hierarquia dentro do card de treino é o ponto mais frágil

Hoje: "Treino 1" (sm/bold) + "upper + core + perna_posterior" (11px/gray-400) + "Bloco A" (10px uppercase gray-400) + exercícios. Três elementos competindo por ficarem discretos.

**Sugestão:**
- Título do treino maior (`text-base` ou `text-lg` + semibold)
- Tipo do treino virando **chips coloridos por região** (peito=rosa, costas=azul, perna=verde, core=roxo, cardio=amarelo) em vez de texto concatenado — dá leitura instantânea do "que treino é esse"
- "Bloco A/B/C" como **chip circular destacado** (●A) à esquerda em vez de label apagado

### 2. Emojis nos botões de ação puxam o app pra baixo

Botões usam ✏️ ↺ ✕ 🔄 📌 🗑 e a sidebar usa 🏋️ 👥 📚. É o detalhe que mais "grita amador" num produto para profissional.

**Sugestão:** trocar por ícones de uma lib consistente. **Lucide** é a pedida — combina com Tailwind, minimalista, gratuito. Troca simples que eleva o nível visual em ~30% sem mudar mais nada. Inclui os estados vazios (🏋️ 📋) — ficam melhor com ícone em outline grande ou ilustração sutil.

### 3. Separação dos blocos no card é fraca

Um `<hr class="thin">` entre blocos A/B/C quase some. Quando o treino tem 4-5 blocos, o olho se perde.

**Sugestão:** 
- Opção leve: cada bloco num container com background `gray-50` bem sutil e padding consistente
- Opção mais assertiva: aumentar o peso do label do bloco e usar um indicador colorido lateral
- Ou ambas, dependendo do apetite por mudança

### 4. Badge de prescrição comprimido em mobile

O `3×8-12 · RIR 2` fica apertado ao lado do nome do exercício, especialmente em mobile.

**Sugestão:** em mobile, empurrar o badge para uma segunda linha alinhada à direita, ou dar mais respiro (padding maior, destaque monospace para os números).

### 5. Falta elemento de "resumo" no HUB

Quando o aluno é selecionado, vai direto para os cards de treino. O `max-w-5xl` fica vazio no topo.

**Sugestão:** mini-header contextual acima dos cards:
> João Silva · Hipertrofia · Nível 3 · 4 treinos na rotina · atualizado há 3 dias

Preenche o espaço, dá contexto imediato e facilita o fluxo do personal quando alterna entre alunos.

### 6. ~~Gerador: 3 colunas densas no desktop~~

**Resolvido pelo roadmap.** Usuário confirmou que vai remover/remodelar:
- Painel de referências (não está sendo usado)
- Painel "Dicas" (legado de protótipo)

Isso libera espaço no gerador e reduz a densidade naturalmente.

### 7. Excesso de `text-[11px] uppercase tracking-wider gray-500`

Usado em labels de campo, títulos de seção, "Configurações gerais", "Dicas", "Aluno/Turma". Quando *tudo* é discreto, vira ruído.

**Sugestão:** segurar para 1-2 usos por tela (títulos de seção fortes). Para labels de campo, usar peso/tamanho normal — já fica discreto pela hierarquia.

## Ordem sugerida de implementação

Por custo/benefício, do mais barato ao mais trabalhoso:

1. **Trocar emojis por ícones Lucide** — mudança mecânica, altíssimo impacto visual
2. **Chips coloridos por região no tipo do treino** — mapeamento simples, ajuda muito na leitura
3. **Mini-header do aluno no HUB** — backend já tem os dados, só UI
4. **Bloco A/B/C como chip destacado** — CSS puro
5. **Redução dos 11px uppercase** — revisar caso a caso
6. **Separação visual mais forte por bloco** — exige mais decisões de design
7. **Remoção de referências + dicas no gerador** — libera espaço para reorganizar
8. **Prescrição responsiva em mobile** — ajuste de breakpoint

## Paleta sugerida para chips de região

Valores iniciais para iterar:

| Região          | Background    | Texto         |
| --------------- | ------------- | ------------- |
| peito           | `bg-rose-100` | `text-rose-700` |
| costas          | `bg-sky-100`  | `text-sky-700`  |
| ombro           | `bg-amber-100`| `text-amber-800`|
| bracos          | `bg-violet-100`| `text-violet-700`|
| perna_anterior  | `bg-emerald-100`| `text-emerald-700`|
| perna_posterior | `bg-teal-100` | `text-teal-700` |
| core            | `bg-purple-100`| `text-purple-700`|
| cardio          | `bg-yellow-100`| `text-yellow-800`|

Ajustar conforme o gosto e o contraste ficar OK no fundo `#f9fafb`.
