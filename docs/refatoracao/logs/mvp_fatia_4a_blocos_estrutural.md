# Log — MVP Fatia 4.A: modelagem estrutural de blocos no CSP

**Data**: 2026-05-24
**Branch**: `fatia-4a-blocos-estrutural` (a partir de `frente-d-vetor-perfil`)
**Arquivos modificados**:
- `gerador_csp.py` (variáveis estruturais de bloco + S-T1 reformulada + saída de `blocos` + collector estendido)
- `app_flask.py` (adapter `_resultado_csp_pra_sessao` consome `blocos` estruturado do motor)
- `tests/test_blocos_estrutural.py` (novo, 7 testes)

**Status**: ✅ concluída — gate verde (pytest 242 = 235 + 7 novos + 1 skip; harness 16/16 OK; smoke E2E mostra blocos variados em produção).

---

## Objetivo

Substituir o paradigma "rotina é lista linear de exercícios" pelo paradigma "rotina é lista de **blocos** estruturados pelo solver", em linha com o princípio fundador do refator declarativo (decisões globais, não greedy pós-processo).

Bernardo levantou crítica de princípio importante: caminho A (pós-processo greedy igual ao motor antigo) trairia a motivação central do CSP. Caminho B (modelagem estrutural no mesmo modelo) é o certo. Fatia 4.A é só a parte estrutural — sem S-B's ainda, motor agrupa "livre" satisfazendo só tier-order de blocos + bounds de tamanho.

Escopo CONSCIENTEMENTE MÍNIMO:
- Variáveis de bloco no modelo CSP (não pós-processo).
- S-T1 reformulada por bloco (não por slot).
- Output muda: `treinos[t]["blocos"]: list[list[Exercicio]]`.
- Adapter Frente C consome blocos nativos do motor.
- **Sem S-B1..S-B4** — entram em 4.B (S-B1 distância funcional + evitar_agonistas) e 4.C (S-B4 tamanho preferido + tamanho_bloco da UI).

## Decisões fechadas (antes de codar)

Confirmadas via texto pelo Bernardo:

1. **Reformulação S-T1: escolha (a)** — "tier máximo do bloco" ordena entre blocos. Forma par-a-par equivalente: pra pares (s1, s2) no mesmo treino, viol se bloco anterior tem tier slot menor.
2. **Bloco solo permitido** — tamanho ∈ [1, TAMANHO_MAX_BLOCO=3]. Caso natural pra 1-slot e futuro H-P2 (Centralidade Alta + Aderência Alta).
3. **Cadastros S-B2/S-B3 adiados** — `demanda_lombar` e `estabilidade_externa` ficam pra 4.B/4.C/futuro.
4. **Caminho B** (modelo único) sobre caminho A (pós-processo). Aceito como diretriz arquitetural.

## O que foi implementado

### Variáveis de bloco em `_construir_modelo`

```python
X[(t, sid, b)]   BoolVar          # slot sid no bloco b do treino t
bloco_idx[sid]   IntVar [0, max_b)  # bloco_idx[sid] = sum_b (b * X[(t,sid,b)])
```

- `max_b = n_slots_treino` (bloco solo sempre possível).
- `AddExactlyOne(X[(t,sid,b)] for b)` por slot.
- `Sum(X[(t,sid,b)] for sid) <= TAMANHO_MAX_BLOCO` por (t, b).
- Constante `TAMANHO_MAX_BLOCO = 3` no topo do módulo (4.C torna parâmetro vindo da UI).

### S-T1 reformulada (par-a-par com `lt`/`gt` sobre `bloco_idx`)

Substitui `for grupos_t in treinos: for g in grupos_t: pares (i,j) em g["slot_ids"]` por **pares de slots no mesmo treino**, ordem definida por `bloco_idx` (variável de decisão):

```python
for t_idx, sids_t in slots_por_treino.items():
    for s1, s2 in pairs(sids_t):
        lt = NewBoolVar()  # bloco_idx[s1] < bloco_idx[s2]
        gt = NewBoolVar()  # bloco_idx[s1] > bloco_idx[s2]
        Add(bloco_idx[s1] - bloco_idx[s2] <= -1).OnlyEnforceIf(lt)
        Add(bloco_idx[s1] - bloco_idx[s2] >= 1).OnlyEnforceIf(gt)
        Add(lt + gt <= 1)
        viol = NewIntVar(0, rank_max)
        Add(viol >= tier_rank[s2] - tier_rank[s1]).OnlyEnforceIf(lt)
        Add(viol >= tier_rank[s1] - tier_rank[s2]).OnlyEnforceIf(gt)
        penalidades.append(viol)
```

