# Log — Filtro de subregiões acessórias no CSP (faceta panturrilha do Achado 1)

**Data**: 2026-05-27
**Branch**: `fix-filtro-acessorias-csp` (a partir de `main`, após merge S-R1 commit `22ff4a9`)
**Bloco**: 4 do roadmap CSP — fecha **faceta panturrilha** do Achado 1
da auditoria 2026-05-26. A faceta de **simetria T1↔T2** foi fechada em
sessão anterior (S-R1, mergeada em main 2026-05-27).

**Arquivos modificados**:
- `gerador_treino.py` — `ANCORAS_POR_REGIAO['lower']`: entrada de
  panturrilha removida (4 linhas → 3 linhas + comentário explicativo).
- `tests/test_csp_filtro_acessorias.py` — novo arquivo, 4 testes
  cobrindo a fix em CSP (lower 3/5/6 sem pant + subregião explícita
  preservada + core não regride).
- `tests/test_pre_alocacao.py` — 3 testes legados refatorados pra
  refletir novo comportamento do motor antigo em lower(5+) e lower(6).
- `tests/test_ancoras.py` — 2 testes legados refatorados (Hamilton
  helper sem panturrilha).
- `tests/test_ha0_ancoras_regiao_csp.py` — docstring atualizada em
  `test_lower_3_cobre_perna_anterior_e_posterior` (sem mudança de
  assertion).
- `docs/refatoracao/logs/filtro_acessorias_pre.json` — sondagem PRÉ
  N=10 em main (peso_sr1=4).
- `docs/refatoracao/logs/filtro_acessorias_pos.json` — sondagem PÓS
  com mesma config.

**Status**: ✅ concluída. Aguarda aprovação do Bernardo para merge FF em
`main` (disciplina de merge do roadmap exige confirmação explícita).

---

## Objetivo

Fechar a **faceta panturrilha** do Achado 1 da auditoria 2026-05-26.
Em rotinas com `regiao lower(3)`, panturrilha aparecia em ~70% das
rotinas (sondagem N=10 pré-fix). Decisão clínica de Bernardo
(2026-05-27): panturrilha tem o mesmo tratamento de adutores — só
entra em demanda subregião explícita, nunca em demanda região
`lower(N)` (qualquer N).

Causa estrutural: o CSP **não herdou o filtro pré-Hamilton** do motor
antigo (`gerador_treino._decompor_demanda_regiao:2989-2996`), que
removia subregiões acessórias quando `qtd <= 2 * n_obrig`. O CSP só
considera `obrigatoria` na declaração da âncora — todas as âncoras
declaradas (incluindo acessórias) entram no pool de subregiões
permitidas em demanda região.

## Decisões fechadas

### Decisão arquitetural — caminho B-mínima (remoção declarativa)

O handoff propunha **Opção B — campo `min_qtd_demanda` por subregião
acessória** em `ANCORAS_POR_REGIAO`. A justificativa era declarativa:
"panturrilha entra em `lower(5+)`, adutores em `lower(6+)`, etc".

Bernardo (2026-05-27, abertura da sessão) revogou o pressuposto:
preferiu panturrilha **sempre oculta** em demanda região, **igual
adutores**. Isso transforma a Opção B (mecanismo declarativo de
threshold) em overengineering — sem caso de uso ativo.

**Caminho final — B-mínima**: remover a entrada de panturrilha de
`ANCORAS_POR_REGIAO['lower']`. O filtro upstream `subs_ancora_h_a0`
em `gerador_csp.py:642-646` já bania subregiões não declaradas; ao
tirar panturrilha do dict, ela passa automaticamente a ser banida em
demanda região, sem nova lógica nem novo campo.

### Trade-off discutido com Bernardo

A "1 linha de diff" prometida na abertura virou "1 linha + 4 testes
legados refatorados" — `ANCORAS_POR_REGIAO` é compartilhado entre
motor antigo e CSP, e o antigo tinha testes assertando que panturrilha
entrava em lower(5) e lower(6) via Hamilton 2:2:1.

Duas opções apresentadas:
- **(A) Remover do dict** + atualizar testes legados como mudança
  intencional. Motor antigo morre em frente futura, comportamento
  alinhado entre antigo e CSP, sem campo morto.
- **(B) `min_qtd_demanda=999`** só no CSP. Motor antigo intocado mas
  introduz infra (campo + filtro) com 1 único uso ativo ("nunca").

