# Log — MVP Fatia 3 Frente D: vetor de perfil (Aderência ao Tier MVP)

**Data**: 2026-05-24
**Branch**: `frente-d-vetor-perfil` (criada a partir de `frente-c-integracao-ui`)
**Arquivos modificados**:
- `database.py` (migração ALTER TABLE + `aderencia` em CRUD)
- `templates/alunos.html` (select novo no form + modal de edição + meta)
- `app_flask.py` (rotas `/alunos/novo` + `/alunos/<i>/editar` leem campo; adapter `_PESO_ADERENCIA_POR_PERFIL` + `_peso_aderencia_csp`; wiring no `/treino/<t>/regerar`)
- `gerador_csp.py` (`_construir_modelo` ganha kwarg `peso_aderencia`; propagado em `_resolver_legacy`, `_resolver_com_variedade`, `gerar_rotina_csp`, `gerar_treino_csp`)
- `tests/test_aderencia_tier.py` (novo, 6 testes)

**Status**: ✅ concluída — gate verde (pytest 235 passed + 1 skipped = +6 da Frente D; harness 16/16 OK; smoke E2E via Flask test client).

---

## Objetivo

Resolver o **achado #1 da Frente C**: slots únicos de padrão (ex.: `("padrao", "hinge", 1)`, `("padrao", "abduction", 1)`) caíam em Acessório ~33-50% do tempo via sorteio do CSP. Causa raiz: H-T4 só dispara em `nivel=subregiao + qtd=1`, e S-T1 não produz par i<j em grupo de 1 slot → todas as 3 tier-choices têm score=0 → softmax distribui livre.

Solução: introduzir a primeira dimensão do **vetor de perfil de aluno** (princípios clínicos 2026-05-21, Seção "Vetor de perfil") como modulador real de constraint soft. **Aderência ao Tier alta** = motor força tier alto mesmo em slot único de padrão.

Escopo CONSCIENTEMENTE MÍNIMO conforme handoff:
- 1 dimensão (Aderência ao Tier), não as 4. Centralidade Compostos depende de S-T3/S-T2 que não existem no CSP; Densidade Pareamento depende de S-B (Fatia 4); Nível Técnico já está implementado via H-P1.
- 1 modulador (Opção A — peso no objetivo CSP), não 4 do MVP da Seção 3 do catálogo.
- Campo cru no form (3 selects Alta/Média/Baixa), não presets nomeados.
- Sem override por geração (próxima frente).

## Decisões fechadas (antes de codar)

Via AskUserQuestion (3 perguntas):

1. **Mecanismo: Opção A** — termo extra no objetivo CSP, modulando peso por aluno.
   - Rejeitadas: Opção B (filtro hard pré-solver — binário e risco de inviabilidade); Opção C (só turbinar `alpha_tier` existente — garantia clínica fraca porque modula sobre a 1ª solução enumerada do CP-SAT, que pode ser Acessório por sorte).
2. **Escopo MVP: Só Aderência ao Tier** — Centralidade/Densidade ficam pra próximas iterações; presets adiados até houver 2+ dimensões pra empacotar.
3. **Branch base: `frente-c-integracao-ui`** — Frente D estende o adapter da Frente C diretamente; merge final pra main carrega P2+B+C+D juntas.

Decisões implícitas aceitas no plano:

- **Mapeamento string→int conservador**: `alta=2, media=0, baixa=0`. Média neutra preserva byte-a-byte a Frente B. Iterar pra cima se calibração indicar.
- **Default em `_construir_modelo`**: `peso_aderencia=0` → comportamento Frente B preservado. Caller (legacy + Phase 1 + Phase 2 da variedade) opt-in via kwarg.
- **Migração de schema** via ALTER TABLE no `init_db`, padrão dos 6 ALTER existentes.
- **Sem mudança no `/gerar`** (motor antigo) — escopo da Frente D fica no motor CSP via `/regerar`.

## O que foi implementado

### Checkpoint 2 — schema (`database.py`)

- ALTER TABLE no `init_db`: `ADD COLUMN aderencia TEXT DEFAULT 'media'`. Try/except OperationalError igual aos 6 migrations preexistentes (rotina_ativa_id, rascunho_*, data_atualizada).
- `carregar_alunos`, `salvar_aluno`, `editar_aluno`, `buscar_aluno_por_nome` ganham campo `aderencia` (read + write).
- Smoke test: 4 alunos existentes ganharam `aderencia='media'`; insert/edit com `alta`/`baixa` funcionou.

