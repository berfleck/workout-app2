"""
BF Treinamento — Versão Flask + HTMX (completa)
"""

from flask import Flask, render_template, request, send_file, redirect, url_for, jsonify, session
import os, random, json, copy, io, zipfile, unicodedata, secrets
from dataclasses import replace as _dc_replace
from pathlib import Path
from datetime import datetime
from gerador_treino import (
    carregar_banco, gerar_sessao, gerar_sessao_por_demandas, gerar_multiplos_treinos,
    substituir_exercicio, buscar_substitutos, substituir_exercicio_por,
    expandir_para_padroes, selecionar_evitando_familia,
    TEMPLATES, TEMPLATE_EPP, EXERCICIOS_POR_PADRAO,
    PADRAO_PARA_SUBREGIAO, SUBREGIAO_PARA_REGIAO,
    REGIAO_PARA_SUBREGIOES, SUBREGIAO_PARA_PADROES,
    ANCORAS_POR_REGIAO, ANCORAS_POR_SUBREGIAO,
    Exercicio, Sessao, SuperSerie,
)
from gerador_csp import ConfigVariedade, gerar_treino_csp
from gerar_imagem import gerar_png
from database import (
    init_db, migrar_json_para_sqlite,
    carregar_alunos, salvar_aluno, editar_aluno, deletar_aluno,
    definir_rotina_ativa, carregar_rotina_ativa, carregar_rotina_anterior, buscar_aluno_por_nome,
    salvar_rascunho, carregar_rascunho, limpar_rascunho,
    salvar_etiqueta_rascunho, carregar_etiqueta_rascunho,
    salvar_intent_rascunho, carregar_intent_rascunho,
    carregar_historico, carregar_registro, salvar_historico_registro,
    atualizar_historico_registro, atualizar_etiqueta_historico, deletar_historico,
    buscar_historico_por_aluno, nomes_unicos_historico,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "bf-treinamento-dev")


# ══════════════════════════════════════════════════════════════
# TOPBAR MOBILE — persistência do aluno selecionado entre páginas
# ══════════════════════════════════════════════════════════════

@app.before_request
def _track_aluno_selecionado():
    if "aluno_id" not in request.args:
        return
    aluno_id = request.args.get("aluno_id", type=int)
    if aluno_id:
        session["aluno_id"] = aluno_id
    else:
        # ?aluno_id= (vazio) limpa a seleção
        session.pop("aluno_id", None)


@app.context_processor
def _inject_topbar_aluno():
    alunos = carregar_alunos()
    sel_id = session.get("aluno_id")
    aluno = next((a for a in alunos if a["id"] == sel_id), None) if sel_id else None
    sem_rotina = sum(1 for a in alunos if not a.get("rotina_ativa_id"))
    # Estado do rascunho do aluno selecionado (drives reactividade da bb mobile)
    eh_rascunho = False
    tem_publicada = False
    intent = ""
    alteracoes = 0
    if aluno:
        eh_rascunho = bool(carregar_rascunho(aluno["id"]))
        tem_publicada = bool(aluno.get("rotina_ativa_id"))
        if eh_rascunho:
            intent = carregar_intent_rascunho(aluno["id"]) or ""
            if tem_publicada:
                alteracoes = len(diff_rascunho_vs_publicada(aluno["id"]))
    em_edicao = bool(edicao_hub and aluno and edicao_hub.get("aluno_id") == aluno["id"])
    return {
        "_topbar_alunos": alunos,
        "_topbar_aluno": aluno,
        "_topbar_tem_rotina": tem_publicada,
        "_topbar_eh_rascunho": eh_rascunho,
        "_topbar_intent": intent,
        "_topbar_alteracoes": alteracoes,
        "_topbar_em_edicao": em_edicao,
        "_nav_alunos_total": len(alunos),
        "_nav_sem_rotina": sem_rotina,
    }


# ══════════════════════════════════════════════════════════════
# DADOS
# ══════════════════════════════════════════════════════════════

banco = carregar_banco("banco_exercicios.xlsx")

SESSOES_PATH = Path("sessoes_salvas.json")

# Estado em memória
sessoes_ativas: list[Sessao] = []
configs_geradas: list[dict] = []
opcoes_globais: dict = {}
# Estado de edição do HUB (quando professor edita um treino da rotina)
edicao_hub: dict | None = None  # {"aluno_id": int, "rotina_id": str}
# Estado de criação manual pendente (permite cancelar e restaurar rascunho anterior)
criacao_manual: dict | None = None  # {"aluno_id": int, "backup": [...sessoes_dicts...], "novo_idx": int}
# Histórico de sugestões do botão substituir (cycle sem repetir até esgotar):
# (treino_idx, bloco_idx, posicao) -> {"inicial": str, "vistos": set[str]}
# "inicial" é o nome do exercício no momento do primeiro clique e nunca volta a ser sugerido.
historico_substituicoes: dict[tuple[int, int, str], dict] = {}

# Mapeamento padrão → (label curto, slug de cor) para chips no card de treino.
# Derivado dos exercícios da sessão (não da string sessao.tipo, que pode vir em níveis diferentes).
PADRAO_PARA_CHIP = {
    "empurrar_compostos": ("peito", "peito"),
    "empurrar_isolados":  ("peito", "peito"),
    "remadas":            ("costas", "costas"),
    "puxadas":            ("costas", "costas"),
    "ombro_composto":     ("ombro", "ombro"),
    "ombro_isolado":      ("ombro", "ombro"),
    "posterior_ombro":    ("ombro post.", "ombro"),
    "biceps":             ("bíceps", "bracos"),
    "triceps":            ("tríceps", "bracos"),
    "squat":              ("quadríceps", "perna-ant"),
    "squat_bilateral":    ("quadríceps", "perna-ant"),
    "squat_unilateral":   ("quadríceps", "perna-ant"),
    "hinge":              ("posterior", "perna-post"),
    "knee_flexion":       ("posterior", "perna-post"),
    "abduction":          ("abdutores", "perna-post"),
    "adduction":          ("adutores", "adutores"),
    "flexao_plantar":     ("panturrilha", "panturrilha"),
    "core_isometrico":    ("core", "core"),
    "core_dinamico":      ("core", "core"),
    # Padrões refinados Etapa 8 (Anexo 15-quater) — ainda sem exercícios
    # mapeados em 8.1 (XLSX migra em 8.2). Chips entram aqui pra label estar
    # pronto quando XLSX migrar.
    "flexao_tronco":      ("core", "core"),
    "flexao_lateral":     ("core", "core"),
    "rotacao_tronco":     ("core", "core"),
    "flexao_quadril":     ("core", "core"),
    "cardio":             ("cardio", "cardio"),
}

def tempo_relativo(data_str):
    """Retorna 'hoje', 'ontem', 'há X dias', 'há X meses' ou 'há X anos' a partir de 'dd/mm/YYYY HH:MM'."""
    if not data_str:
        return ""
    try:
        dt = datetime.strptime(data_str, "%d/%m/%Y %H:%M")
    except ValueError:
        try:
            dt = datetime.strptime(data_str.split(" ")[0], "%d/%m/%Y")
        except ValueError:
            return ""
    dias = (datetime.now().date() - dt.date()).days
    if dias < 0:
        return ""
    if dias == 0:
        return "hoje"
    if dias == 1:
        return "ontem"
    if dias < 30:
        return f"há {dias} dias"
    if dias < 365:
        meses = dias // 30
        return f"há {meses} {'mês' if meses == 1 else 'meses'}"
    anos = dias // 365
    return f"há {anos} {'ano' if anos == 1 else 'anos'}"

def subtitulo_sessao(sessao):
    """Devolve subtítulo amigável para o card do treino.

    Regras:
    - Se sessao.tipo for um nome livre (sem ' + ' e diferente de 'manual'): usa direto.
    - Senão: deriva dos chips de grupo (ex: 'Peito · Costas · Ombro'), até 3 chips.
    """
    tipo = getattr(sessao, "tipo", None) if sessao else None
    if tipo and tipo != "manual" and " + " not in tipo:
        return tipo
    chips = sessao_chips(sessao)
    if not chips:
        return ""
    labels = [c[0].capitalize() for c in chips[:3]]
    return " · ".join(labels)


def sessao_chips(sessao):
    """Retorna chips deduplicados (label, slug) para a sessão, na ordem de aparição dos exercícios."""
    if not sessao or not getattr(sessao, "blocos", None):
        return []
    chips, vistos = [], set()
    for bloco in sessao.blocos:
        for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
            if not ex or not getattr(ex, "padrao", None):
                continue
            chip = PADRAO_PARA_CHIP.get(ex.padrao)
            if not chip or chip[0] in vistos:
                continue
            vistos.add(chip[0])
            chips.append(chip)
    return chips

PADROES_LABELS = {
    "squat": "Agachamento",
    "squat_bilateral": "Agachamento bilateral",
    "squat_unilateral": "Agachamento unilateral",
    "hinge": "Extensão de quadril",
    "knee_flexion": "Flexão de joelho", "abduction": "Abdução",
    "adduction": "Adução", "flexao_plantar": "Flexão plantar",
    "empurrar_compostos": "Empurrar compostos", "empurrar_isolados": "Empurrar isolados",
    "remadas": "Remadas", "puxadas": "Puxadas",
    "ombro_composto": "Desenvolvimento", "ombro_isolado": "Elevações",
    "posterior_ombro": "Posterior de ombro",
    "biceps": "Bíceps", "triceps": "Tríceps",
    "core_isometrico": "Core isométrico", "core_dinamico": "Core dinâmico",
    # Padrões refinados Etapa 8 (Anexo 15-quater)
    "flexao_tronco": "Flexão de tronco",
    "flexao_lateral": "Flexão lateral",
    "rotacao_tronco": "Rotação de tronco",
    "flexao_quadril": "Flexão de quadril",
    "cardio": "Cardio",
}

REGIOES_LABELS = {"upper": "Membros superiores", "lower": "Membros inferiores", "core": "Core", "cardio": "Cardio"}
SUBREGIOES_LABELS = {
    "peito": "Peito", "costas": "Costas", "ombro": "Ombro", "bracos": "Braços",
    "perna_anterior": "Perna anterior", "perna_posterior": "Perna posterior",
    "adutores": "Adutores", "panturrilha": "Panturrilha",
    "core_dinamico": "Core dinâmico", "core_isometrico": "Core isométrico",
    "cardio": "Cardio",
}
ORDEM_REGIOES = ["upper", "lower", "core", "cardio"]
ORDEM_SUBREGIOES = {
    "upper": ["peito", "costas", "ombro", "bracos"],
    "lower": ["perna_anterior", "perna_posterior", "adutores", "panturrilha"],
    "core": ["core_isometrico", "core_dinamico"], "cardio": ["cardio"],
}
ORDEM_PADROES = {
    "peito": ["empurrar_compostos", "empurrar_isolados"],
    "costas": ["remadas", "puxadas"],
    "ombro": ["ombro_composto", "ombro_isolado", "posterior_ombro"],
    "bracos": ["biceps", "triceps"],
    "perna_anterior": ["squat"], "perna_posterior": ["hinge", "knee_flexion", "abduction"],
    "adutores": ["adduction"], "panturrilha": ["flexao_plantar"],
    # Etapa 8 (Anexo 15-quater): 4 padrões refinados substituem core_iso/din.
    # `flexao_lateral` só tem variante iso (Prancha Lateral) — dyn vazio.
    # `rotacao_tronco` só tem variante iso (Pallof Press) até Fase 4 cadastrar
    # Russian Twist no XLSX.
    "core_isometrico": ["flexao_tronco", "flexao_lateral", "rotacao_tronco", "flexao_quadril"],
    "core_dinamico": ["flexao_tronco", "flexao_quadril"],
    "cardio": ["cardio"],
}

todos_equipamentos = sorted({e.eq_primario for e in banco if e.eq_primario and e.eq_primario != "Sem equipamento"})
_m_set = set()
todos_musculos = []
for _e in banco:
    if _e.musculo_primario:
        for _m in _e.musculo_primario.split(","):
            _ms = _m.strip().lower()
            if _ms and _ms not in _m_set:
                _m_set.add(_ms)
                todos_musculos.append(_ms)
todos_musculos = sorted(todos_musculos)

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _normalizar(texto):
    return unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode().lower()

def filtrar_banco(texto="", padrao=None, purpose=None, unilateral=None,
                  equipamento=None, musculo=None, max_cx=5):
    resultado = list(banco)
    if padrao and padrao != "": resultado = [e for e in resultado if e.padrao == padrao]
    if purpose and purpose != "": resultado = [e for e in resultado if e.purpose == purpose]
    if unilateral and unilateral != "": resultado = [e for e in resultado if e.unilateral == unilateral]
    if equipamento and equipamento != "": resultado = [e for e in resultado if e.eq_primario == equipamento or e.eq_secundario == equipamento]
    if musculo and musculo != "":
        m_norm = _normalizar(musculo)
        resultado = [e for e in resultado if e.musculo_primario and m_norm in _normalizar(e.musculo_primario)]
    resultado = [e for e in resultado if e.complexidade <= max_cx]
    if texto.strip():
        txt_norm = _normalizar(texto.strip())
        resultado = [e for e in resultado if txt_norm in _normalizar(e.nome)]
    resultado.sort(key=lambda e: e.nome)
    return resultado

def _exercicio_to_dict(ex):
    d = {"nome": ex.nome, "variacao_de": ex.variacao_de,
            "eq_primario": ex.eq_primario, "eq_secundario": ex.eq_secundario,
            "regiao": ex.regiao, "subregiao": ex.subregiao, "padrao": ex.padrao,
            "purpose": ex.purpose,
            "unilateral": ex.unilateral, "complexidade": ex.complexidade,
            "fadiga": ex.fadiga, "circuito": ex.circuito,
            "similaridade": ex.similaridade, "musculo_primario": ex.musculo_primario,
            "obs": ex.obs, "series": ex.series, "reps": ex.reps, "rir": ex.rir}
    # Etapa 8 — rationale da decisão (Explicabilidade). Só serializa quando
    # populado, pra não inflar payloads de exs do banco / sessões legadas.
    if getattr(ex, "rationale", None) is not None:
        d["rationale"] = ex.rationale
    return d

def _dict_to_exercicio(d):
    padrao = d.get("padrao", "")
    # Frente 4: retrocompat de leitura — sessões antigas serializadas com
    # padrao="squat" são derivadas para squat_bilateral / squat_unilateral
    # via coluna unilateral. Cobre sessoes_salvas.json e historico.sessoes.
    if padrao == "squat":
        lat = (d.get("unilateral") or "").strip()
        padrao = "squat_unilateral" if lat == "unilateral" else "squat_bilateral"
    subregiao = d.get("subregiao") or PADRAO_PARA_SUBREGIAO.get(padrao, "")
    return Exercicio(nome=d["nome"], variacao_de=d.get("variacao_de"),
        eq_primario=d.get("eq_primario",""), eq_secundario=d.get("eq_secundario"),
        regiao=d.get("regiao",""), subregiao=subregiao, padrao=padrao,
        purpose=d.get("purpose",""),
        unilateral=d.get("unilateral",""), complexidade=d.get("complexidade",1),
        fadiga=d.get("fadiga",1), circuito=d.get("circuito","não"),
        similaridade=d.get("similaridade",""), musculo_primario=d.get("musculo_primario",""),
        obs=d.get("obs"), series=d.get("series"), reps=d.get("reps"), rir=d.get("rir"),
        rationale=d.get("rationale"))

def _sessao_to_dict(s):
    blocos = []
    for b in s.blocos:
        blocos.append({"label": b.label,
            "ex1": _exercicio_to_dict(b.ex1) if b.ex1 else None,
            "ex2": _exercicio_to_dict(b.ex2) if b.ex2 else None,
            "ex3": _exercicio_to_dict(b.ex3) if b.ex3 else None})
    return {"tipo": s.tipo, "blocos": blocos,
            "relaxados": list(getattr(s, "relaxados", []) or []),
            "avisos": list(getattr(s, "avisos", []) or [])}

def _dict_to_sessao(d):
    blocos = []
    for b in d["blocos"]:
        blocos.append(SuperSerie(label=b["label"],
            ex1=_dict_to_exercicio(b["ex1"]) if b.get("ex1") else None,
            ex2=_dict_to_exercicio(b["ex2"]) if b.get("ex2") else None,
            ex3=_dict_to_exercicio(b["ex3"]) if b.get("ex3") else None))
    s = Sessao(tipo=d["tipo"], blocos=blocos)
    s.relaxados = list(d.get("relaxados") or [])
    s.avisos = list(d.get("avisos") or [])
    return s