Equivalência clínica com escolha (a): se TODOS os slots de tier alto estão em blocos com idx menor que slots de tier baixo, soma = 0. Slot dentro do mesmo bloco não contribui pra viol (ambos lt e gt falsos, OnlyEnforceIf desliga as constraints).

### `_decode_solucao` estende saída

Recebe arg novo opcional `sid_to_bloco: dict[int, int]`. Estrutura cada treino em:
- `grupos` (legacy, retrocompat)
- `ordem_global` (legacy, agora derivado da concatenação dos blocos em ordem `bloco_idx`)
- `blocos: list[list[Exercicio]]` (NOVO — slots agrupados por bloco_idx, ordenado asc)

### `_SolucoesCollector` estendido

Captura `bloco_idx` por solução (`self.blocos: list[dict[int,int]]`). Branch variedade passa pro decode.

### `gerar_treino_csp` wrapper propaga `blocos`

`out["blocos"] = t0.get("blocos", [])` no dict de retorno.

### Adapter Frente C consome blocos nativos

`_resultado_csp_pra_sessao` em `app_flask.py`:
- **Antes (Frente C MVP)**: itera `ordem_global` linear, cria 1 SuperSerie solo por exercício (label A, B, C...).
- **Depois (4.A)**: itera `blocos`, cria 1 SuperSerie por bloco com até 3 ex (ex1/ex2/ex3 preenchidos pelos primeiros 1/2/3 do bloco).
- Fallback retrocompat: se `blocos` ausente, cai pro caminho linear antigo.

## Resultado da validação

### Smoke isolado do motor

Demanda `[("subregiao", "peito", 2), ("subregiao", "costas", 2), ("subregiao", "perna_anterior", 2)]` (6 slots):
- viavel=True, inversoes=0 (S-T1 reformulada respeitada).
- 2 blocos de 3 slots cada (motor concentrou — sem incentivo de tamanho menor).
- Bloco 0: tier_max=3 (Principal); Bloco 1: tier_max=2 (Intermediário). Tier-order por bloco respeitada.

### Smoke E2E via `/regerar` (10 runs)

Aluno Bernardo, mesma demanda rica de 6 slots:
- Distribuição de tamanhos de bloco: **17 solo + 8 duplas + 9 triplas** (em 34 blocos totais).
- Total de slots: 60 = 10 × 6 (estrutura preservada).
- Run 1 representativo: A=2×Principal | B=Intermediário+Principal+Intermediário | C=Intermediário.

Sem incentivo de tamanho (S-B4 é 4.C), motor escolhe agrupamento "ótimo" só pro objetivo de tier — algumas vezes bloco grande (junta tier alto num lugar só), outras solo. Comportamento esperado pra 4.A: variabilidade alta porque não há sinal direcionado pra estrutura específica de blocos.

### Gate de fechamento

| Métrica | Resultado |
|---|---|
| pytest | **242 passed + 1 skipped** (=235 pré-4.A + 7 novos) ✓ |
| 13 snapshots | ✓ preservados |
| harness | **16/16 OK** (2.3 + 4.1 NO-OPs preservados) ✓ |
| Tempo pytest | 10.76s → 18.62s (~1.7x; aceitável pro ganho estrutural) |
| Frente B intacta | ✓ (variedade enumera + sampla blocos via callback estendido) |
| Frente D intacta | ✓ (Aderência continua slot-level, ortogonal a bloco_idx) |
| Gerador antigo | Intocado ✓ |

## Decisões fechadas (relevantes pra 4.B+)

1. **`TAMANHO_MAX_BLOCO=3` é constante na 4.A** — vira parâmetro na 4.C, vindo da UI antiga (`tamanho_bloco` 1/2/3).

2. **Bloco solo sempre permitido no modelo** — `max_b = n_slots_treino` na variável X (limite trivial). Sem custo pra solver porque BoolVars não-usadas viram trivialmente 0.

3. **S-T1 par-a-par equivalente a "tier máx do bloco"** — evita criar IntVar de max (multiplicativo). 4.B/4.C não precisam recodificar.

4. **`bloco_idx[sid]` exposto em retorno de `_construir_modelo`** — ponto de extensão pra S-B1 (4.B) e S-B4 (4.C) que precisam saber qual bloco cada slot habita.

