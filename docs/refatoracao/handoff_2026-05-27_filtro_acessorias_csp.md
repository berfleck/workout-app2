# Handoff — Filtro de subregiões acessórias no CSP (faceta panturrilha do Achado 1)

**Sessão**: próxima após encerramento da frente S-R1 (mergeada em
main 2026-05-27, commit `22ff4a9`).

**Branch base**: a partir de `main`. Branch sugerida:
`fix-filtro-acessorias-csp`. Disciplina de merge se aplica.

**Bloco**: 4 do roadmap CSP — continuação do Achado 1 da auditoria
2026-05-26. A frente S-R1 anterior fechou a **faceta de simetria
T1↔T2** (split repetido entre treinos). Esta frente fecha a **faceta
de panturrilha** (acessórias entrando em demandas pequenas).

---

## 1. Por que esta sessão existe

### O bug

Durante a frente S-R1 (2026-05-27), descobri que o CSP **NÃO herdou o
filtro pré-Hamilton** do motor antigo (`gerador_treino.
_decompor_demanda_regiao` linha 2989-2996), que removia subregiões
acessórias quando `qtd <= 2 * n_obrig`.

No motor antigo, em `regiao lower(3)`:
- `n_obrig=2` (perna_anterior, perna_posterior).
- threshold `2*n_obrig=4`.
- `qtd=3 <= 4` → panturrilha (`obrigatoria=False`) é **removida** do
  pool antes do Hamilton.
- Resultado: panturrilha não aparece em lower(3) — comportamento
  desejado por Bernardo.

No CSP atual (`gerador_csp.py:642-646`):
```python
if nivel == "regiao" and escopo in ANCORAS_POR_REGIAO:
    subs_ancora_h_a0 = {
        a["subregiao"] for a in ANCORAS_POR_REGIAO[escopo]
    }
```

Pega **TODAS** as subregiões declaradas em `ANCORAS_POR_REGIAO[lower]`
— incluindo panturrilha. Ignora `obrigatoria` e ignora qualquer regra
de tamanho. Resultado empírico: panturrilha aparece em 60-80% das
rotinas `lower(3)` (sondagem N=5 do S-R1).

### O equívoco anterior

Quando Bernardo decidiu "(c) Aceitar status quo" na abertura da frente
S-R1, eu (Claude) descrevi o status quo do MOTOR ANTIGO (com filtro),
mas o que está em produção é o CSP (sem filtro). Bernardo aceitou o
status quo achando que panturrilha não aparecia; na verdade aparece.

Esta sessão **reverte** essa parte da decisão e implementa o
comportamento que ele realmente quer:
- `lower(3)`: panturrilha NÃO aparece.
- `lower(10)`: panturrilha pode aparecer.
- Generaliza pra outras acessórias (adutores, bracos, etc).

---

## 2. Leitura preparatória (na ordem)

1. **`docs/refatoracao/norte.md`** — princípios. Seções 3
   (motivação refator), 4 (anti-padrões: centralidade curada, não
   emergente), 5 (trade-offs).
2. **`docs/refatoracao/auditorias/2026-05-26.md`** Achado 1 — status
   atual (✅ parcial pós-S-R1) e o que ainda falta (panturrilha).
3. **`docs/refatoracao/logs/mvp_sr1_cross_treino.md`** — log da
   frente anterior. Seção "Achados" item 2 fala da descoberta do
   60-80% panturrilha em sondagem.
4. **`gerador_treino.py:142-157`** — `ANCORAS_POR_REGIAO` atual.
   Schema das âncoras: `{subregiao, peso, obrigatoria}`.
5. **`gerador_treino.py:2989-2996`** — filtro `qtd <= 2*n_obrig`
   no motor antigo (lógica a ser portada/refatorada).
6. **`gerador_csp.py:642-646`** — bloco que monta `subs_ancora_h_a0`
   no CSP (onde a mudança vai).
7. **`gerador_csp.py:618-672`** — bloco maior de pool_default por
   slot pra contexto.

---