# ══════════════════════════════════════════════════════════════
# Frente C — adapter motor CSP (gerador_csp.py) → Sessao
# ══════════════════════════════════════════════════════════════

def _label_bloco_csp(i):
    """0 → 'A', 1 → 'B', ..., 25 → 'Z', 26 → 'AA'. Mesma convenção do
    gerador antigo. Em /regerar com até ~10 slots nunca passa de 'J'."""
    out = ""
    n = i
    while True:
        out = chr(ord("A") + (n % 26)) + out
        n = n // 26 - 1
        if n < 0:
            return out


def _resultado_csp_pra_sessao(resultado, tipo_label):
    """Converte o dict de saída de `gerar_treino_csp` em `Sessao`.

    Pós-Fatia 4.A (2026-05-24): consome `resultado["blocos"]` (lista de
    listas de Exercicio, estruturada pelo motor) em vez de fabricar
    SuperSeries solo a partir de `ordem_global`. Cada bloco do motor vira
    1 SuperSerie com até 3 ex (ex1/ex2/ex3). Fallback retrocompat: se
    `blocos` ausente (caller antigo), cai pra `ordem_global` 1-por-bloco.

    Marca cada Exercicio com `rationale={"gerador": "csp"}` via
    `dataclasses.replace` — não muta as instâncias do banco global. A
    página /decisoes usa esse marker pra detectar treinos do motor novo
    e mostrar mensagem em vez de timeline vazio.

    Avisos: cada eixo H-R1 marcado `degraded=True` vira aviso
    `tipo="h_r1_degradado"` em `Sessao.avisos`.
    """
    blocos: list[SuperSerie] = []
    blocos_motor = resultado.get("blocos")
    if blocos_motor is not None:
        # Fatia 4.A: blocos estruturados pelo motor.
        for i, bloco_exs in enumerate(blocos_motor):
            exs_marker = [_dc_replace(ex, rationale={"gerador": "csp"}) for ex in bloco_exs]
            ex1 = exs_marker[0] if len(exs_marker) > 0 else None
            ex2 = exs_marker[1] if len(exs_marker) > 1 else None
            ex3 = exs_marker[2] if len(exs_marker) > 2 else None
            blocos.append(SuperSerie(label=_label_bloco_csp(i),
                                     ex1=ex1, ex2=ex2, ex3=ex3))
    else:
        # Retrocompat: caller antigo (pré-4.A) — 1 ex por bloco solo.
        for i, ex in enumerate(resultado.get("ordem_global", [])):
            ex_marker = _dc_replace(ex, rationale={"gerador": "csp"})
            blocos.append(SuperSerie(label=_label_bloco_csp(i),
                                     ex1=ex_marker, ex2=None, ex3=None))

    s = Sessao(tipo=tipo_label, blocos=blocos)
    s.relaxados = []
    s.avisos = []
    for a in resultado.get("h_r1_aplicadas", []) or []:
        if a.get("degraded"):
            s.avisos.append({
                "tipo": "h_r1_degradado",
                "subregiao": a.get("subregiao"),
                "eixo": a.get("eixo"),
                "motivo": a.get("motivo", "pool sem candidato"),
            })
    return s


_NIVEL_ALUNO_PARA_CSP = {
    "iniciante": 1,
    "intermediario": 2,
    "avancado": 3,
}


def _nivel_aluno_csp(aluno_obj):
    """Mapeia o `nivel` (string) do aluno pro int 1/2/3 esperado pelo CSP.
    Default 3 (sem teto) quando aluno desconhecido ou nivel não bate.
    """
    if not aluno_obj:
        return 3
    return _NIVEL_ALUNO_PARA_CSP.get((aluno_obj.get("nivel") or "").strip(), 3)


# Frente D Fatia 3 (2026-05-24) — vetor de perfil dim "Aderência ao Tier".
# Mapeia label string do aluno pro peso int passado ao CSP.
# Chute inicial conservador: media=0 = comportamento Frente B byte-a-byte
# (slots únicos sorteados livre entre tiers). alta=2 cobre o achado #1
# (slots de padrão único caindo em Acessório) sem matar variedade DENTRO
# do tier — smoke do C4 mostrou 9/11 Principais distintos em 30 runs com
# Aderência Alta em hinge(1). Iterar pra cima se calibração indicar.
_PESO_ADERENCIA_POR_PERFIL = {
    "alta": 2,
    "media": 0,
    "baixa": 0,
}


def _peso_aderencia_csp(aluno_obj):
    """Peso int da dimensão Aderência ao Tier do perfil. 0 (default) =
    comportamento Frente B. Aluno desconhecido ou aderencia ausente =
    'media' = 0 (neutro, sem mudar nada).
    """
    if not aluno_obj:
        return 0
    return _PESO_ADERENCIA_POR_PERFIL.get((aluno_obj.get("aderencia") or "media").strip(), 0)


# Fatia 4.B (2026-05-24) — S-B1 distância funcional intra-bloco.
# Peso int passado ao CSP quando o usuário liga "evitar agonistas" na UI.
# Chute inicial conservador: 10 = dominante o bastante pra eliminar pares
# agonistas no smoke (23.4% → 0% em 20 runs com demanda 6 slots) sem ser
# desproporcional vs S-T1 (rank_max=3, viol max por par = 2).
_PESO_EVITAR_AGONISTAS_DEFAULT = 10


def _peso_evitar_agonistas_csp(cfg_r):
    """Peso int do S-B1 derivado do flag `evitar_agonistas` da cfg do form.
    True → _PESO_EVITAR_AGONISTAS_DEFAULT; False/ausente → 0 (sem efeito).
    """
    if not cfg_r or not cfg_r.get("evitar_agonistas"):
        return 0
    return _PESO_EVITAR_AGONISTAS_DEFAULT


# Fatia 4.C (2026-05-24) — S-B4 tamanho preferido do bloco.
# tamanho_bloco da UI antiga (select 1/2/3) vira parâmetro do CSP.
# Peso default 5: não dominante (compete com S-B1=10 sem dominar), mas
# suficiente pra fazer motor respeitar a preferência. Smoke isolado:
# 100% dos blocos no tamanho preferido em 15 runs por valor.
_PESO_TAMANHO_BLOCO_DEFAULT = 5


def _tamanho_e_peso_bloco_csp(cfg_r):
    """Retorna (tamanho_preferido, peso) pro CSP.
    cfg_r['tamanho_bloco'] vem da UI antiga (int 1/2/3, default 2 no parser).
    Se cfg_r presente e tamanho_bloco válido → (tamanho, _PESO_DEFAULT).
    Sem cfg ou tamanho ausente → (2, 0) (sem efeito, default neutro).
    """
    if not cfg_r:
        return (2, 0)
    tb = cfg_r.get("tamanho_bloco")
    if tb not in (1, 2, 3):
        return (2, 0)
    return (tb, _PESO_TAMANHO_BLOCO_DEFAULT)


def _cfg_antiga_pra_demandas_csp(cfg_r):
    """Converte cfg do gerador antigo em demandas CSP `(nivel, escopo, qtd)`.

    Modo hierarquia: `cfg_r["demandas"]` já vem parsed do form em formato
    compatível — passa direto, só expande aliases legados (`squat` agregado
    aparece em configs antigas mas o form parser de /gerar já o substitui;
    salvaguarda mesmo assim).

    Modo template: `cfg_r["padroes"]` + `cfg_r["exercicios_por_padrao"]`
    (EPP). Converte cada padrão+qtd em demanda `("padrao", padrao, qtd)`.
    EPP pode ser `int` ou `dict` de lateralidade — pra dict, soma os
    valores (CSP não tem split bi/uni nesse nível ainda).

    Aliases legados de padrão (do gerador antigo, pré-Frente 4 + pré-Etapa 8):
      - `"squat"` → split Bresenham ceil/floor em `squat_bilateral` +
        `squat_unilateral`.
      - `"core_isometrico"` / `"core_dinamico"` → vira demanda `subregiao`
        (são subregiões reais no XLSX, padrões dentro delas foram refinados
        em flexao_*). Tradeoff: H-T4 passa a disparar em vaga única
        (clinicamente OK — vaga única de core deve ser principal/interm).
    """
    if cfg_r.get("demandas"):
        out = []
        for n, e, q in cfg_r["demandas"]:
            out.extend(_expandir_demanda_csp(n, e, q))
        return out

    padroes = cfg_r.get("padroes") or []
    epp = cfg_r.get("exercicios_por_padrao") or {}
    out = []
    for p in padroes:
        val = epp.get(p, 0)
        qtd = sum(val.values()) if isinstance(val, dict) else int(val or 0)
        if qtd <= 0:
            continue
        out.extend(_expandir_demanda_csp("padrao", p, qtd))
    return out


def _expandir_demanda_csp(nivel, escopo, qtd):
    """Devolve list de demandas CSP-friendly pra (nivel, escopo, qtd).
    Aplica os aliases legados descritos em `_cfg_antiga_pra_demandas_csp`.
    """
    if nivel == "padrao" and escopo == "squat":
        bi = (qtd + 1) // 2
        uni = qtd // 2
        out = []
        if bi > 0:
            out.append(("padrao", "squat_bilateral", bi))
        if uni > 0:
            out.append(("padrao", "squat_unilateral", uni))
        return out
    if nivel == "padrao" and escopo in ("core_isometrico", "core_dinamico"):
        return [("subregiao", escopo, qtd)]
    return [(nivel, escopo, qtd)]


def _configs_to_serializable(configs):
    result = []
    for cfg in configs:
        c = dict(cfg)
        if "exercicios_travados" in c:
            c["exercicios_travados"] = [_exercicio_to_dict(e) for e in c["exercicios_travados"]]
        result.append(c)
    return result

def _configs_from_serializable(configs):
    if not configs:
        return []
    result = []
    for c in configs:
        cfg = dict(c)
        if "exercicios_travados" in cfg:
            cfg["exercicios_travados"] = [_dict_to_exercicio(e) for e in cfg["exercicios_travados"]]
        if cfg.get("demandas"):
            cfg["demandas"] = [tuple(d) for d in cfg["demandas"]]
        result.append(cfg)
    return result

