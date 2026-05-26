# Log — Calibração `_PESO_ADERENCIA_POR_PERFIL` DESCONTINUADA

**Data**: 2026-05-26
**Branch**: `calibracao-aderencia` (criada, nunca mergeada — descartada no final da sessão)
**Decisão final**: Bernardo encerrou a frente sem implementar nenhuma mudança em `app_flask.py` ou `gerador_csp.py`. Default atual `{alta:2, media:0, baixa:0}` permanece em produção.

---

## O que foi tentado

Handoff inicial (`handoff_2026-05-26_calibracao_aderencia.md`, agora obsoleto)
previa calibração curada do dict de 3 ints baseada em sondagem N=20.
Premissa: a fórmula `(rank_max - tier_rank[s]) * peso_aderencia` da Frente D
diferenciaria os 3 perfis com escolha curada de `(X, Y, Z)`.

### Achado 1 — fórmula é binária na prática

Sondagem pré (`docs/refatoracao/logs/aderencia_calibracao_pre.json`,
N=20 por peso em {-1, 0, 1, 2, 3, 4, 5, 10}, config Full Body 2T região
upper(3)+lower(3)+core(2) × 2 treinos):

| peso | % Principal | % Intermediário | % Acessório |
|---:|---:|---:|---:|
| -1 | 24.7% | 18.4% | 56.9% |
| 0 | 22.2% | 15.9% | 61.9% |
| 1 | **68.8%** | 6.2% | 25.0% |
| 2 | **68.8%** | 6.2% | 25.0% |
| 3 | **68.8%** | 6.2% | 25.0% |
| 4 | **68.8%** | 6.2% | 25.0% |
| 5 | **68.8%** | 6.2% | 25.0% |
| 10 | **68.8%** | 6.2% | 25.0% |

Pesos 1..10 dão **exatamente a mesma distribuição**. A fórmula tem
preferência estrita PRI > INT > ACE com proporção fixa 1:2 (penalty
INT vs ACE) — escala uniformemente; não permite gradação. Peso ≥1 satura
no teto estrutural (~68.8% PRI, limitado por core sem PRI e padrões
secundários sem PRI no banco).

### Achado 2 — diagnóstico clínico do Bernardo

Apresentadas rotinas concretas seed=0/7/23 com peso=0, 1, 2, 4 lado a
lado. Resposta dele: *"esses números não fazem sentido par mim. o que
entendo é como avaliar treinos. lembre que temos Principal, Intermediário
e Acessório. se não faz sentido esse cadastro, então nunca deveriamos
ter criado essas categorias."*

Diagnóstico estrutural: a fórmula só sabe traduzir 3 níveis cadastrados
em 2 estados operacionais (tier ignorado vs tier saturado). Não há
região intermediária do tipo "60% PRI, 30% INT, 10% ACE por design"
— que seria o que clinicamente faz sentido pra um aluno `media`.

### Achado 3 — combinar penalty (Frente D) + softmax (Frente B) entrega gradação suave

Sondagem combinada `(peso_aderencia, slack, temperatura)`, mesma config
canônica (N=20):

| config | peso | slack | T | % PRI | % INT | % ACE | nomes distintos |
|---|---:|---:|---:|---:|---:|---:|---:|
| BASELINE alta atual | 2 | 0 | 1.0 | 68.8% | 6.2% | 25.0% | 60 |
| alta_variada | 2 | 10 | 3.0 | 66.2% | 7.2% | 26.6% | 69 |
| alta_variada+ | 2 | 15 | 3.5 | 65.3% | 6.9% | 27.8% | 71 |
| media_variada | 1 | 15 | 3.5 | 55.3% | 10.3% | 34.4% | 89 |
| media_variada+ | 1 | 20 | 4.0 | 53.4% | 10.9% | 35.6% | 92 |
| baixa_aberta | 0 | 20 | 5.0 | 16.9% | 24.4% | 58.8% | 92 |

O canal funciona — gradação suave de % PRI E aumento mensurável de
variedade de nomes (60→71 em alta; 60→89 em media). Mecanismo: motor
enumera rotinas até `optimal+slack` piores; softmax sorteia com peso
proporcional a `exp(-distancia/T)`. Slack alto + T alto = sorteio mais
espalhado entre rotinas viáveis.

