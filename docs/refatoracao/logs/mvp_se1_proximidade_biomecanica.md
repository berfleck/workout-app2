# Log — S-E1 proximidade biomecânica cross-treino (Achado 2)

**Data**: 2026-05-28
**Branch**: `frente-s-e1-proximidade-biomecanica` (a partir de `main`,
após merge `10d3c63` filtro acessórias)
**Bloco**: 4 do roadmap CSP — Achado 2 da auditoria 2026-05-26 fechado.

**Arquivos modificados**:

- `gerador_csp.py` — constantes `PEGADA_CODE` / `PLANO_CODE` /
  `EQUIPAMENTO_CODE` + sentinelas `_*_BASE_VAZIA=100` + 3 helpers
  `_pegada_code_do_ex` / `_plano_code_do_ex` / `_equipamento_code_do_ex`
  (sentinela por slot pra dim ausente). Bloco S-E1 cross-treino em
  `_construir_modelo` após S-R1 (par-a-par cross-treino mesma-sub via
  reificação de `same_sub` + `same_dim`). Args novos
  `peso_se1_pegada / peso_se1_plano / peso_se1_eq` em 5 funções:
  `_construir_modelo`, `_resolver_legacy`, `_resolver_com_variedade`
  (+ entrada no `teto_por_termo`), `gerar_rotina_csp`,
  `gerar_treino_csp`.
- `app_flask.py` — 3 constantes `_PESO_SE1_PEGADA_DEFAULT=10`,
  `_PESO_SE1_PLANO_DEFAULT=10`, `_PESO_SE1_EQ_DEFAULT=2` + wire na
  chamada `gerar_rotina_csp` em `/gerar`. `treino_regerar` NÃO recebe
  (skip estrutural: 1 treino isolado, sem cross-treino possível —
  mesmo critério da S-R1).
- `tests/test_csp_se1_proximidade_biomecanica.py` — 6 testes novos.
- `tools/sondar_se1_proximidade.py` — sondador N=10 default sobre
  Full Body 2T `aderencia=alta` (setup exato do achado).
- `docs/refatoracao/logs/se1_proximidade_pre.json` / `se1_proximidade_pos.json`
  — snapshots PRÉ × PÓS.

**Status**: ✅ concluída. Aguarda aprovação do Bernardo para merge FF em
`main` (disciplina de merge do roadmap exige confirmação explícita).

---

## Objetivo

Fechar o **Achado 2** da auditoria 2026-05-26: pares cross-treino mesma
subregião com pegada / plano_corporal / equipamento_grupo idênticos
quando o banco oferece alternativas. Caso reportado em N=1: peito 1+1
com 2 supinos halteres + ombro 1+1 com 2 desenv halteres em
`aderencia=alta`.

Sondagem PRÉ N=10 em main (Full Body 2T região + aderência alta)
confirmou caso clínico mensurável nas dims agregadas:

| Métrica | PRÉ peso=0 (main) |
|---|---:|
| `pct_pegada_repetida_cross_treino` | **100.0%** |
| `pct_plano_repetido_cross_treino` | **100.0%** |
| `pct_eq_repetido_cross_treino` | 40.0% |
| `pct_supinos_halteres_repetido` (peito 1+1) | 10.0% |
| `pct_desenv_halteres_repetido` (ombro 1+1) | 0.0% |
| `tempo_p50_s` | 0.79s |

As métricas SPECIFIC reportadas na auditoria N=1 (halteres+halteres em
peito/ombro) caíram pra ~10%/0% em N=10 — confirma que **a auditoria
N=1 capturou casualidade**; o problema clínico real está nas dims
**agregadas** (100% pegada / 100% plano), que S-E1 ataca diretamente.

Causa estrutural: motor antigo tinha `_score_proximidade` que
penalizava INTER ~0.8 × INTRA dessas 3 dimensões (Seção 8.9/D3.1 da
`dimensoes_proximidade.md`). Motor CSP só tinha S-B5 (regiao
INTRA-bloco) e S-B1 (agonistas INTRA-bloco) — zero soft cross-treino
pra proximidade biomecânica.

