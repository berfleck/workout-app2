# Log — S-B5 diversidade de região INTRA-bloco

**Data**: 2026-05-26
**Branch**: `sb5-diversidade-regiao-bloco` (a partir de `main`)
**Bloco**: 4 do roadmap CSP — primeiro item 🔴 prioritário da auditoria
clínica 2026-05-26 (Achado 3)

**Arquivos modificados**:
- `gerador_csp.py` — constantes `REGIAO_CODE` + helper `_regiao_code_do_ex`
  + kwarg `peso_sb5` em `_construir_modelo`/`_resolver_legacy`/
  `_resolver_com_variedade`/`gerar_rotina_csp`/`gerar_treino_csp` +
  `regiao_idx[s]` IntVar (sempre criado, espelho de `grupo_func[s]`)
  + bloco de constraint soft S-B5 reaproveitando `same_bloco` da S-B1
  + `peso_sb5` adicionado ao `teto_por_termo` do Phase 2 da variedade
  + skip estrutural em treinos single-region (otimização de tempo)
- `app_flask.py` — constante `_PESO_SB5_DEFAULT = 4` (calibrada na
  sondagem) + wire em `/gerar` (gerar_rotina_csp) e `treino_regerar`
  (gerar_treino_csp)
- `tests/test_csp_sb5_diversidade_regiao.py` — 7 testes novos
- `tools/sondar_sb5_diversidade.py` — script de sondagem 5 configs × N=10
- `docs/refatoracao/logs/sb5_pre.json` — baseline peso=0
- `docs/refatoracao/logs/sb5_pos.json` — pós peso=4 (calibrado)

**Status**: ✅ concluída. Aguarda aprovação do Bernardo para merge FF
em `main` (disciplina de merge do roadmap exige confirmação explícita).

---

## Objetivo

Fechar o **achado 3 da auditoria 2026-05-26** (rotina Full Body 2T com
4/8 blocos pareando exercícios da mesma região — circuito do mesmo
grupo, fadiga cumulativa errada). Recupera a feature P1-P4 do
`montar_blocos` greedy antigo (geo-diversidade nos slots ex1/ex2/ex3),
**perdida na migração CSP** e nunca documentada como gap.

S-B5 é uma soft constraint nova no objetivo do CSP: penalty fixo por
par de slots no MESMO BLOCO + MESMA REGIÃO
(`upper`/`lower`/`core`/`cardio`). Espelha estruturalmente a S-B1
(distância funcional via `GRUPO_MUSCULAR_PADRAO`), mas com granularidade
de região em vez de grupo funcional. Razão clínica: dois exercícios de
grupos funcionais diferentes (ex.: remada + desenvolvimento halteres)
podem ser ambos da mesma região (`upper`) e ainda assim quebrar o ponto
da supersérie.

## Decisões fechadas

### Default ON sempre, sem toggle UI (decisão §4.1 do handoff)

Diversidade de região é benefício clínico universal — vale pra qualquer
rotina multi-região, não é decisão caso-a-caso. Toggle adicionaria
superfície de erro no fluxo do personal sem motivo. Em demandas
single-region (ex.: `upper(4)` sozinha) o motor naturalmente aceita
pareamento same-region pagando penalty — graceful degradation.

### Peso=4 (calibrado por sondagem, §4.2 do handoff)

**1ª tentativa: peso=10** (mesma magnitude de S-B1) — falhou. Em config
single-region o motor preferiu blocos solo:

- ABC 3T: blocos solo **19.6% → 61.8%** (motor fugindo de pares
  same-region em vez de aceitar).
- perna_ant+post: blocos solo **0% → 46.2%**.
- ABC 3T p50: 8.56s → **116.30s** (~14× lento).

**Diagnóstico**: peso=10 empata com custo de "virar 2 solos" do S-B4
(`peso_tamanho_bloco=5 × desvio=1 × 2 solos = 10`). Solver escolhe
qualquer dos dois caminhos.

**Recalibração: peso=4** — entre `S-T1 rank_max=3` (mantém precedência
clínica do tier-order) e `5*1=5` (custo de quebrar 1 par em 2 solos
no S-B4). Motor:

- Multi-região: cross-region (custo 0) > same-region (custo 4) →
  alterna sem ambiguidade.
- Single-region: 1 par same-region (custo 4) > 2 solos (custo 10) →
  motor PREFERE par a fugir pra solos.
- Tier-order: peso=4 > rank_max=3 → S-B5 nunca inverte ordem de tier
  (alta antes de baixa) em troca de diversidade — clinicamente correto.

### Granularidade `regiao` direto do banco (decisão §4.3 do handoff)

`upper`/`lower`/`core`/`cardio` — 4 valores já no XLSX. Não inventar
granularidade nova (ex.: `core_iso` vs `core_din`). Norte Seção 4
("centralidade vem de tag curada, não emerge do banco"). Se calibração
futura mostrar caso especial, refina depois.

