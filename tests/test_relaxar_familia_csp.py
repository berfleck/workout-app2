"""Testes da Fatia 4.E — relaxar_familia no motor CSP.

Comportamento esperado (decisões fechadas com Bernardo, 2026-05-24):

(a) `_familia_cross(ex)` = `ex.variacao_de or ex.nome` — cobre pai+filho.
(b) `familias_proibidas` pré-filtra pool dos slots non-travados (hard
    cross-treino quando o adapter passa).
(c) Estrito sem alternativas + `relaxar_familia=False` → inviável,
    `relax_ativado=False`.
(d) Estrito sem alternativas + `relaxar_familia=True` → motor refaz
    sem o filtro, viável, `relax_ativado=True`, `relaxados_por_treino`
    com os nomes que violaram a regra original.
(e) `familias_proibidas` vazio/None → comportamento pré-4.E (relax nunca
    aciona, mesmo com `relaxar_familia=True`).
(f) `relaxar_familia=True` mas estrito é viável → relax NÃO dispara.
(g) Travado supera `familias_proibidas` — slot dedicado bypassa o filtro,
    e o travado NÃO entra na lista de relaxados (decisão deliberada do
    user > regra automática, igual 4.D).
(h) Wrapper `gerar_treino_csp` expõe `relaxados: list[str]` +
    `relax_ativado: bool` no top-level.
"""
from __future__ import annotations

from gerador_csp import (
    ConfigVariedade,
    _familia_cross,
    gerar_rotina_csp,
    gerar_treino_csp,
)


# Helpers
def _todos_nomes_treino(treino):
    return [e.nome for g in treino["grupos"] for e in g["exercicios"]]


def _ex_por_nome(banco, nome):
    for e in banco:
        if e.nome == nome:
            return e
    raise ValueError(f"{nome} não está no banco")


# (a) _familia_cross helper — cobre pai (variacao_de vazio) + filho
def test_familia_cross_pai_e_filho(banco):
    cadeira = _ex_por_nome(banco, "Cadeira Extensora")
    assert cadeira.variacao_de in (None, ""), "Cadeira Extensora é pai (sem variacao_de)"
    assert _familia_cross(cadeira) == "Cadeira Extensora"

    # Filho com variacao_de não-vazio
    barra_fixa = _ex_por_nome(banco, "Barra Fixa")
    assert barra_fixa.variacao_de == "Barra"
    assert _familia_cross(barra_fixa) == "Barra"


# (b) familias_proibidas filtra pool quando estrito é viável
def test_familias_proibidas_filtra_pool(banco):
    # puxadas tem 4 famílias: Barra (5 ex), Pullover (2), Puxada (4), Pulldown (1).
    # Proibir Barra deixa 7 ex em 3 famílias — fácil preencher demanda(2).
    r = gerar_rotina_csp(
        [[("padrao", "puxadas", 2)]],
        banco, nivel_aluno=3, seed=42,
        familias_proibidas={"Barra"},
    )
    assert r["viavel"] is True
    nomes = _todos_nomes_treino(r["treinos"][0])
    exs = [_ex_por_nome(banco, n) for n in nomes]
    assert all(_familia_cross(e) != "Barra" for e in exs), (
        f"familias_proibidas={'Barra'} não foi respeitado: {nomes}"
    )
    assert r["relax_ativado"] is False
    assert r["relaxados_por_treino"] == {}


# (c) Sem alternativas + relaxar_familia=False → inviável
def test_estrito_inviavel_sem_relax(banco):
    # knee_extension tem só 1 família ("Cadeira Extensora", 1 ex).
    # Proibir essa família = pool vazio → inviável no estrito.
    r = gerar_rotina_csp(
        [[("padrao", "knee_extension", 1)]],
        banco, nivel_aluno=3, seed=42,
        familias_proibidas={"Cadeira Extensora"},
        relaxar_familia=False,
    )
    assert r["viavel"] is False
    assert r["relax_ativado"] is False
    assert r["relaxados_por_treino"] == {}


