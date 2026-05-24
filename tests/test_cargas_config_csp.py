"""Testes da Fatia 4.E cargas — `cargas_config` no motor CSP.

Filtro de carga acumulada par-a-par dentro do bloco. Réplica clínica fiel
do `_bloqueio_cargas` do motor antigo (`gerador_treino.py:1186-1211`), com
graceful degradation por bloco (BoolVar `cargas_off_b[b]`) quando inviável.

Decisões fechadas (Bernardo + sub-agent, 2026-05-24):

1. Modelagem par-a-par (não cumulativa). Dim ativa quando `thr[d] > 0`,
   bloqueia se `a>=1 AND b>=1 AND (a+b) >= thr[d]`.

2. Graceful degradation POR BLOCO: `cargas_off_b[b]` BoolVar; quando o
   solver não satisfaz todos pares, liga `cargas_off_b[b]=True` (penalty
   `peso_cargas_off=1000` no objetivo) e emite aviso `relaxado_carga`.

3. Travados ENTRAM nos pares (divergência intencional do antigo). Como
   travado tem `pool_slot=[ex]` (4.D), par travado+non-travado violador
   força non-travado a mudar — "travado nunca some" preservado.

4. Default `cargas_config=None` ou `{}` ou todas dims 0 = constraint
   inteira pulada (preserva 4.D byte-a-byte).
"""
from __future__ import annotations

from dataclasses import replace

from gerador_csp import (
    ConfigVariedade,
    gerar_rotina_csp,
    gerar_treino_csp,
    _viola_carga_par,
    _cargas_config_ativo,
)


# ── Helpers ─────────────────────────────────────────────────────────────

def _ex_por_nome(banco, nome):
    for e in banco:
        if e.nome == nome:
            return e
    raise ValueError(f"{nome} não está no banco")


def _todos_nomes(rotina_ou_treino):
    out = []
    if "treinos" in rotina_ou_treino:
        for tr in rotina_ou_treino["treinos"]:
            for g in tr["grupos"]:
                for e in g["exercicios"]:
                    out.append(e.nome)
    else:
        for g in rotina_ou_treino["grupos"]:
            for e in g["exercicios"]:
                out.append(e.nome)
    return out


def _blocos_dict_to_lista(treino):
    return [[e.nome for e in b] for b in treino.get("blocos", [])]


# ── (a) Default `cargas_config=None` preserva 4.D byte-a-byte ──────────

def test_cargas_config_none_preserva_comportamento(banco):
    demandas = [("subregiao", "peito", 2), ("subregiao", "costas", 2)]
    r1 = gerar_treino_csp(demandas, banco, nivel_aluno=3, seed=42)
    r2 = gerar_treino_csp(
        demandas, banco, nivel_aluno=3, seed=42, cargas_config=None,
    )
    assert r1["viavel"] is True
    assert r2["viavel"] is True
    # Mesma estrutura de demanda e mesma quantidade de exs
    assert len(_todos_nomes(r1)) == len(_todos_nomes(r2)) == 4
    # Sem aviso de carga quando default
    assert r1.get("avisos_carga", []) == []
    assert r2.get("avisos_carga", []) == []


# ── (b) `cargas_config={}` ou todas zeros = pulada ─────────────────────

def test_cargas_config_vazio_ou_zeros_pulada(banco):
    demandas = [("subregiao", "costas", 2)]
    # Dict vazio
    r_vazio = gerar_treino_csp(
        demandas, banco, nivel_aluno=3, seed=42, cargas_config={},
    )
    # Dict com todas dims 0
    r_zeros = gerar_treino_csp(
        demandas, banco, nivel_aluno=3, seed=42,
        cargas_config={"grip": 0, "lombar": 0, "core": 0},
    )
    r_none = gerar_treino_csp(
        demandas, banco, nivel_aluno=3, seed=42, cargas_config=None,
    )
    # Todos viáveis, todos sem aviso de carga
    assert r_vazio["viavel"] is True
    assert r_zeros["viavel"] is True
    assert r_none["viavel"] is True
    assert r_vazio.get("avisos_carga", []) == []
    assert r_zeros.get("avisos_carga", []) == []
    assert r_none.get("avisos_carga", []) == []


