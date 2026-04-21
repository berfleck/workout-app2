# CLAUDE.md — BF Treinamento · Gerador de Treinos (Flask + HTMX)

Contexto permanente para o Claude Code. Atualizar sempre que houver decisões de arquitetura, novas funcionalidades ou mudanças relevantes.

---

## Visão geral

App Flask + HTMX (Python) para personal trainer gerar, editar e exportar sessões de treino personalizadas. Roda localmente, sem servidor, sem nuvem. Dados persistem em SQLite (`bf_treinamento.db`) + XLSX.

**Stack:** Flask backend + templates Jinja2 + HTMX para requisições parciais sem reload. Cada ação do usuário faz um POST/GET e o servidor devolve apenas o trecho de HTML afetado.

---

## Estrutura de arquivos

```
app_flask.py              — Backend Flask: todas as rotas
database.py               — Persistência SQLite (CRUD alunos + histórico)
gerador_treino.py         — Lógica de geração de treinos (inalterado da versão Streamlit)
gerar_imagem.py           — Exportação de PNG (Pillow + fontes DejaVu embutidas)
banco_exercicios.xlsx     — Banco de dados de exercícios (aba "Exercícios")
requirements.txt          — flask, pandas, openpyxl, pillow

static/logo.png           — Logo usada nos PNGs exportados

templates/
  base.html               — Layout base: CSS completo, SortableJS CDN, navegação por abas
  treinos.html            — Aba Treinos: config (hierarquia + template), resultado, painel histórico do aluno
  _resultado.html         — Partial: lista de treinos gerados (com auto-ref badge e badge "novo")
  _treino_card.html       — Partial: card de 1 treino (modo visualizar e editar)
  _substituicao.html      — Partial: lista de exercícios para substituição/adição
  _historico_aluno.html   — Partial: histórico filtrado por aluno (com "Carregar config" e "Fixar ref")
  _historico_detalhe.html — Partial: exercícios de um registro do histórico
  _referencia.html        — Partial: painel de referência read-only (borda azul/índigo)
  _comparacao.html        — Partial: diff visual lado a lado (ref vs ativo)
  alunos.html             — Aba Alunos: CRUD completo
  historico.html          — Aba Histórico: listar, ver, carregar, apagar

Gerados automaticamente:
  bf_treinamento.db       — SQLite (alunos + histórico com configs)
  sessoes_salvas.json     — Snapshot das sessões ativas
```

---

## Estado do servidor

- `sessoes_ativas` — lista de `Sessao` (variável global em `app_flask.py`)
- `configs_geradas` — config usada para regerar com mesma seleção. Salva no histórico junto das sessões
- `opcoes_globais` — dict com `n_treinos`, `max_complexidade`, `tamanho_bloco`, `variar_entre`, `evitar_agonistas`
- `referencias` — lista de dicts, cada item = um treino fixado como referência: `{"sessao": Sessao, "origem": {"etiqueta","aluno","data","reg_id","treino_idx"}, "id_ref": str}`. Não persiste em disco. Múltiplas refs podem acumular (de sessões distintas). Auto-preenchidas ao gerar para aluno com histórico. Helpers: `_ref_sessoes()`, `_novo_id_ref()`, `_nomes_ref_set()`.
- Persistência: `salvar_sessoes_disco()` salva em `sessoes_salvas.json` a cada modificação; startup restaura automaticamente

---

## Estruturas de dados

### `Exercicio` (dataclass)
Campos do banco: `nome`, `variacao_de`, `eq_primario`, `eq_secundario`, `regiao`, `subregiao`, `padrao`, `purpose`, `unilateral`, `complexidade` (1-5), `fadiga` (1-5), `circuito`, `similaridade`, `musculo_primario`, `obs`
Campos de prescrição: `series`, `reps` (str, ex: "8-12"), `rir` (0-4)

### `SuperSerie` (dataclass)
`label` (A/B/C...), `ex1`, `ex2` (opcional), `ex3` (opcional)

### `Sessao` (dataclass)
`tipo` (string de padrões concatenados), `blocos` (lista de SuperSerie)

### SQLite (`bf_treinamento.db` via `database.py`)
- `alunos` (id INTEGER PK, nome, nivel, objetivo, restricoes JSON, obs)
- `historico` (id TEXT PK, data_salvo, aluno, etiqueta, n_treinos, sessoes JSON, configs JSON)
- Migração automática de JSONs antigos no startup (`migrar_json_para_sqlite`)

---

## Rotas do Flask (`app_flask.py`)

### Páginas
| Rota | Método | O que faz |
|------|--------|-----------|
| `/` | GET | Página principal (aba Treinos) |
| `/alunos` | GET | Aba Alunos |
| `/historico` | GET | Aba Histórico |

