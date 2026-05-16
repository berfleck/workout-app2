# Log — Fase 4: Cadastro das 5 Dimensões de Proximidade

**Branch:** `fase-4` (a partir de `main` @ `ecc7c19`)
**Período:** 2026-05-14 (Sessão Sonnet) + 2026-05-15 (Sessão Opus)
**Scope:** Preencher 5 colunas dims (`variacao_de`/familia_estrita, `pegada`,
`plano_corporal`, `equipamento_grupo`, `variante_pontual`) em todos os
exercícios do XLSX (`banco_exercicios.xlsx`) + Annexo 4.1 itens pendentes.

---

## Sub-tarefas e commits

| Sub | Commit | Descrição |
|-----|--------|-----------|
| Triagem | `ce55db3` | Triagem completa 136 ex (script + triagem_fase_4.md) |
| 4.2-A | `c05a7bc` | Annexo 4.1 items 7+8+11: renames variacao_de |
| 4.2-B | `72a2d0b` + `906d5d4` | Annexo 4.1 items 3+13: purpose + split família prancha |
| Sub-C | `a0f9e1b` | Setup estrutural: 5 colunas dim + loader ativo/variante_pontual |
| Handoff | `1016b9a` | Auditoria C1-C7 + YAML + anti-padrões (sessão Sonnet) |
| Sub-D | `5fe25ed` | Cadastrar 11 mock_futuros + expandir rotacao_tronco dyn |
| Sub-E | `72bb9c4` | Port 66 entradas YAML → XLSX (5 colunas dims) |
| Sub-F | `a423ec8` | Preencher dims para 59 exercícios non-YAML |
| Sub-H | `56052b5` | Remada Landmine split (Annexo 4.1 item 1) |

---

## Resultado final

**Banco:** 137 exercícios (125 originais + 11 mock_futuros + 1 Remada LM Aberta)

**5 colunas dims preenchidas em 100% dos exercícios:**
- `variacao_de` (familia_estrita): 125/137 preenchidas + 12 null por decisão clínica
- `pegada`: null por default; exceções: neutra (Landmine press/row, crossovers,
  pulldowns supinados, barras abertas/supinadas, etc.), pronada (supinos, empurrar,
  curvadas), aberta (puxadas abertas, remada LM Aberta), supinada (puxadas supinadas)
- `plano_corporal`: null por default; preenchido para peito (reto/inclinado/
  pullover), costas (curvada/suspensão/apoiada/baixa_sentada/unilateral_apoiada),
  hinge (em_pe: stiffs/terra/good morning/hiper45°; deitado: thrusts/pontes)
- `equipamento_grupo`: preenchido individualmente por evidência de eq_primario +
  decisões C1-C7; null para: TRX (não tem grupo), Feijão/Slide (C5), cardio
- `variante_pontual`: False para todos; True apenas para Supino Fechado e
  Apoio Fechado (narrow-scope cross-family)

---

## Decisões clínicas registradas (C1-C7)

| ID | Decisão | Exercícios |
|----|---------|-----------|
| C1 | `flexao_plantar` → `pegada=null` | Elevação Panturrilha (2) |
| C2 | Face Pull (Polia) → `pegada=null` (corda permite rotação) | Face Pull |
| C3 | Desenvolvimento Landmine → `pegada=neutra` | Desenv. Landmine |
| C4 | anilha → `equipamento_grupo=halter` (default) | Elev. Frontal Anilha |
| C4-exc | Lev. Terra Anilha → `barra` (família terra = família de barra) | Lev. Terra Anilha |
| C4-exc2 | Supino Com Anilha → `null` (eixo de equipamento não aproxima) | Supino Com Anilha |
| C5 | Feijão/Slide Board → `equipamento_grupo=null` | Flexão Joelhos Feijão/Slide |
| C6 | Hip Thrust Uni./Ponte Uni./Copenhagen → `corporal` | 3 exercícios |
| C7 | Hiperextensão 45° → `plano_corporal=em_pe` | Hiperextensão 45° |

**C7+extra:** Hiperextensão 45° → `equipamento_grupo=maquina` (não `caixa`
como triagem auto-gerou — Roman chair = máquina dedicada).

**Elevação Panturrilha:** eq_primario=Rack → `corporal` (bodyweight com rack
para equilíbrio; triagem assumia `barra` erroneamente).

---

