# Handoff — Achado 1 da auditoria 2026-05-26 (distribuição lower 2:1 + panturrilha zerada)

**Sessão**: próxima após encerramento da frente S-B5 (mergeada em main 2026-05-27).

**Branch base**: a partir de `main`. Branch sugerida: `achado-1-distribuicao-lower`.
Disciplina de merge se aplica — 1 branch ativa por vez.

**Bloco**: 4 do roadmap CSP — primeiro item 🟡 prioritário restante da auditoria
clínica 2026-05-26. Pós-S-B5 (Achado 3 fechado), Achado 4 descontinuado
e Achado 2 depende de S-R1, este é o próximo lógico.

**Princípio diretor do Bernardo (2026-05-26)**: *"prefiro regular o app sem
diferenciar entre nível de alunos até achar um 'treino médio' adequado"*.
Esta frente continua exatamente nisso — corrige bug clínico do treino médio.

---

## 1. Por que esta sessão existe (achado clínico real)

Auditoria 2026-05-26 (`auditorias/2026-05-26.md` Achado 1): em rotina
Full Body 2T região com demanda `regiao lower(3)`:

- **T1 lower**: 2 perna_anterior + 1 perna_posterior + 0 panturrilha
- **T2 lower**: 2 perna_anterior + 1 perna_posterior + 0 panturrilha

Ambos os treinos caem no MESMO split em CADA uma das 2 rodadas
(aderência média e aderência alta). Distribuição total da rotina:
4 anterior + 2 posterior + 0 panturrilha em 6 slots.

**Críticas clínicas**:

1. **Distribuição assimétrica entre treinos**. Para 6 slots de lower, a
   distribuição ideal seria 3+3 anterior/posterior. Mesmo aceitando 2+1
   por treino (forçado pela paridade), a rotina deveria ALTERNAR entre
   treinos: T1=2+1 + T2=1+2. Como está, anterior é trabalhado 2× mais
   que posterior na rotina inteira.
2. **Panturrilha nunca aparece**. Usuário pediu `lower` abrangente; o
   motor decide silenciosamente que panturrilha não vale a pena.

**Bloqueia uso real**: não totalmente — é 🟡 (qualidade clínica
perceptível mas não destrutiva). Mas em rotinas Full Body geradas pela
UI default, panturrilha some 100% do tempo, e a assimetria entre treinos
empilha volume desigual entre quadríceps e posterior em mesociclos.

---

## 2. Leitura preparatória (na ordem)

1. **`docs/refatoracao/norte.md`** — princípios (sempre).
2. **`docs/refatoracao/roadmap_csp.md`** — Bloco 4, item "🟡 ⬜ S-R1
   cross-treino para distribuição subregião dentro de região" e
   "⬜ Repensar panturrilha.obrigatoria=False".
3. **`docs/refatoracao/auditorias/2026-05-26.md`** seção **Achado 1** —
   sintoma completo + causa estrutural + 3 caminhos propostos.
4. **`docs/refatoracao/logs/mvp_sb5_diversidade_regiao_bloco.md`** — log
   da frente anterior (mais imediato), mostra como modelar penalty
   par-a-par no CSP. **Pode reaproveitar o pattern do `regiao_idx[s]`
   pra um `subregiao_idx[s]`** mas a granularidade aqui é cross-treino
   (não intra-bloco), modelagem diferente.
5. **`docs/refatoracao/logs/frente_s_a1.md`** — log S-A1 (predecessor
   arquitetural mais próximo). S-A1 é INTRA-treino entre âncoras
   não-obrigatórias; S-R1 será CROSS-treino. Padrão de modelagem similar
   (penalty no objetivo proporcional a desbalanço).
6. **`gerador_treino.py:142-157`** — `ANCORAS_POR_REGIAO` (lower tem
   ant=2, post=2, panturrilha=1 não-obrigatória).
7. **`gerador_treino.py:277-363`** — `calcular_quotas` (Hamilton's
   Largest Remainder). Note que **já existe `random.random()` no
   tie-break** (linha 355) — primeira coisa a verificar: o bug é o
   filtro pré-Hamilton (linhas 2989-2996 de `_decompor_demanda_regiao`)
   que tira panturrilha antes do sorteio, NÃO o Hamilton em si.
