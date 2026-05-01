# Por que remover o filtro de similaridade do gerador (v3)

> Documento de evidências para limpeza de código. Atualizado para refletir
> o estado pós-patch do gerador (que adicionou `relaxar_familia`, sistema
> de avisos e separação `var_pais_inter` / `var_pais_intra`).
>
> **Importante**: este documento NÃO mexe em `relaxar_familia`, avisos,
> badge `↻`, ou qualquer outra feature recente. Esses ficam.

---

## TL;DR

O sistema de "similaridade" no gerador tem três peças, e nenhuma das três
está fazendo trabalho útil hoje:

1. **Checkbox `variar_entre_treinos`** — write-only. Confirmado empiricamente
   após o patch (50/50 simulações idênticas variando só o flag).
2. **Filtro de similaridade intra-treino** — em 96.3% das chamadas é inócuo
   (não filtra nada) ou zera os candidatos forçando fallback. Mesmos
   números pós-patch (banco não mudou).
3. **Estrutura conceitual** — após adicionar tags multi-dimensionais e
   sistema de penalidades (próxima fase, ver `visao_proxima_fase.md`),
   `similaridade` perde qualquer função restante.

Removível com segurança. Detalhes e provas abaixo.


---

## O que mudou do v2 pro v3

`gerador_treino.py` está **idêntico** ao estado descrito no v2 — todos os
números de linha continuam corretos.

`app_flask.py` cresceu ~20 linhas (de 2401 → 2420). Os trechos de código a
modificar são os mesmos, mas as linhas se deslocaram:

| Item | Linha v2 | Linha v3 (atual) |
|---|---:|---:|
| `variar = request.form.get("variar_entre")...` | 1300 | 1315 |
| `gerar_multiplos_treinos(..., variar_entre_treinos=variar, ...)` | 1454 | 1469 |
| `"variar_entre": variar` em opcoes_globais | 1492 | 1507 |
| Primeira chamada `selecionar_sem_repeticao_similaridade` | 1258 | 1273 |
| Segunda chamada `selecionar_sem_repeticao_similaridade` | 1750 | 1766 |

A importação na linha 12 não mudou.

---

## Prova 1 — checkbox `variar_entre_treinos` é write-only

### Evidência por inspeção de código (estado atual)

A variável `sims_globais` aparece **apenas duas vezes** em
`gerador_treino.py` (1435 linhas no estado atual):

```
linha 1214: sims_globais: set[str] = set()        # criação
linha 1295: sims_globais.add(ex.similaridade)     # adição (dentro do if variar_entre_treinos)
```

Não é passada como parâmetro para função alguma. Não aparece em filtro
algum. Não é lida em decisão alguma. O checkbox apenas controla se algo
é gravado num set que é descartado ao final de `gerar_multiplos_treinos`.

### Evidência empírica (estado atual)

Rodando 50 simulações idênticas (mesma seed) variando apenas o flag,
após o patch:

```
Resultado idêntico:    50/50
Resultado diferente:    0/50
```

### Causa raiz

Na função `gerar_multiplos_treinos`, o pretendido seria passar
`sims_globais` como parâmetro pra função filha (`gerar_sessao_por_demandas`),
e dentro dela usar como filtro inicial. Nada disso está implementado. O
flag e o set existem só semanticamente, não funcionalmente.

---

## Prova 2 — filtro de similaridade intra-treino é majoritariamente inócuo

### Evidência por inspeção de código (estado atual)

O filtro intra-treino agora vive em duas funções principais:

**Em `gerador_treino.py`, função `_selecionar_ciclando` dentro de `gerar_sessao_por_demandas`**, linhas 1005–1013 (nível 0 — estrito):

