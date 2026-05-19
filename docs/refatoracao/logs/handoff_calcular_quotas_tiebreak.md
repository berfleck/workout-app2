# Handoff — corrigir viés de tie-break em `calcular_quotas`

## Tarefa

Corrigir viés de tie-break em `calcular_quotas` (gerador_treino.py
~linhas 285-293).

## Contexto

A função distribui vagas entre âncoras via Hamilton's Largest Remainder.
Quando duas âncoras empatam em (obrigatoriedade, peso, resto), o
desempate atual usa `idx` (ordem de definição na lista ANCORAS_*). Isso
cria viés determinístico:

- peito sempre vence costas em upper
- perna_anterior sempre vence perna_posterior em lower
- core_dinamico sempre vence core_isometrico em core
- remadas sempre vencem puxadas em costas (subregião)

Como `pre_alocar_rotina` (~linha 3052) roda Hamilton agregado sobre
`vagas_total = qt × n_treinos`, o viés aparece sistematicamente em
rotinas reais. Cenários empíricos confirmados (seed=42,
calcular_quotas direto):

| Cenário agregado | Distribuição atual | Empate em |
|---|---|---|
| upper(4) | peito=2, costas=1, ombro=1 | peito ↔ costas |
| upper(6) | peito=3, costas=2, ombro=1 | peito ↔ costas |
| lower(4) | perna_ant=2, perna_post=1 | perna_ant ↔ perna_post |
| lower(6) | perna_ant=3, perna_post=2 | perna_ant ↔ perna_post |
| core(3) | core_din=2, core_iso=1 | core_din ↔ core_iso |
| costas-sub(3) | remadas=2, puxadas=1 | remadas ↔ puxadas |
| costas-sub(5) | remadas=3, puxadas=2 | remadas ↔ puxadas |
| costas-sub(7) | remadas=4, puxadas=3 | remadas ↔ puxadas |

## Fix esperado

Dentro do bloco "Hamilton's Largest Remainder" em `calcular_quotas`,
trocar o último critério do `tiebreak_key` (atualmente `idx`) por
sorteio aleatório. Usar `random` global do módulo (mesmo já usado na
linha 252 com `random.sample` no caso especial). Preserva
reprodutibilidade via seed do chamador. Critérios anteriores
(obrigatória > peso) ficam intactos — sorteio só dispara quando os
dois primeiros já empataram.

Esboço (não literal, valide com leitura local):

```python
def tiebreak_key(p):
    idx, a, ideal, floor = p
    resto = ideal - floor
    return (
        -resto,
        0 if a.get("obrigatoria") else 1,
        -a["peso"],
        random.random(),  # ← era `idx`
    )
```

## NÃO mexer

- Estrutura de ANCORAS_POR_REGIAO / ANCORAS_POR_SUBREGIAO (pesos e
  obrigatoriedades inalterados).
- `pre_alocar_rotina` ou qualquer call-site — correção é interna à
  `calcular_quotas`.
- Caso especial `vagas < n_obrigatorias` (linha ~252) — já usa
  `random.sample`, está correto.
- Critérios anteriores do tie-break (obrigatória, peso) — só o último
  (idx) muda.

## Validação

1. **Rodar `tests/test_calcular_quotas_vies.py`** — arquivo já existe
   untracked, 4 casos parametrizados (upper N=4, lower N=4, core N=3,
   costas-sub N=3) com 2000 seeds cada, validando ratio ~50% (entre
   45% e 55%). HOJE TODOS FALHAM (ratio 100% — vencedor determinístico).
   Após fix, todos devem passar.
2. **pytest inteiro**: 202 passed + 1 skipped + 13 snapshots na main
   atual. Snapshots de regressão (tests/__snapshots__/test_regressao.ambr)
   provavelmente regeneram — esperado pela mudança de distribuição. Aceitar
   regeneração apenas se distribuição cross-subregiões obrigatórias for
   plausível e nenhuma obrigatória sumir indevidamente.
3. **Fixture HIB2** (`test_filtro_carga_realmente_dissolve_par_conhecido`):
   pode precisar atualizar seed mais uma vez (a sequência aleatória muda
   com o random.random() adicional). Estado atual: seed=358 com par
   `{Stiff Barra Smith, Remada Baixa Aberta}`.
4. **harness** `tools/calibrar_pesos_dimensoes.py` — deve continuar
   **16/16 OK** (estado atual main pós-sessão 2026-05-18). 4.1 e 4.2
   são informativos, não FAIL — não esperar regressão.

## Convenção de commit

Branch nova (ex: `fix/calcular-quotas-tiebreak`) ou no main direto se
você preferir. Commit: `fix(quotas): randomiza tie-break em empates de
Hamilton's Largest Remainder` ou similar. Não criar PR sem pedir.

