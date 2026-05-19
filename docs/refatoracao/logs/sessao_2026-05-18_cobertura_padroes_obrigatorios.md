# Sessão 2026-05-18 (noite) — cobertura de padrões obrigatórios na rotina

Branch: `fix/cobertura-padroes-obrigatorios-rotina` (a partir de main).

Continuação da sessão `sessao_2026-05-18_fix_calcular_quotas_tiebreak.md`
(mesma noite, descoberta do bug via rotina real de Bernardo após
testar o fix anterior em uso real).

---

## 1. Caso clínico de origem

Bernardo gerou rotina `20260518_203030_2a06` com config
`upper(3) + lower(3) + core(2) × 2T`. Inspeção:

- **peito**: 2 ex em T1 + 1 em T2 (Supino Inclinado Halteres,
  Crossover Sentado, Apoio Ajoelhado) — total 3, distribuição 2+1.
- **costas**: 2 ex, **ambos puxadas** (Barra Isométrica em T1,
  Puxada Unilateral Polia em T2). Zero remadas.
- **ombro**: 1 ex (Desenv. Halteres Sentado em T2).

Pergunta do usuário: "como existem 2 exercícios de peito em T1 e 1
em T2? por que não entraram remadas?"

---

## 2. Diagnóstico

### 2.1 Por que peito 2+1?

**Comportamento correto pós-fix de tie-break (sessão anterior).**
`upper(3) × 2T = 6 vagas`. Hamilton com pesos 2:2:1 → floor (2,2,1),
restante=1. Resto empata entre peito e costas (0.4 cada). Pré-fix de
2026-05-18, peito sempre vencia (idx menor); pós-fix, sorteia.

Sondagem: peito vence 51%, costas 49%. Nessa rotina específica,
peito ganhou o +1 → `{peito:3, costas:2, ombro:1}` → Bresenham 3
entre 2 treinos = 2+1.

### 2.2 Por que 2 puxadas e 0 remadas?

**Bug pré-existente, agora visível.** Sondagem N=2000:

```
both_puxadas=25%  both_remadas=25%  mixed=49%
```

**Mecanismo:** pipeline tem 2 camadas. Camada rotina-level já
agregava no nível **subregião** (Hamilton uma vez na rotina) mas no
nível **padrão** caía no `_decompor_demanda_subregiao` per-treino.

Para `costas qt_rotina=2` distribuído como 1+1 entre 2 treinos:
- Cada treino chama `_decompor_demanda_subregiao('costas', 1)`.
- `calcular_quotas([remadas:2 obrig, puxadas:2 obrig], 1)` cai no
  caso especial `qt=1 < n_obrigatorias=2` → `random.sample(obrigs, 1)`.
- Cada treino sorteia INDEPENDENTEMENTE. 25% prob ambos iguais.

### 2.3 Por que score INTER não compensou?

Arquitetura em 2 camadas sequenciais:

1. **Planejamento**: decide quantos slots de cada padrão por treino.
   Saída: slots tipados `("padrao", "puxadas")`.
2. **Escolha**: scoring INTRA/INTER/HISTÓRICO dentro do pool daquele
   padrão.

INTER opera em família/pegada/plano/equipamento/variante_pontual —
granularidades menores que padrão. Quando o planejamento entrega 2
slots de puxadas (1 por treino), o INTER só consegue escolher
puxadas DIFERENTES — não trocar uma por remada (não está no pool).

**Fix correto está na camada de planejamento, não no scoring.**

---

## 3. Fix — agregação rotina-level no nível padrão

### 3.1 Mudança em `pre_alocar_rotina` (~linha 3100-3175)

Substituiu o loop per-treino que chamava `_decompor_demanda_subregiao`
por:

1. **Agregar capacidade por subregião**: `qts_treino = [por_treino_sub[i][sub] for i]`
2. **Para cada subregião com âncoras**:
   - `qt_total_sub = sum(qts_treino)`
   - `calcular_quotas(ancoras, qt_total_sub)` UMA VEZ no nível rotina
   - `_distribuir_quotas_entre_treinos(quotas_pad, n_tr, qts_treino, pesos)`
3. **Subregiões sem âncoras** (cardio etc): mantém path per-treino legado.

### 3.2 Piso de cobertura por treino (refinamento)

Caso edge encontrado durante validação:

