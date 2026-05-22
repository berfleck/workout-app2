# Sessão 2026-05-18 — fix viés de tie-break em `calcular_quotas` + auditoria

Branch: `fix/calcular-quotas-tiebreak` (a partir de `main`).

Continuação direta da sessão `sessao_2026-05-18_cadastros_e_tiebreaker.md`
— mesmo dia, mesma patologia conceitual (tie-break determinístico em
empate aleatorizável), camada diferente do motor.

---

## 1. Diagnóstico — handoff recebido

Handoff: `docs/refatoracao/logs/handoff_calcular_quotas_tiebreak.md`.

`calcular_quotas` (gerador_treino.py ~285-293) distribui vagas entre
âncoras via Hamilton's Largest Remainder. Quando duas âncoras empatam
em (obrigatoriedade, peso, resto), o tie-break atual usa `idx` (ordem
da lista `ANCORAS_*`). Resultado: viés determinístico em todas as
distribuições com empate:

- peito sempre vence costas em `upper`
- perna_anterior sempre vence perna_posterior em `lower`
- core_dinamico sempre vence core_isometrico em `core`
- remadas sempre vencem puxadas em `costas` (subregião)

Este é o **3º caso da mesma patologia descoberta em 24h**:

1. Tag `plano_corporal=NaN` em Apoios — fix por cadastro de dado
2. `_selecionar_cand_score_aware` — `sort(key=score)` estável, empate por
   ordem do XLSX → fix com `key=(-score, random.random())`
3. **Este fix** — Hamilton em `calcular_quotas`, empate por `idx` =
   ordem da lista `ANCORAS_*` → fix com `random.random()` no tie-break

Caso 3 explica retroativamente o viés posicional T1 vs T2 documentado
em `docs/refatoracao/logs/analise_vies_upper.md` Q4 (peito 25% T1, 50%
T2, χ²=533, zero variação em 1000 iters).

---

## 2. Test-first — confirmação do viés

Teste já entregue pelo handoff e aplicado pré-fix:
`tests/test_calcular_quotas_vies.py`. 4 casos parametrizados (upper N=4,
lower N=4, core N=3, costas-sub N=3), 2000 seeds cada, asserindo ratio
~50% (entre 45% e 55%) entre as duas âncoras empatadas.

Pré-fix: todos os 4 casos com **ratio = 100%** — a primeira âncora da
lista vence sempre, exatamente como previsto.

---

## 3. Fix principal — 1 linha em `calcular_quotas`

`gerador_treino.py` ~linhas 285-293:

```python
def tiebreak_key(p):
    idx, a, ideal, floor = p
    resto = ideal - floor
    return (
        -resto,                          # maior resto primeiro
        0 if a.get("obrigatoria") else 1,  # obrig primeiro
        -a["peso"],                      # peso maior primeiro
        random.random(),                 # sorteio (era `idx`)
    )
```

Critérios anteriores (obrigatória, peso) preservados — sorteio só
dispara em empate triplo.

Pós-fix: `tests/test_calcular_quotas_vies.py` 4/4 OK (ratios 49-51%
em todos os casos).

---

## 4. Auditoria de outros tie-breaks — 3 patologias novas

Handoff opcional pediu "auditoria de outros tie-breaks na mesma
patologia". Critério: variância zero ou quase-zero em sondagem N≥500
no caso isolado.

### 4.1 `_distribuir_quotas_entre_treinos` — Bresenham (linha 453)

```python
chaves_ord = sorted(quotas_global.keys(), key=lambda k: (-quotas_global[k], k))
```

Tie-break alfabético na ordenação do Bresenham. Sondagem isolada:
`quotas={peito:1, costas:1, ombro:1}`, `vagas=[1,1,1]`, 2000 seeds →
**costas 100% T1, ombro 100% T2, peito 100% T3**. Variância zero.

Mesma patologia. Fix:

```python
chaves_ord = sorted(quotas_global.keys(), key=lambda k: (-quotas_global[k], random.random()))
```

