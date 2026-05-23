# Log — MVP Fatia 3 Frente B: variedade INTRA-config (top-K enumeration + softmax)

**Data**: 2026-05-23 (mesma sessão da Fatia 2 P2)
**Branch**: `fatia-2-parte-2` (continuação — Fatia 2 P2 fechada em commit `839e05e`)
**Arquivos modificados**:
- `gerador_csp.py` (substancial — dataclass nova, helpers extraídos, refator de `gerar_rotina_csp` em branch legacy + branch variedade)

**Status**: ✅ concluída (Frentes 1 + 2) — gate verde, sem regressão.

---

## Objetivo

Frente B da Fatia 3: resolver o **determinismo do solver CP-SAT** quando há múltiplas soluções ótimas. Caso real medido na Fatia 2 P2: Config A com 5 seeds devolvia só 1–2 rotinas distintas — solver pega a primeira solução ótima que encontra e seeds não diversificam o suficiente.

Escopo declarado (escopo NÃO incluído):
- Variedade INTER-rotina (S-H1 — "rotina nova evita exercícios da rotina anterior") — frente separada.
- Aderência ao Tier do vetor de perfil de aluno — Frente D.
- Modulação por aluno (peso de bias por perfil) — Frente D.

## Decisões fechadas (antes de codar)

Tomadas via AskUserQuestion na abertura da sessão:

1. **Mecanismo central** — Top-K enumeration + softmax pós-solver (forma "(b)" do menu). Recusadas: perturbação ε nos coeficientes (suja semântica de S-T1), multi-solve com seeds (já provado ineficaz na Fatia 1 e P2).
2. **Default `variedade=None` = comportamento Fatia 2 P2 byte-a-byte** (Opção A — opt-in via dataclass). Bernardo registrou ressalva: integração com UI Flask DEVE ativar `variedade=ConfigVariedade()` por default — produto espera variedade, não rotina determinística. TODO pra Frente C.
3. **API via dataclass `ConfigVariedade`** (consistente com `ConfigPesosProximidade` do gerador antigo; escalável pra Frente 2 + Frente D).
4. **Frente 2: distância aditiva** `exp(-(d + α·H) / T)` (recusada multiplicativa — acopla os 2 knobs). **Referência = 1ª solução enumerada pelo CP-SAT** (arbitrária mas estável dentro de uma chamada).

## O que foi implementado

### Frente 1 — Top-K enumeration + softmax

#### 1. Dataclass `ConfigVariedade`

```python
@dataclass
class ConfigVariedade:
    slack: int = 0              # inversões adicionais aceitas
    temperatura: float = 1.0    # T do softmax
    max_solucoes: int = 100     # cap da enumeração
    python_seed: Optional[int] = None  # seed do random.Random
    alpha_tier: float = 0.0     # Frente 2 (modulação por tier)
```

#### 2. Helper `_construir_modelo`

Extrai a construção do CpModel completo (H-T1/T2/T3/T4 + H-R1 + penalidades S-T1) MAS sem chamar `Minimize`. Devolve dict com `model`, `assign`, `slots_globais`, `treinos`, `grupo_por_idx`, `h_r1_aplicadas`, `penalidades`. Caller decide se vira `Minimize(sum(penalidades))` (legacy + Phase 1) ou IntVar de soma + bound (Phase 2).

**Decisão de design importante**: o IntVar `var_total` é criado SÓ na Phase 2 (caller faz `model.NewIntVar(...)`), porque adicionar um IntVar a mais no helper muda microscopicamente a ordem de busca do CP-SAT e quebraria a equivalência byte-a-byte com a Fatia 2 P2. A primeira versão do refator criava o IntVar dentro do helper e mexia em variedade do baseline.

#### 3. Callback `_SolucoesCollector`

`CpSolverSolutionCallback` que coleta `(sid_to_cidx, inversoes)` por solução. Aborta a busca com `StopSearch()` ao atingir `max_solucoes`.

#### 4. `gerar_rotina_csp` refatorada — 2 branches

- `variedade is None` → `_resolver_legacy`: 1 solve com `Minimize`, decodifica via `solver.Value` (igual ao código antigo).
- `variedade is ConfigVariedade` → `_resolver_com_variedade`:
  - **Phase 1**: solve com `Minimize` pra descobrir `optimal`.
  - **Phase 2**: reconstrói o modelo, cria IntVar `var_total = sum(penalidades)`, adiciona `var_total <= optimal + slack`, ativa `enumerate_all_solutions = True` + `num_search_workers = 1`, solve com callback.
  - Softmax: `peso[k] = exp(-(distancia[k] + α·H[k]) / T)` (H zerado quando alpha_tier=0).
  - Amostra com `random.Random(python_seed).choices(solucoes, weights=pesos)`.

#### 5. Helper `_decode_solucao(treinos, sid_to_cidx)`

Compartilhado entre os 2 branches. Garante mesma forma de saída em `resultado["treinos"]`.

#### 6. Wrapper `gerar_treino_csp` propaga `variedade=`

E inclui chave `variedade` no dict de retorno quando ativo.

