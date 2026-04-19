import streamlit as st
import random
import json
import io
import zipfile
import unicodedata
from pathlib import Path
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

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="BF Treinamento — Gerador",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Estilos globais
# ---------------------------------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

/* Layout */
.block-container { padding-top: 2rem !important; padding-bottom: 4rem !important; max-width: 960px !important; }

/* Esconde sidebar */
button[data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }

/* Header */
.app-header {
    display: flex; align-items: center; gap: 16px;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 20px; margin-bottom: 28px;
}
.app-header h1 { font-size: 22px; font-weight: 700; color: #111827; margin: 0; letter-spacing: -0.02em; }
.app-header p  { font-size: 13px; color: #9ca3af; margin: 2px 0 0 0; }

/* Config panel */
.config-panel { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 14px; padding: 20px 24px; margin-bottom: 20px; }
.config-title  { font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: 0.1em; margin: 0 0 14px 0; }

/* Slim view */
.ex-slim { padding: 6px 0 6px 12px; border-left: 3px solid #e85d04; margin-bottom: 5px; }
.ex-slim-nome { font-size: 14px; font-weight: 600; color: #111827; }
.ex-slim-meta { font-size: 11px; color: #9ca3af; margin-top: 1px; }
.prescr-badge { display: inline-block; background: #fff3e6; color: #e85d04; border-radius: 6px; padding: 1px 7px; font-size: 11px; font-weight: 700; margin-left: 6px; }
.bloco-lbl { font-size: 10px; font-weight: 700; color: #9ca3af; letter-spacing: 0.1em; text-transform: uppercase; margin: 10px 0 4px 0; }
.thin-hr { border: none; border-top: 1px solid #f3f4f6; margin: 6px 0; }

/* Sub panel */
.sub-panel { background: #fffbf5; border: 1px solid #fed7aa; border-radius: 10px; padding: 14px 18px; margin-top: 8px; }

/* Checkboxes compactos */
.stCheckbox { margin-bottom: 0px !important; padding: 0px !important; min-height: 0 !important; }
.stCheckbox label { font-size: 12px !important; padding: 1px 0 !important; }
.stCheckbox label p { font-size: 12px !important; margin: 0 !important; line-height: 1.4 !important; }

/* Toggles compactos (usados nos refinamentos de hierarquia) */
.stToggle { margin-bottom: 0 !important; padding: 0 !important; min-height: 0 !important; }
.stToggle > label { display: none !important; }
.stToggle > div { margin-top: 2px !important; }

/* Sliders compactos */
.stSlider { margin-bottom: 2px !important; padding-bottom: 0 !important; }
.stSlider label, .stSlider label p { font-size: 11px !important; margin-bottom: 0px !important; color: #6b7280 !important; }

/* Botão primário laranja */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #e85d04 !important; color: white !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 600 !important; font-size: 15px !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover { background: #c44d03 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------

@st.cache_data
def get_banco():
    return carregar_banco("banco_exercicios.xlsx")

def carregar_alunos():
    path = Path("alunos.json")
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def salvar_alunos(lista):
    with open(Path("alunos.json"), "w", encoding="utf-8") as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------------------------
# Persistência de sessões geradas
# ---------------------------------------------------------------------------

SESSOES_PATH  = Path("sessoes_salvas.json")
HISTORICO_PATH = Path("historico_treinos.json")

def _exercicio_to_dict(ex: Exercicio) -> dict:
    return {
        "nome": ex.nome, "variacao_de": ex.variacao_de,
        "eq_primario": ex.eq_primario, "eq_secundario": ex.eq_secundario,
        "regiao": ex.regiao, "padrao": ex.padrao, "purpose": ex.purpose,
        "unilateral": ex.unilateral, "complexidade": ex.complexidade,
        "fadiga": ex.fadiga, "circuito": ex.circuito,
        "similaridade": ex.similaridade, "musculo_primario": ex.musculo_primario,
        "obs": ex.obs, "series": ex.series, "reps": ex.reps, "rir": ex.rir,
    }

def _dict_to_exercicio(d: dict) -> Exercicio:
    return Exercicio(
        nome=d["nome"], variacao_de=d.get("variacao_de"),
        eq_primario=d.get("eq_primario", ""), eq_secundario=d.get("eq_secundario"),
        regiao=d.get("regiao", ""), padrao=d.get("padrao", ""),
        purpose=d.get("purpose", ""), unilateral=d.get("unilateral", ""),
        complexidade=d.get("complexidade", 1), fadiga=d.get("fadiga", 1),
        circuito=d.get("circuito", "não"), similaridade=d.get("similaridade", ""),
        musculo_primario=d.get("musculo_primario", ""), obs=d.get("obs"),
        series=d.get("series"), reps=d.get("reps"), rir=d.get("rir"),
    )

def _sessao_to_dict(s: Sessao) -> dict:
    blocos = []
    for b in s.blocos:
        blocos.append({
            "label": b.label,
            "ex1": _exercicio_to_dict(b.ex1) if b.ex1 else None,
            "ex2": _exercicio_to_dict(b.ex2) if b.ex2 else None,
            "ex3": _exercicio_to_dict(b.ex3) if b.ex3 else None,
        })
    return {"tipo": s.tipo, "blocos": blocos}

def _dict_to_sessao(d: dict) -> Sessao:
    blocos = []
    for b in d["blocos"]:
        blocos.append(SuperSerie(
            label=b["label"],
            ex1=_dict_to_exercicio(b["ex1"]) if b.get("ex1") else None,
            ex2=_dict_to_exercicio(b["ex2"]) if b.get("ex2") else None,
            ex3=_dict_to_exercicio(b["ex3"]) if b.get("ex3") else None,
        ))
    return Sessao(tipo=d["tipo"], blocos=blocos)

def salvar_sessoes(sessoes: list):
    """Persiste as sessões atuais em disco (snapshot de continuidade)."""
    try:
        data = [_sessao_to_dict(s) for s in sessoes]
        with open(SESSOES_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def carregar_sessoes_salvas() -> list:
    """Restaura sessões do snapshot. Retorna [] se não existir ou falhar."""
    if not SESSOES_PATH.exists():
        return []
    try:
        with open(SESSOES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return [_dict_to_sessao(d) for d in data]
    except Exception:
        return []

# ---------------------------------------------------------------------------
# Histórico de treinos
# ---------------------------------------------------------------------------

def carregar_historico() -> list:
    """Retorna lista de registros do histórico. Cada registro é um dict com
    id, data, aluno, etiqueta, e lista de sessões serializadas."""
    if not HISTORICO_PATH.exists():
        return []
    try:
        with open(HISTORICO_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def salvar_historico(historico: list):
    try:
        with open(HISTORICO_PATH, "w", encoding="utf-8") as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def adicionar_ao_historico(sessoes: list, aluno: str, etiqueta: str):
    """Adiciona o conjunto de sessões ao histórico com metadados."""
    from datetime import datetime
    historico = carregar_historico()
    registro = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "aluno": aluno or "—",
        "etiqueta": etiqueta.strip() or f"{len(sessoes)} treino(s)",
        "n_treinos": len(sessoes),
        "sessoes": [_sessao_to_dict(s) for s in sessoes],
    }
    historico.insert(0, registro)   # mais recente primeiro
    salvar_historico(historico)

banco = get_banco()
alunos = carregar_alunos()
nomes_alunos = ["Selecionar aluno..."] + [a["nome"] for a in alunos]
todos_padroes = sorted({e.padrao for e in banco if e.padrao})

# Listas únicas para filtros
todos_equipamentos = sorted({e.eq_primario for e in banco if e.eq_primario and e.eq_primario != "Sem equipamento"})
todos_musculos: list[str] = []
_m_set: set[str] = set()
for _e in banco:
    if _e.musculo_primario:
        for _m in _e.musculo_primario.split(","):
            _ms = _m.strip().lower()
            if _ms and _ms not in _m_set:
                _m_set.add(_ms)
                todos_musculos.append(_ms)
todos_musculos = sorted(todos_musculos)

PADROES_LABELS = {
    # Membros inferiores
    "squat":           "Agachamento",
    "hinge":           "Extensão de quadril",
    "knee_flexion":    "Flexão de joelho",
    "abduction":       "Abdução",
    "adduction":       "Adução",
    "flexao_plantar":  "Flexão plantar",
    # Membros superiores
    "empurrar_compostos": "Empurrar compostos",
    "empurrar_isolados":  "Empurrar isolados",
    "remadas":            "Remadas",
    "puxadas":            "Puxadas",
    "ombro_composto":      "Desenvolvimento",
    "ombro_isolado":       "Elevações",
    "posterior_ombro":     "Posterior de ombro",
    "biceps":             "Bíceps",
    "triceps":            "Tríceps",
    # Outros
    "core_isometrico": "Core isométrico",
    "core_dinamico":   "Core dinâmico",
    "cardio":          "Cardio",
}

# Hierarquia para UI expansível
REGIOES_LABELS = {
    "upper":  "Membros superiores",
    "lower":  "Membros inferiores",
    "core":   "Core",
    "cardio": "Cardio",
}

SUBREGIOES_LABELS = {
    "peito":           "Peito",
    "costas":          "Costas",
    "ombro":           "Ombro",
    "bracos":          "Braços",
    "perna_anterior":  "Perna anterior",
    "perna_posterior": "Perna posterior",
    "adutores":        "Adutores",
    "panturrilha":     "Panturrilha",
    "core":            "Core",
    "cardio":          "Cardio",
}

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "sessoes"        not in st.session_state: st.session_state.sessoes        = []
if "configs_geradas" not in st.session_state: st.session_state.configs_geradas = []
if "sub_alvo"       not in st.session_state: st.session_state.sub_alvo       = []
if "candidatos"     not in st.session_state: st.session_state.candidatos     = []
if "modo_viz"       not in st.session_state: st.session_state.modo_viz       = []
if "config_aberta"  not in st.session_state: st.session_state.config_aberta  = True
if "edit_aluno_idx" not in st.session_state: st.session_state.edit_aluno_idx = None
if "add_ex_alvo"    not in st.session_state: st.session_state.add_ex_alvo    = {}
if "add_ex_cands"   not in st.session_state: st.session_state.add_ex_cands   = {}
if "novo_bloco_cands" not in st.session_state: st.session_state.novo_bloco_cands = {}
# mover exercício entre blocos: chave = (t, i, idx), valor = True se painel aberto
if "mover_ex_alvo"  not in st.session_state: st.session_state.mover_ex_alvo  = {}

# Restaura treino APENAS em caso de reconexão/timeout (não em abertura nova)
# A flag "ja_iniciou" distingue: se existe = mesma sessão do browser; se não = abertura nova
if "ja_iniciou" not in st.session_state:
    # Abertura nova — não restaura nada, mostra tela inicial limpa
    st.session_state.ja_iniciou = True
elif not st.session_state.sessoes:
    # Reconexão após timeout na mesma sessão — restaura o último estado
    sessoes_restauradas = carregar_sessoes_salvas()
    if sessoes_restauradas:
        n = len(sessoes_restauradas)
        st.session_state.sessoes    = sessoes_restauradas
        st.session_state.sub_alvo   = [None] * n
        st.session_state.candidatos = [[] for _ in range(n)]
        st.session_state.modo_viz   = ["visualizar"] * n

def _salvar_e_rerun():
    """Persiste o estado atual das sessões e reinicia o script."""
    salvar_sessoes(st.session_state.sessoes)
    st.rerun()

# ---------------------------------------------------------------------------
# Helpers visuais
# ---------------------------------------------------------------------------

def prescr_badge(ex):
    parts = []
    if ex.series: parts.append(f"{ex.series}×")
    if ex.reps:   parts.append(ex.reps)
    if ex.rir is not None: parts.append(f"RIR {ex.rir}")
    if not parts: return ""
    return f"<span class='prescr-badge'>{' · '.join(parts)}</span>"


def gerar_zip(sessoes: list, nome_aluno: str, logo_bytes) -> bytes:
    """Gera ZIP com um PNG por treino."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for t, sessao in enumerate(sessoes):
            png = gerar_png(sessao, nome_aluno, logo_bytes=logo_bytes)
            fname = f"treino{t+1}_{nome_aluno.lower().replace(' ', '_')}.png"
            zf.writestr(fname, png)
    buf.seek(0)
    return buf.getvalue()


def _normalizar(texto: str) -> str:
    """Remove acentos e converte para minúsculas para busca fuzzy."""
    return unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode().lower()


def filtrar_banco(
    texto: str = "",
    padrao: str = None,
    purpose: str = None,
    unilateral: str = None,
    equipamento: str = None,
    musculo: str = None,
    max_cx: int = 5,
) -> list:
    """Filtra o banco — busca por nome é case-insensitive e ignora acentos.
    Passar None ou '(qualquer)' em qualquer filtro = sem filtro."""
    resultado = list(banco)
    if padrao and padrao != "(qualquer)":
        resultado = [e for e in resultado if e.padrao == padrao]
    if purpose and purpose != "(qualquer)":
        resultado = [e for e in resultado if e.purpose == purpose]
    if unilateral and unilateral != "(qualquer)":
        resultado = [e for e in resultado if e.unilateral == unilateral]
    if equipamento and equipamento != "(qualquer)":
        resultado = [e for e in resultado if e.eq_primario == equipamento or e.eq_secundario == equipamento]
    if musculo and musculo != "(qualquer)":
        m_norm = _normalizar(musculo)
        resultado = [e for e in resultado
                     if e.musculo_primario and m_norm in _normalizar(e.musculo_primario)]
    resultado = [e for e in resultado if e.complexidade <= max_cx]
    if texto.strip():
        txt_norm = _normalizar(texto.strip())
        resultado = [e for e in resultado if txt_norm in _normalizar(e.nome)]
    resultado.sort(key=lambda e: (e.purpose != "compound", e.nome))
    return resultado


def render_slim(sessao: Sessao):
    for bloco in sessao.blocos:
        exs = [e for e in [bloco.ex1, bloco.ex2, bloco.ex3] if e]
        st.markdown(f"<p class='bloco-lbl'>Bloco {bloco.label}</p>", unsafe_allow_html=True)
        for idx, ex in enumerate(exs, 1):
            eq = ex.eq_primario + (f" + {ex.eq_secundario}" if ex.eq_secundario else "")
            st.markdown(
                f"<div class='ex-slim'>"
                f"<div class='ex-slim-nome'>{bloco.label}{idx}&nbsp; {ex.nome}{prescr_badge(ex)}</div>"
                f"<div class='ex-slim-meta'>{ex.purpose} · 🔧 {eq}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.markdown("<hr class='thin-hr'>", unsafe_allow_html=True)


def render_editar(sessao: Sessao, t: int, max_cx: int):
    labels = "ABCDEFGHIJKLMNOP"
    n_blocos = len(sessao.blocos)

    for i, bloco in enumerate(sessao.blocos):
        exs = [e for e in [bloco.ex1, bloco.ex2, bloco.ex3] if e]
        n_exs = len(exs)

        # Cabeçalho do bloco: label + setas + lixeira
        col_lbl, col_up, col_dn, col_del_bloco = st.columns([12, 1, 1, 1])
        with col_lbl:
            st.markdown(f"<p class='bloco-lbl'>Bloco {bloco.label}</p>", unsafe_allow_html=True)
        with col_up:
            if i > 0 and st.button("↑", key=f"up_{t}_{i}"):
                bl = sessao.blocos[:]
                bl[i], bl[i-1] = bl[i-1], bl[i]
                for j, b in enumerate(bl): b.label = labels[j]
                st.session_state.sessoes[t].blocos = bl
                _salvar_e_rerun()
        with col_dn:
            if i < n_blocos - 1 and st.button("↓", key=f"dn_{t}_{i}"):
                bl = sessao.blocos[:]
                bl[i], bl[i+1] = bl[i+1], bl[i]
                for j, b in enumerate(bl): b.label = labels[j]
                st.session_state.sessoes[t].blocos = bl
                _salvar_e_rerun()
        with col_del_bloco:
            if st.button("🗑", key=f"del_bloco_{t}_{i}", help="Remover bloco"):
                bl = sessao.blocos[:]
                bl.pop(i)
                for j, b in enumerate(bl): b.label = labels[j]
                st.session_state.sessoes[t].blocos = bl
                st.session_state.add_ex_alvo.pop((t, i), None)
                st.session_state.add_ex_cands.pop((t, i), None)
                _salvar_e_rerun()

        # Exercícios do bloco
        for idx, ex in enumerate(exs, 1):
            eq  = ex.eq_primario + (f" + {ex.eq_secundario}" if ex.eq_secundario else "")
            obs = f" · {ex.obs}" if ex.obs else ""
            pk  = f"p_{t}_{bloco.label}_{idx}"
            sub_key = f"{t}_{i}_{idx}"

            col_ex, col_sub, col_mv, col_rm = st.columns([13, 1, 1, 1])
            with col_ex:
                st.markdown(
                    f"<p style='margin:0;font-size:13px;line-height:1.6'>"
                    f"<b>{bloco.label}{idx}</b>&nbsp;{ex.nome}{prescr_badge(ex)} "
                    f"<span style='color:#9ca3af;font-size:11px'>{ex.purpose} · 🔧 {eq}{obs}</span></p>",
                    unsafe_allow_html=True,
                )
            with col_sub:
                sub_aberto = st.session_state.sub_alvo[t] == sub_key
                if st.button("✕" if sub_aberto else "↺",
                             key=f"sub_btn_{t}_{i}_{idx}",
                             help="Fechar" if sub_aberto else "Substituir"):
                    if sub_aberto:
                        st.session_state.sub_alvo[t] = None
                        st.session_state.candidatos[t] = []
                    else:
                        st.session_state.sub_alvo[t] = sub_key
                        st.session_state.candidatos[t] = []
                        st.session_state.add_ex_alvo.pop((t, i), None)
                        st.session_state.mover_ex_alvo.pop((t, i, idx), None)
                    st.rerun()
            with col_mv:
                mv_aberto = st.session_state.mover_ex_alvo.get((t, i, idx), False)
                if st.button("✕" if mv_aberto else "↗",
                             key=f"mv_btn_{t}_{i}_{idx}",
                             help="Fechar" if mv_aberto else "Mover para outro bloco"):
                    if mv_aberto:
                        st.session_state.mover_ex_alvo.pop((t, i, idx), None)
                    else:
                        st.session_state.mover_ex_alvo[(t, i, idx)] = True
                        st.session_state.sub_alvo[t] = None
                        st.session_state.add_ex_alvo.pop((t, i), None)
                    st.rerun()
            with col_rm:
                if st.button("✕", key=f"rm_ex_{t}_{i}_{idx}", help="Remover exercício"):
                    target = st.session_state.sessoes[t].blocos[i]
                    ri = idx - 1
                    if ri == 0:
                        target.ex1 = target.ex2
                        target.ex2 = target.ex3
                        target.ex3 = None
                    elif ri == 1:
                        target.ex2 = target.ex3
                        target.ex3 = None
                    else:
                        target.ex3 = None
                    if not any([target.ex1, target.ex2, target.ex3]):
                        bl = st.session_state.sessoes[t].blocos[:]
                        bl.pop(i)
                        for j, b in enumerate(bl): b.label = labels[j]
                        st.session_state.sessoes[t].blocos = bl
                    _salvar_e_rerun()

            # Prescrição em linha
            pc0, pc1, pc2, pc3, pc4 = st.columns([3, 2, 3, 2, 2])
            with pc0:
                st.markdown(
                    "<p style='font-size:10px;color:#9ca3af;margin:4px 0 2px 0;"
                    "text-transform:uppercase;letter-spacing:0.08em'>Prescrição</p>",
                    unsafe_allow_html=True,
                )
            with pc1:
                new_s = st.number_input("Séries", 1, 10, ex.series or 3, key=f"s_{pk}", label_visibility="collapsed")
            with pc2:
                new_r = st.text_input("Reps", ex.reps or "8-12", key=f"r_{pk}", placeholder="reps", label_visibility="collapsed")
            with pc3:
                new_rir = st.number_input("RIR", 0, 4, ex.rir if ex.rir is not None else 2, key=f"rir_{pk}", label_visibility="collapsed")
            with pc4:
                if st.button("💾", key=f"save_{pk}", help="Salvar prescrição"):
                    target = st.session_state.sessoes[t].blocos[i]
                    slot = [target.ex1, target.ex2, target.ex3]
                    ri = idx - 1
                    if slot[ri] is not None:
                        slot[ri].series = int(new_s)
                        slot[ri].reps   = new_r.strip() or None
                        slot[ri].rir    = int(new_rir)
                        if ri == 0: target.ex1 = slot[0]
                        elif ri == 1: target.ex2 = slot[1]
                        else: target.ex3 = slot[2]
                    _salvar_e_rerun()

            # Painel substituição INLINE — logo abaixo do exercício
            if st.session_state.sub_alvo[t] == sub_key:
                _render_painel_substituicao_inline(t, i, idx, ex, sessao, max_cx)

            # Painel mover — logo abaixo do exercício
            if st.session_state.mover_ex_alvo.get((t, i, idx), False):
                _render_painel_mover(t, i, idx, ex, sessao)

        # Botão "+ Exercício"
        if n_exs < 3:
            add_key = (t, i)
            painel_aberto = st.session_state.add_ex_alvo.get(add_key, False)
            lbl_add = "✕ Fechar" if painel_aberto else "＋ Exercício"
            if st.button(lbl_add, key=f"toggle_add_{t}_{i}"):
                if painel_aberto:
                    st.session_state.add_ex_alvo.pop(add_key, None)
                    st.session_state.add_ex_cands.pop(add_key, None)
                else:
                    st.session_state.add_ex_alvo[add_key] = True
                    st.session_state.add_ex_cands[add_key] = []
                    st.session_state.sub_alvo[t] = None
                _salvar_e_rerun()

            if painel_aberto:
                _render_painel_adicionar(t, i, bloco, max_cx)

        st.markdown("<hr class='thin-hr'>", unsafe_allow_html=True)

    # Botão "+ Novo bloco"
    novo_aberto = st.session_state.novo_bloco_cands.get(t) is not None
    lbl_novo = "✕ Fechar" if novo_aberto else "＋ Novo bloco"
    if st.button(lbl_novo, key=f"toggle_novo_bloco_{t}"):
        if novo_aberto:
            st.session_state.novo_bloco_cands.pop(t, None)
        else:
            st.session_state.novo_bloco_cands[t] = []
            st.session_state.sub_alvo[t] = None
        _salvar_e_rerun()

    if novo_aberto:
        _render_painel_novo_bloco(t, sessao, max_cx)


def _render_painel_substituicao_inline(t: int, i: int, idx: int, ex, sessao: Sessao, max_cx: int):
    """Painel de substituição inline — logo abaixo do exercício, com busca por nome."""
    sub_key = f"{t}_{i}_{idx}"
    st.markdown(
        f"<div class='sub-panel'>"
        f"<p style='font-size:12px;font-weight:700;color:#92400e;margin:0 0 8px 0'>"
        f"↺ Substituir: {ex.nome}</p></div>",
        unsafe_allow_html=True,
    )

    # Filtros — busca por nome + dropdowns
    fs0, fs1, fs2, fs3 = st.columns([3, 2, 2, 2])
    with fs0:
        txt = st.text_input("Buscar por nome", key=f"sub_txt_{sub_key}",
                            placeholder="ex: bul → Búlgaro...")
    with fs1:
        f_pad = st.selectbox("Categoria", ["(qualquer)"] + sorted(PADROES_LABELS.keys()),
            key=f"f_pad_{sub_key}",
            format_func=lambda x: PADROES_LABELS.get(x, x) if x != "(qualquer)" else "Qualquer")
    with fs2:
        f_pur = st.selectbox("Purpose",
            ["(qualquer)", "compound", "isolation", "stability", "explosive"],
            key=f"f_pur_{sub_key}")
    with fs3:
        f_uni = st.selectbox("Lateralidade",
            ["(qualquer)", "bilateral", "unilateral"],
            key=f"f_uni_{sub_key}")

    f_ign = st.checkbox("Ignorar similaridade já usada", value=True, key=f"f_ign_{sub_key}")

    # Linha 2: equipamento e músculo
    fs4, fs5 = st.columns(2)
    with fs4:
        f_eq = st.selectbox("Equipamento", ["(qualquer)"] + todos_equipamentos,
            key=f"f_eq_{sub_key}")
    with fs5:
        f_musc = st.selectbox("Músculo", ["(qualquer)"] + todos_musculos,
            key=f"f_musc_{sub_key}")

    # Nomes e similaridades em uso na sessão (excluindo o exercício alvo)
    nomes_em_uso = {
        e.nome for bloco in sessao.blocos
        for e in [bloco.ex1, bloco.ex2, bloco.ex3] if e and e.nome != ex.nome
    }
    sims_em_uso = {
        e.similaridade for bloco in sessao.blocos
        for e in [bloco.ex1, bloco.ex2, bloco.ex3] if e and e.nome != ex.nome
    }

    cands = filtrar_banco(
        texto=txt,
        padrao=None if f_pad == "(qualquer)" else f_pad,
        purpose=None if f_pur == "(qualquer)" else f_pur,
        unilateral=None if f_uni == "(qualquer)" else f_uni,
        equipamento=None if f_eq == "(qualquer)" else f_eq,
        musculo=None if f_musc == "(qualquer)" else f_musc,
        max_cx=max_cx,
    )
    cands = [e for e in cands if e.nome not in nomes_em_uso and e.nome != ex.nome]
    if not f_ign:
        cands = [e for e in cands if e.similaridade not in sims_em_uso]

    cb1, cb2 = st.columns(2)
    with cb1:
        if st.button("🎲 Aleatório", key=f"sub_alea_{sub_key}", use_container_width=True,
                     help="Substitui por exercício do mesmo padrão, aleatório"):
            st.session_state.sessoes[t] = substituir_exercicio(
                sessao, ex.nome, banco, max_complexidade=max_cx)
            st.session_state.sub_alvo[t] = None
            st.session_state.candidatos[t] = []
            _salvar_e_rerun()
    with cb2:
        st.caption(f"{len(cands)} exercício(s)")

    if cands:
        nomes_c = [f"{e.nome}  [{e.purpose} · {e.eq_primario}]" for e in cands[:60]]
        escolha = st.radio("Escolha o substituto", nomes_c,
                           key=f"sub_radio_{sub_key}", label_visibility="collapsed")
        escolha_nome = escolha.split("  [")[0]
        if st.button("✅ Aplicar", type="primary", key=f"sub_aplicar_{sub_key}"):
            st.session_state.sessoes[t] = substituir_exercicio_por(sessao, ex.nome, escolha_nome, banco)
            st.session_state.sub_alvo[t] = None
            st.session_state.candidatos[t] = []
            _salvar_e_rerun()
    elif txt or f_pad != "(qualquer)" or f_pur != "(qualquer)" or f_uni != "(qualquer)" \
            or f_eq != "(qualquer)" or f_musc != "(qualquer)":
        st.caption("Nenhum exercício encontrado com esses filtros.")


def _render_painel_mover(t: int, i: int, idx: int, ex, sessao: Sessao):
    """Painel para mover um exercício para outro bloco."""
    blocos_destino = [
        b for j, b in enumerate(sessao.blocos)
        if j != i and len([e for e in [b.ex1, b.ex2, b.ex3] if e]) < 3
    ]

    st.markdown(
        f"<div style='background:#f5f3ff;border:1px solid #c4b5fd;border-radius:10px;"
        f"padding:10px 14px;margin:4px 0 6px 0'>"
        f"<p style='font-size:12px;font-weight:700;color:#5b21b6;margin:0 0 6px 0'>"
        f"↗ Mover: {ex.nome}</p></div>",
        unsafe_allow_html=True,
    )

    if not blocos_destino:
        st.caption("Todos os outros blocos já têm 3 exercícios.")
        return

    labels_destino = [b.label for b in blocos_destino]
    col_sel, col_ok = st.columns([3, 1])
    with col_sel:
        destino_label = st.selectbox(
            "Mover para bloco", labels_destino,
            key=f"mv_dest_{t}_{i}_{idx}",
            format_func=lambda x: f"Bloco {x}",
            label_visibility="collapsed",
        )
    with col_ok:
        if st.button("✅ Mover", key=f"mv_ok_{t}_{i}_{idx}", type="primary", use_container_width=True):
            # Remove do bloco origem
            target_orig = st.session_state.sessoes[t].blocos[i]
            ri = idx - 1
            if ri == 0:
                target_orig.ex1 = target_orig.ex2
                target_orig.ex2 = target_orig.ex3
                target_orig.ex3 = None
            elif ri == 1:
                target_orig.ex2 = target_orig.ex3
                target_orig.ex3 = None
            else:
                target_orig.ex3 = None

            # Remove bloco se ficou vazio
            labels = "ABCDEFGHIJKLMNOP"
            if not any([target_orig.ex1, target_orig.ex2, target_orig.ex3]):
                bl = st.session_state.sessoes[t].blocos[:]
                bl.pop(i)
                for j, b in enumerate(bl): b.label = labels[j]
                st.session_state.sessoes[t].blocos = bl

            # Insere no bloco destino
            for bloco_d in st.session_state.sessoes[t].blocos:
                if bloco_d.label == destino_label:
                    if bloco_d.ex1 is None: bloco_d.ex1 = ex
                    elif bloco_d.ex2 is None: bloco_d.ex2 = ex
                    elif bloco_d.ex3 is None: bloco_d.ex3 = ex
                    break

            st.session_state.mover_ex_alvo.pop((t, i, idx), None)
            _salvar_e_rerun()


def _render_painel_adicionar(t: int, i: int, bloco: SuperSerie, max_cx: int):
    """Painel para adicionar um exercício a um bloco existente."""
    add_key = (t, i)
    exs_no_bloco = [e for e in [bloco.ex1, bloco.ex2, bloco.ex3] if e]
    nomes_em_uso = {e.nome for e in exs_no_bloco}

    st.markdown(
        f"<div style='background:#f0fdf4;border:1px solid #86efac;border-radius:10px;"
        f"padding:12px 16px;margin:6px 0 8px 0'>"
        f"<p style='font-size:12px;font-weight:700;color:#166534;margin:0 0 8px 0'>"
        f"＋ Adicionar exercício ao Bloco {bloco.label}</p></div>",
        unsafe_allow_html=True,
    )

    fa1, fa2, fa3, fa4 = st.columns([3, 2, 2, 2])
    with fa1:
        txt = st.text_input("Buscar por nome", key=f"add_txt_{t}_{i}", placeholder="Digite para filtrar...")
    with fa2:
        pad = st.selectbox("Categoria", ["(qualquer)"] + sorted(PADROES_LABELS.keys()),
            key=f"add_pad_{t}_{i}",
            format_func=lambda x: PADROES_LABELS.get(x, x) if x != "(qualquer)" else "Qualquer")
    with fa3:
        pur = st.selectbox("Purpose", ["(qualquer)", "compound", "isolation", "stability", "explosive"],
            key=f"add_pur_{t}_{i}")
    with fa4:
        uni = st.selectbox("Lateralidade", ["(qualquer)", "bilateral", "unilateral"],
            key=f"add_uni_{t}_{i}")

    fa5, fa6 = st.columns(2)
    with fa5:
        eq_f = st.selectbox("Equipamento", ["(qualquer)"] + todos_equipamentos, key=f"add_eq_{t}_{i}")
    with fa6:
        musc_f = st.selectbox("Músculo", ["(qualquer)"] + todos_musculos, key=f"add_musc_{t}_{i}")

    cands = filtrar_banco(texto=txt, padrao=pad, purpose=pur, unilateral=uni,
                          equipamento=None if eq_f == "(qualquer)" else eq_f,
                          musculo=None if musc_f == "(qualquer)" else musc_f,
                          max_cx=max_cx)
    cands = [e for e in cands if e.nome not in nomes_em_uso]

    ab1, ab2 = st.columns(2)
    with ab1:
        if st.button("🎲 Aleatório", key=f"add_alea_{t}_{i}", use_container_width=True):
            if cands:
                _aplicar_adicionar(t, i, random.choice(cands))
            _salvar_e_rerun()
    with ab2:
        st.caption(f"{len(cands)} exercício(s)")

    if cands:
        nomes_c = [f"{e.nome}  [{e.purpose} · {e.eq_primario}]" for e in cands[:50]]
        escolha = st.radio("Escolha o exercício", nomes_c, key=f"add_radio_{t}_{i}", label_visibility="collapsed")
        escolha_nome = escolha.split("  [")[0]
        if st.button("✅ Adicionar", type="primary", key=f"add_aplicar_{t}_{i}"):
            novo_ex = next((e for e in cands if e.nome == escolha_nome), None)
            if novo_ex:
                _aplicar_adicionar(t, i, novo_ex)
            _salvar_e_rerun()
    elif txt or pad != "(qualquer)" or pur != "(qualquer)" or uni != "(qualquer)" \
            or eq_f != "(qualquer)" or musc_f != "(qualquer)":
        st.caption("Nenhum exercício encontrado com esses filtros.")


def _aplicar_adicionar(t: int, i: int, novo_ex):
    """Insere novo_ex no próximo slot vazio do bloco i do treino t."""
    target = st.session_state.sessoes[t].blocos[i]
    if target.ex1 is None:
        target.ex1 = novo_ex
    elif target.ex2 is None:
        target.ex2 = novo_ex
    elif target.ex3 is None:
        target.ex3 = novo_ex
    # Fecha o painel
    st.session_state.add_ex_alvo.pop((t, i), None)
    st.session_state.add_ex_cands.pop((t, i), None)


def _render_painel_novo_bloco(t: int, sessao: Sessao, max_cx: int):
    """Painel para criar um novo bloco do zero."""
    nomes_em_uso = {
        ex.nome for bloco in sessao.blocos
        for ex in [bloco.ex1, bloco.ex2, bloco.ex3] if ex
    }

    st.markdown(
        "<div style='background:#f0f9ff;border:1px solid #7dd3fc;border-radius:10px;"
        "padding:12px 16px;margin:6px 0 8px 0'>"
        "<p style='font-size:12px;font-weight:700;color:#075985;margin:0 0 8px 0'>"
        "＋ Novo bloco</p></div>",
        unsafe_allow_html=True,
    )

    fn1, fn2, fn3, fn4 = st.columns([3, 2, 2, 2])
    with fn1:
        txt = st.text_input("Buscar por nome", key=f"nb_txt_{t}", placeholder="Digite para filtrar...")
    with fn2:
        pad = st.selectbox("Categoria", ["(qualquer)"] + sorted(PADROES_LABELS.keys()),
            key=f"nb_pad_{t}",
            format_func=lambda x: PADROES_LABELS.get(x, x) if x != "(qualquer)" else "Qualquer")
    with fn3:
        pur = st.selectbox("Purpose", ["(qualquer)", "compound", "isolation", "stability", "explosive"],
            key=f"nb_pur_{t}")
    with fn4:
        uni = st.selectbox("Lateralidade", ["(qualquer)", "bilateral", "unilateral"],
            key=f"nb_uni_{t}")

    fn5, fn6 = st.columns(2)
    with fn5:
        eq_f = st.selectbox("Equipamento", ["(qualquer)"] + todos_equipamentos, key=f"nb_eq_{t}")
    with fn6:
        musc_f = st.selectbox("Músculo", ["(qualquer)"] + todos_musculos, key=f"nb_musc_{t}")

    cands = filtrar_banco(texto=txt, padrao=pad, purpose=pur, unilateral=uni,
                          equipamento=None if eq_f == "(qualquer)" else eq_f,
                          musculo=None if musc_f == "(qualquer)" else musc_f,
                          max_cx=max_cx)
    cands = [e for e in cands if e.nome not in nomes_em_uso]

    nb1, nb2 = st.columns(2)
    with nb1:
        if st.button("🎲 Bloco aleatório", key=f"nb_alea_{t}", use_container_width=True):
            if cands:
                _aplicar_novo_bloco(t, sessao, random.choice(cands))
            _salvar_e_rerun()
    with nb2:
        st.caption(f"{len(cands)} exercício(s)")

    if cands:
        nomes_c = [f"{e.nome}  [{e.purpose} · {e.eq_primario}]" for e in cands[:50]]
        escolha = st.radio("Escolha o exercício", nomes_c, key=f"nb_radio_{t}", label_visibility="collapsed")
        escolha_nome = escolha.split("  [")[0]
        if st.button("✅ Criar bloco", type="primary", key=f"nb_aplicar_{t}"):
            novo_ex = next((e for e in cands if e.nome == escolha_nome), None)
            if novo_ex:
                _aplicar_novo_bloco(t, sessao, novo_ex)
            _salvar_e_rerun()
    elif txt or pad != "(qualquer)" or pur != "(qualquer)" or uni != "(qualquer)" \
            or eq_f != "(qualquer)" or musc_f != "(qualquer)":
        st.caption("Nenhum exercício encontrado com esses filtros.")


def _aplicar_novo_bloco(t: int, sessao: Sessao, novo_ex):
    """Cria novo SuperSerie com novo_ex como ex1 e adiciona ao treino t."""
    labels = "ABCDEFGHIJKLMNOP"
    novo_label = labels[len(sessao.blocos)] if len(sessao.blocos) < len(labels) else str(len(sessao.blocos) + 1)
    novo_bloco = SuperSerie(label=novo_label, ex1=novo_ex, ex2=None, ex3=None)
    st.session_state.sessoes[t].blocos.append(novo_bloco)
    st.session_state.novo_bloco_cands.pop(t, None)



# ---------------------------------------------------------------------------
# Config UI de um treino — retorna dict
# ---------------------------------------------------------------------------

# Ordem de exibição das regiões na UI (top-down)
ORDEM_REGIOES = ["upper", "lower", "core", "cardio"]

# Ordem de exibição das subregiões dentro de cada região
ORDEM_SUBREGIOES = {
    "upper":  ["peito", "costas", "ombro", "bracos"],
    "lower":  ["perna_anterior", "perna_posterior", "adutores", "panturrilha"],
    "core":   ["core"],
    "cardio": ["cardio"],
}

# Ordem de exibição dos padrões dentro de cada subregião
ORDEM_PADROES = {
    "peito":           ["empurrar_compostos", "empurrar_isolados"],
    "costas":          ["remadas", "puxadas"],
    "ombro":           ["ombro_composto", "ombro_isolado", "posterior_ombro"],
    "bracos":          ["biceps", "triceps"],
    "perna_anterior":  ["squat"],
    "perna_posterior": ["hinge", "knee_flexion", "abduction"],
    "adutores":        ["adduction"],
    "panturrilha":     ["flexao_plantar"],
    "core":            ["core_isometrico", "core_dinamico"],
    "cardio":          ["cardio"],
}


def ui_config_treino(t: int) -> dict:
    """
    UI hierárquica expansível.
    Comportamento A: marcar pai = atalho. Se filhos específicos forem marcados,
    apenas eles valem para aquela subárvore. Caso contrário, o pai expande
    para todos os filhos.

    Mistura livre: pode-se marcar 'Membros superiores' inteiro + apenas
    'Hinge' nas pernas, e o app entende.

    Retorna dict com:
      - padroes: lista plana expandida (compatível com código existente)
      - exercicios_por_padrao: dict padrão→qtd (sliders)
    """
    modo = st.radio(
        "Modo", ["Hierarquia", "Template"],
        key=f"modo_{t}", horizontal=True, label_visibility="collapsed",
    )

    padroes_sel: list[str] = []
    epp: dict = {}
    lateralidade_por_padrao: dict = {}

    if modo == "Template":
        tmpl = st.selectbox("Template", list(TEMPLATES.keys()), key=f"tmpl_{t}")
        padroes_tmpl = TEMPLATES[tmpl]
        tmpl_epp = TEMPLATE_EPP.get(tmpl, {})
        st.markdown(
            "<p style='font-size:11px;color:#6b7280;text-transform:uppercase;"
            "letter-spacing:0.07em;margin:10px 0 4px 0'>Exercícios por categoria</p>",
            unsafe_allow_html=True,
        )
        cols = st.columns(min(len(padroes_tmpl), 4))
        for ci, p in enumerate(padroes_tmpl):
            with cols[ci % len(cols)]:
                epp[p] = st.slider(PADROES_LABELS.get(p, p), 0, 5, tmpl_epp.get(p, 1), key=f"epp_{t}_{p}")
        padroes_sel = [p for p in padroes_tmpl if epp.get(p, 0) > 0]

        if "squat" in padroes_tmpl and epp.get("squat", 0) > 0:
            with st.expander("Lateralidade — Agachamento", expanded=False):
                n_squat = epp["squat"]
                col_bi, col_uni = st.columns(2)
                with col_bi:
                    n_bi = st.slider("Bilateral", 0, n_squat, 0, key=f"squat_bi_{t}")
                with col_uni:
                    n_uni = st.slider("Unilateral", 0, n_squat, 0, key=f"squat_uni_{t}")
                if n_bi > 0 or n_uni > 0:
                    if n_bi + n_uni != n_squat:
                        st.caption(f"⚠ Total refinado ({n_bi + n_uni}) difere do total de Agachamento ({n_squat}). Ajuste os sliders.")
                    epp["squat"] = {k: v for k, v in {"bilateral": n_bi, "unilateral": n_uni}.items() if v > 0}

    else:
        # ── Modo Hierarquia (Região → Subregião → Padrão) ─────────────────
        # Cada checkbox marcado vira UMA demanda com seu próprio slider de
        # quantidade. Comportamento A continua: se filhos específicos são
        # marcados, eles substituem o pai dentro daquele ramo.
        st.markdown(
            "<p style='font-size:11px;color:#9ca3af;margin:6px 0 10px 0'>"
            "Marque um grupo e defina quantos exercícios. "
            "Use o toggle ▸ para refinar em subgrupos.</p>",
            unsafe_allow_html=True,
        )

        # Listas de itens marcados, separados por nível
        regioes_marcadas: list[str] = []
        subs_marcadas_por_regiao: dict[str, list[str]] = {}
        pads_marcados_por_subregiao: dict[str, list[str]] = {}

        # Layout em 3 colunas: Superiores | Inferiores | Core + Cardio
        col_upper, col_lower, col_other = st.columns([5, 5, 3])
        col_map = {
            "upper":  col_upper,
            "lower":  col_lower,
            "core":   col_other,
            "cardio": col_other,
        }

        for regiao in ORDEM_REGIOES:
            if regiao not in REGIAO_PARA_SUBREGIOES:
                continue
            regiao_lbl = REGIOES_LABELS.get(regiao, regiao)

            with col_map[regiao]:
                # Header visual da região
                st.markdown(
                    f"<div style='background:#fff7ed;border-left:3px solid #e85d04;"
                    f"padding:5px 10px;margin:4px 0 6px;border-radius:0 4px 4px 0'>"
                    f"<span style='font-size:11px;font-weight:700;color:#c2410c;"
                    f"text-transform:uppercase;letter-spacing:.06em'>{regiao_lbl}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # Linha da região: checkbox "Todos" + toggle refinar
                rc, rt = st.columns([6, 1])
                with rc:
                    marcado_regiao = st.checkbox(
                        "Todos os grupos", key=f"reg_{t}_{regiao}",
                    )
                with rt:
                    expandido_regiao = st.toggle(
                        "r", key=f"reg_exp_{t}_{regiao}",
                        label_visibility="collapsed",
                        help=f"Refinar {regiao_lbl} por subgrupo",
                    )

                if marcado_regiao:
                    regioes_marcadas.append(regiao)

                if expandido_regiao:
                    subs_aqui: list[str] = []
                    for subregiao in ORDEM_SUBREGIOES.get(regiao, []):
                        sub_lbl = SUBREGIOES_LABELS.get(subregiao, subregiao)
                        padroes_da_sub = ORDEM_PADROES.get(subregiao, [])

                        # Subregião: indentada via coluna vazia à esquerda
                        _, s_col = st.columns([0.07, 0.93])
                        with s_col:
                            s_chk, s_tog = st.columns([6, 1])
                            with s_chk:
                                marcado_sub = st.checkbox(
                                    sub_lbl, key=f"sub_{t}_{subregiao}",
                                )
                            with s_tog:
                                expandido_sub = False
                                if len(padroes_da_sub) > 1:
                                    expandido_sub = st.toggle(
                                        "r", key=f"sub_exp_{t}_{subregiao}",
                                        label_visibility="collapsed",
                                        help=f"Refinar {sub_lbl} por padrão",
                                    )

                        if marcado_sub:
                            subs_aqui.append(subregiao)

                        if expandido_sub:
                            pads_aqui: list[str] = []
                            for padrao in padroes_da_sub:
                                pad_lbl = PADROES_LABELS.get(padrao, padrao)
                                # Padrão: indentação dupla
                                _, p_col = st.columns([0.14, 0.86])
                                with p_col:
                                    marcado_pad = st.checkbox(
                                        pad_lbl, key=f"pad_{t}_{padrao}",
                                    )
                                    if marcado_pad:
                                        pads_aqui.append(padrao)
                            pads_marcados_por_subregiao[subregiao] = pads_aqui

                    subs_marcadas_por_regiao[regiao] = subs_aqui

        # ── Resolver Comportamento A e montar lista de demandas ───────────
        # Demanda = (nivel, escopo, qtd). Para cada item marcado, cria 1.
        # Regra A: se um pai tem filhos específicos marcados (ou netos via
        # subregião), o pai NÃO vira demanda — apenas os filhos.
        demandas_def: list[tuple[str, str]] = []  # (nivel, escopo) na ordem da UI

        # Padrões individuais marcados → sempre viram demandas
        for sub, pads in pads_marcados_por_subregiao.items():
            for p in pads:
                demandas_def.append(("padrao", p))

        # Subregiões marcadas: vira demanda só se NÃO houver padrões
        # específicos marcados dentro dela
        for regiao, subs in subs_marcadas_por_regiao.items():
            for sub in subs:
                if not pads_marcados_por_subregiao.get(sub):
                    demandas_def.append(("subregiao", sub))

        # Regiões marcadas: vira demanda só se NÃO houver subregiões nem
        # padrões específicos marcados dentro dela
        for regiao in regioes_marcadas:
            tem_subs   = bool(subs_marcadas_por_regiao.get(regiao))
            tem_pads   = any(
                pads_marcados_por_subregiao.get(s)
                for s in ORDEM_SUBREGIOES.get(regiao, [])
            )
            if not tem_subs and not tem_pads:
                demandas_def.append(("regiao", regiao))

        # ── Sliders: 1 por demanda ────────────────────────────────────────
        demandas: list[tuple[str, str, int]] = []
        if demandas_def:
            st.markdown(
                "<p style='font-size:11px;color:#6b7280;text-transform:uppercase;"
                "letter-spacing:0.07em;margin:14px 0 4px 0'>"
                "Quantos exercícios de cada grupo</p>",
                unsafe_allow_html=True,
            )
            cols_sl = st.columns(min(len(demandas_def), 3))
            for ci, (nivel, escopo) in enumerate(demandas_def):
                if nivel == "regiao":
                    label = REGIOES_LABELS.get(escopo, escopo)
                    default = 6
                elif nivel == "subregiao":
                    label = SUBREGIOES_LABELS.get(escopo, escopo)
                    default = 2
                else:
                    label = PADROES_LABELS.get(escopo, escopo)
                    default = 1
                with cols_sl[ci % len(cols_sl)]:
                    qtd = st.slider(
                        label, 0, 12, default,
                        key=f"qtd_{t}_{nivel}_{escopo}",
                    )
                if qtd > 0:
                    demandas.append((nivel, escopo, qtd))

        # Lateralidade para squat: detecta demanda de padrao=squat ou subregiao=perna_anterior
        _squat_dem = next(
            ((n, e, qtd) for n, e, qtd in demandas
             if (n == "padrao" and e == "squat") or (n == "subregiao" and e == "perna_anterior")),
            None,
        )
        if _squat_dem:
            _squat_nivel, _squat_escopo, squat_qtd = _squat_dem
            with st.expander("Lateralidade — Agachamento", expanded=False):
                col_bi, col_uni = st.columns(2)
                with col_bi:
                    n_bi = st.slider("Bilateral", 0, squat_qtd, 0, key=f"squat_bi_{t}")
                with col_uni:
                    n_uni = st.slider("Unilateral", 0, squat_qtd, 0, key=f"squat_uni_{t}")
                if n_bi > 0 or n_uni > 0:
                    if n_bi + n_uni != squat_qtd:
                        st.caption(f"⚠ Total refinado ({n_bi + n_uni}) difere do total de Agachamento ({squat_qtd}). Ajuste os sliders.")
                    lateralidade_por_padrao[_squat_escopo] = {k: v for k, v in {"bilateral": n_bi, "unilateral": n_uni}.items() if v > 0}

        # Marcador para o resto do código saber que estamos em modo demandas
        epp = {}                # não usado nesse modo
        padroes_sel = []        # mantido vazio — quem dirige é demandas

    # ── Exercícios fixos ──────────────────────────────────────────────────
    st.markdown("<hr class='thin-hr' style='margin:14px 0'>", unsafe_allow_html=True)

    fixos_key = f"fixos_{t}"
    st.session_state.setdefault(fixos_key, [])
    fixos: list[str] = st.session_state[fixos_key]

    with st.expander(f"📌 Exercícios fixos ({len(fixos)}/3)", expanded=bool(fixos)):

        # Lista de exercícios já fixados
        for fi, nome_fixo in enumerate(fixos):
            ex_fixo = next((e for e in banco if e.nome == nome_fixo), None)
            col_fixo, col_rm_fixo = st.columns([11, 1])
            with col_fixo:
                if ex_fixo:
                    st.markdown(
                        f"<p style='margin:2px 0;font-size:13px;line-height:1.6'>"
                        f"📌 <b>{ex_fixo.nome}</b> "
                        f"<span style='color:#9ca3af;font-size:11px'>"
                        f"{ex_fixo.purpose} · {ex_fixo.padrao} · 🔧 {ex_fixo.eq_primario}</span></p>",
                        unsafe_allow_html=True,
                    )
            with col_rm_fixo:
                if st.button("✕", key=f"rm_fixo_{t}_{fi}", help="Remover"):
                    fixos.pop(fi)
                    st.session_state[fixos_key] = fixos
                    st.rerun()

        if len(fixos) < 3:
            if fixos:
                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

            nomes_fixos = set(fixos)
            busca_fixo = st.text_input(
                "Buscar exercício",
                key=f"busca_fixo_{t}",
                placeholder="Digite o nome para filtrar...",
                label_visibility="collapsed",
            )

            if busca_fixo.strip():
                cands_fixo = filtrar_banco(texto=busca_fixo, max_cx=5)
                cands_fixo = [e for e in cands_fixo if e.nome not in nomes_fixos]

                if cands_fixo:
                    nomes_c = [f"{e.nome}  [{e.purpose} · {e.padrao}]" for e in cands_fixo[:30]]
                    escolha_fixo = st.radio(
                        "Resultado",
                        nomes_c,
                        key=f"radio_fixo_{t}",
                        label_visibility="collapsed",
                    )
                    if st.button("📌 Fixar", key=f"add_fixo_{t}", type="primary"):
                        nome_esc = escolha_fixo.split("  [")[0]
                        if nome_esc not in nomes_fixos:
                            fixos.append(nome_esc)
                            st.session_state[fixos_key] = fixos
                            if f"busca_fixo_{t}" in st.session_state:
                                del st.session_state[f"busca_fixo_{t}"]
                        st.rerun()
                else:
                    st.caption("Nenhum exercício encontrado.")
        else:
            st.caption("Máximo de 3 exercícios fixos atingido.")

    # Modo Template não usa demandas
    if modo == "Template":
        demandas = []

    exercicios_travados = [e for e in banco if e.nome in set(fixos)]
    return {
        "padroes": padroes_sel,
        "exercicios_por_padrao": epp,
        "demandas": demandas,
        "exercicios_travados": exercicios_travados,
        "lateralidade_por_padrao": lateralidade_por_padrao,
    }


# ---------------------------------------------------------------------------
# Reset guard — executa ANTES de qualquer widget ser renderizado
# ---------------------------------------------------------------------------
if st.session_state.get("_do_reset", False):
    del st.session_state["_do_reset"]
    for k in list(st.session_state.keys()):
        if k.startswith(("reg_", "sub_", "pad_", "chk_", "grp_")):
            # Inclui reg_exp_ e sub_exp_ (toggles de expansão)
            st.session_state[k] = False
        elif k.startswith("fixos_"):
            st.session_state[k] = []
        elif k.startswith(("epp_", "qtd_", "tmpl_", "busca_fixo_", "radio_fixo_", "squat_bi_", "squat_uni_")) or \
             (k.startswith("modo_") and k[5:].isdigit()) or \
             k in ("n_treinos", "tamanho_bloco", "max_cx", "variar_entre", "evitar_agonistas", "aluno_exp"):
            del st.session_state[k]

# ===========================================================================
# LAYOUT
# ===========================================================================

st.markdown("""
<div class="app-header">
    <div>
        <h1>💪 BF Treinamento</h1>
        <p>Gerador de sessões personalizadas</p>
    </div>
</div>
""", unsafe_allow_html=True)

tab_treino, tab_alunos, tab_historico = st.tabs(["🏋️ Treinos", "👥 Alunos", "📋 Histórico"])

# ===========================================================================
# TAB TREINOS
# ===========================================================================
with tab_treino:

    # -----------------------------------------------------------------------
    # Painel de configuração
    # -----------------------------------------------------------------------
    lbl_toggle = "▲ Fechar configuração" if st.session_state.config_aberta else "▼ Configurar treinos"
    if st.button(lbl_toggle, key="toggle_config"):
        st.session_state.config_aberta = not st.session_state.config_aberta
        st.rerun()

    configs_ui = []   # preenchido dentro do painel

    if st.session_state.config_aberta:
        st.markdown("<div class='config-panel'>", unsafe_allow_html=True)

        # Configurações gerais
        st.markdown("<p class='config-title'>Configurações gerais</p>", unsafe_allow_html=True)
        cg1, cg2, cg3, cg4, cg4b, cg5 = st.columns([2, 2, 2, 3, 3, 3])
        with cg1:
            n_treinos = st.selectbox("Nº de treinos", [1, 2, 3, 4, 5], index=0, key="n_treinos")
        with cg2:
            tamanho_bloco = st.radio("Exerc./bloco", [1, 2, 3], index=1, horizontal=True, key="tamanho_bloco")
        with cg3:
            max_cx = st.slider("Complexidade máx.", 1, 5, 5, key="max_cx")
        with cg4:
            variar = st.checkbox(
                "Evitar similaridade entre treinos", value=False, key="variar_entre",
                help="Evita repetir grupos de similaridade entre treinos",
            )
        with cg4b:
            evitar_agon = st.checkbox(
                "Evitar agonistas no bloco", value=True, key="evitar_agonistas",
                help="Evita parear exercícios do mesmo grupo muscular (push+push ou pull+pull). "
                     "Favorece pares antagonistas: costas+peito, bíceps+tríceps.",
            )
        with cg5:
            aluno_exp = st.selectbox("Aluno (PNG)", nomes_alunos, key="aluno_exp")

        st.markdown("<hr class='thin-hr' style='margin:16px 0'>", unsafe_allow_html=True)

        # Config por treino
        n = int(n_treinos)
        if n == 1:
            st.markdown("<p class='config-title'>Treino 1</p>", unsafe_allow_html=True)
            cfg = ui_config_treino(0)
            cfg.update({"max_complexidade": max_cx, "tamanho_bloco": tamanho_bloco, "equipamentos_bloqueados": [], "evitar_agonistas": evitar_agon})
            configs_ui.append(cfg)
        else:
            tabs_cfg = st.tabs([f"Treino {i+1}" for i in range(n)])
            for i, tab_c in enumerate(tabs_cfg):
                with tab_c:
                    cfg = ui_config_treino(i)
                    cfg.update({"max_complexidade": max_cx, "tamanho_bloco": tamanho_bloco, "equipamentos_bloqueados": [], "evitar_agonistas": evitar_agon})
                    configs_ui.append(cfg)

        st.markdown("</div>", unsafe_allow_html=True)

        # Botões gerar + resetar
        st.markdown("<div style='margin-top:12px'>", unsafe_allow_html=True)
        bc1, bc2 = st.columns([4, 1])
        with bc1:
            gerar_clicked = st.button("▶ Gerar treinos", type="primary", use_container_width=True)
        with bc2:
            if st.button("↺ Resetar", use_container_width=True, help="Limpa todas as seleções e volta ao padrão"):
                st.session_state["_do_reset"] = True
                st.rerun()

        if gerar_clicked:
            vazios = [
                i+1 for i, c in enumerate(configs_ui)
                if not c.get("padroes") and not c.get("demandas")
            ]
            if vazios:
                st.warning(f"Selecione ao menos uma categoria no(s) Treino(s) {', '.join(str(x) for x in vazios)}.")
            else:
                with st.spinner("Gerando..."):
                    sessoes = gerar_multiplos_treinos(banco, configs_ui, variar_entre_treinos=variar)
                n_sess = len(sessoes)
                st.session_state.sessoes        = sessoes
                st.session_state.configs_geradas = configs_ui
                st.session_state.sub_alvo       = [None] * n_sess
                st.session_state.candidatos     = [[] for _ in range(n_sess)]
                st.session_state.modo_viz       = ["visualizar"] * n_sess
                # Não fecha o painel — checkboxes permanecem visíveis
                salvar_sessoes(sessoes)
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Resultados
    # -----------------------------------------------------------------------
    sessoes: list = st.session_state.sessoes

    if sessoes:
        n_sess = len(sessoes)

        # Garante tamanho das listas de estado
        for k, default in [("sub_alvo", None), ("candidatos", []), ("modo_viz", "visualizar")]:
            while len(st.session_state[k]) < n_sess:
                st.session_state[k].append([] if default == [] else default)

        # Botão ZIP quando há mais de 1 treino
        if n_sess > 1:
            ae_zip = st.session_state.get("aluno_exp", "Selecionar aluno...")
            if ae_zip and ae_zip != "Selecionar aluno...":
                lp = Path("logo.png")
                if not lp.exists(): lp = Path("logo.jpg")
                logo_b = lp.read_bytes() if lp.exists() else None
                zip_bytes = gerar_zip(sessoes, ae_zip, logo_b)
                st.download_button(
                    f"⬇ Baixar todos os treinos (ZIP)",
                    data=zip_bytes,
                    file_name=f"treinos_{ae_zip.lower().replace(' ','_')}.zip",
                    mime="application/zip",
                    use_container_width=True,
                    key="dl_zip",
                )
                st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

        # Salvar no histórico
        with st.expander("💾 Salvar no histórico", expanded=False):
            ae_hist = st.session_state.get("aluno_exp", "Selecionar aluno...")
            aluno_hist = ae_hist if ae_hist != "Selecionar aluno..." else ""
            col_et, col_sv = st.columns([3, 1])
            with col_et:
                etiqueta_hist = st.text_input(
                    "Etiqueta (opcional)",
                    placeholder="ex: Turma manhã — semana 1",
                    key="etiqueta_hist",
                    label_visibility="collapsed",
                )
            with col_sv:
                if st.button("💾 Salvar", key="btn_salvar_hist", use_container_width=True):
                    adicionar_ao_historico(sessoes, aluno_hist, etiqueta_hist)
                    st.success("Salvo no histórico!")

        result_tabs = st.tabs([f"Treino {i+1}" for i in range(n_sess)]) if n_sess > 1 else [st.container()]

        for t, container in enumerate(result_tabs):
            with container:
                sessao: Sessao = sessoes[t]
                cats = " · ".join(PADROES_LABELS.get(p, p) for p in sessao.tipo.split(" + ") if p)

                st.markdown(
                    f"<p style='font-size:11px;color:#9ca3af;margin:16px 0 2px 0;"
                    f"text-transform:uppercase;letter-spacing:0.08em'>Sessão {t+1}</p>"
                    f"<p style='font-size:18px;font-weight:700;color:#111827;"
                    f"margin:0 0 12px 0'>{cats}</p>",
                    unsafe_allow_html=True,
                )

                # Linha de ações
                ca1, ca2, ca3 = st.columns([3, 2, 2])
                with ca1:
                    ae = st.session_state.get("aluno_exp", "Selecionar aluno...")
                    if ae and ae != "Selecionar aluno...":
                        lp = Path("logo.png")
                        if not lp.exists(): lp = Path("logo.jpg")
                        logo_b = lp.read_bytes() if lp.exists() else None
                        png = gerar_png(sessao, ae, logo_bytes=logo_b)
                        st.download_button(
                            "⬇ Baixar PNG", data=png,
                            file_name=f"treino{t+1}_{ae.lower().replace(' ','_')}.png",
                            mime="image/png", use_container_width=True, key=f"dl_{t}",
                        )
                with ca2:
                    if st.button("🔄 Regerar", key=f"regen_{t}", use_container_width=True):
                        # Prioridade 1: config salva no momento da geração
                        cfgs = st.session_state.get("configs_geradas", [])
                        if cfgs and t < len(cfgs):
                            cfg_r = cfgs[t]
                        else:
                            # Fallback: reconstrói EPP contando exercícios reais da sessão
                            contagem: dict = {}
                            for bloco in sessao.blocos:
                                for ex in [bloco.ex1, bloco.ex2, bloco.ex3]:
                                    if ex and ex.padrao:
                                        contagem[ex.padrao] = contagem.get(ex.padrao, 0) + 1
                            pats = list(contagem.keys())
                            cfg_r = {
                                "padroes": pats,
                                "exercicios_por_padrao": contagem,
                                "max_complexidade": st.session_state.get("max_cx", 5),
                                "tamanho_bloco": st.session_state.get("tamanho_bloco", 2),
                                "equipamentos_bloqueados": [],
                                "exercicios_travados": [],
                            }
                        # Bloqueia exercícios já presentes nos outros treinos
                        exs_outros = [
                            ex
                            for i, s in enumerate(st.session_state.sessoes)
                            if i != t
                            for bloco in s.blocos
                            for ex in [bloco.ex1, bloco.ex2, bloco.ex3]
                            if ex
                        ]
                        nomes_outros = {ex.nome for ex in exs_outros}
                        # Bloqueio bidirecional de variações: bloqueia variações dos usados
                        # e bloqueia o pai quando uma variação foi usada
                        pais_dos_outros = {ex.variacao_de for ex in exs_outros if ex.variacao_de}
                        banco_regen = [
                            e for e in banco
                            if e.nome not in nomes_outros           # nome exato bloqueado
                            and e.nome not in pais_dos_outros       # pai de variação usada bloqueado
                            and (e.variacao_de is None or e.variacao_de not in nomes_outros)  # variação de exercício usado bloqueada
                        ]
                        if cfg_r.get("demandas"):
                            nova = gerar_sessao_por_demandas(
                                banco_regen, demandas=cfg_r["demandas"],
                                equipamentos_bloqueados=cfg_r.get("equipamentos_bloqueados", []),
                                max_complexidade=cfg_r.get("max_complexidade", 5),
                                tamanho_bloco=cfg_r.get("tamanho_bloco", 2),
                                exercicios_travados=cfg_r.get("exercicios_travados", []),
                                evitar_agonistas=cfg_r.get("evitar_agonistas", False),
                                lateralidade_por_padrao=cfg_r.get("lateralidade_por_padrao"),
                            )
                        else:
                            nova = gerar_sessao(
                                banco_regen, cfg_r["padroes"],
                                exercicios_por_padrao=cfg_r["exercicios_por_padrao"],
                                equipamentos_bloqueados=cfg_r.get("equipamentos_bloqueados", []),
                                max_complexidade=cfg_r.get("max_complexidade", 5),
                                tamanho_bloco=cfg_r.get("tamanho_bloco", 2),
                                exercicios_travados=cfg_r.get("exercicios_travados", []),
                                evitar_agonistas=cfg_r.get("evitar_agonistas", False),
                            )
                        st.session_state.sessoes[t] = nova
                        st.session_state.sub_alvo[t] = None
                        st.session_state.candidatos[t] = []
                        salvar_sessoes(st.session_state.sessoes)
                        st.rerun()
                with ca3:
                    modo_atual = st.session_state.modo_viz[t]
                    lbl_m = "✏️ Editar" if modo_atual == "visualizar" else "👁 Visualizar"
                    if st.button(lbl_m, key=f"toggle_modo_{t}", use_container_width=True):
                        st.session_state.modo_viz[t] = "editar" if modo_atual == "visualizar" else "visualizar"
                        st.session_state.sub_alvo[t] = None
                        st.session_state.candidatos[t] = []
                        st.rerun()

                st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

                if st.session_state.modo_viz[t] == "visualizar":
                    render_slim(sessao)
                else:
                    render_editar(sessao, t, max_cx=st.session_state.get("max_cx", 5))

    else:
        st.markdown("""
        <div style="text-align:center; padding: 60px 20px; color: #9ca3af;">
            <div style="font-size: 52px; margin-bottom: 16px;">🏋️</div>
            <div style="font-size: 18px; font-weight: 600; color: #374151;">Configure e gere seu primeiro treino</div>
            <div style="font-size: 14px; margin-top: 8px;">
                Use o painel acima para definir as categorias e clique em <strong>Gerar treinos</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ===========================================================================
# TAB ALUNOS
# ===========================================================================
with tab_alunos:
    st.markdown(
        "<p style='font-size:11px;color:#9ca3af;margin:0 0 2px 0;"
        "text-transform:uppercase;letter-spacing:0.08em'>Gestão de alunos</p>"
        "<p style='font-size:20px;font-weight:600;color:#111827;margin:0 0 16px 0'>Cadastro</p>",
        unsafe_allow_html=True,
    )

    alunos_atual = carregar_alunos()
    objs  = ["hipertrofia", "forca", "resistencia", "emagrecimento", "condicionamento", "reabilitacao"]
    nivis = ["iniciante", "intermediario", "avancado"]

    with st.expander("➕ Novo aluno", expanded=(len(alunos_atual) == 0)):
        with st.form("form_novo_aluno", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                novo_nome  = st.text_input("Nome *")
                novo_nivel = st.selectbox("Nível", nivis, index=1)
            with c2:
                novo_obj  = st.selectbox("Objetivo", objs)
                novo_rest = st.text_input("Restrições (vírgula)", placeholder="ex: ombro direito, joelho")
            novo_obs = st.text_area("Observações")
            if st.form_submit_button("Salvar aluno", type="primary", use_container_width=True):
                if not novo_nome.strip():
                    st.error("Nome é obrigatório.")
                elif any(a["nome"].lower() == novo_nome.strip().lower() for a in alunos_atual):
                    st.error(f"Já existe '{novo_nome.strip()}'.")
                else:
                    alunos_atual.append({
                        "nome": novo_nome.strip(), "nivel": novo_nivel, "objetivo": novo_obj,
                        "restricoes": [r.strip() for r in novo_rest.split(",") if r.strip()],
                        "obs": novo_obs.strip(),
                    })
                    salvar_alunos(alunos_atual)
                    st.success(f"Aluno '{novo_nome.strip()}' cadastrado.")
                    st.rerun()

    st.markdown("---")

    if not alunos_atual:
        st.markdown(
            "<div style='text-align:center;padding:40px 20px;color:#9ca3af'>"
            "<div style='font-size:40px;margin-bottom:8px'>👥</div>"
            "<div style='font-size:14px'>Nenhum aluno cadastrado ainda.</div>"
            "</div>", unsafe_allow_html=True,
        )
    else:
        st.caption(f"{len(alunos_atual)} aluno(s)")
        for i, aluno in enumerate(alunos_atual):
            if st.session_state.edit_aluno_idx == i:
                with st.form(f"form_edit_{i}"):
                    st.markdown(
                        f"<p style='font-size:13px;font-weight:600;color:#e85d04;margin:0 0 8px 0'>"
                        f"✏️ Editando: {aluno['nome']}</p>", unsafe_allow_html=True,
                    )
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        en  = st.text_input("Nome *", value=aluno["nome"])
                        enl = st.selectbox("Nível", nivis, index=nivis.index(aluno.get("nivel", "intermediario")))
                    with ec2:
                        eo = st.selectbox("Objetivo", objs, index=objs.index(aluno.get("objetivo", "hipertrofia")))
                        er = st.text_input("Restrições", value=", ".join(aluno.get("restricoes", [])))
                    eob = st.text_area("Observações", value=aluno.get("obs", ""))
                    cs, cc = st.columns(2)
                    with cs:
                        if st.form_submit_button("💾 Salvar", type="primary", use_container_width=True):
                            if not en.strip():
                                st.error("Nome obrigatório.")
                            else:
                                alunos_atual[i] = {
                                    "nome": en.strip(), "nivel": enl, "objetivo": eo,
                                    "restricoes": [r.strip() for r in er.split(",") if r.strip()],
                                    "obs": eob.strip(),
                                }
                                salvar_alunos(alunos_atual)
                                st.session_state.edit_aluno_idx = None
                                st.rerun()
                    with cc:
                        if st.form_submit_button("✕ Cancelar", use_container_width=True):
                            st.session_state.edit_aluno_idx = None
                            st.rerun()
            else:
                col_info, col_ed, col_del = st.columns([10, 1, 1])
                with col_info:
                    rt = ", ".join(aluno.get("restricoes", [])) or "—"
                    ob = aluno.get("obs", "") or "—"
                    st.markdown(
                        f"<div style='background:#f9fafb;border:1px solid #e5e7eb;"
                        f"border-radius:8px;padding:12px 16px;margin-bottom:8px'>"
                        f"<p style='margin:0;font-size:15px;font-weight:600;color:#111827'>{aluno['nome']}</p>"
                        f"<p style='margin:4px 0 0 0;font-size:12px;color:#6b7280'>"
                        f"<b>Nível:</b> {aluno.get('nivel','—')} &nbsp;·&nbsp; "
                        f"<b>Objetivo:</b> {aluno.get('objetivo','—')} &nbsp;·&nbsp; "
                        f"<b>Restrições:</b> {rt}</p>"
                        f"<p style='margin:4px 0 0 0;font-size:12px;color:#9ca3af'><b>Obs:</b> {ob}</p></div>",
                        unsafe_allow_html=True,
                    )
                with col_ed:
                    if st.button("✏️", key=f"edit_{i}", help=f"Editar {aluno['nome']}"):
                        st.session_state.edit_aluno_idx = i
                        st.rerun()
                with col_del:
                    if st.button("🗑", key=f"del_{i}", help=f"Remover {aluno['nome']}"):
                        alunos_atual.pop(i)
                        salvar_alunos(alunos_atual)
                        st.rerun()

# ===========================================================================
# TAB HISTÓRICO
# ===========================================================================
with tab_historico:
    st.markdown(
        "<p style='font-size:11px;color:#9ca3af;margin:0 0 2px 0;"
        "text-transform:uppercase;letter-spacing:0.08em'>Registros salvos</p>"
        "<p style='font-size:20px;font-weight:600;color:#111827;margin:0 0 16px 0'>Histórico de treinos</p>",
        unsafe_allow_html=True,
    )

    historico = carregar_historico()

    if not historico:
        st.markdown(
            "<div style='text-align:center;padding:60px 20px;color:#9ca3af'>"
            "<div style='font-size:40px;margin-bottom:12px'>📋</div>"
            "<div style='font-size:15px;font-weight:500;color:#374151'>Nenhum treino salvo ainda</div>"
            "<div style='font-size:13px;margin-top:6px'>Gere um treino e clique em "
            "<b>💾 Salvar no histórico</b> para registrá-lo aqui.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.caption(f"{len(historico)} registro(s)")
        st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

        for reg in historico:
            reg_id   = reg["id"]
            data     = reg.get("data", "—")
            aluno    = reg.get("aluno", "—")
            etiqueta = reg.get("etiqueta", "—")
            n_sess   = reg.get("n_treinos", len(reg.get("sessoes", [])))

            # Card do registro
            with st.container():
                col_info, col_acoes = st.columns([5, 2])
                with col_info:
                    treinos_label = "treino" if n_sess == 1 else "treinos"
                    st.markdown(
                        f"<div style='background:#f9fafb;border:1px solid #e5e7eb;"
                        f"border-radius:10px;padding:14px 18px;margin-bottom:8px'>"
                        f"<p style='margin:0;font-size:15px;font-weight:600;color:#111827'>"
                        f"{etiqueta}</p>"
                        f"<p style='margin:4px 0 0 0;font-size:12px;color:#6b7280'>"
                        f"<b>Aluno/Turma:</b> {aluno} &nbsp;·&nbsp; "
                        f"<b>Data:</b> {data} &nbsp;·&nbsp; "
                        f"<b>{n_sess} {treinos_label}</b></p>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                with col_acoes:
                    # Expandir para ver o conteúdo
                    with st.expander("👁 Ver treinos"):
                        try:
                            sessoes_reg = [_dict_to_sessao(s) for s in reg["sessoes"]]
                            for ti, sessao_h in enumerate(sessoes_reg):
                                cats = " · ".join(
                                    PADROES_LABELS.get(p, p)
                                    for p in sessao_h.tipo.split(" + ") if p
                                )
                                st.markdown(
                                    f"<p style='font-size:11px;font-weight:700;color:#e85d04;"
                                    f"text-transform:uppercase;letter-spacing:0.08em;"
                                    f"margin:10px 0 6px 0'>Treino {ti+1} — {cats}</p>",
                                    unsafe_allow_html=True,
                                )
                                render_slim(sessao_h)
                        except Exception as e:
                            st.caption(f"Erro ao carregar: {e}")

                    # Carregar para editar
                    if st.button("↩ Carregar", key=f"load_{reg_id}",
                                 use_container_width=True,
                                 help="Carrega estes treinos na aba principal para editar"):
                        try:
                            sessoes_reg = [_dict_to_sessao(s) for s in reg["sessoes"]]
                            n = len(sessoes_reg)
                            st.session_state.sessoes        = sessoes_reg
                            st.session_state.configs_geradas = []
                            st.session_state.sub_alvo       = [None] * n
                            st.session_state.candidatos     = [[] for _ in range(n)]
                            st.session_state.modo_viz       = ["visualizar"] * n
                            salvar_sessoes(sessoes_reg)
                            st.success("Treinos carregados! Role a página para ver o resultado.")
                        except Exception as e:
                            st.error(f"Erro ao carregar: {e}")

                    # Deletar registro
                    if st.button("🗑 Apagar", key=f"del_hist_{reg_id}",
                                 use_container_width=True,
                                 help="Remove este registro do histórico"):
                        historico_novo = [r for r in historico if r["id"] != reg_id]
                        salvar_historico(historico_novo)
                        st.rerun()
