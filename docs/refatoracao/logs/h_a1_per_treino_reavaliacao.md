# Log — Reavaliação da frente "cobertura per-treino do H-A1 marker"

**Data**: 2026-05-26
**Branch**: `h-a1-per-treino-marker` (fechada SEM código de produção,
mergeada FF em `main` só com evidência docs)
**Bloco**: 4 do roadmap CSP — primeiro item bonus pós-S-A1 (handoff
`handoff_2026-05-25_h_a1_per_treino.md`, agora deletado)

**Status**: ❌ frente fechada como **não-frente**. Diagnóstico
original (handoff 2026-05-25) era falso achado clínico; motor pós-H-A0
+ S-A1 já está correto pelos princípios que Bernardo verbalizou na
sessão de reavaliação.

---

## Resumo executivo

O handoff `handoff_2026-05-25_h_a1_per_treino.md` descrevia um "bug
Filipe Santos": rotina ativa do aluno (id=17, rotina `20260525_195735_bb15`)
saiu com T1 sem `squat_bilateral` (apenas Recuo = `squat_unilateral`)
e T2 com Agachamento Goblet Rampa (`squat_bilateral`). Conclusão do
handoff: H-A1 cross-rotina garante apenas ≥1 squat_bilateral na rotina,
não per-treino — bug que requer espelhar H-A0 (per-treino) no H-A1
marker.

Bernardo reavaliou em 2026-05-26 e **rejeitou o diagnóstico**: T1 uni +
T2 bi é variabilidade clínica desejada, não bug. Verbalizou 3 princípios
que invalidam a frente como descrita e reconfiguram o entendimento de
"cobertura clínica":

1. **Equilíbrio cross-treino** (universal): se uma sub tem N slots
   distribuídos em K treinos, distribuir o mais equilibrado possível.
   Não concentrar 2 em T1 e 0 em T2.
2. **Composto antes de isolado na ROTINA** (não per-treino): se rotina
   tem 1 slot da sub, esse slot é composto. Com 2+ slots, ≥1 composto
   na rotina (cross-rotina); o outro pode ser isolado OU composto.
   T1 supino + T2 apoio/isolado é variabilidade aceitável.
3. **Variabilidade entre treinos** (perna_anterior + costas
   explicitamente): T1 bilateral → T2 unilateral preferencialmente
   (perna_anterior); T1 vertical → T2 horizontal (costas).

Pelos princípios 1-3, **o motor pós-H-A0 + S-A1 já entrega o
comportamento desejado**:

- Princípio 2 = H-A1 cross-rotina (≥1 obrigatória por sub na rotina).
  Já implementado.
- Princípio 3 emerge da interação H-A0 per-treino (cada treino com
  cada sub obrigatória da região) + H-A1 cross-rotina (≥1 de cada
  padrão obrig). Em costas (2 obrig), cada treino tem ≥1 slot de
  costas, e a rotina tem ≥1 remadas + ≥1 puxadas — força T1=vert +
  T2=horiz ou vice-versa em 100% das rotinas.

Princípio 1 (equilíbrio cross-treino numérico) é o único que **NÃO
está coberto** — fica registrado como instância de S-R1 cross-treino
no Bloco 4 do roadmap (já listado).

---

## Evidência empírica (baseline 10 seeds, setup Filipe)

`tools/sondar_h_a1_per_treino_baseline.py` rodado com setup do Filipe
(`regiao upper(3) + lower(3) + core(2) × 2T`, peso_sa1=12,
peso_sa1_repet=10, seeds 0-9):

```
=== Sondagem H-A1 per-treino (Filipe Santos setup, n=10) ===

Rotinas validas: 10/10 (inviaveis: 0)
Cobertura completa per-treino: 0/10 (0.0%)

regiao   sub                padrao                      T1%    T2%  cross%
-------- ------------------ ------------------------ ------ ------ -------
lower    perna_anterior     squat_bilateral             60%    40%    100%
lower    perna_posterior    hinge                       80%    90%    100%
upper    peito              empurrar_compostos          60%    40%    100%
upper    costas             remadas                     50%    50%    100%
upper    costas             puxadas                     50%    50%    100%
upper    ombro              ombro_composto              40%    70%    100%
```

Persistido em `docs/refatoracao/logs/h_a1_per_treino_baseline_pre.json`
como referência permanente.

**Releitura da tabela sob os 3 princípios:**

- **Cross-rotina 100% pra tudo** → princípio 2 satisfeito em 100% das
  rotinas. Cada padrão obrigatório aparece em pelo menos 1 treino.