### Geração
| Rota | Método | O que faz |
|------|--------|-----------|
| `/gerar` | POST | Gera treinos (hierarquia ou template). Retorna `_resultado.html` |

Parâmetros: `modo`, `n_treinos`, `max_complexidade`, `tamanho_bloco`, `variar_entre`, `evitar_agonistas`, `aluno`, `evitar_ultimos` (0-3), demandas (`dem_nivel_0_N` / `dem_escopo_0_N` / `dem_qtd_0_N`), EPP (`epp_0_PADRAO`), lateralidade squat (`squat_bi_0` / `squat_uni_0`), exercícios fixos (`fixos_0`). Quando `aluno` + `evitar_ultimos > 0`: bloqueia exercícios do histórico + auto-fixa referências do último período.

### Ações por treino
| Rota | Método | O que faz |
|------|--------|-----------|
| `/treino/<t>/visualizar` | GET | Card modo visualizar |
| `/treino/<t>/editar` | GET | Card modo editar |
| `/treino/<t>/regerar` | POST | Regera treino respeitando os outros |
| `/treino/<t>/substituir/<nome>` | POST | Substitui exercício aleatoriamente |
| `/treino/<t>/substituir-por/<atual>/<novo>` | POST | Substitui por exercício específico |
| `/treino/<t>/prescricao/<bi>/<ei>` | POST | Salva séries/reps/RIR |
| `/treino/<t>/bloco/<bi>/mover/<up\|down>` | POST | Reordena bloco |
| `/treino/<t>/bloco/<bi>/deletar` | POST | Remove bloco |
| `/treino/<t>/bloco/<bi>/adicionar/<nome>` | POST | Adiciona exercício a bloco existente |
| `/treino/<t>/novo-bloco/<nome>` | POST | Cria novo bloco com exercício |
| `/treino/<t>/exercicio/remover/<bi>/<ei>` | POST | Remove exercício |
| `/treino/<t>/exercicio/mover/<bi>/<ei>/<dest_label>` | POST | Move exercício para outro bloco (usado pelo drag-and-drop) |
| `/treino/<t>/exercicio/<bi>/<ei>/destacar` | POST | Remove do bloco e cria novo bloco isolado (drop zone) |
| `/buscar-exercicios` | GET | Busca com filtros; retorna HTML de radio buttons |

### Downloads
| Rota | Método | O que faz |
|------|--------|-----------|
| `/treino/<t>/png/<aluno>` | GET | Download PNG |
| `/treinos/zip/<aluno>` | GET | Download ZIP de todos os treinos |

### Referência
Modelo atual = lista `referencias` com **acúmulo granular** (1 treino por vez).
| Rota | Método | O que faz |
|------|--------|-----------|
| `/referencia/fixar/<reg_id>/<treino_idx>` | POST | Fixa 1 treino específico de um registro do histórico. Acumula em `referencias`. Retorna `_referencia.html` |
| `/referencia/fixar-ativo/<treino_idx>` | POST | Fixa 1 treino ativo como referência. Acumula |
| `/referencia/remover/<id_ref>` | POST | Remove 1 item específico por `id_ref` |
| `/referencia/limpar` | POST | Limpa **todas** as referências |
| `/referencia/clonar/<id_ref>` | POST | Clona 1 item para `sessoes_ativas` (substitui) |
| `/referencia/copiar-bloco/<ref_t>/<ref_bi>/para/<dest_t>` | POST | `ref_t` é índice em `referencias`. Copia bloco para o treino ativo |
| `/referencia/lista` | GET | JSON resumido das referências (para dropdown de comparação) |
| `/referencia/render` | GET | HTML do painel de referência (usado pelo auto-ref após gerar) |
| `/comparar/<ref_t>/<ativo_t>` | GET | Compara qualquer par ref×ativo (índices arbitrários). Retorna `_comparacao.html` |

### Alunos / Histórico
| Rota | Método | O que faz |
|------|--------|-----------|
| `/alunos/novo` | POST | Cria aluno |
| `/alunos/<i>/editar` | POST | Edita aluno |
| `/alunos/<i>/deletar` | DELETE | Remove aluno |
| `/historico/salvar` | POST | Salva sessões ativas |
| `/historico/<id>/ver` | GET | Exercícios de um registro |
| `/historico/<id>/carregar` | POST | Carrega para edição |
| `/historico/<id>/apagar` | DELETE | Remove registro |
| `/historico/<id>/configs` | GET | JSON das configs salvas (globals + treinos) |
| `/aluno-historico?nome=X` | GET | Retorna `_historico_aluno.html` filtrado por aluno |

