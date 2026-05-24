# Log — MVP Fatia 4.E cargas: cargas_config no motor CSP

**Data**: 2026-05-24
**Branch**: `fatia-4e-cargas-config` (a partir de `main`)
**Arquivos modificados**:
- `gerador_csp.py` (novos args `cargas_config` + `peso_cargas_off` em `_construir_modelo` e 4 wrappers; H-cargas par-a-par no bloco; BoolVar `cargas_off_b[(t,b)]` por bloco; pré-processo de pares violadores; novo helper `_avisos_carga_por_treino` pra decoding pós-solve; `_SolucoesCollector` ganhou captura de `cargas_off_b` por solução)
- `app_flask.py` (`treino_regerar` lê `cfg_r["cargas_config"]` e propaga pra `gerar_treino_csp`; `_resultado_csp_pra_sessao` propaga `avisos_carga` pra `Sessao.avisos`)
- `tests/test_cargas_config_csp.py` (novo, 13 testes cobrindo 12 decisões clínicas + helpers internos)
- `tools/smoke_cargas_config.py` (novo, smoke E2E sem servidor — espelhando `tools/smoke_travados.py`)
- `docs/refatoracao/catalogo_constraints.md` (H-cargas adicionada na Seção 1 escopo BLOCO; nomenclatura `carga_*` consolidada na Seção 4)
- `docs/refatoracao/roadmap_csp.md` (Fatia 4.E cargas marcada ✅)

**Status**: ✅ concluída — gate verde (pytest 285 + 1 skipped = 272 base + 13 novos; harness 16/16 OK preservado; smoke E2E 5 cenários × 10 runs com avisos onde esperado).

---

## Objetivo

Fechar a segunda micro-frente do Bloco 1 do roadmap: portar o filtro hard
de **cargas par-a-par dentro do bloco** do motor antigo
(`gerador_treino._bloqueio_cargas`) pro motor CSP novo. Réplica clínica
fiel, com graceful degradation por bloco e divergência intencional sobre
travados.

Escopo MVP:
- 3 dimensões hard-coded: `grip`, `lombar`, `core` (atributos `carga_grip`,
  `carga_lombar`, `demanda_core`).
- Threshold por dim configurável via `cargas_config` dict; ausente / 0
  pula a dim.
- BoolVar `cargas_off_b[(t,b)]` por bloco — solver desliga só quando
  inviável (penalty `peso_cargas_off=1000` no objetivo).
- Avisos `relaxado_carga` emitidos por par violador efetivamente
  atribuído num bloco com filtro desligado.
- Travados PARTICIPAM dos pares (divergência intencional do antigo).

## Decisões fechadas (handoff inicial + validações durante implementação)

1. **Modelagem par-a-par dentro do bloco** (não cumulativa). Mirror do
   `_bloqueio_cargas` antigo. Para cada par (a,b) no mesmo bloco e cada
   dim d com `thr[d] > 0`: bloqueia se `a≥1 AND b≥1 AND (a+b) ≥ thr[d]`.

2. **Graceful degradation POR BLOCO** (não por treino, não por rotina).
   BoolVar `cargas_off_b[(t,b)]` por bloco; default `False` (filtro
   ativo); ligada (`True`) só quando solver não acha solução evitando
   pares violadores. Penalty `peso_cargas_off=1000` no objetivo garante
   que solver só desligue quando estritamente necessário.

3. **Travados ENTRAM nos pares** (divergência intencional do antigo).
   Pool_slot de 1 elemento (4.D) garante "travado nunca some"
   naturalmente: se par travado+non-travado viola, motor é forçado a
   trocar o non-travado (o travado é fixado pela cardinalidade 1). Par
   travado-travado violador no mesmo bloco → cargas_off_b=True + aviso.

4. **Default `cargas_config=None` ou `{}` ou todas dims 0 = constraint
   inteira pulada**. Preserva 4.D byte-a-byte; nenhuma BoolVar criada;
   nenhuma constraint adicionada ao modelo.

