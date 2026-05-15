"""
Fase 4.1 — Gerador de triagem dos 125 exercícios XLSX + 11 mock_futuros YAML.

Saída: docs/refatoracao/triagem_fase_4.md

Regras aplicadas (Seção 7 do dimensoes_proximidade.md):
  - YAML cadastrado (66): dims copiadas do YAML (já decididas clinicamente) → 🟢
  - YAML mock_futuro (11): dims do YAML + extras (eq_primario, purpose etc.) → 🟢
  - Não-YAML (59): heurística por subregião/padrão + flag de ambiguidade

Flags de triagem:
  🟢  todas as 5 dims determinadas pelas diretrizes (Code preenche)
  🟡  1-2 dims precisam de decisão clínica (consultar Bernardo na Fase 4.6)
  🔴  3+ dims ambíguas ou exercício atípico (revisão completa antes de preencher)

NÃO escreve no XLSX.
"""

import sys
import io
import os
import yaml
import pandas as pd
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ─── Caminhos ──────────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX_PATH = os.path.join(BASE, "banco_exercicios.xlsx")
YAML_PATH = os.path.join(BASE, "tools", "mocks", "dimensoes_etapa_6.yaml")
OUT_PATH = os.path.join(BASE, "docs", "refatoracao", "triagem_fase_4.md")

# ─── Helpers ───────────────────────────────────────────────────────────────

def _s(v) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return ""
    return str(v).strip()


def eq_grupo_de(eq_primario: str) -> str | None:
    """
    Heurística: eq_primario → equipamento_grupo (8 grupos da Seção 7.2).
    Retorna None quando não mapeável ou N/A pelo 9-bis (core).
    """
    eq = eq_primario.lower() if eq_primario else ""
    if not eq:
        return None
    if "smith" in eq or "guiado" in eq or "hack" in eq:
        return "barra_guiada"
    if "crossover" in eq or "polia" in eq or "cabo" in eq or "cable" in eq:
        return "polia"
    if "máquina" in eq or "maquina" in eq or "cadeira" in eq or "leg press" in eq:
        return "maquina"
    if "caixa" in eq or "step" in eq or "box" in eq or "banco romano" in eq:
        return "caixa"
    if "elástico" in eq or "elastico" in eq or "glute band" in eq or "band" in eq or "faixa" in eq:
        return "banda_elastica"
    if (
        "halter" in eq or "halteres" in eq or "dumbell" in eq or "dumbbell" in eq
        or "anilha" in eq  # tratamos anilha como halter (free weight análogo) — 🟡 anotado
    ):
        return "halter"
    if "barra" in eq or "rack" in eq or "olímpica" in eq or "olimpica" in eq or "landmine" in eq:
        return "barra"
    if (
        "sem equipamento" in eq or "colchonete" in eq or "chão" in eq or "chao" in eq
        or "barra fixa" in eq or "suspensão" in eq or "suspensao" in eq
        or "banco reto" in eq or "feijao" in eq or "feijão" in eq or "slide" in eq
        or "trx" in eq or "suspensao" in eq
    ):
        return "corporal"
    if "air bike" in eq or "bicicleta" in eq:
        return None  # cardio sem equipamento_grupo relevante
    return None  # não mapeável → 🟡


def is_core_subregiao(sub: str) -> bool:
    return sub in ("core_isometrico", "core_dinamico", "core")


def is_cardio(sub: str) -> bool:
    return sub == "cardio"


def dims_nulas_pegada(padrao: str) -> bool:
    """
    Seção 7.3 diretriz 12 — null para: squats, hinges, knee_flex, tríceps, pranchas.
    Extendido por consistência: adução, abdução, panturrilha (sem diferenciação clínica
    real de grip — marcado como 🟡 onde extensão da regra é julgamento clínico).
    """
    return padrao in (
        "squat_bilateral", "squat_unilateral", "hinge",
        "knee_flexion", "triceps",
        "flexao_tronco", "flexao_lateral", "rotacao_tronco", "flexao_quadril",
        "abduction", "adduction", "flexao_plantar",
    )


