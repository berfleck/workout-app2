# Handoff — S-E1 proximidade biomecânica cross-treino (Achado 2 da auditoria 2026-05-26)

**Sessão**: próxima após encerramento da frente Filtro de Acessórias
CSP (mergeada em main 2026-05-27, commit `10d3c63`).

**Branch base**: a partir de `main`. Branch sugerida:
`frente-s-e1-proximidade-biomecanica`. Disciplina de merge se aplica
(1 branch ativa por vez, aguardar aprovação Bernardo pra merge FF).

**Bloco**: 4 do roadmap CSP — Achado 2 da auditoria 2026-05-26.
Achado 1 totalmente fechado (S-R1 simetria T1↔T2 + filtro acessórias
panturrilha). Achado 3 fechado (S-B5 diversidade região INTRA-bloco).
Achado 4 ainda aberto.

---

## 1. Por que esta sessão existe

### O bug (Achado 2)

Em rotina Full Body 2T com `aderencia=alta`, padrões single-slot por
treino caem em equipamento idêntico cross-treino:

- **Peito**: T1 Supino Inclinado Halteres + T2 Supino Com Halteres
  (2 supinos halteres, ambos Principal).
- **Ombro**: T1 Desenv. Halteres Uni. + T2 Desenv. Halteres Sentado
  (2 desenvolvimentos halteres).

Em ambos casos havia opções não-halteres no banco (Supino Com Barra,
Supino Smith Inclinado, Desenv. Landmine, Desenv. Smith). Variedade
de equipamento perdida.

**Importante (refinamento Bernardo 2026-05-27)**: a frente foi
**renomeada** de "equipamento cross-treino" para **"proximidade
biomecânica cross-treino"**. O caso clínico nuclear é:

> "halteres vs barra IMPORTA em supino, NÃO IMPORTA em passada"

Equipamento sozinho não captura isso — é a soma de **pegada +
plano_corporal + equipamento_grupo** que diferencia movimentos
clinicamente próximos. Escopo "mesma subregião" do antigo resolve
naturalmente o caso (em peito, halteres vs barra muda o vetor; em
perna_anterior unilateral, halteres vs barra é equivalente).

### Causa estrutural

- Dimensões `pegada` / `plano_corporal` / `equipamento_grupo` foram
  **cadastradas no XLSX na Fase 4** do refator antigo (2026-05-15) e
  **sobreviveram no refator declarativo** (CLAUDE.md `dimensoes_proximidade.md`
  é referência viva).
- Pesos calibrados na Etapa 6 do antigo (Seções 8.9-8.11) **NÃO
  foram migrados** para o CSP. `_score_proximidade` do antigo nunca
  foi consumido pelo motor declarativo.
- O CSP novo só tem soft INTRA via S-B1 (agonistas Fatia 4.B) +
  S-B5 (região same-bloco). Não há nenhum soft cross-treino pra
  proximidade biomecânica.

---

## 2. Leitura preparatória (na ordem)

1. **`docs/refatoracao/norte.md`** — princípios. Especialmente
   Seções 3-5 (motivação refator, anti-padrões, trade-offs).
2. **`docs/refatoracao/roadmap_csp.md`** — estado pós-S-R1 +
   filtro-acessorias.
3. **`docs/refatoracao/auditorias/2026-05-26.md`** — Achado 2
   completo (§143-188). Sintoma + causa + caminho proposto +
   interações com roadmap.
4. **`docs/refatoracao/catalogo_constraints.md`** — escopo
   ROTINA + INTRA. Especialmente S-T4 (Conceito 5, INTRA) e S-R1
   (Conceito 9, ROTINA) — ambos usam as mesmas dimensões que
   S-E1 vai usar. Conferir que S-E1 não duplica conceito.
5. **`docs/refatoracao/arquivo/era_v4_greedy_incremental/dimensoes_proximidade.md`**
   — **REFERÊNCIA VIVA** (exceção registrada no CLAUDE.md).
   Especificação clínica das 3 dimensões + pesos calibrados +
   escopo "mesma subregião". **Ler especificamente**:
   - Seções 1-2 (set final de dimensões — 5 core + 1 narrow).
   - Seção 8.9/D3.1 (multiplicadores INTER: default 0.8 × INTRA;
     overrides familia_estrita 0.80, variante_pontual 0.95).
   - Seção 8.10/B (estrutura de configuração).
   - Seção 8.11/A (escala numérica unificada -100/-50/-20/-5).
