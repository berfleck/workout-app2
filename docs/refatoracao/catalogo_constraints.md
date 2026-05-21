# Catálogo de Constraints do Gerador

> **STATUS: RASCUNHO INICIAL — passo 2 do fluxo de refator iniciado em 2026-05-21.** Compilado a partir dos princípios clínicos (`principios_clinicos.md`) + brainstorming pós-IAs (2026-05-21). Documento vivo, atualizar a cada sessão de refinamento.
>
> **Propósito**: especificação executável do gerador. Cada constraint é uma entrada nomeada do registro declarativo do CSP/ILP. Adicionar constraint = adicionar item à lista; remover = deletar item; sem refator de outros sítios. **A coluna de dados de cada constraint determina o modelo de dados final** (Seção 4) — sem mágica, sem tag oculta.

---

## Estrutura do documento

- **Seção 1 — Hard constraints**: regras invioláveis que filtram o espaço de soluções. Sem peso, binárias.
- **Seção 2 — Soft constraints**: preferências negociáveis que entram na função objetivo com peso.
- **Seção 3 — Função objetivo**: como pesos base + moduladores do perfil de aluno combinam.
- **Seção 4 — Modelo de dados consolidado**: colunas do XLSX exigidas pelas constraints. Derivado de cima pra baixo.

---

## Seção 1 — Hard constraints

### Escopo TREINO (dentro de um único treino)

**H-T1. Mesma família refinada não repete**
- Origem: Etapa 6 Fase 3, já existe no app atual
- Dado: `familia_estrita`

**H-T2. Variante pontual não atravessa famílias na mesma subregião**
- Origem: Etapa 6 Fase 3, já existe
- Dado: `variante_pontual`

**H-T3. Lateralidade contextual em costas**
- Origem: Etapa 6 Fase 3, já existe
- Dado: `lateralidade`, subregião = `costas`

**H-T4. Vaga única na subregião ⇒ exercício composto/principal**
- Origem: Conceito 7
- Dado: `tier`
- Justificativa clínica: *"Se for pra deixar 1 exercício de coxa, esse único quase nunca seria Cadeira Extensora."*

### Escopo ROTINA (across treinos)

**H-R1. Cobertura de eixos via compostos em subregiões com ≥2 slots**
- Origem: Conceito 5, generalizado por Bernardo em 2026-05-21
- Regra: se ≥2 slots de uma subregião na rotina, exigir cobertura dos eixos de movimento via **exercícios compostos** (isolados não contam):
  - Costas: ≥1 vertical composto + ≥1 horizontal composto
  - Peito: ≥1 horizontal composto se ≥2 slots
  - Perna anterior: ≥1 bilateral composto + ≥1 unilateral composto se ≥2 slots
- Princípio geral: cobertura de variedade só "conta" quando o exercício é composto. Isolados são extras.
- Dado: `plano_corporal`, `lateralidade`, `tier`/composto
- **Importante**: solver não trata nenhuma subregião como "primeira". Ordem de processamento é justamente o que gera vieses (achado central do handoff). Todos os slots da rotina negociam simultaneamente.

### Escopo PERFIL DE ALUNO

**H-P1. Nível técnico filtra pool por `complexidade`**
- Origem: dimensão Nível técnico do vetor (sessão 2026-05-21)
- Dado: `complexidade` (existe), `nivel` no perfil do aluno
- Regra: exercício com `complexidade > teto_do_nível` não entra no pool antes do solver começar.

**H-P2. Tier Principal + Centralidade Alta + Aderência Alta ⇒ bloco solo**
- Origem: Conceito 12 + decisão da sessão 2026-05-21 sobre Terra (Fernanda vs turma 7h)
- Substitui: o `bloco_solo` manual atual no banco. Vira constraint derivada da intersecção tier do exercício × vetor do aluno.
- Dado: `tier`, vetor do aluno

### Escopo restrições físicas/dor (pendente)

**H-X. Restrições físicas/dor sobre pool**
- **STATUS**: pendente. Discutir em sessão futura.
- Direcionamento: filtros hard sobre pool por aluno (lista de exercícios proibidos ou padrões a evitar por causa de lesão).

