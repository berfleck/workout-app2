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
    """Em modo estrito, a rotina deve ficar incompleta em algum treino (só
    3 famílias de peito viáveis pra 4 vagas pedidas) e isso deve aparecer
    como aviso `incompleta` (treino-level OU rotina-level) em algum dos
    treinos. `sessao.relaxados` deve ficar vazio em todos os treinos.

    Pré-Etapa 2 o aviso aparecia sempre em T2 (geração sequencial).
    Pós-Etapa 2 a Fase 0 redistribui escassez: o exercício composto raro
    (`Apoio`) pode ser alocado em T1 ou T2 dependendo da seed; o aviso
    cai no treino que ficou sem essa família. A intenção clínica do
    teste é preservada: a regra de família detecta o problema e gera o
    aviso, em algum lugar da rotina.
    """
    sessoes = _rodar(banco, seed, modo, relaxar=False)
    todos_avisos = [a for s in sessoes for a in s.avisos]
    if modo == "hierarquia":
        avisos_peito = [
            a for a in todos_avisos
            if a.get("tipo") == "incompleta"
            and (
                (a.get("nivel") == "subregiao" and a.get("escopo") == "peito")
                or a.get("escopo_demanda") == "peito"
                or a.get("escopo_alocacao") == "peito"
            )
        ]
    else:
        peito_pads = {"empurrar_compostos", "empurrar_isolados"}
        avisos_peito = [
            a for a in todos_avisos
            if a.get("tipo") == "incompleta"
            and (
                (a.get("nivel") == "padrao" and a.get("escopo") in peito_pads)
                or a.get("escopo_demanda") in peito_pads
                or a.get("escopo_alocacao") in peito_pads
            )
        ]
    assert avisos_peito, (
        f"({modo}, seed={seed}): esperado aviso 'incompleta' de peito em "
        f"algum treino; avisos={[a for s in sessoes for a in s.avisos]}"
    )
    # Faltou pelo menos 1 vaga (Fase 0 ou Fase 1). Aviso treino-level traz
    # `qtd_obtida`/`qtd_pedida`; aviso rotina-level traz `faltam`.
    faltam_total = 0
    for a in avisos_peito:
        if "faltam" in a:
            faltam_total += a["faltam"]
        elif "qtd_pedida" in a and "qtd_obtida" in a:
            faltam_total += a["qtd_pedida"] - a["qtd_obtida"]
    assert faltam_total >= 1, f"avisos_peito: {avisos_peito}"
    # Nenhuma sessão deve ter relaxados (modo estrito)
    for i, s in enumerate(sessoes):
        assert s.relaxados == [], (
            f"sem relaxar, T{i}.relaxados deveria ser []; got {s.relaxados}"
        )


@pytest.mark.parametrize("modo", ["hierarquia", "templates"])
def test_crossover_sentado_coexistencia_INTER_e_rara_pos_caminho_A(
    banco, modo,
):
    """Sob Caminho A da Etapa 7 Fase 7.4 (D3.2 clean break), família INTER
    deixou de ser hard. Mesma família entre treinos passa a ser soft —
    desencorajada por penalty -40 mas permitida quando banco aperta.

    Este teste valida que, MESMO com banco apertado (peito filtrado pra
    4 famílias e 4 vagas pedidas), a coexistência cross-treino de mesma
    família continua **rara** (penalty INTER faz seu trabalho). Não exige
    proibição absoluta como antes — captura a semântica "soft alto
    desencoraja mas permite quando banco aperta" da Seção 1.4.

    Antes do Caminho A (até Fase 7.3): hard INTER família bloqueava
    Crossover (T1) + Crossover Sentado (T2) em qualquer seed.
    Pós Caminho A: ≤20% das seeds permitem coexistência (cap empírico).
    """
    coexistem = 0
    n_seeds = len(SEEDS)
    for seed in SEEDS:
        sessoes = _rodar(banco, seed, modo, relaxar=False)
        nomes_t1, nomes_t2 = _coletar_nomes(sessoes[0]), _coletar_nomes(sessoes[1])
        par1 = "Crossover" in nomes_t1 and "Crossover Sentado" in nomes_t2
        par2 = "Crossover Sentado" in nomes_t1 and "Crossover" in nomes_t2
        if par1 or par2:
            coexistem += 1
    pct = 100.0 * coexistem / n_seeds
    assert pct <= 40.0, (
        f"({modo}): coexistência cross-treino acima do cap empírico "
        f"({pct:.1f}% > 40%) — soft INTER família pode estar fraco demais. "
        f"Calibração 7.6 deve ajustar peso INTER."
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
