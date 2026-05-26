# Handoff — Cobertura per-treino do H-A1 marker pós-H-A0

**Sessão**: próxima após Frente S-A1 fechada (2026-05-25) — primeiro
refinamento priorizado do Bloco 4 do roadmap CSP.

**Branch base**: a partir de `main` (S-A1 já mergeada — commit `76df7cf`).
Branch sugerida: `h-a1-per-treino-marker`. Disciplina de merge do
roadmap se aplica — 1 branch ativa por vez.

---

## 1. Por que esta sessão existe (achado clínico real)

Em 2026-05-25, durante a Frente S-A1, Bernardo perguntou: "treinos com
lower(3) saem sem squat bilateral?" — referindo-se à rotina ativa do
aluno **Filipe Santos** (id=17, rotina `20260525_195735_bb15` no SQLite
de produção).

Inspeção da rotina confirma:

| Treino | Exercícios lower |
|---|---|
| **T1** | Recuo [`squat_unilateral`], Hip Thrust [hinge bi], Elev. Panturrilha Uni |
| T2 | Agachamento Goblet Rampa [`squat_bilateral`], Stiff Uni [hinge uni], Elev. Panturrilha |

**T1 NÃO tem squat_bilateral** (só Recuo = squat_unilateral). T2 tem.

A demanda da rotina é `regiao upper(3) + regiao lower(3) + regiao core(2)` ×
2T (Full Body via UI default).

### Diagnóstico técnico

H-A0 obriga (per-treino) ≥1 slot da subregião `perna_anterior` em cada
treino (ambos T1 e T2). Marker `subregioes_obrigadas_ha0[(t_idx, lower)]`
popula `{perna_anterior, perna_posterior}` para t_idx=0 e t_idx=1.

H-A1 lê o marker e estende `slots_subregiao_explicita[perna_anterior]`
com os sids dos 2 treinos (6 sids — 3 de cada treino). Vagas garantidas:
1 (T1) + 1 (T2) = 2.

`ANCORAS_POR_SUBREGIAO[perna_anterior]` tem 1 obrigatória:
`squat_bilateral` (peso 3).

H-A1 cria 1 constraint hard: `sum(termos squat_bilateral sobre os 6 sids) >= 1`.

**≥1 cross-rotina, NÃO por treino**. Solver cumpre colocando 1
squat_bilateral em T2. T1 fica livre e o solver bota `squat_unilateral`
(Recuo) lá por outros motivos (S-A1, aderência, S-B1 cross-sub).

### Por que isso é um bug

H-A0 é **per-treino** (decisão 4.1 do handoff H-A0): "treino de lower
deve cobrir perna_anterior NAQUELE treino". Espera-se cobertura
clínica por treino, não rotina inteira.

Mas H-A1 marker, ao herdar do H-A0, **converte essa semântica per-treino
em cross-rotina**: garante 1 squat_bilateral na rotina toda. Quebra a
intenção do H-A0.

### Por que S-A1 NÃO resolve

`squat_bilateral` é OBRIGATÓRIA em `ANCORAS_POR_SUBREGIAO[perna_anterior]`.
S-A1 só penaliza NÃO-obrigatórias de peso baixo. Não interfere com
escolha entre obrigatórias.

---

## 2. Leitura preparatória (na ordem)

1. **`docs/refatoracao/norte.md`** — princípios (sempre).
2. **`docs/refatoracao/roadmap_csp.md`** — Bloco 4, item "Cobertura
   per-treino do H-A1 marker pós-H-A0" (recém-adicionado pós-S-A1).
3. **`docs/refatoracao/catalogo_constraints.md`** — seções H-A0 (origem
   do marker) e H-A1 (lógica atual cross-treino).
4. **`docs/refatoracao/logs/micro_h_a0_ancoras_regiao.md`** — log da
   H-A0. Especialmente Achado #2 (conflito de cardinalidade H-A0 × H-A1
   marker) — o mesmo lugar que vai precisar mexer.
5. **`docs/refatoracao/logs/frente_s_a1.md`** — log da S-A1, contexto
   imediato. A análise da rotina do Filipe está no Adendo v3 e no
   próprio relato textual da sessão.
6. **`gerador_csp.py:1003-1100`** — bloco H-A1 atual. Especialmente
   linhas 1020-1029 onde marker estende `slots_subregiao_explicita`
   e `vagas_garantidas_por_sub`.

---

## 3. Objetivo desta sessão

Modelar **cobertura per-treino** quando a constraint H-A1 entra ativa
via marker H-A0. Especificamente:

Pra cada (t_idx, R) com marker H-A0 populado em sub X, e X tendo
âncora obrigatória P: exigir **≥1 slot DAQUELE TREINO com padrão P**
(não ≥1 cross-rotina).

Resultado esperado pra rotina Filipe (regiao upper+lower+core × 2T,
seed dele):
- T1: peito (emp_compostos) + costas (remadas ou puxadas) + ombro
  (ombro_composto) + perna_anterior (squat_bilateral) + perna_posterior
  (hinge) + panturrilha (flexao_plantar) + 2 core
- T2: idem (cada treino fecha o repertório por si próprio)

Demandas subregião explícitas (`("subregiao", X, qtd)`) continuam
cross-treino — comportamento atual mantido. A mudança é APENAS pra
slots adicionados via marker.

---

## 4. Decisões a fechar (perguntar ANTES de codar via AskUserQuestion
ou conversa — ver §10)

### 4.1 Granularidade da constraint per-treino

Quando o marker H-A0 popula `subregioes_obrigadas_ha0[(t_idx, R)] = {X}`,
H-A1 deve criar:

- **(a)** 1 constraint hard "≥1 slot com `padrao == âncora.padrao` DENTRO
  dos slots da demanda região `(t_idx, R)`" — por (t_idx, sub_obrig, padrao_obrig).
- **(b)** Manter constraint cross-rotina existente E adicionar 1 hard
  per-treino — redundante mas mais defensivo. Provavelmente over-engineered.

Recomendação preliminar: **(a)**. Mais limpo, sem redundância. Igual à
forma que H-A0 já faz com `sub_idx`.

### 4.2 Demandas subregião explícita preservam cross-treino?

A constraint cross-rotina existente cobre 2 casos:

- **Caso A** (demanda subregião explícita): `("subregiao", X, qtd)` direta.
  Aqui o cross-treino faz sentido — user pediu X(qtd) cross-rotina; se
  qtd=2 e X está em 2 treinos, ≥1 obrig na rotina inteira é razoável.
- **Caso B** (via marker H-A0): demanda região, sub é obrigada per-treino
  pelo H-A0. **Aqui é o bug**.

Pergunta: preservar comportamento atual no Caso A E aplicar regra
per-treino só no Caso B? Provavelmente sim — mas vale validar.

Recomendação preliminar: **sim**, isolar a mudança ao Caso B.

### 4.3 Como diferenciar Caso A vs Caso B no código

Hoje `slots_subregiao_explicita[sub]` agrega ambos. Precisaria:

- **(a)** Mapas paralelos: `slots_subregiao_explicita_directa` (Caso A)
  e `slots_subregiao_explicita_via_marker[(t_idx, R, sub)]` (Caso B,
  per-treino).
- **(b)** Refator do bloco H-A1 inteiro pra processar Caso A e Caso B
  separadamente.

Recomendação preliminar: **(a)**. Mantém compatibilidade com bloco
existente, adiciona uma nova passada per-treino só pra Caso B.

### 4.4 Vagas garantidas em conflito de cardinalidade