---

## Lógica de geração (`gerador_treino.py`)

### Hierarquia de classificação

| Região | Subregiões | Padrões |
|---|---|---|
| `upper` | peito | empurrar_compostos, empurrar_isolados |
| | costas | remadas, puxadas |
| | ombro | ombro_composto, ombro_isolado, posterior_ombro |
| | bracos | biceps, triceps |
| `lower` | perna_anterior | squat |
| | perna_posterior | hinge, knee_flexion, abduction |
| | adutores | adduction |
| | panturrilha | flexao_plantar |
| `core` | core | core_isometrico, core_dinamico |
| `cardio` | cardio | cardio |

### Dois modos de geração

**`gerar_sessao()`** (modo legado, Templates): recebe lista de padrões + EPP (int ou dict de lateralidade por padrão).

**`gerar_sessao_por_demandas()`** (modo principal, Hierarquia): recebe `[(nivel, escopo, quantidade)]`. Demandas de região aplicam proporção mínima 60% compostos (`PROPORCAO_COMPOSTOS = 0.6`).

### Fluxo de geração
1. Seleciona exercícios por padrão respeitando similaridade (`selecionar_sem_repeticao_similaridade`)
2. `ordenar_compostos_primeiro()` — compostos por fadiga desc, depois isolados por fadiga desc
3. `montar_blocos()` — compostos buscam parceiros compostos primeiro (`preferido = purpose == "compound"`); geo-diversidade (P1: região E padrão diferentes) tem prioridade sobre qualidade de pareamento
4. `ordenar_blocos()` — score: composto = `10 + fadiga` (11–15); isolado grupo grande = `fadiga × 0.5`; isolado braço = `fadiga × 0.1`. Garante que 2 compostos sempre precedem 1 composto + isolado
5. `gerar_multiplos_treinos()` — 3 camadas de bloqueio entre treinos: nomes exatos, variações via `variacao_de` (bidirecional), similaridade (opcional)

---

## Funcionalidades implementadas

### Aba Treinos — Modo Editar
- Substituir exercício (aleatório ↺) ou remover (✕)
- Prescrição inline (séries × reps · RIR) diretamente na linha do exercício — badge exibido só no modo visualizar
- **Drag-and-drop** (SortableJS): arrastar exercício entre blocos; soltar na drop zone cria novo bloco isolado
- Reordenar blocos (↑↓), deletar bloco (🗑)
- Adicionar exercício a bloco existente, criar novo bloco via painel de busca

### Aba Treinos — Configuração
- **Abas por treino** (até `MAX_TREINOS=5`): cada treino tem sua própria config independente; campos sufixo `_{t}_`; botão "📋 Copiar config de Treino X → Aplicar" clona modo/checkboxes/sliders entre abas
- **Modo Hierarquia**: 3 níveis (Região → Subregião → Padrão), 1 slider por escopo, default **1**. Valores preservados por chave `nivel:escopo` quando demandas são re-renderizadas (evita reset ao adicionar nova categoria)
- **Modo Template**: sliders EPP por padrão
- **Lateralidade squat** integrada como refinamento de `perna_anterior` (checkboxes `.lat-chk` "Agachamento bilateral/unilateral"): gera uma demanda `(padrao, squat, bi+uni)` + hidden `squat_bi_{t}` / `squat_uni_{t}`. No modo Template continua como expander separado
- Exercícios fixos por treino (backend suporta `fixos_{t}`; UI ainda não implementada)
- Download PNG por treino, ZIP de todos os treinos

### Aba Treinos — Layout do resultado
- Treinos renderizados em **grid lado a lado** (`.resultado-grid`, `auto-fit minmax(280px, 1fr)`), dentro do container 960px; quebra para stack em telas estreitas
- **Modo visualizar compacto**: classe `.treino-card.modo-visualizar` remove meta (purpose/equip/lateralidade/fadiga/obs), reduz paddings e margens. Meta só aparece em modo editar
- **Foco de edição**: quando qualquer card entra em `modo-editar`, o grid recebe `.focando-edicao` (listener `htmx:afterSwap` em `base.html`); card editado ocupa 100% do container e os demais colapsam mostrando só o `.treino-header`
- Header do card: ações em ícones (`btn-icon`: 🔄 ✏️ ⬇) acima do título "Treino N · padrões"

### Aba Alunos / Histórico
- CRUD alunos com edição inline (SQLite via `database.py`)
- Histórico: ver, carregar para edição, apagar. Configs salvas junto (`{globals, treinos}`)

