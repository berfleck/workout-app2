# Guia de Implementação — Painel de Referência + Ferramentas de Variação

## Contexto

O app BF Treinamento (Flask + HTMX) gera treinos para personal trainers. O usuário quer poder **criar treinos novos enquanto visualiza um treino existente** — caso clássico: aluno treina 1x/semana, já tem Treino A, precisa criar Treino B (variação) vendo o A ao lado.

Leia o `CLAUDE.md` do projeto para contexto completo da arquitetura, rotas e estruturas de dados.

## Implementação em 3 Fases

Implementar na ordem abaixo. Cada fase é funcional e testável independentemente. Ao final de cada fase, atualize o `CLAUDE.md` com as novas rotas, variáveis e decisões.

---

## FASE 1 — Painel de Referência + Clonar Treino

### Objetivo
Um painel read-only na aba Treinos que mostra treino(s) de referência carregados do histórico. O usuário gera/edita treinos novos enquanto vê a referência. Também pode clonar a referência para edição.

### 1.1 Backend (`app_flask.py`)

**Nova variável global:**
```python
referencia_ativa: list[Sessao] = []  # treinos carregados como referência (read-only)
referencia_meta: dict = {}            # {"etiqueta": "...", "aluno": "...", "data": "..."}
```

**Novas rotas:**

| Rota | Método | O que faz |
|------|--------|-----------|
| `/referencia/carregar/<reg_id>` | POST | Carrega sessões de um registro do histórico para `referencia_ativa`. Retorna o partial `_referencia.html` |
| `/referencia/carregar-ativo` | POST | Copia as `sessoes_ativas` atuais para `referencia_ativa` (para "fixar" o estado atual antes de gerar novos) |
| `/referencia/limpar` | POST | Limpa `referencia_ativa` e `referencia_meta`. Retorna div vazia |
| `/referencia/clonar` | POST | Faz `deepcopy` de `referencia_ativa` → `sessoes_ativas`. Retorna `_resultado.html` com os treinos clonados prontos para edição |

**Implementação da rota `/referencia/carregar/<reg_id>`:**
```python
@app.route("/referencia/carregar/<reg_id>", methods=["POST"])
def referencia_carregar(reg_id):
    global referencia_ativa, referencia_meta
    historico = carregar_historico()
    reg = next((r for r in historico if r["id"] == reg_id), None)
    if not reg:
        return "Registro não encontrado", 404
    referencia_ativa = [_dict_to_sessao(s) for s in reg["sessoes"]]
    referencia_meta = {
        "etiqueta": reg.get("etiqueta", ""),
        "aluno": reg.get("aluno", "—"),
        "data": reg.get("data", "—"),
        "id": reg_id,
    }
    return render_template("_referencia.html",
                           ref_sessoes=referencia_ativa,
                           ref_meta=referencia_meta,
                           padroes_labels=PADROES_LABELS)
```

**Implementação da rota `/referencia/carregar-ativo`:**
```python
@app.route("/referencia/carregar-ativo", methods=["POST"])
def referencia_carregar_ativo():
    global referencia_ativa, referencia_meta
    if not sessoes_ativas:
        return '<p class="aviso">Nenhum treino ativo para usar como referência.</p>'
    referencia_ativa = copy.deepcopy(sessoes_ativas)
    referencia_meta = {
        "etiqueta": "Sessão atual",
        "aluno": "—",
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    return render_template("_referencia.html",
                           ref_sessoes=referencia_ativa,
                           ref_meta=referencia_meta,
                           padroes_labels=PADROES_LABELS)
```

**Implementação da rota `/referencia/clonar`:**
```python
@app.route("/referencia/clonar", methods=["POST"])
def referencia_clonar():
    global sessoes_ativas, configs_geradas
    if not referencia_ativa:
        return '<p class="aviso">Nenhuma referência carregada.</p>'
    sessoes_ativas = copy.deepcopy(referencia_ativa)
    configs_geradas = []  # configs não se aplicam a clone
    salvar_sessoes_disco()
    return render_template("_resultado.html", sessoes=sessoes_ativas,
                           padroes_labels=PADROES_LABELS, alunos=carregar_alunos())
```