6. **`docs/refatoracao/logs/mvp_sr1_cross_treino.md`** — log da
   S-R1 (precedente direto: soft cross-treino com BoolVar por par
   treino+escopo, default ON sem toggle UI).
7. **`docs/refatoracao/logs/mvp_filtro_acessorias_csp.md`** — log
   da frente anterior (último estado do motor antes desta sessão).
8. **`gerador_csp.py`** — bloco do objetivo. Especialmente como
   S-R1 e S-B5 montam suas penalties (precedente arquitetural).
9. **`pesos_proximidade.py`** (raiz) — dataclass de pesos do
   gerador antigo. Reaproveitar estrutura ou trazer pra dentro do
   CSP.

---

## 3. Decisões prováveis a fechar com Bernardo (pré-código)

Estas decisões definem o escopo e a forma da constraint. **Texto
livre** com sugestões/contrapontos pra cada uma (tópico clínico
aberto; ver [[feedback-askquestion-exploratorio]]).

### 3.1 Granularidade — par cross-treino × subregião ou × padrão?

S-R1 fechou granularidade **par × região** (split T1==T2 em
TODAS subs da R). Precedente sugere subregião como próximo nível.

Mas o caso clínico do Achado 2 é **padrão single-slot** — Supino
+ Supino, Desenv. + Desenv. Granularidade padrão captura
diretamente. Granularidade subregião captura também (peito 1+1 =
padrão único cross-treino na maioria dos casos).

**Sugestão**: granularidade `(t1, t2) × subregião`, igual S-R1.
Em casos onde subregião tem múltiplos padrões single-slot
cross-treino (ex: peito Supino + Crucifixo em T1; Apoio + Voador
em T2), o score INTER vai ser somatório das dimensões — naturalmente
penaliza pares próximos.

### 3.2 Quais dimensões consumir

O antigo usa 5 core + 1 narrow (Seção 1 de `dimensoes_proximidade.md`):

- `familia_estrita` — hard INTRA / soft INTER (já implementado no
  CSP via H-T2/H-T1 + Frente E.1). **Excluir desta frente** (cobertura
  duplicada).
- `lateralidade` — hard INTRA contextual costas (já em H-T3). Soft
  INTER. **Excluir** (cobertura duplicada).
- `pegada` (matriz 4×4) — peso ALTO.
- `plano_corporal` — peso ALTO.
- `equipamento_grupo` (8 níveis) — peso BAIXO/tiebreaker.
- `variante_pontual` — narrow-scope. **Excluir** (cross-family
  hard INTRA via H-T2).

**Sugestão**: S-E1 consome `pegada` + `plano_corporal` +
`equipamento_grupo` cross-treino. Reaproveitar a matriz 4×4 da
pegada (não constante). Mantém escopo "mesma subregião" do antigo.

### 3.3 Pesos — reaproveitar calibração ou recalibrar?

A calibração do antigo (Seção 8.15 da `dimensoes_proximidade.md`)
fechou as 5 dims como NO-OPs em coordinate descent (cap 10
rounds/dim). Defaults da Fase 7.1 do antigo mantidos.

**Sugestão inicial** (preserva proporção do antigo, escala unificada):
- `pegada`: INTER -40 (= -50 × 0.8)
- `plano_corporal`: INTER -40
- `equipamento_grupo`: INTER -4 (= -5 × 0.8, tiebreaker)

Pesos chegam ao objetivo como `peso_se1_pegada × penalty_pegada +
peso_se1_plano × penalty_plano + peso_se1_eq × penalty_eq` por
par. Calibração rodada na sessão via sondagem.

Alternativa: 1 peso só (`peso_se1`) sobre score agregado.
**Contraponto**: dá menos controle clínico — mas o antigo
calibrou cada dim individualmente. Se uma sondagem PRÉ × PÓS
fechar o Achado 2 com 1 peso só, simplifica.