8. **`gerador_treino.py:2950-3017`** — `_decompor_demanda_regiao`. **A
   regra crítica está em 2990**: `if n_obrig > 0 and qtd <= 2 * n_obrig`
   filtra acessórias quando vagas são "poucas". Em `lower(3)`,
   `n_obrig=2`, `2*2=4`, `3<=4` → panturrilha cai antes do Hamilton.
9. **`gerador_csp.py:1294-1310`** — set `pares_intra_sub` (S-A1) — não
   é reaproveitado aqui, mas mostra como pré-calcular sets de pares
   estruturais por treino.
10. **`gerador_csp.py:1278-1336`** — loop par-a-par S-T1/S-B1/S-B5
    (onde S-R1 cross-treino vai entrar). Pares (s1, s2) já são iterados
    com `s1` e `s2` em mesmo treino — pra cross-treino precisa loop
    diferente (pares cross-treino).

---

## 3. Objetivo desta sessão

Resolver as 3 facetas do Achado 1:

(a) **Aleatorização efetiva** da distribuição de subregião dentro de
    região. Confirmar empiricamente que o `random.random()` do Hamilton
    está fazendo efeito; se não, corrigir.

(b) **Soft cross-treino S-R1** novo: premia distribuições simétricas
    entre treinos da rotina. Ex: para `regiao lower(3)` × 2 treinos,
    motor prefere `T1=2ant+1post + T2=1ant+2post` (cross-treino equi)
    sobre `T1=T2=2ant+1post` (alocação repetida).

(c) **Decisão clínica sobre panturrilha**: ou
    `obrigatoria=True` (panturrilha aparece em todo `lower(N≥3)`), ou
    mecanismo de "acessórios opcionais" separado do Hamilton, ou
    aceitar status quo. **Pergunta para o Bernardo na abertura da
    sessão** — esta é a única decisão clínica do escopo.

**NÃO é** refator estrutural do Hamilton (já está OK).
**É** soft cross-treino novo + decisão clínica + verificação empírica
de (a).

---

## 4. Decisões a fechar (perguntar via texto livre)

### 4.1 Comportamento desejado para `panturrilha.obrigatoria` (CLÍNICA)

Hoje `panturrilha.obrigatoria=False` em `ANCORAS_POR_REGIAO['lower']`. Em
`lower(3)`, panturrilha cai ANTES do Hamilton (filtro
`qtd <= 2*n_obrig`). Resultado: 0% das rotinas com panturrilha.

Opções:

- **(a) `obrigatoria=True`** — panturrilha aparece em todo lower(N≥3).
  Em `lower(3)`: vira ant=2, post=2, pant=1 (todas obrigatórias) com
  qtd=3 vagas, n_obrig=3. Hamilton ainda funciona — ideal: ant=1.2,
  post=1.2, pant=0.6. Floor: 1+1+0. Restantes=1. Tie-break: ant/post
  empatam em resto=0.2, pant ganha (resto=0.6). Resultado: **1+1+1**
  (cada treino tem 1 de cada).
- **(b) "Acessório opcional" separado do Hamilton** — mecanismo novo
  pra panturrilha aparecer em ALGUMAS rotinas mas não todas (ex: 50%
  probabilidade). Mais complexo, melhor representa "panturrilha é
  acessório dispensável".
- **(c) Aceitar status quo** — panturrilha some em lower(3) e só
  aparece em lower(4+). Status quo atual.

Recomendação preliminar: **(a)** — mais simples, garante cobertura
clínica completa, encaixa no design declarativo. Trade-off:
`lower(2)` força sortear 2 de 3 obrigatórias (panturrilha vs ant ou
post), mais variabilidade. Aceitável.

### 4.2 Granularidade do S-R1 (TÉCNICA — eu decido)

S-R1 cross-treino pode operar em 2 níveis:

- **Subregião dentro de região**: penaliza desbalanço de distribuição
  de subregiões entre treinos da rotina (ex: T1=2ant+1post vs
  T2=1ant+2post premiado vs T1=T2=2ant+1post).
- **Padrão dentro de subregião**: penaliza desbalanço de distribuição
  de padrões em demandas subregião (ex: T1=composto+iso vs
  T2=iso+composto premiado vs T1=T2=composto+iso).

Recomendação: começar com **subregião dentro de região** (faceta do
Achado 1). Padrão dentro de subregião fica pra extensão futura se a
auditoria mostrar caso real.

### 4.3 Modelagem do S-R1 (TÉCNICA — eu decido)

