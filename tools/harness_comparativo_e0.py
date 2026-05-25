"""Harness comparativo Frente E.0 — CSP × motor antigo.

Roda N rotinas por configuração nos DOIS motores com a mesma entrada
normalizada e produz relatório markdown lado-a-lado em
`docs/refatoracao/relatorios/E0_<data>.md`.

Frente E.0 do Bloco 2 do roadmap CSP (pré-requisito pra Frente E.1, que
vai substituir `/gerar` pelo motor CSP). Puramente observacional: NÃO
modifica nenhum motor; achados de divergência viram pendência no
roadmap, não patch.

Decisões fechadas no handoff `handoff_2026-05-24_frente_e0.md`:
- N=100 default, --n configurável via CLI.
- 4 configurações: Full Body 2T, ABC 3T, upper(3)×2T, perna_ant(3)+perna_post(3).
- Perfil default (nivel=3, aderencia=media); --matriz roda 2×2.
- Visual + descartar INFEASIBLE + pipeline completo (Solve + decode).
- Métricas mínimas: distribuição tier por subregião, cobertura H-R1,
  cobertura âncoras obrigatórias, variedade INTRA-config, overlap R-1,
  cycling fairness, tempo médio. % inviabilidade como auxiliar.

Roda standalone:

    python tools/harness_comparativo_e0.py            # N=100, 1 perfil
    python tools/harness_comparativo_e0.py --n 500    # mais sinal
    python tools/harness_comparativo_e0.py --matriz   # 2×2 perfis
    python tools/harness_comparativo_e0.py --out custom.md
"""
from __future__ import annotations

import argparse
import math
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gerador_csp import (  # noqa: E402
    ConfigVariedade,
    H_R1_REGRAS,
    carregar_banco_ativo,
    gerar_rotina_csp,
)
from gerador_treino import (  # noqa: E402
    ANCORAS_POR_SUBREGIAO,
    PADRAO_PARA_SUBREGIAO,
    Exercicio,
    Sessao,
    gerar_multiplos_treinos,
)


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfigComum:
    """Entrada normalizada que ambos os motores consomem."""

    nome: str
    # Uma lista de demandas por treino.
    demandas_por_treino: tuple[tuple[tuple[str, str, int], ...], ...]
    tamanho_bloco: int = 2
    evitar_agonistas: bool = True
    relaxar_familia: bool = True
    max_complexidade: int = 5

    @property
    def n_treinos(self) -> int:
        return len(self.demandas_por_treino)

    def descricao(self) -> str:
        partes = []
        for i, dems in enumerate(self.demandas_por_treino):
            ds = ", ".join(f"{esc}({q})" for _, esc, q in dems)
            partes.append(f"T{i+1}: [{ds}]")
        return " | ".join(partes)


@dataclass(frozen=True)
class PerfilAluno:
    nome: str
    nivel: int
    aderencia_tier: str  # "alta" | "media" | "baixa"

    @property
    def peso_aderencia_csp(self) -> int:
        # Mapeamento conservador da Frente D: alta=2, media=0, baixa=0
        return {"alta": 2, "media": 0, "baixa": 0}.get(self.aderencia_tier, 0)


@dataclass
class RunResult:
    """Resultado de UMA execução (1 rotina) de UM motor."""

    motor: str  # "csp" | "antigo"
    viavel: bool
    elapsed_ms: float
    # Rotina normalizada: list[treino][bloco][exercicio]. None se inviável.
    rotina: Optional[list[list[list[Exercicio]]]] = None
    status: str = ""
    # Micro-frente H-A0 (só CSP): lista de aplicações com flag degraded.
    # Antigo não tem H-A0 modelado; lista fica vazia. Usada pela métrica
    # `degradacoes_ha0_media`.
    h_a0_aplicadas: list[dict] = field(default_factory=list)


@dataclass
class AgregadoMotor:
    """Métricas agregadas sobre N runs de um motor numa config."""

    motor: str
    n_runs: int
    n_viaveis: int
    elapsed_ms_medio: float
    elapsed_ms_p95: float
    # Métricas só sobre runs viáveis.
    rotinas_distintas: int = 0
    overlap_pct: float = 0.0
    overlap_aplicavel: bool = False  # depende de n_viaveis >= 2
    tier_por_subregiao: dict[str, Counter] = field(default_factory=dict)
    h_r1_violacoes: dict[str, float] = field(default_factory=dict)
    ancoras_violacoes: dict[tuple[str, str], float] = field(default_factory=dict)
    cycling_distribuicao: dict[str, list[int]] = field(default_factory=dict)
    # Micro-frente H-A0 (2026-05-25): cobertura per (treino, região) de
    # subregiões obrigatórias. Aplicável quando config tem ≥1 demanda
    # nível regiao com âncoras declaradas. dict `{(t_idx, regiao, sub_obrig):
    # % rotinas COM cobertura}` — alvo 100% para o motor CSP, qualquer
    # outro valor é regressão.
    cobertura_ha0_por_treino: dict[tuple[int, str, str], float] = field(
        default_factory=dict
    )
    # Micro-frente H-A0: número médio de degradações por rotina (só CSP;
    # antigo fica em 0). Métrica auxiliar — alto = motor está degradando
    # H-A0 com frequência (pool/cardinalidade).
    degradacoes_ha0_media: float = 0.0


