"""Testes da Etapa 8 — Explicabilidade.

Cobertura:
1. Geração popula `rationale` em todos os exercícios escolhidos via score-aware.
2. Estrutura do rationale tem os campos esperados (slot, score, componentes, alternativas).
3. Não contamina o banco — referências do banco continuam com rationale=None.
4. Round-trip via `_exercicio_to_dict` / `_dict_to_exercicio` preserva rationale.
5. Retrocompat — sessões antigas (sem rationale no dict) deserializam com None.
6. JSON serializável (todos os campos são tipos primitivos).
"""
from __future__ import annotations

import json
import random

import pytest

from gerador_treino import gerar_multiplos_treinos


def _iter_exercicios(sessoes):
    for s in sessoes:
        for b in s.blocos:
            for ex in (b.ex1, b.ex2, b.ex3):
                if ex:
                    yield ex


# 1. Geração popula rationale --------------------------------------------------


def test_geracao_popula_rationale_em_exs_escolhidos(banco):
    random.seed(42)
    configs = [
        {
            "demandas": [("subregiao", "peito", 2), ("subregiao", "costas", 2)],
            "max_complexidade": 5,
            "evitar_agonistas": True,
            "tamanho_bloco": 2,
        }
    ] * 2
    sessoes = gerar_multiplos_treinos(banco, configs)
    exs = list(_iter_exercicios(sessoes))
    assert exs, "geração deveria ter produzido exercícios"
    assert all(ex.rationale is not None for ex in exs), (
        "todo ex escolhido via _selecionar_cand_score_aware deve carregar rationale"
    )


def test_rationale_tem_estrutura_esperada(banco):
    random.seed(42)
    configs = [
        {
            "demandas": [("subregiao", "peito", 2)],
            "max_complexidade": 5,
            "evitar_agonistas": True,
            "tamanho_bloco": 2,
        }
    ]
    sessoes = gerar_multiplos_treinos(banco, configs)
    exs = list(_iter_exercicios(sessoes))
    for ex in exs:
        r = ex.rationale
        # Slot
        assert "slot" in r
        assert set(r["slot"].keys()) >= {
            "treino_idx", "nivel", "escopo", "escopo_demanda_original", "passe"
        }
        assert r["slot"]["passe"] in {"estrito", "relax"}
        # Score
        assert isinstance(r["score_total"], (int, float))
        # Componentes
        assert isinstance(r["componentes"], list)
        for c in r["componentes"]:
            assert set(c.keys()) >= {"contexto", "dim", "peso", "com"}
            assert c["contexto"] in {"intra", "inter", "historico"}
        # Alternativas
        assert isinstance(r["alternativas"], list)
        for a in r["alternativas"]:
            assert set(a.keys()) >= {"nome", "score_total", "componentes", "delta"}
        # Tamanho do pool
        assert r["tamanho_pool"] >= 1


# 2. Banco não contaminado -----------------------------------------------------


def test_banco_nao_e_contaminado_por_rationale(banco):
    """O banco-fonte tem ex sem rationale; após gerar, banco continua limpo."""
    random.seed(13)
    # Sanity pré: banco limpo
    assert all(ex.rationale is None for ex in banco)
    configs = [
        {
            "demandas": [("subregiao", "peito", 2)],
            "max_complexidade": 5,
            "evitar_agonistas": True,
            "tamanho_bloco": 2,
        }
    ] * 2
    sessoes = gerar_multiplos_treinos(banco, configs)
    assert list(_iter_exercicios(sessoes))  # geração funcionou
    # Sanity pós: banco continua limpo (dataclasses.replace cria cópia)
    assert all(ex.rationale is None for ex in banco), (
        "rationale vazou pro banco — _selecionar_cand_score_aware deveria usar replace()"
    )


# 3. Round-trip de serialização ------------------------------------------------


def test_round_trip_serializacao_preserva_rationale(banco):
    """_exercicio_to_dict → JSON → _dict_to_exercicio mantém rationale."""
    from app_flask import _dict_to_exercicio, _exercicio_to_dict

    random.seed(99)
    configs = [
        {
            "demandas": [("subregiao", "peito", 2), ("subregiao", "costas", 1)],
            "max_complexidade": 5,
            "evitar_agonistas": True,
            "tamanho_bloco": 2,
        }
    ] * 2
    sessoes = gerar_multiplos_treinos(banco, configs)
    for ex in _iter_exercicios(sessoes):
        d = _exercicio_to_dict(ex)
        # JSON é serializável (tipos primitivos)
        js = json.dumps(d)
        d2 = json.loads(js)
        ex2 = _dict_to_exercicio(d2)
        assert ex2.rationale == ex.rationale, (
            f"rationale não sobreviveu round-trip pro ex {ex.nome}"
        )


