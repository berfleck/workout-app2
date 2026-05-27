# Log — S-R1 distribuição cross-treino de subregião (Achado 1 parcial)

**Data**: 2026-05-27
**Branch**: `achado-1-distribuicao-lower` (a partir de `main`)
**Bloco**: 4 do roadmap CSP — Achado 1 da auditoria clínica 2026-05-26
(faceta de simetria T1↔T2; panturrilha mantida em status quo)

**Arquivos modificados**:
- `gerador_csp.py` — import `REGIAO_PARA_SUBREGIOES` + `SUBREGIAO_PARA_REGIAO`;
  constantes `SUBREGIAO_CODE` + helper `_subregiao_code_do_ex`; kwarg
  `peso_sr1` em `_construir_modelo`/`_resolver_legacy`/`_resolver_com_variedade`/
  `gerar_rotina_csp`/`gerar_treino_csp` + `subregiao_idx[s]` IntVar (sempre
  criado, espelho de `regiao_idx`) + bloco de constraint soft S-R1 (BoolVar
  `splits_iguais` por par treino+região + AND de `same_S` BoolVars) +
  `peso_sr1` no `teto_por_termo` da Phase 2 da variedade
- `app_flask.py` — constante `_PESO_SR1_DEFAULT = 4` (calibrada na sondagem)
  + wire em `/gerar` (gerar_rotina_csp); `treino_regerar` não recebe (skip
  estrutural cobre rotina 1 treino isolado)
- `tests/test_csp_sr1_cross_treino.py` — 4 testes novos
- `tools/sondar_sr1_cross_treino.py` — script de sondagem N=5 × 1 config
  default (Full Body 2T região) + flag `--config lower_iso` opcional
- `docs/refatoracao/logs/sr1_pre.json` — baseline peso=0
- `docs/refatoracao/logs/sr1_pos.json` — pós peso=4 (calibrado)

**Status**: ✅ concluída. Aguarda aprovação do Bernardo para merge FF em
`main` (disciplina de merge do roadmap exige confirmação explícita).

---

## Objetivo

Fechar a **faceta de simetria cross-treino do Achado 1** da auditoria
2026-05-26: em rotina Full Body 2T com `regiao lower(3)`, T1 e T2 caíam
no MESMO split `2 perna_anterior + 1 perna_posterior + 0 panturrilha`
em ambas as rodadas (média e alta aderência). Volume rotina inteira:
4 anterior + 2 posterior + 0 panturrilha em 6 slots — assimétrico.

Causa: o CSP não tinha soft cross-treino balanceando subregião dentro
de região. Cada treino decidia o split independentemente; com Hamilton
sorteando 50/50 entre `2ant+1post` e `1ant+2post`, há 25% chance dos
2 treinos caírem no mesmo split. Auditoria N=1+1 capturou essa
casualidade — sondagem N=5 em main mostrou 40% (multi-treino com
demanda região) e 60% (lower(3) × 2T isolado) de splits T1==T2.

**Panturrilha**: faceta separada, decisão clínica Bernardo (2026-05-27)
**status quo aceito** — `panturrilha.obrigatoria=False` mantém o filtro
pré-Hamilton (`qtd ≤ 2*n_obrig`) que faz panturrilha cair em lower(3).
Frente não toca em `ANCORAS_POR_REGIAO`.

## Decisões fechadas

### 4.1 Panturrilha — **(c) Status quo** (Bernardo 2026-05-27)

`ANCORAS_POR_REGIAO['lower']` continua com `panturrilha.obrigatoria=False`.
Panturrilha aparece naturalmente em ~60-80% das rotinas Full Body 2T
quando o cycling do Hamilton sorteia `1+1+1+0` (split com pant) em
algum treino — sondagem confirma. Em `lower(3) × 2T isolado` peso=0
baseline já era 80%. Não é o 0% reportado na auditoria N=1+1 (azar).

### 4.2 Granularidade — Subregião dentro de região

Faceta exata do achado. Padrão-dentro-de-subregião fica pra futuro se
auditoria mostrar caso real.

### 4.3 Modelagem CSP — `splits_iguais` BoolVar por par+região

**Mudança vs spec original do handoff**: a spec propunha minimizar
`sum(|diff_t1_t2|)` por subregião. **Errado**: minimizar |diff| empurra
pra T1==T2 (espelho matemático = mesmo split), o OPOSTO do objetivo
clínico. Implementação inicial mostrou exatamente isso na sondagem:
peso=4 com a fórmula errada subiu split T1==T2 de 40% pra 100% (!).