---

## Decisões fechadas (pré-código, texto livre)

### §3.1 Granularidade — par cross-treino `(s1, s2)` mesma-subregião

Mais simples do que "par × subregião" proposto no handoff. Captura
diretamente o caso clínico do Achado 2 (peito 1+1 = 1 par s1+s2
cross-treino mesma sub; ombro 1+1 idem) e generaliza grátis pra subs
com >1 slot por treino. Modelagem direta: penalty linear sobre 3
BoolVars (same_pegada / same_plano / same_eq) reificada com same_sub.

### §3.2 Dimensões — `pegada` + `plano_corporal` + `equipamento_grupo`

Concordamos com a proposta. Família / lateralidade / variante_pontual
já cobertas (H-T1/T2/T3 + `familias_proibidas` da Frente E.1).

### §3.3 Pesos — **binário (não matriz 4×4)** + 10/10/2 inicial

**Descoberta durante leitura preparatória**: pegada **JÁ é binária**
no motor antigo, não matriz 4×4 como o handoff (escrito olhando a
spec Etapa 6 inicial) sugeria. Docstring de
`gerador_treino._score_proximidade:2217` registra: _"Pegada: D2.1
fechou em **constante por dim**, não matriz 4×4. Calibração numérica
final em 7.6."_ Impl real ([gerador_treino.py:2247](../../gerador_treino.py#L2247))
faz `if cand.pegada == outro.pegada: total += peso`. Match binário,
igual `plano_corporal` e `equipamento_grupo`.

Isso elimina toda complexidade de IntVar/mapping específico do §4.1
do handoff. 3 BoolVars reificadas + penalty linear bastam.

**Magnitudes calibradas via sondagem (3 tentativas)**:
- **10/10/2 (escolhido)** — zera todas as 5 métricas, p50=1.65s
- 5/5/1 — também zera 5/5, p50=1.68s
- 3/3/1 — também zera 5/5, mas p50=1.89s e max=3.21s (pesos baixos
  ampliam slack na Phase 2 da variedade, mais soluções enumeradas)

Decisão final pesos **10/10/2** por: (i) consistência com escala
do projeto (`peso_sa1=12`, `peso_sa1_repet=10`, `peso_sb5=peso_sr1=4`),
(ii) tempo p50 melhor, (iii) margem clínica larga. Proporção 5:1
ALTO:BAIXO preserva semântica da Seção 1.5 (equipamento_grupo é
tiebreaker BAIXO; pegada e plano são ALTO).

### §3.4 Escopo "mesma subregião" — preservado via reificação

`same_sub` BoolVar criada UMA vez por par cross-treino, multiplicada
no AND com `same_dim` no `OnlyEnforceIf`. Halteres vs barra IMPORTA
em supino (mesmo peito), NÃO importa em passada (perna_anterior
unilateral — `same_sub` true, mas pegada/plano N/A via sentinela por
slot → `same_pegada` false). Decisão clínica fechada na Etapa 6,
intocada.

### §3.5 Default ON sem toggle UI — aceito

Igual S-R1, S-B5, S-A1. UI sem toggle. Calibração via sondagem.

### §3.6 Modulação por Aderência ao Tier — skip

Aderência atual é binária no CSP (alta=2 / media=baixa=0), calibração
DESCONTINUADA em 2026-05-26 (memory `calibracao_aderencia_descontinuada`).
S-E1 entra com peso fixo. Refinamento futuro quando aderência virar
gradual de novo.

---

## Implementação

### `gerador_csp.py` — constantes + helpers

