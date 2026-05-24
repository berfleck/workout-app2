# Log — MVP Fatia 4.B: S-B1 (distância funcional intra-bloco) + evitar_agonistas

**Data**: 2026-05-24
**Branch**: `fatia-4b-sb1-pareamento` (a partir de `fatia-4a-blocos-estrutural`)
**Arquivos modificados**:
- `gerador_csp.py` (import GRUPO_MUSCULAR_PADRAO + GRUPO_FUNC_CODE + grupo_func[s] IntVar + S-B1 penalty + kwarg peso_evitar_agonistas propagado)
- `app_flask.py` (`_PESO_EVITAR_AGONISTAS_DEFAULT` + `_peso_evitar_agonistas_csp` adapter + wire em treino_regerar)
- `tests/test_sb1_pareamento.py` (novo, 6 testes)

**Status**: ✅ concluída — gate verde (pytest 248 + 1 skip = 242 + 6 novos; harness 16/16 OK; smoke E2E mostra 100% redução de pares agonistas em produção).

---

## Objetivo

Implementar S-B1 (Seção 2 do catálogo, Conceito 10) — primeira soft de bloco. Resolve o achado da 4.A: blocos com 2 ou 3 ex do mesmo grupo funcional (push+push, pull+pull, quad+quad) aconteciam por sorteio livre porque motor não tinha critério clínico de pareamento.

Escopo MVP:
- Penalty fixo por par no MESMO BLOCO com MESMO GRUPO funcional (push/pull/quad/hamstring/glute/addutor/calf/core/cardio).
- Toggle `evitar_agonistas` da UI antiga mapeia em peso (True=10, False=0).
- Sem ainda implementar antagonismo refinado (peso por distância muscular específica) — basta evitar mesmo grupo.

## Decisões fechadas

1. **Reutilizar `GRUPO_MUSCULAR_PADRAO` do gerador antigo** — source of truth única, importada em `gerador_csp.py`. 9 grupos.
2. **`GRUPO_FUNC_CODE`** mapeia cada grupo único em int [1..9]; código 0 reservado pra padrões sem grupo conhecido ("outro+outro" não conta como agonista — favorável a casos de borda).
3. **`grupo_func[s]` IntVar criado SEMPRE** (mesmo com peso=0) — leve e serve de gancho pra futuras constraints. Vars não-referenciadas no objetivo CP-SAT simplifica.
4. **`same_bloco[s1,s2]` BoolVar reutilizando `lt`/`gt` da S-T1 (4.A)** — `same_bloco + lt + gt == 1` (exatamente um dos três true). Zero variáveis extras pra detectar mesmo bloco.
5. **Penalty fixo `viol_sb1 >= peso` se `same_bloco AND same_grupo`** — modelado via `OnlyEnforceIf([same_bloco, same_grupo])`. Sem gradação por "quão próximo é o agonismo" — toggle binário (alta penalidade) elimina o caso.
6. **Mapping `evitar_agonistas=True → peso=10`** — chute inicial. Smoke isolado mostrou eliminação total de agonistas (23.4% → 0%) com peso=10 em 20 runs. Margem suficiente: viol max por par S-T1 é 2; peso=10 é dominante.
7. **`peso=0` preserva 4.A byte-a-byte** — clause `if peso_evitar_agonistas > 0` skipa todas as vars novas. Gate de não-regressão garantido pelo `assert r["inversoes"] == 0` em pytest.

## O que foi implementado

### `gerador_csp.py` — constants

```python
from gerador_treino import GRUPO_MUSCULAR_PADRAO  # +1 import

_GRUPOS_UNICOS = sorted(set(GRUPO_MUSCULAR_PADRAO.values()))
GRUPO_FUNC_CODE: dict[str, int] = {g: i for i, g in enumerate(_GRUPOS_UNICOS, start=1)}
_GRUPO_OUTRO_CODE = 0

def _grupo_code_do_ex(ex): return GRUPO_FUNC_CODE.get(GRUPO_MUSCULAR_PADRAO.get(ex.padrao, ""), 0)
```

### `_construir_modelo` — `grupo_func[s]` IntVar

