# Regras do auditor clínico — base de conhecimento (Fase 1)

> **Status**: rascunho inicial — Fase 1 do plano "agente auditor clínico"
> discutido em 2026-05-25. Bernardo valida + corrige + completa antes da
> Fase 2 (protótipo do agente).
>
> **Propósito**: documento operacional com regras VERIFICÁVEIS sobre uma
> rotina gerada, formatadas pra serem aplicadas por um agente auditor
> (ou pelo próprio Claude Code antes de fechar uma frente). Diferente
> do `principios_clinicos.md`, que é documento de elicitação histórica
> com conceitos abstratos — aqui o foco é "input rotina → output
> achados".

---

## Fontes deste doc

Cada regra cita de onde vem (pra rastreabilidade clínica):

1. **`principios_clinicos.md`** — Conceitos 1-12 da entrevista de 2026-05-19/21.
2. **`auditorias/*.md`** — achados de leitura clínica humana (1ª auditoria: `auditorias/2026-05-25_pos_h_a0.md`).
3. **Tabelas curadas** em `gerador_treino.py`:
   - `ANCORAS_POR_REGIAO` (peito/costas/ombro em upper; perna_anterior/perna_posterior em lower).
   - `ANCORAS_POR_SUBREGIAO` (empurrar_compostos em peito; remadas+puxadas em costas; etc).
   - `PADRAO_PARA_SUBREGIAO` (mapeamento estrutural).
   - `GRUPO_MUSCULAR_PADRAO` (mapa atual, grosseiro — ver R-BAL-2).
4. **`catalogo_constraints.md`** — constraints declaradas no motor CSP (H-* hard, S-* soft).

---

## Formato das regras

Cada regra tem:

- **ID** `R-<categoria>-<n>`
- **Categoria**: cobertura / ordem / balanceamento / variedade / pareamento / proibição
- **Severidade**: crítico (treino clinicamente incompleto) / alto (vaza qualidade visível) / médio (sub-ótimo mas tolerável) / aceitável
- **Predicate**: o que verificar (pseudocódigo legível)
- **Fonte**: rastreabilidade
- **Status no motor**: já cobre (qual constraint), parcial, ainda não

---

## Regras de COBERTURA

### R-COB-1 — Âncoras de região cobertas
**Severidade**: crítico
**Predicate**: para cada demanda `("regiao", R, N)` com `R ∈ ANCORAS_POR_REGIAO`, cada subregião com `obrigatoria=True` em `ANCORAS_POR_REGIAO[R]` deve aparecer em ≥1 slot daquele treino.
**Fonte**: H-A0 (Bloco 2.5-bis do roadmap CSP), achado original 2026-05-25.
**Status no motor**: coberto por H-A0 (per-treino, decisão 4.1 do handoff).

### R-COB-2 — Âncoras de subregião cobertas
**Severidade**: crítico
**Predicate**: para cada slot de subregião X com `X ∈ ANCORAS_POR_SUBREGIAO`, cada padrão com `obrigatoria=True` em `ANCORAS_POR_SUBREGIAO[X]` deve aparecer em ≥1 slot daquele treino.
**Fonte**: H-A1.
**Status no motor**: coberto por H-A1 + marker via H-A0. **⚠️ Achado A da auditoria 2026-05-25 sugere bug em propagação do marker** — peito sem composto em T1 do Filipe.

### R-COB-3 — Vaga única exige composto/principal
**Severidade**: alto
**Predicate**: se uma subregião tem **exatamente 1 slot** em uma rotina inteira (não treino), esse slot deve ser composto / `purpose ∈ {compound, explosive}` / tier=Principal.
**Fonte**: Conceito 7 (`principios_clinicos.md`). Caso Cadeira Extensora como único de coxa = ❌.
**Status no motor**: NÃO COBERTO. Provavelmente cabe em frente nova do Bloco 4 ou variação de H-A1.

