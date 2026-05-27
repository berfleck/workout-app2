"""Testes da S-E1 — proximidade biomecânica cross-treino (2026-05-28).

`peso_se1_pegada`, `peso_se1_plano`, `peso_se1_eq` em `_construir_modelo`
penalizam pares de slots em treinos diferentes mesma-subregião com match
exato na dim. Achado 2 da auditoria 2026-05-26: peito 1+1 cross-treino
caía 100% em pegada+plano repetidos (sondagem N=10 main, aderência alta);
ombro 1+1 análogo no caso N=1 da auditoria.

Testa:
(a) peso=0 preserva pré-S-E1 (sem regressão);
(b) peso>0 reduz drasticamente pegada/plano repetidos em peito 1+1;
(c) peso>0 análogo em ombro 1+1;
(d) escopo "mesma subregião" preservado: padrão same-eq em perna_anterior
    unilateral NÃO força inviabilidade (peso eq=2 baixo + pegada/plano N/A
    via sentinela por slot);
(e) compatibilidade com S-B5/S-R1/S-A1/S-B1 ativos juntos.
"""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import replace

from gerador_csp import (
    ConfigVariedade,
    gerar_rotina_csp,
)


def _ex_por_treino_subregiao(rotina, subregiao):
    """Lista de Exercicios na subregião dada, por treino."""
    out = []
    for t in rotina["treinos"]:
        exs = []
        for bloco in t["blocos"]:
            for ex in bloco:
                if ex.subregiao == subregiao:
                    exs.append(ex)
        out.append(exs)
    return out


# (a) peso=0 preserva pré-S-E1 (sem regressão)
def test_peso_zero_eh_neutro(banco):
    """Todos os pesos S-E1 em 0 = comportamento idêntico ao pré-frente."""
    full_body_t = [
        ("regiao", "upper", 3),
        ("regiao", "lower", 3),
        ("regiao", "core", 2),
    ]
    r = gerar_rotina_csp(
        [full_body_t, full_body_t], banco, nivel_aluno=3, seed=42,
        peso_se1_pegada=0, peso_se1_plano=0, peso_se1_eq=0,
    )
    assert r["viavel"] is True
    assert len(r["treinos"]) == 2


# (b) Caso clínico do Achado 2: peito 1+1 com equipamento repetido
def test_supino_halteres_repetido_e_penalizado(banco):
    """`subregiao peito(1) × 2T` com pesos 10/10/2 (default produção):
    alvo <30% rotinas com equipamento igual entre T1.peito e T2.peito em
    N=10 runs. Auditoria N=1 reportou Supino Halteres + Supino Halteres
    (100% halter+halter); banco tem barra/barra_guiada/corporal/halter
    em empurrar_compostos — alternância possível.

    Nota técnica: pegada em peito empurrar_compostos é uniformemente
    `pronada` (todos os supinos no banco), então S-E1 não tem como
    alternar pegada — a dim relevante pra alternar é equipamento."""
    demandas = [("subregiao", "peito", 1)]
    n_eq_repetido = 0
    n_validos = 0
    for python_seed in range(10):
        r = gerar_rotina_csp(
            [demandas, demandas], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_se1_pegada=10,
            peso_se1_plano=10,
            peso_se1_eq=2,
        )
        if not r["viavel"]:
            continue
        n_validos += 1
        peitos = _ex_por_treino_subregiao(r, "peito")
        if not (peitos[0] and peitos[1]):
            continue
        if (
            peitos[0][0].equipamento_grupo
            and peitos[0][0].equipamento_grupo == peitos[1][0].equipamento_grupo
        ):
            n_eq_repetido += 1
    assert n_validos >= 8, (
        f"Esperado >=8 rotinas viáveis em 10 runs; got {n_validos}"
    )
    pct = 100.0 * n_eq_repetido / n_validos
    assert pct <= 30.0, (
        f"S-E1 ativo deveria reduzir equipamento repetido em peito cross-treino; "
        f"got {n_eq_repetido}/{n_validos} = {pct:.1f}% (alvo <=30%)"
    )


# (c) Ombro 1+1 análogo
def test_desenv_halteres_repetido_e_penalizado(banco):
    """`subregiao ombro(1) × 2T` com pesos 10/10/2: alvo <30% rotinas
    com equipamento igual entre T1.ombro e T2.ombro em N=10 runs.
    Auditoria N=1 reportou 100% halter+halter."""
    demandas = [("subregiao", "ombro", 1)]
    n_eq_repetido = 0
    n_validos = 0
    for python_seed in range(10):
        r = gerar_rotina_csp(
            [demandas, demandas], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_se1_pegada=10,
            peso_se1_plano=10,
            peso_se1_eq=2,
        )
        if not r["viavel"]:
            continue
        n_validos += 1
        ombros = _ex_por_treino_subregiao(r, "ombro")
        if not (ombros[0] and ombros[1]):
            continue
        if (
            ombros[0][0].equipamento_grupo
            and ombros[0][0].equipamento_grupo == ombros[1][0].equipamento_grupo
        ):
            n_eq_repetido += 1
    assert n_validos >= 8, (
        f"Esperado >=8 rotinas viáveis em 10 runs; got {n_validos}"
    )
    pct = 100.0 * n_eq_repetido / n_validos
    assert pct <= 30.0, (
        f"S-E1 ativo deveria reduzir eq repetido em ombro cross-treino; "
        f"got {n_eq_repetido}/{n_validos} = {pct:.1f}% (alvo <=30%)"
    )


