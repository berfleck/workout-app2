# Log — Frente E.1 (substituir `/gerar` pelo motor CSP)

**Data**: 2026-05-26
**Branch**: `frente-e-1` (a partir de `main`)
**Bloco**: 3 do roadmap CSP — substituição final do caminho de execução de
`/gerar`. Pré-requisitos Frente E.0 (Bloco 2) + Micro-frente H-A1 (Bloco 2.5)
concluídos e em `main`.

**Arquivos atualizados**:

- `app_flask.py` — import de `gerar_rotina_csp`; 4 helpers novos
  (`_tipo_label_da_cfg`, `_treino_dict_csp_pra_sessao`,
  `_primeiro_treino_por_subregiao`, `_distribuir_avisos_rotina_csp`);
  refator do corpo de `gerar()` substituindo `gerar_multiplos_treinos`
  por orquestração `gerar_rotina_csp` + decode. `_regerar_motor_legacy`
  permanece como referência viva pra rollback rápido (não chamado em
  runtime — paridade com a estratégia da Frente C).
- `templates/_avisos_modal.html` — 2 clauses novas: `h_a1_degradado`
  (âncora obrigatória sem candidatos) e `h_r1_degradado` (distribuição
  clínica de eixos degraded). Cobre tanto a Frente C (`/regerar`,
  populado desde 2026-05-23 sem render) quanto a Frente E.1 (`/gerar`).
  Cabeçalho "gerado com restrições" agora dispara também por h_*_deg.
- `tests/test_gerar_csp_adapter.py` — 21 testes novos cobrindo helpers
  novos do adapter + integração mínima com `gerar_rotina_csp`.
- `docs/refatoracao/roadmap_csp.md` — Bloco 3 marcado ✅; Bloco 4
  (refinamentos pós-E.1) ganha 2 follow-ups (lentidão ABC 3T + cadastro
  variações bíceps com `variacao_de` distinto).
- `MEMORY.md` + memória nova `project_frente_e1_substituir_gerar.md`.

**Status**: ✅ concluída — todos os critérios do handoff atendidos.
Aguardando aprovação do Bernardo para merge em `main` (disciplina de
merge do roadmap exige confirmação explícita).

---

## Objetivo

Substituir `/gerar` (geração inicial de rotina) pelo motor CSP, seguindo o
padrão de adapter já estabelecido em `/regerar` na Frente C. A chamada a
`gerar_multiplos_treinos` (motor antigo greedy) sai do caminho de execução
da rota; `gerar_rotina_csp` + `ConfigVariedade()` default assume o lugar.
Output normalizado preserva `Sessao` shape pra UI não precisar mudar.

## Decisões fechadas (handoff + AskUserQuestion inicial)

Via AskUserQuestion (4 perguntas), todas no início da sessão antes de
codar:

1. **Migração: clean break** (alinha com norte Seção 5). `/gerar` chama
   SEMPRE CSP, sem flag `?motor=legacy` ou checkbox. `_regerar_motor_legacy`
   helper continua no código pra referência/rollback, mas não é chamado.
2. **Bíceps família única: NO-OP nesta sessão**. As 6 variações
   compartilham `variacao_de="Rosca bíceps"`, então `biceps(2)` é
   INFEASIBLE no CSP. Aceito; ABC do harness E.0 usa `bracos(2)` (mistura
   bi+tri) e funciona normalmente. Não bloqueia E.1. Decisão clínica de
   cadastrar variações com `variacao_de` distinto fica pra frente futura.
3. **Avisos H-A1/H-R1 degraded: tipos separados** `h_a1_degradado` e
   `h_r1_degradado` em `Sessao.avisos`. Modal `_avisos_modal.html` ganha
   2 clauses novas (escopo pequeno, mesma sessão). Vantagem: payload
   claro por constraint, fácil de filtrar/estender no futuro.
4. **Toggle `usar_historico_r1` (UI ON/OFF): wirado como
   `familias_proibidas` hard cross-rotina**. CSP ainda não tem S-H1 soft
   (Bloco 4 do roadmap). Hard é a primitiva disponível mais próxima do
   intent ("evitar repetir família da R-1"); o retry de `relaxar_familia`
   (geralmente ON na UI) garante fallback quando inviável. Substitui o
   score soft D3.3 do motor antigo.

## O que foi implementado

### Helpers novos em `app_flask.py`

Análogos aos da Frente C, mas operando sobre a rotina inteira (saída de
`gerar_rotina_csp`, não `gerar_treino_csp`):

```python
def _tipo_label_da_cfg(cfg) -> str:
    """template → template_nome; hierarquia → "escopo(qtd) + ...";
    padrões legados → " + ".join(padroes); fallback → "Sessão"."""
```

```python
def _treino_dict_csp_pra_sessao(treino_dict, tipo_label) -> Sessao:
    """Converte 1 item de resultado["treinos"] em Sessao com blocos
    estruturados (Fatia 4.A). Marca cada ex com rationale={"gerador":
    "csp"} via dataclasses.replace — não muta banco. avisos/relaxados
    começam vazios; distribuição posterior popula."""
```