def dims_nulas_plano(padrao: str) -> bool:
    """
    Seção 7.4 diretriz 13-14 — plano vazio em:
    squats, knee_flex, tríceps, core, adutores, panturrilha, abduction, bracos, ombro.
    Tem valor em: supinos (reto/inclinado), remadas, hinges (em_pe/deitado), puxadas (pullover).
    """
    return padrao in (
        "squat_bilateral", "squat_unilateral", "knee_flexion", "triceps",
        "biceps", "ombro_composto", "ombro_isolado", "posterior_ombro",
        "abduction", "adduction", "flexao_plantar", "cardio",
        "flexao_tronco", "flexao_lateral", "rotacao_tronco", "flexao_quadril",
    )


# Mapeamentos manuais para exercícios específicos (não cobertos pela heurística de padrão)
# Formato: nome_exato → {dim: (valor, flag, nota)}
OVERRIDES_MANUAIS: dict[str, dict] = {
    # Hinges — plano_corporal (em_pe vs deitado)
    "Good Morning":           {"plano_corporal": ("em_pe", "verde", "extensão de quadril em pé")},
    "Hiperextensão 45°":      {"plano_corporal": ("em_pe", "amarelo", "banco romano 45° ≈ em_pe mas ângulo intermediário — não é nem em_pe puro nem deitado; proposta: em_pe")},
    "Lev. Terra":             {"plano_corporal": ("em_pe", "verde", "")},
    "Lev. Terra Anilha":      {"plano_corporal": ("em_pe", "verde", ""), "equipamento_grupo": ("halter", "amarelo", "eq_primario='suporte anilhas' → anilha livre na mão ≈ halter (free weight); ou null se sem analogia")},
    "Lev. Terra Sumô":        {"plano_corporal": ("em_pe", "verde", "")},
    "Stiff Barra Livre":      {"plano_corporal": ("em_pe", "verde", "")},
    "Stiff Barra Smith":      {"plano_corporal": ("em_pe", "verde", "")},
    "Stiff Halteres":         {"plano_corporal": ("em_pe", "verde", "")},
    "Stiff Uni. Halteres":    {"plano_corporal": ("em_pe", "verde", "")},
    "Stiff Uni. Smith":       {"plano_corporal": ("em_pe", "verde", "")},
    "Hip Thrust":             {"plano_corporal": ("deitado", "verde", "extensão de quadril deitado"), "equipamento_grupo": ("barra", "verde", "Barra olímpica")},
    "Hip Thrust C/ Band":     {"plano_corporal": ("deitado", "verde", ""), "equipamento_grupo": ("banda_elastica", "verde", "")},
    "Hip Thrust Uni.":        {"plano_corporal": ("deitado", "verde", ""), "equipamento_grupo": ("corporal", "amarelo", "eq_primario NaN — sem equipamento (peso corporal)? Confirmar se usa barra/band ou bodyweight")},
    "Ponte":                  {"plano_corporal": ("deitado", "verde", ""), "equipamento_grupo": ("banda_elastica", "verde", "")},
    "Ponte Alternada":        {"plano_corporal": ("deitado", "verde", ""), "equipamento_grupo": ("caixa", "verde", "")},
    "Ponte C/ Band":          {"plano_corporal": ("deitado", "verde", ""), "equipamento_grupo": ("banda_elastica", "verde", "")},
    "Ponte Na Caixa":         {"plano_corporal": ("deitado", "verde", ""), "equipamento_grupo": ("caixa", "verde", "")},
    "Ponte Uni. Caixa":       {"plano_corporal": ("deitado", "verde", ""), "equipamento_grupo": ("caixa", "verde", "")},
    "Ponte Unilateral":       {"plano_corporal": ("deitado", "verde", ""), "equipamento_grupo": ("corporal", "amarelo", "eq_primario NaN — bodyweight com suporte?")},

    # Bíceps — pegada
    "Bíceps 21S":             {"pegada": ("supinada", "verde", "rosca barra = supinada padrão")},
    "Bíceps Banco":           {"pegada": ("supinada", "verde", "rosca inclinada = supinada")},
    "Bíceps Bayesian":        {"pegada": ("supinada", "verde", "rosca polia = supinada")},
    "Bíceps Cabo":            {"pegada": ("supinada", "verde", "rosca polia = supinada")},
    "Bíceps Halteres":        {"pegada": ("supinada", "verde", "rosca direta = supinada")},
    "Bíceps Martelo":         {"pegada": ("neutra", "verde", "martelo = neutra explícita")},

    # Ombro composto — pegada pronada (desenvolvimento overhead press)
    "Desenv. Halteres Sentado": {"pegada": ("pronada", "verde", "desenvolvimento = pronada padrão")},
    "Desenv. Halteres Uni.":    {"pegada": ("pronada", "verde", "")},
    "Desenv. Landmine":         {"pegada": ("neutra", "amarelo", "landmine press = 1 mão segurando ponta da barra = grip neutro; alternativa: pronada se considerarmos pressing pattern")},
    "Desenvolvimento Barra":    {"pegada": ("pronada", "verde", "barbell OHP = pronada")},
    "Desenvolvimento Smith":    {"pegada": ("pronada", "verde", "smith OHP = pronada")},

    # Ombro isolado — elevações
    "Elevação Frontal Anilha":  {"pegada": ("pronada", "verde", "elevação frontal = pronada (palmas pra baixo)"), "equipamento_grupo": ("halter", "amarelo", "anilha segurada nas extremidades = free weight análogo a halter; alternativa: null")},
    "Elevação Frontal Halteres": {"pegada": ("pronada", "verde", "elevação frontal = pronada")},
    "Elevação Lateral":          {"pegada": ("neutra", "verde", "elevação lateral = neutra")},
    "Elevação Lateral Polia":    {"pegada": ("neutra", "verde", "")},
    "Elevação Lateral Sentado":  {"pegada": ("neutra", "verde", "")},

    # Ombro posterior
    "Crucifíxo Invertido":      {"pegada": ("neutra", "verde", "crucifíxo invertido = neutra")},
    "Face Pull (Polia)":        {"pegada": ("aberta", "amarelo", "corda de Face Pull = grip aberto (mãos separadas); alternativa: neutra se considerarmos supinação na puxada")},
    "Posterior Ombro Polia":    {"pegada": ("neutra", "verde", "posterior ombro polia = neutra")},

    # Knee_flexion especiais
    "Cadeira Flexora":          {"equipamento_grupo": ("maquina", "verde", "")},
    "Nordic Curl":              {"equipamento_grupo": ("corporal", "verde", "sem equipamento, ancoramento pelo parceiro")},
    "Flexão Joelhos Feijão":    {"equipamento_grupo": ("corporal", "amarelo", "feijão = rolo de espuma/feijão de espuma sob pé; próximo de corporal; não tem analogia exata nos 8 grupos")},
    "Flexão Joelhos Slide":     {"equipamento_grupo": ("corporal", "amarelo", "slide board sob pé; não é nenhum dos 8 grupos exatos; corporal é o mais próximo")},

    # Adução
    "Copenhagen Adduction":     {"equipamento_grupo": ("corporal", "amarelo", "banco reto como ancoragem = bodyweight; alternativa: null pois o banco não é o vetor de carga")},

    # Panturrilha — pegada (ver nota abaixo)
    "Elevação De Panturrilha Em Pé": {"pegada": (None, "amarelo", "barbell sobre ombros, mãos seguram barra = pronada. Mas panturrilha não está na lista null da Seção 7.3; clinicamente a pegada não diferencia exercícios de panturrilha → proposta: null")},
    "Elevação Unilateral Panturrilha": {"pegada": (None, "amarelo", "idem acima")},

    # Box Jump — ativo=false
    "Box Jump":                 {"ativo": (False, "verde", "Seção 7.8 diretriz 22 — cadastrado mas não ativo no gerador")},

    # Cardio
    "Air Bike (Sprint)":        {"equipamento_grupo": (None, "verde", "cardio — equipamento_grupo null por definição")},
    "Air Bike (Steady State)":  {"equipamento_grupo": (None, "verde", "cardio — equipamento_grupo null por definição")},
}

