"""
BF Treinamento — Versão Flask + HTMX (completa)
"""

from flask import Flask, render_template, request, send_file, redirect, url_for, jsonify
import random, json, copy, io, zipfile, unicodedata, secrets
from pathlib import Path
from datetime import datetime
from gerador_treino import (
    carregar_banco, gerar_sessao, gerar_sessao_por_demandas, gerar_multiplos_treinos,
    substituir_exercicio, buscar_substitutos, substituir_exercicio_por,
    expandir_para_padroes,
    TEMPLATES, TEMPLATE_EPP, EXERCICIOS_POR_PADRAO,
    PADRAO_PARA_SUBREGIAO, SUBREGIAO_PARA_REGIAO,
    REGIAO_PARA_SUBREGIOES, SUBREGIAO_PARA_PADROES,
    Exercicio, Sessao, SuperSerie,
)
from gerar_imagem import gerar_png
from database import (
    init_db, migrar_json_para_sqlite,
    carregar_alunos, salvar_aluno, editar_aluno, deletar_aluno,
    carregar_historico, carregar_registro, salvar_historico_registro, deletar_historico,
    buscar_historico_por_aluno, nomes_unicos_historico,
)

app = Flask(__name__)
app.secret_key = "bf-treinamento-dev"

# ══════════════════════════════════════════════════════════════
# DADOS
# ══════════════════════════════════════════════════════════════

banco = carregar_banco("banco_exercicios.xlsx")

SESSOES_PATH = Path("sessoes_salvas.json")

# Estado em memória
sessoes_ativas: list[Sessao] = []
configs_geradas: list[dict] = []
opcoes_globais: dict = {}
# referencias: cada item = {"sessao": Sessao, "origem": {...}, "id_ref": str}
referencias: list[dict] = []

def _ref_sessoes():
    return [r["sessao"] for r in referencias]

def _nomes_ref_set():
    nomes = set()
    for r in referencias:
        for bloco in r["sessao"].blocos:
            for ex in [bloco.ex1, bloco.ex2, bloco.ex3]:
                if ex:
                    nomes.add(ex.nome)
    return nomes

def _novo_id_ref():
    return secrets.token_hex(4)

PADROES_LABELS = {
    "squat": "Agachamento", "hinge": "Extensão de quadril",
    "knee_flexion": "Flexão de joelho", "abduction": "Abdução",
    "adduction": "Adução", "flexao_plantar": "Flexão plantar",
    "empurrar_compostos": "Empurrar compostos", "empurrar_isolados": "Empurrar isolados",
    "remadas": "Remadas", "puxadas": "Puxadas",
    "ombro_composto": "Desenvolvimento", "ombro_isolado": "Elevações",
    "posterior_ombro": "Posterior de ombro",
    "biceps": "Bíceps", "triceps": "Tríceps",
    "core_isometrico": "Core isométrico", "core_dinamico": "Core dinâmico",
    "cardio": "Cardio",
}