**Correção**: `splits_iguais` BoolVar por par (t1, t2) e região R, true
sse `count_S_t1 == count_S_t2` pra **todas** as subregiões S em R.
Penalty `peso_sr1 * splits_iguais`. Premia que pelo menos uma
subregião tenha contagem diferente entre os 2 treinos. Modelagem:

```python
# Pra cada subregião S em R:
same_S = (count_S_t1 == count_S_t2) BoolVar via OnlyEnforceIf.
# AND:
splits_iguais = AddBoolAnd([same_S for S in subs_comuns])
# Penalty:
pen = peso_sr1 * splits_iguais (IntVar 0 ou peso_sr1).
```

`splits_iguais` criado SÓ quando `peso_sr1 > 0 and len(treinos) >= 2`.

### 4.4 Peso=4 (calibrado por sondagem)

Tentativa única — peso=4 atingiu 0% split T1==T2 em ambas as configs.
Não foi necessário escalar. Mesma magnitude do S-B5: entre `rank_max=3`
(S-T1) e `5*1=5` (S-B4), não inverte tier-order nem força motor a
quebrar bloco em solos.

### 4.5 Sondagem N=5 × 2 configs

Após corte 2026-05-27 (Bernardo aprovou tempo reduzido). Config default
(Full Body 2T região, achado exato) + lower(3)×2T isolado opcional.
N=5 suficiente pra delta direcional. Métricas:

- `%T1.ant == T2.ant` (split repetido).
- `%vol_lower_assim` (volume ant != post na rotina inteira).
- `%pant_presente` (informativo — status quo).
- p50/max tempo de solve.

---

## Implementação

### `gerador_csp.py` — imports + constantes

```python
from gerador_treino import (
    ...,
    REGIAO_PARA_SUBREGIOES,  # S-R1
    SUBREGIAO_PARA_REGIAO,   # S-R1
)

_SUBREGIOES_UNICAS = sorted(SUBREGIAO_PARA_REGIAO.keys())
SUBREGIAO_CODE: dict[str, int] = {
    s: i for i, s in enumerate(_SUBREGIOES_UNICAS, start=1)
}
_SUBREGIAO_OUTRO_CODE = 0

def _subregiao_code_do_ex(ex): ...
```

### `_construir_modelo` — `subregiao_idx[s]` IntVar (espelho de `regiao_idx`)

Sempre criado. Mesma linha de raciocínio do `grupo_func`/`regiao_idx`
(gancho pra futuras constraints; CP-SAT simplifica IntVars não
referenciadas no objetivo).

```python
subregiao_idx: dict[int, cp_model.IntVar] = {}
for s in slots_globais:
    pool = s["pool_slot"]
    codes = [_subregiao_code_do_ex(ex) for ex in pool]
    lo, hi = (min(codes), max(codes)) if codes else (0, 0)
    si = model.NewIntVar(lo, hi, f"subreg_t{s['t_idx']}_s{s['sid']}")
    model.Add(si == sum(assign[(s["sid"], c)] * codes[c]
                        for c in range(len(pool))))
    subregiao_idx[s["sid"]] = si
```

### `_construir_modelo` — bloco S-R1 cross-treino

Logo após o bloco S-B5 (no fim do loop par-a-par S-T1/S-B1/S-B5),
antes do S-B4. Skip estrutural: `if peso_sr1 > 0 and len(treinos) >= 2`.

Pra cada região R que aparece como demanda em ≥2 treinos:
- Pra cada subregião S em R: contar slots-S em cada treino via
  indicators `is_sub` (BoolVars) + soma → IntVar `count_S_t`.
- Pra cada par (t1, t2) com R: `same_S = (count_S_t1 == count_S_t2)`,
  AND → `splits_iguais`, penalty `peso_sr1 * splits_iguais`.

### Propagação `peso_sr1`

Em `_construir_modelo`, `_resolver_legacy`, `_resolver_com_variedade`
(Phase 1 + Phase 2 + `teto_por_termo`), `gerar_rotina_csp`,
`gerar_treino_csp`. Default 0.

### `app_flask.py` — constante + wire

```python
_PESO_SR1_DEFAULT = 4
```

Wire em `/gerar` (gerar_rotina_csp). `treino_regerar` não recebe (skip
estrutural cobre rotina 1 treino isolado).

---

## Resultado da sondagem

### Tabela comparativa (N=5 por config, peso=4 vs peso=0)

| Config | Pré split T1==T2 | Pós split T1==T2 | Δ | Pré p50 | Pós p50 |
|---|---:|---:|---|---:|---:|
| Full Body 2T (região, achado) | 40.0% | **0.0%** | -40.0pp ✅ | 0.62s | 0.71s |
| lower(3)×2T isolado | 60.0% | **0.0%** | -60.0pp ✅ | 0.24s | 0.36s |