### Periodização por aluno
- **Seletor de aluno** no topo da aba Treinos — dropdown com alunos cadastrados + nomes do histórico
- **Painel de histórico do aluno** (`_historico_aluno.html`): ao selecionar aluno, mostra registros filtrados com botões "Carregar config" e "Fixar ref"
- **Carregar config**: lê configs do registro via `/historico/<id>/configs`, JS `aplicarConfigs()` reconstrói formulário inteiro (modo, checkboxes, sliders, demandas)
- **Bloqueio por histórico**: select "Evitar exerc. dos últimos N períodos" (0=desativado, 1-3). Filtra banco removendo exercícios + variações dos últimos N registros do aluno
- **Auto-ref ao gerar**: quando aluno tem histórico e bloqueio ativo, `/gerar` auto-fixa sessões do último registro como `referencias`. Badge azul "Comparando com período anterior: [etiqueta]" em `_resultado.html`
- **Badge "novo"**: exercícios que não existiam na referência recebem badge verde "novo" no modo visualizar (`_treino_card.html`)
- **Comparação automática**: seção de comparação abre automaticamente quando há auto-ref; dropdowns pré-populados
- O personal pode remover referências manualmente (fluxo existente inalterado)

---

## Decisões técnicas e convenções

- **CSS:** centralizado em `base.html` dentro de `<style>`
- **JavaScript:** mínimo — `showTab`, montagem de demandas, lateralidade, SortableJS init. HTMX faz toda comunicação servidor
- **SortableJS 1.15.3** via CDN em `base.html`. A função `initSortable(t)` no final de `_treino_card.html` inicializa as zonas sortáveis — roda na carga inicial e re-roda após cada swap HTMX (scripts em HTML swapped executam automaticamente no HTMX 2.x)
- **`hx-include`** exige atributo `name` nos inputs/selects para serializar corretamente — sem `name`, o valor não é enviado ao servidor
- **`/buscar-exercicios`**: resultados ordenados alfabeticamente, sem limite de quantidade; container com `max-height: 240px; overflow-y: auto`
- **Cores:** laranja `#e85d04`, fundo `#f9fafb`
- **Fonte UI:** DM Sans (Google Fonts)
- **HTMX:** 2.0.4 via unpkg.com

### Convenções de templates
- Arquivos com `_` são **partials** injetados pelo HTMX
- `treinos.html` estende `base.html` via `{% extends %}`
- `alunos.html` e `historico.html` carregados via HTMX nas divs de abas

---

## Roadmap

### Funcionalidades implementadas — Referência e Comparação
- **Acúmulo granular**: usuário fixa 1 treino por vez (botão `📌 Fixar` em `_historico_detalhe.html` por treino; botões `📌 T1/T2/...` em `_resultado.html` para fixar treinos ativos). Múltiplas referências de sessões distintas podem coexistir.
- **Painel slim colapsado** (`_referencia.html`): barra fina sempre visível (`.ref-bar`) com `<details>` **fechado por padrão**; cada item tem cabeçalho com origem + botões `📋 Clonar` e `✕ Remover este`; blocos/exercícios ficam em `<details>` aninhado. Botão `Limpar todas` separado do remover individual.
- **Comparação qualquer-par**: `_resultado.html` usa 2 dropdowns (`#cmp-ativo`, `#cmp-ref`) + botão que chama JS `compararTreinos()` em `base.html`. Permite comparar qualquer treino ativo com qualquer referência (não mais restrito a índices iguais).
- **Diff visual** (`_comparacao.html`): grid 2 colunas; `diff-removido` (vermelho) na coluna de referência, `diff-adicionado` (verde) na coluna ativa.
- **Copiar bloco**: mantido (`➡ Copiar` com select de destino quando há múltiplos treinos ativos); usa `copiarBloco()` em `base.html` via `htmx.ajax`.
- **Bloqueio na geração**: `/gerar`, `/treino/<t>/regerar`, `/treino/<t>/substituir` filtram banco removendo exercícios (e variações via `variacao_de`) da união de todas as `referencias`.
- **Badge REF**: `/buscar-exercicios` e `/treino/<t>/buscar-substitutos/<nome>` marcam exercícios presentes na referência com opacidade reduzida (não bloqueia escolha).
- `#ref-container` sempre presente no DOM em `treinos.html` (permite injeção HTMX cross-tab do histórico).

### Curto prazo
- UI de exercícios fixos (backend já suporta `exercicios_travados`)
- Substituição manual por escolha: backend suporta `/substituir-por/`, falta painel conectado na UI
- Download ZIP: rota existe, falta botão na UI
- Lista de exercícios pausados por aluno

---

## Como rodar

```bash
python app_flask.py
```
Acesse `http://localhost:5000`.