### 3.4 Escopo "mesma subregião" — preservar?

Sim. **Decisão arquitetural ainda mais forte do que pesos**.

O escopo é o que **diferencia o S-E1 do simplesmente "minimizar
equipamento repetido"**. Em peito, halteres vs barra muda o
estímulo (pegada/plano). Em passada (unilateral), halteres vs
barra é equivalente do ponto de vista biomecânico — só o load
muda. Sem escopo "mesma subregião", o score iria penalizar
"passada halteres + supino halteres", o que é clinicamente errado.

`dimensoes_proximidade.md` calibrou esse escopo na Etapa 6
(Seções 1-2). **Não reabrir.**

### 3.5 Default ON sem toggle UI? (igual S-R1, S-B5)

**Sugestão**: sim. Toggle UI explode complexidade da interface;
S-R1 e S-B5 também são default ON sem toggle. Calibração via
sondagem decide se peso correto.

### 3.6 Modulação por Aderência ao Tier?

Spec `catalogo_constraints.md` cita Aderência ao Tier como
modulador frequente (+++/+). Aluno com aderência baixa quer
variedade alta — peso S-E1 aumentaria. Aluno alta aderência
quer consistência — peso S-E1 diminuiria.

**Sugestão**: skip por ora. Aderência atual é binária no CSP
(alta=2/media=0/baixa=0; [[calibracao-aderencia-descontinuada]]).
S-E1 entra com peso fixo. Refinamento futuro quando aderência
virar gradual de novo.

---

## 4. Spec técnica (rascunho — depende das decisões §3)

### 4.1 Mudança em `gerador_csp.py`

Análogo direto da S-R1 e S-B5:

```python
# Para cada par (t1, t2) de treinos e cada subregião S em comum:
#   Para cada par de exs (e1 em T1, e2 em T2) com mesma sub e
#   ambos no escopo same-padrão (decisão §3.1):
#     penalty_pegada = matriz_pegada[e1.pegada][e2.pegada]  # 4x4
#     penalty_plano  = (e1.plano_corporal == e2.plano_corporal) ? -X : 0
#     penalty_eq     = (e1.equipamento_grupo == e2.equipamento_grupo) ? -Y : 0
#     soma no objetivo: peso_se1_pegada * penalty_pegada + ...
```

Estrutura provável: BoolVars `same_pegada_pair[(s1, s2)]`,
`same_plano_pair[(s1, s2)]`, `same_eq_pair[(s1, s2)]` por par
de slots cross-treino com mesma subregião. Penalty linear sobre
BoolVars no objetivo.

**Cuidado**: matriz pegada 4×4 não é binária — precisa de IntVar
ou de mapping específico. Olhar como o antigo fez em
`_score_proximidade` (`gerador_treino.py` ~linha 1577 conforme
Sessão 10 da Etapa 7).

### 4.2 Reaproveitar `pesos_proximidade.py`?

Decisão arquitetural. Duas opções:

- **(a)** Reimportar `ConfigPesosProximidade` no `gerador_csp.py`.
  Vantagem: 1 fonte da verdade pros pesos. Desvantagem: amarra
  CSP a um módulo do antigo.
- **(b)** Criar constantes locais no `gerador_csp.py` ou um novo
  `pesos_csp.py`. Vantagem: independência. Desvantagem: duplicação
  de configuração.

**Sugestão (b)**. Antigo morre eventualmente; CSP fica.

### 4.3 Wire em `app_flask.py`

Constante `_PESO_SE1_DEFAULT` em `app_flask.py` (precedente
S-R1, S-B5) passada por kwarg em `gerar_rotina_csp`. Sem UI.

### 4.4 Testes novos

`tests/test_csp_se1_proximidade_biomecanica.py`:

1. **`test_supino_halteres_repetido_e_penalizado`** — peito 1+1
   cross-treino, halteres vs barra disponíveis no banco. N=10
   seeds. Esperado <30% rotinas com supino halteres em ambos
   treinos (baseline da auditoria 100%).
2. **`test_desenv_halteres_repetido_e_penalizado`** — ombro 1+1
   análogo.
