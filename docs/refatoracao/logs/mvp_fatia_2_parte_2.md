# Log — MVP Fatia 2 Parte 2: consumir tier curado + H-T1/T2/T3 + H-R1

**Data**: 2026-05-23
**Branch**: `fatia-2-parte-2` (a commitar — aguardando review)
**Arquivos modificados**:
- `gerador_csp.py` (substancial — heurística removida, refator pra rotina, 4 constraints novas, helpers)
- `gerador_treino.py` (mínimo — campo `tier: str` no dataclass `Exercicio` + populado em `carregar_banco`)
- `banco_exercicios.xlsx` (Checkpoint 0: Nordic Curl Acessório → Intermediário)
- `docs/refatoracao/logs/fatia_2_curadoria_tier.md` (atualizado pro Nordic Curl)
- `docs/refatoracao/catalogo_constraints.md` (correspondência conceito↔coluna nas Seções 1 e 4)

**Status**: ✅ concluída — gate de fechamento verde (ver Validação).

---

## Objetivo

Frente C da Fatia 2: estender o `gerador_csp.py` (spike da Fatia 1) com as 3 constraints hard intra-treino que já existiam no gerador antigo (H-T1/T2/T3) + a constraint hard cross-treino nova (H-R1) + o consumo da coluna `tier` curada na Parte 1 (substituindo a heurística temporária).

Pré-condição (Frente A): coluna `tier` no XLSX já preenchida na Parte 1 — distribuição final 52P/27I/68A (após movimentação do Nordic Curl no Checkpoint 0 desta sessão).

Escopo declarado (Frente B + D ficam pra Fatia 3+):
- Variedade/fairness cross-rotina (Frente B)
- Vetor de perfil de aluno completo com moduladores (Frente D)

## O que foi implementado

### Checkpoint 0 — pendência rápida de curadoria

`Nordic Curl: Acessório → Intermediário`. Decisão tomada ao revisar o S-T1 do Cenário 2 (handoff). XLSX + log da Parte 1 atualizados. Contagens: Acessório 69→68, Intermediário 26→27.

### Checkpoint 2 — Wire da coluna `tier` + ajuste H-T4

| Mudança | Local |
|---|---|
| Campo `tier: str = ""` no dataclass `Exercicio` | `gerador_treino.py` ~linha 918 |
| `carregar_banco` popula `tier=_str(row.get("tier"))` | `gerador_treino.py` ~linha 1040 |
| Removida heurística `derivar_tier_heuristico` + `PADROES_ANCORA` + `_padrao_e_ancora` | `gerador_csp.py` |
| Novo helper `_tier_rank(ex)` (Tier→IntRank, fallback 1=Acessório se vazio) | `gerador_csp.py` |
| H-T4 com **graceful degradation**: só força não-Acessório se o pool tiver candidato não-Acessório | `gerador_csp.py` |
| Campo novo no resultado: `h_t4_aplicado_efetivamente` (False = degraded) | `gerador_csp.py` |

Default `tier=""` preserva retrocompat com fixtures legacy que constroem `Exercicio` direto (pytest passa 218/218).

### Checkpoint 3 — H-T1 (mesma família refinada intra-treino)

