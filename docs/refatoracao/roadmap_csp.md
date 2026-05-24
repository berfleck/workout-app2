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

## Estado das branches (2026-05-24)

Pós-instituição da disciplina de merge (seção abaixo): branches mergeadas
em `main` assim que passam no gate. Pilha empilhada anterior já consolidada.

```
main  ← inclui Fatias 1-4.D + Frentes B/C/D
 └─ fatia-4e-relaxar-familia  ✅ ← atual (a mergear em main)
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

---

## ⬜ Próximas frentes (priorizadas)

### Bloco 1 — 3 micro-frentes paralelas (~30min cada, independentes)

Pré-requisito: nenhum. Podem entrar em qualquer ordem ou paralelo.

- **✅ exercicios_travados** (Fatia 4.D) — pool-por-slot + bypass H-P1/H-T4/AllDifferent cross-treino entre travados. Travados participam de S-T1/S-B1/S-B4/Aderência. Adapter `treino_regerar` lê `cfg_r["exercicios_travados"]` e garante travado em `banco_regen`. Ver `logs/mvp_fatia_4d_exercicios_travados.md`.
- **⬜ cargas_config** — nova hard **H-cargas** (filtro de pool por aluno baseado em config de carga, análoga a H-P1). Adapter lê `cfg_r["cargas_config"]`.
- **✅ relaxar_familia** (Fatia 4.E) — `familias_proibidas` motor-side substitui filtro upstream do adapter (norte Seção 5: coerência declarativa); `gerar_rotina_csp` faz retry 2 fases quando estrito inviável + toggle ON. Travado bypassa filtro (princípio 4.D). UI default ON, badge ↻ via `Sessao.relaxados` + aviso `familia_repetida` no modal — zero código novo na UI. Ver `logs/mvp_fatia_4e_relaxar_familia.md`.

### Bloco 2 — Frente E.0 (harness comparativo CSP × antigo)

Pré-requisito: Bloco 1 (3 micro-frentes) — comparação justa requer paridade.

- **⬜ Frente E.0** — script harness que roda N rotinas (~100-1000) por config comum (templates Full Body, ABC, hierarquias típicas) com mesma entrada nos 2 motores. Output: relatório markdown lado-a-lado com métricas:
  - Distribuição de tier por subregião
  - Cobertura de eixos H-R1 (% violações)
  - Cobertura de padrões obrigatórios (% âncoras não cumpridas)
  - Variedade INTRA-config (distintas em N runs)
  - Variedade INTER-rotina (overlap R-1)
  - Distribuição entre treinos (cycling fairness)
  - Tempo de solve médio
- Caveat: ainda terá gaps documentados (S-B2/S-B3 não cadastrados; pareamento gradual S-B1 ainda binário). Aceitável — gate é comparação principal.

### Bloco 3 — Frente E.1 (substituir `/gerar`)

Pré-requisito: Frente E.0 com relatório aprovado pelo Bernardo.

- **⬜ Frente E.1** — substituir `/gerar` pelo motor CSP. Opções:
  - **Clean break** (alinha com norte.md Seção 5 "sem usuários = sem retrocompat"): remover motor antigo da rota direta. Branch git preservada conforme Seção 4 do norte.
  - **Flag de transição** (curto prazo): manter motor antigo via `?motor=legacy` ou checkbox durante período de validação clínica.
  - Decisão pós-relatório E.0.

### Bloco 4 — Refinamentos pós-E.1 (não bloqueiam produção)

Cada item independente; entram conforme prioridade clínica observada.

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

### Bloco 5 — Estado-alvo final

Pré-requisitos: Bloco 3 (E.1) + cadastros completos no XLSX.

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
