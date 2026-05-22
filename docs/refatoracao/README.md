# Refatoração do gerador de treinos

> **Status**: refator declarativo (CSP/ILP) em andamento desde 2026-05-19. Próximo passo: Fatia 1 do MVP (spike de viabilidade do CP-SAT).

## Fonte de verdade (ler nesta ordem)

1. **`handoff_2026-05-19_decisao_refator.md`** — decisão estrutural, contexto do refator, estado atual do fluxo de 5 passos.
2. **`principios_clinicos.md`** — 12 conceitos clínicos + vetor de perfil de aluno (4 dimensões). O QUE valorizar.
3. **`catalogo_constraints.md`** — passo 2 do fluxo. 8 hard + 12 soft constraints + função objetivo + modelo de dados. O QUE implementar.

Esses três documentos são a especificação executável do gerador novo. Adicionar regra clínica nova = editar este conjunto, não código.

## Histórico

A pasta `arquivo/` contém documentos de eras anteriores, preservados como referência histórica:

- `arquivo/era_v4_greedy_incremental/` — refator incremental por Etapas 1-8 (caminho do meio, paradigma greedy sequencial). Superado pelo refator declarativo em 2026-05-19. Conhecimento ainda relevante para entender por que certas decisões foram tomadas, mas NÃO usar como referência operacional.
- `arquivo/` (raiz) — documentos pré-v4 já arquivados antes.

**Para qualquer agente (Claude Code, etc.)**: não consultar `arquivo/` para planejar implementação. Use exclusivamente os 3 docs da raiz.

## Estado do fluxo (5 passos)

1. ✅ Princípios clínicos
2. ✅ Catálogo de constraints
3. ⏳ Cadastro: tier, estabilidade_externa, demanda_lombar (em parte coberto pela heurística inicial da Fatia 1 do MVP)
4. ⏳ Engine declarativa CSP/ILP (Fatia 1 do MVP é o spike inicial)
5. ⏳ Dashboard de calibração quantitativa

Detalhes em `handoff_2026-05-19_decisao_refator.md` (seção "Update 2026-05-21").
