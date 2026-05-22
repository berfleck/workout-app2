# Etapa 8 — Refator estrutural CORE

**Status:** ✅ **CONCLUÍDA em 2026-05-13** (sessão única). Fases 8.1, 8.2,
8.3 fechadas; 8.4 = docs + PR pra main.

**Última atualização:** 2026-05-13 (Fase 8.4 — fechamento).

**Branch:** `etapa-8` (a partir de main).

**Escopo:** itens 1 + 2 da Seção 8.15.7 do `dimensoes_proximidade.md`:

- Item 2: refator estrutural CORE conforme Anexo 15-quater — `core_isometrico`
  / `core_dinamico` como padrões substituídos pelos 4 padrões biomecânicos
  refinados (`flexao_tronco`, `flexao_lateral`, `rotacao_tronco`,
  `flexao_quadril`). Subregiões iso/dyn inalteradas.
- Item 1: bug retrocompat `("subregiao", "core", N)` que falhava com
  `qtd_obtida=0` — agora fechado via `_SUBREGIOES_LEGADAS`.

**Restrições mantidas durante toda a etapa:**

- Pesos da proximidade (defaults da Fase 7.1) intocados.
- 5 dimensões já cadastradas (familia_estrita, pegada, plano_corporal,
  equipamento_grupo, variante_pontual) intocadas.
- 5 cadastros novos (Russian Twist + 4 INFRAs) adiados pra Fase 4
  (P2 do briefing inicial).

---

## Fase 8.1 — Scaffolding estrutural (commit `4a1b8ca`)

### Mudanças aplicadas

- `PADRAO_PARA_SUBREGIAO` muda de `dict[str, str]` pra `dict[str, set[str]]`.
  Padrões pré-Etapa 8 mantêm set de 1 elemento (1:1). 4 padrões refinados
  adicionados atravessando `{core_isometrico, core_dinamico}` quando
  aplicável (`flexao_lateral` só iso — dyn vazio futuro).
- `core_isometrico`/`core_dinamico` mantidos como padrões 1:1 normais
  pra retrocompat — XLSX ainda usa esses nomes nesta fase.
- ~6 call-sites em `gerador_treino.py` adaptados pra trabalhar com set:
  build loop de `SUBREGIAO_PARA_PADROES`, sanity check `_validar_ancoras`,
  `carregar_banco` (subregião XLSX validada contra set canônico),
  `pre_alocar_rotina` (`subs_obrig` via union, `pads_obrig_sub` via `in`,
  `_aviso_slot_sem_candidato` via any cross sub × âncora).
- `PADRAO_PARA_CHIP` + `PADROES_LABELS` em `app_flask.py` ganham entries
  pros 4 novos padrões. `ORDEM_PADROES` intacto pra evitar chip vazio na
  UI até XLSX migrar.
- `_PADROES_LEGADOS` inalterado — aliases adiados pra 8.2.

### Surpresa estrutural — `_PADROES_RESERVADOS` introduzido durante a fase

Primeira tentativa adicionou os 4 padrões refinados direto em
`PADRAO_PARA_SUBREGIAO` e propagou pra `SUBREGIAO_PARA_PADROES["core_*"]`.
Decompositor de `região("core", N)` distribuiu vagas pros padrões com 0
exercícios no banco → 30+ testes quebraram com avisos "incompleta".

Solução cirúrgica: `_PADROES_RESERVADOS = {flexao_tronco, flexao_lateral,
rotacao_tronco, flexao_quadril}` filtra os 4 refinados de
`SUBREGIAO_PARA_PADROES` enquanto banco não tem exercícios. Set fica vazio
em 8.2 junto com migração XLSX.

Bug bônus: `NameError` em `_aviso_slot_sem_candidato` quando `sub_da_padrao`
foi renomeado pra `subs_do_padrao` (set) sem atualizar uma referência no
return. Helper `subregiao_aviso = sorted(subs)[0]` resolve a interface
legada do aviso.

### Gate verde

- pytest 174 passed + 13 snapshots + 1 skip
- harness 16/16 OK (números pré-Etapa 8 preservados: 4.1=12.85%, 2.3=0%)
- snapshots inalterados
- 4 padrões novos existem em `PADRAO_PARA_SUBREGIAO` com 0 exercícios

---

## Fase 8.2 — Migração estrutural + 6º NO-OP (commit `204ca49`)

### Mudanças aplicadas (commit atômico)

