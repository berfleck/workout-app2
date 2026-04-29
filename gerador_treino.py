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
    "squat":          "perna_anterior",
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
    "core_isometrico": "core",
    "core_dinamico":   "core",
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
    "core":   "core",
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


# Classificação composto vs isolado é por EXERCÍCIO via coluna `purpose` do banco.
# compound + explosive → composto. isolation + stability → isolado.
# A constante PADROES_COMPOSTOS abaixo é mantida apenas pra retrocompatibilidade
# de import (não é usada na lógica de seleção). Padrões mistos como `hinge`,
# `squat` e `puxadas` têm tanto compostos quanto isolados no banco — a
# classificação por padrão era incorreta.
PURPOSE_COMPOSTO = {"compound", "explosive"}

PADROES_COMPOSTOS = {
    "squat", "hinge",
    "empurrar_compostos", "remadas", "puxadas", "ombro_composto",
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
    "squat":        "quad",
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
        exercicios.append(Exercicio(
            nome=nome,
            variacao_de=_str(row.get("variacao_de")) or None,
            eq_primario=eq_pri,
            eq_secundario=_str(row.get("eq_secundario")) or None,
            regiao=_str(row.get("regiao")),
            padrao=_str(row.get("padrao")),
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
# Regra de similaridade
# ---------------------------------------------------------------------------

def selecionar_sem_repeticao_similaridade(
    candidatos: list[Exercicio],
    similaridades_usadas: set[str],
    variacao_pais_usados: set[str],
    n: int,
    relaxar_familia: bool = False,
    relaxados_out: Optional[list] = None,
) -> list[Exercicio]:
    """
    Seleciona até n exercícios evitando repetir grupos de similaridade.
    Se não houver candidatos suficientes respeitando a regra, relaxa:
    permite repetir grupos de similaridade para completar n exercícios,
    mas nunca repete o mesmo exercício.

    Se relaxar_familia=True e ainda assim não completar n, relaxa também
    o bloqueio por família (variacao_de). Os exercícios escolhidos nessa
    fase são adicionados a relaxados_out (se passado).
    """
    nomes_usados: set[str] = set()

    def _selecionar(pool, respeitar_sim, respeitar_familia=True):
        selecionados = []
        sims_desta_selecao = set()
        random.shuffle(pool)
        for e in pool:
            if e.nome in nomes_usados:
                continue
            sim_ok = (not respeitar_sim) or (
                e.similaridade not in similaridades_usadas
                and e.similaridade not in sims_desta_selecao
            )
            var_ok = (not respeitar_familia) or (
                e.variacao_de is None or e.variacao_de not in variacao_pais_usados
            )
            if sim_ok and var_ok:
                selecionados.append(e)
                sims_desta_selecao.add(e.similaridade)
                nomes_usados.add(e.nome)
            if len(selecionados) >= n:
                break
        return selecionados

    # Tentativa 1: respeitar similaridade + família
    resultado = _selecionar(list(candidatos), respeitar_sim=True)

    # Tentativa 2: relaxar similaridade (mantém família)
    if len(resultado) < n:
        restantes = [e for e in candidatos if e.nome not in nomes_usados]
        resultado += _selecionar(restantes, respeitar_sim=False)

    # Tentativa 3: relaxar família (apenas se permitido)
    if len(resultado) < n and relaxar_familia:
        restantes = [e for e in candidatos if e.nome not in nomes_usados]
        novos = _selecionar(restantes, respeitar_sim=False, respeitar_familia=False)
        if relaxados_out is not None:
            relaxados_out.extend(e.nome for e in novos)
        resultado += novos

    return resultado[:n]


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
) -> Sessao:
    """
    Substitui um exercício específico na sessão por outro do mesmo padrão
    e grupo de similaridade diferente dos já usados.

    Args:
        sessao: sessão atual
        nome_atual: nome do exercício a substituir
        banco: banco completo de exercícios
        equipamentos_bloqueados: equipamentos indisponíveis
        max_complexidade: complexidade máxima permitida

    Returns:
        Sessao atualizada com o exercício substituído
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

    # Similaridades já em uso (excluindo o exercício alvo)
    sims_em_uso = set()
    for i, bloco in enumerate(sessao.blocos):
        if bloco.ex1.nome != nome_atual:
            sims_em_uso.add(bloco.ex1.similaridade)
        if bloco.ex2 and bloco.ex2.nome != nome_atual:
            sims_em_uso.add(bloco.ex2.similaridade)
        if bloco.ex3 and bloco.ex3.nome != nome_atual:
            sims_em_uso.add(bloco.ex3.similaridade)

    # Nomes já em uso na sessão
    nomes_em_uso = set()
    for bloco in sessao.blocos:
        nomes_em_uso.add(bloco.ex1.nome)
        if bloco.ex2:
            nomes_em_uso.add(bloco.ex2.nome)
        if bloco.ex3:
            nomes_em_uso.add(bloco.ex3.nome)
    nomes_em_uso.discard(nome_atual)

    # Buscar substituto: mesmo padrão, similaridade não usada
    candidatos = filtrar_por_padrao(banco, exercicio_alvo.padrao)
    candidatos = filtrar_por_equipamentos(candidatos, eq_bloq)
    candidatos = filtrar_por_complexidade(candidatos, max_complexidade)
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

    similaridades_usadas: set[str] = set()
    todos_selecionados: list[Exercicio] = []
    avisos_da_sessao: list[dict] = []
    relaxados_local: list[str] = []

    # Exercícios travados entram primeiro
    for e in travados:
        todos_selecionados.append(e)
        similaridades_usadas.add(e.similaridade)

    # Selecionar por padrão
    nomes_travados = {e.nome for e in travados}
    for padrao in padroes:
        n_spec = epp.get(padrao, 1)

        # n_spec pode ser int (padrão) ou dict {"bilateral": n, "unilateral": n}
        if isinstance(n_spec, dict):
            sub_specs = [(lat, qt) for lat, qt in n_spec.items() if qt > 0]
        else:
            sub_specs = [(None, n_spec)]

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

            selecionados = selecionar_sem_repeticao_similaridade(
                candidatos, similaridades_usadas, var_pais, n,
                relaxar_familia=relaxar_familia,
                relaxados_out=relaxados_local,
            )
            for e in selecionados:
                similaridades_usadas.add(e.similaridade)
            todos_selecionados.extend(selecionados)

        # Avisos do tipo familia_repetida (1 por exercício relaxado)
        novos_relax = relaxados_local[n_antes_relax:]
        for nome_rel in novos_relax:
            ex_rel = next((e for e in todos_selecionados if e.nome == nome_rel), None)
            avisos_da_sessao.append({
                "tipo": "familia_repetida",
                "nivel": "padrao",
                "escopo": padrao,
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
                "escopo": padrao,
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
        return [escopo]
    if nivel == "subregiao":
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

    similaridades_usadas: set[str] = set()
    nomes_usados: set[str] = set()
    todos_selecionados: list[Exercicio] = []
    relaxados_local: list[str] = []  # nomes escolhidos via relax família

    # Travados entram primeiro
    for e in travados:
        todos_selecionados.append(e)
        similaridades_usadas.add(e.similaridade)
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

        Aplica os 3 níveis de relax CRUZANDO TODOS os padrões em cada nível,
        antes de descer pro próximo: estrito em todos → relax 1 em todos →
        relax 2 em todos. Isso evita que um padrão "esgotado" (sem candidatos
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
            # Preferência por composto dentro do nível: se houver, sorteia só dele;
            # caso contrário cai no pool inteiro.
            if preferir_composto and filtro_purpose is None:
                comp = [e for e in base if _eh_composto(e)]
                if comp:
                    return comp
            return base

        selecionados = 0

        # Niveis de relax a tentar, em ordem. Relax 2 só se relaxar_familia=True.
        niveis = [0, 1] + ([2] if relaxar_familia else [])

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
                    similaridades_usadas.add(escolhido.similaridade)
                    nomes_usados.add(escolhido.nome)
                    if escolhido.variacao_de:
                        var_pais_intra.add(escolhido.variacao_de)
                    var_pais_intra.add(escolhido.nome)
                    if nivel_relax == 2:
                        relaxados_local.append(escolhido.nome)
                    selecionados += 1
                    progresso = True
                if not progresso:
                    break  # esgotou este nível, desce pro próximo

        return selecionados

    # Resolver cada demanda
    rotulos_demandas: list[str] = []
    avisos_da_sessao: list[dict] = []

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
# Geração de múltiplos treinos com compartilhamento de estado de similaridade
# ---------------------------------------------------------------------------

def gerar_multiplos_treinos(
    banco: list[Exercicio],
    configs: list[dict],
    variar_entre_treinos: bool = True,
    relaxar_familia: bool = False,
) -> list[Sessao]:
    """
    Gera N sessões de treino evitando repetição de exercícios entre elas.

    Args:
        banco: banco completo de exercícios
        configs: lista de dicts, um por treino, com chaves:
            - padroes: list[str]
            - exercicios_por_padrao: dict
            - max_complexidade: int
            - tamanho_bloco: int
            - exercicios_travados: list[Exercicio] (opcional)
            - equipamentos_bloqueados: list[str] (opcional)
        variar_entre_treinos: se True, similaridades usadas num treino
            não se repetem nos seguintes (mais variação).
            Se False, só os nomes exatos são bloqueados entre treinos.

    Returns:
        Lista de Sessao na mesma ordem de configs.
    """
    # Conjuntos globais compartilhados entre treinos
    nomes_exatos_globais: set[str] = set()   # apenas nomes EXATOS de exercícios usados → filtra banco
    sims_globais: set[str] = set()           # grupos de similaridade bloqueados
    variacao_pais_globais: set[str] = set()  # nomes + pais usados → bloqueia famílias (relaxável)

    sessoes = []
    for cfg in configs:
        demandas      = cfg.get("demandas")  # lista de (nivel, escopo, qtd)
        padroes       = cfg.get("padroes", [])
        epp           = cfg.get("exercicios_por_padrao", {p: 1 for p in padroes})
        max_cx        = cfg.get("max_complexidade", 5)
        tam_bloco     = cfg.get("tamanho_bloco", 2)
        travados      = cfg.get("exercicios_travados", [])
        eq_bloq       = cfg.get("equipamentos_bloqueados", [])
        evit_agon     = cfg.get("evitar_agonistas", False)
        lat_padrao    = cfg.get("lateralidade_por_padrao")

        # Bloqueia nomes EXATOS já usados em treinos anteriores
        # (não inclui pais, pra permitir que o relax_familia ressuscite-os)
        banco_filtrado = [e for e in banco if e.nome not in nomes_exatos_globais]

        if demandas:
            sessao = gerar_sessao_por_demandas(
                banco_filtrado,
                demandas=demandas,
                equipamentos_bloqueados=eq_bloq,
                max_complexidade=max_cx,
                exercicios_travados=travados,
                tamanho_bloco=tam_bloco,
                variacao_pais_usados=variacao_pais_globais,
                evitar_agonistas=evit_agon,
                lateralidade_por_padrao=lat_padrao,
                relaxar_familia=relaxar_familia,
            )
        else:
            sessao = gerar_sessao(
                banco_filtrado,
                padroes,
                exercicios_por_padrao=epp,
                equipamentos_bloqueados=eq_bloq,
                max_complexidade=max_cx,
                exercicios_travados=travados,
                tamanho_bloco=tam_bloco,
                variacao_pais_usados=variacao_pais_globais,
                evitar_agonistas=evit_agon,
                relaxar_familia=relaxar_familia,
            )

        # Recompõe familias_usadas em cada aviso usando o banco COMPLETO
        # (sem o filtro nomes_globais que removeria justamente as famílias
        # já usadas — fundamental pra Templates mode, que não popula var_pais
        # durante a seleção interna).
        for av in sessao.avisos:
            if av["nivel"] == "padrao":
                escopo_padroes = [av["escopo"]]
            elif av["nivel"] == "subregiao":
                escopo_padroes = list(SUBREGIAO_PARA_PADROES.get(av["escopo"], []))
            elif av["nivel"] == "regiao":
                escopo_padroes = []
                for sub in REGIAO_PARA_SUBREGIOES.get(av["escopo"], []):
                    escopo_padroes.extend(SUBREGIAO_PARA_PADROES.get(sub, []))
            else:
                escopo_padroes = []
            nomes_em_escopo: set[str] = set()
            for e in banco:
                if e.padrao in escopo_padroes:
                    nomes_em_escopo.add(e.nome)
                    if e.variacao_de:
                        nomes_em_escopo.add(e.variacao_de)
            av["familias_usadas"] = sorted(n for n in variacao_pais_globais if n in nomes_em_escopo)

        # Registra o que foi usado para os próximos treinos
        for bloco in sessao.blocos:
            for ex in [bloco.ex1, bloco.ex2, bloco.ex3]:
                if ex:
                    nomes_exatos_globais.add(ex.nome)
                    # Família: adiciona AMBOS ex.nome e ex.variacao_de em var_pais pra
                    # cobrir filho-usado → irmãos bloqueados E pai-usado → filhos bloqueados.
                    # Esse set é o que o relax_familia consegue ignorar.
                    variacao_pais_globais.add(ex.nome)
                    if ex.variacao_de:
                        variacao_pais_globais.add(ex.variacao_de)
                    if variar_entre_treinos:
                        sims_globais.add(ex.similaridade)

        sessoes.append(sessao)

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
    similaridade: Optional[str] = None,
    max_complexidade: int = 5,
    max_fadiga: int = 5,
    equipamentos_bloqueados: Optional[list[str]] = None,
    ignorar_similaridade_usada: bool = False,
) -> list[Exercicio]:
    """
    Retorna lista de candidatos filtrados para substituir um exercício na sessão.
    Use após buscar_substitutos() e passe a escolha para substituir_exercicio_por().
    """
    eq_bloq = equipamentos_bloqueados or []

    nomes_em_uso = set()
    sims_em_uso = set()
    for bloco in sessao.blocos:
        for ex in [bloco.ex1, bloco.ex2, bloco.ex3]:
            if ex and ex.nome != nome_atual:
                nomes_em_uso.add(ex.nome)
                sims_em_uso.add(ex.similaridade)

    candidatos = list(banco)
    if padrao:
        candidatos = [e for e in candidatos if e.padrao == padrao]
    if regiao:
        candidatos = [e for e in candidatos if e.regiao == regiao]
    if purpose:
        candidatos = [e for e in candidatos if e.purpose == purpose]
    if unilateral:
        candidatos = [e for e in candidatos if e.unilateral == unilateral]
    if similaridade:
        candidatos = [e for e in candidatos if e.similaridade == similaridade]
    if eq_bloq:
        candidatos = [e for e in candidatos if e.eq_primario not in eq_bloq]

    candidatos = [e for e in candidatos if e.complexidade <= max_complexidade]
    candidatos = [e for e in candidatos if e.fadiga <= max_fadiga]
    candidatos = [e for e in candidatos if e.nome not in nomes_em_uso]
    if not ignorar_similaridade_usada:
        candidatos = [e for e in candidatos if e.similaridade not in sims_em_uso]

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