**Implementação da rota `/referencia/limpar`:**
```python
@app.route("/referencia/limpar", methods=["POST"])
def referencia_limpar():
    global referencia_ativa, referencia_meta
    referencia_ativa = []
    referencia_meta = {}
    return ""
```

**Ajustar a rota `/` (index)** para passar `referencia_ativa` e `referencia_meta` ao template:
```python
# Adicionar ao render_template de index():
ref_sessoes=referencia_ativa,
ref_meta=referencia_meta,
```

### 1.2 Novo template `_referencia.html`

Criar `templates/_referencia.html`. É um painel read-only, compacto, colapsável. Estilo visual distinto (borda azul ou cinza para diferenciar da área de edição laranja).

```html
{% if ref_sessoes %}
<div class="ref-panel">
    <div class="ref-header">
        <div>
            <span class="ref-titulo">📌 Referência</span>
            <span class="ref-meta">{{ ref_meta.etiqueta }} · {{ ref_meta.aluno }} · {{ ref_meta.data }}</span>
        </div>
        <div style="display:flex;gap:6px">
            <button class="btn btn-sm"
                    hx-post="/referencia/clonar"
                    hx-target="#resultado"
                    hx-swap="innerHTML">📋 Clonar para edição</button>
            <button class="btn btn-sm"
                    hx-post="/referencia/limpar"
                    hx-target="#ref-container"
                    hx-swap="innerHTML">✕ Fechar</button>
        </div>
    </div>

    {% for sessao in ref_sessoes %}
    <details {% if ref_sessoes|length == 1 %}open{% endif %}>
        <summary style="font-size:13px;padding:6px 0">
            Treino {{ loop.index }} — {% for p in sessao.tipo.split(' + ') if p %}{{ padroes_labels.get(p, p) }}{% if not loop.last %} · {% endif %}{% endfor %}
        </summary>
        {% for bloco in sessao.blocos %}
        <p class="bloco-label">Bloco {{ bloco.label }}</p>
        {% for ex in [bloco.ex1, bloco.ex2, bloco.ex3] if ex %}
        <div class="exercicio ref-exercicio">
            <div class="exercicio-info">
                <span class="exercicio-nome">{{ bloco.label }}{{ loop.index }} · {{ ex.nome }}
                    {% if ex.series or ex.reps %}
                    <span class="prescr-badge">{% if ex.series %}{{ ex.series }}×{% endif %}{{ ex.reps or '' }}{% if ex.rir is not none %} · RIR {{ ex.rir }}{% endif %}</span>
                    {% endif %}
                </span>
                <div class="exercicio-meta">{{ ex.purpose }} · 🔧 {{ ex.eq_primario }}</div>
            </div>
        </div>
        {% endfor %}
        <hr class="thin">
        {% endfor %}
    </details>
    {% endfor %}
</div>
{% endif %}
```

### 1.3 Ajustar `treinos.html`

Adicionar o container de referência **entre o form de config e o `#resultado`**:

```html
<!-- Logo após </form> e antes de <div id="resultado"> -->

<div id="ref-container">
    {% if ref_sessoes %}
        {% include "_referencia.html" %}
    {% endif %}
</div>
```

### 1.4 Adicionar botão no histórico

Em `historico.html`, adicionar um botão "📌 Referência" ao lado de "↩ Carregar" em cada registro:

```html
<button class="btn btn-sm"
        hx-post="/historico/{{ reg.id }}/ver"
        hx-target="...">📌 Referência</button>
```

