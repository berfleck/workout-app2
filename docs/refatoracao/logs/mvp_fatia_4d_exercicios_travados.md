# Log — MVP Fatia 4.D: exercicios_travados no motor CSP

**Data**: 2026-05-24
**Branch**: `fatia-4d-exercicios-travados` (a partir de `main`)
**Arquivos modificados**:
- `gerador_csp.py` (novo arg `travados_por_treino` em `_construir_modelo` + 3 wrappers; pool-por-slot; bypass H-P1/H-T4/AllDifferent cross-treino entre travados)
- `app_flask.py` (`treino_regerar` lê `cfg_r["exercicios_travados"]`, garante travados em `banco_regen`, propaga pra `gerar_treino_csp`)
- `tests/test_exercicios_travados_csp.py` (novo, 9 testes cobrindo 9 decisões clínicas)
- `tools/smoke_travados.py` (novo, smoke E2E sem servidor — UI ainda não existe)

**Status**: ✅ concluída — gate verde (pytest 263 + 1 skipped = 254 base + 9 novos; harness 16/16 OK; smoke E2E 5 cenários × 10 runs com travado presente em 100% dos casos esperados).

---

## Objetivo

Implementar feature `exercicios_travados` no motor CSP novo, fechando a primeira micro-frente do Bloco 1 do roadmap. Backend antigo já suporta a feature (campo `cfg_r["exercicios_travados"]`); adapter da Frente C ignorava. Esta frente fecha paridade.

Escopo MVP:
- Cada travado tenta consumir vaga na primeira demanda compatível do treino.
- Sem demanda compatível, vira exercício EXTRA (treino N+1).
- Travado bypassa H-P1 (complexidade do nível), H-T4 (vaga única ≠ Acessório), AllDifferent global cross-treino entre travados.
- Travado PARTICIPA de S-T1 (tier-order), S-B1 (agonistas), S-B4 (tamanho bloco), Aderência ao Tier (paga penalty se Acessório + Aderência Alta).

## Decisões fechadas (AskUserQuestion inicial)

1. **Modelagem: filtra pool do slot** (caminho A). Pool por slot — slot travado tem pool de 1 elemento. Travado participa de todas as soft constraints (tier-order, agonistas, tamanho bloco, Aderência). Caminho declarativo coerente com norte: todo slot negocia ao mesmo tempo.

2. **Travado fora do pool: travado nunca some.** Bernardo rejeitou "skip + aviso" — se o personal travou, é decisão deliberada e o app precisa honrar. Caminho: replica antigo (vira extra do treino).

3. **Travado off-script vira extra.** Treino sai com N+1 exercícios. Demanda virtual `("padrao", ex.padrao, 1)` criada pra acomodar o travado e fazê-lo participar de todas as constraints.

4. **Conflito travado Acessório × Aderência Alta: hard wins.** Travado é decisão do user (hard); Aderência paga penalty desse slot mas continua atuando nos outros. Princípio do norte (Seção 5): princípio clínico do user > conveniência técnica.

5. **Bypass H-P1 + H-T4 + AllDifferent cross-treino entre travados.** Derivação direta de (2): se a regra automática barra o travado, o travado vence. AllDifferent entre travados: o motor antigo já permite que travado apareça em N treinos (Etapa B do `pre_alocar_rotina` adiciona nome ao `nomes_globais` mas não bloqueia outro travado do mesmo nome em treino diferente). Replicamos: slots travados ficam fora do AllDifferent global.

6. **Non-travados não podem usar nome travado em outro slot.** Implementado removendo nomes travados dos pools default dos slots non-travados (preventivo) — preserva unicidade efetiva sem precisar de constraint extra.

7. **Validação sem UI de browser.** UI pra travar exercício ainda não existe (pendência CLAUDE.md). Smoke script + pytest cobrem 100% do comportamento backend; substituem browser nesta frente.

## O que foi implementado

### `gerador_csp.py` — pré-processamento + pool-por-slot

Novo arg `travados_por_treino: dict[int, list[Exercicio]]` em `_construir_modelo`. Pré-processamento (~40 linhas novas):