```python
PEGADA_CODE: dict[str, int] = {
    "aberta": 1, "neutra": 2, "pronada": 3, "supinada": 4,
}
_PEGADA_BASE_VAZIA: int = 100  # > max(PEGADA_CODE.values())

PLANO_CODE: dict[str, int] = {
    "apoiada": 1, "baixa_sentada": 2, ..., "unilateral_apoiada": 10,
}
_PLANO_BASE_VAZIA: int = 100

EQUIPAMENTO_CODE: dict[str, int] = {
    "banda_elastica": 1, "barra": 2, ..., "polia": 8,
}
_EQUIPAMENTO_BASE_VAZIA: int = 100

def _pegada_code_do_ex(ex, sid_fallback):
    if not ex.pegada:
        return _PEGADA_BASE_VAZIA + sid_fallback  # único por slot
    return PEGADA_CODE.get(ex.pegada, _PEGADA_BASE_VAZIA + sid_fallback)
```

**Sentinela por slot** (decisão de implementação): ex sem dim
cadastrada recebe code `BASE_VAZIA + sid`. Dois slots vazios em sids
diferentes recebem codes distintos → `same_X` BoolVar reifica false
naturalmente, sem precisar BoolVar de validade adicional. Espelha o
predicado `cand.X and outro.X and cand.X == outro.X` do
`_score_inter` antigo. Resolve naturalmente o "halteres vs barra
NÃO importa em passada" — em perna_anterior, todos os squats têm
pegada vazia (`_SUBREGIOES_PEGADA_NA` da Etapa 6); codes sentinela
distintos → same_pegada false sem precisar lógica explícita.

### `_construir_modelo` — bloco S-E1 (após S-R1, antes S-B4)

```python
usa_se1 = (peso_se1_pegada > 0 or peso_se1_plano > 0 or peso_se1_eq > 0)
if usa_se1 and len(treinos) >= 2:
    # IntVars por slot pra cada dim ativa (skip se peso=0).
    pegada_idx, plano_idx, eq_idx = {}, {}, {}
    for s in slots_globais:
        pool, sid = s["pool_slot"], s["sid"]
        if peso_se1_pegada > 0:
            codes = [_pegada_code_do_ex(ex, sid) for ex in pool]
            lo, hi = (min(codes), max(codes))
            pi = model.NewIntVar(lo, hi, f"se1_peg_t{s['t_idx']}_s{sid}")
            model.Add(pi == sum(assign[(sid, c)] * codes[c] for c in range(len(pool))))
            pegada_idx[sid] = pi
        # análogo plano_idx, eq_idx

    # Loop sobre pares cross-treino (t1 < t2).
    for t1 in range(len(treinos)):
        sids_t1 = slots_por_treino.get(t1, [])
        for t2 in range(t1 + 1, len(treinos)):
            sids_t2 = slots_por_treino.get(t2, [])
            for sid1 in sids_t1:
                subs1 = {ex.subregiao for ex in slot_por_sid[sid1]["pool_slot"]}
                for sid2 in sids_t2:
                    subs2 = {ex.subregiao for ex in slot_por_sid[sid2]["pool_slot"]}
                    if not (subs1 & subs2):
                        continue  # par nunca tem same_sub true → skip
                    same_sub = model.NewBoolVar(f"se1_samesub_{sid1}_{sid2}")
                    model.Add(subregiao_idx[sid1] == subregiao_idx[sid2]).OnlyEnforceIf(same_sub)
                    model.Add(subregiao_idx[sid1] != subregiao_idx[sid2]).OnlyEnforceIf(same_sub.Not())

                    for dim_tag, peso, idx_dict in (
                        ("peg", peso_se1_pegada, pegada_idx),
                        ("pla", peso_se1_plano, plano_idx),
                        ("eq", peso_se1_eq, eq_idx),
                    ):
                        if peso <= 0:
                            continue
                        same_dim = model.NewBoolVar(f"se1_same{dim_tag}_{sid1}_{sid2}")
                        model.Add(idx_dict[sid1] == idx_dict[sid2]).OnlyEnforceIf(same_dim)
                        model.Add(idx_dict[sid1] != idx_dict[sid2]).OnlyEnforceIf(same_dim.Not())
                        viol = model.NewIntVar(0, peso, f"se1_pen_{dim_tag}_{sid1}_{sid2}")
                        model.Add(viol >= peso).OnlyEnforceIf([same_sub, same_dim])
                        penalidades.append(viol)
```

