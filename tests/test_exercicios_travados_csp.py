"""Testes da Fatia 4.D — exercicios_travados no motor CSP.

Travados são exercícios fixados pelo personal — decisão clínica deliberada
que supera regras automáticas. Comportamento esperado (decisões clínicas
fechadas com Bernardo, 2026-05-24):

(a) Travado em demanda compatível consome 1 vaga da PRIMEIRA demanda cujo
    escopo cobre o padrão do travado.
(b) Travado sem demanda compatível vira EXERCÍCIO EXTRA (treino com N+1
    exs, não substitui vaga existente).
(c) Travado BYPASSA H-P1 (complexidade alta em aluno iniciante).
(d) Travado BYPASSA H-T4 (Acessório em vaga única de subregião).
(e) Travado BYPASSA AllDifferent cross-treino entre travados (mesmo
    travado pode aparecer em mais de 1 treino da rotina).
(f) Slot non-travado nunca recebe nome travado em algum outro slot.
(g) Travado PARTICIPA de S-T1 (tier-order respeita ele).
(h) Sem travados, comportamento idêntico ao pré-4.D (regressão).
"""
from __future__ import annotations

from gerador_csp import (
    ConfigVariedade,
    gerar_rotina_csp,
    gerar_treino_csp,
)


# Helpers
def _todos_nomes(rotina_ou_treino):
    out = []
    treinos = rotina_ou_treino.get("treinos") or [rotina_ou_treino]
    for tr in treinos:
        for g in tr["grupos"]:
            for e in g["exercicios"]:
                out.append(e.nome)
    return out


def _ex_por_nome(banco, nome):
    for e in banco:
        if e.nome == nome:
            return e
    raise ValueError(f"{nome} não está no banco")


# (a) Travado em demanda compatível consome vaga
def test_travado_em_demanda_compativel_consome_vaga(banco):
    apoio = _ex_por_nome(banco, "Apoio")  # padrao=empurrar_compostos, subreg=peito
    r = gerar_treino_csp(
        [("subregiao", "peito", 2), ("subregiao", "costas", 2)],
        banco, nivel_aluno=3, seed=42, travados=[apoio],
    )
    assert r["viavel"] is True
    nomes = _todos_nomes(r)
    # 4 exs ao total — travado consumiu 1 das 2 vagas de peito
    assert len(nomes) == 4, f"esperado 4 exs (sem extra), veio {nomes}"
    assert "Apoio" in nomes
    # Apoio entra na demanda de peito (não vira demanda extra)
    grupos_demandas = [g["demanda"] for g in r["grupos"]]
    assert ("subregiao", "peito", 2) in grupos_demandas
    assert ("padrao", "empurrar_compostos", 1) not in grupos_demandas


# (b) Travado sem demanda compatível vira EXTRA
def test_travado_off_script_vira_extra(banco):
    apoio = _ex_por_nome(banco, "Apoio")  # peito, mas treino só pede perna_anterior
    r = gerar_treino_csp(
        [("subregiao", "perna_anterior", 2)],
        banco, nivel_aluno=3, seed=42, travados=[apoio],
    )
    assert r["viavel"] is True
    nomes = _todos_nomes(r)
    # 3 exs: 2 pernas + 1 extra (Apoio)
    assert len(nomes) == 3, f"esperado 3 exs (2 pernas + Apoio extra), veio {nomes}"
    assert "Apoio" in nomes
    # Demanda virtual extra foi criada
    grupos_demandas = [g["demanda"] for g in r["grupos"]]
    assert ("padrao", "empurrar_compostos", 1) in grupos_demandas


# (c) Travado bypassa H-P1 (complexidade alta + nível iniciante)
def test_travado_bypassa_nivel_p1(banco):
    # Apoio tem cx=3; nível 1 tem teto cx=2 → normalmente filtrado
    apoio = _ex_por_nome(banco, "Apoio")
    assert apoio.complexidade > 2, "fixture: Apoio precisa ter cx>2 pra teste fazer sentido"
    r = gerar_treino_csp(
        [("subregiao", "peito", 2)],
        banco, nivel_aluno=1, seed=42, travados=[apoio],
    )
    assert r["viavel"] is True
    nomes = _todos_nomes(r)
    assert "Apoio" in nomes, f"travado deve entrar mesmo no nível 1, veio {nomes}"


# (d) Travado supera H-T4 (vaga única + Acessório)
def test_travado_supera_h_t4(banco):
    crossover = _ex_por_nome(banco, "Crossover")
    assert crossover.tier == "Acessório"
    r = gerar_treino_csp(
        [("subregiao", "peito", 1)],  # vaga única — H-T4 dispararia
        banco, nivel_aluno=3, seed=42, travados=[crossover],
    )
    assert r["viavel"] is True
    nomes = _todos_nomes(r)
    assert "Crossover" in nomes, f"travado Acessório deve superar H-T4, veio {nomes}"