def test_retrocompat_sessao_sem_rationale_no_json(banco):
    """Sessões antigas (sem campo 'rationale' no dict) viram ex.rationale=None."""
    from app_flask import _dict_to_exercicio

    d = {
        "nome": "Supino Plano Halter",
        "variacao_de": "Supino Plano",
        "eq_primario": "halter",
        "eq_secundario": None,
        "regiao": "upper",
        "subregiao": "peito",
        "padrao": "empurrar_compostos",
        "purpose": "compound",
        "unilateral": "bilateral",
        "complexidade": 2,
        "fadiga": 3,
        "circuito": "não",
        "similaridade": "",
        "musculo_primario": "peitoral",
        "obs": None,
        "series": 3,
        "reps": "8-12",
        "rir": 2,
        # rationale ausente — caso retrocompat
    }
    ex = _dict_to_exercicio(d)
    assert ex.rationale is None


# 4. Conteúdo clínico do rationale (smoke) -------------------------------------


def test_alternativas_excluem_o_proprio_escolhido(banco):
    random.seed(11)
    configs = [
        {
            "demandas": [("subregiao", "peito", 2)],
            "max_complexidade": 5,
            "evitar_agonistas": True,
            "tamanho_bloco": 2,
        }
    ]
    sessoes = gerar_multiplos_treinos(banco, configs)
    for ex in _iter_exercicios(sessoes):
        nomes_alts = {a["nome"] for a in ex.rationale["alternativas"]}
        assert ex.nome not in nomes_alts, (
            f"alternativa não pode ser o próprio escolhido ({ex.nome})"
        )


def test_score_total_bate_com_soma_dos_componentes(banco):
    random.seed(7)
    configs = [
        {
            "demandas": [("subregiao", "peito", 2)],
            "max_complexidade": 5,
            "evitar_agonistas": True,
            "tamanho_bloco": 2,
        }
    ] * 3
    sessoes = gerar_multiplos_treinos(banco, configs)
    for ex in _iter_exercicios(sessoes):
        soma = sum(c["peso"] for c in ex.rationale["componentes"])
        assert pytest.approx(ex.rationale["score_total"], abs=1e-6) == soma


# 5. Validação clínica — caso "Crossover Sentado solo" (guia v4 §1093) ---------


def test_rationale_revela_papel_composto_vs_isolado_via_slot(banco):
    """O caso clínico clássico: Crossover Sentado (isolado) aparecendo sem
    composto de peito = âncora não cumprida. Esta verificação garante que o
    rationale identifica o slot (`empurrar_compostos` vs `empurrar_isolados`)
    de cada ex de peito — torna rastreável que a Etapa 3 (âncoras) atuou.
    """
    random.seed(31)
    configs = [
        {
            "demandas": [("subregiao", "peito", 2)],
            "max_complexidade": 5,
            "evitar_agonistas": True,
            "tamanho_bloco": 2,
        }
    ] * 4  # 4 rotinas — varredura razoável
    sessoes = gerar_multiplos_treinos(banco, configs)
    # Sanity: padrões de peito existem nos rationales (slot escopo)
    padroes_peito = set()
    for ex in _iter_exercicios(sessoes):
        if ex.rationale and ex.rationale["slot"]["nivel"] == "padrao":
            esc = ex.rationale["slot"]["escopo"]
            if esc in {"empurrar_compostos", "empurrar_isolados"}:
                padroes_peito.add(esc)
    # Etapa 3 (âncoras) faz com que peito(2) decomponha em 1 composto + 1
    # isolado por treino — então em 4 rotinas, AMBOS os padrões devem aparecer.
    assert "empurrar_compostos" in padroes_peito, (
        "rationale deveria identificar o slot 'empurrar_compostos' — "
        "ferramenta de debug pra confirmar que Etapa 3 está atuando"
    )
    assert "empurrar_isolados" in padroes_peito