`peito qt_rotina=2`, pesos 3:2 → Hamilton dá `compostos:1, isolados:1`.
Bresenham distribui 1+1 entre treinos → um treino sem composto.
Quebra invariante clínica "cada treino com vagas de peito tem 1
composto" (teste `test_upper_3x2treinos_tem_composto_de_cada_ancora`
saltou de ≤5 falhas/200 → 48/200).

Solução: após Hamilton, garantir piso de cobertura:

```python
deficit = n_treinos_qt_pos - sum(quotas_pad.get(p, 0) for p in obrigs)
if deficit > 0:
    for doador in nao_obrigs:
        while deficit > 0 and quotas_pad.get(doador, 0) > 0:
            alvo = min(obrigs, key=lambda p: (quotas_pad.get(p, 0), random.random()))
            quotas_pad[doador] -= 1
            quotas_pad[alvo] += 1
            deficit -= 1
```

Doa só de não-obrigatórias (preserva obrigatórias). Tie-break random
em empate de quotas (consistência com fixes da sessão prévia).

---

## 4. Resultados

### 4.1 Sondagem de cobertura (N=1000 rotinas)

| Cenário | Pré-fix | Pós-fix |
|---|---|---|
| `upper(3) × 2T` costas (remadas+puxadas) | **73%** | **100%** |
| `upper(3) × 2T` peito (composto invariante) | 48/200 falhas | **0/200** |
| `upper(4) × 2T` costas | ~100% | 100% |
| `upper(3) × 3T` costas | ~85% | **100%** |
| `lower(4) × 2T` perna_post (hinge+knee_flex) | ~100% | 100% |
| `lower(3) × 2T` perna_post | ~100% | 100% |

### 4.2 Validação completa

- **pytest 206 passed + 1 skipped** (preservado)
- **2 snapshots regenerados** (`test_upper_3x2treinos_seed11` +
  `test_upper_3_lower_2_core_2_3treinos_seed42`) — diffs removem
  avisos `ancora_nao_cumprida` de puxadas (não falta mais)
- **Fixture HIB2**: seed 543 → **2202** (4ª transição em ~30h)
- **Harness 16/16 OK** preservado
- **Métrica secundária 6.1** (% com ancora_nao_cumprida): **100% → 0%**
  — ganho clínico significativo.

---

## 5. Arquivos modificados

- `gerador_treino.py`:
  - Linhas ~3100-3175: reescrita do bloco de decomposição per-treino
    para agregação rotina-level + piso de cobertura
- `tests/test_carga_filter.py`: seed HIB2 543 → 2202
- `tests/__snapshots__/test_regressao.ambr`: 2 snapshots regenerados
- `docs/refatoracao/dimensoes_proximidade.md`: Seção 8.15.15 (esta sessão)
- `docs/refatoracao/logs/sessao_2026-05-18_cobertura_padroes_obrigatorios.md`:
  este log

---

## 6. Decisões fechadas (não reabrir sem motivo forte)

### 6.1 Fix vai na camada de planejamento, não no scoring

INTER é per-slot-tipado por design. Estender INTER pro nível padrão
contrariaria o planejamento (quebraria invariante "score escolhe
dentro do que foi planejado, sem reabrir alocação"). Mantém separação
de camadas.

### 6.2 Piso de cobertura prefere doar de não-obrigatórias

Quando obrigatórias têm `quotas_obrig < n_treinos_qt_pos`, doa de
não-obrigatórias primeiro. Preserva semântica "obrigatória sempre
tem ≥1 por treino quando há vagas suficientes". Empate entre
obrigatórias (qual recebe a doação) sorteado random — consistente com
fixes da sessão prévia.

### 6.3 Subregiões sem âncoras (cardio) mantêm path legado

Cardio só tem 1 padrão (cardio) → não há viés possível. Mantém path
per-treino para preservar simplicidade.

---

## 7. Cross-references

- `docs/refatoracao/dimensoes_proximidade.md` Seção 8.15.15 — entrada
  oficial na fonte de verdade
- `docs/refatoracao/logs/sessao_2026-05-18_fix_calcular_quotas_tiebreak.md`
  — sessão anterior mesmo dia (fixes de tie-break que tornaram este
  bug visível ao desbloquear costas qt_rotina=2)
- Rotina real de origem: `bf_treinamento.db` registro `20260518_203030_2a06`