```python
def _filtrar(cands: list[Exercicio], nivel_relax: int) -> list[Exercicio]:
    # nivel_relax: 0=estrito, 1=relax similaridade, 2=relax família inter
    if nivel_relax == 0:
        base = [
            e for e in cands
            if e.similaridade not in similaridades_usadas    # ← filtro de similaridade
            and e.nome not in nomes_usados
            and not _bloqueado_familia(e, [var_pais_inter, var_pais_intra])
        ]
    elif nivel_relax == 1:
        base = [
            e for e in cands
            if e.nome not in nomes_usados                    # ← já sem filtro de similaridade
            and not _bloqueado_familia(e, [var_pais_inter, var_pais_intra])
        ]
    else:
        # nivel 2: relax família inter (preserva intra)
        ...
```

**Em `gerador_treino.py`, função `selecionar_sem_repeticao_similaridade`**,
linhas 364+ — usada por `gerar_sessao` (versão antiga) e duas rotas de
`app_flask.py` (regerar bloco).

### Evidência por análise do banco

A coluna `similaridade` no banco atual tem distribuição muito pobre:

| padrao | n_exercícios | n_similaridades distintas |
|---|---:|---:|
| biceps | 6 | **1** |
| empurrar_compostos | 7 | **1** |
| empurrar_isolados | 3 | **1** |
| knee_flexion | 4 | **1** |
| ombro_composto | 5 | **1** |
| ombro_isolado | 5 | **1** |
| posterior_ombro | 3 | **1** |
| puxadas | 7 | **1** |
| remadas | 12 | **1** |
| triceps | 8 | **1** |
| core_dinamico | 7 | **1** |
| flexao_plantar | 3 | **1** |
| cardio | 2 | **1** |
| adduction | 3 | 2 |
| core_isometrico | 13 | 2 |
| abduction | 5 | 3 |
| hinge | 21 | 3 |
| squat | 17 | 4 |

**13 dos 18 padrões têm similaridade única**. Como o filtro só consegue
distinguir candidatos quando há mais de uma similaridade no padrão, ele
fica inócuo na maioria dos casos.

### Evidência empírica — quanto o filtro realmente filtra

Em 200 simulações × 10 padrões processados = 2000 chamadas ao filtro:

| Resultado | Contagem | % |
|---|---:|---:|
| Filtro **efetivo** (reduziu candidatos sem zerar) | 74 | 3.7% |
| Filtro **inócuo** (lista com filtro = lista sem filtro) | 1726 | 86.3% |
| Filtro **zerou** candidatos (fallback usado) | 200 | 10.0% |

Mesmos números antes e depois do patch — o problema é o **dado**, não o
código.

---

## Prova 3 — `similaridade` perde sentido com a próxima fase

A próxima fase do app introduz colunas multi-dimensionais (`tag_angulo`,
`tag_equipamento`, `tag_estabilidade`, etc) com sistema de penalidades.
Essas tags capturam proximidade entre exercícios de forma rica e
discriminativa.

A coluna `similaridade` foi pensada como uma proximidade de granulometria
intermediária. Após as tags:

- **Granulometria fina** (família mecânica idêntica): coberto por `variacao_de`
- **Granulometria intermediária** (movimento parecido): coberto por tags multi-dimensionais
- **Granulometria grossa** (categoria genérica): redundante, não acrescenta

A coluna `similaridade` fica sem nicho — qualquer trabalho que ela faria
é feito melhor por tags com pesos baixos (penalidade leve).

---

## O que remover do código

> **Antes de aplicar qualquer remoção**, rode `grep -n "similaridade\|sims_glob\|sims_em_uso\|variar_entre" gerador_treino.py app_flask.py` no estado em que o repo se encontra. Os números de linha podem ter mudado, mas os pontos abaixo identificam blocos por contexto, não só por linha.

### Em `gerador_treino.py`

#### A) Em `gerar_multiplos_treinos` (≈ linhas 1187–1299)

Remover o parâmetro `variar_entre_treinos` e tudo que depende dele:

**Antes:**
```python
def gerar_multiplos_treinos(
    banco: list[Exercicio],
    configs: list[dict],
    variar_entre_treinos: bool = True,        # ← REMOVER
    relaxar_familia: bool = False,
) -> list[Sessao]:
```

**Depois:**
```python
def gerar_multiplos_treinos(
    banco: list[Exercicio],
    configs: list[dict],
    relaxar_familia: bool = False,
) -> list[Sessao]:
```

Remover do docstring as referências a `variar_entre_treinos` e a
"similaridades bloqueadas".

Remover o set `sims_globais` e seu uso:

**Antes (≈ linha 1214):**
```python
nomes_exatos_globais: set[str] = set()
sims_globais: set[str] = set()           # ← REMOVER
variacao_pais_globais: set[str] = set()
```

**Depois:**
```python
nomes_exatos_globais: set[str] = set()
variacao_pais_globais: set[str] = set()
```

**Antes (≈ linhas 1294–1295), no loop de pós-processamento:**
```python
variacao_pais_globais.add(ex.nome)
if ex.variacao_de:
    variacao_pais_globais.add(ex.variacao_de)
if variar_entre_treinos:                 # ← REMOVER bloco
    sims_globais.add(ex.similaridade)    # ← REMOVER bloco
```

**Depois:**
```python
variacao_pais_globais.add(ex.nome)
if ex.variacao_de:
    variacao_pais_globais.add(ex.variacao_de)
```

#### B) Em `_selecionar_ciclando` dentro de `gerar_sessao_por_demandas` (≈ linhas 947–1066)

**Remover variável `similaridades_usadas`:**

**Antes (≈ linha 947):**
```python
similaridades_usadas: set[str] = set()
nomes_usados: set[str] = set()
todos_selecionados: list[Exercicio] = []
relaxados_local: list[str] = []

# Travados entram primeiro
for e in travados:
    todos_selecionados.append(e)
    similaridades_usadas.add(e.similaridade)   # ← REMOVER
    nomes_usados.add(e.nome)
```

**Depois:**
```python
nomes_usados: set[str] = set()
todos_selecionados: list[Exercicio] = []
relaxados_local: list[str] = []

# Travados entram primeiro
for e in travados:
    todos_selecionados.append(e)
    nomes_usados.add(e.nome)
```

**Simplificar `_filtrar` removendo o nível 1 (relax similaridade)** — após
remover similaridade, o nível 0 e o nível 1 ficam idênticos, então o
nível 1 some:

**Antes:**
```python
def _filtrar(cands: list[Exercicio], nivel_relax: int) -> list[Exercicio]:
    # nivel_relax: 0=estrito, 1=relax similaridade, 2=relax família inter
    if nivel_relax == 0:
        base = [
            e for e in cands
            if e.similaridade not in similaridades_usadas
            and e.nome not in nomes_usados
            and not _bloqueado_familia(e, [var_pais_inter, var_pais_intra])
        ]
    elif nivel_relax == 1:
        base = [
            e for e in cands
            if e.nome not in nomes_usados
            and not _bloqueado_familia(e, [var_pais_inter, var_pais_intra])
        ]
    else:
        # nivel 2: relax família inter (preserva intra)
        base = [
            e for e in cands
            if e.nome not in nomes_usados
            and not _bloqueado_familia(e, [var_pais_intra])
        ]
    if preferir_composto and filtro_purpose is None:
        comp = [e for e in base if _eh_composto(e)]
        if comp:
            return comp
    return base
```

**Depois:**
```python
def _filtrar(cands: list[Exercicio], nivel_relax: int) -> list[Exercicio]:
    # nivel_relax: 0=estrito, 1=relax família inter (preserva intra)
    if nivel_relax == 0:
        base = [
            e for e in cands
            if e.nome not in nomes_usados
            and not _bloqueado_familia(e, [var_pais_inter, var_pais_intra])
        ]
    else:
        # nivel 1: relax família inter (preserva intra)
        base = [
            e for e in cands
            if e.nome not in nomes_usados
            and not _bloqueado_familia(e, [var_pais_intra])
        ]
    if preferir_composto and filtro_purpose is None:
        comp = [e for e in base if _eh_composto(e)]
        if comp:
            return comp
    return base
```

