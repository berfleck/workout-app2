"""Testes de regressão de bloqueio inter-treino e detecção de demanda
incompleta. Portado do antigo `test_demanda_incompleta.py` (script ad-hoc
na raiz) pra suite pytest formal.

Cenário: banco filtrado pra conter só 4 peitos
("Crossover", "Crossover Sentado", "Crucifixo Halteres", "Apoio").
Geramos 2 treinos com demanda de 2 peitos cada — o 2º treino
necessariamente fica incompleto (só 1 peito disponível depois de
bloquear famílias do T1).

Modos cobertos: hierarquia × templates × estrito × relaxado = 4 cenários,
5 seeds cada = 20 casos por teste função.
"""
from __future__ import annotations

import random

import pytest

from gerador_treino import carregar_banco, gerar_multiplos_treinos


PEITOS_TESTE = {"Crossover", "Crossover Sentado", "Crucifixo Halteres", "Apoio"}
SEEDS = [42, 7, 100, 200, 999]


# Helpers --------------------------------------------------------------------


def _filtrar_banco(banco_completo):
    """Mantém todos os exercícios EXCETO peitos não-listados."""
    return [
        e for e in banco_completo
        if e.padrao not in ("empurrar_compostos", "empurrar_isolados")
        or e.nome in PEITOS_TESTE
    ]


def _coletar_nomes(sessao):
    return [
        ex.nome
        for bloco in sessao.blocos
        for ex in (bloco.ex1, bloco.ex2, bloco.ex3)
        if ex
    ]


def _rodar(banco, seed: int, modo: str, relaxar: bool):
    random.seed(seed)
    banco_filtrado = _filtrar_banco(banco)
    if modo == "hierarquia":
        cfg = {
            "demandas": [("subregiao", "peito", 2), ("subregiao", "core", 2)],
            "max_complexidade": 5,
            "tamanho_bloco": 2,
        }
    else:
        cfg = {
            "padroes": [
                "empurrar_compostos", "empurrar_isolados",
                "core_isometrico", "core_dinamico",
            ],
            "exercicios_por_padrao": {
                "empurrar_compostos": 1, "empurrar_isolados": 1,
                "core_isometrico": 1, "core_dinamico": 1,
            },
            "max_complexidade": 5,
            "tamanho_bloco": 2,
        }
    return gerar_multiplos_treinos(banco_filtrado, [cfg, cfg], relaxar_familia=relaxar)


# Modo estrito --------------------------------------------------------------


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("modo", ["hierarquia", "templates"])
def test_t2_incompleto_sem_relax_gera_aviso_e_nao_relaxados(banco, modo, seed):
    """Em modo estrito, T2 deve ficar incompleto (só 1 peito disponível
    após bloquear famílias de T1) e isso deve aparecer como aviso
    `incompleta`. `sessao.relaxados` deve ficar vazio."""
    sessoes = _rodar(banco, seed, modo, relaxar=False)
    if modo == "hierarquia":
        avisos_peito_t2 = [
            a for a in sessoes[1].avisos
            if a.get("tipo") == "incompleta"
            and a["nivel"] == "subregiao" and a["escopo"] == "peito"
        ]
    else:
        peito_pads = {"empurrar_compostos", "empurrar_isolados"}
        avisos_peito_t2 = [
            a for a in sessoes[1].avisos
            if a.get("tipo") == "incompleta"
            and a["nivel"] == "padrao" and a["escopo"] in peito_pads
        ]
    assert avisos_peito_t2, (
        f"T2 ({modo}, seed={seed}): esperado aviso 'incompleta' de peito; "
        f"avisos={sessoes[1].avisos}"
    )
    if modo == "hierarquia":
        av = avisos_peito_t2[0]
        assert av["qtd_obtida"] == 1
        assert av["faltam"] == 1
    else:
        total_obtido = sum(a["qtd_obtida"] for a in avisos_peito_t2)
        total_pedido = sum(a["qtd_pedida"] for a in avisos_peito_t2)
        assert total_obtido < total_pedido
    assert sessoes[1].relaxados == [], (
        f"sem relaxar, sessao.relaxados deveria ser []; got {sessoes[1].relaxados}"
    )


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("modo", ["hierarquia", "templates"])
def test_estrito_crossover_e_crossover_sentado_nao_coexistem_entre_treinos(
    banco, modo, seed,
):
    """Em modo estrito, Crossover (T1) e Crossover Sentado (T2) — ou
    vice-versa — não devem coexistir entre treinos: variacao_de iguais."""
    sessoes = _rodar(banco, seed, modo, relaxar=False)
    nomes_t1, nomes_t2 = _coletar_nomes(sessoes[0]), _coletar_nomes(sessoes[1])
    assert not ("Crossover" in nomes_t1 and "Crossover Sentado" in nomes_t2), (
        f"REGRESSÃO ({modo}, seed={seed}): {nomes_t1=} {nomes_t2=}"
    )
    assert not ("Crossover Sentado" in nomes_t1 and "Crossover" in nomes_t2), (
        f"REGRESSÃO ({modo}, seed={seed}): {nomes_t1=} {nomes_t2=}"
    )


# Modo relaxado -------------------------------------------------------------


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("modo", ["hierarquia", "templates"])
def test_relaxado_avisos_familia_repetida_consistente_com_relaxados(
    banco, modo, seed,
):
    """Em modo relaxado: ou T2 completa via flexibilização (avisos
    familia_repetida + sessao.relaxados) ou bate em limite intra-sessão
    (avisos incompleta). Em ambos os casos, número de avisos
    family_repetida deve casar com tamanho de relaxados."""
    sessoes = _rodar(banco, seed, modo, relaxar=True)
    repetidas = [a for a in sessoes[1].avisos if a.get("tipo") == "familia_repetida"]
    nomes_t2 = _coletar_nomes(sessoes[1])

    # Consistência básica: bool e tamanho casam
    assert bool(repetidas) == bool(sessoes[1].relaxados), (
        f"({modo}, seed={seed}): repetidas={bool(repetidas)} mas "
        f"relaxados={bool(sessoes[1].relaxados)}"
    )
    if repetidas:
        assert len(sessoes[1].relaxados) == len(repetidas), (
            f"({modo}, seed={seed}): {len(sessoes[1].relaxados)} relaxados "
            f"vs {len(repetidas)} avisos"
        )
        # Cada nome relaxado deve aparecer no T2
        for nome in sessoes[1].relaxados:
            assert nome in nomes_t2, (
                f"nome relaxado {nome!r} não aparece no T2 (nomes_t2={nomes_t2})"
            )
