# CLAUDE.md — BF Treinamento (Flask + HTMX)

App para personal trainer gerar, editar e exportar sessões de treino. Roda localmente. Dados em SQLite + XLSX.

## Refatoração em andamento

Estamos em refatoração planejada do gerador de treinos.
Documento mestre: `docs/refatoracao/guia_refatoracao_v4.md`.

Antes de qualquer mudança em `gerador_treino.py`, no banco de
exercícios, ou em rotas que toquem o motor de geração, ler o guia
e identificar em qual etapa o trabalho atual se encaixa. Não
acumular mudanças de etapas diferentes no mesmo PR.

**Log por etapa — manter atualizado.** Cada etapa tem log próprio em
`docs/refatoracao/logs/etapa_N.md`. O log é atualizado **ao fim de
cada sessão substantiva** — registra contexto da sessão, decisões
grandes, surpresas/desvios e atualizações em outros arquivos. **Não
duplicar conteúdo de docs especializados** (`dimensoes_proximidade.md`
etc) — usar ponteiros pra seções específicas. Padrão de granularidade:
seguir o que está nas Sessões 1-2 do `etapa_6.md` como referência.

Documentos de apoio (em `docs/refatoracao/`):
- `memoria_projeto.md` — contexto histórico (HIB2, casos clínicos,
  conceitos). Tem nota de superação parcial no topo: consultar com
  atenção a essa nota.
- `arquivo/` — documentos superados, NÃO usar como referência.

Fonte de verdade operacional: `guia_refatoracao_v4.md`.

## Etapa 6 Fase 3 — decisões fechadas (não reabrir sem motivo forte)

A Fase 3 conceitual foi 100% fechada na Sessão 6 (2026-05-08).
Todas as decisões abaixo estão consolidadas em
`docs/refatoracao/dimensoes_proximidade.md` (Seções 1, 2, 7, 8) e
devem ser tratadas como decididas em sessões futuras. Reabrir só
mediante evidência clínica nova ou falha empírica em calibração C
explícita — não por "será que faz sentido?" abstrato.

**Filtros hard INTRA — predicado `_compativel_intra`** (Seção 1.7):
3 regras hard centralizadas — (i) família refinada same-treino;
(ii) `variante_pontual` cross-family same-subregião; (iii) lateralidade
contextual via `SUBREGIOES_LATERALIDADE_HARD = frozenset({"costas"})`.
Outras lateralidades soft via `anti_uni_mesmo_grupo` Etapa 5.

**Set final de dimensões** (Seções 1-2): 5 core + 1 narrow-scope —
`familia_estrita`, `lateralidade`, `pegada` (matriz 4×4),
`plano_corporal`, `equipamento_grupo` (tiebreaker BAIXO INTRA),
`variante_pontual`. 5 dims descartadas (`musculo_alvo_especifico`,
`posicao_carga`, `padrao_execucao`, `plano_estabilizacao`, `tipo_core`).

**Escala numérica** (Seção 8.11 / A): unificada **-100/-50/-20/-5**
(Crítico/Alto/Médio/Baixo). `anti_uni_mesmo_grupo = -75` da Etapa 5
fica **fora** da escala unificada em estrutura paralela
(`anti_uni_mesmo_grupo_pesos`) — mecanismo já validado empiricamente
não realinha sem evidência.

**Multiplicadores INTER** (Seção 8.9 / D3.1): default global **0.8 ×
INTRA**. Overrides explícitos:
- `familia_estrita` INTER ≈ 0.80 (Soft Alto, Seção 1.4)
- `variante_pontual` INTER ≈ 0.95 (Soft Crítico, D1.c)

**HISTÓRICO toggle** (Seções 1.3, 8.9 / D3.3): janela R-1 only,
peso integral (multiplicador 1.0) quando ON, zero quando OFF.
Granularidade nome + família. Soma livre com INTER (sem clipping) —
pior caso família INTER+HISTÓRICO = -90, intencionalmente menor que
`padrao_diff +100` pra preservar semântica "soft alto desencoraja
mas permite quando banco aperta" da Seção 1.4.

**Estrutura de configuração** (Seção 8.10 / B): módulo separado
`pesos_proximidade.py` na raiz com dataclass. Hierarquia 2 níveis
(default global → override por subregião). `anti_uni` em estrutura
paralela ortogonal. Labels categóricos em B (`"soft_critico"` etc),
mapping numérico em A. Argumento opcional `pesos_override:
ConfigPesosProximidade | None = None` em `gerar_multiplos_treinos`
pra harness de calibração não contaminar globais.

**Processo de calibração** (Seção 8.12 / C): manual + coordinate
descent. Ordem das 5 dims: **família INTER → plano+pegada (acopladas)
→ lateralidade soft → HISTÓRICO → equipamento_grupo (último,
tiebreaker)**. Cap **5-10 rounds/dim** + validação cruzada como
salvaguarda — se ajuste em X quebrar Y, é sinal pra revisitar B
ou A em vez de brute-force calibração.

