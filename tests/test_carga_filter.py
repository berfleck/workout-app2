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


# ---------------------------------------------------------------------------
# Sub-PR 0.2 — helper puro _bloqueio_cargas
# ---------------------------------------------------------------------------

HIB2 = {"grip": 6, "lombar": 5, "core": 6}


def test_bloqueio_cargas_par_lombar_atinge_threshold():
    """Hiperextensão (lombar=3) + Remada Curvada (lombar=2) bloqueia em HIB2 (lombar=5)."""
    from gerador_treino import _bloqueio_cargas
    a = _make_ex("Hiperextensão", lombar=3)
    b = _make_ex("Remada Curvada", lombar=2)
    assert _bloqueio_cargas(a, b, HIB2) is True


def test_bloqueio_cargas_um_zero_libera():
    """Regra "ambos >= 1" — se um lado é 0, par passa mesmo se outro é alto."""
    from gerador_treino import _bloqueio_cargas
    a = _make_ex("A", lombar=0)
    b = _make_ex("B", lombar=5)  # b sozinho atinge threshold
    assert _bloqueio_cargas(a, b, HIB2) is False


def test_bloqueio_cargas_soma_abaixo_threshold():
    """Soma 5 com threshold 6 → não bloqueia."""
    from gerador_treino import _bloqueio_cargas
    a = _make_ex("A", grip=2)
    b = _make_ex("B", grip=3)
    assert _bloqueio_cargas(a, b, HIB2) is False


def test_bloqueio_cargas_qualquer_dimensao_dispara():
    """Bloqueia se *qualquer* dimensão viola (não precisa todas)."""
    from gerador_treino import _bloqueio_cargas
    a = _make_ex("A", grip=3, lombar=2, core=1)
    b = _make_ex("B", grip=3, lombar=2, core=1)
    # grip 3+3=6 ≥ 6 (threshold grip) → True
    assert _bloqueio_cargas(a, b, HIB2) is True


def test_bloqueio_cargas_thresholds_diferentes():
    """Mesmo par com threshold mais frouxo libera."""
    from gerador_treino import _bloqueio_cargas
    a = _make_ex("A", lombar=3)
    b = _make_ex("B", lombar=2)
    # threshold lombar=6 (mais frouxo) → soma 5 não bloqueia
    assert _bloqueio_cargas(a, b, {"grip": 6, "lombar": 6, "core": 6}) is False


def test_bloqueio_cargas_threshold_zero_pula_dimensao():
    """Threshold 0 ou None pula a dimensão (não bloqueia por ela)."""
    from gerador_treino import _bloqueio_cargas
    a = _make_ex("A", lombar=3)
    b = _make_ex("B", lombar=3)
    # só threshold de grip definido — lombar/core ignorados
    assert _bloqueio_cargas(a, b, {"grip": 6}) is False
    assert _bloqueio_cargas(a, b, {"grip": 6, "lombar": 0, "core": 0}) is False


def test_bloqueio_cargas_simetrico():
    """`_bloqueio_cargas(a, b, t)` === `_bloqueio_cargas(b, a, t)`."""
    from gerador_treino import _bloqueio_cargas
    a = _make_ex("A", lombar=3)
    b = _make_ex("B", lombar=2)
    assert _bloqueio_cargas(a, b, HIB2) == _bloqueio_cargas(b, a, HIB2)


# ---------------------------------------------------------------------------
# Sub-PR 1.1 — integrar filtro em pode_adicionar_ao_bloco
# ---------------------------------------------------------------------------

def test_pode_adicionar_carga_off_nao_bloqueia():
    """Sem cargas_config, comportamento idêntico ao pré-Etapa 4."""
    from gerador_treino import pode_adicionar_ao_bloco
    a = _make_ex("A", lombar=3)
    b = _make_ex("B", lombar=3)
    assert pode_adicionar_ao_bloco([a], b, 2) is True


def test_pode_adicionar_carga_on_bloqueia_par_acima_threshold():
    """Com cargas_config, par lombar 3+3=6 acima de threshold 5 é bloqueado."""
    from gerador_treino import pode_adicionar_ao_bloco
    a = _make_ex("A", lombar=3)
    b = _make_ex("B", lombar=3)
    assert pode_adicionar_ao_bloco([a], b, 2, cargas_config=HIB2) is False


def test_pode_adicionar_carga_on_libera_par_abaixo_threshold():
    """Soma 4 com threshold lombar=5 → não bloqueia."""
    from gerador_treino import pode_adicionar_ao_bloco
    a = _make_ex("A", lombar=2)
    b = _make_ex("B", lombar=2)
    assert pode_adicionar_ao_bloco([a], b, 2, cargas_config=HIB2) is True


def test_pode_adicionar_travados_bypassam_carga_lista_exercicios():
    """Travados (passados como lista de Exercicio) bypassam filtro de cargas."""
    from gerador_treino import pode_adicionar_ao_bloco
    a = _make_ex("A_travado", lombar=3)
    b = _make_ex("B", lombar=3)
    travados = [a]
    assert pode_adicionar_ao_bloco(
        [a], b, 2, cargas_config=HIB2, exercicios_travados=travados
    ) is True


def test_pode_adicionar_travados_bypassam_carga_set_de_nomes():
    """Travados passados como set de nomes também bypassam."""
    from gerador_treino import pode_adicionar_ao_bloco
    a = _make_ex("A_travado", lombar=3)
    b = _make_ex("B_travado", lombar=3)
    travados_nomes = {"A_travado", "B_travado"}
    assert pode_adicionar_ao_bloco(
        [a], b, 2, cargas_config=HIB2, exercicios_travados=travados_nomes
    ) is True


def test_pode_adicionar_carga_bloco_3_par_a_par():
    """Em bloco de 3, filtro é par-a-par (não soma trio)."""
    from gerador_treino import pode_adicionar_ao_bloco
    a = _make_ex("A", grip=2)
    b = _make_ex("B", grip=2)
    # C+A=5 OK, C+B=5 OK (não somam grip=6 → trio passaria)
    c = _make_ex("C", grip=3)
    assert pode_adicionar_ao_bloco([a, b], c, 3, cargas_config=HIB2) is True
    # Mas C2+A=6 ≥ 6 → C2 deve ser rejeitado
    c2 = _make_ex("C2", grip=4)
    assert pode_adicionar_ao_bloco([a, b], c2, 3, cargas_config=HIB2) is False


def test_pode_adicionar_carga_e_fadiga_independentes():
    """Filtro de cargas roda antes de fadiga; ambos podem bloquear."""
    from gerador_treino import pode_adicionar_ao_bloco
    # Par bloqueado por carga E candidato com fadiga 4 (também violaria fadiga)
    a = _make_ex("A", lombar=3, fadiga=4)
    b = _make_ex("B", lombar=3, fadiga=4)
    # Carga bloqueia → return False (não importa fadiga)
    assert pode_adicionar_ao_bloco([a], b, 2, cargas_config=HIB2) is False
    # Sem carga, fadiga ainda bloqueia (max_alta_fadiga=1 em bloco 2)
    assert pode_adicionar_ao_bloco([a], b, 2, cargas_config=None) is False