def salvar_sessoes_disco():
    try:
        data = [_sessao_to_dict(s) for s in sessoes_ativas]
        with open(SESSOES_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception: pass
    # Auto-sincroniza rascunho do aluno quando edição partiu do HUB
    if edicao_hub and edicao_hub.get("aluno_id"):
        try:
            salvar_rascunho(edicao_hub["aluno_id"],
                            [_sessao_to_dict(s) for s in sessoes_ativas])
        except Exception: pass

def _formatar_prescricao(ex_dict):
    """Formata séries × reps · RIR; retorna '' se nada definido."""
    if not ex_dict:
        return ""
    s = ex_dict.get("series")
    r = ex_dict.get("reps")
    rir = ex_dict.get("rir")
    if not s and not r and rir in (None, ""):
        return ""
    partes = []
    if s and r:
        partes.append(f"{s}×{r}")
    elif s:
        partes.append(f"{s}×")
    elif r:
        partes.append(str(r))
    if rir not in (None, ""):
        partes.append(f"RIR {rir}")
    return " · ".join(partes)


def _estados_rascunho_por_posicao(rascunho_sessoes, publicada_sessoes):
    """Para cada posição (treino_idx, bloco_label, ei) na rotina rascunho, classifica:
    - 'mantido' — mesma exercise no mesmo lugar da publicada
    - 'swap'    — mesmo nome em outra posição da publicada (mudou de lugar)
    - 'substituido' — posição existia na publicada com OUTRO exercício
    - 'novo'    — posição nova (não existia na publicada)
    Retorna dict {(treino_idx, bloco_label, ei): estado}.

    Quando publicada_sessoes é vazio (rotina nova sem comparação), todas as
    posições viram 'novo'.
    """
    if not rascunho_sessoes:
        return {}
    publicada_sessoes = publicada_sessoes or []
    # Index por nome (1ª ocorrência) e por posição
    nomes_pub = set()
    pub_por_pos = {}
    for ti, sessao in enumerate(publicada_sessoes):
        for bloco in sessao.get("blocos", []):
            label = bloco.get("label", "")
            for ei, key in enumerate(("ex1", "ex2", "ex3")):
                ex = bloco.get(key)
                if not ex or not ex.get("nome"): continue
                nomes_pub.add(ex["nome"])
                pub_por_pos[(ti, label, ei)] = ex["nome"]
    estados = {}
    for ti, sessao in enumerate(rascunho_sessoes):
        for bloco in sessao.get("blocos", []):
            label = bloco.get("label", "")
            for ei, key in enumerate(("ex1", "ex2", "ex3")):
                ex = bloco.get(key)
                if not ex or not ex.get("nome"): continue
                pos = (ti, label, ei)
                nome = ex["nome"]
                pub_aqui = pub_por_pos.get(pos)
                if pub_aqui == nome:
                    estados[pos] = "mantido"
                elif nome in nomes_pub:
                    estados[pos] = "swap"
                elif pub_aqui is not None:
                    estados[pos] = "substituido"
                else:
                    estados[pos] = "novo"
    return estados


def _coletar_exercicios_por_nome(sessoes_dicts):
    """Retorna {nome_ex: {'ex': dict, 'treino_idx': int, 'bloco_label': str, 'ei': int, 'pos_label': 'A1'}} (1ª ocorrência)."""
    out = {}
    for ti, sessao in enumerate(sessoes_dicts or []):
        for bloco in sessao.get("blocos", []):
            label = bloco.get("label", "")
            for ei, key in enumerate(("ex1", "ex2", "ex3")):
                ex = bloco.get(key)
                if not ex or not ex.get("nome"):
                    continue
                if ex["nome"] not in out:
                    out[ex["nome"]] = {
                        "ex": ex,
                        "treino_idx": ti,
                        "bloco_label": label,
                        "ei": ei,
                        "pos_label": f"{label}{ei + 1}",
                    }
    return out


def diff_rascunho_vs_publicada(aluno_id):
    """Compara rascunho com rotina publicada (por nome de exercício, ignorando posição).
    Retorna lista de mudanças: added / removed / edited (prescrição)."""
    rascunho = carregar_rascunho(aluno_id)
    if not rascunho:
        return []
    rotina_reg = carregar_rotina_ativa(aluno_id)
    if not rotina_reg:
        # Rotina nova — não há base para comparar
        return []

    pub = _coletar_exercicios_por_nome(rotina_reg["sessoes"])
    rasc = _coletar_exercicios_por_nome(rascunho)

    nomes_pub = set(pub.keys())
    nomes_rasc = set(rasc.keys())

    mudancas = []

    # Detecta treinos inteiros removidos: treino da publicada cujos exercícios
    # nenhum aparece no rascunho. Colapsa em uma única mudança "treino_removed".
    treinos_removidos = set()
    if len(rascunho) < len(rotina_reg["sessoes"]):
        faltam = len(rotina_reg["sessoes"]) - len(rascunho)
        for ti, sessao in enumerate(rotina_reg["sessoes"]):
            nomes_treino = set()
            for bloco in sessao.get("blocos", []):
                for k in ("ex1", "ex2", "ex3"):
                    ex = bloco.get(k)
                    if ex and ex.get("nome"):
                        nomes_treino.add(ex["nome"])
            if nomes_treino and not (nomes_treino & nomes_rasc):
                treinos_removidos.add(ti)
                if len(treinos_removidos) >= faltam:
                    break

    for ti in treinos_removidos:
        mudancas.append({
            "tipo": "treino_removed",
            "ex": f"Treino {ti + 1} removido",
            "treino_idx": ti,
            "bloco_label": "",
        })

    # Adicionados (no rascunho, ausentes na publicada)
    for nome in nomes_rasc - nomes_pub:
        info = rasc[nome]
        mudancas.append({
            "tipo": "added",
            "ex": nome,
            "treino_idx": info["treino_idx"],
            "bloco_label": info["bloco_label"],
        })

    # Removidos (na publicada, ausentes no rascunho) — exclui os de treinos inteiros já colapsados
    for nome in nomes_pub - nomes_rasc:
        info = pub[nome]
        if info["treino_idx"] in treinos_removidos:
            continue
        mudancas.append({
            "tipo": "removed",
            "ex": nome,
            "treino_idx": info["treino_idx"],
            "bloco_label": info["bloco_label"],
        })

    # Editados — prescrição mudou
    for nome in nomes_rasc & nomes_pub:
        antes = _formatar_prescricao(pub[nome]["ex"])
        depois = _formatar_prescricao(rasc[nome]["ex"])
        if antes != depois:
            info = rasc[nome]
            mudancas.append({
                "tipo": "edited",
                "ex": nome,
                "treino_idx": info["treino_idx"],
                "bloco_label": info["bloco_label"],
                "antes": antes or "—",
                "depois": depois or "—",
            })

    # Movimentações: nomes em ambos cuja posição (mesmo treino) mudou.
    # Pares simétricos (A pra posição de B, B pra posição de A) são reportados como "swap".
    movs = {}
    for nome in nomes_rasc & nomes_pub:
        if pub[nome]["treino_idx"] != rasc[nome]["treino_idx"]:
            continue  # mover entre treinos é raro e fora do escopo do swap intra-treino
        if (pub[nome]["bloco_label"], pub[nome]["ei"]) != (rasc[nome]["bloco_label"], rasc[nome]["ei"]):
            movs[nome] = {
                "treino_idx": pub[nome]["treino_idx"],
                "from": pub[nome]["pos_label"],
                "to": rasc[nome]["pos_label"],
            }
    pareados = set()
    nomes_movidos = sorted(movs.keys())
    for i, na in enumerate(nomes_movidos):
        if na in pareados: continue
        for nb in nomes_movidos[i+1:]:
            if nb in pareados: continue
            if movs[na]["treino_idx"] != movs[nb]["treino_idx"]: continue
            if movs[na]["to"] == movs[nb]["from"] and movs[na]["from"] == movs[nb]["to"]:
                mudancas.append({
                    "tipo": "moved",
                    "ex": f"{movs[na]['from']} ↔ {movs[nb]['from']}",
                    "treino_idx": movs[na]["treino_idx"],
                    "bloco_label": "",
                    "nome_a": na,
                    "nome_b": nb,
                    "pos_a": movs[na]["from"],
                    "pos_b": movs[nb]["from"],
                })
                pareados.add(na); pareados.add(nb)
                break
    for nome in nomes_movidos:
        if nome in pareados: continue
        m = movs[nome]
        mudancas.append({
            "tipo": "moved",
            "ex": f"{nome}: {m['from']} → {m['to']}",
            "treino_idx": m["treino_idx"],
            "bloco_label": "",
            "nome_a": nome,
            "pos_a": m["from"],
            "pos_b": m["to"],
        })

    # Ordenar: edited primeiro (mais "ativo"), depois moved, added, removed; dentro de cada por treino_idx
    ordem = {"treino_removed": 0, "edited": 1, "moved": 2, "added": 3, "removed": 4}
    mudancas.sort(key=lambda m: (ordem.get(m["tipo"], 9), m["treino_idx"], m.get("ex", "")))
    return mudancas


def classificar_exercicios_diff(sessoes_atuais, sessoes_anteriores):
    """Para o lado-a-lado: classifica cada exercício (por nome) em mantido/adicionado/removido/editado.

    Retorna dois dicts:
      atual_status[nome] = {'status': 'mantido'|'adicionado'|'editado', 'prescr_outro': str}
      anterior_status[nome] = {'status': 'mantido'|'removido'|'editado', 'prescr_outro': str}
    """
    atuais = _coletar_exercicios_por_nome(sessoes_atuais or [])
    anteriores = _coletar_exercicios_por_nome(sessoes_anteriores or [])
    atual_status, anterior_status = {}, {}

    nomes_atuais = set(atuais.keys())
    nomes_anteriores = set(anteriores.keys())

    for nome in nomes_atuais & nomes_anteriores:
        prescr_a = _formatar_prescricao(atuais[nome]["ex"])
        prescr_p = _formatar_prescricao(anteriores[nome]["ex"])
        if prescr_a != prescr_p:
            atual_status[nome] = {"status": "editado", "prescr_outro": prescr_p or "—"}
            anterior_status[nome] = {"status": "editado", "prescr_outro": prescr_a or "—"}
        else:
            atual_status[nome] = {"status": "mantido", "prescr_outro": ""}
            anterior_status[nome] = {"status": "mantido", "prescr_outro": ""}

    for nome in nomes_atuais - nomes_anteriores:
        atual_status[nome] = {"status": "adicionado", "prescr_outro": ""}

    for nome in nomes_anteriores - nomes_atuais:
        anterior_status[nome] = {"status": "removido", "prescr_outro": ""}

    return atual_status, anterior_status


def render_draft_banner_oob(aluno_id):
    """Renderiza o banner de rascunho como fragmento OOB (swap outerHTML #draft-banner-X)."""
    if not aluno_id:
        return ""
    rascunho_sessoes = carregar_rascunho(aluno_id)
    rotina_reg = carregar_rotina_ativa(aluno_id)
    eh_rascunho = bool(rascunho_sessoes)
    tem_rotina_publicada = bool(rotina_reg)
    total_alteracoes = len(diff_rascunho_vs_publicada(aluno_id)) if (eh_rascunho and tem_rotina_publicada) else 0
    etiqueta = carregar_etiqueta_rascunho(aluno_id) if eh_rascunho else ""
    intent = carregar_intent_rascunho(aluno_id) if eh_rascunho else ""
    html = render_template("_draft_banner.html",
                           aluno_id=aluno_id,
                           eh_rascunho=eh_rascunho,
                           tem_rotina_publicada=tem_rotina_publicada,
                           total_alteracoes=total_alteracoes,
                           etiqueta_rascunho=etiqueta,
                           rascunho_intent=intent)
    # Marcar como OOB swap outerHTML
    return html.replace(f'<div id="draft-banner-{aluno_id}">',
                        f'<div id="draft-banner-{aluno_id}" hx-swap-oob="outerHTML">', 1)


def _responder_card_com_banner(t):
    """Renderiza _treino_card.html (modo editar) + OOB do banner se em edição inline do HUB.
    Substitui chamadas diretas a render_template em rotas /treino/* durante edicao_hub."""
    card = render_template("_treino_card.html", sessao=sessoes_ativas[t], idx=t,
                           modo="editar", padroes_labels=PADROES_LABELS,
                           alunos=carregar_alunos(),
                           todos_padroes=sorted(PADROES_LABELS.keys()),
                           todos_equipamentos=todos_equipamentos,
                           todos_musculos=todos_musculos)
    if edicao_hub and edicao_hub.get("aluno_id"):
        card += render_draft_banner_oob(edicao_hub["aluno_id"])
    return card


QUICK_PICK_PADROES = [
    "empurrar_compostos", "remadas", "squat", "hinge", "ombro_composto", "puxadas",
]

def quick_pick_para_aluno(aluno=None):
    """Retorna até 6 exercícios compostos, um por padrão de movimento principal.
    Hoje a seleção não depende do aluno — espaço reservado para sugestões inteligentes."""
    sugestoes = []
    for padrao in QUICK_PICK_PADROES:
        candidatos = [e for e in banco if e.padrao == padrao and e.purpose == "compound"]
        if not candidatos:
            continue
        candidatos.sort(key=lambda e: (-(e.fadiga or 0), e.complexidade or 0, e.nome))
        sugestoes.append(candidatos[0])
    return sugestoes

def _criacao_manual_aluno_obj():
    if not criacao_manual:
        return None
    return next((a for a in carregar_alunos() if a["id"] == criacao_manual.get("aluno_id")), None)

@app.context_processor
def _inject_hub_ctx():
    aluno_obj = _criacao_manual_aluno_obj()
    return {
        "hub_aluno_id": edicao_hub["aluno_id"] if edicao_hub else None,
        "criacao_manual_idx": criacao_manual["novo_idx"] if criacao_manual else None,
        "criacao_manual_aluno": criacao_manual["aluno_id"] if criacao_manual else None,
        "criacao_manual_aluno_obj": aluno_obj,
        "criacao_manual_quick_pick": quick_pick_para_aluno(aluno_obj) if aluno_obj else [],
        "sessao_chips": sessao_chips,
        "subtitulo_sessao": subtitulo_sessao,
        "tempo_relativo": tempo_relativo,
        "todos_padroes_drawer": sorted(PADROES_LABELS.keys()),
        "padroes_labels_drawer": PADROES_LABELS,
        "padrao_para_chip": PADRAO_PARA_CHIP,
    }

def carregar_sessoes_disco():
    if not SESSOES_PATH.exists():
        return []
    try:
        with open(SESSOES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return [_dict_to_sessao(d) for d in data]
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════
# ROTAS — PÁGINA PRINCIPAL
# ══════════════════════════════════════════════════════════════

@app.route("/")
def index():
    alunos = carregar_alunos()
    aluno_id = request.args.get("aluno_id", type=int)
    avisos_por_treino = session.pop("avisos_pendentes", None)
    return render_template("hub.html",
        active_page="hub",
        alunos=alunos,
        selected_aluno_id=aluno_id,
        avisos_por_treino=avisos_por_treino,
    )


@app.route("/gerador")
def gerador_page():
    global sessoes_ativas, edicao_hub
    # Ao entrar no gerador, encerra edição inline do HUB (para não contaminar rotas /treino)
    edicao_hub = None
    alunos = carregar_alunos()
    nomes_alunos = {a["nome"] for a in alunos}
    nomes_hist = [n for n in nomes_unicos_historico() if n not in nomes_alunos]

    # Contexto do HUB
    aluno_id = request.args.get("aluno_id", type=int)
    acao = request.args.get("acao", "")  # nova_rotina, adicionar, substituir
    treino_idx = request.args.get("treino", type=int)

    ctx_aluno = None
    if aluno_id:
        ctx_aluno = next((a for a in alunos if a["id"] == aluno_id), None)

    if acao in ("nova_rotina", "adicionar", "substituir"):
        sessoes_ativas = []
        historico_substituicoes.clear()
        salvar_sessoes_disco()

    return render_template("treinos.html",
        active_page="gerador",
        templates=list(TEMPLATES.keys()),
        template_epp=TEMPLATE_EPP,
        n_exercicios=len(banco),
        regioes=ORDEM_REGIOES, regioes_labels=REGIOES_LABELS,
        subregioes=ORDEM_SUBREGIOES, subregioes_labels=SUBREGIOES_LABELS,
        padroes_ordem=ORDEM_PADROES, padroes_labels=PADROES_LABELS,
        subregiao_para_padroes=SUBREGIAO_PARA_PADROES,
        alunos=alunos,
        nomes_hist=nomes_hist,
        sessoes=sessoes_ativas,
        ctx_aluno=ctx_aluno,
        ctx_acao=acao,
        ctx_treino_idx=treino_idx,
    )


# ══════════════════════════════════════════════════════════════
# ROTAS — HUB (rotina do aluno)
# ══════════════════════════════════════════════════════════════

@app.route("/hub/rotina")
def hub_rotina():
    aluno_id = request.args.get("aluno_id", type=int)
    periodo = request.args.get("periodo", "atual")
    if not aluno_id:
        return '<div class="text-center py-12 text-gray-400"><div class="text-sm">Selecione um aluno.</div></div>'

    alunos = carregar_alunos()
    aluno = next((a for a in alunos if a["id"] == aluno_id), None)
    if not aluno:
        return '<div class="erro">Aluno não encontrado.</div>'

    # Rascunho tem prioridade sobre rotina salva para exibição "atual"
    rascunho_sessoes = carregar_rascunho(aluno_id)
    rotina_reg = carregar_rotina_ativa(aluno_id)
    eh_rascunho = False

    rotina = None
    if rascunho_sessoes:
        sessoes_obj = [_dict_to_sessao(s) for s in rascunho_sessoes]
        rotina = {
            "sessoes": sessoes_obj,
            "etiqueta": rotina_reg.get("etiqueta", "") if rotina_reg else "",
            "data": rotina_reg.get("data", "") if rotina_reg else "",
            "data_atualizada": rotina_reg.get("data_atualizada") if rotina_reg else None,
            "id": rotina_reg["id"] if rotina_reg else None,
        }
        eh_rascunho = True
    elif rotina_reg:
        sessoes_obj = [_dict_to_sessao(s) for s in rotina_reg["sessoes"]]
        rotina = {
            "sessoes": sessoes_obj,
            "etiqueta": rotina_reg.get("etiqueta", ""),
            "data": rotina_reg.get("data", ""),
            "data_atualizada": rotina_reg.get("data_atualizada"),
            "id": rotina_reg["id"],
        }

    # Carregar rotina anterior para comparação:
    # - Quando há rascunho: "anterior" = rotina ativa publicada (referência do que está com o aluno)
    # - Sem rascunho: "anterior" = última rotina antes da ativa (comportamento original)
    anterior = None
    nomes_anteriores = set()
    if eh_rascunho and rotina_reg:
        sessoes_ant = [_dict_to_sessao(s) for s in rotina_reg["sessoes"]]
        anterior = {
            "sessoes": sessoes_ant,
            "etiqueta": rotina_reg.get("etiqueta", ""),
            "data": rotina_reg.get("data", ""),
            "rotulo_origem": "Publicada",
        }
        for s in sessoes_ant:
            for bloco in s.blocos:
                for ex in [bloco.ex1, bloco.ex2, bloco.ex3]:
                    if ex:
                        nomes_anteriores.add(ex.nome)
        rot_ant_reg = None
    else:
        rot_ant_reg = carregar_rotina_anterior(aluno["nome"], aluno.get("rotina_ativa_id"))
    if rot_ant_reg:
        sessoes_ant = [_dict_to_sessao(s) for s in rot_ant_reg["sessoes"]]
        anterior = {
            "sessoes": sessoes_ant,
            "etiqueta": rot_ant_reg.get("etiqueta", ""),
            "data": rot_ant_reg.get("data", ""),
            "rotulo_origem": "Anterior",
        }
        # Não popula nomes_anteriores aqui: o badge "mantido" só faz sentido em rascunho×publicada.
        # Comparação explícita rotina×anterior usa o toggle "Lado a lado" (diff_atual/diff_anterior).

    total_alteracoes = 0
    tem_rotina_publicada = False
    if eh_rascunho:
        tem_rotina_publicada = bool(rotina_reg)
        if tem_rotina_publicada:
            total_alteracoes = len(diff_rascunho_vs_publicada(aluno_id))

    # Para o lado-a-lado: classifica exercícios por nome em mantido/adicionado/removido/editado
    diff_atual, diff_anterior, diff_summary = {}, {}, {"mantidos": 0, "adicionados": 0, "removidos": 0, "editados": 0}
    if periodo == "comparar" and rotina and anterior:
        atuais_dicts = [_sessao_to_dict(s) for s in rotina["sessoes"]]
        anteriores_dicts = [_sessao_to_dict(s) for s in anterior["sessoes"]]
        diff_atual, diff_anterior = classificar_exercicios_diff(atuais_dicts, anteriores_dicts)
        for nome, info in diff_atual.items():
            if info["status"] == "mantido":
                diff_summary["mantidos"] += 1
            elif info["status"] == "adicionado":
                diff_summary["adicionados"] += 1
            elif info["status"] == "editado":
                diff_summary["editados"] += 1
        for nome, info in diff_anterior.items():
            if info["status"] == "removido":
                diff_summary["removidos"] += 1

    estados_rascunho = {}
    if eh_rascunho:
        intent_atual = carregar_intent_rascunho(aluno_id)
        publicada_para_diff = [] if intent_atual == "nova-rotina" else (rotina_reg["sessoes"] if rotina_reg else [])
        estados_rascunho = _estados_rascunho_por_posicao(rascunho_sessoes, publicada_para_diff)
    return render_template("_rotina_hub.html",
                           rotina=rotina,
                           anterior=anterior,
                           nomes_anteriores=nomes_anteriores,
                           aluno=aluno,
                           aluno_id=aluno_id,
                           periodo=periodo,
                           eh_rascunho=eh_rascunho,
                           etiqueta_rascunho=carregar_etiqueta_rascunho(aluno_id) if eh_rascunho else "",
                           rascunho_intent=carregar_intent_rascunho(aluno_id) if eh_rascunho else "",
                           total_alteracoes=total_alteracoes,
                           tem_rotina_publicada=tem_rotina_publicada,
                           estados_rascunho=estados_rascunho,
                           diff_atual=diff_atual,
                           diff_anterior=diff_anterior,
                           diff_summary=diff_summary,
                           padroes_labels=PADROES_LABELS)


@app.route("/hub/rotina/<int:aluno_id>/treino/<int:treino_idx>", methods=["DELETE"])
def hub_remover_treino(aluno_id, treino_idx):
    sessoes = _obter_sessoes_trabalho(aluno_id)
    if sessoes is None:
        return '<div class="erro">Nenhuma rotina ativa.</div>'

    if treino_idx < 0 or treino_idx >= len(sessoes):
        return '<div class="erro">Índice de treino inválido.</div>'

    sessoes.pop(treino_idx)
    salvar_rascunho(aluno_id, sessoes)
    return hub_rotina_render(aluno_id, "atual")


def _obter_sessoes_trabalho(aluno_id):
    """Retorna sessões como lista de dicts: rascunho se existir, senão rotina ativa."""
    rascunho = carregar_rascunho(aluno_id)
    if rascunho:
        return rascunho
    rotina_reg = carregar_rotina_ativa(aluno_id)
    if rotina_reg:
        return list(rotina_reg["sessoes"])
    return None


def hub_rotina_render(aluno_id, periodo="atual"):
    """Helper: renderiza a rotina do aluno (reutilizado por várias rotas)."""
    with app.test_request_context(f"/hub/rotina?aluno_id={aluno_id}&periodo={periodo}"):
        return hub_rotina()


def _carregar_hub_edicao(aluno_id):
    """Carrega sessoes do aluno em sessoes_ativas e marca edicao_hub."""
    global sessoes_ativas, edicao_hub, historico_substituicoes
    sessoes_dicts = _obter_sessoes_trabalho(aluno_id)
    if not sessoes_dicts:
        return False
    sessoes_ativas = [_dict_to_sessao(s) for s in sessoes_dicts]
    historico_substituicoes = {}
    rotina_reg = carregar_rotina_ativa(aluno_id)
    edicao_hub = {"aluno_id": aluno_id, "rotina_id": rotina_reg["id"] if rotina_reg else None}
    return True


@app.route("/hub/rotina/<int:aluno_id>/treino/<int:t>/editar-inline", methods=["POST"])
def hub_editar_inline(aluno_id, t):
    """Entra em modo edição de um único treino, inline no HUB."""
    if not _carregar_hub_edicao(aluno_id):
        return '<div class="erro">Nenhuma rotina ativa.</div>'
    if t < 0 or t >= len(sessoes_ativas):
        return '<div class="erro">Treino não encontrado.</div>'
    salvar_sessoes_disco()
    return _responder_card_com_banner(t)


@app.route("/hub/rotina/<int:aluno_id>/treino/<int:t>/visualizar-inline")
def hub_visualizar_inline(aluno_id, t):
    """Volta um treino ao modo visualização (card estilo HUB)."""
    global edicao_hub
    sessoes_dicts = _obter_sessoes_trabalho(aluno_id)
    if not sessoes_dicts or t < 0 or t >= len(sessoes_dicts):
        return '<div class="erro">Treino não encontrado.</div>'
    # Se veio do sessoes_ativas, usa ele (mais recente durante edição)
    if edicao_hub and edicao_hub.get("aluno_id") == aluno_id and t < len(sessoes_ativas):
        sessao = sessoes_ativas[t]
    else:
        sessao = _dict_to_sessao(sessoes_dicts[t])
    edicao_hub = None

    aluno = next((a for a in carregar_alunos() if a["id"] == aluno_id), None)
    nomes_anteriores = set()
    if aluno:
        rot_ant = carregar_rotina_anterior(aluno["nome"], aluno.get("rotina_ativa_id"))
        if rot_ant:
            for s_dict in rot_ant["sessoes"]:
                for b in s_dict["blocos"]:
                    for key in ("ex1", "ex2", "ex3"):
                        ex = b.get(key)
                        if ex: nomes_anteriores.add(ex["nome"])
    estados_rascunho = {}
    rascunho = carregar_rascunho(aluno_id)
    rotina_reg = carregar_rotina_ativa(aluno_id)
    if rascunho:
        intent_atual = carregar_intent_rascunho(aluno_id)
        publicada_para_diff = [] if intent_atual == "nova-rotina" else (rotina_reg["sessoes"] if rotina_reg else [])
        estados_rascunho = _estados_rascunho_por_posicao(rascunho, publicada_para_diff)
    return render_template("_hub_treino_card.html", sessao=sessao, idx=t,
                           aluno_id=aluno_id,
                           nomes_anteriores=nomes_anteriores,
                           estados_rascunho=estados_rascunho,
                           padroes_labels=PADROES_LABELS)


@app.route("/hub/rotina/<int:aluno_id>/editar", methods=["POST"])
def hub_editar_rotina(aluno_id):
    """Carrega a rotina do aluno em sessoes_ativas para edição."""
    global sessoes_ativas, configs_geradas, edicao_hub
    rotina_reg = carregar_rotina_ativa(aluno_id)
    aluno = next((a for a in carregar_alunos() if a["id"] == aluno_id), None)
    if not aluno:
        return '<div class="erro">Aluno não encontrado.</div>'
    if not rotina_reg:
        return '<div class="erro">Nenhuma rotina ativa.</div>'

    sessoes_ativas = [_dict_to_sessao(s) for s in rotina_reg["sessoes"]]
    configs_geradas = []
    edicao_hub = {"aluno_id": aluno_id, "rotina_id": rotina_reg["id"]}
    salvar_sessoes_disco()

    return redirect("/gerador")


@app.route("/hub/rotina/salvar-edicao", methods=["POST"])
def hub_salvar_edicao():
    """Salva sessoes_ativas de volta como rotina do aluno."""
    global edicao_hub
    if not edicao_hub:
        return '<div class="erro">Nenhuma edição em andamento.</div>'

    aluno_id = edicao_hub["aluno_id"]
    aluno = next((a for a in carregar_alunos() if a["id"] == aluno_id), None)
    if not aluno:
        return '<div class="erro">Aluno não encontrado.</div>'

    reg_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + secrets.token_hex(2)
    salvar_historico_registro(
        reg_id=reg_id,
        data_salvo=datetime.now().strftime("%d/%m/%Y %H:%M"),
        aluno=aluno["nome"],
        etiqueta="",
        n_treinos=len(sessoes_ativas),
        sessoes=[_sessao_to_dict(s) for s in sessoes_ativas],
    )
    definir_rotina_ativa(aluno_id, reg_id)
    edicao_hub = None
    return redirect("/")


@app.route("/hub/rotina/<int:aluno_id>/salvar-rotina", methods=["POST"])
def hub_salvar_rotina(aluno_id):
    """Salva o rascunho (ou rotina atual) como registro oficial no histórico.

    modo='atualizar' (default): sobrescreve o registro vigente mantendo o id.
    modo='nova': cria registro novo no histórico e vira a nova rotina ativa.
    Se não há rotina publicada, 'atualizar' degrada para 'nova'.
    """
    sessoes = _obter_sessoes_trabalho(aluno_id)
    if not sessoes:
        return '<div class="erro">Nenhuma rotina para salvar.</div>'

    aluno = next((a for a in carregar_alunos() if a["id"] == aluno_id), None)
    if not aluno:
        return '<div class="erro">Aluno não encontrado.</div>'

    modo = (request.form.get("modo") or "atualizar").strip()
    etiqueta = (request.form.get("etiqueta", "") or carregar_etiqueta_rascunho(aluno_id) or "").strip()
    rotina_atual = carregar_rotina_ativa(aluno_id)
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Salva configs se houver (vem do último /gerar, persiste via configs_geradas global)
    configs_serial = None
    if configs_geradas:
        configs_serial = {"globals": dict(opcoes_globais), "treinos": _configs_to_serializable(configs_geradas)}

    if modo == "atualizar" and rotina_atual:
        atualizar_historico_registro(
            reg_id=rotina_atual["id"],
            data_atualizada=agora,
            etiqueta=etiqueta or rotina_atual.get("etiqueta", ""),
            n_treinos=len(sessoes),
            sessoes=sessoes,
            configs=configs_serial or rotina_atual.get("configs"),
        )
    else:
        reg_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + secrets.token_hex(2)
        salvar_historico_registro(
            reg_id=reg_id,
            data_salvo=agora,
            aluno=aluno["nome"],
            etiqueta=etiqueta,
            n_treinos=len(sessoes),
            sessoes=sessoes,
            configs=configs_serial,
        )
        definir_rotina_ativa(aluno_id, reg_id)

    limpar_rascunho(aluno_id)
    return hub_rotina_render(aluno_id, "atual")


@app.route("/hub/rotina/<int:aluno_id>/alteracoes")
def hub_alteracoes(aluno_id):
    """Retorna a lista de mudanças do rascunho vs rotina publicada (HTMX lazy)."""
    mudancas = diff_rascunho_vs_publicada(aluno_id)
    return render_template("_changes_list.html", mudancas=mudancas)


@app.route("/hub/rotina/<int:aluno_id>/etiqueta-rascunho", methods=["POST"])
def hub_etiqueta_rascunho(aluno_id):
    """Salva a etiqueta do rascunho (autosave on-blur). Não re-renderiza nada."""
    etiqueta = (request.form.get("etiqueta", "") or "").strip()
    salvar_etiqueta_rascunho(aluno_id, etiqueta)
    return ("", 204)


@app.route("/_mobile_bb_actions")
def mobile_bb_actions():
    """Re-fetch do conteudo do slot direito da bb (hub). Re-renderiza o partial
    com base no estado atual do rascunho via context_processor."""
    return render_template("_mobile_bb_actions_hub.html")


@app.route("/hub/rotina/<int:aluno_id>/etiqueta", methods=["POST"])
def hub_etiqueta_rotina(aluno_id):
    """Edit inline da etiqueta da rotina ativa (ou do rascunho, se houver).
    Autosave on-blur — não re-renderiza nada."""
    etiqueta = (request.form.get("etiqueta", "") or "").strip()
    if carregar_rascunho(aluno_id):
        salvar_etiqueta_rascunho(aluno_id, etiqueta)
    else:
        rotina_reg = carregar_rotina_ativa(aluno_id)
        if rotina_reg:
            atualizar_etiqueta_historico(rotina_reg["id"], etiqueta)
    return ("", 204)


@app.route("/hub/rotina/<int:aluno_id>/descartar-rascunho", methods=["POST"])
def hub_descartar_rascunho(aluno_id):
    """Descarta o rascunho e volta para a última rotina salva. Encerra edição se ativa."""
    global edicao_hub
    limpar_rascunho(aluno_id)
    if edicao_hub and edicao_hub.get("aluno_id") == aluno_id:
        edicao_hub = None
    return hub_rotina_render(aluno_id, "atual")


@app.route("/hub/rotina/<int:aluno_id>/concluir-edicao", methods=["POST"])
def hub_concluir_edicao(aluno_id):
    """Encerra o modo edição inline (mantém alterações como rascunho) e volta a visualização."""
    global edicao_hub
    if edicao_hub and edicao_hub.get("aluno_id") == aluno_id:
        edicao_hub = None
    return hub_rotina_render(aluno_id, "atual")


@app.route("/hub/rotina/<int:aluno_id>/criar-manual", methods=["POST"])
def hub_criar_manual(aluno_id):
    """Adiciona uma sessão vazia ao rascunho do aluno e abre em modo edição."""
    global criacao_manual
    aluno = next((a for a in carregar_alunos() if a["id"] == aluno_id), None)
    if not aluno:
        return '<div class="erro">Aluno não encontrado.</div>'

    sessoes_dicts = _obter_sessoes_trabalho(aluno_id) or []
    sessoes_dicts.append(_sessao_to_dict(Sessao(tipo="manual", blocos=[])))
    salvar_rascunho(aluno_id, sessoes_dicts)
    novo_idx = len(sessoes_dicts) - 1
    criacao_manual = {"aluno_id": aluno_id, "novo_idx": novo_idx}

    html = hub_rotina_render(aluno_id, "atual")
    html += (f'<script>setTimeout(function(){{'
             f'var b=document.querySelector("#treino-{novo_idx} [title=Editar]");'
             f'if(b)b.click();}},30);</script>')
    return html


@app.route("/hub/rotina/<int:aluno_id>/criar-manual/salvar", methods=["POST"])
def hub_criar_manual_salvar(aluno_id):
    """Confirma adição do treino manual à rotina."""
    global criacao_manual, edicao_hub
    criacao_manual = None
    edicao_hub = None
    return hub_rotina_render(aluno_id, "atual")


@app.route("/hub/rotina/<int:aluno_id>/criar-manual/cancelar", methods=["POST"])
def hub_criar_manual_cancelar(aluno_id):
    """Remove o treino em criação e volta ao HUB."""
    global criacao_manual, edicao_hub
    if criacao_manual and criacao_manual.get("aluno_id") == aluno_id:
        novo_idx = criacao_manual.get("novo_idx")
        sessoes_dicts = _obter_sessoes_trabalho(aluno_id) or []
        if novo_idx is not None and 0 <= novo_idx < len(sessoes_dicts):
            sessoes_dicts.pop(novo_idx)
            if sessoes_dicts:
                salvar_rascunho(aluno_id, sessoes_dicts)
            else:
                limpar_rascunho(aluno_id)
    criacao_manual = None
    edicao_hub = None
    return hub_rotina_render(aluno_id, "atual")


@app.route("/hub/rotina/<int:aluno_id>/nova-rotina-manual", methods=["POST"])
def hub_nova_rotina_manual(aluno_id):
    """Inicia uma rotina nova do zero, manualmente. Limpa rascunho atual e cria 1 sessão vazia.

    Marca intent='nova-rotina' para o banner esconder 'Atualizar rotina' (a rotina vigente
    publicada não deve ser sobrescrita por uma nova rotina manual em construção)."""
    global criacao_manual
    aluno = next((a for a in carregar_alunos() if a["id"] == aluno_id), None)
    if not aluno:
        return '<div class="erro">Aluno não encontrado.</div>'

    limpar_rascunho(aluno_id)
    sessoes_dicts = [_sessao_to_dict(Sessao(tipo="manual", blocos=[]))]
    salvar_rascunho(aluno_id, sessoes_dicts)
    salvar_intent_rascunho(aluno_id, "nova-rotina")
    criacao_manual = {"aluno_id": aluno_id, "novo_idx": 0}

    html = hub_rotina_render(aluno_id, "atual")
    html += ('<script>setTimeout(function(){'
             'var b=document.querySelector("#treino-0 [title=Editar]");'
             'if(b)b.click();},30);</script>')
    return html


@app.route("/hub/rotina/<int:aluno_id>/criar-manual/nome", methods=["POST"])
def hub_criar_manual_nome(aluno_id):
    """Salva o nome (Sessao.tipo) do treino em criação manual."""
    if not criacao_manual or criacao_manual.get("aluno_id") != aluno_id:
        return ("", 204)
    novo_idx = criacao_manual.get("novo_idx")
    nome = (request.form.get("nome") or "").strip()

    sessoes_dicts = _obter_sessoes_trabalho(aluno_id) or []
    if novo_idx is not None and 0 <= novo_idx < len(sessoes_dicts):
        sessoes_dicts[novo_idx]["tipo"] = nome or "manual"
        salvar_rascunho(aluno_id, sessoes_dicts)
        # Mantém sessoes_ativas em sincronia se edição inline está ativa
        if edicao_hub and edicao_hub.get("aluno_id") == aluno_id and novo_idx < len(sessoes_ativas):
            sessoes_ativas[novo_idx].tipo = nome or "manual"
            salvar_sessoes_disco()
    return ("", 204)


@app.route("/treino/<int:t>/novo-bloco-vazio", methods=["POST"])
def novo_bloco_vazio(t):
    """Cria um bloco sem exercício (CTA do estado vazio guiado)."""
    global sessoes_ativas
    if t >= len(sessoes_ativas):
        return "", 404
    labels = "ABCDEFGHIJKLMNOP"
    n = len(sessoes_ativas[t].blocos)
    lbl = labels[n] if n < len(labels) else str(n + 1)
    sessoes_ativas[t].blocos.append(SuperSerie(label=lbl, ex1=None, ex2=None, ex3=None))
    salvar_sessoes_disco()
    return _responder_card_com_banner(t)


@app.route("/hub/rotina/<int:aluno_id>/treino/<int:t>/bloco/<int:bi>/regerar", methods=["POST"])
def hub_regerar_bloco(aluno_id, t, bi):
    """Regenera um bloco individual mantendo os mesmos padrões de movimento."""
    sessoes_dicts = _obter_sessoes_trabalho(aluno_id)
    if not sessoes_dicts:
        return '<div class="erro">Nenhuma rotina ativa.</div>'

    if t < 0 or t >= len(sessoes_dicts):
        return '<div class="erro">Treino não encontrado.</div>'

    sessao_dict = sessoes_dicts[t]
    blocos = sessao_dict["blocos"]
    if bi < 0 or bi >= len(blocos):
        return '<div class="erro">Bloco não encontrado.</div>'

    bloco = blocos[bi]
    padroes_bloco = []
    for key in ("ex1", "ex2", "ex3"):
        ex = bloco.get(key)
        if ex:
            padroes_bloco.append(ex.get("padrao", ""))

    # Coletar nomes de exercícios da rotina inteira (para bloqueio)
    nomes_bloqueados = set()
    pais_bloqueados = set()
    for s_dict in sessoes_dicts:
        for b in s_dict["blocos"]:
            for key in ("ex1", "ex2", "ex3"):
                ex = b.get(key)
                if ex:
                    nomes_bloqueados.add(ex["nome"])
                    if ex.get("variacao_de"):
                        pais_bloqueados.add(ex["variacao_de"])

    # Bloqueio por período anterior
    aluno = next((a for a in carregar_alunos() if a["id"] == aluno_id), None)
    if aluno:
        rot_ant = carregar_rotina_anterior(aluno["nome"], aluno.get("rotina_ativa_id"))
        if rot_ant:
            for s_dict in rot_ant["sessoes"]:
                for b in s_dict["blocos"]:
                    for key in ("ex1", "ex2", "ex3"):
                        ex = b.get(key)
                        if ex:
                            nomes_bloqueados.add(ex["nome"])
                            if ex.get("variacao_de"):
                                pais_bloqueados.add(ex["variacao_de"])

    banco_filtrado = [e for e in banco
                      if e.nome not in nomes_bloqueados
                      and e.nome not in pais_bloqueados
                      and (e.variacao_de is None or e.variacao_de not in nomes_bloqueados)]

    # Gerar novos exercícios para cada padrão do bloco
    novos_exs = []
    for padrao in padroes_bloco:
        candidatos = [e for e in banco_filtrado if e.padrao == padrao and e.complexidade <= 5]
        if not candidatos:
            candidatos = [e for e in banco if e.padrao == padrao]
        ex = selecionar_evitando_familia(candidatos, set(), 1)
        if ex:
            novos_exs.append(ex[0])
        elif candidatos:
            novos_exs.append(candidatos[0])

    # Atualizar o bloco
    label = bloco["label"]
    novo_bloco = {"label": label, "ex1": None, "ex2": None, "ex3": None}
    for i, ex in enumerate(novos_exs):
        key = f"ex{i+1}"
        novo_bloco[key] = {
            "nome": ex.nome, "variacao_de": ex.variacao_de,
            "eq_primario": ex.eq_primario, "eq_secundario": ex.eq_secundario,
            "regiao": ex.regiao, "subregiao": getattr(ex, "subregiao", ""),
            "padrao": ex.padrao, "purpose": ex.purpose,
            "unilateral": ex.unilateral, "complexidade": ex.complexidade,
            "fadiga": ex.fadiga, "circuito": ex.circuito,
            "similaridade": ex.similaridade, "musculo_primario": ex.musculo_primario,
            "obs": ex.obs,
            "series": bloco.get(f"ex{i+1}", {}).get("series") if bloco.get(f"ex{i+1}") else 3,
            "reps": bloco.get(f"ex{i+1}", {}).get("reps") if bloco.get(f"ex{i+1}") else "8-12",
            "rir": bloco.get(f"ex{i+1}", {}).get("rir") if bloco.get(f"ex{i+1}") else 2,
        }

    sessoes_dicts[t]["blocos"][bi] = novo_bloco
    salvar_rascunho(aluno_id, sessoes_dicts)

    return hub_rotina_render(aluno_id, "atual")


# ══════════════════════════════════════════════════════════════
# ROTAS — GERAÇÃO DE TREINOS
# ══════════════════════════════════════════════════════════════

@app.route("/gerar", methods=["POST"])
def gerar():
    global sessoes_ativas, configs_geradas, opcoes_globais
    historico_substituicoes.clear()
    n_treinos = int(request.form.get("n_treinos", 1))
    max_cx = int(request.form.get("max_complexidade", 5))
    tam_bloco = int(request.form.get("tamanho_bloco", 2))
    evitar_agon = request.form.get("evitar_agonistas") == "on"
    relaxar_familia = request.form.get("relaxar_familia") == "on"
    usar_historico_r1 = request.form.get("usar_historico_r1") == "on"

    # Filtro de cargas (Etapa 4 / HIB2). Apenas aplica se os 3 thresholds vierem
    # preenchidos no form. Defaults da UI: grip=6, lombar=5, core=6 (HIB2).
    grip_max = int(request.form.get("carga_grip_max") or 0)
    lombar_max = int(request.form.get("carga_lombar_max") or 0)
    core_max = int(request.form.get("demanda_core_max") or 0)
    cargas_config = (
        {"grip": grip_max, "lombar": lombar_max, "core": core_max}
        if (grip_max and lombar_max and core_max) else None
    )

    all_configs = []

    for t in range(n_treinos):
        cfg = {"max_complexidade": max_cx, "tamanho_bloco": tam_bloco,
               "equipamentos_bloqueados": [], "evitar_agonistas": evitar_agon,
               "cargas_config": cargas_config}

        modo = request.form.get(f"modo_{t}", "hierarquia")
        cfg["modo"] = modo
        if modo == "template":
            tmpl_nome = request.form.get(f"template_{t}", "")
            cfg["template_nome"] = tmpl_nome
            padroes = TEMPLATES.get(tmpl_nome, [])
            epp = dict(TEMPLATE_EPP.get(tmpl_nome, {}))
            # Read EPP sliders
            for p in padroes:
                val = request.form.get(f"epp_{t}_{p}")
                if val is not None: epp[p] = int(val)
            # Frente 4: traduz squat_bi/squat_uni direto em padrões refinados.
            # Substitui o agregado "squat" por squat_bilateral e squat_unilateral.
            squat_bi = int(request.form.get(f"squat_bi_{t}", 0))
            squat_uni = int(request.form.get(f"squat_uni_{t}", 0))
            if squat_bi > 0 or squat_uni > 0:
                epp.pop("squat", None)
                if squat_bi > 0: epp["squat_bilateral"] = squat_bi
                if squat_uni > 0: epp["squat_unilateral"] = squat_uni
                # Inserir os filhos no lugar de "squat" na lista de padroes
                padroes_novos = []
                for p in padroes:
                    if p == "squat":
                        if squat_bi > 0: padroes_novos.append("squat_bilateral")
                        if squat_uni > 0: padroes_novos.append("squat_unilateral")
                    else:
                        padroes_novos.append(p)
                padroes = padroes_novos

            cfg["padroes"] = [p for p in padroes if (epp.get(p, 0) if isinstance(epp.get(p, 0), int) else sum(epp.get(p, {}).values())) > 0]
            cfg["exercicios_por_padrao"] = epp
            cfg["demandas"] = None
        else:
            # Hierarquia: parse demandas from form
            demandas = []
            # Collect all demand entries
            i = 0
            while True:
                nivel = request.form.get(f"dem_nivel_{t}_{i}")
                if nivel is None: break
                escopo = request.form.get(f"dem_escopo_{t}_{i}", "")
                qtd = int(request.form.get(f"dem_qtd_{t}_{i}", 1))
                if qtd > 0:
                    demandas.append((nivel, escopo, qtd))
                i += 1

            # Frente 4: traduz squat_bi/squat_uni direto em demandas refinadas.
            # Substitui qualquer demanda agregada (padrao=squat ou subregiao=perna_anterior)
            # por demandas (padrao, squat_bilateral, X) + (padrao, squat_unilateral, Y).
            squat_bi = int(request.form.get(f"squat_bi_{t}", 0))
            squat_uni = int(request.form.get(f"squat_uni_{t}", 0))
            if squat_bi > 0 or squat_uni > 0:
                demandas_novas = []
                substituida = False
                for n, e, q in demandas:
                    eh_agregada_squat = (n == "padrao" and e == "squat") or \
                                        (n == "subregiao" and e == "perna_anterior")
                    if eh_agregada_squat and not substituida:
                        if squat_bi > 0:
                            demandas_novas.append(("padrao", "squat_bilateral", squat_bi))
                        if squat_uni > 0:
                            demandas_novas.append(("padrao", "squat_unilateral", squat_uni))
                        substituida = True
                    else:
                        demandas_novas.append((n, e, q))
                # Caso usuário tenha marcado bi/uni sem demanda agregada presente,
                # ainda assim adiciona as demandas refinadas.
                if not substituida:
                    if squat_bi > 0:
                        demandas_novas.append(("padrao", "squat_bilateral", squat_bi))
                    if squat_uni > 0:
                        demandas_novas.append(("padrao", "squat_unilateral", squat_uni))
                demandas = demandas_novas

            cfg["demandas"] = demandas if demandas else None
            cfg["padroes"] = []
            cfg["exercicios_por_padrao"] = {}

        # Fixed exercises
        fixos_str = request.form.get(f"fixos_{t}", "")
        fixos_nomes = [n.strip() for n in fixos_str.split(",") if n.strip()]
        cfg["exercicios_travados"] = [e for e in banco if e.nome in set(fixos_nomes)]

        all_configs.append(cfg)

    # Filtra treinos vazios — n_treinos vira emergente das demandas configuradas.
    # Mantém mapeamento orig_idx → new_idx pra preservar nomes customizados.
    kept_indices = [i for i, c in enumerate(all_configs)
                    if c.get("padroes") or c.get("demandas")]
    if not kept_indices:
        return "<p class='aviso'>Selecione categorias em pelo menos um treino antes de gerar.</p>"
    all_configs = [all_configs[i] for i in kept_indices]
    n_treinos = len(all_configs)

    banco_gerar = list(banco)

    # Bloqueio por treinos irmãos (substituir/adicionar)
    ctx_acao = request.form.get("ctx_acao", "")
    ctx_aluno_id_form = request.form.get("ctx_aluno_id", type=int)
    ctx_treino_idx_form = request.form.get("ctx_treino_idx", type=int)
    if ctx_acao in ("substituir", "adicionar") and ctx_aluno_id_form:
        rotina_irmaos = carregar_rotina_ativa(ctx_aluno_id_form)
        if rotina_irmaos:
            nomes_irmaos = set()
            pais_irmaos = set()
            for i, s_dict in enumerate(rotina_irmaos["sessoes"]):
                if ctx_acao == "substituir" and i == ctx_treino_idx_form:
                    continue
                for bloco in s_dict["blocos"]:
                    for key in ("ex1", "ex2", "ex3"):
                        ex = bloco.get(key)
                        if ex:
                            nomes_irmaos.add(ex["nome"])
                            if ex.get("variacao_de"):
                                pais_irmaos.add(ex["variacao_de"])
            banco_gerar = [e for e in banco_gerar
                           if e.nome not in nomes_irmaos
                           and e.nome not in pais_irmaos
                           and (e.variacao_de is None or e.variacao_de not in nomes_irmaos)]

    # Rotina ativa do aluno — lookup único; alimenta tanto o score HIST quanto o
    # auto-fixar refs visuais (decisão UX: refs sempre aparecem quando há rotina
    # ativa; toggle só controla o score HIST D3.3).
    aluno_nome = request.form.get("aluno", "").strip()
    rotina_ativa_aluno = None
    if aluno_nome:
        aluno_obj_db = buscar_aluno_por_nome(aluno_nome)
        if aluno_obj_db and aluno_obj_db.get("rotina_ativa_id"):
            rotina_ativa_aluno = carregar_rotina_ativa(aluno_obj_db["id"])

    # Score HIST D3.3 (Etapa 7 Fase 7.4) — toggle "Evitar exercícios da rotina
    # anterior". Quando ON e há rotina ativa, propaga R-1 pro _score_proximidade
    # (penalty soft -50 família, peso integral). Não bloqueia banco, desencoraja
    # via softmax; permite repetir quando inevitável.
    historico_r1_sessoes: list[Sessao] | None = None
    if usar_historico_r1 and rotina_ativa_aluno:
        historico_r1_sessoes = [_dict_to_sessao(s) for s in rotina_ativa_aluno["sessoes"]]

    sessoes_ativas = gerar_multiplos_treinos(banco_gerar, all_configs,
                                             relaxar_familia=relaxar_familia,
                                             historico_r1=historico_r1_sessoes)

    # Calcula avisos cedo (antes de qualquer redirect contextual) para podermos
    # stashar em session quando a rota redireciona pro HUB (substituir/adicionar/nova_rotina).
    def _label_escopo_av(nivel, escopo):
        if nivel == "regiao":
            return REGIOES_LABELS.get(escopo, escopo)
        if nivel == "subregiao":
            return SUBREGIOES_LABELS.get(escopo, escopo)
        return PADROES_LABELS.get(escopo, escopo)

    def _bloco_label_por_exercicio(nome, blocos):
        """Encontra o label A/B/C... do bloco que contém o exercício."""
        if not nome:
            return None
        for b in blocos:
            if any(ex and ex.nome == nome for ex in (b.ex1, b.ex2, b.ex3)):
                return b.label
        return None

    avisos_por_treino = []
    for i, s in enumerate(sessoes_ativas, start=1):
        if not s.avisos:
            continue
        avisos_enriq = []
        for av in s.avisos:
            av_copy = dict(av)
            # Avisos com nivel/escopo (incompleta, ancora_*) ganham label legível.
            if av.get("nivel"):
                av_copy["escopo_label"] = _label_escopo_av(av["nivel"], av["escopo"])
            # relaxado_carga: derivar bloco_label A/B/C... a partir do exercício âncora.
            if av.get("tipo") == "relaxado_carga":
                bl = _bloco_label_por_exercicio(av.get("exercicio"), s.blocos)
                if bl:
                    av_copy["bloco_label"] = bl
            avisos_enriq.append(av_copy)
        avisos_por_treino.append({"treino_num": i, "tipo": s.tipo, "avisos": avisos_enriq})

    if avisos_por_treino:
        session["avisos_pendentes"] = avisos_por_treino
    else:
        session.pop("avisos_pendentes", None)

    # Aplica nome customizado por treino (sobrescreve sessao.tipo se usuário digitou).
    # Usa orig_idx pra ler nome_{N} do form mesmo após filtrar treinos vazios.
    for new_idx, orig_idx in enumerate(kept_indices[:len(sessoes_ativas)]):
        nome_custom = (request.form.get(f"nome_{orig_idx}", "") or "").strip()
        if nome_custom:
            sessoes_ativas[new_idx].tipo = nome_custom
            all_configs[new_idx]["nome_custom"] = nome_custom

    configs_geradas = all_configs
    opcoes_globais = {
        "n_treinos": n_treinos,
        "max_complexidade": max_cx,
        "tamanho_bloco": tam_bloco,
        "evitar_agonistas": evitar_agon,
        "relaxar_familia": relaxar_familia,
        "usar_historico_r1": usar_historico_r1,
        "cargas_config": cargas_config,
    }
    salvar_sessoes_disco()

    # Ações contextuais do HUB (substituir/adicionar)
    ctx_acao = request.form.get("ctx_acao", "")
    ctx_aluno_id = request.form.get("ctx_aluno_id", type=int)
    ctx_treino_idx = request.form.get("ctx_treino_idx", type=int)

    if ctx_acao in ("substituir", "adicionar", "nova_rotina") and ctx_aluno_id and sessoes_ativas:
        aluno_obj = next((a for a in carregar_alunos() if a["id"] == ctx_aluno_id), None)

        if aluno_obj:
            if ctx_acao == "nova_rotina":
                sessoes_rascunho = [_sessao_to_dict(s) for s in sessoes_ativas]
                salvar_rascunho(ctx_aluno_id, sessoes_rascunho)
                salvar_intent_rascunho(ctx_aluno_id, "nova-rotina")
                return f'<div class="sucesso">Rotina gerada para {aluno_obj["nome"]}!</div><script>setTimeout(()=>window.location.href="/?aluno_id={ctx_aluno_id}",1500)</script>'

            sessoes_rotina = _obter_sessoes_trabalho(ctx_aluno_id) or []

            if ctx_acao == "substituir" and ctx_treino_idx is not None:
                if 0 <= ctx_treino_idx < len(sessoes_rotina):
                    sessoes_rotina[ctx_treino_idx] = _sessao_to_dict(sessoes_ativas[0])
                    salvar_rascunho(ctx_aluno_id, sessoes_rotina)
                    return f'<div class="sucesso">Treino {ctx_treino_idx + 1} substituído na rotina de {aluno_obj["nome"]}!</div><script>setTimeout(()=>window.location.href="/?aluno_id={ctx_aluno_id}",1500)</script>'

            elif ctx_acao == "adicionar":
                sessoes_rotina.append(_sessao_to_dict(sessoes_ativas[0]))
                salvar_rascunho(ctx_aluno_id, sessoes_rotina)
                return f'<div class="sucesso">Treino adicionado à rotina de {aluno_obj["nome"]}!</div><script>setTimeout(()=>window.location.href="/?aluno_id={ctx_aluno_id}",1500)</script>'

    # No fluxo padrão de /gerador (sem ctx_acao), exibimos o modal direto em
    # _resultado.html e limpamos a stash pra não duplicar no próximo HUB.
    session.pop("avisos_pendentes", None)

    return render_template("_resultado.html", sessoes=sessoes_ativas,
                           padroes_labels=PADROES_LABELS, alunos=carregar_alunos(),
                           avisos_por_treino=avisos_por_treino)

# ══════════════════════════════════════════════════════════════
# ROTAS — AÇÕES POR TREINO
# ══════════════════════════════════════════════════════════════

@app.route("/treino/<int:t>/visualizar")
def treino_visualizar(t):
    if t >= len(sessoes_ativas): return "Treino não encontrado", 404
    return render_template("_treino_card.html", sessao=sessoes_ativas[t], idx=t,
                           modo="visualizar", padroes_labels=PADROES_LABELS, alunos=carregar_alunos())


def _ex_do_slot(sessao, bi, ei):
    """Retorna o Exercicio na posição (bi, ei) da sessão, ou None se inválido."""
    if not sessao or bi < 0 or bi >= len(sessao.blocos):
        return None
    bloco = sessao.blocos[bi]
    slots = [bloco.ex1, bloco.ex2, bloco.ex3]
    if ei < 0 or ei >= len(slots):
        return None
    return slots[ei]


@app.route("/hub/rotina/<int:aluno_id>/treino/<int:t>/decisoes")
def hub_treino_decisoes(aluno_id, t):
    """Página dedicada de dev — relatório completo das decisões do gerador para
    um treino. Agrega rationale de pré-alocação, pareamento, alternativas softmax,
    rejeições por filtro de cargas e avisos da rotina (incompleta / familia
    repetida / relaxado_carga). Lê rascunho ou rotina ativa, mesmo padrão de
    `hub_treino_rationale`."""
    aluno = next((a for a in carregar_alunos() if a["id"] == aluno_id), None)
    if not aluno:
        return "Aluno não encontrado", 404
    sessoes_dicts = carregar_rascunho(aluno_id)
    rotina_id = None
    configs = None
    fonte = "rascunho"
    if sessoes_dicts:
        # Rascunho não persiste configs — busca da rotina ativa se houver
        if aluno.get("rotina_ativa_id"):
            rotina = carregar_registro(aluno["rotina_ativa_id"])
            if rotina:
                rotina_id = rotina["id"]
                configs = rotina.get("configs")
    else:
        if aluno.get("rotina_ativa_id"):
            rotina = carregar_registro(aluno["rotina_ativa_id"])
            if rotina:
                sessoes_dicts = rotina["sessoes"]
                rotina_id = rotina["id"]
                configs = rotina.get("configs")
                fonte = "rotina_ativa"
    if not sessoes_dicts or t >= len(sessoes_dicts):
        return "Treino não encontrado", 404
    sessao = _dict_to_sessao(sessoes_dicts[t])
    config_treino = None
    if configs and isinstance(configs, list) and t < len(configs):
        config_treino = configs[t]

    # Frente C (2026-05-23): treino vindo do motor CSP novo não tem rationale
    # capturado. Marker em ex.rationale={"gerador": "csp"} sinaliza isso pro
    # template, que renderiza uma mensagem em vez de timeline vazio.
    treino_csp = any(
        ex and getattr(ex, "rationale", None)
        and ex.rationale.get("gerador") == "csp"
        for b in sessao.blocos for ex in (b.ex1, b.ex2, b.ex3)
    )

    # Agrega distribuição real por demanda raiz lendo o rationale.pre_alocacao
    # de cada exercício escolhido. Devolve, por (nivel, escopo), a contagem de
    # exercícios por subregião (quando nivel="regiao") ou por padrão (quando
    # nivel="subregiao"). Permite comparar a distribuição obtida com as
    # âncoras declaradas. Computa pra o treino corrente E pros demais treinos
    # da rotina — o fix de cobertura rotina-level (Seção 8.15.15) sacrifica
    # ótimo per-treino pra garantir cobertura agregada, então a coluna
    # "em outros" desambigua "obrig ✗ neste treino" vs "obrig ✗ na rotina toda".
    def _agregar_distribuicao(sessoes_iter):
        agg = {}
        for s in sessoes_iter:
            for bloco in s.blocos:
                for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
                    if not ex or not getattr(ex, "rationale", None):
                        continue
                    pa = ex.rationale.get("pre_alocacao") or {}
                    slot = ex.rationale.get("slot") or {}
                    nivel_orig = pa.get("nivel_demanda_original")
                    escopo_orig = slot.get("escopo_demanda_original")
                    if not nivel_orig or not escopo_orig:
                        continue
                    chave = (nivel_orig, escopo_orig)
                    bucket = agg.setdefault(chave, {
                        "por_subregiao": {}, "por_padrao": {}, "total": 0,
                    })
                    bucket["total"] += 1
                    sub = pa.get("subregiao_intermediaria") or ex.subregiao
                    if sub:
                        bucket["por_subregiao"][sub] = bucket["por_subregiao"].get(sub, 0) + 1
                    if ex.padrao:
                        bucket["por_padrao"][ex.padrao] = bucket["por_padrao"].get(ex.padrao, 0) + 1
        return agg

    distribuicao_por_demanda = _agregar_distribuicao([sessao])
    outras_sessoes = [
        _dict_to_sessao(sd) for ti, sd in enumerate(sessoes_dicts) if ti != t
    ]
    distribuicao_outros_treinos = _agregar_distribuicao(outras_sessoes)

    return render_template(
        "decisoes_treino.html",
        sessao=sessao,
        idx=t,
        aluno=aluno,
        aluno_id=aluno_id,
        rotina_id=rotina_id,
        fonte=fonte,
        config_treino=config_treino,
        ancoras_por_regiao=ANCORAS_POR_REGIAO,
        ancoras_por_subregiao=ANCORAS_POR_SUBREGIAO,
        distribuicao_por_demanda=distribuicao_por_demanda,
        distribuicao_outros_treinos=distribuicao_outros_treinos,
        total_treinos_rotina=len(sessoes_dicts),
        treino_csp=treino_csp,
    )


@app.route("/treino/<int:t>/editar")
def treino_editar(t):
    if t >= len(sessoes_ativas): return "Treino não encontrado", 404
    return _responder_card_com_banner(t)

def _regerar_motor_legacy(t, cfg_r, banco_regen):
    """Branch legado de /treino/<t>/regerar — gerador_treino.py greedy.
    Mantido como fallback acessível pra rollback rápido. Não chamado em
    runtime pela rota (motor novo CSP é default). Pra reativar: trocar
    o corpo de treino_regerar pra chamar este helper."""
    if cfg_r.get("demandas"):
        return gerar_sessao_por_demandas(banco_regen, demandas=cfg_r["demandas"],
            equipamentos_bloqueados=cfg_r.get("equipamentos_bloqueados", []),
            max_complexidade=cfg_r.get("max_complexidade", 5),
            tamanho_bloco=cfg_r.get("tamanho_bloco", 2),
            exercicios_travados=cfg_r.get("exercicios_travados", []),
            evitar_agonistas=cfg_r.get("evitar_agonistas", False),
            lateralidade_por_padrao=cfg_r.get("lateralidade_por_padrao"),
            cargas_config=cfg_r.get("cargas_config"))
    return gerar_sessao(banco_regen, cfg_r["padroes"],
        exercicios_por_padrao=cfg_r["exercicios_por_padrao"],
        equipamentos_bloqueados=cfg_r.get("equipamentos_bloqueados", []),
        max_complexidade=cfg_r.get("max_complexidade", 5),
        tamanho_bloco=cfg_r.get("tamanho_bloco", 2),
        exercicios_travados=cfg_r.get("exercicios_travados", []),
        evitar_agonistas=cfg_r.get("evitar_agonistas", False),
        cargas_config=cfg_r.get("cargas_config"))


@app.route("/treino/<int:t>/regerar", methods=["POST"])
def treino_regerar(t):
    """Frente C MVP (2026-05-23): regenera 1 treino via motor CSP novo
    (`gerador_csp.gerar_treino_csp` + `ConfigVariedade()`).

    Features do gerador antigo que SÃO IGNORADAS aqui (motor novo ainda
    não cobre — ver handoff_fatia_3_frente_c.txt): tamanho_bloco,
    evitar_agonistas, relaxar_familia, cargas_config, exercicios_travados,
    lateralidade_por_padrao (mas split squat_bi/squat_uni continua via
    `_expandir_demanda_csp`).

    Saída: lista linear de blocos solo (labels A/B/C…). Pareamento real
    de blocos fica pra Fatia 4 (S-B do catálogo).
    """
    global sessoes_ativas
    if t >= len(sessoes_ativas): return "Treino não encontrado", 404

    cfg_r = configs_geradas[t] if t < len(configs_geradas) else None
    if not cfg_r:
        contagem = {}
        for bloco in sessoes_ativas[t].blocos:
            for ex in [bloco.ex1, bloco.ex2, bloco.ex3]:
                if ex and ex.padrao: contagem[ex.padrao] = contagem.get(ex.padrao, 0) + 1
        cfg_r = {"padroes": list(contagem.keys()), "exercicios_por_padrao": contagem,
                 "max_complexidade": 5, "tamanho_bloco": 2, "equipamentos_bloqueados": [],
                 "exercicios_travados": [], "demandas": None}

    # Bloqueio cross-treino: filtra nomes + famílias dos outros treinos do
    # banco antes de mandar pro CSP (CSP só faz AllDifferent dentro da
    # rotina que recebe; aqui mandamos só 1 treino).
    exs_outros = [ex for i, s in enumerate(sessoes_ativas) if i != t
                  for bloco in s.blocos for ex in [bloco.ex1, bloco.ex2, bloco.ex3] if ex]
    nomes_outros = {ex.nome for ex in exs_outros}
    pais_dos_outros = {ex.variacao_de for ex in exs_outros if ex.variacao_de}
    banco_regen = [e for e in banco if e.nome not in nomes_outros
                   and e.nome not in pais_dos_outros
                   and (e.variacao_de is None or e.variacao_de not in nomes_outros)]

    # Mapeia cfg antiga → demandas CSP + nível do aluno via session.
    demandas_csp = _cfg_antiga_pra_demandas_csp(cfg_r)
    aluno_id_sel = session.get("aluno_id") or (edicao_hub.get("aluno_id") if edicao_hub else None)
    aluno_obj = next((a for a in carregar_alunos() if a["id"] == aluno_id_sel), None) if aluno_id_sel else None
    nivel = _nivel_aluno_csp(aluno_obj)
    peso_aderencia = _peso_aderencia_csp(aluno_obj)
    # Fatia 4.B: extrai flag evitar_agonistas da cfg (UI antiga)
    peso_evitar_agon = _peso_evitar_agonistas_csp(cfg_r)
    # Fatia 4.C: extrai tamanho_bloco da cfg (UI antiga, 1/2/3)
    tam_pref, peso_tam = _tamanho_e_peso_bloco_csp(cfg_r)

    if demandas_csp:
        resultado = gerar_treino_csp(
            demandas_csp, banco_regen, nivel_aluno=nivel,
            seed=random.randint(0, 2**31 - 1),
            variedade=ConfigVariedade(),
            peso_aderencia=peso_aderencia,
            peso_evitar_agonistas=peso_evitar_agon,
            tamanho_preferido=tam_pref,
            peso_tamanho_bloco=peso_tam,
        )
        nome_custom = cfg_r.get("nome_custom", "")
        tipo_label = nome_custom or sessoes_ativas[t].tipo
        if resultado.get("viavel"):
            nova = _resultado_csp_pra_sessao(resultado, tipo_label)
        else:
            # Fallback: pool insuficiente no CSP. Mantém sessão atual e
            # devolve aviso visível no card (sem trocar nada).
            nova = sessoes_ativas[t]
            nova.avisos = list(nova.avisos or []) + [{
                "tipo": "h_r1_degradado",
                "subregiao": "(regeneração CSP)",
                "eixo": "",
                "motivo": f"motor CSP inviável (status={resultado.get('status')}); treino mantido",
            }]
    else:
        # cfg sem demandas reconhecíveis — mantém sessão atual.
        nova = sessoes_ativas[t]

    sessoes_ativas[t] = nova
    salvar_sessoes_disco()
    return render_template("_treino_card.html", sessao=nova, idx=t,
                           modo="visualizar", padroes_labels=PADROES_LABELS, alunos=carregar_alunos())

@app.route("/treino/<int:t>/substituir/<path:nome_ex>", methods=["POST"])
def treino_substituir(t, nome_ex):
    global sessoes_ativas, historico_substituicoes
    if t >= len(sessoes_ativas): return "", 404

    # Localizar posição (treino, bloco, slot) — chave estável do histórico de sugestões
    pos_key = None
    for bi, b in enumerate(sessoes_ativas[t].blocos):
        if b.ex1 and b.ex1.nome == nome_ex: pos_key = (t, bi, "ex1"); break
        if b.ex2 and b.ex2.nome == nome_ex: pos_key = (t, bi, "ex2"); break
        if b.ex3 and b.ex3.nome == nome_ex: pos_key = (t, bi, "ex3"); break

    nomes_outros_treinos = {ex.nome for i, s in enumerate(sessoes_ativas) if i != t
                            for b in s.blocos for ex in [b.ex1, b.ex2, b.ex3] if ex}
    banco_sem_irmaos = [e for e in banco if e.nome not in nomes_outros_treinos]
    banco_subst = banco_sem_irmaos if banco_sem_irmaos else banco

    # Filtrar nomes já sugeridos para esta posição; se esgotou o ciclo, reseta (preservando inicial)
    if pos_key:
        if pos_key not in historico_substituicoes:
            historico_substituicoes[pos_key] = {"inicial": nome_ex, "vistos": {nome_ex}}
        dados = historico_substituicoes[pos_key]
        inicial = dados["inicial"]
        ja_sugeridos = dados["vistos"]
        ex_atual = getattr(sessoes_ativas[t].blocos[pos_key[1]], pos_key[2])
        padrao_alvo = ex_atual.padrao if ex_atual else None
        candidatos_padrao = {e.nome for e in banco_subst if e.padrao == padrao_alvo} if padrao_alvo else set()
        restantes = candidatos_padrao - ja_sugeridos - {nome_ex}
        if restantes:
            banco_subst = [e for e in banco_subst if e.nome not in ja_sugeridos]
        else:
            # Reset do ciclo: preserva o inicial (nunca volta) e o atual (evita repetir em sequência)
            dados["vistos"] = {inicial, nome_ex}
            banco_filtrado = [e for e in banco_subst if e.nome not in dados["vistos"]]
            if banco_filtrado:
                banco_subst = banco_filtrado

    sessoes_ativas[t] = substituir_exercicio(sessoes_ativas[t], nome_ex, banco_subst)

    # Registrar nome efetivamente escolhido
    if pos_key and pos_key in historico_substituicoes:
        novo_ex = getattr(sessoes_ativas[t].blocos[pos_key[1]], pos_key[2], None)
        if novo_ex and novo_ex.nome != nome_ex:
            historico_substituicoes[pos_key]["vistos"].add(novo_ex.nome)

    salvar_sessoes_disco()
    return _responder_card_com_banner(t)

@app.route("/treino/<int:t>/substituir-por", methods=["POST"])
def treino_substituir_por(t):
    global sessoes_ativas
    if t >= len(sessoes_ativas): return "", 404
    nome_atual = request.form.get("nome_atual", "")
    nome_novo = request.form.get("nome_novo", "")
    if not nome_atual or not nome_novo: return "", 400
    sessoes_ativas[t] = substituir_exercicio_por(sessoes_ativas[t], nome_atual, nome_novo, banco)
    salvar_sessoes_disco()
    return _responder_card_com_banner(t)

@app.route("/treino/<int:t>/buscar-substitutos/<path:nome_ex>")
def buscar_subs(t, nome_ex):
    """Returns substitution panel HTML."""
    if t >= len(sessoes_ativas): return "", 404
    padrao = request.args.get("padrao", "")
    purpose = request.args.get("purpose", "")
    unilateral = request.args.get("unilateral", "")
    equipamento = request.args.get("equipamento", "")
    musculo = request.args.get("musculo", "")
    texto = request.args.get("texto", "")

    nomes_em_uso = {e.nome for bloco in sessoes_ativas[t].blocos
                    for e in [bloco.ex1, bloco.ex2, bloco.ex3] if e and e.nome != nome_ex}
    nomes_em_uso |= {ex.nome for i, s in enumerate(sessoes_ativas) if i != t
                     for b in s.blocos for ex in [b.ex1, b.ex2, b.ex3] if ex}

    cands = filtrar_banco(texto=texto, padrao=padrao or None, purpose=purpose or None,
                          unilateral=unilateral or None, equipamento=equipamento or None,
                          musculo=musculo or None, max_cx=5)
    cands = [e for e in cands if e.nome not in nomes_em_uso and e.nome != nome_ex]

    return render_template("_substituicao.html", cands=cands[:50], nome_ex=nome_ex, idx=t,
                           padroes_labels=PADROES_LABELS,
                           todos_padroes=sorted(PADROES_LABELS.keys()),
                           todos_equipamentos=todos_equipamentos,
                           todos_musculos=todos_musculos)

# ── Bloco operations ──────────────────────────────────────────

@app.route("/treino/<int:t>/bloco/<int:bi>/mover/<direction>", methods=["POST"])
def bloco_mover(t, bi, direction):
    global sessoes_ativas
    if t >= len(sessoes_ativas): return "", 404
    blocos = sessoes_ativas[t].blocos
    labels = "ABCDEFGHIJKLMNOP"
    if direction == "up" and bi > 0:
        blocos[bi], blocos[bi-1] = blocos[bi-1], blocos[bi]
    elif direction == "down" and bi < len(blocos) - 1:
        blocos[bi], blocos[bi+1] = blocos[bi+1], blocos[bi]
    for j, b in enumerate(blocos): b.label = labels[j] if j < len(labels) else str(j+1)
    salvar_sessoes_disco()
    return _responder_card_com_banner(t)

@app.route("/treino/<int:t>/bloco/<int:bi>/regerar", methods=["POST"])
def bloco_regerar(t, bi):
    """Regenera um bloco individual mantendo os mesmos padrões de movimento."""
    global sessoes_ativas
    if t >= len(sessoes_ativas): return "", 404
    sessao = sessoes_ativas[t]
    if bi < 0 or bi >= len(sessao.blocos): return "", 404
    bloco = sessao.blocos[bi]
    padroes_bloco = [ex.padrao for ex in [bloco.ex1, bloco.ex2, bloco.ex3] if ex]

    # Bloquear exercícios já em uso em qualquer treino (incl. este)
    nomes_bloqueados = set()
    pais_bloqueados = set()
    for i, s in enumerate(sessoes_ativas):
        for j, b in enumerate(s.blocos):
            if i == t and j == bi: continue
            for ex in [b.ex1, b.ex2, b.ex3]:
                if ex:
                    nomes_bloqueados.add(ex.nome)
                    if ex.variacao_de: pais_bloqueados.add(ex.variacao_de)

    banco_filtrado = [e for e in banco
                      if e.nome not in nomes_bloqueados
                      and e.nome not in pais_bloqueados
                      and (e.variacao_de is None or e.variacao_de not in nomes_bloqueados)]

    novos = []
    for padrao in padroes_bloco:
        cands = [e for e in banco_filtrado if e.padrao == padrao]
        if not cands: cands = [e for e in banco if e.padrao == padrao]
        escolhidos = selecionar_evitando_familia(cands, set(), 1)
        if escolhidos:
            novos.append(escolhidos[0])
        elif cands:
            novos.append(cands[0])

    slots = ["ex1", "ex2", "ex3"]
    originais = [bloco.ex1, bloco.ex2, bloco.ex3]
    for k in slots: setattr(bloco, k, None)
    for i, ex in enumerate(novos):
        orig = originais[i] if i < len(originais) else None
        if orig:
            ex.series, ex.reps, ex.rir = orig.series, orig.reps, orig.rir
        setattr(bloco, slots[i], ex)

    salvar_sessoes_disco()
    return _responder_card_com_banner(t)


@app.route("/treino/<int:t>/bloco/<int:bi>/deletar", methods=["POST"])
def bloco_deletar(t, bi):
    global sessoes_ativas
    if t >= len(sessoes_ativas): return "", 404
    labels = "ABCDEFGHIJKLMNOP"
    sessoes_ativas[t].blocos.pop(bi)
    for j, b in enumerate(sessoes_ativas[t].blocos):
        b.label = labels[j] if j < len(labels) else str(j+1)
    salvar_sessoes_disco()
    return _responder_card_com_banner(t)

@app.route("/treino/<int:t>/exercicio/remover/<int:bi>/<int:ei>", methods=["POST"])
def exercicio_remover(t, bi, ei):
    global sessoes_ativas
    if t >= len(sessoes_ativas): return "", 404
    labels = "ABCDEFGHIJKLMNOP"
    bloco = sessoes_ativas[t].blocos[bi]
    if ei == 0:
        bloco.ex1 = bloco.ex2; bloco.ex2 = bloco.ex3; bloco.ex3 = None
    elif ei == 1:
        bloco.ex2 = bloco.ex3; bloco.ex3 = None
    else:
        bloco.ex3 = None
    if not any([bloco.ex1, bloco.ex2, bloco.ex3]):
        sessoes_ativas[t].blocos.pop(bi)
        for j, b in enumerate(sessoes_ativas[t].blocos):
            b.label = labels[j] if j < len(labels) else str(j+1)
    salvar_sessoes_disco()
    return _responder_card_com_banner(t)

@app.route("/treino/<int:t>/exercicio/mover/<int:bi>/<int:ei>/<dest_label>", methods=["POST"])
def exercicio_mover(t, bi, ei, dest_label):
    global sessoes_ativas
    if t >= len(sessoes_ativas): return "", 404
    labels = "ABCDEFGHIJKLMNOP"
    bloco = sessoes_ativas[t].blocos[bi]
    ex = [bloco.ex1, bloco.ex2, bloco.ex3][ei]
    # Remove from source
    if ei == 0: bloco.ex1 = bloco.ex2; bloco.ex2 = bloco.ex3; bloco.ex3 = None
    elif ei == 1: bloco.ex2 = bloco.ex3; bloco.ex3 = None
    else: bloco.ex3 = None
    if not any([bloco.ex1, bloco.ex2, bloco.ex3]):
        sessoes_ativas[t].blocos.pop(bi)
        for j, b in enumerate(sessoes_ativas[t].blocos): b.label = labels[j] if j < len(labels) else str(j+1)
    # Add to dest
    for bd in sessoes_ativas[t].blocos:
        if bd.label == dest_label:
            if bd.ex1 is None: bd.ex1 = ex
            elif bd.ex2 is None: bd.ex2 = ex
            elif bd.ex3 is None: bd.ex3 = ex
            break
    salvar_sessoes_disco()
    return _responder_card_com_banner(t)

def _swap_ex_in_sessao(sessao, bi_a, ei_a, bi_b, ei_b):
    """Troca atomicamente dois exercícios pela posição (bloco_idx, ei). Mesmo treino."""
    attrs = ("ex1", "ex2", "ex3")
    bloco_a = sessao.blocos[bi_a]
    bloco_b = sessao.blocos[bi_b]
    attr_a, attr_b = attrs[ei_a], attrs[ei_b]
    ex_a = getattr(bloco_a, attr_a)
    ex_b = getattr(bloco_b, attr_b)
    setattr(bloco_a, attr_a, ex_b)
    setattr(bloco_b, attr_b, ex_a)


@app.route("/hub/rotina/<int:aluno_id>/treino/<int:t>/swap/<int:bi_a>/<int:ei_a>/<int:bi_b>/<int:ei_b>", methods=["POST"])
def hub_swap_visualizar(aluno_id, t, bi_a, ei_a, bi_b, ei_b):
    """Swap atômico entre 2 exercícios do mesmo treino, em modo visualização do HUB.
    Persiste como rascunho SEM ativar modo edição (edicao_hub fica intacto).
    Retorna card visualizar + banner OOB."""
    sessoes_dicts = _obter_sessoes_trabalho(aluno_id)
    if not sessoes_dicts:
        return '<div class="erro">Nenhuma rotina ativa.</div>', 404
    if t < 0 or t >= len(sessoes_dicts):
        return '<div class="erro">Treino não encontrado.</div>', 404
    sessao_dict = sessoes_dicts[t]
    blocos = sessao_dict["blocos"]
    if bi_a < 0 or bi_a >= len(blocos) or bi_b < 0 or bi_b >= len(blocos):
        return '<div class="erro">Bloco inválido.</div>', 400
    if ei_a not in (0, 1, 2) or ei_b not in (0, 1, 2):
        return '<div class="erro">Posição inválida.</div>', 400
    if (bi_a, ei_a) == (bi_b, ei_b):
        return '<div class="erro">Selecione um exercício diferente.</div>', 400
    attrs = ("ex1", "ex2", "ex3")
    attr_a, attr_b = attrs[ei_a], attrs[ei_b]
    blocos[bi_a][attr_a], blocos[bi_b][attr_b] = blocos[bi_b][attr_b], blocos[bi_a][attr_a]
    salvar_rascunho(aluno_id, sessoes_dicts)

    sessao = _dict_to_sessao(sessao_dict)
    aluno = next((a for a in carregar_alunos() if a["id"] == aluno_id), None)
    nomes_anteriores = set()
    if aluno:
        rot_ant = carregar_rotina_anterior(aluno["nome"], aluno.get("rotina_ativa_id"))
        if rot_ant:
            for s_dict in rot_ant["sessoes"]:
                for b in s_dict["blocos"]:
                    for key in ("ex1", "ex2", "ex3"):
                        ex = b.get(key)
                        if ex: nomes_anteriores.add(ex["nome"])
    rotina_reg = carregar_rotina_ativa(aluno_id)
    intent_atual = carregar_intent_rascunho(aluno_id)
    publicada_para_diff = [] if intent_atual == "nova-rotina" else (rotina_reg["sessoes"] if rotina_reg else [])
    estados_rascunho = _estados_rascunho_por_posicao(sessoes_dicts, publicada_para_diff)
    card = render_template("_hub_treino_card.html", sessao=sessao, idx=t,
                           aluno_id=aluno_id, nomes_anteriores=nomes_anteriores,
                           estados_rascunho=estados_rascunho,
                           padroes_labels=PADROES_LABELS)
    return card + render_draft_banner_oob(aluno_id)


@app.route("/hub/rotina/<int:aluno_id>/treino/<int:t>/substituir-aleatorio/<int:bi>/<slot>", methods=["POST"])
def hub_substituir_aleatorio(aluno_id, t, bi, slot):
    """Substitui um exercício por outro aleatório do mesmo padrão (ou da subregião,
    via param 'escopo'), salvando como rascunho — SEM ativar modo edição.
    Cycle por (aluno_id, t, bi, slot, escopo): trocar de escopo reinicia o cycle."""
    global historico_substituicoes
    if slot not in ("ex1", "ex2", "ex3"):
        return '<div class="erro">Slot inválido.</div>', 400
    escopo = (request.form.get("escopo") or "padrao").strip().lower()
    if escopo not in ("padrao", "subregiao"):
        escopo = "padrao"

    sessoes_dicts = _obter_sessoes_trabalho(aluno_id)
    if not sessoes_dicts:
        return '<div class="erro">Nenhuma rotina ativa.</div>', 404
    if t < 0 or t >= len(sessoes_dicts):
        return '<div class="erro">Treino não encontrado.</div>', 404
    blocos = sessoes_dicts[t]["blocos"]
    if bi < 0 or bi >= len(blocos):
        return '<div class="erro">Bloco inválido.</div>', 400
    ex_atual_dict = blocos[bi].get(slot)
    if not ex_atual_dict:
        return '<div class="erro">Exercício não encontrado.</div>', 404
    nome_ex = ex_atual_dict["nome"]

    # Banco filtrado: exclui nomes em uso nos OUTROS treinos da rotina
    nomes_outros_treinos = set()
    for i, s in enumerate(sessoes_dicts):
        if i == t: continue
        for b in s["blocos"]:
            for k in ("ex1", "ex2", "ex3"):
                ex = b.get(k)
                if ex: nomes_outros_treinos.add(ex["nome"])
    banco_subst = [e for e in banco if e.nome not in nomes_outros_treinos]
    if not banco_subst:
        banco_subst = list(banco)

    # Cycle: chave inclui escopo (toggle reinicia o cycle)
    pos_key = (aluno_id, t, bi, slot, escopo)
    if pos_key not in historico_substituicoes:
        historico_substituicoes[pos_key] = {"inicial": nome_ex, "vistos": {nome_ex}}
    dados = historico_substituicoes[pos_key]
    inicial = dados["inicial"]
    ja_sugeridos = dados["vistos"]
    if escopo == "subregiao":
        sub_alvo = ex_atual_dict.get("subregiao") or PADRAO_PARA_SUBREGIAO.get(ex_atual_dict.get("padrao", ""))
        candidatos_escopo = {e.nome for e in banco_subst if e.subregiao == sub_alvo} if sub_alvo else set()
    else:
        candidatos_escopo = {e.nome for e in banco_subst if e.padrao == ex_atual_dict.get("padrao")}
    restantes = candidatos_escopo - ja_sugeridos - {nome_ex}
    if restantes:
        banco_subst = [e for e in banco_subst if e.nome not in ja_sugeridos]
    else:
        # Reset do ciclo: preserva inicial (nunca volta) e atual (evita repetição em sequência)
        dados["vistos"] = {inicial, nome_ex}
        banco_filtrado = [e for e in banco_subst if e.nome not in dados["vistos"]]
        if banco_filtrado:
            banco_subst = banco_filtrado

    # Aplicar substituição via gerador (usa Sessao)
    sessao_obj = _dict_to_sessao(sessoes_dicts[t])
    nova_sessao = substituir_exercicio(sessao_obj, nome_ex, banco_subst, escopo=escopo)

    # Verificar se realmente mudou (caso não haja candidatos)
    novo_dict = _sessao_to_dict(nova_sessao)
    novo_ex = novo_dict["blocos"][bi].get(slot)
    if not novo_ex or novo_ex["nome"] == nome_ex:
        # Nada substituído — devolve card atual sem mexer no rascunho
        sessao_render = _dict_to_sessao(sessoes_dicts[t])
    else:
        sessoes_dicts[t] = novo_dict
        salvar_rascunho(aluno_id, sessoes_dicts)
        historico_substituicoes[pos_key]["vistos"].add(novo_ex["nome"])
        sessao_render = nova_sessao

    aluno = next((a for a in carregar_alunos() if a["id"] == aluno_id), None)
    nomes_anteriores = set()
    if aluno:
        rot_ant = carregar_rotina_anterior(aluno["nome"], aluno.get("rotina_ativa_id"))
        if rot_ant:
            for s_dict in rot_ant["sessoes"]:
                for b in s_dict["blocos"]:
                    for key in ("ex1", "ex2", "ex3"):
                        ex = b.get(key)
                        if ex: nomes_anteriores.add(ex["nome"])
    rotina_reg = carregar_rotina_ativa(aluno_id)
    intent_atual = carregar_intent_rascunho(aluno_id)
    publicada_para_diff = [] if intent_atual == "nova-rotina" else (rotina_reg["sessoes"] if rotina_reg else [])
    estados_rascunho = _estados_rascunho_por_posicao(sessoes_dicts, publicada_para_diff)
    card = render_template("_hub_treino_card.html", sessao=sessao_render, idx=t,
                           aluno_id=aluno_id, nomes_anteriores=nomes_anteriores,
                           estados_rascunho=estados_rascunho,
                           padroes_labels=PADROES_LABELS)
    return card + render_draft_banner_oob(aluno_id)


@app.route("/treino/<int:t>/exercicio/<int:bi>/<int:ei>/destacar", methods=["POST"])
def exercicio_destacar(t, bi, ei):
    """Remove exercise from its block and create a new block with it at the end."""
    global sessoes_ativas
    if t >= len(sessoes_ativas): return "", 404
    labels = "ABCDEFGHIJKLMNOP"
    bloco = sessoes_ativas[t].blocos[bi]
    ex = [bloco.ex1, bloco.ex2, bloco.ex3][ei]
    if ex is None: return "", 400
    if ei == 0: bloco.ex1 = bloco.ex2; bloco.ex2 = bloco.ex3; bloco.ex3 = None
    elif ei == 1: bloco.ex2 = bloco.ex3; bloco.ex3 = None
    else: bloco.ex3 = None
    if not any([bloco.ex1, bloco.ex2, bloco.ex3]):
        sessoes_ativas[t].blocos.pop(bi)
    for j, b in enumerate(sessoes_ativas[t].blocos):
        b.label = labels[j] if j < len(labels) else str(j + 1)
    n = len(sessoes_ativas[t].blocos)
    lbl = labels[n] if n < len(labels) else str(n + 1)
    sessoes_ativas[t].blocos.append(SuperSerie(label=lbl, ex1=ex, ex2=None, ex3=None))
    salvar_sessoes_disco()
    return _responder_card_com_banner(t)

@app.route("/treino/<int:t>/bloco/<int:bi>/adicionar/<nome_ex>", methods=["POST"])
def bloco_adicionar_exercicio(t, bi, nome_ex):
    global sessoes_ativas
    if t >= len(sessoes_ativas): return "", 404
    novo_ex = next((e for e in banco if e.nome == nome_ex), None)
    if novo_ex:
        bloco = sessoes_ativas[t].blocos[bi]
        if bloco.ex1 is None: bloco.ex1 = novo_ex
        elif bloco.ex2 is None: bloco.ex2 = novo_ex
        elif bloco.ex3 is None: bloco.ex3 = novo_ex
    salvar_sessoes_disco()
    return _responder_card_com_banner(t)

@app.route("/treino/<int:t>/novo-bloco/<path:nome_ex>", methods=["POST"])
def novo_bloco(t, nome_ex):
    global sessoes_ativas
    if t >= len(sessoes_ativas): return "", 404
    novo_ex = next((e for e in banco if e.nome == nome_ex), None)
    if novo_ex:
        labels = "ABCDEFGHIJKLMNOP"
        n = len(sessoes_ativas[t].blocos)
        lbl = labels[n] if n < len(labels) else str(n+1)
        sessoes_ativas[t].blocos.append(SuperSerie(label=lbl, ex1=novo_ex, ex2=None, ex3=None))
    salvar_sessoes_disco()
    return _responder_card_com_banner(t)

@app.route("/treino/<int:t>/prescricao/<int:bi>/<int:ei>", methods=["POST"])
def salvar_prescricao(t, bi, ei):
    global sessoes_ativas
    if t >= len(sessoes_ativas): return "", 404
    bloco = sessoes_ativas[t].blocos[bi]
    ex = [bloco.ex1, bloco.ex2, bloco.ex3][ei]
    if ex:
        ex.series = int(request.form.get("series", 3))
        ex.reps = request.form.get("reps", "8-12").strip() or None
        ex.rir = int(request.form.get("rir", 2))
    salvar_sessoes_disco()
    return _responder_card_com_banner(t)


@app.route("/treino/<int:t>/prescricao/<int:bi>/<int:ei>/limpar", methods=["POST"])
def limpar_prescricao(t, bi, ei):
    """Zera séries/reps/RIR do exercício alvo (volta para 'sem prescrição')."""
    global sessoes_ativas
    if t >= len(sessoes_ativas): return "", 404
    bloco = sessoes_ativas[t].blocos[bi]
    ex = [bloco.ex1, bloco.ex2, bloco.ex3][ei]
    if ex:
        ex.series = None
        ex.reps = None
        ex.rir = None
    salvar_sessoes_disco()
    return _responder_card_com_banner(t)

# ── Busca de exercícios (para painéis de adicionar/novo bloco) ─

@app.route("/buscar-exercicios")
def buscar_exercicios():
    """API endpoint for searching exercises (used by add/new block panels)."""
    texto = request.args.get("texto", "")
    padrao = request.args.get("padrao", "")
    purpose = request.args.get("purpose", "")
    unilateral = request.args.get("unilateral", "")
    equipamento = request.args.get("equipamento", "")
    musculo = request.args.get("musculo", "")
    excluir = set(request.args.get("excluir", "").split(",")) if request.args.get("excluir") else set()

    cands = filtrar_banco(texto=texto, padrao=padrao or None, purpose=purpose or None,
                          unilateral=unilateral or None, equipamento=equipamento or None,
                          musculo=musculo or None)
    cands = [e for e in cands if e.nome not in excluir]

    html = f"<p class='meta-count'>{len(cands)} exercício(s)</p>"
    for e in cands:
        html += (f'<label class="ex-option">'
                 f'<input type="radio" name="exercicio_escolhido" value="{e.nome}">'
                 f'<span>{e.nome}</span>'
                 f'<span class="ex-option-meta">{e.purpose} · {e.eq_primario}</span>'
                 f'</label>')
    if not cands:
        html += "<p class='meta-count'>Nenhum encontrado.</p>"
    return html

# ══════════════════════════════════════════════════════════════
# ROTAS — PNG / ZIP DOWNLOAD
# ══════════════════════════════════════════════════════════════

@app.route("/treino/<int:t>/png/<aluno>")
def download_png(t, aluno):
    if t >= len(sessoes_ativas): return "", 404
    lp = Path("static/logo.png")
    logo_b = lp.read_bytes() if lp.exists() else None
    png = gerar_png(sessoes_ativas[t], aluno, logo_bytes=logo_b)
    return send_file(io.BytesIO(png), mimetype="image/png",
                     download_name=f"treino{t+1}_{aluno.lower().replace(' ','_')}.png",
                     as_attachment=True)

@app.route("/treinos/zip/<aluno>")
def download_zip(aluno):
    lp = Path("static/logo.png")
    logo_b = lp.read_bytes() if lp.exists() else None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for t, sessao in enumerate(sessoes_ativas):
            png = gerar_png(sessao, aluno, logo_bytes=logo_b)
            zf.writestr(f"treino{t+1}_{aluno.lower().replace(' ','_')}.png", png)
    buf.seek(0)
    return send_file(buf, mimetype="application/zip",
                     download_name=f"treinos_{aluno.lower().replace(' ','_')}.zip",
                     as_attachment=True)

# ══════════════════════════════════════════════════════════════
# ROTAS — HISTÓRICO
# ══════════════════════════════════════════════════════════════

@app.route("/historico")
def historico_page():
    aluno_filtro = request.args.get("aluno", "").strip()
    busca = request.args.get("busca", "").strip()
    registros = carregar_historico()
    if aluno_filtro:
        registros = [r for r in registros if r.get("aluno") == aluno_filtro]
    if busca:
        busca_lower = busca.lower()
        registros = [r for r in registros if busca_lower in (r.get("etiqueta") or "").lower()]
    alunos_historico = nomes_unicos_historico()

    # Enriquecimento (mobile): periodo, ano, flag rotina ativa, mini pills
    from datetime import datetime
    MESES = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
             'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    alunos_atuais = carregar_alunos()
    rotina_ativa_por_aluno = {a["nome"]: a.get("rotina_ativa_id") for a in alunos_atuais}
    anos_disponiveis = set()
    for idx, r in enumerate(registros):
        data_ref = r.get("data_atualizada") or r.get("data_salvo") or r.get("data") or ""
        ano, mes_num, dia = "", 0, ""
        if data_ref:
            try:
                dt = datetime.strptime(data_ref.split(" ")[0], "%d/%m/%Y")
                ano = str(dt.year)
                mes_num = dt.month
                dia = dt.strftime("%d/%m")
                anos_disponiveis.add(ano)
            except (ValueError, IndexError):
                pass
        r["_ano"] = ano
        r["_mes_label"] = MESES[mes_num] if mes_num else "Sem data"
        r["_grupo"] = f"{ano}-{mes_num:02d}" if ano and mes_num else "sem-data"
        r["_data_curta"] = dia
        r["_eh_ativa"] = rotina_ativa_por_aluno.get(r.get("aluno")) == r.get("id")
        r["_p_label"] = f"P{idx + 1}"
        # Mini pills dos treinos: lê sessoes e extrai .tipo (max 5)
        sessoes = r.get("sessoes", []) or []
        r["_mini_pills"] = [
            {"n": i + 1, "nome": (s.get("tipo") or f"Treino {i+1}")[:18]}
            for i, s in enumerate(sessoes[:5])
        ]

    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        return render_template("historico.html", historico=registros,
                               padroes_labels=PADROES_LABELS,
                               alunos_historico=alunos_historico,
                               aluno_filtro=aluno_filtro,
                               busca=busca)
    return render_template("historico_page.html",
                           active_page="historico",
                           historico=registros,
                           padroes_labels=PADROES_LABELS,
                           alunos_historico=alunos_historico,
                           aluno_filtro=aluno_filtro,
                           busca=busca,
                           anos_disponiveis=sorted(anos_disponiveis, reverse=True))

@app.route("/aluno-historico")
def aluno_historico():
    nome = request.args.get("nome", "").strip()
    if not nome:
        return ""
    # Limita às 2 rotinas mais recentes pra não poluir a UI.
    registros = buscar_historico_por_aluno(nome)[:2]
    return render_template("_historico_aluno.html", registros=registros,
                           padroes_labels=PADROES_LABELS)

@app.route("/historico/<reg_id>/configs")
def historico_configs(reg_id):
    reg = carregar_registro(reg_id)
    if not reg:
        return jsonify({"error": "Registro nao encontrado"}), 404
    cfg_data = reg.get("configs")
    if not cfg_data:
        return jsonify({"error": "Sem configs salvas neste registro"}), 404
    if isinstance(cfg_data, list):
        cfg_data = {"globals": {}, "treinos": cfg_data}
    return jsonify(cfg_data)

@app.route("/historico/salvar", methods=["POST"])
def historico_salvar():
    aluno = request.form.get("aluno", "")
    etiqueta = request.form.get("etiqueta", "").strip() or f"{len(sessoes_ativas)} treino(s)"
    configs_serial = None
    if configs_geradas:
        configs_serial = {"globals": opcoes_globais, "treinos": _configs_to_serializable(configs_geradas)}
    reg_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + secrets.token_hex(2)
    salvar_historico_registro(
        reg_id=reg_id,
        data_salvo=datetime.now().strftime("%d/%m/%Y %H:%M"),
        aluno=aluno or "—",
        etiqueta=etiqueta,
        n_treinos=len(sessoes_ativas),
        sessoes=[_sessao_to_dict(s) for s in sessoes_ativas],
        configs=configs_serial,
    )
    if aluno:
        aluno_db = buscar_aluno_por_nome(aluno)
        if aluno_db:
            definir_rotina_ativa(aluno_db["id"], reg_id)
    return '<p class="sucesso">Salvo no histórico!</p>'

@app.route("/historico/<reg_id>/carregar", methods=["POST"])
def historico_carregar(reg_id):
    global sessoes_ativas, configs_geradas, opcoes_globais
    reg = carregar_registro(reg_id)
    if not reg: return "Registro não encontrado", 404
    sessoes_ativas = [_dict_to_sessao(s) for s in reg["sessoes"]]
    cfg_data = reg.get("configs")
    if cfg_data and isinstance(cfg_data, dict) and "treinos" in cfg_data:
        configs_geradas = _configs_from_serializable(cfg_data["treinos"])
        opcoes_globais = cfg_data.get("globals", {})
    else:
        configs_geradas = []
        opcoes_globais = {}
    salvar_sessoes_disco()
    return render_template("_resultado.html", sessoes=sessoes_ativas,
                           padroes_labels=PADROES_LABELS, alunos=carregar_alunos())

@app.route("/historico/<reg_id>/ver")
def historico_ver(reg_id):
    reg = carregar_registro(reg_id)
    if not reg: return "Registro não encontrado", 404
    sessoes_reg = [_dict_to_sessao(s) for s in reg["sessoes"]]
    return render_template("_historico_detalhe.html", sessoes=sessoes_reg,
                           padroes_labels=PADROES_LABELS, reg_id=reg_id)

@app.route("/historico/<reg_id>/apagar", methods=["DELETE"])
def historico_apagar(reg_id):
    deletar_historico(reg_id)
    registros = carregar_historico()
    return render_template("historico.html", historico=registros,
                           padroes_labels=PADROES_LABELS,
                           alunos_historico=nomes_unicos_historico(),
                           aluno_filtro="", busca="")


@app.route("/historico/apagar-selecionados", methods=["POST"])
def historico_apagar_selecionados():
    ids = request.form.getlist("sel")
    for reg_id in ids:
        deletar_historico(reg_id)
    registros = carregar_historico()
    return render_template("historico.html", historico=registros,
                           padroes_labels=PADROES_LABELS,
                           alunos_historico=nomes_unicos_historico(),
                           aluno_filtro="", busca="")

# ══════════════════════════════════════════════════════════════
# ROTAS — ALUNOS
# ══════════════════════════════════════════════════════════════

def _render_alunos_com_dropdown(alunos):
    """Renderiza alunos.html + dropdown OOB para atualizar sel-aluno na aba treinos."""
    nomes_alunos = {a["nome"] for a in alunos}
    nomes_hist = [n for n in nomes_unicos_historico() if n not in nomes_alunos]
    html = render_template("alunos.html", alunos=alunos)
    html += render_template("_aluno_dropdown.html",
                            alunos_dropdown=alunos,
                            nomes_hist_dropdown=nomes_hist)
    return html

@app.route("/alunos")
def alunos_page():
    is_htmx = request.headers.get("HX-Request") == "true"
    alunos = carregar_alunos()
    if is_htmx:
        return render_template("alunos.html", alunos=alunos)
    # Enriquecimento (mobile): n_treinos, data_atualizada, dias_atras p/ status dot
    from datetime import datetime
    hoje = datetime.now()
    for a in alunos:
        a["_n_treinos"] = 0
        a["_atualizado_label"] = ""
        a["_dias_atras"] = None
        rid = a.get("rotina_ativa_id")
        if not rid:
            continue
        reg = carregar_registro(rid)
        if not reg:
            continue
        a["_n_treinos"] = reg.get("n_treinos", 0) or len(reg.get("sessoes", []))
        data_ref = reg.get("data_atualizada") or reg.get("data_salvo") or reg.get("data") or ""
        if data_ref:
            try:
                dt = datetime.strptime(data_ref.split(" ")[0], "%d/%m/%Y")
                dias = (hoje - dt).days
                a["_dias_atras"] = dias
                if dias == 0: a["_atualizado_label"] = "hoje"
                elif dias == 1: a["_atualizado_label"] = "1d"
                elif dias < 30: a["_atualizado_label"] = f"{dias}d"
                else: a["_atualizado_label"] = f"{dias // 30}m"
            except (ValueError, IndexError):
                pass
    return render_template("alunos_page.html", active_page="alunos", alunos=alunos)

@app.route("/alunos/novo", methods=["POST"])
def aluno_novo():
    alunos = carregar_alunos()
    nome = request.form.get("nome", "").strip()
    if not nome:
        return '<p class="erro">Nome é obrigatório.</p>'
    if any(a["nome"].lower() == nome.lower() for a in alunos):
        return f'<p class="erro">Já existe \'{nome}\'.</p>'
    salvar_aluno(
        nome=nome,
        nivel=request.form.get("nivel", "intermediario"),
        objetivo=request.form.get("objetivo", "hipertrofia"),
        restricoes=[r.strip() for r in request.form.get("restricoes", "").split(",") if r.strip()],
        obs=request.form.get("obs", "").strip(),
        aderencia=request.form.get("aderencia", "media"),
    )
    return _render_alunos_com_dropdown(carregar_alunos())

@app.route("/alunos/<int:i>/editar", methods=["POST"])
def aluno_editar(i):
    alunos = carregar_alunos()
    aluno = next((a for a in alunos if a["id"] == i), None)
    if not aluno: return "", 404
    nome = request.form.get("nome", "").strip()
    if not nome: return '<p class="erro">Nome obrigatório.</p>'
    editar_aluno(
        aluno_id=i,
        nome=nome,
        nivel=request.form.get("nivel", "intermediario"),
        objetivo=request.form.get("objetivo", "hipertrofia"),
        restricoes=[r.strip() for r in request.form.get("restricoes", "").split(",") if r.strip()],
        obs=request.form.get("obs", "").strip(),
        aderencia=request.form.get("aderencia", "media"),
    )
    return _render_alunos_com_dropdown(carregar_alunos())

@app.route("/alunos/<int:i>/deletar", methods=["DELETE"])
def aluno_deletar(i):
    deletar_aluno(i)
    return _render_alunos_com_dropdown(carregar_alunos())

@app.route("/alunos/deletar-multiplos", methods=["POST"])
def alunos_deletar_multiplos():
    raw = request.form.get("ids", "")
    ids = [int(x) for x in raw.split(",") if x.strip().isdigit()]
    for aluno_id in ids:
        deletar_aluno(aluno_id)
    return _render_alunos_com_dropdown(carregar_alunos())

# ══════════════════════════════════════════════════════════════

init_db()
migrar_json_para_sqlite()
sessoes_ativas = carregar_sessoes_disco()

if __name__ == "__main__":
    if sessoes_ativas:
        print(f"  Restauradas {len(sessoes_ativas)} sessoes ativas")
    print(f"[OK] Banco carregado: {len(banco)} exercicios")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    print(f"[OK] Acesse: http://localhost:{port}")
    app.run(debug=debug, host="0.0.0.0", port=port)
