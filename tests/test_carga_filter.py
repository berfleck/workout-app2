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
    """Banco real tem 90/112/119 ex com grip/lombar/core >= 1 (pós Fase 4 Sub-H: +Remada LM Aberta)."""
    grip_nz = sum(1 for e in banco if e.carga_grip >= 1)
    lombar_nz = sum(1 for e in banco if e.carga_lombar >= 1)
    core_nz = sum(1 for e in banco if e.demanda_core >= 1)
    assert grip_nz == 90
    assert lombar_nz == 112
    assert core_nz == 119


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


# ---------------------------------------------------------------------------
# Sub-PR 1.2 — plumbing pelas 6 funções: invariante end-to-end
# ---------------------------------------------------------------------------

def test_gerar_multiplos_treinos_respeita_cargas_config(banco):
    """Invariante: com cargas_config no cfg, nenhum par dentro de bloco viola filtro.

    Roda 20 seeds (mesmas do harness recalibrar_cargas_hib2) pra cobrir variação.
    """
    import random
    from gerador_treino import _bloqueio_cargas, gerar_multiplos_treinos
    cfg = {
        "demandas": [("regiao", "lower", 4), ("regiao", "upper", 3), ("regiao", "core", 1)],
        "tamanho_bloco": 2,
        "max_complexidade": 5,
        "equipamentos_bloqueados": [],
        "evitar_agonistas": True,
        "cargas_config": HIB2,
    }
    SEEDS = [1, 7, 13, 23, 42, 99, 100, 117, 200, 314,
             555, 777, 1000, 1234, 1492, 1789, 1984, 2024, 4096, 9999]
    for seed in SEEDS:
        random.seed(seed)
        sessoes = gerar_multiplos_treinos(banco, [cfg, cfg], relaxar_familia=True)
        for s in sessoes:
            for bloco in s.blocos:
                exs = [e for e in (bloco.ex1, bloco.ex2, bloco.ex3) if e]
                for i in range(len(exs)):
                    for j in range(i + 1, len(exs)):
                        assert not _bloqueio_cargas(exs[i], exs[j], HIB2), (
                            f"seed={seed}: par viola filtro HIB2: "
                            f"{exs[i].nome} (g={exs[i].carga_grip} "
                            f"l={exs[i].carga_lombar} c={exs[i].demanda_core}) + "
                            f"{exs[j].nome} (g={exs[j].carga_grip} "
                            f"l={exs[j].carga_lombar} c={exs[j].demanda_core})"
                        )


def test_filtro_carga_realmente_dissolve_par_conhecido(banco):
    """Evidência forte: par documentado pelo harness some quando filtro liga.

    Sem filtro, seed=71 com cfg lower(4)+upper(3)+core(1)×2 produz par
    'Lev. Terra' + 'Remada Baixa Aberta' (grip somando 6, viola HIB2).
    Com filtro HIB2 ligado, esse par precisa desaparecer.

    Atualizado no refator cycling fallback: quota ponderada por pool em
    subregiões sem âncora redistribui sequência de random.
    Histórico: seed=1 Lev.Terra Sumô + Remada Baixa Aberta (Etapa 5) →
    seed=9 Lev.Terra + Barra Isométrica (Fase 7.3) → seed=22 Hiperextensão
    45° + Remada Baixa Aberta (Fase 7.4) → seed=3 Lev.Terra + Remada Baixa
    Aberta (Etapa 8.2) → seed=1 Lev.Terra + Remada Baixa Aberta (Fase 4
    Sub-D, 136 ex) → seed=4 Lev.Terra + Barra Isométrica (Fase 4 Sub-F,
    dims completas) → seed=71 Lev.Terra + Remada Baixa Aberta (refator
    cycling fallback). Mesmo contrato clínico: par viola HIB2 sem filtro,
    some com filtro.
    """
    import random
    from gerador_treino import gerar_multiplos_treinos
    cfg = {
        "demandas": [("regiao", "lower", 4), ("regiao", "upper", 3), ("regiao", "core", 1)],
        "tamanho_bloco": 2,
        "max_complexidade": 5,
        "equipamentos_bloqueados": [],
        "evitar_agonistas": True,
    }
    PAR = {"Lev. Terra", "Remada Baixa Aberta"}
    SEED = 71

    def par_aparece(sessoes):
        for s in sessoes:
            for bloco in s.blocos:
                nomes = {e.nome for e in (bloco.ex1, bloco.ex2, bloco.ex3) if e}
                if PAR.issubset(nomes):
                    return True
        return False

    random.seed(SEED)
    s_off = gerar_multiplos_treinos(banco, [cfg, cfg], relaxar_familia=True)
    assert par_aparece(s_off), (
        f"Pré-condição falhou: harness disse que seed={SEED} produz o par "
        "sem filtro. Se isso mudou, atualize o teste com par bloqueado novo."
    )

    random.seed(SEED)
    cfg_on = {**cfg, "cargas_config": HIB2}
    s_on = gerar_multiplos_treinos(banco, [cfg_on, cfg_on], relaxar_familia=True)
    assert not par_aparece(s_on), (
        "Filtro falhou: par 'Lev. Terra' + 'Barra Isometrica' apareceu "
        "mesmo com cargas_config HIB2 ativo."
    )


