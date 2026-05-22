# Log — MVP Fatia 1: spike de viabilidade CP-SAT

**Data**: 2026-05-22
**Branch/commit**: `main` · `79ab9b8`
**Arquivo entregue**: `gerador_csp.py` (novo, paralelo ao `gerador_treino.py` — antigo NÃO tocado)
**Status**: ✅ concluída — 5/5 critérios de fechamento PASS

---

## Objetivo

Spike de viabilidade do gerador declarativo (passo 4 do fluxo do refator).
Caminho iterativo escolhido: **tier por heurística temporária + engine CP-SAT
mínima rodando**, em vez de cadastrar `tier` à mão nos 147 exercícios antes da
engine. Cadastro real fica pra Fatia 2, depois do spike confirmar viabilidade.

Escopo mínimo: 3 das 20 constraints do `catalogo_constraints.md` + filtro `ativo`.

## O que foi implementado

| Constraint | Tipo | Implementação |
|---|---|---|
| **H-T4** | hard | Vaga única de **subregião** (qtd=1) ⇒ tier ≠ Acessório. Atribuições de Acessório forçadas a 0 nesses slots. |
| **S-T1** | soft/objetivo | Tier-order dentro de cada grupo de demanda. `viol ≥ tier[j] − tier[i]` para pares i<j; minimiza a soma. Penalidade proporcional ao gap de tier. |
| **H-P1** | filtro de pool | Nível técnico do aluno filtra por `complexidade` antes do solver. Tetos: nível 1 → cx≤2, nível 2 → cx≤3, nível 3 → sem teto. |
| filtro `ativo` | load | Reuso de `gerador_treino.carregar_banco` (já descarta `ativo=False`). 144/147 ativos. |

Modelagem CP-SAT: 1 demanda `(nivel, escopo, qtd)` → `qtd` slots; bool de
atribuição `assign[slot, candidato]` com `AddExactlyOne`; `AddAtMostOne` por
nome (AllDifferent global); `tier_rank` por slot como IntVar. Todos os slots no
mesmo modelo, **sem ordem de processamento** (princípio declarativo do refator).

## Decisões fechadas (relevantes pra Fatia 2)

1. **"Padrão é âncora?" = membership em `ANCORAS_POR_SUBREGIAO`** (qualquer
   obrigatoriedade), NÃO `obrigatoria=True`. Razão: `obrigatoria=True` rebaixaria
   `squat_unilateral` (compound) a Intermediário, criando hierarquia
   bilateral>unilateral que Bernardo rejeitou — bilateralidade é ortogonal a
   tier. `squat_unilateral` é o único padrão `obrigatoria=False` com compounds
   (os demais não-obrigatórios são isolation → Acessório de qualquer jeito), logo
   membership ≡ "obrigatoria=True + exceção squat", sem caso especial.

2. **H-T4 só se aplica a demandas de `subregiao`**, não de `padrao`. Catálogo diz
   "vaga única **na subregião**". Demanda de padrão = intenção explícita do
   usuário; H-T4 não second-guessa. É o que faz a Config B funcionar
   (`knee_extension=1` → Cadeira Extensora, mesmo sendo Acessório).

3. **Heurística de tier é TEMPORÁRIA** (purpose+padrão). Distribuição no banco:
   Principal 82 / Acessório 62 / Intermediário **0** (vazio — será populado à mão
   na Fatia 2). Vira ~2 tiers efetivos no spike. Aceito porque a coluna `tier`
   manual da Fatia 2 substitui a função inteira.

## Resultado da validação (5/5 PASS)

| Critério | Resultado |
|---|---|
| 1. Vaga única tem tier ≠ Acessório (5/5 rotinas Config A) | ✅ |
| 2. Tier-order respeitado dentro de subregião (5/5, inversões 0) | ✅ |
| 3. Filtro de complexidade (pool 144→123→78 p/ nível 3→2→1) | ✅ |
| 4. Filtro ativo=True (Box Jump, Air Bike Sprint/Steady ausentes) | ✅ |
| 5. Config B → Cadeira Extensora selecionada (knee_extension) | ✅ |

Performance: **0.01–0.04s** por rotina (limite era 1s). Sem sinal de problema
de modelagem.

## Achados / sinais de alerta

1. **Determinismo do solver** (achado central de design): as 5 rodadas de Config
   A com seeds diferentes (42–46) retornaram a **MESMA rotina**, apesar de
   `random_seed` + `randomize_search`. CP-SAT, num objetivo com muitas soluções
   ótimas-empatadas (todas 0 inversões), retorna sempre a primeira ótima. **Não é
   bug** — confirma que **variedade/fairness não vem de graça do solver** e
   precisa de modelagem explícita (perturbação do objetivo, constraint de
   diversidade, ou seleção pós-hoc estilo softmax). O handoff já previa "fairness
   como first-class na função objetivo". Provável próximo grande ponto de design.

2. **knee_extension NÃO precisou de hack no pool default** de `perna_anterior`.
   H-T4 sozinho resolve: Cadeira Extensora fica no pool por subregião, mas é
   bloqueada em vaga única; em qtd≥2 é acessório elegível (= output esperado:
   Agachamento + Cadeira Extensora).

3. **Hip Thrust = Acessório** (esperado, `notas_cadastro.md`). Não apareceu em
   posição estranha nestas configs (perna_posterior só testado em vaga única →
   Stiff via H-T4). Apareceria em qtd≥2; tier dele é refinamento Fatia 2.

4. **Goblet Rampa / Apoio Elevado = Principal** pela heurística (compound em padrão
   âncora), divergindo do Conceito 1 (acessórios). Caso-escola de `purpose ≠ tier`
   — só o cadastro manual resolve.

## Conclusão

CP-SAT é **viável** pro domínio. As 3 constraints modelam-se de forma limpa,
declarativa, sem ordem de processamento, e resolvem instantaneamente. O spike
cumpriu seu papel: validar a abordagem e revelar o ponto de design de
variedade/determinismo antes do investimento de cadastro manual.

## Próximos passos (Fatia 2 — não iniciada)

- Cadastrar coluna `tier` à mão no XLSX (substitui a heurística).
- Decidir modelagem de variedade/fairness (resposta ao determinismo do solver).
- Adicionar mais constraints do catálogo conforme prioridade (família H-T1/2/3,
  cobertura de eixos H-R1, pareamento de blocos, etc.).
- Vetor de perfil de aluno completo (moduladores de peso).
