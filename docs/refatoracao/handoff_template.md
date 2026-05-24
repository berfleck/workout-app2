# Handoff de sessão — template

**Propósito**: template curto pra abrir cada sessão de Claude no refator.
Bernardo copia, adapta as 5 seções abaixo, cola no prompt inicial.
Objetivo: orientar a sessão sem ter que reescrever 200 linhas de contexto
a cada vez (norte + roadmap + CLAUDE.md já carregam o resto).

**Como usar**:
1. Copia o bloco "Handoff" abaixo.
2. Preenche as 5 seções.
3. Cola no prompt inicial da nova sessão.
4. Deleta esta seção de explicação (ou mantém pra referência).

---

## Handoff

**Sessão**: [data] — [tema curto, ex: "Micro-frente exercicios_travados"]

**Leitura preparatória (na ordem)**:
1. `docs/refatoracao/norte.md` — princípios e anti-padrões.
2. `docs/refatoracao/roadmap_csp.md` — estado atual + próximas frentes.
3. `docs/refatoracao/catalogo_constraints.md` — se for tocar motor.
4. [opcional: log da última fatia/frente relevante, ex:
   `docs/refatoracao/logs/mvp_fatia_4c_sb4_tamanho.md`]

**Objetivo desta sessão**:
[1 parágrafo. Ex: "Implementar a micro-frente `exercicios_travados`
do Bloco 1 do roadmap. Adicionar constraint hard que fixa slot quando
user trava exercício na UI. Wire em /regerar."]

**Decisões já fechadas (não reabrir sem motivo forte)**:
- [decisão 1, ex: "Branch base: a partir de fatia-4c-sb4-tamanho"]
- [decisão 2]
- [decisão 3 — se aplica]

**Pontos de decisão pendentes (perguntar antes de codar)**:
- [pergunta 1, ex: "Como tratar slot travado com ex que não passa H-P1?"]
- [pergunta 2 — se aplica]

**Restrições / não-fazer**:
- [restrição 1, ex: "Não tocar gerador_treino.py (motor antigo)"]
- [restrição 2, ex: "Não merger pra main sem aprovação"]
- [restrição 3 — se aplica]

---

## Versão mínima (pra micro-frentes simples)

Quando a sessão é trivial (~30min, sem ambiguidade), bastam 3 linhas:

```
Implementar [item do roadmap] em branch `[nome]`. Leituras: norte.md +
roadmap_csp.md + log da fatia anterior. Restrição: não tocar
gerador_treino.py.
```

---

## Anti-padrão de handoff

- **NÃO** repetir contexto que já está em `norte.md` ou `roadmap_csp.md`.
  Esses docs são carregados automaticamente. Handoff é pra **esta sessão**
  específica.
- **NÃO** listar todas as decisões já tomadas no projeto. Listar só as
  que afetam esta sessão diretamente.
- **NÃO** mandar Claude "decidir o que fazer". Handoff é pra delimitar
  escopo, não pra delegar planejamento estratégico (esse vem do roadmap).
- **SIM** preencher "decisões já fechadas" quando há alternativa óbvia
  que Claude pode tentar implementar — fechar a porta evita 1 round de
  AskUserQuestion.
- **SIM** listar "pontos de decisão pendentes" explicitamente — vira
  AskUserQuestion no checkpoint 1 da sessão.
