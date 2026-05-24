# Log — MVP Fatia 4.E: relaxar_familia no motor CSP

**Data**: 2026-05-24
**Branch**: `fatia-4e-relaxar-familia` (a partir de `main`)
**Arquivos modificados**:
- `gerador_csp.py` (novo `_familia_cross`, args `familias_proibidas`/`relaxar_familia` em `_construir_modelo`/`_resolver_legacy`/`_resolver_com_variedade`/`gerar_rotina_csp`/`gerar_treino_csp`; helper `_identificar_relaxados_por_familia`; retry de 2 fases em `gerar_rotina_csp`; saída expõe `relax_ativado`/`relaxados_por_treino`; fix `AddBoolOr([])` quando pool vazio)
- `app_flask.py` (`treino_regerar` substitui filtro upstream de família por `familias_proibidas` no motor; lê `relaxar_familia` do `cfg_r`; `_resultado_csp_pra_sessao` consome `resultado["relaxados"]` propaga pra `Sessao.relaxados` + gera avisos `familia_repetida`)
- `tests/test_relaxar_familia_csp.py` (novo, 9 testes cobrindo 9 decisões clínicas)
- `tools/smoke_relaxar_familia.py` (novo, smoke E2E sem servidor)

**Status**: ✅ concluída — gate verde (pytest 272 + 1 skipped = 263 base + 9 novos; harness 16/16 OK; smoke E2E 5 cenários × 10 runs com comportamento esperado em 100% dos casos).

---

## Objetivo

Implementar `relaxar_familia` no motor CSP novo, fechando a 2ª micro-frente do Bloco 1 do roadmap. Backend antigo já suporta a feature; adapter da Frente C ignorava (`docstring` da rota mencionava explicitamente "feature ignorada"). Esta frente fecha paridade.

Visão clínica: por default, app evita repetir variações da mesma família entre os treinos da rotina. Em rotinas apertadas (banco pequeno, demandas que esgotam famílias disponíveis), isso pode tornar impossível preencher. Toggle "Relaxar família se necessário" (UI default ON) ativa rede de segurança: motor tenta estrito primeiro, e só relaxa se necessário. Exercícios escolhidos no relax recebem badge `↻` no card + aviso `familia_repetida` no modal.

## Decisões fechadas (AskUserQuestion inicial)

1. **Modelagem: motor-side** (Opção B — decisão delegada, justificada pelos princípios do norte). Adapter passa `familias_proibidas` + `relaxar_familia` pro motor; motor decide hard/relax internamente.

   Razões da escolha B sobre A (adapter refaz chamada quando inviável):
   - **Coerência declarativa** (norte Seção 5) — cross-treino de família vira problema do solver, não filtro upstream que reintroduz o anti-padrão "patch em cascata".
   - **Generalização natural** do AllDifferent cross-treino que já existe pra nomes (pré-filtra `pool_slot` pelo mesmo mecanismo da 4.D pra `nomes_travados`).
   - **Prepara Frente E.1**: quando `/gerar` passar pro CSP, o adapter não terá "outros treinos" pra filtrar — eles serão criados pelo motor. Bloqueio cross-treino TEM que viver no motor. Fazer agora é menos código no final.

2. **Default UI: continua ON** (desktop + mobile). Paridade total com motor antigo — UI já é `checked` em `templates/treinos.html:144` e `:390`. Personal que sempre ignorou o toggle continua tendo rede de segurança.

3. **Forma do aviso: por exercício relaxado** (paridade antigo). 1 entrada `{tipo: "familia_repetida", exercicio, familia, escopo_label}` por nome relaxado em `sessao.avisos`. Template `_avisos_modal.html` já tem branch dedicado renderizando lista por-ex; badge `↻` no card via `sessao.relaxados`. **Zero código novo de UI.**

## O que foi implementado

### `gerador_csp.py` — `_familia_cross` + args nos resolvers + retry

Novo helper de identidade de família cross-treino (mais agressivo que H-T1 intra — cobre pai+filho):