Para `regiao R(N)` × T treinos, contar para cada subregião `S` o
número de slots em cada treino e penalizar desvio entre os treinos.

Forma proposta: para cada subregião S possível na região R, para cada
par de treinos `(t1, t2)`:

```
count_S_t1 = sum(assign[s,c] for s in slots_demanda_R_treino_t1
                              for c in pool[s] se ex[c].subregiao == S)
count_S_t2 = idem pra t2
diff_S_t1_t2 = abs(count_S_t1 - count_S_t2)  (IntVar)
penalidade = peso_sr1 * sum(diff_S_t1_t2)
```

Implementação CP-SAT padrão (`AddAbsEquality`). Peso a calibrar.

### 4.4 Peso default S-R1 (TÉCNICA — calibrar via sondagem)

Espelhar pattern S-B5: começar com `peso=4` ou `peso=5` (entre S-T1
rank_max=3 e custo de S-B4 desvio=5). Sondagem N=10 com 2 configs:
Full Body 2T região (achado) + lower(3)×2T isolado. Métrica:
desbalanço total cross-treino entre subregiões.

### 4.5 Granularidade da sondagem

2 configs canônicas mínimas:
- Full Body 2T (região) — o setup exato da auditoria.
- lower(3)×2T isolado — stress test do mecanismo.

N=10 por config. Métricas:
- % rotinas com `T1.ant == T2.ant` (assimetria persistente — quanto menor melhor).
- % rotinas com `T1.ant + T2.ant != T1.post + T2.post` (volume desigual).
- % rotinas com panturrilha presente (dependendo da decisão 4.1).
- p50 tempo de solve (sanity).

---

## 5. Spec técnica (rascunho de implementação)

### 5.1 (Opcional, dependente de 4.1) Mudar `panturrilha.obrigatoria=True`

Uma linha em `gerador_treino.py:151`. Em seguida verificar:

- `_decompor_demanda_regiao`: filtro `qtd <= 2*n_obrig` muda de
  `n_obrig=2` pra `n_obrig=3`. Em `lower(3)`: `3 <= 6` → TRUE; agora
  TODAS as 3 ficam na lista pré-Hamilton (vs antes onde panturrilha
  caia).
- `calcular_quotas` (Hamilton): com 3 vagas pra 3 obrigatórias todas
  pesos 2/2/1: floor (1+1+0), restantes=1, pant ganha (maior resto).
  Resultado: 1+1+1.

Pra `lower(2)`: 2 vagas < 3 obrigatórias → entra no caso especial
`vagas < n_obrig` (linha 313-327) que sorteia 2 das 3. Resultado:
1 das 3 fica com aviso `ancora_nao_cumprida`. UI já renderiza esse
aviso via modal `_avisos_modal.html`.

### 5.2 S-R1 cross-treino — variável `subregiao_idx[s]`

Análogo a `regiao_idx[s]` da S-B5. Em `_construir_modelo`,
após o bloco `regiao_idx`:

```python
# S-R1 (2026-05-27): codificação de subregião por slot pra contagem
# cross-treino. Lista de subregiões ativas no problema dinamicamente.
subregioes_no_problema = sorted({
    ex.subregiao for s in slots_globais for ex in s["pool_slot"]
})
SUBREGIAO_CODE = {sub: i for i, sub in enumerate(subregioes_no_problema, start=1)}

subregiao_idx: dict[int, cp_model.IntVar] = {}
for s in slots_globais:
    pool = s["pool_slot"]
    codes = [SUBREGIAO_CODE.get(ex.subregiao, 0) for ex in pool]
    lo, hi = (min(codes), max(codes)) if codes else (0, 0)
    si = model.NewIntVar(lo, hi, f"subreg_t{s['t_idx']}_s{s['sid']}")
    model.Add(si == sum(assign[(s["sid"], c)] * codes[c] for c in range(len(pool))))
    subregiao_idx[s["sid"]] = si
```

### 5.3 S-R1 penalty cross-treino

Pra cada demanda `regiao R(N)` que aparece em ≥2 treinos da rotina,
e cada par de treinos `(t1, t2)`, e cada subregião `S` possível em R:

