# Log — MVP Fatia 3 Frente C: integração da engine CSP com a UI Flask

**Data**: 2026-05-23 (mesma sessão da Fatia 2 P2 + Frente B; trabalho separado em branch nova)
**Branch**: `frente-c-integracao-ui` (criada a partir de `fatia-2-parte-2`)
**Arquivos modificados**:
- `app_flask.py` (adapter motor CSP → Sessao + rota `/treino/<t>/regerar` reescrita + detecção `treino_csp` na rota `/decisoes`)
- `templates/decisoes_treino.html` (clause `{% if treino_csp %}` mostra mensagem em vez de timeline vazio quando treino veio do motor novo)

**Status**: ✅ concluída — gate verde (pytest 228 + 1 skip + 13 snapshots + harness 16/16 OK; smoke test browser via curl + Flask test client).

---

## Objetivo

Primeira ponte real entre `gerador_csp.py` (engine declarativa CP-SAT) e a UI Flask. Escopo CONSCIENTEMENTE MÍNIMO conforme handoff:

- Substituir UMA rota — `/treino/<t>/regerar` — pelo motor novo.
- Manter `/gerar` (geração principal) intocada (motor antigo).
- Default `variedade=ConfigVariedade()` por padrão (Caveat 2 da Frente B fechado).
- Sem implementar features ausentes do motor novo (tamanho_bloco, evitar_agonistas, cargas, exercicios_travados, etc.) — apenas ignorar.

## Decisões fechadas (antes de codar)

Via AskUserQuestion (4 perguntas):

1. **Escopo da rota** — só `/treino/<t>/regerar`. Isola risco (1 treino vs rotina; cross-treino do CSP não dispara; fluxo opt-in do usuário).
2. **Pareamento de blocos** — cada exercício vira 1 `SuperSerie` solo (labels A/B/C/...). Pareamento clínico real fica pra Fatia 4 (S-B do catálogo). Mais honesto com o estado do motor.
3. **Modo template** — mapear pra demandas equivalentes via `TEMPLATES[nome]` + `TEMPLATE_EPP[nome]`. Funciona pros 4 templates existentes.
4. **Página /decisoes** — botão 🔍 continua visível; página detecta marker `rationale={'gerador': 'csp'}` e mostra mensagem amber "rationale indisponível" em vez de timeline vazio.

Recomendações implícitas aceitas no plano:

- **Nivel mapping** `iniciante→1`, `intermediario→2`, `avancado→3`. Default 3 (sem teto) quando aluno desconhecido.
- **Features ignoradas em /regerar**: `tamanho_bloco`, `evitar_agonistas`, `relaxar_familia`, `cargas_config`, `exercicios_travados`, `lateralidade_por_padrao` (squat_bi/uni continua via expansor de demanda).
- **Salvar no histórico**: `/regerar` só substitui `sessoes_ativas[t]`; em modo edição via HUB, `salvar_sessoes_disco` propaga pro rascunho. Sem mudança no histórico.
- **Branch nova** `frente-c-integracao-ui` a partir de `fatia-2-parte-2`.

## O que foi implementado

### Checkpoint 2 — adapter de saída (motor → Sessao)

`app_flask.py` ganhou:

- **`_label_bloco_csp(i)`**: `0→'A'`, `25→'Z'`, `26→'AA'`. Conversão limpa pra qualquer i.
- **`_resultado_csp_pra_sessao(resultado, tipo_label)`**: itera `resultado["ordem_global"]`, cria 1 `SuperSerie` solo por exercício, atacha marker `rationale={"gerador": "csp"}` via `dataclasses.replace` (não muta instâncias do banco global). Itens `h_r1_aplicadas[degraded=True]` viram `Sessao.avisos` com `tipo="h_r1_degradado"`.

### Checkpoint 3 — adapter de entrada (cfg → demandas CSP)

`app_flask.py` ganhou:

- **`_NIVEL_ALUNO_PARA_CSP`** + **`_nivel_aluno_csp(aluno_obj)`**: mapeia string→int. Default 3 quando aluno None ou nivel não bate. `.strip()` defensivo.
- **`_cfg_antiga_pra_demandas_csp(cfg_r)`**:
  - Modo hierarquia (`cfg_r["demandas"]` presente): passa direto, expandindo aliases legados.
  - Modo template (`cfg_r["padroes"]` + `cfg_r["exercicios_por_padrao"]`): cada padrão+qtd vira `("padrao", padrao, qtd)`. EPP `dict` (lateralidade) soma valores.
- **`_expandir_demanda_csp(nivel, escopo, qtd)`**: handle aliases legados pré-Etapa 8 / pré-Frente 4:
  - `("padrao", "squat", N)` → split Bresenham ceil/floor em `squat_bilateral` + `squat_unilateral` (N=1→1 bi; N=2→1+1; N=3→2+1; N=4→2+2).
  - `("padrao", "core_isometrico"|"core_dinamico", N)` → vira `("subregiao", escopo, N)` (são subregiões reais no XLSX após Etapa 8; H-T4 passa a disparar em vaga única — clinicamente OK).
  - Outros: passa direto.

