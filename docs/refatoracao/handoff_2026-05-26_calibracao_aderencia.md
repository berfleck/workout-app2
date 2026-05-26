# Handoff — Calibração `_PESO_ADERENCIA_POR_PERFIL` (Achado 4 da auditoria 2026-05-26)

**Sessão**: próxima após fechamento da frente "cobertura per-treino do
H-A1 marker" (reavaliada como não-frente em 2026-05-26 —
`logs/h_a1_per_treino_reavaliacao.md`).

**Branch base**: a partir de `main` (frente anterior mergeada FF).
Branch sugerida: `calibracao-aderencia`. Disciplina de merge do
roadmap se aplica — 1 branch ativa por vez.

**Bloco**: 4 do roadmap CSP — primeiro item 🔴 prioritário da
auditoria clínica 2026-05-26.

---

## 1. Por que esta sessão existe (achado clínico real)

Auditoria 2026-05-26 (`auditorias/2026-05-26.md` Achado 4): default
atual de `_PESO_ADERENCIA_POR_PERFIL` em `app_flask.py:486`:

```python
_PESO_ADERENCIA_POR_PERFIL = {
    "alta": 2,
    "media": 0,
    "baixa": 0,
}
```

Sintoma observado em Full Body 2T (Aluno Teste, demanda região):

| Aderência | % slots tier Principal (16 slots) |
|---|---|
| `media` (default UI) | **0/16 = 0%** |
| `alta` | 11/16 ≈ 69% |

Dois problemas estruturais:

1. **`media == baixa == 0`** — perfis distintos tratados iguais. Não há
   como modelar "aluno com baixa aderência" diferente de "médio".
2. **`media == 0` significa "ignora tier completamente"** — sorteio
   uniforme do pool entre tiers. Vai contra prática clínica padrão de
   prescrever Principal por default.

Comentário no próprio código admite: *"Chute inicial conservador.
Iterar pra cima se calibração indicar."* Calibração nunca foi feita
formalmente. Frente D (2026-05-24) foi tunada em **um** smoke
(hinge(1)) sem matriz mais ampla.

**Bloqueia uso real**: personal trainer não vai trocar aderência a
cada aluno só para conseguir Principal nos slots. Default errado vira
viés sistemático em todas as rotinas geradas pela UI.

---

## 2. Leitura preparatória (na ordem)

1. **`docs/refatoracao/norte.md`** — princípios (sempre).
2. **`docs/refatoracao/roadmap_csp.md`** — Bloco 4, item "🔴 ⬜
   Calibração `_PESO_ADERENCIA_POR_PERFIL`" (já listado).
3. **`docs/refatoracao/auditorias/2026-05-26.md`** seção **Achado 4** —
   sintoma completo + comparativo media/alta + diagnóstico estrutural +
   caminho proposto.
4. **`docs/refatoracao/logs/mvp_fatia_3_frente_d.md`** — log da Frente
   D (aderência ao tier). Histórico das decisões de design: peso por
   slot, fórmula `(rank_max - tier_rank[s]) * peso_aderencia`, smoke
   hinge(1).
5. **`app_flask.py:480-500`** — função `_peso_aderencia_csp` +
   constante `_PESO_ADERENCIA_POR_PERFIL`.
6. **`gerador_csp.py:1484-1496`** — bloco "Aderência ao Tier" no
   `_construir_modelo`. Bloco inteiro skipado quando `peso_aderencia==0`.

---

## 3. Objetivo desta sessão

Substituir o chute inicial de `_PESO_ADERENCIA_POR_PERFIL` por
**calibração curada baseada em sondagem N=10-20 rotinas por valor**.

Resultado esperado:

- `media` (default UI): % Principal substancialmente acima de 0%,
  preservando variedade dentro do tier. Sugestão auditoria: 1-2.
- `alta`: % Principal alto (>= 70%, próximo do atual com peso=2),
  pouca variedade entre tiers. Pode ficar 3-4.
- `baixa`: distinguível de `media`. Favorece Intermediário/Acessório.
  Sugestão auditoria: 0 ou negativo.

**NÃO é** ajuste em massa do motor — é calibração de **3 valores int**
no dicionário Python. Trabalho cabe em 1 sessão.

---

## 4. Decisões a fechar (perguntar via texto livre — ver §10)

### 4.1 Pesos finais

A auditoria sugere `{alta: 3-4, media: 1-2, baixa: 0 ou negativo}`.
A sessão deve estreitar com base em sondagem empírica:

- **`alta`**: 3 vs 4? Diferença marginal pra calibração N=20.
  Recomendação preliminar: começar com 3 e medir.
- **`media`**: 1 vs 2? Limiar do "Principal preferido sem matar
  variedade". Recomendação preliminar: 1.
- **`baixa`**: 0 vs negativo? Negativo INVERTE a fórmula (penaliza
  Principal, premia Acessório). Pode ter side effects. Recomendação
  preliminar: **0 e diferenciar de `media` via outro mecanismo
  futuro** (a discutir na sessão).