```python
if peso_sr1 > 0:
    # Identifica grupos por (t_idx, R) onde R é nivel=regiao
    grupos_regiao_por_treino: dict[tuple[int, str], list[int]] = {}
    for grupos_t in treinos:
        for g in grupos_t:
            nv, esc, qtd = g["demanda"]
            if nv == "regiao":
                grupos_regiao_por_treino[(g["t_idx"], esc)] = g["slot_ids"]

    # Pra cada região R que aparece em ≥2 treinos
    regioes_repetidas: dict[str, list[int]] = defaultdict(list)
    for (t_idx, R), sids in grupos_regiao_por_treino.items():
        regioes_repetidas[R].append(t_idx)

    for R, t_idxs in regioes_repetidas.items():
        if len(t_idxs) < 2:
            continue
        subs_possiveis = REGIAO_PARA_SUBREGIOES.get(R, [])
        for sub in subs_possiveis:
            sub_code = SUBREGIAO_CODE.get(sub)
            if sub_code is None:
                continue
            # count[t] = qtd de slots em (t, R) com subregiao == sub
            counts = {}
            for t_idx in t_idxs:
                sids = grupos_regiao_por_treino[(t_idx, R)]
                if not sids:
                    continue
                indicators = []
                for sid in sids:
                    is_sub = model.NewBoolVar(f"sr1_is_{R}_{sub}_t{t_idx}_s{sid}")
                    model.Add(subregiao_idx[sid] == sub_code).OnlyEnforceIf(is_sub)
                    model.Add(subregiao_idx[sid] != sub_code).OnlyEnforceIf(is_sub.Not())
                    indicators.append(is_sub)
                count_var = model.NewIntVar(0, len(sids), f"sr1_count_{R}_{sub}_t{t_idx}")
                model.Add(count_var == sum(indicators))
                counts[t_idx] = count_var

            # Penalty: sum de |count[t1] - count[t2]| em todos os pares
            t_list = sorted(counts.keys())
            for i in range(len(t_list)):
                for j in range(i+1, len(t_list)):
                    t1, t2 = t_list[i], t_list[j]
                    diff = model.NewIntVar(0, len(grupos_regiao_por_treino[(t1, R)]),
                                           f"sr1_diff_{R}_{sub}_{t1}_{t2}")
                    model.AddAbsEquality(diff, counts[t1] - counts[t2])
                    pen = model.NewIntVar(0, peso_sr1 * len(grupos_regiao_por_treino[(t1, R)]),
                                          f"sr1_pen_{R}_{sub}_{t1}_{t2}")
                    model.Add(pen == peso_sr1 * diff)
                    penalidades.append(pen)
```

Cuidado:
- `subregiao_idx` cria 1 IntVar por slot — mesma magnitude de
  `regiao_idx` (S-B5) e `grupo_func` (S-B1). Custo leve.
- `is_sub` BoolVars criados **só** quando S-R1 ativo. Otimização
  estrutural — pulamos quando peso=0.
- `AddAbsEquality` é built-in do CP-SAT, eficiente.

### 5.4 Kwarg novo em `_construir_modelo`

```python
def _construir_modelo(
    ...,
    peso_sb5: int = 0,
    peso_sr1: int = 0,  # NOVO
):
```

Propagar pelas 4 funções resolver: `_resolver_legacy`,
`_resolver_com_variedade`, `gerar_rotina_csp`, `gerar_treino_csp`. Mesmo
pattern da S-B5.

Lembrar de incluir `peso_sr1` no `teto_por_termo` da Phase 2 da variedade.

### 5.5 Constante e adapter em `app_flask.py`

```python
# S-R1 (2026-05-27) — distribuição cross-treino de subregião em demanda
# nivel região. Peso a calibrar via sondagem. Default ON sempre, sem
# toggle UI (achado clínico estrutural).
_PESO_SR1_DEFAULT = 4  # placeholder; calibrar
```

Wire em `treino_regerar` E adapter rotina-inteira da `/gerar`. Análogo
a `_PESO_SB5_DEFAULT`.

**Nota**: S-R1 só faz sentido quando rotina tem ≥2 treinos. Em
`treino_regerar` (1 treino isolado), passar `peso_sr1=0` é correto —
mas o motor deveria tratar isso graceful. Implementar bypass dentro do
`_construir_modelo` quando `len(demandas_por_treino) < 2`.

### 5.6 UI

Zero código novo. Default ON sempre, sem toggle.

### 5.7 Tests novos

Pelo menos 4 testes em `tests/test_csp_sr1_cross_treino.py`:

1. **`test_peso_zero_eh_neutro`**: rotina viável; sem mudança vs
   pré-S-R1.