# ---------------------------------------------------------------------------
# Configurações canônicas (handoff Frente E.0)
# ---------------------------------------------------------------------------


def _configs_canonicas() -> list[ConfigComum]:
    """4 configurações mínimas decididas no handoff.

    Mistura templates clássicos (Full Body 2T, ABC 3T) com hierarquias
    diagnósticas (upper(3)×2T que destravou cycling Bresenham, e
    perna_ant(3)+perna_post(3) que estressa H-R1).
    """
    # 1) Full Body 2T: cada treino com upper(4) + lower(4) + core(1) = 9
    full_body_t1 = (
        ("subregiao", "peito", 1),
        ("subregiao", "costas", 2),
        ("subregiao", "ombro", 1),
        ("subregiao", "perna_anterior", 2),
        ("subregiao", "perna_posterior", 2),
        ("regiao", "core", 1),
    )
    full_body_t2 = (
        ("subregiao", "peito", 2),
        ("subregiao", "costas", 1),
        ("subregiao", "bracos", 2),
        ("subregiao", "perna_anterior", 1),
        ("subregiao", "perna_posterior", 2),
        ("regiao", "core", 1),
    )
    full_body = ConfigComum(
        nome="Full Body 2T",
        demandas_por_treino=(full_body_t1, full_body_t2),
    )

    # 2) ABC 3T: A=push (peito+ombro+tri), B=pull (costas+arms), C=lower+core
    # Day B usa `bracos(2)` em vez de `biceps(2)` direto: o pool curado de
    # `biceps` tem 6 exs mas TODOS são `variacao_de="Rosca bíceps"`, então
    # H-T1 (família refinada não repete intra-treino) torna biceps(2)
    # INVIÁVEL no CSP. O motor antigo aceita via relax intra-treino. A
    # divergência é registrada como achado no log; `bracos(2)` mantém a
    # intenção clínica do ABC (pull+arms no mesmo dia) e gera comparação útil.
    abc_a = (
        ("subregiao", "peito", 3),
        ("subregiao", "ombro", 2),
        ("padrao", "triceps", 2),
    )
    abc_b = (
        ("subregiao", "costas", 4),
        ("subregiao", "bracos", 2),
        ("regiao", "core", 1),
    )
    abc_c = (
        ("subregiao", "perna_anterior", 2),
        ("subregiao", "perna_posterior", 2),
        ("subregiao", "adutores", 1),
        ("subregiao", "panturrilha", 1),
        ("regiao", "core", 1),
    )
    abc = ConfigComum(
        nome="ABC 3T",
        demandas_por_treino=(abc_a, abc_b, abc_c),
    )

    # 3) upper(3) × 2T — destravou cycling Bresenham (Seção 8.15.14 + carve-outs)
    upper_t = (("regiao", "upper", 3),)
    upper_x2 = ConfigComum(
        nome="upper(3)×2T",
        demandas_por_treino=(upper_t, upper_t),
    )

    # 4) Stress H-R1: perna_anterior(3) + perna_posterior(3), 1 treino
    perna_full = (
        ("subregiao", "perna_anterior", 3),
        ("subregiao", "perna_posterior", 3),
    )
    perna = ConfigComum(
        nome="perna_ant(3)+perna_post(3)",
        demandas_por_treino=(perna_full,),
    )

    # 5) Full Body 2T — DEMANDAS NÍVEL REGIÃO (Micro-frente H-A0, 2026-05-25)
    # Reproduz o setup do achado clínico (`tools/criar_aluno_e_rotina_teste.py`):
    # regiao upper(3) + regiao lower(3) + regiao core(2) × 2T. Pré-H-A0:
    # zero costas + zero squat em 16 slots. Pós-H-A0: peito+costas+ombro
    # em cada treino de upper, perna_anterior+perna_posterior em cada lower.
    full_body_regiao_t = (
        ("regiao", "upper", 3),
        ("regiao", "lower", 3),
        ("regiao", "core", 2),
    )
    full_body_regiao = ConfigComum(
        nome="Full Body 2T (região, H-A0)",
        demandas_por_treino=(full_body_regiao_t, full_body_regiao_t),
    )

    return [full_body, abc, upper_x2, perna, full_body_regiao]


def _perfis(matriz: bool) -> list[PerfilAluno]:
    default = PerfilAluno(nome="default (nivel=3, aderencia=media)",
                          nivel=3, aderencia_tier="media")
    if not matriz:
        return [default]
    return [
        PerfilAluno("nivel=3, aderencia=alta", nivel=3, aderencia_tier="alta"),
        PerfilAluno("nivel=3, aderencia=baixa", nivel=3, aderencia_tier="baixa"),
        PerfilAluno("nivel=1, aderencia=alta", nivel=1, aderencia_tier="alta"),
        PerfilAluno("nivel=1, aderencia=baixa", nivel=1, aderencia_tier="baixa"),
    ]


# ---------------------------------------------------------------------------
# Invocação dos motores
# ---------------------------------------------------------------------------


def _peso_evitar_agon_para_csp(evitar: bool) -> int:
    # Espelha a Fatia 4.B: toggle ON → peso 10; OFF → 0.
    return 10 if evitar else 0


def _peso_tam_bloco_csp() -> int:
    # Espelha a Fatia 4.C: peso default 5 (não dominante).
    return 5


