# Handoff — Sessão pós-E.1 (frente H-A0: âncoras obrigatórias por região)

**Sessão**: 2026-05-27 (ou quando o Bernardo abrir) — frente corretiva
da E.1.

**Contexto**: E.1 foi mergeada em `main` em 2026-05-25 com gap clínico
catastrófico não detectado. Em demandas nível região (`("regiao", X, qtd)`),
o motor CSP não aplica `ANCORAS_POR_REGIAO` (peito+costas+ombro obrigatórios
em upper, perna_ant+perna_post obrigatórios em lower). Resultado em
testes reais com aluno Filipe Santos (avancado/media), config upper(3) +
lower(3) + core(2) × 2T: **costas 0 slots em 6 vagas** de upper; perna_ant
ausente em T1; padrões obrigatórios (`remadas`, `puxadas`) sumindo da
rotina; braços/adutores/abduction ocupando vagas que não deveriam.

Decisão fechada na sessão da E.1: **não reverter o merge**. Estamos
desenvolvendo o app, /gerar fica no CSP, mas precisamos da frente H-A0
pra restaurar qualidade clínica.

**Leitura preparatória (na ordem)**:

1. `docs/refatoracao/norte.md` — princípios. **Seção 3 (motivação
   estrutural) e Seção 7 (anti-padrão clássico)** especialmente —
   esta frente surge porque a sessão E.1 propôs uma vez "pré-
   decomposição via Hamilton no adapter" que é greedy disfarçado.
   Bernardo pegou no terceiro round de perguntas. Releia antes de
   tentar atalhos.
2. `docs/refatoracao/roadmap_csp.md` — Bloco 3 (E.1) ✅, mas gap H-A0
   identificado. Esta frente é **Bloco 2.5-bis** (corretiva da H-A1).
3. `docs/refatoracao/catalogo_constraints.md` — confirmar que H-A0
   não está catalogado e adicionar spec.
4. `docs/refatoracao/logs/micro_h_a1_ancoras_subregiao.md` — modelagem
   da H-A1 (subregião). H-A0 é o irmão; mesma técnica, mas slot de
   demanda região tem subregião VARIÁVEL (não fixa). É o ponto técnico
   novo da modelagem.
5. `docs/refatoracao/logs/frente_e1_substituir_gerar.md` — log da E.1,
   pra contexto do gap detectado e da decisão de não reverter.

**Objetivo desta sessão**:

Implementar **H-A0 (âncoras obrigatórias por região)** no motor CSP de
forma **declarativa**, espelhando H-A1. Não usar pré-decomposição
imperativa no adapter.

**Approach técnico (proposta — refinar com AskUserQuestion no início)**:

Em demanda `("regiao", R, qtd)` com R em ANCORAS_POR_REGIAO:

- Cada slot pode ser qualquer ex do pool região (já é como funciona hoje).
- Modelar `sub_idx[s]` IntVar por slot (subregião escolhida — análogo
  ao `bloco_idx[s]` da Fatia 4.A). Domínio: ids das subregiões em
  `REGIAO_PARA_SUBREGIOES[R]`. Constraint canalizando: para cada
  cidx do pool, se `assign[(s, cidx)] = 1` então `sub_idx[s] =
  id(pool[cidx].subregiao)`.
- Para cada subregião S com `obrigatoria=True` em ANCORAS_POR_REGIAO[R]:
  exigir `sum(sub_idx[s] == id(S) for s in slots de R) >= 1`.
- Cross-treino: igual H-A1, agrega slots de demanda região cross-treino
  por região (subregião obrigatória cobre rotina inteira, não treino
  individual).
- **Conflito de cardinalidade** (qtd < n_obrigatórias): constraint
  colaborativa força N obrigatórias DISTINTAS via BoolVar reificada
  (igual H-A1).
- **Graceful degradation**: âncora obrigatória com pool 100% vazio
  pós-H-P1 vira `degraded=True` com motivo `pool sem candidato`
  (igual H-A1).
- **NÃO ativa** quando peso/obrigatoriedade incoerentes (regiões sem
  entry em ANCORAS_POR_REGIAO — ex: cardio).
- **Compatibilidade** com peso_aderencia: H-A0 hard se sobrepõe; depois
  Aderência modula tier DENTRO de cada subregião.

**Decisões já fechadas (não reabrir sem motivo forte)**:

- **Branch nova** `frente-h-a0` a partir de `main`.
- **NÃO usar pré-decomposição via Hamilton no adapter** — anti-padrão
  da Seção 7 do norte. Caminho declarativo obrigatório.
- **NÃO reverter merge da E.1** — estamos desenvolvendo o app no CSP.
- **`PROPORCAO_COMPOSTOS = 0.6` do antigo é separado** — H-A0 cuida
  só de cobertura de subregiões. Se motor cair em 100% Acessórios DENTRO
  da subregião correta, é outra discussão (S-? do Bloco 4 ou
  refinamento da Aderência ao Tier).
- **`PROPORCAO_COMPOSTOS` provavelmente não precisa ser modelada
  explicitamente** — H-A1 (subregião → âncora padrão obrigatória)
  já garante o padrão composto principal em peito/ombro/costas/
  perna_ant/perna_post. Validar empiricamente com cenários do harness
  E.0; abrir frente própria só se gap persistir.

**Pontos de decisão pendentes (perguntar antes de codar)**:

1. **Modelagem `sub_idx[s]`** — IntVar canalizado vs BoolVar
   `is_sub[(s, S)]` por subregião do slot? IntVar é mais compacto;
   BoolVar mais flexível pra constraints futuras. Espelhar o que
   Fatia 4.A fez com `bloco_idx[s]` é o caminho coerente.

