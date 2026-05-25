"""Testes da Frente E.1 — adapter do /gerar pra `gerar_rotina_csp`.

Frente E.1 (2026-05-26) substitui o motor antigo (`gerar_multiplos_treinos`)
no caminho de execução do /gerar pelo motor CSP. Esses testes cobrem os
helpers novos do adapter em `app_flask.py`:

- `_tipo_label_da_cfg(cfg)`: deriva `Sessao.tipo` da cfg (template/hierarquia).
- `_treino_dict_csp_pra_sessao(treino_dict, tipo_label)`: converte um item
  de `resultado["treinos"]` em Sessao com blocos estruturados (4.A) e marker
  rationale={"gerador": "csp"}.
- `_primeiro_treino_por_subregiao(demandas_por_treino)`: mapa subregião →
  primeiro idx de treino com demanda associada (rotear avisos cross-treino).
- `_distribuir_avisos_rotina_csp(resultado, sessoes, demandas_por_treino)`:
  distribui h_r1/h_a1 (cross-treino) + avisos_carga/relaxados (per-treino).

Decisões fechadas no handoff 2026-05-26:
- Clean break (sem flag de transição).
- Bíceps INFEASIBLE em biceps(2) é NO-OP nesta sessão.
- Avisos h_a1_degradado/h_r1_degradado como tipos separados.
- Toggle `usar_historico_r1` ON → `familias_proibidas` hard cross-rotina
  (CSP não tem S-H1 ainda; vira refinamento do Bloco 4).
"""
from __future__ import annotations

from app_flask import (
    _distribuir_avisos_rotina_csp,
    _primeiro_treino_por_subregiao,
    _tipo_label_da_cfg,
    _treino_dict_csp_pra_sessao,
)
from gerador_csp import ConfigVariedade, gerar_rotina_csp
from gerador_treino import Exercicio, Sessao, SuperSerie


# ── _tipo_label_da_cfg ──────────────────────────────────────────────────


def test_tipo_label_modo_template():
    cfg = {"modo": "template", "template_nome": "Full Body 2T",
           "padroes": ["squat_bilateral", "empurrar_compostos"]}
    assert _tipo_label_da_cfg(cfg) == "Full Body 2T"


def test_tipo_label_modo_hierarquia_com_demandas():
    cfg = {"modo": "hierarquia", "demandas": [
        ("subregiao", "peito", 2), ("subregiao", "costas", 3),
    ]}
    assert _tipo_label_da_cfg(cfg) == "peito(2) + costas(3)"


def test_tipo_label_template_sem_nome_cai_pra_padroes():
    cfg = {"modo": "template", "template_nome": "",
           "padroes": ["squat_bilateral", "hinge"]}
    assert _tipo_label_da_cfg(cfg) == "squat_bilateral + hinge"


def test_tipo_label_fallback_sessao():
    """cfg sem template_nome, sem demandas, sem padroes — não deve quebrar."""
    assert _tipo_label_da_cfg({}) == "Sessão"


# ── _treino_dict_csp_pra_sessao ─────────────────────────────────────────


def _ex_falso(nome, padrao="empurrar_compostos", subregiao="peito"):
    """Constrói Exercicio mínimo pra testar adapter (sem banco real)."""
    return Exercicio(
        nome=nome, variacao_de=None, eq_primario="halteres", eq_secundario=None,
        regiao="upper", subregiao=subregiao, padrao=padrao, purpose="compound",
        unilateral="bilateral", complexidade=2, fadiga=2, circuito=None,
        similaridade=None, musculo_primario="peitoral", obs="",
    )


def test_treino_dict_para_sessao_blocos_pareados():
    """Bloco de 2 ex vira SuperSerie com ex1+ex2 e label correto."""
    ex_a, ex_b = _ex_falso("Supino Reto"), _ex_falso("Crucifixo")
    treino_dict = {"blocos": [[ex_a, ex_b]]}
    s = _treino_dict_csp_pra_sessao(treino_dict, "peito(2)")
    assert s.tipo == "peito(2)"
    assert len(s.blocos) == 1
    b = s.blocos[0]
    assert b.label == "A"
    assert b.ex1.nome == "Supino Reto"
    assert b.ex2.nome == "Crucifixo"
    assert b.ex3 is None


def test_treino_dict_para_sessao_marker_gerador_csp():
    """Todo ex devolvido pelo adapter carrega rationale={'gerador': 'csp'}.
    Necessário pro /decisoes detectar e renderizar mensagem amber."""
    ex = _ex_falso("Apoio")
    s = _treino_dict_csp_pra_sessao({"blocos": [[ex]]}, "peito(1)")
    assert s.blocos[0].ex1.rationale == {"gerador": "csp"}


def test_treino_dict_para_sessao_nao_muta_banco():
    """`dataclasses.replace` deve criar nova instância — ex original do
    banco intocado (decisão Frente C)."""
    ex = _ex_falso("Supino")
    assert ex.rationale is None
    s = _treino_dict_csp_pra_sessao({"blocos": [[ex]]}, "x")
    assert ex.rationale is None  # original
    assert s.blocos[0].ex1.rationale == {"gerador": "csp"}  # cópia marcada