### 4.2 Aceitar peso negativo em `baixa`?

Hoje o bloco em `gerador_csp.py:1489` skipa quando `peso_aderencia==0`.
Negativos não foram testados — fórmula
`(rank_max - tier_rank[s]) * peso_aderencia` com peso negativo
inverteria sinal (Principal vira -peso × 0 = 0; Acessório vira
peso negativo × 2 = penalty negativo = bonus). **Solver minimiza
score**, então bonus em Acessório premia escolher Acessório.

Pergunta de design: peso negativo é semanticamente "preferir tiers
baixos" ou "tratar como neutro forte"? Decisão dispara sessão de
implementação extra (validar fórmula, ajustar IntVar bounds em
`gerador_csp.py:1491-1492`, teste). Recomendação preliminar: **0 como
default**, abrir frente separada se baixa-com-peso-negativo virar
prioridade.

### 4.3 Cobertura da matriz `nivel × aderencia` no harness E.0

Hoje `tools/harness_comparativo_e0.py` tem flag `--matriz` (2x2 nivel
× aderência). Vale rodar a matriz pós-calibração pra registrar a nova
distribuição de Principal por perfil. Sem refator do harness — só
rerun com nova calibração. Recomendação preliminar: **sim, rerun**.

### 4.4 Granularidade da sondagem

Sugestão da auditoria: 10-20 rotinas por valor. Pra calibrar 3 valores
× ~2 candidatos cada × 10-20 rotinas = ~60-120 runs. Cabe em ~5-10min
de sondagem (Full Body 2T ~0.5s/rotina). Recomendação preliminar:
**N=20 por (valor, perfil)** + **1 config canônica (Full Body 2T
região, mesma da auditoria)**.

---

## 5. Spec técnica (rascunho de implementação)

### 5.1 Sondagem pré (item 0)

Novo `tools/sondar_aderencia_calibracao.py` (espelha o pattern do
`sondar_sa1_baseline.py`):

```python
# Setup: Aluno Teste (nivel=intermediario), demanda
# regiao upper(3) + lower(3) + core(2) x 2T (= auditoria 2026-05-26).
# Pra cada peso candidato {0, 1, 2, 3, 4}, roda N=20 seeds e mede:
#   - % slots tier Principal
#   - % slots tier Intermediario
#   - % slots tier Acessorio
#   - Variedade entre rotinas (nomes distintos por sub na rotina inteira)
```

Persiste em `logs/aderencia_calibracao_pre.json`.

### 5.2 Decisão dos valores finais

Após análise da sondagem, Bernardo escolhe `{alta, media, baixa}`
finais. Exemplo de saída esperada (varia com a sondagem real):

```
peso=0: Principal 25-35% (sorteio puro por banco)
peso=1: Principal 50-60% (Principal preferido, variedade preservada)
peso=2: Principal 65-75% (atual default da `alta`)
peso=3: Principal 80-90%
peso=4: Principal 90%+ (quase determinístico)
```

Daí mapeamento curado:

```python
_PESO_ADERENCIA_POR_PERFIL = {
    "alta": <X>,
    "media": <Y>,
    "baixa": <Z>,
}
```

### 5.3 Fix

Edit em `app_flask.py:486`. **3 valores int** — não mexe na função
`_peso_aderencia_csp`, não mexe no `gerador_csp.py`, não mexe na
fórmula em si.

### 5.4 Sondagem pós

Re-rodar o mesmo script da §5.1 com `_PESO_ADERENCIA_POR_PERFIL` novo,
persistir `logs/aderencia_calibracao_pos.json`. Compara lado-a-lado.

### 5.5 Comentário atualizado em `app_flask.py:481-485`

Substituir o comentário "Chute inicial conservador..." por algo curto
referenciando a calibração:

```python
# Calibração curada 2026-05-26 (auditoria Achado 4):
# - alta=<X>: Principal preferido forte, variedade reduzida entre tiers
# - media=<Y>: Principal preferido moderado, variedade preservada
# - baixa=<Z>: tier neutro (ou negativo se sessão expandiu escopo)
# Ver logs/aderencia_calibracao_*.json + auditoria 2026-05-26.
_PESO_ADERENCIA_POR_PERFIL = {...}
```

---

## 6. Validação esperada (gate de fechamento)

### 6.1 Sondagem comparativa pré × pós

Tabela markdown com (peso, % Principal, % Intermediário, % Acessório,
% rotinas com nome único por sub) lado-a-lado.

### 6.2 Pytest

Baseline 348 testes preservados (frente anterior era zero-código,
testes intocados).

Provavelmente **zero testes novos**. Calibração não introduz lógica
nova — só muda 3 ints. Se algum teste estatístico do harness E.0
ficar tight com nova calibração, ajustar tolerância (espelha o
tratamento da H-A1 que reduziu sensibilidade do alpha_tier).

### 6.3 Harness 16/16

Sem regressão funcional. Se algum cenário ficou statísticamente
diferente (esperado com peso != 0), revisar caso a caso.

