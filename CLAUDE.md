# CLAUDE.md — BF Treinamento · Gerador de Treinos (Flask + HTMX)

Contexto permanente para o Claude Code. Atualizar sempre que houver decisões de arquitetura, novas funcionalidades ou mudanças relevantes.

---

## Visão geral

App Flask + HTMX (Python) para personal trainer gerar, editar e exportar sessões de treino personalizadas. Roda localmente, sem servidor, sem nuvem. Dados persistem em arquivos locais (JSON + XLSX).

**Stack:** Flask backend + templates Jinja2 + HTMX para requisições parciais sem reload. Cada ação do usuário faz um POST/GET e o servidor devolve apenas o trecho de HTML afetado.

---

## Estrutura de arquivos

```
app_flask.py              — Backend Flask: todas as rotas
gerador_treino.py         — Lógica de geração de treinos (inalterado da versão Streamlit)
gerar_imagem.py           — Exportação de PNG (Pillow + fontes DejaVu embutidas)
banco_exercicios.xlsx     — Banco de dados de exercícios (aba "Exercícios")
requirements.txt          — flask, pandas, openpyxl, pillow

static/logo.png           — Logo usada nos PNGs exportados

templates/
  base.html               — Layout base: CSS completo, SortableJS CDN, navegação por abas
  treinos.html            — Aba Treinos: config (hierarquia + template), resultado
  _resultado.html         — Partial: lista de treinos gerados
  _treino_card.html       — Partial: card de 1 treino (modo visualizar e editar)
  _substituicao.html      — Partial: lista de exercícios para substituição/adição
  _historico_detalhe.html — Partial: exercícios de um registro do histórico
  _referencia.html        — Partial: painel de referência read-only (borda azul/índigo)
  _comparacao.html        — Partial: diff visual lado a lado (ref vs ativo)
  alunos.html             — Aba Alunos: CRUD completo
  historico.html          — Aba Histórico: listar, ver, carregar, apagar

Gerados automaticamente:
  alunos.json / sessoes_salvas.json / historico_treinos.json
```

---

## Estado do servidor

- `sessoes_ativas` — lista de `Sessao` (variável global em `app_flask.py`)
- `configs_geradas` — config usada para regerar com mesma seleção
- `referencia_ativa` — lista de `Sessao` carregada como referência read-only (não persiste em disco)
- `referencia_meta` — dict `{"etiqueta", "aluno", "data", "id"}` da referência ativa
- Persistência: `salvar_sessoes_disco()` salva em `sessoes_salvas.json` a cada modificação

---

## Estruturas de dados

### `Exercicio` (dataclass)
Campos do banco: `nome`, `variacao_de`, `eq_primario`, `eq_secundario`, `regiao`, `subregiao`, `padrao`, `purpose`, `unilateral`, `complexidade` (1-5), `fadiga` (1-5), `circuito`, `similaridade`, `musculo_primario`, `obs`
Campos de prescrição: `series`, `reps` (str, ex: "8-12"), `rir` (0-4)

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
| `/alunos` | GET | Aba Alunos |
| `/historico` | GET | Aba Histórico |

### Geração
| Rota | Método | O que faz |
|------|--------|-----------|
| `/gerar` | POST | Gera treinos (hierarquia ou template). Retorna `_resultado.html` |

Parâmetros: `modo`, `n_treinos`, `max_complexidade`, `tamanho_bloco`, `variar_entre`, `evitar_agonistas`, demandas (`dem_nivel_0_N` / `dem_escopo_0_N` / `dem_qtd_0_N`), EPP (`epp_0_PADRAO`), lateralidade squat (`squat_bi_0` / `squat_uni_0`), exercícios fixos (`fixos_0`).

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
| Rota | Método | O que faz |
|------|--------|-----------|
| `/referencia/carregar/<reg_id>` | POST | Carrega sessões de um registro do histórico para `referencia_ativa`. Retorna `_referencia.html` |
| `/referencia/carregar-ativo` | POST | Copia `sessoes_ativas` → `referencia_ativa`. Retorna `_referencia.html` |
| `/referencia/limpar` | POST | Limpa `referencia_ativa`. Retorna string vazia (limpa `#ref-container`) |
| `/referencia/clonar` | POST | `deepcopy` de `referencia_ativa` → `sessoes_ativas`. Retorna `_resultado.html` |
| `/referencia/copiar-bloco/<ref_t>/<ref_bi>/para/<dest_t>` | POST | Copia bloco da referência para o final do treino ativo. Retorna `_treino_card.html` em modo editar |
| `/comparar/<ref_t>/<ativo_t>` | GET | Diff de exercícios entre ref e ativo. Retorna `_comparacao.html` |

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
- CRUD alunos com edição inline
- Histórico: ver, carregar para edição, apagar

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