## 3. Decisão arquitetural já fechada — Opção B

Avaliei 4 opções com Bernardo (2026-05-27). Decisão arquitetural
fechada: **Opção B — campo declarativo `min_qtd_demanda` por
subregião acessória em `ANCORAS_POR_REGIAO`**.

### As 4 opções (NÃO reabrir sem motivo forte)

| Opção | Descrição | Veredito |
|---|---|---|
| A | Portar literal a fórmula `qtd <= 2 * n_obrig` do antigo | ❌ Número mágico arbitrário (`2x`), patch de cascata, anti-padrão norte §7 |
| **B** | **Campo `min_qtd_demanda` por sub em ANCORAS_POR_REGIAO** | **✅ Declarativo, curado, generaliza, alinhado com norte §4-§5** |
| C | Constraint hard no CSP (BoolVar + count == 0 quando qtd ≤ K) | ❌ Mais caro computacionalmente, sem benefício vs (B) |
| D | Mudar `obrigatoria=True` mas tornar condicional | ❌ Conflita com semântica de "obrigatória" |

### Por que B venceu

1. **Declarativo** (norte §4 e §5). Cada acessória declara
   explicitamente o ponto em que entra.
2. **Curado, não emergente**. Bernardo decide caso a caso. Não há
   fórmula global enviesando.
3. **Generaliza**. Funciona pra panturrilha, adutores, bracos, ou
   qualquer acessória futura sem mexer em código.
4. **Não conflita com S-R1/H-A0/S-A1**. Filtro upstream no pool, igual
   ao H-A0 atual.
5. **Implementação mínima**. 5 linhas no CSP + 1 campo opcional no
   dict. Backwards-compatible com âncoras existentes.

---

## 4. Decisões clínicas a fechar (perguntar a Bernardo via texto livre)

Bernardo precisa responder na **abertura da sessão**. As 3 perguntas
são clínicas, abertas (não binárias), então **texto livre** é o
formato (não AskUserQuestion — ver [[feedback-askquestion-exploratorio]]).

### 4.1 Threshold de panturrilha em lower

Bernardo já indicou indiretamente: "se eu selecionasse lower(10), por
exemplo, não me importaria se app colocasse panturrilha no treino".

Sugestão de partida: `min_qtd_demanda=5` (panturrilha entra em
`lower(5+)`). Pode escalar pra 6 se ele quiser mais conservador.

### 4.2 Adutores em lower

Hoje **adutores não é âncora declarada** em `ANCORAS_POR_REGIAO['lower']`
(só ant, post, panturrilha). Adutores caem no fallback de cycling.

Mas em demanda `regiao lower`, adutores podem aparecer via cycling do
H-A0. Pergunta: adicionar adutores como âncora acessória declarada
com `min_qtd_demanda=X`? Se sim, qual X?

Alternativa: deixar como está (sem declarar como âncora), e o filtro
upstream `subs_ancora_h_a0` automaticamente exclui adutores. Mas isso
significa que adutores **nunca aparecem** em demanda região (só em
demanda subregião explícita).

### 4.3 Bracos em upper

Hoje `ANCORAS_POR_REGIAO['upper']` tem peito, costas, ombro — todas
obrigatórias. **Bracos não está declarado.** Em demanda `regiao upper`,
bracos não aparece (pelo mesmo filtro upstream).

Pergunta: bracos faz sentido como acessória declarável em upper?
Em upper(6+) bracos seria benéfico? Ou bracos só aparece quando user
pede demanda subregião explícita `bracos(N)`?

---

## 5. Spec técnica (rascunho de implementação)

### 5.1 Mudança em `gerador_treino.py:142-157` (schema)

Adicionar `min_qtd_demanda` opcional nas acessórias. Exemplo (placeholder
até Bernardo responder §4):