```python
travados_por_slot_meta: dict[(t_idx, di, pos)] = Exercicio
for t_idx, demandas_orig in enumerate(demandas_por_treino):
    for ex in travados_t:
        # Tenta primeira demanda compatível (escopo cobre ex.padrao)
        for di, (nv, esc, qt) in enumerate(demandas_t):
            if di >= len(demandas_orig): continue  # só demandas reais
            if reservados[di] >= qt: continue
            if ex.padrao in _padroes_de_escopo(nv, esc):
                travados_por_slot_meta[(t_idx, di, reservados[di])] = ex
                reservados[di] += 1
                encaixou = True
                break
        if not encaixou:
            # Demanda virtual extra
            demandas_t.append(("padrao", ex.padrao, 1))
            travados_por_slot_meta[(t_idx, len(demandas_t)-1, 0)] = ex
```

Pool por slot (em vez de por grupo):

```python
for pos in range(qtd):
    ex_travado = travados_por_slot_meta.get((t_idx, di, pos))
    if ex_travado is not None:
        pool_slot = [ex_travado]
    else:
        # Remove nomes travados do pool default (preserva unicidade)
        pool_slot = [e for e in pool_default if e.nome not in nomes_travados]
    slots_globais.append({
        "sid": sid, "t_idx": t_idx, "di": di,
        "pool_slot": pool_slot, "travado": ex_travado is not None,
    })
```

Constraints refatoradas pra usar `s["pool_slot"]` em vez de `grupo_por_idx[(t,di)]["pool"]`:
assign, AllDifferent (com bypass de travados), grupo_func (S-B1), H-T1, H-T2, H-T3, tier_rank (S-T1), H-R1.

H-T4 ganha bypass explícito de slots travados (decisão 5).

Propagação de `travados_por_treino` em `gerar_rotina_csp`, `_resolver_legacy`, `_resolver_com_variedade`, `gerar_treino_csp` (wrapper de 1 treino renomeia pra `travados: list[Exercicio]` e empacota internamente).

`_decode_solucao` ganha arg opcional `slot_por_sid` — quando presente, resolve o ex escolhido via `pool_slot` (necessário pra slots travados cujo pool ≠ pool default).

### `app_flask.py` — wire em `treino_regerar`

```python
travados_cfg = list(cfg_r.get("exercicios_travados") or [])
if travados_cfg:
    # Garante que travados estão em banco_regen mesmo se cross-treino bloqueado
    nomes_no_banco_regen = {e.nome for e in banco_regen}
    for ex_trav in travados_cfg:
        if ex_trav.nome not in nomes_no_banco_regen:
            banco_regen.append(ex_trav)

resultado = gerar_treino_csp(
    demandas_csp, banco_regen, nivel_aluno=nivel, seed=...,
    variedade=ConfigVariedade(),
    peso_aderencia=peso_aderencia, peso_evitar_agonistas=peso_evitar_agon,
    tamanho_preferido=tam_pref, peso_tamanho_bloco=peso_tam,
    travados=travados_cfg or None,  # Fatia 4.D
)
```

Atualiza docstring removendo `exercicios_travados` da lista de "features ignoradas".

### `tests/test_exercicios_travados_csp.py` — 9 testes

Cada teste mapeia 1:1 com uma decisão clínica:

| Teste | Decisão |
|---|---|
| `travado_em_demanda_compativel_consome_vaga` | (a) Apoio em peito × 2 → 4 exs ao total |
| `travado_off_script_vira_extra` | (b) Apoio em pernas-only → 3 exs (2 + extra) |
| `travado_bypassa_nivel_p1` | (c) Apoio cx=3 com aluno nivel=1 → entra |
| `travado_supera_h_t4` | (d) Crossover (Acessório) em peito × 1 → entra |
| `travado_mesmo_em_dois_treinos_da_rotina` | (e) Apoio em t0 + t1 → aparece em ambos |
| `non_travado_nao_repete_nome_travado` | (f) Apoio travado em t0 → não aparece em t1 |
| `travado_participa_de_st1_tier_order` | (g) Travado Principal mantém ordem por tier |
| `sem_travados_preserva_comportamento` | (h) None/{} / sem arg → comportamento pré-4.D |
| `travado_com_variedade_ativa` | (i) Funciona com ConfigVariedade (modo /regerar) |

### `tools/smoke_travados.py` — smoke E2E sem UI