### Métricas secundárias (Full Body 2T região, peso=4)

- `%vol_lower_assim`: 60% → 80% (esperado — quando pant entra em UM
  treino só, vol ant+post+pant fica desigual entre os 2). Não é
  problema clínico — o que importa é o split não repetir.
- `%pant_presente`: 60% → 80% (panturrilha apareceu MAIS pós-S-R1 —
  motor usa pant como alavanca pra diferenciar T1 vs T2 sem custo
  estrutural).

### Smoke E2E browser

POST `/gerar` Full Body 2T região (Aluno Teste):

```
T1 split lower: (1, 2, 0, 0)  # 1 ant + 2 post
T2 split lower: (1, 1, 1, 0)  # 1 ant + 1 post + 1 PANT
```

T1 ≠ T2 confirmado no flow real. Panturrilha entra em T2.

---

## Gate de fechamento

| Métrica | Resultado |
|---|---|
| pytest (`tests/`) | **360 passed + 1 skipped** (356 base + 4 novos em `test_csp_sr1_cross_treino.py`) ✓ |
| 13 snapshots | ✓ preservados |
| Harness 16/16 | ✓ 16/16 OK (2 NO-OPs informativos preservados: 2.3 banco, 4.1 viés distribuição pós-CORE) |
| Sondagem pós | ✓ Faceta cross-treino do Achado 1 fechada (0% split T1==T2 em ambas as configs) |
| Smoke E2E browser | ✓ POST `/gerar` Full Body 2T região → T1 ≠ T2 |
| Motor antigo | Intocado ✓ |
| `ANCORAS_POR_REGIAO` | Intocado (status quo panturrilha) ✓ |
| Hamilton | Intocado (random.random() já lá; auditoria N=1 não justifica) ✓ |

---

## Achados / sinais de alerta

1. **Bug de design da spec original do handoff** — minimizar
   `sum(|diff_t1_t2|)` por subregião era a modelagem ingênua proposta,
   mas é matematicamente o oposto do objetivo clínico. Forçava T1==T2
   (espelho matemático = mesmo split) em vez de alternância.
   Sondagem peso=4 com a versão errada mostrou: split T1==T2 de
   40% → 100% (piorou). Correção: `splits_iguais` BoolVar + penalty
   binária. Lição: spec matemática precisa ser validada com sondagem
   ANTES de assumir que está clinicamente correta.

2. **Panturrilha em status quo aparece mais que reportado** — auditoria
   N=1+1 mostrou 0% panturrilha, mas sondagem N=5 baseline já tinha
   60% (Full Body 2T) e 80% (lower iso). Auditoria capturou
   casualidade. Status quo aceito mesmo assim — Bernardo prefere
   manter `obrigatoria=False` e aceitar variabilidade natural.

3. **Tempo de solve sem regressão estrutural** — p50 +0.1s em ambas
   as configs. S-R1 é constraint "leve" — pares (t1, t2) × subregiões
   é magnitude pequena no problema típico (1-3 regiões em demanda × 2
   treinos = 1-3 BoolVars `splits_iguais` por rotina).

4. **`subregiao_idx[s]` IntVar criado SEMPRE** — mesma decisão do
   `regiao_idx[s]` da S-B5. Custo leve, simplifica futuras constraints
   de subregião (ex.: S-E1 cross-treino que pode reusar).

5. **Achado 1 fecha PARCIALMENTE** — faceta cross-treino ✅, faceta
   panturrilha status quo aceito (não fechado, decisão clínica). A
   tabela do achado na auditoria fica como ✅ parcial.

6. **Bloco 4 do roadmap — próximos itens**:
   - Achado 2 (S-E1 proximidade biomecânica cross-treino) — desbloqueado
     por esta frente. Próximo lógico. Reusar 3 dimensões já cadastradas
     (pegada/plano_corporal/equipamento_grupo) + lógica INTER 0.8×INTRA
     do `dimensoes_proximidade.md` (referência viva).
   - Achado 4 (calibração `_PESO_ADERENCIA_POR_PERFIL`): DESCONTINUADO.
   - Gate de avaliação clínica semântica.

---

## Próximos passos

- Atualizar `roadmap_csp.md` (S-R1 ✅; panturrilha 🟦 status quo).
- Atualizar `auditorias/2026-05-26.md` (Achado 1 → ✅ parcial).
- Atualizar `MEMORY.md` (novo memory file `project_frente_s_r1.md`).
- Commit seletivo + push + aguardar aprovação Bernardo pra merge FF.