Replicação fiel do predicado clássico `_compativel_intra` ([gerador_treino.py:2158](gerador_treino.py#L2158)): `cand.variacao_de == outro.variacao_de` com AMBOS não-vazios. Pai (variacao_de=None) + filho NÃO é bloqueado — decisão histórica intra preservada.

**Modelagem CSP**: agrupa todas as vars `assign[(sid, cidx)]` por `variacao_de` (não-vazio) e aplica `model.AddAtMostOne()`. Constraint global cross-slots dentro do mesmo treino.

### Checkpoint 4 — H-T2 (variante pontual cross-família same-subregião)

Replicação fiel do predicado clássico ([gerador_treino.py:2155-2161](gerador_treino.py#L2155-L2161)): 2 exercícios com `variante_pontual=True`, mesma subregião e famílias DIFERENTES não coexistem no treino.

**Modelagem CSP**: agrupa VPs por subregião, depois pares all-vs-all dentro do grupo onde `variacao_de` difere → `AddAtMostOne([var_a, var_b])`.

Banco real tem só 2 VPs ativos: Apoio Fechado + Supino Fechado (ambos peito, famílias 'Apoio' e 'Supino Reto'). H-T2 garante que no máximo 1 dos 2 entra por treino.

### Checkpoint 5 — H-T3 (lateralidade contextual em costas)

Replicação fiel do predicado clássico ([gerador_treino.py:2162-2169](gerador_treino.py#L2162-L2169)). Importa `SUBREGIOES_LATERALIDADE_HARD` de [pesos_proximidade.py:44](pesos_proximidade.py#L44) (uma única fonte de verdade canônica entre os 2 geradores).

**Modelagem CSP**: agrupa vars onde `ex.unilateral == "unilateral" AND ex.subregiao in SUBREGIOES_LATERALIDADE_HARD` → `AddAtMostOne` por subregião.

### Checkpoint 6 — refator pra rotina + H-R1 cross-treino

**Mudança arquitetural**: `gerar_treino_csp(demandas, ...)` virou wrapper retrocompatível de `gerar_rotina_csp(demandas_por_treino: list[list[tuple]], ...)`. A função nova negocia N treinos no MESMO `CpModel`, necessário pra H-R1 cross-treino.

**Slots agora indexados por `(t_idx, di, sid_global)`**. Constraints intra-treino (H-T1/T2/T3, H-T4, S-T1) scoped via `t_idx`. AllDifferent global (por nome) continua cross-treino — mantém o comportamento legado de `nomes_exatos_globais` do gerador antigo.

**Implementação de H-R1** (catálogo Seção 1):

```python
H_R1_REGRAS = {
    "costas": {
        "min_slots": 2,
        "eixos": [
            ("puxadas_composto",  lambda e: e.padrao == "puxadas" and e.purpose == "compound"),
            ("remadas_composto",  lambda e: e.padrao == "remadas" and e.purpose == "compound"),
        ],
    },
    "peito": {
        "min_slots": 2,
        "eixos": [("horizontal_composto", lambda e: e.padrao == "empurrar_compostos" and e.purpose == "compound")],
    },
    "perna_anterior": {
        "min_slots": 2,
        "eixos": [
            ("bilateral_composto",  lambda e: e.subregiao == "perna_anterior" and e.unilateral == "bilateral" and e.purpose == "compound"),
            ("unilateral_composto", lambda e: e.subregiao == "perna_anterior" and e.unilateral == "unilateral" and e.purpose == "compound"),
        ],
    },
}
```

Pra cada subregião com ≥ min_slots na rotina (via demandas `subregiao` OU `padrao→subregião 1:1`), e cada eixo: `sum(assign sobre candidatos satisfazendo predicado) >= 1`.

**Graceful degradation H-R1** (decisão Bernardo, 2026-05-23 — análoga ao H-T4 graceful): se o pool não tiver candidato pra um eixo (ex: nível 1 / perna_anterior — todos os unilaterais compostos têm cx > 2), o eixo é PULADO e marcado `degraded=True`. UI deve mostrar o aviso ao usuário. Caso de conflito H-P1 vs H-R1 — implementado, validado em Config A nível 1.

## Decisões fechadas (relevantes pra Fatia 3+)

1. **H-R1 usa `purpose == "compound"`** (composição biomecânica), NÃO `tier != Acessório` (centralidade clínica curada). Apoio (compound + Intermediário) conta como composto horizontal de peito; Hip Thrust (isolation + Principal) NÃO conta como composto.
2. **H-T1 usa `variacao_de`** como família refinada (mesma definição operacional do predicado antigo). Pai+filho NÃO é bloqueado intra. Bloqueio inter-família via S-R3 soft fica pra futura constraint.
3. **H-T3 usa coluna `unilateral`** + `SUBREGIOES_LATERALIDADE_HARD = frozenset({"costas"})` importado de `pesos_proximidade.py` (one source of truth entre os 2 geradores).
4. **S-T1 fica como tier-order soft** (mesma forma da Fatia 1 — penalidade proporcional ao gap, empates aceitos sem pena). Recusada a sugestão de troca por purpose+fadiga: a forma atual já internaliza a curadoria clínica (Hip Thrust=Principal, Apoio=Intermediário) que fadiga sozinha perderia.
5. **H-R1 graceful degradation com flag visível** quando pool não tem candidato. Decisão Bernardo durante implementação. Configuração: campo `degraded=True` + `motivo` no `h_r1_aplicadas[i]`; aviso impresso em `imprimir_rotina_resultado`. UI futura deve renderizar.

## Resultado da validação

Configs do `_main()` (script standalone — `python gerador_csp.py`):

| Config | Demandas | Resultado | Comentário |
|---|---|---|---|
| **A** (nível 3, 5 seeds) | 5 demandas subregião totalizando 8 slots | ✅ 5/5 viáveis, tier-order OK, vagas únicas != Acessório | **Variedade subiu 1→2** rotinas distintas em 5 seeds (vs Fatia 1) — H-T1/T2/T3 quebraram empates do plateau S-T1 |
| **B** (nível 3) | peito(2) + knee_extension(1) + perna_post(1) | ✅ Cadeira Extensora presente; perna_post H-T4 OK (Nordic Curl agora viável após Checkpoint 0) | |
| **C** (nível 3, NOVO) | core_isometrico(1) | ✅ Roda Abdominal — **H-T4 graceful degradation** disparou (pool 100% Acessório pós-curadoria), `h_t4_aplicado_efetivamente=False` | Caso real do conflito H-T4 + curadoria. |
| **D** (nível 3, NOVO) | 2 treinos × {costas(1) + peito(1)} | ✅ T1=Remada Uni Polia + Supino; T2=Puxada Supinada + Supino Fechado; H-R1 costas cobre vertical+horizontal cross-treino; AllDifferent global mantido | |
| **Bônus** (nível 1) | Config A com pool cx ≤ 2 | ✅ viável; **perna_anterior/unilateral_composto degraded** com flag — H-P1 esvaziou o eixo no pool, H-R1 pulou | Caso real do conflito H-R1 vs H-P1. Decisão Bernardo. |

**Tempos de solving**: 0.005–0.04s por rotina (limite era 1s da Fatia 1, sem regressão).

**Regressão**: pytest 218 passed + 13 snapshots ✓ + 1 skip (pré-existente). Gerador antigo intacto.

## Achados / sinais de alerta

1. **Variedade subiu sem esforço** (Config A: 1→2 distintas em 5 seeds). Adicionar H-T1/T2/T3 hard quebrou alguns dos empates que prendiam o solver no plateau de S-T1. **NÃO resolve o determinismo geral** — ainda 2/5 é baixo. Variedade explícita continua tarefa da Fatia 3. Mas é um bônus: as novas constraints clínicas também melhoram exploração.

2. **6º NO-OP estrutural — Hip Thrust em vaga única.** Antes (heurística), perna_posterior vaga única caía em Stiff B-Stance. Agora, com tier curado, Hip Thrust (Principal curado) seria empate, MAS o solver continua escolhendo Stiff por causa do tie-break determinístico. NÃO é regressão — é apenas que a curadoria não diferenciou o suficiente entre 2 Principais que cobrem o mesmo slot. Fairness/variedade pra Fatia 3.

3. **Conflito H-P1 vs H-R1 é real**. Iniciante (cx ≤ 2) não tem pool pra cumprir todos os eixos de perna_anterior. Graceful degradation resolve. Implicação: H-R1 como "hard puro" do catálogo precisava da exceção do pool — agora documentada como decisão clínica do Bernardo, não bug.

4. **`min_slots=2` é uniforme em H-R1**. Catálogo já assume isso. Subregião com 1 slot não dispara H-R1 (decisão clínica: 1 slot é "tem que ser bom (H-T4)", não "cobre eixos").

5. **Pareamento de blocos não modelado**. Decisão de fora do MVP da Fatia 2: a Frente B (variedade) e a modelagem de blocos (`SuperSerie` do gerador antigo) ficam pra Fatia 3+. O resultado atual entrega exercícios em ordem linear — equivalente a 1 ex por bloco. UI pode renderizar como blocos clinically depois.

## Conclusão

Fatia 2 Parte 2 fecha **5/6 das hard constraints do catálogo** (faltam só H-P2 e H-X, que dependem do vetor de perfil completo) + a **graceful degradation pragmática nos 2 cantos onde regras hard colidem com filtros físicos** (H-T4 vs curadoria CORE = pool 100% Acessório; H-R1 vs H-P1 = pool sem composto unilateral). Modelo segue declarativo (todas as constraints são entradas independentes), resolve em <50ms, sem ordem de processamento entre constraints.

A engine CP-SAT continua viável pro domínio, agora com cobertura clínica genuína (cross-treino) ativa.

## Próximos passos (Fatia 3 — não iniciada)

- **Variedade/fairness** como first-class na função objetivo (Frente B do plano original).
- **Vetor de perfil de aluno completo** com moduladores (Frente D).
- **Pareamento de blocos** (S-B1 / S-B2 / S-B3 / S-B4 do catálogo).
- Outras hards (H-P2 bloco solo, H-X restrições físicas).
- Outras softs (S-T2 fadiga blocos, S-T3 demanda neural total, S-T4 variedade eixos soft, S-R* família/freq/nome, S-H1 histórico).
- Integração com a UI Flask atual — substituir `gerador_treino.py` em pelo menos uma rota.
