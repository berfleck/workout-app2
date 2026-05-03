"""Testes do filtro de cargas (Etapa 4 / HIB2).

Cada par (ex_a, ex_b) é avaliado em 3 dimensões: grip, lombar, core. Bloqueia
se soma >= threshold E ambos têm valor >= 1 nessa dimensão.
"""
from __future__ import annotations

import pytest

from gerador_treino import Exercicio, carregar_banco


def _make_ex(
    nome: str,
    *,
    grip: int = 0,
    lombar: int = 0,
    core: int = 0,
    fadiga: int = 1,
    padrao: str = "empurrar_compostos",
    regiao: str = "upper",
    subregiao: str = "peito",
) -> Exercicio:
    """Constrói um Exercicio mínimo pra testes unitários."""
    return Exercicio(
        nome=nome,
        variacao_de=None,
        eq_primario="",
        eq_secundario=None,
        regiao=regiao,
        subregiao=subregiao,
        padrao=padrao,
        purpose="compound",
        unilateral="bilateral",
        complexidade=2,
        fadiga=fadiga,
        circuito="não",
        similaridade="",
        musculo_primario="",
        obs=None,
        carga_grip=grip,
        carga_lombar=lombar,
        demanda_core=core,
    )


# ---------------------------------------------------------------------------
# Sub-PR 0.1 — campos no dataclass + leitura no carregar_banco
# ---------------------------------------------------------------------------

def test_carga_fields_exist_with_default_zero():
    """Construir Exercicio sem passar cargas → defaults zero."""
    e = Exercicio(
        nome="X", variacao_de=None, eq_primario="", eq_secundario=None,
        regiao="upper", subregiao="peito", padrao="empurrar_compostos",
        purpose="compound", unilateral="bilateral", complexidade=2, fadiga=3,
        circuito="não", similaridade="", musculo_primario="", obs=None,
    )
    assert e.carga_grip == 0
    assert e.carga_lombar == 0
    assert e.demanda_core == 0


def test_carregar_banco_le_cargas(banco):
    """Banco real tem 82/102/109 ex com grip/lombar/core >= 1."""
    grip_nz = sum(1 for e in banco if e.carga_grip >= 1)
    lombar_nz = sum(1 for e in banco if e.carga_lombar >= 1)
    core_nz = sum(1 for e in banco if e.demanda_core >= 1)
    assert grip_nz == 82
    assert lombar_nz == 102
    assert core_nz == 109


def test_carregar_banco_cargas_em_faixa_0_3(banco):
    """Valores curados são int entre 0 e 3."""
    for e in banco:
        assert isinstance(e.carga_grip, int)
        assert isinstance(e.carga_lombar, int)
        assert isinstance(e.demanda_core, int)
        assert 0 <= e.carga_grip <= 3
        assert 0 <= e.carga_lombar <= 3
        assert 0 <= e.demanda_core <= 3