Pós-fix: distribuição cai pra ~33/33/33 nas 3 posições.

### 4.2 `_decompor_demanda_subregiao` — doador (linha 2750)

```python
p_doador = max(quotas, key=lambda k: (quotas[k], k))
```

Quando um padrão obrigatório recebe 0 vagas, doa de outro com a
maior quota. Empate em `quotas[k]` resolvido alfabeticamente.
Sondagem com `quotas={peito:2, costas:2, ombro:1}`: peito sempre
vence (porque max compara strings e 'p' > 'c').

Fix:

```python
p_doador = max(quotas, key=lambda k: (quotas[k], random.random()))
```

### 4.3 `_decompor_demanda_regiao` — doador (linha 2854)

Mesma estrutura, mesma patologia, mesmo fix. Aplicado idêntico.

---

## 5. Patologia residual descoberta e consertada na mesma sessão — offset inicial do Bresenham

Sondagem real `cfg=upper(3) x 2 treinos`, 1000 iters após os 4 fixes
de tie-break, contando ocorrências por subregião em T1 vs T2:

| Subregião | T1 | T2 |
|---|---|---|
| peito | 60.4% | 39.6% |
| costas | 59.6% | 40.4% |
| **ombro** | **0.0%** | **100.0%** |

Origem: o algoritmo Bresenham é determinístico no cycling estrutural,
não no tie-break. Quando `quotas_reg={peito:2, costas:3, ombro:1}` e
`vagas=[3,3]`, o offset acumulado após processar peito+costas é par,
e ombro (qtd=1) sempre cai em T2 via `t = offset % n_treinos`.

### 5.1 Extensão da patologia (sondagem N=500 por cenário)

Confirmou viés posicional em **4 cenários realistas**:

| Cenário | Chave afetada | Pré-fix |
|---|---|---|
| `upper(3) x 2T` | ombro | **T2=100%** |
| `upper(3) x 3T` | ombro | **T1=0%**, T2/T3 50/50 |
| `perna_posterior(3) x 2T` | abduction | **T2=100%** |
| `perna_posterior(3) x 2T` | hinge | 66/33 |
| `ombro(3) x 2T` | posterior_ombro | **T2=100%** |
| `ombro(3) x 2T` | ombro_composto | 66/33 |

Cenários com quotas balanceadas (`upper(4-5)`, `lower(3-5)`, `costas(3)`)
já estavam ok pré-fix — viés só aparece quando uma chave tem quota
estritamente menor que as outras E `soma_outras % n_treinos` é constante.

Severidade clínica: ombro 100% T2 em `upper(3)` (config comum) significa
personal trainer vê ombro só no T2. Não-trivial.

### 5.2 Fix aplicado — opção 1 (offset inicial aleatório)

