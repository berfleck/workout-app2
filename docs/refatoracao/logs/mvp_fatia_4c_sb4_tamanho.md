# Log — MVP Fatia 4.C: S-B4 tamanho preferido do bloco + tamanho_bloco da UI

**Data**: 2026-05-24
**Branch**: `fatia-4c-sb4-tamanho` (a partir de `fatia-4b-sb1-pareamento`)
**Arquivos modificados**:
- `gerador_csp.py` (kwargs `tamanho_preferido` + `peso_tamanho_bloco` propagados; vars `tamanho_b/usado_b/desvio_b` + S-B4 penalty no objetivo)
- `app_flask.py` (`_PESO_TAMANHO_BLOCO_DEFAULT` + `_tamanho_e_peso_bloco_csp` adapter + wire em treino_regerar)
- `tests/test_sb4_tamanho_bloco.py` (novo, 6 testes)

**Status**: ✅ concluída — gate verde (pytest 254 + 1 skip = 248 + 6 novos; harness 16/16 OK; smoke E2E mostra motor respeitando `tamanho_bloco` da UI com 100% precisão).

---

## Objetivo

Implementar S-B4 (Seção 2 do catálogo) — segunda soft de bloco. Resolve o trade-off observado na 4.B: motor com S-B1 ativo prefere blocos solo (sem agonistas = sem penalty), entregando rotinas estatisticamente diluídas.

S-B4 dá incentivo positivo a blocos com tamanho preferido pelo user (`tamanho_bloco` da UI antiga, select 1/2/3). Motor agora equilibra: evita agonistas E respeita tamanho desejado.

Escopo MVP:
- Penalty por bloco em uso com tamanho ≠ preferido.
- Blocos vazios não contam (não inflam penalty).
- `tamanho_bloco` da UI antiga (1/2/3) mapeia direto pro parâmetro.
- Modulador Densidade Pareamento (do vetor de perfil) ainda não existe — placeholder peso fixo (5).

## Decisões fechadas

1. **Penalty proporcional ao desvio absoluto**: `pen_b = peso * |tamanho_b - tamanho_preferido|` por bloco em uso. Simétrica (pref=2 penaliza solo igual a triplo).
2. **`usado_b` BoolVar separado**: blocos vazios (tamanho=0) NÃO contam (desvio=0 quando NOT usado_b). Motor não é incentivado a fragmentar artificialmente.
3. **`tamanho_preferido` é parâmetro, não variável**: vem da UI direto pro `_construir_modelo`. Default 2.
4. **`_PESO_TAMANHO_BLOCO_DEFAULT = 5`** — não dominante (compete com S-B1=10 sem dominar). Smoke isolado mostrou 100% respeito em pref=1/2/3 com este peso.
5. **Sempre ativo quando cfg presente**: adapter `_tamanho_e_peso_bloco_csp` retorna peso=5 quando `cfg_r["tamanho_bloco"]` válido. Não há toggle separado — UI antiga sempre envia valor (default 2 no parser).
6. **peso=0 preserva 4.B byte-a-byte** via `if peso_tamanho_bloco > 0` skip de todas as vars novas.

## O que foi implementado

### `_construir_modelo` — vars + S-B4

Pra cada bloco `b` de cada treino `t`:

```python
tamanho_b = NewIntVar(0, TAMANHO_MAX_BLOCO)
model.Add(tamanho_b == sum(X[(t,sid,b)] for sid in slots_t))

usado_b = NewBoolVar()
model.Add(tamanho_b >= 1).OnlyEnforceIf(usado_b)
model.Add(tamanho_b == 0).OnlyEnforceIf(usado_b.Not())

desvio_b = NewIntVar(0, TAMANHO_MAX_BLOCO)
model.Add(desvio_b >= tamanho_b - tamanho_preferido).OnlyEnforceIf(usado_b)
model.Add(desvio_b >= tamanho_preferido - tamanho_b).OnlyEnforceIf(usado_b)
model.Add(desvio_b == 0).OnlyEnforceIf(usado_b.Not())

pen_b = NewIntVar(0, peso * TAMANHO_MAX_BLOCO)
model.Add(pen_b == peso * desvio_b)
penalidades.append(pen_b)
```

### Propagação `tamanho_preferido` + `peso_tamanho_bloco`

Em `gerar_rotina_csp`, `_resolver_legacy`, `_resolver_com_variedade` (Phase 1 + Phase 2 + fallback), `gerar_treino_csp`. Defaults `tamanho_preferido=2`, `peso_tamanho_bloco=0`.

### `app_flask.py` — adapter

```python
_PESO_TAMANHO_BLOCO_DEFAULT = 5

def _tamanho_e_peso_bloco_csp(cfg_r):
    if not cfg_r:
        return (2, 0)
    tb = cfg_r.get("tamanho_bloco")
    if tb not in (1, 2, 3):
        return (2, 0)
    return (tb, _PESO_TAMANHO_BLOCO_DEFAULT)
```

Em `treino_regerar`:
```python
tam_pref, peso_tam = _tamanho_e_peso_bloco_csp(cfg_r)
gerar_treino_csp(..., tamanho_preferido=tam_pref, peso_tamanho_bloco=peso_tam)
```

## Resultado da validação

### Smoke isolado motor (15 runs por configuração)

Demanda 6 slots (peito 2, costas 2, perna_anterior 2):

| Config | Distribuição tamanhos | Pares agonistas |
|---|---|---|
| 4.B sozinha (S-B1=10, sem S-B4) | {1: 37, 2: 19, 3: 5} (60% solo) | já 0 |
| S-B1=10 + S-B4 pref=2, peso=5 | **{2: 45}** (100%) | 0 |
| S-B1=10 + S-B4 pref=3, peso=5 | **{3: 30}** (100%) | 0 |
| S-B1=10 + S-B4 pref=1, peso=5 | **{1: 90}** (100%) | N/A (solo) |

