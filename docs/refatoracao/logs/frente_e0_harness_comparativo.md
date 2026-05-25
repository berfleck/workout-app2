# Log — Frente E.0: harness comparativo CSP × motor antigo

**Data**: 2026-05-24
**Branch**: `frente-e0-harness-comparativo` (a partir de `main`)
**Arquivos novos**:
- `tools/harness_comparativo_e0.py` — script standalone, ~600 linhas
- `docs/refatoracao/relatorios/E0_<data>.md` — relatório gerado
- `docs/refatoracao/logs/frente_e0_harness_comparativo.md` — este log

**Arquivos atualizados**:
- `docs/refatoracao/roadmap_csp.md` — Frente E.0 marcada ✅; Bloco 3 (E.1) desbloqueado
- `MEMORY.md` + memória nova `project_frente_e0_harness.md`

**Status**: ✅ concluída — relatório gerado N=100, 4 configs × 1 perfil
default, decisão de Frente E.1 (clean break vs flag) fica pra Bernardo
ler o relatório e decidir.

---

## Objetivo

Primeira frente do Bloco 2 do roadmap CSP. Implementar harness que roda
N rotinas (~100) por configuração comum nos DOIS motores (CSP novo +
antigo) com mesma entrada normalizada e produz relatório markdown
lado-a-lado em `docs/refatoracao/relatorios/E0_<data>.md`. Pré-requisito
pra Frente E.1 (substituir `/gerar` pelo CSP).

Escopo Frente E.0 — **puramente observacional**:
- Não modificar nenhum motor.
- Achados de divergência viram pendência no roadmap, não patch.
- Decisão de aprovação visual; sem veredicto automático.

## Decisões fechadas (handoff + AskUserQuestion inicial)

1. **N=100 default**, configurável via `--n` CLI.
2. **4 configs canônicas** (decisão recomendada):
   - Full Body 2T (mix amplo de subregiões)
   - ABC 3T (push/pull+arms/lower+core)
   - upper(3)×2T (caso que destravou cycling Bresenham, Seção 8.15.14)
   - perna_ant(3)+perna_post(3), 1 treino (testa H-R1)
3. **1 perfil default** (nivel=3, aderência=media) + flag `--matriz` opcional
   pra rodar 2×2 (nivel ∈ {1,3} × aderência ∈ {alta, baixa}).
4. **Visual + descartar INFEASIBLE + pipeline completo**:
   - Aprovação por leitura visual do Bernardo.
   - INFEASIBLE = run descartado; reportar % inviabilidade como métrica
     auxiliar.
   - Tempo medido = pipeline inteiro (gerar_rotina_csp end-to-end vs
     gerar_multiplos_treinos end-to-end). Comparação justa.

## O que foi implementado

### `tools/harness_comparativo_e0.py`

Script standalone em uma única peça. Organização interna:

1. **Tipos** — `ConfigComum` (entrada normalizada), `PerfilAluno` (perfil
   de aluno com mapping `aderencia_tier` → `peso_aderencia_csp`),
   `RunResult` (1 execução), `AgregadoMotor` (agregado N runs).
2. **Configurações canônicas** — função `_configs_canonicas()` retorna
   as 4 configs decididas. Demandas tipadas como tuplas (frozen).
3. **Invocação dos motores** — `rodar_csp` e `rodar_antigo` recebem
   `ConfigComum`+`PerfilAluno`+`banco`+`seed`, retornam `RunResult`. CSP
   recebe `ConfigVariedade()` default, peso evitar agonistas=10 quando
   toggle ON, peso tamanho bloco=5 (defaults validados em 4.B/4.C).
   Antigo usa `max_complexidade=perfil.nivel` (mirror byte-a-byte do
   H-P1 do CSP) e `random.seed(seed)` antes de invocar (cycling +
   tie-break do antigo lê `random` global).
4. **Normalização de output** — saída do CSP (`dict` com
   `treinos: list[dict]` com `blocos: list[list[Exercicio]]`) e do
   antigo (`list[Sessao]` com `blocos: list[SuperSerie]`) são
   convertidas pro mesmo shape `list[treino][bloco][exercicio]`.