# (e) Travado bypassa AllDifferent cross-treino ENTRE TRAVADOS
def test_travado_mesmo_em_dois_treinos_da_rotina(banco):
    apoio = _ex_por_nome(banco, "Apoio")
    r = gerar_rotina_csp(
        [
            [("subregiao", "peito", 2)],  # treino 0
            [("subregiao", "peito", 2)],  # treino 1
        ],
        banco, nivel_aluno=3, seed=42,
        travados_por_treino={0: [apoio], 1: [apoio]},
    )
    assert r["viavel"] is True
    apoio_count = 0
    for tr in r["treinos"]:
        nomes_t = [e.nome for g in tr["grupos"] for e in g["exercicios"]]
        if "Apoio" in nomes_t:
            apoio_count += 1
    assert apoio_count == 2, f"Apoio deveria aparecer em ambos treinos, contagem={apoio_count}"


# (f) Non-travado não pode usar nome que está travado em qualquer slot
def test_non_travado_nao_repete_nome_travado(banco):
    apoio = _ex_por_nome(banco, "Apoio")
    # Trava Apoio no treino 0; treino 1 também pede peito 2 mas não trava nada.
    # Apoio NÃO deve aparecer no treino 1 (non-travado bloqueado pelo nome travado).
    r = gerar_rotina_csp(
        [
            [("subregiao", "peito", 2)],  # treino 0 com travado
            [("subregiao", "peito", 2)],  # treino 1 sem travado
        ],
        banco, nivel_aluno=3, seed=42,
        travados_por_treino={0: [apoio]},
    )
    assert r["viavel"] is True
    nomes_t1 = [e.nome for g in r["treinos"][1]["grupos"] for e in g["exercicios"]]
    assert "Apoio" not in nomes_t1, (
        f"non-travado de t1 não deve escolher Apoio (travado em t0), nomes={nomes_t1}"
    )


# (g) Travado participa de S-T1 (tier-order respeitado)
def test_travado_participa_de_st1_tier_order(banco):
    # Travado Principal + 1 vaga Acessório livre. S-T1 deve manter Principal
    # antes (bloco com índice menor) que Acessório.
    supino = _ex_por_nome(banco, "Supino Com Halteres")  # Principal
    assert supino.tier == "Principal"
    r = gerar_treino_csp(
        [("subregiao", "peito", 2)],
        banco, nivel_aluno=3, seed=42, travados=[supino],
        peso_tamanho_bloco=5,  # força blocos separados pra exercitar ordem
        tamanho_preferido=1,
    )
    assert r["viavel"] is True
    blocos = r["blocos"]
    # Travado Principal não pode aparecer DEPOIS de um Acessório no treino
    ranks = {"Principal": 3, "Intermediário": 2, "Acessório": 1}
    ordem_global = [e for b in blocos for e in b]
    for i in range(len(ordem_global) - 1):
        r1 = ranks.get(ordem_global[i].tier, 1)
        r2 = ranks.get(ordem_global[i + 1].tier, 1)
        # Se travado é Principal e está num bloco, todos depois com tier menor OK,
        # mas tier maior depois é violação.
        assert r1 >= r2, (
            f"S-T1 violado: {ordem_global[i].nome}({r1}) antes de "
            f"{ordem_global[i+1].nome}({r2})"
        )


# (h) Sem travados, comportamento idêntico ao pré-4.D (sanity de regressão)
def test_sem_travados_preserva_comportamento(banco):
    demandas = [
        ("subregiao", "peito", 2),
        ("subregiao", "costas", 2),
        ("subregiao", "perna_anterior", 2),
    ]
    # Mesma seed → mesma rotina (modulo CP-SAT não-determinismo aceito) com
    # qualquer um dos paths (None ou dict vazio).
    r1 = gerar_rotina_csp([demandas], banco, nivel_aluno=3, seed=42)
    r2 = gerar_rotina_csp(
        [demandas], banco, nivel_aluno=3, seed=42,
        travados_por_treino={},
    )
    r3 = gerar_rotina_csp(
        [demandas], banco, nivel_aluno=3, seed=42,
        travados_por_treino=None,
    )
    assert r1["viavel"] is True
    assert r2["viavel"] is True
    assert r3["viavel"] is True
    # Estrutura básica preservada: mesmo número de exs, mesmo número de grupos
    assert sum(len(g["exercicios"]) for g in r1["treinos"][0]["grupos"]) == 6
    assert sum(len(g["exercicios"]) for g in r2["treinos"][0]["grupos"]) == 6
    assert sum(len(g["exercicios"]) for g in r3["treinos"][0]["grupos"]) == 6
    assert len(r1["treinos"][0]["grupos"]) == 3
    assert len(r2["treinos"][0]["grupos"]) == 3
    assert len(r3["treinos"][0]["grupos"]) == 3


# (i) Travado funciona com ConfigVariedade (modo padrão do /regerar)
def test_travado_com_variedade_ativa(banco):
    apoio = _ex_por_nome(banco, "Apoio")
    r = gerar_treino_csp(
        [("subregiao", "peito", 2), ("subregiao", "costas", 2)],
        banco, nivel_aluno=3, seed=42,
        variedade=ConfigVariedade(),
        travados=[apoio],
    )
    assert r["viavel"] is True
    nomes = _todos_nomes(r)
    assert "Apoio" in nomes, "travado deve aparecer mesmo com variedade ativa"
    assert len(nomes) == 4