def test_treino_dict_para_sessao_labels_acima_de_z():
    """Labels A..Z..AA pra blocos a partir do 26°."""
    exs = [_ex_falso(f"Ex {i}") for i in range(27)]
    treino_dict = {"blocos": [[ex] for ex in exs]}
    s = _treino_dict_csp_pra_sessao(treino_dict, "muitos")
    assert s.blocos[0].label == "A"
    assert s.blocos[25].label == "Z"
    assert s.blocos[26].label == "AA"


def test_treino_dict_para_sessao_inicializa_avisos_relaxados_vazios():
    """`avisos` e `relaxados` começam como listas vazias — distribuição
    posterior popula."""
    s = _treino_dict_csp_pra_sessao({"blocos": []}, "x")
    assert s.avisos == []
    assert s.relaxados == []


# ── _primeiro_treino_por_subregiao ──────────────────────────────────────


def test_primeiro_treino_subregiao_direta():
    """Demanda `("subregiao", X, _)` mapeia X → primeiro treino com X."""
    demandas_por_treino = [
        [("subregiao", "peito", 2), ("subregiao", "costas", 2)],
        [("subregiao", "ombro", 2)],
    ]
    mapa = _primeiro_treino_por_subregiao(demandas_por_treino)
    assert mapa["peito"] == 0
    assert mapa["costas"] == 0
    assert mapa["ombro"] == 1


def test_primeiro_treino_subregiao_via_padrao():
    """Demanda `("padrao", P, _)` mapeia subregiões de P."""
    demandas_por_treino = [
        [("padrao", "empurrar_compostos", 2)],  # → peito
    ]
    mapa = _primeiro_treino_por_subregiao(demandas_por_treino)
    assert mapa.get("peito") == 0


def test_primeiro_treino_subregiao_via_regiao():
    """Demanda `("regiao", R, _)` mapeia todas subregiões de R."""
    demandas_por_treino = [
        [("regiao", "upper", 4)],
    ]
    mapa = _primeiro_treino_por_subregiao(demandas_por_treino)
    # upper tem peito, costas, ombro, bracos
    assert "peito" in mapa
    assert "costas" in mapa
    assert mapa["peito"] == 0


def test_primeiro_treino_nao_sobrescreve():
    """Se subregião aparece em treinos 0 E 1, mapa fica em 0 (primeiro wins)."""
    demandas_por_treino = [
        [("subregiao", "peito", 1)],
        [("subregiao", "peito", 2)],
    ]
    mapa = _primeiro_treino_por_subregiao(demandas_por_treino)
    assert mapa["peito"] == 0


# ── _distribuir_avisos_rotina_csp ───────────────────────────────────────


def _sessoes_falsas(n=2):
    out = []
    for _ in range(n):
        s = Sessao(tipo="x", blocos=[])
        s.avisos = []
        s.relaxados = []
        out.append(s)
    return out


def test_distribuir_h_r1_degradado_no_treino_certo():
    """h_r1_aplicadas degraded=True com subregiao=peito vai pro treino com
    demanda subregiao peito (treino 1, não treino 0 que tem só costas)."""
    sessoes = _sessoes_falsas(2)
    demandas_por_treino = [
        [("subregiao", "costas", 2)],
        [("subregiao", "peito", 2)],
    ]
    resultado = {
        "h_r1_aplicadas": [
            {"subregiao": "peito", "eixo": "compound", "degraded": True,
             "motivo": "pool sem candidato"},
        ],
    }
    _distribuir_avisos_rotina_csp(resultado, sessoes, demandas_por_treino)
    assert sessoes[0].avisos == []  # costas — sem aviso
    assert len(sessoes[1].avisos) == 1
    av = sessoes[1].avisos[0]
    assert av["tipo"] == "h_r1_degradado"
    assert av["subregiao"] == "peito"
    assert av["eixo"] == "compound"


def test_distribuir_h_r1_nao_degradado_ignorado():
    """h_r1_aplicadas com degraded=False NÃO vira aviso (só sinaliza
    aplicação bem-sucedida da constraint)."""
    sessoes = _sessoes_falsas(1)
    resultado = {
        "h_r1_aplicadas": [
            {"subregiao": "peito", "eixo": "compound", "degraded": False,
             "n_termos": 5, "n_slots": 2},
        ],
    }
    _distribuir_avisos_rotina_csp(resultado, sessoes, [[("subregiao", "peito", 2)]])
    assert sessoes[0].avisos == []