5. **Métricas** (7 + auxiliar):
   - `metrica_tier_por_subregiao` — Counter por subregião, slot a slot
     cross-iter.
   - `metrica_h_r1_violacoes` — % rotinas com violação por subregião
     ativa (≥ min_slots), usando `H_R1_REGRAS` do gerador_csp como
     fonte de verdade (predicados puxadas/remadas/horizontal/bi/uni
     compostos via `purpose=="compound"`).
   - `metrica_ancoras_violacoes` — % rotinas sem cada padrão
     `obrigatoria=True` do `ANCORAS_POR_SUBREGIAO` (gerador_treino),
     filtrado pelas subregiões com ≥1 slot na rotina.
   - `metrica_variedade_intra` — # rotinas distintas via assinatura
     canônica `(sorted_nomes_T1, sorted_nomes_T2, ...)`.
   - `metrica_overlap_r1` — % slots iguais entre rotinas consecutivas
     (multiset intersect / total slots). Mirror da métrica contínua
     4.1 da Etapa 7 Fase 7.5.
   - `metrica_cycling_fairness` — distribuição (counter por treino)
     de cada padrão usado. Mostra % treino dominante (idealmente
     1/n_treinos). Inativa quando n_treinos < 2.
   - Tempo p50 + p95 em ms (pipeline completo) + % inviabilidade.
6. **Renderização markdown** — uma seção por (perfil, config) com
   tabelas lado-a-lado CSP × Antigo. Cabeçalho global lista parâmetros
   + decisões + métricas reportadas.
7. **CLI** — `--n`, `--seed`, `--matriz`, `--out`, `--quiet`.

### Decisões de implementação

- **Reuso direto de `H_R1_REGRAS` e `ANCORAS_POR_SUBREGIAO`**: o harness
  é puramente observacional; mantém fonte única de verdade. Quando
  catálogos evoluírem, o harness segue automaticamente.
- **Filtragem H-P1 do antigo via `max_complexidade=perfil.nivel`**: o
  motor antigo não aceita `nivel_aluno` direto; precisa do teto. Como o
  vetor de perfil só tem `nivel` por enquanto, mapping é trivial.
- **Seed nos dois motores**: CSP recebe `seed` direto (consome em
  `random.Random(seed).randint(...)` interno); antigo recebe via
  `random.seed(seed)` global antes da chamada. Resultado: mesmo seed
  → resultado reproduzível para o antigo. Pro CSP, CP-SAT não é
  totalmente determinístico mesmo com seed fixa (memória
  `feedback_cpsat_nao_determinismo.md`), mas seeds distintas dão
  variedade suficiente pras métricas estatísticas.
- **Tempo médio em ms (não segundos)**: a faixa típica é 1ms (antigo)
  até ~2s (CSP); ms dá precisão razoável sem virar notação científica.

## Achados / sinais de alerta

### 1. Bíceps tem todas as 6 variações na mesma família (`Rosca bíceps`)

Descoberto no smoke N=5: a config inicial do ABC 3T Day B incluía
`("padrao", "biceps", 2)`. O CSP retornou INFEASIBLE em 5/5 runs porque
H-T1 (`H-T1. Mesma família refinada não repete`) é hard intra-treino e
todos os 6 exercícios de `biceps` são `variacao_de="Rosca bíceps"`.

O motor antigo aceita biceps(2) no mesmo treino — `relaxar_familia=True`
permite repetir família intra-treino quando inviável.

**Divergência clínica**: o CSP é mais conservador que o antigo aqui.
Soluções possíveis (fora do escopo da Frente E.0):

- (a) Cadastrar `Rosca martelo`, `Rosca direta` etc com `variacao_de`
  diferentes (decisão clínica — são variações da mesma família?).
- (b) Mudar H-T1 de hard intra-treino pra soft (com peso alto). Bate
  com a tese declarativa de não preservar greedy.
- (c) Aceitar como NO-OP: ABC clássico não precisa de bi(2); usar
  `bracos(2)` que mistura bi+tri.

**Decisão prática (não-bloqueante)**: no harness, Day B usa
`("subregiao", "bracos", 2)` em vez de `("padrao", "biceps", 2)`.
Mantém a intenção clínica (pull+arms no mesmo dia) e gera comparação
útil. Achado deve voltar quando Frente E.1 escolher caminho — provável
ponto de discussão na própria E.1.

### 2. CSP é ~150x mais lento que o antigo (pipeline completo)