def rodar_csp(config: ConfigComum, perfil: PerfilAluno,
              banco: list[Exercicio], seed: int) -> RunResult:
    inicio = time.perf_counter()
    try:
        r = gerar_rotina_csp(
            list(config.demandas_por_treino),
            banco,
            nivel_aluno=perfil.nivel,
            seed=seed,
            variedade=ConfigVariedade(),
            peso_aderencia=perfil.peso_aderencia_csp,
            peso_evitar_agonistas=_peso_evitar_agon_para_csp(
                config.evitar_agonistas
            ),
            tamanho_preferido=config.tamanho_bloco,
            peso_tamanho_bloco=_peso_tam_bloco_csp(),
            relaxar_familia=config.relaxar_familia,
        )
    except Exception as exc:  # noqa: BLE001
        elapsed = (time.perf_counter() - inicio) * 1000.0
        return RunResult(motor="csp", viavel=False, elapsed_ms=elapsed,
                         status=f"EXC:{type(exc).__name__}:{exc}")
    elapsed = (time.perf_counter() - inicio) * 1000.0
    if not r.get("viavel"):
        return RunResult(motor="csp", viavel=False, elapsed_ms=elapsed,
                         status=str(r.get("status", "INFEASIBLE")))
    rotina = [t["blocos"] for t in r["treinos"]]
    return RunResult(motor="csp", viavel=True, elapsed_ms=elapsed,
                     rotina=rotina, status="OPTIMAL",
                     h_a0_aplicadas=list(r.get("h_a0_aplicadas") or []))


def rodar_antigo(config: ConfigComum, perfil: PerfilAluno,
                 banco: list[Exercicio], seed: int) -> RunResult:
    # `gerar_multiplos_treinos` consome `random` global pra cycling +
    # tie-breaks. Plantar a semente aqui dá reprodutibilidade.
    random.seed(seed)

    configs_antigo = [
        {
            "demandas": list(dems),
            "max_complexidade": config.max_complexidade,
            "tamanho_bloco": config.tamanho_bloco,
            "evitar_agonistas": config.evitar_agonistas,
        }
        for dems in config.demandas_por_treino
    ]
    # Filtragem por nível replicada do app antigo: complexidade > teto cai
    # fora do pool. Mirror byte-a-byte do `H-P1` aplicado no CSP. O motor
    # antigo aplica filtro internamente via `max_complexidade` da cfg, então
    # configuro = nivel.
    for c in configs_antigo:
        c["max_complexidade"] = perfil.nivel

    inicio = time.perf_counter()
    try:
        sessoes = gerar_multiplos_treinos(
            banco, configs_antigo,
            relaxar_familia=config.relaxar_familia,
        )
    except Exception as exc:  # noqa: BLE001
        elapsed = (time.perf_counter() - inicio) * 1000.0
        return RunResult(motor="antigo", viavel=False, elapsed_ms=elapsed,
                         status=f"EXC:{type(exc).__name__}:{exc}")
    elapsed = (time.perf_counter() - inicio) * 1000.0

    rotina = []
    for s in sessoes:
        treino = []
        for bloco in s.blocos:
            exs = [bloco.ex1]
            if bloco.ex2 is not None:
                exs.append(bloco.ex2)
            if bloco.ex3 is not None:
                exs.append(bloco.ex3)
            treino.append(exs)
        rotina.append(treino)
    return RunResult(motor="antigo", viavel=True, elapsed_ms=elapsed,
                     rotina=rotina, status="OPTIMAL")


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------


def _todos_exercicios(rotina: list[list[list[Exercicio]]]) -> list[Exercicio]:
    return [e for treino in rotina for bloco in treino for e in bloco]


def _exercicios_por_treino(
    rotina: list[list[list[Exercicio]]],
) -> list[list[Exercicio]]:
    return [[e for bloco in treino for e in bloco] for treino in rotina]


def _assinatura_rotina(rotina: list[list[list[Exercicio]]]) -> tuple:
    """Assinatura canônica pra detectar rotinas distintas.

    Ordena nomes dentro de cada treino e preserva ordem dos treinos
    (mudança entre T1/T2 conta como rotina diferente; ordem dentro do
    bloco e ordem dos blocos não).
    """
    return tuple(
        tuple(sorted(e.nome for bloco in treino for e in bloco))
        for treino in rotina
    )


def _tier_de(ex: Exercicio) -> str:
    """Lê tier; default Acessório quando vazio (banco antigo)."""
    t = getattr(ex, "tier", "") or ""
    if t in ("Principal", "Intermediário", "Acessório"):
        return t
    return "Acessório"


def metrica_tier_por_subregiao(
    rotinas: list[list[list[list[Exercicio]]]],
) -> dict[str, Counter]:
    """Distribuição de tier por subregião, agregada cross-iter.

    Retorna {subregiao: Counter({Principal: n, ...})} contando slot a slot.
    """
    contagem: dict[str, Counter] = defaultdict(Counter)
    for rotina in rotinas:
        for ex in _todos_exercicios(rotina):
            contagem[ex.subregiao][_tier_de(ex)] += 1
    return dict(contagem)