**Migração família INTER hard → soft** (Seção 8.9 / D3.2): Caminho C
— marca legacy em D3 (spec), execução estrutural em **Etapa 7**
(remover `variacao_pais_globais` set hard + adicionar penalty score).
Decisão "A clean break vs B coexistência" registrada como ponto de
auditoria pra Etapa 7.

**Implementação real fica pra Etapa 7.** Spec atual NÃO mexe no
gerador real. **Etapa 6 concluída em 2026-05-09** (Sessões 7a/7b/7c
fecharam E.1.b2: 78 mocks YAML em 8 grupos + 16 cenários no harness +
3 FAIL baseline pré-Etapa 7 esperados — 1.3, 2.2A, 4.1).

## Etapa 7 — plano e decisões fechadas (não reabrir sem motivo forte)

Plano consolidado na Sessão 7c (2026-05-09). **Fases 7.1-7.6 ✅
Sessões 8-13 (todas 2026-05-09). Etapa 7 CONCLUÍDA.** 7.6 fechou
como **validação + wire da Dim 3** (NÃO ajuste numérico) — 4 das 5
dims são NO-OPs no harness atual; defaults da 7.1 já razoáveis;
calibração futura via setup B do 4.1 ou escalada setup 2.3 não
bloqueia. Decisões já fechadas:

**Branch:** `etapa-7` (criado Sessão 8 a partir de `refator-gerador`).
Sem sub-branches por fase (1 PR por fase no mesmo branch).

**Ordem das 6 fases (Ordem A — predicado antes de soft INTRA antes
de INTER+HIST):**

1. **7.1 ✅ Sessão 8** — módulo `pesos_proximidade.py` completo
   (dataclass + defaults globais + overrides por subregião + estrutura
   paralela `anti_uni_mesmo_grupo_pesos` + mapping labels→numérico).
   Decisões fechadas: estrutura B.2 detalhada (overrides aninhados em
   `PesoDim`); defaults Seção 8.15.2 simplificada (1 default global +
   N/A); limitação `costas` aceita; **família INTRA = soft_alto (-50)
   ancorado em A.3** (Nota de correção 8.15.2.bis registra
   contradição com 8.15.2 shorthand).
2. **7.2 ✅ Sessão 9** — predicado `_compativel_intra` em
   `gerador_treino.py` (3 regras hard: família + variante_pontual +
   lateralidade contextual costas) + wire em `pre_alocar_rotina` via
   3 call-sites de `_candidatos_estritos`. Campo novo
   `Exercicio.variante_pontual`. **1.3: 3.80% → 0.00% ✓** /
   **2.2A: 4.30% → 0.00% ✓**. Efeito secundário corretional: relax
   antes era over-permissivo (permitia família INTRA same-treino) —
   3 snapshots e 1 teste de razão atualizados.
3. **7.3 ✅ Sessão 10** — `_score_proximidade(cand, alocados, contexto,
   pesos_config)` em `gerador_treino.py` (~linha 1577) com branch INTRA:
   par-a-par cumulativa sobre 3 dims soft (pegada, plano_corporal,
   equipamento_grupo), escopo same-subregião, **constante por dim**
   (D2.1 final, sem matriz 4×4). Helper
   `_selecionar_cand_score_aware` substitui `random.choice` nos 2
   call-sites de `pre_alocar_rotina` (passe estrito + relax). 3 fields
   novos no `Exercicio`: pegada/plano_corporal/equipamento_grupo.
   **Harness 14/16 OK + 2 FAIL esperados:** 2.3 over-correta 5.50%→0%
   (calibração 7.6 ajusta), 4.1 mantido 100% (aguarda 7.4). 1.3+2.2A
   = 0% (predicado 7.2 mantido). 13 snapshots atualizados (shifts
   benignos do score-aware) + 1 fixture hardcoded ajustada
   (Lev. Terra+Barra Isométrica seed=9).
4. **7.4 ✅ Sessão 11** — branches INTER + HISTÓRICO em
   `_score_proximidade` + Caminho A (clean break) migração família
   INTER hard→soft em `pre_alocar_rotina`. Args novos em
   `gerar_multiplos_treinos`: `historico_r1: list[Sessao] | None` (D3.3
   toggle) + `pesos_override: ConfigPesosProximidade | None` (B.4).
   Harness 4.1/4.2 com `historico_r1_factory` em `Cenario`. **Achado
   Sessão 11:** mecanismo HIST funciona (overlap cai ~13→~1.34/rotina)
   mas **métrica 4.1 binária estruturalmente impossível ficar <5% no
   setup atual** (R-1 e rotina nova mesma estrutura Variante B 2x).
   Refinamento métrica fica pra 7.5 (registrado Seção 8.15.7 item 7).
   8 snapshots + 1 fixture hardcoded ajustadas; 1 teste reformulado
   (`test_crossover_sentado_coexistencia_INTER_e_rara_pos_caminho_A`).