5. **Decoder analítico pós-solve** (`_avisos_carga_por_treino`). Para
   cada par violador (pré-processado), confere: (a) cidx correto
   atribuído em ambos slots; (b) ambos no mesmo bloco efetivo; (c)
   `cargas_off_b=True` naquele bloco. Se todas satisfeitas, emite aviso
   com motivo (`dim, soma, threshold`). Dedup por
   `(bloco, frozenset({nome_a, nome_b}))` — múltiplos motivos de dim no
   mesmo par viram 1 aviso só (primeira dim violada wins, igual antigo).

6. **`peso_cargas_off` parametrizável** (default 1000). Permite calibrar
   trade-off "rigidez vs graceful" futuramente via harness.
   `_resolver_com_variedade` ajusta o `teto` do `var_total` pra acomodar
   o peso (poderia explodir o IntVar bound sem isso).

## O que foi implementado

### `gerador_csp.py` — H-cargas + decoding pós-solve

**Constantes novas** (~linha 130):
```python
_DIMS_CARGA_CSP: tuple[tuple[str, str], ...] = (
    ("grip", "carga_grip"),
    ("lombar", "carga_lombar"),
    ("core", "demanda_core"),
)
```
Espelha `_DIMS_CARGA` do antigo exatamente. Atributo `demanda_core`
mantido por retrocompat com banco existente (não `carga_core`).

**Helpers** (~linha 142):
- `_cargas_config_ativo(cargas_config)`: True quando ≥1 dim tem
  threshold > 0. Pula constraint inteira quando inativo.
- `_viola_carga_par(ex_a, ex_b, cargas_config)`: retorna
  `(dim, soma, threshold)` da PRIMEIRA dim violada, ou None.

**Pré-processamento dentro de `_construir_modelo`** (~50 linhas novas):
Para cada treino, percorre par-a-par (s1, s2) e produto cartesiano de
candidatos (c1 ∈ pool_slot[s1] × c2 ∈ pool_slot[s2]). Identifica
violadores via `_viola_carga_par`, guarda em
`pares_violadores_por_treino[t_idx]`. Cria `cargas_off_b[(t,b)]` por
bloco do treino.

**Constraint principal** (linearização do AND de 4 BoolVars):
```python
assign[(s1, c1)]
+ assign[(s2, c2)]
+ slot_to_bloco_vars[s1][b]
+ slot_to_bloco_vars[s2][b]
- 3
<= cargas_off_b[(t_idx, b)]
```
Quando os 4 são True (lado esquerdo = 1), força `cargas_off_b[b] = 1`.
Quando ≤3 True (lado esquerdo ≤ 0), restrição trivialmente satisfeita
(cargas_off_b livre = 0 por padrão pelo objetivo).

**Penalty no objetivo**:
```python
pen_carga = peso_cargas_off * cargas_off_b[(t_idx, b)]
penalidades.append(pen_carga)
```
Default `peso_cargas_off=1000`.

**Decoding pós-solve** (`_avisos_carga_por_treino`, ~70 linhas novas):
Espelha analiticamente o motor antigo (`gerador_treino.py:1469-1516`).
Para cada par pré-identificado, confere se foi efetivamente atribuído +
caiu no mesmo bloco + bloco está com filtro desligado. Emite aviso
`relaxado_carga` deduplicado.

**Propagação nos wrappers**:
- `gerar_rotina_csp`: novos args `cargas_config` + `peso_cargas_off`,
  propagados pras 2 fases do `_resolver_com_variedade` e pro
  `_resolver_legacy`. Saída ganha chave `avisos_carga_por_treino:
  dict[int, list[dict]]`.
- `gerar_treino_csp`: novos args; saída ganha `avisos_carga: list[dict]`
  (extraído de `avisos_carga_por_treino[0]`).
- `_SolucoesCollector`: ganha arg `cargas_off_b`; captura `cargas_off`
  por solução pra decoder usar na ramificação variedade.

### `app_flask.py` — wire em `treino_regerar`

```python
# Fatia 4.E cargas: extrai cargas_config da cfg (UI antiga).
cargas_cfg = cfg_r.get("cargas_config")

resultado = gerar_treino_csp(
    demandas_csp, banco_regen, nivel_aluno=nivel,
    seed=..., variedade=ConfigVariedade(),
    ...
    cargas_config=cargas_cfg or None,  # Fatia 4.E cargas
)
```

