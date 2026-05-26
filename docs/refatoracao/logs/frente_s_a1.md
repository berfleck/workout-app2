# Log — Frente S-A1 (distribuição entre âncoras não-obrigatórias no CSP)

**Data**: 2026-05-25
**Branch**: `frente-s-a1` (a partir de `main` pós-H-A0)
**Bloco**: 4 do roadmap CSP — segunda frente prioritária pós-H-A0

**Arquivos atualizados**:
- `gerador_csp.py` — argumentos `peso_sa1` e `peso_sa1_repet` em
  `_construir_modelo` + bloco S-A1 (componente v1 + v2) entre H-A1 e S-T1
  + propagação pelas 4 saídas (`_resolver_legacy`, `_resolver_com_variedade`,
  `gerar_rotina_csp`, `gerar_treino_csp`) + `teto_por_termo` inclui termos S-A1
- `app_flask.py` — constantes novas `_PESO_SA1_DEFAULT=12` e
  `_PESO_SA1_REPET_DEFAULT=10` + propagação em `/gerar` e `treino_regerar`
- `tests/test_sa1_ancoras_nao_obrigatorias_csp.py` — 14 testes novos
- `tools/sondar_sa1_baseline.py` — script de sondagem 40 seeds × 4 subregiões
  (4 snapshots persistidos em `logs/sa1_*.json`)
- `tools/sondar_sa1_regiao_smoke.py` — smoke em demanda região lower(4)
- `tools/harness_comparativo_e0.py` — métrica `distribuicao_subregiao_2` +
  render markdown + constantes `_PESO_SA1_HARNESS` espelhando produção
- `docs/refatoracao/catalogo_constraints.md` — seção S-A1 nova na Seção 2
  (Soft constraints — escopo SUBREGIÃO)
- `docs/refatoracao/roadmap_csp.md` — S-A1 marcada ✅ no Bloco 4

**Status**: ✅ concluída — todos os critérios de gate atendidos.
Aguardando aprovação do Bernardo pra merge em `main` (disciplina de merge
do roadmap exige confirmação explícita).

---

## Objetivo

Fechar regressão real CSP × antigo descoberta pós-H-A0 (handoff
`handoff_2026-05-25_s_a1.md`):

| Demanda | Motor antigo | CSP pré-S-A1 |
|---|---|---|
| `ombro(2)` | 100% (composto + isolado) ✓ | 100% (composto + posterior_ombro) ✗ |
| `perna_posterior(2)` | 48% (hinge+knee_flexion) / 52% (hinge+abduction) ✓ | 100% (hinge + abduction) ✗ |
| `peito(2)` | 100% (composto + isolado) ✓ | 55% (composto+isolado) / 45% (composto+composto) |
| `perna_anterior(2)` | 100% (bilateral + unilateral) ✓ | 100% (bilateral + unilateral) ✓ |

Causa raiz: H-A0/H-A1 ignoram os pesos curados 3/2/1 de
`ANCORAS_POR_SUBREGIAO`. S-B1 (peso 10) domina a decisão entre padrões
não-obrigatórios.

## Decisões fechadas (handoff 2026-05-25 + AskUserQuestion inicial)

### Do handoff (Seção 4)

1. **§4.1 vagas > n_obrig em demanda subregião** — condicionar S-A1 v1
   pra isolar trade-off com S-B1.
2. **§4.2 S-B1 fora do escopo** — não mexer no S-B1 mesmo se calibração
   apertar.
3. **§4.3 Validar empiricamente** — sondagem pré/pós (item 0 / decisão 4.4).
4. **§4.4 Snapshot baseline** — persistido em
   `docs/refatoracao/logs/sa1_baseline_pre.json`.
5. **§4.5 NÃO mexer em `ANCORAS_POR_SUBREGIAO`** — pesos são curados
   clinicamente.
6. **§4.6 Reuso padrão arquitetural** — `peso_sa1: int = 0` default
   preserva motor pré-S-A1.
7. **§4.7 Sondagem 40 seeds vira padrão** — metodologia validada em
   H-A0.

### Da AskUserQuestion inicial (Seção 5)

8. **§5.1 Forma linear** — `(peso_max - peso_ancora) * peso_sa1`.
   Quadrática descartada (resultado clínico idêntico na config atual).
