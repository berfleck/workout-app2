"""
Gerador de Treinos — lógica central
Lê o banco de exercícios (.xlsx) e gera sessões respeitando as regras definidas.

Uso:
    python gerador_treino.py
"""

import math
import pandas as pd
import random
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

XLSX_PATH = "banco_exercicios.xlsx"

# ---------------------------------------------------------------------------
# Hierarquia: Região → Subregião → Padrão
# ---------------------------------------------------------------------------

# Mapeamento PADRÃO → SUBREGIÃO (todo padrão pertence a uma e só uma subregião)
PADRAO_PARA_SUBREGIAO = {
    # Membros inferiores
    "squat_bilateral":  "perna_anterior",
    "squat_unilateral": "perna_anterior",
    "hinge":          "perna_posterior",
    "knee_flexion":   "perna_posterior",
    "abduction":      "perna_posterior",
    "adduction":      "adutores",
    "flexao_plantar": "panturrilha",
    # Membros superiores
    "empurrar_compostos": "peito",
    "empurrar_isolados":  "peito",
    "remadas":            "costas",
    "puxadas":            "costas",
    "ombro_composto":     "ombro",
    "ombro_isolado":      "ombro",
    "posterior_ombro":    "ombro",
    "biceps":             "bracos",
    "triceps":            "bracos",
    # Outros
    "core_isometrico": "core_isometrico",
    "core_dinamico":   "core_dinamico",
    "cardio":          "cardio",
}

# Mapeamento SUBREGIÃO → REGIÃO
SUBREGIAO_PARA_REGIAO = {
    "perna_anterior":  "lower",
    "perna_posterior": "lower",
    "adutores":        "lower",
    "panturrilha":     "lower",
    "peito":  "upper",
    "costas": "upper",
    "ombro":  "upper",
    "bracos": "upper",
    "core_isometrico": "core",
    "core_dinamico":   "core",
    "cardio": "cardio",
}

# Inverso: REGIÃO → lista de SUBREGIÕES, SUBREGIÃO → lista de PADRÕES
# (gerados automaticamente para garantir consistência)
REGIAO_PARA_SUBREGIOES: dict[str, list[str]] = {}
for sub, reg in SUBREGIAO_PARA_REGIAO.items():
    REGIAO_PARA_SUBREGIOES.setdefault(reg, []).append(sub)

SUBREGIAO_PARA_PADROES: dict[str, list[str]] = {}
for pad, sub in PADRAO_PARA_SUBREGIAO.items():
    SUBREGIAO_PARA_PADROES.setdefault(sub, []).append(pad)


# Estrutura essencial/acessório usada na pré-alocação global (Etapa 2).
# Em demanda região(N): garante 1 de cada essencial; vagas restantes ciclam
# por essenciais; acessórias só competem se N > 2 × num_essenciais.
# Quando N < num_essenciais, sorteia uniformemente N essenciais (com seed).
SUBREGIOES_POR_REGIAO: dict[str, dict[str, list[str]]] = {
    "lower": {
        "essenciais": ["perna_anterior", "perna_posterior"],
        "acessorias": ["panturrilha", "adutores"],
    },
    "upper": {
        # posterior_ombro a decidir junto com Etapa 3 (âncoras com peso)
        "essenciais": ["peito", "costas", "ombro"],
        "acessorias": [],
    },
    "core": {
        "essenciais": ["core_dinamico", "core_isometrico"],
        "acessorias": [],
    },
    "cardio": {
        "essenciais": ["cardio"],
        "acessorias": [],
    },
}


# ---------------------------------------------------------------------------
# Etapa 3: Âncoras protegidas (peso + obrigatoriedade)
# ---------------------------------------------------------------------------
# Pesos definem QUOTAS proporcionais (independente do tamanho do banco).
# Sorteio dentro do banco filtrado decide QUAL exercício específico preenche
# cada vaga. Tie-break em arredondamento: obrigatórias > peso maior > ordem.
#
# Subregiões/padrões NÃO listados aqui caem em fallback Etapa 2 (cycling
# uniforme via _decompor_demanda_*). Casos atuais sem âncora:
#   - bracos (sub) e biceps/triceps (padrões): user pede explicitamente
#   - adutores (sub) e adduction (padrão): user pede explicitamente
#   - core_dinamico/core_isometrico: padrões internos a definir no futuro

ANCORAS_POR_REGIAO: dict[str, list[dict]] = {
    "upper": [
        {"subregiao": "peito",  "peso": 2, "obrigatoria": True},
        {"subregiao": "costas", "peso": 2, "obrigatoria": True},
        {"subregiao": "ombro",  "peso": 1, "obrigatoria": True},
    ],
    "lower": [
        {"subregiao": "perna_anterior",  "peso": 2, "obrigatoria": True},
        {"subregiao": "perna_posterior", "peso": 2, "obrigatoria": True},
        {"subregiao": "panturrilha",     "peso": 1, "obrigatoria": False},
    ],
    "core": [
        {"subregiao": "core_dinamico",   "peso": 1, "obrigatoria": False},
        {"subregiao": "core_isometrico", "peso": 1, "obrigatoria": False},
    ],
}

ANCORAS_POR_SUBREGIAO: dict[str, list[dict]] = {
    "peito": [
        {"padrao": "empurrar_compostos", "peso": 3, "obrigatoria": True},
        {"padrao": "empurrar_isolados",  "peso": 2, "obrigatoria": False},
    ],
    "costas": [
        {"padrao": "remadas", "peso": 2, "obrigatoria": True},
        {"padrao": "puxadas", "peso": 2, "obrigatoria": True},
    ],
    "ombro": [
        {"padrao": "ombro_composto",  "peso": 3, "obrigatoria": True},
        {"padrao": "ombro_isolado",   "peso": 2, "obrigatoria": False},
        {"padrao": "posterior_ombro", "peso": 1, "obrigatoria": False},
    ],
    "perna_anterior": [
        {"padrao": "squat_bilateral",  "peso": 3, "obrigatoria": True},
        {"padrao": "squat_unilateral", "peso": 2, "obrigatoria": False},
    ],
    "perna_posterior": [
        {"padrao": "hinge",        "peso": 3, "obrigatoria": True},
        {"padrao": "knee_flexion", "peso": 2, "obrigatoria": False},
        {"padrao": "abduction",    "peso": 1, "obrigatoria": False},
    ],
    "panturrilha": [
        {"padrao": "flexao_plantar", "peso": 1, "obrigatoria": True},
    ],
    # core_dinamico, core_isometrico, bracos, adutores: sem âncoras
    # (fallback pra cycling uniforme da Etapa 2).
}


def _validar_ancoras() -> None:
    """Sanity check: nomes em ANCORAS_* batem com PADRAO_PARA_SUBREGIAO."""
    for regiao, ancoras in ANCORAS_POR_REGIAO.items():
        for a in ancoras:
            sub = a["subregiao"]
            assert sub in SUBREGIAO_PARA_REGIAO, (
                f"ANCORAS_POR_REGIAO[{regiao!r}]: subregião '{sub}' não existe"
            )
            assert SUBREGIAO_PARA_REGIAO[sub] == regiao, (
                f"ANCORAS_POR_REGIAO[{regiao!r}]: '{sub}' aponta pra "
                f"'{SUBREGIAO_PARA_REGIAO[sub]}' em SUBREGIAO_PARA_REGIAO"
            )
    for sub, ancoras in ANCORAS_POR_SUBREGIAO.items():
        for a in ancoras:
            pad = a["padrao"]
            assert pad in PADRAO_PARA_SUBREGIAO, (
                f"ANCORAS_POR_SUBREGIAO[{sub!r}]: padrão '{pad}' não existe"
            )
            assert PADRAO_PARA_SUBREGIAO[pad] == sub, (
                f"ANCORAS_POR_SUBREGIAO[{sub!r}]: '{pad}' aponta pra "
                f"'{PADRAO_PARA_SUBREGIAO[pad]}' em PADRAO_PARA_SUBREGIAO"
            )


_validar_ancoras()


def calcular_quotas(
    ancoras: list[dict],
    vagas: int,
) -> tuple[dict[str, int], list[dict]]:
    """Distribui `vagas` entre âncoras pelos pesos via Hamilton's Largest
    Remainder Method. Mínimos contam na proporção (não são adicionais).

    Args:
        ancoras: lista de dicts {chave, peso, obrigatoria}. `chave` pode ser
            nome de subregião (ANCORAS_POR_REGIAO) ou padrão (ANCORAS_POR_SUBREGIAO).
        vagas: total de vagas a distribuir.

    Returns:
        (quotas, avisos) onde:
          quotas = {chave: qtd_vagas} (chaves com qtd > 0)
          avisos = lista de dicts {tipo: "ancora_nao_cumprida", chave: str,
            motivo: "vagas_insuficientes"} para obrigatórias que ficaram fora.

    Algoritmo:
      1. Se vagas == 0 ou ancoras vazia: retornar ({}, []).
      2. Se vagas < num_obrigatorias: sortear `vagas` entre obrigatórias com
         random.sample (respeita seed do chamador). Obrigatórias não sorteadas
         viram aviso `ancora_nao_cumprida`. Não-obrigatórias ignoradas.
      3. Caso normal: Hamilton's Largest Remainder.
         a. Para cada âncora: ideal = vagas × peso / soma_pesos
         b. floor = int(ideal); resto = ideal - floor
         c. Distribuir vagas remanescentes (vagas - sum(floors)) pra âncoras
            com maior resto. Tie-break em resto: obrigatória > peso maior >
            ordem de definição (estável).
    """
    if vagas <= 0 or not ancoras:
        return {}, []

    obrigatorias = [a for a in ancoras if a.get("obrigatoria")]
    n_obrig = len(obrigatorias)

    # ── Caso especial: vagas < obrigatórias → sorteio ────────────────────
    if vagas < n_obrig:
        sorteadas = random.sample(obrigatorias, vagas)
        quotas = {a["chave"]: 1 for a in sorteadas}
        nomes_sorteadas = {a["chave"] for a in sorteadas}
        avisos = [
            {
                "tipo": "ancora_nao_cumprida",
                "chave": a["chave"],
                "motivo": "vagas_insuficientes",
            }
            for a in obrigatorias
            if a["chave"] not in nomes_sorteadas
        ]
        return quotas, avisos

    # ── Hamilton's Largest Remainder ────────────────────────────────────
    total_peso = sum(a["peso"] for a in ancoras)
    if total_peso <= 0:
        return {}, []

    # Calcula ideal e floor pra cada âncora
    pares = []  # [(idx_estavel, ancora, ideal, floor)]
    for idx, a in enumerate(ancoras):
        ideal = vagas * a["peso"] / total_peso
        pares.append((idx, a, ideal, int(ideal)))

    # Quota inicial = floor
    quotas = {a["chave"]: f for _, a, _, f in pares}
    distribuidas = sum(f for _, _, _, f in pares)
    restantes = vagas - distribuidas

    # Distribuir vagas restantes pelos maiores restos com tie-break:
    # obrigatória > peso maior > ordem de definição (estável)
    if restantes > 0:
        def tiebreak_key(p):
            idx, a, ideal, floor = p
            resto = ideal - floor
            return (
                -resto,                          # maior resto primeiro
                0 if a.get("obrigatoria") else 1,  # obrig primeiro
                -a["peso"],                      # peso maior primeiro
                idx,                             # ordem definição (estável)
            )
        pares_ord = sorted(pares, key=tiebreak_key)
        for _, a, _, _ in pares_ord[:restantes]:
            quotas[a["chave"]] += 1

    # Filtra zeros pra retornar dict limpo
    quotas = {k: v for k, v in quotas.items() if v > 0}
    return quotas, []


def _quotas_de_regiao(regiao: str, vagas: int) -> tuple[dict[str, int], list[dict]]:
    """Aplica ANCORAS_POR_REGIAO[regiao] a `vagas`. Quotas têm chave=subregiao.

    Devolve ({}, []) quando região não tem âncoras (caso atual: cardio).
    Avisos retornados têm campo `nivel="regiao"` e `escopo=regiao`.

    NOTA: Hamilton puro sobre todas as âncoras da região. O filtro
    pré-quotas (acessórias só competem se qtd > 2 × num_obrigatorias) é
    responsabilidade do caller (`_decompor_demanda_regiao` na Sub-PR 2).
    """
    ancoras_raw = ANCORAS_POR_REGIAO.get(regiao, [])
    ancoras = [
        {"chave": a["subregiao"], "peso": a["peso"], "obrigatoria": a["obrigatoria"]}
        for a in ancoras_raw
    ]
    quotas, avisos = calcular_quotas(ancoras, vagas)
    for av in avisos:
        av["nivel"] = "regiao"
        av["escopo"] = regiao
    return quotas, avisos