**Atualizar a lista de níveis:**

**Antes:**
```python
# Niveis de relax a tentar, em ordem. Relax 2 só se relaxar_familia=True.
niveis = [0, 1] + ([2] if relaxar_familia else [])
```

**Depois:**
```python
# Niveis de relax a tentar, em ordem. Relax 1 só se relaxar_familia=True.
niveis = [0] + ([1] if relaxar_familia else [])
```

**No loop interno, remover `similaridades_usadas.add(...)`:**

**Antes:**
```python
escolhido = random.choice(disponiveis)
todos_selecionados.append(escolhido)
similaridades_usadas.add(escolhido.similaridade)  # ← REMOVER
nomes_usados.add(escolhido.nome)
if escolhido.variacao_de:
    var_pais_intra.add(escolhido.variacao_de)
var_pais_intra.add(escolhido.nome)
if nivel_relax == 2:                              # ← AJUSTAR para 1 (já que removemos nível antigo)
    relaxados_local.append(escolhido.nome)
```

**Depois:**
```python
escolhido = random.choice(disponiveis)
todos_selecionados.append(escolhido)
nomes_usados.add(escolhido.nome)
if escolhido.variacao_de:
    var_pais_intra.add(escolhido.variacao_de)
var_pais_intra.add(escolhido.nome)
if nivel_relax == 1:                              # antes era 2
    relaxados_local.append(escolhido.nome)
```

#### C) Função `selecionar_sem_repeticao_similaridade` (≈ linhas 364–415)

Essa função ainda é chamada em três lugares:
- `gerar_sessao` (linha 793) em `gerador_treino.py`
- `app_flask.py` linha 1273 (regerar bloco)
- `app_flask.py` linha 1766 (substituição/troca)

A função **não é só sobre similaridade** — ela também aplica família e
implementa o relax. Renomear é uma opção, mas **mais limpo é refatorar
inline em cada chamada** removendo o conceito.

**Opção recomendada — substituir por uma versão simplificada chamada `selecionar_evitando_familia`:**

```python
def selecionar_evitando_familia(
    candidatos: list[Exercicio],
    var_pais: set[str],
    n: int,
    nomes_usados: Optional[set[str]] = None,
    relaxar_familia: bool = False,
    relaxados_out: Optional[list] = None,
) -> list[Exercicio]:
    """
    Seleciona até n exercícios evitando repetir famílias (variacao_de).
    Se relaxar_familia=True e o estrito não preencher, relaxa família.
    Exercícios escolhidos no relax vão pra relaxados_out (lista de nomes).
    """
    nomes_usados = nomes_usados if nomes_usados is not None else set()
    selecionados: list[Exercicio] = []
    var_pais_local: set[str] = set(var_pais)

    def _passa_familia(e):
        if e.nome in var_pais_local:
            return False
        if e.variacao_de and e.variacao_de in var_pais_local:
            return False
        return True

    # Tentativa 1: estrito (família + nome)
    for e in random.sample(candidatos, len(candidatos)):
        if len(selecionados) >= n:
            break
        if e.nome in nomes_usados:
            continue
        if not _passa_familia(e):
            continue
        selecionados.append(e)
        nomes_usados.add(e.nome)
        var_pais_local.add(e.nome)
        if e.variacao_de:
            var_pais_local.add(e.variacao_de)

    # Tentativa 2: relax família (apenas se autorizado)
    if relaxar_familia and len(selecionados) < n:
        nomes_ja = {x.nome for x in selecionados}
        for e in random.sample(candidatos, len(candidatos)):
            if len(selecionados) >= n:
                break
            if e.nome in nomes_usados or e.nome in nomes_ja:
                continue
            selecionados.append(e)
            nomes_usados.add(e.nome)
            if relaxados_out is not None:
                relaxados_out.append(e.nome)

    return selecionados
```

