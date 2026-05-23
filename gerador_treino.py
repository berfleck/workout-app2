"""
Gerador de Treinos — lógica central
Lê o banco de exercícios (.xlsx) e gera sessões respeitando as regras definidas.

Uso:
    python gerador_treino.py
"""

import math
import pandas as pd
import random
from dataclasses import dataclass, field, replace
from typing import Optional

from pesos_proximidade import (
    PESOS_DEFAULT,
    SUBREGIOES_LATERALIDADE_HARD,
    ConfigPesosProximidade,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

XLSX_PATH = "banco_exercicios.xlsx"

# ---------------------------------------------------------------------------
# Hierarquia: Região → Subregião → Padrão
# ---------------------------------------------------------------------------

# Mapeamento PADRÃO → SUBREGIÕES. Valor é set[str] desde Etapa 8 (refator
# CORE) — padrões refinados de core atravessam as 2 subregiões (ex:
# `flexao_tronco` aparece em Prancha iso E Crunch dyn). Padrões não-core
# continuam 1:1 (set de 1 elemento) por consistência. Padrões `core_isometrico`
# e `core_dinamico` legados saíram do mapa em Fase 8.2 — XLSX migrou pros
# 4 refinados; demandas legadas que ainda peçam o nome antigo passam por
# `_PADROES_LEGADOS` aliasing.
PADRAO_PARA_SUBREGIAO: dict[str, set[str]] = {
    # Membros inferiores
    "squat_bilateral":  {"perna_anterior"},
    "squat_unilateral": {"perna_anterior"},
    "hinge":          {"perna_posterior"},
    "knee_flexion":   {"perna_posterior"},
    # knee_extension → perna_anterior (extensão isolada de joelho, quad).
    # Distinto de knee_flexion (perna_posterior, hamstring). Pool de 1
    # (Cadeira Extensora) é por design — ver docs/refatoracao/notas_cadastro.md.
    "knee_extension": {"perna_anterior"},
    "abduction":      {"perna_posterior"},
    "adduction":      {"adutores"},
    "flexao_plantar": {"panturrilha"},
    # Membros superiores
    "empurrar_compostos": {"peito"},
    "empurrar_isolados":  {"peito"},
    "remadas":            {"costas"},
    "puxadas":            {"costas"},
    "ombro_composto":     {"ombro"},
    "ombro_isolado":      {"ombro"},
    "posterior_ombro":    {"ombro"},
    "biceps":             {"bracos"},
    "triceps":            {"bracos"},
    # Core refinados (Etapa 8 / Anexo 15-quater) — 1:N atravessando iso/dyn
    # quando o banco real tem exercícios na variante. Padrões refinados sem
    # variante cadastrada no XLSX ficam restritos à subregião com exercícios
    # — evita cycling pegar padrão vazio (= aviso "incompleta" espúrio):
    # - flexao_lateral: só iso (Prancha Lateral). Sem variante dyn prevista.
    # - rotacao_tronco: iso (Pallof Press) + dyn (Russian Twist — Fase 4)
    "flexao_tronco":   {"core_isometrico", "core_dinamico"},
    "flexao_lateral":  {"core_isometrico"},
    "rotacao_tronco":  {"core_isometrico", "core_dinamico"},
    "flexao_quadril":  {"core_isometrico", "core_dinamico"},
    # Cardio
    "cardio":          {"cardio"},
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
for pad, subs in PADRAO_PARA_SUBREGIAO.items():
    for sub in subs:
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
#   - core_dinamico/core_isometrico (subregiões) e seus 4 padrões refinados
#     da Etapa 8 (flexao_tronco/lateral/rotacao_tronco/flexao_quadril):
#     cycling natural pelos padrões da subregião

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
    "bracos": [
        {"padrao": "biceps",  "peso": 1, "obrigatoria": True},
        {"padrao": "triceps", "peso": 1, "obrigatoria": True},
    ],
    # core_dinamico, core_isometrico, adutores: sem âncoras
    # (fallback pra cycling uniforme da Etapa 2). core_din/core_iso têm
    # decisão clínica forte só no nível região (declarada em
    # ANCORAS_POR_REGIAO['core']); padrões internos são variações sem
    # obrigatoriedade entre si. Adutores tem só 1 padrão (adduction).
}


# Carve-out de quotas por subregião: distribuições explícitas que substituem
# o Hamilton normal em (subregião, vagas) específicos.
#
# Motivação clínica (2026-05-18): Hamilton determinístico cria 0% para
# acessórias em vários cenários por causa do tie-break "obrigatória vence
# empate de resto". Esta estrutura permite, por subregião e por número de
# vagas, declarar a distribuição clínica desejada explicitamente.
#
# Formato: SUBREGIOES_CARVE_OUT_QUOTAS[subregiao][vagas] é uma lista de
# tuplas (quotas_dict, peso_prob). Sorteia-se UM quota_dict da lista
# proporcional aos pesos. Soma das quotas em cada dict deve bater com
# vagas. Use peso 100 quando quiser distribuição fixa (1 entrada só).
#
# Quando NÃO há entrada pra (subregião, vagas), Hamilton normal opera.
SUBREGIOES_CARVE_OUT_QUOTAS: dict[str, dict[int, list[tuple[dict[str, int], int]]]] = {
    "ombro": {
        # Vaga única: 70/30 composto/isolado. posterior_ombro fora —
        # específico demais pra uma rotina single-slot de ombro.
        1: [
            ({"ombro_composto": 1}, 70),
            ({"ombro_isolado":  1}, 30),
        ],
        # vagas ≥ 2: Hamilton normal (composto:1 + isolado:1 em 2 vagas,
        # composto:2 + isolado:1 em 3 vagas; posterior só entra em 4+).
    },
    "perna_posterior": {
        # Vaga única: variedade ampla (hinge dominante mas kn/ab têm vez).
        1: [
            ({"hinge":        1}, 60),
            ({"knee_flexion": 1}, 20),
            ({"abduction":    1}, 20),
        ],
        # Vaga dupla: hinge sempre presente; 2º slot 50/50 kn vs ab.
        2: [
            ({"hinge": 1, "knee_flexion": 1}, 50),
            ({"hinge": 1, "abduction":    1}, 50),
        ],
        # 3 vagas: cobertura completa preferida; 40% das rotinas dobra
        # hinge (priorização leve do composto) sacrificando 1 das
        # acessórias. kn e ab permanecem simétricas entre si.
        # Slot-level esperado: hinge ~47%, kn ~27%, ab ~27%.
        3: [
            ({"hinge": 1, "knee_flexion": 1, "abduction": 1}, 60),
            ({"hinge": 2, "knee_flexion": 1},                 20),
            ({"hinge": 2, "abduction":    1},                 20),
        ],
        # vagas ≥ 4: Hamilton normal (já distribui os 3 padrões
        # naturalmente — hinge:2 kn:1 ab:1 em 4; hinge:3 kn:2 ab:1 em 6).
    },
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
            assert sub in PADRAO_PARA_SUBREGIAO[pad], (
                f"ANCORAS_POR_SUBREGIAO[{sub!r}]: '{pad}' não pertence a "
                f"esta subregião — PADRAO_PARA_SUBREGIAO[{pad!r}]="
                f"{sorted(PADRAO_PARA_SUBREGIAO[pad])}"
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
    # obrigatória > peso maior > sorteio aleatório (evita viés da ordem)
    if restantes > 0:
        def tiebreak_key(p):
            idx, a, ideal, floor = p
            resto = ideal - floor
            return (
                -resto,                          # maior resto primeiro
                0 if a.get("obrigatoria") else 1,  # obrig primeiro
                -a["peso"],                      # peso maior primeiro
                random.random(),                 # sorteio (evita viés da ordem de definição)
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
    # Carve-out: subregião com distribuição explícita pra esse nº de vagas.
    # Sorteia 1 entrada da lista (peso = probabilidade); copia o dict
    # resultante pra não mutar o estado da constante.
    distribs = SUBREGIOES_CARVE_OUT_QUOTAS.get(subregiao, {}).get(vagas)
    if distribs:
        dicts = [d for d, _ in distribs]
        pesos = [p for _, p in distribs]
        escolhido = random.choices(dicts, weights=pesos, k=1)[0]
        return dict(escolhido), []

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


def _quotas_por_pool(
    chaves: list[str],
    qtd: int,
    pool_por_chave: dict[str, int],
    obrigatorias: Optional[list[str]] = None,
) -> dict[str, int]:
    """Distribui `qtd` vagas entre `chaves` sorteando vaga-a-vaga com peso
    proporcional ao tamanho do pool, SEM reposição (pool decrementa a cada
    escolha).

    Resolve viés mono-ex documentado na Seção 8.15.12 (6º NO-OP pós-CORE):
    fallback antigo do `_decompor_demanda_*` atribuía 1 vaga por chave em
    ordem random, ignorando tamanho do pool — padrão com 1 candidato
    (Pallof Press, Prancha Lateral) ganhava o mesmo peso de padrão com 8
    candidatos (flexao_tronco). Resultado: P(Pallof em core_iso(1)) = 25%
    via cycling vs 7.7% se fosse uniforme por exercício. Esta função
    pondera por pool — Pallof recebe peso 1, flexao_tronco recebe peso 8.

    Args:
        chaves: nomes (padrão ou subregião) a distribuir vagas.
        qtd: total de vagas.
        pool_por_chave: tamanho do pool de exercícios de cada chave.
            Chaves com pool=0 são ignoradas no sorteio.
        obrigatorias: chaves que devem ter ≥ 1 vaga (travados — D3.1).
            Consome 1 vaga inicial pra cada obrigatória antes de sortear o
            resto. Se pool=0 do obrigatório, vira no-op.

    Returns:
        dict {chave: qtd} (só chaves com qtd > 0).
    """
    if qtd <= 0 or not chaves:
        return {}

    obrig = [c for c in (obrigatorias or []) if c in chaves]
    pool = {c: int(pool_por_chave.get(c, 0)) for c in chaves}
    quotas: dict[str, int] = {c: 0 for c in chaves}
    qtd_rest = qtd

    # Garantir 1 vaga pra cada obrigatória (consome 1 do pool dela)
    for c in obrig:
        if pool[c] > 0 and qtd_rest > 0:
            quotas[c] += 1
            pool[c] -= 1
            qtd_rest -= 1

    # Sortear vagas restantes ponderado por pool, sem reposição
    while qtd_rest > 0:
        total = sum(pool.values())
        if total == 0:
            break  # pool global esgotado — vagas restantes ficam sem alocação
        r = random.random() * total
        cum = 0
        escolhida = None
        for c in chaves:
            cum += pool[c]
            if r < cum:
                escolhida = c
                break
        if escolhida is None:
            # Fallback numérico (r == total por erro de float): pega a última
            # chave com pool > 0
            for c in reversed(chaves):
                if pool[c] > 0:
                    escolhida = c
                    break
            if escolhida is None:
                break
        quotas[escolhida] += 1
        pool[escolhida] -= 1
        qtd_rest -= 1

    return {c: q for c, q in quotas.items() if q > 0}


def _distribuir_quotas_entre_treinos(
    quotas_global: dict[str, int],
    n_treinos: int,
    vagas_por_treino: list[int],
    pesos: dict[str, int],
) -> list[dict[str, int]]:
    """Distribui quotas globais entre N treinos via Bresenham por chave.

    Cada chave entra com offset = acumulador mod n_treinos e distribui
    suas vagas em round-robin a partir desse offset, pulando treinos com
    capacidade esgotada. O acumulador soma a quota ao final de cada chave,
    o que evita o phase lock do algoritmo antigo (`A,B,A,B` na mesma ordem
    em todos os treinos) — chaves diferentes começam em treinos diferentes.

    Resolve diagnóstico de 2026-05-17 (notas_distribuicao.md, Solução 1):
    `peito` sempre em T2, `perna_anterior` sempre em T1, etc. quando havia
    > 1 chave com quotas iguais.

    Args:
        quotas_global: {chave: qtd_total_na_rotina}.
        n_treinos: número de treinos.
        vagas_por_treino: vagas alocadas pra esta demanda em cada treino.
        pesos: {chave: peso} — mantido na assinatura por compat de API,
            **não usado**. Ordenação agora é por quota desc + alfabético.

    Returns:
        Lista de N dicts {chave: qtd_no_treino}, soma == quotas_global.
    """
    if n_treinos <= 0:
        return []
    if sum(quotas_global.values()) == 0:
        return [{} for _ in range(n_treinos)]

    # Ordenar chaves por quota desc (tie-break sorteado — evita que chaves
    # com quotas iguais caiam sempre nos mesmos treinos. Ver auditoria
    # 2026-05-18: empate alfabético criava viés posicional residual mesmo
    # após o fix do Hamilton em calcular_quotas).
    chaves_ord = sorted(
        quotas_global.keys(),
        key=lambda k: (-quotas_global[k], random.random()),
    )

    por_treino: list[dict[str, int]] = [{} for _ in range(n_treinos)]
    capacidade = list(vagas_por_treino)
    # Offset inicial aleatório (em vez de 0 fixo). Sem isso, a soma
    # determinística das quotas anteriores fazia chaves de qtd menor caírem
    # sempre no mesmo treino mesmo após o tie-break aleatório acima (ex.
    # ombro 100% T2 em upper(3)x2T pré-2026-05-18). Distribui o offset
    # acumulado entre rotinas — preserva Bresenham, quebra viés estrutural.
    acumulador = random.randrange(n_treinos)

    for chave in chaves_ord:
        qtd = quotas_global[chave]
        if qtd <= 0:
            continue
        offset = acumulador % n_treinos
        restantes = qtd
        t = offset
        tentativas_sem_progresso = 0
        while restantes > 0:
            if capacidade[t] > 0:
                por_treino[t][chave] = por_treino[t].get(chave, 0) + 1
                capacidade[t] -= 1
                restantes -= 1
                tentativas_sem_progresso = 0
            else:
                tentativas_sem_progresso += 1
                if tentativas_sem_progresso >= n_treinos:
                    # Sem capacidade em ninguém — consistência interna falha
                    # (não deveria acontecer se sum(vagas_por_treino) == sum(quotas))
                    break
            t = (t + 1) % n_treinos
        acumulador += qtd

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

# Tabela de tradução de padrões legados (configs salvas em SQLite,
# templates antigos, ou cenários do harness podem referenciar os nomes
# antigos). Aplicada em `expandir_para_padroes`, `_padroes_de_escopo` e
# `gerar_sessao` legacy.
# - `squat`: refinado em squat_bilateral/unilateral na Frente 4 da Etapa 1
# - `core_isometrico`/`core_dinamico`: refinados nos 4 padrões biomecânicos
#   na Etapa 8 (Anexo 15-quater). Expandem nos padrões correspondentes da
#   subregião: iso ganha flexao_lateral também (Prancha Lateral); dyn não
#   tem variante de flexao_lateral cadastrada por enquanto.
_PADROES_LEGADOS = {
    "squat": ("squat_bilateral", "squat_unilateral"),
    "core_isometrico": (
        "flexao_tronco", "flexao_lateral", "rotacao_tronco", "flexao_quadril",
    ),
    "core_dinamico": (
        "flexao_tronco", "rotacao_tronco", "flexao_quadril",
    ),
}

# Tabela de tradução de SUBREGIÕES legadas — paralela a _PADROES_LEGADOS,
# mas no nível de subregião. Aplicada em `_padroes_de_escopo` e em
# `_decompor_demanda_subregiao` (caminho de pré-alocação).
# - `core`: subregião antiga (pré-Frente 3 da Etapa 1) que foi quebrada em
#   `core_isometrico` + `core_dinamico`. Configs antigas salvas em SQLite
#   ou cenários do harness podem ainda pedir `("subregiao", "core", N)`;
#   o decompositor divide N entre as 2 filhas (Hamilton ceil/floor) e cada
#   filha decompõe normalmente nos seus padrões refinados Etapa 8.
_SUBREGIOES_LEGADAS = {
    "core": ("core_isometrico", "core_dinamico"),
}

# DEPRECATED na Etapa 3: a regra 60% compostos foi aposentada da
# pré-alocação porque emerge naturalmente dos pesos das âncoras subregião
# (empurrar_compostos:3 vs empurrar_isolados:2 dá ~60% composto em peito).
# Mantida pra retrocompat de import e usada APENAS no caminho fallback de
# gerar_sessao_por_demandas standalone (regiões sem ANCORAS_POR_REGIAO
# definida — caso atual: cardio).
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
    "knee_extension":   "quad",
    "knee_flexion": "hamstring",
    # Lower — posterior
    "hinge":     "hamstring",
    "abduction": "glute",
    # Lower — outros
    "adduction":      "addutor",
    "flexao_plantar": "calf",
    # Core / cardio (Etapa 8 / Anexo 15-quater — 4 padrões refinados
    # substituíram core_isometrico/core_dinamico; todos compartilham grupo
    # "core" pra mesma semântica anti-agonista que antes)
    "flexao_tronco":  "core",
    "flexao_lateral": "core",
    "rotacao_tronco": "core",
    "flexao_quadril": "core",
    "cardio":          "cardio",
}


# ---------------------------------------------------------------------------
# Etapa 5: Score de pareamento intra-bloco
# ---------------------------------------------------------------------------
# Substitui a cascata determinística de 16 combinações geo×sub em
# `_buscar_candidato` por scoring linear + amostragem softmax top-K.
# A hierarquia dos pesos preserva a ordem da cascata anterior:
# regiao_diff (1000) >> padrao_diff (100) >> nao_agonista (50) >> composto (25),
# evitando compensações cruzadas (não dá pra somar 10x não-agonista pra
# superar 1x região diferente). Anti-uni é sensível a contraste muscular:
# penalidade alta entre unilaterais do mesmo grupo (resolveria caso V-Up
# Uni + Hollow Hold), baixa entre grupos diferentes (V-Up Uni + Tríceps
# Uni continua atraente).
PESOS_SCORE_PAREAMENTO: dict[str, int] = {
    "regiao_diff":         1000,  # candidato em região diferente do âncora
    "padrao_diff":          100,  # candidato em padrão diferente
    "nao_agonista":          50,  # grupo músculo-funcional diferente
    "composto":              25,  # candidato com purpose composto
    "anti_uni_mesmo_grupo": -75,  # 2 unilaterais do mesmo grupo musculo-funcional
    "anti_uni_diff_grupo":  -10,  # 2 unilaterais de grupos diferentes
}

# Amostragem entre top-K candidatos. K=3 dá variabilidade real sem
# arriscar pegar candidato de tier inferior (ex: P3 quando P1 tem
# 4 candidatos válidos). T=200 (1/5 do peso de regiao_diff) faz a
# softmax distribuir ~uniforme dentro do mesmo tier mas dominar top-1
# quando há gap entre tiers.
SOFTMAX_TOP_K: int = 3
SOFTMAX_TEMPERATURA: float = 200.0


def _score_pareamento(
    candidato: "Exercicio",
    bloco_atual: list["Exercicio"],
    evitar_agonistas: bool,
    pesos_config: Optional["ConfigPesosProximidade"] = None,
) -> float:
    """Score linear de quão bom é parear `candidato` com o bloco já montado.

    Maior = melhor. Componentes aditivos definidos em
    `PESOS_SCORE_PAREAMENTO`. Não aplica filtros hard (cargas, fadiga) —
    assume que `pode_adicionar_ao_bloco` já validou viabilidade.

    Componentes:
    - `regiao_diff`: candidato cuja região não está no bloco
    - `padrao_diff`: candidato cujo padrão não está no bloco
    - `nao_agonista`: grupo musculo-funcional diferente de todos no bloco
      (só pesa se `evitar_agonistas=True`)
    - `composto`: candidato com purpose composto/explosivo
    - `anti_uni_mesmo_grupo` / `anti_uni_diff_grupo`: penalidade quando
      candidato é unilateral E há outro unilateral no bloco; o peso
      depende de mesmo/diferente grupo musculo-funcional

    `pesos_config` (opcional, Etapa 7 Fase 7.6): quando passado, lê
    `anti_uni_mesmo_grupo_pesos[grupo]` do config (peso por grupo musculo-
    funcional) em vez da constante `PESOS_SCORE_PAREAMENTO["anti_uni_mesmo_grupo"]`.
    Wire da Seção 8.10 / B.2 (estrutura paralela ortogonal). `None` =
    comportamento legado (constante -75 da Etapa 5). Demais componentes
    seguem `PESOS_SCORE_PAREAMENTO` — calibração 7.6 só toca anti_uni
    nesta dim.
    """
    pesos = PESOS_SCORE_PAREAMENTO
    score: float = 0.0

    regioes_no_bloco = {e.regiao for e in bloco_atual}
    padroes_no_bloco = {e.padrao for e in bloco_atual}
    if candidato.regiao not in regioes_no_bloco:
        score += pesos["regiao_diff"]
    if candidato.padrao not in padroes_no_bloco:
        score += pesos["padrao_diff"]

    if evitar_agonistas:
        grupos_no_bloco = {GRUPO_MUSCULAR_PADRAO.get(e.padrao) for e in bloco_atual}
        if GRUPO_MUSCULAR_PADRAO.get(candidato.padrao) not in grupos_no_bloco:
            score += pesos["nao_agonista"]

    if _eh_composto(candidato):
        score += pesos["composto"]

    # Anti-unilateral refinado — sensível a contraste muscular.
    # Aplica uma penalidade por cada unilateral já presente no bloco.
    # Em blocos de 3 com 2 unilaterais já presentes, somam duas penalidades
    # (efeito acumulativo desejado: desincentiva trio com 3 unilaterais).
    anti_uni_pesos = (
        pesos_config.anti_uni_mesmo_grupo_pesos
        if pesos_config is not None else None
    )
    if candidato.unilateral == "unilateral":
        grupo_cand = GRUPO_MUSCULAR_PADRAO.get(candidato.padrao)
        for ex in bloco_atual:
            if ex.unilateral != "unilateral":
                continue
            grupo_outro = GRUPO_MUSCULAR_PADRAO.get(ex.padrao)
            mesmo_grupo = grupo_cand == grupo_outro
            if mesmo_grupo:
                # Lookup config (Fase 7.6 Dim 3) → fallback constante legado
                if anti_uni_pesos is not None and grupo_cand in anti_uni_pesos:
                    score += anti_uni_pesos[grupo_cand]
                else:
                    score += pesos["anti_uni_mesmo_grupo"]
            else:
                score += pesos["anti_uni_diff_grupo"]

    return score


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
    # Cargas (filtro Etapa 4 / HIB2). Default 0 = "não se aplica".
    carga_grip: int = 0
    carga_lombar: int = 0
    demanda_core: int = 0
    # Tag narrow-scope da Etapa 6 (Seção 7.7). True em exercícios "uso
    # pontual cross-family same-subregião" (Supino Fechado, Apoio Fechado
    # etc.). Hard INTRA via predicado `_compativel_intra` (D1.c). Default
    # False; banco real (XLSX) ainda não tem coluna — Fase 4 cadastra.
    variante_pontual: bool = False
    # Dimensões de proximidade soft INTRA da Etapa 6 (Fase 7.3 — Seções
    # 2/3/7). Default `None` = tag ausente (skip silencioso no score, ver
    # `_score_proximidade`). Banco real (XLSX) ainda não tem colunas;
    # harness propaga via overlay; Fase 4 cadastra.
    pegada: Optional[str] = None
    plano_corporal: Optional[str] = None
    equipamento_grupo: Optional[str] = None
    # Flag operacional — False exclui o exercício de todas as gerações.
    # Default True; XLSX vazio = ativo. Fase 4 cadastra.
    ativo: bool = True
    # Tier clínico curado (Fatia 2 Parte 1, 2026-05-23): Principal /
    # Intermediário / Acessório. Consumido pelo gerador_csp (H-T4, S-T1).
    # Default "" (vazio) preserva retrocompat com fixtures legacy que constroem
    # Exercicio direto. XLSX real tem coluna `tier` 100% preenchida pós-Parte 1.
    tier: str = ""
    # Rationale da decisão (Etapa 8 — Explicabilidade). Default None;
    # populado em `_selecionar_cand_score_aware` para o exercício escolhido.
    # Estrutura em `_montar_rationale`.
    rationale: Optional[dict] = None


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


def _int_or_zero(val) -> int:
    """Converte célula do XLSX em int, retornando 0 para None/NaN/inválido."""
    if val is None:
        return 0
    try:
        f = float(val)
        if math.isnan(f):
            return 0
        return int(f)
    except (TypeError, ValueError):
        return 0


def _bool_xlsx(val, default: bool) -> bool:
    """Converte célula do XLSX em bool, usando default para None/NaN."""
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, float) and math.isnan(val):
        return default
    return bool(val)


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
        if not _bool_xlsx(row.get("ativo"), True):
            continue
        eq_pri = _str(row.get("eq_primario")) or _EQ_FIXES.get(nome, "")
        padrao = _str(row.get("padrao"))
        # Etapa 8: PADRAO_PARA_SUBREGIAO retorna set[str] (1:N pra core).
        # Pra 1:1, usa a única subregião do set. Pra 1:N (core refinados),
        # se XLSX já informa subregião válida do set, respeita; senão pega
        # a primeira ordenada e warn.
        subs_canonicas = PADRAO_PARA_SUBREGIAO.get(padrao, set())
        subregiao_xlsx = _str(row.get("subregiao"))
        if subs_canonicas:
            if subregiao_xlsx and subregiao_xlsx in subs_canonicas:
                subregiao_canonica = subregiao_xlsx
            else:
                subregiao_canonica = sorted(subs_canonicas)[0]
                if subregiao_xlsx and subregiao_xlsx not in subs_canonicas:
                    print(
                        f"[carregar_banco] WARN: '{nome}' tem subregiao='{subregiao_xlsx}' "
                        f"no XLSX, mas padrao='{padrao}' deriva subregiões "
                        f"{sorted(subs_canonicas)} do mapa canônico. "
                        f"Usando '{subregiao_canonica}'."
                    )
        else:
            subregiao_canonica = ""
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
            carga_grip=_int_or_zero(row.get("carga_grip")),
            carga_lombar=_int_or_zero(row.get("carga_lombar")),
            demanda_core=_int_or_zero(row.get("demanda_core")),
            pegada=_str(row.get("pegada")) or None,
            plano_corporal=_str(row.get("plano_corporal")) or None,
            equipamento_grupo=_str(row.get("equipamento_grupo")) or None,
            variante_pontual=_bool_xlsx(row.get("variante_pontual"), False),
            ativo=_bool_xlsx(row.get("ativo"), True),
            tier=_str(row.get("tier")),
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

# Filtro de cargas (Etapa 4 / HIB2). Mapeamento dimensão → atributo no Exercicio.
_DIMS_CARGA: tuple[tuple[str, str], ...] = (
    ("grip", "carga_grip"),
    ("lombar", "carga_lombar"),
    ("core", "demanda_core"),
)


def _bloqueio_cargas(ex_a: "Exercicio", ex_b: "Exercicio", thresholds: dict) -> bool:
    """Retorna True se o par viola o filtro de cargas em qualquer dimensão.

    Bloqueia se (a) ambos os exercícios têm valor >= 1 na dimensão E
    (b) a soma dos valores >= threshold[dim]. Threshold ausente, 0 ou None
    pula a dimensão. Simétrica.

    Travados (`exercicios_travados`) são exceção e devem ser filtrados pelo
    caller — esta função é o predicado puro.
    """
    for dim, attr in _DIMS_CARGA:
        thr = thresholds.get(dim)
        if not thr:
            continue
        va = getattr(ex_a, attr, 0)
        vb = getattr(ex_b, attr, 0)
        if va >= 1 and vb >= 1 and (va + vb) >= thr:
            return True
    return False


def _rejeicoes_carga_vs_bloco(
    bloco: list["Exercicio"],
    pool: list["Exercicio"],
    excluir_idx: set[int],
    cargas_config: dict | None,
    exercicios_travados: list | set | None,
) -> list[dict]:
    """Lista candidatos do `pool` bloqueados por `_bloqueio_cargas` vs algum ex
    do `bloco`. Cada item: `{nome, contra, dimensao, soma, threshold}`.

    Mirror analítico de `_bloqueio_cargas` pra rationale de pareamento —
    captura quem foi descartado pela regra hard de cargas (grip/lombar/core).
    Travados (em `bloco` ou candidato) bypassam, conforme regra do filtro.
    Retorna `[]` quando `cargas_config` ausente/vazio.
    """
    if not cargas_config:
        return []
    travados_nomes = {
        e.nome if hasattr(e, "nome") else e
        for e in (exercicios_travados or [])
    }
    rejeicoes: list[dict] = []
    for k, cand in enumerate(pool):
        if k in excluir_idx:
            continue
        if cand.nome in travados_nomes:
            continue
        for ex_bloco in bloco:
            if ex_bloco.nome in travados_nomes:
                continue
            motivo = None
            for dim, attr in _DIMS_CARGA:
                thr = cargas_config.get(dim)
                if not thr:
                    continue
                va = getattr(ex_bloco, attr, 0)
                vb = getattr(cand, attr, 0)
                if va >= 1 and vb >= 1 and (va + vb) >= thr:
                    motivo = (dim, va + vb, thr)
                    break
            if motivo:
                rejeicoes.append({
                    "nome": cand.nome,
                    "contra": ex_bloco.nome,
                    "dimensao": motivo[0],
                    "soma": motivo[1],
                    "threshold": motivo[2],
                })
                break
    return rejeicoes


def pode_adicionar_ao_bloco(
    bloco_atual: list,
    candidato: Exercicio,
    tamanho_bloco: int,
    cargas_config: dict | None = None,
    exercicios_travados: list | set | None = None,
) -> bool:
    """Verifica se o candidato pode entrar no bloco.

    Aplica duas regras hard, nesta ordem:

    1. **Filtro de cargas** (Etapa 4 / HIB2). Se `cargas_config` é dict
       não-vazio, par é avaliado por `_bloqueio_cargas`. Travados bypassam
       — exercícios em `exercicios_travados` (lista de Exercicio ou set de
       nomes) não são checados contra carga.
    2. **Regra de fadiga**. Bloco 1-2: máx 1 alta-fadiga; bloco 3: máx 2.

    `cargas_config=None` mantém comportamento pré-Etapa 4 (filtro OFF).
    """
    # 1. Filtro de cargas (Etapa 4)
    if cargas_config:
        travados_nomes = {
            e.nome if hasattr(e, "nome") else e
            for e in (exercicios_travados or [])
        }
        cand_travado = candidato.nome in travados_nomes
        for ex in bloco_atual:
            if ex.nome in travados_nomes or cand_travado:
                continue
            if _bloqueio_cargas(ex, candidato, cargas_config):
                return False
    # 2. Regra de fadiga (existente)
    max_alta_fadiga = 1 if tamanho_bloco <= 2 else 2
    alta_fadiga_no_bloco = sum(1 for e in bloco_atual if e.fadiga >= FADIGA_MAX_PAR)
    if candidato.fadiga >= FADIGA_MAX_PAR and alta_fadiga_no_bloco >= max_alta_fadiga:
        return False
    return True


def _buscar_candidato(
    exercicios: list[Exercicio],
    usados: list[bool],
    bloco_atual: list[Exercicio],
    tamanho: int,
    evitar_agonistas: bool = False,
    cargas_config: dict | None = None,
    exercicios_travados: list | set | None = None,
    pesos_config: Optional["ConfigPesosProximidade"] = None,
) -> tuple[int | None, list[tuple[int, float]]]:
    """Retorna `(indice, scored)` — índice via softmax top-K + lista scored.

    `scored` = `[(j, score), ...]` de todos os candidatos hard-viáveis (mesmo
    os fora do top-K). Útil pra captura de rationale de pareamento (Etapa 8
    Explicabilidade — extensão pós-MVP). Quando não há candidatos, retorna
    `(None, [])`.

    Filtros hard (cargas, fadiga) continuam em `pode_adicionar_ao_bloco`. Os
    candidatos que sobrevivem são scored via `_score_pareamento`; os top-K
    (`SOFTMAX_TOP_K=3`) vão para softmax (`SOFTMAX_TEMPERATURA=200`) e
    amostra-se 1.

    Componentes do score em `PESOS_SCORE_PAREAMENTO`:
      +1000 região diferente do bloco
      +100  padrão diferente
      +50   grupo músculo-funcional diferente (se evitar_agonistas)
      +25   purpose composto/explosivo
      -75   2 unilaterais do mesmo grupo (anti-uni mesmo grupo)
      -10   2 unilaterais de grupos diferentes (anti-uni cross-group)
    """
    if not bloco_atual:
        return None, []

    candidatos: list[tuple[int, float]] = []
    for j in range(len(exercicios)):
        if usados[j]:
            continue
        if not pode_adicionar_ao_bloco(
            bloco_atual, exercicios[j], tamanho,
            cargas_config=cargas_config,
            exercicios_travados=exercicios_travados,
        ):
            continue
        s = _score_pareamento(exercicios[j], bloco_atual, evitar_agonistas,
                                pesos_config=pesos_config)
        candidatos.append((j, s))

    if not candidatos:
        return None, []

    candidatos.sort(key=lambda t: t[1], reverse=True)
    top = candidatos[:SOFTMAX_TOP_K]
    max_s = top[0][1]
    exps = [math.exp((s - max_s) / SOFTMAX_TEMPERATURA) for _, s in top]
    total = sum(exps)
    pesos = [e / total for e in exps]
    escolhido_idx = random.choices([j for j, _ in top], weights=pesos, k=1)[0]
    return escolhido_idx, candidatos


# Penalidade por exercício deixado solo no matching. Maior que qualquer score
# de par possível (P1 + composto + nao_agonista ≈ 1175), pra garantir que
# pareamentos válidos sempre venham antes de solos. Solos só sobram quando
# não há par viável (hard filter cargas/fadiga isola exercício).
_MATCHING_SOLO_PENALTY: float = 100_000.0


def _montar_blocos_matching(
    exercicios: list["Exercicio"],
    evitar_agonistas: bool = False,
    cargas_config: dict | None = None,
    exercicios_travados: list | set | None = None,
    avisos_carga: list | None = None,
    pesos_config: Optional["ConfigPesosProximidade"] = None,
) -> list[tuple]:
    """Monta blocos de tamanho 2 via matching enumerativo (Solução 2 do
    notas_distribuicao.md, 2026-05-17).

    Algoritmo:
      1. Pré-computa par-a-par viabilidade (hard) e score (`_score_pareamento`).
      2. Enumera todos emparelhamentos perfeitos + (quando inevitável) solos.
      3. Escolhe o de maior soma de scores. Solos pagam
         `_MATCHING_SOLO_PENALTY` cada — força minimização de solos antes
         da otimização de score por par.
      4. Constrói blocos com a âncora = exercício de menor índice no par
         (preserva semântica "mais cedo na lista de input = âncora"), ordenados
         pelo índice da âncora ascendente.
      5. Captura rationale de pareamento (papel=ancora + papel=par) reusando
         `_montar_rationale_pareamento` com `scored` = todos candidatos viáveis
         pra parear com a âncora (delta < 0 nas alternativas mostra quando
         o matching escolheu não-greedy por motivo global).

    Determinístico — sem `random.choice` na seleção. Pares iguais em score
    são desempatados pela ordem da recursão (primeiro encontrado wins, e a
    recursão explora índices em ordem crescente).
    """
    N = len(exercicios)

    # Pré-computa viabilidade hard + score do par (i âncora, j parceiro).
    # `pode_adicionar_ao_bloco` é simétrica em cargas e fadiga, então basta
    # checar i<j. O score, porém, NÃO é simétrico em todos os componentes
    # (composto avalia só o candidato), mas é simétrico nos componentes
    # estruturais (regiao_diff, padrao_diff, anti_uni). Escolhemos i como
    # âncora pra preservar "mais cedo = âncora".
    pair_ok: dict[tuple[int, int], bool] = {}
    pair_score: dict[tuple[int, int], float] = {}
    for i in range(N):
        for j in range(i + 1, N):
            if not pode_adicionar_ao_bloco(
                [exercicios[i]], exercicios[j], 2,
                cargas_config=cargas_config,
                exercicios_travados=exercicios_travados,
            ):
                continue
            pair_ok[(i, j)] = True
            pair_score[(i, j)] = _score_pareamento(
                exercicios[j], [exercicios[i]],
                evitar_agonistas, pesos_config=pesos_config,
            )

    # Enumeração recursiva. Estado: frozenset de índices não usados +
    # listas paralelas de pairs e solos acumuladas. Pega sempre o menor
    # unused, opções: parear com cada j>first em pair_ok, ou virar solo.
    best = {"score": float("-inf"), "pairs": [], "solos": []}

    def rec(unused: frozenset[int], pairs: list, solos: list, score: float) -> None:
        if not unused:
            adj = score - _MATCHING_SOLO_PENALTY * len(solos)
            if adj > best["score"]:
                best["score"] = adj
                best["pairs"] = list(pairs)
                best["solos"] = list(solos)
            return
        first = min(unused)
        rest = unused - {first}
        # Opção: parear first com j (em ordem crescente pra determinismo)
        for j in sorted(rest):
            if (first, j) in pair_ok:
                rec(
                    rest - {j},
                    pairs + [(first, j)],
                    solos,
                    score + pair_score[(first, j)],
                )
        # Opção: deixar first solo (sempre considerada — cobre N ímpar e
        # caso em que NENHUM par viável existe pra first).
        rec(rest, pairs, solos + [first], score)

    rec(frozenset(range(N)), [], [], 0.0)

    # Construir layout final: lista de (ancora_idx, [exs_idx]) ordenada
    # pelo índice da âncora ascendente. Preserva ordem original.
    bloco_por_ancora: list[tuple[int, list[int]]] = []
    for (i, j) in best["pairs"]:
        bloco_por_ancora.append((i, [i, j]))
    for i in best["solos"]:
        bloco_por_ancora.append((i, [i]))
    bloco_por_ancora.sort(key=lambda t: t[0])

    # Emitir avisos relaxado_carga pros solos que existiriam SÓ por causa
    # de cargas_config. Dedup por par de exercícios (frozenset): quando A e
    # B são ambos solos e violariam cargas entre si, emitir 1 vez (mirror
    # do greedy, que ao processar A acha B livre → emite; ao processar B,
    # A já está usado → não emite).
    if cargas_config and avisos_carga is not None:
        ancora_para_bloco_idx = {
            anc: bi for bi, (anc, _) in enumerate(bloco_por_ancora)
        }
        emitted_pairs: set[frozenset[int]] = set()
        # Iterar solos em ordem crescente (já vêm assim do best["solos"],
        # mas explicitamos pra segurança).
        for solo_i in sorted(best["solos"]):
            ancora_ex = exercicios[solo_i]
            cand_off_idx = None
            cand_off = None
            for other in range(N):
                if other == solo_i:
                    continue
                if pode_adicionar_ao_bloco(
                    [ancora_ex], exercicios[other], 2,
                    cargas_config=None,
                    exercicios_travados=exercicios_travados,
                ):
                    cand_off_idx = other
                    cand_off = exercicios[other]
                    break
            if cand_off is None:
                continue
            pair_key = frozenset({solo_i, cand_off_idx})
            if pair_key in emitted_pairs:
                continue
            emitted_pairs.add(pair_key)
            motivo = None
            for dim, attr in _DIMS_CARGA:
                t = cargas_config.get(dim)
                if not t:
                    continue
                va = getattr(ancora_ex, attr, 0)
                vb = getattr(cand_off, attr, 0)
                if va >= 1 and vb >= 1 and (va + vb) >= t:
                    motivo = (dim, va + vb, t)
                    break
            if motivo:
                avisos_carga.append({
                    "tipo": "relaxado_carga",
                    "bloco_idx": ancora_para_bloco_idx[solo_i],
                    "exercicio": ancora_ex.nome,
                    "par_bloqueado": cand_off.nome,
                    "dimensao": motivo[0],
                    "soma": motivo[1],
                    "threshold": motivo[2],
                })

    # Construir blocos com rationale.
    blocos: list[tuple] = []
    for ancora_idx, exs_idx in bloco_por_ancora:
        if len(exs_idx) == 1:
            blocos.append((exercicios[exs_idx[0]],))
            continue

        ancora_ex = exercicios[exs_idx[0]]
        parceiro_idx = exs_idx[1]
        parceiro_ex = exercicios[parceiro_idx]

        # `scored` pra rationale do parceiro: todos os candidatos viáveis pra
        # parear com a âncora, com seus scores LOCAIS (âncora sozinha no bloco).
        # Inclui o próprio parceiro escolhido. Delta < 0 nas alts mostra quando
        # o matching escolheu um candidato local-subótimo por ganho global.
        scored_alts: list[tuple[int, float]] = []
        for j in range(N):
            if j == ancora_idx:
                continue
            key = (min(ancora_idx, j), max(ancora_idx, j))
            if key not in pair_ok:
                continue
            s_local = _score_pareamento(
                exercicios[j], [ancora_ex],
                evitar_agonistas, pesos_config=pesos_config,
            )
            scored_alts.append((j, s_local))
        scored_alts.sort(key=lambda t: t[1], reverse=True)

        pareamento_par = _montar_rationale_pareamento(
            parceiro_ex, scored_alts, exercicios, [ancora_ex],
            evitar_agonistas, pesos_config,
        )
        parceiro_com_rat = replace(parceiro_ex, rationale={
            **(parceiro_ex.rationale or {}),
            "pareamento": pareamento_par,
        })

        rejeitados_carga = _rejeicoes_carga_vs_bloco(
            bloco=[ancora_ex],
            pool=exercicios,
            excluir_idx={ancora_idx, parceiro_idx},
            cargas_config=cargas_config,
            exercicios_travados=exercicios_travados,
        )
        ancora_com_rat = replace(ancora_ex, rationale={
            **(ancora_ex.rationale or {}),
            "pareamento": {
                "papel": "ancora",
                "parceiros": [parceiro_ex.nome],
                "rejeitados_carga": rejeitados_carga,
            },
        })

        blocos.append((ancora_com_rat, parceiro_com_rat))

    return blocos


def montar_blocos(
    exercicios: list[Exercicio],
    tamanho: int = 2,
    evitar_agonistas: bool = False,
    cargas_config: dict | None = None,
    exercicios_travados: list | set | None = None,
    avisos_carga: list | None = None,
    pesos_config: Optional["ConfigPesosProximidade"] = None,
) -> list[tuple]:
    """
    Monta blocos de tamanho configurável (1, 2 ou 3).
    A escolha do par é feita por `_buscar_candidato` (Etapa 5: scoring linear
    + softmax top-K). Score privilegia região e padrão diferentes dentro do
    bloco, contraste muscular (não-agonista), parceiro composto, e penaliza
    pares unilateral-unilateral conforme grupo musculo-funcional.

    Se `cargas_config` está ativo e `avisos_carga` é uma lista mutável, blocos
    que ficam solo *por causa do filtro de cargas* (verificado via second-pass
    com filtro off) emitem aviso `relaxado_carga` na lista. Solo por fadiga
    ou por exaustão do banco não emite. Aviso traz: bloco_idx, exercicio
    (âncora), par_bloqueado (que existiria sem filtro), dimensao, soma, threshold.
    """
    if not exercicios:
        return []

    # Matching enumerativo pra tamanho=2 (Solução 2 do notas_distribuicao.md):
    # substitui o greedy `_buscar_candidato`-loop por enumeração de
    # emparelhamentos perfeitos com maximização da soma de scores. Resolve
    # caso Jose T1 (3 uni + 3 bi greedy → 2 uni juntos; ótimo é 3×P1).
    # tamanho=1 e tamanho=3 continuam no greedy original.
    if tamanho == 2 and len(exercicios) >= 2:
        return _montar_blocos_matching(
            exercicios,
            evitar_agonistas=evitar_agonistas,
            cargas_config=cargas_config,
            exercicios_travados=exercicios_travados,
            avisos_carga=avisos_carga,
            pesos_config=pesos_config,
        )

    usados = [False] * len(exercicios)
    blocos = []

    i = 0
    while i < len(exercicios):
        if usados[i]:
            i += 1
            continue

        bloco_atual = [exercicios[i]]
        usados[i] = True

        while len(bloco_atual) < tamanho:
            # Snapshot do contexto pré-append — usado pra rationale de
            # pareamento (papel "par") refletir o estado quando o candidato
            # foi escolhido (não o estado pós-append).
            bloco_no_momento = list(bloco_atual)
            melhor, scored = _buscar_candidato(
                exercicios, usados, bloco_atual, tamanho,
                evitar_agonistas=evitar_agonistas,
                cargas_config=cargas_config,
                exercicios_travados=exercicios_travados,
                pesos_config=pesos_config,
            )

            if melhor is None:
                # Second-pass para detectar relaxado_carga: se cargas_config
                # está ativo, tentar novamente sem filtro pra ver se carga era
                # a causa do solo. Se sim, emitir aviso.
                if cargas_config and avisos_carga is not None:
                    melhor_off, _scored_off = _buscar_candidato(
                        exercicios, usados, bloco_atual, tamanho,
                        evitar_agonistas=evitar_agonistas,
                        cargas_config=None,  # filtro desligado
                        exercicios_travados=exercicios_travados,
                        pesos_config=pesos_config,
                    )
                    if melhor_off is not None:
                        cand_off = exercicios[melhor_off]
                        ancora = bloco_atual[0]
                        # Achar a primeira dimensão violada vs âncora
                        motivo = None
                        for dim, attr in _DIMS_CARGA:
                            t = cargas_config.get(dim)
                            if not t:
                                continue
                            va = getattr(ancora, attr, 0)
                            vb = getattr(cand_off, attr, 0)
                            if va >= 1 and vb >= 1 and (va + vb) >= t:
                                motivo = (dim, va + vb, t)
                                break
                        if motivo:
                            avisos_carga.append({
                                "tipo": "relaxado_carga",
                                "bloco_idx": len(blocos),
                                "exercicio": ancora.nome,
                                "par_bloqueado": cand_off.nome,
                                "dimensao": motivo[0],
                                "soma": motivo[1],
                                "threshold": motivo[2],
                            })
                break

            # Captura rationale de pareamento pro par (papel="par") —
            # extensão pós-MVP da Etapa 8 Explicabilidade. Usa snapshot
            # `bloco_no_momento` (estado pré-append) pra capturar quem era
            # âncora + outros parceiros já presentes quando este candidato
            # foi escolhido. Custo: O(N) sobre `scored` (lista pequena).
            escolhido = exercicios[melhor]
            pareamento = _montar_rationale_pareamento(
                escolhido, scored, exercicios, bloco_no_momento,
                evitar_agonistas, pesos_config,
            )
            escolhido = replace(escolhido, rationale={
                **(escolhido.rationale or {}),
                "pareamento": pareamento,
            })
            bloco_atual.append(escolhido)
            usados[melhor] = True

        # Captura rationale na âncora (papel="ancora") só quando o bloco
        # acabou com parceiros — solo (tamanho 1 ou fallhrough quando relax
        # falhou) não recebe pareamento. Mutação local em `bloco_atual[0]`
        # via `replace`, sem mexer na lista de input `exercicios`.
        if len(bloco_atual) > 1:
            ancora_atual = bloco_atual[0]
            parceiros_nomes = [ex.nome for ex in bloco_atual[1:]]
            rejeitados_carga = _rejeicoes_carga_vs_bloco(
                bloco=[exercicios[i]],
                pool=exercicios,
                excluir_idx={i},
                cargas_config=cargas_config,
                exercicios_travados=exercicios_travados,
            )
            pareamento_ancora = {
                "papel": "ancora",
                "parceiros": parceiros_nomes,
                "rejeitados_carga": rejeitados_carga,
            }
            bloco_atual[0] = replace(ancora_atual, rationale={
                **(ancora_atual.rationale or {}),
                "pareamento": pareamento_ancora,
            })

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
    cargas_config: dict | None = None,
    pesos_config: Optional[ConfigPesosProximidade] = None,
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
    avisos_carga_local: list[dict] = []
    grupos = ordenar_blocos(montar_blocos(
        todos_selecionados,
        tamanho=tamanho_bloco,
        evitar_agonistas=evitar_agonistas,
        cargas_config=cargas_config,
        exercicios_travados=travados,
        avisos_carga=avisos_carga_local,
        pesos_config=pesos_config,
    ))
    avisos_da_sessao.extend(avisos_carga_local)

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
        # Retrocompat de subregiões legadas (`_SUBREGIOES_LEGADAS`): expande
        # nos padrões das subregiões filhas. Atual: "core" → padrões de
        # core_isometrico + core_dinamico.
        if escopo in _SUBREGIOES_LEGADAS:
            pads: list[str] = []
            for filha in _SUBREGIOES_LEGADAS[escopo]:
                pads.extend(SUBREGIAO_PARA_PADROES.get(filha, []))
            return pads
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
    # requer_composto aposentado na Etapa 3: quota composta emerge dos pesos
    # das âncoras subregião. Mantido como kwarg opcional pra retrocompat.
    requer_composto: bool = False
    # Extensão pós-Etapa 8 Explic (pre_alocacao): quando a demanda original é
    # `regiao`, este campo guarda o nome da subregião intermediária pela qual
    # o slot foi decomposto (regiao → subregiao_intermediaria → padrao).
    # `None` quando demanda original é subregiao ou padrao (sem intermediária).
    subregiao_intermediaria: Optional[str] = None


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


def _compativel_intra(
    cand: "Exercicio",
    alocados_intra: list["Exercicio"],
) -> bool:
    """Predicado central de proximidade hard INTRA (Etapa 6, D1 — Sessão 4).

    Retorna True sse `cand` é compatível com TODOS os exercícios já
    alocados no MESMO treino segundo as 3 regras hard:

    1. **Família refinada same-treino** — `cand.variacao_de == outro.variacao_de`
       (ambas não-vazias). Mesma família refinada = redundante (Seção 1.4).
    2. **`variante_pontual` cross-family same-subregião** — Supino Fechado +
       Apoio Fechado dentro de peito = max 1 por rotina por subregião (D1.c).
    3. **Lateralidade contextual costas** — 2 unilaterais dentro de costas =
       hard. Outras subregiões usam soft `anti_uni_mesmo_grupo` Etapa 5
       (D1.d). Subregiões "hard" listadas em `SUBREGIOES_LATERALIDADE_HARD`.

    Soft INTRA (pegada, plano_corporal, equipamento_grupo) NÃO entra aqui —
    vive em `_score_proximidade` aditivamente (D2, Fase 7.3), aplicado
    durante a seleção em `pre_alocar_rotina`.
    """
    for outro in alocados_intra:
        # 1. Família refinada same-treino
        if cand.variacao_de and cand.variacao_de == outro.variacao_de:
            return False
        # 2. variante_pontual cross-family same-subregião
        if (
            cand.variante_pontual
            and outro.variante_pontual
            and cand.subregiao == outro.subregiao
            and cand.variacao_de != outro.variacao_de
        ):
            return False
        # 3. Lateralidade contextual (costas)
        if (
            cand.unilateral == "unilateral"
            and outro.unilateral == "unilateral"
            and cand.subregiao == outro.subregiao
            and cand.subregiao in SUBREGIOES_LATERALIDADE_HARD
        ):
            return False
    return True


def _score_proximidade(
    cand: "Exercicio",
    alocados: list["Exercicio"],
    contexto: str,
    pesos_config: ConfigPesosProximidade = PESOS_DEFAULT,
) -> float:
    """Penalty soft de proximidade (D2 + D3 — Etapa 6, Seções 8.7 + 8.9).

    Composição **par-a-par cumulativa**: cada par (cand, outro) soma uma
    penalty constante por dim que colide. Penalty é negativa — quanto maior
    o módulo, mais o gerador desencoraja a escolha.

    `contexto`:
    - `"intra"` — pares dentro do MESMO treino (Fase 7.3). Dims:
      pegada, plano_corporal, equipamento_grupo. Família estrita,
      variante_pontual e lateralidade contextual costas são HARD via
      `_compativel_intra` (Seção 1.7) — não entram aqui.
    - `"inter"` — pares cross-treino dentro da mesma rotina (Fase 7.4,
      D3.1). Dims: família estrita (universal cross-subregião — Seção
      1.5; multiplicador 0.8 default), pegada/plano/equipamento_grupo
      same-subregião (multiplicador 0.8), variante_pontual cross-family
      same-subregião (multiplicador 0.95 — Soft Crítico, D1.c).
    - `"historico"` — match com R-1 (Fase 7.4, D3.3). Granularidade
      **nome OU família** (set match), penalty única por candidato
      (não cumulativa pares). Peso = `familia_estrita.peso_historico`
      (multiplicador 1.0 quando toggle ON).

    **Escopo de aplicação (Seção 1.5):**
    - INTRA + INTER soft (pegada/plano/equipamento): same-subregião only.
    - Família estrita INTER: **universal** (qualquer cross-treino, mesma
      família = penalty), independente de subregião.
    - variante_pontual INTER: cross-family + same-subregião only.

    **Tag ausente:** dim do cand ou outro `None`/`""` → ignorada
    silenciosamente. Banco real ainda não cadastra (Fase 4 fecha).

    **Pegada:** D2.1 fechou em **constante por dim**, não matriz 4×4.
    Calibração numérica final em 7.6.

    Pesos vêm de `pesos_config.<dim>.peso_intra/inter/historico(subregiao)`
    com cascata override→default (B.2). Subregiões marcadas N/A no override
    retornam 0 e a dim é silenciosamente ignorada.
    """
    if not alocados:
        return 0.0

    if contexto == "intra":
        return _score_intra(cand, alocados, pesos_config)
    if contexto == "inter":
        return _score_inter(cand, alocados, pesos_config)
    if contexto == "historico":
        return _score_historico(cand, alocados, pesos_config)
    return 0.0


def _score_intra(
    cand: "Exercicio",
    alocados: list["Exercicio"],
    pesos_config: ConfigPesosProximidade,
) -> float:
    """Branch INTRA — par-a-par cumulativa, same-subregião, 3 dims soft."""
    total = 0.0
    sub_cand = cand.subregiao
    for outro in alocados:
        if sub_cand != outro.subregiao:
            continue
        if cand.pegada and outro.pegada and cand.pegada == outro.pegada:
            total += pesos_config.pegada.peso_intra(sub_cand)
        if (
            cand.plano_corporal
            and outro.plano_corporal
            and cand.plano_corporal == outro.plano_corporal
        ):
            total += pesos_config.plano_corporal.peso_intra(sub_cand)
        if (
            cand.equipamento_grupo
            and outro.equipamento_grupo
            and cand.equipamento_grupo == outro.equipamento_grupo
        ):
            total += pesos_config.equipamento_grupo.peso_intra(sub_cand)
    return total


def _score_inter(
    cand: "Exercicio",
    alocados: list["Exercicio"],
    pesos_config: ConfigPesosProximidade,
) -> float:
    """Branch INTER — par-a-par cumulativa cross-treino (D3.1).

    Família estrita: universal (qualquer subregião). Pegada/plano/
    equipamento_grupo: same-subregião only. variante_pontual: cross-family
    same-subregião (multiplicador 0.95 — Soft Crítico).
    """
    total = 0.0
    sub_cand = cand.subregiao
    for outro in alocados:
        # Família estrita — escopo universal cross-treino (Seção 1.5)
        if cand.variacao_de and cand.variacao_de == outro.variacao_de:
            total += pesos_config.familia_estrita.peso_inter(sub_cand)
        # Demais dims same-subregião only
        if sub_cand != outro.subregiao:
            continue
        if cand.pegada and outro.pegada and cand.pegada == outro.pegada:
            total += pesos_config.pegada.peso_inter(sub_cand)
        if (
            cand.plano_corporal
            and outro.plano_corporal
            and cand.plano_corporal == outro.plano_corporal
        ):
            total += pesos_config.plano_corporal.peso_inter(sub_cand)
        if (
            cand.equipamento_grupo
            and outro.equipamento_grupo
            and cand.equipamento_grupo == outro.equipamento_grupo
        ):
            total += pesos_config.equipamento_grupo.peso_inter(sub_cand)
        # variante_pontual cross-family same-subregião (D1.c — Soft Crítico)
        if (
            cand.variante_pontual
            and outro.variante_pontual
            and cand.variacao_de != outro.variacao_de
        ):
            total += pesos_config.variante_pontual.peso_inter(sub_cand)
    return total


def _score_historico(
    cand: "Exercicio",
    historico_r1: list["Exercicio"],
    pesos_config: ConfigPesosProximidade,
) -> float:
    """Branch HISTÓRICO — D3.3: granularidade nome OR família, penalty única.

    Peso = `familia_estrita.peso_historico(subregiao)` (multiplicador 1.0
    quando toggle ON). Match qualquer ex na R-1 com nome igual OU família
    igual = penalty. Não cumulativa entre pares (candidato está ou não na
    R-1; o "quanto" é fixo).
    """
    nomes_r1 = {e.nome for e in historico_r1}
    fams_r1 = {e.variacao_de for e in historico_r1 if e.variacao_de}
    if cand.nome in nomes_r1 or (
        cand.variacao_de and cand.variacao_de in fams_r1
    ):
        return pesos_config.familia_estrita.peso_historico(cand.subregiao)
    return 0.0


# ---------------------------------------------------------------------------
# Etapa 8 — Explicabilidade: decomposição por dim
# ---------------------------------------------------------------------------
#
# Reproduzem `_score_intra`/`_score_inter`/`_score_historico` retornando uma
# lista de eventos `{"contexto", "dim", "peso", "com"}` em vez do total. O
# total ainda é calculado pelas funções originais (autoridade); estas servem
# apenas pra explicar o "por que" do candidato escolhido + top alternativas.
# Custo: dupla avaliação só nos K=top alternativas (não em todo o pool).


def _componentes_intra(
    cand: "Exercicio",
    alocados: list["Exercicio"],
    pesos_config: ConfigPesosProximidade,
) -> list[dict]:
    eventos: list[dict] = []
    sub_cand = cand.subregiao
    for outro in alocados:
        if sub_cand != outro.subregiao:
            continue
        if cand.pegada and outro.pegada and cand.pegada == outro.pegada:
            eventos.append({
                "contexto": "intra", "dim": "pegada",
                "peso": pesos_config.pegada.peso_intra(sub_cand),
                "com": outro.nome,
            })
        if (
            cand.plano_corporal
            and outro.plano_corporal
            and cand.plano_corporal == outro.plano_corporal
        ):
            eventos.append({
                "contexto": "intra", "dim": "plano_corporal",
                "peso": pesos_config.plano_corporal.peso_intra(sub_cand),
                "com": outro.nome,
            })
        if (
            cand.equipamento_grupo
            and outro.equipamento_grupo
            and cand.equipamento_grupo == outro.equipamento_grupo
        ):
            eventos.append({
                "contexto": "intra", "dim": "equipamento_grupo",
                "peso": pesos_config.equipamento_grupo.peso_intra(sub_cand),
                "com": outro.nome,
            })
    return eventos


def _componentes_inter(
    cand: "Exercicio",
    alocados: list["Exercicio"],
    pesos_config: ConfigPesosProximidade,
) -> list[dict]:
    eventos: list[dict] = []
    sub_cand = cand.subregiao
    for outro in alocados:
        if cand.variacao_de and cand.variacao_de == outro.variacao_de:
            eventos.append({
                "contexto": "inter", "dim": "familia_estrita",
                "peso": pesos_config.familia_estrita.peso_inter(sub_cand),
                "com": outro.nome,
            })
        if sub_cand != outro.subregiao:
            continue
        if cand.pegada and outro.pegada and cand.pegada == outro.pegada:
            eventos.append({
                "contexto": "inter", "dim": "pegada",
                "peso": pesos_config.pegada.peso_inter(sub_cand),
                "com": outro.nome,
            })
        if (
            cand.plano_corporal
            and outro.plano_corporal
            and cand.plano_corporal == outro.plano_corporal
        ):
            eventos.append({
                "contexto": "inter", "dim": "plano_corporal",
                "peso": pesos_config.plano_corporal.peso_inter(sub_cand),
                "com": outro.nome,
            })
        if (
            cand.equipamento_grupo
            and outro.equipamento_grupo
            and cand.equipamento_grupo == outro.equipamento_grupo
        ):
            eventos.append({
                "contexto": "inter", "dim": "equipamento_grupo",
                "peso": pesos_config.equipamento_grupo.peso_inter(sub_cand),
                "com": outro.nome,
            })
        if (
            cand.variante_pontual
            and outro.variante_pontual
            and cand.variacao_de != outro.variacao_de
        ):
            eventos.append({
                "contexto": "inter", "dim": "variante_pontual",
                "peso": pesos_config.variante_pontual.peso_inter(sub_cand),
                "com": outro.nome,
            })
    return eventos


def _componentes_historico(
    cand: "Exercicio",
    historico_r1: list["Exercicio"],
    pesos_config: ConfigPesosProximidade,
) -> list[dict]:
    if not historico_r1:
        return []
    nomes_r1 = {e.nome for e in historico_r1}
    fams_r1 = {e.variacao_de for e in historico_r1 if e.variacao_de}
    hit_nome = cand.nome in nomes_r1
    hit_familia = bool(cand.variacao_de and cand.variacao_de in fams_r1)
    if not (hit_nome or hit_familia):
        return []
    motivo = "nome" if hit_nome else "familia"
    return [{
        "contexto": "historico", "dim": "familia_estrita",
        "peso": pesos_config.familia_estrita.peso_historico(cand.subregiao),
        "com": motivo,  # "nome" ou "familia" (granularidade D3.3)
    }]


def _componentes_totais(
    cand: "Exercicio",
    alocados_intra: list["Exercicio"],
    alocados_inter: list["Exercicio"],
    historico_r1: list["Exercicio"],
    pesos_config: ConfigPesosProximidade,
) -> tuple[list[dict], float]:
    """Concatena componentes dos 3 contextos e retorna (eventos, total)."""
    eventos: list[dict] = []
    eventos.extend(_componentes_intra(cand, alocados_intra, pesos_config))
    eventos.extend(_componentes_inter(cand, alocados_inter, pesos_config))
    eventos.extend(_componentes_historico(cand, historico_r1, pesos_config))
    total = sum(ev["peso"] for ev in eventos)
    return eventos, total


def _montar_rationale(
    escolhido: "Exercicio",
    cands_scored: list[tuple["Exercicio", float]],
    slot_info: dict,
    alocados_intra: list["Exercicio"],
    alocados_inter: list["Exercicio"],
    historico_r1: list["Exercicio"],
    pesos_config: ConfigPesosProximidade,
    max_alternativas: int = 3,
    pre_alocacao_info: Optional[dict] = None,
) -> dict:
    """Monta o dict de rationale pro exercício escolhido.

    `cands_scored` é a lista completa `(exercicio, score)` (mesma que o
    softmax usa). Inclui o escolhido. As alternativas exibidas são as `K`
    de maior score depois do escolhido (não passaram no sorteio softmax).

    `pre_alocacao_info` (extensão pós-MVP) — quando passado, atacha chave
    `"pre_alocacao"` no rationale com info sobre a decomposição (subregião
    intermediária), ordem do slot no passe e escassez no momento da escolha.
    """
    componentes_escolhido = _componentes_intra(
        escolhido, alocados_intra, pesos_config
    )
    componentes_escolhido.extend(
        _componentes_inter(escolhido, alocados_inter, pesos_config)
    )
    componentes_escolhido.extend(
        _componentes_historico(escolhido, historico_r1, pesos_config)
    )
    score_escolhido = sum(ev["peso"] for ev in componentes_escolhido)

    # Top K alternativas (excluindo o escolhido), por score desc
    outros = [
        (e, s) for e, s in cands_scored
        if e.nome != escolhido.nome
    ]
    outros.sort(key=lambda t: t[1], reverse=True)
    alternativas: list[dict] = []
    for alt, _s_alt in outros[:max_alternativas]:
        eventos_alt, total_alt = _componentes_totais(
            alt, alocados_intra, alocados_inter, historico_r1, pesos_config,
        )
        alternativas.append({
            "nome": alt.nome,
            "score_total": total_alt,
            "componentes": eventos_alt,
            "delta": score_escolhido - total_alt,
        })

    resultado: dict = {
        "slot": slot_info,
        "score_total": score_escolhido,
        "componentes": componentes_escolhido,
        "alternativas": alternativas,
        "tamanho_pool": len(cands_scored),
    }
    if pre_alocacao_info is not None:
        resultado["pre_alocacao"] = pre_alocacao_info
    return resultado


def _componentes_pareamento(
    candidato: "Exercicio",
    bloco_atual: list["Exercicio"],
    evitar_agonistas: bool,
    pesos_config: Optional["ConfigPesosProximidade"] = None,
) -> list[dict]:
    """Decomposição por componente do `_score_pareamento` — mirror analítico.

    Cada evento: `{tipo, peso, com}`. `com` é o nome do parceiro quando o
    componente é par-a-par (anti_uni_*); `None` quando é propriedade do
    candidato vs bloco inteiro (regiao_diff, padrao_diff, nao_agonista,
    composto). Soma dos pesos == `_score_pareamento(candidato, bloco_atual, ...)`.
    """
    pesos = PESOS_SCORE_PAREAMENTO
    eventos: list[dict] = []

    regioes_no_bloco = {e.regiao for e in bloco_atual}
    padroes_no_bloco = {e.padrao for e in bloco_atual}
    if candidato.regiao not in regioes_no_bloco:
        eventos.append({
            "tipo": "regiao_diff",
            "peso": pesos["regiao_diff"],
            "com": None,
        })
    if candidato.padrao not in padroes_no_bloco:
        eventos.append({
            "tipo": "padrao_diff",
            "peso": pesos["padrao_diff"],
            "com": None,
        })

    if evitar_agonistas:
        grupos_no_bloco = {GRUPO_MUSCULAR_PADRAO.get(e.padrao) for e in bloco_atual}
        if GRUPO_MUSCULAR_PADRAO.get(candidato.padrao) not in grupos_no_bloco:
            eventos.append({
                "tipo": "nao_agonista",
                "peso": pesos["nao_agonista"],
                "com": None,
            })

    if _eh_composto(candidato):
        eventos.append({
            "tipo": "composto",
            "peso": pesos["composto"],
            "com": None,
        })

    anti_uni_pesos = (
        pesos_config.anti_uni_mesmo_grupo_pesos
        if pesos_config is not None else None
    )
    if candidato.unilateral == "unilateral":
        grupo_cand = GRUPO_MUSCULAR_PADRAO.get(candidato.padrao)
        for ex in bloco_atual:
            if ex.unilateral != "unilateral":
                continue
            grupo_outro = GRUPO_MUSCULAR_PADRAO.get(ex.padrao)
            if grupo_cand == grupo_outro:
                if anti_uni_pesos is not None and grupo_cand in anti_uni_pesos:
                    peso = anti_uni_pesos[grupo_cand]
                else:
                    peso = pesos["anti_uni_mesmo_grupo"]
                eventos.append({
                    "tipo": "anti_uni_mesmo_grupo",
                    "peso": peso,
                    "com": ex.nome,
                })
            else:
                eventos.append({
                    "tipo": "anti_uni_diff_grupo",
                    "peso": pesos["anti_uni_diff_grupo"],
                    "com": ex.nome,
                })

    return eventos


def _montar_rationale_pareamento(
    escolhido: "Exercicio",
    scored: list[tuple[int, float]],
    exercicios: list["Exercicio"],
    bloco_atual_no_momento: list["Exercicio"],
    evitar_agonistas: bool,
    pesos_config: Optional["ConfigPesosProximidade"] = None,
    max_alternativas: int = 3,
) -> dict:
    """Monta dict de rationale do pareamento (papel=par) pro ex escolhido.

    `scored` = lista `(indice, score)` produzida por `_buscar_candidato` no
    momento da escolha. Contém o escolhido + alternativas viáveis. As alts
    exibidas são as `K` de maior score depois do escolhido (não passaram no
    sorteio softmax).
    """
    ancora = bloco_atual_no_momento[0]
    outros = [e.nome for e in bloco_atual_no_momento[1:]]

    componentes_escolhido = _componentes_pareamento(
        escolhido, bloco_atual_no_momento, evitar_agonistas, pesos_config,
    )
    score_escolhido = sum(c["peso"] for c in componentes_escolhido)

    outros_scored = [
        (exercicios[j], s) for j, s in scored
        if exercicios[j].nome != escolhido.nome
    ]
    outros_scored.sort(key=lambda t: t[1], reverse=True)

    alternativas: list[dict] = []
    for alt, _s in outros_scored[:max_alternativas]:
        comps_alt = _componentes_pareamento(
            alt, bloco_atual_no_momento, evitar_agonistas, pesos_config,
        )
        score_alt = sum(c["peso"] for c in comps_alt)
        alternativas.append({
            "nome": alt.nome,
            "score_total": score_alt,
            "componentes": comps_alt,
            "delta": score_escolhido - score_alt,
        })

    return {
        "papel": "par",
        "ancora": ancora.nome,
        "outros_no_momento": outros,
        "score_pareamento": score_escolhido,
        "componentes": componentes_escolhido,
        "alternativas": alternativas,
    }


def _selecionar_cand_score_aware(
    cands: list["Exercicio"],
    alocados_intra: list["Exercicio"],
    alocados_inter: Optional[list["Exercicio"]] = None,
    historico_r1: Optional[list["Exercicio"]] = None,
    pesos_config: ConfigPesosProximidade = PESOS_DEFAULT,
    slot_info: Optional[dict] = None,
    pre_alocacao_info: Optional[dict] = None,
) -> "Exercicio":
    """Escolhe um candidato em `cands` ponderando pelo score soft total.

    Substitui `random.choice(cands)` em `pre_alocar_rotina` (Etapa 7,
    Fases 7.3 + 7.4). Score = INTRA (alocados mesmo treino) + INTER
    (alocados outros treinos) + HISTÓRICO (R-1, quando toggle ON).

    Quando todos os candidatos pontuam 0 (cross-subregião, tags ausentes,
    nenhum par redundante, R-1 vazio), a softmax cai em distribuição
    uniforme — equivalente a `random.choice` antigo.

    Reusa `SOFTMAX_TOP_K` / `SOFTMAX_TEMPERATURA` da Etapa 5 (mesma escala
    do `_score_pareamento`).

    **Etapa 8 — Explicabilidade.** Se `slot_info` for fornecido, o exercício
    retornado é uma cópia (`dataclasses.replace`) com `rationale` populado
    (slot + score + componentes + top 3 alternativas). A referência do banco
    permanece intocada. Quando `slot_info=None`, mantém compatibilidade
    retroativa (call-sites que ainda não passam slot_info recebem a
    referência do banco como antes).
    """
    if not cands:
        raise ValueError("cands vazio")

    inter_list = alocados_inter or []
    hist_list = historico_r1 or []

    # Caminho rápido — sem nada pra comparar, escolha uniforme + rationale trivial
    if (
        len(cands) == 1
        or (not alocados_intra and not alocados_inter and not historico_r1)
    ):
        escolhido = random.choice(cands)
        if slot_info is None:
            return escolhido
        rationale = _montar_rationale(
            escolhido,
            [(e, 0.0) for e in cands],
            slot_info,
            alocados_intra, inter_list, hist_list,
            pesos_config,
            pre_alocacao_info=pre_alocacao_info,
        )
        return replace(escolhido, rationale=rationale)

    def _total_score(e: "Exercicio") -> float:
        s = _score_proximidade(e, alocados_intra, "intra", pesos_config)
        s += _score_proximidade(e, inter_list, "inter", pesos_config)
        s += _score_proximidade(e, hist_list, "historico", pesos_config)
        return s

    scored = [(e, _total_score(e)) for e in cands]
    # Tiebreaker aleatório em empates (2026-05-18): sort estável + ordem do XLSX
    # introduzia viés sistemático — quando vários candidatos empatavam em score
    # 0, os primeiros do XLSX entravam no top-K do softmax de forma
    # determinística. Caso real: em costas(2)×2 slot puxada do T2, Pullover
    # Halteres + Pullover Polia ficavam nas 2 primeiras posições do empate por
    # ordem de cadastro, sendo escolhidos em ~50% das rotinas. Tupla
    # (-score, random) preserva ranking por score e desempata uniformemente.
    scored.sort(key=lambda t: (-t[1], random.random()))
    top = scored[:SOFTMAX_TOP_K]
    max_s = top[0][1]
    exps = [math.exp((s - max_s) / SOFTMAX_TEMPERATURA) for _, s in top]
    total = sum(exps)
    pesos = [e / total for e in exps]
    escolhido = random.choices([e for e, _ in top], weights=pesos, k=1)[0]

    if slot_info is None:
        return escolhido
    rationale = _montar_rationale(
        escolhido,
        scored,
        slot_info,
        alocados_intra, inter_list, hist_list,
        pesos_config,
        pre_alocacao_info=pre_alocacao_info,
    )
    return replace(escolhido, rationale=rationale)


def _candidatos_estritos(
    banco: list[Exercicio],
    nivel: str,
    escopo: str,
    cfg_treino: dict,
    nomes_bloqueados: set[str],
    familias_bloqueadas: set[str],
    filtro_purpose: Optional[str] = None,  # None | "composto" | "isolado"
    alocados_intra: Optional[list[Exercicio]] = None,
) -> list[Exercicio]:
    """Retorna candidatos viáveis pra um slot no MODO ESTRITO.

    Aplica filtros user (eq, complexidade), filtros de hierarquia (padrões do
    escopo), e bloqueia nomes + famílias já alocados. Não considera relax.

    `alocados_intra` (opcional) é a lista de exercícios já alocados no MESMO
    treino do slot — usada pelo predicado `_compativel_intra` pra aplicar
    regras hard INTRA 2 (variante_pontual) e 3 (lateralidade contextual
    costas). Regra 1 (família refinada same-treino) já é coberta pelo
    filtro `familias_bloqueadas` existente; será migrada pro predicado
    quando 7.4 separar família INTRA de INTER. Quando `None`, predicado
    é skip (compatibilidade retroativa com call-sites legados que não
    rastreiam alocados intra).
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
        # Predicado central de proximidade hard INTRA (Etapa 6 D1) —
        # cobre variante_pontual cross-family same-subregião + lateralidade
        # contextual costas. Família refinada já está coberta acima
        # via familias_bloqueadas (migração pro predicado fica pra 7.4).
        if alocados_intra and not _compativel_intra(e, alocados_intra):
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
    alocados_intra: Optional[list[Exercicio]] = None,
) -> int:
    """Número de candidatos viáveis (modo estrito) pra esse slot.

    Quanto menor, mais escasso, mais prioritário na ordenação. Slot com
    Etapa 3: filtro composto aposentado. A quota composta agora emerge
    dos pesos das âncoras subregião (Hamilton sobre ANCORAS_POR_SUBREGIAO),
    não de uma flag separada no slot.

    `alocados_intra` propagado pra `_candidatos_estritos` aciona o
    predicado D1 (variante_pontual + lateralidade contextual costas).
    """
    cands = _candidatos_estritos(
        banco, slot.nivel, slot.escopo_alocacao, cfg_treino,
        nomes_bloqueados, familias_bloqueadas, filtro_purpose=None,
        alocados_intra=alocados_intra,
    )
    return len(cands)


def _decompor_demanda_subregiao(
    subregiao: str,
    qtd: int,
    padroes_obrigatorios: Optional[list[str]] = None,
    banco: Optional[list[Exercicio]] = None,
) -> tuple[list[tuple[str, str, int]], list[dict]]:
    """Decompõe demanda subregião em sub-demandas por padrão.

    Etapa 3: usa ANCORAS_POR_SUBREGIAO quando definida pra distribuir vagas
    pelos pesos via Hamilton's Largest Remainder. Subregiões sem âncoras
    (core_dinamico, core_isometrico, bracos, adutores) caem em fallback.

    `padroes_obrigatorios`: padrões da subregião que devem ter ≥ 1 vaga
    (suporte a travados — D3.1). No caminho com âncoras, força inclusão
    doando 1 vaga da maior quota se necessário.

    `banco`: quando fornecido (caso normal via pre_alocar_rotina), o
    fallback usa quota ponderada por tamanho do pool de cada padrão
    (`_quotas_por_pool`), resolvendo o viés mono-ex documentado na Seção
    8.15.12. Quando `None` (chamada legacy/teste direto), preserva o
    cycling uniforme 1-de-cada da Etapa 2.

    Returns:
        (sub_demandas, avisos):
          sub_demandas = [("padrao", padrao, qtd), ...]
          avisos = lista de avisos `ancora_nao_cumprida` propagados de
            calcular_quotas (chave/escopo/nivel populados).
    """
    # Retrocompat de subregiões legadas (`_SUBREGIOES_LEGADAS`): expande
    # divisão de vagas entre as subregiões filhas (Hamilton ceil/floor com
    # cycling), cada filha decompõe recursivamente. Atual: "core" →
    # core_isometrico + core_dinamico.
    if subregiao in _SUBREGIOES_LEGADAS:
        filhas = _SUBREGIOES_LEGADAS[subregiao]
        if qtd <= 0:
            return [], []
        cada = qtd // len(filhas)
        sobra = qtd % len(filhas)
        filhas_shuf = random.sample(list(filhas), len(filhas))
        sub_dems_out: list[tuple[str, str, int]] = []
        avisos_out: list[dict] = []
        for i, filha in enumerate(filhas_shuf):
            q_filha = cada + (1 if i < sobra else 0)
            if q_filha <= 0:
                continue
            sd, av = _decompor_demanda_subregiao(
                filha, q_filha, padroes_obrigatorios, banco=banco,
            )
            sub_dems_out.extend(sd)
            avisos_out.extend(av)
        return sub_dems_out, avisos_out

    padroes = list(SUBREGIAO_PARA_PADROES.get(subregiao, []))
    if not padroes or qtd <= 0:
        return [], []

    obrig = [p for p in (padroes_obrigatorios or []) if p in padroes]

    # ── Caminho com âncoras (Etapa 3) ────────────────────────────────────
    if subregiao in ANCORAS_POR_SUBREGIAO:
        quotas, avisos = _quotas_de_subregiao(subregiao, qtd)

        # Garantir que cada padrão obrigatório (travado) tem ≥1 vaga.
        # Se a quota não cobre, doar 1 da maior quota pro travado.
        for p_trav in obrig:
            if quotas.get(p_trav, 0) == 0:
                if quotas:
                    # Tie-break sorteado entre quotas iguais (auditoria 2026-05-18)
                    p_doador = max(quotas, key=lambda k: (quotas[k], random.random()))
                    if quotas[p_doador] > 1:
                        quotas[p_doador] -= 1
                        quotas[p_trav] = 1

        return [("padrao", p, q) for p, q in quotas.items() if q > 0], avisos

    # ── Caminho fallback ─────────────────────────────────────────────────
    # Subregiões sem âncora: core_dinamico, core_isometrico, bracos,
    # adutores. Quando `banco` fornecido, usa quota ponderada por pool
    # (fix do viés mono-ex pós-CORE — Seção 8.15.12). Sem `banco`, mantém
    # cycling uniforme legacy (compat com chamadas externas/testes).
    if banco is not None:
        pool_por_padrao = {
            p: sum(1 for e in banco if e.padrao == p) for p in padroes
        }
        quotas = _quotas_por_pool(padroes, qtd, pool_por_padrao, obrigatorias=obrig)
        return [("padrao", p, q) for p, q in quotas.items() if q > 0], []

    # Legacy: cycling uniforme 1-de-cada (Etapa 2)
    if qtd <= len(obrig):
        escolhidos = random.sample(obrig, qtd)
        return [("padrao", p, 1) for p in escolhidos], []

    alocacao = {p: 1 for p in obrig}
    vagas_restantes = qtd - len(obrig)

    nao_obrig = [p for p in padroes if p not in alocacao]
    if vagas_restantes > 0 and nao_obrig:
        n_cobrir = min(vagas_restantes, len(nao_obrig))
        nao_obrig_shuf = random.sample(nao_obrig, len(nao_obrig))
        for p in nao_obrig_shuf[:n_cobrir]:
            alocacao[p] = 1
        vagas_restantes -= n_cobrir

    if vagas_restantes > 0:
        pool_shuf = random.sample(padroes, len(padroes))
        for i in range(vagas_restantes):
            p = pool_shuf[i % len(pool_shuf)]
            alocacao[p] = alocacao.get(p, 0) + 1
    return [("padrao", p, qt) for p, qt in alocacao.items() if qt > 0], []


def _decompor_demanda_regiao(
    regiao: str,
    qtd: int,
    subregioes_obrigatorias: Optional[list[str]] = None,
    banco: Optional[list[Exercicio]] = None,
) -> tuple[list[tuple[str, str, int]], list[dict]]:
    """Decompõe demanda região em sub-demandas por subregião.

    Etapa 3: usa ANCORAS_POR_REGIAO quando definida pra distribuir vagas
    pelas subregiões via Hamilton. Filtro pré-quotas preserva regra Etapa
    2 D2.1: acessórias (obrigatoria=False) só competem se qtd > 2 ×
    num_obrigatorias. Regiões sem âncoras caem em fallback.

    `subregioes_obrigatorias`: subregiões que devem ter ≥ 1 vaga (suporte
    a travados — D3.1). Pode forçar inclusão de subregião com peso baixo.

    `banco`: quando fornecido (caso normal via pre_alocar_rotina), o
    fallback usa quota ponderada por tamanho do pool de cada subregião
    (espelha o que `_decompor_demanda_subregiao` faz pra padrões). Atual
    estado real: única região em fallback é `cardio` (1 subregião só),
    então o efeito prático é cosmético — mas mantemos consistência.

    Returns:
        (sub_demandas, avisos):
          sub_demandas = [("subregiao", subregiao, qtd), ...]
    """
    if qtd <= 0:
        return [], []

    obrig = list(subregioes_obrigatorias or [])

    # ── Caminho com âncoras (Etapa 3) ────────────────────────────────────
    if regiao in ANCORAS_POR_REGIAO:
        ancoras_raw = ANCORAS_POR_REGIAO[regiao]

        # Filtro pré-quotas: acessórias só competem se qtd > 2 × num_obrig
        # (preserva regra Etapa 2 D2.1 — essenciais não dividem espaço com
        # acessórias em demandas pequenas). Travado em acessória força
        # inclusão da acessória mesmo em qtd pequena.
        n_obrig = sum(1 for a in ancoras_raw if a["obrigatoria"])
        if n_obrig > 0 and qtd <= 2 * n_obrig:
            ancoras_para_q = [
                a for a in ancoras_raw
                if a["obrigatoria"] or a["subregiao"] in obrig
            ]
        else:
            ancoras_para_q = ancoras_raw

        ancoras_dict = [
            {"chave": a["subregiao"], "peso": a["peso"], "obrigatoria": a["obrigatoria"]}
            for a in ancoras_para_q
        ]
        quotas, avisos = calcular_quotas(ancoras_dict, qtd)
        for av in avisos:
            av["nivel"] = "regiao"
            av["escopo"] = regiao

        # Travado força inclusão de subregião não coberta
        for s_trav in obrig:
            if quotas.get(s_trav, 0) == 0:
                if quotas:
                    # Tie-break sorteado entre quotas iguais (auditoria 2026-05-18)
                    s_doador = max(quotas, key=lambda k: (quotas[k], random.random()))
                    if quotas[s_doador] > 1:
                        quotas[s_doador] -= 1
                        quotas[s_trav] = 1

        return [("subregiao", s, q) for s, q in quotas.items() if q > 0], avisos

    # ── Caminho fallback (Etapa 2 — essencial/acessório) ────────────────
    if regiao not in SUBREGIOES_POR_REGIAO:
        # Fallback duplo: distribui uniformemente entre subregiões da região
        subs = REGIAO_PARA_SUBREGIOES.get(regiao, [])
        if not subs:
            return [], []
        return [("subregiao", sub, qtd // len(subs)) for sub in subs if qtd // len(subs) > 0], []

    estrutura = SUBREGIOES_POR_REGIAO[regiao]
    essenciais = list(estrutura.get("essenciais", []))
    acessorias = list(estrutura.get("acessorias", []))
    todas_subs = essenciais + acessorias
    obrig_validas = [s for s in obrig if s in todas_subs]

    if qtd <= len(obrig_validas):
        escolhidos = random.sample(obrig_validas, qtd)
        return [("subregiao", sub, 1) for sub in escolhidos], []

    # Determinar pool de candidatas (essenciais + acessórias quando qtd
    # justifica), preservando regra D2.1 (acessórias só competem se
    # qtd > 2 × num_essenciais).
    inclui_acessorias = (qtd > 2 * len(essenciais)) or any(s in acessorias for s in obrig_validas)
    pool_subs = essenciais + acessorias if (inclui_acessorias and acessorias) else essenciais

    if not pool_subs:
        return [], []

    # Caminho novo (banco fornecido): quota ponderada por pool de
    # exercícios cadastrados em cada subregião. Resolve viés mono-ex.
    if banco is not None:
        pool_por_sub: dict[str, int] = {
            s: sum(1 for e in banco if e.subregiao == s) for s in pool_subs
        }
        quotas = _quotas_por_pool(
            pool_subs, qtd, pool_por_sub, obrigatorias=obrig_validas,
        )
        return [("subregiao", s, q) for s, q in quotas.items() if q > 0], []

    # Legacy: cycling uniforme 1-de-cada (Etapa 2)
    alocacao = {sub: 1 for sub in obrig_validas}
    vagas_restantes = qtd - len(obrig_validas)

    essenciais_faltantes = [s for s in essenciais if s not in alocacao]
    for sub in essenciais_faltantes:
        if vagas_restantes <= 0:
            break
        alocacao[sub] = 1
        vagas_restantes -= 1

    if vagas_restantes <= 0:
        return [("subregiao", sub, qt) for sub, qt in alocacao.items() if qt > 0], []

    if vagas_restantes > 0 and pool_subs:
        pool_shuffled = random.sample(pool_subs, len(pool_subs))
        for i in range(vagas_restantes):
            sub = pool_shuffled[i % len(pool_shuffled)]
            alocacao[sub] = alocacao.get(sub, 0) + 1

    return [("subregiao", sub, qt) for sub, qt in alocacao.items() if qt > 0], []


def _slot_compativel_com_travado(slot: _Slot, ex: Exercicio) -> bool:
    """Travado é compatível com slot se o padrão do travado pertence ao escopo do slot."""
    padroes_do_slot = set(_padroes_de_escopo(slot.nivel, slot.escopo_alocacao))
    return ex.padrao in padroes_do_slot


def pre_alocar_rotina(
    banco: list[Exercicio],
    configs: list[dict],
    relaxar_familia: bool = False,
    historico_r1: Optional[list[Exercicio]] = None,
    pesos_override: Optional[ConfigPesosProximidade] = None,
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
        relaxar_familia: sob Caminho A (Etapa 7 Fase 7.4 — D3.2), família
                 INTER deixou de ser hard. Toggle agora é no-op efetivo:
                 passe relax tem o mesmo conjunto de candidatos que estrito
                 (família INTER vira soft via `_score_proximidade` branch
                 INTER). Mantido na assinatura por retrocompat com app.
        historico_r1: lista de Exercicios da rotina anterior (R-1) quando
                 toggle HISTÓRICO ON (D3.3). `None` = toggle OFF (default).
                 Score HIST aplica penalty quando candidato match nome ou
                 família com algum ex da R-1.
        pesos_override: override opcional dos pesos de proximidade
                 (B.4 — `ConfigPesosProximidade`). `None` usa
                 `PESOS_DEFAULT`. Útil pra harness de calibração C 7.6.

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

    # Estrutura intermediária: pra cada (t_idx, d_idx_original), guardamos:
    #   - demanda original (nivel, escopo, qtd)
    #   - sub-demandas (apenas pra região; pra subregião/padrão é a própria)
    # Etapa 3: quota_composta aposentada (pesos das âncoras decidem composto/iso).
    quota_total: dict[tuple[int, int], tuple[str, str, int]] = {}
    sub_demandas_por_origem: dict[tuple[int, int], list[tuple[str, str, int]]] = {}
    # Mapa paralelo pra rationale.pre_alocacao (extensão pós-MVP Etapa 8 Explic):
    # `(t_idx, d_idx, sub_idx)` → nome da subregião intermediária pela qual essa
    # sub-demanda foi decomposta. Populado só quando demanda original é regiao
    # (e portanto há um nível intermediário). Travados mutam qtd mas preservam
    # ordem do sub_idx, então o mapa segue válido após Etapa B.
    subregiao_intermediaria_por_sub: dict[tuple[int, int, int], Optional[str]] = {}

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

    # ─── Etapa A.0: agregar demandas idênticas across treinos (Etapa 3) ──
    # Hierarquia treino > rotina: demandas iguais (mesmo nivel/escopo/qtd) em
    # treinos diferentes têm quota calculada UMA VEZ no nível rotina e
    # redistribuída via round-robin que minimiza concentração de déficit.
    # Demandas com travado entram no caminho per-treino (não agregam).
    demandas_agregadas: dict[tuple[str, str, int], list[tuple[int, int]]] = {}
    for t_idx, cfg in enumerate(configs_norm):
        for d_idx, dem in enumerate(cfg.get("demandas") or []):
            if not (isinstance(dem, (list, tuple)) and len(dem) >= 3):
                continue
            nv, esc, qt = dem[0], dem[1], int(dem[2])
            if qt <= 0:
                continue
            # Demandas com travado têm constraint extra → caminho per-treino
            if travados_por_demanda.get((t_idx, d_idx)):
                continue
            chave = (nv, esc, qt)
            demandas_agregadas.setdefault(chave, []).append((t_idx, d_idx))

    # Pra cada grupo com >1 treino e nivel != "padrao" (padrão é imune às
    # âncoras), calcular quotas globais e redistribuir
    quotas_pre_alocadas: dict[tuple[int, int], dict[str, int]] = {}
    # Mapa paralelo: para demandas regiao agregadas, padrão → primeira subregião
    # que aportou aquela vaga. Usado em rationale.pre_alocacao.subregiao_intermediaria.
    sub_intermediaria_aggr: dict[tuple[int, int], dict[str, str]] = {}
    for (nv, esc, qt), instancias in demandas_agregadas.items():
        if nv == "padrao":
            continue  # demanda padrão imune a âncoras
        if len(instancias) <= 1:
            continue  # 1 treino só → caminho per-treino normal

        n_tr = len(instancias)
        vagas_total = qt * n_tr

        if nv == "regiao":
            if esc not in ANCORAS_POR_REGIAO:
                continue  # fallback Etapa 2 (cardio) — sem agregação
            ancoras_raw = ANCORAS_POR_REGIAO[esc]
            n_obrig = sum(1 for a in ancoras_raw if a["obrigatoria"])
            # Filtro pré-quotas no nível região (acessórias só se qtd > 2*n_obrig)
            if n_obrig > 0 and qt <= 2 * n_obrig:
                ancoras_para_q = [a for a in ancoras_raw if a["obrigatoria"]]
            else:
                ancoras_para_q = ancoras_raw
            anc_dict = [
                {"chave": a["subregiao"], "peso": a["peso"], "obrigatoria": a["obrigatoria"]}
                for a in ancoras_para_q
            ]
            # Quotas no nível rotina: subregiões totais
            quotas_reg, avs_reg = calcular_quotas(anc_dict, vagas_total)
            for av in avs_reg:
                av["nivel"] = "regiao"
                av["escopo"] = esc
                av["escopo_demanda"] = esc
                av["treino_idx"] = instancias[0][0]
                avisos_rotina.append(av)

            # Distribuir subregiões entre treinos
            pesos_reg = {a["subregiao"]: a["peso"] for a in ancoras_para_q}
            por_treino_sub = _distribuir_quotas_entre_treinos(
                quotas_reg, n_tr, [qt] * n_tr, pesos_reg,
            )

            # Descer um nível: aplicar quotas de padrão. Agregação rotina-level
            # também aqui (2026-05-18) — antes cada treino chamava
            # `_decompor_demanda_subregiao` independentemente, o que sorteava
            # padrões obrigatórios per-treino quando qt<n_obrig (ex: costas
            # qt=1 em cada treino → 25% das rotinas perdia 1 obrigatória).
            # Agora: soma qt_subregiao na rotina, aplica Hamilton uma vez,
            # distribui resultado entre treinos via Bresenham respeitando
            # capacidade individual.
            quotas_pre_alocadas_por_inst: dict[int, dict[str, int]] = {
                i: {} for i in range(n_tr)
            }
            pad_to_sub_por_inst: dict[int, dict[str, str]] = {
                i: {} for i in range(n_tr)
            }

            subs_qts_por_treino: dict[str, list[int]] = {}
            for i in range(n_tr):
                for sub_esc, sub_qt in por_treino_sub[i].items():
                    if sub_qt > 0:
                        subs_qts_por_treino.setdefault(sub_esc, [0] * n_tr)[i] = sub_qt

            for sub_esc, qts_treino in subs_qts_por_treino.items():
                qt_total_sub = sum(qts_treino)
                if qt_total_sub <= 0:
                    continue

                if sub_esc in ANCORAS_POR_SUBREGIAO:
                    ancoras_sub = ANCORAS_POR_SUBREGIAO[sub_esc]
                    # Passa por _quotas_de_subregiao em vez de chamar
                    # calcular_quotas direto: respeita o carve-out
                    # SUBREGIOES_SORTEIO_VAGA_UNICA (ombro com vaga única).
                    quotas_pad_rotina, avs_pad = _quotas_de_subregiao(
                        sub_esc, qt_total_sub,
                    )
                    for av in avs_pad:
                        av["escopo_demanda"] = esc
                        av["treino_idx"] = instancias[0][0]
                        avisos_rotina.append(av)

                    # Piso de cobertura por treino: cada treino com qt>0
                    # da subregião deve receber ≥1 padrão obrigatório. Se
                    # soma das quotas obrigatórias < n_treinos_pos, doa
                    # de não-obrigatórias. (Caso típico: peito qt_rotina=2,
                    # 2 treinos → Hamilton dá compostos:1+isolados:1 pela
                    # proporção 3:2, mas T2 ficaria sem composto — Bernardo
                    # rotina 2026-05-18.)
                    #
                    # Carve-out: subregiões em SUBREGIOES_CARVE_OUT_QUOTAS
                    # com entrada pra esse nº de vagas já decidiram a
                    # distribuição por sorteio ponderado (decisão clínica
                    # deliberada). Aplicar piso aqui anularia o sorteio
                    # (forçaria de volta pra obrigatória), então pulamos.
                    obrigs_sub = [a["padrao"] for a in ancoras_sub if a["obrigatoria"]]
                    nao_obrigs_sub = [a["padrao"] for a in ancoras_sub if not a["obrigatoria"]]
                    n_treinos_qt_pos = sum(1 for q in qts_treino if q > 0)
                    carve_out_ativo = qt_total_sub in (
                        SUBREGIOES_CARVE_OUT_QUOTAS.get(sub_esc) or {}
                    )
                    if obrigs_sub and nao_obrigs_sub and not carve_out_ativo:
                        soma_obrig = sum(quotas_pad_rotina.get(p, 0) for p in obrigs_sub)
                        deficit = n_treinos_qt_pos - soma_obrig
                        for doador in nao_obrigs_sub:
                            while deficit > 0 and quotas_pad_rotina.get(doador, 0) > 0:
                                alvo = min(
                                    obrigs_sub,
                                    key=lambda p: (quotas_pad_rotina.get(p, 0), random.random()),
                                )
                                quotas_pad_rotina[doador] -= 1
                                quotas_pad_rotina[alvo] = quotas_pad_rotina.get(alvo, 0) + 1
                                deficit -= 1
                            if deficit <= 0:
                                break

                    pesos_pad = {a["padrao"]: a["peso"] for a in ancoras_sub}
                    por_treino_pad = _distribuir_quotas_entre_treinos(
                        quotas_pad_rotina, n_tr, qts_treino, pesos_pad,
                    )
                    for i in range(n_tr):
                        for pad, q in por_treino_pad[i].items():
                            if q > 0:
                                quotas_pre_alocadas_por_inst[i][pad] = (
                                    quotas_pre_alocadas_por_inst[i].get(pad, 0) + q
                                )
                                pad_to_sub_por_inst[i].setdefault(pad, sub_esc)
                else:
                    # Subregião sem âncoras (raro em região agregada — só
                    # cardio cai aqui). Mantém path per-treino legado.
                    for i in range(n_tr):
                        sub_qt = qts_treino[i]
                        if sub_qt <= 0:
                            continue
                        sub_dems_p, avs_sub = _decompor_demanda_subregiao(
                            sub_esc, sub_qt, banco=banco,
                        )
                        for av in avs_sub:
                            av["treino_idx"] = instancias[i][0]
                            av["escopo_demanda"] = esc
                            avisos_rotina.append(av)
                        for (_n, p, q) in sub_dems_p:
                            quotas_pre_alocadas_por_inst[i][p] = (
                                quotas_pre_alocadas_por_inst[i].get(p, 0) + q
                            )
                            pad_to_sub_por_inst[i].setdefault(p, sub_esc)

            for i, (t_idx, d_idx) in enumerate(instancias):
                quotas_pre_alocadas[(t_idx, d_idx)] = quotas_pre_alocadas_por_inst[i]
                sub_intermediaria_aggr[(t_idx, d_idx)] = pad_to_sub_por_inst[i]

        elif nv == "subregiao":
            if esc not in ANCORAS_POR_SUBREGIAO:
                continue  # fallback Etapa 2
            ancoras_raw = ANCORAS_POR_SUBREGIAO[esc]
            # Passa por _quotas_de_subregiao pra respeitar o carve-out
            # SUBREGIOES_SORTEIO_VAGA_UNICA (ombro com vaga única).
            quotas_sub, avs_sub = _quotas_de_subregiao(esc, vagas_total)
            for av in avs_sub:
                av["escopo_demanda"] = esc
                av["treino_idx"] = instancias[0][0]
                avisos_rotina.append(av)

            pesos_sub = {a["padrao"]: a["peso"] for a in ancoras_raw}
            por_treino_pad = _distribuir_quotas_entre_treinos(
                quotas_sub, n_tr, [qt] * n_tr, pesos_sub,
            )
            for i, (t_idx, d_idx) in enumerate(instancias):
                quotas_pre_alocadas[(t_idx, d_idx)] = por_treino_pad[i]

    # ─── Etapa A: decompor demandas e construir slots ────────────────────
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
            # Etapa 8: PADRAO_PARA_SUBREGIAO[p] é set[str] (1:N pra core).
            # Une todas as subregiões possíveis dos padrões obrigatórios.
            subs_obrig_set: set[str] = set()
            for p in padroes_obrig:
                subs_obrig_set |= PADRAO_PARA_SUBREGIAO.get(p, set())
            subs_obrig = list(subs_obrig_set)

            # Caminho hierarquia treino > rotina: usa quotas pré-calculadas
            # no nível rotina (Etapa A.0) se essa demanda foi agregada.
            quotas_aggr = quotas_pre_alocadas.get((t_idx, d_idx))
            if quotas_aggr is not None:
                pad_to_sub = sub_intermediaria_aggr.get((t_idx, d_idx), {})
                sub_dems_aggr = [
                    ("padrao", p, q) for p, q in quotas_aggr.items() if q > 0
                ]
                sub_demandas_por_origem[(t_idx, d_idx)] = sub_dems_aggr
                for sub_idx, (_n, p, _q) in enumerate(sub_dems_aggr):
                    subregiao_intermediaria_por_sub[(t_idx, d_idx, sub_idx)] = (
                        pad_to_sub.get(p)  # presente só pro caminho regiao agregado
                    )
                continue

            if nivel == "regiao":
                sub_dems_subregiao, avs_reg = _decompor_demanda_regiao(
                    escopo, qtd, subregioes_obrigatorias=subs_obrig, banco=banco,
                )
                for av in avs_reg:
                    av["treino_idx"] = t_idx
                    av["escopo_demanda"] = escopo
                    avisos_rotina.append(av)
                sub_dems_padrao: list[tuple[str, str, int]] = []
                # Track sub_esc parent para cada padrão produzido (primeira ocorrência)
                pad_sub_origem: list[Optional[str]] = []
                for (_n, sub_esc, sub_qt) in sub_dems_subregiao:
                    # Etapa 8: padrão pertence à subregião sse o nome está
                    # no set do mapa (1:N pra core).
                    pads_obrig_sub = [
                        p for p in padroes_obrig
                        if sub_esc in PADRAO_PARA_SUBREGIAO.get(p, set())
                    ]
                    sub_dems_p, avs_sub = _decompor_demanda_subregiao(
                        sub_esc, sub_qt, padroes_obrigatorios=pads_obrig_sub, banco=banco,
                    )
                    for sd in sub_dems_p:
                        sub_dems_padrao.append(sd)
                        pad_sub_origem.append(sub_esc)
                    for av in avs_sub:
                        av["treino_idx"] = t_idx
                        av["escopo_demanda"] = escopo
                        avisos_rotina.append(av)
                sub_demandas_por_origem[(t_idx, d_idx)] = sub_dems_padrao
                for sub_idx, sub_esc in enumerate(pad_sub_origem):
                    subregiao_intermediaria_por_sub[(t_idx, d_idx, sub_idx)] = sub_esc
            elif nivel == "subregiao":
                sub_dems_p, avs_sub = _decompor_demanda_subregiao(
                    escopo, qtd, padroes_obrigatorios=padroes_obrig, banco=banco,
                )
                sub_demandas_por_origem[(t_idx, d_idx)] = sub_dems_p
                for av in avs_sub:
                    av["treino_idx"] = t_idx
                    av["escopo_demanda"] = escopo
                    avisos_rotina.append(av)
                # subregiao_intermediaria fica None pra todos os slots desta demanda
                # (demanda original JÁ é subregião — sem intermediário no meio)
                for sub_idx in range(len(sub_dems_p)):
                    subregiao_intermediaria_por_sub[(t_idx, d_idx, sub_idx)] = None
            else:
                sub_demandas_por_origem[(t_idx, d_idx)] = [(nivel, escopo, qtd)]
                subregiao_intermediaria_por_sub[(t_idx, d_idx, 0)] = None

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
        for sub_idx, (sub_nivel, sub_escopo, sub_qtd) in enumerate(sub_dems):
            sub_int = subregiao_intermediaria_por_sub.get((t_idx, d_idx, sub_idx))
            for _ in range(sub_qtd):
                slot = _Slot(
                    treino_idx=t_idx,
                    d_idx_original=d_idx,
                    nivel=sub_nivel,
                    escopo_alocacao=sub_escopo,
                    escopo_demanda_original=escopo_orig,
                    subregiao_intermediaria=sub_int,
                )
                slots_pendentes.append(slot)

    pesos = pesos_override or PESOS_DEFAULT
    hist_list: list[Exercicio] = historico_r1 or []

    # Helper interno — exercícios já alocados no MESMO treino do slot
    # (input pro predicado D1 `_compativel_intra` e branch INTRA do score).
    # Inclui travados (-1) e demandas regulares.
    def _alocados_intra(t_idx: int) -> list[Exercicio]:
        out: list[Exercicio] = []
        for exs in alocacao[t_idx].values():
            out.extend(exs)
        return out

    # Helper — exercícios já alocados em OUTROS treinos da rotina (input
    # pro branch INTER do score, D3.1 — Fase 7.4).
    def _alocados_inter(t_idx_atual: int) -> list[Exercicio]:
        out: list[Exercicio] = []
        for t_idx, by_d in alocacao.items():
            if t_idx == t_idx_atual:
                continue
            for exs in by_d.values():
                out.extend(exs)
        return out

    # ─── Etapa D: passe 1 (estrito) ──────────────────────────────────────
    # Etapa 3: quota composta aposentada. Pesos das âncoras subregião
    # decidem distribuição composto/isolado (empurrar_compostos:3 vs
    # empurrar_isolados:2 já dá ~60% composto em peito).
    #
    # **Caminho A (Fase 7.4 — D3.2):** família INTER deixou de ser hard.
    # `_candidatos_estritos` recebe `set()` no lugar de `familias_globais`
    # — o filtro de família INTER não bloqueia mais; vira soft via score
    # INTER (`_score_proximidade` branch "inter"). `nomes_globais` continua
    # hard (regra forte de unicidade de nomes). `familias_globais` segue
    # rastreado pra propagar a Fase 1 via `variacao_pais_globais` (info
    # em avisos `incompleta`), sem bloquear seleção.
    slots_para_relax: list[_Slot] = []
    total_slots_estrito = len(slots_pendentes)  # snapshot pré-loop pra rationale
    ordem_estrito = 0
    nivel_orig_por_d: dict[tuple[int, int], str] = {
        k: v[0] for k, v in quota_total.items()
    }
    while slots_pendentes:
        # Calcular escassez de cada slot pendente (usando filtro INTER soft)
        def _escassez_slot(s: _Slot) -> int:
            cfg_t = configs_norm[s.treino_idx]
            return _calcular_escassez(
                s, banco, cfg_t, nomes_globais, set(),
                alocados_intra=_alocados_intra(s.treino_idx),
            )

        # Ordenação: (escassez_estrita, peso_nivel, jitter_seeded)
        slots_pendentes.sort(
            key=lambda s: (_escassez_slot(s), _peso_nivel(s.nivel), random.random())
        )

        slot = slots_pendentes.pop(0)
        ordem_estrito += 1
        escassez_no_momento = _escassez_slot(slot)
        cfg_t = configs_norm[slot.treino_idx]

        alocados_t = _alocados_intra(slot.treino_idx)
        alocados_inter_t = _alocados_inter(slot.treino_idx)
        cands = _candidatos_estritos(
            banco, slot.nivel, slot.escopo_alocacao, cfg_t,
            nomes_globais, set(),  # família INTER soft (Caminho A)
            filtro_purpose=None,
            alocados_intra=alocados_t,
        )

        if cands:
            slot_info = {
                "treino_idx": slot.treino_idx,
                "nivel": slot.nivel,
                "escopo": slot.escopo_alocacao,
                "escopo_demanda_original": slot.escopo_demanda_original,
                "passe": "estrito",
            }
            pre_alocacao_info = {
                "nivel_demanda_original": nivel_orig_por_d.get(
                    (slot.treino_idx, slot.d_idx_original), slot.nivel
                ),
                "subregiao_intermediaria": slot.subregiao_intermediaria,
                "ordem_processamento": ordem_estrito,
                "total_slots": total_slots_estrito,
                "escassez_no_momento": escassez_no_momento,
            }
            escolhido = _selecionar_cand_score_aware(
                cands, alocados_t, alocados_inter_t, hist_list, pesos,
                slot_info=slot_info,
                pre_alocacao_info=pre_alocacao_info,
            )
            alocacao[slot.treino_idx][slot.d_idx_original].append(escolhido)
            nomes_globais.add(escolhido.nome)
            familias_globais.add(escolhido.nome)
            if escolhido.variacao_de:
                familias_globais.add(escolhido.variacao_de)
        else:
            # Slot sem candidatos no estrito → vira candidato a relax
            slots_para_relax.append(slot)

    # ─── Etapa E: passe 2 (relax família entre treinos) ──────────────────
    # **Caminho A (Fase 7.4):** sob D3.2 clean break, família INTER deixou
    # de ser hard no passe estrito (Etapa D). O passe relax fica como
    # safety net pra casos onde o estrito ainda falha por outras razões
    # (banco saturado, fadiga, equipamento bloqueado, lateralidade
    # contextual costas). Sob esses casos, comportamento idêntico ao
    # estrito — `_candidatos_estritos` já recebe `set()` por família. Mantido
    # por retrocompat de sinalização de relaxados (`Sessao.relaxados`),
    # apesar de ser efetivamente no-op no caso comum.
    if relaxar_familia and slots_para_relax:
        # Re-ordenar slots remanescentes por escassez (relaxada — só nomes bloqueiam)
        def _escassez_relax(s: _Slot) -> int:
            cfg_t = configs_norm[s.treino_idx]
            # No relax, familias_bloqueadas = vazio, mas nomes_globais ainda bloqueia.
            return _calcular_escassez(
                s, banco, cfg_t, nomes_globais, set(),
                alocados_intra=_alocados_intra(s.treino_idx),
            )

        total_slots_relax = len(slots_para_relax)
        ordem_relax = 0
        while slots_para_relax:
            slots_para_relax.sort(
                key=lambda s: (_escassez_relax(s), _peso_nivel(s.nivel), random.random())
            )
            slot = slots_para_relax.pop(0)
            ordem_relax += 1
            escassez_no_momento = _escassez_relax(slot)
            cfg_t = configs_norm[slot.treino_idx]
            alocados_t = _alocados_intra(slot.treino_idx)
            alocados_inter_t = _alocados_inter(slot.treino_idx)
            cands = _candidatos_estritos(
                banco, slot.nivel, slot.escopo_alocacao, cfg_t,
                nomes_globais, set(),  # família relaxada
                filtro_purpose=None,
                alocados_intra=alocados_t,
            )
            if cands:
                slot_info = {
                    "treino_idx": slot.treino_idx,
                    "nivel": slot.nivel,
                    "escopo": slot.escopo_alocacao,
                    "escopo_demanda_original": slot.escopo_demanda_original,
                    "passe": "relax",
                }
                pre_alocacao_info = {
                    "nivel_demanda_original": nivel_orig_por_d.get(
                        (slot.treino_idx, slot.d_idx_original), slot.nivel
                    ),
                    "subregiao_intermediaria": slot.subregiao_intermediaria,
                    "ordem_processamento": ordem_relax,
                    "total_slots": total_slots_relax,
                    "escassez_no_momento": escassez_no_momento,
                }
                escolhido = _selecionar_cand_score_aware(
                    cands, alocados_t, alocados_inter_t, hist_list, pesos,
                    slot_info=slot_info,
                    pre_alocacao_info=pre_alocacao_info,
                )
                alocacao[slot.treino_idx][slot.d_idx_original].append(escolhido)
                nomes_globais.add(escolhido.nome)
                # Família AINDA é tracked pra slots subsequentes do mesmo passe relax
                familias_globais.add(escolhido.nome)
                if escolhido.variacao_de:
                    familias_globais.add(escolhido.variacao_de)
                relaxados_por_treino.setdefault(slot.treino_idx, []).append(escolhido.nome)
            else:
                # Mesmo no relax não há candidato → aviso rotina-level
                avisos_rotina.append(_aviso_slot_sem_candidato(
                    slot, quota_total, motivo="banco_filtrado_vazio_apos_relax",
                ))
    else:
        # relax desligado: slots_para_relax viram avisos diretamente
        for slot in slots_para_relax:
            avisos_rotina.append(_aviso_slot_sem_candidato(
                slot, quota_total, motivo="banco_filtrado_vazio",
            ))

    return alocacao, avisos_rotina, relaxados_por_treino


def _aviso_slot_sem_candidato(
    slot: _Slot,
    quota_total: dict,
    motivo: str,
) -> dict:
    """Constrói aviso pra slot que não conseguiu ser preenchido.

    Etapa 3: distingue `ancora_sem_candidatos` (slot é padrão de uma âncora
    obrigatória que ficou sem pool no banco filtrado) de `incompleta`
    genérico. Isso permite UI sinalizar diferente: âncora obrigatória sem
    candidatos é problema clínico mais sério que demanda incompleta por
    família esgotada.
    """
    nivel_dem = quota_total[(slot.treino_idx, slot.d_idx_original)][0]
    # Etapa 8: padrão pode mapear pra múltiplas subregiões (1:N pra core).
    # Considera padrão obrigatório se for âncora obrigatória em QUALQUER
    # subregião que ele atravessa. Pra padrões não-core (1:1), comportamento
    # idêntico ao pré-Etapa 8.
    subs_do_padrao = PADRAO_PARA_SUBREGIAO.get(slot.escopo_alocacao, set())
    # Pra interface do aviso, preserva 1 subregião escolhida deterministicamente.
    # 1:1 (não-core): primeira do set é a única. 1:N (core): primeira por ordem
    # alfabética — interface legada espera string única. Padrão sem mapeamento
    # vira "".
    subregiao_aviso = sorted(subs_do_padrao)[0] if subs_do_padrao else ""
    eh_obrigatoria = any(
        a["padrao"] == slot.escopo_alocacao and a["obrigatoria"]
        for sub in subs_do_padrao
        for a in ANCORAS_POR_SUBREGIAO.get(sub, [])
    )
    if eh_obrigatoria:
        return {
            "tipo": "ancora_sem_candidatos",
            "escopo": "rotina",
            "treino_idx": slot.treino_idx,
            "nivel": nivel_dem,
            "escopo_demanda": slot.escopo_demanda_original,
            "padrao": slot.escopo_alocacao,
            "subregiao": subregiao_aviso,
            "motivo": motivo,
            "faltam": 1,
        }
    return {
        "tipo": "incompleta",
        "escopo": "rotina",
        "treino_idx": slot.treino_idx,
        "nivel": nivel_dem,
        "escopo_demanda": slot.escopo_demanda_original,
        "nivel_alocacao": slot.nivel,
        "escopo_alocacao": slot.escopo_alocacao,
        "faltam": 1,
    }


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
    cargas_config: dict | None = None,
    pesos_config: Optional[ConfigPesosProximidade] = None,
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
                # Etapa 3: aplicar âncoras região + subregião quando definidas.
                # Fallback (regiões sem âncoras: cardio): cycling com regra
                # 60% compostos via PROPORCAO_COMPOSTOS (legado preservado).
                if escopo in ANCORAS_POR_REGIAO:
                    ancoras_raw = ANCORAS_POR_REGIAO[escopo]
                    n_obrig = sum(1 for a in ancoras_raw if a["obrigatoria"])
                    # Filtro pré-quotas: acessórias só competem se qtd > 2 × n_obrig
                    if n_obrig > 0 and qtd <= 2 * n_obrig:
                        ancoras_para_q = [a for a in ancoras_raw if a["obrigatoria"]]
                    else:
                        ancoras_para_q = ancoras_raw
                    anc_reg_dict = [
                        {"chave": a["subregiao"], "peso": a["peso"], "obrigatoria": a["obrigatoria"]}
                        for a in ancoras_para_q
                    ]
                    quotas_reg, avisos_reg = calcular_quotas(anc_reg_dict, qtd)
                    for av in avisos_reg:
                        av["nivel"] = "regiao"
                        av["escopo"] = escopo
                        avisos_da_sessao.append(av)
                    # Pra cada subregião alocada, descer um nível
                    for sub_esc, sub_qt in quotas_reg.items():
                        if sub_qt <= 0:
                            continue
                        if sub_esc in ANCORAS_POR_SUBREGIAO:
                            ancoras_sub = ANCORAS_POR_SUBREGIAO[sub_esc]
                            anc_sub_dict = [
                                {"chave": a["padrao"], "peso": a["peso"], "obrigatoria": a["obrigatoria"]}
                                for a in ancoras_sub
                            ]
                            quotas_sub, avisos_sub = calcular_quotas(anc_sub_dict, sub_qt)
                            for av in avisos_sub:
                                av["nivel"] = "subregiao"
                                av["escopo"] = sub_esc
                                avisos_da_sessao.append(av)
                            for p, q in quotas_sub.items():
                                if q > 0:
                                    _selecionar_ciclando([p], q)
                        else:
                            # Fallback: cycling pelos padrões da subregião
                            pads_sub = SUBREGIAO_PARA_PADROES.get(sub_esc, [])
                            pads_ord = _ordenar_padroes_por_prioridade(pads_sub, banco=banco)
                            _selecionar_ciclando(pads_ord, sub_qt, preferir_composto=True)
                else:
                    # Fallback Etapa 2: cycling com PROPORCAO_COMPOSTOS
                    cands_no_escopo = [e for e in banco if e.padrao in padroes]
                    tem_compostos = any(_eh_composto(e) for e in cands_no_escopo)
                    tem_isolados  = any(not _eh_composto(e) for e in cands_no_escopo)
                    padroes_shuf = list(padroes)
                    random.shuffle(padroes_shuf)
                    if tem_compostos and tem_isolados:
                        min_compostos = math.ceil(qtd * PROPORCAO_COMPOSTOS)
                        min_compostos = min(min_compostos, qtd)
                        max_isolados = qtd - min_compostos
                        n_comp = _selecionar_ciclando(padroes_shuf, min_compostos, filtro_purpose="composto")
                        n_iso = _selecionar_ciclando(padroes_shuf, max_isolados, filtro_purpose="isolado")
                        faltam = qtd - n_comp - n_iso
                        if faltam > 0:
                            n_extra_c = _selecionar_ciclando(padroes_shuf, faltam, filtro_purpose="composto")
                            faltam -= n_extra_c
                        if faltam > 0:
                            _selecionar_ciclando(padroes_shuf, faltam, filtro_purpose="isolado")
                    else:
                        _selecionar_ciclando(padroes_shuf, qtd, preferir_composto=True)
            elif nivel == "subregiao":
                # Etapa 3: aplicar âncoras subregião quando definidas.
                # Fallback (sem âncoras: core_dinamico, core_isometrico,
                # bracos, adutores): cycling com prioridade dinâmica.
                if escopo in ANCORAS_POR_SUBREGIAO:
                    ancoras_sub = ANCORAS_POR_SUBREGIAO[escopo]
                    anc_sub_dict = [
                        {"chave": a["padrao"], "peso": a["peso"], "obrigatoria": a["obrigatoria"]}
                        for a in ancoras_sub
                    ]
                    quotas_sub, avisos_sub = calcular_quotas(anc_sub_dict, qtd)
                    for av in avisos_sub:
                        av["nivel"] = "subregiao"
                        av["escopo"] = escopo
                        avisos_da_sessao.append(av)
                    for p, q in quotas_sub.items():
                        if q > 0:
                            _selecionar_ciclando([p], q)
                else:
                    padroes_ord = _ordenar_padroes_por_prioridade(padroes, banco=banco)
                    _selecionar_ciclando(padroes_ord, qtd, preferir_composto=True)
            else:
                # Demanda padrão: imune a âncoras (usuário foi específico)
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
    avisos_carga_local: list[dict] = []
    grupos = ordenar_blocos(montar_blocos(
        todos_selecionados,
        tamanho=tamanho_bloco,
        evitar_agonistas=evitar_agonistas,
        cargas_config=cargas_config,
        exercicios_travados=travados,
        avisos_carga=avisos_carga_local,
        pesos_config=pesos_config,
    ))
    avisos_da_sessao.extend(avisos_carga_local)

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
    historico_r1: Optional[list[Sessao]] = None,
    pesos_override: Optional[ConfigPesosProximidade] = None,
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
        historico_r1: rotina anterior do aluno (R-1) quando toggle HISTÓRICO
            ON (Etapa 7 Fase 7.4 — D3.3). `None` = toggle OFF (default).
            Score HIST aplica penalty quando candidato match nome ou família
            com algum ex da R-1.
        pesos_override: override opcional dos pesos de proximidade
            (`ConfigPesosProximidade`). `None` usa `PESOS_DEFAULT`. Útil
            pra harness de calibração C 7.6 (B.4).

    Returns:
        Lista de Sessao na mesma ordem de configs. Avisos `incompleta`
        rotina-level são anexados em sessoes[0].avisos com escopo="rotina".
    """
    # Normaliza configs (templates → demandas, D4 opção C)
    configs_norm = [_normalizar_config(c) for c in configs]

    # Achata historico_r1 (list[Sessao] → list[Exercicio]) pra propagar
    # à Fase 0. None preserva-se como None (toggle OFF).
    hist_r1_exs: Optional[list[Exercicio]] = None
    if historico_r1 is not None:
        hist_r1_exs = []
        for s in historico_r1:
            for b in s.blocos:
                for ex in (b.ex1, b.ex2, b.ex3):
                    if ex is not None:
                        hist_r1_exs.append(ex)

    # Fase 0: pré-alocação global (com 2º passe de relax se relaxar_familia)
    alocacao, avisos_rotina, relaxados_por_treino = pre_alocar_rotina(
        banco, configs_norm,
        relaxar_familia=relaxar_familia,
        historico_r1=hist_r1_exs,
        pesos_override=pesos_override,
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
        cargas_cfg    = cfg.get("cargas_config")

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
            cargas_config=cargas_cfg,
            pesos_config=pesos_override,
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