5. **7.5 ✅ Sessão 12** — E.2 validação. (a) Métrica 4.1 refinada
   pra contínua "% slots com overlap" (opção A): novo
   `Cenario.metrica_continua_fn` no harness + branch contínuo no
   runner agregando cross-iter (`pct = sum(viol)/sum(total)`). 4.1
   = **22.18% slots** pré-calibração; alvo <10% pós-7.6. 4.2 =
   70.72% (informativo; gap 4.2-4.1 = 48.54 pp confirma efeito
   HIST). (b) Cenário 5.1 implementado como pytest determinístico
   em `tests/test_score_proximidade_cross_region.py` (13 testes
   parametrizados — INTRA/INTER/HIST cross-region) — fora do
   harness, decisão Sessão 12. (c) Harness 14/16 OK + 2 FAIL
   esperados (2.3 + 4.1, calibração 7.6). 5.2 drift pós-7.4
   17.20%→34.60% registrado (não regressão funcional).
6. **7.6 ✅ Sessão 13** — calibração C coordinate descent fechada
   como **validação + wire**, NÃO ajuste numérico. Wire da Dim 3
   (anti_uni) implementado em `_score_pareamento` honrando spec
   8.10/B.2 (config→gerador, default-preserving). 4 das 5 dims
   confirmadas NO-OP por sondagem empírica em 1000 iters/candidato:
   Dim 1 (família INTER) cenários gateados por outras dims;
   Dim 2 (plano+pegada) banco grande, softmax acha alternativa;
   Dim 3 (anti_uni) setup 2.4 sem alternativa de pareamento;
   Dim 5 (equipamento) tiebreaker nunca dispara isolado.
   Dim 4 (HIST) plateau ~17% dentro do teto 1.2x (alvo <10%
   inalcançável sem violar invariante; piso estrutural ~6% só
   chega com mult ≥5 = peso -250). Restrições pré-7.6 (cap 10
   rounds + teto HIST 1.2x) honradas — paramos antes de
   brute-force. 2 FAIL benignas: 2.3 (NO-OP Dim 2; reabrir via
   escalada setup) + 4.1 (plateau Dim 4; reabrir via setup B do
   refinamento métrica). Detalhes Seção 8.15.9.

**Granularidade Fase 7.1:** módulo completo (não incremental).
**Ressalva:** se ambiguidade na Seção 8.10 / B aparecer durante
implementação (ex: estrutura exata do mapping labels→numérico,
comportamento de override do `anti_uni_pesos`, onde fica a função
de score que aplica pesos), parar e perguntar antes de implementar.

**Razão da Ordem A** (Sessão 7c): predicado é arquiteturalmente
independente da migração família INTER; vitória rápida em
1.3 + 2.2A; validação incremental facilita debug em 7.3 (mais
iterativa); Caminho C da D3.2 não obriga acoplamento entre
predicado e migração.

**Documentos fonte de verdade pós-Etapa 7 (próximas sessões — Etapa 8 ou refinamentos):**

- `docs/refatoracao/dimensoes_proximidade.md` Seção 8.15.9 (fechamento
  Fase 7.6 — wire Dim 3 + 4 NO-OPs como ACHADO + 2 FAIL benignas com
  caminhos de resolução)
- Seção 8.15.8 (fechamento Fase 7.5 + auditoria/reconciliação 4.1 e 5.2)
- `pesos_proximidade.py` — pesos finais validados na 7.6 (defaults da
  7.1 mantidos). Argumento `pesos_override` em `gerar_multiplos_treinos`
  pra harness de calibração futura (não contamina globais — B.4).
- `tools/calibrar_pesos_dimensoes.py` harness pronto. Métrica 4.1
  contínua via `metrica_continua_fn`.

**Refinamentos pós-Etapa 7 abertos (não bloqueiam uso real):**

- **Setup B do 4.1** (item 7 da 8.15.7): R-1 Variante A 2x ↔ rotina
  nova Variante B 2x. Banco com mais "ar" → fecha 4.1 < 10% sem
  violar invariante. ~1 sessão.
- **Escalada de setup do 2.3** (item 8 NOVO da 8.15.7): `costas(7)`
  ou `costas(8)` pra dar sinal mensurável a Dim 2 — ou aceitar 2.3
  em over-correção benigna. ~30min se aprovado.

**Pendências em aberto pós-Etapa 7** (Seção 8.15.7 + atualização 8.15.9):

