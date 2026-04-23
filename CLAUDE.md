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
  base.html               — Layout base: CSS, scripts, navegação por abas
  treinos.html            — Aba Treinos: config 3 colunas + resultado + JS completo
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
  alunos.html             — Aba Alunos: CRUD
  historico.html          — Aba Histórico: filtros + lista

Gerados: bf_treinamento.db, sessoes_salvas.json
```

## Estruturas de dados

- **`Exercicio`** (dataclass): nome, variacao_de, eq_primario, eq_secundario, regiao, subregiao, padrao, purpose, unilateral, complexidade (1-5), fadiga (1-5), circuito, similaridade, musculo_primario, obs + prescrição: series, reps (str), rir (0-4)
- **`SuperSerie`**: label (A/B/C...), ex1, ex2?, ex3?
- **`Sessao`**: tipo (string de padrões), blocos (lista de SuperSerie)
- **SQLite**: tabelas `alunos` (id, nome, nivel, objetivo, restricoes JSON, obs) e `historico` (id, data_salvo, aluno, etiqueta, n_treinos, sessoes JSON, configs JSON)

## Estado do servidor (variáveis globais em app_flask.py)

- `sessoes_ativas` — lista de Sessao
- `configs_geradas` — config por treino (salva no histórico)
- `opcoes_globais` — n_treinos, max_complexidade, tamanho_bloco, variar_entre, evitar_agonistas
- `referencias` — lista de `{"sessao": Sessao, "origem": {...}, "id_ref": str}`. Auto-preenchidas ao gerar com histórico
- Persistência via `sessoes_salvas.json` (auto-save + auto-restore)

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

## Layout (treinos.html)

**Config** — grid 3 colunas (lg): sidebar esquerda (aluno + histórico + config geral + botão gerar), main (abas T1-T5 com hierarquia/template), sidebar direita (referências).

**Resultado** — grid auto-fit de treino cards. Foco de edição: card editado expande, demais colapsam.

**Mobile** — barra fixa inferior com Gerar + Ver treinos lado a lado (quando há treinos), ou Configurar (na tela de resultado).

## Convenções técnicas

- Partials (prefixo `_`) injetados via HTMX; `treinos.html` estende `base.html`; `alunos.html`/`historico.html` carregados via HTMX nas divs de abas
- `hx-include` exige atributo `name` nos inputs
- `initSortable(t)` em `_treino_card.html` re-roda a cada HTMX swap
- Campos de formulário sufixados por treino: `modo_{t}`, `dem_nivel_{t}_{i}`, `dem_escopo_{t}_{i}`, `dem_qtd_{t}_{i}`, `epp_{t}_{padrao}`, `squat_bi_{t}`, `squat_uni_{t}`, `fixos_{t}`

## Pendências (curto prazo)

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

1. Checar portas 5000/5001 com `Get-NetTCPConnection` antes de iniciar
2. Reutilizar processo existente ou matar antes de reiniciar
3. Usar `run_in_background` do Bash tool (nunca `&`)
4. Lembrar o usuário que o servidor continua rodando ao final da sessão
