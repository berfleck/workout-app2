# Handoff — S-B5 diversidade de região INTRA-bloco (Achado 3 da auditoria 2026-05-26)

**Sessão**: próxima após encerramento da frente Calibração `_PESO_ADERENCIA_POR_PERFIL` (descontinuada — ver `logs/calibracao_aderencia_descontinuada.md`).

**Branch base**: a partir de `main`. Branch sugerida: `sb5-diversidade-regiao-bloco`. Disciplina de merge se aplica — 1 branch ativa por vez.

**Bloco**: 4 do roadmap CSP — primeiro item 🔴 prioritário restante da auditoria clínica 2026-05-26 (Achado 4 foi descontinuado; Achados 1 e 2 são 🟡).

**Princípio diretor da Bernardo (2026-05-26)**: *"prefiro regular o app sem diferenciar entre nível de alunos até achar um 'treino médio' adequado"*. Esta frente faz parte exatamente disso — corrige um bug clínico do treino médio que afeta TODA rotina, independente de perfil de aluno.

---

## 1. Por que esta sessão existe (achado clínico real)

Auditoria 2026-05-26 (`auditorias/2026-05-26.md` Achado 3): em rotina
Full Body 2T região com `aderencia=alta`, **4 de 8 blocos** pararam
exercícios da mesma região no mesmo bloco:

- T1 Bloco B: Passada (lower) + Stiff Uni. Smith (lower) — **2 lower**
- T1 Bloco C: Remada LM Neutra (upper) + Desenv. Halteres Uni. (upper) — **2 upper**
- T1 Bloco D: Crunch Na Bola (core) + Infra Roll-Up (core) — **2 core**
- T2 Bloco D: V-Up Unilateral (core) + Abd Bicicleta (core) — **2 core**

Crítica clínica: **superset existe para alternar grupos musculares** — um descansa enquanto o outro trabalha. Pares same-region anulam esse benefício; viram **circuito do mesmo grupo**, com fadiga cumulativa errada (acumula em vez de revezar).

**Feature perdida na migração greedy → CSP**: gerador antigo tinha geo-diversidade P1-P4 em `montar_blocos` (CLAUDE.md menciona; código antigo `gerador_treino.py` heurística ordenava blocos preferindo regiões diferentes nos slots ex1/ex2/ex3). CSP novo **não tem constraint análoga**.

O único soft pareamento intra-bloco hoje é **S-B1 distância funcional + `evitar_agonistas`** (Fatia 4.B). Mira agonistas específicos via `GRUPO_MUSCULAR_PADRAO` (push/pull/quad/hamstring/etc) — NÃO regiões diferentes em supersérie. Quando o usuário não liga `evitar_agonistas` (default OFF), nada premia diversidade de região. Mesmo com ele ligado, dois exercícios de regiões DIFERENTES (ex: lower+core) podem ter agonistas distintos e ainda assim formar circuito inapropriado.

**Bloqueia uso real**: sem fix, a recomendação é forçar `tamanho_bloco=1` manualmente (treino só de solos), o que **perde o produto "supersérie"**. Esta é a 1ª prioridade 🔴 do treino médio.

---

## 2. Leitura preparatória (na ordem)

1. **`docs/refatoracao/norte.md`** — princípios (sempre).
2. **`docs/refatoracao/roadmap_csp.md`** — Bloco 4, item "🔴 ⬜ S-B5 diversidade de região INTRA-bloco" (achado 3).
3. **`docs/refatoracao/auditorias/2026-05-26.md`** seção **Achado 3** — sintoma completo + causa estrutural + caminho proposto.
4. **`docs/refatoracao/logs/mvp_fatia_4b_sb1_pareamento.md`** — log da Fatia 4.B (S-B1 distância funcional, predecessor mais próximo arquiteturalmente). Mostra como modelar pares intra-bloco no CSP.
5. **`gerador_csp.py:1338-1370`** — bloco S-B1 ativo no `_construir_modelo`. Reusar `same_bloco` BoolVar; trocar `same_grupo` por `same_regiao`.
6. **`gerador_csp.py:677-685`** — bloco `grupo_func[s] IntVar` (mesmo padrão de modelagem que vai precisar replicar pra `regiao_idx[s]`).
7. **`gerador_csp.py:392-510`** — assinatura de `_construir_modelo` (onde vai entrar kwarg `peso_sb5`).
8. **`app_flask.py:480-500`** — onde está `_PESO_EVITAR_AGONISTAS_DEFAULT` (constante análoga ao que será criado pra S-B5).
9. **`docs/refatoracao/logs/calibracao_aderencia_descontinuada.md`** — contexto da decisão de "focar no treino médio antes de diferenciar perfis". Sessão anterior. NÃO retomar a frente da calibração.

