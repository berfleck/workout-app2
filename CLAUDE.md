# CLAUDE.md — BF Treinamento · Gerador de Treinos (Flask + HTMX)

Contexto permanente para o Claude Code. Atualizar sempre que houver decisões de arquitetura, novas funcionalidades ou mudanças relevantes.

---

## Visão geral

App Flask + HTMX (Python) para personal trainer gerar, editar e exportar sessões de treino personalizadas. Roda localmente, sem servidor, sem nuvem. Todos os dados persistem em arquivos locais (JSON + XLSX).

**Migrado de Streamlit para Flask + HTMX** em abril/2026 para ganhar controle total sobre a interface, eliminar o rerun do script inteiro a cada interação, e permitir adição futura de JavaScript para funcionalidades como drag-and-drop, filtros instantâneos e comparação visual de treinos.

---

## Estrutura de arquivos

```
app_flask.py              — Backend Flask: todas as rotas (~530 linhas)
gerador_treino.py         — Lógica de geração de treinos (~1070 linhas, inalterado da versão Streamlit)
gerar_imagem.py           — Exportação de PNG (fontes DejaVu embutidas, inalterado)
banco_exercicios.xlsx     — Banco de dados de exercícios (aba "Exercícios")
requirements.txt          — Dependências Python (flask, pandas, openpyxl, pillow)
DejaVuSans.ttf            — Fonte para geração de imagem
DejaVuSans-Bold.ttf       — Fonte bold para geração de imagem

static/
  logo.png                — Logo usada nos PNGs exportados

templates/
  base.html               — Layout base: CSS completo, navegação por abas, HTMX
  treinos.html             — Aba Treinos: config (hierarquia + template), resultado
  _resultado.html          — Partial HTMX: lista de treinos gerados
  _treino_card.html        — Partial HTMX: card de 1 treino (modo visualizar e editar)
  _substituicao.html       — Partial HTMX: lista de exercícios para substituição/adição
  _historico_detalhe.html  — Partial HTMX: exercícios de um registro do histórico
  alunos.html              — Aba Alunos: CRUD completo
  historico.html           — Aba Histórico: listar, ver, carregar, apagar

Gerados automaticamente pelo app:
  alunos.json              — Cadastro de alunos
  sessoes_salvas.json      — Snapshot das sessões ativas
  historico_treinos.json   — Histórico salvo pelo usuário
```

---

## Arquitetura Flask + HTMX

### Como funciona (para quem vem do Streamlit)

No Streamlit, cada clique reroda o script inteiro (1700 linhas). No Flask + HTMX:

1. O **backend** (`app_flask.py`) define **rotas** — cada URL faz uma coisa específica
2. Os **templates** (pasta `templates/`) são HTML com marcações Jinja2 (`{% for %}`, `{{ variavel }}`)
3. O **HTMX** (biblioteca JavaScript incluída no `base.html`) faz requisições ao servidor e substitui pedaços da página sem recarregar tudo

**Exemplo concreto:** quando o usuário clica "↺" para substituir um exercício:
- O botão tem `hx-post="/treino/0/substituir/NomeDoExercicio"` e `hx-target="#treino-0"`
- O HTMX manda um POST para essa rota
- O Flask processa (chama `substituir_exercicio()` do `gerador_treino.py`)
- Retorna o HTML do card atualizado (`_treino_card.html`)
- O HTMX injeta esse HTML no lugar do card antigo — só aquele pedaço atualiza

### Templates parciais (partials)

Arquivos que começam com `_` são **partials** — não são páginas completas, são pedaços de HTML que o HTMX injeta dentro da página. Exemplo:
- `_resultado.html` → injetado na div `#resultado` quando o usuário gera treinos
- `_treino_card.html` → injetado na div `#treino-0` quando substitui/regera/edita

### Estado

- **Sessões ativas:** variável global `sessoes_ativas` no `app_flask.py` (lista de `Sessao`)
- **Configs geradas:** variável global `configs_geradas` (para regerar com mesma config)
- **Persistência:** salvo em `sessoes_salvas.json` a cada modificação via `salvar_sessoes_disco()`
- **Sem session_state:** não existe o conceito de `st.session_state`. O estado da UI é gerenciado pelo DOM (HTML na página) e pelo servidor

---

## Estruturas de dados principais (inalteradas)

### `Exercicio` (dataclass)
Campos do banco: `nome`, `variacao_de`, `eq_primario`, `eq_secundario`, `regiao`, `subregiao`, `padrao`, `purpose`, `unilateral`, `complexidade` (1-5), `fadiga` (1-5), `circuito`, `similaridade`, `musculo_primario`, `obs`
Campos de prescrição (definidos na UI): `series`, `reps` (str, ex: "8-12"), `rir` (0-4)

### `SuperSerie` (dataclass)
`label` (A/B/C...), `ex1`, `ex2` (opcional), `ex3` (opcional)