def _quotas_de_subregiao(subregiao: str, vagas: int) -> tuple[dict[str, int], list[dict]]:
    """Aplica ANCORAS_POR_SUBREGIAO[subregiao] a `vagas`. Quotas têm chave=padrao.

    Devolve ({}, []) quando subregião não tem âncoras (caso atual:
    core_dinamico, core_isometrico, bracos, adutores). Chamador deve cair
    em fallback Etapa 2 (cycling uniforme via _decompor_demanda_subregiao).
    Avisos retornados têm campo `nivel="subregiao"` e `escopo=subregiao`.
    """
    ancoras_raw = ANCORAS_POR_SUBREGIAO.get(subregiao, [])
    ancoras = [
        {"chave": a["padrao"], "peso": a["peso"], "obrigatoria": a["obrigatoria"]}
        for a in ancoras_raw
    ]
    quotas, avisos = calcular_quotas(ancoras, vagas)
    for av in avisos:
        av["nivel"] = "subregiao"
        av["escopo"] = subregiao
    return quotas, avisos


def _distribuir_quotas_entre_treinos(
    quotas_global: dict[str, int],
    n_treinos: int,
    vagas_por_treino: list[int],
    pesos: dict[str, int],
) -> list[dict[str, int]]:
    """Distribui quotas globais entre N treinos via round-robin sobre fila
    intercalada por peso, minimizando concentração de déficit (R6 da Etapa 3).

    Args:
        quotas_global: {chave: qtd_total_na_rotina}.
        n_treinos: número de treinos.
        vagas_por_treino: vagas alocadas pra esta demanda em cada treino.
        pesos: {chave: peso} (usado pra ordenar a fila — peso maior primeiro).

    Returns:
        Lista de N dicts {chave: qtd_no_treino}, soma == quotas_global.

    Algoritmo:
      1. Ordenar chaves por peso desc (tie-break alfabético).
      2. Construir fila intercalada via round-robin pelas qtds.
      3. Distribuir slots pelos N treinos via round-robin, respeitando
         vagas_por_treino (pula treino lotado).
    """
    if n_treinos <= 0:
        return []
    if sum(quotas_global.values()) == 0:
        return [{} for _ in range(n_treinos)]

    # Ordenar chaves por peso desc (tie-break alfabético estável)
    chaves_ord = sorted(
        quotas_global.keys(),
        key=lambda k: (-pesos.get(k, 0), k),
    )

    # Construir fila intercalada via round-robin pelas qtds
    fila: list[str] = []
    qtds = {k: quotas_global[k] for k in chaves_ord}
    while sum(qtds.values()) > 0:
        for k in chaves_ord:
            if qtds[k] > 0:
                fila.append(k)
                qtds[k] -= 1

    # Distribuir slots pelos treinos via round-robin, respeitando capacidade
    por_treino: list[dict[str, int]] = [{} for _ in range(n_treinos)]
    capacidade = list(vagas_por_treino)
    treino_atual = 0
    for chave in fila:
        # Avança até treino com capacidade disponível
        tentativas = 0
        while capacidade[treino_atual] <= 0:
            treino_atual = (treino_atual + 1) % n_treinos
            tentativas += 1
            if tentativas > n_treinos:
                # Sem capacidade em ninguém — consistência interna falha
                # (não deveria acontecer se sum(vagas_por_treino) == sum(quotas))
                break
        else:
            por_treino[treino_atual][chave] = por_treino[treino_atual].get(chave, 0) + 1
            capacidade[treino_atual] -= 1
            treino_atual = (treino_atual + 1) % n_treinos
            continue
        # Loop saiu por break — parar distribuição
        break

    return por_treino


# Classificação composto vs isolado é por EXERCÍCIO via coluna `purpose` do banco.
# compound + explosive → composto. isolation + stability → isolado.
# A constante PADROES_COMPOSTOS abaixo é mantida apenas pra retrocompatibilidade
# de import (não é usada na lógica de seleção). Padrões mistos como `hinge`,
# `squat_*` e `puxadas` têm tanto compostos quanto isolados no banco — a
# classificação por padrão era incorreta.
PURPOSE_COMPOSTO = {"compound", "explosive"}

PADROES_COMPOSTOS = {
    "squat_bilateral", "squat_unilateral", "hinge",
    "empurrar_compostos", "remadas", "puxadas", "ombro_composto",
}

# Tabela de tradução de padrões legados (configs salvas em SQLite ou
# templates antigos podem referenciar `squat`). Frente 4 da Etapa 1
# refinou squat em squat_bilateral + squat_unilateral. Aplicada em
# `expandir_para_padroes`, `_padroes_de_escopo` e `gerar_sessao` legacy.
_PADROES_LEGADOS = {
    "squat": ("squat_bilateral", "squat_unilateral"),
}

# Proporção mínima de compostos em demandas de nível "regiao".
# Ex: 0.6 = ao menos 60% dos exercícios serão compostos.
# Só se aplica quando o escopo tem tanto compostos quanto isolados.
PROPORCAO_COMPOSTOS = 0.6


def _eh_composto(e: "Exercicio") -> bool:
    """Classificação de composto vs isolado no nível do exercício."""
    return e.purpose in PURPOSE_COMPOSTO

# Agrupamento funcional push/pull para evitar pares agonistas em super séries.
# Exercícios do mesmo grupo compartilham musculatura primária ou sinergista relevante:
#   push → peito, ombro anterior/lateral, tríceps
#   pull → costas, ombro posterior, bíceps
# Membros inferiores e core têm grupos próprios.
GRUPO_MUSCULAR_PADRAO: dict[str, str] = {
    # Upper — push
    "empurrar_compostos": "push",
    "empurrar_isolados":  "push",
    "ombro_composto":     "push",
    "ombro_isolado":      "push",
    "triceps":            "push",
    # Upper — pull
    "remadas":         "pull",
    "puxadas":         "pull",
    "posterior_ombro": "pull",
    "biceps":          "pull",
    # Lower — anterior
    "squat_bilateral":  "quad",
    "squat_unilateral": "quad",
    "knee_flexion": "hamstring",
    # Lower — posterior
    "hinge":     "hamstring",
    "abduction": "glute",
    # Lower — outros
    "adduction":      "addutor",
    "flexao_plantar": "calf",
    # Core / cardio
    "core_isometrico": "core",
    "core_dinamico":   "core",
    "cardio":          "cardio",
}


def expandir_para_padroes(
    regioes: list[str] | None = None,
    subregioes: list[str] | None = None,
    padroes: list[str] | None = None,
) -> list[str]:
    """
    Expande seleções de qualquer nível da hierarquia para uma lista plana
    de padrões, sem duplicatas, mantendo a ordem.

    Lógica de "marcar pai = atalho" (Comportamento A):
    - Se padroes específicos foram passados, eles têm prioridade absoluta
    - Subregioes expandem para todos os seus padrões
    - Regioes expandem para todos os padrões de todas as suas subregiões
    - Combinações são unidas (set union) preservando ordem de inserção
    """
    resultado: list[str] = []
    seen: set[str] = set()

    def add(p: str):
        if p not in seen:
            seen.add(p)
            resultado.append(p)

    for r in (regioes or []):
        for sub in REGIAO_PARA_SUBREGIOES.get(r, []):
            for pad in SUBREGIAO_PARA_PADROES.get(sub, []):
                add(pad)
    for sub in (subregioes or []):
        for pad in SUBREGIAO_PARA_PADROES.get(sub, []):
            add(pad)
    for pad in (padroes or []):
        if pad in _PADROES_LEGADOS:
            for filho in _PADROES_LEGADOS[pad]:
                add(filho)
        else:
            add(pad)

    return resultado


# Padrões disponíveis e defaults de exercícios por padrão (usado no modo livre)
EXERCICIOS_POR_PADRAO = {p: 1 for p in PADRAO_PARA_SUBREGIAO}

# Templates: lista de padrões
TEMPLATES = {
    "Full Body": [
        "remadas", "puxadas",
        "empurrar_compostos", "ombro_composto",
        "squat", "hinge", "abduction", "adduction", "core_isometrico",
    ],
    "Full Body + Braços": [
        "remadas", "puxadas",
        "empurrar_compostos", "ombro_composto",
        "squat", "hinge", "abduction", "adduction", "core_isometrico",
        "biceps", "triceps",
    ],
    "Empurrar + Posterior": [
        "empurrar_compostos", "empurrar_isolados", "ombro_composto",
        "hinge", "knee_flexion", "abduction",
        "core_isometrico", "triceps",
    ],
    "Puxar + Anterior": [
        "remadas", "puxadas", "posterior_ombro",
        "squat", "adduction",
        "core_dinamico", "biceps",
    ],
}

# EPP padrão por template (quantos exercícios cada categoria inicia por padrão)
TEMPLATE_EPP = {
    "Full Body": {
        "remadas": 1, "puxadas": 1,
        "empurrar_compostos": 1, "ombro_composto": 1,
        "squat": 1, "hinge": 1, "abduction": 1, "adduction": 1, "core_isometrico": 1,
    },
    "Full Body + Braços": {
        "remadas": 1, "puxadas": 1,
        "empurrar_compostos": 1, "ombro_composto": 1,
        "squat": 1, "hinge": 1, "abduction": 1, "adduction": 1, "core_isometrico": 1,
        "biceps": 1, "triceps": 1,
    },
    "Empurrar + Posterior": {
        "empurrar_compostos": 2, "empurrar_isolados": 1, "ombro_composto": 2,
        "hinge": 2, "knee_flexion": 1, "abduction": 1,
        "core_isometrico": 2, "triceps": 1,
    },
    "Puxar + Anterior": {
        "remadas": 2, "puxadas": 2, "posterior_ombro": 1,
        "squat": 2, "adduction": 1,
        "core_dinamico": 2, "biceps": 1,
    },
}

# Não parear dois exercícios com fadiga >= este valor no mesmo bloco
FADIGA_MAX_PAR = 4

# Tamanho padrão dos blocos (super séries)
TAMANHO_BLOCO_PADRAO = 2


# ---------------------------------------------------------------------------
# Estruturas de dados
# ---------------------------------------------------------------------------

@dataclass
class Exercicio:
    nome: str
    variacao_de: Optional[str]
    eq_primario: str
    eq_secundario: Optional[str]
    regiao: str
    subregiao: str
    padrao: str
    purpose: str
    unilateral: str
    complexidade: int
    fadiga: int
    circuito: str
    similaridade: str
    musculo_primario: str
    obs: Optional[str]
    # Prescrição (definida pelo personal na UI, não vem do banco)
    series: Optional[int] = None
    reps: Optional[str] = None   # ex: "8-12", "10", "12-15"
    rir: Optional[int] = None    # Reps In Reserve 0-4


@dataclass
class SuperSerie:
    label: str
    ex1: Exercicio
    ex2: Optional[Exercicio]
    ex3: Optional[Exercicio] = None


@dataclass
class Sessao:
    tipo: str
    blocos: list[SuperSerie] = field(default_factory=list)
    avisos: list[dict] = field(default_factory=list)
    relaxados: list[str] = field(default_factory=list)  # nomes de exercícios escolhidos via relaxamento de família


# ---------------------------------------------------------------------------
# Carregamento do banco
# ---------------------------------------------------------------------------

def _str(val) -> str:
    if val is None:
        return ""
    try:
        if math.isnan(float(val)):
            return ""
    except (TypeError, ValueError):
        pass
    return str(val).strip()


_EQ_FIXES = {
    "Apoio":           "Sem equipamento",
    "Apoio ajoelhado": "Sem equipamento",
    "Apoio elevado":   "Sem equipamento",
    "Remada trx":      "TRX",
}


def carregar_banco(path: str) -> list[Exercicio]:
    df = pd.read_excel(path, sheet_name="Exercícios")
    df = df.where(pd.notna(df), None)
    exercicios = []
    for _, row in df.iterrows():
        nome = _str(row.get("nome"))
        if not nome:
            continue
        eq_pri = _str(row.get("eq_primario")) or _EQ_FIXES.get(nome, "")
        padrao = _str(row.get("padrao"))
        subregiao_canonica = PADRAO_PARA_SUBREGIAO.get(padrao, "")
        subregiao_xlsx = _str(row.get("subregiao"))
        if subregiao_xlsx and subregiao_canonica and subregiao_xlsx != subregiao_canonica:
            print(
                f"[carregar_banco] WARN: '{nome}' tem subregiao='{subregiao_xlsx}' "
                f"no XLSX, mas padrao='{padrao}' deriva '{subregiao_canonica}' "
                f"do mapa canônico. Usando o mapa."
            )
        exercicios.append(Exercicio(
            nome=nome,
            variacao_de=_str(row.get("variacao_de")) or None,
            eq_primario=eq_pri,
            eq_secundario=_str(row.get("eq_secundario")) or None,
            regiao=_str(row.get("regiao")),
            subregiao=subregiao_canonica,
            padrao=padrao,
            purpose=_str(row.get("purpose")),
            unilateral=_str(row.get("unilateral")),
            complexidade=int(row.get("complexidade") if row.get("complexidade") and not (isinstance(row.get("complexidade"), float) and math.isnan(row.get("complexidade"))) else 1),
            fadiga=int(row.get("fadiga") if row.get("fadiga") and not (isinstance(row.get("fadiga"), float) and math.isnan(row.get("fadiga"))) else 1),
            circuito=_str(row.get("circuito")) or "não",
            similaridade=_str(row.get("similaridade")),
            musculo_primario=_str(row.get("musculo_primario")),
            obs=_str(row.get("obs")) or None,
        ))
    return exercicios


# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------

def filtrar_por_padrao(banco: list[Exercicio], padrao: str) -> list[Exercicio]:
    return [e for e in banco if e.padrao == padrao]


def filtrar_por_equipamentos(
    banco: list[Exercicio],
    equipamentos_bloqueados: list[str],
) -> list[Exercicio]:
    if not equipamentos_bloqueados:
        return banco
    return [e for e in banco if e.eq_primario not in equipamentos_bloqueados]


def filtrar_por_complexidade(
    banco: list[Exercicio],
    max_complexidade: int,
) -> list[Exercicio]:
    return [e for e in banco if e.complexidade <= max_complexidade]


# ---------------------------------------------------------------------------
# Ordenação: compostos antes de todo o resto
# ---------------------------------------------------------------------------

def ordenar_compostos_primeiro(exercicios: list[Exercicio]) -> list[Exercicio]:
    """
    Compostos vêm primeiro. Dentro de cada grupo (compound vs resto),
    ordena por fadiga decrescente para os mais pesados abrirem o bloco.
    """
    compostos = [e for e in exercicios if e.purpose == "compound"]
    resto     = [e for e in exercicios if e.purpose != "compound"]
    compostos.sort(key=lambda e: e.fadiga, reverse=True)
    resto.sort(key=lambda e: e.fadiga, reverse=True)
    return compostos + resto


# ---------------------------------------------------------------------------
# Seleção evitando família (variacao_de)
# ---------------------------------------------------------------------------

def selecionar_evitando_familia(
    candidatos: list[Exercicio],
    variacao_pais_usados: set[str],
    n: int,
    relaxar_familia: bool = False,
    relaxados_out: Optional[list] = None,
) -> list[Exercicio]:
    """
    Seleciona até n exercícios evitando repetir famílias (variacao_de) e nomes.
    Se relaxar_familia=True e o estrito não preencher, relaxa família entre treinos.
    Exercícios escolhidos no relax são adicionados a relaxados_out (se passado).
    """
    nomes_usados: set[str] = set()
    var_pais_local: set[str] = set(variacao_pais_usados)

    def _passa_familia(e):
        if e.nome in var_pais_local:
            return False
        if e.variacao_de and e.variacao_de in var_pais_local:
            return False
        return True

    selecionados: list[Exercicio] = []

    # Tentativa 1: estrito (família + nome)
    pool = list(candidatos)
    random.shuffle(pool)
    for e in pool:
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
        pool = [e for e in candidatos if e.nome not in nomes_usados]
        random.shuffle(pool)
        for e in pool:
            if len(selecionados) >= n:
                break
            selecionados.append(e)
            nomes_usados.add(e.nome)
            if relaxados_out is not None:
                relaxados_out.append(e.nome)

    return selecionados[:n]


# ---------------------------------------------------------------------------
# Ordenamento de blocos
# ---------------------------------------------------------------------------

# Padrões de braço isolado recebem peso mínimo no score de bloco.
# Todos os outros isolados recebem peso intermediário.
_PADROES_BRACO = {"biceps", "triceps"}


def _score_exercicio(e: Exercicio) -> float:
    """
    Pontuação de um exercício para fins de ordenamento de blocos.
    Compostos recebem base 10 + fadiga (11–15) para garantir que qualquer bloco
    com 2 compostos pontue acima de qualquer bloco com apenas 1 composto.
    """
    if e.purpose == "compound":
        return 10.0 + float(e.fadiga)   # 11–15: composto
    if e.padrao in _PADROES_BRACO:
        return e.fadiga * 0.1           # 0.1–0.5: isolado de braço
    return e.fadiga * 0.5               # 0.5–2.5: isolado de grupo grande


def ordenar_blocos(blocos: list[tuple]) -> list[tuple]:
    """
    Reordena blocos por prioridade decrescente (soma dos scores).
    Resultado típico:
      1º/2º — blocos com 2 compostos (score 22–30)
      3º    — bloco com 1 composto + 1 isolado (score 11.5–17.5)
      último — blocos só com isolados ou isolados de braço
    """
    return sorted(blocos, key=lambda b: sum(_score_exercicio(e) for e in b), reverse=True)


# ---------------------------------------------------------------------------
# Pareamento em super séries
# ---------------------------------------------------------------------------

def pode_adicionar_ao_bloco(bloco_atual: list, candidato: Exercicio, tamanho_bloco: int) -> bool:
    """Verifica se o candidato pode entrar no bloco respeitando a regra de fadiga."""
    max_alta_fadiga = 1 if tamanho_bloco <= 2 else 2
    alta_fadiga_no_bloco = sum(1 for e in bloco_atual if e.fadiga >= FADIGA_MAX_PAR)
    if candidato.fadiga >= FADIGA_MAX_PAR and alta_fadiga_no_bloco >= max_alta_fadiga:
        return False
    return True


def _buscar_candidato(
    exercicios: list[Exercicio],
    usados: list[bool],
    bloco_atual: list[Exercicio],
    regioes: set[str],
    padroes: set[str],
    tamanho: int,
    evitar_unilateral: bool = False,
    evitar_agonistas: bool = False,
) -> int | None:
    """
    Retorna o índice do melhor candidato para entrar no bloco, ou None.

    Prioridades geográficas (P1 > P2 > P3 > P4):
      P1: região diferente E padrão diferente
      P2: região diferente
      P3: padrão diferente
      P4: qualquer válido

    Dentro de cada prioridade, sub-preferências qualitativas (melhor → pior):
      1. Não-agonista E preferido (parceiro composto)
      2. Não-agonista
      3. Preferido (parceiro composto)
      4. Sem restrição adicional (fallback)

    "Não-agonista": o candidato não pertence ao mesmo grupo push/pull do âncora.
    "Preferido": candidato com purpose == "compound" — compostos procuram parceiros
    compostos para formar blocos pesados; isolados também buscam compostos como parceiros.
    Se evitar_agonistas=False, a regra de agonistas é ignorada.
    Se evitar_unilateral=True e já há um unilateral no bloco, candidatos unilaterais
    são ignorados (mas usados no último fallback se necessário).
    """
    n = len(exercicios)
    ja_tem_uni = evitar_unilateral and any(e.unilateral == "unilateral" for e in bloco_atual)
    anchor_purpose = bloco_atual[0].purpose if bloco_atual else None

    # Grupos musculares já presentes no bloco (para evitar agonistas)
    grupos_no_bloco: set[str] = set()
    if evitar_agonistas:
        for e in bloco_atual:
            g = GRUPO_MUSCULAR_PADRAO.get(e.padrao)
            if g:
                grupos_no_bloco.add(g)

    def aceita(j: int) -> bool:
        if usados[j]:
            return False
        if not pode_adicionar_ao_bloco(bloco_atual, exercicios[j], tamanho):
            return False
        if ja_tem_uni and exercicios[j].unilateral == "unilateral":
            return False
        return True

    def nao_agonista(j: int) -> bool:
        if not evitar_agonistas:
            return True
        g = GRUPO_MUSCULAR_PADRAO.get(exercicios[j].padrao)
        return g not in grupos_no_bloco

    def preferido(j: int) -> bool:
        # Compostos são sempre o parceiro ideal, independente do purpose do âncora.
        # Para âncora composta: forma blocos compound+compound (mais pesados primeiro).
        # Para âncora isolada: puxa um composto para o bloco (superset equilibrado).
        return exercicios[j].purpose == "compound"

    def _primeiro(geo_fn, extra_fn) -> int | None:
        for j in range(n):
            if aceita(j) and geo_fn(j) and extra_fn(j):
                return j
        return None

    # Prioridades geográficas
    p1 = lambda j: exercicios[j].regiao not in regioes and exercicios[j].padrao not in padroes
    p2 = lambda j: exercicios[j].regiao not in regioes
    p3 = lambda j: exercicios[j].padrao not in padroes
    p4 = lambda j: True

    # Sub-preferências qualitativas
    sub1 = lambda j: nao_agonista(j) and preferido(j)
    sub2 = lambda j: nao_agonista(j)
    sub3 = lambda j: preferido(j)
    sub4 = lambda j: True

    for geo in [p1, p2, p3, p4]:
        for sub in [sub1, sub2, sub3, sub4]:
            r = _primeiro(geo, sub)
            if r is not None:
                return r
    return None


def montar_blocos(
    exercicios: list[Exercicio],
    tamanho: int = 2,
    evitar_agonistas: bool = False,
) -> list[tuple]:
    """
    Monta blocos de tamanho configurável (1, 2 ou 3).
    Prioriza regiões E padrões diferentes dentro do bloco para distribuir
    categorias uniformemente (ex: não colocar 2 squats no mesmo bloco).
    Em blocos de 2 exercícios, tenta evitar dois exercícios unilaterais juntos.
    Se evitar_agonistas=True, evita parear exercícios do mesmo grupo push/pull.
    O último bloco pode ter menos exercícios se não houver suficientes.
    Retorna lista de tuplas de tamanho variável.
    """
    if not exercicios:
        return []

    usados = [False] * len(exercicios)
    blocos = []

    i = 0
    while i < len(exercicios):
        if usados[i]:
            i += 1
            continue

        bloco_atual = [exercicios[i]]
        usados[i] = True
        regioes_no_bloco = {exercicios[i].regiao}
        padroes_no_bloco = {exercicios[i].padrao}

        while len(bloco_atual) < tamanho:
            melhor = None

            # Para blocos de 2: primeira passagem evitando 2 unilaterais
            if tamanho <= 2:
                melhor = _buscar_candidato(
                    exercicios, usados, bloco_atual,
                    regioes_no_bloco, padroes_no_bloco, tamanho,
                    evitar_unilateral=True,
                    evitar_agonistas=evitar_agonistas,
                )

            # Fallback (ou blocos de 3): sem restrição de unilateral
            if melhor is None:
                melhor = _buscar_candidato(
                    exercicios, usados, bloco_atual,
                    regioes_no_bloco, padroes_no_bloco, tamanho,
                    evitar_unilateral=False,
                    evitar_agonistas=evitar_agonistas,
                )

            if melhor is None:
                break

            bloco_atual.append(exercicios[melhor])
            regioes_no_bloco.add(exercicios[melhor].regiao)
            padroes_no_bloco.add(exercicios[melhor].padrao)
            usados[melhor] = True

        blocos.append(tuple(bloco_atual))
        i += 1

    return blocos


# ---------------------------------------------------------------------------
# Substituição pontual de exercício
# ---------------------------------------------------------------------------