---

## 3. Objetivo desta sessão

Introduzir constraint **S-B5 diversidade de região INTRA-bloco** no motor CSP. Bloco com 2+ exercícios da mesma região recebe penalty por par mesmo bloco + mesma região.

Resultado esperado:

- Pares same-region em blocos de 2+ exercícios: 4/8 (auditoria) → 0/8 (ou <10% como graceful degradation quando demanda força).
- Pareamento natural cross-region: upper+lower, upper+core, lower+core.
- Tamanho de bloco preservado quando possível (não regredir Fatia 4.C).
- Graceful degradation: quando demanda força same-region (ex: `upper(4)` sozinha sem outras regiões), motor aceita o pareamento same-region em vez de inviabilizar.

**NÃO é** refator do mecanismo de variedade nem mudança de fórmula do tier. **É** constraint nova no objetivo CSP, paralela ao S-B1.

---

## 4. Decisões a fechar (perguntar via texto livre — ver §10)

### 4.1 Default ON/OFF na UI

Hoje `evitar_agonistas` (S-B1) é toggle na UI default OFF (manual do usuário). Para S-B5, opções:

- **(a) Default ON sempre**, sem toggle UI — penalidade leve mas presente em qualquer rotina. Garante que mesmo usuário desavisado não recebe rotina com circuito same-region.
- **(b) Toggle UI análogo ao `evitar_agonistas`**, default ON — usuário pode desligar conscientemente para demandas single-region (upper(4) sozinha).
- **(c) Toggle UI default OFF** — usuário precisa ligar conscientemente.

Recomendação preliminar: **(a)**. S-B1 ficou default OFF por razão histórica (introduzido como opcional na Fatia 4.B), mas Achado 3 mostra que diversidade de região é clinicamente quase universal — qualquer rotina multi-região deveria ter. Toggle (b) é elegante mas só vale se Bernardo prevê demandas single-region frequentes. (c) reproduziria o problema atual.

### 4.2 Peso default

S-B1 usa `_PESO_EVITAR_AGONISTAS_DEFAULT = 10`. Para S-B5, candidatos:

- **Igual a S-B1 (peso=10)** — mesma magnitude; motor trata "mesma região" como problema da mesma classe que "mesmo agonista".
- **Menor que S-B1 (peso=5)** — diversidade de região é "menos crítica" que agonista direto; pode ser violada em troca de outros objetivos.
- **Maior que S-B1 (peso=15-20)** — diversidade de região é "mais crítica" porque captura um conjunto maior de problemas (qualquer same-region, não só same-agonist).

Recomendação preliminar: começar com **peso=10** (igual a S-B1) e medir via sondagem. Iterar se distribuição empirica indicar.

### 4.3 Granularidade da "região"

`Exercicio.regiao` no banco tem valores: `upper`, `lower`, `core`, `cardio`. Quatro grupos.

Pergunta: contar `core_isometrico` e `core_dinamico` como mesma região (core) ou diferentes? Hoje ambos são `regiao=core` no banco — então mesma. Mas semanticamente um superset core_iso+core_din pode ser mais aceitável que core_din+core_din.

Recomendação preliminar: usar **`regiao` direto do banco** (4 grupos). Não inventar granularidade nova. Refinar pra `subregiao` no futuro só se calibração indicar.

### 4.4 Interação com S-B1

S-B1 já penaliza par mesmo bloco + mesmo `GRUPO_MUSCULAR_PADRAO`. S-B5 vai penalizar par mesmo bloco + mesma `regiao`. **Pares que violam ambos** (ex: 2 push do mesmo bloco — mesmo grupo `push` E mesma região `upper`) recebem penalty dupla.

Não é necessariamente errado — par "duplamente ruim" deve pesar mais. Mas vale conferir empiricamente que peso=10+10=20 não dispara cascata estranha (ex: motor preferir 4 blocos solo em vez de 2 duplas válidas). Recomendação: medir via sondagem pós-implementação.