### `app_flask.py` — defaults e wire

```python
_PESO_SE1_PEGADA_DEFAULT = 10
_PESO_SE1_PLANO_DEFAULT = 10
_PESO_SE1_EQ_DEFAULT = 2

# Em /gerar (gerar_rotina_csp):
resultado_csp = gerar_rotina_csp(
    ..., peso_sr1=_PESO_SR1_DEFAULT,
    peso_se1_pegada=_PESO_SE1_PEGADA_DEFAULT,
    peso_se1_plano=_PESO_SE1_PLANO_DEFAULT,
    peso_se1_eq=_PESO_SE1_EQ_DEFAULT,
)
```

---

## Resultado da sondagem PRÉ × PÓS

### Tabela comparativa (N=10, Full Body 2T região aderência alta)

| Métrica | PRÉ peso=0 | PÓS 10/10/2 | Δ |
|---|---:|---:|---|
| `pct_supinos_halteres_repetido` | 10.0% | **0.0%** ✅ | -10.0pp |
| `pct_desenv_halteres_repetido` | 0.0% | 0.0% | — |
| `pct_pegada_repetida_cross_treino` | 100.0% | **0.0%** ✅ | -100.0pp |
| `pct_plano_repetido_cross_treino` | 100.0% | **0.0%** ✅ | -100.0pp |
| `pct_eq_repetido_cross_treino` | 40.0% | **0.0%** ✅ | -40.0pp |
| `tempo_p50_s` | 0.79s | 1.65s | +0.86s (~2x) |
| `inviaveis` | 0/10 | 0/10 | 0 |

**5/5 métricas zeram com pesos 10/10/2.** Zero inviabilidade.

### Calibração intermediária (sondas extras)

| Pesos | pegada/plano/eq | rep | p50 |
|---|---|---:|---:|
| 10/10/2 | **0%/0%/0%** | escolhido | 1.65s |
| 5/5/1 | 0%/0%/0% | sem ganho | 1.68s |
| 3/3/1 | 0%/0%/0% | tempo piora | 1.89s, max 3.21s |

Tendência inversa entre peso e tempo p50: pesos baixos ampliam slack
da Phase 2 (mais soluções enumeradas dentro do bound), pesos altos
filtram cedo. 10/10/2 melhor em tempo + clinicamente consistente
com escala do projeto.

### Smoke E2E (Flask test client POST /gerar)

`POST /gerar` Full Body 2T (3 demandas região × 2 treinos), defaults
da UI:

```
HTTP 200, 2 sessoes geradas, 8 exs cada
T1.peito = Crossover Sentado (polia)
T2.peito = Supino Smith Inclinado (barra_guiada)
```

Equipamentos diferentes cross-treino em peito no flow real ✓.

---

## Gate de fechamento

| Métrica | Resultado |
|---|---|
| pytest (`tests/`) | **370 passed + 1 skipped** (364 base + 6 novos em `test_csp_se1_proximidade_biomecanica.py`) ✓ |
| 13 snapshots | ✓ preservados |
| Harness 16/16 | ✓ 16/16 OK (motor antigo intocado; 2 NO-OPs informativos preservados: 2.3 banco-limitado, 4.1 viés distribuição pós-CORE) |
| Sondagem pós | ✓ 5/5 métricas zeram (100% pegada / 100% plano / 40% eq / 10% supinos hlt / 0% desenv hlt → 0% / 0% / 0% / 0% / 0%) |
| Smoke E2E (Flask test client) | ✓ POST /gerar Full Body 2T → equipamentos distintos cross-treino |
| Motor antigo | Intocado ✓ |
| `dimensoes_proximidade.md` | Lida (REFERÊNCIA VIVA) — pesos calibrados antigos consultados; binário (D2.1) honrado ✓ |
| `pesos_proximidade.py` | NÃO importado pelo CSP — caminho (b) do §4.2 do handoff (independência arquitetural) ✓ |