1. ~~Bug retrocompat `("subregiao", "core", N)`~~ ✅ **Fechado em Fase
   8.3** (2026-05-13) via `_SUBREGIOES_LEGADAS` paralelo a
   `_PADROES_LEGADOS` + branch retrocompat em `_decompor_demanda_subregiao`.
   Teste de regressão `test_subregiao_core_legada_aloca_qtd_pedida`.
2. ~~Refator estrutural CORE real (padrões `flexao_tronco`/etc)~~
   ✅ **Fechado em Fase 8.2** (2026-05-13). XLSX migrado, aliases
   legados via `_PADROES_LEGADOS`. 4.1 declarado 6º NO-OP estrutural
   (Seção 8.15.12).
3. ~~Cenário 5.1 — implementar em Fase 7.5.~~ ✅ **Fechado em pytest
   determinístico** (`tests/test_score_proximidade_cross_region.py`,
   13 testes parametrizados — Fase 7.5 / Sessão 12).
4. Mock_futuros (5 restantes) vão pro XLSX na Fase 4 — Russian Twist +
   4 INFRAs. Etapa 8 reduziu de 11 pra 5 (refator CORE absorveu o
   resto). Pode reduzir piso 4.1.
5. Cycling determinístico de subregião (achado paralelo Sessão 7a)
   — investigar se relevante pós-Etapa 7. Pode interagir com viés
   mono-ex do 6º NO-OP.
6. **UI Histórico exposed** (Sessão 11 / Fase 7.4): contrato
   programatic `gerar_multiplos_treinos(historico_r1=...)` pronto, mas
   sem UI/integração SQLite. Toggle UI + leitura R-1 do banco fica
   pra fase posterior — não bloqueia 7.6.
7. ~~**Refinamento métrica 4.1**.~~ ✅ **Fechado opção A** (Fase 7.5 /
   Sessão 12) — métrica contínua "% slots com overlap" agregada
   cross-iter. Alvo <15% via setup B C3 (Fase 7.6 / Frente A).
   Pós-Etapa 8: predicate vira informativo (6º NO-OP).

## Etapa 8 — plano e decisões fechadas (não reabrir sem motivo forte)

**Etapa 8 CONCLUÍDA em 2026-05-13** (sessão única, branch `etapa-8`,
fases 8.1-8.4). Resolve itens 1+2 da 8.15.7: refator estrutural CORE
(item 15-quater do Anexo) + bug retrocompat `("subregiao", "core", N)`.

**Decisões fechadas** (4 perguntas iniciais via AskUserQuestion):

1. **`PADRAO_PARA_SUBREGIAO` 1:N** — vira `dict[str, set[str]]`.
   Padrões pré-Etapa 8 mantêm set de 1 elemento. 4 refinados core
   (`flexao_tronco`, `flexao_lateral`, `rotacao_tronco`, `flexao_quadril`)
   atravessam iso/dyn conforme spec; `flexao_lateral` só iso;
   `rotacao_tronco` só iso até Fase 4 cadastrar Russian Twist.
2. **Cadastros novos adiados pra Fase 4** — Russian Twist + 4 INFRAs
   continuam só em mocks YAML, não no XLSX.
3. **Aceitar spec do Anexo 15-quater nos 3 🟡** — Roda Abdominal,
   Prancha Renegade, Abd Bicicleta → `flexao_tronco`.
4. **Aliases legados via `_PADROES_LEGADOS`** — templates antigos e
   cenários do harness não migram. `core_isometrico` expande pros 4
   refinados iso; `core_dinamico` pra 2 (sem flexao_lateral nem
   rotacao_tronco até Fase 4).

**Ordem das 4 fases:**

| Fase | Escopo | Commit |
|---|---|---|
| 8.1 | Scaffolding (1:N + 4 padrões + call-sites + `_PADROES_RESERVADOS`) | `4a1b8ca` |
| 8.2 | XLSX migration + aliases + YAML cleanup + snapshots + **6º NO-OP** | `204ca49` |
| 8.3 | Bug item 1 + `_SUBREGIOES_LEGADAS` + teste de regressão | `da53a5a` |
| 8.4 | Docs + log + memory + PR pra main | (este) |

**Achado central da Fase 8.2 — 6º NO-OP estrutural pós-CORE**
(Seção 8.15.12 nova):

Refator CORE introduz **viés de distribuição por padrões mono-exercício**:
Pallof Press em `rotacao_tronco` e Prancha Lateral em `flexao_lateral`
concentram ~25% de probabilidade em R-1 (vs 7.7% pré-refator, 3.2× mais
provável). 4.1 sobe de 12.85% pra 21.54%. Sondagem Nota #5 v2 com 8
candidatos de R-1 — nenhum fecha alvo original <15%. Setup B C3 mantido
(continuidade com Frente A); predicate vira informativo.

**Taxonomia consolidada dos 3 sub-tipos de NO-OP** (Nota #5 / 1.8.4
ganha 3ª validação empírica):