def _slots_de_subregiao_na_demanda(
    demandas: tuple[tuple[str, str, int], ...],
) -> Counter:
    """Conta slots determinísticos por subregião nas demandas.

    Reusa a lógica do CSP: subregião conta diretamente; padrão conta se
    mapping 1:1; região não conta (slot sem subregião determinística
    pré-solver). Mirror de `_subregioes_da_demanda` do gerador_csp.
    """
    contagem: Counter = Counter()
    for nivel, escopo, qtd in demandas:
        if nivel == "subregiao":
            contagem[escopo] += qtd
        elif nivel == "padrao":
            subs = PADRAO_PARA_SUBREGIAO.get(escopo, set())
            if len(subs) == 1:
                contagem[next(iter(subs))] += qtd
    return contagem


def metrica_h_r1_violacoes(
    rotinas: list[list[list[list[Exercicio]]]],
    config: ConfigComum,
) -> dict[str, float]:
    """% de rotinas que violam H-R1 por subregião.

    Aplica a regra do `H_R1_REGRAS`: subregião com ≥ min_slots slots na
    rotina exige ≥1 candidato em cada eixo. Slots contados via
    `_slots_de_subregiao_na_demanda` em todos os treinos da rotina.
    """
    # Slots totais por subregião (somando os treinos).
    slots_por_sub: Counter = Counter()
    for dems in config.demandas_por_treino:
        slots_por_sub.update(_slots_de_subregiao_na_demanda(dems))

    # Subregiões que ativam H-R1 (≥ min_slots).
    sub_ativas: list[str] = []
    for sub, regra in H_R1_REGRAS.items():
        if slots_por_sub.get(sub, 0) >= regra["min_slots"]:
            sub_ativas.append(sub)

    if not sub_ativas or not rotinas:
        return {}

    violacoes: dict[str, int] = {sub: 0 for sub in sub_ativas}
    for rotina in rotinas:
        exs = _todos_exercicios(rotina)
        for sub in sub_ativas:
            regra = H_R1_REGRAS[sub]
            for _eixo_nome, predicado in regra["eixos"]:
                if not any(predicado(e) for e in exs):
                    violacoes[sub] += 1
                    break  # 1 violação por (rotina, subregiao) basta

    return {sub: violacoes[sub] / len(rotinas) for sub in sub_ativas}


def metrica_ancoras_violacoes(
    rotinas: list[list[list[list[Exercicio]]]],
    config: ConfigComum,
) -> dict[tuple[str, str], float]:
    """% de rotinas que NÃO cumprem âncora obrigatória por (subregião, padrão).

    Toma como verdade as âncoras `obrigatoria=True` do
    `ANCORAS_POR_SUBREGIAO`. Só ativa quando a subregião tem ≥1 slot na
    rotina (via demanda subregião direta OU padrão 1:1).
    """
    slots_por_sub: Counter = Counter()
    for dems in config.demandas_por_treino:
        slots_por_sub.update(_slots_de_subregiao_na_demanda(dems))

    obrigatorias: list[tuple[str, str]] = []
    for sub, ancoras in ANCORAS_POR_SUBREGIAO.items():
        if slots_por_sub.get(sub, 0) < 1:
            continue
        for anc in ancoras:
            if anc.get("obrigatoria"):
                obrigatorias.append((sub, anc["padrao"]))

    if not obrigatorias or not rotinas:
        return {}

    violacoes: dict[tuple[str, str], int] = {p: 0 for p in obrigatorias}
    for rotina in rotinas:
        nomes_padrao = {e.padrao for e in _todos_exercicios(rotina)}
        for sub, padrao in obrigatorias:
            if padrao not in nomes_padrao:
                violacoes[(sub, padrao)] += 1

    return {p: violacoes[p] / len(rotinas) for p in obrigatorias}


def metrica_variedade_intra(
    rotinas: list[list[list[list[Exercicio]]]],
) -> int:
    """Número de rotinas distintas em N runs (assinatura canônica)."""
    return len({_assinatura_rotina(r) for r in rotinas})


def metrica_overlap_r1(
    rotinas: list[list[list[list[Exercicio]]]],
) -> tuple[float, bool]:
    """Overlap médio entre rotinas consecutivas — % slots iguais.

    Definição: para cada par (R_i, R_{i+1}), conta exercícios em comum
    (mesmo nome, qualquer treino) e divide por |R_i|. Agrega cross-iter
    (sum sobre pares / sum |R_i|). Reflete "quão repetitivo é gerar
    rotinas seguidas" — métrica também usada na Etapa 7 Fase 7.5 do
    refator antigo.

    Retorna (pct, aplicavel). aplicavel=False se n < 2 (sem par válido).
    """
    if len(rotinas) < 2:
        return (0.0, False)

    total_intersect = 0
    total_slots = 0
    for i in range(len(rotinas) - 1):
        nomes_a = Counter(e.nome for e in _todos_exercicios(rotinas[i]))
        nomes_b = Counter(e.nome for e in _todos_exercicios(rotinas[i + 1]))
        # Intersecção como multiset (min counts).
        intersect = sum((nomes_a & nomes_b).values())
        total_intersect += intersect
        total_slots += sum(nomes_a.values())

    if total_slots == 0:
        return (0.0, False)
    return (total_intersect / total_slots, True)