Bernardo escolheu **(A)**. Norte §3 (refator declarativo, sem campo
morto) e §4 (decisão curada, não emergente) endossam.

### 4.2 Adutores em lower — manter status quo

Adutores **NÃO está declarada** em `ANCORAS_POR_REGIAO['lower']` há
muito tempo (decisão Etapa 3 do refator). Continua fora. Confirmado.

### 4.3 Bracos em upper — manter status quo

Bracos **NÃO está declarado** em `ANCORAS_POR_REGIAO['upper']`.
Continua fora. Bracos só aparece em demanda subregião explícita.
Confirmado.

---

## Mudança técnica

### `gerador_treino.py` (linha 148-152)

**Antes**:
```python
"lower": [
    {"subregiao": "perna_anterior",  "peso": 2, "obrigatoria": True},
    {"subregiao": "perna_posterior", "peso": 2, "obrigatoria": True},
    {"subregiao": "panturrilha",     "peso": 1, "obrigatoria": False},
],
```

**Depois**:
```python
"lower": [
    {"subregiao": "perna_anterior",  "peso": 2, "obrigatoria": True},
    {"subregiao": "perna_posterior", "peso": 2, "obrigatoria": True},
    # panturrilha intencionalmente fora — decisão clínica 2026-05-27:
    # demanda região lower nunca traz panturrilha; user pede via
    # demanda subregião explícita. Mesmo tratamento de adutores.
],
```

### Impacto no motor antigo (`gerador_treino._decompor_demanda_regiao`)

Antes: em lower(5+), Hamilton 2:2:1 incluía 1 vaga de panturrilha.
Depois: em qualquer lower(N), Hamilton 2:2 sobre as 2 obrigatórias.
Em lower(N par), 50/50 ant/post; em lower(N ímpar), tie-break decide.

Mudança intencional do comportamento do antigo, alinhada com CSP.
Antigo só roda em testes legados e harness comparativo; produção é
CSP. Norte §3 endossa essa convergência.

### Testes legados afetados (refatorados, não removidos)

1. `test_decompor_lower_5_acessoria_entra` →
   `test_decompor_lower_5_sem_panturrilha`. Antes: `{ant: 2, post: 2,
   panturrilha: 1}`. Depois: `{ant: 2|3, post: 3|2}` (Hamilton sobre 2
   obrigatórias).
2. `test_decompor_lower_6_proporcional`. Antes: `{ant: 3|2, post: 2|3,
   panturrilha: 1}`. Depois: `{ant: 3, post: 3}`.
3. `test_pre_alocar_lower_6_proporcional`. Mesma refatoração no pré-
   alocador.
4. `test_quotas_de_regiao_lower_2_um_de_cada_essencial`. Docstring +
   comentários atualizados (resultado idêntico: `{ant: 1, post: 1}`).
5. `test_quotas_de_regiao_lower_5_panturrilha_pode_aparecer` →
   `test_quotas_de_regiao_lower_5_sem_panturrilha`. Hamilton 5×2:2 →
   tie-break decide qual ganha o +1.
6. `test_lower_3_cobre_perna_anterior_e_posterior` (CSP). Docstring
   atualizada — assertion já compatível.

---

## Testes novos

`tests/test_csp_filtro_acessorias.py` (4 testes):

1. **`test_panturrilha_filtrada_em_lower_3`**. N=10 seeds, lower(3) ×
   1T. 0/10 ocorrências de panturrilha (era ~70% pré-fix em sondagem).
2. **`test_panturrilha_filtrada_em_lower_5_e_6`**. N=5×2 seeds em
   lower(5) e lower(6). 0 ocorrências em ambas — confirma que o filtro
   não depende de tamanho de demanda.
3. **`test_panturrilha_aparece_em_subregiao_explicita`**.
   `subregiao panturrilha(1)` × 3 seeds. Confirma que demanda
   subregião explícita continua funcionando (sanity check de escopo
   da fix).
4. **`test_core_nao_regride`**. `regiao core(2)` × 15 seeds. Pool de
   core continua funcionando; nenhuma sub fora de core entra. NOTA:
   o teste NÃO afirma que ambas core_iso e core_din aparecem
   distributivamente — viés pré-existente (sempre core_din).

---

## Sondagem PRÉ × PÓS

`tools/sondar_sr1_cross_treino.py --peso 4 --n 10` em Full Body 2T
região (3 demandas × 2 treinos, exatamente o setup da auditoria
2026-05-26).

