# Roadmap do Refator CSP — BF Treinamento

**Propósito**: lista priorizada de TODO o escopo do refator declarativo
até atingir o estado-alvo da Seção 6 do `norte.md`. Único ponto canônico
do que falta fazer. Atualizado a cada fatia/frente fechada.

**Audiência**: próximas sessões de Claude — primeira coisa a ler depois
do `norte.md`. Bernardo (criador) também — pra evitar refazer handoffs
manuais de 200 linhas a cada sessão.

**Manutenção**: cada fatia/frente que fecha, atualizar status aqui + 1
linha de "o que entregou" + 1 linha de "próximo bloqueio se houver".

---

## Estado das branches (2026-05-26)

Pós-instituição da disciplina de merge (seção abaixo): branches mergeadas
em `main` assim que passam no gate. Pilha empilhada anterior já consolidada.

```
main  ← inclui Fatias 1-4.E (Bloco 1 completo) + Frente E.0 (Bloco 2) + Micro-frente H-A1 (Bloco 2.5)
 └─ frente-e-1  ✅ ← atual (a mergear em main após aprovação Bernardo)
```

---

## Frentes concluídas (referência rápida)

| Frente | O que entregou | Doc |
|---|---|---|
| Fatia 1 | Spike CP-SAT (H-T4 + S-T1 + H-P1) | `logs/mvp_fatia_1.md` |
| Fatia 2 P1 | Coluna `tier` curada no XLSX | `logs/mvp_fatia_2_parte_1.md` |
| Fatia 2 P2 | H-T1/T2/T3/T4 + H-R1 cross-treino + graceful | `logs/mvp_fatia_2_parte_2.md` |
| Frente B | Variedade INTRA-config (top-K + softmax) | `logs/mvp_fatia_3_frente_b.md` |
| Frente C | Adapter UI Flask × CSP em `/regerar` | `logs/mvp_fatia_3_frente_c.md` |
| Frente D | Aderência ao Tier (peso no objetivo) | `logs/mvp_fatia_3_frente_d.md` |
| Fatia 4.A | Blocos estruturais (X[s,b] + bloco_idx) | `logs/mvp_fatia_4a_blocos_estrutural.md` |
| Fatia 4.B | S-B1 distância funcional + evitar_agonistas | `logs/mvp_fatia_4b_sb1_pareamento.md` |
| Fatia 4.C | S-B4 tamanho preferido + tamanho_bloco da UI | `logs/mvp_fatia_4c_sb4_tamanho.md` |
| Fatia 4.D | exercicios_travados (pool-por-slot, bypass H-P1/H-T4/AllDiff cross) | `logs/mvp_fatia_4d_exercicios_travados.md` |
| Fatia 4.E | relaxar_familia (familias_proibidas motor-side + retry 2 fases) | `logs/mvp_fatia_4e_relaxar_familia.md` |
| Fatia 4.E cargas | H-cargas par-a-par no bloco + graceful degradation por bloco | `logs/mvp_fatia_4e_cargas_config.md` |
| Frente E.0 | Harness comparativo CSP × antigo (7 métricas, relatório markdown) | `logs/frente_e0_harness_comparativo.md` |
| Micro-frente H-A1 | Âncoras obrigatórias por subregião (cross-treino, graceful degradation, constraint colaborativa em conflito de cardinalidade) | `logs/micro_h_a1_ancoras_subregiao.md` |
| Frente E.1 | `/gerar` chamando `gerar_rotina_csp` (clean break do motor antigo); adapter rotina-inteira (`_distribuir_avisos_rotina_csp` + helpers); modal de avisos ganha clauses `h_a1_degradado` + `h_r1_degradado`; toggle R-1 wirado como `familias_proibidas` hard cross-rotina | `logs/frente_e1_substituir_gerar.md` |

---

## ⬜ Próximas frentes (priorizadas)

### Bloco 1 — 3 micro-frentes paralelas (~30min cada, independentes)

Pré-requisito: nenhum. Podem entrar em qualquer ordem ou paralelo.