ATENÇÃO: este botão deve usar a rota `/referencia/carregar/{{ reg.id }}` com `hx-target="#ref-container"`. Para funcionar cross-tab (o botão está na aba Histórico mas o target está na aba Treinos), adicionar `hx-swap="innerHTML"` e após o swap, trocar para a aba Treinos via `hx-on::after-request="showTab('treinos')"`.

Também adicionar um botão "📌 Fixar como referência" na área de resultado (`_resultado.html`) para que o usuário possa fixar os treinos atuais antes de gerar novos:

```html
<!-- Adicionar após o <details> de salvar no histórico em _resultado.html -->
<button class="btn btn-sm"
        hx-post="/referencia/carregar-ativo"
        hx-target="#ref-container"
        hx-swap="innerHTML">📌 Fixar como referência</button>
```

### 1.5 CSS em `base.html`

Adicionar ao `<style>`:

```css
/* Painel de referência */
.ref-panel {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-left: 4px solid #6366f1;
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 20px;
}
.ref-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    flex-wrap: wrap;
    gap: 8px;
}
.ref-titulo {
    font-size: 14px;
    font-weight: 700;
    color: #4f46e5;
}
.ref-meta {
    font-size: 11px;
    color: #9ca3af;
    margin-left: 8px;
}
.ref-exercicio {
    border-left-color: #a5b4fc !important;
    opacity: 0.85;
}
.ref-exercicio .exercicio-nome { font-size: 13px; }
.ref-exercicio .exercicio-meta { font-size: 10px; }
```

### Resultado esperado da Fase 1
- Usuário vai no Histórico → clica "📌 Referência" → volta pra aba Treinos e vê o treino fixado acima da área de resultado
- Pode gerar novos treinos normalmente, vendo a referência
- Botão "📋 Clonar para edição" copia os treinos da referência para edição
- Botão "✕ Fechar" remove o painel
- Botão "📌 Fixar como referência" na área de resultado permite fixar treinos atuais antes de gerar novos

---

## FASE 2 — Bloqueio Automático + Indicador Visual

### Objetivo
Quando a referência está ativa, a geração de novos treinos automaticamente bloqueia exercícios (e variações) presentes na referência. Os painéis de busca mostram quais exercícios já estão na referência.

### 2.1 Bloqueio na geração (`app_flask.py`)

**Ajustar a rota `/gerar`:** antes de chamar `gerar_multiplos_treinos`, se `referencia_ativa` não está vazio, filtrar o banco:

```python
# Dentro de gerar(), antes de chamar gerar_multiplos_treinos:
banco_gerar = list(banco)
if referencia_ativa:
    nomes_ref = set()
    pais_ref = set()
    for s in referencia_ativa:
        for bloco in s.blocos:
            for ex in [bloco.ex1, bloco.ex2, bloco.ex3]:
                if ex:
                    nomes_ref.add(ex.nome)
                    if ex.variacao_de:
                        pais_ref.add(ex.variacao_de)
    banco_gerar = [e for e in banco_gerar
                   if e.nome not in nomes_ref
                   and e.nome not in pais_ref
                   and (e.variacao_de is None or e.variacao_de not in nomes_ref)]

# Trocar a chamada:
sessoes_ativas = gerar_multiplos_treinos(banco_gerar, all_configs, variar_entre_treinos=variar)
```

**Ajustar também a rota `/treino/<t>/regerar`:** aplicar o mesmo filtro de referência somado ao filtro de outros treinos que já existe.

### 2.2 Indicador visual no painel de busca

**Ajustar `/buscar-exercicios`:** receber lista de nomes da referência e marcar visualmente.

Duas opções de implementação (escolher a mais simples):

**Opção A (recomendada):** O backend lê `referencia_ativa` diretamente (já é variável global):