Aí substituir as 3 chamadas:

**Em `gerador_treino.py`, função `gerar_sessao` (≈ linha 793):**

```python
# antes
selecionados = selecionar_sem_repeticao_similaridade(
    candidatos, similaridades_usadas, var_pais, n,
    relaxar_familia=relaxar_familia,
    relaxados_out=relaxados_local,
)
for e in selecionados:
    similaridades_usadas.add(e.similaridade)
todos_selecionados.extend(selecionados)

# depois
selecionados = selecionar_evitando_familia(
    candidatos, var_pais, n,
    relaxar_familia=relaxar_familia,
    relaxados_out=relaxados_local,
)
todos_selecionados.extend(selecionados)
```

E também remover `similaridades_usadas: set[str] = set()` no início de
`gerar_sessao`, e o `similaridades_usadas.add(e.similaridade)` que tinha
sido feito pra travados.

**Em `app_flask.py`, linhas 1273 e 1766:** mesma substituição (passar
`var_pais` apropriado pro contexto, retirar `sims_usados`).

**Após substituir as 3 chamadas, deletar a função
`selecionar_sem_repeticao_similaridade` inteira** (≈ linhas 364–415).

#### D) Função `substituir_exercicio` (≈ linhas 632–740)

Esta função usa `sims_em_uso` para evitar repetir similaridade na sessão
ao buscar substituto. Seguindo o mesmo princípio (similaridade não
discrimina nada útil), remover.

**Antes:**
```python
sims_em_uso = set()
for i, bloco in enumerate(sessao.blocos):
    if bloco.ex1.nome != nome_atual:
        sims_em_uso.add(bloco.ex1.similaridade)
    if bloco.ex2 and bloco.ex2.nome != nome_atual:
        sims_em_uso.add(bloco.ex2.similaridade)
    if bloco.ex3 and bloco.ex3.nome != nome_atual:
        sims_em_uso.add(bloco.ex3.similaridade)

# ... mais abaixo ...
candidatos = [
    e for e in candidatos
    if e.nome not in nomes_em_uso
    and e.similaridade not in sims_em_uso
]

if not candidatos:
    # Relaxa regra de similaridade se não encontrar nada
    candidatos = filtrar_por_padrao(banco, exercicio_alvo.padrao)
    candidatos = filtrar_por_equipamentos(candidatos, eq_bloq)
    candidatos = filtrar_por_complexidade(candidatos, max_complexidade)
    candidatos = [e for e in candidatos if e.nome not in nomes_em_uso]
```

**Depois:**
```python
candidatos = [e for e in candidatos if e.nome not in nomes_em_uso]
```

(Bloco do "if not candidatos: relaxa" sai inteiro — agora a primeira
filtragem já é a versão relaxada.)

#### E) Função `buscar_substitutos` (≈ linhas 1320–1372)

Esta função tem dois parâmetros e duas lógicas com similaridade:

```python
def buscar_substitutos(
    sessao: Sessao,
    nome_atual: str,
    banco: list[Exercicio],
    padrao: Optional[str] = None,
    regiao: Optional[str] = None,
    purpose: Optional[str] = None,
    unilateral: Optional[str] = None,
    similaridade: Optional[str] = None,        # ← REMOVER parâmetro
    max_complexidade: int = 5,
    max_fadiga: int = 5,
    equipamentos_bloqueados: Optional[list[str]] = None,
    ignorar_similaridade_usada: bool = False,  # ← REMOVER parâmetro
) -> list[Exercicio]:
```