5 cenários × 10 runs cada usando o modo padrão de `/regerar` (ConfigVariedade). Output mostra distribuição de tamanho do treino + contagem de runs com travado presente. Substituto da validação browser enquanto UI pra travar não existe (pendência CLAUDE.md).

## Resultado da validação

### Smoke E2E (10 runs por cenário, modo /regerar com variedade)

| Cenário | N exs esperado | Travado presente |
|---|---|---|
| 1. Demanda compatível (Apoio em peito) | {4: 10} | 10/10 |
| 2. Off-script (Apoio em pernas) | **{3: 10}** | 10/10 |
| 3. Bypass nível (Apoio cx=3, nivel=1) | {2: 10} | 10/10 |
| 4. Bypass H-T4 (Crossover Acessório vaga única) | {1: 10} | 10/10 |
| 5. Sem travados (regressão) | {4: 10} | 0/10 (sanity) |

100% de respeito ao travado em todos os cenários, em todas as 50 runs.

### Gate de fechamento

| Métrica | Resultado |
|---|---|
| pytest | **263 passed + 1 skipped** (=254 pré-4.D + 9 novos) ✓ |
| 13 snapshots | ✓ preservados |
| harness | **16/16 OK** (2.3 + 4.1 NO-OPs informativos preservados) ✓ |
| Smoke E2E | 5/5 cenários, 50/50 runs com travado onde esperado ✓ |
| Gerador antigo | Intocado ✓ |
| Default behavior | `travados_por_treino=None` ou `{}` → byte-a-byte comportamento pré-4.D ✓ |

## Decisões fechadas (pra próximas frentes)

1. **`travados_por_treino` default `None`** em todas as funções do CSP. Preserva 4.C byte-a-byte sem flag explícito.

2. **Slot travado tem flag `travado=True`** no dict de `slots_globais`. Usado em 3 lugares: H-T4 bypass, AllDifferent bypass, debugging. Mantém clean check sem precisar comparar pool_slot.

3. **Demanda virtual extra usa nivel `padrao`**. Garante que H-T4 nunca dispara (só dispara em `subregiao` qtd=1), independente do bypass adicional. Defesa em profundidade.

4. **Nomes travados removidos dos pools non-travados** (preventivo). Mais limpo que tentar bypass de AllDifferent caso a caso. Pool default vira `[e for e in pool if e.nome not in nomes_travados]`.

5. **Adapter Flask honra cross-treino do travado** garantindo presença no `banco_regen` mesmo se outro treino já tinha o mesmo nome. Bernardo decidiu: travado supera AllDifferent cross-treino entre travados.

## Achados / sinais de alerta

1. **UI pra travar exercício ainda não existe** (pendência CLAUDE.md). Smoke script substitui browser nesta frente. Quando UI for construída, ela monta `cfg_r["exercicios_travados"]` (já consumido pelo adapter) e tudo passa a fluir end-to-end.

2. **Demanda virtual extra clinicamente OK mas pode surpreender** — personal vê treino com N+1 exs em vez de N. Decisão deliberada do Bernardo ("travado nunca some"). UI futura pode mostrar visualmente que o N+1 é extra (badge, ícone, etc) pra evitar surpresa.

3. **Travado pode contribuir pra H-R1** — se travado é vertical composto de costas e a regra costas pede cobertura vertical, ele conta. Comportamento esperado, não testado explicitamente (cobertura indireta via testes que rodam H-R1 com slot travado).

4. **Tempo de pytest cresceu modestamente** 27.27s vs 23.95s pré-4.C. Adição da Fatia 4.D + 9 testes novos. Ainda <30s.

5. **`/regerar` agora cobre paridade quase total com motor antigo**: tamanho_bloco (4.C) + evitar_agonistas (4.B) + exercicios_travados (4.D) + Aderência (Frente D) + variedade (Frente B). Faltam: cargas_config + relaxar_familia (próximas 2 micro-frentes do Bloco 1).

## Próximos passos

- **2 micro-frentes restantes do Bloco 1** (cargas_config + relaxar_familia) — independentes, mesmo tamanho, podem entrar em qualquer ordem.
- **Bloco 2** (Frente E.0 — harness comparativo CSP × antigo) — pré-requisito agora completo só faltam as 2 micro-frentes acima.
- **UI pra travar exercício** — pendência CLAUDE.md, fora do refator CSP. Backend pronto.