Em `("regiao", "lower", 1)` com 2 obrigatórias (perna_ant + perna_post):
H-A0 hoje cai em conflito de cardinalidade — solver escolhe 1 das 2 via
constraint colaborativa. **Marker NÃO popula** (Achado #2 do log H-A0).

Quando NÃO popula → H-A1 também não ativa per-treino. OK, sem mudança.

Quando popula (caso normal, vagas >= n_ativas), H-A1 ativa per-treino
COMO É HOJE no Caso B. Espelhar comportamento atual mas escopo per-treino.

Recomendação preliminar: marker H-A0 segue o padrão atual; mudança
APENAS no escopo da constraint H-A1 derivada do marker.

---

## 5. Spec técnica (rascunho de implementação)

### 5.1 Nova estrutura paralela em `_construir_modelo`

Em vez de adicionar ao `slots_subregiao_explicita`, criar:

```python
# Mapa per-treino dos slots derivados do marker H-A0.
# `{(t_idx, sub_obrig_via_ha0): [sids_da_demanda_regiao_naquele_treino]}`
slots_via_marker_per_treino: dict[tuple[int, str], list[int]] = defaultdict(list)

for (t_idx, R), subs_obrig in subregioes_obrigadas_ha0.items():
    sids_regiao = slots_demanda_regiao_por_treino[(t_idx, R)]
    for sub_obrig in subs_obrig:
        if sub_obrig in ANCORAS_POR_SUBREGIAO:
            slots_via_marker_per_treino[(t_idx, sub_obrig)] = sids_regiao
```

### 5.2 Bloco H-A1 ganha passada per-treino derivada do marker

Mantém a passada cross-rotina atual (cobre Caso A — demanda subregião
direta). Adiciona nova passada per-treino logo após:

```python
# Per-treino marker H-A0 (decisão 4.x do handoff h_a1_per_treino):
# H-A1 derivado do marker H-A0 atua per-treino, não cross-rotina.
for (t_idx, sub), sids in slots_via_marker_per_treino.items():
    obrigatorias = [
        a for a in ANCORAS_POR_SUBREGIAO[sub] if a.get("obrigatoria")
    ]
    if not obrigatorias:
        continue
    for ancora in obrigatorias:
        pad = ancora["padrao"]
        termos = [
            assign[(sid, cidx)]
            for sid in sids
            for cidx, ex in enumerate(slot_por_sid[sid]["pool_slot"])
            if ex.padrao == pad
        ]
        if not termos:
            # Degraded por pool (espelha H-A1 atual).
            h_a1_aplicadas.append({
                "treino": t_idx,
                "subregiao": sub,
                "padrao_obrigatorio": pad,
                "n_termos": 0,
                "n_slots": len(sids),
                "degraded": True,
                "motivo": "pool sem candidato per-treino (H-A1 via marker H-A0)",
                "escopo": "per_treino",
            })
            continue
        model.Add(sum(termos) >= 1)
        h_a1_aplicadas.append({
            "treino": t_idx,
            "subregiao": sub,
            "padrao_obrigatorio": pad,
            "n_termos": len(termos),
            "n_slots": len(sids),
            "degraded": False,
            "escopo": "per_treino",
        })
```

### 5.3 Cuidados arquiteturais

- **Cross-treino atual NÃO deve dobrar a constraint per-treino**.
  Provavelmente vale REMOVER do `slots_subregiao_explicita` os sids
  vindos de marker H-A0 (pra não criar a constraint cross-rotina
  redundante). Ou marcar de algum jeito que esses sids só contam pra
  per-treino.

- **Conflito de cardinalidade**: a regra atual no H-A1 cross-rotina
  trata `vagas < n_ativas` com constraint colaborativa. Per-treino
  pode ter o mesmo caso (ex: `regiao upper(1)` com 3 subs obrig — 3
  padrões obrig competindo por 1 slot). Espelhar comportamento atual:
  constraint colaborativa "sum(obrig_usadas) >= vagas" + degradação.

- **Conflito H-A0 marker × constraint cardinalidade**: ver Achado #2
  do log H-A0. Marker SÓ popula no caso normal (vagas ≥ n_ativas). Em
  conflito, marker não popula → per-treino também não ativa. Mantém
  invariante.

### 5.4 Avisos `h_a1_aplicadas` ganham campo `escopo`

Entrada atual:
```python
{"subregiao": ..., "padrao_obrigatorio": ..., "n_termos": ...,
 "n_slots": ..., "degraded": ..., "motivo": ...}
```

Nova entrada per-treino:
```python
{"treino": int, "subregiao": ..., "padrao_obrigatorio": ...,
 "n_termos": ..., "n_slots": ..., "degraded": ..., "motivo": ...,
 "escopo": "per_treino"}
```

Cross-rotina existente: ganha `"escopo": "cross_rotina"` opcionalmente
pra distinguir nos logs.

### 5.5 Modal de avisos

Caso de degradação per-treino: `_avisos_modal.html` clause `h_a1_deg`
pode usar `aviso.get("treino")` quando presente. Renderiza "T1: peito —
emp_compostos sem cobertura" em vez do genérico.

---

## 6. Validação esperada (gate de fechamento)

### 6.1 Smoke do achado clínico (regressão protetora)

Reproduzir setup do Filipe (`regiao upper(3) + lower(3) + core(2)` ×
2T, seed aleatória). Em 20 seeds:
- T1 deve ter `squat_bilateral` em ≥80% das rotinas
- T2 idem
- Hoje (pré-fix): T1 sem squat_bilateral em ~50% (cross-rotina não
  garante per-treino)

### 6.2 Pytest

Baseline 349 testes preservados.

Adicionar ~6-10 testes em `tests/test_ha1_per_treino_csp.py`:
- `test_demanda_regiao_lower_3_x_2t_cobre_squat_bilateral_per_treino`
- `test_demanda_regiao_upper_3_x_2t_cobre_emp_compostos_per_treino`
- `test_demanda_subregiao_direta_preserva_cross_rotina`
- `test_conflito_cardinalidade_per_treino_via_marker`
- `test_degraded_per_treino_propaga_para_h_a1_aplicadas`
- `test_h_a1_aplicadas_ganha_campo_escopo`

### 6.3 Harness 16/16 e harness E.0

Sem regressão. Métrica `cobertura_ha0_por_treino` no E.0 deve subir
em demanda região com sub que tem padrão obrigatório (perna_anterior,
peito, ombro), porque a cobertura per-treino vira hard.

### 6.4 Métrica nova no harness E.0 (opcional)

`cobertura_padrao_obrigatorio_per_treino[(t_idx, R, padrao)]` — %
rotinas com aquela âncora obrigatória presente DAQUELE TREINO.

Pode ser adicionada pra evitar regressão futura. Mas opcional —
`cobertura_ha0_por_treino` já cobre a maior parte do sinal.

### 6.5 Smoke E2E manual via browser

Gerar rotina pro Filipe (id=17) novamente via /gerar. Confirmar T1 E T2
têm squat_bilateral.

---

## 7. Arquivos a mexer

- `gerador_csp.py`:
  - `_construir_modelo` (~linha 978-1104): nova estrutura
    `slots_via_marker_per_treino`, nova passada per-treino no H-A1.
  - Cuidado pra NÃO duplicar constraint (sids do marker não devem
    contribuir pra constraint cross-rotina).
- `app_flask.py`:
  - `_distribuir_avisos_rotina_csp`: branch `h_a1_degradado` lê
    `aviso.get("treino")` quando presente.
  - `_resultado_csp_pra_sessao`: idem.
- `tests/test_ha1_per_treino_csp.py`: arquivo novo.
- `tests/test_ha1_ancoras_subregiao_csp.py`: pode precisar adaptar
  testes existentes se quebrarem com a mudança de escopo.
- `templates/_avisos_modal.html`: clause `h_a1_deg` pode mostrar
  "T1 — peito — empurrar_compostos" quando `aviso.treino` presente.
- `docs/refatoracao/catalogo_constraints.md`: atualizar seção H-A1
  pra refletir os 2 escopos (cross-rotina pra demanda direta,
  per-treino pra marker).
- `docs/refatoracao/logs/h_a1_per_treino.md`: log da frente (novo).
- `docs/refatoracao/roadmap_csp.md`: marcar ✅ no Bloco 4.
- `MEMORY.md`: 1 linha "H-A1 per-treino via marker fechada".

---

## 8. Restrições / não-fazer

- **NÃO mexer em H-A0** — H-A0 já está per-treino, comportamento OK.
- **NÃO mexer em S-A1 nem na tabela `ANCORAS_POR_SUBREGIAO`** — frente
  recém-fechada, sem motivo pra revisitar.
- **NÃO mergear em main sem aprovação explícita do Bernardo.**
- **NÃO usar `--no-verify` ou flags que pulem hooks.**
- **Commit seletivo** (`git add <arquivo>`, NUNCA `-A`). Antes de
  commitar: `git status` + `git diff --cached`.
- **NÃO usar AskUserQuestion em tópico exploratório** —
  ver `[[feedback-askquestion-exploratorio]]` na memória. Em decisão
  estrutural ainda em aberto, conversar em texto. Bernardo prefere
  recomendar antes de perguntar.

---

## 9. Pendências NÃO incluídas nesta frente

- ~~peso curado de abduction~~ — já ajustado na S-A1 v3 (peso 2).
- **Cadastros com 3+ pesos esparsos em não-obrig** — caso futuro,
  abre frente se acontecer.
- **Dashboard quantitativo** (passo 5 do fluxo) — Bloco 5.
- **Refinamento métrica cobertura H-A0/H-A1 no harness E.0** — pode
  vir junto se útil, mas escopo separado.

---

## 10. Como abrir a sessão

Primeira mensagem da sessão deve:

1. Confirmar que leu norte.md + roadmap_csp.md + catálogo (H-A0 + H-A1)
   + log H-A0 + log S-A1 (Adendo v3 onde achado do Filipe está descrito).
2. Reproduzir o bug: rodar smoke `regiao upper(3) + lower(3) + core(2)` ×
   2T em 10 seeds e medir % rotinas com `squat_bilateral` em T1 E T2.
   Persistir baseline em `logs/h_a1_per_treino_baseline_pre.json`.
3. Confirmar entendimento das 4 decisões pendentes (Seção 4) e do
   trade-off escopo per-treino vs cross-rotina.
4. **Recomendar caminho concreto** (Seção 4 com recomendações) e
   perguntar UMA pergunta de validação ao Bernardo (texto livre, não
   AskUserQuestion) — algo como "vou seguir com (a) per-treino-puro
   isolando do cross-rotina; ok?".
5. Após confirmação, codar.

Não começar a codar antes da confirmação textual. Não começar a codar
antes de rodar o baseline pré.