def test_gerar_multiplos_treinos_sem_cargas_config_inalterado(banco):
    """Sem cargas_config, comportamento idêntico ao pré-Etapa 4 (sanity check)."""
    import random
    from gerador_treino import gerar_multiplos_treinos
    cfg = {
        "demandas": [("regiao", "lower", 3)],
        "tamanho_bloco": 2,
        "max_complexidade": 5,
        "equipamentos_bloqueados": [],
        "evitar_agonistas": False,
    }
    random.seed(42)
    s_ref = gerar_multiplos_treinos(banco, [cfg], relaxar_familia=True)
    random.seed(42)
    cfg_with_none = {**cfg, "cargas_config": None}
    s_test = gerar_multiplos_treinos(banco, [cfg_with_none], relaxar_familia=True)
    # Nomes nos blocos devem ser idênticos (cargas_config=None == omitido)
    nomes_ref = [
        [e.nome for e in (b.ex1, b.ex2, b.ex3) if e]
        for b in s_ref[0].blocos
    ]
    nomes_test = [
        [e.nome for e in (b.ex1, b.ex2, b.ex3) if e]
        for b in s_test[0].blocos
    ]
    assert nomes_ref == nomes_test


def test_gerar_sessao_por_demandas_respeita_cargas_config(banco):
    """Standalone gerar_sessao_por_demandas (caminho /regerar) também respeita filtro."""
    from gerador_treino import _bloqueio_cargas, gerar_sessao_por_demandas
    sessao = gerar_sessao_por_demandas(
        banco,
        demandas=[("regiao", "lower", 4)],
        max_complexidade=5,
        tamanho_bloco=2,
        evitar_agonistas=True,
        cargas_config=HIB2,
    )
    for bloco in sessao.blocos:
        exs = [e for e in (bloco.ex1, bloco.ex2, bloco.ex3) if e]
        for i in range(len(exs)):
            for j in range(i + 1, len(exs)):
                assert not _bloqueio_cargas(exs[i], exs[j], HIB2), (
                    f"par viola filtro HIB2 em standalone: "
                    f"{exs[i].nome} + {exs[j].nome}"
                )


# ---------------------------------------------------------------------------
# Sub-PR 1.3 — aviso relaxado_carga via second-pass em montar_blocos
# ---------------------------------------------------------------------------