```python
def _primeiro_treino_por_subregiao(demandas_por_treino) -> dict[str, int]:
    """Mapa subregião → idx do primeiro treino com demanda associada.
    Roteia avisos cross-treino (h_r1/h_a1) ao treino certo (não duplica
    mensagem em todos os treinos). Suporta demanda nível padrão (via
    PADRAO_PARA_SUBREGIAO) e nível regiao (via REGIAO_PARA_SUBREGIOES)."""
```

```python
def _distribuir_avisos_rotina_csp(resultado, sessoes, demandas_por_treino):
    """Distribui:
    - h_r1_aplicadas[degraded=True] → aviso h_r1_degradado no treino com
      a subregião associada.
    - h_a1_aplicadas[degraded=True] → aviso h_a1_degradado análogo.
    - avisos_carga_por_treino[t] → sessoes[t].avisos.extend().
    - relaxados_por_treino[t] → sessoes[t].relaxados + avisos familia_repetida."""
```

### Refator do corpo de `gerar()`

Substitui o bloco que chamava `gerar_multiplos_treinos` por:

1. **Constrói `demandas_por_treino`** aplicando `_cfg_antiga_pra_demandas_csp`
   por cfg.
2. **Constrói `travados_por_treino: dict[int, list]`** a partir de
   `cfg["exercicios_travados"]` por treino (não-vazios).
3. **Calcula `familias_proibidas`** unindo:
   - Famílias dos exs de TODOS os outros treinos da rotina ativa quando
     ctx_acao=`substituir`/`adicionar` (preservando o filtro de irmãos
     existente, agora declarativo cross-rotina em vez de só filtragem
     no banco).
   - Famílias dos exs da rotina ativa quando `usar_historico_r1=True`
     (toggle ON — wire decidido nesta sessão).
4. **Mapeia pesos da UI antiga pros parâmetros do CSP**:
   - `evitar_agon` → `peso_evitar_agonistas = 10` (padrão `_PESO_EVITAR_AGONISTAS_DEFAULT`)
   - `tam_bloco` → `tamanho_preferido = 1/2/3`, `peso_tamanho_bloco = 5`
   - `relaxar_familia` → `relaxar_familia` (retry 2 fases)
   - `cargas_config` → `cargas_config` (H-cargas par-a-par + degradation)
   - Aluno → `nivel_aluno` (1/2/3), `peso_aderencia` (Frente D)
5. **Chama `gerar_rotina_csp`** com `variedade=ConfigVariedade()` default
   e `seed=random.randint(0, 2**31 - 1)`.
6. **Decodifica** via `_treino_dict_csp_pra_sessao` + `_distribuir_avisos_rotina_csp`.
7. **Fallback inviável**: devolve N treinos vazios + aviso global no
   treino 0 (preserva shape de `sessoes_ativas` pra UI não quebrar).

### Modal `_avisos_modal.html` — 2 clauses novas

`h_a1_degradado` (chip 🎯 azul): "Âncora obrigatória não pôde ser
garantida — subregião X: padrão âncora P ficou sem candidatos (motivo)".

`h_r1_degradado` (chip ⚖️ vermelho): "Distribuição clínica de eixos
não pôde ser garantida — subregião X (eixo Y): motivo".

Cabeçalho "gerado com restrições" agora inclui `hr1_deg or ha1_deg`
(antes só cargas/ancoras_*).

## Decisões de implementação

- **Avisos cross-treino → 1 treino específico** (não duplicar). `h_r1`
  e `h_a1` operam na rotina inteira no CSP, mas a UI mostra por treino.
  `_primeiro_treino_por_subregiao` deriva o mapa subregião → idx de
  treino; aviso vai pro primeiro treino com a subregião associada
  (primeiro wins). Fallback defensivo: treino 0 quando subregião não
  aparece em nenhum mapa (improvável, mas guardrail).
- **`familias_proibidas` cobre 2 fontes**: irmãos da rotina ativa
  (substituir/adicionar) + rotina ativa inteira (toggle R-1 ON). Union
  simples. Banco_gerar continua filtrado por NOME (preserva semântica
  imediata); set adicional bloqueia famílias inteiras.
- **`relaxar_familia` retry** já cobre o caso onde `familias_proibidas`
  inviabiliza a rotina (R-1 grande com banco apertado). UI default ON
  conhece esse padrão; toggle R-1 ON + relaxar_familia ON é coerente.
- **Inviabilidade total** vira aviso `h_r1_degradado` (não inventei tipo
  novo) com `subregiao="(rotina inteira)"`. Mensagem clara pro
  usuário ajustar demandas. Não acontece em rotinas normais — testado
  com Full Body 2T mais ABC 3T-like e ambos passam.

## Resultado da validação (gate de fechamento)