```python
# Dentro de buscar_exercicios():
nomes_ref = set()
for s in referencia_ativa:
    for bloco in s.blocos:
        for ex in [bloco.ex1, bloco.ex2, bloco.ex3]:
            if ex:
                nomes_ref.add(ex.nome)

# Na geração do HTML, marcar exercícios da referência:
for e in cands:
    na_ref = e.nome in nomes_ref
    badge = ' <span style="color:#6366f1;font-size:10px;font-weight:700">REF</span>' if na_ref else ''
    html += (f'<label class="ex-option" {"style=\"opacity:0.6\"" if na_ref else ""}>'
             f'<input type="radio" name="exercicio_escolhido" value="{e.nome}">'
             f'<span>{e.nome}{badge}</span>'
             f'<span class="ex-option-meta">{e.purpose} · {e.eq_primario}</span>'
             f'</label>')
```

Isso NÃO bloqueia a seleção (o usuário pode escolher um exercício da referência se quiser), apenas sinaliza.

### 2.3 Indicador na substituição aleatória

Ajustar `/treino/<t>/substituir/<nome>`: ao buscar substitutos, se `referencia_ativa` está ativo, preferir exercícios que NÃO estão na referência. Não é bloqueio hard — se não houver alternativa, usa o que tiver.

```python
# Na rota substituir():
if referencia_ativa:
    nomes_ref = {ex.nome for s in referencia_ativa for b in s.blocos
                 for ex in [b.ex1, b.ex2, b.ex3] if ex}
    # Filtrar candidatos: prefere não-ref, mas aceita ref se não houver opção
    cands_sem_ref = [c for c in candidatos if c.nome not in nomes_ref]
    candidatos = cands_sem_ref if cands_sem_ref else candidatos
```

### Resultado esperado da Fase 2
- Com referência ativa: gerar treinos automaticamente evita exercícios da referência
- Nos painéis de busca (adicionar/novo bloco), exercícios da referência aparecem com badge "REF" e opacidade reduzida
- Substituição aleatória prefere exercícios fora da referência

---

## FASE 3 — Copiar Bloco da Referência + Diff Visual

### Objetivo
Poder importar blocos individuais da referência para o treino ativo. Comparar lado a lado o treino de referência com o treino ativo para ver diferenças.

### 3.1 Copiar bloco da referência

**Nova rota:**

| Rota | Método | O que faz |
|------|--------|-----------|
| `/referencia/copiar-bloco/<int:ref_t>/<int:ref_bi>/para/<int:dest_t>` | POST | Copia um bloco da referência (treino ref_t, bloco ref_bi) para o final do treino ativo dest_t |

```python
@app.route("/referencia/copiar-bloco/<int:ref_t>/<int:ref_bi>/para/<int:dest_t>", methods=["POST"])
def referencia_copiar_bloco(ref_t, ref_bi, dest_t):
    global sessoes_ativas
    if ref_t >= len(referencia_ativa) or dest_t >= len(sessoes_ativas):
        return "", 404
    bloco_ref = referencia_ativa[ref_t].blocos[ref_bi]
    bloco_novo = copy.deepcopy(bloco_ref)
    labels = "ABCDEFGHIJKLMNOP"
    n = len(sessoes_ativas[dest_t].blocos)
    bloco_novo.label = labels[n] if n < len(labels) else str(n + 1)
    sessoes_ativas[dest_t].blocos.append(bloco_novo)
    salvar_sessoes_disco()
    return render_template("_treino_card.html", sessao=sessoes_ativas[dest_t], idx=dest_t,
                           modo="editar", padroes_labels=PADROES_LABELS,
                           alunos=carregar_alunos(),
                           todos_padroes=sorted(PADROES_LABELS.keys()),
                           todos_equipamentos=todos_equipamentos,
                           todos_musculos=todos_musculos)
```

**Ajustar `_referencia.html`:** adicionar botão de copiar em cada bloco. O botão precisa saber para qual treino ativo enviar. Usar um select ou o mais simples: enviar para o treino 0 (primeiro ativo) com opção de escolher via dropdown se houver múltiplos:

```html
<!-- Dentro do loop de blocos em _referencia.html -->
<div style="display:flex;align-items:center;justify-content:space-between">
    <p class="bloco-label">Bloco {{ bloco.label }}</p>
    <button class="btn-ghost" title="Copiar bloco para treino ativo"
            hx-post="/referencia/copiar-bloco/{{ ref_t_idx }}/{{ bloco_idx }}/para/0"
            hx-target="#treino-0"
            hx-swap="innerHTML"
            style="font-size:11px;color:#6366f1">
        ➡ Copiar
    </button>
</div>
```

Para suportar múltiplos treinos ativos, pode-se usar um dropdown ou simplesmente copiar para o primeiro e deixar o usuário mover. A versão simples (copiar para treino 0) é suficiente para a v1. Se quiser dropdown, usar JS para ler quantos treinos existem e montar o target dinamicamente.

Ajustar o template `_referencia.html` para passar os índices dos loops como variáveis (usar `{% set ref_t_idx = loop.index0 %}` no loop de sessões e `{% set bloco_idx = loop.index0 %}` no loop de blocos).

### 3.2 Diff visual (comparação)

**Nova rota:**

| Rota | Método | O que faz |
|------|--------|-----------|
| `/comparar/<int:ref_t>/<int:ativo_t>` | GET | Retorna HTML com comparação lado a lado |

```python
@app.route("/comparar/<int:ref_t>/<int:ativo_t>")
def comparar_treinos(ref_t, ativo_t):
    if ref_t >= len(referencia_ativa) or ativo_t >= len(sessoes_ativas):
        return "", 404
    ref = referencia_ativa[ref_t]
    ativo = sessoes_ativas[ativo_t]

    nomes_ref = {ex.nome for b in ref.blocos for ex in [b.ex1, b.ex2, b.ex3] if ex}
    nomes_ativo = {ex.nome for b in ativo.blocos for ex in [b.ex1, b.ex2, b.ex3] if ex}

    mantidos = nomes_ref & nomes_ativo
    removidos = nomes_ref - nomes_ativo
    adicionados = nomes_ativo - nomes_ref

    return render_template("_comparacao.html",
                           ref=ref, ativo=ativo,
                           ref_idx=ref_t, ativo_idx=ativo_t,
                           mantidos=mantidos, removidos=removidos, adicionados=adicionados,
                           padroes_labels=PADROES_LABELS)
```

**Novo template `_comparacao.html`:**

Mostrar um resumo no topo ("5 mantidos · 3 removidos · 4 adicionados") seguido de duas colunas: referência à esquerda, ativo à direita. Exercícios mantidos em cinza neutro, removidos com fundo vermelho claro na coluna da referência, adicionados com fundo verde claro na coluna do ativo.

```html
<div class="comparacao-panel">
    <div class="comparacao-header">
        <span class="ref-titulo">Comparação</span>
        <span class="comparacao-stats">
            {{ mantidos|length }} mantido(s) · 
            <span style="color:#dc2626">{{ removidos|length }} removido(s)</span> · 
            <span style="color:#16a34a">{{ adicionados|length }} adicionado(s)</span>
        </span>
    </div>
    <div class="comparacao-grid">
        <div>
            <p class="config-title">Referência (Treino {{ ref_idx + 1 }})</p>
            {% for bloco in ref.blocos %}
            <p class="bloco-label">{{ bloco.label }}</p>
            {% for ex in [bloco.ex1, bloco.ex2, bloco.ex3] if ex %}
            <div class="exercicio {{ 'diff-removido' if ex.nome in removidos else '' }}">
                <div class="exercicio-info">
                    <span class="exercicio-nome" style="font-size:13px">{{ ex.nome }}</span>
                </div>
            </div>
            {% endfor %}
            {% endfor %}
        </div>
        <div>
            <p class="config-title">Ativo (Treino {{ ativo_idx + 1 }})</p>
            {% for bloco in ativo.blocos %}
            <p class="bloco-label">{{ bloco.label }}</p>
            {% for ex in [bloco.ex1, bloco.ex2, bloco.ex3] if ex %}
            <div class="exercicio {{ 'diff-adicionado' if ex.nome in adicionados else '' }}">
                <div class="exercicio-info">
                    <span class="exercicio-nome" style="font-size:13px">{{ ex.nome }}</span>
                </div>
            </div>
            {% endfor %}
            {% endfor %}
        </div>
    </div>
</div>
```