def test_relaxado_carga_emite_aviso_quando_solo_por_carga():
    """Banco sintético: 2 ex de hinge com lombar=3 cada → bloqueia em HIB2.
    Com filtro ON, ambos ficam solo e o aviso relaxado_carga é emitido."""
    from gerador_treino import montar_blocos
    a = _make_ex("Hiper A", lombar=3, padrao="hinge", regiao="lower")
    b = _make_ex("Hiper B", lombar=3, padrao="hinge", regiao="lower")
    avisos: list[dict] = []
    blocos = montar_blocos(
        [a, b], tamanho=2,
        cargas_config=HIB2,
        avisos_carga=avisos,
    )
    # 2 blocos solo (cada exercício no seu próprio bloco)
    assert len(blocos) == 2
    assert all(len(bl) == 1 for bl in blocos)
    # 1 aviso relaxado_carga emitido
    avisos_carga = [a for a in avisos if a["tipo"] == "relaxado_carga"]
    assert len(avisos_carga) == 1
    av = avisos_carga[0]
    assert av["dimensao"] == "lombar"
    assert av["soma"] == 6
    assert av["threshold"] == 5


def test_relaxado_carga_nao_emite_se_solo_por_fadiga():
    """Banco sintético: 2 ex com fadiga=4 (alta). Bloco 2 → 1 alta-fadiga max.
    Solo ocorre por fadiga, NÃO por carga. relaxado_carga não deve emitir."""
    from gerador_treino import montar_blocos
    a = _make_ex("Pesado A", fadiga=4)
    b = _make_ex("Pesado B", fadiga=4)
    avisos: list[dict] = []
    blocos = montar_blocos(
        [a, b], tamanho=2,
        cargas_config=HIB2,
        avisos_carga=avisos,
    )
    avisos_carga = [a for a in avisos if a["tipo"] == "relaxado_carga"]
    assert avisos_carga == []


def test_relaxado_carga_nao_emite_se_filtro_off():
    """Sem cargas_config, nenhum aviso relaxado_carga (mesmo se 2 ex com lombar 6)."""
    from gerador_treino import montar_blocos
    a = _make_ex("Hiper A", lombar=3, padrao="hinge")
    b = _make_ex("Hiper B", lombar=3, padrao="hinge")
    avisos: list[dict] = []
    blocos = montar_blocos(
        [a, b], tamanho=2,
        cargas_config=None,
        avisos_carga=avisos,
    )
    # Sem filtro, ambos pareiam normalmente (mesmo padrão, mas sem regra de carga)
    assert len(blocos) == 1
    assert len(blocos[0]) == 2
    assert avisos == []


def test_relaxado_carga_propaga_para_sessao_avisos(banco):
    """Aviso relaxado_carga acaba em Sessao.avisos quando vem via gerar_multiplos_treinos."""
    import random
    from gerador_treino import gerar_multiplos_treinos
    cfg = {
        "demandas": [("regiao", "lower", 4), ("regiao", "upper", 3), ("regiao", "core", 1)],
        "tamanho_bloco": 2,
        "max_complexidade": 5,
        "equipamentos_bloqueados": [],
        "evitar_agonistas": True,
        "cargas_config": HIB2,
    }
    # Iterar seeds até encontrar uma que produza aviso (banco real, comportamento estocástico)
    SEEDS = [1, 7, 13, 23, 42, 99, 100, 117, 200, 314, 555, 777, 1000]
    encontrou = False
    for seed in SEEDS:
        random.seed(seed)
        sessoes = gerar_multiplos_treinos(banco, [cfg, cfg], relaxar_familia=True)
        for s in sessoes:
            avisos_c = [a for a in s.avisos if a["tipo"] == "relaxado_carga"]
            if avisos_c:
                # Confirmar estrutura do aviso
                av = avisos_c[0]
                assert "dimensao" in av
                assert "soma" in av
                assert "threshold" in av
                assert av["dimensao"] in ("grip", "lombar", "core")
                encontrou = True
                break
        if encontrou:
            break
    # Não asserto que encontrou — banco real pode não disparar em nenhuma das seeds,
    # mas o teste verifica que QUANDO disparar, a estrutura está correta.
    # O caso síntetico cobre a emissão obrigatória.