9. **§5.2 Ativa em demanda região via marker H-A0** — Bernardo escolheu
   "mais pronto"; empírico depois mostrou trade-off (ver Achado #2).
10. **§5.3 peso_sa1 = 8 inicial** — calibração coordinate descent achou
    12 como mínimo robusto (ver Achado #1).
11. **§5.4 Métrica E.0 agora** — `distribuicao_subregiao_2` incluída
    com render markdown.

### Decisões em sessão (não previstas no handoff)

12. **Extensão S-A1 v2 (padrão repetido)** — empírico mostrou v1 sozinho
    introduzia regressão crítica em `perna_posterior(2)`: 78% saíam
    `hinge+hinge` (sobrecarga lombar potencial). Bernardo aprovou
    "corrigir agora ou depois — como achar melhor"; recomendei estender
    nesta sessão (norte Seção 1: "qualidade absoluta como prioridade").
13. **peso_sa1_repet = 10** — calibração final 2026-05-25 zera hinge+hinge
    e composto+composto sem perturbar comportamento de outras subs.

## O que foi implementado

### Bloco S-A1 em `_construir_modelo` (após H-A1, antes de S-T1)

**Componente v1** — penalty linear sobre âncoras não-obrigatórias:

```python
if peso_sa1 > 0:
    # Caso 1: demanda subregião explícita (condicionar qtd > n_obrig)
    # Caso 2: demanda região via marker H-A0 (ativa sempre, via assign)
    for sid, cidx, ex in ...:
        if ex.padrao in nao_obrigatorias[sub]:
            custo = (peso_max - peso[ex.padrao]) * peso_sa1
            penalty = NewIntVar(0, custo) == custo * assign[(sid, cidx)]
            penalidades.append(penalty)
```

**Componente v2** — penalty por padrão repetido na mesma demanda:

```python
if peso_sa1_repet > 0:
    for grupos_t in treinos:
        for g in grupos_t:
            for (s1, s2) in pares_da_demanda:
                # eq_P[s1,s2] = "ambos slots escolheram P" (reificada)
                # same_padrao = OR(eq_P para todo P)
                penalty = peso_sa1_repet * same_padrao
                penalidades.append(penalty)
```

A construção de `same_padrao` usa BoolVars `eq_P` reificadas com
`AddBoolOr(eq_vars).OnlyEnforceIf(same_padrao)` + implications inversas.

### Wire em `app_flask.py`

`_PESO_SA1_DEFAULT = 12` e `_PESO_SA1_REPET_DEFAULT = 10` propagados em
`/gerar` (via `gerar_rotina_csp`) e `treino_regerar` (via `gerar_treino_csp`).

### Métrica E.0

Função `metrica_distribuicao_subregiao_2(rotinas, config)` retorna
`{(treino_idx, sub): Counter({combo: n_rotinas})}`. Aplicável quando
config tem demandas `("subregiao", X, 2)`. Render markdown lado-a-lado
CSP × antigo. `_PESO_SA1_HARNESS=12` + `_PESO_SA1_REPET_HARNESS=10` no
`rodar_csp` espelham produção.

## Calibração (coordinate descent 2026-05-25)

### Componente v1 sozinho (peso_sa1_repet=0)

| peso_sa1 | ombro(2) iso% | perna_post(2) knee% | peito(2) iso% | perna_post(2) hinge+hinge% |
|---|---|---|---|---|
| 0 (baseline CSP) | 0% | 0% | 55% | 0% |
| 8 | 0% (NO-OP) | 0% (NO-OP) | 52% | 0% |
| 11 | 78% | 28% | 50% | 72% ⚠️ |
| 12 | 80% | 22% | 62% | 78% ⚠️ |
| 15 | 72% | 18% | 50% | 82% ⚠️ |

**Achado**: peso < 11 = NO-OP (S-B1=10 domina). Peso ≥ 11 resolve ombro
parcialmente MAS introduz regressão crítica em perna_posterior
(hinge+hinge sobe de 0% pra 72-82%). Em demanda região `lower(4)`,
regressão escala pra 55% das rotinas.

**Causa arquitetural**: S-A1 v1 não consegue distinguir A=(obr+não-obr)
de C=(obr+obr). Ambos custam S-B1=10 + S-A1=0. Solver decide ~ aleatório.

### Componente v1 + v2 (peso_sa1=12, peso_sa1_repet=10)

| Demanda | Resultado |
|---|---|
| `ombro(2)` | 100% composto+isolado ✓ (era 0% iso) |
| `perna_posterior(2)` | 100% hinge+knee_flexion ✓ (hinge+hinge zerou) |
| `peito(2)` | 100% composto+isolado ✓ (era 55%) |
| `perna_anterior(2)` | 100% bilateral+unilateral ✓ (preservado) |
| `regiao lower(4)` hinge+hinge | 0% ✓ (era 35% pre-S-A1, 70% com v1 sozinho) |

## Achados

### 1. peso < 11 = NO-OP em S-A1 v1 (canibalização com S-B1)

Lição direta da Etapa 7 Fase 7.6 (4 dimensões NO-OP por canibalização
de pesos). Calibração precisa de **peso > S-B1 (=10)** pra v1 dominar
a decisão entre padrões não-obrig em ombro_iso vs posterior_ombro.
Margem +1 escolhida (peso=12) pra robustez.

### 2. Decisão §5.2 (b) refutada empiricamente em demanda região

Bernardo aprovou §5.2 (b) "S-A1 ativa em demanda região via marker H-A0"
no AskUserQuestion inicial. Empírico smoke `regiao lower(4)` n=20
mostrou:

| Configuração | hinge+hinge | abduction | knee |
|---|---|---|---|
| Pré-S-A1 | 35% | 50% | 5% |
| v1 sozinho (peso=12) | **70%** ⚠️ | 0% | 5% |
| v1 + v2 (12, 10) | 0% ✓ | 0% | 80% |

v1 sozinho **amplifica** o problema "padrão repetido" em demanda região
(de 35% pra 70%). v2 fecha o gap.

**Trade-off documentado**: abduction (peso 1) zerou em demanda região.
É comportamento correto pelo norte Seção 4 — peso 1 ≪ peso 2 reflete
decisão clínica curada. Se Bernardo quiser mais abduction, ajustar peso
em `ANCORAS_POR_SUBREGIAO`, não em S-A1.

### 3. peito 45% 2 compostos era achado bonus do baseline

Sondagem pré-S-A1 (peso_sa1=0) já mostrava CSP entregando
`empurrar_compostos+empurrar_compostos` em 45% das rotinas `peito(2)` —
não previsto no handoff. v2 com peso=10 fecha esse achado também.

### 4. Bug do Filipe Santos — frente futura

Rotina ativa do aluno Filipe Santos (id=17, rotina
`20260525_195735_bb15`) saiu com T1 sem `squat_bilateral` (apenas Recuo
= `squat_unilateral`); T2 tem (Agachamento Goblet Rampa). H-A1 marker é
cross-treino — garante ≥1 squat_bilateral na rotina inteira, não por
treino. **S-A1 NÃO resolve esse caso** (squat_bilateral é a obrigatória;
não está em `nao_obrigatorias`).

Pendência registrada como **frente futura**: cobertura per-treino do
H-A1 marker pós-H-A0. Espelha como H-A0 modelou per-treino (decisão
4.1 do handoff H-A0).

### 5. Empate A vs C (obrig+obrig) é buraco arquitetural genérico

S-A1 v1 sozinho não distingue:
- A = obrigatória + não-obrig (clinicamente preferido)
- C = obrigatória + obrigatória (mesmo padrão repetido)

Ambos custam S-B1=10 + S-A1=0. Solver decide ~ por exploração da árvore.
Em ombro saiu 80/20 (A vence por sorte); em perna_posterior saiu 22/78
(C vence por azar). Esse buraco é fechado por v2, que é **frente
prevista pelo catálogo** (S-R3 — variedade INTRA na rotina) mas
implementada aqui como complemento direto do S-A1.

## Resultado da validação (gate de fechamento)

| Critério | Resultado |
|---|---|
| Snapshot baseline pré-S-A1 (item 0) | ✅ `docs/refatoracao/logs/sa1_baseline_pre.json` |
| Pytest S-A1 novos (14 testes) | ✅ 14/14 passed em 5s |
| Pytest baseline (334 + 14 = 348) | ✅ 348 passed, 1 skipped |
| Harness antigo 16/16 | ✅ preservado, NO-OPs informativos inalterados |
| Smoke achado clínico (40 seeds × 4 subs) | ✅ 100% combos clinicamente corretos |
| Smoke demanda região (lower(4) n=20) | ✅ hinge+hinge 0% |
| Métrica E.0 nova (`distribuicao_subregiao_2`) | ✅ render markdown OK em N=5 |
| Wire em `/gerar` + `treino_regerar` | ✅ propaga `_PESO_SA1_DEFAULT` e `_PESO_SA1_REPET_DEFAULT` |

## Próximos passos

- **Mergear em main** após aprovação do Bernardo (disciplina de merge).
- **Bloco 4 continua**: próximo achado registrado é a cobertura
  per-treino do H-A1 marker pós-H-A0 (bug Filipe). Frente futura, fora
  de S-A1.
- **Refinamentos pós-S-A1 abertos**:
  - Variedade entre padrões em demanda região com vagas extras grandes
    (`upper(6)` → vagas livres podem repetir composto). Se gate clínico
    futuro detectar, abre frente.
  - Calibração de peso_sa1 / peso_sa1_repet em modo Dashboard quantitativo
    (passo 5 do fluxo, ainda não rodando). Hoje a calibração é manual.

## Pendências em aberto pós-S-A1 (não bloqueiam Bloco 4)

1. **Bug Filipe — cobertura per-treino do H-A1 marker**: aguarda frente
   nova com decisões. Espelhar H-A0 (per-treino) no H-A1 quando ativa
   via marker.
2. **abduction (peso 1) zerou em demanda região** — design correto pelo
   norte mas Bernardo pode querer revisitar peso curado.
3. **Cadastros de não-obrigatórias com 3+ pesos esparsos** — caso futuro.
   Hoje todas as subs com não-obrig têm gap=1 entre pesos (linear ==
   quadrática). Se algum cadastro futuro introduzir 3+ pesos esparsos,
   revisitar §5.1.