```python
ANCORAS_POR_REGIAO: dict[str, list[dict]] = {
    "upper": [
        {"subregiao": "peito",  "peso": 2, "obrigatoria": True},
        {"subregiao": "costas", "peso": 2, "obrigatoria": True},
        {"subregiao": "ombro",  "peso": 1, "obrigatoria": True},
        # opcional, dep. §4.3:
        # {"subregiao": "bracos", "peso": 1, "obrigatoria": False, "min_qtd_demanda": 6},
    ],
    "lower": [
        {"subregiao": "perna_anterior",  "peso": 2, "obrigatoria": True},
        {"subregiao": "perna_posterior", "peso": 2, "obrigatoria": True},
        {"subregiao": "panturrilha",     "peso": 1, "obrigatoria": False,
         "min_qtd_demanda": 5},  # dep. §4.1
        # opcional, dep. §4.2:
        # {"subregiao": "adutores", "peso": 1, "obrigatoria": False, "min_qtd_demanda": 6},
    ],
    "core": [
        {"subregiao": "core_dinamico",   "peso": 1, "obrigatoria": False},
        {"subregiao": "core_isometrico", "peso": 1, "obrigatoria": False},
    ],
}
```

**Decisão importante sobre core**: as duas subs de core são `obrigatoria=False`
hoje. Esse filtro atual em CSP DEPOIS desta mudança vai exigir cuidado: se
não houver obrigatórias E não houver `min_qtd_demanda`, o filtro
`if a["obrigatoria"] or qtd >= a.get("min_qtd_demanda", 1)` precisa
funcionar (default `1` faz acessória sempre entrar — preserva core).
Validar manualmente que core não regride.

### 5.2 Mudança em `gerador_csp.py:642-646`

Antes:
```python
subs_ancora_h_a0: set[str] = set()
if nivel == "regiao" and escopo in ANCORAS_POR_REGIAO:
    subs_ancora_h_a0 = {
        a["subregiao"] for a in ANCORAS_POR_REGIAO[escopo]
    }
```

Depois:
```python
subs_ancora_h_a0: set[str] = set()
if nivel == "regiao" and escopo in ANCORAS_POR_REGIAO:
    subs_ancora_h_a0 = {
        a["subregiao"] for a in ANCORAS_POR_REGIAO[escopo]
        if a["obrigatoria"] or qtd >= a.get("min_qtd_demanda", 1)
    }
```

5 linhas modificadas. Backwards-compatible: âncoras sem
`min_qtd_demanda` (todas as obrigatórias atuais + core acessória)
preservam comportamento — default 1 faz acessória sempre entrar (se
não for obrigatória).

### 5.3 O que NÃO mexer

- **`gerador_treino.py:2989-2996`** (motor antigo) — antigo vive até
  ser substituído (regra do norte §3). Continua com a fórmula
  `qtd <= 2 * n_obrig`. Inconsistência intencional: o antigo só roda
  em harness e testes legados; produção é CSP.
- **Hamilton** (`gerador_treino.py:355` `tiebreak_key`). Já tem
  `random.random()`; sem mudanças.
- **H-A0, H-A1, S-A1, S-R1, S-B5** — todas as constraints atuais
  preservadas. Mudança é só no pool upstream.

### 5.4 Testes novos

Pelo menos 3 testes em `tests/test_csp_filtro_acessorias.py` (novo):

1. **`test_panturrilha_filtrada_em_lower_3`** — `regiao lower(3) × 1T`
   N runs (~5). 0% panturrilha presente.
2. **`test_panturrilha_aparece_em_lower_5plus`** — `regiao lower(5)
   × 1T` N runs. Panturrilha aparece em pelo menos algumas (>20%).
3. **`test_core_nao_regride`** — `regiao core(2) × 1T`. Ambas as
   subs (core_iso e core_din) podem aparecer. Sanity check do
   default `min_qtd_demanda=1`.

---

## 6. Validação esperada (gate de fechamento)

### 6.1 Sondagem comparativa pré × pós

Reusar `tools/sondar_sr1_cross_treino.py` que **já existe** (criado na
frente S-R1). Métrica `pct_pant_presente` já está implementada. Rodar:

```bash
# PRE (em main pós-S-R1, sem mudança ainda):
python tools/sondar_sr1_cross_treino.py --peso 4 --n 10 \
  --out docs/refatoracao/logs/filtro_acessorias_pre.json

# POS (após implementar):
python tools/sondar_sr1_cross_treino.py --peso 4 --n 10 \
  --out docs/refatoracao/logs/filtro_acessorias_pos.json
```

Métricas esperadas em Full Body 2T região (`regiao lower(3)`):
- `pct_pant_presente`: ~80% → **0%** ✅
- `pct_split_t1_eq_t2`: 0% → 0% (preservado pela S-R1)
- p50 tempo: sem regressão >2x

**Adicionar config nova de teste em lower(5+)**: extender o sondar com
`("regiao", "lower", 5)` pra confirmar que panturrilha entra. Ou
deixar como verificação manual de pytest (§5.4 item 2).

### 6.2 Pytest

Baseline 360 + 3 novos = 363. Snapshots podem regenerar (mudanças
benignas — esperado em rotinas que tinham pant em lower(3)).

### 6.3 Harness 16/16

Sem regressão funcional.

### 6.4 Smoke E2E browser

POST `/gerar` Full Body 2T região com Aluno Teste. Verificar
**visualmente** que panturrilha sumiu dos 2 treinos (vs S-R1 onde
apareceu em T2). Esperado: T1 e T2 só com ant e post lower.

---

## 7. Arquivos a mexer

- `gerador_treino.py` — 1-3 entradas em `ANCORAS_POR_REGIAO` (dep
  §4.1, §4.2, §4.3). ~3-10 linhas.
- `gerador_csp.py` — filtro `subs_ancora_h_a0` em `:642-646`.
  ~5 linhas.
- `tests/test_csp_filtro_acessorias.py` — novo, 3-4 testes.
  ~80-120 linhas.
- `tools/sondar_sr1_cross_treino.py` — opcional: estender com
  config `lower(5)` pra cobertura. ~5 linhas.
- `docs/refatoracao/logs/filtro_acessorias_{pre,pos}.json` — snapshots.
- `docs/refatoracao/logs/mvp_filtro_acessorias_csp.md` — log da
  frente. ~150 linhas.
- `docs/refatoracao/roadmap_csp.md` — anotar item ✅
  (`panturrilha.obrigatoria=False` muda de "🟦 status quo aceito"
  para "✅ resolvido via filtro declarativo").
- `docs/refatoracao/auditorias/2026-05-26.md` — Achado 1 status
  atualizado: faceta panturrilha ✅, achado **totalmente fechado**.
- `MEMORY.md` — 1 linha apontando pro memory file novo.

---

## 8. Restrições / não-fazer

- **NÃO mergear em main sem aprovação explícita do Bernardo**
  (disciplina de merge — 1 branch ativa por vez).
- **NÃO usar `--no-verify`** ou flags que pulem hooks.
- **Commit seletivo** (`git add <arquivo>`, NUNCA `-A`).
- **NÃO usar AskUserQuestion** pras decisões clínicas §4 — texto livre
  com sugestões e contraponto é o padrão pra tópicos clínicos abertos
  (ver [[feedback-askquestion-exploratorio]]).
- **NÃO mexer no motor antigo** `gerador_treino._decompor_demanda_regiao`
  — regra do norte §3-§4. Antigo continua com fórmula `2*n_obrig`,
  inconsistência intencional (só roda em harness e testes legados).
- **Validar core não regride** — `ANCORAS_POR_REGIAO['core']` tem
  ambas subs `obrigatoria=False`. Default `min_qtd_demanda=1` deve
  preservar comportamento. Teste explícito.

---

## 9. Pendências NÃO incluídas nesta frente

- **🟡 Achado 2 da auditoria 2026-05-26 — S-E1 proximidade biomecânica
  cross-treino**. Continua próxima depois desta. Reusa 3 dimensões
  cadastradas no XLSX desde Fase 4 + pesos calibrados em
  `arquivo/era_v4_greedy_incremental/dimensoes_proximidade.md`
  (referência viva, exceção do CLAUDE.md). Ver §9 do
  `handoff_2026-05-27_achado_1_distribuicao_lower.md` pra detalhes.