3. **`test_passada_halteres_OK_em_perna_anterior`** — perna_anterior
   unilateral. Passada halteres em T1 + Passada halteres em T2 NÃO
   deve gerar penalty significativa (escopo same-subregião + same-padrão
   single-slot — biomecanicamente equivalente). Garante que o escopo
   funciona.
4. **`test_grace_degradation_banco_unico_equipamento`** — cenário
   simulado onde só há 1 equipamento disponível pro padrão. Constraint
   não deve forçar inviabilidade.

---

## 5. Validação esperada (gate de fechamento)

### 5.1 Sondagem PRÉ × PÓS

Criar `tools/sondar_se1_proximidade.py` (análogo aos sondares
existentes). Métricas:

- `pct_supinos_halteres_repetido` (peito single-slot cross-treino).
- `pct_desenv_halteres_repetido` (ombro single-slot).
- `pct_pegada_repetida_cross_treino` (qualquer sub).
- `pct_plano_repetido_cross_treino`.
- `tempo_p50_s`.

Config principal: Full Body 2T com `aderencia=alta` (setup exato
da auditoria).

Baseline esperado: ~100% supino halteres + ~100% desenv halteres
em alta aderência (auditoria N=1 reportou; sondagem N=10 confirma).
Alvo pós: <30% em cada métrica.

### 5.2 Pytest

Baseline 364 + 4 novos = 368. Snapshots podem regenerar (mudanças
benignas em rotinas snapshot-protegidas que agora têm equipamento
diverso).

### 5.3 Harness 16/16

Sem regressão. Cenário 2.3 (pegada+plano cumulativa em costas) era
gate de não-regressão (5º NO-OP). Esta frente pode tirá-lo do
NO-OP — se mensurável, ótimo; se continuar 0%, é informativo.

### 5.4 Smoke E2E browser

POST `/gerar` Full Body 2T região com `aderencia=alta` (Bernardo
tem aluno teste configurável). Verificar visualmente que peito e
ombro têm equipamentos diferentes cross-treino.

---

## 6. Arquivos a mexer

- `gerador_csp.py` — bloco do objetivo + IntVars/BoolVars de
  proximidade. ~50-100 linhas.
- `app_flask.py` — constante `_PESO_SE1_DEFAULT` + wire em
  `gerar_rotina_csp` (1 linha cada).
- `tests/test_csp_se1_proximidade_biomecanica.py` — novo. 4 testes.
- `tools/sondar_se1_proximidade.py` — novo. Análogo aos outros.
- `docs/refatoracao/logs/se1_proximidade_pre.json` — snapshot.
- `docs/refatoracao/logs/se1_proximidade_pos.json` — snapshot.
- `docs/refatoracao/logs/mvp_se1_proximidade_biomecanica.md` — log.
- `docs/refatoracao/roadmap_csp.md` — marcar S-E1 como ✅.
- `docs/refatoracao/auditorias/2026-05-26.md` — Achado 2 fechado.
- `docs/refatoracao/catalogo_constraints.md` — adicionar entrada
  S-E1 no escopo ROTINA (entre S-R1 e S-R2).
- `MEMORY.md` — 1 linha apontando pro memory file novo.

---

## 7. Restrições / não-fazer

- **NÃO mergear em main sem aprovação explícita do Bernardo**
  (disciplina de merge — 1 branch ativa por vez).
- **NÃO usar `--no-verify`** ou flags que pulem hooks.
- **Commit seletivo** (`git add <arquivo>`, NUNCA `-A` — ver
  [[feedback-sessoes-paralelas-git]]).
- **NÃO usar AskUserQuestion** pras decisões clínicas §3 — texto
  livre com sugestões e contraponto (tópico clínico aberto).
- **NÃO mexer no motor antigo** `gerador_treino._score_proximidade`
  — referência arquitetural, mas implementação no CSP fica
  independente (norte §3).
- **NÃO recalibrar escopo "mesma subregião"** — decisão clínica
  fechada na Etapa 6 (Seções 1-2 da `dimensoes_proximidade.md`).
- **NÃO duplicar dims já cobertas hard** (familia_estrita,
  lateralidade, variante_pontual). Escopo desta frente é
  `pegada` + `plano_corporal` + `equipamento_grupo`.