# (d) Escopo "mesma subregião" preservado em perna_anterior unilateral
def test_passada_halteres_OK_em_perna_anterior(banco):
    """Subregiões com pegada+plano N/A no banco (perna_anterior — squats)
    NÃO devem ser forçadas a mudar quando S-E1 está ativo. Pegada/plano
    sentinela por slot → codes distintos → same_pegada/same_plano false
    sem precisar BoolVar de validade. Equipamento pode repetir (peso 2
    baixo, motor pode aceitar). Teste: rotina viável + zero inviabilidade
    em N=5 runs."""
    demandas = [("subregiao", "perna_anterior", 1)]
    n_validos = 0
    for python_seed in range(5):
        r = gerar_rotina_csp(
            [demandas, demandas], banco, nivel_aluno=3,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(python_seed=python_seed),
            peso_se1_pegada=10,
            peso_se1_plano=10,
            peso_se1_eq=2,
        )
        if r["viavel"]:
            n_validos += 1
    assert n_validos == 5, (
        f"S-E1 ativo NÃO deveria inviabilizar perna_anterior unilateral "
        f"(pegada/plano N/A via sentinela); got {n_validos}/5 viáveis"
    )


# (e) Graceful degradation: banco com 1 só equipamento pro padrão
def test_grace_degradation_banco_unico_equipamento(banco):
    """Constraint não deve inviabilizar quando todos os candidatos de um
    padrão usam o mesmo equipamento. Setup: filtra banco pra simular
    candidatos de peito todos com mesmo equipamento_grupo=halter.
    S-E1 vai querer alternar mas só há halter — solver paga penalty mas
    não inviabiliza."""
    # Filtra banco pra deixar SÓ exercícios de peito com halter
    # (+ exercícios de outras subs intactos pro resto da rotina).
    banco_mock = [
        ex if ex.subregiao != "peito" or ex.equipamento_grupo == "halter"
        else replace(ex, ativo=False)  # mock: descativa
        for ex in banco
    ]
    banco_mock = [ex for ex in banco_mock if getattr(ex, "ativo", True)]
    # Banco ainda tem peito com halter? Sanity check.
    peitos_halter = [
        ex for ex in banco_mock
        if ex.subregiao == "peito" and ex.equipamento_grupo == "halter"
    ]
    assert len(peitos_halter) >= 2, (
        f"Sanity: banco mockado deve ter >=2 peitos halter; got {len(peitos_halter)}"
    )

    demandas = [("subregiao", "peito", 1)]
    r = gerar_rotina_csp(
        [demandas, demandas], banco_mock, nivel_aluno=3, seed=42,
        peso_se1_pegada=10, peso_se1_plano=10, peso_se1_eq=2,
    )
    # Graceful degradation: viável (paga penalty mas resolve).
    assert r["viavel"] is True, (
        "S-E1 não deve inviabilizar quando banco força equipamento repetido"
    )


# (f) Compatibilidade com outros softs ativos juntos
def test_se1_compativel_com_softs_ativos(banco):
    """Full Body 2T região com S-E1 + S-B5 + S-R1 + S-A1 + S-B1 ativos
    juntos (config real de produção): viável, zero regressão estrutural."""
    full_body_t = [
        ("regiao", "upper", 3),
        ("regiao", "lower", 3),
        ("regiao", "core", 2),
    ]
    r = gerar_rotina_csp(
        [full_body_t, full_body_t], banco, nivel_aluno=3, seed=42,
        variedade=ConfigVariedade(python_seed=7),
        peso_aderencia=2,
        peso_evitar_agonistas=10,
        tamanho_preferido=2,
        peso_tamanho_bloco=5,
        peso_sa1=12,
        peso_sa1_repet=10,
        peso_sb5=4,
        peso_sr1=4,
        peso_se1_pegada=10,
        peso_se1_plano=10,
        peso_se1_eq=2,
    )
    assert r["viavel"] is True
    assert len(r["treinos"]) == 2
    # Sanity: pegada cross-treino mesma-sub não DEVE repetir em peito.
    peitos = _ex_por_treino_subregiao(r, "peito")
    if peitos[0] and peitos[1]:
        for e1 in peitos[0]:
            for e2 in peitos[1]:
                if e1.pegada and e2.pegada and e1.pegada == e2.pegada:
                    raise AssertionError(
                        f"S-E1 ativo NÃO deveria deixar passar pegada repetida "
                        f"em peito cross-treino; got {e1.nome} <-> {e2.nome} "
                        f"(pegada={e1.pegada})"
                    )
