# Fase 4 — Handoff Sessão Sonnet → Opus

Branch `fase-4` · Última sessão: 2026-05-15 (Sonnet 4.6)
HEAD ao fechar sessão: commit `a0f9e1b`

---

## Seção 1 — Trail de auditoria das decisões C1–C7

### C1 — `flexao_plantar` → `pegada = null`

- **Origem:** (b) decidida pelo user via AskUserQuestion. Contexto clínico: exercícios
  de panturrilha (variantes de elevação ponta do pé) envolvem apoio em superfície
  ou corrimão — o "grip" não é um vetor biomecânico diferenciador entre pares de
  exercícios; não se enquadra em nenhuma das 4 categorias (aberta/neutra/pronada/
  supinada). Confirmou-se que flexao_plantar join com a lista de padrões que recebem
  null por default (Seção 7.2 directives).
- **Escopo:** todos os exercícios no padrão `flexao_plantar` (subregião `panturrilha`).
  No banco atual: Elevação Ponta Do Pé, Elevação Ponta Do Pé Máquina, Elevação Ponta
  Do Pé Leg Press (e quaisquer variações cadastradas neste padrão).
- **Exceções:** nenhuma conhecida.
- **Análogos a vigiar:** nenhum — diretriz aplica ao padrão inteiro, não a exercícios
  individuais. Qualquer exercício novo em `flexao_plantar` recebe null automaticamente.

---

### C2 — Face Pull (Polia) → `pegada = null`

- **Origem:** (b) decidida pelo user via AskUserQuestion. Contexto clínico: Face Pull
  usa corda com liberdade de rotação — o punho rotaciona externamente ao longo do
  movimento. Não há aderência a aberta/neutra/pronada/supinada; a corda permite
  transição contínua. Não aproxima clinicamente por pegada.
- **Escopo:** "Face Pull" especificamente (padrão `posterior_ombro`). Se existir
  variante com barra fixa em vez de corda, precisa ser reavaliada individualmente.
- **Exceções:** variantes com barra reta → pegada seria pronada ou supinada e
  mereceriam tag. Nenhuma dessas existe no banco atual.
- **Análogos a vigiar:** outros exercícios de `posterior_ombro` com corda/handle
  rotacional (ex: "Reverse Fly Polia" com corda → checar se o handle rota). Exercícios
  com TRX ring handles também são candidatos a null por liberdade rotacional.

---

### C3 — Desenvolvimento Landmine → `pegada = neutra`

- **Origem:** (b) decidida pelo user via AskUserQuestion. Contexto clínico: handle
  tipo T-bar no landmine (ou mão sobre o cano) posiciona o antebraço em neutro
  natural — polegar para cima durante todo o movimento. Distinto de desenvolvimento
  com barra (pronada) ou halteres (neutro/livre).
- **Escopo:** "Desenvolvimento Landmine" (padrão `ombro_composto`). Se existir
  variante unilateral ("Desenvolvimento Landmine One Arm"), mesma decisão — handle
  identico, mesmo plano neutro.
- **Exceções:** nenhuma conhecida no banco atual.
- **Análogos a vigiar:** outros exercícios Landmine de empurrar/ombro que existam
  no banco. Remada Landmine já tem `pegada: neutra` no YAML G2 (linha 267) —
  consistente.

---

### C4 — Anilha → `equipamento_grupo = halter` (exceto Lev. Terra Anilha = `barra`)

- **Origem:** (b) decidida pelo user via AskUserQuestion (regra geral: anilha como
  halter), com exceção detectada retroativamente via protocolo doc-first: Anexo 4.1
  item 9 especifica explicitamente `Lev. Terra Anilha → barra` por consistência de
  família com os outros terra (que são barbell). A exceção toma precedência sobre a
  regra geral.
- **Escopo de aplicação:**
  - `halter`: Elevação Frontal Anilha, Crucifixo Declinado Anilha (se existir),
    Dead Bug C/ Anilha (mas é core → null por 9-bis de qualquer forma), e qualquer
    outro exercício com "Anilha" no nome que não seja da família terra.
  - `barra` (exceção): Lev. Terra Anilha — família `terra`, segue a família.
- **Exceções explícitas:**
  - `Lev. Terra Anilha` → `barra` por Anexo 4.1 item 9. Exceção é nominal e
    específica; não se estende a outros exercícios anilha por analogia sem nova
    evidência.
  - Exercícios de core com anilha → null por diretriz 9-bis (ex: Dead Bug C/ Anilha).
    A diretriz 9-bis toma precedência sobre C4.
