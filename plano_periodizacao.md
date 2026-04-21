# Plano: Fluxo de Periodização por Aluno/Turma

## Contexto

Hoje o app gera treinos "soltos" — o personal cria treinos, pode salvar no histórico, mas não há vínculo forte entre aluno e seus treinos ao longo do tempo. As configs de geração (`configs_geradas`) se perdem ao reiniciar o servidor e não são salvas no histórico.

**Objetivo:** permitir que o personal selecione um aluno/turma, carregue os treinos do período anterior, regenere treinos similares (evitando repetição), e compare visualmente o novo período com o anterior — tudo de forma fluida.

**Decisões tomadas:**
- Turma = nome livre (sem entidade formal, mesmo campo que aluno)
- Comparação = automática ao gerar + controle manual
- Banco de dados = migrar para SQLite
- Implementação = gradual em etapas

---

## Etapa 1: Migração para SQLite + Salvar Configs no Histórico — CONCLUÍDA

**O que foi feito:**
- Criado `database.py` — módulo SQLite com schema (alunos + historico), migração automática de JSON, CRUD completo
- Schema: tabela `alunos` (id, nome, nivel, objetivo, restricoes, obs) + tabela `historico` (id, data_salvo, aluno, etiqueta, n_treinos, sessoes JSON, configs JSON)
- `app_flask.py` — importa de `database.py`, removidas funções JSON locais
- Adicionadas `_configs_to_serializable()` / `_configs_from_serializable()` para serializar configs
- Adicionada `carregar_sessoes_disco()` para restaurar sessões no startup
- `/historico/salvar` inclui configs (formato `{globals: {...}, treinos: [...]}`)
- `/historico/<id>/carregar` restaura `configs_geradas` e `opcoes_globais`
- `templates/alunos.html` usa `aluno.id` (SQLite) em vez de `loop.index0`
- Migração automática: `alunos.json` e `historico_treinos.json` → `bf_treinamento.db`, originais renomeados `.json.bak`
- IDs de histórico agora incluem token hex para evitar colisão (`%Y%m%d_%H%M%S_` + hex)

---

## Etapa 2: Fluxo Centrado no Aluno — CONCLUÍDA

**O que foi feito:**
- Dropdown "Aluno / Turma" no topo dispara `onAlunoChange()` que faz fetch de `/aluno-historico?nome=X`
- Painel `#hist-aluno-panel` mostra registros do aluno com botões "Carregar config" e "Fixar ref"
- Rota `GET /aluno-historico` retorna `_historico_aluno.html` filtrado por aluno
- Rota `GET /historico/<id>/configs` retorna JSON das configs (compatível com formato legado e novo)
- `carregarConfigDoHistorico(regId)` faz fetch do JSON e chama `aplicarConfigs(data)` que:
  - Seta globals (n_treinos, complexidade, tamanho_bloco, variar, agonistas)
  - Para cada treino: seta modo, marca checkboxes, abre expanders, chama updateDemandas, seta sliders
- `fixarTodosComoRef(regId, n)` fixa todos os treinos de um registro como referências via fetch
- Dropdown inclui nomes do histórico que não são alunos cadastrados (turmas)
- `opcoes_globais` salvo junto do histórico; `modo` e `template_nome` salvos por treino config
- `database.py` — adicionada `nomes_unicos_historico()`

---

## Etapa 3: Geração Inteligente com Bloqueio por Histórico — PENDENTE

**Objetivo:** ao gerar treinos para um aluno com histórico, o app automaticamente evita repetir exercícios dos períodos anteriores.

### O que fazer:

**Modificar: `app_flask.py` rota `/gerar`**
- Ler campo `aluno` do form
- Se há aluno com histórico, buscar os últimos N registros desse aluno via `buscar_historico_por_aluno()`
- Para cada registro, carregar sessões via `carregar_registro()` e extrair exercícios (nomes + `variacao_de`)
- Adicioná-los ao filtro de exclusão do banco (mesmo mecanismo das `referencias`)
- Se o banco filtrado ficar pequeno demais, relaxar: permitir exercícios mais antigos primeiro

**Novo controle na UI (`treinos.html`):**
- Slider/select: "Evitar exercícios dos últimos N períodos" (0 = desativado, 1-5)
- Default: 1 (evitar só o último período)
- Passa como `evitar_ultimos` no form
- Visível apenas quando aluno está selecionado

**gerador_treino.py** — nenhuma mudança necessária

### Verificação
- Gerar treinos para aluno com histórico → exercícios do período anterior não aparecem
- Variações (`variacao_de`) também bloqueadas
- Slider em 0 → sem bloqueio (comportamento atual)
- Banco insuficiente → relaxa e gera com aviso

---

## Etapa 4: Comparação Automática + Visual — PENDENTE

**Objetivo:** ao gerar novos treinos para aluno com histórico, os treinos anteriores são carregados automaticamente como referência e a comparação visual está disponível de imediato.

### O que fazer:

**Modificar: `app_flask.py` rota `/gerar`**
- Se aluno selecionado e tem histórico:
  1. Carregar último registro do aluno
  2. Auto-fixar sessões desse registro como `referencias`
  3. Retornar `_resultado.html` com referências já populadas
- Personal pode remover referências manualmente (fluxo existente)

**Modificar: `templates/_resultado.html`**
- Quando há referências auto-carregadas, exibir badge "Comparando com: [etiqueta do registro anterior]"
- Dropdowns de comparação pré-selecionados (Treino 1 ativo vs Ref 1, etc.)
- Comparação visual inline: indicadores coloridos (verde=novo, sem cor=mantido, vermelho=removido)

### Verificação
- Gerar treinos para aluno com histórico → referências carregadas automaticamente
- Comparação visual disponível sem ação extra
- Remover referência manual → funciona
- Gerar sem aluno selecionado → comportamento atual (sem auto-ref)

---

## Arquivos envolvidos

| Arquivo | Etapas |
|---------|--------|
| `database.py` | 1, 2, 3 |
| `app_flask.py` | 1, 2, 3, 4 |
| `templates/treinos.html` | 2, 3 |
| `templates/_historico_aluno.html` | 2 |
| `templates/_resultado.html` | 4 |
| `templates/_treino_card.html` | 4 |
| `templates/_referencia.html` | 4 |
| `templates/alunos.html` | 1 |
| `CLAUDE.md` | atualizar ao final |