# ─── Regras padrão para campos ─────────────────────────────────────────────

def inferir_dims_nao_yaml(nome: str, padrao: str, subregiao: str, eq_primario: str) -> dict:
    """
    Retorna proposta de dims para exercício NÃO coberto pelo YAML.
    Cada campo: (valor, flag, nota)
      flag: "verde" | "amarelo" | "vermelho"
    """
    result = {}
    manual = OVERRIDES_MANUAIS.get(nome, {})

    # ── pegada ──────────────────────────────────────────────────────────────
    if "pegada" in manual:
        result["pegada"] = manual["pegada"]
    elif is_core_subregiao(subregiao) or is_cardio(subregiao):
        result["pegada"] = (None, "verde", "core/cardio → null (Seção 7.3)")
    elif dims_nulas_pegada(padrao):
        result["pegada"] = (None, "verde", f"padrão {padrao} → null (Seção 7.3 dir. 12)")
    else:
        # Não temos regra automática → 🟡
        result["pegada"] = (None, "amarelo", f"padrão {padrao}/{subregiao}: revisar valor correto")

    # ── plano_corporal ───────────────────────────────────────────────────────
    if "plano_corporal" in manual:
        result["plano_corporal"] = manual["plano_corporal"]
    elif is_core_subregiao(subregiao) or is_cardio(subregiao):
        result["plano_corporal"] = (None, "verde", "core/cardio → null (Seção 7.4)")
    elif dims_nulas_plano(padrao):
        result["plano_corporal"] = (None, "verde", f"padrão {padrao} → null (Seção 7.4 dir. 14)")
    elif padrao == "empurrar_compostos":
        result["plano_corporal"] = (None, "amarelo", "supino empurrar_compostos: precisa reto vs inclinado (Seção 7.4 dir. 13)")
    elif padrao == "empurrar_isolados":
        result["plano_corporal"] = (None, "amarelo", "crucifíxo/crossover: precisa reto vs inclinado vs null")
    elif padrao == "remadas":
        result["plano_corporal"] = (None, "amarelo", "remada: curvada/baixa_sentada/apoiada/unilateral_apoiada/suspensao")
    elif padrao == "puxadas":
        result["plano_corporal"] = (None, "amarelo", "puxada: null (default) ou pullover")
    elif padrao == "hinge":
        result["plano_corporal"] = (None, "amarelo", "hinge: em_pe ou deitado — não inferido")
    else:
        result["plano_corporal"] = (None, "verde", "null por padrão")

    # ── equipamento_grupo ────────────────────────────────────────────────────
    if "equipamento_grupo" in manual:
        result["equipamento_grupo"] = manual["equipamento_grupo"]
    elif is_core_subregiao(subregiao):
        result["equipamento_grupo"] = (None, "verde", "core → null (Seção 7.2 dir. 9-bis)")
    elif is_cardio(subregiao):
        result["equipamento_grupo"] = (None, "verde", "cardio → null")
    else:
        eq = eq_grupo_de(eq_primario)
        nota = f"eq_primario='{eq_primario}'"
        flag = "verde" if eq else "amarelo"
        if not eq:
            nota += " — não mapeável aos 8 grupos; proposta: null"
        result["equipamento_grupo"] = (eq, flag, nota)

    # ── variante_pontual ─────────────────────────────────────────────────────
    if "variante_pontual" in manual:
        result["variante_pontual"] = manual["variante_pontual"]
    else:
        result["variante_pontual"] = (False, "verde", "default false — não tem uso pontual cross-family")

    # ── ativo ────────────────────────────────────────────────────────────────
    if "ativo" in manual:
        result["ativo"] = manual["ativo"]
    else:
        result["ativo"] = (True, "verde", "default true")

    return result