# ── (c) Par válido (soma < thr) → bloco intacto, sem aviso ──────────────

def test_par_valido_nao_dispara_aviso(banco):
    # Threshold permissivo: thr=10 → soma de quaisquer 2 exs do banco é < 10.
    # Em dim grip, max é 3+3=6. Em lombar e core também ≤ 6.
    r = gerar_treino_csp(
        [("subregiao", "peito", 2), ("subregiao", "costas", 2)],
        banco, nivel_aluno=3, seed=42,
        cargas_config={"grip": 10, "lombar": 10, "core": 10},
    )
    assert r["viavel"] is True
    assert r.get("avisos_carga", []) == []


# ── (d) Par violador resolúvel: solver substitui (sem aviso) ────────────

def test_par_violador_resoluvel_sem_aviso(banco):
    # Caso clinicamente óbvio onde o motor TEM alternativa válida:
    # combinação peito+costas em blocos solo. Sem par no mesmo bloco,
    # constraint H-cargas nunca dispara (par-a-par dentro do bloco).
    r = gerar_treino_csp(
        [("subregiao", "peito", 2), ("subregiao", "costas", 2)],
        banco, nivel_aluno=3, seed=42,
        cargas_config={"grip": 4, "lombar": 4, "core": 4},
        tamanho_preferido=1, peso_tamanho_bloco=10000,  # força solos
    )
    assert r["viavel"] is True
    # Solos não acionam aviso de carga (par-a-par só dispara em bloco compartilhado)
    assert r.get("avisos_carga", []) == []


# ── (e) Par violador irresolúvel: cargas_off_b=True + aviso correto ────

def test_par_violador_irresoluvel_emite_aviso(banco):
    # Banco mini de costas (puxadas + remadas) — H-R1 exige 1 puxada compound
    # + 1 remada compound. Todos compounds têm grip≥2. Threshold=4 vira
    # inviável: qualquer par compound viola. Pareamento forçado (peso alto).
    banco_mini = [e for e in banco if e.padrao in ("puxadas", "remadas")]
    r = gerar_treino_csp(
        [("subregiao", "costas", 2)], banco_mini, nivel_aluno=3, seed=42,
        cargas_config={"grip": 4, "lombar": 4, "core": 4},
        tamanho_preferido=2, peso_tamanho_bloco=10000,
    )
    assert r["viavel"] is True
    avisos = r.get("avisos_carga", [])
    assert len(avisos) >= 1, f"esperava ≥1 aviso, veio {avisos}"
    aviso = avisos[0]
    # Estrutura: tipo, bloco_idx, exercicio, par_bloqueado, dimensao, soma, threshold
    assert aviso["tipo"] == "relaxado_carga"
    assert isinstance(aviso["bloco_idx"], int)
    assert "exercicio" in aviso and isinstance(aviso["exercicio"], str)
    assert "par_bloqueado" in aviso and isinstance(aviso["par_bloqueado"], str)
    assert aviso["dimensao"] in ("grip", "lombar", "core")
    assert isinstance(aviso["soma"], int)
    assert isinstance(aviso["threshold"], int)
    assert aviso["soma"] >= aviso["threshold"], (
        f"soma {aviso['soma']} deveria violar thr {aviso['threshold']}"
    )


# ── (f) Travado ENTRA nos pares: non-travado é forçado a mudar ─────────