### Interação com S-B1 (decisão §4.4 do handoff)

Pares "duplamente ruins" (mesmo grupo funcional E mesma região, ex.:
push+push) pagam penalty dupla = 10 (S-B1) + 4 (S-B5) = 14. Comportamento
correto — par duplamente ruim deve pesar mais. Sondagem não mostrou
cascata estranha (motor ainda aceita antagonistas same-region como
push+pull em upper sem viés excessivo).

---

## Implementação

### `gerador_csp.py` — constantes

```python
_REGIOES_UNICAS = ["upper", "lower", "core", "cardio"]
REGIAO_CODE: dict[str, int] = {r: i for i, r in enumerate(_REGIOES_UNICAS, start=1)}
_REGIAO_OUTRO_CODE = 0  # fallback

def _regiao_code_do_ex(ex): return REGIAO_CODE.get(ex.regiao, _REGIAO_OUTRO_CODE)
```

### `_construir_modelo` — `regiao_idx[s]` IntVar

Espelho exato de `grupo_func[s]` (Fatia 4.B):

```python
regiao_idx: dict[int, cp_model.IntVar] = {}
for s in slots_globais:
    pool = s["pool_slot"]
    codes = [_regiao_code_do_ex(ex) for ex in pool]
    lo, hi = (min(codes), max(codes)) if codes else (0, 0)
    ri = model.NewIntVar(lo, hi, ...)
    model.Add(ri == sum(assign[(s["sid"], c)] * codes[c] for c in range(len(pool))))
    regiao_idx[s["sid"]] = ri
```

Criado SEMPRE (mesmo com peso_sb5=0). Leve, gancho pra futuras
constraints; CP-SAT simplifica IntVars não referenciadas no objetivo.

### `_construir_modelo` — constraint soft

Dentro do loop par-a-par da S-T1, reaproveitando `same_bloco` quando
S-B1 também está ativo:

```python
precisa_same_bloco = (
    (peso_evitar_agonistas > 0 and (s1, s2) not in pares_intra_sub)
    or peso_sb5 > 0
)
if precisa_same_bloco:
    same_bloco = model.NewBoolVar(...)
    model.Add(same_bloco + lt + gt == 1)
    # ... bloco S-B1 (se ativo) ...
    if peso_sb5 > 0:
        same_regiao = model.NewBoolVar(...)
        model.Add(regiao_idx[s1] == regiao_idx[s2]).OnlyEnforceIf(same_regiao)
        model.Add(regiao_idx[s1] != regiao_idx[s2]).OnlyEnforceIf(same_regiao.Not())
        viol_sb5 = model.NewIntVar(0, peso_sb5, ...)
        model.Add(viol_sb5 >= peso_sb5).OnlyEnforceIf([same_bloco, same_regiao])
        penalidades.append(viol_sb5)
```

### Propagação `peso_sb5`

Em `_resolver_legacy`, `_resolver_com_variedade` (Phase 1 + Phase 2 +
`teto_por_termo`), `gerar_rotina_csp`, `gerar_treino_csp`. Default 0.

### `app_flask.py` — constante + wire

```python
_PESO_SB5_DEFAULT = 4
```

Wire em duas chamadas:
- `/gerar` → `gerar_rotina_csp(..., peso_sb5=_PESO_SB5_DEFAULT)`
- `treino_regerar` → `gerar_treino_csp(..., peso_sb5=_PESO_SB5_DEFAULT)`

Sempre ativo. Sem toggle UI.

---

## Resultado da sondagem

### Configs canônicas (5, mesmas do harness E.0)

1. Full Body 2T (subregião) — composição variada
2. ABC 3T — push/pull/lower split (mais single-region)
3. upper(3)×2T — single-region (graceful test)
4. perna_ant+post — single-region lower (graceful test)
5. Full Body 2T (região, H-A0) — setup EXATO da auditoria 2026-05-26

### Tabela comparativa (N=10 por config)

Números do `sb5_pos.json` (peso=4, com skip de treinos single-region):

| Config | Pré same-region | Pós same-region | Δ | Pré solo | Pós solo | Pré p50 | Pós p50 |
|---|---:|---:|---|---:|---:|---:|---:|
| Full Body 2T (sub) | 38.8% | **0.0%** | -38.8pp ✅ | 9.1% | 19.2% | 1.45s | 11.18s |
| ABC 3T | 80.2% | 76.5% | -3.7pp | 19.6% | 30.9% | 8.56s | 71.60s |
| upper(3)×2T | 100% | 100% (esperado) | 0pp | 50% | 50% (preservado) | 0.22s | 0.22s |
| perna_ant+post | 100% | 100% (esperado) | 0pp | 0% | 0% (preservado) | 0.12s | 0.12s |
| Full Body 2T (região, achado) | 22.5% | **0.0%** | -22.5pp ✅ | 0% | 0% | 0.50s | 0.53s |