### R-COB-4 — Vagas não-obrigatórias respeitam peso curado
**Severidade**: alto
**Predicate**: para cada subregião com vagas > n_obrigatórias, vagas extras preferem padrões com peso maior em `ANCORAS_POR_SUBREGIAO[X]` (3 > 2 > 1).
**Fonte**: Conceito 4 (frequência típica), Achado B da auditoria (ombro_isolado zerado em ombro(2); knee_flexion zerado em perna_posterior(2)).
**Status no motor**: NÃO COBERTO. **Frente S-A1 em andamento.**

### R-COB-5 — Panturrilha rara em lower compartilhado
**Severidade**: médio
**Predicate**: em rotina com ≥2 treinos contendo demanda lower, panturrilha aparece em **≤1 treino**, idealmente 0.
**Fonte**: Achado C da auditoria, fala clínica do Bernardo ("raramente prescrevo panturrilha").
**Status no motor**: NÃO COBERTO. **Decisão pendente** — Bernardo escolhe entre (a) remover panturrilha de `ANCORAS_POR_REGIAO['lower']` (hard ban exceto demanda explícita), (b) constraint cross-treino soft "panturrilha ≤1×", (c) deixar S-A1 calibrar peso.

### R-COB-6 — Cobertura push/pull no upper
**Severidade**: alto
**Predicate**: em treino com demanda upper(N≥2), exercícios de `push` e `pull` devem aparecer em ambas as direções. Não 3 push + 0 pull nem o contrário.
**Fonte**: Conceito 9 (distribuição multi-eixo), achado original 2026-05-25 (zero costas em upper).
**Status no motor**: parcialmente coberto via R-COB-1 (peito+costas+ombro obrigatórios em upper). Reforço explícito desejável.

---

## Regras de ORDEM

### R-ORD-1 — Tier-order dentro do treino
**Severidade**: alto
**Predicate**: dentro de cada treino, blocos com exercícios `Principal` aparecem antes de blocos com `Intermediário` ou `Acessório`. Equivalente: `tier_rank(bloco[i]) ≥ tier_rank(bloco[i+1])` (tier alto antes).
**Fonte**: Conceito 1 (`principios_clinicos.md`). **3 de 3 rotinas da entrevista de 2026-05-19 tiveram esse erro.**
**Status no motor**: coberto por S-T1 (tier-order soft por bloco no treino).

### R-ORD-2 — Composto pesado abre o treino
**Severidade**: alto
**Predicate**: bloco A do treino contém ≥1 exercício composto (purpose=compound ou explosive). Não abrir com 2 isolados leves (fad≤2 + cpx≤2).
**Fonte**: Conceito 1 + 12 (escolha+arranjo inseparáveis). Caso T2 do Teste CSP id=1 abriu com Side Clams + Ponte Uni Caixa (fad 1+1).
**Status no motor**: parcialmente coberto via S-T1 + Aderência ao Tier. Reforço explícito desejável (talvez constraint hard "bloco A tem ≥1 composto").

### R-ORD-3 — Carryover de fadiga peso-livre → máquina
**Severidade**: médio
**Predicate**: dentro do treino, exercícios de peso-livre alto-impacto vêm antes de máquina (Conceito 2). Ex: Pullover ANTES de Barra Fixa Livre = ❌; Pullover ANTES de Puxada na máquina = ✓.
**Fonte**: Conceito 2. Bernardo cita exemplo Pullover.
**Status no motor**: NÃO COBERTO. Exige coluna `estabilidade_externa` no XLSX que Bernardo decidiu não cadastrar agora — fica em standby.

---

## Regras de BALANCEAMENTO

### R-BAL-1 — Push/pull balanceado na rotina
**Severidade**: alto
**Predicate**: na rotina inteira, contagem de exercícios push ≈ pull dentro de ±20%. Em cada treino com upper(N≥3), push e pull aparecem ambos (sem zero).
**Fonte**: Conceito 9, achado original 2026-05-25.
**Status no motor**: parcialmente coberto via R-COB-1+R-COB-6.