### Checkpoint 4 — substituição cirúrgica de `/treino/<t>/regerar`

`app_flask.py` ganhou:

- **`_regerar_motor_legacy(t, cfg_r, banco_regen)`**: helper que encapsula a versão antiga (`gerar_sessao_por_demandas` / `gerar_sessao`). Não chamado em runtime — disponível pra rollback rápido se precisar.
- **`treino_regerar(t)` reescrita**:
  - Preserva fallback do cfg quando `configs_geradas[t]` vazio (deriva padrões dos blocos atuais).
  - Preserva o filtro de banco cross-treino (nomes + famílias dos outros treinos da rotina) — CSP só faz AllDifferent dentro da rotina que recebe; mandamos só 1 treino aqui.
  - Mapeia `cfg_r` em demandas CSP via wrapper.
  - Detecta aluno via `session.get("aluno_id")` ou `edicao_hub`. Fallback nivel 3.
  - Chama `gerar_treino_csp(demandas, banco_regen, nivel, seed=random, variedade=ConfigVariedade())` — `python_seed=None` (Caveat 2 da Frente B). `seed` do CP-SAT randomizado por chamada pra ajudar exploração.
  - Sucesso: converte via `_resultado_csp_pra_sessao`, preserva `nome_custom`.
  - Falha (`viavel=False`): mantém sessão atual + adiciona aviso `h_r1_degradado` com motivo "motor CSP inviável; treino mantido". Fallback defensivo.
  - cfg sem demandas: mantém sessão atual.

### Checkpoint 4-bis — tratamento defensivo da página `/decisoes`

`app_flask.py` (rota `hub_treino_decisoes`):

- Detecta `treino_csp = any(ex.rationale.get("gerador") == "csp" for ...)` após `_dict_to_sessao`. Passa pro template.

`templates/decisoes_treino.html`:

- Antes da seção "Estatísticas agregadas", clause `{% if treino_csp %}` mostra card amber "Motor CSP — rationale indisponível" com explicação clínica. `{% else %}` envolve TODO o resto da página (timeline + distribuição + alternativas). Fechamento `{% endif %}` antes do `</div>` final.

## Resultado da validação

### Smoke test funcional (rota /regerar via curl)

Servidor Flask subiu sem erros (3 sessões restauradas). 5 POST consecutivos em `/treino/0/regerar`:

| Run | Slots gerados (1 ex/slot) |
|---|---|
| 1 | Remada Seal Halteres, Agachamento Smith, Supino Fechado, V-Up Unilateral, Prancha Alternada, Stiff Uni. Smith |
| 2 | Remada Baixa Neutra, Agachamento Livre, Apoio Elevado, Infra Roll-Up, Crunch Na Bola, Lev. Terra |
| 3 | Serrote Aberto, Agachamento Livre, Apoio, Dead Bug C/ Bola, Prancha Bola, Stiff Uni. Smith |
| 4 | Remada Curvada Halteres, Agachamento Smith, Apoio Elevado, Infra Roll-Up, Prancha Renegade, Stiff Uni. Halteres |
| 5 | Remada Aberta Trx, Agachamento Goblet Rampa, Supino Inclinado Halteres, Dead Bug C/ Anilha, Prancha Bola, Stiff Uni. Smith |

**5 rotinas distintas em 5 runs** — variedade ativa funcionando. Slot A (costas) 5 distintos, slot B (perna_ant) 3, slot C (peito) 5, slot D (core) 4, slot E (core) 3, slot F (perna_post) 3.

### Smoke test do template /decisoes (via Flask test client)

Criou sessão CSP, salvou como rascunho, GET `/hub/rotina/<aluno>/treino/0/decisoes`. Body contém "Motor CSP — rationale indisponível" → template detectou e renderizou mensagem corretamente.

### Gate de fechamento

| Métrica | Resultado |
|---|---|
| pytest | 228 passed + 1 skipped (=229) + 13 snapshots ✓ pré-existente |
| harness | 16/16 OK (2.3 + 4.1 NO-OPs informativos preservados) ✓ |
| Servidor Flask | sobe + responde HTTP 200 ✓ |
| /regerar via curl | retorna `_treino_card.html` com blocos solo A/B/C ✓ |
| Variedade INTRA-config | 5/5 distintas em 5 runs (Caveat 2 fechado: default `ConfigVariedade()`) ✓ |
| Template /decisoes (CSP) | mostra mensagem amber, não timeline vazio ✓ |
| Gerador antigo intocado | ✓ — toda lógica nova em `app_flask.py` |
| Motor CSP intocado | ✓ — nada em `gerador_csp.py` |