---

## Achados / sinais de alerta

1. **Pegada em peito empurrar_compostos é uniformemente pronada no
   banco** — todos os supinos têm pegada=pronada (Apoio, Reto, Smith
   Inclinado, etc). S-E1 não tem como alternar pegada em `peito(1)×2T`
   isolado; só consegue alternar equipamento. Teste (b) reformulado
   pra medir equipamento (dim alternável) em vez de pegada (uniforme).
   Lição: granularidade de testes precisa refletir a estrutura real
   do banco — auditar antes de assertir.

2. **Auditoria N=1 capturou casualidade nas métricas SPECIFIC** —
   "supinos halteres repetido" 100% N=1 vs 10% N=10. O problema
   clínico real está nas dims AGGREGATE (100% pegada / 100% plano).
   S-E1 ataca diretamente a causa biomecânica, não o sintoma específico
   da rotina auditada. Mesmo padrão da S-R1 (panturrilha N=1=0% vs
   N=5=60-80%).

3. **Sentinela por slot é elegante mas exige cuidado**:
   `BASE_VAZIA + sid` garante codes distintos entre slots vazios.
   Espelha exatamente o predicado `cand.X and outro.X and cand.X ==
   outro.X` do antigo, sem precisar BoolVar de validade adicional
   nem manter mapping de `_SUBREGIOES_X_NA` explícito no CSP. Banco
   cadastra dim vazia em subs onde N/A (Seção 7 dimensoes_proximidade),
   e a sentinela aproveita isso automaticamente.

4. **Discrepância handoff vs spec real** — handoff escrito com base na
   Etapa 6 inicial mencionava "matriz pegada 4×4" como complexidade
   estrutural; spec real (D2.1, Sessão 8 da Etapa 6, 2026-05-09)
   simplificou pra constante por dim. Validação pré-código evitou
   complexidade desnecessária (norte §5: caminhos mais simples
   quando não regridem). Lição: ler `gerador_treino._score_proximidade`
   real, não só dimensoes_proximidade.md (que registra spec evolutiva).

5. **Tempo p50 dobrou (~0.79s → ~1.65s)** — esperado: S-E1 adiciona
   BoolVars + IntVars por par cross-treino mesma-sub. Aceitável pra
   UI hobby (<2s p50 em Full Body 2T). Cresce com tamanho da rotina;
   se ABC 3T ficar lento, otimizar pulando pares onde subs1 ∩ subs2
   é pequeno (já implementado: pares sem intersecção pulados).

6. **`treino_regerar` NÃO recebe S-E1** — `/regerar` chama
   `gerar_treino_csp` com 1 treino, `len(treinos) < 2` → skip
   estrutural natural. Pra cobrir caso "regerar T2 mantendo
   biomecânica distinta de T1 fixo", seria preciso passar slots
   virtuais cross-treino. Out of scope desta frente (mesma decisão
   da S-R1). Pode ser reabrir se auditoria mostrar caso real.

7. **Achado 2 totalmente fechado**. Acessórios pendentes do Bloco 4:
   - Achado 4 (calibração aderência) — descontinuado em 2026-05-26.
   - Gate de avaliação clínica semântica — não-bloqueador.

---

## Próximos passos

- Atualizar `roadmap_csp.md` (S-E1 ✅).
- Atualizar `auditorias/2026-05-26.md` (Achado 2 → ✅).
- Atualizar `catalogo_constraints.md` (entrada S-E1 ROTINA, entre
  S-R1 e S-R2).
- Atualizar `MEMORY.md` (novo memory file `project_frente_s_e1.md`).
- Commit seletivo + push + aguardar aprovação Bernardo pra merge FF.