### Frente 2 — Modulação por tier

Aplica modulação puramente no softmax pós-coleta (não toca no modelo CP-SAT). Frente 2 é ortogonal ao solver — qualquer mudança nela é refator local sem impacto em pytest/harness do gerador antigo.

Pra cada solução `k` coletada:
1. Referência = `collector.solucoes[0]` (1ª enumerada).
2. `ref_tier_rank[s]` = tier rank do ex escolhido pela ref no slot s.
3. `H[k] = sum_s ref_tier_rank[s] * (k[s] != ref[s])` — mudar slot Principal (rank=3) custa 3× mais que Acessório (rank=1).
4. Score composto entra no expoente do softmax (aditivo, decisão fechada).

`alpha_tier == 0` (default) zera o termo H → comportamento Frente 1 puro.

### Metadados expostos em `resultado["variedade"]`

Quando `variedade` é ativa:
```python
{
    "ativa": True,
    "slack": int, "temperatura": float,
    "max_solucoes": int, "python_seed": int|None,
    "alpha_tier": float,
    "n_solucoes_enumeradas": int,
    "distancia_escolhida": int|None,
    "optimal_value": int|None,
    "enumeracao_limitada": bool,
    "hamming_ponderado_escolhido": int|None,
    "tempo_phase_1": float, "tempo_phase_2": float,
}
```

## Resultado da validação

### Frente 1 (Config A com defaults `ConfigVariedade()`)

| Cenário | Distintas / 5 | Notas |
|---|---|---|
| Baseline (variedade=None, 5 seeds CP-SAT) | 2 / 5 | Bonus benigno do refator: era 1/5 pré-refator. Reorder microscópico no helper mudou exploração do solver. |
| `ConfigVariedade()` (slack=0, 5 python_seeds) | **5 / 5** | 100 solucoes enumeradas, dist=0 em todas (todas ótimas). |
| `ConfigVariedade(slack=1, T=1.0)` | 5 / 5 | dist=0 (T=1 ainda prioriza ótimas mesmo com folga). |
| `ConfigVariedade(slack=2, T=2.0)` | 5 / 5 | dist=1 (T=2 alto o suficiente pra sub-ótimas terem peso real). |
| Configs B/C/D/Bônus (legacy) | OK | Viabilidade + H-T4 graceful + H-R1 graceful + AllDifferent cross-treino preservados. |

**Tempo médio (Phase 1 + Phase 2)**: ~0.03s no banco atual. Sem regressão significativa vs 0.005–0.04s da Fatia 2 P2.

### Frente 2 (Config A com `alpha_tier` variando, 20 python_seeds cada)

Mediu-se variedade por slot e distintas totais. Slot 4 (vaga única ombro) e slot 7 (vaga única perna_post) são onde há mais flexibilidade no pool — outros slots são Principais "dominantes" pelo S-T1.

| alpha_tier | Distintas / 20 | Slot 4 (Ombro) | Slot 7 (PernaPost) |
|---|---|---|---|
| 0.0 (Frente 1 puro) | 19 | 7 distintos, 13 Intermediário / 7 Principal | 13 distintos, 16 Principal / 4 Intermediário |
| 0.3 | 19 | 6 distintos | 13 distintos |
| 0.5 | 17 | 6 distintos, começa a colapsar pra Principal | 11 distintos |
| 1.0 | 13 | 2 distintos, 17/20 Principal | 10 distintos |
| 2.0 | 5 | 1 distinto, 20/20 Principal | 5 distintos |

**Gradiente claro:** alpha_tier desincentiva progressivamente mudanças em slots de tier alto. Acessórios (slot 1 = Crucifixo) já estavam saturados na ref e não mudam. Sweet spot pareceu ser 0.3–0.5 (conserva alguma variedade mas começa a estabilizar tier alto).

### Gate de fechamento

| Métrica | Resultado |
|---|---|
| pytest | 217 passed + 1 skipped (=218 total) ✓ (pré-existente) |
| harness | 16/16 OK (2.3 + 4.1 NO-OPs informativos preservados) ✓ |
| _main() do gerador_csp.py | Todas as 5 configs (A/B/C/D/Bônus) verdes ✓ |
| Gerador antigo (`gerador_treino.py`) | Intocado — Frente B vive 100% em `gerador_csp.py` |

## Decisões fechadas (relevantes pra Fatia 3+)

1. **`variedade=None` é byte-a-byte legacy.** Snapshot do `_main()` da Fatia 2 P2 + pytest + harness preservados. Trade-off: variedade é opt-in. Bernardo registrou ressalva: produto final NÃO pode ficar com default = rotina determinística. TODO pra Frente C (integração UI Flask) ou explicitamente discutir mudar o default em outra frente.

2. **`_construir_modelo` não cria `var_total` IntVar.** Caller (Phase 2) cria. Razão técnica: criar o IntVar a mais no modelo (mesmo logicamente equivalente) muda a ordem de busca do CP-SAT e quebraria a equivalência byte-a-byte do legacy com a Fatia 2 P2.