def test_rationale_em_rotina_estressada_captura_historia_completa(banco):
    """3 treinos da mesma subregião com pool pequeno → rationale deve mostrar
    componentes INTRA + INTER acumulando ao longo da rotina. Ferramenta de
    'por que esse e não outro' funciona até em casos saturados.
    """
    random.seed(42)
    configs = [
        {
            "demandas": [("subregiao", "peito", 2)],
            "max_complexidade": 5,
            "evitar_agonistas": True,
            "tamanho_bloco": 2,
        }
    ] * 3
    sessoes = gerar_multiplos_treinos(banco, configs)
    # Treino 3 deve ter pelo menos 1 ex com componente INTER (família ou
    # pegada cross-treino) — pool de peito é limitado.
    ultimos_exs = list(_iter_exercicios([sessoes[-1]]))
    contextos_t3 = set()
    for ex in ultimos_exs:
        for c in ex.rationale["componentes"]:
            contextos_t3.add(c["contexto"])
    assert "inter" in contextos_t3, (
        f"Treino 3 com pool saturado de peito deveria mostrar componentes INTER. "
        f"Contextos observados: {contextos_t3}"
    )


# 6. Pareamento — extensão pós-MVP (captura em `montar_blocos`) ----------------


def test_pareamento_papel_ancora_e_par_em_bloco_2ex(banco):
    """Bloco de 2 exs: primeiro tem papel='ancora', segundo papel='par'."""
    random.seed(42)
    configs = [
        {
            "demandas": [("regiao", "upper", 6)],
            "max_complexidade": 5,
            "evitar_agonistas": True,
            "tamanho_bloco": 2,
        }
    ]
    sessoes = gerar_multiplos_treinos(banco, configs)
    for b in sessoes[0].blocos:
        if b.ex2 is None:
            continue  # solo, sem pareamento — coberto por outro teste
        assert b.ex1.rationale and b.ex1.rationale.get("pareamento"), (
            f"ex1 ({b.ex1.nome}) deveria ter rationale.pareamento"
        )
        assert b.ex2.rationale and b.ex2.rationale.get("pareamento"), (
            f"ex2 ({b.ex2.nome}) deveria ter rationale.pareamento"
        )
        assert b.ex1.rationale["pareamento"]["papel"] == "ancora"
        assert b.ex2.rationale["pareamento"]["papel"] == "par"
        # Ancora vê o nome do par; par vê o nome da âncora
        assert b.ex2.nome in b.ex1.rationale["pareamento"]["parceiros"]
        assert b.ex2.rationale["pareamento"]["ancora"] == b.ex1.nome


def test_pareamento_bloco_solo_nao_atacha_na_ancora(banco):
    """Bloco solo (tamanho 1 ou par não encontrado) → âncora sem pareamento."""
    random.seed(42)
    # Demanda 1 ex de peito + bloco_size 2 → forçará pareamento ou solo
    configs = [
        {
            "demandas": [("padrao", "biceps", 1)],
            "max_complexidade": 5,
            "evitar_agonistas": True,
            "tamanho_bloco": 2,
        }
    ]
    sessoes = gerar_multiplos_treinos(banco, configs)
    # Único ex → bloco solo
    b = sessoes[0].blocos[0]
    assert b.ex2 is None, "esperava bloco solo"
    # ex1 deve ter rationale do slot mas SEM pareamento attached
    assert b.ex1.rationale is not None
    assert "pareamento" not in b.ex1.rationale or b.ex1.rationale["pareamento"] is None


def test_pareamento_score_bate_com_soma_componentes(banco):
    """Invariante: score_pareamento == soma dos pesos dos componentes."""
    random.seed(7)
    configs = [
        {
            "demandas": [("regiao", "upper", 6)],
            "max_complexidade": 5,
            "evitar_agonistas": True,
            "tamanho_bloco": 2,
        }
    ] * 2
    sessoes = gerar_multiplos_treinos(banco, configs)
    for ex in _iter_exercicios(sessoes):
        p = (ex.rationale or {}).get("pareamento")
        if not p or p.get("papel") != "par":
            continue
        soma = sum(c["peso"] for c in p["componentes"])
        assert pytest.approx(p["score_pareamento"], abs=1e-6) == soma, (
            f"score_pareamento ({p['score_pareamento']}) != soma componentes "
            f"({soma}) para {ex.nome}"
        )


