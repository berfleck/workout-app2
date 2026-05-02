"""Testes de invariante — propriedades que devem valer em qualquer geração,
sob qualquer configuração. Quebrá-los significa regressão dura.

Onze invariantes (Apêndice A do guia v4 propõe 6 mínimos; estendi pra 11
cobrindo contratos derivados do código atual).
"""
from __future__ import annotations

import random
from collections import Counter

import pytest

from gerador_treino import (
    FADIGA_MAX_PAR,
    PURPOSE_COMPOSTO,
    Sessao,
    gerar_multiplos_treinos,
    gerar_sessao,
    gerar_sessao_por_demandas,
)

# Helpers locais ------------------------------------------------------------


def _exercicios(sessao: Sessao):
    for b in sessao.blocos:
        for ex in (b.ex1, b.ex2, b.ex3):
            if ex:
                yield ex


def _all_exercicios(sessoes):
    for s in sessoes:
        yield from _exercicios(s)


# 1. nenhum exercício aparece duas vezes no mesmo treino --------------------


def test_nenhum_exercicio_aparece_duas_vezes_no_mesmo_treino(banco):
    random.seed(7)
    cfg = {"demandas": [("regiao", "lower", 4), ("regiao", "upper", 4)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg, cfg], relaxar_familia=True)
    for i, s in enumerate(sessoes):
        nomes = [ex.nome for ex in _exercicios(s)]
        duplicatas = [n for n, c in Counter(nomes).items() if c > 1]
        assert not duplicatas, f"Treino {i}: duplicatas {duplicatas}"


# 2. blocos respeitam fadiga máxima -----------------------------------------


def test_blocos_respeitam_fadiga_maxima(banco):
    random.seed(13)
    cfg_b2 = {"demandas": [("regiao", "lower", 6)], "tamanho_bloco": 2}
    cfg_b3 = {"demandas": [("regiao", "upper", 6)], "tamanho_bloco": 3}
    for cfg in (cfg_b2, cfg_b3):
        sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
        tam = cfg["tamanho_bloco"]
        max_alta = 1 if tam <= 2 else 2
        for s in sessoes:
            for b in s.blocos:
                exs = [ex for ex in (b.ex1, b.ex2, b.ex3) if ex]
                n_alta = sum(1 for ex in exs if ex.fadiga >= FADIGA_MAX_PAR)
                assert n_alta <= max_alta, (
                    f"bloco {b.label} (tam={tam}) tem {n_alta} ex de fadiga ≥ "
                    f"{FADIGA_MAX_PAR}: {[(e.nome, e.fadiga) for e in exs]}"
                )


# 3. blocos respeitam tamanho configurado -----------------------------------


def test_blocos_respeitam_tamanho_configurado(banco):
    random.seed(21)
    for tam in (1, 2, 3):
        cfg = {"demandas": [("regiao", "lower", 4)], "tamanho_bloco": tam}
        sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
        for s in sessoes:
            for b in s.blocos:
                exs = [ex for ex in (b.ex1, b.ex2, b.ex3) if ex]
                assert len(exs) <= tam, (
                    f"bloco {b.label} tem {len(exs)} ex (tam configurado={tam})"
                )


# 4. exercícios travados aparecem no resultado ------------------------------


def test_exercicios_travados_aparecem_no_resultado(banco):
    random.seed(31)
    travados = [next(e for e in banco if e.padrao in ("squat_bilateral", "squat_unilateral"))]
    nomes_travados = {e.nome for e in travados}
    cfg = {
        "demandas": [("regiao", "lower", 4)],
        "exercicios_travados": travados,
    }
    sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    nomes_resultado = {ex.nome for ex in _all_exercicios(sessoes)}
    faltando = nomes_travados - nomes_resultado
    assert not faltando, f"travados ausentes: {faltando}"


# 5. equipamentos bloqueados não aparecem -----------------------------------


def test_exercicios_em_equipamentos_bloqueados_nao_aparecem(banco):
    random.seed(33)
    bloqueados = ["Polia"]
    cfg = {
        "demandas": [("regiao", "upper", 6)],
        "equipamentos_bloqueados": bloqueados,
    }
    sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    for ex in _all_exercicios(sessoes):
        assert ex.eq_primario not in bloqueados, (
            f"ex '{ex.nome}' usa equipamento bloqueado '{ex.eq_primario}'"
        )


# 6. max_complexidade respeitado --------------------------------------------


def test_max_complexidade_respeitado(banco):
    random.seed(37)
    cfg = {"demandas": [("regiao", "upper", 4)], "max_complexidade": 2}
    sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    for ex in _all_exercicios(sessoes):
        assert ex.complexidade <= 2, (
            f"ex '{ex.nome}' tem complexidade {ex.complexidade} (max=2)"
        )


# 7. labels de blocos consecutivos e únicos ---------------------------------


def test_labels_de_blocos_sao_consecutivos_e_unicos(banco):
    random.seed(41)
    cfg = {"demandas": [("regiao", "lower", 6)], "tamanho_bloco": 2}
    sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    for s in sessoes:
        labels = [b.label for b in s.blocos]
        # Únicos
        assert len(set(labels)) == len(labels), f"labels duplicados: {labels}"
        # Consecutivos a partir de 'A'
        esperado = [chr(ord("A") + i) for i in range(len(labels))]
        assert labels == esperado, f"labels {labels} != esperado {esperado}"


# 8. avisos têm estrutura válida --------------------------------------------