- **✅ exercicios_travados** (Fatia 4.D) — pool-por-slot + bypass H-P1/H-T4/AllDifferent cross-treino entre travados. Travados participam de S-T1/S-B1/S-B4/Aderência. Adapter `treino_regerar` lê `cfg_r["exercicios_travados"]` e garante travado em `banco_regen`. Ver `logs/mvp_fatia_4d_exercicios_travados.md`.
- **✅ cargas_config** (Fatia 4.E cargas) — H-cargas par-a-par dentro do bloco (réplica fiel do antigo) com graceful degradation por bloco via BoolVar `cargas_off_b[b]` + penalty no objetivo. Travados ENTRAM nos pares (divergência intencional do antigo; pool_slot de 1 garante "travado nunca some" naturalmente). Adapter lê `cfg_r["cargas_config"]`; avisos `relaxado_carga` propagados pra `Sessao.avisos`. Ver `logs/mvp_fatia_4e_cargas_config.md`.
- **✅ relaxar_familia** (Fatia 4.E) — `familias_proibidas` motor-side substitui filtro upstream do adapter (norte Seção 5: coerência declarativa); `gerar_rotina_csp` faz retry 2 fases quando estrito inviável + toggle ON. Travado bypassa filtro (princípio 4.D). UI default ON, badge ↻ via `Sessao.relaxados` + aviso `familia_repetida` no modal — zero código novo na UI. Ver `logs/mvp_fatia_4e_relaxar_familia.md`.

### Bloco 2 — Frente E.0 (harness comparativo CSP × antigo)

- **✅ Frente E.0** — `tools/harness_comparativo_e0.py` standalone roda N rotinas (default 100, configurável via `--n`) por config nos dois motores com entrada normalizada e gera relatório `docs/refatoracao/relatorios/E0_<data>.md` lado-a-lado. 4 configs canônicas (Full Body 2T, ABC 3T, upper(3)×2T, perna_ant+post), 1 perfil default (nivel=3, aderencia=media) + flag opcional `--matriz` (2×2 nivel×aderência). 7 métricas (tier por subregião, cobertura H-R1, âncoras obrigatórias, variedade INTRA, overlap R-1, cycling fairness, tempo p50/p95) + % inviabilidade auxiliar. Aprovação visual; sem veredicto automático. Ver `logs/frente_e0_harness_comparativo.md`.
- **Achados N=100 a discutir na Frente E.1**:
  - **(BLOQUEADOR)** **Âncoras de subregião não modeladas no CSP**: quando recebe demanda `("subregiao", "ombro", 2)` o CSP cicla pelos padrões da subregião uniformemente, ignorando `ANCORAS_POR_SUBREGIAO[ombro] = [composto obrigatorio, ...]`. Resultado em ABC 3T: 100% das rotinas sem `ombro_composto` e 100% sem `biceps`. Antigo aplica âncoras via `_decompor_demanda_subregiao` (Seção 8.15.16). Provável **micro-frente pré-E.1**: adicionar constraint H-A1 (âncoras obrigatórias por subregião) ao catálogo + ao motor CSP.
  - **Bíceps família única**: 6 variações todas `variacao_de=Rosca bíceps` → H-T1 hard intra-treino faz `biceps(2)` INFEASIBLE no CSP (antigo aceita via relax intra). Discussão E.1.
  - **CSP ~150-200x mais lento** (Full Body 1.9s p50; ABC 6s p95 — primeiro caso na faixa de "lento"). Aceitável; otimização pós-E.1.
  - **Wins do CSP no relatório**: H-R1 costas zera vs antigo 15% violação em Full Body 2T; overlap R-1 menor em 3/4 configs; cycling em upper(3)×2T cobre TODOS padrões T1/T2 (~50/50) onde antigo zera vários.

### Bloco 2.5 — Micro-frente H-A1 (pré-requisito da E.1)

Pré-requisito: Frente E.0 (concluída).