def test_pareamento_alternativas_excluem_o_proprio(banco):
    """Alternativas do pareamento não incluem o exercício escolhido."""
    random.seed(11)
    configs = [
        {
            "demandas": [("regiao", "upper", 6)],
            "max_complexidade": 5,
            "evitar_agonistas": True,
            "tamanho_bloco": 2,
        }
    ]
    sessoes = gerar_multiplos_treinos(banco, configs)
    for ex in _iter_exercicios(sessoes):
        p = (ex.rationale or {}).get("pareamento")
        if not p or p.get("papel") != "par":
            continue
        nomes_alts = {a["nome"] for a in p["alternativas"]}
        assert ex.nome not in nomes_alts, (
            f"alternativa de pareamento não pode ser o próprio escolhido ({ex.nome})"
        )


def test_pareamento_round_trip_serializacao_preserva_dados(banco):
    """_exercicio_to_dict → JSON → _dict_to_exercicio mantém pareamento."""
    from app_flask import _dict_to_exercicio, _exercicio_to_dict

    random.seed(99)
    configs = [
        {
            "demandas": [("regiao", "upper", 6)],
            "max_complexidade": 5,
            "evitar_agonistas": True,
            "tamanho_bloco": 2,
        }
    ]
    sessoes = gerar_multiplos_treinos(banco, configs)
    cobertura = 0
    for ex in _iter_exercicios(sessoes):
        d = _exercicio_to_dict(ex)
        js = json.dumps(d)
        d2 = json.loads(js)
        ex2 = _dict_to_exercicio(d2)
        assert ex2.rationale == ex.rationale, (
            f"rationale (incl. pareamento) não sobreviveu round-trip pro ex {ex.nome}"
        )
        if (ex.rationale or {}).get("pareamento"):
            cobertura += 1
    assert cobertura > 0, "esperava pelo menos 1 ex com pareamento serializado"


def test_pareamento_outros_no_momento_reflete_ordem_pre_append(banco):
    """Em bloco de 3, o terceiro ex tem 'outros_no_momento' com 2 nomes
    (âncora + segundo par adicionado antes dele)."""
    random.seed(42)
    configs = [
        {
            "demandas": [("regiao", "upper", 6)],
            "max_complexidade": 5,
            "evitar_agonistas": True,
            "tamanho_bloco": 3,  # forçar trio
        }
    ]
    sessoes = gerar_multiplos_treinos(banco, configs)
    cobertura = 0
    for b in sessoes[0].blocos:
        if b.ex3 is None:
            continue
        p3 = b.ex3.rationale["pareamento"]
        assert p3["papel"] == "par"
        # No momento que ex3 entrou, bloco era [ex1, ex2]: ancora=ex1, outros=[ex2]
        assert p3["ancora"] == b.ex1.nome
        assert p3["outros_no_momento"] == [b.ex2.nome], (
            f"ex3 ({b.ex3.nome}) deveria ver outros=[{b.ex2.nome}], "
            f"viu {p3['outros_no_momento']}"
        )
        cobertura += 1
    assert cobertura > 0, "esperava pelo menos 1 bloco de 3 pra cobrir o teste"


def test_pareamento_componentes_refletem_score_pareamento(banco):
    """Componentes capturados batem com `_score_pareamento` recomputado.

    Sanity numérica do mirror analítico — `_componentes_pareamento` deve
    decompor exatamente o que `_score_pareamento` calcula.
    """
    from gerador_treino import _score_pareamento

    random.seed(13)
    configs = [
        {
            "demandas": [("regiao", "upper", 6)],
            "max_complexidade": 5,
            "evitar_agonistas": True,
            "tamanho_bloco": 2,
        }
    ]
    sessoes = gerar_multiplos_treinos(banco, configs)
    for b in sessoes[0].blocos:
        if b.ex2 is None:
            continue
        # Reconstruir contexto: ex2 entrou contra bloco [ex1] (âncora sozinha)
        score_recomputado = _score_pareamento(
            b.ex2, [b.ex1], evitar_agonistas=True,
        )
        p = b.ex2.rationale["pareamento"]
        assert pytest.approx(p["score_pareamento"], abs=1e-6) == score_recomputado, (
            f"score do par {b.ex2.nome} divergente — capturado "
            f"{p['score_pareamento']}, recomputado {score_recomputado}"
        )