- **Gate de avaliação clínica semântica** (Bloco 4) — pré-requisito
  do Bloco 5.

- **Otimização da suíte de testes** (relato Bernardo 2026-05-27 — testes
  "levam horas"). Pytest-xdist, fixtures session-scoped, mark slow.
  Frente própria, fora deste escopo.

---

## 10. Como abrir a sessão

Primeira mensagem da sessão deve:

1. **Confirmar leitura**: norte.md + auditoria 2026-05-26 (Achado 1)
   + log `mvp_sr1_cross_treino.md` + `gerador_treino.py:142-157`
   (ANCORAS_POR_REGIAO) + `:2989-2996` (filtro antigo) +
   `gerador_csp.py:642-646` (filtro upstream do H-A0 — onde a mudança
   vai).

2. **Confirmar entendimento** da Opção B (decisão arquitetural já
   fechada, §3) e das 3 perguntas clínicas em aberto (§4.1, §4.2,
   §4.3).

3. **Texto livre** pra coletar as 3 decisões clínicas do Bernardo.
   Sugestões iniciais (não obrigam):
   - panturrilha em lower: `min_qtd_demanda=5`
   - adutores em lower: declarar como acessória `min_qtd_demanda=6`?
     ou deixar fora?
   - bracos em upper: declarar como acessória `min_qtd_demanda=6`?
     ou deixar fora?

4. **Rodar sondagem PRÉ** em main ANTES da implementação. Persistir
   `logs/filtro_acessorias_pre.json`.

5. **Implementar na ordem** §5.1 → §5.2 → §5.4.

6. **Rodar sondagem PÓS** com mesma config. Comparar.

7. **Gate**: pytest + harness + smoke E2E browser.

8. **Atualizar docs**: log + roadmap + auditoria + MEMORY.md.

9. **Commit seletivo + push** + aguardar aprovação Bernardo pra merge FF.

**Tempo estimado pós-cortes (S-R1 padrão)**: ~30-45min total
(sondagem ~3min pré + ~3min pós + implementação ~10min + testes
~5min + smoke ~3min + docs ~10min).

---

## 11. Contexto importante da sessão anterior (S-R1, 2026-05-27)

Mergeada em main commit `22ff4a9`. Branch `achado-1-distribuicao-lower`
fechou após push + merge FF.

**O que entregou**:
- `splits_iguais` BoolVar por par (t1, t2) + região R no CSP. Penalty
  `peso_sr1=4` quando T1==T2 em todas as subs de R. Default ON.
- `subregiao_idx[s]` IntVar (espelho do `regiao_idx`) — gancho pra
  futuras constraints. Esta frente NÃO usa, mas está disponível.
- Full Body 2T região: 40% → 0% splits T1==T2.

**O que descobriu (motivo desta frente)**:
- Sondagem N=5 pós-S-R1: panturrilha aparece em 60-80% das rotinas
  lower(3). Bernardo (auditoria original N=1+1) tinha reportado 0%
  — era azar de seed.
- Investigação: CSP não herdou o filtro pré-Hamilton do motor antigo.
- Bernardo verbalizou intuição clínica: "lower(3) sem pant; lower(10)
  com pant OK".
- Reabriu faceta panturrilha do Achado 1 — esta frente fecha.

**O que aprender com a S-R1 (lição metodológica)**:
A spec original do S-R1 propunha modelagem matemática que era
**clinicamente oposta** ao objetivo (minimizar `|diff|` força T1==T2,
espelho matemático). Sondagem pós com fórmula errada confirmou:
40% → 100% (piorou). Correção: penalizar `splits_iguais` BoolVar.
**Lição**: spec matemática precisa ser validada com sondagem
ANTES de assumir que está clinicamente correta. Aplica também aqui
— rodar sondagem pré ANTES de implementar pra ter baseline empírico
e confirmar o que o motor está fazendo hoje.