### Funcionalidades implementadas — Copiar Bloco + Diff Visual (Fase 3)
- No painel de referência, cada bloco tem botão "➡ Copiar": 1 treino ativo → botão direto; múltiplos → select + botão. Usa `copiarBloco(refT, blocoIdx, destT)` definida em `base.html` via `htmx.ajax`
- `/referencia/copiar-bloco/<ref_t>/<ref_bi>/para/<dest_t>` (POST): deepcopy do bloco + append ao treino ativo; retorna `_treino_card.html` em modo editar
- `/comparar/<ref_t>/<ativo_t>` (GET): compara nomes de exercícios; retorna `_comparacao.html` com sets `mantidos`, `removidos`, `adicionados`
- `_comparacao.html`: grid 2 colunas, exercícios coloridos (vermelho = removido da ref, verde = adicionado no ativo)
- `_resultado.html`: seção "🔍 Comparar com referência" (visível só quando `tem_referencia`); botões por par de treino limitados por `n_ref_sessoes`
- `n_sessoes_ativas` passado ao `_referencia.html`; `n_ref_sessoes` passado ao `_resultado.html` por todas as rotas que o renderizam

### Funcionalidades implementadas — Bloqueio por Referência (Fase 2)
- `/gerar`: filtra `banco` removendo exercícios (e variações via `variacao_de`) presentes na `referencia_ativa` antes de chamar `gerar_multiplos_treinos`
- `/treino/<t>/regerar`: aplica o mesmo filtro de referência somado ao filtro de outros treinos
- `/treino/<t>/substituir/<nome>`: tenta substituição preferindo exercícios fora da referência; fallback para banco completo se filtrado estiver vazio
- `/buscar-exercicios`: exercícios da referência recebem badge "REF" com opacidade reduzida (não bloqueados — usuário pode escolher)
- `/treino/<t>/buscar-substitutos/<nome>`: mesma lógica de badge REF via `nomes_ref` passado ao `_substituicao.html`

### Funcionalidades implementadas — Painel de Referência (Fase 1)
- Histórico → botão "📌 Referência" carrega treino em painel read-only acima do resultado (aba Treinos)
- Painel de referência: borda índigo, colapsável por treino, mostra exercícios com prescrição/purpose/equip
- Botão "📌 Fixar como referência" em `_resultado.html`: copia sessão atual para referência antes de gerar novos
- Botão "📋 Clonar para edição": copia referência para `sessoes_ativas` prontos para edição
- Botão "✕ Fechar": limpa painel
- `#ref-container` sempre presente no DOM em `treinos.html` (permite injeção HTMX cross-tab do histórico)
- `_resultado.html` recebe `tem_referencia=bool(referencia_ativa)` (usado nas Fases 2/3)

### Curto prazo
- UI de exercícios fixos (backend já suporta `exercicios_travados`)
- Substituição manual por escolha: backend suporta `/substituir-por/`, falta painel conectado na UI
- Download ZIP: rota existe, falta botão na UI
- Restauração de sessão após reinício do servidor (ler `sessoes_salvas.json` no startup)

### Próxima grande feature — Periodização por aluno
- Alunos como entidade central (histórico → gerar próximo treino)
- Histórico vinculado ao aluno (não só etiqueta livre)
- Geração inteligente: evitar exercícios dos últimos N treinos
- Lista de exercícios pausados por aluno
- **Decisão pendente:** continuar com JSON ou migrar para SQLite (recomendado para queries de histórico)

---

## Como rodar

```bash
python app_flask.py
```
Acesse `http://localhost:5000`.