### 6.4 Harness E.0

Rerodar `tools/harness_comparativo_e0.py` com `--matriz`. Atualizar
relatório se já existir do dia, ou criar `E0_2026-05-26_pos_calibracao.md`.

### 6.5 Smoke E2E manual via browser

Gerar 2-3 rotinas com aluno Aderência `media` (default UI). Confirmar
que tier Principal aparece em quantidade clinicamente razoável (era 0%
pré-fix; alvo qualitativo: maioria dos slots de padrões compostos
caindo em Principal/Intermediário, não Acessório).

---

## 7. Arquivos a mexer

- `app_flask.py` linha 486 — 3 valores int + comentário atualizado.
- `tools/sondar_aderencia_calibracao.py` — novo, ~80 linhas espelhando
  pattern do `sondar_sa1_baseline.py`.
- `docs/refatoracao/logs/aderencia_calibracao_pre.json` — novo, snapshot.
- `docs/refatoracao/logs/aderencia_calibracao_pos.json` — novo, snapshot.
- `docs/refatoracao/logs/calibracao_aderencia.md` — log da frente (novo).
- `docs/refatoracao/relatorios/E0_2026-05-26_pos_calibracao.md` —
  opcional, se rerodar harness E.0 com `--matriz`.
- `docs/refatoracao/roadmap_csp.md` — marcar ✅ no item Achado 4 do
  Bloco 4 + 1 linha em "Frentes concluídas".
- `docs/refatoracao/auditorias/2026-05-26.md` Achado 4 — atualizar
  status pra ✅ (linkando log da frente).
- `MEMORY.md` — 1 linha registrando calibração.

**NÃO mexer**:
- `gerador_csp.py` (a menos que 4.2 expanda escopo pra peso negativo).
- Frente D (já mergeada; calibração é tuning, não refator).

---

## 8. Restrições / não-fazer

- **NÃO refator** da fórmula
  `aderencia_pen[s] = (rank_max - tier_rank[s]) * peso_aderencia`. Só
  calibração dos pesos.
- **NÃO introduzir dimensões novas** do vetor de perfil (Centralidade
  Compostos, Densidade Pareamento, etc) — frentes separadas.
- **NÃO mergear em main sem aprovação explícita do Bernardo.**
- **NÃO usar `--no-verify` ou flags que pulem hooks.**
- **Commit seletivo** (`git add <arquivo>`, NUNCA `-A`). Antes de
  commitar: `git status` + `git diff --cached`.
- **NÃO usar AskUserQuestion em tópico exploratório** —
  ver `[[feedback-askquestion-exploratorio]]`. Em decisão de calibração
  (valor concreto X vs Y), texto livre com dados da sondagem é melhor.

---

## 9. Pendências NÃO incluídas nesta frente

- **🔴 S-B5 — diversidade região INTRA-bloco** (auditoria Achado 3) —
  próxima frente prioritária após calibração. Restaura feature P1-P4
  do greedy antigo perdida na migração CSP. Constraint nova, ~2 sessões.
- **🟡 S-R1 cross-treino + panturrilha** (auditoria Achado 1) — soft
  cross-treino dentro de demanda região; decisão clínica sobre
  panturrilha `obrigatoria=False`. ~1-2 sessões.
- **🟡 S-E1 diversidade equipamento cross-treino** (auditoria Achado
  2) — depende de S-B5 e S-R1 entrarem (interação de pesos). ~1-2
  sessões.
- **Dashboard quantitativo** (Bloco 5) — instrumento formal de
  calibração com N=1000+ rotinas. Calibração desta frente é "de
  partida"; dashboard é refino futuro.

---

## 10. Como abrir a sessão

Primeira mensagem da sessão deve:

1. Confirmar que leu norte.md + roadmap_csp.md + auditoria
   2026-05-26 (Achado 4) + log Frente D + `app_flask.py:480-500` +
   `gerador_csp.py:1484-1496`.
2. Rodar sondagem pré (§5.1) com pesos candidatos `{0, 1, 2, 3, 4}` e
   N=20 cada. Persistir `logs/aderencia_calibracao_pre.json`. Mostrar
   tabela ao Bernardo.
3. Confirmar entendimento das 4 decisões pendentes (§4) e do
   trade-off "Principal preferido vs variedade entre tiers".
4. **Recomendar valores concretos** (não AskUserQuestion — texto
   livre) baseado na sondagem. Algo como: "sondagem mostra peso=1 dá
   55% Principal sem matar variedade; peso=3 dá 85% mas concentra; vou
   com `{alta: 3, media: 1, baixa: 0}`; ok?".
5. Após confirmação, fix em `app_flask.py:486` + sondagem pós + log +
   roadmap + commit + push + merge FF.

Não codar antes da confirmação textual dos valores. Não codar antes de
rodar a sondagem pré.

**Tempo estimado**: 1 sessão (~30-60min). Sondagem ~5-10min cada,
decisão ~10min, fix ~5min, validação ~15min.