---

## Seção 2 — Soft constraints

### Escopo BLOCO (par/trio dentro de superset)

**S-B1. Distância funcional entre exercícios do par**
- Origem: Conceito 10 + matriz P×Sub atual
- Função: preferir grupos musculares distantes ou antagonistas no mesmo bloco. Penalidade cresce com proximidade muscular.
- Dado: `padrao`, `regiao`, mapa de antagonismo
- Modulador: Densidade de Pareamento (inversão — alta = neutro, baixa = exige distância)

**S-B2. Balanço de carga implícita acumulada**
- Origem: Conceito 6
- Função: soma de carga em core, lombar, grip e neural dentro do bloco. Penalidade cresce com a soma.
- Dado: `demanda_core` (existe), `demanda_grip` (existe), `demanda_lombar` *(cadastrar)*, demanda neural derivada (`tier` + perfil)
- Modulador: Densidade de Pareamento (alta tolera mais)

**S-B3. Tolerância a fadiga prévia dentro do bloco**
- Origem: Conceito 2
- Função: se o segundo exercício do bloco é peso-livre, penalidade maior se o primeiro fadigou músculos compartilhados. Máquina tolera mais.
- Dado: `estabilidade_externa` (máquina/livre) *(cadastrar)*

**S-B4. Tamanho preferido do bloco modulado pelo perfil** ⭐
- Origem: dimensão Densidade de Pareamento do vetor
- Função: densidade alta = peso positivo pra blocos completos; densidade baixa = peso positivo pra solo.
- Modulador: Densidade de Pareamento (**dimensão dominante**)
- **MVP**: modulador ativo

### Escopo TREINO

**S-T1. Tier-order: tier alto antes de tier baixo** ⭐
- Origem: Conceito 1, achado mais consistente da entrevista (3 de 3 rotinas com esse erro)
- Função: ordem dos blocos dentro do treino respeita ranking de tier.
- Dado: `tier` *(cadastrar)*
- Modulador: Aderência ao Tier (+++), Centralidade Compostos (+++)
- **MVP**: modulador ativo

**S-T2. Fadiga prévia entre blocos**
- Origem: Conceito 2
- Função: exercício de peso-livre deve vir antes de máquina que pede os mesmos músculos.
- Dado: `estabilidade_externa`, `tier`
- Modulador: Aderência ao Tier (+), Centralidade Compostos (+)

**S-T3. Demanda neural acumulada do treino** ⭐
- Origem: Conceito 6 + perfil
- Função: penaliza soma de demanda neural alta no treino, especialmente pra alunos sem Centralidade alta.
- Dado: demanda neural derivada (`tier` + perfil)
- Modulador: Centralidade Compostos (+++), Densidade de Pareamento (alta tolera mais)
- **MVP**: modulador ativo

**S-T4. Variedade de eixos dentro de subregião com múltiplos slots**
- Origem: Conceito 5 (versão soft do H-R1)
- Função: preferir mix de planos/pegadas mesmo quando a constraint hard de cobertura está satisfeita pelo básico.
- Dado: `plano_corporal`, `pegada`

### Escopo ROTINA

**S-R1. Distribuição multi-eixo entre treinos**
- Origem: Conceito 9
- Função: mesmo grupo aparece em múltiplos treinos? Diferenciar tipo de movimento. Caso ombro caiu em Desenvolvimento nas 2× = ruim.
- Dado: `padrao`, `plano_corporal`, `lateralidade`
- Importante: solver vê os N treinos simultaneamente.

**S-R2. Frequência típica de combinações** ⭐
- Origem: Conceito 4
- Função: combinações típicas (Supino + Isolado pra peito 2 vagas) com peso maior; atípicas (Apoio + Isolado) com peso menor mas permitidas.
- Dado: ranking/tabela de tipicidade *(elicitar com Bernardo)*
- Modulador: Aderência ao Tier (+++), Centralidade Compostos (+)
- **MVP**: modulador ativo