### `Sessao` (dataclass)
`tipo` (string de padrões concatenados), `blocos` (lista de SuperSerie)

---

## Rotas do Flask (`app_flask.py`)

### Páginas

| Rota | Método | O que faz |
|------|--------|-----------|
| `/` | GET | Página principal (aba Treinos) |
| `/alunos` | GET | Aba Alunos (HTMX injeta no tab) |
| `/historico` | GET | Aba Histórico (HTMX injeta no tab) |

### Geração de treinos

| Rota | Método | O que faz |
|------|--------|-----------|
| `/gerar` | POST | Gera treinos (hierarquia ou template). Retorna `_resultado.html` |

Parâmetros do form:
- `modo` = "hierarquia" ou "template"
- `n_treinos`, `max_complexidade`, `tamanho_bloco`
- `variar_entre` (checkbox), `evitar_agonistas` (checkbox)
- Hierarquia: `dem_nivel_0_N`, `dem_escopo_0_N`, `dem_qtd_0_N` (N = índice da demanda)
- Template: `template_0` (nome), `epp_0_PADRAO` (sliders)
- Lateralidade: `squat_bi_0`, `squat_uni_0`
- Exercícios fixos: `fixos_0` (nomes separados por vírgula)

### Ações por treino

| Rota | Método | O que faz |
|------|--------|-----------|
| `/treino/<t>/visualizar` | GET | Retorna card modo visualizar |
| `/treino/<t>/editar` | GET | Retorna card modo editar |
| `/treino/<t>/regerar` | POST | Regera treino respeitando os outros |
| `/treino/<t>/substituir/<nome>` | POST | Substitui exercício aleatoriamente |
| `/treino/<t>/substituir-por/<atual>/<novo>` | POST | Substitui por exercício específico |
| `/treino/<t>/prescricao/<bi>/<ei>` | POST | Salva séries/reps/RIR |
| `/treino/<t>/bloco/<bi>/mover/<up\|down>` | POST | Reordena bloco |
| `/treino/<t>/bloco/<bi>/deletar` | POST | Remove bloco |
| `/treino/<t>/bloco/<bi>/adicionar/<nome>` | POST | Adiciona exercício a bloco |
| `/treino/<t>/novo-bloco/<nome>` | POST | Cria bloco novo com exercício |
| `/treino/<t>/exercicio/remover/<bi>/<ei>` | POST | Remove exercício |
| `/buscar-exercicios` | GET | Busca exercícios com filtros (retorna HTML de radio buttons) |

### Downloads

| Rota | Método | O que faz |
|------|--------|-----------|
| `/treino/<t>/png/<aluno>` | GET | Download PNG de 1 treino |
| `/treinos/zip/<aluno>` | GET | Download ZIP de todos os treinos |

### Alunos

| Rota | Método | O que faz |
|------|--------|-----------|
| `/alunos/novo` | POST | Cria aluno |
| `/alunos/<i>/editar` | POST | Edita aluno |
| `/alunos/<i>/deletar` | DELETE | Remove aluno |

### Histórico

| Rota | Método | O que faz |
|------|--------|-----------|
| `/historico/salvar` | POST | Salva sessões ativas no histórico |
| `/historico/<id>/ver` | GET | Mostra exercícios de um registro |
| `/historico/<id>/carregar` | POST | Carrega registro para edição |
| `/historico/<id>/apagar` | DELETE | Remove registro |

---

## Lógica de geração (`gerador_treino.py`) — inalterada

### Hierarquia de classificação dos exercícios

Três níveis. Cada exercício pertence a UM padrão; padrão deriva subregião e região via mapeamento canônico.

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

**1. `gerar_sessao()` (modo legado, usado por Templates)**
Recebe lista plana de padrões + `exercicios_por_padrao` (EPP).

**2. `gerar_sessao_por_demandas()` (modo principal, usado pelo modo Hierarquia)**
Recebe lista de demandas `[(nivel, escopo, quantidade)]`. Para demandas de nível "regiao", aplica regra de proporção 60% compostos.

### Lateralidade — Agachamento
EPP aceita dois formatos: `int` (ex: `{"squat": 2}`) ou `dict` de lateralidade (ex: `{"squat": {"bilateral": 1, "unilateral": 1}}`). Quando dict, o gerador filtra candidatos pela coluna `unilateral` do banco.

### Fluxo de geração
1. Seleciona exercícios por padrão respeitando similaridade
2. Ordena compostos primeiro por fadiga decrescente
3. Monta blocos evitando agonistas, regiões iguais, e fadiga excessiva
4. Ordena blocos por peso (compostos pesados primeiro, isolados de braço por último)
5. `gerar_multiplos_treinos()` — 3 camadas de bloqueio entre treinos: nomes, variações (bidirecional), similaridade

---

## Funcionalidades implementadas