### Checkpoint 3 — CRUD aluno (`templates/alunos.html` + rotas)

- Select novo `<select name="aderencia">` com 3 opções (Alta/Média/Baixa) no form de criação e no modal de edição. Default Média.
- Rotas `/alunos/novo` e `/alunos/<i>/editar` leem `request.form.get("aderencia", "media")` e passam pra database.
- Meta line do card de aluno exibe `Aderência: {{ aluno.get('aderencia', 'media') }}` entre Objetivo e Restrições.

### Checkpoint 4 — modulação no motor (`gerador_csp.py`)

- `_construir_modelo` ganha kwarg `peso_aderencia: int = 0`. Quando >0, adiciona por slot:
  ```python
  ader_pen = NewIntVar(0, rank_max * peso_aderencia, ...)
  model.Add(ader_pen == (rank_max - tier_rank[s["sid"]]) * peso_aderencia)
  penalidades.append(ader_pen)
  ```
- Slot Principal (rank=3, rank_max=3): pen = 0. Acessório (rank=1): pen = 2 * peso.
- Quando peso=0: bloco inteiro skipado — preserva byte-a-byte Frente B (nenhuma IntVar adicional).
- Propagado em `_resolver_legacy` (branch sem variedade), `_resolver_com_variedade` (Phase 1 e Phase 2 reconstruídas com mesmo peso), `gerar_rotina_csp`, `gerar_treino_csp`.

### Checkpoint 5 — adapter + wiring (`app_flask.py`)

- `_PESO_ADERENCIA_POR_PERFIL = {"alta": 2, "media": 0, "baixa": 0}`.
- `_peso_aderencia_csp(aluno_obj)` — fail-open default 0 (sem aluno = sem efeito).
- `treino_regerar` passa `peso_aderencia=_peso_aderencia_csp(aluno_obj)` pro `gerar_treino_csp`. Mesma fonte de aluno do `_nivel_aluno_csp` (session ou edicao_hub).

## Resultado da validação

### Smoke isolado do motor (`gerador_csp` direto, 30 runs)

Demanda `("padrao", "hinge", 1)`. Pool hinge no XLSX atual: 11 Principal + 1 Intermediário + 9 Acessório.

| peso_aderencia | Principal | Intermediário | Acessório |
|---|---|---|---|
| 0 (Média/Baixa) | 15/30 | 0/30 | 15/30 |
| 2 (Alta) | 30/30 | 0/30 | 0/30 |

Variedade dentro de Principal preservada com peso=2: 9/11 Principais distintos em 30 runs (Lev. Terra 6×, Stiff Uni. Smith 4×, Hip Thrust 4×, Lev. Terra Sumô 4×, Stiff B-Stance 3×, Stiff Barra Smith 3×, Good Morning 3×, Stiff Halteres 2×, Stiff Barra Livre 1×). Frente B continua trabalhando dentro do tier que Aderência Alta força.

### Smoke E2E via Flask test client (`/treino/0/regerar`, 20 runs)

| Aluno | Aderência | Tiers em 20 regenerações |
|---|---|---|
| `__FrenteD_alta__` | alta | 20/20 Principal |
| `__FrenteD_baixa__` | baixa (= media=0 na implementação atual) | 11 Acessório, 7 Principal, 2 Intermediário |

### Gate de fechamento

| Métrica | Resultado |
|---|---|
| pytest | **235 passed + 1 skipped** (=236) — era 229 (228+1) pré-Frente D; +6 testes novos em `test_aderencia_tier.py` ✓ |
| harness | **16/16 OK** — 2 FAIL informativos pré-existentes (2.3 NO-OP, 4.1 NO-OP 14.44%) preservados ✓ |
| 13 snapshots | ✓ (sem regressão) |
| `_main()` do gerador_csp.py | Não testado explicitamente (não é gate); peso=0 preserva byte-a-byte por construção (kwarg opcional) ✓ |
| Gerador antigo (`gerador_treino.py`) | Intocado ✓ |

## Decisões fechadas (relevantes pra Frente D+ / Fatia 4+)

1. **Default `peso_aderencia=0` em todas as funções do CSP** preserva byte-a-byte a Frente B. Garantia de não-regressão.