### Achado 4 — efeito colateral observado

Slack/T altos introduzem ocasionalmente Acessórios "fora de contexto" no
bloco A (composto de abertura). Exemplos seed-by-seed:

- `alta_variada` seed=1, T1: **Apoio Ajoelhado [INT]** abrindo peito —
  estranho pra aluno avançado/intermediário.
- `alta_variada` seed=7, T1: **Elevação Frontal Anilha [ACE]** no
  bloco A — frontal antes do composto inverte ordem clínica.
- `alta_variada` seed=23, T2: **Crucifíxo Invertido [ACE]** no bloco A —
  isolation abrindo bloco é discutível.

A fórmula não captura "Acessório que faz sentido como variação" vs
"Acessório que parece misturado". `tier`, `complexidade`, `unilateral`
não codificam essa nuance. Aumentar slack pra ter variedade vira aumentar
risco de escolhas clinicamente estranhas no bloco de abertura.

---

## Decisão de encerramento

Bernardo (citação direta): *"quero parar completamente completamente
com essa implementação. não estamos achando um meio termo. prefiro
regular o app sem diferenciar entre nível de alunos até achar um 'treino
médio' adequado."*

Princípio implícito: enquanto o **treino médio** (rotina default da UI,
sem diferenciar perfil) não estiver clinicamente sólido, diferenciar por
perfil é prematuro. Calibração de aderência exige um baseline confiável
pra cima do qual modular — e esse baseline ainda tem bugs estruturais
(ver Achados 1-3 da auditoria 2026-05-26).

**Próxima prioridade explicitada**: refinamentos que melhoram o "treino
médio" independente de perfil. Achado 3 da auditoria 2026-05-26 (S-B5
diversidade de região INTRA-bloco) é o próximo 🔴, ataca bug clínico
universal (supersets pareando mesma região = circuito do mesmo grupo).

---

## Artefatos preservados

Esta sessão não tocou em `app_flask.py` nem `gerador_csp.py`. Único
output é evidência da investigação:

1. **`tools/sondar_aderencia_calibracao.py`** — sondagem N=20 por peso
   isolado em config canônica. Reproduz o platô binário da fórmula
   atual.
2. **`tools/inspecionar_rotina_por_peso.py`** — comparação visual
   rotina-a-rotina com mesma seed × pesos diferentes. Útil pra
   demonstrar que pesos 1, 2, 4 dão escolhas qualitativamente
   parecidas (variabilidade vem do não-determinismo do CP-SAT, não
   do peso).
3. **`tools/simular_perfis_aderencia.py`** — sondagem combinada
   `(peso, slack, T)`. Útil se a frente for retomada — mostra que o
   canal `slack + softmax` entrega gradação suave de tier.
4. **`docs/refatoracao/logs/aderencia_calibracao_pre.json`** — snapshot
   da sondagem isolada (N=20, 8 pesos). Material primário pra
   referência futura.

Scripts ficam em `tools/` ativos — não atrapalham nada e podem ser
reutilizados ou descartados quando a frente for retomada.

---

## Pendência futura mapeada (NÃO bloqueia uso real)

A frente "calibração de aderência" pode ser retomada quando:

1. Treino médio default da UI estiver clinicamente sólido (depende dos
   demais 3 achados da auditoria 2026-05-26 + Gate de avaliação clínica
   do Bloco 4).
2. Existir um **5º cadastro no XLSX** que diferencie clinicamente PRI/
   INT/ACE de forma que o motor possa modular além de saturação binária.
   Hipóteses (a discutir em frente futura): "Acessório aceitável pra
   abertura de bloco" (boolean) ou "Centralidade Compostos" (2ª dim do
   vetor de perfil — depende de S-T2/S-T3).
3. Existir mecanismo arquitetural pra diferenciar 3 níveis na fórmula
   — opção concreta avaliada nesta sessão: combinar `peso_aderencia`
   (Frente D) + `slack` + `temperatura` (Frente B) por perfil. O canal
   funciona mas tem efeito colateral (Acessórios estranhos em bloco A
   — Achado 4 acima); refinamentos clínicos do banco mitigariam.

Nenhum item acima é caminho crítico do refator declarativo. Pendência
fica em "✅ frentes concluídas" como **❌ DESCONTINUADA** no
`roadmap_csp.md`.