1. **XLSX** ([banco_exercicios.xlsx](../../../banco_exercicios.xlsx)) —
   20 células `padrao` migradas. Subregião inalterada. Distribuição final:
   `flexao_tronco` 12 ex (8 iso + 4 dyn), `flexao_lateral` 1 ex iso,
   `rotacao_tronco` 1 ex iso, `flexao_quadril` 6 ex.
2. **`gerador_treino.py`:**
   - `core_isometrico` e `core_dinamico` removidos como padrões válidos
     em `PADRAO_PARA_SUBREGIAO` (XLSX não usa mais).
   - `_PADROES_RESERVADOS` removido (era scaffolding da 8.1).
   - `_PADROES_LEGADOS` ganha aliases: `core_isometrico` → 4 refinados;
     `core_dinamico` → 2 (sem flexao_lateral nem rotacao_tronco — Russian
     Twist adiado pra Fase 4).
   - `GRUPO_MUSCULAR_PADRAO`: 4 entries refinadas todos = `"core"`.
3. **`app_flask.py`:** `ORDEM_PADROES` ganha refinados em ambas subregiões
   core.
4. **`tools/mocks/dimensoes_etapa_6.yaml`:** 5 mock_futuros atualizados
   pros padrões refinados corretos. Mock_futuros continuam só no YAML,
   não no XLSX (P2 do briefing).
5. **Snapshots regenerados** em `tests/__snapshots__/test_regressao.ambr`
   (5 snapshots failed → regenerados consistentes; mudanças refletem
   padrão refinado + reordenação por cycling).
6. **`tests/test_carga_filter.py`:** pré-condição calibrada por seed
   atualizada (seed=22 da Fase 7.4 → seed=3 da Etapa 8.2) com par "Lev.
   Terra + Remada Baixa Aberta". Contrato clínico preservado.

### Surpresa estrutural mais relevante — 6º NO-OP pós-CORE

Após aplicar todas as mudanças, harness rodou 15/16 OK + **4.1 = 21.54%
FAIL** (alvo era <15%, pré-Etapa 8 era 12.85%). Sondagem Nota #5 (Seção
1.8.4) com 8 candidatos de R-1 — nenhum fecha o alvo original.

**Causa raiz mensurada:** refator CORE muda cycling em subregião —
padrões mono-exercício (Pallof Press em `rotacao_tronco`, Prancha Lateral
em `flexao_lateral`) concentram ~25% de probabilidade em R-1 (vs 7.7%
pré-refator).

| Métrica | Pré-Etapa 8 | Pós-Etapa 8 |
|---|---|---|
| Prob Pallof em R-1 A2 | 1/13 = 7.7% | 1/4 × 1/1 = 25% (3.2×) |
| 4.1 (HIST ON) | 12.85% | 21.54% |
| Gap 4.2-4.1 | 41.19 pp | 33.65 pp |

Mecanismo HIST continua funcionando (gap mantido). Setup B C3 mantido
pra continuidade documental com Frente A (Seção 8.15.11). Predicate vira
informativo (`pct >= 0`). **Detalhes Seção 8.15.12 nova.**

### Achado metodológico — sondagem v1 (raw) vs v2 (overlay)

Primeira versão da sondagem usou banco raw (sem overlay YAML do harness)
e deu C8.4 vencedor em 14.51%. Versão corrigida (com overlay) inverteu
ranking: C8.4 sobe pra 17.82%, C8.1 vira melhor (16.49% — ainda FAIL).
**Divergiu em ranking, convergiu em conclusão.**

Diretriz registrada na Seção 8.15.12: **instrumentação de sondagem
deve replicar overlay do harness; raw XLSX subestima 4.1**.

### Achado adicional — C8.1 contraintuitivo invertido

Com overlay: +slots core *melhora* 4.1 (dilui mono-ex via mais slots).
Sem overlay: piora. Achado depende do banco concreto — overlay adiciona
4 INFRAs em flexao_quadril que diluem peso relativo dos mono-ex.

### Documentação — Seção 8.15.12 nova

Taxonomia consolidada dos 3 sub-tipos de NO-OP (Nota #5 / 1.8.4 ganha
3ª validação empírica):

1. NO-OP banco-limitado (2.3 / 8.15.10)
2. NO-OP gated por piso (4.1 pré-Etapa 8 / 8.15.11) — resolvido
3. NO-OP por viés de distribuição (4.1 pós-Etapa 8 / 8.15.12 NOVO)