E no corpo:
```python
sims_em_uso = set()
for bloco in sessao.blocos:
    for ex in [bloco.ex1, bloco.ex2, bloco.ex3]:
        if ex and ex.nome != nome_atual:
            nomes_em_uso.add(ex.nome)
            sims_em_uso.add(ex.similaridade)   # ← REMOVER

# ... mais abaixo ...
if similaridade:                                                       # ← REMOVER bloco
    candidatos = [e for e in candidatos if e.similaridade == similaridade]

# ...
if not ignorar_similaridade_usada:                                      # ← REMOVER bloco
    candidatos = [e for e in candidatos if e.similaridade not in sims_em_uso]
```

Antes de remover os parâmetros da assinatura, conferir se algum chamador
em `app_flask.py` passa `similaridade=` ou `ignorar_similaridade_usada=`.
Se sim, remover dos chamadores também.

```bash
grep -n "buscar_substitutos\|similaridade=\|ignorar_similaridade_usada" app_flask.py
```

### Em `app_flask.py`

#### F) Importação no topo (linha 12)

```python
from gerador_treino import (
    substituir_exercicio, buscar_substitutos, substituir_exercicio_por,
    expandir_para_padroes, selecionar_sem_repeticao_similaridade,   # ← REMOVER
    ...
)
```

Após substituir as chamadas, remover esse import. Se você criou
`selecionar_evitando_familia`, importar essa no lugar.

#### G) Rota /gerar (linha ≈ 1315)

```python
variar = request.form.get("variar_entre") == "on"     # ← REMOVER
```

E na chamada (≈ linha 1469):

```python
sessoes_ativas = gerar_multiplos_treinos(...
                                         variar_entre_treinos=variar,    # ← REMOVER
                                         relaxar_familia=relaxar_familia)
```

E no dict de opcoes_globais (≈ linha 1507):

```python
"variar_entre": variar,    # ← REMOVER
```

#### H) Rotas de regerar bloco (linhas 1273 e 1766)

Substituir `selecionar_sem_repeticao_similaridade` pela
`selecionar_evitando_familia` (criada no item C). Remover variável
`sims_usados` / `sims` que precede a chamada.

**Exemplo da rota linha ≈ 1265:**

```python
# antes
novos_exs = []
sims_usados = set()                          # ← REMOVER
for padrao in padroes_bloco:
    candidatos = [e for e in banco_filtrado if e.padrao == padrao and e.complexidade <= 5]
    if not candidatos:
        candidatos = [e for e in banco if e.padrao == padrao]
    ex = selecionar_sem_repeticao_similaridade(candidatos, set(), sims_usados, 1)
    if ex:
        novos_exs.append(ex[0])
        sims_usados.add(ex[0].similaridade)  # ← REMOVER
    elif candidatos:
        novos_exs.append(candidatos[0])

# depois
novos_exs = []
for padrao in padroes_bloco:
    candidatos = [e for e in banco_filtrado if e.padrao == padrao and e.complexidade <= 5]
    if not candidatos:
        candidatos = [e for e in banco if e.padrao == padrao]
    ex = selecionar_evitando_familia(candidatos, set(), 1)
    if ex:
        novos_exs.append(ex[0])
    elif candidatos:
        novos_exs.append(candidatos[0])
```

Mesma estrutura na rota da linha ≈ 1766.

### Em templates HTML (provavelmente `treinos.html`)

Não tenho acesso direto aos templates, mas o backend lê
`request.form.get("variar_entre")`. Procurar e remover:

```bash
grep -rn "variar_entre" templates/
```

Provavelmente tem um `<input type="checkbox" name="variar_entre">` em
`treinos.html` que pode ser deletado junto com seu label/wrapper.

### O que NÃO mudar

**Manter intactos** (foram features novas e funcionam):
- `relaxar_familia` (parâmetro, lógica, UI)
- `Sessao.avisos` e tipos `incompleta` / `familia_repetida`
- `Sessao.relaxados`
- Modal `_avisos_modal.html`
- Badge `↻` no UI
- Separação `var_pais_inter` / `var_pais_intra`
- Estrutura geral de `_filtrar` e `_selecionar_ciclando` (só simplifica
  a lista de níveis de 3 pra 2)