```python
def _familia_cross(ex: Exercicio) -> str:
    """Identificador de família pra bloqueio CROSS-treino. Pai concentra
    filhos: ex.variacao_de quando filho, ex.nome quando pai (variacao_de
    vazio)."""
    return ex.variacao_de or ex.nome
```

`_construir_modelo` ganha arg `familias_proibidas: Optional[set[str]] = None`. Filtro estendido em `pool_default_sem_travados`:

```python
pool_default_sem_travados = [
    e for e in pool_default
    if e.nome not in nomes_travados
    and _familia_cross(e) not in fams_proibidas
]
```

Travados bypassam (slot dedicado tem `pool_slot = [ex_travado]`, fora desse filtro — mesma técnica da 4.D).

Fix necessário: quando filtro esvazia o pool (caso real: `knee_extension` com `familias_proibidas={"Cadeira Extensora"}`), `AddExactlyOne([])` é no-op e modelo fica trivialmente "viável" mas decode explode com `KeyError`. Solução:

```python
if bvars:
    model.AddExactlyOne(bvars)
else:
    model.AddBoolOr([])  # força inviabilidade trivial
```

Helper novo `_identificar_relaxados_por_familia(rotina, familias_originais, travados_por_treino)`:

```python
for t_idx, treino in enumerate(rotina["treinos"]):
    for grupo in treino["grupos"]:
        for ex in grupo["exercicios"]:
            if (t_idx, ex.nome) in travados_set:
                continue  # travado bypassa (decisão deliberada do user)
            if _familia_cross(ex) in familias_originais:
                nomes_rel.append(ex.nome)
```

Retry de 2 fases em `gerar_rotina_csp`:

```python
fams_originais = set(familias_proibidas or [])
rotina = _resolver(fams_originais if fams_originais else None)
if rotina["viavel"] or not fams_originais or not relaxar_familia:
    rotina["relax_ativado"] = False
    rotina["relaxados_por_treino"] = {}
    return rotina
# 2ª passagem sem filtro
rotina_relax = _resolver(None)
if not rotina_relax["viavel"]:
    rotina["relax_ativado"] = False
    rotina["relaxados_por_treino"] = {}
    return rotina
relaxados = _identificar_relaxados_por_familia(rotina_relax, fams_originais, travados_por_treino)
rotina_relax["relax_ativado"] = True
rotina_relax["relaxados_por_treino"] = relaxados
return rotina_relax
```

Closure `_resolver(fams_arg)` despacha pra `_resolver_legacy` ou `_resolver_com_variedade` conforme `variedade is None`. Ambos resolvers ganham o arg, propagam pra `_construir_modelo`.

Wrapper `gerar_treino_csp` (1 treino) extrai `relaxados_por_treino.get(0, [])` e expõe como `relaxados: list[str]` + `relax_ativado: bool` no top-level. Default None / vazio preserva 4.D byte-a-byte.

### `app_flask.py` — adapter `treino_regerar` (substitui filtro upstream)

Antes (Frente C): filtro upstream removendo nomes + famílias dos outros treinos do `banco_regen`.

```python
# Pré-4.E:
banco_regen = [e for e in banco if e.nome not in nomes_outros
               and e.nome not in pais_dos_outros
               and (e.variacao_de is None or e.variacao_de not in nomes_outros)]
```

Pós-4.E: filtro só de nomes (AllDifferent local); famílias viram `familias_proibidas` pro motor.

```python
exs_outros = [...]
nomes_outros = {ex.nome for ex in exs_outros}
familias_outros = {_familia_cross(ex) for ex in exs_outros}
banco_regen = [e for e in banco if e.nome not in nomes_outros]
...
resultado = gerar_treino_csp(
    demandas_csp, banco_regen, nivel_aluno=nivel,
    ...
    familias_proibidas=familias_outros or None,
    relaxar_familia=bool(cfg_r.get("relaxar_familia", True)),  # UI default ON
)
```

Cfg fallback (rotina importada sem `cfg_r` gravada) ganha `"relaxar_familia": True` pra paridade.

`_resultado_csp_pra_sessao` aceita arg opcional `escopo_labels` e propaga `resultado["relaxados"]` pra `Sessao.relaxados` + `Sessao.avisos`:

```python
relaxados_nomes = list(resultado.get("relaxados") or [])
if relaxados_nomes:
    s.relaxados = list(relaxados_nomes)
    for nome_rel in relaxados_nomes:
        ex_rel = ex_por_nome.get(nome_rel)
        familia = ex_rel.variacao_de if (ex_rel and ex_rel.variacao_de) else nome_rel
        s.avisos.append({
            "tipo": "familia_repetida",
            "exercicio": nome_rel,
            "familia": familia,
            "escopo_label": labels.get(nome_rel) or ex_rel.subregiao,
        })
```

UI consome `sessao.relaxados` em `_treino_card.html:123` e `_hub_treino_card.html:68` (badge `↻`) e `_avisos_modal.html:60-75` (lista no modal) — **zero código novo de template**.

### `tests/test_relaxar_familia_csp.py` — 9 testes

| Teste | Decisão clínica coberta |
|---|---|
| `_familia_cross_pai_e_filho` | (a) helper cobre `variacao_de` vazio (pai) e não-vazio (filho) |
| `familias_proibidas_filtra_pool` | (b) filtra pool quando estrito é viável |
| `estrito_inviavel_sem_relax` | (c) inviável + `relaxar_familia=False` → motor devolve inviável |
| `estrito_inviavel_com_relax_aciona` | (d) inviável + `relaxar_familia=True` → relax dispara, marca relaxados |
| `sem_familias_proibidas_preserva_pre_4e` | (e) `None`/vazio → comportamento pré-4.E |
| `estrito_viavel_relax_nao_dispara` | (f) estrito viável → relax NÃO ativa mesmo com flag ON |
| `travado_bypassa_e_nao_eh_relaxado` | (g) travado supera `familias_proibidas` + não vai pra relaxados |
| `wrapper_treino_expoe_relaxados` | (h) wrapper 1-treino expõe `relaxados`+`relax_ativado` top-level |
| `relax_com_variedade_ativa` | (i) funciona em modo `ConfigVariedade` (modo /regerar) |

Cenários (c) e (d) usam `knee_extension` (1 família "Cadeira Extensora", 1 ex) — caso ideal pra forçar inviabilidade absoluta no estrito.

### `tools/smoke_relaxar_familia.py` — smoke E2E sem UI

5 cenários × 10 runs cada usando o modo padrão de `/regerar` (`ConfigVariedade()` + `gerar_treino_csp`). Substituto da validação browser pra exercitar o caminho do adapter sem servidor Flask.

## Resultado da validação

### Smoke E2E (10 runs por cenário, modo `/regerar` com variedade)

| Cenário | Viáveis | `relax_ativado` | Com `relaxados` não-vazio |
|---|---|---|---|
| 1. Estrito viável (banco rico, proíbe 1 família de 4) | 10/10 | 0/10 | 0/10 |
| 2. Estrito inviável + relax ON (knee_extension proibido) | 10/10 | **10/10** | **10/10** (todos com "Cadeira Extensora") |
| 3. Estrito inviável + relax OFF (mesmo cenário) | 0/10 | 0/10 | 0/10 |
| 4. Travado bypassa filtro de família | 10/10 | 0/10 | 0/10 (travado entrou direto) |
| 5. Sem `familias_proibidas` (regressão pré-4.E) | 10/10 | 0/10 | 0/10 |

100% de comportamento esperado em todos os cenários, em todas as 50 runs.

### Gate de fechamento

| Métrica | Resultado |
|---|---|
| pytest | **272 passed + 1 skipped** (=263 pré-4.E + 9 novos) ✓ |
| 13 snapshots | ✓ preservados |
| harness | **16/16 OK** (2.3 + 4.1 NO-OPs informativos preservados) ✓ |
| Smoke E2E | 5/5 cenários, 50/50 runs com comportamento esperado ✓ |
| Gerador antigo | Intocado ✓ |
| Default behavior | `familias_proibidas=None` ou vazio → byte-a-byte comportamento pré-4.E ✓ |

