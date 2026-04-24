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

Gerados: bf_treinamento.db, sessoes_salvas.json
```

## Estruturas de dados

- **`Exercicio`** (dataclass): nome, variacao_de, eq_primario, eq_secundario, regiao, subregiao, padrao, purpose, unilateral, complexidade (1-5), fadiga (1-5), circuito, similaridade, musculo_primario, obs + prescrição: series, reps (str), rir (0-4)
- **`SuperSerie`**: label (A/B/C...), ex1, ex2?, ex3?
- **`Sessao`**: tipo (string de padrões), blocos (lista de SuperSerie)
- **SQLite**: tabelas `alunos` (id, nome, nivel, objetivo, restricoes JSON, obs, rotina_ativa_id TEXT) e `historico` (id, data_salvo, aluno, etiqueta, n_treinos, sessoes JSON, configs JSON)

## Estado do servidor (variáveis globais em app_flask.py)

- `sessoes_ativas` — lista de Sessao (buffer de trabalho para gerador/edição)
- `configs_geradas` — config por treino (salva no histórico)
- `opcoes_globais` — n_treinos, max_complexidade, tamanho_bloco, variar_entre, evitar_agonistas
- `referencias` — lista de `{"sessao": Sessao, "origem": {...}, "id_ref": str}`. Auto-preenchidas ao gerar com histórico
- `edicao_hub` — dict com `aluno_id` e `rotina_id` quando editando rotina do HUB
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

## Layout

**HUB** (`hub.html`) — seletor de aluno no topo, toggle Atual/Anterior/Lado a lado, grid de treino cards com ações (substituir, remover, regerar bloco).

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

## Pendências (curto prazo)

- Fase 6 do redesign: remoção do sistema de referências manuais (substituído pelo toggle de período)
- UI de exercícios fixos (backend suporta `exercicios_travados`, falta UI)
- Painel de substituição manual conectado (backend suporta `/substituir-por/`)
- Botão download ZIP na UI (rota existe)
- Lista de exercícios pausados por aluno

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
