# Etapa 4 — Filtro de cargas (Fase B / HIB2)

**Branch**: `refator-gerador` · **Sub-PRs**: 0.1+0.2+0.3 (calibração) + 1.1+1.2+1.3+1.4 (motor) + 2.1+2.2+2.3+2.4 (UI/avisos/log)

## O que foi feito

- 3 campos novos no `Exercicio`: `carga_grip`, `carga_lombar`, `demanda_core` (defaults 0). `_int_or_zero` helper genérico pra ler colunas int do XLSX (None/NaN/inválido → 0). `carregar_banco` lê os 3 campos curados (125/125 preenchidos, valores 0-3).
- `_bloqueio_cargas(ex_a, ex_b, thresholds)` — predicado puro: bloqueia se ambos têm valor ≥ 1 numa dimensão E soma ≥ threshold. Threshold 0/None pula a dimensão. Simétrico.
- `pode_adicionar_ao_bloco` integra filtro **antes** da regra de fadiga. Travados (`exercicios_travados`, lista de `Exercicio` ou set de nomes) bypassam — hard precedence pra escolha explícita do usuário.
- `cargas_config: dict | None` plumbado pelas 6 funções: `pode_adicionar_ao_bloco` → `_buscar_candidato` → `montar_blocos` → `gerar_sessao` / `gerar_sessao_por_demandas` → `gerar_multiplos_treinos`. `gerar_multiplos_treinos` lê `cfg.get("cargas_config")` por treino.
- Aviso `relaxado_carga` via **second-pass** em `montar_blocos`: quando `_buscar_candidato` retorna `None` e `cargas_config` está ativo, faz 1 chamada extra com filtro off; se aparece candidato, era carga que bloqueou. Aviso traz `bloco_idx`, `exercicio` (âncora), `par_bloqueado`, `dimensao`, `soma`, `threshold`. Solo por fadiga ou exaustão de banco não emite. Acumulador via `avisos_carga: list | None` passado por kwarg (mesmo pattern de `relaxados_local` da Etapa 3).
- `app_flask.py /gerar` lê 3 inputs novos do form (`carga_grip_max`, `carga_lombar_max`, `demanda_core_max`); monta `cargas_config` só se os 3 vierem preenchidos (senão None = filtro OFF). Anexa em cada cfg + persiste em `opcoes_globais`. Regen path (`/regerar`) lê `cfg.get("cargas_config")` e propaga para ambas chamadas (`gerar_sessao_por_demandas` e legacy `gerar_sessao`).
- UI: 3 selects num `<details>` "Limites de carga (avançado)" colapsado por padrão dentro de "Configurações gerais". Layout `grid-cols-3` (compacto, funciona mobile + desktop). Defaults visíveis 6/5/6 (HIB2). Opção em branco "—" desliga a dimensão.
- `_avisos_modal.html` agora renderiza 5 tipos: `incompleta`, `familia_repetida` (existentes); `relaxado_carga` (novo, ícone 🔒 vermelho); `ancora_nao_cumprida` e `ancora_sem_candidatos` (Etapa 3, eram silenciosos — R3 do `etapa_3.md` resolvido). Cabeçalho do treino: "ficou incompleto" se `incompletas`; senão "gerado com restrições" se cargas/âncoras_*; senão "preenchido com flexibilizações". Enrichment defensivo no `app_flask`: só chama `_label_escopo_av` se aviso tem `nivel`. `relaxado_carga` ganha `bloco_label` derivado buscando o exercício âncora em `sessao.blocos` (robusto contra `ordenar_blocos` reordenar).
- Persistência: `_configs_to_serializable` / `_from_serializable` preservam `cargas_config` naturalmente como dict no JSON. Registros antigos sem `cargas_config` viram `None` ao carregar (retrocompat). Sem código novo necessário.
- Harness de calibração `tools/recalibrar_cargas_hib2.py` (Sub-PR 0.3): simula em pós-hoc HIB (6/5/5) e HIB2 (6/5/6) sobre os blocos OFF gerados pelo motor pós-Etapa 3. 20 seeds × cfg `lower(4) + upper(3) + core(1)` × 2 treinos. Output em `docs/refatoracao/logs/casos_clinicos_hib2_pos_etapa3.md` com tabela agregada + top pares persistentes/repermitidos + 20 casos individuais com cargas par-a-par.
- 25 testes novos em `tests/test_carga_filter.py` cobrindo: campos no dataclass, helper puro, integração em `pode_adicionar_ao_bloco`, plumbing end-to-end (20 seeds × HIB2), evidência forte (par documentado dissolve), standalone `gerar_sessao_por_demandas`, aviso `relaxado_carga` (sintético + propagação para `Sessao.avisos`).
- 1 snapshot novo `test_full_body_4treinos_seed1_HIB2` em `test_regressao.py` — congela comportamento com filtro ON (no-op safety check pra essa config específica; teste de evidência forte cobre comportamento ativo).

## Decisão arquitetural consolidada

### Hard filter, não score

