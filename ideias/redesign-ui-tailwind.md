# Redesign da UI com Tailwind — notas

Documento de referência pras ideias de redesign discutidas. O protótipo estático vive em `ideias/prototipo-tailwind.html` (standalone, abre direto no navegador).

---

## Problemas diagnosticados no app atual

Dos 4 pontos de atrito que você listou, apenas 2 são realmente limitação do stack Flask+HTMX:

| Problema | Causa raiz | Resolve só com Tailwind? |
|---|---|---|
| Drag & drop difícil | Não é limitação — SortableJS já funciona | N/A |
| Estado confuso (configs × aluno × ref) | Arquitetura: estado global no servidor | Não, exige refactor |
| App não atualiza na hora | HTMX swap incompleto (faltam `hx-swap-oob`) | Não |
| **UI poluída** | Design: tudo exposto simultaneamente em 960px | **Sim** |

Tailwind + redesign de layout resolve a poluição visual sem mexer no backend.

---

## O que o protótipo mostra

### Layout em 3 colunas (desktop ≥ 1024px)

```
┌─────────┬──────────────────┬─────────┐
│ Aluno   │ Config do treino │ Refs    │
│ +       │ (modo, hierarq.) │ fixadas │
│ Histór. │                  │         │
│         │                  │         │
│ [Gerar] │                  │         │
│ sticky  │                  │         │
└─────────┴──────────────────┴─────────┘
```

Elementos competem menos por atenção. O "Gerar" fica sticky na sidebar — não precisa rolar pro fim.

### Layout em 1 coluna (mobile < 1024px)

```
┌─────────────────┐
│ Header sticky   │
├─────────────────┤
│ Aluno + hist.   │
├─────────────────┤
│ Config do treino│
├─────────────────┤
│ Referências     │
├─────────────────┤
│ ...             │
└─────────────────┘
┌─────────────────┐
│ [▶ Gerar] fixo  │ ← barra fixa no rodapé
└─────────────────┘
```

- Header encolhe (labels das abas somem, só ícones)
- Ordem natural: aluno → config → refs
- Botão "Gerar" vira barra fixa no rodapé (sempre acessível)

### Padrões de UI aplicados

1. **Configurações gerais colapsáveis** (`<details>`) — fecham após preenchidas, liberam espaço
2. **Hierarquia em acordeões**, não 3 colunas sempre abertas — só abre o que está sendo editado
3. **Tabs de treino estilo shadcn** — hierarquia visual real em vez de botões com `style="background:#e85d04"` setado via JS
4. **Painel de referências persistente** à direita — hoje fica enfiado no fluxo da config competindo por espaço
5. **Chevrons e badges sutis** com Tailwind utility classes — sem CSS custom
6. **Estados hover/focus consistentes** — utility classes (`hover:bg-gray-50`, `focus:ring-2`) substituem dezenas de linhas de CSS manual

---

## Breakpoints usados

- `sm` (640px+): header mostra subtítulo, labels das abas voltam
- `lg` (1024px+): layout vira 3 colunas, botão "Gerar" volta pra sidebar

Única quebra necessária. O range 640–1023px usa stack vertical mas com header mais rico.

---

## Custo estimado

| Item | Estimativa |
|---|---|
| Adicionar Tailwind via CDN ao `base.html` | 10 minutos |
| Migrar CSS global (`base.html`) pras utility classes | 1 dia |
| Refactor da `treinos.html` pro novo layout | 1–2 dias |
| Ajustar `_treino_card.html`, `_resultado.html`, `_referencia.html`, `_comparacao.html` | 1 dia |
| Ajustar `alunos.html` e `historico.html` | 0,5 dia |
| **Total** | **3–5 dias** de trabalho focado |

Remove ~300 linhas de CSS do `base.html`. Não muda **nenhuma rota** nem **nenhuma lógica** do backend.

---

## O que Tailwind NÃO resolve

- **Estado confuso entre configs/aluno/refs**: exige repensar onde mora o estado (continua no servidor, mas com `hx-swap-oob` consistente, ou migrar refs pra SQLite).
- **Reatividade (app não atualiza)**: auditoria dos swaps HTMX, não é Tailwind.
- **Interações complexas**: autocomplete com teclado, command palette, drag-and-drop multi-zona — precisa de Alpine.js ou componentes JS de verdade. Acima disso começa a fazer sentido o caminho híbrido (Flask API + Next.js frontend).

---

## Próximos passos se decidir seguir

1. **Validar direção**: olhar o protótipo em desktop e mobile, decidir se o layout em 3 colunas faz sentido pro seu uso real (você costuma usar em tela grande ou no celular no ginásio?).
2. **Spike de 1 dia**: adicionar Tailwind CDN no `base.html` e converter só a página `alunos.html` (é a mais simples) pra validar o fluxo de migração.
3. **Migração gradual**: template por template, sem PR monolítico. Cada template continua funcional ao longo da migração.
4. **Manter o arquivo de protótipo** (`prototipo-tailwind.html`) como referência visual até o refactor terminar.

---

## Como visualizar o protótipo em mobile

1. Abrir `ideias/prototipo-tailwind.html` no Chrome/Edge/Firefox
2. F12 → ícone de celular no topo do DevTools (ou Ctrl+Shift+M)
3. Escolher dispositivo (iPhone 12 Pro, Pixel 7, etc.) ou arrastar a borda pra simular largura custom
4. Pra testar no celular real: `python -m http.server 8000` na pasta do projeto e acessar `http://IP-DO-PC:8000/ideias/prototipo-tailwind.html` pelo Wi-Fi