## Sub-H — Remada Landmine split (Annexo 4.1 item 1)

"Remada Landmine" renomeada para "Remada LM Neutra" + nova linha
"Remada LM Aberta" (pegada=aberta). Ambas mantêm `variacao_de='curvada'`
(família curvada existente, consistente com Remada Curvada Barra/Halteres/Smith).

Nota sobre spec: Annexo item 1 dizia `variacao_de = "remada curvada"`, mas YAML
(ported Sub-E) já consolidou como `"curvada"` — mantemos `"curvada"` para
consistência com a família estabelecida. Se houver motivo clínico para separar
as LM em família própria, reabrir com justificativa.

---

## Anti-padrões identificados na sessão Sonnet (aplicar em futuras sessões)

1. **Anti-padrão 1 — Violação doc-first**: nunca abrir AskUserQuestion sobre dim
   de exercício sem varrer Annexo 4.1/4.2 + Seção 2 + Seção 7 primeiro.

2. **Anti-padrão 2 — Shorthand prevalece sobre detalhado**: regra detalhada
   (ex: Seção 1.6 "pontes simples → corporal") prevalece sobre heurística geral.

3. **Anti-padrão 3 — Analogia de exceção além do escopo nominal**: exceções
   nominais (ex: Lev. Terra Anilha = barra) não se estendem por analogia a
   outras famílias (Supino Com Anilha ≠ barra).

---

## Sub-G — Validação dos 12 casos amarelos

Todos os 12 casos 🟡 da triagem foram resolvidos via C1-C7 + evidência de
eq_primario. Desvios da proposta da triagem auto-gerada:

| Caso | Proposta triagem | Decisão final | Justificativa |
|------|-----------------|---------------|---------------|
| Face Pull pegada | aberta | null | C2: corda permite rotação |
| Lev. Terra Anilha equip | halter | barra | C4-exc: família terra |
| Feijão/Slide equip | corporal | null | C5: sem grupo exato |
| Hiperextensão 45° equip | caixa | maquina | Roman chair = máquina |
| Elevação Panturrilha equip | barra | corporal | eq_primario=Rack (bodyweight) |

---

## Pytest + harness (Fase 4.8)

**pytest:** 175 passed, 1 skipped (mesmo baseline de Etapa 8)

**Snapshots atualizados ao longo de Fase 4:**
- Sub-D: 8 snapshots (bank size 125→136)
- Sub-E: 9 snapshots (variacao_de changes affect _compativel_intra)
- Sub-F: 6 snapshots (score-aware tem mais dims preenchidas)
- Sub-H: 3 snapshots (Remada LM rename + nova Aberta)
- Total: 26 atualizações ao longo da Fase 4

**Seed HIB2 test** (`test_filtro_carga_realmente_dissolve_par_conhecido`):
- Sub-D: seed 3→1 (Lev.Terra + Remada Baixa Aberta)
- Sub-F: seed 1→4 (Lev.Terra + Barra Isométrica, grip G=6)

**Harness calibrar_pesos_dimensoes.py:** 16/16 OK
- 4.1 = 19.76% (informativo — 6º NO-OP por viés de distribuição mono-ex,
  Seção 8.15.12; baseline Etapa 8 era 21.54%; leve melhora esperada pela
  diversidade adicional das LM e exercícios novos)
- 4.2 = 46.91% (informativo — toggle OFF aceita repetição)
- Todos os demais cenários: OK

---

## Estado do git ao fechar

**Branch:** `fase-4`
**HEAD:** `56052b5` (Sub-H)
**Working tree:** limpo (salvo este log)

**Pendências pós-Fase 4 (não bloqueiam uso real):**
- YAML overlay (`dimensoes_etapa_6.yaml`) tem "Remada Landmine" como entry —
  agora desatualizado (renomeado para "Remada LM Neutra"). Harness não falha
  (apenas ignora entry sem match), mas pode ser limpo em manutenção futura.
- mock_futuros no YAML (5 restantes: Russian Twist + 4 INFRAs) têm dims
  no YAML overlay mas também foram cadastrados no XLSX em Sub-D — dupla fonte.
  O XLSX é a fonte de verdade; o YAML overlay é redundante para esses.
- Pendência 4 da 8.15.7: mock_futuros no XLSX podem reduzir piso 4.1 (já
  refletido na leve melhora 21.54% → 19.76%).