### 4.5 Granularidade da sondagem

Sugestão: 5-10 rotinas por config (Full Body 2T região, upper(3)×2T, ABC 3T, perna_ant+post — 4 configs canônicas do harness E.0). Métrica primária: % blocos com 2+ exs same-region. Alvo: <10% (vs ~50% pré-fix observado na auditoria).

---

## 5. Spec técnica (rascunho de implementação)

### 5.1 Nova variável `regiao_idx[s]`

Em `_construir_modelo`, espelhando `grupo_func[s]` em `gerador_csp.py:677-685`:

```python
# Mapping: regiao_str → int code (ex: upper=0, lower=1, core=2, cardio=3)
_REGIAO_CODE = {"upper": 0, "lower": 1, "core": 2, "cardio": 3}

# Variável por slot:
regiao_idx: dict[int, cp_model.IntVar] = {}
for s in slots_globais:
    ri = model.NewIntVar(0, 3, f"regiao_idx_s{s['sid']}")
    pool = ...  # já existe via grupo_pool_por_sid
    codes = [_REGIAO_CODE[ex.regiao] for ex in pool]
    model.Add(ri == sum(assign[s['sid'], c] * codes[c] for c in range(len(pool))))
    regiao_idx[s['sid']] = ri
```

Sempre criar (independente de `peso_sb5` ativo) — leve, espelha pattern do grupo_func.

### 5.2 Constraint soft

Espelhando bloco S-B1 em `gerador_csp.py:1338-1370`:

```python
# Para cada par (s1, s2) com s1 < s2 do mesmo treino:
if peso_sb5 > 0:
    same_bloco = ...  # já criado pela S-B1 ou recriar
    same_regiao = model.NewBoolVar(f"sr_{s1}_{s2}")
    model.Add(regiao_idx[s1] == regiao_idx[s2]).OnlyEnforceIf(same_regiao)
    model.Add(regiao_idx[s1] != regiao_idx[s2]).OnlyEnforceIf(same_regiao.Not())

    sb5_par = model.NewBoolVar(f"sb5par_{s1}_{s2}")
    model.AddBoolAnd([same_bloco, same_regiao]).OnlyEnforceIf(sb5_par)
    # penalty:
    penalidades.append(sb5_par * peso_sb5)
```

Reusar `same_bloco` da S-B1 quando ambos ativos. Refatorar pra criar `same_bloco` antes do branch de S-B1 (uma vez por par) se necessário.

### 5.3 Kwarg novo em `_construir_modelo`

```python
def _construir_modelo(
    ...,
    peso_evitar_agonistas: int = 0,
    peso_sb5: int = 0,   # NOVO
    ...
):
```

Propagar pelas 4 funções resolver: `_resolver_legacy`, `_resolver_com_variedade`, `gerar_rotina_csp`, `gerar_treino_csp`. Mesmo pattern da Frente D / Fatia 4.B / 4.C.

### 5.4 Constante e adapter em `app_flask.py`

```python
# Fatia 4.D-bis (2026-05-26) — S-B5 diversidade de região INTRA-bloco.
# Peso int passado ao CSP por default. Default ON (decisão 4.1).
_PESO_SB5_DEFAULT = 10
```

Wire em `treino_regerar` E adapter rotina-inteira da `/gerar`. Análogo a `peso_evitar_agonistas`.

### 5.5 UI (depende da decisão 4.1)

- (a) Default ON sempre: zero código UI novo.
- (b) Toggle UI: 1 checkbox novo em `templates/treinos.html` (form principal); leitura em `/gerar` e `/regerar`.
- (c) Default OFF + toggle: igual a (b).

### 5.6 Tests novos

Pelo menos 4 testes em `tests/test_csp_sb5_diversidade_regiao.py`:

1. **`test_par_same_region_penalizado`**: rotina pequena com 2 upper na mesma demanda força bloco com 2 upper; mede penalty > 0.
2. **`test_par_cross_region_zero_penalty`**: rotina com 1 upper + 1 lower no mesmo bloco; penalty = 0.
3. **`test_graceful_demanda_single_region`**: demanda `upper(4)` com `tamanho_preferido=2`, peso_sb5=10; motor produz rotina viável (não inviabiliza) com pares same-region (forçados).
4. **`test_sb5_off_preserva_comportamento`**: peso_sb5=0; rotina idêntica byte-a-byte ao baseline pré-S-B5 (regression test).