Faixa observada (smoke N=5):
- Full Body 2T: CSP 1478ms vs Antigo 10ms (~150x)
- upper(3)×2T: CSP ~150ms vs Antigo ~1ms (~150x)
- perna_ant+post: CSP ~110ms vs Antigo ~1ms (~110x)

Aceitável: hobby app sem pressão de tempo. P95 do Full Body deu 2044ms;
ainda longe da percepção de "lento" pro usuário (~5s seria limite). UI
percebida fica fine.

### 3. `evitar_agonistas=True` (default) + `relaxar_familia=True` (default)

São os defaults do harness pra refletir a UI default do app. Mudar isso
no harness sem mudar a UI distorce a comparação. Configurável via
edição manual do dataclass se Bernardo quiser explorar.

### 4. Métrica "Overlap R-1" usa pares de rotinas CONSECUTIVAS, não R-1
real do toggle UI

A métrica do harness assume "rotina seguinte" = "próxima iteração do
loop". O toggle UI "Usar histórico R-1" do app é diferente — passa
explicitamente `historico_r1=` pra `gerar_multiplos_treinos` ou
`historico_r1_por_treino=` (CSP). Como o harness NÃO usa essa flag
(default OFF), a métrica overlap mede VARIEDADE ENTRE GERAÇÕES
INDEPENDENTES — não cobertura ao longo de uma série planejada. Isso é
o esperado pra E.0 ("variedade INTER-rotina").

Pode ser estendido em Frente E.2 (se existir) ou ad-hoc passando o
resultado da rodada N pra rodada N+1 como histórico — fora do escopo
desta frente.

## Resultado da validação

### Gate de fechamento

| Métrica | Resultado |
|---|---|
| Script roda fim-a-fim N=5 + N=100 | ✓ |
| Relatório markdown gerado | ✓ `docs/refatoracao/relatorios/E0_2026-05-24.md` |
| 4 configs cobertas | ✓ |
| 1 perfil default; matriz opcional via flag | ✓ |
| Pytest preservado | ✓ **285 passed, 1 skipped** (mesmo baseline pós-Fatia 4.E cargas) |
| Harness 16/16 OK preservado | ✓ (NO-OPs informativos: 4.1=14.44%, 2.3=0.00%) |
| Motores intocados | ✓ |

### Run completo N=100 — sumário

| Config | CSP viáveis | Antigo viáveis | CSP médio (p95) | Antigo médio (p95) | Overlap R-1 CSP | Overlap R-1 Antigo |
|---|---|---|---|---|---|---|
| Full Body 2T | 100/100 | 100/100 | 1873ms (3084) | 10ms (13) | 18.0% | 20.7% |
| ABC 3T | 100/100 | 100/100 | 4857ms (6071) | 5ms (6) | 34.3% | 27.6% |
| upper(3)×2T | 100/100 | 100/100 | 146ms (158) | 1ms (1) | 9.9% | 19.7% |
| perna_ant+post | 100/100 | 100/100 | 101ms (125) | 1ms (1) | 17.7% | 27.6% |

Viabilidade: 100% em todas as 8 combinações (motor × config). Variedade
INTRA-config: 100/100 distintas em todas, ambos motores (banco ar
suficiente + softmax CSP / cycling antigo dão variedade plena).

### Achados clínicos comparativos (resumo — detalhe no relatório)

**Onde o CSP ganha:**

1. **H-R1 costas em Full Body 2T**: antigo VIOLA em 15% das rotinas
   (não cobre 1 puxada composta + 1 remada composta cross-treino).
   CSP zera. Caso clínico real, cobertura cross-treino é exatamente o
   que H-R1 do CSP modela.
2. **Overlap R-1 menor**: CSP < Antigo em 3 das 4 configs
   (Full Body, upper×2T, perna). Rotinas consecutivas têm menos
   repetição. Em upper×2T: 9.9% CSP vs 19.7% Antigo (~2x menos).
3. **Cycling em upper(3)×2T** (caso Bresenham, Seção 8.15.14): CSP
   distribui TODOS os padrões em T1 e T2 (~50/50). Antigo zera
   alguns padrões nos N=100 (ex: biceps/triceps sem nenhum slot —
   nunca caem em upper hierarquia do antigo).

**Onde o antigo ganha:**