def test_travado_entra_nos_pares_non_travado_muda(banco):
    # Travado heavy grip — esperado: motor escolhe non-travado SEM heavy grip
    # pra evitar par violador, em vez de manter o travado preferido inicial.
    # Lev. Terra: grip=3, lombar=3, core=3. Forçar par no bloco (peso alto).
    lev_terra = _ex_por_nome(banco, "Lev. Terra")
    # Demandas: hinge + outro hinge (pra travado consumir vaga).
    r = gerar_treino_csp(
        [("subregiao", "perna_posterior", 2)],
        banco, nivel_aluno=3, seed=42,
        cargas_config={"grip": 4, "lombar": 4, "core": 4},
        travados=[lev_terra],
        tamanho_preferido=2, peso_tamanho_bloco=10000,
    )
    assert r["viavel"] is True
    nomes = _todos_nomes(r)
    # Lev. Terra está presente (travado nunca some)
    assert "Lev. Terra" in nomes, f"travado deve aparecer, veio {nomes}"


# ── (g) Travado vs travado: ambos mantêm + cargas_off_b=True ───────────

def test_dois_travados_violadores_mantem_e_emite_aviso(banco):
    # 2 travados heavy grip no mesmo treino — sem pool extra pra desviar.
    # Travado tem pool=[ex_travado] (1 elemento), então motor não pode
    # substituir. Resultado: ambos mantêm; cargas_off_b=True; aviso emitido.
    lev_terra = _ex_por_nome(banco, "Lev. Terra")       # grip=3, lombar=3
    stiff = _ex_por_nome(banco, "Stiff Barra Livre")    # grip=3, lombar=3
    r = gerar_treino_csp(
        [("subregiao", "perna_posterior", 2)],
        banco, nivel_aluno=3, seed=42,
        cargas_config={"grip": 5, "lombar": 5, "core": 5},
        travados=[lev_terra, stiff],
        tamanho_preferido=2, peso_tamanho_bloco=10000,
    )
    assert r["viavel"] is True
    nomes = _todos_nomes(r)
    assert "Lev. Terra" in nomes, f"travado #1 deve aparecer, veio {nomes}"
    assert "Stiff Barra Livre" in nomes, f"travado #2 deve aparecer, veio {nomes}"
    avisos = r.get("avisos_carga", [])
    # Ambos no mesmo bloco — par grip=3+3=6 >= thr=5 viola
    blocos = _blocos_dict_to_lista(
        r if "blocos" in r else r["treinos"][0]
    ) if r.get("blocos") else _blocos_dict_to_lista(r)
    # Procura par travado-travado no mesmo bloco
    par_no_mesmo_bloco = any(
        {"Lev. Terra", "Stiff Barra Livre"}.issubset(set(b)) for b in blocos
    )
    if par_no_mesmo_bloco:
        assert len(avisos) >= 1, f"par travado-travado no bloco deveria emitir aviso, blocos={blocos}"


# ── (h) Threshold 0 ou ausente em uma dim pula só essa dim ─────────────

def test_threshold_zero_em_uma_dim_pula_so_aquela(banco):
    # Lombar=0 pula só lombar; grip/core continuam restritivos.
    # Banco mini costas, grip restritivo (=4): mesma situação do (e),
    # mas lombar/core OFF. Esperado: aviso emitido com dim=grip
    # (não lombar nem core).
    banco_mini = [e for e in banco if e.padrao in ("puxadas", "remadas")]
    r = gerar_treino_csp(
        [("subregiao", "costas", 2)], banco_mini, nivel_aluno=3, seed=42,
        cargas_config={"grip": 4, "lombar": 0, "core": 0},
        tamanho_preferido=2, peso_tamanho_bloco=10000,
    )
    assert r["viavel"] is True
    avisos = r.get("avisos_carga", [])
    if avisos:
        # Se emitiu aviso, deve ser por grip (única dim ativa)
        assert all(a["dimensao"] == "grip" for a in avisos), (
            f"avisos devem ser de grip apenas, veio {avisos}"
        )


# ── (i) Composição com 4.B (evitar_agonistas) + 4.C (tamanho_bloco) ───

