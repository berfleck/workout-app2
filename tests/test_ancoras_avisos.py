"""Testes de avisos novos da Etapa 3.

- ancora_sem_candidatos: emitido quando obrigatória tem quota >0 mas
  banco filtrado está vazio (equipamento bloqueado, complexidade baixa).
- proporcao_desviada: estrutura definida; teste skip por enquanto
  (caso natural de drift sob relax difícil de construir sem mock).
"""
from __future__ import annotations

import random
import pytest

from gerador_treino import gerar_multiplos_treinos


def _avisos(sessoes):
    out = []
    for s in sessoes:
        out.extend(s.avisos)
    return out


def test_ancora_sem_candidatos_quando_equipamentos_bloqueiam_obrigatoria(banco):
    """Bloqueio de equipamentos zera candidatos pra hinge → aviso
    ancora_sem_candidatos.

    perna_posterior(6) com hinge:3 obrig + knee:2 + abd:1. Bloqueando
    todos os equipamentos de hinge, a quota=3 hinge não tem candidato.
    """
    eqs_hinge = {e.eq_primario for e in banco if e.padrao == "hinge"}
    cfg = {
        "demandas": [("subregiao", "perna_posterior", 6)],
        "equipamentos_bloqueados": list(eqs_hinge),
    }
    random.seed(42)
    sessoes = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    avisos = _avisos(sessoes)
    sem_cand = [a for a in avisos if a.get("tipo") == "ancora_sem_candidatos"]
    assert sem_cand, f"esperado ancora_sem_candidatos, avisos: {avisos}"
    # Aviso identifica a âncora afetada
    assert any(a.get("padrao") == "hinge" for a in sem_cand)


@pytest.mark.skip(reason="Caso natural de drift sob relax difícil de construir sem mock")
def test_proporcao_desviada_quando_relax_muda_quota(banco):
    """Cenário onde estrito esgota família e relax substitui por outro padrão,
    gerando drift na proporção esperada vs entregue.
    """
    pass