### R-BAL-2 — Agonismo intra-bloco (gradual)
**Severidade**: médio
**Predicate**: pareamento de exercícios same-group dentro do mesmo bloco evita musculatura primária OU secundária compartilhada forte. Hoje S-B1 do motor é binário por padrão; achado E mostra que Hip Thrust (hinge, posterior chain) + Recuo (squat_unilateral, quad+glute) compartilham glute como secundária forte.
**Fonte**: Conceito 6 (balanço de carga), Achado E da auditoria.
**Status no motor**: coberto binariamente por S-B1. **Refinamento "mapa antagonismo gradual" no Bloco 4.**

### R-BAL-3 — Double demand em mesmo eixo de carga
**Severidade**: médio
**Predicate**: bloco de 2 exercícios evita double demand no mesmo eixo (core/lombar, grip, ombro estabilizador, neural). Ex: Remada Curvada + Smith = 2× core demand.
**Fonte**: Conceito 6. Coluna `demanda_lombar` já existe no XLSX (Bernardo confirmou); `estabilidade_externa` em standby.
**Status no motor**: NÃO COBERTO. **Frente S-B2 do Bloco 4 (destravada pós-confirmação de `demanda_lombar`).**

---

## Regras de VARIEDADE

### R-VAR-1 — Família repetida cross-treino dentro da rotina
**Severidade**: médio
**Predicate**: para cada par de treinos (T_i, T_j) na mesma rotina, `variacao_de(ex_em_T_i) ∩ variacao_de(ex_em_T_j) = ∅`. Exemplo de violação: Desenv. Halteres Sentado em T1 + Desenv. Halteres Uni. em T2 (mesma família).
**Fonte**: Conceito 9 + Achado F da auditoria.
**Status no motor**: NÃO COBERTO dentro da rotina nova (`familias_proibidas` só age cross-rotina via toggle histórico R-1). **Frente S-R3 do Bloco 4.**

### R-VAR-2 — Variedade multi-eixo em subregião com ≥2 slots
**Severidade**: médio
**Predicate**: subregião com 2+ slots na rotina inteira deve variar pelo menos 1 dos eixos: padrão, pegada, plano corporal, unilateralidade.
**Fonte**: Conceito 5 (diversidade no nível da subregião inteira, casos Rotina 1 vs Rotina 3 da entrevista 2026-05-19).
**Status no motor**: parcialmente coberto via H-A1 (forca padrões obrigatórios diferentes quando existem múltiplos).

### R-VAR-3 — Distribuição cross-treino multi-eixo
**Severidade**: médio
**Predicate**: grupos musculares que aparecem em múltiplos treinos da rotina devem variar tipo de movimento entre eles. Caso real: 2 desenvolvimentos de ombro em T1+T2 (idem família, idem padrão) = ❌.
**Fonte**: Conceito 9 refinado, Achado F.
**Status no motor**: subset de R-VAR-1. Coberto pela mesma frente S-R3.

---

## Regras de PROIBIÇÃO

### R-PRO-1 — Banimento hard de subregião não-âncora em demanda região
**Severidade**: crítico
**Predicate**: em slot de demanda `("regiao", R, N)`, subregiões em `REGIAO_PARA_SUBREGIOES[R]` mas NÃO em `ANCORAS_POR_REGIAO[R]` (ex: bracos em upper, adutores em lower) não aparecem.
**Fonte**: H-A0 decisão 4.3 (Caminho A). Decisão clínica explícita.
**Status no motor**: coberto por H-A0.

### R-PRO-2 — Restrições físicas/dor por aluno
**Severidade**: crítico
**Predicate**: nenhum exercício na rotina pertence à lista de proibições por lesão/dor do aluno.
**Fonte**: `principios_clinicos.md` "Pendências do perfil" — direcionamento.
**Status no motor**: NÃO COBERTO. **Frente H-X do Bloco 4.**

---

## Pendências de decisão clínica (perguntar Bernardo antes de codar)

- **R-COB-5 panturrilha** — escolher entre (a)/(b)/(c) descritas acima.
- **R-VAR-1 granularidade** — nome estrito (Desenv. Halteres Sentado ≠ Uni.) ou família via `variacao_de` (ambos = "Desenvolvimento de Halteres")? Sugestão: família, mais permissivo.
- **R-BAL-1 magnitude** — ±20% é tolerável ou queremos mais rígido?
- **R-ORD-2 hard ou soft** — bloco A com composto: hard constraint (inviabiliza) ou soft pesado (preferência forte mas relaxável)?