- **Análogos a vigiar:**
  - `Supino Com Anilha` — **⚠️ CONFLITO COM YAML** (ver Seção 2). YAML tem `barra`
    por analogia a item 9, mas C4 indica `halter` (Supino não é família terra).
    Resolver em Sub-E antes de portar.
  - `Lev. Terra Uma Perna Anilha` (se existir) → `barra` pela mesma lógica do item 9
    (família terra).

---

### C5 — Feijão / Slide Board `knee_flexion` → `equipamento_grupo = null`

- **Origem:** (a) deduzida — resposta literal/deductível no doc. Fontes:
  - Seção 1.6 lista Slide Board como exemplo de `(vazio)` em contextos onde o
    implemento define mecânica mas não carga.
  - Seção 7.2 item 8 lista Slide Board explicitamente como caso de "aceita vazio
    quando não aproxima".
  - YAML G4 linha 615: `Slide Board Lateral` já tem `equipamento_grupo: null` com
    comentário "Seção 7.2 nota 8 — Slide Board = vazio".
  - *Pergunta C5 foi desnecessária — protocolo doc-first teria evitado.*
- **Escopo:** `Flexão Joelhos Feijão`, `Flexão Joelhos Slide` (padrão `knee_flexion`,
  subregião `perna_posterior`).
- **Exceções:** nenhuma conhecida.
- **Análogos a vigiar:** outros exercícios com superfície de deslize ou implemento que
  define mecânica sem carga: Prancha Slideboard já tem null no YAML G8 (linha 722);
  TRX em qualquer posição → null em G2 (Remada Aberta/Neutra Trx já null); Box Jump
  → null em YAML G4 (linha 482). Padrão: "se o nome do implemento define o exercício
  mas não aproxima pelo eixo de equipamento, usa null."

---

### C6 — Hip Thrust Uni., Ponte Unilateral, Copenhagen → `equipamento_grupo = corporal`

- **Origem:** (a) deduzida — precedente em Seção 1.6 lista "pontes simples" como
  `corporal`. Extensão por analogia direta: Hip Thrust Unilateral e Ponte Unilateral
  são variações de ponte; Copenhagen é abdução com apoio corporal. Todos são
  peso-corporal primariamente.
  - *Pergunta C6 foi desnecessária — Seção 1.6 dava o precedente.*
- **Escopo:** `Hip Thrust Unilateral`, `Ponte Unilateral`, `Copenhagen` (padrão
  `abduction` ou subregião `perna_posterior` dependendo do exercício — verificar no
  XLSX em Sub-F).
- **Exceções:** variantes com banda elástica ou halter → checar individualmente se
  existe no banco. Uma banda elástica adicionada muda o vetor primário?
  Clinicamente não — a posição corporal é o vetor de proximidade aqui.
  Manter `corporal` mesmo com banda como implemento secundário (banda vai no
  `eq_secundario`, não muda o `equipamento_grupo`).
- **Análogos a vigiar:** Hiperextensão Na Bola (se existir) → provavelmente `corporal`
  pela mesma lógica. Ponte Bilateral simples — já coberta pela regra de Seção 1.6
  ("pontes simples").

---

### C7 — Hiperextensão 45° → `plano_corporal = em_pe`

- **Origem:** (a) deduzida — literal no Anexo 4.1 item 10. Texto do Anexo: "Hiperextensão
  45° → `plano_corporal = em_pe`" (aparelho inclinado em 45° = posição ortostática
  funcional, diferente de apoiada/curvada/deitado).
  - *Pergunta C7 foi desnecessária — Anexo 4.1 item 10 é literal.*
- **Escopo:** `Hiperextensão 45°` (padrão `hinge`, subregião `perna_posterior`).
- **Exceções:** Mesa Romana (GHD horizontal) → plano diferente; não coberta por esta
  decisão — avaliar separado em Sub-F se existir no banco.
- **Análogos a vigiar:** Hiperextensão 90° (equipamento vertical tipo Roman chair) →
  seria `apoiada` ou outro plano; avaliar se existe. Hiperextensão com Bola de
  Pilates → `apoiada` (deitado prono sobre a bola).

---

## Seção 2 — Auditoria do YAML mocks vs. regras atualizadas

Verificação realizada via leitura integral de `tools/mocks/dimensoes_etapa_6.yaml`
(77 entradas: 66 cadastrado + 11 mock_futuro).

### 1. Seção 7.2 item 9-bis — `equipamento_grupo = null` em todos os G8 (core)

**Status: ✅ Propagado — 25/25 entradas G8 têm `equipamento_grupo: null`.**