| Critério | Resultado |
|---|---|
| Pytest novo (21 testes do adapter `/gerar`) | ✅ 21/21 passed |
| Pytest baseline (297 → 318 esperado) | ✅ 318 passed + 1 skipped + 13 snapshots |
| Harness antigo (`tests/test_problemas_etapa.py`) | ✅ 11/11 (preservados) |
| Harness 16 cenários (`tools/calibrar_pesos_dimensoes.py`) | ✅ 16/16 OK (2 NO-OPs benignas preservadas: 2.3 e 4.1) |
| Smoke E2E `/gerar` Full Body 2T (peito+costas / ombro+bracos) | ✅ 8 ex distintos, blocos pareados, H-A1 cumprida (T2: ombro_composto + biceps + triceps), tempo subseg |
| Smoke modal de avisos | ✅ render OK em cenário inviável artificial (curl com demanda vazia) — chip ⚖️ "rotina inteira" como esperado |
| `_regerar_motor_legacy` preservado | ✅ helper mantido pra rollback |
| Motor antigo intocado | ✅ `gerador_treino.py` zero alterações |
| Motor CSP intocado | ✅ `gerador_csp.py` zero alterações |

## Achados / sinais de alerta

1. **ABC 3T continua ~25s/rotina no CSP** (achado da E.0 + H-A1
   preservado). Tempo aceitável pra hobby app (norte Seção 5). Otimização
   fica pra Bloco 4 se UI sentir. Outras configs (Full Body 2T,
   upper(3)×2T, perna_ant+post) ficam sub-segundo a poucos segundos.

2. **Bíceps família única é NO-OP estrutural** (decisão da sessão). UI
   com `biceps(2)` direto devolve INFEASIBLE → fallback de
   `Sessao.avisos = [h_r1_degradado motivo CSP inviável]` aparece no
   modal. Aluno entende o motivo. Discussão clínica de cadastrar
   `Rosca martelo` / `Rosca direta` com `variacao_de` distinto fica
   pra frente futura.

3. **`historico_r1` como hard substitui o soft D3.3**. Comportamento
   diferente do antigo: antigo desencorajava mas permitia repetição
   quando inevitável; novo proíbe e relaxa via retry quando inviável.
   Funcionalmente mais forte ("evita repetição" é o intent declarado).
   Caso edge: rotinas curtas (1 treino × 3 ex) com R-1 igual e
   `relaxar_familia=OFF` podem dar inviável onde antigo dava overlap
   parcial. Mitigação: UI já default `relaxar_familia=ON`; combinação
   problema é configuração explícita do usuário.

4. **Score HIST D3.3 obsoleto** no caminho de `/gerar` (motor antigo
   sai). Continua presente em `gerador_treino.py` (vivo até estado-alvo
   do norte). Memória `[[etapa-7]]` (Fase 7.4) preserva contexto
   histórico.

## Próximos passos

- **Bloco 4 do roadmap CSP** desbloqueado. Refinamentos não-bloqueadores:
  - **S-B2 / S-B3** — balanço de carga implícita / fadiga prévia.
  - **Centralidade Compostos** + **Densidade Pareamento** (2 dims novas
    do vetor de perfil).
  - **S-H1** — substituto soft do `usar_historico_r1` hard atual. Vai
    ser cobertura do repertório ao longo do tempo; modula score como
    D3.3 fazia no antigo.
  - **Captura de rationale no CSP** — destrava UI `/decisoes` pra
    treinos CSP (hoje renderiza mensagem amber).
- **Bloco 5 — estado-alvo**: dashboard quantitativo, cadastros XLSX
  completos, remoção do motor antigo do app (preservação em branch/tag
  git permanente). E.1 é o **penúltimo passo** estrutural.

## Pendências em aberto pós-E.1 (não bloqueiam uso real)

1. **Bíceps família única** (achado #1 da E.0 + reabordado na E.1) —
   cadastrar `Rosca martelo` / `Rosca direta` / `Rosca pegada neutra` /
   etc com `variacao_de` distinto. Decisão clínica futura; quando feita,
   `biceps(2)` vira viável no CSP sem outro mecanismo.
2. **Lentidão ABC 3T** (achado H-A1) — investigar otimização do modelo
   (decomposição em sub-modelos? `solver_workers`?) se UX sentir.
3. **Bloqueio cross-treino entre rotinas separadas** — o adapter
   `treino_regerar` (Frente C) ainda passa `familias_proibidas` derivado
   manualmente; E.1 mantém esse padrão. CSP não tem ainda H- pra
   AllDifferent cross-rotina (fora do escopo do solver, são rotinas
   independentes). OK pra produção; se algum dia o motor receber a
   rotina inteira de uma vez no `/regerar` (ao invés de 1 treino), o
   filtro pode ser declarativo.
4. **UX inviabilidade total** — quando rotina toda é inviável (caso
   raro, demanda sem candidatos no banco), mostramos aviso "(rotina
   inteira) motor CSP inviável" no treino 0. Mensagem é técnica;
   poderia ser mais clínica ("sua combinação de subregiões + nível +
   complexidade não tem candidatos suficientes"). Refinamento de copy.
