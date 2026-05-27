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
- Dado: `familia_estrita` → **operacionalmente `variacao_de`** (predicado `cand.variacao_de == outro.variacao_de` com ambos não-vazios, [gerador_treino.py:2158](../../gerador_treino.py#L2158)). Pai+filho NÃO bloqueado intra (decisão histórica preservada na Fatia 2 P2).

**H-T2. Variante pontual não atravessa famílias na mesma subregião**
- Origem: Etapa 6 Fase 3, já existe
- Dado: `variante_pontual` (boolean)

**H-T3. Lateralidade contextual em costas**
- Origem: Etapa 6 Fase 3, já existe
- Dado: `lateralidade` → **operacionalmente coluna `unilateral`** (valores `bilateral`/`unilateral`). Subregiões hard via `SUBREGIOES_LATERALIDADE_HARD = frozenset({"costas"})` em [pesos_proximidade.py:44](../../pesos_proximidade.py#L44) (fonte canônica única entre gerador antigo e CSP).

**H-T4. Vaga única na subregião ⇒ exercício composto/principal**
- Origem: Conceito 7
- Dado: `tier` (curado manualmente, Fatia 2 P1)
- Justificativa clínica: *"Se for pra deixar 1 exercício de coxa, esse único quase nunca seria Cadeira Extensora."*
- **Graceful degradation** (Fatia 2 P2): se o pool da subregião for 100% Acessório (caso `core_isometrico` / `core_dinamico` pós-curadoria, e `perna_posterior` no nível 1), H-T4 pula a constraint em vez de inviabilizar. Resultado marca `h_t4_aplicado_efetivamente=False` pra UI sinalizar ao usuário.

### Escopo ROTINA (across treinos)

**H-R1. Cobertura de eixos via compostos em subregiões com ≥2 slots**
- Origem: Conceito 5, generalizado por Bernardo em 2026-05-21
- Regra: se ≥2 slots de uma subregião na rotina, exigir cobertura dos eixos de movimento via **exercícios compostos** (isolados não contam):
  - Costas: ≥1 vertical composto + ≥1 horizontal composto
  - Peito: ≥1 horizontal composto se ≥2 slots
  - Perna anterior: ≥1 bilateral composto + ≥1 unilateral composto se ≥2 slots
- Princípio geral: cobertura de variedade só "conta" quando o exercício é composto. Isolados são extras.
- Dado: `padrao`, `unilateral`, `purpose` — **"composto" = `purpose == "compound"`** (decisão fechada na Fatia 2 P2). Centralidade clínica curada (`tier`) é ortogonal: Apoio (compound+Intermediário) cobre eixo horizontal, Hip Thrust (isolation+Principal) NÃO cobre como composto biomecânico.
- **Slot conta pra subregião X se**: demanda é `("subregiao", "X", qtd)` OU `("padrao", "Y", qtd)` onde Y mapeia 1:1 pra X via `PADRAO_PARA_SUBREGIAO`. Demandas com mapping 1:N (padrões CORE refinados) ou nivel `regiao` não contam — slot sem subregião determinística pré-solver.
- **Graceful degradation** (Fatia 2 P2): se um eixo não tem candidato no pool (caso real: nível 1 + perna_anterior, todos os afundos têm `cx > 2` → filtrados por H-P1), o eixo é pulado e marcado `degraded=True` no resultado. Resolve o conflito H-P1 vs H-R1 sem regredir pra soft. Decisão de Bernardo durante a Fatia 2 P2.
- **Importante**: solver não trata nenhuma subregião como "primeira". Ordem de processamento é justamente o que gera vieses (achado central do handoff). Todos os slots da rotina negociam simultaneamente.

**H-A0. Âncoras obrigatórias por REGIÃO decompõem demanda nível região**
- Origem: motor antigo (`ANCORAS_POR_REGIAO` em [gerador_treino.py:142-157](../../gerador_treino.py#L142-L157)) + auditoria clínica pós-Frente E.1 (2026-05-25) — `/gerar` no CSP entregou Full Body 2T com **zero exercícios de costas em 16 slots e zero squat em 6 slots de lower** quando UI mandou demanda nível região (caminho default do Full Body); ver `logs/micro_h_a0_ancoras_regiao.md` e `relatorios/E0_2026-05-25_pos_h_a0.md`. H-A1 só dispara em demanda nível subregião; demanda nível região passava sem âncora.
- Regra: quando a demanda é nível região (`("regiao", R, qtd)`), a região R tem entrada em `ANCORAS_POR_REGIAO`, e qtd ≥ 1: pra cada subregião com `obrigatoria=True` declarada nessa região, exigir ≥1 slot **daquele treino** com `ex.subregiao == sub_obrig`. Agregação **per-treino** (decisão 4.1 do handoff H-A0 — diferente da H-A1 que é cross-treino): semântica de "treino de upper" é "cobre upper NAQUELE treino", não "alguma hora da rotina".
- Dado: `ANCORAS_POR_REGIAO` (existe em `gerador_treino.py`, fonte canônica única entre motores), `subregiao` (existe no XLSX). Variável CSP nova: `sub_idx[s] = IntVar(0, len(subs_R)-1)` por slot de demanda região, canalizada via `assign` (mesma técnica de `grupo_func` e `tier_rank`).
- Exemplos atuais (regiões com âncoras obrigatórias):
  - `upper`: `peito` + `costas` + `ombro` obrigatórias (não-obrig nenhuma)
  - `lower`: `perna_anterior` + `perna_posterior` obrigatórias; `panturrilha` não-obrig
  - `core`: ambas (`core_dinamico` + `core_isometrico`) não-obrig → H-A0 não força nada
- **Banimento hard de subregiões não-âncora (decisão 4.3 / Caminho A)**: subregiões em `REGIAO_PARA_SUBREGIOES[R]` mas NÃO listadas em `ANCORAS_POR_REGIAO[R]` ficam BANIDAS hard dos slots dessa demanda região (ex: `bracos` banido em `("regiao","upper",N)`, `adutores` banido em `("regiao","lower",N)`). Implementação upstream: filtro do `pool_default_sem_travados` rejeita exercícios cuja `subregiao` não está em `ANCORAS_POR_REGIAO[R]`. **Importante**: rejeição é só dentro dos slots dessa demanda região. Outras demandas na rotina (ex: `("padrao", "biceps", 1)` em paralelo) continuam livres — usuário pode pedir braços explicitamente.
- **Interação com H-A1 via marker (decisão 4.2 / Caminho A)**: quando H-A0 obriga ≥1 slot de subregião X num treino, popula estrutura paralela `subregioes_obrigadas_ha0[(t_idx, R)] = set(subs_ativas)`. Bloco H-A1 lê essa estrutura e estende `slots_subregiao_explicita[sub]` com os `slot_ids` da demanda região correspondente — ativando H-A1 para padrões obrigatórios dessas subregiões (ex: peito ativa exigência de `empurrar_compostos`). **Apenas no caso normal** (vagas ≥ n_ativas) — em conflito de cardinalidade (vagas < n_ativas), nenhuma sub é garantida individualmente, marker não popula. `vagas_garantidas_por_sub` separado de `len(sids_lista)` no H-A1 pra detecção correta de conflito quando marker contribui.
- **Graceful degradation**:
  - Pool sem candidato: sub obrigatória sem nenhum exercício no pool dos slots daquele (treino, região) → constraint daquela sub PULADA, marcada `degraded=True` no resultado.
  - Conflito de cardinalidade (`vagas < n_obrigatórias com pool viável`, ex: `("regiao","upper",1)` com 3 obrigatórias): constraint colaborativa `sum(obrig_usada) >= vagas` força N distintas. Solver decide quais. Cada uma marcada `degraded=True` com motivo `conflito_cardinalidade`.
- **NÃO ativa em demanda nível subregião nem padrão**: aquelas são domínio de H-A1 (subregião) ou pedido explícito do usuário (padrão).
- **NÃO modela `PROPORCAO_COMPOSTOS = 0.6`** (decisão 4.6): cobertura de compostos vem via H-A1 marker — peito → `empurrar_compostos` (composto), ombro → `ombro_composto`, etc. Se empírico mostrar que não cobre suficiente, abre frente separada (provavelmente S-A1).
- **Resolve junto**: rotina Full Body 2T com zero costas / zero ombro / zero squat (achado 2026-05-25). Cobertura clínica per-treino garantida em `upper(3)×2T`, `lower(3)`, Full Body 2T (região).

**H-A1. Âncoras obrigatórias por subregião decompõem demanda nível subregião**
- Origem: motor antigo (`ANCORAS_POR_SUBREGIAO` em [gerador_treino.py:159-194](../../gerador_treino.py#L159-L194)) + achado da Frente E.0 (2026-05-24) — CSP não modela âncoras e viola padrão obrigatório em 100% das rotinas em casos como ABC Day A (`ombro_composto` violado 100%, `biceps` violado 100%; ver `relatorios/E0_2026-05-24.md` e `logs/frente_e0_harness_comparativo.md`).
- Regra: quando a demanda é nível subregião (`("subregiao", "X", qtd)`), a subregião X tem entrada em `ANCORAS_POR_SUBREGIAO`, e qtd ≥ 1: pra cada âncora com `obrigatoria=True` declarada nessa subregião, exigir ≥1 slot da rotina com `padrao == âncora.padrao`. Mantém comportamento clínico do antigo declarativamente — substitui a decomposição imperativa pré-solver (`_decompor_demanda_subregiao` + `_quotas_de_subregiao`).
- Dado: `padrao` (existe), `ANCORAS_POR_SUBREGIAO` (existe em `gerador_treino.py`) — fonte canônica única entre motores.
- Exemplos atuais (subregiões com âncoras obrigatórias):
  - `peito`: `empurrar_compostos` obrigatória
  - `costas`: `remadas` + `puxadas` obrigatórias
  - `ombro`: `ombro_composto` obrigatória
  - `perna_anterior`: `squat_bilateral` obrigatória
  - `perna_posterior`: `hinge` obrigatória
  - `panturrilha`: `flexao_plantar` obrigatória
  - `bracos`: `biceps` + `triceps` obrigatórias
- **Causa raiz do bug observado** (Frente E.0): sem H-A1, o solver decide entre padrões da subregião por interação livre com S-B1 (evitar agonistas). Em treinos push-pesados, `("subregiao", "ombro", 2)` cai 100% em `posterior_ombro` (único padrão pull da subregião) porque minimiza penalty global de pareamento.
- **Interação com demanda nível padrão**: H-A1 NÃO ativa quando a demanda é `("padrao", "Y", qtd)` direta — usuário explicitamente pediu o padrão Y; respeitar a escolha.
- **Interação com cross-treino**: quando uma subregião soma ≥1 slot em treinos distintos, a obrigatoriedade vale na rotina (≥1 slot global), não por treino. Espelha `_distribuir_quotas_entre_treinos` do antigo (a distribuição fina entre treinos pode ser refinada via soft posterior, fora do escopo H-A1).
- **Graceful degradation**: se o pool da subregião não tem candidato pra alguma âncora obrigatória após H-P1 (filtro de nível), a constraint daquela âncora é pulada e marcada `degraded=True` no resultado (mesmo padrão de H-R1 e H-T4 da Fatia 2 P2).
- **Distribuição entre âncoras não-obrigatórias** (pesos 1/2/3 do antigo): fora do escopo H-A1. Quando importar, vira soft S-A1 separado (peso no objetivo proporcional ao peso da âncora).
- **Resolve junto**: bug do `biceps` em ABC Day B (`bracos(2)` cai 0 biceps + 2 triceps), bug do `ombro_composto` em ABC Day A (0 nas 100 rotinas), bug do `hinge` 16% em ABC Day C.

### Escopo PERFIL DE ALUNO

**H-P1. Nível técnico filtra pool por `complexidade`**
- Origem: dimensão Nível técnico do vetor (sessão 2026-05-21)
- Dado: `complexidade` (existe), `nivel` no perfil do aluno
- Regra: exercício com `complexidade > teto_do_nível` não entra no pool antes do solver começar.

**H-P2. Tier Principal + Centralidade Alta + Aderência Alta ⇒ bloco solo**
- Origem: Conceito 12 + decisão da sessão 2026-05-21 sobre Terra (Fernanda vs turma 7h)
- Substitui: o `bloco_solo` manual atual no banco. Vira constraint derivada da intersecção tier do exercício × vetor do aluno.
- Dado: `tier`, vetor do aluno

### Escopo BLOCO (par/trio dentro de superset)

**H-cargas. Soma de carga par-a-par dentro do bloco ≤ threshold por dimensão**
- Origem: motor antigo (Etapa 4 / HIB2), portado pra Fatia 4.E cargas (2026-05-24)
- Dado: `cargas_config: dict[str, int]` no perfil de geração (`{"grip", "lombar", "core"}` → threshold int), colunas `carga_grip`/`carga_lombar`/`demanda_core` no XLSX
- Regra: pra cada par (a,b) no mesmo bloco e cada dim d com thr[d]>0: bloqueia se `carga_d(a)>=1 AND carga_d(b)>=1 AND (carga_d(a)+carga_d(b))>=thr[d]`. Não é cumulativa por bloco (decisão clínica fechada).
- **Graceful degradation por bloco**: quando inviável, motor "desliga" filtro só pro bloco afetado (BoolVar `cargas_off_b[b]`, penalizado no objetivo com peso 1000 default). Emite aviso `relaxado_carga` por par violador no bloco. Réplica fiel do antigo (~`gerador_treino.py:1469-1516`).
- **Travados ENTRAM nos pares** (divergência intencional do antigo). Travado tem pool_slot de 1 elemento (Fatia 4.D), então par travado+non-travado violador força non-travado a mudar — "travado nunca some" preservado naturalmente.
- Dado adicional: `peso_cargas_off: int = 1000` (parametrizável; alto pra desligar só quando inviável).

### Escopo restrições físicas/dor (pendente)

**H-X. Restrições físicas/dor sobre pool**
- **STATUS**: pendente. Discutir em sessão futura.
- Direcionamento: filtros hard sobre pool por aluno (lista de exercícios proibidos ou padrões a evitar por causa de lesão).

---

## Seção 2 — Soft constraints

### Escopo SUBREGIÃO (distribuição entre padrões âncora)

**S-A1. Distribuição entre âncoras não-obrigatórias (com guarda anti-repetição)**
- Origem: handoff `handoff_2026-05-25_s_a1.md` + sondagem 40 seeds 2026-05-25 (`tools/sondar_sa1_baseline.py`) — sem S-A1, `ombro(2)` no CSP saía 100% (composto + posterior_ombro) — ZERO `ombro_isolado` (vs antigo 100% composto + isolado); `perna_posterior(2)` saía 100% (hinge + abduction) — ZERO `knee_flexion` (vs antigo ~48% knee). Causa: H-A0/H-A1 ignoram os pesos curados 3/2/1 da `ANCORAS_POR_SUBREGIAO`; S-B1 (peso 10) domina a decisão entre padrões não-obrig.
- Função: consumir o `peso` curado em `ANCORAS_POR_SUBREGIAO` que H-A0/H-A1 ignoram, e impedir que o solver escape pela repetição da própria obrigatória. **Dois componentes complementares**:
  - **v1 (linear sobre pesos não-obrig)**: pra cada slot S × candidato C cujo `padrao` está em `nao_obrigatorias[sub]`, adiciona penalty `(peso_max_nao_obrig - peso_da_ancora) * peso_sa1 * assign[S,C]`. Solver minimiza → vaga sobrando prefere padrão de peso alto (ex: ombro_isolado peso 2 > posterior_ombro peso 1).
  - **v2 (penalty por padrão repetido na mesma demanda)**: pra cada par (s_i, s_j) na MESMA demanda original, BoolVar `same_padrao` reifica "padrão escolhido em s_i == padrão escolhido em s_j"; penalty `peso_sa1_repet * same_padrao`. Fecha buraco arquitetural do v1 (sem v2, em `perna_posterior(2)` o solver escapava 78% das vezes pra `hinge+hinge` — mesmo custo S-B1 que `hinge+knee_flexion`, S-A1=0 ambos).
- Ativação (decisões fechadas no handoff):
  - **v1 em demanda subregião explícita**: condicionado a `qtd > n_obrig` (isola trade-off com S-B1, decisão 4.1).
  - **v1 em demanda região**: ativa SEMPRE (decisão 5.2 / b — "mais pronto"); penalty atua via `assign`, slot obrigatório anula custo automaticamente.
  - **v2 em qualquer demanda**: par dentro da mesma demanda original. Cross-demanda no mesmo treino NÃO penaliza (decisão de escopo: 2 demandas distintas com mesmo padrão é decisão do user).
- Dado: `peso` curado em `ANCORAS_POR_SUBREGIAO` (existe) + `obrigatoria=True/False`. **NÃO mexer na tabela** (decisão 4.5).
- Forma do penalty (decisão 5.1 do handoff): linear `(peso_max - peso_ancora) * peso_sa1`. Quadrática descartada — entrega resultado clínico idêntico na config atual de pesos.
- **Calibração** (2026-05-25, iterativa com Bernardo):
  - `peso_sa1 = 12` (componente v1). Pesos curados 2 (não-obrig central) ficam em vantagem sobre pesos curados 1 (não-obrig periférica) por 12 unidades de custo.
  - `peso_sa1_repet = 10` (componente v2). Zera hinge+hinge em `perna_posterior(2)` e composto+composto em `peito(2)`.
  - **Ajuste estrutural acompanhante**: peso curado de `abduction` em `perna_posterior` subiu de 1 pra 2 (igualou knee_flexion) — refletindo equivalência clínica das 2 não-obrig (ambas "segunda escolha" depois do hinge obrigatório). Sem essa mudança, a distribuição em `perna_posterior(2)` ficava 100% de uma combinação (`hinge+knee` ou `hinge+abd`); com pesos iguais, softmax distribui ~50/50 (sondagem n=40: 62/38 a 50/50 com folga de softmax).
  - **S-B1 desligada intra-sub** (mudança acompanhante na S-B1): preserva sua semântica cross-sub. Razão clínica: em demanda sub explícita, user pediu a categoria — agonistas dentro dela são esperados.
- **Resolve junto** (sondagem 40 seeds com peso_sa1=12 + peso_sa1_repet=10 + S-B1 não-intra-sub + abd peso=2):
  - `ombro(2)`: 100% (composto + isolado) — pré-S-A1 era 0% iso.
  - `perna_posterior(2)`: **62% hinge+knee / 38% hinge+abd** — distribuição equilibrada (alvo clínico Bernardo).
  - `peito(2)`: 100% (composto + isolado) — pré-S-A1 era 55%.
  - `perna_anterior(2)`: 100% (bilateral + unilateral) — preservado.
  - Demanda região `lower(4)`: hinge+hinge **0%** (era 35% sem S-A1).
- **Achados bonus registrados na sessão** (não resolvidos por S-A1; frentes futuras):
  - Cobertura per-treino do H-A1 marker pós-H-A0: rotina Filipe Santos 2026-05-25 saiu com T1 sem `squat_bilateral` (apenas `squat_unilateral` = Recuo). H-A1 marker é cross-treino — garante ≥1 squat_bilateral na rotina inteira, não por treino. Bernardo aceitou registrar como pendência separada.
  - Variedade INTRA-subregião (3+ vagas mesma sub): se sub tem só 1 não-obrigatória e ≥3 vagas, v2 zera repetição entre pares, mas não há mais opção pra cumprir. Caso degenerado, sem impacto observado.

### Escopo BLOCO (par/trio dentro de superset)

**S-B1. Distância funcional entre exercícios do par**
- Origem: Conceito 10 + matriz P×Sub atual
- Função: preferir grupos musculares distantes ou antagonistas no mesmo bloco. Penalidade cresce com proximidade muscular.
- Dado: `padrao`, `regiao`, mapa de antagonismo
- Modulador: Densidade de Pareamento (inversão — alta = neutro, baixa = exige distância)
- **Escopo (decisão 2026-05-25)**: S-B1 NÃO atua em pares dentro da MESMA demanda subregião explícita (`("subregiao", X, qtd)`). User pediu a sub explicitamente — exercícios da mesma categoria muscular são esperados/aceitáveis. Atua sim cross-sub no mesmo bloco (peito+ombro = ambos push em demanda região). Razão clínica: em `perna_posterior(2)`, par `hinge+knee_flexion` é válido apesar de ambos serem hamstring; bloquear seria over-restritivo e empurrava solver pra `hinge+abduction` em 100% (eliminando variedade).

**S-B2. Balanço de carga implícita acumulada**
- Origem: Conceito 6
- Função: soma de carga em core, lombar, grip e neural dentro do bloco. Penalidade cresce com a soma. **Complementar à H-cargas** (hard par-a-par): S-B2 captura a fadiga cumulativa por bloco em escala soft (modulável por perfil), enquanto H-cargas é gate binário par-a-par.
- Dado: `demanda_core` (existe), `carga_grip` (existe), `carga_lombar` (existe), demanda neural derivada (`tier` + perfil). **Nomenclatura final**: `carga_grip` / `carga_lombar` no XLSX (não `demanda_grip` / `demanda_lombar` — esse rótulo aparecia em rascunhos pré-Fatia 4.E; foi consolidado com `carga_*` na hora de portar H-cargas pro CSP).
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

**S-E1. Proximidade biomecânica cross-treino**
- Origem: Achado 2 da auditoria 2026-05-26; spec consolidada na frente S-E1 (2026-05-28).
- Função: penaliza pares de slots em treinos diferentes mesma-subregião com match exato em `pegada` / `plano_corporal` / `equipamento_grupo`. Recupera o `_score_inter` do gerador antigo (`gerador_treino._score_proximidade`, contexto `"inter"`) com modelagem declarativa CSP, sem migrar `pesos_proximidade.py` (CSP fica independente).
- Dado: `pegada`, `plano_corporal`, `equipamento_grupo` (cadastrados desde Fase 4 — Seção 1 da `arquivo/era_v4_greedy_incremental/dimensoes_proximidade.md`, REFERÊNCIA VIVA).
- Modelagem (par-a-par cross-slot, escopo "mesma subregião" via reificação):
  - Pra cada par (s1, s2) com t_idx(s1) < t_idx(s2) e `subs_possiveis(s1) ∩ subs_possiveis(s2) ≠ ∅`: cria `same_sub = (subregiao_idx[s1] == subregiao_idx[s2])` UMA vez.
  - Pra cada dim X com `peso_se1_X > 0`: cria `same_X = (X_idx[s1] == X_idx[s2])`, e `viol_X >= peso_se1_X` quando `AND(same_sub, same_X)`.
  - **Sentinela por slot** pra dim ausente: ex sem `X` cadastrada recebe `code = BASE_VAZIA + sid` (único por slot). Dois slots vazios em sids distintos recebem codes diferentes → `same_X` reifica false naturalmente, sem precisar BoolVar de validade. Honra `cand.X and outro.X and cand.X == outro.X` do antigo + `_SUBREGIOES_X_NA` da Seção 7 dimensoes_proximidade automaticamente (banco cadastra dim vazia em subs N/A).
- Pesos calibrados (2026-05-28 via sondagem N=10 Full Body 2T `aderencia=alta`):
  - `peso_se1_pegada = 10` (ALTO)
  - `peso_se1_plano = 10` (ALTO)
  - `peso_se1_eq = 2` (BAIXO tiebreaker — Seção 1.5 dimensoes_proximidade)
  - Proporção 5:1 ALTO:BAIXO preserva semântica clínica. Pegada NÃO usa matriz 4×4 (D2.1 fechou em constante por dim, 2026-05-09).
- Escopo "mesma subregião" preservado (Seção 1.5): halteres vs barra IMPORTA em supino (mesmo peito), NÃO importa em passada (perna_anterior unilateral — pegada/plano N/A via sentinela). Decisão clínica fechada na Etapa 6, não reabrir.
- Default ON sempre, sem toggle UI (igual S-R1/S-B5/S-A1). Skip estrutural em rotinas com <2 treinos. NÃO ativa em `treino_regerar` (1 treino isolado, sem cross-treino possível — mesmo critério da S-R1).
- **Resolve junto** (sondagem Full Body 2T região + aderência alta): pct_pegada_repetida_cross_treino 100% → 0%; pct_plano_repetido 100% → 0%; pct_eq_repetido 40% → 0%; pct_supinos_halteres_repetido 10% → 0%. Smoke E2E confirma equipamentos distintos cross-treino em peito.
- **Não cobre**: INTRA-treino mesma-subregião (esse é escopo de S-T4, frente separada). Família estrita / lateralidade / variante_pontual cross-treino seguem cobertas por H-T1/T2/T3 + `familias_proibidas` da Frente E.1.

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

| Coluna do XLSX | Conceito do catálogo | Consumido por |
|---|---|---|
| `variacao_de` | `familia_estrita` (conceito) | H-T1, futuras S-R3/S-H1 família |
| `variante_pontual` | `variante_pontual` | H-T2 |
| `unilateral` (valores `bilateral`/`unilateral`) | `lateralidade` | H-T3, H-R1 (perna_anterior) |
| `pegada`, `plano_corporal`, `equipamento_grupo` | mesmos nomes | S-B1, S-T4, S-R1 (futuras) |
| `padrao`, `regiao`, `subregiao`, `complexidade` | hierarquia + filtros | H-P1, H-R1, todas as demandas |
| `demanda_core`, `carga_grip`, `carga_lombar` | dims de carga acumulada | H-cargas (Fatia 4.E cargas), S-B2 (futura) |
| `purpose` (`compound`/`isolation`/`stability`/`explosive`) | "composto" do H-R1 | H-R1 |
| `tier` (Principal/Intermediário/Acessório) | `tier` — curado na Fatia 2 P1 | H-T4, S-T1 (e futuras H-P2/S-T2/S-T3/S-R3/S-H1) |
| `ativo` (boolean) | filtro operacional | descarte pré-solver |

### Colunas a cadastrar (derivadas das constraints)

- **`estabilidade_externa`** — máquina / livre. Necessária pra S-B3, S-T2.

*Nota*: `carga_lombar` (originalmente listada como "a cadastrar" sob o
nome `demanda_lombar`) já existe no XLSX e está consumida pela H-cargas
(Fatia 4.E cargas, 2026-05-24). Mantida cobertura pra futura S-B2
sem cadastro extra.

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

*Última atualização: 2026-05-25 (Micro-frente H-A0 — âncoras obrigatórias
por região per-treino + banimento upstream de subs não-âncora + marker
para H-A1; fecha bug clínico de demanda nível região zerando costas e
squat em rotinas Full Body via UI — auditoria 2026-05-25).*

*2026-05-24 (Fatia 4.E cargas — H-cargas adicionada na Seção 1 escopo
BLOCO; nomenclatura de colunas consolidada com prefixo `carga_*` na
Seção 4; nota explicativa sobre `carga_lombar` já cadastrado).*

*2026-05-23 (Fatia 2 Parte 2 — Seções 1 e 4 ganharam correspondência conceito↔coluna pra H-T1, H-T3, H-T4, H-R1, e a graceful degradation de H-T4 e H-R1 foi documentada como decisão clínica fechada).*