Opcionais (se couber):
- **`test_interacao_com_sb1`**: par mesmo bloco + mesmo grupo (push+push) recebe penalty dupla.
- **`test_smoke_full_body_2t`**: replica achado da auditoria 2026-05-26. N=10 rotinas; conta % blocos same-region. Alvo: <10% (vs ~50% pré-fix).

---

## 6. Validação esperada (gate de fechamento)

### 6.1 Sondagem comparativa pré × pós

Script novo `tools/sondar_sb5_diversidade.py` (espelha pattern de outros sondares). Mede em 4 configs canônicas (Full Body 2T região, upper(3)×2T, ABC 3T, perna_ant+post) com N=10 cada:

- % blocos com 2+ exs same-region (alvo: <10%)
- Total de blocos solo (pra ver se motor "fugiu pra blocos solo" — regressão da Fatia 4.C)
- Tempo p50 (sanity check, não deve regredir muito)

Persistir `logs/sb5_pre.json` (rodar com peso_sb5=0) e `logs/sb5_pos.json` (rodar com peso_sb5=10). Comparar lado-a-lado em log da frente.

### 6.2 Pytest

Baseline 348 testes preservados + 4-6 testes novos = 352-354. Snapshots devem regenerar; mudanças esperadas em rotinas geradas (motor agora evita same-region quando antes aceitava).

### 6.3 Harness 16/16

Sem regressão funcional. Se algum cenário ficou estatísticamente diferente (provável: cenários que testavam pareamento intra-bloco), revisar caso a caso. Ajustar tolerância se for shift benigno.

### 6.4 Harness E.0

Rerodar `tools/harness_comparativo_e0.py`. Métrica nova candidata: "% blocos same-region". Atualizar relatório se já existir do dia ou criar `E0_2026-05-26_pos_sb5.md`.

### 6.5 Smoke E2E manual via browser

Gerar 2-3 rotinas Full Body 2T região com Aluno Teste. Verificar visualmente que blocos misturam regiões (upper+lower em bloco A, etc). Era 4/8 blocos same-region pré-fix; alvo qualitativo: nenhum bloco com 2 exercícios da mesma região (ou raramente).

---

## 7. Arquivos a mexer

- `gerador_csp.py` — `_construir_modelo` (constraint nova) + `_resolver_legacy` + `_resolver_com_variedade` + `gerar_rotina_csp` + `gerar_treino_csp` (propagação de kwarg). ~30-50 linhas líquidas.
- `app_flask.py` — constante `_PESO_SB5_DEFAULT` + wire em `treino_regerar` + wire em adapter rotina-inteira `/gerar`. ~5-10 linhas.
- `tests/test_csp_sb5_diversidade_regiao.py` — novo, 4-6 testes (~120-180 linhas).
- `tools/sondar_sb5_diversidade.py` — novo, ~100 linhas espelhando pattern de outros sondares.
- `docs/refatoracao/logs/sb5_pre.json` + `sb5_pos.json` — snapshots.
- `docs/refatoracao/logs/mvp_sb5_diversidade_regiao_bloco.md` — log da frente.
- `docs/refatoracao/roadmap_csp.md` — marcar ✅ no item S-B5 do Bloco 4 + 1 linha em "Frentes concluídas".
- `docs/refatoracao/auditorias/2026-05-26.md` Achado 3 — atualizar status pra ✅ (linkando log da frente).
- `MEMORY.md` — 1 linha registrando frente concluída.
- (Opcional, depende decisão 4.1) `templates/treinos.html` — toggle UI novo.

**NÃO mexer**:
- Mecanismo de tier / aderência (frente descontinuada anterior).
- S-B1 (Fatia 4.B) — só reusar variáveis se útil.
- Motor antigo `gerador_treino.py` — refator é só CSP.

---

## 8. Restrições / não-fazer