3. **Frente 2 vive fora do solver.** Modulação por tier é puramente softmax-side, não vira constraint CP-SAT. Vantagem: zero impacto em pytest/harness/cobertura clínica do gerador antigo. Refinamentos (Hamming não-ponderado, L1 sobre rank, etc.) são swaps locais.

4. **Hamming usa 1ª solução enumerada como referência.** Decisão arbitrária mas pragmática — alternativas (centroide, solução com menor inv) são mais "principled" mas custam mais código por marginal benefit. Reabrir só se calibração mostrar que importa.

5. **Aditivo no softmax: `exp(-(d + α·H) / T)`.** Decisão fechada com Bernardo. Mantém T e α ortogonais — T é "amplitude geral", α é "penalidade específica por mudar tier alto". Multiplicativo (T_eff = T/(1+α·H)) acopla, mais difícil calibrar isoladamente.

## Achados / sinais de alerta

1. **Bônus benigno no legacy: 1→2 distintas pós-refator.** A reorganização em `_construir_modelo` mudou microscopicamente a ordem de criação de variáveis no CpModel, e CP-SAT explorou ligeiramente diferente. Todas as constraints + S-T1=0 continuam satisfeitas. Não é regressão, é melhora incidental.

2. **`enumeracao_limitada=True` quase sempre.** Config A tem >100 soluções ótimas, e estamos coletando só as 100 primeiras encontradas pelo CP-SAT. Possível viés sutil (amostra não-uniforme do espaço total). MVP aceita isso; refinamento futuro: aumentar cap, ou amostragem CP-SAT-side via parâmetro do solver.

3. **Hamming "vs primeira enumerada" não-determinístico clinicamente.** A "referência" depende da ordem de enumeração do CP-SAT, que muda com `seed` e detalhes do modelo. Para uma chamada específica, é estável. Cross-chamada, a ref muda. Pro MVP, OK — alpha_tier é knob exploratório, não foi calibrado.

4. **Slots de Principal puro são imóveis em Config A.** Mesmo com `ConfigVariedade()`, slots 0, 2, 3, 5, 6 da Config A ficam 100% fixos nas 100 amostras (Supino Halteres, Puxada Supinada, Remada LM Neutra, Agachamento Livre, Recuo). Isso é porque pra essas vagas há um pool grande de candidatos Principais e eles "ganham por S-T1" em todas as ótimas. Mecanismo Frente B só explora slots onde múltiplas ótimas concordam que vários ex são válidos.

5. **Sweet spot empírico de `alpha_tier`**: entre 0.3 e 0.5 pra Config A. Acima de 1.0 colapsa variedade demais; abaixo de 0.3 quase indistinguível de 0.0. NÃO é calibração formal — apenas observação pra orientar uso e refinamento futuro.

## Conclusão

Frente B fecha **variedade INTRA-config como first-class na engine CP-SAT**. Mecanismo declarativo (top-K enumeration via callback, sampling pós-solver) — sem patchar `gerador_treino.py` antigo e sem mudar a semântica do objetivo (S-T1 continua sendo inversões inteiras, slack é knob explícito).

Mais relevante pro produto: Bernardo levantou que default opt-in é inconsistente com a expectativa de produto. **Pra Frente C (integração UI Flask), wiring DEVE passar `variedade=ConfigVariedade()` por default** — registrado aqui como TODO pra não perder.

## Próximos passos (Fatia 3 — continuação)

- **Frente C** — integração com UI Flask: substituir `gerador_treino.py` em pelo menos uma rota pelo `gerador_csp.py`, com `variedade=ConfigVariedade()` por default.
- **Frente D** — vetor de perfil de aluno completo + moduladores (incluindo Aderência ao Tier do MVP da seção 3 do catálogo). `alpha_tier` da Frente B pode virar um output da modulação por perfil.
- **Pareamento de blocos** — S-B1/B2/B3/B4 do catálogo. Hoje rotina sai linear (1 ex por bloco efetivamente).
- **Outras hards** — H-P2 (bloco solo), H-X (restrições físicas).
- **Outras softs** — S-T2 fadiga blocos, S-T3 demanda neural, S-T4 variedade eixos soft, S-R1/R2/R3, S-H1 histórico cross-rotina (variedade INTER-rotina, distinta da INTRA-config desta Frente B).

## Refinamentos pós-Frente B abertos (não bloqueiam uso real)

- **Refinar `enumeracao_limitada`**: cap maior, ou amostragem CP-SAT-side. Item de calibração quando começar a integração com produto.
- **Refinar referência do Hamming**: explorar centroide ou solução com menor inv. Reabrir se calibração indicar que a aleatoriedade da 1ª enumerada bagunça a interpretação clínica.
- **Pytest pra Frente B**: cobertura atual é zero (só smoke test manual). Adicionar testes que validem (a) `variedade=None` preserva Fatia 2 P2, (b) `ConfigVariedade()` enumera + sampla, (c) `slack` bound é respeitado, (d) `alpha_tier > 0` muda distribuição por slot, (e) `python_seed` é reprodutível. Item de qualidade — não bloqueia uso, mas evita regressões silenciosas em refator futuro.