## Decisões fechadas (pra próximas frentes)

1. **`familias_proibidas` default `None`** em todas as funções do CSP. Preserva 4.D byte-a-byte sem flag explícito. `None` ou `set()` ⟹ filtro inativo.

2. **`relaxar_familia` default `False`** no motor (paramétrico). Toggle ON é responsabilidade do adapter (que lê `cfg_r["relaxar_familia"]`, default `True` pra paridade UI). Mantém motor "conservador por default" sem mudar paridade UI.

3. **Identidade de família CROSS é mais agressiva que H-T1 intra**. `_familia_cross(ex) = ex.variacao_de or ex.nome` cobre pai+filho (3 casos do filtro pré-existente do adapter). H-T1 intra continua estrito (filhos do mesmo pai apenas; comentário em `gerador_csp.py:24` preservado).

4. **Travado SEMPRE supera `familias_proibidas`**. Mesmo princípio da 4.D — decisão deliberada do user vence regra automática. Implementação: slot travado tem `pool_slot = [ex_travado]` (fora do filtro de família); `_identificar_relaxados_por_familia` pula travados.

5. **2 solves no pior caso** (relax dispara). Custo aceitável — cada solve em `/regerar` é sub-segundo. Pra Frente E.1 (rotina inteira via /gerar), continuará sub-segundo na ordem de magnitude que o motor processa hoje.

6. **Fix `AddBoolOr([])` pra pool vazio é defensivo**, não específico da 4.E. Qualquer filtro futuro que possa esvaziar `pool_slot` (ex: H-X restrições físicas) se beneficia.

## Achados / sinais de alerta

1. **Adapter `treino_regerar` agora SÓ filtra nomes (AllDifferent local)**. Famílias viraram constraint do motor. Próxima iteração natural: AllDifferent cross-rotina também migrar pro motor quando Frente E.1 fizer `/gerar` usar CSP — adapter para de filtrar `nomes_outros` upstream porque os outros treinos serão criados pelo solver junto.

2. **`/regerar` agora cobre paridade COMPLETA com motor antigo no que diz respeito a regras estruturais**: tamanho_bloco (4.C), evitar_agonistas (4.B), exercicios_travados (4.D), relaxar_familia (4.E), Aderência (Frente D), variedade (Frente B). Falta só `cargas_config` (última micro-frente do Bloco 1).

3. **Aviso `familia_repetida` no modal pode aparecer agora em `/regerar`** — antes só aparecia em `/gerar` (motor antigo). Comportamento intencional: rede de segurança visual igual nos 2 fluxos.

4. **Modal de avisos auto-abre via IIFE no `_avisos_modal.html`** quando `avisos_por_treino` é não-vazio. Mas `_avisos_modal.html` é incluído só em `_resultado.html` e `hub.html` (fluxo de geração + redirect); `/regerar` retorna `_treino_card.html` direto. Avisos novos da 4.E ficam em `Sessao.avisos` mas não disparam modal em `/regerar` — só ficariam visíveis num refresh do HUB. Aceitável pra MVP — badge `↻` no card já comunica o relaxamento visualmente.

5. **Default `cfg_r["relaxar_familia"]=True` em fallback de cfg legada** — quando o personal regera um treino numa rotina importada sem `cfg_r` gravada, o motor assume comportamento "rede de segurança ON" (paridade UI). Documentado no comentário do `cfg_r` fallback.

## Próximos passos

- **1 micro-frente restante do Bloco 1** (`cargas_config`) — última peça pra paridade total `/regerar`. Pré-requisito completo pra Frente E.0 (harness comparativo) após essa.
- **Frente E.0** (Bloco 2) — harness comparativo CSP × antigo. Pode entrar imediato após cargas_config.
- **Modal de avisos em `/regerar`** — pendência menor de UX. Quando `relax_ativado=True` em `/regerar`, idealmente o frontend deveria pop um toast/banner curto avisando. Não bloqueia uso real (badge `↻` no card já cumpre).
- **UI pra travar exercício** — continua pendência CLAUDE.md, fora do refator CSP.