def flag_global(dims: dict) -> str:
    flags = [v[1] for v in dims.values()]
    if "vermelho" in flags:
        return "🔴"
    if "amarelo" in flags:
        return "🟡"
    return "🟢"


def fmt_val(v) -> str:
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    return str(v)


# ─── Carregar dados ─────────────────────────────────────────────────────────
df = pd.read_excel(XLSX_PATH, sheet_name="Exercícios")
df = df.where(pd.notna(df), None)
rows_xlsx = list(df.to_dict("records"))

with open(YAML_PATH, encoding="utf-8") as f:
    ydata = yaml.safe_load(f)

yaml_by_nome = {e["nome"]: e for e in ydata["exercicios"]}

# ─── Processar exercícios ───────────────────────────────────────────────────
linhas = []  # lista de dicts para a tabela

for row in rows_xlsx:
    nome = _s(row.get("nome"))
    if not nome:
        continue
    padrao = _s(row.get("padrao"))
    subregiao = _s(row.get("subregiao"))
    eq_primario = _s(row.get("eq_primario"))
    variacao_de = _s(row.get("variacao_de")) or "—"

    if nome in yaml_by_nome:
        # YAML cadastrado: dims já decididas clinicamente
        y = yaml_by_nome[nome]
        d = y.get("dimensoes", {})
        dims = {
            "pegada":          (d.get("pegada"),          "verde", "YAML Etapa 6"),
            "plano_corporal":  (d.get("plano_corporal"),  "verde", "YAML Etapa 6"),
            "equipamento_grupo": (d.get("equipamento_grupo"), "verde", "YAML Etapa 6"),
            "variante_pontual": (d.get("variante_pontual", False), "verde", "YAML Etapa 6"),
            "ativo":           (True,                     "verde", "default true"),
        }
        # Box Jump override
        if nome == "Box Jump":
            dims["ativo"] = (False, "verde", "Seção 7.8 — ativo=false")
        fonte = "YAML"
    else:
        dims = inferir_dims_nao_yaml(nome, padrao, subregiao, eq_primario)
        fonte = "NOVO"

    flag = flag_global(dims)

    linhas.append({
        "nome": nome,
        "fonte": fonte,
        "subregiao": subregiao,
        "padrao": padrao,
        "variacao_de": variacao_de,
        "flag": flag,
        "dims": dims,
    })