2. **`test_peso_alto_alterna_subregiao_cross_treino`**:
   `regiao lower(3) × 2T` com peso=5. % rotinas com `T1.ant == T2.ant`
   cai vs baseline.
3. **`test_1_treino_so_eh_neutro`**: `regiao lower(3) × 1T` com peso=5.
   S-R1 não dispara (sem cross-treino possível).
4. **`test_sr1_compativel_com_sb5_e_sa1`**: rotina com todos os softs
   ativos juntos: viável, sem regressão de cada um.

Opcional: smoke test reproduzindo achado da auditoria (Full Body 2T
região × seed da auditoria) — mas seeds eram aleatórias na auditoria,
então pode ser N=5 com seed=0..4 e medir agregado.

### 5.8 (Dependente de 4.1) Mudança no XLSX `banco_exercicios.xlsx`?

Não. `obrigatoria` está no código (`ANCORAS_POR_REGIAO`), não no XLSX.

---

## 6. Validação esperada (gate de fechamento)

### 6.1 Sondagem comparativa pré × pós

Script novo `tools/sondar_sr1_cross_treino.py` (pattern dos outros
sondares). 2 configs canônicas com N=10:

- Full Body 2T (região, achado da auditoria)
- lower(3) × 2T isolado

Métricas:
- % rotinas com assimetria persistente (`T1.ant == T2.ant`).
- % rotinas com volume cross-treino desigual entre ant e post.
- % rotinas com panturrilha presente (≥1 slot).
- Tempo p50.

Persistir `logs/sr1_pre.json` e `logs/sr1_pos.json`. Comparar
lado-a-lado em log da frente.

### 6.2 Pytest

Baseline 364 testes (357 + 7 da S-B5) + 4-6 novos = 368-370. Snapshots
devem regenerar (mudanças benignas esperadas em rotinas geradas).

### 6.3 Harness 16/16

Sem regressão funcional.

### 6.4 Smoke E2E manual via browser

POST `/gerar` Full Body 2T região 3x. Verificar que cada par de
treinos da rotina alterna a distribuição de subregião — não 100%
`T1=T2=2ant+1post`.

---

## 7. Arquivos a mexer

- `gerador_treino.py` — `ANCORAS_POR_REGIAO['lower']` (1 linha,
  depende de 4.1).
- `gerador_csp.py` — `subregiao_idx[s]` + bloco S-R1 cross-treino +
  propagação de `peso_sr1` em 5 funções (`_construir_modelo`,
  `_resolver_legacy`, `_resolver_com_variedade`, `gerar_rotina_csp`,
  `gerar_treino_csp`) + `peso_sr1` no `teto_por_termo`. ~60-80 linhas.
- `app_flask.py` — `_PESO_SR1_DEFAULT` + wire em 2 chamadas. ~5 linhas.
- `tests/test_csp_sr1_cross_treino.py` — novo, 4-6 testes
  (~120-180 linhas).
- `tools/sondar_sr1_cross_treino.py` — novo, ~150 linhas.
- `docs/refatoracao/logs/sr1_pre.json` + `sr1_pos.json` — snapshots.
- `docs/refatoracao/logs/mvp_sr1_cross_treino.md` — log da frente.
- `docs/refatoracao/roadmap_csp.md` — 2 ticks ✅ (S-R1 + panturrilha,
  se decisão 4.1=(a)).
- `docs/refatoracao/auditorias/2026-05-26.md` Achado 1 — status ✅.
- `MEMORY.md` — 1 linha.

**NÃO mexer**:
- Mecanismo de tier / aderência (descontinuado).
- S-A1 ou S-B5 (já mergeadas).
- Motor antigo `gerador_treino.py` exceto pela mudança opcional na
  constante `ANCORAS_POR_REGIAO` (caso 4.1=(a)).

---

## 8. Restrições / não-fazer

- **NÃO mergear em main sem aprovação explícita do Bernardo.**
- **NÃO usar `--no-verify` ou flags que pulem hooks.**
- **Commit seletivo** (`git add <arquivo>`, NUNCA `-A`).
- **NÃO usar AskUserQuestion em decisões técnicas** — texto livre com
  pros/contras é melhor (ver `feedback-askquestion-exploratorio`).
  **EXCEÇÃO**: decisão 4.1 é clínica e binária (a/b/c) — AskUserQuestion
  apropriado.