**S-R3. Variedade no nome dentro da rotina**
- Origem: valor do app (cobertura do repertório), refinado pela observação de Fernanda (2026-05-21)
- Função: dentro da rotina, preferir nomes diferentes em slots equivalentes. Mesma família OK; mesmo nome exato em slots equivalentes não.
- Dado: `nome_exercicio`, `familia_estrita`
- Modulador: Aderência ao Tier (inversão — alta protege tier alto contra variação periférica)

### Escopo HISTÓRICO

**S-H1. Cobertura do repertório ao longo do tempo**
- Origem: valor central do app, refinamento do HIST/R-1 atual
- Função: exercícios sem aparecer há N rotinas ganham bonus crescente; exercícios da rotina anterior penalidade decrescente.
- Dado: histórico do aluno (existe)
- Modulador: Aderência ao Tier (inversão — alta = peso menor porque prefere repetir centrais; baixa = peso maior)

### Decisões da sessão — não-constraints

**Removidos da rodada inicial:**

- **Ponderação por intervalo entre treinos** (Conceito 9 refinado²) — cortado por complexidade de implementação. Reabrir se evidência clínica indicar necessidade.
- **Anti-redundância de ênfase cross-treino** (Conceito 11) — pulado. O caso original (Apoio Fechado + Supino com Anilha) é capturado pela pegada FECHADA, não por sub_enfase. Reabrir adicionando `fechada` como valor da coluna `pegada` se evidência justificar.
- **Cobertura mínima de glúteo** (Conceito 8) — redundante com H-T4 (vaga única ⇒ composto) + Conceito 1 (tier). Composto de coxa quase sempre trabalha glúteo junto, então cobertura emerge automaticamente.
- **Centralidade dentro da família** (roadmap 2026-05-18) — **fundida com `tier`**. Centralidade na família ≡ tier alto dentro da família. Uma coluna só.

**Auditoria, não constraint:**

- **Fairness anti-extinção** — preocupação histórica de Bernardo, resolvida via dashboard quantitativo (passo 5 do fluxo), não no solver. Solver não otimiza fairness; dashboard audita e flagra. Consequência: se dashboard flagrar "exercício X aparece em 3% das rotinas", a correção é ajuste manual nos pesos/constraints, não resposta autônoma do solver. Característica do design, não bug.

---

## Seção 3 — Função objetivo

### Estrutura

Em notação informal:

    score_total = SOMA sobre todas constraints soft de ( peso_constraint × violação_constraint )
    peso_constraint = peso_base × PRODUTO dos moduladores de cada dimensão do vetor do aluno

Solver minimiza `score_total`. Constraint hard violada = solução inviável (descartada). Constraint soft violada = penalidade na função objetivo proporcional ao peso final.

**Pesos base** = quanto a regra importa em média, pra um aluno médio.
**Moduladores** = quanto uma dimensão do vetor do aluno multiplica o peso base. Quando uma dimensão não afeta uma constraint, modulador = 1.0.

### Decisão de MVP — operação híbrida (2026-05-21)

Calibração contínua via dashboard (passo 5 do fluxo), mas no MVP apenas **4 constraints saem com moduladores ativos** — aquelas que mais diferenciam perfis na prática:

- **S-T1** (tier-order) modulada por Aderência ao Tier + Centralidade Compostos
- **S-B4** (tamanho bloco) modulada por Densidade de Pareamento
- **S-T3** (demanda neural total) modulada por Centralidade Compostos + Densidade de Pareamento
- **S-R2** (frequência típica) modulada por Aderência ao Tier

As outras 8 constraints saem com modulador = 1.0 (peso base só). Quando o dashboard mostrar que alguma comporta diferente do esperado, ativa-se o modulador correspondente.

**Razão da escolha**: preservar diferenciação por aluno no MVP (metade do trabalho clínico foi sobre vetor de perfil), sem inflar o MVP com calibração simultânea dos 12 moduladores. Quando o contexto clínico desta sessão estiver frio, é mais barato ativar um modulador novo do que reformular tudo do zero.

### Tabela completa de moduladores (referência)