def substituir_exercicio(
    sessao: Sessao,
    nome_atual: str,
    banco: list[Exercicio],
    equipamentos_bloqueados: Optional[list[str]] = None,
    max_complexidade: int = 5,
    escopo: str = "padrao",
) -> Sessao:
    """
    Substitui um exercício específico na sessão por outro do mesmo padrão
    (escopo='padrao', default) ou da mesma subregião (escopo='subregiao').
    """
    eq_bloq = equipamentos_bloqueados or []

    # Encontrar o exercício a substituir e seu contexto
    exercicio_alvo = None
    bloco_idx = None
    posicao = None  # "ex1" ou "ex2"

    for i, bloco in enumerate(sessao.blocos):
        if bloco.ex1.nome == nome_atual:
            exercicio_alvo = bloco.ex1
            bloco_idx = i
            posicao = "ex1"
            break
        if bloco.ex2 and bloco.ex2.nome == nome_atual:
            exercicio_alvo = bloco.ex2
            bloco_idx = i
            posicao = "ex2"
            break
        if bloco.ex3 and bloco.ex3.nome == nome_atual:
            exercicio_alvo = bloco.ex3
            bloco_idx = i
            posicao = "ex3"
            break

    if exercicio_alvo is None:
        print(f"  [!] Exercício '{nome_atual}' não encontrado na sessão.")
        return sessao

    # Nomes já em uso na sessão
    nomes_em_uso = set()
    for bloco in sessao.blocos:
        nomes_em_uso.add(bloco.ex1.nome)
        if bloco.ex2:
            nomes_em_uso.add(bloco.ex2.nome)
        if bloco.ex3:
            nomes_em_uso.add(bloco.ex3.nome)
    nomes_em_uso.discard(nome_atual)

    # Buscar substituto: mesmo padrão (ou subregião) e sem repetir nomes da sessão
    if escopo == "subregiao":
        sub_alvo = exercicio_alvo.subregiao or None
        candidatos = [e for e in banco if e.subregiao == sub_alvo] if sub_alvo else []
    else:
        candidatos = filtrar_por_padrao(banco, exercicio_alvo.padrao)
    candidatos = filtrar_por_equipamentos(candidatos, eq_bloq)
    candidatos = filtrar_por_complexidade(candidatos, max_complexidade)
    candidatos = [e for e in candidatos if e.nome not in nomes_em_uso and e.nome != nome_atual]

    if not candidatos:
        print(f"  [!] Nenhum substituto encontrado para '{nome_atual}'.")
        return sessao

    substituto = random.choice(candidatos)

    # Aplicar substituição
    import copy
    nova_sessao = copy.deepcopy(sessao)
    bloco = nova_sessao.blocos[bloco_idx]
    if posicao == "ex1":
        bloco.ex1 = substituto
    elif posicao == "ex2":
        bloco.ex2 = substituto
    else:
        bloco.ex3 = substituto

    print(f"  [OK] '{nome_atual}' substituido por '{substituto.nome}'")
    return nova_sessao


# ---------------------------------------------------------------------------
# Geração da sessão
# ---------------------------------------------------------------------------