| Métrica                | PRÉ (main, peso_sr1=4) | PÓS (fix, peso_sr1=4) | Δ        |
|------------------------|------------------------|------------------------|----------|
| `pct_pant_presente`    | 70.0%                  | **0.0%** ✅            | -70 pp   |
| `pct_vol_lower_assim`  | 70.0%                  | 0.0%                   | -70 pp   |
| `pct_split_t1_eq_t2`   | 0.0%                   | 0.0%                   | 0        |
| `tempo_p50_s`          | 0.82s                  | 0.69s                  | -0.13s   |

**Observações**:
- Métrica primária (`pct_pant_presente`) atingiu alvo 0% conforme spec.
- `pct_vol_lower_assim` (ant != post em volume de rotina) caiu de 70%
  pra 0% como efeito colateral positivo — sem panturrilha "roubando"
  uma vaga, o split sempre é {ant: 3, post: 3}.
- S-R1 (`pct_split_t1_eq_t2`) preservada em 0% — a fix não regride
  a faceta de simetria.
- Tempo p50 melhorou levemente (-16%) — menos pool = menos branches
  no solver.

Snapshots persistidos em `docs/refatoracao/logs/filtro_acessorias_pre.json`
e `filtro_acessorias_pos.json` para auditoria futura.

---

## Gate de fechamento

- ✅ Sondagem PRÉ × PÓS: `pct_pant_presente` 70% → 0%
- ✅ Pytest: 364 passed + 1 skipped (era 360 pré-frente, +4 testes
  novos em `test_csp_filtro_acessorias.py`)
- ✅ 13 snapshots verdes sem regeneração (mudança não afeta rotinas
  snapshot-protegidas)
- ✅ Harness 16/16 OK (sem regressão, 4.1 e 4.2 mantidos em
  17.07%/36.79% — 6º NO-OP da Seção 8.15.12)
- ✅ Smoke E2E browser `/gerar` Full Body 2T região × 2T: 16 exs em
  2 treinos, ZERO panturrilha, volume lower simétrico (3+3 cada
  rotina). Treinos compostos só de perna_anterior + perna_posterior
  no lower; demais demandas (upper, core) intactas.

---

## Pendências NÃO incluídas nesta frente

- **🟡 Achado 2 da auditoria 2026-05-26 — S-E1 proximidade biomecânica
  cross-treino**. Próxima frente do Bloco 4. Reusa 3 dimensões
  cadastradas no XLSX desde Fase 4 + pesos calibrados em
  `arquivo/era_v4_greedy_incremental/dimensoes_proximidade.md`.

- **Gate de avaliação clínica semântica** (Bloco 4) — pré-requisito
  do Bloco 5.

- **Otimização da suíte de testes** — pytest-xdist, fixtures
  session-scoped, mark slow. Frente própria.

- **Mecanismo declarativo `min_qtd_demanda`** — descartado nesta
  frente por YAGNI. Pode ressurgir se Bernardo decidir reativar
  panturrilha/adutores/bracos em demanda região de alto volume.
  Caminho de reintrodução documentado no handoff
  `handoff_2026-05-27_filtro_acessorias_csp.md` §5.

---

## Lições aprendidas

1. **Norte §3 paga dividendos**: a fix mais simples ("remover") só
   foi viável porque o filtro upstream `subs_ancora_h_a0` no CSP já
   era declarativo. Sem essa infra anterior (Frente E.1 + Micro H-A0),
   teríamos que escrever lógica de filtro nova. Mecanismos declarativos
   compostam.
2. **Inventário de impacto antes de prometer "1 linha"**: a remoção
   pareceu trivial até descobrir que 4 testes legados quebravam.
   Lição: antes de quotar tamanho de diff, grep o nome do símbolo no
   diretório `tests/`.
3. **YAGNI sobre mecanismo declarativo**: o handoff propôs uma infra
   (`min_qtd_demanda`) cuja única instância de uso virou "999 =
   nunca" após decisão clínica. Aceitar overengineering pelo apelo
   declarativo é anti-padrão (norte §4 — centralidade emergente).
4. **Spec de handoff vs realidade clínica**: o handoff assumia
   pressupostos clínicos ("Bernardo já indicou panturrilha em lower(10+)
   tudo bem") que podiam mudar na verbalização da abertura. Bernardo
   foi mais conservador do que o handoff antecipava. Validar pressupostos
   antes de implementar (alinhado com
   [[feedback-reavaliar-dx-antes-codar]]).