# Adicionar 11 mock_futuros (não existem no XLSX)
for e in ydata["exercicios"]:
    if e["origem"] != "mock_futuro":
        continue
    nome = e["nome"]
    d = e.get("dimensoes", {})
    ex = e.get("extras", {})
    dims = {
        "pegada":           (d.get("pegada"),           "verde", "YAML mock_futuro"),
        "plano_corporal":   (d.get("plano_corporal"),   "verde", "YAML mock_futuro"),
        "equipamento_grupo": (d.get("equipamento_grupo"), "verde", "YAML mock_futuro"),
        "variante_pontual": (d.get("variante_pontual", False), "verde", "YAML mock_futuro"),
        "ativo":            (True, "verde", "default true"),
    }
    linhas.append({
        "nome": f"{nome} ⟵ mock_futuro",
        "fonte": "MOCK",
        "subregiao": _s(ex.get("subregiao")),
        "padrao": _s(ex.get("padrao")),
        "variacao_de": _s(d.get("familia_estrita")) or "—",
        "flag": "🟢",
        "dims": dims,
    })

# ─── Estatísticas ───────────────────────────────────────────────────────────
n_verde = sum(1 for l in linhas if l["flag"] == "🟢")
n_amarelo = sum(1 for l in linhas if l["flag"] == "🟡")
n_vermelho = sum(1 for l in linhas if l["flag"] == "🔴")

print(f"Total linhas: {len(linhas)}")
print(f"  🟢 verde:    {n_verde}")
print(f"  🟡 amarelo:  {n_amarelo}")
print(f"  🔴 vermelho: {n_vermelho}")
print()

# 🟡 detail
print("=== 🟡 AMARELOS ===")
for l in linhas:
    if l["flag"] != "🟡":
        continue
    issues = []
    for dim, (val, flag, nota) in l["dims"].items():
        if flag == "amarelo":
            issues.append(f"{dim}={fmt_val(val)} [{nota[:80]}]")
    print(f"  {l['nome']:40s}  {l['subregiao']:20s}/{l['padrao']}")
    for issue in issues:
        print(f"    ^ {issue}")

# ─── Escrever Markdown ──────────────────────────────────────────────────────
hoje = date.today().isoformat()

md_lines = []
md_lines.append(f"# Triagem Fase 4 — Cadastro das 5 Dimensões de Proximidade")
md_lines.append(f"")
md_lines.append(f"> **Gerado em:** {hoje} por `tools/gerar_triagem_fase_4.py`")
md_lines.append(f"> **Referência:** Seção 9 + Seção 7 de `docs/refatoracao/dimensoes_proximidade.md`")
md_lines.append(f"> **NÃO modifica o XLSX.** Serve de base para as Fases 4.4-4.7.")
md_lines.append(f"")
md_lines.append(f"## Sumário")
md_lines.append(f"")
md_lines.append(f"| Flag | N | Próxima fase |")
md_lines.append(f"|---|---|---|")
md_lines.append(f"| 🟢 Verde | {n_verde} | 4.4 (YAML) + 4.5 (não-YAML) — Code preenche |")
md_lines.append(f"| 🟡 Amarelo | {n_amarelo} | 4.6 — revisão clínica por critério agrupado |")
md_lines.append(f"| 🔴 Vermelho | {n_vermelho} | 4.7 — revisão clínica completa |")
md_lines.append(f"| **Total** | **{len(linhas)}** | 125 XLSX + 11 mock_futuros |")
md_lines.append(f"")
md_lines.append(f"## Chave de colunas")
md_lines.append(f"")
md_lines.append(f"- **Fonte** — `YAML` = dims vêm do overlay clínico (Etapa 6); `NOVO` = exercício sem overlay; `MOCK` = mock_futuro (linha nova no XLSX)")
md_lines.append(f"- **peg/plan/eq/vp/at** — pegada / plano_corporal / equipamento_grupo / variante_pontual / ativo")
md_lines.append(f"- Valores `null` = campo vazio (None) no XLSX")
md_lines.append(f"- `🟡 nota` após valor = dim com ambiguidade clínica a resolver na Fase 4.6")
md_lines.append(f"")