---

## Saída esperada do auditor

Por achado, dict com:

```json
{
  "id": "<sequencial>",
  "regra_violada": "R-COB-2",
  "severidade": "critico|alto|medio|aceitavel",
  "treino": 1,
  "bloco": "C",
  "exercicio": "Crucifixo Halteres",
  "descricao_humana": "T1: peito coberto só com Crucifixo Halteres (empurrar_isolados). Empurrar_compostos é âncora obrigatória de peito e não aparece em nenhum slot deste treino.",
  "causa_raiz_sugerida": "constraint H-A1[peito] possivelmente não ativada para t_idx=0 OU degraded silenciosamente — investigar resultado_csp['h_a1_aplicadas']",
  "frente_que_resolve": "investigação técnica antes do merge H-A0"
}
```

Achado pode ter `causa_raiz_sugerida` em branco se a violação é evidente mas a raiz não é técnica (ex: R-COB-5 panturrilha — não tem frente ainda).

---

## Como o auditor opera (proposta Fase 2)

**Input**:
- Rotina JSON (lista de sessões, cada uma com blocos, cada um com 2-3 exercícios).
- Demandas usadas (lista por treino).
- Perfil do aluno (nivel, aderencia, vetor 4D quando completo).
- Tabelas curadas (`ANCORAS_POR_REGIAO`, `ANCORAS_POR_SUBREGIAO`, etc) — leituras dinâmicas, não hardcoded.

**Processo**:
1. Carrega regras deste doc.
2. Para cada regra, executa o predicate sobre a rotina + tabelas + perfil.
3. Coleta violações com severidade.
4. Sugere causa raiz quando rastreável a frente/constraint.
5. Output: lista de achados (formato acima) + resumo agregado (% conformidade por categoria).

**Falsos positivos esperados no início**. Calibrar conforme Bernardo confirmar / refutar. Cada confirmação afina o predicate; cada refutação vira nota na regra correspondente.

---

## Limitações conhecidas (Fase 1)

- **Regras CORE** ainda imprecisas — Conceito 3 reforçado em `principios_clinicos.md` aponta que o eixo de classificação está ERRADO, não ausente. Auditor pode flagar "redundância de core não detectada" mas não saberá precisar o critério até a refatoração CORE clínica acontecer.
- **Mapa antagonismo gradual** ainda binário — R-BAL-2 flagga apenas violações óbvias (push+push, hinge+squat_uni). Refinamentos vêm na frente do Bloco 4.
- **Carga implícita** (R-BAL-3) só cobre `demanda_lombar` (já no XLSX); `grip`, `core`, `neural` por exercício ainda não cadastrados.
- **Carryover de fadiga** (R-ORD-3) em standby (`estabilidade_externa` não cadastrada).
- **Perfil 4D parcial** — só `nivel` e `aderencia` no DB hoje. Centralidade e densidade pareamento ainda virão.
- **N de auditorias = 1**. Regras vão refinar conforme mais auditorias rodarem; algumas podem ser fundidas/descartadas.

---

## Próximos passos

1. **Bernardo revisa este doc** — confirma/corrige/adiciona regras. Especialmente decisões pendentes da seção acima.
2. **Fase 2 — protótipo do agente** (próxima sessão dedicada): subagent ou script Python que lê este doc + recebe rotina JSON + produz achados. Testar contra rotina do Filipe (sabemos a resposta — Achados A-G da `auditorias/2026-05-25_pos_h_a0.md`).
3. **Fase 3 — integrar no fluxo**: agente roda no fechamento de cada frente que toca motor; reduz fricção das perguntas técnicas do Claude Code (catch clínico vem do agente, não da leitura humana toda vez).

---

*Última atualização: 2026-05-25. Doc inaugurado na Fase 1 do plano
"agente auditor clínico" (conversa 2026-05-25). Atualizar a cada
auditoria nova que descobrir regra ou refinamento. Bernardo é o
revisor clínico final — Claude Code/agente auditor apenas operam
as regras que ele aprovou.*