- **Cuidado com regressão**: se sondagem mostrar tempo de solve subindo
  drasticamente em alguma config (>2x), considerar skip estrutural
  análogo ao da S-B5 (`treinos_single_region`).
- **Achado 2** (equipamento cross-treino) tem dependência DECLARADA
  em S-R1 entrar antes — esta frente DESBLOQUEIA Achado 2.

---

## 9. Pendências NÃO incluídas nesta frente

- **🟡 Achado 2 da auditoria 2026-05-26** — equipamento repetido
  cross-treino. Novo eixo S-E1. Pós-S-R1.
- **Gate de avaliação clínica semântica** (Bloco 4) — pré-requisito
  do Bloco 5. Continua aberto.
- **S-T2/S-T3/S-T4/S-R2/S-R3/S-H1/H-P2/H-X** — frentes futuras
  listadas no Bloco 4 do roadmap.

---

## 10. Como abrir a sessão

Primeira mensagem da sessão deve:

1. Confirmar que leu norte.md + roadmap_csp.md + auditoria 2026-05-26
   (Achado 1) + log S-B5 (mais imediato) + log S-A1 (predecessor
   arquitetural) + `gerador_treino.py:142-157` (ANCORAS_POR_REGIAO) +
   `:277-363` (calcular_quotas) + `:2950-3017`
   (_decompor_demanda_regiao com filtro pré-Hamilton) +
   `gerador_csp.py:1278-1336` (loop par-a-par onde S-R1 vai entrar).
2. Confirmar entendimento das 5 decisões pendentes (§4).
3. **AskUserQuestion específica para decisão 4.1 (panturrilha)** com 3
   opções (a)/(b)/(c). Decisão clínica binária — única ocasião pra
   usar AskUserQuestion nesta sessão.
4. Após resposta, **decidir 4.2-4.5 sozinho** e comunicar via texto
   livre: "vou com subregião dentro de região + peso=4 + sondagem 2
   configs; ok?".
5. Rodar sondagem pré (peso_sr1=0) em `main` ANTES da implementação.
   Persistir baseline.
6. Implementar na ordem:
   - 5.1 (mudança ANCORAS_POR_REGIAO se 4.1=(a))
   - 5.2 (subregiao_idx[s])
   - 5.3 (constraint S-R1)
   - 5.4 (propagação kwarg)
   - 5.5 (adapter)
   - 5.7 (testes)
7. Rodar sondagem pós + comparar lado-a-lado.
8. Gate: pytest + harness + smoke E2E browser.
9. Atualizar docs (log, roadmap, auditoria, MEMORY.md).
10. Commit seletivo + push + aguardar aprovação Bernardo pra merge FF.

Não codar antes da confirmação textual das decisões e da sondagem pré.

**Tempo estimado**: 1-2 sessões (~2-3h). Sondagem ~5min cada,
implementação ~1h, testes ~30min, validação ~30min.

---

## 11. Contexto importante da sessão anterior (2026-05-27)

Frente **S-B5** (Achado 3) acabou de fechar. Resumo do que entregou:

- Soft constraint nova no CSP: penalty por par mesmo bloco + mesma
  região. Default ON, peso=4, sem toggle UI.
- Skip estrutural em treinos single-region (otimização de tempo CP-SAT
  — ABC 3T de 490s/p50 → 71.6s/p50).
- Full Body 2T (sub) 38.8% → 0% blocos same-region.
- Full Body 2T (região, achado): 22.5% → 0% (achado da auditoria
  fechado).
- Smoke E2E `/gerar` confirma 0/8 blocos same-region (auditoria N=1
  era 4/8).
- Pytest 364 + harness 16/16 OK.

Calibração inicial peso=10 foi rejeitada (empate com S-B4 quebrava
blocos em solos em configs single-region — ABC 3T 19.6% → 61.8% solo).
Recalibrado peso=4 + skip single-region resolveu.

Pattern arquitetural: `regiao_idx[s]` IntVar criado SEMPRE (espelho de
`grupo_func[s]` da S-B1, gancho pra futuras constraints).
**Esta frente (S-R1) reusa esse pattern com `subregiao_idx[s]`.**

Calibração descontinuada da aderência (Achado 4) NÃO foi retomada.
Default `{alta:2, media:0, baixa:0}` permanece em produção.

Próxima frente após esta (S-R1): **Achado 2** — equipamento repetido
cross-treino. Dependência DECLARADA em S-R1, então S-R1 desbloqueia.