def metrica_cobertura_ha0_por_treino(
    rotinas: list[list[list[list[Exercicio]]]],
    config: ConfigComum,
) -> dict[tuple[int, str, str], float]:
    """% de rotinas que CUMPREM cobertura H-A0 por (treino, região, sub_obrig).

    Aplicável quando config tem demanda `("regiao", R, qtd)` com R em
    `ANCORAS_POR_REGIAO`. Para cada (treino, regiao, sub_obrig=True),
    conta % de rotinas onde existe ao menos 1 ex com `subregiao=sub_obrig`
    naquele treino.

    Motor CSP pós-H-A0: alvo 100% para todas (treino, regiao, sub_obrig).
    Motor antigo: distribuição natural do gerador greedy — referência pra
    quantificar o ganho do CSP.
    """
    from gerador_treino import ANCORAS_POR_REGIAO
    # Identifica (treino, regiao, sub_obrig) ativos pela config.
    ativos: list[tuple[int, str, str]] = []
    for t_idx, dems in enumerate(config.demandas_por_treino):
        for nivel, escopo, _qtd in dems:
            if nivel != "regiao" or escopo not in ANCORAS_POR_REGIAO:
                continue
            for ancora in ANCORAS_POR_REGIAO[escopo]:
                if ancora.get("obrigatoria"):
                    ativos.append((t_idx, escopo, ancora["subregiao"]))

    if not ativos or not rotinas:
        return {}

    coberturas: dict[tuple[int, str, str], int] = {k: 0 for k in ativos}
    for rotina in rotinas:
        for (t_idx, regiao, sub) in ativos:
            if t_idx >= len(rotina):
                continue
            ex_no_treino = [e for bloco in rotina[t_idx] for e in bloco]
            tem = any(e.subregiao == sub for e in ex_no_treino)
            if tem:
                coberturas[(t_idx, regiao, sub)] += 1

    return {k: coberturas[k] / len(rotinas) for k in ativos}


def metrica_degradacoes_ha0_media(
    runs_viaveis: list[RunResult],
) -> float:
    """Número médio de entradas H-A0 com `degraded=True` por rotina.

    0 = motor não degrada (pool suficiente, sem conflito de cardinalidade).
    >0 = motor degrada em algumas rotinas — útil pra estimar pressão em
    configs estreitas (ex: upper(1) com 3 obrigatórias).

    Só CSP. Antigo fica 0 (sem h_a0_aplicadas).
    """
    if not runs_viaveis:
        return 0.0
    total = sum(
        sum(1 for a in r.h_a0_aplicadas if a.get("degraded"))
        for r in runs_viaveis
    )
    return total / len(runs_viaveis)


def metrica_cycling_fairness(
    rotinas: list[list[list[list[Exercicio]]]],
    config: ConfigComum,
) -> dict[str, list[int]]:
    """Distribuição de cada padrão entre os N treinos da rotina, agregada.

    Retorna {padrao: [count_t1, count_t2, ...]}. Idealmente, padrões com
    N_p instâncias na rotina deveriam aparecer ~uniformemente entre os N
    treinos da rotina (excluindo padrões cuja demanda explicitamente
    força um treino só).

    Métrica relevante quando n_treinos > 1. Renderização visualiza
    diretamente; análise quantitativa fica pro humano.
    """
    n_treinos = config.n_treinos
    if n_treinos < 2 or not rotinas:
        return {}

    dist: dict[str, list[int]] = defaultdict(lambda: [0] * n_treinos)
    for rotina in rotinas:
        for t_idx, treino in enumerate(rotina):
            for bloco in treino:
                for ex in bloco:
                    dist[ex.padrao][t_idx] += 1
    return dict(dist)


# ---------------------------------------------------------------------------
# Agregação por motor
# ---------------------------------------------------------------------------


def agregar(motor: str, runs: list[RunResult],
            config: ConfigComum) -> AgregadoMotor:
    n = len(runs)
    viaveis = [r for r in runs if r.viavel and r.rotina is not None]
    n_viaveis = len(viaveis)

    if runs:
        elapsed = [r.elapsed_ms for r in runs]
        elapsed_medio = statistics.mean(elapsed)
        elapsed_p95 = _percentil(elapsed, 0.95)
    else:
        elapsed_medio = elapsed_p95 = 0.0

    rotinas = [r.rotina for r in viaveis]

    if rotinas:
        rotinas_distintas = metrica_variedade_intra(rotinas)
        overlap_pct, overlap_aplic = metrica_overlap_r1(rotinas)
        tier_por_sub = metrica_tier_por_subregiao(rotinas)
        h_r1 = metrica_h_r1_violacoes(rotinas, config)
        ancoras = metrica_ancoras_violacoes(rotinas, config)
        cycling = metrica_cycling_fairness(rotinas, config)
        cobertura_ha0 = metrica_cobertura_ha0_por_treino(rotinas, config)
        degrad_ha0 = metrica_degradacoes_ha0_media(viaveis)
    else:
        rotinas_distintas = 0
        overlap_pct = 0.0
        overlap_aplic = False
        tier_por_sub = {}
        h_r1 = {}
        ancoras = {}
        cycling = {}
        cobertura_ha0 = {}
        degrad_ha0 = 0.0

    return AgregadoMotor(
        motor=motor,
        n_runs=n,
        n_viaveis=n_viaveis,
        elapsed_ms_medio=elapsed_medio,
        elapsed_ms_p95=elapsed_p95,
        rotinas_distintas=rotinas_distintas,
        overlap_pct=overlap_pct,
        overlap_aplicavel=overlap_aplic,
        tier_por_subregiao=tier_por_sub,
        h_r1_violacoes=h_r1,
        ancoras_violacoes=ancoras,
        cycling_distribuicao=cycling,
        cobertura_ha0_por_treino=cobertura_ha0,
        degradacoes_ha0_media=degrad_ha0,
    )