def test_distribuir_h_a1_degradado_no_treino_certo():
    """h_a1 degraded gera aviso h_a1_degradado com padrao_obrigatorio."""
    sessoes = _sessoes_falsas(2)
    demandas_por_treino = [
        [("subregiao", "peito", 2)],
        [("subregiao", "ombro", 2)],
    ]
    resultado = {
        "h_a1_aplicadas": [
            {"subregiao": "ombro", "padrao_obrigatorio": "ombro_composto",
             "degraded": True, "motivo": "pool sem candidato"},
        ],
    }
    _distribuir_avisos_rotina_csp(resultado, sessoes, demandas_por_treino)
    assert sessoes[0].avisos == []
    assert len(sessoes[1].avisos) == 1
    av = sessoes[1].avisos[0]
    assert av["tipo"] == "h_a1_degradado"
    assert av["subregiao"] == "ombro"
    assert av["padrao_obrigatorio"] == "ombro_composto"


def test_distribuir_avisos_carga_per_treino():
    """avisos_carga_por_treino[t] é por treino — passa direto pra sessoes[t]."""
    sessoes = _sessoes_falsas(2)
    aviso = {"tipo": "relaxado_carga", "exercicio": "Lev. Terra",
             "par_bloqueado": "Stiff", "dimensao": "lombar", "soma": 10,
             "threshold": 5}
    resultado = {"avisos_carga_por_treino": {1: [aviso]}}
    _distribuir_avisos_rotina_csp(resultado, sessoes, [[], []])
    assert sessoes[0].avisos == []
    assert sessoes[1].avisos == [aviso]


def test_distribuir_relaxados_popula_sessao_e_gera_aviso():
    """relaxados_por_treino[t] vira `sessoes[t].relaxados` + 1 aviso
    `familia_repetida` por nome."""
    ex_a = _ex_falso("Apoio", subregiao="peito")
    sessoes = _sessoes_falsas(1)
    sessoes[0].blocos = [SuperSerie(label="A", ex1=ex_a, ex2=None, ex3=None)]
    resultado = {"relaxados_por_treino": {0: ["Apoio"]}}
    _distribuir_avisos_rotina_csp(resultado, sessoes, [[("subregiao", "peito", 1)]])
    assert sessoes[0].relaxados == ["Apoio"]
    assert len(sessoes[0].avisos) == 1
    av = sessoes[0].avisos[0]
    assert av["tipo"] == "familia_repetida"
    assert av["exercicio"] == "Apoio"
    assert av["familia"] == "Apoio"  # ex sem variacao_de → familia = nome
    assert av["escopo_label"] == "peito"


def test_distribuir_fallback_para_treino_0_subregiao_desconhecida():
    """Subregião que NÃO aparece em nenhuma demanda do mapa cai no treino 0
    (defensivo, não esperado em produção)."""
    sessoes = _sessoes_falsas(2)
    resultado = {
        "h_r1_aplicadas": [
            {"subregiao": "subregiao_inexistente", "eixo": "compound",
             "degraded": True, "motivo": "x"},
        ],
    }
    _distribuir_avisos_rotina_csp(resultado, sessoes, [[], []])
    assert len(sessoes[0].avisos) == 1


# ── Integração — gerar_rotina_csp via adapter ───────────────────────────


def test_gerar_rotina_csp_integracao_minima(banco):
    """E2E mínimo: 2 treinos, motor CSP, adapter converte em 2 Sessoes
    com blocos estruturados (Fatia 4.A) e marker gerador=csp."""
    demandas_por_treino = [
        [("subregiao", "peito", 2)],
        [("subregiao", "costas", 2)],
    ]
    resultado = gerar_rotina_csp(
        demandas_por_treino, banco, nivel_aluno=3, seed=42,
        variedade=ConfigVariedade(),
    )
    assert resultado["viavel"]
    assert len(resultado["treinos"]) == 2
    sessoes = [
        _treino_dict_csp_pra_sessao(t, f"treino_{i}")
        for i, t in enumerate(resultado["treinos"])
    ]
    assert len(sessoes) == 2
    for s in sessoes:
        assert s.blocos
        for bloco in s.blocos:
            for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
                if ex is not None:
                    assert ex.rationale == {"gerador": "csp"}


def test_gerar_rotina_csp_familias_proibidas_bloqueia_pais(banco):
    """familias_proibidas hard cross-rotina (toggle historico_r1 ON):
    nenhum ex com `_familia_cross(ex) in familias` aparece na rotina."""
    from gerador_csp import _familia_cross
    # Pega família dum exercício de costas pra proibir
    ex_alvo = next(e for e in banco if e.subregiao == "costas")
    fam_alvo = _familia_cross(ex_alvo)

    demandas_por_treino = [
        [("subregiao", "costas", 2)],
    ]
    resultado = gerar_rotina_csp(
        demandas_por_treino, banco, nivel_aluno=3, seed=0,
        familias_proibidas={fam_alvo},
        relaxar_familia=False,  # estrito pra forçar viabilidade ou inviabilidade
    )
    if resultado["viavel"]:
        for tr in resultado["treinos"]:
            for g in tr["grupos"]:
                for ex in g["exercicios"]:
                    assert _familia_cross(ex) != fam_alvo, (
                        f"{ex.nome} viola familias_proibidas={fam_alvo}"
                    )
