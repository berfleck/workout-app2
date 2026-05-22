# Rotinas mais comuns — uso real do gerador

> **Propósito.** Documentar as configurações de geração de treino que
> aparecem (ou aparecerão) com frequência na prática clínica do
> personal trainer responsável pelo app. Serve de fonte de verdade pra
> calibração da Fase 3 (Etapa 6) e decisões futuras de UX/calibração.
>
> **Status.** O app está em desenvolvimento e não está em uso de
> produção ainda. Este documento descreve o uso *projetado* com base
> na prática presencial do personal, não *observado* via telemetria do
> app. Atualizar quando uso real de produção começar.

---

## 1. Universo de alunos

Carteira ativa: ~20 alunos.

**Perfis identificáveis: 3 principais.** O perfil modal — aquele que
aparece com mais frequência — pode ser descrito assim:

> Aluno que treina de 2 a 3 vezes por semana com foco em saúde e
> condicionamento geral, buscando equilíbrio entre recomposição
> corporal (estética) e saúde.

Os outros dois perfis aparecem em menor frequência. Não estão detalhados
neste documento porque não foram caracterizados com profundidade
suficiente ainda; expandir conforme uso real revelar suas
particularidades.

---

## 2. Frequência semanal e divisão típica

Frequências que aparecem na prática: **1x, 2x, 3x** semana. **4x**
acontece com pouca frequência. **5x ou mais** não aparece.

### 2.1 Frequência 1x semana

**Configuração:** treino estilo **full body** — composição de
categorias que cubra vários movimentos e grupos musculares no único
treino da semana.

> ⚠️ **Nota de nomenclatura.** Quando "full body" aparece neste
> documento, refere-se a uma *composição feita pelo personal* que
> cobre múltiplos grupos musculares. **NÃO** se refere ao template
> `full_body` do app (funcionalidade existente mas sem uso ativo —
> ver Seção 5).

Tamanho típico: 6-8 exercícios. Configuração concreta varia mas tende
a misturar regiões (`upper(N)` + `lower(N)` + `core(N)`) ou usar
subregiões pra ter mais controle de cobertura.

### 2.2 Frequência 2x semana

Duas variantes aparecem com frequência **aproximadamente igual**
(metade-metade):

**Variante A — Full body com viés:** ambos os treinos cobrem o corpo
inteiro, mas cada um tem volume maior em grupos específicos. Treino 1
pode ter mais peito/ombro/tríceps; Treino 2 mais costas/pernas/bíceps,
por exemplo. Ambos os treinos ainda tocam todas as regiões principais.

**Variante B — Empurrar/Puxar split com pernas distribuídas:** cada
treino foca em metade do corpo com perna de lado oposto.

Exemplo concreto da Variante B (com setup típico em demandas):

```
Treino 1 (Empurrar + perna posterior):
  peito(2) + ombro(1) + perna_posterior(3) + core(1) + tríceps(1)
  = 8 exercícios

Treino 2 (Puxar + perna anterior):
  costas(3) + perna_anterior(3) + core(1) + bíceps(1)
  = 8 exercícios
```

> **Variações comuns nesta variante:** as demandas exatas variam de
> rotina pra rotina. Exemplos: ombro(2) em vez de ombro(1);
> perna_posterior(2) em vez de (3); inclusão de posterior_ombro(1)
> substituindo alguma demanda. A estrutura geral (Empurrar+posterior /
> Puxar+anterior) se mantém; quantidades flexíveis.

### 2.3 Frequência 3x semana

Duas variantes:

**Variante A — 3 treinos full body com viés:** cada um dos 3 treinos
da semana é full body com volume maior em grupos diferentes.
Distribuição do "viés" rotaciona entre os treinos pra cobrir bem todos
os grupos ao longo da semana.

**Variante B — 4 treinos A1/A2/B1/B2 ciclando 3x:** rotina conceitual
tem 4 treinos, mas o aluno faz 3 treinos por semana ciclando
A-B-A / B-A-B. A1 e A2 têm **as mesmas categorias e demandas**, só
variando exercícios concretos; B1 e B2 idem.

> **Implicação técnica importante:** A1 e A2 são "duas instâncias da
> mesma rotina conceitual com exercícios diferentes". Para calibração
> INTER, o comportamento desejado é que o gerador produza variação
> entre A1 e A2 — não que trate como se fossem o mesmo treino. Mesma
> coisa entre B1 e B2.

### 2.4 Frequência 4x semana

Aparece com pouca frequência. Configurações concretas não foram
caracterizadas em profundidade. Provavelmente split upper/lower
alternado (upper/lower/upper/lower) ou variantes do split A1/A2/B1/B2
com cycle 4x.

---

## 3. Padrões de uso do gerador

### 3.1 Origem das rotinas

O personal estima que o uso vai se concentrar em:

- **(c) Conjunto pequeno de configurações que rotaciona** — caminho
  principal projetado. Personal terá um conjunto enxuto de
  configurações-base que aplica a alunos do perfil modal, ajustando
  exercícios concretos via geração mas mantendo a estrutura de
  demandas.
- **Criação na hora** — caminho secundário, usado quando situação
  específica emerge. Exemplos:
  - Aluno de 2x/semana só vai comparecer 1x: criar treino maior na
    hora cobrindo mais grupos.
  - Aluno tem dois treinos próximos na semana (ex: quarta+quinta em
    vez de seg+qui): split mais granular pra evitar musculatura
    sobrecarregada.

### 3.2 Tamanho de bloco

**Padrão: 2 exercícios por bloco** (super-séries em duplas).

