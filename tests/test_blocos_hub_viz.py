"""Testes dos helpers de operação estrutural nível BLOCO no HUB-viz
(Sub-PR 5 da iniciativa swipe/edição direta · Frente C parte 2 · §7.2-7.4).

Cobrem a lógica pura por trás das rotas hub_bloco_* em app_flask.py:
- `_mover_bloco_dict`: reorder com a aritmética off-by-one (o ponto mais
  frágil do PR — testado nos dois sentidos + no-ops + bordas).
- `_ex_dict_do_banco`: prescrição default em exercícios vindos do banco.
- helpers dict reusados (_add/_pop/_relabel/_novo) no contexto de bloco.

As rotas em si são wrappers finos (validação → mutação → salvar_rascunho →
_render_swap_cards), no padrão das rotas hub_ex_* do Sub-PR 4.
"""
from __future__ import annotations

from app_flask import (
    _add_ex_a_bloco_dict,
    _bloco_vazio_dict,
    _ex_dict_do_banco,
    _mover_bloco_dict,
    _novo_bloco_dict,
    _pop_ex_de_bloco_dict,
    _relabel_blocos_dict,
)
from gerador_treino import Exercicio


def _bloco(marca):
    """Bloco-dict mínimo identificável pela marca em ex1.nome."""
    return {"label": "?", "ex1": {"nome": marca}, "ex2": None, "ex3": None}


def _marcas(blocos):
    return [b["ex1"]["nome"] for b in blocos]


def _labels(blocos):
    return [b["label"] for b in blocos]


# ── _mover_bloco_dict — reorder + off-by-one ────────────────────────────


def test_mover_bloco_para_topo():
    blocos = [_bloco("A"), _bloco("B"), _bloco("C"), _bloco("D")]
    assert _mover_bloco_dict(blocos, 1, 0) is True   # carrega B, solta no topo
    assert _marcas(blocos) == ["B", "A", "C", "D"]
    assert _labels(blocos) == ["A", "B", "C", "D"]   # re-rotulado por posição


def test_mover_bloco_para_fim():
    blocos = [_bloco("A"), _bloco("B"), _bloco("C"), _bloco("D")]
    assert _mover_bloco_dict(blocos, 1, 4) is True   # B pro fim (pos=len)
    assert _marcas(blocos) == ["A", "C", "D", "B"]


def test_mover_bloco_frente_pequena():
    blocos = [_bloco("A"), _bloco("B"), _bloco("C"), _bloco("D")]
    # carrega A (bi=0), solta na pos=2 (após B). pop→[B,C,D], pos>bi→dest=1 → [B,A,C,D]
    assert _mover_bloco_dict(blocos, 0, 2) is True
    assert _marcas(blocos) == ["B", "A", "C", "D"]


def test_mover_bloco_tras():
    blocos = [_bloco("A"), _bloco("B"), _bloco("C"), _bloco("D")]
    # carrega D (bi=3), solta na pos=1 (após A). pos<=bi→dest=1 → [A,D,B,C]
    assert _mover_bloco_dict(blocos, 3, 1) is True
    assert _marcas(blocos) == ["A", "D", "B", "C"]


def test_mover_bloco_gaps_adjacentes_sao_noop():
    base = ["A", "B", "C", "D"]
    # Para bi=1, os gaps adjacentes pos==bi e pos==bi+1 devem deixar a lista igual.
    for pos in (1, 2):
        blocos = [_bloco(m) for m in base]
        assert _mover_bloco_dict(blocos, 1, pos) is True
        assert _marcas(blocos) == base


def test_mover_bloco_posicao_invalida():
    blocos = [_bloco("A"), _bloco("B")]
    assert _mover_bloco_dict(blocos, 0, 5) is False   # pos > len
    assert _mover_bloco_dict(blocos, 9, 0) is False   # bi fora de range
    assert _marcas(blocos) == ["A", "B"]              # intacto


# ── _ex_dict_do_banco — prescrição default ──────────────────────────────


def _ex_banco(nome, purpose="isolation"):
    return Exercicio(
        nome=nome, variacao_de=None, eq_primario="", eq_secundario=None,
        regiao="upper", subregiao="peito", padrao="empurrar_isolados",
        purpose=purpose, unilateral="", complexidade=2, fadiga=2,
        circuito="não", similaridade="", musculo_primario="", obs=None,
    )


def test_ex_dict_do_banco_aplica_prescricao_default():
    d = _ex_dict_do_banco(_ex_banco("Crucifixo"))
    assert d["series"] == 3 and d["reps"] == "8-12" and d["rir"] == 2
    assert d["nome"] == "Crucifixo"


def test_ex_dict_do_banco_preserva_prescricao_existente():
    ex = _ex_banco("Supino")
    ex.series, ex.reps, ex.rir = 5, "5", 1
    d = _ex_dict_do_banco(ex)
    assert (d["series"], d["reps"], d["rir"]) == (5, "5", 1)


# ── helpers dict reusados no contexto de bloco ──────────────────────────


def test_adicionar_preenche_proximo_slot_e_falha_no_quarto():
    bloco = {"label": "A", "ex1": {"nome": "x"}, "ex2": None, "ex3": None}
    assert _add_ex_a_bloco_dict(bloco, {"nome": "y"}) is True
    assert bloco["ex2"]["nome"] == "y"
    assert _add_ex_a_bloco_dict(bloco, {"nome": "z"}) is True
    assert bloco["ex3"]["nome"] == "z"
    assert _add_ex_a_bloco_dict(bloco, {"nome": "w"}) is False   # cheio


def test_remover_ultimo_ex_esvazia_bloco():
    bloco = _novo_bloco_dict({"nome": "só"})
    assert _bloco_vazio_dict(bloco) is False
    assert _pop_ex_de_bloco_dict(bloco, 0)["nome"] == "só"
    assert _bloco_vazio_dict(bloco) is True


def test_relabel_apos_remocao():
    blocos = [_bloco("A"), _bloco("B"), _bloco("C")]
    blocos.pop(1)
    _relabel_blocos_dict(blocos)
    assert _labels(blocos) == ["A", "B"]
    assert _marcas(blocos) == ["A", "C"]
