# Handoff — Frente E.0 (harness comparativo CSP × antigo)

**Sessão**: 2026-05-24 — Frente E.0 do Bloco 2 do refator CSP

**Leitura preparatória (na ordem)**:
1. `docs/refatoracao/norte.md` — princípios e anti-padrões. Especial atenção à Seção 5 (trade-offs) e Seção 6 (estado-alvo: comparação justa é gate pra Frente E.1).
2. `docs/refatoracao/roadmap_csp.md` — Bloco 2 é o seu escopo. Bloco 1 (3/3) **completou em 2026-05-24** (commit `be5f81c`); pré-requisito atendido.
3. `docs/refatoracao/catalogo_constraints.md` — referência das métricas (cobertura H-R1, âncoras obrigatórias, S-T1 tier-order) pra saber o que comparar.
4. `docs/refatoracao/logs/mvp_fatia_4e_cargas_config.md` — log da última fatia (formato do log que VOCÊ vai escrever pra fechar a frente).
5. `tools/calibrar_pesos_dimensoes.py` — harness do motor antigo (16 cenários, métricas estruturais). Referência de estrutura, não de implementação.
6. `tools/smoke_cargas_config.py` + `tools/smoke_travados.py` — formato dos smokes recentes (cenário × N runs × tabela).

**Objetivo desta sessão**:
Implementar `tools/harness_comparativo_e0.py` — script que roda N rotinas (~100-1000) por configuração comum nos DOIS motores (CSP novo via `gerar_rotina_csp`/`gerar_treino_csp` + antigo via `gerar_multiplos_treinos`) com mesma entrada (mesma config, mesmo banco, mesmo perfil de aluno) e produz relatório markdown lado-a-lado em `docs/refatoracao/relatorios/E0_<data>.md`. Métricas mínimas (do roadmap):

- Distribuição de tier por subregião (Principal/Intermediário/Acessório)
- Cobertura H-R1 (% violações por subregião com ≥2 slots)
- Cobertura de padrões obrigatórios (% âncoras não cumpridas)
- Variedade INTRA-config (# rotinas distintas em N runs)
- Variedade INTER-rotina (overlap R-1, % slots iguais entre rotinas consecutivas)
- Distribuição entre treinos (fairness do cycling — Hamilton/Bresenham antigo vs CSP novo)
- Tempo de solve médio (ms por rotina)

**Decisões já fechadas (não reabrir sem motivo forte)**:
- **Branch nova** `frente-e0-harness-comparativo` a partir de `main`. Após gate verde (script roda fim-a-fim em N=100, relatório gerado, pytest preservado), mergear em `main` (regra de disciplina do roadmap).
- **Não modificar nenhum motor** (nem `gerador_treino.py` nem `gerador_csp.py`) — Frente E.0 é puramente observacional. Achados de divergência viram pendência no roadmap, não patch.
- **Gaps documentados são aceitáveis**: S-B2/S-B3 não cadastrados; S-B1 ainda binário no CSP (vs ranking gradual planejado). O gate é a comparação principal, não paridade de features.
- **Output em markdown** com tabelas lado-a-lado (não JSON, não HTML). Bernardo lê visualmente.
- **Sessões paralelas**: VERIFIQUE `git status` + `git branch --show-current` antes de qualquer edit. Se houver sinal de outra sessão ativa, use `Agent` com `isolation: "worktree"` em vez de prosseguir manualmente (recorrência confirmada em 2026-05-24, ver memory `feedback_sessoes_paralelas_git.md`).

**Pontos de decisão pendentes (perguntar antes de codar)**:
1. **N de iterações por config**: 100 (rápido, ruído alto), 500 (médio), ou 1000 (lento, sinal limpo)? Trade-off entre tempo de execução e confiabilidade estatística das métricas. Sugestão default: 100 pra dev/iteração, configurável via CLI.
2. **Conjunto de configurações**: quais templates/hierarquias? Sugestão mínima: Full Body 2x, ABC, hierarquia "upper(3)×2T" (caso que destravou o cycling Bresenham), hierarquia "perna_anterior(3)+perna_posterior(3)" (testa H-R1). Bernardo deve confirmar/ampliar.
3. **Perfis de aluno**: rodar 1 perfil (médio) ou matriz (nivel × aderência tier)? Matriz multiplica tempo de execução por N perfis. Sugestão: 1 perfil default + flag opcional pra rodar matriz.
4. **Critério de aprovação**: Bernardo lê visualmente e decide se aprova pra Frente E.1, OU existe threshold quantitativo (ex: "CSP precisa ter pelo menos paridade em 5 de 7 métricas")? Afeta se o script só gera o relatório ou também emite veredicto.
5. **Falha do CSP**: quando inviável (status INFEASIBLE), conta como "0 rotina" (descartada) ou "1 rotina vazia"? Afeta agregação das métricas. Sugestão: descartar + reportar % de iterações inviáveis como métrica adicional.
6. **Captura de tempo de solve**: incluir só tempo do solver, ou pipeline completo (pré-processamento + solve + decode)? Comparação justa depende de comparar mesma fronteira.

**Restrições / não-fazer**:
- NÃO tocar `gerador_treino.py` nem `gerador_csp.py` (puramente observacional).
- NÃO mergear em main sem aprovação explícita do Bernardo.
- Commit seletivo (`git add` por arquivo, NUNCA `-A`). Antes de commitar: `git status` + `git diff --cached`.
- NÃO use `--no-verify` ou flags que pulem hooks.
- Se ambiguidade na implementação, pergunte antes de codar (AskUserQuestion). Não chute thresholds, configs ou formato de relatório.