```python
for s in slots_globais:
    pool = grupo_por_idx[(s["t_idx"], s["di"])]["pool"]
    codes = [_grupo_code_do_ex(ex) for ex in pool]
    lo, hi = (min(codes), max(codes)) if codes else (0, 0)
    gf = model.NewIntVar(lo, hi, ...)
    model.Add(gf == sum(assign[(sid, c)] * codes[c] for c in range(len(pool))))
    grupo_func[s["sid"]] = gf
```

`AddExactlyOne` em assign garante que exatamente 1 cidx ativo → `gf = code` do ex escolhido.

### `_construir_modelo` — S-B1 penalty no loop de pares

Dentro do loop existente da S-T1 4.A (que cria `lt` e `gt` por par), branch `if peso_evitar_agonistas > 0`:

```python
same_bloco = NewBoolVar(...)
model.Add(same_bloco + lt + gt == 1)  # reusa lt/gt

same_grupo = NewBoolVar(...)
model.Add(grupo_func[s1] == grupo_func[s2]).OnlyEnforceIf(same_grupo)
model.Add(grupo_func[s1] != grupo_func[s2]).OnlyEnforceIf(same_grupo.Not())

viol_sb1 = NewIntVar(0, peso, ...)
model.Add(viol_sb1 >= peso).OnlyEnforceIf([same_bloco, same_grupo])
penalidades.append(viol_sb1)
```

### Propagação `peso_evitar_agonistas`

Em `gerar_rotina_csp`, `_resolver_legacy`, `_resolver_com_variedade` (Phase 1 + Phase 2 + fallback), `gerar_treino_csp`. Default 0 em todos.

### `app_flask.py` — adapter + wire

```python
_PESO_EVITAR_AGONISTAS_DEFAULT = 10

def _peso_evitar_agonistas_csp(cfg_r):
    if not cfg_r or not cfg_r.get("evitar_agonistas"):
        return 0
    return _PESO_EVITAR_AGONISTAS_DEFAULT
```

Em `treino_regerar`:
```python
peso_evitar_agon = _peso_evitar_agonistas_csp(cfg_r)
gerar_treino_csp(..., peso_evitar_agonistas=peso_evitar_agon)
```

## Resultado da validação

### Smoke isolado motor (20 runs)

Demanda `[("subregiao", "peito", 2), ("subregiao", "costas", 2), ("subregiao", "perna_anterior", 2)]`:

| peso | Pares totais (em 20 runs) | Pares agonistas | % agonistas |
|---|---|---|---|
| 0 (baseline 4.A) | 77 | 18 | 23.4% |
| 10 (4.B ativa) | 58 | 0 | 0.0% |

Trade-off observado: total de pares caiu (77 → 58) porque motor faz mais blocos solo pra evitar penalty. **Esperado** — 4.C (S-B4 tamanho preferido) vai dar incentivo positivo a blocos não-solos e equilibrar.

### Smoke E2E via `/regerar` (15 runs cada)

Aluno Bernardo, mesma demanda 6 slots:
- `evitar_agonistas=False` (4.A): 7 pares agonistas
- `evitar_agonistas=True` (4.B): **0 pares agonistas** (100% redução)

### Gate de fechamento

| Métrica | Resultado |
|---|---|
| pytest | **248 passed + 1 skipped** (=242 pré-4.B + 6 novos em `test_sb1_pareamento.py`) ✓ |
| 13 snapshots | ✓ preservados |
| harness | **16/16 OK** (2.3 + 4.1 NO-OPs informativos preservados) ✓ |
| Tempo pytest | 18.62s → 23.95s (~1.3x; aceitável) |
| Frente B (variedade) intacta | ✓ |
| Frente D (Aderência) intacta | ✓ — `peso=2 + peso_evitar_agon=10` rodou viável (teste e) |
| Gerador antigo | Intocado ✓ |

## Decisões fechadas (pra 4.C+)

1. **`grupo_func[s]` exposto em retorno de `_construir_modelo`** — gancho pra futuras constraints que dependem de grupo (S-T3 demanda neural? S-R1 distribuição multi-eixo? — futuras).

2. **`same_bloco` BoolVar pode ser reutilizado pela 4.C** — quando S-B4 (tamanho preferido) entrar, vai precisar contar slots por bloco. `same_bloco` por par já está pronto pra agregar.