def gerar_sessao(
    banco: list[Exercicio],
    padroes: list[str],
    exercicios_por_padrao: Optional[dict] = None,
    equipamentos_bloqueados: Optional[list[str]] = None,
    max_complexidade: int = 5,
    variacao_pais_usados: Optional[set] = None,
    exercicios_travados: Optional[list[Exercicio]] = None,
    tamanho_bloco: int = 2,
    evitar_agonistas: bool = False,
    relaxar_familia: bool = False,
) -> Sessao:
    epp      = exercicios_por_padrao or EXERCICIOS_POR_PADRAO
    eq_bloq  = equipamentos_bloqueados or []
    var_pais = variacao_pais_usados or set()
    travados = exercicios_travados or []

    todos_selecionados: list[Exercicio] = []
    avisos_da_sessao: list[dict] = []
    relaxados_local: list[str] = []

    # Exercícios travados entram primeiro
    for e in travados:
        todos_selecionados.append(e)

    # Selecionar por padrão
    nomes_travados = {e.nome for e in travados}

    # Retrocompat Frente 4: padrões legados ("squat") são expandidos.
    # - EPP int N → cycling entre os 2 filhos (B3.iii do plano).
    # - EPP dict {"bilateral": X, "unilateral": Y} → split direto pros 2 filhos
    #   (cobre configs salvas que usavam lateralidade_por_padrao via legacy mode).
    padroes_iter: list[tuple[str, list[tuple[Optional[str], int]]]] = []
    for padrao in padroes:
        n_spec = epp.get(padrao, 1)
        if padrao in _PADROES_LEGADOS:
            filhos = _PADROES_LEGADOS[padrao]
            if isinstance(n_spec, dict):
                # split direto: bilateral→squat_bilateral, unilateral→squat_unilateral
                lat_para_filho = {"bilateral": "squat_bilateral", "unilateral": "squat_unilateral"}
                for lat, qt in n_spec.items():
                    if qt <= 0: continue
                    filho = lat_para_filho.get(lat)
                    if filho:
                        padroes_iter.append((filho, [(None, qt)]))
            else:
                # cycling: distribuir N entre os 2 filhos com viés aleatório.
                # ceil(N/2) pro primeiro filho do shuffle, floor(N/2) pro segundo.
                # N=1 → (1, 0): 50/50 entre bi/uni dependendo do shuffle.
                # N=2 → (1, 1); N=3 → (2, 1); N=4 → (2, 2).
                total = int(n_spec)
                ordem = list(filhos); random.shuffle(ordem)
                cotas = [(total + 1) // 2, total // 2]
                for filho, qt in zip(ordem, cotas):
                    if qt > 0:
                        padroes_iter.append((filho, [(None, qt)]))
        else:
            if isinstance(n_spec, dict):
                sub_specs = [(lat, qt) for lat, qt in n_spec.items() if qt > 0]
            else:
                sub_specs = [(None, n_spec)]
            padroes_iter.append((padrao, sub_specs))

    # Mapa de padrões internos → escopo reportado em avisos (UI legada espera "squat")
    _AVISO_ESCOPO_FALLBACK = {filho: legado for legado, filhos in _PADROES_LEGADOS.items() for filho in filhos}

    for padrao, sub_specs in padroes_iter:
        n_antes_padrao = len(todos_selecionados)
        n_antes_relax = len(relaxados_local)
        n_pedido_padrao = sum(qt for _, qt in sub_specs)

        for lateralidade, n in sub_specs:
            candidatos = filtrar_por_padrao(banco, padrao)
            candidatos = filtrar_por_equipamentos(candidatos, eq_bloq)
            candidatos = filtrar_por_complexidade(candidatos, max_complexidade)
            candidatos = [e for e in candidatos if e.nome not in nomes_travados]
            if lateralidade:
                candidatos = [e for e in candidatos if e.unilateral == lateralidade]

            selecionados = selecionar_evitando_familia(
                candidatos, var_pais, n,
                relaxar_familia=relaxar_familia,
                relaxados_out=relaxados_local,
            )
            todos_selecionados.extend(selecionados)

        # Escopo reportado em avisos: usa o nome legado (ex: "squat") quando
        # padrão interno é filho refinado (squat_bilateral / squat_unilateral).
        # Mantém compatibilidade com UI/snapshots que esperam o nome agregado.
        escopo_aviso = _AVISO_ESCOPO_FALLBACK.get(padrao, padrao)

        # Avisos do tipo familia_repetida (1 por exercício relaxado)
        novos_relax = relaxados_local[n_antes_relax:]
        for nome_rel in novos_relax:
            ex_rel = next((e for e in todos_selecionados if e.nome == nome_rel), None)
            avisos_da_sessao.append({
                "tipo": "familia_repetida",
                "nivel": "padrao",
                "escopo": escopo_aviso,
                "exercicio": nome_rel,
                "familia": (ex_rel.variacao_de if ex_rel and ex_rel.variacao_de else nome_rel),
            })

        n_obtido_padrao = len(todos_selecionados) - n_antes_padrao
        if n_obtido_padrao < n_pedido_padrao:
            nomes_em_escopo: set[str] = set()
            for e in banco:
                if e.padrao == padrao:
                    nomes_em_escopo.add(e.nome)
                    if e.variacao_de:
                        nomes_em_escopo.add(e.variacao_de)
            familias_usadas = sorted(n for n in var_pais if n in nomes_em_escopo)
            avisos_da_sessao.append({
                "tipo": "incompleta",
                "nivel": "padrao",
                "escopo": escopo_aviso,
                "qtd_pedida": n_pedido_padrao,
                "qtd_obtida": n_obtido_padrao,
                "faltam": n_pedido_padrao - n_obtido_padrao,
                "familias_usadas": familias_usadas,
            })

    # Ordenar: compostos primeiro, depois o resto
    todos_selecionados = ordenar_compostos_primeiro(todos_selecionados)

    # Montar e ordenar blocos
    grupos = ordenar_blocos(montar_blocos(todos_selecionados, tamanho=tamanho_bloco, evitar_agonistas=evitar_agonistas))

    # Criar SuperSeries
    labels = "ABCDEFGHIJKLMNOP"
    blocos = []
    for i, grupo in enumerate(grupos):
        label = labels[i] if i < len(labels) else str(i + 1)
        ex1 = grupo[0]
        ex2 = grupo[1] if len(grupo) > 1 else None
        ex3 = grupo[2] if len(grupo) > 2 else None
        blocos.append(SuperSerie(label=label, ex1=ex1, ex2=ex2, ex3=ex3))

    tipo = " + ".join(padroes)
    sessao = Sessao(tipo=tipo, blocos=blocos)
    sessao.avisos = avisos_da_sessao
    sessao.relaxados = list(relaxados_local)
    return sessao


# ---------------------------------------------------------------------------
# Geração por DEMANDAS (Opção C: 1 de cada padrão antes de repetir,
# priorizando compostos)
# ---------------------------------------------------------------------------

def _padroes_de_escopo(
    nivel: str, escopo: str
) -> list[str]:
    """Retorna a lista de padrões pertencentes a um escopo (regiao/subregiao/padrao)."""
    if nivel == "padrao":
        # Retrocompat: o padrão antigo "squat" foi refinado em
        # squat_bilateral + squat_unilateral (Frente 4 da refatoração).
        # Configs salvos em SQLite ou testes antigos podem ainda pedir
        # ("padrao", "squat", N) — expandimos para os 2 filhos.
        if escopo in _PADROES_LEGADOS:
            return list(_PADROES_LEGADOS[escopo])
        return [escopo]
    if nivel == "subregiao":
        # Retrocompat: a subregião antiga "core" foi quebrada em
        # core_dinamico + core_isometrico (Frente 3 da refatoração).
        # Configs salvos em SQLite ou testes antigos podem ainda pedir
        # ("subregiao", "core", N) — expandimos para os padrões das duas
        # subregiões novas pra preservar comportamento.
        if escopo == "core":
            return list(SUBREGIAO_PARA_PADROES.get("core_dinamico", [])) + \
                   list(SUBREGIAO_PARA_PADROES.get("core_isometrico", []))
        return list(SUBREGIAO_PARA_PADROES.get(escopo, []))
    if nivel == "regiao":
        pads: list[str] = []
        for sub in REGIAO_PARA_SUBREGIOES.get(escopo, []):
            pads.extend(SUBREGIAO_PARA_PADROES.get(sub, []))
        return pads
    return []


def _ordenar_padroes_por_prioridade(
    padroes: list[str],
    banco: Optional[list["Exercicio"]] = None,
) -> list[str]:
    """
    Padrões com candidatos compostos disponíveis no banco vêm primeiro
    (a classificação é dinâmica via purpose, não via lista estática).
    Dentro de cada grupo, ordem aleatória pra evitar viés determinístico.

    Se `banco` for None, faz shuffle simples (sem priorizar — modo legado).
    """
    if banco is None:
        out = list(padroes)
        random.shuffle(out)
        return out

    com_compostos: list[str] = []
    sem_compostos: list[str] = []
    for p in padroes:
        cands = [e for e in banco if e.padrao == p]
        if any(_eh_composto(e) for e in cands):
            com_compostos.append(p)
        else:
            sem_compostos.append(p)
    random.shuffle(com_compostos)
    random.shuffle(sem_compostos)
    return com_compostos + sem_compostos


# ---------------------------------------------------------------------------
# Pré-alocação global (Etapa 2 da refatoração v4)
#
# Antes de qualquer treino ser montado, alocamos os exercícios entre os N
# treinos de uma rotina, ordenando vagas por escassez (slots com poucos
# candidatos viáveis vão primeiro). Resolve viés posterior > anterior em
# lower(N), bloqueios em cadeia, e treinos finais incompletos.
#
# Princípio quota → sorteio (Seção 2 do guia v4): a Fase 0 (quota) decide
# QUANTOS exercícios de cada subregião/padrão entram; o sorteio dentro do
# pool de cada slot decide QUAL exercício específico. Etapa 3 vai estender
# a quota com pesos clínicos, sem mexer no sorteio.
# ---------------------------------------------------------------------------


@dataclass
class _Slot:
    """Vaga unitária na pré-alocação global. Granular: 1 vaga = 1 exercício."""
    treino_idx: int
    d_idx_original: int        # índice da demanda no config[treino_idx]
    nivel: str                  # "regiao" | "subregiao" | "padrao"
    escopo_alocacao: str       # subregião ou padrão fixado pra este slot
    escopo_demanda_original: str  # escopo da demanda mãe (regiao quando vem de regiao)
    requer_composto: bool      # True = a quota composta da demanda mãe ainda não foi cumprida


def _peso_nivel(nivel: str) -> int:
    """Tie-breaker: granular (padrão) ganha em empate de escassez."""
    return {"padrao": 0, "subregiao": 1, "regiao": 2}.get(nivel, 9)


def _normalizar_config(cfg: dict) -> dict:
    """Converte um cfg em formato canônico com `demandas` (D4 opção C).

    - Se `cfg` tem `demandas`: pass-through (já é o formato canônico).
    - Se `cfg` tem `padroes` + `exercicios_por_padrao`: converte cada
      `(padrao, qtd)` em `("padrao", padrao, qtd)`. Trata _PADROES_LEGADOS
      ("squat" → squat_bilateral + squat_unilateral) preservando comportamento
      atual via `lateralidade_por_padrao`.
    """
    if cfg.get("demandas"):
        return dict(cfg)

    padroes = cfg.get("padroes", []) or []
    epp = cfg.get("exercicios_por_padrao", {}) or {}
    lat_atual = dict(cfg.get("lateralidade_por_padrao") or {})
    demandas: list[tuple[str, str, int]] = []

    for p in padroes:
        n_spec = epp.get(p, 1)

        if p in _PADROES_LEGADOS:
            filhos = _PADROES_LEGADOS[p]
            if isinstance(n_spec, dict):
                # split direto: bilateral→squat_bilateral, unilateral→squat_unilateral
                lat_para_filho = {"bilateral": "squat_bilateral", "unilateral": "squat_unilateral"}
                for lat, qt in n_spec.items():
                    if qt <= 0:
                        continue
                    filho = lat_para_filho.get(lat)
                    if filho:
                        demandas.append(("padrao", filho, qt))
            else:
                # cycling: ceil/floor entre os 2 filhos com viés aleatório
                total = int(n_spec)
                if total > 0:
                    ordem = list(filhos)
                    random.shuffle(ordem)
                    cotas = [(total + 1) // 2, total // 2]
                    for filho, qt in zip(ordem, cotas):
                        if qt > 0:
                            demandas.append(("padrao", filho, qt))
        else:
            if isinstance(n_spec, dict):
                # EPP-dict de lateralidade preserva comportamento via lateralidade_por_padrao
                # Total de vagas = soma dos qts; lateralidade aplicada na Fase 1.
                total = sum(qt for qt in n_spec.values() if qt > 0)
                if total > 0:
                    demandas.append(("padrao", p, total))
                    lat_atual[p] = {lat: qt for lat, qt in n_spec.items() if qt > 0}
            else:
                if int(n_spec) > 0:
                    demandas.append(("padrao", p, int(n_spec)))

    out = dict(cfg)
    out["demandas"] = demandas
    if lat_atual:
        out["lateralidade_por_padrao"] = lat_atual
    return out


def _candidatos_estritos(
    banco: list[Exercicio],
    nivel: str,
    escopo: str,
    cfg_treino: dict,
    nomes_bloqueados: set[str],
    familias_bloqueadas: set[str],
    filtro_purpose: Optional[str] = None,  # None | "composto" | "isolado"
) -> list[Exercicio]:
    """Retorna candidatos viáveis pra um slot no MODO ESTRITO.

    Aplica filtros user (eq, complexidade), filtros de hierarquia (padrões do
    escopo), e bloqueia nomes + famílias já alocados. Não considera relax.
    """
    eq_bloq = cfg_treino.get("equipamentos_bloqueados") or []
    max_cx = cfg_treino.get("max_complexidade", 5)
    lat_map = cfg_treino.get("lateralidade_por_padrao") or {}
    padroes_do_escopo = _padroes_de_escopo(nivel, escopo)

    cands: list[Exercicio] = []
    for e in banco:
        if e.padrao not in padroes_do_escopo:
            continue
        if e.eq_primario in eq_bloq:
            continue
        if e.complexidade > max_cx:
            continue
        if e.nome in nomes_bloqueados:
            continue
        if e.nome in familias_bloqueadas:
            continue
        if e.variacao_de and e.variacao_de in familias_bloqueadas:
            continue
        # Lateralidade: se a demanda original (escopo) tem filtro explícito
        # via lateralidade_por_padrao (template legado), aplicar.
        if escopo in lat_map and isinstance(lat_map[escopo], dict):
            # lat_map[escopo] = {"bilateral": X, "unilateral": Y}
            lats_permitidas = {lat for lat, qt in lat_map[escopo].items() if qt > 0}
            if e.unilateral not in lats_permitidas:
                continue
        if filtro_purpose == "composto" and not _eh_composto(e):
            continue
        if filtro_purpose == "isolado" and _eh_composto(e):
            continue
        cands.append(e)
    return cands


def _calcular_escassez(
    slot: _Slot,
    banco: list[Exercicio],
    cfg_treino: dict,
    nomes_bloqueados: set[str],
    familias_bloqueadas: set[str],
) -> int:
    """Número de candidatos viáveis (modo estrito) pra esse slot.

    Quanto menor, mais escasso, mais prioritário na ordenação. Slot com
    `requer_composto=True` filtra só compostos (mais restritivo).
    """
    filtro = "composto" if slot.requer_composto else None
    cands = _candidatos_estritos(
        banco, slot.nivel, slot.escopo_alocacao, cfg_treino,
        nomes_bloqueados, familias_bloqueadas, filtro_purpose=filtro,
    )
    return len(cands)


def _decompor_demanda_subregiao(
    subregiao: str,
    qtd: int,
    padroes_obrigatorios: Optional[list[str]] = None,
) -> list[tuple[str, str, int]]:
    """Decompõe demanda subregião em sub-demandas por padrão.

    Estratégia análoga à decomposição região: garante 1 de cada padrão da
    subregião + ciclar entre eles. Preserva paridade clínica que o cycling
    do `_selecionar_ciclando` legacy entregava (ex: costas(4) → 2 remadas +
    2 puxadas, em vez de 3:1 puxando pra proporção do banco).

    Subregiões com 1 padrão só (panturrilha, adutores no banco atual) viram
    qtd vagas do padrão único.

    `padroes_obrigatorios`: padrões da subregião que devem ter ≥ 1 vaga
    (suporte a travados — D3.1). Se houver mais obrigatórios que `qtd`,
    sorteia entre os obrigatórios.
    """
    padroes = list(SUBREGIAO_PARA_PADROES.get(subregiao, []))
    if not padroes or qtd <= 0:
        return []

    obrig = [p for p in (padroes_obrigatorios or []) if p in padroes]

    if qtd <= len(obrig):
        escolhidos = random.sample(obrig, qtd)
        return [("padrao", p, 1) for p in escolhidos]

    # 1 vaga pra cada obrigatório, depois 1 de cada padrão remanescente
    alocacao = {p: 1 for p in obrig}
    vagas_restantes = qtd - len(obrig)

    nao_obrig = [p for p in padroes if p not in alocacao]
    if vagas_restantes > 0 and nao_obrig:
        n_cobrir = min(vagas_restantes, len(nao_obrig))
        # Cobertura 1 de cada padrão restante (pra preservar paridade)
        nao_obrig_shuf = random.sample(nao_obrig, len(nao_obrig))
        for p in nao_obrig_shuf[:n_cobrir]:
            alocacao[p] = 1
        vagas_restantes -= n_cobrir

    # Ciclar todas as vagas extras entre todos os padrões da subregião
    if vagas_restantes > 0:
        pool_shuf = random.sample(padroes, len(padroes))
        for i in range(vagas_restantes):
            p = pool_shuf[i % len(pool_shuf)]
            alocacao[p] = alocacao.get(p, 0) + 1
    return [("padrao", p, qt) for p, qt in alocacao.items() if qt > 0]


def _decompor_demanda_regiao(
    regiao: str,
    qtd: int,
    subregioes_obrigatorias: Optional[list[str]] = None,
) -> list[tuple[str, str, int]]:
    """Aplica regra essencial/acessório (D2.1) pra demanda região.

    Retorna lista de sub-demandas `("subregiao", sub, qty)`. A ordem das
    sub-demandas e a distribuição em ciclo dependem de `random.*` — chamador
    deve setar seed se quiser determinismo.

    `subregioes_obrigatorias`: subregiões que devem ter ≥ 1 vaga (suporte a
    travados — D3.1). Pode forçar inclusão de subregião acessória que
    normalmente não competiria.
    """
    if regiao not in SUBREGIOES_POR_REGIAO:
        # Fallback: distribui uniformemente entre subregiões da região
        subs = REGIAO_PARA_SUBREGIOES.get(regiao, [])
        if not subs:
            return []
        return [("subregiao", sub, qtd // len(subs)) for sub in subs if qtd // len(subs) > 0]

    estrutura = SUBREGIOES_POR_REGIAO[regiao]
    essenciais = list(estrutura.get("essenciais", []))
    acessorias = list(estrutura.get("acessorias", []))
    todas_subs = essenciais + acessorias

    if qtd <= 0:
        return []

    obrig = [s for s in (subregioes_obrigatorias or []) if s in todas_subs]

    if qtd <= len(obrig):
        # Mais obrigatórias que vagas: sortear qtd entre obrigatórias
        escolhidos = random.sample(obrig, qtd)
        return [("subregiao", sub, 1) for sub in escolhidos]

    # 1 vaga pra cada obrigatória primeiro
    alocacao = {sub: 1 for sub in obrig}
    vagas_restantes = qtd - len(obrig)

    # Cobre essenciais não-cobertas (até esgotar vagas)
    essenciais_faltantes = [s for s in essenciais if s not in alocacao]
    for sub in essenciais_faltantes:
        if vagas_restantes <= 0:
            break
        alocacao[sub] = 1
        vagas_restantes -= 1

    if vagas_restantes <= 0:
        return [("subregiao", sub, qt) for sub, qt in alocacao.items() if qt > 0]

    # Pool de ciclo: essenciais sempre; acessórias só se qtd > 2 × num_essenciais
    # OU se há acessória obrigatória (já alocada acima — pool inclui acessórias).
    inclui_acessorias = (qtd > 2 * len(essenciais)) or any(s in acessorias for s in obrig)
    if inclui_acessorias and acessorias:
        pool_ciclo = essenciais + acessorias
    else:
        pool_ciclo = essenciais

    if vagas_restantes > 0 and pool_ciclo:
        pool_shuffled = random.sample(pool_ciclo, len(pool_ciclo))
        for i in range(vagas_restantes):
            sub = pool_shuffled[i % len(pool_shuffled)]
            alocacao[sub] = alocacao.get(sub, 0) + 1

    return [("subregiao", sub, qt) for sub, qt in alocacao.items() if qt > 0]


def _slot_compativel_com_travado(slot: _Slot, ex: Exercicio) -> bool:
    """Travado é compatível com slot se o padrão do travado pertence ao escopo do slot."""
    padroes_do_slot = set(_padroes_de_escopo(slot.nivel, slot.escopo_alocacao))
    return ex.padrao in padroes_do_slot


def pre_alocar_rotina(
    banco: list[Exercicio],
    configs: list[dict],
    relaxar_familia: bool = False,
) -> tuple[
    dict[int, dict[int, list[Exercicio]]],
    list[dict],
    dict[int, list[str]],
]:
    """Aloca exercícios entre os N treinos antes de qualquer um ser montado.

    Args:
        banco: banco completo de exercícios.
        configs: lista de cfg dict, idealmente já normalizadas via
                 _normalizar_config (configs sem `demandas` são normalizadas
                 internamente).
        relaxar_familia: aceito por simetria de assinatura, mas a Fase 0
                 sempre opera no modo estrito (D3.2). Relax é responsabilidade
                 da Fase 1 em gerar_sessao_por_demandas.

    Returns:
        (alocacao, avisos_rotina, relaxados_por_treino) onde:
          alocacao = {treino_idx: {d_idx: [Exercicio, ...]}}
          avisos_rotina = lista de avisos `incompleta` rotina-level (escopo="rotina")
          relaxados_por_treino = {treino_idx: [nome_ex, ...]} — exs alocados via
            relax de família entre treinos (segundo passe, só se relaxar_familia=True).

    Algoritmo:
      1. Normaliza configs (templates → demandas).
      2. Pra cada demanda região, decompõe em sub-demandas usando regra
         essencial/acessório (SUBREGIOES_POR_REGIAO). Subregião → padrão
         (cycling pra preservar paridade do _selecionar_ciclando legacy).
      3. Travados de cada treino consomem 1 vaga da primeira demanda compatível
         (decomposição é travado-aware via padroes_obrigatorios). Se nenhuma
         demanda bate, vira "extra" — alocado mas sem d_idx.
      4. Cada (sub-)demanda restante vira N slots granulares. Slots de
         demandas região marcam requer_composto=True até a quota composta
         (ceil(qtd × 0.6)) ser cumprida.
      5. Passe 1 (estrito): ordena slots por (escassez, peso_nivel,
         jitter_seeded); pega o primeiro; sorteia exercício do pool estrito.
         Slots sem candidato estrito viram pendentes pro passe 2.
      6. Passe 2 (relax — só se relaxar_familia=True): pra cada slot pendente,
         tenta de novo permitindo família repetida entre treinos (mas nome
         único globalmente). Sucessos vão pra relaxados_por_treino[t_idx].
      7. Slots ainda vazios após passe 2 → aviso `incompleta` rotina-level.
    """
    configs_norm = [_normalizar_config(c) for c in configs]

    alocacao: dict[int, dict[int, list[Exercicio]]] = {
        t_idx: {d_idx: [] for d_idx in range(len(cfg.get("demandas", []) or []))}
        for t_idx, cfg in enumerate(configs_norm)
    }
    nomes_globais: set[str] = set()
    familias_globais: set[str] = set()
    avisos_rotina: list[dict] = []
    relaxados_por_treino: dict[int, list[str]] = {}

    # ─── Etapa A: decompor demandas e construir slots ────────────────────
    # Estrutura intermediária: pra cada (t_idx, d_idx_original), guardamos:
    #   - demanda original (nivel, escopo, qtd)
    #   - sub-demandas (apenas pra região; pra subregião/padrão é a própria)
    #   - quota composta restante (apenas pra região)
    quota_composta: dict[tuple[int, int], int] = {}
    quota_total: dict[tuple[int, int], tuple[str, str, int]] = {}
    sub_demandas_por_origem: dict[tuple[int, int], list[tuple[str, str, int]]] = {}

    # Pré-mapeamento travados → primeira demanda compatível (D3.1).
    # Esse mapeamento informa a decomposição (subregioes_obrigatorias e
    # padroes_obrigatorios) pra garantir que cada travado tenha um slot
    # do padrão dele depois da decomposição.
    travados_por_demanda: dict[tuple[int, int], list[Exercicio]] = {}
    for t_idx, cfg in enumerate(configs_norm):
        travados = list(cfg.get("exercicios_travados") or [])
        for ex in travados:
            for d_idx, dem in enumerate(cfg.get("demandas") or []):
                if not (isinstance(dem, (list, tuple)) and len(dem) >= 3):
                    continue
                nv, esc, qt = dem[0], dem[1], int(dem[2])
                if qt <= 0:
                    continue
                if ex.padrao in set(_padroes_de_escopo(nv, esc)):
                    travados_por_demanda.setdefault((t_idx, d_idx), []).append(ex)
                    break

    for t_idx, cfg in enumerate(configs_norm):
        for d_idx, dem in enumerate(cfg.get("demandas") or []):
            if not (isinstance(dem, (list, tuple)) and len(dem) >= 3):
                continue
            nivel, escopo, qtd = dem[0], dem[1], int(dem[2])
            if qtd <= 0:
                continue
            quota_total[(t_idx, d_idx)] = (nivel, escopo, qtd)

            travados_d = travados_por_demanda.get((t_idx, d_idx), [])
            padroes_obrig = [ex.padrao for ex in travados_d]
            subs_obrig = list({
                PADRAO_PARA_SUBREGIAO[p] for p in padroes_obrig
                if p in PADRAO_PARA_SUBREGIAO
            })

            if nivel == "regiao":
                # Quota composta global por demanda (D2.2: 60% por demanda região)
                quota_composta[(t_idx, d_idx)] = math.ceil(qtd * PROPORCAO_COMPOSTOS)
                # Decomposição em 2 níveis: região → subregião → padrão, com
                # awareness de travados em ambos os níveis.
                sub_dems_subregiao = _decompor_demanda_regiao(
                    escopo, qtd, subregioes_obrigatorias=subs_obrig,
                )
                sub_dems_padrao: list[tuple[str, str, int]] = []
                for (_n, sub_esc, sub_qt) in sub_dems_subregiao:
                    pads_obrig_sub = [
                        p for p in padroes_obrig
                        if PADRAO_PARA_SUBREGIAO.get(p) == sub_esc
                    ]
                    sub_dems_padrao.extend(
                        _decompor_demanda_subregiao(
                            sub_esc, sub_qt, padroes_obrigatorios=pads_obrig_sub,
                        )
                    )
                sub_demandas_por_origem[(t_idx, d_idx)] = sub_dems_padrao
            elif nivel == "subregiao":
                sub_demandas_por_origem[(t_idx, d_idx)] = _decompor_demanda_subregiao(
                    escopo, qtd, padroes_obrigatorios=padroes_obrig,
                )
            else:
                sub_demandas_por_origem[(t_idx, d_idx)] = [(nivel, escopo, qtd)]

    # ─── Etapa B: processar travados (D3.1) ──────────────────────────────
    # Travado consome 1 vaga da primeira demanda compatível (mesmo padrão >
    # mesma subregião > mesma região), na ordem das demandas do treino.
    travados_por_treino: dict[int, list[Exercicio]] = {}
    for t_idx, cfg in enumerate(configs_norm):
        travados = list(cfg.get("exercicios_travados") or [])
        travados_por_treino[t_idx] = travados

        for ex in travados:
            # Tenta achar demanda compatível, em ordem; se houver sub-demandas
            # de uma região, escolhe a que cobre o padrão do travado.
            consumiu = False
            for d_idx in alocacao[t_idx].keys():
                sub_dems = sub_demandas_por_origem.get((t_idx, d_idx), [])
                # Se alguma sub-demanda dessa origem cobre o padrão do travado, consome
                for sub_idx, (sub_nivel, sub_escopo, sub_qtd) in enumerate(sub_dems):
                    padroes_cobertura = _padroes_de_escopo(sub_nivel, sub_escopo)
                    if ex.padrao in padroes_cobertura and sub_qtd > 0:
                        # Decrementa a sub-demanda
                        novos_sub = list(sub_dems)
                        novos_sub[sub_idx] = (sub_nivel, sub_escopo, sub_qtd - 1)
                        sub_demandas_por_origem[(t_idx, d_idx)] = novos_sub
                        # Adiciona à alocação
                        alocacao[t_idx][d_idx].append(ex)
                        nomes_globais.add(ex.nome)
                        familias_globais.add(ex.nome)
                        if ex.variacao_de:
                            familias_globais.add(ex.variacao_de)
                        # Se região, decrementa quota composta se travado é composto
                        if (t_idx, d_idx) in quota_composta and _eh_composto(ex):
                            quota_composta[(t_idx, d_idx)] = max(0, quota_composta[(t_idx, d_idx)] - 1)
                        consumiu = True
                        break
                if consumiu:
                    break

            if not consumiu:
                # Nenhuma demanda compatível: travado vira "extra" (sem d_idx)
                # Adicionamos sob a chave especial -1 pra propagar à Fase 1.
                alocacao[t_idx].setdefault(-1, []).append(ex)
                nomes_globais.add(ex.nome)
                familias_globais.add(ex.nome)
                if ex.variacao_de:
                    familias_globais.add(ex.variacao_de)

    # ─── Etapa C: construir lista de slots pendentes ─────────────────────
    slots_pendentes: list[_Slot] = []
    for (t_idx, d_idx), sub_dems in sub_demandas_por_origem.items():
        nivel_orig, escopo_orig, _ = quota_total[(t_idx, d_idx)]
        for (sub_nivel, sub_escopo, sub_qtd) in sub_dems:
            for _ in range(sub_qtd):
                slot = _Slot(
                    treino_idx=t_idx,
                    d_idx_original=d_idx,
                    nivel=sub_nivel,
                    escopo_alocacao=sub_escopo,
                    escopo_demanda_original=escopo_orig,
                    requer_composto=False,  # marcado em loop separado abaixo
                )
                slots_pendentes.append(slot)

    # Marca requer_composto pros primeiros N slots de cada demanda região
    # (N = quota composta restante após travados). Como a ordem dos slots
    # ainda não foi ordenada por escassez, o requer_composto vai pra TODOS
    # os slots da demanda; a flag é decrementada conforme compostos são
    # alocados. Slot só fica "obriga composto" enquanto há quota.
    # Implementação: a flag é dinâmica — recalculada antes de cada iteração.

    # ─── Etapa D: passe 1 (estrito) ──────────────────────────────────────
    slots_para_relax: list[_Slot] = []
    while slots_pendentes:
        # Atualizar requer_composto dinamicamente. Slot herda quota composta
        # da demanda região mãe (presente em quota_composta sse origem é região).
        for slot in slots_pendentes:
            slot.requer_composto = (
                (slot.treino_idx, slot.d_idx_original) in quota_composta
                and quota_composta[(slot.treino_idx, slot.d_idx_original)] > 0
            )

        # Calcular escassez de cada slot pendente
        def _escassez_slot(s: _Slot) -> int:
            cfg_t = configs_norm[s.treino_idx]
            return _calcular_escassez(s, banco, cfg_t, nomes_globais, familias_globais)

        # Ordenação: (escassez_estrita, peso_nivel, jitter_seeded)
        # jitter usa random.random() — seed do chamador é respeitada.
        slots_pendentes.sort(
            key=lambda s: (_escassez_slot(s), _peso_nivel(s.nivel), random.random())
        )

        slot = slots_pendentes.pop(0)
        cfg_t = configs_norm[slot.treino_idx]

        # Tentar alocar com filtro composto se requer_composto
        cands = _candidatos_estritos(
            banco, slot.nivel, slot.escopo_alocacao, cfg_t,
            nomes_globais, familias_globais,
            filtro_purpose="composto" if slot.requer_composto else None,
        )
        # Se requer_composto mas não há composto disponível, tenta sem filtro
        # (slot ainda conta na quota composta mas aceita isolado — quota fica
        # em deficit que será detectado em etapas futuras via âncoras).
        if slot.requer_composto and not cands:
            cands = _candidatos_estritos(
                banco, slot.nivel, slot.escopo_alocacao, cfg_t,
                nomes_globais, familias_globais,
                filtro_purpose=None,
            )

        if cands:
            escolhido = random.choice(cands)
            alocacao[slot.treino_idx][slot.d_idx_original].append(escolhido)
            nomes_globais.add(escolhido.nome)
            familias_globais.add(escolhido.nome)
            if escolhido.variacao_de:
                familias_globais.add(escolhido.variacao_de)
            # Decrementa quota composta se aplicável
            chave = (slot.treino_idx, slot.d_idx_original)
            if chave in quota_composta and _eh_composto(escolhido):
                quota_composta[chave] = max(0, quota_composta[chave] - 1)
        else:
            # Slot sem candidatos no estrito → vira candidato a relax
            slots_para_relax.append(slot)

    # ─── Etapa E: passe 2 (relax família entre treinos) ──────────────────
    # Só rodado se relaxar_familia=True. Permite candidato cuja família já
    # foi usada em outros treinos da mesma rotina (mas nome único global).
    if relaxar_familia and slots_para_relax:
        # Re-ordenar slots remanescentes por escassez (relaxada — só nomes bloqueiam)
        def _escassez_relax(s: _Slot) -> int:
            cfg_t = configs_norm[s.treino_idx]
            # No relax, familias_bloqueadas = vazio, mas nomes_globais ainda bloqueia.
            return _calcular_escassez(s, banco, cfg_t, nomes_globais, set())

        while slots_para_relax:
            slots_para_relax.sort(
                key=lambda s: (_escassez_relax(s), _peso_nivel(s.nivel), random.random())
            )
            slot = slots_para_relax.pop(0)
            cfg_t = configs_norm[slot.treino_idx]
            cands = _candidatos_estritos(
                banco, slot.nivel, slot.escopo_alocacao, cfg_t,
                nomes_globais, set(),  # família relaxada
                filtro_purpose=None,
            )
            if cands:
                escolhido = random.choice(cands)
                alocacao[slot.treino_idx][slot.d_idx_original].append(escolhido)
                nomes_globais.add(escolhido.nome)
                # Família AINDA é tracked pra slots subsequentes do mesmo passe relax
                familias_globais.add(escolhido.nome)
                if escolhido.variacao_de:
                    familias_globais.add(escolhido.variacao_de)
                relaxados_por_treino.setdefault(slot.treino_idx, []).append(escolhido.nome)
            else:
                # Mesmo no relax não há candidato → aviso rotina-level
                avisos_rotina.append({
                    "tipo": "incompleta",
                    "escopo": "rotina",
                    "treino_idx": slot.treino_idx,
                    "nivel": quota_total[(slot.treino_idx, slot.d_idx_original)][0],
                    "escopo_demanda": slot.escopo_demanda_original,
                    "nivel_alocacao": slot.nivel,
                    "escopo_alocacao": slot.escopo_alocacao,
                    "faltam": 1,
                })
    else:
        # relax desligado: slots_para_relax viram avisos diretamente
        for slot in slots_para_relax:
            avisos_rotina.append({
                "tipo": "incompleta",
                "escopo": "rotina",
                "treino_idx": slot.treino_idx,
                "nivel": quota_total[(slot.treino_idx, slot.d_idx_original)][0],
                "escopo_demanda": slot.escopo_demanda_original,
                "nivel_alocacao": slot.nivel,
                "escopo_alocacao": slot.escopo_alocacao,
                "faltam": 1,
            })

    return alocacao, avisos_rotina, relaxados_por_treino


def gerar_sessao_por_demandas(
    banco: list[Exercicio],
    demandas: list[tuple[str, str, int]],
    equipamentos_bloqueados: Optional[list[str]] = None,
    max_complexidade: int = 5,
    variacao_pais_usados: Optional[set] = None,
    exercicios_travados: Optional[list[Exercicio]] = None,
    tamanho_bloco: int = 2,
    evitar_agonistas: bool = False,
    lateralidade_por_padrao: Optional[dict] = None,
    relaxar_familia: bool = False,
    exercicios_pre_alocados: Optional[dict[int, list[Exercicio]]] = None,
) -> Sessao:
    """
    Gera uma sessão a partir de uma lista de DEMANDAS hierárquicas.

    demandas: lista de tuplas (nivel, escopo, quantidade), onde:
      - nivel  = "regiao" | "subregiao" | "padrao"
      - escopo = nome do nível (ex: "upper", "peito", "remadas")
      - quantidade = quantos exercícios pegar desse escopo

    Algoritmo (Opção C):
      Para cada demanda, lista todos os padrões pertencentes ao escopo,
      ordena (compostos primeiro), e cicla pegando 1 exercício de cada
      padrão até atingir a quantidade pedida. Se um padrão não tem mais
      candidatos disponíveis, pula para o próximo.

    Exemplo:
      demandas=[("regiao", "upper", 6)]
      → padrões de upper = [empurrar_compostos, remadas, puxadas (compostos),
                            empurrar_isolados, ombro_composto, ombro_isolado,
                            posterior_ombro, biceps, triceps]
      → reordenado: [empurrar_compostos, remadas, puxadas, ombro_composto,
                     empurrar_isolados, ombro_isolado, posterior_ombro,
                     biceps, triceps]
      → 6 exercícios = 1º de cada um dos 6 primeiros padrões disponíveis
    """
    eq_bloq  = equipamentos_bloqueados or []
    var_pais_inter = variacao_pais_usados or set()  # inter-treino, READ-ONLY
    var_pais_intra: set[str] = set()                # within-session, mutado durante seleção
    travados = exercicios_travados or []

    nomes_usados: set[str] = set()
    todos_selecionados: list[Exercicio] = []
    relaxados_local: list[str] = []  # nomes escolhidos via relax família

    # Modo pré-alocado (Fase 0 da Etapa 2 já fixou os exercícios concretos):
    # pula a seleção interna e usa os exercícios fornecidos. Travados já estão
    # contemplados na alocação (chave -1 pra travados sem demanda compatível).
    pre_alocados_modo = exercicios_pre_alocados is not None

    if not pre_alocados_modo:
        # Fluxo legado (gerar_sessao_por_demandas chamado standalone, ex: /regerar):
        # travados entram primeiro como extras.
        for e in travados:
            todos_selecionados.append(e)
            nomes_usados.add(e.nome)

    lat_map = lateralidade_por_padrao or {}

    # Helper interno para selecionar N exercícios ciclando pelos padrões
    def _selecionar_ciclando(
        padroes_ciclo: list[str], qtd: int,
        filtros_lateralidade: Optional[dict[str, str]] = None,
        filtro_purpose: Optional[str] = None,   # None | "composto" | "isolado"
        preferir_composto: bool = False,
    ) -> int:
        """Cicla pelos padrões pegando 1 por vez. Retorna quantos selecionou.

        Aplica os 2 níveis de relax CRUZANDO TODOS os padrões em cada nível,
        antes de descer pro próximo: estrito em todos → relax família entre
        treinos em todos. Isso evita que um padrão "esgotado" (sem candidatos
        estritos) seja preenchido via relax enquanto outro padrão do mesmo
        escopo ainda teria opção estrita disponível.

        filtro_purpose: se "composto" só aceita candidatos com _eh_composto=True;
        se "isolado" só aceita _eh_composto=False; se None aceita todos.
        preferir_composto: quando filtro_purpose=None, prefere candidatos
        compostos se houver no nível atual; senão usa qualquer.
        """
        # Pré-calcular candidatos por padrão
        candidatos_por_padrao: dict[str, list[Exercicio]] = {}
        for p in padroes_ciclo:
            cands = filtrar_por_padrao(banco, p)
            cands = filtrar_por_equipamentos(cands, eq_bloq)
            cands = filtrar_por_complexidade(cands, max_complexidade)
            cands = [e for e in cands if e.nome not in nomes_usados]
            if filtros_lateralidade and p in filtros_lateralidade:
                lat = filtros_lateralidade[p]
                cands = [e for e in cands if e.unilateral == lat]
            if filtro_purpose == "composto":
                cands = [e for e in cands if _eh_composto(e)]
            elif filtro_purpose == "isolado":
                cands = [e for e in cands if not _eh_composto(e)]
            candidatos_por_padrao[p] = cands

        def _bloqueado_familia(e, sets):
            """e está bloqueado por família se nome ou variacao_de aparecem em algum dos sets."""
            for s in sets:
                if e.nome in s:
                    return True
                if e.variacao_de and e.variacao_de in s:
                    return True
            return False

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
            # Preferência por composto dentro do nível: se houver, sorteia só dele;
            # caso contrário cai no pool inteiro.
            if preferir_composto and filtro_purpose is None:
                comp = [e for e in base if _eh_composto(e)]
                if comp:
                    return comp
            return base

        selecionados = 0

        # Niveis de relax a tentar, em ordem. Relax 1 só se relaxar_familia=True.
        niveis = [0] + ([1] if relaxar_familia else [])

        for nivel_relax in niveis:
            if selecionados >= qtd:
                break
            # Cicla pelos padrões neste nível até esgotar progresso
            while selecionados < qtd:
                progresso = False
                for p in padroes_ciclo:
                    if selecionados >= qtd:
                        break
                    disponiveis = _filtrar(candidatos_por_padrao[p], nivel_relax)
                    if not disponiveis:
                        continue
                    escolhido = random.choice(disponiveis)
                    todos_selecionados.append(escolhido)
                    nomes_usados.add(escolhido.nome)
                    if escolhido.variacao_de:
                        var_pais_intra.add(escolhido.variacao_de)
                    var_pais_intra.add(escolhido.nome)
                    if nivel_relax == 1:
                        relaxados_local.append(escolhido.nome)
                    selecionados += 1
                    progresso = True
                if not progresso:
                    break  # esgotou este nível, desce pro próximo

        return selecionados

    # Resolver cada demanda
    rotulos_demandas: list[str] = []
    avisos_da_sessao: list[dict] = []

    if pre_alocados_modo:
        # ── Modo pré-alocado: usa os exercícios fixados pela Fase 0 ─────
        # Travados sem demanda compatível ficam na chave especial -1.
        for ex in (exercicios_pre_alocados.get(-1, []) or []):
            if ex.nome not in nomes_usados:
                todos_selecionados.append(ex)
                nomes_usados.add(ex.nome)

        for d_idx, demanda in enumerate(demandas):
            if not (isinstance(demanda, (list, tuple)) and len(demanda) >= 3):
                continue
            nivel, escopo, qtd = demanda[0], demanda[1], int(demanda[2])
            if qtd <= 0:
                continue
            rotulos_demandas.append(f"{escopo}({qtd})")
            exs_pre = exercicios_pre_alocados.get(d_idx, []) or []
            for ex in exs_pre:
                if ex.nome not in nomes_usados:
                    todos_selecionados.append(ex)
                    nomes_usados.add(ex.nome)
            # Aviso `incompleta` treino-level só quando a Fase 0 não preencheu
            # tudo desta demanda (D3.2): Fase 1 não relaxa, mas a contagem do
            # pré-alocado pode ter ficado abaixo do pedido (e a Fase 0 já
            # gerou o aviso rotina-level correspondente).
            n_obtido = len(exs_pre)
            if n_obtido < qtd:
                padroes = _padroes_de_escopo(nivel, escopo)
                nomes_em_escopo: set[str] = set()
                for e in banco:
                    if e.padrao in padroes:
                        nomes_em_escopo.add(e.nome)
                        if e.variacao_de:
                            nomes_em_escopo.add(e.variacao_de)
                familias_usadas = sorted(n for n in var_pais_inter if n in nomes_em_escopo)
                avisos_da_sessao.append({
                    "tipo": "incompleta",
                    "escopo_aviso": "treino",  # D3.2
                    "nivel": nivel,
                    "escopo": escopo,
                    "qtd_pedida": qtd,
                    "qtd_obtida": n_obtido,
                    "faltam": qtd - n_obtido,
                    "familias_usadas": familias_usadas,
                })
    else:
        # ── Modo standalone: comportamento atual (chamada via /regerar) ──
        for nivel, escopo, qtd in demandas:
            if qtd <= 0:
                continue
            rotulos_demandas.append(f"{escopo}({qtd})")

            n_antes = len(todos_selecionados)
            n_antes_relax = len(relaxados_local)
            padroes = _padroes_de_escopo(nivel, escopo)

            # Lateralidade: quando o escopo tem refinamento bilateral/unilateral explícito
            if escopo in lat_map:
                padroes_esc = padroes
                for lat, qt in lat_map[escopo].items():
                    if qt > 0:
                        filtros = {p: lat for p in padroes_esc}
                        _selecionar_ciclando(padroes_esc, qt, filtros_lateralidade=filtros)
            elif not padroes:
                pass
            elif nivel == "regiao":
                # ── Regra de proporção: ao menos 60% compostos ────────────────
                # Classificação por exercício (purpose), não por padrão.
                # Cada padrão pode contribuir nas duas fases (ex: hinge tem 12
                # compostos e 8 isolados no banco — entra em ambas).
                cands_no_escopo = [e for e in banco if e.padrao in padroes]
                tem_compostos = any(_eh_composto(e) for e in cands_no_escopo)
                tem_isolados  = any(not _eh_composto(e) for e in cands_no_escopo)

                padroes_shuf = list(padroes)
                random.shuffle(padroes_shuf)

                if tem_compostos and tem_isolados:
                    min_compostos = math.ceil(qtd * PROPORCAO_COMPOSTOS)
                    # Não pedir mais compostos do que o total
                    min_compostos = min(min_compostos, qtd)
                    max_isolados  = qtd - min_compostos

                    # Fase 1: preencher compostos ciclando os padrões
                    n_comp = _selecionar_ciclando(padroes_shuf, min_compostos, filtro_purpose="composto")
                    # Fase 2: preencher isolados ciclando os padrões
                    n_iso = _selecionar_ciclando(padroes_shuf, max_isolados, filtro_purpose="isolado")
                    # Fase 3: se sobrou espaço, tenta mais compostos; depois isolados
                    faltam = qtd - n_comp - n_iso
                    if faltam > 0:
                        n_extra_c = _selecionar_ciclando(padroes_shuf, faltam, filtro_purpose="composto")
                        faltam -= n_extra_c
                    if faltam > 0:
                        _selecionar_ciclando(padroes_shuf, faltam, filtro_purpose="isolado")
                else:
                    # Só um tipo disponível — cicla com preferência por composto
                    _selecionar_ciclando(padroes_shuf, qtd, preferir_composto=True)
            else:
                # ── Subregião / Padrão: cicla padrões com prioridade dinâmica ──
                # Padrões que TÊM candidato composto no banco vêm primeiro;
                # dentro de cada padrão, candidatos compostos são preferidos.
                padroes_ord = _ordenar_padroes_por_prioridade(padroes, banco=banco)
                _selecionar_ciclando(padroes_ord, qtd, preferir_composto=True)

            n_obtido = len(todos_selecionados) - n_antes

            # Avisos do tipo "familia_repetida" (1 por exercício relaxado nesta demanda)
            novos_relax = relaxados_local[n_antes_relax:]
            for nome_rel in novos_relax:
                ex_rel = next((e for e in todos_selecionados if e.nome == nome_rel), None)
                avisos_da_sessao.append({
                    "tipo": "familia_repetida",
                    "nivel": nivel,
                    "escopo": escopo,
                    "exercicio": nome_rel,
                    "familia": (ex_rel.variacao_de if ex_rel and ex_rel.variacao_de else nome_rel),
                })

            if n_obtido < qtd:
                nomes_em_escopo: set[str] = set()
                for e in banco:
                    if e.padrao in padroes:
                        nomes_em_escopo.add(e.nome)
                        if e.variacao_de:
                            nomes_em_escopo.add(e.variacao_de)
                familias_usadas = sorted(n for n in var_pais_inter if n in nomes_em_escopo)
                avisos_da_sessao.append({
                    "tipo": "incompleta",
                    "nivel": nivel,
                    "escopo": escopo,
                    "qtd_pedida": qtd,
                    "qtd_obtida": n_obtido,
                    "faltam": qtd - n_obtido,
                    "familias_usadas": familias_usadas,
                })

    # Ordenar: compostos primeiro (dentro do conjunto final)
    todos_selecionados = ordenar_compostos_primeiro(todos_selecionados)

    # Montar e ordenar blocos
    grupos = ordenar_blocos(montar_blocos(todos_selecionados, tamanho=tamanho_bloco, evitar_agonistas=evitar_agonistas))

    labels = "ABCDEFGHIJKLMNOP"
    blocos = []
    for i, grupo in enumerate(grupos):
        label = labels[i] if i < len(labels) else str(i + 1)
        ex1 = grupo[0]
        ex2 = grupo[1] if len(grupo) > 1 else None
        ex3 = grupo[2] if len(grupo) > 2 else None
        blocos.append(SuperSerie(label=label, ex1=ex1, ex2=ex2, ex3=ex3))

    tipo = " + ".join(rotulos_demandas) if rotulos_demandas else "Sessão"
    sessao = Sessao(tipo=tipo, blocos=blocos)
    sessao.avisos = avisos_da_sessao
    sessao.relaxados = list(relaxados_local)
    return sessao


# ---------------------------------------------------------------------------
# Geração de múltiplos treinos com compartilhamento de estado entre sessões
# ---------------------------------------------------------------------------

def gerar_multiplos_treinos(
    banco: list[Exercicio],
    configs: list[dict],
    relaxar_familia: bool = False,
) -> list[Sessao]:
    """
    Gera N sessões de treino com pré-alocação global (Etapa 2 da refatoração v4).

    Pipeline em 3 fases:
      Fase 0 — pre_alocar_rotina aloca exercícios entre os N treinos antes de
        qualquer um ser montado, ordenando vagas por escassez. Travados
        consomem vaga (D3.1). Avisos `incompleta` rotina-level são gerados
        aqui (D3.2).
      Fase 1 — gerar_sessao_por_demandas recebe `exercicios_pre_alocados` e
        usa direto, sem refazer seleção. Avisos `familia_repetida` da Fase 1
        existem só pra fluxo standalone (quando chamada via /regerar).
      Fase 2 — montar_blocos (intocada).

    Templates legacy (cfg sem `demandas`) são convertidos via
    `_normalizar_config` na borda externa (D4 opção C). `gerar_sessao` legado
    permanece intocado e continua chamável standalone (ex: `/regerar` no
    app_flask), mas não é chamado a partir daqui.

    Args:
        banco: banco completo de exercícios.
        configs: lista de dicts, um por treino. Aceita formato de demandas
            (`{"demandas": [...]}`) OU formato template legado
            (`{"padroes": [...], "exercicios_por_padrao": {...}}`). Ambos
            convertidos internamente em demandas.
        relaxar_familia: se True, permite Fase 1 relaxar família entre treinos.
            Fase 0 (pré-alocação) sempre opera no modo estrito, independente
            desta flag (D3.2).

    Returns:
        Lista de Sessao na mesma ordem de configs. Avisos `incompleta`
        rotina-level são anexados em sessoes[0].avisos com escopo="rotina".
    """
    # Normaliza configs (templates → demandas, D4 opção C)
    configs_norm = [_normalizar_config(c) for c in configs]

    # Fase 0: pré-alocação global (com 2º passe de relax se relaxar_familia)
    alocacao, avisos_rotina, relaxados_por_treino = pre_alocar_rotina(
        banco, configs_norm, relaxar_familia=relaxar_familia,
    )

    # Reconstrói variacao_pais_globais a partir da alocação (R5).
    # Esse set é repassado pra Fase 1 só pra preencher `familias_usadas` em
    # avisos `incompleta` treino-level (rastreabilidade de quais famílias
    # bloquearam a alocação).
    variacao_pais_globais: set[str] = set()
    for _t_idx, by_demanda in alocacao.items():
        for _d_idx, exs in by_demanda.items():
            for ex in exs:
                variacao_pais_globais.add(ex.nome)
                if ex.variacao_de:
                    variacao_pais_globais.add(ex.variacao_de)

    # Fase 1: gera sessão por treino usando os exercícios pré-alocados
    sessoes: list[Sessao] = []
    for treino_idx, cfg in enumerate(configs_norm):
        demandas      = cfg.get("demandas") or []
        max_cx        = cfg.get("max_complexidade", 5)
        tam_bloco     = cfg.get("tamanho_bloco", 2)
        travados      = cfg.get("exercicios_travados", [])
        eq_bloq       = cfg.get("equipamentos_bloqueados", [])
        evit_agon     = cfg.get("evitar_agonistas", False)
        lat_padrao    = cfg.get("lateralidade_por_padrao")

        exs_pre = alocacao.get(treino_idx, {})

        sessao = gerar_sessao_por_demandas(
            banco,
            demandas=demandas,
            equipamentos_bloqueados=eq_bloq,
            max_complexidade=max_cx,
            exercicios_travados=travados,
            tamanho_bloco=tam_bloco,
            variacao_pais_usados=variacao_pais_globais,
            evitar_agonistas=evit_agon,
            lateralidade_por_padrao=lat_padrao,
            relaxar_familia=relaxar_familia,
            exercicios_pre_alocados=exs_pre,
        )

        # Propaga relaxados da Fase 0 pra Sessao.relaxados (badge ↻ na UI)
        # e gera aviso `familia_repetida` por exercício relaxado.
        relaxados_t = relaxados_por_treino.get(treino_idx, [])
        if relaxados_t:
            sessao.relaxados = list(relaxados_t)
            for nome_rel in relaxados_t:
                # Localiza o exercício pra resgatar variacao_de
                ex_rel = next(
                    (ex for bloco in sessao.blocos
                     for ex in (bloco.ex1, bloco.ex2, bloco.ex3)
                     if ex and ex.nome == nome_rel),
                    None,
                )
                sessao.avisos.append({
                    "tipo": "familia_repetida",
                    "exercicio": nome_rel,
                    "familia": (
                        ex_rel.variacao_de if ex_rel and ex_rel.variacao_de
                        else nome_rel
                    ),
                })

        # Recompõe familias_usadas em avisos de incompleta treino-level
        # (mantém compat com UI legada que olha esse campo).
        for av in sessao.avisos:
            if av.get("tipo") != "incompleta":
                continue
            nivel_av = av.get("nivel")
            escopo_av = av.get("escopo")
            if nivel_av == "padrao":
                escopo_padroes = [escopo_av]
            elif nivel_av == "subregiao":
                escopo_padroes = list(SUBREGIAO_PARA_PADROES.get(escopo_av, []))
            elif nivel_av == "regiao":
                escopo_padroes = []
                for sub in REGIAO_PARA_SUBREGIOES.get(escopo_av, []):
                    escopo_padroes.extend(SUBREGIAO_PARA_PADROES.get(sub, []))
            else:
                escopo_padroes = []
            nomes_em_escopo: set[str] = set()
            for e in banco:
                if e.padrao in escopo_padroes:
                    nomes_em_escopo.add(e.nome)
                    if e.variacao_de:
                        nomes_em_escopo.add(e.variacao_de)
            av["familias_usadas"] = sorted(
                n for n in variacao_pais_globais if n in nomes_em_escopo
            )

        sessoes.append(sessao)

    # Anexa avisos rotina-level no primeiro treino (R3 — sem mexer na UI).
    # Cada aviso já carrega `escopo: "rotina"`. UI mistura visualmente; ajuste
    # de UX vira ponto aberto.
    if avisos_rotina and sessoes:
        sessoes[0].avisos.extend(avisos_rotina)

    return sessoes

def imprimir_sessao(sessao: Sessao):
    print("=" * 60)
    print(f"  SESSÃO: {sessao.tipo}")
    print("=" * 60)
    for bloco in sessao.blocos:
        print(f"\n  Bloco {bloco.label}")
        exercicios = [e for e in [bloco.ex1, bloco.ex2, bloco.ex3] if e]
        for i, ex in enumerate(exercicios, 1):
            eq = ex.eq_primario + (f" + {ex.eq_secundario}" if ex.eq_secundario else "")
            print(f"  {bloco.label}{i} — {ex.nome}  [{ex.purpose} | fd:{ex.fadiga} | cx:{ex.complexidade}]")
            print(f"       Equip: {eq}" + (f"  |  {ex.obs}" if ex.obs else ""))
    print()


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Busca filtrada de substitutos (escolha manual)
# ---------------------------------------------------------------------------

def buscar_substitutos(
    sessao: Sessao,
    nome_atual: str,
    banco: list[Exercicio],
    padrao: Optional[str] = None,
    regiao: Optional[str] = None,
    purpose: Optional[str] = None,
    unilateral: Optional[str] = None,
    max_complexidade: int = 5,
    max_fadiga: int = 5,
    equipamentos_bloqueados: Optional[list[str]] = None,
) -> list[Exercicio]:
    """
    Retorna lista de candidatos filtrados para substituir um exercício na sessão.
    Use após buscar_substitutos() e passe a escolha para substituir_exercicio_por().
    """
    eq_bloq = equipamentos_bloqueados or []

    nomes_em_uso = set()
    for bloco in sessao.blocos:
        for ex in [bloco.ex1, bloco.ex2, bloco.ex3]:
            if ex and ex.nome != nome_atual:
                nomes_em_uso.add(ex.nome)

    candidatos = list(banco)
    if padrao:
        candidatos = [e for e in candidatos if e.padrao == padrao]
    if regiao:
        candidatos = [e for e in candidatos if e.regiao == regiao]
    if purpose:
        candidatos = [e for e in candidatos if e.purpose == purpose]
    if unilateral:
        candidatos = [e for e in candidatos if e.unilateral == unilateral]
    if eq_bloq:
        candidatos = [e for e in candidatos if e.eq_primario not in eq_bloq]

    candidatos = [e for e in candidatos if e.complexidade <= max_complexidade]
    candidatos = [e for e in candidatos if e.fadiga <= max_fadiga]
    candidatos = [e for e in candidatos if e.nome not in nomes_em_uso]

    candidatos.sort(key=lambda e: (e.purpose != "compound", e.fadiga * -1, e.nome))
    return candidatos


def substituir_exercicio_por(
    sessao: Sessao,
    nome_atual: str,
    nome_substituto: str,
    banco: list[Exercicio],
) -> Sessao:
    """Substitui nome_atual por nome_substituto na sessão."""
    import copy
    substituto = next((e for e in banco if e.nome == nome_substituto), None)
    if substituto is None:
        return sessao

    nova_sessao = copy.deepcopy(sessao)
    for bloco in nova_sessao.blocos:
        if bloco.ex1 and bloco.ex1.nome == nome_atual:
            bloco.ex1 = substituto
            return nova_sessao
        if bloco.ex2 and bloco.ex2.nome == nome_atual:
            bloco.ex2 = substituto
            return nova_sessao
        if bloco.ex3 and bloco.ex3.nome == nome_atual:
            bloco.ex3 = substituto
            return nova_sessao
    return sessao


def listar_candidatos(candidatos: list[Exercicio]):
    """Imprime a lista de candidatos para debug no terminal."""
    if not candidatos:
        print("  Nenhum candidato encontrado com esses filtros.")
        return
    print(f"  {len(candidatos)} candidato(s) encontrado(s):\n")
    for i, e in enumerate(candidatos, 1):
        eq = e.eq_primario + (f" + {e.eq_secundario}" if e.eq_secundario else "")
        print(f"  {i:2}. {e.nome}")
        print(f"       [{e.purpose} | {e.padrao} | {e.unilateral} | fd:{e.fadiga} | cx:{e.complexidade}]")
        print(f"       Equip: {eq}" + (f"  |  {e.obs}" if e.obs else ""))


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    random.seed()
    banco = carregar_banco(XLSX_PATH)
    print(f"Banco carregado: {len(banco)} exercícios\n")

    print(">>> Full Body")
    sessao = gerar_sessao(banco, TEMPLATES["Full Body"])
    imprimir_sessao(sessao)

    print(">>> Empurrar + Posterior, iniciante (cx ≤ 3)")
    sessao = gerar_sessao(banco, TEMPLATES["Empurrar + Posterior"], max_complexidade=3)
    imprimir_sessao(sessao)

    print(">>> Expansão hierárquica: Membros superiores + só hinge nas pernas")
    padroes = expandir_para_padroes(regioes=["upper"], padroes=["hinge"])
    print(f"  Padrões expandidos: {padroes}")
    sessao = gerar_sessao(banco, padroes)
    imprimir_sessao(sessao)