Filtro de cargas implementado como **hard filter** dentro de `pode_adicionar_ao_bloco`, consistente com a regra de fadiga existente. Memória `feedback_etapa4_cargas_hard_filter.md` salva: quando Etapa 5 (score consolidado em `_buscar_candidato` com softmax) chegar, decidir explicitamente se cargas viram penalidade contínua no score ou continuam hard. Não deixar acidente arquitetural — discutir antes de codar Etapa 5.

### Travados bypassam filtro

Exercícios travados (`exercicios_travados`) ignoram filtro de cargas: o usuário escolheu explicitamente, hard precedence sobre filtro. Nenhum aviso emitido nesse caso. Trade-off aceito: rotina com par travado violando HIB2 é responsabilidade do trainer, não do gerador.

### Pair-wise em bloco de 3

Filtro é par-a-par, não soma trio. Em bloco de 3, candidato C é checado contra ex1 e ex2 separadamente. Isso é coerente com o spirit de HIB2 (cargas pareadas, não acumuladas) e simplifica raciocínio.

### Detecção de `relaxado_carga` via second-pass

Em vez de mudar contratos de `_buscar_candidato` pra retornar motivo de rejeição, `montar_blocos` faz uma chamada extra com `cargas_config=None` quando o slot fica vazio. Custo: 1 chamada extra por slot vazio (raro, ~0.4% dos blocos). Vantagem: zero invasão na hot path; código limpo.

### Filtro OFF é o default

`cargas_config=None` em todos os 6 callers preserva 100% do comportamento pré-Etapa 4. Snapshots da Etapa 3 estáveis. UI passa `None` quando trainer não interage com `<details>` "Limites de carga". Padrão "opt-in" — só liga quando o trainer explicitamente preenche os 3 selects.

## Thresholds finais — HIB2 6/5/6

Mantidos os defaults originais da memória do projeto:

```python
HIB2 = {"grip": 6, "lombar": 5, "core": 6}
```

**Justificativa via recalibração pós-Etapa 3** (harness `tools/recalibrar_cargas_hib2.py` rodado sobre 20 seeds × cfg `lower(4)+upper(3)+core(1)` × 2 treinos = 159 pares):

| Métrica | OFF | HIB (6/5/5) | HIB2 (6/5/6) |
|---|---:|---:|---:|
| Pares avaliados | 159 | 159 | 159 |
| Bloqueados | 0 | 8 | 3 |
| Repermitidos HIB→HIB2 | — | — | 5 |

**Pares persistentes em HIB2 (clinicamente justificados — lombar pesados juntos):**
1. Hiperextensão 45° + Remada Baixa Aberta (lombar 3+2=5)
2. Lev. Terra Anilha + Remada Curvada Barra
3. Agachamento Smith + Remada Curvada Halteres (lombar 3+2=5)

**Pares repermitidos pelo relax do core (5→6) — aprovados pelo usuário:**
1. Flexão Joelhos Slide + Remada Baixa Neutra (2x)
2. Nordic Curl + Pallof Press
3. Abd Bicicleta + Remada Landmine
4. Box Jump + Remada Curvada Halteres

Aprovação clínica caso-a-caso recebida do usuário em sessão (resposta "A" ao prompt da etapa 4) — todos os 4 repermitidos validados como seguros, todos os 3 persistentes validados como bloqueio justificado.

## Métricas pós-Etapa 4

### A — Performance (4000 simulações × 4 configs × 3 treinos)

| Métrica | OFF | ON (HIB2) | Overhead |
|---|---:|---:|---:|
| Tempo total | 4.48s | 5.09s | +13.5% |
| ms/sim | 1.12 | 1.27 | +0.15ms |

Overhead aceitável (~13%). Filtro adiciona ~6 ops por chamada de `pode_adicionar_ao_bloco` (3 somas + 3 comparações + bypass check). Caching de pools NÃO necessário. (Nota: tempo absoluto OFF maior que pós-Etapa 3 — ~4.5s vs 2.24s — porque agora o cfg de benchmark inclui múltiplas demandas + 3 treinos por sim, não 1 cfg simples.)

### B — Blocos solo (cfg `lower(4)+upper(3)+core(1)` × 2 treinos × 1000 sims)

| Métrica | OFF | ON (HIB2) | Diff |
|---|---:|---:|---:|
| Total de blocos | 8001 | 8015 | — |
| Blocos solo | 2 (0.02%) | 30 (0.37%) | +28 (+0.35pp) |
| Rotinas com aviso `relaxado_carga` | 0 | 11 (1.1%) | — |

Solos forçados pelo filtro: ~28 em 8000 blocos. Critério do plano "< 5% das rotinas" atingido com folga (1.1%). Avisos `relaxado_carga` emitidos em 11/1000 rotinas — usuário fica informado quando bloco solo é causado pelo filtro.

### C — Bloqueios clinicamente justificados

3 pares persistentes em HIB2 (avaliados sobre 159 pares × 20 seeds × 2 treinos):
- Lombar pesados juntos (Hiperextensão+Remadas, Lev.Terra+Remadas, Agachamento+Remadas) → **bloqueio justificado** (vetor de risco lombar é o mais relevante clinicamente, conforme calibração HIB2 original).