- **✅ Micro-frente H-A1** — âncoras obrigatórias por subregião modeladas no motor CSP (2026-05-25). Constraint hard cross-treino exige `padrao == âncora.padrao` para cada `obrigatoria=True` por subregião quando demanda é `("subregiao", X, qtd)` com X em `ANCORAS_POR_SUBREGIAO`. Graceful degradation por pool vazio (espelha H-R1/H-T4). Conflito de cardinalidade (vagas < n_obrig efetivas, ex: `bracos(1)`): constraint colaborativa força N obrigatórias DISTINTAS via BoolVar reificada — replica `random.sample` do antigo declarativamente. NÃO ativa em demanda nível padrão nem regiao (decisões fechadas no handoff). Resultado: `ombro_composto` violado 100%→0% em ABC Day A; `biceps` 100%→0% em Day B; `hinge` 16%→0% em Day C; outras configs sem regressão. Wins do CSP preservados (H-R1 costas, overlap R-1). Trade-off: ABC 3T agora ~25s/rotina (era 4.8s); aceitável pra hobby app, otimização fica pra Bloco 4 se UI sentir. Pytest +13 testes novos; baseline preservado (1 teste estatístico ganhou tolerância +1.0/20 — alpha_tier perdeu sensibilidade pós-H-A1 pois slots de tier alto têm padrão agora fixo). Detalhes em `logs/micro_h_a1_ancoras_subregiao.md` + relatório `relatorios/E0_2026-05-25_pos_h_a1.md`.

### Bloco 3 — Frente E.1 (substituir `/gerar`)

Pré-requisito: Bloco 2.5 (H-A1) ✅ + Frente E.0 com relatório aprovado pelo Bernardo.

- **✅ Frente E.1** — `/gerar` chama `gerar_rotina_csp` SEMPRE (2026-05-26). Clean break, sem flag de transição (decisão fechada na sessão; alinha com norte Seção 5). `_regerar_motor_legacy` helper preservado em `app_flask.py` pra rollback rápido se necessário, mas não chamado em runtime. Mapeamento direto das opções da UI antiga pros parâmetros do CSP — espelha o que `/regerar` (Frente C+D+4.B+4.C+4.D+4.E) já fazia por treino, mas pra rotina inteira. Toggle `usar_historico_r1` wirado como `familias_proibidas` hard cross-rotina (substituto temporário do score soft D3.3 do antigo; S-H1 do Bloco 4 traz o soft de volta). Modal `_avisos_modal.html` ganha 2 clauses (`h_a1_degradado` + `h_r1_degradado`) — cobre tanto E.1 quanto a Frente C que populava sem renderizar desde 2026-05-23. Smoke E2E Full Body 2T OK; pytest +21 testes (318 total); harness 16/16 OK. Bíceps família única continua NO-OP estrutural (cadastro futuro de `Rosca martelo`/`Rosca direta` resolve). Lentidão ABC 3T (~25s/rotina) inalterada — otimização fica pra Bloco 4 se UI sentir. Detalhes em `logs/frente_e1_substituir_gerar.md`.

### Bloco 4 — Refinamentos pós-E.1 (não bloqueiam produção)

Cada item independente; entram conforme prioridade clínica observada.

**Itens prioritários** (achados de auditoria clínica 2026-05-25 — Full Body 2T com demanda nível região via UI; ver "Auditoria clínica pós-E.1" abaixo):

- **⬜ H-A0 — âncoras obrigatórias por REGIÃO** — dual da H-A1 para demanda nível `regiao` (H-A1 tem subregião fixa do slot; H-A0 escolhe subregião do slot via IntVar nova `sub_idx[s]`). Reusa `ANCORAS_POR_REGIAO` (já curado em `gerador_treino.py:142`). Hoje quando UI manda `("regiao", "upper", N)` o CSP cicla pelas subregiões de upper sem garantir cobertura mínima de movimentos básicos (puxar/empurrar/composto). Achado empírico: Full Body 2T com `upper(3) + lower(3) + core(2)` gerou 16 ex sem nenhuma costas e sem nenhum squat. Decisões fechadas (handoff 2026-05-25): per-treino (não cross-treino), hard banimento de subregiões não-âncora (Caminho A), interação H-A0 × H-A1 via marker `subregiao_obrigada_por_ha0` no slot (Caminho b). Graceful degradation análoga à H-A1 (pool vazio + conflito cardinalidade). Spec executável → `handoff_2026-05-25_h_a0.md`.
- **⬜ Gate de avaliação clínica semântica** — pré-requisito do Bloco 5. Antes de mergear cadastros completos ou desligar motor antigo, instituir prática de gerar 5-10 rotinas por config representativa (incluindo nível região da UI real), Bernardo lê como PT, e cada achado vira: (a) constraint nova no catálogo, (b) métrica nova no harness E.0, ou (c) decisão consciente de "tolerável". Saída: doc `auditorias/<data>_<config>.md` por rodada. Cobre o gap entre conformidade declarada (pytest + harness) e adequação clínica em uso real — vide anti-padrão norte Seção 7. **Caiu na E.1**: 318 testes verdes não pegaram zero-costas-zero-squat porque nenhuma métrica do harness E.0 mede cobertura semântica do repertório.