REGIOES_LABELS = {"upper": "Membros superiores", "lower": "Membros inferiores", "core": "Core", "cardio": "Cardio"}
SUBREGIOES_LABELS = {
    "peito": "Peito", "costas": "Costas", "ombro": "Ombro", "bracos": "Braços",
    "perna_anterior": "Perna anterior", "perna_posterior": "Perna posterior",
    "adutores": "Adutores", "panturrilha": "Panturrilha", "core": "Core", "cardio": "Cardio",
}
ORDEM_REGIOES = ["upper", "lower", "core", "cardio"]
ORDEM_SUBREGIOES = {
    "upper": ["peito", "costas", "ombro", "bracos"],
    "lower": ["perna_anterior", "perna_posterior", "adutores", "panturrilha"],
    "core": ["core"], "cardio": ["cardio"],
}
ORDEM_PADROES = {
    "peito": ["empurrar_compostos", "empurrar_isolados"],
    "costas": ["remadas", "puxadas"],
    "ombro": ["ombro_composto", "ombro_isolado", "posterior_ombro"],
    "bracos": ["biceps", "triceps"],
    "perna_anterior": ["squat"], "perna_posterior": ["hinge", "knee_flexion", "abduction"],
    "adutores": ["adduction"], "panturrilha": ["flexao_plantar"],
    "core": ["core_isometrico", "core_dinamico"], "cardio": ["cardio"],
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
    return {"nome": ex.nome, "variacao_de": ex.variacao_de,
            "eq_primario": ex.eq_primario, "eq_secundario": ex.eq_secundario,
            "regiao": ex.regiao, "padrao": ex.padrao, "purpose": ex.purpose,
            "unilateral": ex.unilateral, "complexidade": ex.complexidade,
            "fadiga": ex.fadiga, "circuito": ex.circuito,
            "similaridade": ex.similaridade, "musculo_primario": ex.musculo_primario,
            "obs": ex.obs, "series": ex.series, "reps": ex.reps, "rir": ex.rir}

def _dict_to_exercicio(d):
    return Exercicio(nome=d["nome"], variacao_de=d.get("variacao_de"),
        eq_primario=d.get("eq_primario",""), eq_secundario=d.get("eq_secundario"),
        regiao=d.get("regiao",""), padrao=d.get("padrao",""), purpose=d.get("purpose",""),
        unilateral=d.get("unilateral",""), complexidade=d.get("complexidade",1),
        fadiga=d.get("fadiga",1), circuito=d.get("circuito","não"),
        similaridade=d.get("similaridade",""), musculo_primario=d.get("musculo_primario",""),
        obs=d.get("obs"), series=d.get("series"), reps=d.get("reps"), rir=d.get("rir"))

def _sessao_to_dict(s):
    blocos = []
    for b in s.blocos:
        blocos.append({"label": b.label,
            "ex1": _exercicio_to_dict(b.ex1) if b.ex1 else None,
            "ex2": _exercicio_to_dict(b.ex2) if b.ex2 else None,
            "ex3": _exercicio_to_dict(b.ex3) if b.ex3 else None})
    return {"tipo": s.tipo, "blocos": blocos}

def _dict_to_sessao(d):
    blocos = []
    for b in d["blocos"]:
        blocos.append(SuperSerie(label=b["label"],
            ex1=_dict_to_exercicio(b["ex1"]) if b.get("ex1") else None,
            ex2=_dict_to_exercicio(b["ex2"]) if b.get("ex2") else None,
            ex3=_dict_to_exercicio(b["ex3"]) if b.get("ex3") else None))
    return Sessao(tipo=d["tipo"], blocos=blocos)

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
    nomes_alunos = {a["nome"] for a in alunos}
    nomes_hist = [n for n in nomes_unicos_historico() if n not in nomes_alunos]
    return render_template("treinos.html",
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
        referencias=referencias,
        tem_referencia=bool(referencias),
    )

# ══════════════════════════════════════════════════════════════
# ROTAS — GERAÇÃO DE TREINOS
# ══════════════════════════════════════════════════════════════

@app.route("/gerar", methods=["POST"])
def gerar():
    global sessoes_ativas, configs_geradas, opcoes_globais
    n_treinos = int(request.form.get("n_treinos", 1))
    max_cx = int(request.form.get("max_complexidade", 5))
    tam_bloco = int(request.form.get("tamanho_bloco", 2))
    variar = request.form.get("variar_entre") == "on"
    evitar_agon = request.form.get("evitar_agonistas") == "on"

    all_configs = []

    for t in range(n_treinos):
        cfg = {"max_complexidade": max_cx, "tamanho_bloco": tam_bloco,
               "equipamentos_bloqueados": [], "evitar_agonistas": evitar_agon}

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
            # Lateralidade squat
            squat_bi = int(request.form.get(f"squat_bi_{t}", 0))
            squat_uni = int(request.form.get(f"squat_uni_{t}", 0))
            if squat_bi > 0 or squat_uni > 0:
                lat = {}
                if squat_bi > 0: lat["bilateral"] = squat_bi
                if squat_uni > 0: lat["unilateral"] = squat_uni
                epp["squat"] = lat
                cfg["lateralidade_por_padrao"] = {"squat": lat}

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

            # Lateralidade squat
            lat_padrao = {}
            squat_bi = int(request.form.get(f"squat_bi_{t}", 0))
            squat_uni = int(request.form.get(f"squat_uni_{t}", 0))
            if squat_bi > 0 or squat_uni > 0:
                lat = {}
                if squat_bi > 0: lat["bilateral"] = squat_bi
                if squat_uni > 0: lat["unilateral"] = squat_uni
                # Find which demand scope contains squat
                for n, e, q in demandas:
                    if (n == "padrao" and e == "squat") or (n == "subregiao" and e == "perna_anterior"):
                        lat_padrao[e] = lat
                        break
                cfg["lateralidade_por_padrao"] = lat_padrao

            cfg["demandas"] = demandas if demandas else None
            cfg["padroes"] = []
            cfg["exercicios_por_padrao"] = {}

        # Fixed exercises
        fixos_str = request.form.get(f"fixos_{t}", "")
        fixos_nomes = [n.strip() for n in fixos_str.split(",") if n.strip()]
        cfg["exercicios_travados"] = [e for e in banco if e.nome in set(fixos_nomes)]

        all_configs.append(cfg)

    # Validate
    vazios = [i+1 for i, c in enumerate(all_configs)
              if not c.get("padroes") and not c.get("demandas")]
    if vazios:
        return f"<p class='aviso'>Selecione categorias no(s) Treino(s) {', '.join(str(x) for x in vazios)}.</p>"

    banco_gerar = list(banco)

    # Bloqueio por referências manuais
    ref_sessoes = _ref_sessoes()
    if ref_sessoes:
        nomes_ref = set()
        pais_ref = set()
        for s in ref_sessoes:
            for bloco in s.blocos:
                for ex in [bloco.ex1, bloco.ex2, bloco.ex3]:
                    if ex:
                        nomes_ref.add(ex.nome)
                        if ex.variacao_de:
                            pais_ref.add(ex.variacao_de)
        banco_gerar = [e for e in banco_gerar
                       if e.nome not in nomes_ref
                       and e.nome not in pais_ref
                       and (e.variacao_de is None or e.variacao_de not in nomes_ref)]

    # Bloqueio por histórico do aluno
    aluno_nome = request.form.get("aluno", "").strip()
    evitar_ultimos = int(request.form.get("evitar_ultimos", 0))
    n_bloqueados_hist = 0
    if aluno_nome and evitar_ultimos > 0:
        registros_aluno = buscar_historico_por_aluno(aluno_nome)[:evitar_ultimos]
        nomes_hist = set()
        pais_hist = set()
        for reg_resumo in registros_aluno:
            reg_full = carregar_registro(reg_resumo["id"])
            if not reg_full:
                continue
            for sess_dict in reg_full["sessoes"]:
                for bloco in sess_dict["blocos"]:
                    for key in ("ex1", "ex2", "ex3"):
                        ex = bloco.get(key)
                        if ex:
                            nomes_hist.add(ex["nome"])
                            if ex.get("variacao_de"):
                                pais_hist.add(ex["variacao_de"])
        banco_antes = len(banco_gerar)
        banco_gerar = [e for e in banco_gerar
                       if e.nome not in nomes_hist
                       and e.nome not in pais_hist
                       and (e.variacao_de is None or e.variacao_de not in nomes_hist)]
        n_bloqueados_hist = banco_antes - len(banco_gerar)

    sessoes_ativas = gerar_multiplos_treinos(banco_gerar, all_configs, variar_entre_treinos=variar)
    configs_geradas = all_configs
    opcoes_globais = {
        "n_treinos": n_treinos,
        "max_complexidade": max_cx,
        "tamanho_bloco": tam_bloco,
        "variar_entre": variar,
        "evitar_agonistas": evitar_agon,
    }
    salvar_sessoes_disco()

    # Auto-fixar referências do último período do aluno (Etapa 4)
    auto_ref_etiqueta = None
    if aluno_nome and evitar_ultimos > 0:
        registros_aluno = buscar_historico_por_aluno(aluno_nome)
        if registros_aluno:
            ultimo_reg = carregar_registro(registros_aluno[0]["id"])
            if ultimo_reg:
                # Limpa refs anteriores e carrega do último registro
                referencias.clear()
                for ti, sess_dict in enumerate(ultimo_reg["sessoes"]):
                    sessao_ref = _dict_to_sessao(sess_dict)
                    referencias.append({
                        "sessao": sessao_ref,
                        "origem": {
                            "etiqueta": ultimo_reg.get("etiqueta", ""),
                            "aluno": ultimo_reg.get("aluno", "—"),
                            "data": ultimo_reg.get("data_salvo", "—"),
                            "reg_id": ultimo_reg["id"],
                            "treino_idx": ti,
                        },
                        "id_ref": _novo_id_ref(),
                    })
                auto_ref_etiqueta = ultimo_reg.get("etiqueta") or ultimo_reg.get("data_salvo", "")

    return render_template("_resultado.html", sessoes=sessoes_ativas,
                           padroes_labels=PADROES_LABELS, alunos=carregar_alunos(),
                           tem_referencia=bool(referencias),
                           referencias=referencias,
                           auto_ref_etiqueta=auto_ref_etiqueta,
                           nomes_ref=_nomes_ref_set())

# ══════════════════════════════════════════════════════════════
# ROTAS — AÇÕES POR TREINO
# ══════════════════════════════════════════════════════════════

@app.route("/treino/<int:t>/visualizar")
def treino_visualizar(t):
    if t >= len(sessoes_ativas): return "Treino não encontrado", 404
    return render_template("_treino_card.html", sessao=sessoes_ativas[t], idx=t,
                           modo="visualizar", padroes_labels=PADROES_LABELS, alunos=carregar_alunos(),
                           nomes_ref=_nomes_ref_set())

@app.route("/treino/<int:t>/editar")
def treino_editar(t):
    if t >= len(sessoes_ativas): return "Treino não encontrado", 404
    return render_template("_treino_card.html", sessao=sessoes_ativas[t], idx=t,
                           modo="editar", padroes_labels=PADROES_LABELS,
                           alunos=carregar_alunos(),
                           todos_padroes=sorted(PADROES_LABELS.keys()),
                           todos_equipamentos=todos_equipamentos,
                           todos_musculos=todos_musculos)

@app.route("/treino/<int:t>/regerar", methods=["POST"])
def treino_regerar(t):
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

    # Block exercises from other workouts
    exs_outros = [ex for i, s in enumerate(sessoes_ativas) if i != t
                  for bloco in s.blocos for ex in [bloco.ex1, bloco.ex2, bloco.ex3] if ex]
    nomes_outros = {ex.nome for ex in exs_outros}
    pais_dos_outros = {ex.variacao_de for ex in exs_outros if ex.variacao_de}
    banco_regen = [e for e in banco if e.nome not in nomes_outros
                   and e.nome not in pais_dos_outros
                   and (e.variacao_de is None or e.variacao_de not in nomes_outros)]
    # Block exercises from reference (same logic as /gerar)
    ref_sessoes = _ref_sessoes()
    if ref_sessoes:
        nomes_ref = set()
        pais_ref = set()
        for s in ref_sessoes:
            for bloco in s.blocos:
                for ex in [bloco.ex1, bloco.ex2, bloco.ex3]:
                    if ex:
                        nomes_ref.add(ex.nome)
                        if ex.variacao_de:
                            pais_ref.add(ex.variacao_de)
        banco_regen = [e for e in banco_regen
                       if e.nome not in nomes_ref
                       and e.nome not in pais_ref
                       and (e.variacao_de is None or e.variacao_de not in nomes_ref)]

    if cfg_r.get("demandas"):
        nova = gerar_sessao_por_demandas(banco_regen, demandas=cfg_r["demandas"],
            equipamentos_bloqueados=cfg_r.get("equipamentos_bloqueados", []),
            max_complexidade=cfg_r.get("max_complexidade", 5),
            tamanho_bloco=cfg_r.get("tamanho_bloco", 2),
            exercicios_travados=cfg_r.get("exercicios_travados", []),
            evitar_agonistas=cfg_r.get("evitar_agonistas", False),
            lateralidade_por_padrao=cfg_r.get("lateralidade_por_padrao"))
    else:
        nova = gerar_sessao(banco_regen, cfg_r["padroes"],
            exercicios_por_padrao=cfg_r["exercicios_por_padrao"],
            equipamentos_bloqueados=cfg_r.get("equipamentos_bloqueados", []),
            max_complexidade=cfg_r.get("max_complexidade", 5),
            tamanho_bloco=cfg_r.get("tamanho_bloco", 2),
            exercicios_travados=cfg_r.get("exercicios_travados", []),
            evitar_agonistas=cfg_r.get("evitar_agonistas", False))

    sessoes_ativas[t] = nova
    salvar_sessoes_disco()
    return render_template("_treino_card.html", sessao=nova, idx=t,
                           modo="visualizar", padroes_labels=PADROES_LABELS, alunos=carregar_alunos(),
                           nomes_ref=_nomes_ref_set())

@app.route("/treino/<int:t>/substituir/<nome_ex>", methods=["POST"])
def treino_substituir(t, nome_ex):
    global sessoes_ativas
    if t >= len(sessoes_ativas): return "", 404
    banco_subst = banco
    ref_sessoes = _ref_sessoes()
    if ref_sessoes:
        nomes_ref = {ex.nome for s in ref_sessoes for b in s.blocos
                     for ex in [b.ex1, b.ex2, b.ex3] if ex}
        banco_sem_ref = [e for e in banco if e.nome not in nomes_ref]
        banco_subst = banco_sem_ref if banco_sem_ref else banco
    sessoes_ativas[t] = substituir_exercicio(sessoes_ativas[t], nome_ex, banco_subst)
    salvar_sessoes_disco()
    return render_template("_treino_card.html", sessao=sessoes_ativas[t], idx=t,
                           modo="editar", padroes_labels=PADROES_LABELS,
                           alunos=carregar_alunos(),
                           todos_padroes=sorted(PADROES_LABELS.keys()),
                           todos_equipamentos=todos_equipamentos,
                           todos_musculos=todos_musculos)

@app.route("/treino/<int:t>/substituir-por/<nome_atual>/<nome_novo>", methods=["POST"])
def treino_substituir_por(t, nome_atual, nome_novo):
    global sessoes_ativas
    if t >= len(sessoes_ativas): return "", 404
    sessoes_ativas[t] = substituir_exercicio_por(sessoes_ativas[t], nome_atual, nome_novo, banco)
    salvar_sessoes_disco()
    return render_template("_treino_card.html", sessao=sessoes_ativas[t], idx=t,
                           modo="editar", padroes_labels=PADROES_LABELS,
                           alunos=carregar_alunos(),
                           todos_padroes=sorted(PADROES_LABELS.keys()),
                           todos_equipamentos=todos_equipamentos,
                           todos_musculos=todos_musculos)

@app.route("/treino/<int:t>/buscar-substitutos/<nome_ex>")
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

    cands = filtrar_banco(texto=texto, padrao=padrao or None, purpose=purpose or None,
                          unilateral=unilateral or None, equipamento=equipamento or None,
                          musculo=musculo or None, max_cx=5)
    cands = [e for e in cands if e.nome not in nomes_em_uso and e.nome != nome_ex]

    ref_sessoes = _ref_sessoes()
    nomes_ref = {ex.nome for s in ref_sessoes for b in s.blocos
                 for ex in [b.ex1, b.ex2, b.ex3] if ex} if ref_sessoes else set()

    return render_template("_substituicao.html", cands=cands[:50], nome_ex=nome_ex, idx=t,
                           padroes_labels=PADROES_LABELS,
                           todos_padroes=sorted(PADROES_LABELS.keys()),
                           todos_equipamentos=todos_equipamentos,
                           todos_musculos=todos_musculos,
                           nomes_ref=nomes_ref)

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
    return render_template("_treino_card.html", sessao=sessoes_ativas[t], idx=t,
                           modo="editar", padroes_labels=PADROES_LABELS,
                           alunos=carregar_alunos(),
                           todos_padroes=sorted(PADROES_LABELS.keys()),
                           todos_equipamentos=todos_equipamentos,
                           todos_musculos=todos_musculos)

@app.route("/treino/<int:t>/bloco/<int:bi>/deletar", methods=["POST"])
def bloco_deletar(t, bi):
    global sessoes_ativas
    if t >= len(sessoes_ativas): return "", 404
    labels = "ABCDEFGHIJKLMNOP"
    sessoes_ativas[t].blocos.pop(bi)
    for j, b in enumerate(sessoes_ativas[t].blocos):
        b.label = labels[j] if j < len(labels) else str(j+1)
    salvar_sessoes_disco()
    return render_template("_treino_card.html", sessao=sessoes_ativas[t], idx=t,
                           modo="editar", padroes_labels=PADROES_LABELS,
                           alunos=carregar_alunos(),
                           todos_padroes=sorted(PADROES_LABELS.keys()),
                           todos_equipamentos=todos_equipamentos,
                           todos_musculos=todos_musculos)

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
    return render_template("_treino_card.html", sessao=sessoes_ativas[t], idx=t,
                           modo="editar", padroes_labels=PADROES_LABELS,
                           alunos=carregar_alunos(),
                           todos_padroes=sorted(PADROES_LABELS.keys()),
                           todos_equipamentos=todos_equipamentos,
                           todos_musculos=todos_musculos)

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
    return render_template("_treino_card.html", sessao=sessoes_ativas[t], idx=t,
                           modo="editar", padroes_labels=PADROES_LABELS,
                           alunos=carregar_alunos(),
                           todos_padroes=sorted(PADROES_LABELS.keys()),
                           todos_equipamentos=todos_equipamentos,
                           todos_musculos=todos_musculos)

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
    return render_template("_treino_card.html", sessao=sessoes_ativas[t], idx=t,
                           modo="editar", padroes_labels=PADROES_LABELS,
                           alunos=carregar_alunos(),
                           todos_padroes=sorted(PADROES_LABELS.keys()),
                           todos_equipamentos=todos_equipamentos,
                           todos_musculos=todos_musculos)

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
    return render_template("_treino_card.html", sessao=sessoes_ativas[t], idx=t,
                           modo="editar", padroes_labels=PADROES_LABELS,
                           alunos=carregar_alunos(),
                           todos_padroes=sorted(PADROES_LABELS.keys()),
                           todos_equipamentos=todos_equipamentos,
                           todos_musculos=todos_musculos)

@app.route("/treino/<int:t>/novo-bloco/<nome_ex>", methods=["POST"])
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
    return render_template("_treino_card.html", sessao=sessoes_ativas[t], idx=t,
                           modo="editar", padroes_labels=PADROES_LABELS,
                           alunos=carregar_alunos(),
                           todos_padroes=sorted(PADROES_LABELS.keys()),
                           todos_equipamentos=todos_equipamentos,
                           todos_musculos=todos_musculos)

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
    return render_template("_treino_card.html", sessao=sessoes_ativas[t], idx=t,
                           modo="editar", padroes_labels=PADROES_LABELS,
                           alunos=carregar_alunos(),
                           todos_padroes=sorted(PADROES_LABELS.keys()),
                           todos_equipamentos=todos_equipamentos,
                           todos_musculos=todos_musculos)

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

    ref_sessoes = _ref_sessoes()
    nomes_ref = {ex.nome for s in ref_sessoes for b in s.blocos
                 for ex in [b.ex1, b.ex2, b.ex3] if ex} if ref_sessoes else set()

    html = f"<p class='meta-count'>{len(cands)} exercício(s)</p>"
    for e in cands:
        na_ref = e.nome in nomes_ref
        badge = ' <span class="ref-badge">REF</span>' if na_ref else ''
        style = ' style="opacity:0.6"' if na_ref else ''
        html += (f'<label class="ex-option"{style}>'
                 f'<input type="radio" name="exercicio_escolhido" value="{e.nome}">'
                 f'<span>{e.nome}{badge}</span>'
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
    return render_template("historico.html", historico=carregar_historico(),
                           padroes_labels=PADROES_LABELS)

@app.route("/aluno-historico")
def aluno_historico():
    nome = request.args.get("nome", "").strip()
    if not nome:
        return ""
    registros = buscar_historico_por_aluno(nome)
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
    salvar_historico_registro(
        reg_id=datetime.now().strftime("%Y%m%d_%H%M%S_") + secrets.token_hex(2),
        data_salvo=datetime.now().strftime("%d/%m/%Y %H:%M"),
        aluno=aluno or "—",
        etiqueta=etiqueta,
        n_treinos=len(sessoes_ativas),
        sessoes=[_sessao_to_dict(s) for s in sessoes_ativas],
        configs=configs_serial,
    )
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
                           padroes_labels=PADROES_LABELS, alunos=carregar_alunos(),
                           tem_referencia=bool(referencias),
                           referencias=referencias)

# ══════════════════════════════════════════════════════════════
# ROTAS — REFERÊNCIA
# ══════════════════════════════════════════════════════════════

def _render_referencia():
    return render_template("_referencia.html",
                           referencias=referencias,
                           padroes_labels=PADROES_LABELS,
                           n_sessoes_ativas=len(sessoes_ativas))

@app.route("/referencia/lista")
def referencia_lista():
    """Retorna lista resumida das referências (para atualizar dropdown de comparação)."""
    return jsonify([{
        "idx": i,
        "aluno": r["origem"]["aluno"],
        "treino_idx": r["origem"].get("treino_idx", 0),
        "data": (r["origem"].get("data", "") or "").split(" ")[0],
    } for i, r in enumerate(referencias)])

@app.route("/referencia/render")
def referencia_render():
    """Retorna HTML do painel de referência (usado pelo auto-ref após gerar)."""
    return _render_referencia()

@app.route("/referencia/fixar/<reg_id>/<int:treino_idx>", methods=["POST"])
def referencia_fixar(reg_id, treino_idx):
    """Fixa UM treino específico de um registro do histórico como referência."""
    reg = carregar_registro(reg_id)
    if not reg:
        return "Registro não encontrado", 404
    if treino_idx >= len(reg["sessoes"]):
        return "Treino não encontrado", 404
    sessao = _dict_to_sessao(reg["sessoes"][treino_idx])
    referencias.append({
        "sessao": sessao,
        "origem": {
            "etiqueta": reg.get("etiqueta", ""),
            "aluno": reg.get("aluno", "—"),
            "data": reg.get("data", "—"),
            "reg_id": reg_id,
            "treino_idx": treino_idx,
        },
        "id_ref": _novo_id_ref(),
    })
    return _render_referencia()

@app.route("/referencia/fixar-ativo/<int:treino_idx>", methods=["POST"])
def referencia_fixar_ativo(treino_idx):
    """Fixa UM treino ativo como referência."""
    if treino_idx >= len(sessoes_ativas):
        return "Treino não encontrado", 404
    referencias.append({
        "sessao": copy.deepcopy(sessoes_ativas[treino_idx]),
        "origem": {
            "etiqueta": "Sessão atual",
            "aluno": "—",
            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "reg_id": None,
            "treino_idx": treino_idx,
        },
        "id_ref": _novo_id_ref(),
    })
    return _render_referencia()

@app.route("/referencia/remover/<id_ref>", methods=["POST"])
def referencia_remover(id_ref):
    """Remove um item específico da lista de referências."""
    global referencias
    referencias = [r for r in referencias if r["id_ref"] != id_ref]
    return _render_referencia()

@app.route("/referencia/limpar", methods=["POST"])
def referencia_limpar():
    """Limpa TODAS as referências."""
    global referencias
    referencias = []
    return ""

@app.route("/referencia/clonar/<id_ref>", methods=["POST"])
def referencia_clonar(id_ref):
    """Clona 1 item da referência para sessoes_ativas (substituindo)."""
    global sessoes_ativas, configs_geradas
    item = next((r for r in referencias if r["id_ref"] == id_ref), None)
    if not item:
        return '<p class="aviso">Referência não encontrada.</p>'
    sessoes_ativas = [copy.deepcopy(item["sessao"])]
    configs_geradas = []
    salvar_sessoes_disco()
    return render_template("_resultado.html", sessoes=sessoes_ativas,
                           padroes_labels=PADROES_LABELS, alunos=carregar_alunos(),
                           tem_referencia=bool(referencias), referencias=referencias)

@app.route("/referencia/copiar-bloco/<int:ref_t>/<int:ref_bi>/para/<int:dest_t>", methods=["POST"])
def referencia_copiar_bloco(ref_t, ref_bi, dest_t):
    global sessoes_ativas
    if ref_t >= len(referencias) or dest_t >= len(sessoes_ativas):
        return "", 404
    bloco_ref = referencias[ref_t]["sessao"].blocos[ref_bi]
    bloco_novo = copy.deepcopy(bloco_ref)
    labels = "ABCDEFGHIJKLMNOP"
    n = len(sessoes_ativas[dest_t].blocos)
    bloco_novo.label = labels[n] if n < len(labels) else str(n + 1)
    sessoes_ativas[dest_t].blocos.append(bloco_novo)
    salvar_sessoes_disco()
    return render_template("_treino_card.html", sessao=sessoes_ativas[dest_t], idx=dest_t,
                           modo="editar", padroes_labels=PADROES_LABELS,
                           alunos=carregar_alunos(),
                           todos_padroes=sorted(PADROES_LABELS.keys()),
                           todos_equipamentos=todos_equipamentos,
                           todos_musculos=todos_musculos)

@app.route("/comparar/<int:ref_t>/<int:ativo_t>")
def comparar_treinos(ref_t, ativo_t):
    if ref_t >= len(referencias) or ativo_t >= len(sessoes_ativas):
        return "", 404
    ref = referencias[ref_t]["sessao"]
    ativo = sessoes_ativas[ativo_t]
    nomes_ref = {ex.nome for b in ref.blocos for ex in [b.ex1, b.ex2, b.ex3] if ex}
    nomes_ativo = {ex.nome for b in ativo.blocos for ex in [b.ex1, b.ex2, b.ex3] if ex}
    mantidos = nomes_ref & nomes_ativo
    removidos = nomes_ref - nomes_ativo
    adicionados = nomes_ativo - nomes_ref
    return render_template("_comparacao.html",
                           ref=ref, ativo=ativo,
                           ref_idx=ref_t, ativo_idx=ativo_t,
                           ref_origem=referencias[ref_t]["origem"],
                           mantidos=mantidos, removidos=removidos, adicionados=adicionados,
                           padroes_labels=PADROES_LABELS)

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
    return render_template("historico.html", historico=carregar_historico(), padroes_labels=PADROES_LABELS)

# ══════════════════════════════════════════════════════════════
# ROTAS — ALUNOS
# ══════════════════════════════════════════════════════════════

@app.route("/alunos")
def alunos_page():
    return render_template("alunos.html", alunos=carregar_alunos())

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
    )
    return render_template("alunos.html", alunos=carregar_alunos())

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
    )
    return render_template("alunos.html", alunos=carregar_alunos())

@app.route("/alunos/<int:i>/deletar", methods=["DELETE"])
def aluno_deletar(i):
    deletar_aluno(i)
    return render_template("alunos.html", alunos=carregar_alunos())

# ══════════════════════════════════════════════════════════════

init_db()
migrar_json_para_sqlite()
sessoes_ativas = carregar_sessoes_disco()

if __name__ == "__main__":
    if sessoes_ativas:
        print(f"  Restauradas {len(sessoes_ativas)} sessoes ativas")
    print(f"[OK] Banco carregado: {len(banco)} exercicios")
    print(f"[OK] Acesse: http://localhost:5001 (ou do celular: use o IP da maquina na rede)")
    app.run(debug=True, host="0.0.0.0", port=5001)