- **T1/T2 50/50 em costas (remadas vs puxadas)** → princípio 3
  satisfeito em 100%: nunca T1 tem ambas as obrigatórias e T2 nenhuma
  (H-A0 per-treino força ≥1 slot de costas em cada treino).
- **T1/T2 60/40 em squat_bilateral / empurrar_compostos / ombro_composto**
  → seria "incompleto" pelo princípio per-treino do handoff, mas **boa
  variabilidade pelo princípio 3 reformulado**: 40% das rotinas, T1 ou
  T2 fica com versão alternativa (squat_uni, isolado de peito,
  isolado de ombro), o que Bernardo explicitou ser aceitável.

A linha "Cobertura completa per-treino: 0/10 (0.0%)" mostra que
nenhuma rotina cobre TODOS os padrões obrigatórios em TODOS os treinos
— mas pelo princípio reformulado isso é variabilidade desejada, não
gap clínico.

---

## Decisão estrutural

Frente "cobertura per-treino do H-A1 marker" **fechada sem código de
produção**. Mudanças nesta branch:

- `tools/sondar_h_a1_per_treino_baseline.py` — ferramenta de sondagem
  permanente (útil pra próximas frentes que precisem medir cobertura
  per-padrão por treino).
- `docs/refatoracao/logs/h_a1_per_treino_baseline_pre.json` — snapshot
  baseline (evidência da reavaliação).
- `docs/refatoracao/logs/h_a1_per_treino_reavaliacao.md` — este log.
- `docs/refatoracao/roadmap_csp.md` — item "Cobertura per-treino do H-A1
  marker pós-H-A0" removido do Bloco 4.
- `docs/refatoracao/handoff_2026-05-25_h_a1_per_treino.md` — deletado.

`gerador_csp.py`, `app_flask.py`, `templates/`, `tests/` — **zero
diffs de produção**. Motor pós-H-A0 + S-A1 mantido como está.

---

## Lição metodológica

Anti-padrão observado: handoff escrito em 2026-05-25 capturou o
caso Filipe como "bug per-treino" sem conferir antes com Bernardo se
T1-uni + T2-bi era de fato regressão clínica. O handoff descrevia o
caso como "bloqueador clínico" e propunha solução técnica detalhada
(spec, gate, tests) sem o filtro clínico básico de "isso é problema
mesmo?".

A próxima sessão sentou pra atacar a frente, rodou baseline (10 seeds,
0% cobertura completa per-treino, 100% cross-rotina), e seguiu o
caminho do handoff até Bernardo dizer "espera — isso não é bug, é
variabilidade boa". Ciclo de ~30min de leitura preparatória + smoke +
2 round-trips de recomendação foi necessário pra detectar.

**Princípio reforçado** (já no `norte.md` Seção 7, mas a frente bateu
nele de novo): **conformidade declarada ≠ adequação clínica**. Antes
de codar constraint nova com base em achado descrito num handoff,
**reavaliar com Bernardo o achado em si**, não só o caminho de
implementação. Especialmente quando o achado é descrito como
"obvio bug" e a sessão original que documentou já está fria.

Isso reforça o item ⬜ "Gate de avaliação clínica semântica" do Bloco
4 — auditoria 5-10 rotinas + Bernardo lê como PT é o mecanismo pra
pegar isso ANTES do handoff existir, não DURANTE a frente.

---

## Interação com auditoria 2026-05-26

Os 3 princípios verbalizados nesta sessão interagem com os achados
da auditoria `auditorias/2026-05-26.md`:

| Princípio | Achado relacionado | Status |
|---|---|---|
| 1 (equilíbrio cross-treino numérico) | Achado 1 (distribuição lower 2:1) | Aberto — vira S-R1 cross-treino |
| 2 (composto antes de isolado na rotina) | Achado 4 (calibração aderência) | Achado 4 cobre via tier Principal default |
| 3 (variabilidade entre treinos) | Achado 2 (equip repetido cross-treino) | Achado 2 vira S-E1 (instância específica do princípio 3 em equipamento) |

Os princípios 1-3 são **declarativos clínicos**, não constraints
diretamente — viram constraints quando uma frente do roadmap aterriza
(S-R1, S-E1, S-B5).

---

## Pendências em aberto (não pra esta frente)

- **S-R1 cross-treino** (achado 1 da auditoria 2026-05-26): princípio
  1 declarado, falta constraint.
- **S-E1 diversidade equipamento** (achado 2 da auditoria 2026-05-26):
  princípio 3 declarado pra equipamento, falta constraint.
- **Calibração `_PESO_ADERENCIA_POR_PERFIL`** (achado 4 da auditoria):
  próxima frente prevista. Handoff `handoff_2026-05-26_calibracao_aderencia.md`.
