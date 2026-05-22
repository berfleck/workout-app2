# Casos clínicos HIB2 — recalibração pós-Etapa 3

Gerado por `tools/recalibrar_cargas_hib2.py`. Base: branch `refator-gerador`
pós-Etapa 3 (âncoras protegidas em região e subregião).

**Cada caso:** 1 seed × cfg `lower(4) + upper(3) + core(1)` × 2 treinos × bloco=2.
**OFF** = sem filtro (estado atual do motor pós-Etapa 3).
**HIB** = thresholds 6/5/5 (lombar=5, core=5).
**HIB2** = thresholds 6/5/6 (lombar=5, core=6 — calibração escolhida).

Modos HIB e HIB2 são **simulações pós-hoc** sobre os blocos OFF — a
geração não muda. Cada par dentro de um bloco é avaliado contra os
thresholds e marcado como bloqueado se a soma >= threshold E ambos têm
valor >= 1 na dimensão.

## Agregado

- Pares avaliados: **159**
- Bloqueados em HIB: **8**
- Bloqueados em HIB2: **3**
- Repermitidos HIB→HIB2 (eram bloqueados, agora passam): **5**
- Persistentes (bloqueados em ambos): **3**
- Só em HIB2 (sentinela de inconsistência — esperado 0): **0**

### Pares persistentes em HIB2 (top 10 por frequência)

Estes são os pares que o filtro HIB2 mais bloqueia. Devem ser
clinicamente justificados (lombar ou grip pesados juntos).

| # | Par | Frequência |
|---|-----|-----------:|
| 1 | `Hiperextensão 45°` + `Remada Baixa Aberta` | 1 |
| 2 | `Lev. Terra Anilha` + `Remada Curvada Barra` | 1 |
| 3 | `Agachamento Smith` + `Remada Curvada Halteres` | 1 |

### Pares repermitidos HIB→HIB2 (top 10 por frequência)

Pares que HIB bloqueava mas HIB2 deixa passar (relaxamento do core 5→6).
Validar caso-a-caso: continua sendo seguro permitir?

| # | Par | Frequência |
|---|-----|-----------:|
| 1 | `Flexão Joelhos Slide` + `Remada Baixa Neutra` | 2 |
| 2 | `Nordic Curl` + `Pallof Press` | 1 |
| 3 | `Abd Bicicleta` + `Remada Landmine` | 1 |
| 4 | `Box Jump` + `Remada Curvada Halteres` | 1 |

---

## Casos individuais

### seed=1

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Leg Press + Remada Apoiado
- **B**: Agachamento Smith + Desenv. Landmine
- **C**: Recuo + Apoio Ajoelhado
- **D**: Passada + V-Up Unilateral

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Lev. Terra Sumô + Supino Com Halteres
- **B**: Hiperextensão 45° + Remada Baixa Aberta
- **C**: Flexão Joelhos Slide + Crossover Sentado
- **D**: Abdução Polia + Prancha Lateral

**Pares com bloqueio simulado:**

- T2 B: `Hiperextensão 45°` (g=0 l=3 c=2) + `Remada Baixa Aberta` (g=3 l=2 c=2) — HIB: lombar=5≥5; HIB2: lombar=5≥5

### seed=7

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Recuo C/ Barra + Supino Smith Inclinado
- **B**: Agachamento Smith + Desenv. Landmine
- **C**: Step Up Alt. + Pullover Halteres
- **D**: Cadeira Extensora + Canoinha

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Apoio + Desloc. Lateral c/ Band
- **B**: Remada Apoiado + Flexão Joelhos Slide
- **C**: Crucifixo Halteres + Prancha Bola
- **D**: Hip Thrust Uni. + Ponte Na Caixa

_Nenhum par bloqueado em HIB ou HIB2._

### seed=13

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Agachamento Livre + Desenvolvimento Barra
- **B**: Step Up + Apoio Elevado
- **C**: Barra Isométrica + Box Jump
- **D**: Agach. Lateral + Crunch Chão

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Supino Com Halteres + Flexão Joelhos Feijão
- **B**: Crossover Sentado + Dead Bug C/ Bola
- **C**: Pullover Polia + Side Clams
- **D**: Ponte Na Caixa + Hip Thrust Uni.

_Nenhum par bloqueado em HIB ou HIB2._

### seed=23

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Recuo C/ Barra + Desenvolvimento Barra
- **B**: Agachamento Búlgaro + Supino Com Barra
- **C**: Agachamento Smith + Pullover Polia
- **D**: Leg Press + Canoinha

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Stiff Barra Livre + Apoio Elevado
- **B**: Good Morning + Crucifixo Halteres
- **C**: Serrote + Abdução Polia
- **D**: Flexão Joelhos Slide
- **E**: Dead Bug C/ Anilha

_Nenhum par bloqueado em HIB ou HIB2._