**Demais refinamentos** (ordem não prioritária):

- **⬜ S-B2** — balanço de carga implícita (core + lombar + grip + neural por bloco). Exige cadastrar `demanda_lombar` no XLSX.
- **⬜ S-B3** — fadiga prévia no bloco (máquina tolera mais que livre). Exige cadastrar `estabilidade_externa` no XLSX.
- **⬜ Centralidade Compostos** (2ª dimensão do vetor de perfil). Depende de S-T2 ou S-T3 implementadas (não existem no CSP ainda).
- **⬜ Densidade Pareamento** (3ª dimensão do vetor). Modulador de S-B1/S-B4 (alta = neutro, baixa = mais rígido).
- **⬜ Presets nomeados de perfil** — UI de aluno com botões "Força/hipertrofia", "Metabólico", "Saúde" mapeando combinações comuns. Espera 2+ dimensões implementadas.
- **⬜ Override por geração** — flag temporária no `/gerador` que sobrepõe vetor do aluno só pra essa rotina (B.4 da Etapa 7 já é precedente).
- **⬜ Mapa antagonismo gradual** — refinamento de S-B1 (push+pull "leve" vs "forte" via mapa de proximidade muscular). Hoje binário.
- **⬜ S-T2** — fadiga prévia entre blocos (peso-livre antes de máquina). Exige `estabilidade_externa`.
- **⬜ S-T3** — demanda neural acumulada do treino. Derivada de `tier`+perfil.
- **⬜ S-T4** — variedade de eixos dentro de subregião com múltiplos slots.
- **⬜ S-R1** — distribuição multi-eixo entre treinos.
- **⬜ S-R2** — frequência típica de combinações (precisa elicitar tabela com Bernardo).
- **⬜ S-R3** — variedade no nome dentro da rotina.
- **⬜ S-H1** — cobertura do repertório ao longo do tempo (refinamento do HIST/R-1).
- **⬜ H-P2** — Tier Principal + Centralidade Alta + Aderência Alta ⇒ bloco solo. Depende das 4 dimensões + S-B implementado.
- **⬜ H-X** — restrições físicas/dor sobre pool (filtros hard por aluno).
- **⬜ Captura de rationale no motor CSP** — destrava UI `/decisoes` pra treinos CSP (hoje mostra mensagem amber). Análogo à Etapa 8 Explicabilidade do antigo.

### Auditoria clínica pós-E.1 (registro do achado 2026-05-25)

Rotina gerada via `tools/criar_aluno_e_rotina_teste.py` (seed=42, aluno
nivel=intermediario/aderencia=media, demandas `regiao upper(3) + lower(3)
+ core(2)` em 2 treinos). CSP devolveu OPTIMAL em 0.29s, 16 ex sem
violação de constraints declaradas.

**Achados clínicos** (visão PT):

1. **🔴 Zero exercícios de costas em 16 slots** — push/pull desbalanceado;
   intermediário em Full Body 2x não deveria entrar nessa rotina.
2. **🔴 Zero squat em 6 slots de lower** — quadríceps só via knee_extension
   isolado.
3. **🟡 Blocos A de abertura sem composto** — T2 abre com Side Clams
   (fad 1 cpx 1) + Ponte Uni Caixa (fad 1 cpx 2); SNC alto na posição
   errada da carga neural.

**Diagnóstico técnico:** H-A1 (Micro-frente Bloco 2.5) só dispara em
demanda nível subregião. Demanda nível região passa pela enumeração de
subregiões sem âncora — CSP cicla pelo S-B1/aderência/cycling fairness
mas nenhum desses tem semântica de "cobrir repertório básico". UI real
manda nível região por default (Full Body), então o vazio aparece em
uso real.