1. NO-OP banco-limitado (2.3 / 8.15.10)
2. NO-OP gated por piso (4.1 pré-Etapa 8 / 8.15.11 — resolvido)
3. NO-OP por viés de distribuição (4.1 pós-Etapa 8 / 8.15.12 NOVO)

**Achado metodológico — sondagem v1 vs v2**: instrumentação de sondagem
DEVE replicar overlay do harness; raw XLSX subestima 4.1.

**Gate de fechamento Etapa 8 (todas as fases verdes):**

- pytest 175 passed (=174 + 1 novo de regressão da 8.3) + 13 snapshots
  regenerados consistentes + 1 skip pré-existente
- harness 16/16 OK (4.1 = 21.54% informativo, gate de regressão
  preservado via observação de magnitude)
- defaults da Fase 7.1 (pesos da proximidade) intocados

**Reabertura possível (não bloqueia uso real):**

- Fase 4 (XLSX 125+) — Russian Twist cadastrado de fato → expandir
  `PADRAO_PARA_SUBREGIAO[rotacao_tronco]` pra `{iso, dyn}`; pode reduzir
  piso estrutural do 4.1.
- Refator estrutural do cycling — distribuição uniforme por exercício
  em vez de por padrão eliminaria viés mono-ex. Mudança de algoritmo
  do gerador, fora do escopo Etapa 8.

**Documentos fonte de verdade pós-Etapa 8:**

- `docs/refatoracao/dimensoes_proximidade.md` Seção 8.15.12 (nova)
  — fechamento Fase 8.2 + 6º NO-OP + taxonomia + sondagem v1/v2
- `docs/refatoracao/dimensoes_proximidade.md` Seção 8.15.7 itens 1+2
  marcados ✅ fechados
- `docs/refatoracao/logs/etapa_8.md` — log da etapa
- `gerador_treino.py`:
  - `PADRAO_PARA_SUBREGIAO` final 1:N (linhas 32-66)
  - `_PADROES_LEGADOS` com aliases CORE (~linha 426)
  - `_SUBREGIOES_LEGADAS` paralelo (~linha 443)
  - `_decompor_demanda_subregiao` com branch retrocompat
- `tools/calibrar_pesos_dimensoes.py`:
  - Setup B C3 mantido em `_gerar_sessoes_r1_variante_a`
  - Predicate 4.1 informativo em `_patch_cenarios_4_x`

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
  _draft_banner.html      — Partial: banner de rascunho (atualizar/nova, etiqueta autosave, intent)
  _changes_list.html      — Partial: lista de alterações do rascunho (added/removed/edited)
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
  _avisos_modal.html      — Partial: modal auto-abre após geração com avisos da rotina
                            (demanda incompleta + flexibilização de família). Incluído
                            em _resultado.html (fluxo gerador) e hub.html (após redirect)

  # Mobile (redesign 02 — branch mobile-redesign-02, etapas 1-8 de 12 concluídas)
  _mobile_bottom_bar.html       — Referência standalone do bottom bar mobile (não usado em runtime)
  _mobile_nav_sheet.html        — Bottom sheet de navegação (Hub/Alunos/Histórico)
  _mobile_treino_kebab_sheet.html — Action sheet do kebab do treino card (Editar/Substituir/PNG/Remover)
  _mobile_bb_actions_hub.html   — Slot direito da bb no HUB (estados: vazio/visualizando/rascunho/edição)