# Agrupar por subregião
from collections import defaultdict
por_sub = defaultdict(list)
for l in linhas:
    por_sub[l["subregiao"]].append(l)

ORDER = [
    "peito", "costas", "ombro", "bracos",
    "perna_anterior", "perna_posterior", "adutores", "panturrilha",
    "core_isometrico", "core_dinamico", "cardio",
]

def sub_sort_key(sub):
    try:
        return ORDER.index(sub)
    except ValueError:
        return len(ORDER)

for sub in sorted(por_sub.keys(), key=sub_sort_key):
    grupo = por_sub[sub]
    n_g = len(grupo)
    n_v = sum(1 for l in grupo if l["flag"] == "🟢")
    n_a = sum(1 for l in grupo if l["flag"] == "🟡")
    n_r = sum(1 for l in grupo if l["flag"] == "🔴")

    md_lines.append(f"---")
    md_lines.append(f"")
    md_lines.append(f"## {sub.upper()} ({n_g} exercícios — 🟢{n_v} 🟡{n_a} 🔴{n_r})")
    md_lines.append(f"")
    md_lines.append(f"| Flag | Fonte | Nome | Família | Padrão | peg | plan | eq | vp | at | Notas 🟡 |")
    md_lines.append(f"|---|---|---|---|---|---|---|---|---|---|---|")

    for l in sorted(grupo, key=lambda x: (x["padrao"], x["nome"])):
        d = l["dims"]

        def vcell(dim_name):
            val, flag, nota = d[dim_name]
            s = fmt_val(val)
            if flag == "amarelo":
                return f"**{s}** 🟡"
            return s

        notas_amarelo = []
        for dim_name, (val, flag, nota) in d.items():
            if flag == "amarelo" and nota:
                notas_amarelo.append(f"**{dim_name}:** {nota[:100]}")
        nota_cell = "; ".join(notas_amarelo) if notas_amarelo else ""

        nome_display = l["nome"]
        md_lines.append(
            f"| {l['flag']} | {l['fonte']} | {nome_display} | {l['variacao_de']} | {l['padrao']} "
            f"| {vcell('pegada')} | {vcell('plano_corporal')} | {vcell('equipamento_grupo')} "
            f"| {vcell('variante_pontual')} | {vcell('ativo')} | {nota_cell} |"
        )

    md_lines.append(f"")

md_lines.append(f"---")
md_lines.append(f"")
md_lines.append(f"## Casos 🟡 agrupados por critério (Fase 4.6)")
md_lines.append(f"")
md_lines.append(f"> Perguntas agrupadas por critério clínico (Seção 9.1 Etapa 3).")
md_lines.append(f"> Uma resposta genérica resolve N exercícios. Será respondido por Bernardo na Fase 4.6.")
md_lines.append(f"")

# Agrupar 🟡 por dim + padrão/critério
amarelos_por_criterio = defaultdict(list)
for l in linhas:
    if l["flag"] != "🟡":
        continue
    for dim_name, (val, flag, nota) in l["dims"].items():
        if flag == "amarelo":
            # critério = dim + subregiao
            criterio = f"{dim_name} em {l['subregiao']}"
            amarelos_por_criterio[criterio].append((l["nome"], val, nota))

for criterio, casos in sorted(amarelos_por_criterio.items()):
    md_lines.append(f"### {criterio} ({len(casos)} exercícios)")
    md_lines.append(f"")
    for nome, val, nota in casos:
        md_lines.append(f"- **{nome}** — proposta: `{fmt_val(val)}`. Dúvida: {nota[:200]}")
    md_lines.append(f"")

md_content = "\n".join(md_lines)

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(md_content)

print(f"\nEscrito em: {OUT_PATH}")