### Gate verde

- pytest 174 passed + 13 snapshots regenerados consistentes + 1 skip
- harness 16/16 OK (4.1=21.54% informativo, gate de regressão preservado)
- banco real: 0 ex em core_iso/din legado; 20 distribuídos nos 4 refinados
- aliases legados validados via cenário 5.2 (única demanda direta de
  `("padrao", "core_isometrico", N)`)

---

## Fase 8.3 — Bug retrocompat `("subregiao", "core", N)` (commit `da53a5a`)

### Mudanças aplicadas

- `_SUBREGIOES_LEGADAS = {"core": ("core_isometrico", "core_dinamico")}`
  adicionado paralelo a `_PADROES_LEGADOS`.
- `_decompor_demanda_subregiao` ganha branch retrocompat: divide N entre
  filhas via Hamilton ceil/floor + cycling (`random.sample` pra ordem),
  cada filha decompõe recursivamente. N=1 → 1 filha random; N=2 → 1+1;
  N=3 → 2+1 ou 1+2 cyclado; N=4 → 2+2.
- Workaround inline em `_padroes_de_escopo` consolidado pra usar
  `_SUBREGIOES_LEGADAS`. Remove duplicação semântica.
- Teste de regressão `test_subregiao_core_legada_aloca_qtd_pedida` em
  `tests/test_problemas_etapa.py` cobrindo N=1,2,3,4 × 3 seeds.
- Seção 8.15.7 item 1 marcado ✅ fechado com ponteiro pra implementação.

### Gate verde

- pytest **175** passed (=174 + 1 novo) + 13 snapshots + 1 skip
- harness 16/16 OK (sem mudança vs 8.2)

---

## Decisões fechadas durante a etapa (não reabrir sem motivo forte)

1. **Arquitetura padrão→subregião 1:N** (P1 do briefing): `PADRAO_PARA_SUBREGIAO`
   vira `dict[str, set[str]]`. Aderente literal ao Anexo 15-quater
   ("padrões atravessando subregiões").
2. **Cadastros novos adiados pra Fase 4** (P2): Etapa 8 só toca os 20
   exercícios atuais. 5 mock_futuros permanecem só no YAML do harness.
3. **Aceitar spec do Anexo 15-quater nos 3 🟡** (P3): Roda Abdominal,
   Prancha Renegade, Abd Bicicleta → `flexao_tronco` conforme spec da
   Sessão 2 da Fase 2 (2026-05-06).
4. **Aliases via `_PADROES_LEGADOS`** (P4): templates antigos e cenários
   do harness com `core_isometrico`/`core_dinamico` continuam funcionando.
   Reescrita clínica de templates é frente separada quando user quiser.
5. **`PADRAO_PARA_SUBREGIAO[rotacao_tronco] = {core_isometrico}` only**
   (decisão durante 8.2): banco real não tem Russian Twist (dyn) até Fase
   4 cadastrar. Mapa restrito evita cycling em padrão vazio.
6. **Setup B C3 mantido + predicate 4.1 informativo** (Seção 8.15.12):
   nenhum candidato de R-1 fecha <15% pós-CORE. 4.1 declarado 6º NO-OP
   estrutural. Continuidade documental com Frente A da Seção 8.15.11.

---

## Pendências em aberto pós-Etapa 8 (não bloqueiam uso real)

### Curto prazo — Fase 4 e refator do cycling

1. **Fase 4 — cadastro real dos 5 mock_futuros no XLSX**:
   - Russian Twist (rotacao_tronco dyn) → expandir
     `PADRAO_PARA_SUBREGIAO[rotacao_tronco]` pra `{iso, dyn}` + adicionar
     `rotacao_tronco` ao alias `_PADROES_LEGADOS[core_dinamico]`.
   - 4 INFRAs (flexao_quadril dyn) → entram naturalmente, padrão já
     existe.
   - Pode reduzir piso estrutural do 4.1 (mais ex em flexao_quadril dyn
     diluem mono-exercícios) — reavaliar predicate 4.1 (volta a <15% ou
     fica informativo).

2. **Refator estrutural do cycling em subregião** (alternativa à Fase 4
   pro 6º NO-OP): mudar distribuição uniforme por padrão pra uniforme
   por exercício eliminaria o viés mono-ex pós-CORE. Mudança de algoritmo
   do gerador — fora do escopo Etapa 8 mas naturalmente convergente com
   próximas refatorações.

### Médio prazo — frentes separadas