Decidido em conjunto com o usuário aplicar no mesmo PR — patologia
realista, fix mínimo, mesmo escopo conceitual ("distribuir o
determinismo entre rotinas").

Linha ~463 de `gerador_treino.py`:

```python
acumulador = random.randrange(n_treinos)  # era 0 fixo
```

Justificativa:
- Distribui a fase inicial entre rotinas.
- Preserva Bresenham: cycling intra-rotina via `acumulador += qtd`
  intocado.
- Garantia de soma exata preservada (Bresenham é por construção exato
  enquanto `sum(vagas) == sum(quotas)`).
- 1 linha, complexidade nula.

### 5.3 Validação pós-fix

Sondagem repetida em todos os 4 cenários afetados:

| Cenário | Chave | Pré-fix | Pós-fix |
|---|---|---|---|
| `upper(3) x 2T` | ombro | T2=100% | T1=53% / T2=46% |
| `upper(3) x 3T` | ombro | T1=0% | T1=35% / T2=32% / T3=32% |
| `perna_posterior(3) x 2T` | abduction | T2=100% | T1=49% / T2=50% |
| `perna_posterior(3) x 2T` | hinge | T1=66% | T1=50% / T2=49% |
| `ombro(3) x 2T` | posterior_ombro | T2=100% | T1=49% / T2=50% |
| `ombro(3) x 2T` | ombro_composto | T1=66% | T1=50% / T2=49% |

Cenários não-afetados (`upper(4-5)`, `lower(3-5)`, `costas(3)`)
continuam ~50/50 — comportamento mantido.

### 5.4 Cascata de validação pós-fix

- Pytest geral: **206 passed + 1 skipped** preservado.
- 3 snapshots adicionais regenerados — diffs continuam plausíveis
  (variações de cycling, mesma classe das regenerações anteriores).
- Fixture HIB2: seed 809 → **543**. 3ª transição no total nesta
  sessão.
- Harness 16/16 OK preservado, 4.1 = 15.81% inalterado.

---

## 6. Resultados empíricos

### 6.1 Suite pytest

- Pré-fix: 202 passed + 1 skipped + 13 snapshots OK na main.
- Pós-fix Hamilton: 196 passed + 10 failed (7 snapshots + 2 testes
  que codificavam o viés + 1 fixture HIB2 com seed obsoleta).
- Pós-fix Hamilton + auditoria (3 fixes adicionais): 5 snapshots
  adicionais quebraram + fixture HIB2 quebrou de novo.
- Pós-todos-os-fixes + regen de snapshots + atualizações:
  **206 passed + 1 skipped** ✅.

### 6.2 Snapshots regenerados (`tests/__snapshots__/test_regressao.ambr`)

13 snapshots no total; 12 verdes sem mudança ou regenerados com
distribuição clinicamente plausível. Diffs principais:

- `core_3x1treino_seed17`: pré-fix tinha 3 dinâmicos (V-Up + Russian
  Twist + Canoinha) — exatamente o viés `core_dinamico` sempre vence
  `core_isometrico`. Pós-fix: 1 dinâmico + 2 isométricos (Canoinha,
  Prancha, Dead Bug). **Distribuição mais saudável**.
- `upper_3x2treinos_seed11`: pré-fix T1 sem aviso `ancora_nao_cumprida`
  pra `puxadas` (porque remadas sempre vencia); pós-fix T1 cobre
  puxadas (`Pulldown Braço Estendido`), avisos remanescentes apenas
  em T2.
- Avisos `ancora_nao_cumprida` que mudam `chave: remadas → puxadas` ou
  `treino_idx: 0 → 1`: empate antes determinístico, agora sorteado.

Nenhuma obrigatória sumiu indevidamente — todas as âncoras obrigatórias
permanecem cobertas onde já estavam, e em alguns casos passam a ser
cobertas onde antes faltavam.

### 6.3 Testes que codificavam o viés (reescritos)

- `tests/test_ancoras.py::test_quota_costas_3_tie_break_alfabetico_estavel`
  → renomeado pra `test_quota_costas_3_tie_break_sorteado_em_empate_total`,
  validando agora `{total=3, ambas ≥1, min=1 max=2}` em vez de
  `{remadas:2, puxadas:1}` fixo.
- `tests/test_pre_alocacao.py::test_decompor_lower_6_proporcional`:
  assertion relaxada de `perna_anterior == 3` pra `{qa, qp} == {2, 3}`
  (panturrilha = 1 mantida).

### 6.4 Fixture HIB2

`tests/test_carga_filter.py::test_filtro_carga_realmente_dissolve_par_conhecido`:
seed precisou ser refrescada 2x (sequência random muda a cada
`random.random()` adicional). Estado final: seed=809 com par
`{Stiff Barra Smith, Remada Baixa Aberta}`. Mesmo contrato clínico:
par viola HIB2 sem filtro, some com filtro.

Histórico do seed nesse teste cresce a cada mudança de sequência
aleatória — agora 12 transições registradas.

### 6.5 Harness `tools/calibrar_pesos_dimensoes.py`

**16/16 OK** preservado. Métrica 4.1 contínua: pré-fix 14.95% (pós-cycling
fix de 2026-05-17) → pós-fix 15.81%. Variação pequena, dentro do mesmo
regime estrutural — o piso do 4.1 é gateado pelo viés de distribuição
por padrões mono-ex (NO-OP estrutural Seção 8.15.12), não por
tie-breaks.

---

## 7. Decisões fechadas

### 7.1 Random global do módulo (consistência com fix prévio)

Todos os 4 fixes usam `random.random()` do módulo global, mesmo
mecanismo que `_selecionar_cand_score_aware` (sessão 2026-05-18
prévia) e que `random.sample` no caso especial de `calcular_quotas`
(vagas < n_obrigatorias). Preserva reprodutibilidade via seed do
chamador.

### 7.2 Auditoria foi proativa — incluir no mesmo PR

Handoff deu liberdade ("entra como bonus no mesmo PR temático ou
vira follow-up"). Como as 3 patologias adicionais são da mesma classe
("sort estável + ordem de declaração" ou "max alfabético em empate"),
trivais de fixar, e validadas com sondagem N=2000 mostrando variância
zero, faz mais sentido fechar todas juntas. Nome sugerido do PR:
`fix(quotas): randomiza tie-breaks em calcular_quotas + Bresenham + doadores`.

### 7.3 Viés estrutural do cycling Bresenham é outro escopo

`ombro 100% T2` em `upper(3) x 2 treinos` é viés de algoritmo, não
tie-break. Não corrigir nesta sessão; registrar como follow-up em
§9 abaixo.

---

## 8. Estado final dos arquivos modificados

- `gerador_treino.py`:
  - Linha ~292: tie-break Hamilton `idx` → `random.random()`
  - Linha ~455: tie-break Bresenham alfabético → `random.random()`
  - Linha ~463: `acumulador = 0` → `random.randrange(n_treinos)`
    (offset inicial — quebra viés estrutural do cycling)
  - Linha ~2750: tie-break doador alfabético → `random.random()`
  - Linha ~2855: tie-break doador alfabético → `random.random()`
- `tests/test_calcular_quotas_vies.py`: criado pré-fix (validação 4 casos)
- `tests/test_ancoras.py`: 1 teste reescrito
- `tests/test_pre_alocacao.py`: 1 teste relaxado
- `tests/test_carga_filter.py`: seed atualizada (358 → 543) + nota histórica
- `tests/__snapshots__/test_regressao.ambr`: 7 + 5 + 3 = 15 snapshots regenerados
- `docs/refatoracao/dimensoes_proximidade.md`: Seção 8.15.14 (esta sessão)
- `docs/refatoracao/logs/sessao_2026-05-18_cadastros_e_tiebreaker.md`: §10
  item adicional ✅ fechado
- `docs/refatoracao/logs/sessao_2026-05-18_fix_calcular_quotas_tiebreak.md`:
  este log

---

## 9. Follow-ups abertos

1. ~~**Viés estrutural do cycling Bresenham**~~ ✅ **Fechado nesta
   mesma sessão** via offset inicial aleatório (§5). Decisão tomada
   com o usuário de fazer junto em vez de virar branch separada.
2. **Recalibrar Supino com Halteres = 57 slots** (item 2 do §10
   do log da sessão anterior) — continua aberto.
3. **Validação clínica em uso real** pós-merge — usuário gerar
   rotinas reais e confirmar que viés posicional T1 vs T2 caiu
   significativamente.

---

## Cross-references

- `docs/refatoracao/logs/handoff_calcular_quotas_tiebreak.md` — handoff
  desta sessão
- `docs/refatoracao/logs/sessao_2026-05-18_cadastros_e_tiebreaker.md` —
  sessão anterior (mesmo dia, fix downstream de tie-break em
  `_selecionar_cand_score_aware`)
- `docs/refatoracao/logs/analise_vies_upper.md` Q4 — caso clínico
  retroativamente explicado por este fix (peito 25%/50% χ²=533)
- `docs/refatoracao/dimensoes_proximidade.md` Seção 8.15.14 — entrada
  oficial desta sessão