**Diagnóstico metodológico:** 318 testes do pytest + 16 cenários do
harness antigo + 7 métricas da E.0 medem **conformidade às constraints
declaradas**, não **adequação clínica da rotina entregue**. Antipadrão
do norte Seção 7 caiu apesar de documentado. Bloqueio nasce porque cada
fatia fecha com gates verdes e sensação de progresso — progresso era em
conformidade, não em qualidade do produto.

**Ações:**
- H-A2 e gate de avaliação clínica entram como itens prioritários do
  Bloco 4 (acima).
- Suspeitas a confirmar com mais rodadas de auditoria: distribuição de
  fadiga acumulada por treino, ordem composto→isolado no bloco, volume
  por região na rotina, acoplamento volume/intensidade emergente.

### Bloco 5 — Estado-alvo final

Pré-requisitos: Bloco 3 (E.1) + cadastros completos no XLSX + gate de
avaliação clínica do Bloco 4 com pelo menos 1 rodada arquivada.

- **⬜ Dashboard quantitativo** (passo 5 do fluxo) — script que roda N=1000+ rotinas por config representativa, mede aderência aos princípios clínicos + variação por perfil, permite calibrar pesos com dados.
- **⬜ Cadastros XLSX completos** — `estabilidade_externa`, `demanda_lombar`, mais o que cadastros futuros pedirem.
- **⬜ Remoção do motor antigo do app** — fora de `app_flask.py` + `gerador_treino.py`. Preservar em branch/tag `legacy/motor-greedy` permanente (norte Seção 4).
- **⬜ Atualizar CLAUDE.md** — limpar seções obsoletas pós-remoção (Etapa 6/7/8 do antigo viram referência histórica em `docs/refatoracao/arquivo/`).

---

## Estado-alvo (resumo executivo — ver norte.md Seção 6)

Refator completo quando:
- `/gerar` + `/regerar` no CSP (motor antigo removido do app)
- Pareamento real (Fatia 4 completa)
- 4 dimensões do vetor ativas + moduladoras
- Dashboard quantitativo rodando
- Cadastros completos no XLSX
- Motor antigo preservado em git tag/branch

Pós-marco: retomar features de produto (fixos UI, ZIP, pausados por
aluno, etc) sem risco de patches em cascata.

---

## Como atualizar este doc

Toda fatia/frente que fecha:

1. Adicionar linha na tabela "Frentes concluídas" (1 linha).
2. Marcar item como ✅ no Bloco correspondente.
3. Se descobriu pendência nova, adicionar como ⬜ no bloco apropriado.
4. Atualizar "Estado das branches" se branch nova surgiu.
5. Atualizar `MEMORY.md` (1 linha) pra próxima sessão saber que veio.

**Não criar seções novas sem necessidade** — doc fica enxuto se entradas
forem objetivas. Decisões finas, achados, snapshots → log da fatia
específica em `logs/`. Aqui só status + dependência.

---

## Disciplina de merge (regra fixa pós-2026-05-24)

Origem: até 2026-05-24 acumularam-se 7 branches empilhadas sem merge em
`main`. Tudo era recuperável (pushed + linear) mas dava sensação de
"verdade flutuante" — `main` desatualizada vs último estado real. Pra
evitar isso reincidir:

**Cada fatia/frente que passa no gate verde (pytest + harness + smoke)
deve ser mergeada em `main` antes de iniciar a próxima.**

Sequência ao fechar uma fatia:

1. Pytest + harness + smoke verdes na branch da fatia.
2. Doc no `logs/` + atualização do `MEMORY.md` + tick no `roadmap_csp.md`.
3. Commit + push da branch.
4. **Imediato após push**: `git checkout main && git merge --ff-only <branch> && git push origin main`.
5. Deletar branch local: `git branch -d <branch>` (e opcionalmente `git push origin --delete <branch>` se quiser limpar origin).
6. Próxima fatia sai de `main` direto.

Pilha permitida: **no máximo 1 branch ativa** (a fatia em andamento).

Exceção: trabalho em paralelo legítimo (ex: 3 micro-frentes do Bloco 1
em paralelo) — aceita até 3 branches simultaneamente, mas cada uma
mergeada em `main` assim que fechar.