- **NÃO retomar a frente Calibração `_PESO_ADERENCIA_POR_PERFIL`** — descontinuada (ver log). Default atual `{alta:2, media:0, baixa:0}` permanece em produção desta frente.
- **NÃO inventar nova granularidade de região** (ex: dividir `upper` em `upper_push`/`upper_pull`) — usar `regiao` do banco direto. Refinar só se calibração indicar.
- **NÃO mergear em main sem aprovação explícita do Bernardo.**
- **NÃO usar `--no-verify` ou flags que pulem hooks.**
- **Commit seletivo** (`git add <arquivo>`, NUNCA `-A`). Antes de commitar: `git status` + `git diff --cached`.
- **NÃO usar AskUserQuestion em tópico exploratório** — ver `[[feedback-askquestion-exploratorio]]`. Em decisão de design (ex: default ON/OFF), texto livre com pros/contras é melhor.
- **Cuidado com regressão da Fatia 4.C** (tamanho preferido de bloco). Se motor começar a fazer muitos blocos solo pra evitar same-region, S-B5 está dominando S-B4. Calibrar peso pra evitar.

---

## 9. Pendências NÃO incluídas nesta frente

- **🟡 Achado 1 da auditoria 2026-05-26** — distribuição lower 2:1 + panturrilha zerada. Combina aleatorização de Hamilton + soft cross-treino S-R1 + decisão clínica sobre `panturrilha.obrigatoria`. ~2 sessões.
- **🟡 Achado 2 da auditoria 2026-05-26** — equipamento repetido cross-treino. Eixo S-E1 novo. Depende de S-B5 e S-R1 entrarem (interação de pesos). ~1-2 sessões.
- **Gate de avaliação clínica semântica** (Bloco 4) — pré-requisito do Bloco 5. Continua aberto independente desta frente.
- **❌ Calibração `_PESO_ADERENCIA_POR_PERFIL`** (Achado 4 — DESCONTINUADA). Pode ser retomada quando treino médio estiver sólido + cadastro XLSX refinar tier além de saturação binária.

---

## 10. Como abrir a sessão

Primeira mensagem da sessão deve:

1. Confirmar que leu norte.md + roadmap_csp.md + auditoria 2026-05-26 (Achado 3) + log Fatia 4.B (S-B1) + log calibração descontinuada + `gerador_csp.py:1338-1370` (S-B1) + `:677-685` (grupo_func) + `:392-510` (assinatura `_construir_modelo`) + `app_flask.py:480-510` (constantes).
2. Confirmar entendimento das 5 decisões pendentes (§4) e do trade-off "qualidade clínica de bloco (diversidade) vs tamanho de bloco preferido (Fatia 4.C)".
3. **Recomendar config concreta** (não AskUserQuestion — texto livre) baseada nas recomendações preliminares: default ON, peso=10, granularidade `regiao` do banco. Algo como: "vou com (a)+peso=10+regiao-direto; ok?".
4. Após confirmação, implementar na ordem:
   - 5.1 (regiao_idx[s] variável)
   - 5.2 (constraint soft)
   - 5.3 (propagação de kwarg)
   - 5.4 (adapter)
   - 5.5 (UI opcional, depende decisão 4.1)
   - 5.6 (testes)
5. Rodar sondagem pré (peso_sb5=0) ANTES da implementação, em main. Persistir baseline.
6. Aplicar implementação na branch.
7. Rodar sondagem pós (peso_sb5=10). Persistir.
8. Comparar lado-a-lado. Mostrar tabela ao Bernardo.
9. Pytest + harness 16/16 + smoke E2E.
10. Commit + push + merge FF (após aprovação).

Não codar antes da confirmação textual das decisões. Não codar antes de rodar a sondagem pré.

**Tempo estimado**: 1-2 sessões (~2-3h). Sondagem ~10min cada, implementação ~1h, testes ~30min, validação ~30min.

---

## 11. Contexto importante da sessão anterior (2026-05-26)

Frente Calibração foi tentada e descontinuada por estes motivos (resumo para evitar reabrir):

1. Fórmula `(rank_max - tier_rank[s]) * peso_aderencia` é binária na prática — pesos 1..10 produzem distribuição idêntica.
2. Combinar `peso + slack + temperatura` entrega gradação suave mas introduz Acessórios fora de contexto no bloco A em ~10% das rotinas.
3. Bernardo decidiu priorizar o **treino médio** antes de diferenciar perfis. Esta frente S-B5 é exatamente isso — corrige bug clínico que afeta TODA rotina.

Scripts da sessão anterior preservados em `tools/` (sondar_aderencia_calibracao.py, simular_perfis_aderencia.py, inspecionar_rotina_por_peso.py) — podem ser reutilizados ou descartados quando a frente da calibração for retomada (não nesta sessão).