- **NÃO introduzir modulador por Aderência ao Tier** nesta frente
  (§3.6 — fora de escopo, aguarda aderência gradual).

---

## 8. Pendências NÃO incluídas

- **Achado 4** da auditoria 2026-05-26 — ainda aberto. Próxima
  candidata.
- **Refinamento métrica 4.1 setup B** — pendência antiga
  (8.15.7 item 7), conceitualmente fechada.
- **Gate de avaliação clínica semântica** (Bloco 4) — pré-requisito
  do Bloco 5.
- **Otimização da suíte de testes** — pytest-xdist, frente própria.

---

## 9. Como abrir a sessão

1. **Confirmar leitura**: norte.md + roadmap + auditoria Achado 2
   (§143-188) + dimensoes_proximidade.md (Seções 1-2, 8.9, 8.10,
   8.11) + logs S-R1 + filtro-acessorias + catalogo_constraints.md
   (S-T4, S-R1).

2. **Confirmar entendimento** das 6 perguntas clínicas em aberto
   (§3.1 a §3.6) e propor sugestões + contraponto em texto livre.

3. **Coletar decisões do Bernardo** antes de qualquer código.

4. **Rodar sondagem PRÉ** em main ANTES da implementação. Persistir
   `logs/se1_proximidade_pre.json`. Setup exato da auditoria
   (Full Body 2T `aderencia=alta`).

5. **Implementar na ordem** §4.1 → §4.3 → §4.4.

6. **Calibrar pesos** via sondagem (rodar PÓS com pesos sugeridos
   §3.3; ajustar se métricas não fecharem alvo).

7. **Gate**: pytest + harness + smoke E2E browser.

8. **Atualizar docs**: log + roadmap + auditoria + catálogo +
   MEMORY.md.

9. **Commit seletivo + push** + aguardar aprovação Bernardo pra
   merge FF.

**Tempo estimado**: ~60-90min total (sondagem PRÉ ~5min +
implementação ~30min + calibração ~15min + sondagem PÓS ~5min +
testes ~5min + smoke ~5min + docs ~15min). Mais longo do que as
últimas 2 frentes porque a constraint é nova arquiteturalmente
(IntVars/BoolVars de proximidade + matriz 4×4 da pegada).

---

## 10. Contexto importante da sessão anterior (Filtro Acessórias CSP, 2026-05-27)

Mergeada em main commit `10d3c63`. Achado 1 totalmente fechado.

**O que entregou**:
- panturrilha removida de `ANCORAS_POR_REGIAO['lower']` em
  `gerador_treino.py`.
- 4 testes legados refatorados (motor antigo converge com CSP em
  lower(5+) também).
- 4 testes novos em `tests/test_csp_filtro_acessorias.py`.
- Sondagem PRÉ × PÓS: `pct_pant_presente` 70%→0%, vol simétrico
  30%→100%, S-R1 preservada.

**O que aprender** (lições metodológicas relevantes pra S-E1):
1. **Norte §3 paga dividendos** — filtro upstream declarativo
   (`subs_ancora_h_a0`) construído nas frentes E.1/H-A0 permitiu
   fix com 3 linhas. Mecanismos declarativos compostam.
2. **Inventário de impacto antes de quotar diff** — grep nome do
   símbolo em `tests/` antes de prometer "1 linha". Aplica
   especialmente quando S-E1 vai mexer em `pesos_proximidade.py`
   ou trazer matriz 4×4 da pegada pro CSP.
3. **YAGNI sobre mecanismo declarativo** — `min_qtd_demanda`
   descartado por falta de caso de uso. Pra S-E1: não criar
   estrutura de pesos por subregião se 1 peso global resolver.
4. **Validar pressupostos clínicos antes de implementar** — handoff
   da frente anterior antecipou "panturrilha em lower(5+) OK";
   Bernardo na abertura preferiu mais conservador. **Aplicação aqui**:
   validar com Bernardo se "halteres vs barra IMPORTA em supino, NÃO
   IMPORTA em passada" é universal (frase dele 2026-05-27) ou se há
   exceções (ex: agachamento halteres vs barra também muda estímulo).