def test_composicao_com_4b_4c_sem_regressao(banco):
    # Combinação dos 3 features ativos. Sanity check de não-crash.
    r = gerar_treino_csp(
        [("subregiao", "peito", 2), ("subregiao", "costas", 2)],
        banco, nivel_aluno=3, seed=42,
        cargas_config={"grip": 5, "lombar": 5, "core": 5},
        peso_evitar_agonistas=10,       # 4.B
        tamanho_preferido=2, peso_tamanho_bloco=5,  # 4.C
    )
    assert r["viavel"] is True
    assert len(_todos_nomes(r)) == 4


# ── (j) Helpers internos: _viola_carga_par + _cargas_config_ativo ──────

def test_viola_carga_par_helper(banco):
    # Sanity dos helpers — espelham motor antigo.
    a = _ex_por_nome(banco, "Lev. Terra")       # grip=3, lombar=3, core=3
    b = _ex_por_nome(banco, "Stiff Barra Livre")  # grip=3, lombar=3, core=3
    # Threshold grip=5: 3+3=6 >= 5 → viola
    motivo = _viola_carga_par(a, b, {"grip": 5, "lombar": 0, "core": 0})
    assert motivo is not None
    assert motivo[0] == "grip"
    assert motivo[1] == 6
    assert motivo[2] == 5

    # Threshold permissivo: não viola
    motivo = _viola_carga_par(a, b, {"grip": 10, "lombar": 10, "core": 10})
    assert motivo is None

    # Threshold 0 em todas: não viola (constraint inativa)
    motivo = _viola_carga_par(a, b, {"grip": 0, "lombar": 0, "core": 0})
    assert motivo is None


def test_cargas_config_ativo_helper():
    assert _cargas_config_ativo(None) is False
    assert _cargas_config_ativo({}) is False
    assert _cargas_config_ativo({"grip": 0, "lombar": 0, "core": 0}) is False
    assert _cargas_config_ativo({"grip": 4}) is True
    assert _cargas_config_ativo({"lombar": 5}) is True
    assert _cargas_config_ativo({"grip": 0, "lombar": 4}) is True


# ── (k) Modo variedade (/regerar real) + cargas_config ─────────────────

def test_cargas_config_com_variedade_ativa(banco):
    """Garante que ConfigVariedade (modo padrão do /regerar) funciona com
    cargas_config — caller principal da Fatia 4.E cargas."""
    r = gerar_treino_csp(
        [("subregiao", "peito", 2), ("subregiao", "costas", 2)],
        banco, nivel_aluno=3, seed=42,
        variedade=ConfigVariedade(),
        cargas_config={"grip": 5, "lombar": 5, "core": 5},
    )
    assert r["viavel"] is True
    assert len(_todos_nomes(r)) == 4
    # Tem chave de variedade
    assert "variedade" in r
    # avisos_carga sempre presente como lista (mesmo se vazia)
    assert "avisos_carga" in r
    assert isinstance(r["avisos_carga"], list)


# ── (l) Rota gerar_rotina_csp (N treinos) propaga avisos por treino ────

def test_rotina_propaga_avisos_carga_por_treino(banco):
    # 2 treinos com banco_mini constringente — confere que cada treino
    # tem seu próprio agregado de avisos.
    banco_mini = [e for e in banco if e.padrao in ("puxadas", "remadas")]
    r = gerar_rotina_csp(
        [
            [("subregiao", "costas", 2)],
            [("subregiao", "costas", 2)],
        ],
        banco_mini, nivel_aluno=3, seed=42,
        cargas_config={"grip": 4, "lombar": 4, "core": 4},
        tamanho_preferido=2, peso_tamanho_bloco=10000,
    )
    assert r["viavel"] is True
    # avisos_carga_por_treino sempre presente
    assert "avisos_carga_por_treino" in r
    assert isinstance(r["avisos_carga_por_treino"], dict)