| Constraint | Cent. Compostos | Dens. Pareamento | Aderência Tier |
|---|---|---|---|
| **S-B1** distância funcional | — | inversão (alta = neutro) | — |
| **S-B2** balanço carga | — | densidade alta tolera | — |
| **S-B3** fadiga bloco | — | densidade alta tolera | — |
| **S-B4** tamanho bloco ⭐ | — | **dominante** | — |
| **S-T1** tier-order ⭐ | +++ forte | — | +++ forte |
| **S-T2** fadiga blocos | + | — | + |
| **S-T3** demanda neural total ⭐ | +++ forte | tolera | — |
| **S-T4** variedade eixos | — | — | — |
| **S-R1** distribuição multi-eixo | — | — | — |
| **S-R2** frequência típica ⭐ | + | — | +++ forte |
| **S-R3** variedade nome | — | — | inversão |
| **S-H1** cobertura tempo | — | — | inversão |

⭐ = modulador ativo no MVP

### Override por geração

Flag manual na hora da geração sobrepõe o vetor do aluno apenas pra essa geração específica. Vetor temporário não persiste, não vira novo perfil.

### Calibração: chutes iniciais vs validação

Pesos base e valores dos moduladores na tabela são **chutes iniciais**. A calibração formal é trabalho do dashboard quantitativo (passo 5 do fluxo): roda N=1000+ rotinas das configurações comuns, mede aderência aos princípios clínicos e variação por perfil de aluno, ajusta um peso por vez. Mesma metodologia da Fase 7.6 do gerador atual, aplicada à função objetivo nova.

---

## Seção 4 — Modelo de dados consolidado

### Colunas já existentes no XLSX (verificar uso correto no novo motor)

`familia_estrita`, `variante_pontual`, `lateralidade`, `pegada`, `plano_corporal`, `equipamento_grupo`, `padrao`, `regiao`, `subregiao`, `complexidade`, `demanda_core`, `demanda_grip`, `nome_exercicio`, mapa de recrutamento muscular existente

### Colunas a cadastrar (derivadas das constraints)

- **`tier`** — Principal / Intermediário / Acessório. Necessária pra H-T4, H-P2, S-T1, S-T2, S-T3, S-R3, S-H1. **Funde com o roadmap de centralidade de 2026-05-18.**
- **`estabilidade_externa`** — máquina / livre. Necessária pra S-B3, S-T2.
- **`demanda_lombar`** — 0-3. Necessária pra S-B2. Modelo igual ao `demanda_core`.

### Coluna pendente (não cadastrar agora, marcador)

- **`pegada = fechada`** — adicionar como valor possível da coluna `pegada` SE a constraint de anti-redundância de ênfase cross-treino voltar à pauta. Permite que Supino com Anilha apareça como "supino fechado" e seja comparado a Apoio Fechado via pegada existente.

### Decisão arquitetural: dados nomeados, não tags ocultas

Cada constraint puxa de coluna pelo nome. Adicionar constraint nova exige coluna explícita no XLSX. Sem mágica, sem heurística escondida no código. Princípio garante extensibilidade — adicionar regra clínica nova é editar este catálogo + (se necessário) adicionar coluna ao XLSX, sem refator de motor.

---

## Princípios arquiteturais que guiam o catálogo

Documentados na sessão 2026-05-21 em resposta à pergunta de Bernardo *"a lógica nova deve permitir alterações e constraints novas sem necessidade de fixes pra tapar buraco"*:

1. **Constraints como entradas independentes do registro**, não código espalhado. Adicionar/remover é uma operação local.
2. **Dados nomeados no banco**, não tags ocultas. Cada constraint declara as colunas que consome.
3. **Sem ordem de processamento** entre constraints. Todas são AND-eadas (hard) ou somadas com peso (soft). Adicionar nova não atropela antigas.
4. **Pesos no perfil do aluno**, não no código. Modular comportamento por aluno = mexer no vetor, não na constraint.
5. **Validação quantitativa contínua** via dashboard de calibração (passo 5).
6. **Teste de regressão por constraint** — refator que quebra constraint antiga = fail no teste.

---

*Última atualização: 2026-05-21 (criação inicial, sessão de brainstorming pós-IAs e entrevista de perfil de aluno).*