Motor respeita 100% o tamanho preferido com peso=5 — sem precisar peso dominante.

### Smoke E2E via `/regerar` (10 runs por configuração)

| tamanho_bloco UI | evitar_agonistas | Distribuição | Agonistas |
|---|---|---|---|
| 1 | False | {1: 60} | 0 (sem pares) |
| 1 | True | {1: 60} | 0 |
| 2 | False | {2: 30} | 3 |
| **2** | **True** | **{2: 30}** | **0** ← uso típico |
| 3 | False | {3: 20} | 14 |
| 3 | True | {3: 20} | 0 |

Motor em produção entrega exatamente o que o user pede no form.

### Gate de fechamento

| Métrica | Resultado |
|---|---|
| pytest | **254 passed + 1 skipped** (=248 pré-4.C + 6 novos em `test_sb4_tamanho_bloco.py`) ✓ |
| 13 snapshots | ✓ preservados |
| harness | **16/16 OK** (2.3 + 4.1 NO-OPs informativos preservados) ✓ |
| Tempo pytest | 23.95s → 27.93s (~1.17x; aceitável) |
| Frente B (variedade) intacta | ✓ |
| Frente D (Aderência) intacta | ✓ |
| Fatia 4.A + 4.B intactas | ✓ |
| Gerador antigo | Intocado ✓ |

## Decisões fechadas (pra próximas frentes)

1. **Default `peso_tamanho_bloco=0` em todas as funções do CSP** preserva 4.B byte-a-byte. Garantia de não-regressão.

2. **`tamanho_preferido` em [1, TAMANHO_MAX_BLOCO]**: pra MVP, range = [1, 3]. Quando TAMANHO_MAX_BLOCO virar parâmetro (refator futuro), `tamanho_preferido` deve seguir.

3. **`_PESO_TAMANHO_BLOCO_DEFAULT = 5`** validado empiricamente — 100% respeito em pref=1/2/3 sem dominar S-B1.

4. **Densidade Pareamento (vetor de perfil) NÃO implementada na 4.C** — quando dimensão entrar no perfil (Frente D parte 2 ou paralela), modula peso de S-B4:
   - Densidade Alta = peso 0 (não exige tamanho fixo; aceita variedade)
   - Densidade Média = peso 5 (padrão atual)
   - Densidade Baixa = peso 15 (rígido)

5. **`tamanho_bloco` da UI antiga é honrado em produção via `/regerar`**. Quando `/gerar` migrar pro CSP (Frente E.1), mesmo adapter funciona.

## Achados / sinais de alerta

1. **Pareamento por proximidade clínica fina ainda não implementado** — S-B1 é binário (mesmo grupo OR diferente). Catálogo previa "mapa de antagonismo" pra graduar (push+pull "leve" vs "forte"). Pra MVP, binário cumpre o caso prático.

2. **S-B2 (carga implícita: core/lombar/grip/neural) e S-B3 (fadiga prévia: máquina vs livre) NÃO implementadas** — exigem cadastros novos no XLSX. Adiados como decisão consciente.

3. **Total de penalidades dominantes agora**: S-B1 (peso=10) > S-B4 (peso=5) > Aderência (peso=2 quando alta) > S-T1 (peso implícito=1, viol max=2 por par). Calibração coerente — S-B's dominam pareamento, Aderência influencia tier, S-T1 ordena blocos.

4. **Tempo de solve continua crescendo** (10.76s → 18.62s → 23.95s → 27.93s = ~2.6x desde pré-4.A). Pytest ainda <30s. Solve real de 1 rotina não medi formalmente; estimativa <300ms.

5. **`/regerar` agora está clinicamente próximo de produção real** — respeita evitar_agonistas + tamanho_bloco + Aderência ao Tier. Faltam features: `exercicios_travados`, `cargas_config`, `relaxar_familia`. Cadastros novos (S-B2/S-B3) podem ficar pra futuro.

## Pendências mapeadas (3 micro-frentes + Frente E)

### 3 micro-frentes paralelas (independentes, ~30min cada)

- **exercicios_travados** — `model.Add(assign[slot, cidx_fixo] == 1)` pra slots travados pelo user. Mecânica simples.
- **cargas_config** — nova hard H-cargas (filtro de pool por aluno baseado em config de carga), análoga a H-P1.
- **relaxar_familia** — toggle pra desativar H-T1 sob falha de viabilidade (modela como soft com peso alto OR remove hard quando flag presente).

### Frente E.0 — harness comparativo CSP × Antigo

Agora viável: motor CSP cobre paridade de features clínicas principais (pareamento, agonistas, tamanho_bloco, Aderência ao Tier). 3 micro-frentes adicionam paridade total.

### Frente E.1 — substituir `/gerar` pelo CSP

Decisão pós-Frente E.0. Pode ser parcial (manter motor antigo via flag pra A/B test em produção real).

### Refinamentos pós-Frente E

- **S-B2 + S-B3** (cargas implícitas, fadiga máquina/livre) — exigem cadastros novos.
- **Mapa antagonismo gradual** (S-B1 refinado).
- **Densidade Pareamento** (vetor) modulando S-B1 + S-B4.

## Próximos passos

- **3 micro-frentes paralelas** (exercicios_travados / cargas_config / relaxar_familia) — Bernardo escolhe ordem.
- **Frente E.0** depois — harness comparativo.
- **Frente E.1** por último.
- **`/regerar` em produção real**: agora é viável testar qualitativamente. Bernardo pode usar pra calibrar pesos por feel clínico antes de E.0/E.1.