**CSS:**
```css
.comparacao-panel { background: white; border: 1px solid #e5e7eb; border-radius: 14px; padding: 20px; margin-bottom: 16px; }
.comparacao-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.comparacao-stats { font-size: 12px; color: #6b7280; }
.comparacao-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.diff-removido { background: #fef2f2; border-left-color: #f87171 !important; }
.diff-adicionado { background: #f0fdf4; border-left-color: #4ade80 !important; }
@media (max-width: 700px) { .comparacao-grid { grid-template-columns: 1fr; } }
```

**Botão de comparar:** adicionar na `_resultado.html` (visível quando referência está ativa). O botão precisa verificar se `referencia_ativa` existe. Uma abordagem simples: o backend passa `tem_referencia=bool(referencia_ativa)` ao template. Ou: renderizar o botão condicionalmente no `_resultado.html` via variável passada pelo contexto.

Ajustar todas as rotas que renderizam `_resultado.html` para passar `tem_referencia=bool(referencia_ativa)`.

Em `_resultado.html`, adicionar:
```html
{% if tem_referencia %}
<details style="margin:8px 0">
    <summary style="font-size:12px">🔍 Comparar com referência</summary>
    <div id="comparacao-container">
        {% for sessao in sessoes %}
        <button class="btn btn-sm" style="margin:4px"
                hx-get="/comparar/{{ loop.index0 }}/{{ loop.index0 }}"
                hx-target="#comparacao-result"
                hx-swap="innerHTML">
            Treino {{ loop.index }} vs Ref {{ loop.index }}
        </button>
        {% endfor %}
    </div>
    <div id="comparacao-result"></div>
</details>
{% endif %}
```

### Resultado esperado da Fase 3
- No painel de referência, cada bloco tem botão "➡ Copiar" que importa o bloco para o treino ativo
- Na área de resultado, botão "🔍 Comparar" mostra diff visual lado a lado
- Exercícios mantidos, removidos e adicionados são coloridos distintamente

---

## Notas importantes para implementação

1. **Todas as rotas que renderizam `_resultado.html`** devem passar `tem_referencia=bool(referencia_ativa)`. São elas: `/gerar`, `/treino/<t>/regerar` (não diretamente, mas via `_treino_card`), `/referencia/clonar`, `/historico/<id>/carregar`.

2. **O `_referencia.html` é renderizado dentro de `#ref-container`** que fica em `treinos.html`. O container sempre existe no DOM, mesmo vazio. Isso permite que o HTMX do botão no histórico injete nele via `hx-target="#ref-container"`.

3. **A `referencia_ativa` é estado do servidor (variável global)**, mesma abordagem que `sessoes_ativas`. Não persiste em disco (se reiniciar o servidor, perde a referência — ok para v1).

4. **Não modificar o gerador_treino.py** — todo o bloqueio é feito filtrando o `banco` antes de passar para as funções de geração, mesma abordagem que já existe em `treino_regerar`.

5. **O painel de referência NÃO tem botões de edição** — é puramente visual. Exercícios mostram nome, prescrição, purpose e equipamento. Sem ↺, ✕, drag-and-drop etc.

6. **Ao atualizar CLAUDE.md**, adicionar:
   - Novas rotas na tabela de rotas
   - Variáveis `referencia_ativa` e `referencia_meta` na seção "Estado do servidor"
   - `_referencia.html` e `_comparacao.html` na seção "Estrutura de arquivos"
   - Descrição da feature na seção "Funcionalidades implementadas"