5. **Adapter Frente C simplificou** — `_resultado_csp_pra_sessao` agora usa blocos nativos. Caso "blocos vazio" ainda tem fallback retrocompat (não deveria disparar pós-4.A).

6. **Sem regressão clínica detectável** — pytest 235 originais (cobertura completa Frentes B+D + cenários do harness) continuam verdes. Não há comportamento "pior" no espaço observado.

## Achados / sinais de alerta

1. **Sem S-B's, motor agrupa sem critério clínico** — bloco com 2 Principais (ex.: Remada Uni Polia + Recuo no smoke E2E) acontece. Não viola tier-order de blocos (ambos têm tier_max=3), mas clinicamente é par "pesado". 4.B (S-B1 distância funcional) e 4.C (S-B4 tamanho preferido) vão refinar. Documentar como **comportamento intermediário esperado** — não usar 4.A em produção real até 4.C fechar.

2. **Tempo de solve subiu ~1.7x no pytest** — esperado pelo aumento de variáveis (X[s,b] + lt/gt por par + bloco_idx) e constraints (AddExactlyOne + AtMost(TAMANHO_MAX_BLOCO) + OnlyEnforceIf). Ainda <20s pra suite inteira. Tempo real de uma rotina (3 treinos × ~12 slots): smoke mostrou tempos comparáveis aos pré-4.A (não medi formalmente; estimativa <200ms por rotina).

3. **Variedade pode mudar estatística** — espaço de soluções aumentou (cada solução agora carrega agrupamento, não só seleção). `slack` da ConfigVariedade preservado mas comportamento empírico pode mudar. Não detectei regressão em pytest da Frente B; smoke E2E mostrou variedade preservada (3 tamanhos de bloco diferentes em 10 runs).

4. **`grupos` e `ordem_global` mantidos no retorno** — retrocompat com testes da Frente B/D que ainda lêem essas chaves. Em 4.B/4.C, possivelmente revisar se `grupos` ainda faz sentido semântico (grupo de demanda ≠ bloco; mantém pra propósitos de tracing/debug).

5. **Adapter Frente C: fallback retrocompat preservado** — clause `if blocos_motor is None` cobre caller pré-4.A. Defensivo, custo zero. Remover quando todos os callers garantirem motor pós-4.A.

## Pendências mapeadas (4.B + 4.C)

### 4.B — S-B1 + evitar_agonistas

- Implementar S-B1 como soft sobre pares de slots no mesmo bloco (via `same_bloco[s1,s2] = OR_b(X[s1,b] AND X[s2,b])`).
- Importar mapa de antagonismo + GRUPO_MUSCULAR_PADRAO do gerador antigo.
- Toggle `evitar_agonistas` vira amplificador do peso de S-B1.
- Smoke: blocos com 2 agonistas devem cair >50% vs 4.A pura.

### 4.C — S-B4 + tamanho_bloco da UI

- Adicionar parâmetro `tamanho_preferido: int = 2` (ou similar) em `_construir_modelo`.
- S-B4 como soft que penaliza desvio do tamanho preferido por bloco.
- UI atual envia `tamanho_bloco` (1/2/3) que vira o parâmetro.
- Densidade Pareamento (vetor) modula como amplificador do S-B4 (mas dimensão Densidade ainda não existe no perfil — adia ou implementa junto).
- Smoke: distribuição de tamanhos respeita preferência.

### 3 micro-frentes paralelas após 4.C, antes da Frente E.0

- `exercicios_travados`: `model.Add(assign[slot, cidx_fixo] == 1)`.
- `cargas_config`: nova hard H-cargas (filtro de pool por aluno).
- `relaxar_familia`: toggle pra desativar H-T1 sob falha de viabilidade.

### Refinamentos S-B2/S-B3 (futuro)

- Cadastros novos no XLSX: `demanda_lombar`, `estabilidade_externa`.
- Implementação só quando evidência clínica indicar prioridade (não bloqueia Frente E).

## Próximos passos

- **4.B (S-B1 + evitar_agonistas)** — próxima sub-fatia. Adiciona incentivo clínico de pareamento. Sem isso, 4.A entrega blocos "vazios de critério" — não usável em produção real.
- **Não tocar /gerar ainda** — Frente E.1 espera 4.B + 4.C + (talvez) 3 micro-frentes + harness comparativo Frente E.0.
- **Não rodar `/regerar` em produção real ainda** — comportamento de pareamento 4.A é intermediário. Bernardo pode usar mas com expectativa de ver pares "estranhos" às vezes.
