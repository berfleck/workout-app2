"""Fixtures e helpers compartilhados pelos testes do gerador.

A fixture `banco` é session-scoped — XLSX é lido uma vez por sessão.
O helper `sessao_para_estrutura_clinica` produz a representação derivada
usada nos snapshots de regressão (estrutura clínica, sem metadata cosmético).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Garante que o pacote raiz é importável quando rodamos `pytest` da raiz.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gerador_treino import Sessao, carregar_banco  # noqa: E402

XLSX_PATH = ROOT / "banco_exercicios.xlsx"


@pytest.fixture(scope="session")
def banco():
    """Banco completo, carregado uma vez por sessão de testes."""
    return carregar_banco(str(XLSX_PATH))


def sessao_para_estrutura_clinica(sessao: Sessao) -> dict:
    """Representação derivada de uma sessão pra snapshots de regressão.

    Inclui só o que importa clinicamente: tipo, ordem dos blocos, nomes
    dos exercícios, avisos e relaxados. Ignora metadata como `padrao`,
    `purpose`, `complexidade` (derivados do nome via banco).
    """
    return {
        "tipo": sessao.tipo,
        "blocos": [
            {
                "label": b.label,
                "nomes": [ex.nome for ex in (b.ex1, b.ex2, b.ex3) if ex],
            }
            for b in sessao.blocos
        ],
        "avisos": sessao.avisos,
        "relaxados": list(sessao.relaxados),
    }