O YAML já contém a diretriz no comentário inline (linhas 670-678):
*"Diretriz Sessão 7c (correção retroativa): equipamento_grupo = null em TODO G8"*.
Casos específicos confirmados: Dead Bug C/ Anilha → null (linha 785, nota "Decisão B
Sessão 7c"), Prancha Renegade → null (linha 731), Crunch No Cabo → null (linha 824),
INFRA Suspenso (barra fixa) → null com nota "barra fixa é estrutura passiva" (linha 912).

**Impacto para Sub-E:** nenhum. Port das 20 entradas cadastrado G8 pode copiar
`equipamento_grupo: null` diretamente do YAML sem risco.

---

### 2. Anexo 4.1 item 11 — `variacao_de = "flexao deitado"` (Feijão + Slide)

**Status: N/A — exercícios ausentes do YAML (G5 não coberto).**

`Flexão Joelhos Feijão` e `Flexão Joelhos Slide` não têm entradas no YAML overlay.
A correção do item 11 (campo `variacao_de`) foi aplicada **diretamente ao XLSX em Sub-A**
desta sessão. No Sub-E, essas linhas receberão apenas as 5 colunas de dims (via Seção 7
rules + decisão C5 para `equipamento_grupo`), não a partir do YAML.

**Impacto para Sub-E:** Sub-E não toca essas linhas (não são YAML cadastrado).
Sub-F as cobrirá como "non-YAML com C5 aplicado".

---

### 3. Anexo 4.1 item 13 — Split família `prancha frontal` / `prancha lateral`

**Status: ✅ Propagado no YAML — 6 frontais + 1 lateral.**

YAML G8 linhas 683-741: Prancha, Prancha Alternada, Prancha Bola, Prancha Feijao,
Prancha Slideboard, Prancha Renegade → `familia_estrita: "prancha frontal"`; Prancha
Lateral → `familia_estrita: "prancha lateral"`.

A correção do item 13 (campo `variacao_de` no XLSX) foi aplicada em **Sub-B** desta
sessão, alinhando o XLSX com o YAML. No Sub-E, o port escreverá as dims (que já estão
corretas no YAML) — sem divergência esperada.

**Impacto para Sub-E:** nenhum conflito. YAML e XLSX já estão em sincronia.

---

### 4. Anexo 4.1 item 7 — Stiff bi+uni unificados em `variacao_de = "stiff"`

**Status: N/A — exercícios stiff ausentes do YAML (G5 hinge não coberto).**

`Stiff` e `Stiff Unilateral` não têm entradas no YAML. A correção (variacao_de) foi
aplicada ao XLSX em **Sub-A** desta sessão. No Sub-E, o port não toca essas linhas.
Sub-F as cobrirá como non-YAML: padrão `hinge`, dims por Seção 7 (pegada=null,
plano_corporal=... a checar, equipamento_grupo=barra).

**Impacto para Sub-E:** zero.

---

### 5. Anexo 4.1 item 8 — Good Morning → `variacao_de = "stiff"`

**Status: N/A — Good Morning ausente do YAML (G5 hinge não coberto).**

Mesmo caso do item 7. Correção aplicada ao XLSX em Sub-A. Sub-F cobre.

**Impacto para Sub-E:** zero.

---

### 6. Anexo 4.1 item 15-quater — Refator CORE (4 padrões refinados)

**Status: ✅ Consistente — estratégia correta para cadastrados e mock_futuros.**

Para as 20 entradas **cadastradas** de G8: o YAML **não especifica `padrao`** (campo
ausente nas `dimensoes` — correto). O overlay do harness só sobrescreve os campos de
dims; o campo `padrao` do Exercicio vem do XLSX, que já foi migrado na **Etapa 8.2**
para os 4 padrões refinados (`flexao_tronco`, `flexao_lateral`, `rotacao_tronco`,
`flexao_quadril`). Não há conflito.

Para os 5 **mock_futuros** de G8 (Russian Twist, 4 INFRAs): o campo `extras.padrao`
já usa os padrões refinados corretos:
- Russian Twist → `rotacao_tronco`
- INFRA Alternado, Suspenso, Chão, Roll-Up → `flexao_quadril`

**Impacto para Sub-D:** ao cadastrar Russian Twist no XLSX, obrigatoriamente expandir
`PADRAO_PARA_SUBREGIAO["rotacao_tronco"]` de `{"core_isometrico"}` para
`{"core_isometrico", "core_dinamico"}` **e** adicionar `rotacao_tronco` ao
`_PADROES_LEGADOS["core_dinamico"]` em `gerador_treino.py`. Coordenar com usuário
antes de aplicar (conforme processo original).

---

### ⚠️ DISCREPÂNCIA DETECTADA — Supino Com Anilha

**Conflito entre YAML e regra C4.**

- **YAML G1 linha 52:** `equipamento_grupo: "barra"` com comentário "Anilha tratada
  como barra (Anexo item 9 análogo)".
- **Regra C4 desta sessão:** `anilha → halter`, exceto `Lev. Terra Anilha → barra`
  (exceção específica do item 9).

**Análise:** O YAML foi escrito antes de C4 ser formalizado. A analogia "Anexo item 9"
foi estendida indevidamente — o item 9 é específico para `Lev. Terra Anilha` pela
lógica de consistência de família terra (deadlifts são barra; a variante anilha segue
a família). Supino Com Anilha não pertence à família terra; a anilha aqui é segurada
nas mãos como peso livre, semanticamente mais próximo de `halter`.

**Resolução para Sub-E:** ao portar a entrada G1 Supino Com Anilha, usar `halter` (não
`barra`). O YAML é a fonte de dims para o harness in-memory; o XLSX banco real deve
receber o valor correto conforme C4. Se quiser manter coerência, atualizar o YAML
também (mas o harness usa o valor YAML — é uma decisão separada).

**Nota:** confirmar com usuário antes de aplicar, dado que inverte o YAML.

---

## Seção 3 — Padrões de erro vigiados nesta sessão (anti-padrões para Opus)

### Anti-padrão 1: "Regra geral cobre família" sem cruzar com Anexo 4.1

**O que aconteceu:** C4 estabeleceu "anilha → halter" como regra geral. Só depois, ao
verificar no Anexo 4.1, foi detectado que o item 9 tinha exceção específica para
Lev. Terra Anilha. A regra geral estava correta — a exceção estava no doc e foi
recuperada.

**O problema análogo no YAML:** Supino Com Anilha recebeu `barra` por analogia a item 9
("Anexo item 9 análogo"), mas item 9 é nominal/específico para família terra.
A analogia foi indevida.

**Regra operacional para Opus:** toda recomendação de `equipamento_grupo` que cubra uma
"família de exercícios" (ex: "anilha", "máquina", "cabo") deve ser cruzada com Anexo 4.1
inteiro antes de aplicar. Checar se existe override nominal para aquele exercício
específico. Se existir, o Anexo prevalece sobre a regra geral.

---

### Anti-padrão 2: AskUserQuestion sem varredura doc-first prévia

**O que aconteceu:** decisões C5, C6 e C7 foram abertas como perguntas ao user mesmo
tendo respostas literal ou deductivamente no `dimensoes_proximidade.md`:
- C7: Anexo 4.1 item 10 é literal.
- C5: Seção 1.6 + Seção 7.2 item 8 dão o precedente do Slide Board.
- C6: Seção 1.6 lista "pontes simples → corporal".

**Regra operacional para Opus:** antes de abrir AskUserQuestion sobre dim de exercício,
executar varredura de `dimensoes_proximidade.md` na ordem:
`Annexo 4.1 → 4.2 → Seção 2 Gx → Seção 7.x → notas`. Só abrir pergunta se a varredura
vier vazia. Ao abrir, citar explicitamente os precedentes consultados e por que foram
insuficientes.

---

### Anti-padrão 3: Analogia de exceção além do escopo nominal

**O que aconteceu:** o YAML registrou Supino Com Anilha como `barra` citando
"Anexo item 9 análogo". O item 9 é nominal (cita Lev. Terra Anilha explicitamente
pela lógica de família terra). A extensão para Supino Com Anilha foi errônea porque
a semântica de família é diferente.

**Regra operacional para Opus:** exceções nominais em Anexo 4.1 se aplicam ao exercício
citado e à sua família imediata (pelo mesmo argumento clínico que justificou a exceção).
Extensão por analogia a outras famílias requer nova justificativa clínica — não basta
superficial similaridade de nome de implemento.

---

## Seção 4 — Estado do git ao fechar sessão

**Branch:** `fase-4` (a partir de `main` @ `ecc7c19`)

**Commits da sessão (em ordem):**

| Hash | Descrição |
|------|-----------|
| `ce55db3` | Fase 4 Sub-A/triagem — items 7+8+11 + script triagem + triagem_fase_4.md |
| `906d5d4` | Fase 4 Sub-B + snapshots — items 3+13 (Slide Board purpose, split pranchas) |
| `a0f9e1b` | Fase 4 Sub-C — setup estrutural: 5 colunas dim + loader ativo/variante_pontual |

**HEAD:** `a0f9e1b` ✅

**Working tree:** limpo (verificado antes de fechar — git status mostra sem modificações
não-commitadas após este arquivo ser commitado).

**Push para origin:** verificar abaixo — branch `fase-4` pode não ter upstream ainda.
