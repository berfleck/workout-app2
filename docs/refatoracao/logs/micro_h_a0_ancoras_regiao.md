# Log — Micro-frente H-A0 (âncoras obrigatórias por região no CSP)

**Data**: 2026-05-25
**Branch**: `frente-h-a0` (a partir de `main`)
**Bloco**: 4 do roadmap CSP — primeiro item prioritário pós-Frente E.1

**Arquivos atualizados**:
- `gerador_csp.py` — import de `ANCORAS_POR_REGIAO` + filtro upstream do
  pool por subs-âncora + bloco H-A0 reordenado ANTES do H-A1 (sub_idx +
  constraint per-treino + marker via `subregioes_obrigadas_ha0`) +
  extensão do H-A1 lendo marker + correção de `vagas_garantidas_por_sub`
  separado de `len(sids)` (necessário pro conflito de cardinalidade
  correto quando marker H-A0 contribui)
- `app_flask.py` — `_distribuir_avisos_rotina_csp` ganhou branch
  `h_a0_degradado` (per-treino, lê `aviso['treino']`); `_resultado_csp_pra_sessao`
  ganhou o mesmo branch pro caminho `/regerar` (1 treino)
- `templates/_avisos_modal.html` — clause `h_a0_degradado` análoga a
  `h_r1_degradado` (🎯 amber, lista região + subregião + motivo)
- `tests/test_ha0_ancoras_regiao_csp.py` — 15 testes novos
- `tests/test_ha1_ancoras_subregiao_csp.py` — 1 teste atualizado
  (`test_demanda_regiao_nao_ativa_ha1` → `test_demanda_regiao_ativa_ha1_via_marker_ha0`)
  refletindo a interação H-A0 × H-A1 via marker
- `tools/harness_comparativo_e0.py` — 2 métricas novas
  (`cobertura_ha0_por_treino`, `degradacoes_ha0_media`) + nova config
  canônica `Full Body 2T (região, H-A0)` que reproduz o setup do achado
- `docs/refatoracao/catalogo_constraints.md` — seção H-A0 nova na Seção 1
  (escopo ROTINA)
- `docs/refatoracao/relatorios/E0_2026-05-25_pos_h_a0.md` — comparativo
  CSP × antigo pós-H-A0 (rodada N=100)
- `docs/refatoracao/roadmap_csp.md` — H-A0 marcado ✅ no Bloco 4

**Status**: ✅ concluída — todos os critérios de gate do handoff atendidos.
Aguardando aprovação do Bernardo pra merge em `main` (disciplina de merge
do roadmap exige confirmação explícita).

---

## Objetivo

Fechar bug clínico bloqueador descoberto na auditoria pós-E.1 (2026-05-25):
rotina Full Body 2T gerada via `/gerar` (demanda nível região via UI
default) saiu com **zero exercícios de costas em 16 slots** e **zero squat
em 6 slots de lower**. CSP devolveu OPTIMAL em 0.29s — constraints
declaradas todas satisfeitas, mas rotina clinicamente catastrófica.

**Diagnóstico técnico**: H-A1 (Bloco 2.5) só dispara em demanda nível
subregião. Demanda nível região passava pela enumeração de subregiões via
S-B1/Aderência/cycling fairness — nenhum tem semântica de "cobrir
repertório básico". UI real manda nível região por default (Full Body),
então o vazio aparece em uso real.

**Diagnóstico metodológico**: 318 testes pytest + 16 cenários do harness
antigo + 7 métricas do E.0 medem conformidade às constraints declaradas,
não adequação clínica da rotina entregue. Antipadrão norte Seção 7 caiu
apesar de documentado. Gap metodológico (Problema B) fica fora do escopo
desta frente — Bernardo endereça depois.

Spec: `catalogo_constraints.md` seção H-A0 (acima de H-A1).

## Decisões fechadas (handoff 2026-05-25 + AskUserQuestion inicial)

### Do handoff (Seção 4)