## Achados / sinais de alerta

1. **Slots únicos de padrão caem em Acessório.** Em Templates como Full Body, slots como `("padrao", "hinge", 1)` ou `("padrao", "abduction", 1)` não disparam H-T4 (H-T4 só para `subregiao` com qtd=1) e tier-order com 1 slot é trivial. Resultado pode ser Acessório. Documentado da Frente B como "baseline neutro": antes era artefato da heurística determinística do gerador antigo "preferindo" Principal; agora o motor entrega variedade máxima dentro das regras hard. Aluno "clássico" precisa do modulador "Aderência ao Tier" da Frente D pra forçar Principal sempre que possível.

2. **Aviso `h_r1_degradado` populado mas não renderizado.** `Sessao.avisos` ganha entry quando H-R1 degrada (nível 1 + perna_anterior), mas `_avisos_modal.html` não tem clause pra esse tipo. Dado preservado pro futuro; render no modal fica pra próxima iteração. Não-bloqueador (só silencioso, não há erro).

3. **`configs_geradas` é volátil.** Quando o servidor reinicia, `sessoes_ativas` restaura via `sessoes_salvas.json`, mas `configs_geradas` zera. `/regerar` cai no fallback (deriva padrões dos blocos atuais via `bloco.ex.padrao`), que perde modo template / demandas custom. Equivalente ao comportamento antigo. Não-bloqueador.

4. **CSP não-determinístico mesmo com `random_seed` fixo** quando `randomize_search=True` (memória [[feedback-cpsat-nao-determinismo]]). Por isso `seed=random.randint(0, 2**31)` em cada chamada — randomização é redundante mas não machuca; o que importa é `python_seed=None` (default da `ConfigVariedade()`), que é o knob principal do softmax.

5. **Conflito de naming de seed.** O CSP usa `seed` (random_seed do CP-SAT) e `ConfigVariedade.python_seed` (softmax). Wrapper passa `seed=randint` e deixa `python_seed=None`. Cada chamada vê uma combinação diferente — efeito final é alta variedade.

## Decisões fechadas (relevantes pra Fatia 3+ / 4+)

1. **Default `variedade=ConfigVariedade()` em produção.** Frente C MVP fecha o Caveat 2 da Frente B. Toda chamada feita pela UI usa variedade ativa por padrão. Se algum dia quiser opt-out (ex: "regerar idêntico"), criar knob explícito no UI.

2. **`python_seed=None` em produção.** Cada aperto de Gerar = nova rotina. Se algum dia tiver feature "favoritar geração", salvar o seed específico naquela hora.

3. **Marker `rationale={"gerador": "csp"}`** é a forma canônica pra detectar treinos do motor novo na UI. Estrutura mínima (1 chave). Permite extensão futura sem quebrar contrato.

4. **Pareamento real é Fatia 4.** Frente C não tenta nada — sai como blocos solo. Cards do UI ficam coerentes mas longos. Pareamento clínico (S-B1/B2/B3/B4 do catálogo) requer modelagem nova no CSP.

5. **Mapeamento template → demandas é direto e estável.** TEMPLATES + TEMPLATE_EPP do gerador antigo viraram inputs do CSP via `_cfg_antiga_pra_demandas_csp`. Aliases legados (squat, core_*) tratados explicitamente via `_expandir_demanda_csp`. Robusto pra os 4 templates existentes; novos templates passam direto enquanto não usarem aliases.

## Conclusão

Frente C abre a porta entre engine declarativa e produto real. Mecanismo cirúrgico (1 rota, ~2 wrappers, 1 detecção defensiva) — sem refator no motor antigo, sem refator no motor novo, sem mudar contrato de UI. Default `ConfigVariedade()` resolve o gap mais visível da Frente B (rotinas determinísticas em produto).

Uso real do botão "Regerar" agora exercita: H-T1/T2/T3/T4 + H-R1 + S-T1 + ConfigVariedade. Aluno tem retorno visual real do motor novo num fluxo opt-in, sem risco pra fluxo de geração principal.

## Próximos passos (Fatia 3+ / 4)

- **Frente D** — vetor de perfil completo + moduladores (incluindo "Aderência ao Tier" — resolve achado #1 acima).
- **Substituir `/gerar`** — Frente C parte 2. Espera-se uso real da Frente C MVP por algum tempo antes (validação clínica em rotinas reais do Bernardo).
- **Render do aviso `h_r1_degradado`** em `_avisos_modal.html` — achado #2, escopo pequeno.
- **Pareamento de blocos** — S-B1/B2/B3/B4 do catálogo. Fatia 4.
- **Outras hards** — H-P2 (bloco solo), H-X (restrições físicas).
- **Outras softs** — S-T2/T3/T4, S-R1/R2/R3, S-H1.
- **Captura de rationale no motor novo** — destrava UI completa de /decisoes pra treinos CSP.
