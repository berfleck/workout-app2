# Sessão 2026-05-18 (madrugada) — âncora declarada para bracos

Branch: `feat/ancora-bracos` (a partir de main).

Extensão direta da sessão `sessao_2026-05-18_cobertura_padroes_obrigatorios.md`
(mesma noite). Usuário perguntou se o bug se estendia a bracos —
sondagem confirmou: sim, e em alguns cenários pior que costas.

---

## 1. Pergunta de origem

Após o fix da camada de planejamento (8.15.15), usuário perguntou:
"e o problema não poderia se estender a bracos também?"

Sondagem N=1000 pré-fix mostrou:

| Cenário | Cobertura completa |
|---|---|
| `bracos(2) × 2T` | **86%** (14% perdem biceps OU triceps) |
| `bracos(1) × 2T` | **51%** (49% perdem) |
| `bracos(3) × 2T` | 96% |

Adicionalmente, viés pool-weighted: triceps 65% / biceps 35% (pool 9:6
no banco), arrastando proporção pelo `_quotas_por_pool` do fallback.

---

## 2. Por que o fix anterior não cobria

O fix da 8.15.15 atua em **subregiões com âncoras declaradas** no
`ANCORAS_POR_SUBREGIAO`. Bracos não está lá → cai no caminho fallback
sem agregação rotina-level.

A discussão evoluiu pra entender a estrutura de 2 níveis das âncoras:

- `ANCORAS_POR_REGIAO` declara estrutura nível região → subregião
- `ANCORAS_POR_SUBREGIAO` declara estrutura nível subregião → padrão

Bracos não está em nenhum:
- Não está em `ANCORAS_POR_REGIAO['upper']` (só peito + costas + ombro)
- Não estava em `ANCORAS_POR_SUBREGIAO`

Contraste com **core**: tem âncora de região (core_dinamico +
core_isometrico, peso 1 cada). Quando user pede `regiao core(N)`,
Hamilton garante cobertura entre as 2 subregiões. Padrões internos
de cada uma ficam no fallback porque são **variações sem
obrigatoriedade clínica entre si**.

Bracos é diferente: biceps e triceps **são** obrigatórios entre si
clinicamente. Precisava de âncora.

---

## 3. Discussão sobre "âncoras pra tudo"

Usuário levantou: "se tudo precisa de âncoras pra funcionar bem,
torna existência das âncoras sem sentido".

Esclarecimento:
- Âncoras não existem pra "forçar cobertura" — existem pra **declarar
  a estrutura clínica de cada subregião** (pesos, obrigatoriedade).
- O bug é da camada fallback (per-treino sem coordenação). Mas o fix
  certo depende: subregiões com decisão clínica forte declaram via
  âncoras; subregiões sem decisão (adutores 1 padrão, core internos
  são variações) ficam no fallback.
- Bracos tem decisão clínica forte (biceps E triceps obrigatórios).
  Faltava declarar.

---

## 4. Fix

```python
"bracos": [
    {"padrao": "biceps",  "peso": 1, "obrigatoria": True},
    {"padrao": "triceps", "peso": 1, "obrigatoria": True},
],
```

Mudança declarativa em 4 linhas (`ANCORAS_POR_SUBREGIAO`). Bracos
passa pelo mesmo path agregado de costas pós-8.15.15.

Pesos 1:1 (não pool-weighted). Decisão clínica explícita —
[[tamanho-familia-nao-e-centralidade-clinica]] aplicada.

---

## 5. Resultados

Sondagem pós-fix N=1000:

| Cenário | Pré | Pós |
|---|---|---|
| `bracos(1) × 2T` cobertura | 51% | **100%** |
| `bracos(2) × 2T` cobertura | 86% | **100%** |
| `bracos(2) × 2T` distribuição | 65/35 triceps/biceps | **50/50** |
| `bracos(2) × 3T` cobertura | (não medido) | 100% / 50-50 |

Validação:
- pytest 206 passed + 1 skipped
- 0 snapshots regenerados (mudança restrita ao path bracos)
- Fixture HIB2 inalterada
- Harness 16/16 OK preservado

---

## 6. Estado final dos arquivos modificados

- `gerador_treino.py`: 4 linhas adicionadas em `ANCORAS_POR_SUBREGIAO`
- `docs/refatoracao/dimensoes_proximidade.md`: Seção 8.15.16 (esta sessão)
- `docs/refatoracao/logs/sessao_2026-05-18_ancora_bracos.md`: este log

---

## 7. Follow-ups abertos

Nenhum específico desta mudança. Outros caminhos fallback
(core_dinamico/core_isometrico padrões internos, adutores adduction)
ficam intencionalmente sem âncora — decisão clínica registrada.

---

## 8. Cross-references

- `docs/refatoracao/dimensoes_proximidade.md` Seção 8.15.16 — entrada
  oficial
- `docs/refatoracao/dimensoes_proximidade.md` Seção 8.15.15 — fix da
  camada de planejamento que esta âncora aciona
- `feedback_tamanho_familia_nao_e_centralidade.md` (memory) — princípio
  clínico que esta decisão honra