3. **Reescrita clínica dos 4 templates legados** (Full Body, Full Body+
   Braços, Empurrar+Posterior, Puxar+Anterior) com padrões refinados
   explícitos. Permite prescrever "flexao_lateral + rotacao_tronco" em
   templates específicos. Aliases legados continuam funcionando enquanto
   isso não acontecer.

4. **Cycling determinístico de subregião** (item 5 da 8.15.7) — achado
   paralelo da Sessão 7a da Etapa 6, não investigado nesta etapa.
   Pode interagir com o viés mono-ex pós-CORE.

5. **UI Histórico exposed** (item 6 da 8.15.7) — contrato programatic
   `gerar_multiplos_treinos(historico_r1=...)` pronto, mas sem UI/
   integração SQLite. Independente da Etapa 8.

---

## Critério de "feito" — checklist

### Fase 8.1 ✅

- [x] `PADRAO_PARA_SUBREGIAO` 1:N + 4 padrões refinados
- [x] Call-sites adaptados
- [x] `PADRAO_PARA_CHIP` + `PADROES_LABELS` em `app_flask.py`
- [x] `_PADROES_RESERVADOS` filtra refinados de `SUBREGIAO_PARA_PADROES`
- [x] Snapshots inalterados
- [x] Pytest 174 + harness 16/16

### Fase 8.2 ✅

- [x] XLSX migrado (20 células `padrao`)
- [x] Aliases legados ativados em `_PADROES_LEGADOS`
- [x] `_PADROES_RESERVADOS` removido (set vazio)
- [x] `core_isometrico`/`core_dinamico` saem de `PADRAO_PARA_SUBREGIAO`
- [x] `app_flask.py` `ORDEM_PADROES` refinados
- [x] YAML mocks atualizados (5 mock_futuros + comentários)
- [x] 5 snapshots regenerados consistentes
- [x] `test_carga_filter.py` nova seed
- [x] Sondagem Nota #5 v2 (8 candidatos) + decisão 6º NO-OP
- [x] Seção 8.15.12 nova documentada
- [x] Pytest 174 + harness 16/16 (4.1 informativo)

### Fase 8.3 ✅

- [x] `_SUBREGIOES_LEGADAS` paralelo a `_PADROES_LEGADOS`
- [x] Fix em `_decompor_demanda_subregiao` (Hamilton ceil/floor + cycling)
- [x] Workaround inline em `_padroes_de_escopo` consolidado
- [x] Teste de regressão N=1,2,3,4 × 3 seeds
- [x] Seção 8.15.7 item 1 marcado ✅ fechado
- [x] Pytest 175 + harness 16/16

### Fase 8.4 ✅

- [x] Log `etapa_8.md` criado (este arquivo)
- [x] CLAUDE.md raiz atualizado com fechamento Etapa 8
- [x] Memory `project_etapa_8.md` criada
- [x] PR pra main aberto

---

## Cross-references importantes

- **`docs/refatoracao/dimensoes_proximidade.md`:**
  - Seção 8.15.12 (nova) — fechamento Fase 8.2 + 6º NO-OP + taxonomia
  - Seção 8.15.7 item 1 (atualizado) — bug retrocompat fechado em 8.3
  - Seção 8.15.7 item 2 — referência ao Anexo 15-quater (refator aplicado)
  - Seção 8.15.11 — Frente A original (4.1 pré-Etapa 8 = NO-OP gated)
  - Seção 8.15.10 — 5º NO-OP (2.3 = banco-limitado)
  - Seção 1.8.4 (Nota #5) — 3ª validação empírica

- **Código:**
  - `gerador_treino.py:32-66` — `PADRAO_PARA_SUBREGIAO` final (1:N)
  - `gerador_treino.py:426-455` — `_PADROES_LEGADOS` + `_SUBREGIOES_LEGADAS`
  - `gerador_treino.py:_decompor_demanda_subregiao` — branch retrocompat
  - `tools/calibrar_pesos_dimensoes.py:_patch_cenarios_4_x` — predicate 4.1 informativo
  - `tools/calibrar_pesos_dimensoes.py:_gerar_sessoes_r1_variante_a` — Setup B C3 mantido

- **Testes:**
  - `tests/test_problemas_etapa.py::test_subregiao_core_legada_aloca_qtd_pedida`
  - `tests/test_carga_filter.py::test_filtro_carga_realmente_dissolve_par_conhecido` (seed=3)