1. **Âncoras obrigatórias em ABC 3T**: CSP **deixa de incluir
   ombro_composto em 100% das rotinas** (Day A `ombro(2)` cicla 100%
   pra posterior_ombro) e **biceps em 100%** (Day B `bracos(2)` cicla
   2x triceps). Antigo aplica `ANCORAS_POR_SUBREGIAO` via
   `_decompor_demanda_subregiao` (Seção 8.15.16) e força padrão
   obrigatório. **O CSP NÃO modela âncoras de subregião** — quando
   demanda é nível subregião, cycle livre pelos padrões. Isso é uma
   pendência declarativa que vai aparecer na Frente E.1.
2. **`hinge` violada 16% no CSP em ABC** (Day C `perna_posterior(2)`)
   pelo mesmo motivo de cima — sem âncora obrigatória de subregião.
3. **Distribuição tier**: CSP gera mais Intermediário/Acessório que
   Antigo em costas/peito/perna_anterior. Em Full Body costas: CSP
   51% Principal vs 75% Antigo. O peso_aderencia=0 (perfil media)
   permite ao softmax distribuir; perfil "alta" subiria. Não é viés
   patológico — é uma escolha do default. Vai aparecer no toggle
   `--matriz` quando rodar.

**Tempos:**

- CSP ~150-200x mais lento que antigo no pipeline completo. Aceitável
  pra hobby app: Full Body 1.9s médio (p95 3.1s) ainda dentro da
  percepção UI ("aguardar gera"). **ABC 3T tem p95 6.1s — primeiro
  caso na faixa de "lento" pra usuário**. Pode justificar otimização
  pós-E.1 (Bloco 4).

## Achados a discutir antes da Frente E.1

1. **Caminho de migração da Frente E.1** (decisão pendente do roadmap):
   - Clean break (alinhado norte.md Seção 5 "sem usuários = sem
     retrocompat") — remove motor antigo da rota `/gerar` direto;
     branch git preserva o motor antigo.
   - Flag de transição (curto prazo) — `?motor=legacy` ou checkbox UI
     durante validação clínica.
   Decisão de Bernardo após ler o relatório E.0.

2. **Bíceps família única** (achado #1 deste log) — H-T1 hard
   intra-treino do CSP é mais conservador que o antigo (que aceita
   repetir família intra-treino quando inviável). Discussão pra E.1:
   manter H-T1 hard (clinicamente correto — variações de rosca são
   "mesmo movimento") ou relaxar pra soft?

3. **Âncoras de subregião não modeladas no CSP** (achado mais
   importante do N=100). O CSP recebe demanda `("subregiao", "ombro", 2)`
   e cicla pelos padrões da subregião uniformemente; não respeita
   `ANCORAS_POR_SUBREGIAO[ombro] = [composto obrigatorio, isolado,
   posterior]`. Resultado em ABC 3T: 100% das rotinas sem ombro_composto
   — clinicamente errado. **Isso provavelmente bloqueia a Frente E.1
   sem ajuste prévio**: adicionar constraint H-A1 (âncoras obrigatórias
   por subregião) ao catálogo + ao motor CSP. Pode ser uma micro-frente
   pré-E.1, ou parte da E.1 mesmo.

4. **Lentidão do CSP em ABC 3T** — 6s p95. Não bloqueia uso real mas
   sugere otimização pós-E.1.

## Achados a discutir antes da Frente E.1

1. **Caminho de migração da Frente E.1** (decisão pendente do roadmap):
   - Clean break (alinhado norte.md Seção 5 "sem usuários = sem
     retrocompat") — remove motor antigo da rota `/gerar` direto;
     branch git preserva o motor antigo.
   - Flag de transição (curto prazo) — `?motor=legacy` ou checkbox UI
     durante validação clínica.
   Decisão de Bernardo após ler o relatório E.0.

2. **Bíceps família única** (achado #1 deste log) — provável discussão
   ao iniciar Frente E.1.

3. **Lentidão do CSP** — não bloqueia uso real (sub-2s p95). Pode virar
   item de refinamento pós-E.1 se UI sentir.

## Próximos passos

- **Frente E.1 desbloqueada** — substituir `/gerar` pelo motor CSP.
  Bloco 3 do roadmap. Bernardo lê relatório, decide clean break vs flag.
- **Refinamentos pós-E.1** (Bloco 4) — S-B2/S-B3 (carga implícita,
  fadiga prévia), captura de rationale no CSP, restantes do vetor de
  perfil (Centralidade Compostos, Densidade Pareamento).