def _percentil(valores: list[float], p: float) -> float:
    if not valores:
        return 0.0
    ord_v = sorted(valores)
    k = (len(ord_v) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return ord_v[int(k)]
    return ord_v[f] * (c - k) + ord_v[c] * (k - f)


# ---------------------------------------------------------------------------
# Renderização markdown
# ---------------------------------------------------------------------------


def _pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def _render_tier(tier_csp: dict[str, Counter],
                 tier_antigo: dict[str, Counter]) -> list[str]:
    subs_all = sorted(set(tier_csp.keys()) | set(tier_antigo.keys()))
    linhas = [
        "| Subregião | Motor | Principal | Intermediário | Acessório | Total |",
        "|---|---|---|---|---|---|",
    ]
    for sub in subs_all:
        for motor, dat in (("CSP", tier_csp.get(sub)),
                           ("Antigo", tier_antigo.get(sub))):
            if dat is None:
                continue
            total = sum(dat.values())
            if total == 0:
                continue
            p = dat.get("Principal", 0)
            i = dat.get("Intermediário", 0)
            a = dat.get("Acessório", 0)
            linhas.append(
                f"| {sub} | {motor} | {p} ({_pct(p/total)}) | "
                f"{i} ({_pct(i/total)}) | {a} ({_pct(a/total)}) | {total} |"
            )
    return linhas


def _render_h_r1(h_r1_csp: dict, h_r1_antigo: dict) -> list[str]:
    subs = sorted(set(h_r1_csp.keys()) | set(h_r1_antigo.keys()))
    if not subs:
        return ["_(nenhuma subregião ativa H-R1 — sem ≥ min_slots na rotina)_"]
    linhas = [
        "| Subregião | CSP (% rotinas com violação) | Antigo (% rotinas com violação) |",
        "|---|---|---|",
    ]
    for sub in subs:
        csp = h_r1_csp.get(sub)
        ant = h_r1_antigo.get(sub)
        linhas.append(
            f"| {sub} | "
            f"{_pct(csp) if csp is not None else '—'} | "
            f"{_pct(ant) if ant is not None else '—'} |"
        )
    return linhas


def _render_ancoras(anc_csp: dict, anc_antigo: dict) -> list[str]:
    pares = sorted(set(anc_csp.keys()) | set(anc_antigo.keys()))
    if not pares:
        return ["_(nenhuma âncora obrigatória ativa nesta config)_"]
    linhas = [
        "| Subregião | Padrão obrigatório | CSP (% rotinas sem padrão) | Antigo (% rotinas sem padrão) |",
        "|---|---|---|---|",
    ]
    for sub, padrao in pares:
        csp = anc_csp.get((sub, padrao))
        ant = anc_antigo.get((sub, padrao))
        linhas.append(
            f"| {sub} | {padrao} | "
            f"{_pct(csp) if csp is not None else '—'} | "
            f"{_pct(ant) if ant is not None else '—'} |"
        )
    return linhas


def _render_cobertura_ha0(
    cob_csp: dict[tuple[int, str, str], float],
    cob_antigo: dict[tuple[int, str, str], float],
    degrad_csp: float,
    degrad_antigo: float,
) -> list[str]:
    """Renderiza tabela H-A0: % rotinas COM cobertura por (treino, regiao, sub)
    + linha de degradações médias.
    """
    keys = sorted(set(cob_csp.keys()) | set(cob_antigo.keys()))
    if not keys:
        return [
            "_(config sem demanda nível região com âncoras declaradas — H-A0 não aplica)_"
        ]
    linhas = [
        "| Treino | Região | Subregião obrigatória | CSP (% rotinas COM cobertura) | Antigo (% rotinas COM cobertura) |",
        "|---|---|---|---|---|",
    ]
    for k in keys:
        t_idx, regiao, sub = k
        csp = cob_csp.get(k)
        ant = cob_antigo.get(k)
        linhas.append(
            f"| T{t_idx+1} | {regiao} | {sub} | "
            f"{_pct(csp) if csp is not None else '—'} | "
            f"{_pct(ant) if ant is not None else '—'} |"
        )
    linhas.append("")
    linhas.append(
        f"**Degradações médias H-A0 por rotina** — CSP: {degrad_csp:.2f} | "
        f"Antigo: {degrad_antigo:.2f} _(só CSP modela H-A0 — Antigo sempre 0)_"
    )
    return linhas


def _render_cycling(cyc_csp: dict, cyc_antigo: dict,
                    n_treinos: int) -> list[str]:
    if not cyc_csp and not cyc_antigo:
        return ["_(n_treinos < 2 — cycling fairness não aplicável)_"]

    padroes = sorted(set(cyc_csp.keys()) | set(cyc_antigo.keys()))
    header_cols = " | ".join(f"T{i+1}" for i in range(n_treinos))
    linhas = [
        f"| Padrão | Motor | {header_cols} | Total | % treino dominante |",
        "|---|---|" + "|".join(["---"] * n_treinos) + "|---|---|",
    ]
    for padrao in padroes:
        for motor, cyc in (("CSP", cyc_csp), ("Antigo", cyc_antigo)):
            dist = cyc.get(padrao)
            if not dist:
                continue
            total = sum(dist)
            if total == 0:
                continue
            dominante = max(dist) / total
            cols = " | ".join(str(c) for c in dist)
            linhas.append(
                f"| {padrao} | {motor} | {cols} | {total} | {_pct(dominante)} |"
            )
    return linhas


def _render_config_secao(config: ConfigComum,
                         perfil: PerfilAluno,
                         agr_csp: AgregadoMotor,
                         agr_antigo: AgregadoMotor) -> str:
    linhas = [f"## Config: {config.nome}", ""]
    linhas.append(f"**Demandas**: {config.descricao()}")
    linhas.append(f"**Treinos**: {config.n_treinos} | "
                  f"**tamanho_bloco**: {config.tamanho_bloco} | "
                  f"**evitar_agonistas**: {config.evitar_agonistas} | "
                  f"**relaxar_familia**: {config.relaxar_familia}")
    linhas.append(f"**Perfil**: {perfil.nome}")
    linhas.append("")

    # Sumário
    linhas.append("### Sumário")
    linhas.append("")
    linhas.append("| Métrica | CSP | Antigo |")
    linhas.append("|---|---|---|")
    linhas.append(f"| N runs | {agr_csp.n_runs} | {agr_antigo.n_runs} |")
    linhas.append(
        f"| Viáveis | {agr_csp.n_viaveis}/{agr_csp.n_runs} "
        f"({_pct(agr_csp.n_viaveis/max(agr_csp.n_runs,1))}) | "
        f"{agr_antigo.n_viaveis}/{agr_antigo.n_runs} "
        f"({_pct(agr_antigo.n_viaveis/max(agr_antigo.n_runs,1))}) |"
    )
    linhas.append(
        f"| Tempo médio (ms, pipeline) | "
        f"{agr_csp.elapsed_ms_medio:.1f} | "
        f"{agr_antigo.elapsed_ms_medio:.1f} |"
    )
    linhas.append(
        f"| Tempo p95 (ms) | "
        f"{agr_csp.elapsed_ms_p95:.1f} | "
        f"{agr_antigo.elapsed_ms_p95:.1f} |"
    )
    linhas.append(
        f"| Rotinas distintas (variedade INTRA) | "
        f"{agr_csp.rotinas_distintas}/{agr_csp.n_viaveis} | "
        f"{agr_antigo.rotinas_distintas}/{agr_antigo.n_viaveis} |"
    )
    if agr_csp.overlap_aplicavel and agr_antigo.overlap_aplicavel:
        linhas.append(
            f"| Overlap R-1 (% slots iguais entre consec.) | "
            f"{_pct(agr_csp.overlap_pct)} | "
            f"{_pct(agr_antigo.overlap_pct)} |"
        )
    else:
        linhas.append("| Overlap R-1 | _(n<2)_ | _(n<2)_ |")
    linhas.append("")

    # Tier por subregião
    linhas.append("### Distribuição de tier por subregião")
    linhas.append("")
    linhas.extend(_render_tier(agr_csp.tier_por_subregiao,
                               agr_antigo.tier_por_subregiao))
    linhas.append("")

    # H-R1
    linhas.append("### Cobertura H-R1 (% rotinas com violação por subregião)")
    linhas.append("")
    linhas.extend(_render_h_r1(agr_csp.h_r1_violacoes,
                               agr_antigo.h_r1_violacoes))
    linhas.append("")

    # Âncoras
    linhas.append("### Cobertura de âncoras obrigatórias (% rotinas sem o padrão)")
    linhas.append("")
    linhas.extend(_render_ancoras(agr_csp.ancoras_violacoes,
                                  agr_antigo.ancoras_violacoes))
    linhas.append("")

    # H-A0 cobertura per (treino, regiao, sub_obrig) — Micro-frente H-A0 (2026-05-25).
    linhas.append("### Cobertura H-A0 por (treino, região, subregião obrigatória)")
    linhas.append("")
    linhas.extend(_render_cobertura_ha0(
        agr_csp.cobertura_ha0_por_treino,
        agr_antigo.cobertura_ha0_por_treino,
        agr_csp.degradacoes_ha0_media,
        agr_antigo.degradacoes_ha0_media,
    ))
    linhas.append("")

    # Cycling
    linhas.append("### Distribuição entre treinos (cycling fairness)")
    linhas.append("")
    linhas.extend(_render_cycling(agr_csp.cycling_distribuicao,
                                  agr_antigo.cycling_distribuicao,
                                  config.n_treinos))
    linhas.append("")

    return "\n".join(linhas)


def renderizar_relatorio(
    *,
    n_runs: int,
    seed_inicial: int,
    perfis: list[PerfilAluno],
    resultados: list[tuple[PerfilAluno, ConfigComum, AgregadoMotor, AgregadoMotor]],
) -> str:
    cabec = []
    cabec.append("# Relatório Frente E.0 — Comparativo CSP × motor antigo")
    cabec.append("")
    cabec.append(f"**Data**: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    cabec.append(f"**N por config**: {n_runs}")
    cabec.append(f"**Seed inicial**: {seed_inicial}")
    cabec.append(f"**Perfis**: {len(perfis)}")
    cabec.append("")
    cabec.append("**Decisões fechadas no handoff**: visual + descartar "
                 "INFEASIBLE + tempo pipeline completo. Sem veredicto "
                 "automático: leitura visual decide aprovação pra Frente E.1.")
    cabec.append("")
    cabec.append("**Métricas reportadas**:")
    cabec.append("- Distribuição de tier por subregião")
    cabec.append("- Cobertura H-R1 (% violações por subregião com ≥2 slots)")
    cabec.append("- Cobertura âncoras obrigatórias (% rotinas sem padrão)")
    cabec.append("- **Cobertura H-A0** (% rotinas com subregião obrigatória "
                 "presente por treino, em demandas nível regiao — Micro-frente H-A0)")
    cabec.append("- Variedade INTRA-config (# distintas em N)")
    cabec.append("- Overlap R-1 (% slots iguais entre rotinas consecutivas)")
    cabec.append("- Cycling fairness (distribuição de padrão entre treinos)")
    cabec.append("- Tempo médio + p95 (pipeline completo)")
    cabec.append("- % inviabilidade (auxiliar)")
    cabec.append("")
    cabec.append("---")
    cabec.append("")

    secoes_por_perfil: dict[str, list[str]] = defaultdict(list)
    for perfil, config, agr_csp, agr_antigo in resultados:
        secoes_por_perfil[perfil.nome].append(
            _render_config_secao(config, perfil, agr_csp, agr_antigo)
        )

    perfis_render = []
    for perfil in perfis:
        secs = secoes_por_perfil.get(perfil.nome, [])
        if not secs:
            continue
        perfis_render.append(f"# Perfil: {perfil.nome}\n")
        perfis_render.append("\n---\n\n".join(secs))

    return "\n".join(cabec) + "\n\n---\n\n".join(perfis_render) + "\n"


# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------


def executar(
    *,
    n_runs: int,
    seed_inicial: int,
    matriz: bool,
    out_path: Optional[Path],
    quiet: bool,
) -> Path:
    banco = carregar_banco_ativo()
    configs = _configs_canonicas()
    perfis = _perfis(matriz)

    if not quiet:
        print(f"Banco: {len(banco)} exercícios ativos")
        print(f"N runs: {n_runs} | Configs: {len(configs)} | Perfis: {len(perfis)}")
        total_runs = n_runs * len(configs) * len(perfis) * 2
        print(f"Total de runs (CSP + antigo): {total_runs}")
        print("")

    resultados: list[tuple[PerfilAluno, ConfigComum, AgregadoMotor, AgregadoMotor]] = []

    for perfil in perfis:
        if not quiet:
            print(f"=== Perfil: {perfil.nome} ===")
        for config in configs:
            if not quiet:
                print(f"  -> {config.nome} ({config.descricao()})")
            runs_csp: list[RunResult] = []
            runs_antigo: list[RunResult] = []
            for i in range(n_runs):
                seed = seed_inicial + i
                runs_csp.append(rodar_csp(config, perfil, banco, seed))
                runs_antigo.append(rodar_antigo(config, perfil, banco, seed))
                if not quiet and (i + 1) % 25 == 0:
                    print(f"    {i+1}/{n_runs} runs...")
            agr_csp = agregar("csp", runs_csp, config)
            agr_antigo = agregar("antigo", runs_antigo, config)
            resultados.append((perfil, config, agr_csp, agr_antigo))
            if not quiet:
                print(f"     CSP: {agr_csp.n_viaveis}/{n_runs} viáveis | "
                      f"{agr_csp.elapsed_ms_medio:.0f}ms médio | "
                      f"{agr_csp.rotinas_distintas} distintas")
                print(f"     Ant: {agr_antigo.n_viaveis}/{n_runs} viáveis | "
                      f"{agr_antigo.elapsed_ms_medio:.0f}ms médio | "
                      f"{agr_antigo.rotinas_distintas} distintas")
        if not quiet:
            print("")

    if out_path is None:
        ts = datetime.now().strftime("%Y-%m-%d")
        out_path = ROOT / "docs" / "refatoracao" / "relatorios" / f"E0_{ts}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    md = renderizar_relatorio(
        n_runs=n_runs,
        seed_inicial=seed_inicial,
        perfis=perfis,
        resultados=resultados,
    )
    out_path.write_text(md, encoding="utf-8")
    if not quiet:
        print(f"[OK] Relatório gerado: {out_path}")
    return out_path


def main():
    parser = argparse.ArgumentParser(
        description="Harness comparativo Frente E.0 — CSP × motor antigo"
    )
    parser.add_argument("--n", type=int, default=100,
                        help="N de iterações por configuração (default: 100)")
    parser.add_argument("--seed", type=int, default=1000,
                        help="Seed inicial pras N iterações (default: 1000)")
    parser.add_argument("--matriz", action="store_true",
                        help="Roda matriz 2x2 de perfis (nivel × aderência)")
    parser.add_argument("--out", type=str, default=None,
                        help="Caminho do relatório (default: "
                             "docs/refatoracao/relatorios/E0_<data>.md)")
    parser.add_argument("--quiet", action="store_true",
                        help="Suprime progresso no stdout")
    args = parser.parse_args()

    out_path = Path(args.out) if args.out else None
    executar(
        n_runs=args.n,
        seed_inicial=args.seed,
        matriz=args.matriz,
        out_path=out_path,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    main()