# (d) Sem alternativas + relaxar_familia=True → relax aciona e marca relaxados
def test_estrito_inviavel_com_relax_aciona(banco):
    r = gerar_rotina_csp(
        [[("padrao", "knee_extension", 1)]],
        banco, nivel_aluno=3, seed=42,
        familias_proibidas={"Cadeira Extensora"},
        relaxar_familia=True,
    )
    assert r["viavel"] is True, "relax devia ter resolvido"
    assert r["relax_ativado"] is True
    assert 0 in r["relaxados_por_treino"]
    assert r["relaxados_por_treino"][0] == ["Cadeira Extensora"]
    nomes = _todos_nomes_treino(r["treinos"][0])
    assert nomes == ["Cadeira Extensora"]


# (e) familias_proibidas vazio/None → preserva comportamento pré-4.E
def test_sem_familias_proibidas_preserva_pre_4e(banco):
    cfg = [[("subregiao", "peito", 2)]]
    r_none = gerar_rotina_csp(cfg, banco, nivel_aluno=3, seed=42)
    r_vazio = gerar_rotina_csp(
        cfg, banco, nivel_aluno=3, seed=42,
        familias_proibidas=set(), relaxar_familia=True,
    )
    # Mesma demanda + sem familias_proibidas = relax nunca aciona,
    # independente da flag.
    for r in (r_none, r_vazio):
        assert r["viavel"] is True
        assert r["relax_ativado"] is False
        assert r["relaxados_por_treino"] == {}


# (f) Estrito viável + relaxar_familia=True → relax NÃO dispara
def test_estrito_viavel_relax_nao_dispara(banco):
    # Estrito viável (familias_proibidas={"Pullover"}, sobram 10 puxadas
    # em 3 famílias). Relax flag não muda comportamento.
    r = gerar_rotina_csp(
        [[("padrao", "puxadas", 2)]],
        banco, nivel_aluno=3, seed=42,
        familias_proibidas={"Pullover"},
        relaxar_familia=True,
    )
    assert r["viavel"] is True
    assert r["relax_ativado"] is False
    assert r["relaxados_por_treino"] == {}
    nomes = _todos_nomes_treino(r["treinos"][0])
    exs = [_ex_por_nome(banco, n) for n in nomes]
    assert all(_familia_cross(e) != "Pullover" for e in exs)


# (g) Travado bypassa familias_proibidas + NÃO entra como relaxado
def test_travado_bypassa_e_nao_eh_relaxado(banco):
    # Trava Cadeira Extensora E proíbe família dela.
    # Travado entra (decisão do user > regra), mas NÃO vai pra relaxados.
    cadeira = _ex_por_nome(banco, "Cadeira Extensora")
    r = gerar_rotina_csp(
        [[("padrao", "knee_extension", 1)]],
        banco, nivel_aluno=3, seed=42,
        familias_proibidas={"Cadeira Extensora"},
        relaxar_familia=True,
        travados_por_treino={0: [cadeira]},
    )
    assert r["viavel"] is True
    nomes = _todos_nomes_treino(r["treinos"][0])
    assert "Cadeira Extensora" in nomes
    # 4.E: travado bypassa filtro → não houve precisão de relax
    # (estrito direto ficou viável via travado).
    assert r["relax_ativado"] is False, (
        "Travado bypassa filtro de família — estrito devia ser viável "
        "direto, sem precisar relaxar"
    )
    assert r["relaxados_por_treino"] == {}


# (h) Wrapper gerar_treino_csp expõe relaxados + relax_ativado top-level
def test_wrapper_treino_expoe_relaxados(banco):
    r = gerar_treino_csp(
        [("padrao", "knee_extension", 1)],
        banco, nivel_aluno=3, seed=42,
        familias_proibidas={"Cadeira Extensora"},
        relaxar_familia=True,
    )
    assert r["viavel"] is True
    assert "relaxados" in r
    assert "relax_ativado" in r
    assert r["relax_ativado"] is True
    assert r["relaxados"] == ["Cadeira Extensora"]


# (i) Funciona com ConfigVariedade (modo /regerar)
def test_relax_com_variedade_ativa(banco):
    r = gerar_treino_csp(
        [("padrao", "knee_extension", 1)],
        banco, nivel_aluno=3, seed=42,
        variedade=ConfigVariedade(),
        familias_proibidas={"Cadeira Extensora"},
        relaxar_familia=True,
    )
    assert r["viavel"] is True
    assert r["relax_ativado"] is True
    assert r["relaxados"] == ["Cadeira Extensora"]