2. **Cross-treino quando demanda região aparece em vários treinos**
   — H-A1 agrega cross-treino por subregião. H-A0 deve agregar
   cross-treino por **região** (subregião obrigatória cobre rotina
   inteira) ou **por treino** (cobertura local)? Spec H-A1 = rotina
   inteira; H-A0 deve seguir mesmo padrão? Implicação: se T1 tem
   `upper(3)` e T2 também, H-A0 cross-treino exige que peito + costas +
   ombro apareçam EM TODA A ROTINA (6 slots distribuídos). Mais
   permissivo. Per-treino é mais clínico mas mais rígido.

3. **Comportamento na intersecção H-A0 + H-A1**: quando demanda
   `("regiao", "upper", 3)` ativa H-A0 e isso obriga ≥1 slot em
   subregião X, a H-A1 daquela subregião X ativa? (Spec H-A1 diz
   "NÃO ativa em demanda nível padrão nem regiao".) **Provavelmente
   sim** — H-A0 garante slot em peito; "qual padrão de peito" continua
   sendo decisão livre. Mas formalmente é "demanda subregião derivada
   da H-A0" — H-A1 deveria pegar. Caminhos:
   - (a) H-A1 detecta slots provenientes de H-A0 e ativa.
   - (b) H-A0 ativa H-A1 via marker no slot.
   - (c) Aceitar que peito Principal cubra por Aderência+softmax,
     sem H-A1 dentro de slots H-A0.
   Pergunta clínica difícil — provavelmente AskUserQuestion antes de
   decidir.

4. **Filipe Santos como case de validação** — rodar a config dele
   (upper(3) + lower(3) + core(2) × 2T) com N=20 seeds após implementar
   H-A0; sucesso = todas as 20 rotinas com peito + costas + ombro
   cobertos em upper, perna_ant + perna_post em lower.

**Restrições / não-fazer**:

- **NÃO usar pré-decomposição imperativa no adapter** (anti-padrão).
- **NÃO importar `_decompor_demanda_regiao` do antigo** pro motor CSP.
  Reuso da lógica é OK pra discussão, não pra código.
- **NÃO tocar `gerador_treino.py` (motor antigo)** — vivo até estado-
  alvo do norte.
- **NÃO mexer no XLSX (banco)** nem em `ANCORAS_POR_REGIAO` /
  `PADRAO_PARA_SUBREGIAO` (constantes canônicas — apenas consumir).
- **NÃO mergear em `main` sem aprovação explícita do Bernardo**.
- **Commit seletivo** (`git add <arquivo>`, NUNCA `-A`). `git status`
  + `git diff --cached` antes de commitar. Verificar sessões paralelas.
- **NÃO usar `--no-verify`** ou flags que pulem hooks.
- **AskUserQuestion** nos pontos pendentes 1-3 (técnicos) e 4 (validação).

**Validação obrigatória pré-merge**:

- Pytest baseline (318 esperado + ~10-15 testes novos do H-A0) verde.
- Harness antigo `tests/test_problemas_etapa.py`: 11/11 OK.
- Harness 16 cenários (`tools/calibrar_pesos_dimensoes.py`): 16/16 OK.
- **Cenário Filipe Santos**: rodar config dele (upper(3) + lower(3) +
  core(2) × 2T) com N=20 seeds. Sucesso = ≥18/20 rotinas com:
  - upper(3): peito + costas + ombro cobertos
  - lower(3): perna_ant + perna_posterior cobertos
  - braços / adutores / panturrilha **NÃO** entrando em upper/lower
    quando não pedidos especificamente
- **Cenário Manoel Lima**: mesmo config (com cargas_config: grip=6,
  lombar=5, core=6 ativo) — sucesso = cobertura clínica equivalente
  ao motor antigo em rotinas da Maria Santos (rotina ativa no DB
  pré-E.1).
- Smoke E2E manual via browser pra confirmar UX inalterada.
- Relatório E.0 atualizado com matriz nivel×aderencia em `relatorios/
  E1_pos_ha0_<data>.md`, comparando antigo × CSP pós-H-A0. Confirmar
  que distribuição de tier por subregião + cobertura de âncoras de
  região fica equivalente ou superior ao antigo.

**Sucesso da sessão**:

- H-A0 modelada declarativamente em `gerador_csp.py`. Catálogo
  atualizado com spec.
- Cobertura clínica em demanda nível região restaurada (validação
  Filipe + Manoel + harness).
- Log `docs/refatoracao/logs/frente_h_a0_ancoras_regiao.md`,
  roadmap_csp atualizado, MEMORY.md com 1 linha.
- Branch `frente-h-a0` pushed, aguardando aprovação Bernardo pra merge.

**Notas sobre como esta sessão (E.1) falhou em prever o gap** (pra
próxima sessão internalizar):

1. Relatório E.0 mostrava `bracos | CSP | 131 (100%)` em upper(3)×2T
   vs antigo `0`. Lido sem destacar como bloqueador (chamado de "win
   de cobertura").
2. Smoke E2E da E.1 cobriu demanda nível subregião (peito/costas/
   ombro/bracos), não demanda nível regiao — caminho de maior risco
   estrutural.
3. `ANCORAS_POR_REGIAO` existe em gerador_treino.py linha 142, foi
   lido em validação de imports, não conectado.
4. `catalogo_constraints.md` não foi consultado durante a sessão. H-A0
   não estava catalogado.
5. Decisão H-A1 ("NÃO ativa em regiao") foi tomada sem plano paralelo.

Lição: **smoke E2E deve cobrir o caminho mais arriscado**, não o óbvio.
Quando relatório comparativo mostra delta grande (CSP X% vs antigo Y%
com X−Y >20pp), tratar como sinal estrutural, não como "win" automático.