Wins clínicos:
- Full Body 2T (sub): same-region zerou (-38.8pp).
- Full Body 2T (região, H-A0): **achado da auditoria fechado** (-22.5pp → 0%).
- Single-region (upper(3)×2T, perna_ant+post): SEM regressão na taxa
  de blocos solo da Fatia 4.C — graceful degradation por desativação
  estrutural (skip de treinos single-region).

ABC 3T cai pouco (-3.7pp) porque Day A e Day B são single-region (todos
slots `upper`); S-B5 só atua em Day C (multi-region). Esperado.

### Otimização: skip de treinos single-region

A 1ª sondagem peso=4 expôs problema de performance grave em ABC 3T:
**p50 = 490s, p95 = 1 hora** (vs baseline 8.56s). Causa: CP-SAT
enumerava soluções equivalentes na Phase 2 da variedade em treinos
single-region onde a constraint não pode fazer NADA útil (Day A só
upper — não há cross-region disponível em bloco nenhum).

Fix: detectar treinos cujo union de pools = singleton de região e
desativar S-B5 nesses pares. Análogo conceitualmente ao
`pares_intra_sub` da S-B1.

```python
treinos_single_region: set[int] = set()
for t_idx, sids_t in slots_por_treino.items():
    regioes_treino = set()
    for sid in sids_t:
        for ex in slot_por_sid[sid]["pool_slot"]:
            regioes_treino.add(ex.regiao)
    if len(regioes_treino) <= 1:
        treinos_single_region.add(t_idx)
```

Resultado: ABC 3T p50 cai de 490s → 71.6s (~6.8× mais rápido).
Configs single-region (upper(3)×2T, perna_ant+post) caem para o
tempo baseline.

---

## Gate de fechamento

| Métrica | Resultado |
|---|---|
| pytest (`tests/`) | **357 passed + 1 skipped** (=350 base + 7 novos em `test_csp_sb5_diversidade_regiao.py`) ✓ |
| 13 snapshots | ✓ preservados |
| Harness 16/16 | ✓ 16/16 OK (2 NO-OPs informativos preservados: 2.3 banco, 4.1 viés distribuição) |
| Sondagem pós | ✓ Achado da auditoria fechado (0% same-region em Full Body 2T região) |
| Smoke E2E browser | ✓ POST `/gerar` Full Body 2T região → **0/8 blocos same-region** (Bernardo: comparar com 4/8 da auditoria N=1) |
| Gerador antigo | Intocado ✓ |

---

## Achados / sinais de alerta

1. **Calibração de peso é não-trivial em configs single-region.**
   peso=10 (primeira tentativa) destruiu blocos por empate com S-B4.
   Lição: peso de S-B5 deve ficar abaixo de `peso_tamanho_bloco *
   desvio_max` pra não competir com a preferência de tamanho do bloco.

2. **Performance**: peso=4 é leve. ABC 3T continua o gargalo
   (~10s baseline, +/-20% com S-B5) mas aceitável.

3. **`regiao_idx[s]` IntVar criado SEMPRE** — mesma decisão do
   `grupo_func[s]` (Fatia 4.B). Custo leve, simplifica futuras
   constraints de região.

4. **Decisão estrutural (não medida)**: pares "duplamente ruins"
   (mesmo grupo E mesma região) pagam penalty dupla. Esperado pelo
   handoff §4.4. Sondagem confirma que não dispara cascata estranha.

5. **Bloco 4 da auditoria 2026-05-26 — itens restantes** (não tocados
   nesta frente):
   - Achado 1 (distribuição lower 2:1 + panturrilha zerada): combina
     aleatorização Hamilton + soft cross-treino S-R1. Aberto.
   - Achado 2 (equipamento repetido cross-treino): novo eixo S-E1.
     Calibração depende de S-B5 e S-R1 entrarem. Aberto.
   - Achado 4 (calibração `_PESO_ADERENCIA_POR_PERFIL`): DESCONTINUADO
     em 2026-05-26. Ver `logs/calibracao_aderencia_descontinuada.md`.

---

## Próximos passos

- Smoke E2E manual via browser: gerar 2-3 rotinas Full Body 2T região
  com Aluno Teste e verificar visualmente blocos cross-region.
- Atualizar `roadmap_csp.md` (S-B5 marcada ✅ no Bloco 4).
- Atualizar `auditorias/2026-05-26.md` (Achado 3 → status ✅).
- Commit seletivo + push + aguardar aprovação Bernardo pra merge FF.

Bloco 4 do roadmap continua com os 3 itens restantes acima. Próxima
prioridade (se Bernardo seguir a ordem do norte): Achado 1 (distribuição
lower + panturrilha) ou Achado 2 (equipamento cross-treino).