### Aba Treinos
- **Modo Hierarquia** (3 níveis expansíveis: Região → Subregião → Padrão)
  - Comportamento A: marcar pai = atalho; filhos específicos substituem o pai
  - 1 slider por checkbox marcado
  - Lateralidade squat (bilateral/unilateral) quando squat está selecionado
- **Modo Template**: templates pré-definidos com sliders EPP + lateralidade squat
- Configurações gerais: nº de treinos, exerc./bloco, complexidade máx., aluno PNG
- Checkboxes: evitar similaridade entre treinos, evitar agonistas no bloco
- **Resultado**: cards por treino com visualizar/editar/regerar/PNG
- **Modo Editar**: substituir (aleatório), remover exercício, reordenar blocos (↑↓), deletar bloco, adicionar exercício a bloco, criar novo bloco, edição de prescrição inline (séries × reps × RIR)
- Salvar no histórico com etiqueta
- Download PNG e ZIP

### Aba Alunos
- CRUD completo: nome, nível, objetivo, restrições, observações
- Edição inline com formulário que aparece abaixo do card
- Dados persistidos em `alunos.json`

### Aba Histórico
- Lista registros com data, aluno, nº de treinos
- Ver treinos de um registro (lazy load via HTMX)
- Carregar registro para edição na aba Treinos
- Apagar registro

---

## Decisões técnicas e convenções

- **Framework:** Flask + HTMX (migrado de Streamlit em abril/2026)
- **Persistência:** JSON puro (sem banco de dados por enquanto — ver Roadmap)
- **Exportação:** PNG gerado via Pillow com fontes DejaVu embutidas
- **Estado do servidor:** variáveis globais `sessoes_ativas` e `configs_geradas` no `app_flask.py`
- **CSS:** todo centralizado no `base.html` dentro de `<style>` (~200 linhas)
- **JavaScript:** mínimo necessário — funções para alternar modos, montar demandas dinamicamente, e lateralidade. HTMX cuida de toda a comunicação com o servidor
- **Cores:** laranja primário `#e85d04`, fundo cinza claro `#f9fafb`
- **Fonte UI:** DM Sans (Google Fonts via CDN)
- **HTMX:** versão 2.0.4 via CDN (unpkg.com)
- **Sem sidebar:** layout max-width 960px centralizado

### Convenções de templates
- Arquivos com `_` no início são **partials** (pedaços injetados pelo HTMX)
- `treinos.html` estende `base.html` via `{% extends %}` / `{% block %}`
- `alunos.html` e `historico.html` são carregados via HTMX dentro das divs de abas

### Atributos HTMX mais usados
- `hx-get="/rota"` — faz GET quando clicado
- `hx-post="/rota"` — faz POST quando clicado
- `hx-delete="/rota"` — faz DELETE
- `hx-target="#id"` — onde injetar a resposta
- `hx-swap="innerHTML"` — substitui o conteúdo interno do target
- `hx-trigger="load"` — dispara automaticamente ao carregar
- `hx-confirm="Texto"` — mostra confirmação antes de executar
- `hx-indicator="#id"` — mostra elemento enquanto carrega
- `hx-include="#id"` — inclui valores de outros elementos no request

---

## Roadmap / Funcionalidades futuras

### Melhorias de UI (curto prazo)
- Exercícios fixos: o backend suporta (`fixos_0` no form), mas a UI de busca/fixar ainda não foi criada nos templates
- Mover exercício entre blocos: o backend suporta (`/treino/<t>/exercicio/mover/...`), mas falta botão na UI do modo editar
- Substituição por escolha manual: o backend suporta (`/substituir-por/`), mas o painel de busca com filtros e radio buttons no modo editar ainda não está conectado (hoje só faz substituição aleatória pelo botão ↺)
- Download ZIP: rota existe, falta botão na UI quando há múltiplos treinos e aluno selecionado
- Restauração de sessão após reinício do servidor (ler `sessoes_salvas.json` no startup)

### Periodização e histórico por aluno (próxima grande feature)
- Alunos como entidade central (abrir aluno → ver histórico → gerar próximo treino)
- Histórico vinculado ao aluno (não só etiqueta livre)
- Geração inteligente: evitar exercícios dos últimos N treinos
- Lista de exercícios pausados por aluno

### Migração para SQLite (decisão pendente)
- SQLite facilita consultas de histórico por aluno
- Ainda é arquivo único na pasta do projeto
- Recomendado implementar junto com a feature de periodização

### Possibilidades com JavaScript (médio prazo)
- Drag-and-drop para reordenar blocos (SortableJS)
- Filtros instantâneos no browser sem request ao servidor
- Comparar treinos lado a lado com destaque de diferenças
- Gráficos de distribuição muscular (Chart.js)
- Animações de transição ao substituir exercícios

---

## Como rodar

```bash
cd flask_completo
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
python app_flask.py
```

Acesse `http://localhost:5000` no navegador.