E em `_resultado_csp_pra_sessao`:
```python
# Fatia 4.E cargas: propaga avisos `relaxado_carga` emitidos pelo motor.
for av in resultado.get("avisos_carga", []) or []:
    s.avisos.append(av)
```

Docstring de `treino_regerar` atualizada — `cargas_config` removida da
lista de "features ignoradas".

### `tests/test_cargas_config_csp.py` — 13 testes

| Teste | Cobertura |
|---|---|
| `test_cargas_config_none_preserva_comportamento` | (a) Default None preserva 4.D byte-a-byte |
| `test_cargas_config_vazio_ou_zeros_pulada` | (b) Dict vazio / todas zeros pulada |
| `test_par_valido_nao_dispara_aviso` | (c) Threshold permissivo: nenhum aviso |
| `test_par_violador_resoluvel_sem_aviso` | (d) Tam_pref=1 (solos) sem violação |
| `test_par_violador_irresoluvel_emite_aviso` | (e) Banco mini de costas + thr=4: aviso correto com motivo |
| `test_travado_entra_nos_pares_non_travado_muda` | (f) Travado heavy força non-travado a mudar |
| `test_dois_travados_violadores_mantem_e_emite_aviso` | (g) Travado-travado: ambos mantêm + aviso |
| `test_threshold_zero_em_uma_dim_pula_so_aquela` | (h) Só dim ativa dispara |
| `test_composicao_com_4b_4c_sem_regressao` | (i) Composição com 4.B/4.C: sem crash |
| `test_viola_carga_par_helper` | (j) Helper `_viola_carga_par` espelha antigo |
| `test_cargas_config_ativo_helper` | (j) Helper `_cargas_config_ativo` |
| `test_cargas_config_com_variedade_ativa` | (k) ConfigVariedade (modo /regerar real) |
| `test_rotina_propaga_avisos_carga_por_treino` | (l) Rota N treinos propaga avisos por treino |

### `tools/smoke_cargas_config.py` — smoke E2E

5 cenários × 10 runs cada usando modo padrão de `/regerar`
(ConfigVariedade). Cenários:

| Cenário | Esperado |
|---|---|
| 1. Filtro OFF (regressão) | 0 avisos |
| 2. Filtro permissivo (thr=6) | 0-poucos avisos |
| 3. Filtro restritivo (thr=4) | 0-poucos avisos (banco rico acha alternativa) |
| 4. Banco mini costas + thr=4 + par forçado | 10/10 avisos (inviável) |
| 5. Filtro + 2 travados heavy no mesmo bloco | 10/10 avisos (par travado-travado) |

## Resultado da validação

### Smoke E2E (10 runs por cenário, modo /regerar com variedade)

| Cenário | Avisos esperados | Avisos observados |
|---|---|---|
| 1. Filtro OFF | 0 | 0/10 ✓ |
| 2. Filtro permissivo (thr=6) | 0-poucos | 0/10 ✓ |
| 3. Filtro restritivo (thr=4) | 0-poucos | 0/10 ✓ |
| 4. Banco mini + thr=4 + par forçado | 10/10 | 10/10 ✓ |
| 5. 2 travados heavy + par forçado | 10/10 | 10/10 ✓ |

Cenários 3 e 4 mostram a **inteligência do motor declarativo**: com banco
rico (cenário 3), CSP acha pareamento legal sem desligar filtro mesmo
com thr restritivo (não emite aviso). Com banco mini (cenário 4), motor
**não tem alternativa** (H-R1 exige par compound; todos compound têm
grip≥2) — aí desliga e emite aviso.

### Gate de fechamento

| Métrica | Resultado |
|---|---|
| pytest | **285 passed + 1 skipped** (=272 pré-4.E cargas + 13 novos) ✓ |
| 13 snapshots | ✓ preservados |
| harness | **16/16 OK** (2.3 + 4.1 NO-OPs informativos preservados) ✓ |
| Smoke E2E | 5/5 cenários, avisos onde esperado ✓ |
| Gerador antigo | Intocado ✓ |
| Default behavior | `cargas_config=None` ou `{}` ou zeros → byte-a-byte pré-4.E cargas ✓ |

## Decisões fechadas (pra próximas frentes)

1. **`cargas_config=None` default em todas as funções do CSP**. Preserva
   4.D byte-a-byte sem flag explícito.