3. **`_PESO_EVITAR_AGONISTAS_DEFAULT = 10` é chute inicial**. Empíricamente: smoke mostrou 0% agonistas com peso=10 em 20 runs. Margem ampla (peso=5 provavelmente já zera). Calibração futura via dashboard se preciso. **NÃO ativar Densidade Pareamento como modulador desta dimensão ainda** — dimensão Densidade não existe no perfil; quando entrar (Frente D parte 2 ou frente paralela), modula S-B1 (densidade alta = neutro/zerado; densidade baixa = peso maior, mais distância exigida).

4. **S-B1 elimina agonistas BINÁRIO** (mesmo grupo). Não tem gradação ainda (push+push vs push+pull "leve"). Catálogo previa "mapa de antagonismo" — abrir negociação só se evidência clínica mostrar precisão necessária maior.

5. **Toggle UI antiga (`evitar_agonistas` da cfg) é honrado**. Pra produção, isso significa que `/regerar` agora respeita o toggle do form, igual o motor antigo respeitava. Bug bonus: motor antigo aplicava o toggle só no greedy de `_buscar_candidato`; CSP aplica globalmente no objetivo.

## Achados / sinais de alerta

1. **Total de pares caiu 25%** com peso=10 — motor prefere blocos solo. Sem 4.C, rotina com agonistas no banco vai sair "diluída" (muitos solos). Aceitável pro MVP da 4.B; 4.C resolve.

2. **`grupo_func` IntVar criado SEMPRE** (mesmo com peso=0) — leve. Custo: ~N IntVars + N constraints "gf == sum(assign*code)" por rotina. CP-SAT simplifica eficientemente quando não usado no objetivo.

3. **`OnlyEnforceIf` em IntVar comparison (`!=`)** funciona no CP-SAT mas é custoso conceitualmente — modela como `Not(==)` internamente. Tempo de solve não regrediu pra pytest mas pode ficar mais lento em rotinas grandes.

4. **Não testei interação Aderência Alta + S-B1 + Variedade extensivamente** — só 1 teste de compat (test e). Smoke mais profundo se aparecer regressão.

5. **Cardio sozinho conta como grupo "cardio"** — par cardio+cardio (raro) seria agonista. Atualmente cardio raramente entra em rotinas normais; não-bloqueador.

## Pendências (4.C + paralelas)

### 4.C — S-B4 tamanho preferido + tamanho_bloco da UI

- `_construir_modelo` aceita parâmetro `tamanho_preferido: int` (vem da UI: 1/2/3).
- Pra cada bloco b, criar `tamanho_b = sum(X[s,b] for s)`. Penalty se `tamanho_b != tamanho_preferido` (ou só penaliza menor que preferido — direção a decidir).
- Adapter: `tamanho_bloco` da cfg vai pra parâmetro.
- Compensa o "trade-off solo" da 4.B: dá incentivo positivo a blocos não-solos.

### 3 micro-frentes paralelas

- `exercicios_travados` — `model.Add(assign[slot, cidx_fixo] == 1)` pra slots travados pelo user.
- `cargas_config` — nova hard H-cargas (filtro de pool por aluno, similar a H-P1).
- `relaxar_familia` — toggle pra desativar H-T1 sob falha de viabilidade.

### Frente E.0 (harness CSP × antigo) só após 4.C + 3 micro-frentes

Comparação justa requer paridade de features. Hoje (pós-4.B), motor novo cobre: H-T1/T2/T3/T4, H-R1, H-P1, S-T1, S-B1, Aderência, blocos estruturais, evitar_agonistas. Faltam pra paridade: tamanho_bloco (4.C), exercicios_travados, cargas_config, relaxar_familia. Cadastros novos (S-B2/S-B3) podem ficar pra futuro (sem impacto pra Frente E.0 comparativa).

## Próximos passos

- **4.C** — S-B4 tamanho preferido + `tamanho_bloco` da UI. Crítico pra equilibrar trade-off solo da 4.B.
- Não rodar `/regerar` em produção sem flag de aviso ao usuário até 4.C — rotinas podem sair com muitos solos.
- Não tocar `/gerar` (Frente E.1) até 4.C + 3 micro-frentes + Frente E.0 fecharem.
