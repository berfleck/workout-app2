> ## ⚠️ Nota de superação parcial
>
> Este documento é o **checkpoint de uma sessão anterior** de design
> e análise. Algumas seções foram **superadas** pelo
> `guia_refatoracao_v4.md`, que é a fonte de verdade operacional
> atual. Outras seções **continuam relevantes e únicas** e devem ser
> consultadas para contexto.
>
> ### O que foi superado (NÃO usar como referência)
>
> - **Roteiro de 10 etapas** (seção "Roteiro"): substituído pelas 8
>   etapas do guia v4, com escopo e ordem redefinidos. Em particular:
>   cargas (HIB2) foi movida para depois de Nível 2 + âncoras; squat
>   e core ganharam frentes próprias na Etapa 1; uma Etapa 8 nova
>   (explicabilidade) foi adicionada.
> - **Lista de 6 problemas conhecidos** (seção "Problemas conhecidos
>   não resolvidos"): expandida no guia v4 para 8 problemas, com
>   problemas 7 (distribuição reproduz banco) e 8 (core sem
>   subregiões) adicionados.
> - **Empacotamento "Nível 2 + âncoras protegidas"**: o guia v4
>   separou em Etapas 2 e 3 independentes, e expandiu a regra de
>   âncoras para operar em subregião também (não só em região).
> - **"Próximo passo claro quando retomar"** (seção final): a
>   sequência sugerida lá é da fase pré-v4 e não corresponde mais
>   ao plano atual. Usar a Seção 4 do guia v4.
>
> ### O que continua válido (CONSULTAR para contexto)
>
> - **Calibração HIB2** (seção "Onde paramos: filtro de cargas"):
>   thresholds 6/5/6 escolhidos, justificativa clínica, análise dos
>   20 casos. Continua sendo a calibração de partida da Etapa 4 do
>   guia v4.
> - **Conceitos**: "dança das cadeiras", "blocos solo legítimos vs
>   forçados", "interpretação dos números de bloqueios nos
>   relatórios", "Fase 1 vs Fase 2 do gerador". Continuam corretos
>   e úteis para o vocabulário comum do projeto.
> - **Estado atual do app** (seção "Já implementado e funcionando"):
>   ainda reflete o ponto de partida da refatoração.
> - **Banco atual** (seção "Banco atual"): descrição das 125
>   entradas e colunas continua atualizada.
> - **Documentos do projeto a manter sincronizados**: a lista de
>   referências cruzadas continua útil, embora alguns documentos
>   listados estejam agora em `docs/refatoracao/arquivo/`.
>
> ### Resumo: como usar este documento
>
> Para **decidir o que fazer**, use o `guia_refatoracao_v4.md`.
> Para **entender o contexto histórico** ou consultar a calibração
> HIB2, use este documento. Para **lista de problemas atual**, use
> a tabela do guia v4 (Seção 3).

---

# Memória do projeto — Workout App v2

> Documento de checkpoint criado para encerrar conversa longa e retomar
> em sessão nova sem perder contexto. Ler primeiro antes de qualquer
> nova análise.

---

## Sobre o projeto

Aplicativo Flask que gera treinos de musculação para alunos. O personal trainer
configura quantidades por região/subregião/padrão muscular, e o app monta a
sessão com blocos (super séries) respeitando filtros e regras.

**Repositório**: github.com/berfleck/workout-app2
**Arquivos principais**:
- `gerador_treino.py` — motor de geração (lógica central)
- `app_flask.py` — UI Flask
- `banco_exercicios.xlsx` — banco de exercícios (131 → atualmente 125)
- `CLAUDE.md` — instruções para Claude Code

---

## Estado atual do app (validado nos uploads recentes)

### Já implementado e funcionando

1. **Geração multi-treino** com hierarquia região → subregião → padrão
2. **Sistema de avisos** em `Sessao.avisos`: tipos `incompleta` e `familia_repetida`
3. **`relaxar_familia`** (parâmetro): permite relaxar bloqueio inter-treino quando
   demanda não pode ser cumprida; exercícios escolhidos via relax vão pra
   `Sessao.relaxados` e ganham badge `↻` no UI
4. **Modal de avisos** (`_avisos_modal.html`) que aparece quando rotina é gerada
5. **Filtros hard funcionais**: nome, variacao_de (família), equipamento,
   complexidade, fadiga, lateralidade
6. **Escada de relax em 2 níveis**: 0=estrito, 1=relax família inter (se ligado)
7. **Cleanup de similaridade já aplicado** (similaridade ainda existe no
   banco mas não é usada em decisão alguma)

### Banco atual (`banco_exercicios.xlsx`)

- 125 exercícios
- Colunas existentes: nome, variacao_de, eq_primario, eq_secundario, regiao,
  padrao, purpose, unilateral, complexidade, fadiga, circuito, similaridade,
  musculo_primario, obs
- **3 colunas novas adicionadas e curadas pelo personal**:
  `carga_grip`, `carga_lombar`, `demanda_core` (escala 0-3)

### Problemas conhecidos não resolvidos

1. **Viés posterior > anterior** quando demanda é "lower(N)": app distribui
   ~2.2 perna_posterior e ~1.5 perna_anterior em média (esperado 1:1).
   Adutores e panturrilha quase nunca aparecem. Causa: provavelmente regra
   de proporção 60/40 favorece padrões compostos (hinge tem 21 ex, squat
   tem 17). **Independente do filtro de cargas. Resolvido com Nível 2 +
   regra de âncoras protegidas.**

2. **Tríceps tem 8 exercícios, todos com `variacao_de = "Tríceps"`**: pedir
   `triceps(2)` é matematicamente impossível com filtro família ligado.
   Cleanup do banco necessário.

3. **`subregiao` não está na dataclass `Exercicio`** — é resolvida por mapa
   padrão→subregião no código (mais rígido que poderia ser). Refatoração
   futura.

4. **Squat unilateral/bilateral é tapa-buraco**: na UI tem botões `squat_bi`
   e `squat_uni` que viraram "padrões" mas no banco/motor é só filtro de
   lateralidade aplicado ao padrão `squat`. Decisão: **manter como filtro,
   mas tornar uniforme em todos os padrões no futuro** (motor já suporta
   via `lateralidade_por_padrao`, falta UI).

5. **Padrões âncora podem não ter composto na rotina**: quando pede
   `regiao=upper(3)` × N treinos, o gerador pode sortear sempre os mesmos
   2-3 padrões compostos (ex: ombro+puxadas em todos), deixando peito
   representado só por isolado (ex: Crossover Sentado) ou ausente. Isso é
   problema porque compostos cobrem secundários (supino trabalha tríceps;
   sem composto de peito, o tríceps fica sem ativação acessória, exigindo
   isolado). **Resolvido por: Nível 2 (pré-aloca entre treinos) + regra
   de âncoras protegidas (garante 1 composto de cada padrão âncora antes
   de sortear vagas livres). Aplica só em demandas de nível "regiao", não
   em subregião ou padrão (onde o usuário foi específico).**

6. **Regra anti-2-unilaterais força pareamentos subótimos**: a regra
   "máximo 1 unilateral por bloco de 2" tem boa intenção (evita
   superset chato/demorado) mas em casos onde o treino tem múltiplos
   unilaterais, força pareamentos não-ideais. Caso real: rotina com
   V-Up Uni + Tríceps Uni Polia + Hollow Hold (bilateral) — o gerador
   pareou V-Up + Hollow Hold (mesmo grupo region=core) e Tríceps Uni
   ficou solo, em vez de V-Up Uni + Tríceps Uni (region diferente,
   contraste muscular ideal) + Hollow Hold solo. Solução: revisar
   peso da regra anti-unilateral vs pareamento por contraste. Item 6
   do roteiro.

---

## Onde paramos: filtro de cargas

### A regra

Filtro intra-bloco: bloqueia pareamento se a soma das cargas dos dois
exercícios atingir um threshold numa dimensão (grip, lombar ou core).
Exige que ambos tenham valor ≥ 1 nessa dimensão (3+0 nunca bloqueia).

### Calibração final escolhida (HIB2)

Após várias rodadas de simulação e fase clínica:

```
grip   → threshold = 6  (bloqueia só 3+3)
lombar → threshold = 5  (bloqueia 3+2 e 3+3)
core   → threshold = 6  (bloqueia só 3+3)
```

**Justificativa**: lombar é o vetor de risco de lesão mais relevante,
justifica threshold mais apertado. Grip é desconforto/cansaço, não risco.
Core: a régua no banco está sensível (muitos exercícios em 3), apertar
demais (L5) gerava 65% mais blocos solo sem ganho clínico proporcional.

### O que a fase clínica revelou

20 casos pareados OFF vs HIB vs HIB2 no split B (Full body focado inferior).
Comparação chave:

| Métrica | OFF | HIB (core=L5) | HIB2 (core=L6) |
|---|---:|---:|---:|
| Blocos solo | 4 | 40 | 14 |
| Bloqueios totais | — | 1.715 | 150 |

HIB2 ganha por larga margem. Pares que continuam bloqueados em HIB2 são
todos clinicamente justificados: Hiperextensão+Remada Curvada Halteres,
Remada Landmine+Roda Abdominal, Stiff Uni Halteres+V-Up etc.

### Status: pendente avaliação humana final dos 20 casos clínicos

Os 20 casos foram gerados (`casos_clinicos_hib2.md`). Personal precisa
avaliar caso a caso e confirmar se HIB2 está bom para prosseguir.

---

## Conceitos importantes que apareceram na conversa

### "Dança das cadeiras"

Quando o filtro bloqueia 1 par específico, a fila de pareamentos
reorganiza inteira. Pares aparentemente não relacionados podem mudar
de frequência só por reorganização. **Esse efeito é positivo**: o
gerador acaba fazendo escolhas que um personal experiente faria
(pesado com leve em vez de pesado com pesado), mas também significa
que "pares que sumiram" ≠ "pares bloqueados diretamente". Próximos
relatórios devem separar esses dois conceitos.

### Blocos solo legítimos vs forçados

Bloco com 1 exercício só nem sempre é problema:

**Legítimos** (solo é OK):
- Exercícios pesados/longos: Lev. Terra, Agachamento Livre, Búlgaro,
  Recuo C/ Barra, Good Morning, Remada Curvada Barra, Barra Fixa,
  Serrote, Stiff Uni Halteres/Smith, Hip Thrust, Hip Thrust Uni,
  Nordic Curl, Passada Dos Steps

**Forçados** (problema do filtro):
- Quando exercício leve fica solo porque o par possível foi bloqueado

Métrica relevante: variação de `solos forçados` em ON vs OFF.

### Interpretação dos números de "bloqueios" nos relatórios

CUIDADO ao ler tabelas tipo "Bloqueios por dimensão". Os números (ex: 38.304
em lombar no HIB) NÃO significam "38 mil blocos bloqueados". Significam
"chamadas vetadas pelo filtro".

Numa única rotina, o mesmo par pode ser testado 30+ vezes pelo gerador
durante a busca de candidatos (matriz de prioridades P×Sub × tentativas
de fallback). Cada veto conta uma vez no log.

Métrica válida pra comparar **esforço relativo entre modos** (qual filtro
trabalha mais). NÃO válida pra dizer "X% dos blocos foram afetados".
Pra impacto real, usar `Δ solos forçados vs OFF` ou `pares únicos vetados`.

Exemplo: HIB tem 38k vetos lombar mas isso virou apenas ~663 blocos solo
extras vs OFF. Impacto real ~3-4% dos blocos, não 40%+.

### Fase 1 vs Fase 2 do gerador

Fase 1 = seleção dos N exercícios da sessão (respeita demandas).
Fase 2 = montagem dos blocos com os exercícios já selecionados.

**Limitação arquitetural**: o gerador NÃO volta ao banco se um par
bloqueado deixa exercício órfão. Trabalha apenas com os N selecionados.
Refatorar isso (Fase 1 "olhar pra frente") é trabalho futuro, parte
da migração pra sistema de penalidades.

---

## Visão de longo prazo: tags multi-dimensionais + penalidades

### Por que mudar

App atual = filtros hard + random.choice. Limitações:
- Não captura "preferências"
- Não escala para múltiplos critérios

Solução: filtros hard + ranking por penalidade. Vide
`visao_proxima_fase.md` (já existe no projeto).

### O que já foi decidido

- **Colunas separadas por dimensão** (não tags conjuntas) no banco
- **Pesos diferentes por dimensão** (ex: ângulo > equipamento)
- **Tag vazia = "não se aplica"** (não conflita)
- **Aleatoriedade preservada**: sortear entre os candidatos no tier
  de menor penalidade (não escolher o "ótimo")
- **Hierarquia de granularidade**: nome > variacao_de > tags > similaridade
  (similaridade já removida)

### Roteiro

1. ✅ Patch bug `variacao_pais` + sistema de avisos + relaxar_familia
2. ✅ Cleanup de similaridade
3. ✅ Cargas grip/lombar/core no banco (curadoria humana feita)
4. **🟡 Implementar filtro de cargas no app** (calibração HIB2 escolhida,
   pendente avaliação humana final dos 20 casos)
5. ⬜ **Refatoração Nível 2 + regra de âncoras protegidas** — pacote
   conjunto (ver `refatoracao_visao_global.md`). Resolve cobertura
   categórica entre treinos (peito/costas/ombro garantidos como
   compostos), distribuição entre subregiões, e treinos finais
   incompletos.
6. ⬜ Revisão de regras de pareamento intra-bloco (ex: regra
   anti-2-unilaterais que hoje força cores juntos quando ambos são
   unilaterais — caso real visto em sessao_salvas onde V-Up Uni +
   Hollow Hold ficou pareado e Tríceps Uni Polia ficou solo)
7. ⬜ Listar 8-12 grupos de exercícios próximos com dimensões
   (template já criado: `template_grupos_proximidade.md`)
8. ⬜ Definir colunas de tags multi-dimensionais (ângulo, equipamento, etc)
9. ⬜ Migrar banco com as tags
10. ⬜ Refatorar gerador pra sistema de penalidades

**Importante**: Nível 2 + âncoras vem ANTES das tags multi-dimensionais.
A análise mostrou que muitos problemas atribuídos a "falta de penalidades"
na verdade vêm da arquitetura sequencial. Resolver isso primeiro torna
o sistema de penalidades mais simples depois.

---

## Documentos do projeto a manter sincronizados

Já entregues anteriormente, devem estar no repo:

- `logica_gerador.md` — mapa das 5 hierarquias internas do gerador
- `visao_proxima_fase.md` — arquitetura tags + penalidades
- `refatoracao_visao_global.md` — refatoração para gerar rotinas com
  visão global em vez de sequencial (Nível 2 recomendado)
- `remover_similaridade_v3.md` — cleanup já aplicado (pode arquivar)
- `template_grupos_proximidade.md` — pra preencher etapa 5 do roteiro
- `relatorio_preenchimento_cargas.md` — heurísticas usadas no cadastro
  inicial das cargas

Específicos da fase atual (filtro de cargas):
- `relatorio_v4.md` — análise em massa: viés posterior, blocos solo
- `casos_clinicos_hib2.md` — 20 casos clínicos OFF vs HIB vs HIB2

---

## Próximo passo claro quando retomar

1. Personal avalia os 20 casos clínicos do `casos_clinicos_hib2.md`
2. Se HIB2 OK → preparar prompt pro Claude Code com a Fase B:
   - Adicionar campos `carga_grip`, `carga_lombar`, `demanda_core` na
     dataclass `Exercicio` e no carregamento
   - Adicionar função `_bloqueio_cargas` em `gerador_treino.py`
   - Integrar em `pode_adicionar_ao_bloco`
   - Adicionar 3 dropdowns na UI (config geral): threshold por dimensão,
     valores 3-6, default 6/5/6 (HIB2)
   - Adicionar tipo de aviso `relaxado_carga` no sistema de avisos
3. Se HIB2 não OK → ajustar calibração antes do patch

---

*Memória criada para servir de ponto de partida em nova sessão.
Quando retomar: subir este documento + os 3 arquivos atuais
(gerador_treino.py, app_flask.py, banco_exercicios.xlsx) e dizer
"vamos continuar daqui".*