2. **`peso_cargas_off=1000` é parametrizável** mas não exposto na UI no
   MVP. Harness de calibração pode variar; UI não muda.

3. **Avisos `relaxado_carga` deduplicados** por `(bloco, frozenset({nomes}))`.
   Múltiplos motivos de dim → 1 aviso só (primeira dim wins). Igual antigo.

4. **Slot travado tem pool_slot de 1**, então par travado+non-travado
   violador SEMPRE força non-travado a mudar (não trava o motor). Par
   travado-travado violador no mesmo bloco SEMPRE aciona cargas_off_b
   (decisão deliberada do user > regra automática).

5. **`bloco_idx` retornado no aviso é o ÍNDICE LÓGICO** (0..max_b-1) do
   treino — mesmo IntVar que `_decode_solucao` usa pra agrupar blocos.
   `Sessao.blocos` cronologicamente alinha com isso quando renderizado;
   adapter não precisa remapear.

6. **Constraint pulada quando cargas inativo** evita 0 BoolVars / 0
   constraints novas no modelo. Sanity de regressão garante.

7. **Decoder roda em 2 momentos**: legacy resolve solver.Value() pós-Solve;
   variedade captura no callback (1 dict por solução enumerada), aplica
   só na solução escolhida pelo softmax.

## Achados / sinais de alerta

1. **Banco real rico raramente força desligamento**. Cenários 2 e 3 do
   smoke mostram que o motor declarativo é muito eficaz em achar
   pareamentos legais — só travados ou bancos artificialmente
   restritivos forçam avisos. Isso É O COMPORTAMENTO CORRETO: o filtro
   reflete intenção clínica do user; quando o banco tem ar, o user nem
   sabe que o filtro tava ativo (vê só rotinas limpas).

2. **Trade-off "filtro restritivo + tam_pref=2 + banco rico"** =
   motor naturalmente migra pra blocos solo SE peso de S-B4 for baixo.
   Quando peso é alto, motor escolhe pares legais OU desliga.
   Comportamento consistente com semântica: usuário paga peso de tamanho
   pra forçar par; motor honra ou degrada com aviso.

3. **Constraint H-cargas vs S-B2** (futura, balanço cumulativo soft):
   complementares, não conflitantes. H-cargas é gate par-a-par binário
   por dim; S-B2 é soma cumulativa por bloco, modulável por perfil. Quando
   S-B2 entrar (pós-cadastro de demanda lombar — já existe! ver atualização
   no catálogo), as duas convivem sem refator: H-cargas filtra
   pares óbvios; S-B2 ajusta o resto.

4. **Nomenclatura `demanda_grip` no catálogo era incorreta** (antes da
   Fatia 4.E cargas). Coluna real é `carga_grip` (mirror do antigo).
   Corrigido na Seção 4 do catálogo + nota explicativa na S-B2.

5. **Tempo de pytest cresceu modestamente** 27.71s pré-4.E cargas →
   28.11s pós. Adição de 13 testes + ramificação `_construir_modelo`
   negligível. Ainda <30s.

6. **`/regerar` agora cobre paridade quase total com motor antigo**:
   tamanho_bloco (4.C) + evitar_agonistas (4.B) + exercicios_travados
   (4.D) + relaxar_familia (4.E) + **cargas_config (4.E cargas)** +
   Aderência (Frente D) + variedade (Frente B). Restam só
   `lateralidade_por_padrao` (mas split squat continua coberto pelo
   `_expandir_demanda_csp`).

## Próximos passos

- **Bloco 1 do roadmap concluído** — todas as 3 micro-frentes paralelas
  (travados, cargas_config, relaxar_familia) entregues. Pré-requisito
  pra Bloco 2 (Frente E.0 — harness comparativo) está satisfeito.
- **Bloco 2 (Frente E.0)**: harness comparativo CSP × antigo. Pode
  iniciar imediatamente.
- **UI pra cargas_config** — UI antiga não tem controle exposto;
  `cargas_config` vem da cfg apenas via persistência (rascunho/sessões).
  Quando UI for construída, ela monta `cfg_r["cargas_config"]` (já
  consumido pelo adapter) e tudo passa a fluir end-to-end. Sem ação
  bloqueante aqui.