2. **Mapeamento conservador `alta=2, media=0, baixa=0`** — Média = neutro (não tem efeito ativo "no meio do caminho"). Razão: a semântica clínica de Aderência Baixa não é "empurra Acessório" mas "personal não se importa com o tier escolhido". Igual a Média. Se calibração futura indicar valor pra diferenciar Média e Baixa, abrir negociação.

3. **`alpha_tier` da Frente B continua existindo, ortogonal ao `peso_aderencia`**. `alpha_tier` modula softmax (preferência por NÃO MUDAR slots de tier alto vs a referência da 1ª enumerada). `peso_aderencia` modula objetivo (preferência por tier alto, absoluto). Podem coexistir; smoke não testou interação. Recomendação se algum dia for usado conjunto: começar com `alpha_tier=0` quando `peso_aderencia>0` pra evitar dupla penalização.

4. **Aderência Alta NÃO inviabiliza rotinas** (Opção A vence Opção B). Solver continua aceitando Acessório como fallback se Principal não couber por outras hards. Resultado: graceful, não binário.

5. **Não tocamos `gerador_treino.py` antigo, motor CSP é o único modulado pela Frente D**. Consistente com a Frente C — toda lógica nova fica em `app_flask.py` adapter + `gerador_csp.py`.

## Achados / sinais de alerta

1. **Slot único de padrão hinge sem peso = 50/50 Principal/Acessório**, não ~33%/33%/33% como esperado naive. Razão: pool tem 11 Principal + 1 Intermediário + 9 Acessório — Intermediário sub-representado. Softmax sobre soluções enumeradas reflete pool natural. Não-bloqueador, só interpretativo.

2. **Variedade dentro do tier preservada com peso=2 (9/11 Principais em 30 runs)**, mas a distribuição relativa entre Principais (Lev. Terra 6×, Stiff Uni. Smith 4×, ...) é função da ordem de enumeração do CP-SAT — pode mudar entre rodagens da mesma seed (memória [[feedback-cpsat-nao-determinismo]]). Não-bloqueador clinicamente.

3. **Branch `_resolver_legacy` também propaga `peso_aderencia`** — teste (e) garantia que peso=2 zera Acessório mesmo sem variedade ativa. Útil pra retrocompat em testes/`_main()` que ainda usam `variedade=None`.

4. **Calibração de `peso=2` é chute inicial empírico** validado em hinge (pool ~50/50). Se outro padrão tem distribuição mais extrema (pool 90% Principal vs 10% Acessório), peso=2 ainda funciona porque é multiplicador uniforme. Padrão com pool 100% Acessório (degraded H-T4) força Acessório de qualquer jeito — peso não muda nada (slot rank=1 = peso constante, motor escolhe livre dentro).

## Pendências mapeadas (não bloqueiam uso real)

1. **Centralidade Compostos + Densidade Pareamento** continuam fora do MVP. Centralidade depende de S-T3 (futuro Fatia 4+); Densidade depende de S-B1/B2/B3/B4 (Fatia 4).

2. **Presets nomeados** ("Força/hipertrofia clássico", "Metabólico em grupo", "Saúde geral") adiados — só compensam quando há 2+ dimensões pra empacotar.

3. **Override por geração** (flag temporária no `/gerador` que sobrepõe vetor do aluno só pra essa rotina) — pendente. Próxima frente UX.

4. **`/gerar` (motor antigo) NÃO foi modulado pela Frente D**. Aderência ao Tier hoje só atua em regenerações via `/regerar`. Quando `/gerar` migrar pro CSP (Frente C parte 2), Aderência se aplica automaticamente.

5. **Calibração formal do mapeamento alta/media/baixa → int** via dashboard quantitativo (passo 5 do fluxo de refator) — não bloqueia, chute inicial (alta=2, media=0, baixa=0) cobriu o achado #1.

## Próximos passos

- **Usar a Frente D em produção** — Bernardo cadastrar 1-2 alunos com Aderência Alta (Fernanda da entrevista), comparar regenerações com Aderência Baixa (Turma 7h). Validação clínica em casos reais antes de escalar.
- **Frente E (Substituir `/gerar` pelo CSP)** — Frente C parte 2. Frente D se aplica automaticamente quando isso acontecer.
- **Centralidade Compostos** — espera S-T3/S-T2 entrarem no CSP. Ativa modulador adicional no `_construir_modelo`.
- **Override por geração** — UI no `/gerador` com flag temporária. Não-trivial.
- **Calibração formal** — dashboard mede aderência clínica em N rotinas; iterar mapeamento.
