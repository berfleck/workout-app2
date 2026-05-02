"""Harness de simulação em massa para o gerador de treinos.

Roda N iterações independentes (seeds diferentes) de uma config e
agrega métricas que servem pra validar mudanças nas Etapas 2/3 do
guia de refatoração.

Determinismo: para o mesmo `(config, n_iteracoes, seed_base)` sempre
devolve o mesmo dict de métricas. Cada iteração usa seed `seed_base + i`.
"""
from __future__ import annotations

import random
import statistics
from collections import defaultdict
from typing import Any

from gerador_treino import (
    PADRAO_PARA_SUBREGIAO,
    SUBREGIAO_PARA_REGIAO,
    Sessao,
    _eh_composto,
    gerar_multiplos_treinos,
)

# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------

ConfigEntrada = dict | list[dict]


# ---------------------------------------------------------------------------
# Helpers de extração por sessão
# ---------------------------------------------------------------------------

def _exercicios_da_sessao(sessao: Sessao):
    for bloco in sessao.blocos:
        for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
            if ex:
                yield ex


def _exercicios_da_rotina(sessoes: list[Sessao]):
    for s in sessoes:
        yield from _exercicios_da_sessao(s)


def _avisos_da_rotina(sessoes: list[Sessao]) -> list[dict]:
    out: list[dict] = []
    for s in sessoes:
        out.extend(s.avisos)
    return out


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def simular_rotina(
    banco,
    config: ConfigEntrada,
    n_iteracoes: int = 100,
    seed_base: int = 1000,
    relaxar_familia: bool = True,
) -> dict[str, Any]:
    """Gera N rotinas independentes e agrega métricas.

    Args:
        banco: lista de Exercicio (use a fixture `banco` do conftest).
        config: dict (config única, vira rotina de 1 treino) ou
                list[dict] (rotina multi-treino).
        n_iteracoes: número de rotinas independentes a gerar.
        seed_base: seed da iteração 0; iter i usa seed_base+i.
        relaxar_familia: passado direto pra gerar_multiplos_treinos.

    Returns:
        dict com 8 métricas (ver docstring de cada helper).
    """
    configs = [config] if isinstance(config, dict) else list(config)

    # Acumuladores
    dist_padrao_sub: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    dist_sub_reg: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    n_iter_com_aviso_incompleta = 0
    n_iter_com_aviso_familia_repetida = 0
    n_blocos_total = 0
    n_blocos_solo = 0
    razao_post_ant: list[float] = []
    n_iter_com_adutores_e_panturrilha = 0
    cobertura_compostos_por_sub: dict[str, int] = defaultdict(int)
    todas_subs_vistas: set[str] = set()

    for i in range(n_iteracoes):
        random.seed(seed_base + i)
        sessoes = gerar_multiplos_treinos(banco, configs, relaxar_familia=relaxar_familia)

        # Por iteração: contar exercícios por (sub, padrao) e (reg, sub)
        cnt_padrao_sub: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        cnt_sub_reg: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        compostos_por_sub_iter: set[str] = set()

        for ex in _exercicios_da_rotina(sessoes):
            sub = ex.subregiao or PADRAO_PARA_SUBREGIAO.get(ex.padrao, "")
            reg = ex.regiao or SUBREGIAO_PARA_REGIAO.get(sub, "")
            cnt_padrao_sub[sub][ex.padrao] += 1
            cnt_sub_reg[reg][sub] += 1
            todas_subs_vistas.add(sub)
            if _eh_composto(ex):
                compostos_por_sub_iter.add(sub)

        # Distribui contagens para os acumuladores (preenchendo zeros pra subs já vistas)
        for sub, mp in cnt_padrao_sub.items():
            for pad, n in mp.items():
                dist_padrao_sub[sub][pad].append(n)
        for reg, mp in cnt_sub_reg.items():
            for sub, n in mp.items():
                dist_sub_reg[reg][sub].append(n)

        # Cobertura compostos por subregião
        for sub in compostos_por_sub_iter:
            cobertura_compostos_por_sub[sub] += 1

        # Avisos
        avisos = _avisos_da_rotina(sessoes)
        if any(a.get("tipo") == "incompleta" for a in avisos):
            n_iter_com_aviso_incompleta += 1
        if any(a.get("tipo") == "familia_repetida" for a in avisos):
            n_iter_com_aviso_familia_repetida += 1

        # Blocos solo
        for s in sessoes:
            for b in s.blocos:
                n_blocos_total += 1
                slots_preenchidos = sum(1 for ex in (b.ex1, b.ex2, b.ex3) if ex)
                if slots_preenchidos == 1:
                    n_blocos_solo += 1

        # Razão posterior/anterior em lower
        n_post = sum(cnt_sub_reg["lower"].get(s, 0) for s in ("perna_posterior",))
        n_ant = sum(cnt_sub_reg["lower"].get(s, 0) for s in ("perna_anterior",))
        if n_ant > 0:
            razao_post_ant.append(n_post / n_ant)
        elif n_post > 0:
            razao_post_ant.append(float("inf"))

        # Adutores e panturrilha co-presentes
        if cnt_sub_reg["lower"].get("adutores", 0) >= 1 and cnt_sub_reg["lower"].get("panturrilha", 0) >= 1:
            n_iter_com_adutores_e_panturrilha += 1

    # Substituir defaultdicts por dicts comuns pra serialização limpa
    dist_padrao_sub_out = {sub: dict(mp) for sub, mp in dist_padrao_sub.items()}
    dist_sub_reg_out = {reg: dict(mp) for reg, mp in dist_sub_reg.items()}

    razao_finita = [r for r in razao_post_ant if r != float("inf")]
    razao_metric = {
        "media": statistics.fmean(razao_finita) if razao_finita else None,
        "mediana": statistics.median(razao_finita) if razao_finita else None,
        "n_amostras_finitas": len(razao_finita),
        "n_amostras_inf": sum(1 for r in razao_post_ant if r == float("inf")),
    }

    cobertura_compostos_pct = {
        sub: cobertura_compostos_por_sub.get(sub, 0) / n_iteracoes
        for sub in todas_subs_vistas
    }

    return {
        "n_iteracoes": n_iteracoes,
        "seed_base": seed_base,
        "distribuicao_padrao_por_subregiao": dist_padrao_sub_out,
        "distribuicao_subregiao_por_regiao": dist_sub_reg_out,
        "taxa_aviso_incompleta": n_iter_com_aviso_incompleta / n_iteracoes,
        "taxa_aviso_familia_repetida": n_iter_com_aviso_familia_repetida / n_iteracoes,
        "taxa_blocos_solo": (n_blocos_solo / n_blocos_total) if n_blocos_total else 0.0,
        "razao_posterior_anterior_lower": razao_metric,
        "frequencia_adutores_e_panturrilha_lower": n_iter_com_adutores_e_panturrilha / n_iteracoes,
        "cobertura_compostos_por_subregiao": cobertura_compostos_pct,
    }