## Documentação

- Atualizar `docs/refatoracao/dimensoes_proximidade.md`. Boa âncora:
  Seção 8.15.7 (lista de pendências) — adicionar item registrando o
  bug + fix + caso clínico (peito sempre vencendo). Considerar criar
  Seção 8.15.14 nova se o item ficar grande.
- Atualizar `docs/refatoracao/logs/sessao_2026-05-18_cadastros_e_tiebreaker.md`
  §10 (follow-ups abertos) marcando este item como ✅ fechado, ou
  criar log próprio em `docs/refatoracao/logs/`.

## Tarefa secundária (opcional) — auditoria de outros tie-breaks

Em 1 dia descobrimos 3 casos da mesma patologia ("sort estável +
ordem de declaração", ou "dado vazio interpretado como N/A"). Pode
haver uma 4ª camada. Vale um passe rápido antes de fechar — qualquer
caso achado entra como bonus no mesmo PR temático ou vira follow-up,
sua decisão.

Roteiro:

- `grep -n "sorted\|\.sort(\|min(\|max(\|next(" gerador_treino.py`
- Para cada ocorrência com `key=` ou condição filtrando candidatos:
  - É possível empate no critério principal?
  - Como é desempatado? (Lembrar: `sorted`/`list.sort` em Python são
    estáveis — preservam ordem da lista original em empates)
  - A lista vem do XLSX, de um dicionário Python, ou de uma constante
    hardcoded?

Casos suspeitos a priori:

- Cycling em `_decompor_demanda_subregiao` / `_decompor_demanda_regiao`
- `_ordenar_padroes_por_prioridade`
- `ordenar_blocos`
- `busca_candidato` em `montar_blocos` (P1/P2/P3/P4 sub-preferências)
- Qualquer `next(e for e in pool if ...)` em pool com ordem
  determinística (XLSX, dicionário, lista)

Critério pra promover suspeita a bug: rodar análise estatística
N≥500 no caso isolado e verificar se a distribuição tem **variância
zero ou quase-zero** onde deveria haver dispersão entre candidatos
equivalentes. Se sim, é a mesma patologia.

Escopo de decisão do agente:

- Auditoria negativa (nada achado): registra no log da sessão como
  passe negativo, encerra.
- Achou 1+ casos novos: aplicar `random.random()` no tie-break local,
  validar com pytest + harness. Pode entrar no mesmo PR (sugestão de
  nome: `fix/vies-tiebreak-quotas-e-afins`) ou virar follow-up.

Não é blocker pro fix principal do Hamilton.

## Contexto recente — NÃO confundir, mas observar a patologia

A sessão 2026-05-18 (mergeada em main, commits 1ed8217 + f45a7f9 +
a2a746f + 2d03e20) corrigiu um tiebreaker DIFERENTE em
`_selecionar_cand_score_aware` (linha ~2564). Aquele opera em camada
**downstream** (escolha de exercício dentro de um pool). Este aqui é
camada **upstream** (distribuição de quota por âncora). Sem relação
funcional — fixes independentes que aplicam a mesma técnica
(`random.random()` no tie-break) em locais distintos.

**Mas é a MESMA PATOLOGIA conceitual** — em 1 dia descobrimos 3 casos:

1. Tag `plano_corporal=NaN` em Apoios — escapava do score INTRA, dava
   vantagem injusta sobre Supinos. Fix: cadastrar tag no XLSX.
2. `_selecionar_cand_score_aware` — `sort(key=score)` estável, empates
   resolvidos pela ordem do XLSX. Fix: `key=(-score, random.random())`.
3. **Esta tarefa** — Hamilton em `calcular_quotas`, tie-break por `idx`
   = ordem da lista ANCORAS_*.

Esse 3º caso explica retroativamente o viés posicional T1 vs T2
documentado em `docs/refatoracao/logs/analise_vies_upper.md` Q4
(peito 25% em T1, 50% em T2, χ²=533, **zero variação em 1000
iterações** — o `idx` determinístico era a causa exata). Validação
empírica retroativa do diagnóstico desta tarefa.

Memory relacionada que continua valendo:

- `[[tamanho-familia-nao-e-centralidade-clinica]]` — não derivar peso
  de tamanho de família. Esta tarefa não envolve isso, mas se durante
  a investigação aparecer ideia de "ponderar âncora por número de
  filhos" ou similar, **rejeitar**.
- `[[cadastros-pullover-mitigation]]` — ponteiro pro log da sessão
  anterior.

## Doc relacionado

`docs/refatoracao/dimensoes_proximidade.md` Anexo Seção 6 (estrutura
ANCORAS_*) e Seção 8.15.7 (pendências abertas pós-Etapa 7).