Nenhum par "perigoso conhecido" passou (validação cruzada com casos clínicos originais, todos cobertos pelos 3 pares persistentes ou pela regra `≥ threshold` em outras dimensões).

## Surpresas / desvios do plano

1. **Snapshot HIB2 idêntico ao snapshot OFF para `full_body_seed=1`**. O cfg específico (Full Body × 4 treinos) não produz pares violadores HIB2 nessa seed — o snapshot serve como "no-op safety check" (se algum dia o filtro começar a quebrar essa config, vai disparar). O comportamento ativo do filtro é coberto pelo `test_filtro_carga_realmente_dissolve_par_conhecido` (seed=1 + cfg `lower(4)+upper(3)+core(1)` produz par "Hiperextensão 45° + Remada Baixa Aberta" sem filtro; com HIB2 o par desaparece).

2. **`relaxado_carga` raro em produção**: 11/1000 rotinas (1.1%) emitiram o aviso na simulação representativa. O filtro raramente força solo — quando força, é clinicamente justificado. Threshold pode ser apertado no futuro se desejar mais bloqueios; o mecanismo está pronto.

3. **Mantida calibração HIB2 sem ajuste pós-Etapa 3**. Etapa 3 mudou Fase 1 (quotas clínicas em vez de proporção do banco), mas a Fase 2 (`montar_blocos`) recebe N exercícios já alocados — a distribuição de cargas chegando à Fase 2 não muda dramaticamente pela troca de Fase 1. Recalibração confirmou: 6/5/6 continua justificado clinicamente.

4. **Decisão de não auto-popular form com `cargas_config` salvo**. Os 3 selects sempre mostram defaults 6/5/6. Quando o trainer carrega rotina antiga, os defaults aparecem; pra rodar de novo com mesmo filtro, precisa interagir com `<details>`. Não é problema porque "Limites de carga" é avançado/opt-in. Se virar UX issue, pode-se adicionar lógica de pre-selected option lendo `opcoes_globais.cargas_config` no template — fora de escopo aqui.

## Pontos abertos pra etapas futuras

- **Etapa 5 (score consolidado)**: revisitar se cargas viram penalidade contínua no score ou continuam hard filter. Memória `feedback_etapa4_cargas_hard_filter.md` registrada pra cross-session.
- **Auto-popular form de cargas com valor salvo**: ler `opcoes_globais.cargas_config` no template `treinos.html` e setar `selected` nos selects. Pequeno, fora de escopo Etapa 4.
- **QA mobile com browser real**: smoke test feito via curl confirmou HTTP 200 + selects no HTML. Validação visual em DevTools mobile (375x667 iPhone SE) fica pra revisão manual do usuário antes de mergear.
- **Threshold mais apertado opcional**: hoje só 1.1% das rotinas disparam aviso. Se prática mostrar que isso é pouco, threshold pode ir pra 5/4/5 ou similar — basta rodar harness com novos thresholds e revalidar.

## Critério de "feito" — checklist

- [x] Sub-PR 0.1 — 3 campos no dataclass + helper `_int_or_zero` + `carregar_banco`
- [x] Sub-PR 0.2 — `_bloqueio_cargas` helper puro standalone
- [x] Sub-PR 0.3 — harness `recalibrar_cargas_hib2.py` + 20 casos clínicos pós-Etapa 3
- [x] Aprovação clínica do usuário (HIB2 6/5/6 mantido)
- [x] Sub-PR 1.1 — filtro integrado em `pode_adicionar_ao_bloco` (default OFF)
- [x] Sub-PR 1.2 — `cargas_config` plumbado pelas 6 funções + snapshot HIB2
- [x] Sub-PR 1.3 — aviso `relaxado_carga` via second-pass em `montar_blocos`
- [x] Sub-PR 1.4 — Flask `/gerar` e `/regerar` leem `cargas_config` do form
- [x] Sub-PR 2.1 — 3 selects de carga em `<details>` mobile-first
- [x] Sub-PR 2.2 — modal renderiza `relaxado_carga` + `ancora_nao_cumprida` + `ancora_sem_candidatos` (R3 da Etapa 3)
- [x] Sub-PR 2.3 — persistência verificada (round-trip JSON preserva `cargas_config`; sem código novo)
- [x] `pytest` em < 30s, 0 falhas (atual: 147 passed, 1 skipped, 1 xfailed em 2.77s)
- [x] Recalibração HIB2 sobre base nova: 20 casos clínicos validados pelo usuário
- [x] Blocos solo forçados por carga: 0.35pp (target < 5%)
- [x] Bloqueios clinicamente justificados: 3/3 pares persistentes são lombar pesado entre cadeia posterior — validados
- [x] Snapshots Etapa 3 estáveis (cargas_config=None default mantém comportamento)
- [x] `docs/refatoracao/logs/etapa_4.md` escrito
- [x] Atualização do guia v4 (header de progresso)