### seed=42

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Agachamento Livre + Supino Com Barra
- **B**: Step Up + Remada Apoiado
- **C**: Recuo + Box Jump
- **D**: Desenv. Halteres Uni. + V-Up Unilateral

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Remada Curvada Barra + Lev. Terra Anilha
- **B**: Stiff Barra Livre + Apoio Ajoelhado
- **C**: Flexão Joelhos Slide + Crossover
- **D**: Abdução Polia + Hollow Hold

**Pares com bloqueio simulado:**

- T2 A: `Remada Curvada Barra` (g=3 l=3 c=3) + `Lev. Terra Anilha` (g=2 l=2 c=2) — HIB: lombar=5≥5; core=5≥5; HIB2: lombar=5≥5

### seed=99

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Agachamento Livre + Supino Com Barra
- **B**: Passada Dos Steps + Puxada Neutra
- **C**: Recuo Alternado + Crunch No Cabo
- **D**: Desenv. Halteres Uni. + Box Jump

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Lev. Terra Sumô + Apoio Elevado
- **B**: Stiff Barra Smith + Crucifixo Halteres
- **C**: Desloc. Lateral c/ Band + Pullover Halteres
- **D**: Nordic Curl + Pallof Press

**Pares com bloqueio simulado:**

- T2 D: `Nordic Curl` (g=0 l=2 c=3) + `Pallof Press` (g=1 l=1 c=2) — HIB: core=5≥5; HIB2: livre

### seed=100

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Agachamento Smith + Desenvolvimento Smith
- **B**: Recuo + Apoio Elevado
- **C**: Remada Uni Polia + Box Jump
- **D**: Step Up Alt. + Crunch Chão

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Lev. Terra + Supino Smith Inclinado
- **B**: Puxada Supinada + Flexão Joelhos Slide
- **C**: Crossover Sentado + Abdução Polia
- **D**: Hip Thrust C/ Band + Prancha

_Nenhum par bloqueado em HIB ou HIB2._

### seed=117

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Passada Dos Steps + Desenvolvimento Barra
- **B**: Remada Curvada Halteres + Agachamento Smith
- **C**: Recuo + Supino Com Barra
- **D**: Box Jump + Crunch No Cabo

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Good Morning + Remada Aberta Trx
- **B**: Stiff Uni. Halteres + Apoio Ajoelhado
- **C**: Nordic Curl + Crucifixo Halteres
- **D**: Pallof Press + Side Clams

**Pares com bloqueio simulado:**

- T1 B: `Remada Curvada Halteres` (g=2 l=3 c=3) + `Agachamento Smith` (g=1 l=2 c=1) — HIB: lombar=5≥5; HIB2: lombar=5≥5

### seed=200

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Agachamento Smith + Desenv. Halteres Sentado
- **B**: Walking Lunges + Remada Baixa Aberta
- **C**: Apoio Ajoelhado + Agach. Lateral
- **D**: Cadeira Extensora + Canoinha

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Stiff Halteres + Supino Com Anilha
- **B**: Remada Baixa Neutra + Flexão Joelhos Slide
- **C**: Crossover Sentado + Prancha Bola
- **D**: Side Clams + Ponte Uni. Caixa

**Pares com bloqueio simulado:**

- T2 B: `Remada Baixa Neutra` (g=3 l=2 c=2) + `Flexão Joelhos Slide` (g=0 l=2 c=3) — HIB: core=5≥5; HIB2: livre

### seed=314

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Remada Curvada Halteres + Leg Press
- **B**: Recuo + Desenv. Halteres Sentado
- **C**: Step Up + Supino Smith Inclinado
- **D**: V-Up + Cadeira Extensora

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Hip Thrust + Apoio Ajoelhado
- **B**: Flexão Joelhos Feijão + Crucifixo Halteres
- **C**: Pullover Polia + Side Clams
- **D**: Ponte Na Caixa + Hollow Hold

_Nenhum par bloqueado em HIB ou HIB2._

### seed=555

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Agachamento Livre + Supino Com Anilha
- **B**: Passada + Desenv. Landmine
- **C**: Serrote + Cadeira Extensora
- **D**: Step Up + Crunch Na Bola

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Good Morning + Apoio
- **B**: Flexão Joelhos Slide + Crossover Sentado
- **C**: Pullover Polia + Prancha Lateral
- **D**: Side Clams + Ponte Uni. Caixa

_Nenhum par bloqueado em HIB ou HIB2._

### seed=777

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Leg Press + Desenvolvimento Barra
- **B**: Step Up Alt. + Apoio Elevado
- **C**: Remada Landmine + Abd Bicicleta
- **D**: Agach. Lateral + Cadeira Extensora

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Hiperextensão 45° + Puxada Supinada
- **B**: Supino Com Barra + Prancha Renegade
- **C**: Crucifixo Halteres + Cadeira Flexora
- **D**: Side Clams + Ponte

**Pares com bloqueio simulado:**