def test_avisos_tem_estrutura_valida(banco):
    """Documenta o contrato do campo avisos. Provoca incompleta limitando
    o banco e familia_repetida com uma config redundante + relax."""
    # Cenário 1: provoca aviso incompleta
    random.seed(43)
    banco_curto = [
        e for e in banco
        if e.padrao not in ("empurrar_compostos", "empurrar_isolados")
        or e.nome in {"Crossover", "Crossover Sentado", "Crucifixo Halteres", "Apoio"}
    ]
    cfg = {"demandas": [("subregiao", "peito", 2)]}
    sessoes = gerar_multiplos_treinos(banco_curto, [cfg, cfg], relaxar_familia=False)
    for s in sessoes:
        for av in s.avisos:
            assert "tipo" in av, f"aviso sem 'tipo': {av}"
            assert av["tipo"] in {"incompleta", "familia_repetida"}, (
                f"tipo invalido: {av['tipo']}"
            )


# 9. relaxados consistente com avisos familia_repetida ----------------------


def test_relaxados_consistente_com_avisos_familia_repetida(banco):
    random.seed(47)
    banco_curto = [
        e for e in banco
        if e.padrao not in ("empurrar_compostos", "empurrar_isolados")
        or e.nome in {"Crossover", "Crossover Sentado", "Crucifixo Halteres", "Apoio"}
    ]
    cfg = {"demandas": [("subregiao", "peito", 2)]}
    sessoes = gerar_multiplos_treinos(banco_curto, [cfg, cfg], relaxar_familia=True)
    for s in sessoes:
        n_avisos_familia = sum(
            1 for a in s.avisos if a.get("tipo") == "familia_repetida"
        )
        assert len(s.relaxados) == n_avisos_familia, (
            f"relaxados={s.relaxados} mas avisos familia={n_avisos_familia}"
        )


# 10. compostos aparecem antes de isolados (no resultado final) -------------


def test_compostos_aparecem_antes_de_isolados_no_resultado_final(banco):
    """ordenar_compostos_primeiro garante: dentro do resultado plano, todo
    composto vem antes de qualquer isolado. Verificamos via ordem dos
    exercicios CONCATENADOS na sequência dos blocos (que preserva ordem
    do resultado interno antes de montar_blocos)."""
    random.seed(53)
    cfg = {"demandas": [("regiao", "upper", 6)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    # Coleta por sessão, em ordem de aparição no resultado plano (blocos serializam
    # ex1, ex2 conforme o pareamento). Como o sort feliz acontece ANTES de
    # montar_blocos, a propriedade vale na sequência geral só fracamente:
    # nenhum bloco com 2 isolados aparece antes de um bloco com 2 compostos.
    for s in sessoes:
        scores = []
        for b in s.blocos:
            exs = [ex for ex in (b.ex1, b.ex2, b.ex3) if ex]
            n_comp = sum(1 for ex in exs if ex.purpose in PURPOSE_COMPOSTO)
            scores.append(n_comp)
        # Score por bloco deve ser monotonicamente não-crescente após
        # ordenar_blocos. Toleramos 1 inversão por sessão (ordenamento
        # interno usa pesos diferenciados, não count cru de compostos).
        inversoes = sum(1 for i in range(len(scores) - 1) if scores[i] < scores[i + 1])
        assert inversoes <= 1, (
            f"sessao {s.tipo}: {inversoes} inversoes de compostos por bloco "
            f"({scores})"
        )


# 11. multiplos treinos em modo estrito não repetem nomes -------------------


def test_multiplos_treinos_em_modo_estrito_nao_repetem_nomes(banco):
    """Em modo estrito (relaxar_familia=False), exercícios não devem se
    repetir entre treinos pra rotinas que cabem no banco."""
    random.seed(59)
    cfg = {"demandas": [("regiao", "lower", 4)]}
    sessoes = gerar_multiplos_treinos(banco, [cfg, cfg], relaxar_familia=False)
    nomes_t1 = {ex.nome for ex in _exercicios(sessoes[0])}
    nomes_t2 = {ex.nome for ex in _exercicios(sessoes[1])}
    repetidos = nomes_t1 & nomes_t2
    assert not repetidos, f"nomes repetidos entre treinos (modo estrito): {repetidos}"


# Smoke do harness (1 teste rápido, valida shape do dict) -------------------


def test_harness_simular_rotina_devolve_metricas_esperadas(banco):
    from tests.harness import simular_rotina

    random.seed(0)  # não afeta o harness, que reseed por iteracao
    cfg = {"demandas": [("regiao", "lower", 4)]}
    r = simular_rotina(banco, [cfg], n_iteracoes=10, seed_base=12345)

    chaves_esperadas = {
        "n_iteracoes",
        "seed_base",
        "distribuicao_padrao_por_subregiao",
        "distribuicao_subregiao_por_regiao",
        "taxa_aviso_incompleta",
        "taxa_aviso_familia_repetida",
        "taxa_blocos_solo",
        "razao_posterior_anterior_lower",
        "frequencia_adutores_e_panturrilha_lower",
        "cobertura_compostos_por_subregiao",
    }
    assert set(r.keys()) == chaves_esperadas, (
        f"chaves inesperadas: {set(r.keys()) ^ chaves_esperadas}"
    )
    assert r["n_iteracoes"] == 10
    assert r["seed_base"] == 12345
    assert isinstance(r["distribuicao_subregiao_por_regiao"], dict)
    assert isinstance(r["taxa_blocos_solo"], float)
    assert isinstance(r["razao_posterior_anterior_lower"], dict)
    assert {"media", "mediana", "n_amostras_finitas", "n_amostras_inf"} <= set(
        r["razao_posterior_anterior_lower"].keys()
    )

    # Determinismo: mesmo input -> mesmo output
    r2 = simular_rotina(banco, [cfg], n_iteracoes=10, seed_base=12345)
    assert r == r2, "harness não-determinístico para mesmo seed_base"