1. **Per-treino, não cross-treino** (4.1) — semântica de "treino de upper"
   cobre upper NAQUELE treino. Achado de hoje confirma: T1 sem peito + T2
   com peito passaria num gate cross-treino, mas T1 continua sendo ruim.
2. **Interação H-A0 × H-A1 via marker (Caminho B)** (4.2) — estrutura
   paralela `subregioes_obrigadas_ha0[(t_idx, R)] = set(subs)` populada
   pelo H-A0, lida pelo H-A1 que estende `slots_subregiao_explicita`. Não
   precisa de campo `subregiao_obrigada_por_ha0` no slot.
3. **Rejeição de subs não-âncora HARD (Caminho A)** (4.3) — filtro
   upstream no `pool_default_sem_travados` antes de criar vars `assign`.
4. **Reuso `ANCORAS_POR_REGIAO` do gerador_treino** (4.4) — não duplicar.
5. **NÃO importar `_decompor_demanda_regiao` do antigo** (4.5) — viola
   norte Seção 5 (declarativo até o fim).
6. **NÃO modelar `PROPORCAO_COMPOSTOS = 0.6`** (4.6) — cobertura de
   compostos vem via H-A1 marker (peito → `empurrar_compostos`).
7. **ConfigVariedade preservado** (4.7) — H-A0 não muda nada no wiring.
8. **Nomenclatura H-A0 (não H-A2)** (4.8) — sufixo 0 = "âncora mais
   primitiva" (decide subregião antes de H-A1 decidir padrão).
9. **NÃO reverter merge da E.1** (4.9) — H-A0 é a correção pra frente.

### Da AskUserQuestion inicial (Seção 5)

10. **§5.1 Filtro upstream pool_slot** (recomendação a) — escolhida.
    Modelo menor, replica como H-A1 trata pool já filtrado por H-P1.
    Travados em demanda região não fazem sentido clínico atual.