- T1 C: `Remada Landmine` (g=3 l=3 c=3) + `Abd Bicicleta` (g=0 l=1 c=2) — HIB: core=5≥5; HIB2: livre

### seed=1000

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Passada Dos Steps + Desenvolvimento Smith
- **B**: Agachamento Smith + Apoio Elevado
- **C**: Recuo + Pullover Polia
- **D**: Cadeira Extensora + Crunch Na Bola

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Hiperextensão 45° + Supino Com Barra
- **B**: Remada Seal Halteres + Flexão Joelhos Slide
- **C**: Crossover Sentado + Prancha Bola
- **D**: Side Clams + Ponte Unilateral

_Nenhum par bloqueado em HIB ou HIB2._

### seed=1234

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Agachamento Búlgaro + Desenvolvimento Smith
- **B**: Leg Press + Supino Com Anilha
- **C**: Passada + Puxada Supinada
- **D**: Box Jump + Canoinha

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Stiff Barra Livre + Apoio Elevado
- **B**: Serrote + Flexão Joelhos Feijão
- **C**: Crossover Sentado + Pallof Press
- **D**: Side Clams + Ponte Unilateral

_Nenhum par bloqueado em HIB ou HIB2._

### seed=1492

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Passada Dos Steps + Supino Com Anilha
- **B**: Recuo + Abd Bicicleta
- **C**: Remada Uni Polia + Box Jump
- **D**: Desenv. Halteres Uni. + Cadeira Extensora

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Stiff Uni. Smith + Apoio Elevado
- **B**: Crucifixo Halteres + Prancha Renegade
- **C**: Cadeira Flexora + Pullover Polia
- **D**: Side Clams + Hip Thrust Uni.

_Nenhum par bloqueado em HIB ou HIB2._

### seed=1789

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Passada Dos Steps + Desenvolvimento Smith
- **B**: Remada Curvada Smith + Agachamento Goblet
- **C**: Supino Com Halteres + Agach. Lateral
- **D**: Cadeira Extensora + Canoinha

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Lev. Terra Anilha + Apoio
- **B**: Flexão Joelhos Slide + Crossover
- **C**: Abdução Polia + Pullover Polia
- **D**: Prancha Bola + Ponte

_Nenhum par bloqueado em HIB ou HIB2._

### seed=1984

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Agachamento Búlgaro + Desenv. Halteres Sentado
- **B**: Agachamento Goblet + Apoio Elevado
- **C**: Leg Press + Barra Isométrica
- **D**: Passada + Abd Bicicleta

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Lev. Terra + Supino Com Halteres
- **B**: Puxada Supinada + Desloc. Lateral c/ Band
- **C**: Nordic Curl + Crucifixo Halteres
- **D**: Roda Abdominal + Ponte Uni. Caixa

_Nenhum par bloqueado em HIB ou HIB2._

### seed=2024

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Agachamento Livre + Desenvolvimento Barra
- **B**: Step Up Alt. + Supino Smith Inclinado
- **C**: Barra Isométrica + Box Jump
- **D**: Slide Board Lateral + Canoinha

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Lev. Terra + Apoio
- **B**: Remada Baixa Neutra + Flexão Joelhos Slide
- **C**: Crossover Sentado + Ponte Alternada
- **D**: Prancha Lateral + Side Clams

**Pares com bloqueio simulado:**

- T2 B: `Remada Baixa Neutra` (g=3 l=2 c=2) + `Flexão Joelhos Slide` (g=0 l=2 c=3) — HIB: core=5≥5; HIB2: livre

### seed=4096

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Agachamento Búlgaro + Desenvolvimento Barra
- **B**: Leg Press + Apoio
- **C**: Remada Baixa Aberta + Slide Board Lateral
- **D**: Cadeira Extensora + Canoinha

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Good Morning + Supino Com Anilha
- **B**: Lev. Terra Anilha + Crossover
- **C**: Desloc. Lateral c/ Band + Pullover Polia
- **D**: Flexão Joelhos Feijão + Pallof Press

_Nenhum par bloqueado em HIB ou HIB2._

### seed=9999

**Treino 1** (lower(4) + upper(3) + core(1))

- **A**: Agachamento Búlgaro + Desenv. Halteres Sentado
- **B**: Passada Dos Steps + Apoio Ajoelhado
- **C**: Remada Curvada Halteres + Box Jump
- **D**: V-Up Unilateral + Cadeira Extensora

**Treino 2** (lower(4) + upper(3) + core(1))

- **A**: Stiff Uni. Halteres + Supino Com Anilha
- **B**: Remada Uni Polia + Nordic Curl
- **C**: Crossover + Abdução Polia
- **D**: Hip Thrust C/ Band + Hollow Hold

**Pares com bloqueio simulado:**

- T1 C: `Remada Curvada Halteres` (g=2 l=3 c=3) + `Box Jump` (g=0 l=1 c=2) — HIB: core=5≥5; HIB2: livre