Gerados (gitignored): bf_treinamento.db, sessoes_salvas.json
```

## Estruturas de dados

- **`Exercicio`** (dataclass): nome, variacao_de, eq_primario, eq_secundario, regiao, subregiao, padrao, purpose, unilateral, complexidade (1-5), fadiga (1-5), circuito, similaridade, musculo_primario, obs + prescrição: series, reps (str), rir (0-4)
- **`SuperSerie`**: label (A/B/C...), ex1, ex2?, ex3?
- **`Sessao`**: tipo (string de padrões), blocos (lista de SuperSerie), `avisos` (list[dict] com `tipo: "incompleta" | "familia_repetida"` + metadata por demanda/exercício), `relaxados` (list[str] de nomes escolhidos via flexibilização de família)
- **SQLite**: tabela `alunos` (id, nome, nivel, objetivo, restricoes JSON, obs, rotina_ativa_id, rascunho_rotina JSON, rascunho_etiqueta, rascunho_intent) e `historico` (id, data_salvo, data_atualizada, aluno, etiqueta, n_treinos, sessoes JSON, configs JSON)

## Estado do servidor (variáveis globais em app_flask.py)

- `sessoes_ativas` — lista de Sessao (buffer de trabalho para gerador/edição)
- `configs_geradas` — config por treino (salva no histórico)
- `opcoes_globais` — n_treinos, max_complexidade, tamanho_bloco, evitar_agonistas, relaxar_familia
- `referencias` — lista de `{"sessao": Sessao, "origem": {...}, "id_ref": str}`. Auto-preenchidas ao gerar com histórico
- `edicao_hub` — dict com `aluno_id` e `rotina_id` quando editando rotina do HUB
- `criacao_manual` — dict com `aluno_id` e `novo_idx` quando há treino sendo criado manualmente
- `historico_substituicoes` — `{(treino_idx, bloco_idx, slot): {"inicial": str, "vistos": set}}`. Cycle do botão substituir aleatório: não repete sugestões até esgotar; ao resetar preserva o nome inicial (nunca volta) e o atual. Limpo em `/gerar`, `_carregar_hub_edicao`, e quando contexto do gerador zera sessoes (acao=nova_rotina/adicionar/substituir).
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
| lower | perna_anterior | squat_bilateral, squat_unilateral |
| | perna_posterior | hinge, knee_flexion, abduction |
| | adutores | adduction |
| | panturrilha | flexao_plantar |
| core | core | core_isometrico, core_dinamico |
| cardio | cardio | cardio |

## Geração (gerador_treino.py)

Dois modos: **`gerar_sessao()`** (Templates, padrões + EPP) e **`gerar_sessao_por_demandas()`** (Hierarquia, demandas `[(nivel, escopo, qtd)]`, 60% compostos para região).

Fluxo: selecionar exercícios (família + nome) → ordenar compostos primeiro → montar blocos (geo-diversidade P1-P4, regra fadiga max 4) → ordenar blocos por score → gerar_multiplos_treinos (2 camadas bloqueio: nomes, variacao_de).

**Classificação composto vs isolado é por EXERCÍCIO via `purpose`** (não por padrão). `PURPOSE_COMPOSTO = {"compound", "explosive"}` e helper `_eh_composto(e)`. Padrões mistos como `hinge` (12 compound + 8 isolation), `squat_bilateral`/`squat_unilateral`, `puxadas` (5 + 2) e `adduction` (1 + 2) contribuem em **ambas as fases** do region 60%. Em região(N): Fase 1 cycla padrões com `filtro_purpose="composto"` (min `ceil(N×0.6)`), Fase 2 com `filtro_purpose="isolado"`. Em subregião/padrão: `_ordenar_padroes_por_prioridade(padroes, banco=banco)` põe padrões com candidato composto disponível primeiro (dinâmico, não estático), e `_selecionar_ciclando` recebe `preferir_composto=True`. Constante `PADROES_COMPOSTOS` mantida no arquivo só pra retrocompat de import — não é mais usada na lógica.

**Squat refinado em 2 padrões reais (Frente 4 da Etapa 1)**: `squat_bilateral` (6 ex no banco) e `squat_unilateral` (11 ex). Ambos mapeiam para subregião `perna_anterior`. UI desktop e mobile não mudam — chip único "Agachamento" + sub-controles `squat_bi_{t}` / `squat_uni_{t}` continuam; o parser do form em `/gerar` traduz esses campos diretamente em demandas refinadas (`("padrao", "squat_bilateral", X)` + `("padrao", "squat_unilateral", Y)`). Quando usuário pede `subregiao perna_anterior(N)` sem split bi/uni, `_selecionar_ciclando` cicla naturalmente entre os 2 padrões, dando ~50/50 em vez do viés do banco 6:11. Retrocompat: configs antigas com `("padrao", "squat", N)` ou `lateralidade_por_padrao` continuam funcionando — `_padroes_de_escopo` expande `"squat"` para os 2 filhos via `_PADROES_LEGADOS`. Em sessões serializadas com `padrao="squat"`, `_dict_to_exercicio` deriva o padrão refinado pela coluna `unilateral`. Demanda `padrao squat(N)` no template legado faz cycling com cota ceil/floor (N=2 → 1 bi + 1 uni; N=3 → 2 bi + 1 uni). Decisão deliberada do guia v4: outros padrões mistos (hinge, remadas, puxadas) NÃO migraram nesta etapa — continuam como padrão único.

**Bloqueio inter-treino (gerar_multiplos_treinos)**: dois sets globais separados — `nomes_exatos_globais` (apenas ex.nome, filtra `banco_filtrado`) e `variacao_pais_globais` (ex.nome + ex.variacao_de, controla bloqueio por família). Essa separação permite que pais concretos como "Apoio" sejam ressuscitados pelo relax quando só um filho foi usado. **Internamente** em `_selecionar_ciclando` e `selecionar_evitando_familia`, var_pais é dividido em `var_pais_inter` (read-only, herdado) e `var_pais_intra` (mutado within-session) — só `var_pais_inter` pode ser relaxado.

**Relaxamento de família** (`relaxar_familia: bool`, default ON na UI): quando uma demanda não pode ser preenchida no estrito, tenta 2 níveis em ordem: estrito (família + nome) → relaxa família entre treinos (preserva intra). Exercícios escolhidos no relax vão pra `Sessao.relaxados` (badge `↻` no UI) e geram aviso `tipo: "familia_repetida"`. Se mesmo relaxado faltar exercício (limite intra-família), gera aviso `tipo: "incompleta"`. Avisos são serializados na sessão e propagados via `flask.session['avisos_pendentes']` quando a rota /gerar redireciona pro HUB (substituir/adicionar/nova_rotina), pra que o modal apareça depois do redirect.

## Layout

**HUB** (`hub.html`) — seletor compacto de aluno no topo. Dois split buttons "+ Treino ▾" e "Nova rotina ▾" (cada um com sub-opções "Com gerador" / "Manual"). Toggle Atual/Anterior/Lado a lado dentro do badge do aluno (ícones i-eye, i-clock, i-columns). Grid de treino cards com ações (substituir, remover, regerar bloco). Banner de rascunho aparece automaticamente em qualquer alteração.

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
- **Rascunho/edição**: editar inline ativa rascunho automaticamente. Banner reativo via `hx-swap-oob` (helper `_responder_card_com_banner` adiciona OOB do banner em ~14 rotas `/treino/*` durante `edicao_hub`). Salvar tem dois modos: `atualizar` (sobrescreve registro mantendo id; preenche `data_atualizada`) e `nova` (cria registro novo, vira rotina ativa). Quando `rascunho_intent='nova-rotina'` (split "Nova rotina · Manual"), banner esconde "Atualizar rotina" para evitar sobrescrita acidental. Mini-header do aluno mostra "criada/atualizada há X" usando `data_atualizada` quando existe.
- **Diff rascunho × publicada**: helper `diff_rascunho_vs_publicada(aluno_id)` detecta `added` / `removed` / `edited` (prescrição) / `moved` (troca de posição). Para `moved`, pares simétricos (A↔B) viram um único registro de swap; movimentos avulsos (raros) viram registros individuais. Lazy-load via `/hub/rotina/<id>/alteracoes`. "Lado a lado" usa `classificar_exercicios_diff(atuais, anteriores)` com 4 estados visuais.
- **Estado por posição (rascunho)**: helper `_estados_rascunho_por_posicao(rascunho, publicada)` retorna `{(treino_idx, bloco_label, ei): estado}` com 4 estados — `mantido` / `swap` (mesmo nome em outra posição) / `substituido` (posição existia com outro nome) / `novo`. Passado como `estados_rascunho` para `_hub_treino_card.html` em 3 rotas (HUB principal, swap, visualizar-inline). Rendeiriza pills `.ex-pill-{mantido,swap,substituido,novo}` (ícone-only, sem texto) ao lado do nome quando há rascunho ativo.
- **Swap intra-treino por long-press (mobile)**: rota `POST /hub/rotina/<aluno>/treino/<t>/swap/<bi_a>/<ei_a>/<bi_b>/<ei_b>` faz swap atômico entre 2 exercícios do MESMO treino e persiste como rascunho **sem ativar `edicao_hub`** (escreve direto via `salvar_rascunho`). Long-press 500ms ativa modo swap, tap em outro exercício completa. JS usa `fetch` puro (não `htmx.ajax`) e por isso precisa chamar manualmente `htmx.ajax('GET', '/_mobile_bb_actions')` no callback pra atualizar a bottom bar. Atributos `data-swap-ex` + `data-aluno-id`/`data-treino-idx`/`data-bloco-idx`/`data-ei` em `.exercicio` em `_hub_treino_card.html` são obrigatórios pro JS funcionar.
- **Mobile bb (rascunho)**: `_mobile_bb_actions_hub.html` mostra "Atualizar" sempre que `_topbar_tem_rotina and _topbar_intent != 'nova-rotina'` — espelha o banner desktop. NÃO depende de `_topbar_alteracoes > 0` (que ignora moves; usar essa condição esconderia "Atualizar" após swaps).
- **Toggle Anterior**: quando há rascunho, "Anterior" passa a mostrar a rotina ativa publicada (não a anterior à ativa).
- **Autosave de prescrição**: `hx-trigger="focusout delay:300ms"` na form. Salva ao sair do form, não enquanto digita. Rota `/limpar` zera prescrição.
- **Badge `↻` (família repetida)**: classe `.badge-relaxado` em `base.html`. Renderizado em `_treino_card.html` e `_hub_treino_card.html` quando `ex.nome in sessao.relaxados`. Persiste através de serialização (`_sessao_to_dict`/`_dict_to_sessao` incluem o campo `relaxados`).
- **Modal de avisos** (`_avisos_modal.html`): auto-abre via IIFE inline. Distingue por tipo — `incompleta` mostra "ficou incompleto" + sugestões; `familia_repetida` mostra lista de exercícios relaxados. Botão "ver detalhes" reabre. Em fluxos de redirect (HUB), `session['avisos_pendentes']` é populada em `/gerar` e popped no `/` (index) — modal aparece no HUB após o setTimeout do snippet de redirect.

## Pendências (curto prazo)

- UI de exercícios fixos (backend suporta `exercicios_travados`, falta UI)
- Botão download ZIP na UI (rota existe)
- Lista de exercícios pausados por aluno
- Sistema de referências manuais legado (`_referencia.html`, `_comparacao.html`) — remover quando confirmado que toggle de período + lado a lado cobrem todos os casos

## Redesign mobile (em progresso · branch `mobile-redesign-02`)

**Etapas 1-12 de 12 concluídas** 🎉. Ver `docs/redesign/guia_redesign_mobile.md` (seção "🚦 Estado atual") para handoff completo + lista de commits + decisões importantes. Próxima: QA pass final + abrir PR pra `main` (ou Etapa 13 opcional: modo "Substituir treino" no gerador).

### O que mudou já no app (impacto fora do mobile)

- **Endpoints novos:**
  - `GET /_mobile_bb_actions` — re-fetch das ações da bb (HUB only)
  - `POST /hub/rotina/<id>/etiqueta` — autosave da etiqueta da rotina (rascunho ou histórico)
  - `POST /hub/rotina/<id>/concluir-edicao` — sai modo edição mantendo rascunho
- **`descartar-rascunho`** agora também limpa `edicao_hub` global
- **Função `database.atualizar_etiqueta_historico(reg_id, etiqueta)`** — UPDATE só da etiqueta
- **Context processor `_inject_topbar_aluno`** (em `app_flask.py`) injeta em TODOS os templates: `_topbar_alunos`, `_topbar_aluno`, `_topbar_tem_rotina`, `_topbar_eh_rascunho`, `_topbar_intent`, `_topbar_alteracoes`, `_topbar_em_edicao`, `_nav_alunos_total`, `_nav_sem_rotina`
- **`before_request` `_track_aluno_selecionado`:** `?aluno_id=X` na URL persiste na session; `?aluno_id=` (vazio) limpa
- **`_hub_treino_card.html`:** header reescrito — agora badge "T1" + nome customizado (ou "Treino N" como fallback) + 1 único botão kebab `...` à direita (estado kebab no mobile via `body.body--em-edicao`)
- **`_rotina_hub.html`:** card aluno simplificado — só nome + etiqueta editável inline (input com autosave). Removido nivel/objetivo/N treinos/data
- **`base.html`:** body recebe `data-active-page="{{ active_page or '' }}"`. Tokens novos no `:root`: `--bb-height`, `--bb-action-h`, `--bb-radius`, `--sheet-*`, `--drawer-*`, `--z-*`. Mobile breakpoint = `768px` (sidebar/hambúrguer escondidos no mobile real)
- **`_draft_banner.html`:** ganhou variante mobile compacta (1 linha amber com chevron expand pra alterações)
- **`_treino_card.html`:** removido `<span class="edit-mode-sub">Alterações são salvas automaticamente</span>` (texto redundante no banner do card editado)

### Bugs históricos a evitar (pra próximas etapas)

- **`:has()` quebra drag do SortableJS** — re-avalia CSS a cada mudança de classe (`sortable-ghost`, `sortable-chosen`). Use classe JS no body.
- **`}` órfã em `<style>`** fecha a tag prematuramente, descarta TUDO depois. Conferir abertura/fechamento ao adicionar blocos CSS.
- **Blocks dentro de `{% include %}`** não são overridables pelo template extending (Jinja). Pra slots dinâmicos, defina `{% block %}` direto em base.html.
- **Script no meio do body** roda no parse-time, antes do DOM completo. Use `DOMContentLoaded` ou delegação.
- **`fetch` puro não dispara `htmx:afterSwap`** — listeners que dependem disso (ex: refetch de `.bb-actions` mobile) precisam ser chamados manualmente no callback do `.then()`. Vale também pro inverso: se trocar `htmx.ajax` por `fetch` numa rota existente, mapear todos os listeners de `htmx:afterSwap` que reagem àquele target.
- **`hidden md:inline-flex` do Tailwind CDN às vezes perde** pra `.btn { @apply ... inline-flex }` por ordem de CSS. Se botões desktop "voltarem a aparecer" no mobile, adicionar `display: none !important` defensivo dentro de `@media (max-width: 768px)`.
- **`_responder_card_com_banner` ativa `edicao_hub`** — não usar pra ações que devem só salvar rascunho sem entrar em modo edição (ex: swap por long-press). Pra esses casos, escrever rascunho direto via `salvar_rascunho()` e renderizar `_hub_treino_card.html` (visualizar) + `render_draft_banner_oob()`.

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