**Variação relevante:** alguns grupos de alunos treinam em duplas
normalmente, mas em algumas semanas chegam em 3 e pedem trios. Nesse
caso o personal **edita o treino existente na hora** — adicionando
exercícios, criando bloco novo ou mudando bloco de 2 pra 3. Isso é
mais um caso de UX (regerar/editar bloco) do que de configuração de
geração nova.

### 3.3 Granularidade de configuração: região vs subregião vs padrão

Uso projetado é **mistura**, dependendo do objetivo:

- **Região** (`upper(N)` + `lower(N)` + `core(N)`): treinos mais
  "misturados" gerados rapidamente, sem necessidade de controle fino.
- **Subregião** (`peito(2)` + `costas(2)` + `ombro(1)` + ...): quando
  precisa de refino em quais grupos musculares aparecem em quais
  quantidades. Variantes B do 2x e do 3x semana usam essa
  granularidade.
- **Padrão** (`empurrar_compostos(2)` + ...): casos específicos onde
  o personal quer controle ainda mais fino (ex: forçar composto vs
  isolado).

---

## 4. Casos especiais frequentes

Cenários que existem mas não são modais. Lista ainda **rasa** porque
o app não está em uso de produção:

- **Aluno de 2x/semana faltando um dia**, gerando necessidade de
  treino maior na hora.
- **Intervalo curto entre treinos** (ex: quarta+quinta), forçando
  split mais granular pra preservar recuperação.
- **Aluno de grupo virando trio**, gerando necessidade de aumentar
  blocos de 2 pra 3 exercícios via edição manual.

Casos muito específicos (lesões pontuais, restrições temporárias)
serão tratados via **edição manual** do treino gerado, não via nova
configuração de geração.

---

## 5. Casos fora do escopo

Configurações que **não precisam** ser otimizadas pela Fase 3:

- **Template `full_body` do app**: funcionalidade existe (junto com
  Empurrar/Posterior, etc.), mas não recebe uso ativo nem atenção de
  desenvolvimento agora. Pretende ser uma facilidade de "um clique
  gera rotina típica". Calibração específica desses templates fica
  pra fase posterior, quando receberem atenção dedicada.
- **Rotinas com 12+ exercícios por treino** (ex:
  `upper(5)+lower(5)+core(2)`): não fazem parte do uso do personal.
  Tamanho típico é 6-8 exercícios/treino.
- **Frequência semanal 5x ou mais**: não aparece na prática.
- **Cenários patológicos do harness E.0**: cenários como "peito(3)
  com Inclinado forçado em T1", "perna_anterior(2) com Step Up
  forçado em T1", etc. são propositalmente extremos pra forçar
  resposta do gerador e medir mecanismo. **Não devem ser interpretados
  como cenários de uso real.** Servem pra calibração estrutural.

---

## 6. Limitações desta documentação

**App não está em uso de produção ainda.** Este documento descreve
uso *projetado* baseado na prática presencial do personal, não
*observado* via telemetria.

Implicações pra Fase 3:

1. **Calibração via cenários-âncora E.0 + testes pontuais é o único
   caminho disponível** durante a Fase 3. Não há feedback de uso real
   pra informar ajustes.
2. **Cenários de "configuração frequente que o gerador atende mal"
   ainda não foram identificados** — porque não há uso real produzindo
   esse sinal. Quando uso real começar, esses cenários vão emergir e
   devem alimentar calibrações futuras (Etapa 7+ ou ajustes de
   manutenção).
3. **Documento deve ser atualizado** quando uso real começar — em
   particular, Seções 1 (perfis), 4 (casos especiais frequentes) e
   adicionar uma Seção 7 ("achados de uso real").

---

## 7. Implicações pra calibração da Fase 3

### 7.1 Cenário 6.1 (happy path) — revisão de representatividade

Setup atual do 6.1: `upper(3) + lower(3) + core(2)` × 2 treinos = 8
exercícios/treino.

**Aderência ao uso real:** boa em tamanho de treino (8 exercícios cai
no range 6-8 do uso). Cobre frequência 2x semana com configuração
"full body" (variante 1x ou variante A do 2x).

**Limitações:** não cobre a Variante B do 2x semana (split
Empurrar/Puxar com perna posterior/anterior distribuídas), que aparece
com frequência similar. Vale considerar adicionar um **6.2 happy path
secundário** com setup tipo:

```
Treino 1: peito(2) + ombro(1) + perna_posterior(3) + core(1) + tríceps(1)
Treino 2: costas(3) + perna_anterior(3) + core(1) + bíceps(1)
```

Isso testa happy path com granularidade de subregião — diferente do
6.1 que usa granularidade de região.

### 7.2 Cenário INTER (3.x) — alinhamento com 3x semana variante B

A rotina A1/A2/B1/B2 ciclando 3x é exatamente o caso onde calibração
INTER importa: A1 e A2 devem produzir variação de exercícios mantendo
mesmas categorias. Cenários 3.x do E.0 testam mecanismos relacionados
a isso. Vale auditar se as expectativas numéricas dos 3.x batem com o
desejo clínico nesse uso.

### 7.3 Auditoria geral dos cenários E.0 contra uso real

Recomenda-se, antes de fechar calibração da Fase 3, fazer um pass
explícito de cada um dos 13 cenários E.0 marcando:

- ✓ representativo de uso real
- ⚠️ patológico mas necessário pra calibração estrutural
- ❓ revisar se vale priorizar

Isso evita que a calibração final fique boa em casos que mal
aparecem em produção e ruim em casos comuns.

---

*Documento criado em 2026-05-08. Atualizar conforme uso real do app
começar a produzir feedback.*