11. **§5.2 Reordenar + estrutura paralela** (recomendação a) — escolhida.
    H-A0 popula `subregioes_obrigadas_ha0[(t_idx,R)] = set(subs)`; H-A1
    itera sobre ela ativando padrões obrigatórios nos slot_ids da demanda
    região. Mais limpo que marker por sid (que esbarra em "qual sid vai
    pra X?" — H-A0 garante ≥1 mas não fixa).
12. **§5.3 Smoke pytest + paramétricos** (recomendação c) — escolhida.
    15 testes em `test_ha0_ancoras_regiao_csp.py`: regressão protetora do
    seed=42/Full Body 2T (test_full_body_2t_seed42_cobertura_completa) +
    paramétricos.
13. **§5.4 Métricas E.0 incluídas agora** (recomendação a) — escolhida.
    `cobertura_ha0_por_treino` + `degradacoes_ha0_media` no harness +
    config nova `Full Body 2T (região, H-A0)`.

## O que foi implementado

### Filtro upstream (decisão 4.3 / 5.1) em `gerador_csp.py`

Quando demanda é `("regiao", R, qtd)` com R em `ANCORAS_POR_REGIAO`,
o `pool_default_sem_travados` rejeita exercícios cuja `subregiao` não
está em `[a["subregiao"] for a in ANCORAS_POR_REGIAO[R]]`. Replica como
H-P1 filtra antes do solver — modelo menor, branching menor.

### Bloco H-A0 reordenado antes do H-A1

Inserido após o bloco H-R1 e ANTES do bloco H-A1. Estrutura:

1. **Coleta**: itera por treinos e populates por (t_idx, R) com R em
   `ANCORAS_POR_REGIAO`. Cria IntVar `sub_idx[s] = sum(assign × sub_id)`
   por slot de demanda região (canalização via soma ponderada — mesma
   técnica de `grupo_func`, `tier_rank`).
2. **Detecção de degraded-por-pool**: sub obrigatória sem nenhum candidato
   no pool dos slots daquele (treino, região) → constraint pulada, marcada
   `degraded=True`.
3. **Caso normal** (`vagas >= n_ativas`): 1 constraint hard por sub
   obrigatória ativa — `sum(BoolVar reificadas sobre sub_idx == sub_id) >= 1`.
   Estrutura `subregioes_obrigadas_ha0[(t_idx, R)] = set(ativas)` populada.
4. **Conflito de cardinalidade** (`vagas < n_ativas`): constraint
   colaborativa `sum(obrig_usadas_vars) >= vagas` força N distintas. Cada
   uma marcada `degraded=True` com motivo `conflito_cardinalidade`.
   **Marker NÃO populado** nesse caso — nenhuma sub é garantida
   individualmente (decisão crítica do empírico — ver Achado #2 abaixo).

### Extensão do H-A1 lendo marker

Após a coleta direta de `slots_subregiao_explicita` por demanda subregião,
estende com slots da demanda região cujas subregiões estão obrigadas por
H-A0. Estrutura `vagas_garantidas_por_sub` separa contagem de vagas
GARANTIDAS por sub da contagem `len(sids_lista)`. Necessária porque marker
adiciona TODOS os sids da demanda região à lista de cada sub obrig (sub_idx
decide qual em runtime), mas só 1 desses sids está GARANTIDO pra aquela
sub — detecção de conflito de cardinalidade do H-A1 (vagas < n_ativas)
deve usar vagas garantidas reais.

### Propagação `h_a0_aplicadas` no retorno

Análoga a `h_r1_aplicadas` / `h_a1_aplicadas`. Cada entrada:

```python
{
    "treino": int,                       # ÍNDICE do treino (per-treino)
    "regiao": str,
    "subregiao_obrigatoria": str,
    "n_slots": int,
    "degraded": bool,
    "motivo": str (opcional, só se degraded=True),
}
```

Propagada em 6 sítios:
- `_construir_modelo` (return dict)
- `_resolver_legacy` (viável + inviável)
- `_resolver_com_variedade` (viável + inviável)
- `gerar_treino_csp` (viável + inviável)

### Adapter `app_flask.py`

`_distribuir_avisos_rotina_csp` (rotina inteira / `/gerar`): branch
`h_a0_degradado` lê `aviso["treino"]` direto (H-A0 é per-treino — entrada
já carrega t_idx; não usa o mapa subregião→treino do H-A1).

`_resultado_csp_pra_sessao` (1 treino / `/regerar`): branch espelhado.

### Modal `_avisos_modal.html`

Clause `ha0_deg` (lista filtrada por `selectattr("tipo", "equalto",
"h_a0_degradado")`) análoga ao `ha1_deg`. Renderiza: "Região X: subregião
obrigatória Y ficou sem cobertura (motivo Z)". Header inclui `ha0_deg` na
condição `Treino N foi gerado com restrições`.

## Decisões de implementação

- **Reuso de `ANCORAS_POR_REGIAO`** via import (`from gerador_treino import
  ANCORAS_POR_REGIAO`). Mesmo padrão de `ANCORAS_POR_SUBREGIAO`,
  `PADRAO_PARA_SUBREGIAO`, etc. Fonte canônica única entre motores.
- **Canalização `sub_idx[s]`** via soma ponderada `sum(assign × sub_id)`.
  `AddExactlyOne(assign[s,*])` já força que exatamente 1 candidato é
  escolhido, então `sub_idx[s] = subs_ancora.index(ex_escolhido.subregiao)`
  automaticamente.
- **Marker SÓ no caso normal** (vagas ≥ n_ativas) — decisão tomada em
  resposta ao Achado #2 (ver abaixo): em conflito de cardinalidade, nenhuma
  sub é garantida individualmente, marker não deve ativar H-A1 pra todas.
- **Carve-outs antigos** (`SUBREGIOES_CARVE_OUT_QUOTAS` em
  `gerador_treino.py`, ombro vaga-única `SUBREGIOES_SORTEIO_VAGA_UNICA`)
  ficam de fora — são distribuição/sorteio, não obrigatoriedade. Migram em
  S-A1 (distribuição entre âncoras não-obrigatórias) ou frente separada.

## Achados

### 1. ABC 3T preservada — H-A0 não afeta demanda nível subregião

Configs do harness E.0 que usam só demanda subregião (ABC 3T, perna 1T,
Full Body 2T original subregião) não disparam H-A0 — `h_a0_aplicadas`
vazio. Comportamento idêntico ao pré-H-A0; H-A1 do Bloco 2.5 continua
governando.

### 2. Conflito de cardinalidade entre H-A0 × H-A1 marker requer correção (descoberto na pytest)

Cenário: `("regiao","upper", 3)` com nivel=3, seed=0.

**Problema inicial**: minha primeira implementação do marker fez
`vagas_garantidas_por_sub[sub] += 1` em TODOS os casos (normal +
conflito), e usou `vagas_garantidas` no H-A1 ao detectar conflito. No
caso `upper(1)` (1 vaga, 3 obrigatórias):

- H-A0 conflito: solver escolhe 1 das 3 subs (sem favorecer).
- Marker erroneamente populado com todas as 3 → H-A1 estende
  `slots_subregiao_explicita[peito]`, `[costas]`, `[ombro]` com o 1 sid.
- H-A1 calcula `vagas_garantidas[peito]=1, n_ativas=1` (emp_comp) → cria
  constraint hard "≥1 emp_comp". Mas peito pode não ser escolhida pela
  H-A0 (conflito). Solver entra em INFEASIBLE.

**Fix**: marker SÓ popula no caso normal (vagas ≥ n_ativas). Conflito de
cardinalidade não garante sub específica, então H-A1 marker não deve
ativar pra nenhuma das obrigatórias. H-A0 ainda força a cobertura
coletiva ("≥1 das 3 subs entra") mas H-A1 fica vazio pras subs de upper(1).

**Segundo problema**: em `upper(3)` (3 vagas, 3 obrigatórias), o caso é
NORMAL. Marker popula peito/costas/ombro. H-A1 estende. Pra costas
(2 obrigatórias remadas+puxadas), o cálculo `vagas = len(sids) = 3` (3
slots da demanda região) era usado, mas só 1 desses slots virará costas.
Logo `vagas=3 ≥ n_ativas=2` → cria 2 hard constraints "≥1 remadas" E
"≥1 puxadas" em slots heterogêneos onde apenas 1 será costas. INFEASIBLE.

**Fix**: `vagas_garantidas_por_sub` separado de `len(sids_lista)`.
Marker contribui +1 por (t_idx, R, sub) ao `vagas_garantidas`. Pra costas
em `upper(3)`: `vagas=1` (1 slot garantido como costas via marker
H-A0) < `n_ativas=2` → constraint colaborativa "≥1 das 2 distintas" no
H-A1. Solver escolhe remadas ou puxadas. **upper(3) viável e
clinicamente correto**: 1 peito+emp_comp + 1 costas+remadas (puxadas
degradada por conflito) + 1 ombro+ombro_composto.

### 3. Smoke pós-H-A0 confirma fechamento clínico do achado

`tools/criar_aluno_e_rotina_teste.py` com seed=42 (aluno Teste CSP):

| Treino | Pré-H-A0 | Pós-H-A0 |
|---|---|---|
| T1 | 0 costas, 0 ombro, 0 squat unilateral | peito (Crucifixo→Supino c/ Halt), costas (Pullover→Puxada Uni), ombro (Posterior Ombro→Desenv Halt Sent), perna_ant (Smith Rampa→Step Up), perna_post (Ponte→Stiff Uni) |
| T2 | 3 peito isolados, 0 costas, 0 squat | peito (Crossover Sent), costas (Serrote→Remada Aberta Trx), ombro (Desenv→Elev Lat), perna_ant (Recuo Estepe→Agachamento Goblet), perna_post (Stiff→Ponte Caixa) |
| h_a0_aplicadas | (não existia) | 10 entries, **todas degraded=False** |

### 4. Harness E.0: ganho clínico mensurável na métrica nova

`upper(3)×2T` (N=5 smoke):
- CSP: 100% cobertura em peito/costas/ombro pra T1 E T2.
- Antigo: 100% peito/costas; **40% T1 ombro, 60% T2 ombro** (ombro
  ausente em ~50% das rotinas em algum treino).

`Full Body 2T (região, H-A0)` (N=5 smoke — config nova):
- CSP: 100% cobertura em todas (peito/costas/ombro + perna_ant+perna_post)
  em ambos treinos.
- Antigo: 100% nas peito/costas/perna_*, mas 40-60% no ombro.

Métrica `cobertura_ha0_por_treino` operacionaliza diretamente a pergunta
"a rotina cobre o repertório clínico básico desse treino?" — que era o
gap metodológico que motivou a frente.

### 5. Trade-off de tempo: insignificante

Smoke seed=42 Full Body 2T (região): 0.43s (pré-H-A0: 0.29s). +50% em
solve absoluto mas magnitude irrelevante para usuário (<1s).
`upper(3)×2T` (N=5 smoke) preserva os tempos do baseline.

## Resultado da validação (gate de fechamento)

| Critério | Resultado |
|---|---|
| Pytest H-A0 novos (15 testes) | ✅ 15/15 passed |
| Pytest baseline (334 = 318+15+1 atualizado) | ✅ 334 passed, 1 skipped |
| Pytest H-A1 atualizado (test_demanda_regiao_ativa_ha1_via_marker_ha0) | ✅ verde |
| Harness antigo 16/16 | ✅ preservado, NO-OPs informativos inalterados |
| Harness comparativo E.0 N=100 (relatório oficial) | ✅ gerado em `relatorios/E0_2026-05-25_pos_h_a0.md` |
| Smoke achado clínico (seed=42 / Full Body 2T região) | ✅ T1 e T2 com peito + costas + ombro + perna_ant + perna_post |
| Banimento hard de bracos em upper / adutores em lower | ✅ 0 ocorrências em 5 seeds testadas |
| Cobertura H-A0 100% em upper(3)/lower(3) — CSP | ✅ (vs 40-60% no antigo pro ombro em upper) |
| Conflito de cardinalidade upper(1) | ✅ constraint colaborativa funciona; viável; 2 degraded |
| Pool sem candidato (banco sem peito) | ✅ degrada com aviso `pool sem candidato`; constraint pulada |
| Interação H-A0 × H-A1 marker em upper(3) | ✅ H-A1 ativa via marker; conflito costas degrada via constraint colaborativa |

## Próximos passos

- **Mergear em main** após aprovação do Bernardo (disciplina de merge).
- **Bloco 4 continua**: próximo item priorizado pela auditoria clínica é
  o **gate de avaliação clínica semântica** (Problema B do handoff —
  fora do escopo desta frente). Esse gate é o que pega problemas
  desse tipo antes do merge, não depois.
- **S-A1 futura** (distribuição entre âncoras não-obrigatórias com pesos
  1/2/3 do antigo) — H-A0 não modela. Migra quando necessário.

## Pendências em aberto pós-H-A0 (não bloqueiam Bloco 4)

1. **PROPORCAO_COMPOSTOS = 0.6** (do antigo) — não foi modelada (decisão
   4.6). Cobertura de compostos emerge da cadeia H-A0 → marker → H-A1.
   Se gate clínico futuro mostrar gap, abre frente S-A1 com peso por
   âncora não-obrigatória.
2. **Carve-outs antigos** (`SUBREGIOES_CARVE_OUT_QUOTAS`,
   `SUBREGIOES_SORTEIO_VAGA_UNICA`) — distribuição/sorteio, não
   obrigatoriedade. Continuam só no motor antigo até frente própria.
3. **Métrica `degradacoes_ha0_media` sempre 0 no antigo** — por design
   (motor antigo não modela H-A0). Útil só pra CSP; render comunica isso
   no relatório.