**Manter no banco** (custo zero):
- Coluna `similaridade` em `banco_exercicios.xlsx`. Pode ser deletada
  como cleanup futuro, mas não é necessário pra essa limpeza.

---

## Validação após remoção

Antes da limpeza, rode esses testes pra ter baseline:

```python
import random
import gerador_treino as gt

banco = gt.carregar_banco('banco_exercicios.xlsx')
demandas = [("subregiao", "peito", 2), ("subregiao", "costas", 2),
            ("subregiao", "perna_anterior", 2), ("subregiao", "perna_posterior", 2),
            ("subregiao", "core", 2)]
configs = [{"demandas": demandas, "max_complexidade": 5,
            "tamanho_bloco": 2, "evitar_agonistas": True}] * 3

# 1. Não há famílias repetidas entre treinos (sem relaxar)
for seed in range(20):
    random.seed(seed)
    sessoes = gt.gerar_multiplos_treinos(banco, configs, relaxar_familia=False)
    pais = [{(ex.variacao_de or ex.nome) for b in s.blocos
             for ex in [b.ex1,b.ex2,b.ex3] if ex} for s in sessoes]
    for i in range(len(pais)):
        for j in range(i+1, len(pais)):
            assert not (pais[i] & pais[j]), f"seed {seed}: T{i+1}∩T{j+1} = {pais[i] & pais[j]}"

# 2. relaxar_familia=True preenche treinos que ficariam incompletos
for seed in range(20):
    random.seed(seed)
    sessoes = gt.gerar_multiplos_treinos(banco, configs, relaxar_familia=True)
    for i, s in enumerate(sessoes):
        n = sum(1 for b in s.blocos for ex in [b.ex1,b.ex2,b.ex3] if ex)
        assert n == 10, f"seed {seed} T{i+1} tem {n} exercícios"

# 3. Avisos continuam sendo populados
random.seed(42)
sessoes = gt.gerar_multiplos_treinos(banco, configs, relaxar_familia=True)
total_avisos = sum(len(s.avisos) for s in sessoes)
print(f"Avisos: {total_avisos}")  # esperar > 0 com relaxar_familia=True

# 4. Sessao.relaxados continua populado
total_relaxados = sum(len(s.relaxados) for s in sessoes)
print(f"Relaxados: {total_relaxados}")  # esperar > 0

print("Todos os asserts passaram.")
```

Rodar esse script no estado **antes** da limpeza, anotar saída. Rodar
**depois** da limpeza, comparar — esperado: mesmo comportamento (mesmos
asserts passando, mesma ordem de magnitude de avisos/relaxados).

Como não há mais filtro de similaridade, alguns exercícios podem variar
seed por seed (a aleatoriedade entre candidatos com mesma família agora
inclui exercícios que antes seriam preteridos por similaridade). Isso é
esperado e desejado.

Rodar também o `test_demanda_incompleta.py` que foi criado no patch
anterior — não deve quebrar.

---

## Por que isso é seguro

- **O flag `variar_entre_treinos` não tinha efeito** — remover não muda
  comportamento observável.
- **O filtro intra-treino raramente filtra** (3.7%) e quando filtra, é
  por dado pobre, não por design intencional. A regra de família
  (`variacao_de`) já cobre quase todos os casos relevantes, e o
  `relaxar_familia` cobre o que sobra.
- **A próxima fase substitui o conceito** com algo melhor (tags + penalidades),
  então manter o filtro só atrasa a refatoração.

---

*Documento de evidências v3 — números de linha de `app_flask.py` atualizados
(arquivo cresceu ~20 linhas em alterações pequenas; `gerador_treino.py` está
idêntico ao v2).*
