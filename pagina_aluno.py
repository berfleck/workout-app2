# -*- coding: utf-8 -*-
"""Gerador da PÁGINA DO ALUNO (feature de mídia, Fase 2).

Pega uma rotina (lista de sessões serializadas, shape de `historico.sessoes`)
+ o catálogo de mídia e produz UMA página HTML standalone, mobile-first, com a
marca BF Treinamento. Mídia colapsada com tap-to-play e cadeia de fallback:
   vídeo embedded (iframe 9:16) > imagem animada free-db > (sem botão)

Fonte de verdade do template. A ferramenta de mockup
(`tools/gerar_mockup_pagina_aluno.py`) importa daqui.
"""
import base64
import json
import os

_RAIZ = os.path.dirname(os.path.abspath(__file__))
_CATALOGO_PATH = os.path.join(_RAIZ, "midia_exercicios.json")
_LOGO_PATH = os.path.join(_RAIZ, "static", "logo.png")

_LETRAS = "ABCDEFGH"


def carregar_catalogo():
    if not os.path.exists(_CATALOGO_PATH):
        return {}
    with open(_CATALOGO_PATH, encoding="utf-8") as f:
        return json.load(f)


def _logo_b64():
    try:
        with open(_LOGO_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return ""


def rotina_de_sessoes(sessoes, aluno_nome, nomes_treinos=None):
    """Normaliza a lista de sessões (shape de historico.sessoes) para o formato
    de render. `nomes_treinos`: lista opcional de rótulos por treino."""
    treinos = []
    for ti, s in enumerate(sessoes):
        nome_t = (nomes_treinos[ti] if nomes_treinos and ti < len(nomes_treinos)
                  else f"Treino {_LETRAS[ti] if ti < len(_LETRAS) else ti + 1}")
        blocos = []
        for b in s.get("blocos", []):
            exs = []
            for slot in ("ex1", "ex2", "ex3"):
                ex = b.get(slot)
                if not ex:
                    continue
                exs.append({
                    "nome": ex.get("nome", ""),
                    "presc": _presc(ex),
                    "yt": ex.get("youtube") or None,  # futuro: vídeo no próprio ex
                })
            if exs:
                blocos.append({"label": b.get("label", ""), "exs": exs})
        treinos.append({"nome": nome_t, "blocos": blocos})
    return {"aluno": aluno_nome, "treinos": treinos}


def _presc(ex):
    series = ex.get("series")
    reps = ex.get("reps")
    rir = ex.get("rir")
    partes = []
    if series and reps:
        partes.append(f"{series}×{reps}")
    elif reps:
        partes.append(str(reps))
    elif series:
        partes.append(f"{series} séries")
    if rir not in (None, "", "—"):
        partes.append(f"RIR {rir}")
    return " · ".join(partes)


def _ex_html(ex, num, catalogo):
    nome = ex["nome"]
    m = catalogo.get(nome.strip()) or catalogo.get(nome)
    yt = ex.get("yt")
    expand, tem_midia = "", False
    if yt:
        tem_midia = True
        expand = (f'<div class="media-wrap"><div class="media-video"><div class="video-aspect">'
                  f'<iframe data-yt="{yt}" src="" allow="autoplay; encrypted-media; picture-in-picture" '
                  f'allowfullscreen></iframe></div></div></div>')
    elif m:
        tem_midia = True
        expand = (f'<div class="media-wrap"><div class="media-img">'
                  f'<img loading="lazy" data-a="{m["img0"]}" data-b="{m["img1"]}" alt=""></div></div>')

    if tem_midia:
        botao = ('<div class="btn-slot"><button class="ver-btn" onclick="toggleMedia(this)">'
                 '<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>'
                 '<span class="btn-text">Ver</span></button></div>')
    else:
        botao = '<div class="btn-slot"></div>'

    presc = f'<span class="badge">{ex["presc"]}</span>' if ex["presc"] else ""
    return (f'<div class="ex-item"><div class="ex-row">'
            f'<div class="ex-info"><span class="ex-num">{num}</span>'
            f'<span class="ex-nome">{_esc(nome.strip())}</span></div>'
            f'<div class="ex-actions">{presc}{botao}</div></div>{expand}</div>')


def _bloco_html(bloco, catalogo):
    letra = bloco["label"] or "•"
    itens = "".join(_ex_html(ex, f"{letra}{i + 1}", catalogo)
                    for i, ex in enumerate(bloco["exs"]))
    label = f"Bloco {bloco['label']}" if bloco["label"] else "Bloco"
    return f'<div class="group"><div class="group-label">{label}</div>{itens}</div>'


def _treino_html(treino, idx, catalogo):
    blocos = "".join(_bloco_html(b, catalogo) for b in treino["blocos"])
    ativo = " active" if idx == 0 else ""
    return f'<section class="treino{ativo}" data-treino="{idx}">{blocos}</section>'


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def gerar_html(rotina, catalogo=None):
    """rotina: dict {aluno, treinos:[{nome, blocos:[{label, exs:[{nome,presc,yt}]}]}]}."""
    if catalogo is None:
        catalogo = carregar_catalogo()
    tabs = "".join(
        f'<button class="tab{" active" if i == 0 else ""}" onclick="showTreino({i})">{_esc(t["nome"])}</button>'
        for i, t in enumerate(rotina["treinos"]))
    treinos = "".join(_treino_html(t, i, catalogo) for i, t in enumerate(rotina["treinos"]))
    return _TEMPLATE.format(
        logo=_logo_b64(), aluno=_esc(rotina["aluno"]), tabs=tabs, treinos=treinos)


def gerar_html_de_sessoes(sessoes, aluno_nome, nomes_treinos=None, catalogo=None):
    """Atalho: rotina viva (sessões serializadas) → HTML."""
    return gerar_html(rotina_de_sessoes(sessoes, aluno_nome, nomes_treinos), catalogo)


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BF Treinamento — Seu treino</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'DM Sans',-apple-system,sans-serif; background:#f9fafb; color:#111827; min-height:100vh; }}
  .topbar {{ background:#fff; border-bottom:1px solid #f3f4f6; padding:.55rem 1rem;
             display:flex; align-items:center; justify-content:space-between; gap:8px;
             position:sticky; top:0; z-index:6; }}
  .topbar-left {{ display:flex; align-items:center; gap:8px; }}
  .topbar-left img {{ height:26px; }}
  .app-name {{ font-size:.8rem; font-weight:700; }}
  .student {{ font-size:.8rem; font-weight:600; }}
  .tabs {{ position:sticky; top:42px; z-index:5; background:#f9fafb; display:flex; gap:6px;
           padding:.6rem .75rem; max-width:520px; margin:0 auto; flex-wrap:wrap; }}
  .tab {{ flex:1; min-width:84px; background:#fff; border:1px solid #e5e7eb; color:#6b7280; border-radius:9px;
          padding:.5rem; font:inherit; font-size:.8rem; font-weight:600; cursor:pointer; transition:.15s; }}
  .tab.active {{ background:#e85d04; border-color:#e85d04; color:#fff; }}
  .content {{ padding:0 .75rem 1rem; max-width:520px; margin:0 auto; }}
  .treino {{ display:none; }}
  .treino.active {{ display:block; }}
  .group {{ background:#fff; border-radius:14px; margin-bottom:.7rem; overflow:hidden; border:1px solid #f3f4f6; }}
  .group-label {{ background:#fff7ed; color:#e85d04; border-bottom:1px solid #fed7aa;
                  padding:.4rem 1rem; font-size:.63rem; font-weight:700;
                  letter-spacing:.09em; text-transform:uppercase; }}
  .ex-item + .ex-item {{ border-top:1px solid #f9fafb; }}
  .ex-row {{ display:flex; align-items:center; padding:.65rem 1rem; gap:8px; }}
  .ex-info {{ display:flex; align-items:center; gap:8px; flex:1; min-width:0; }}
  .ex-num {{ color:#059669; font-size:.63rem; font-weight:700; flex-shrink:0; min-width:18px; }}
  .ex-nome {{ font-size:.9rem; font-weight:500; line-height:1.3; }}
  .ex-actions {{ display:flex; align-items:center; gap:6px; flex-shrink:0; }}
  .badge {{ background:#dcfce7; color:#166534; border-radius:6px; padding:0 8px; height:28px;
            font-size:.63rem; font-weight:700; white-space:nowrap; display:flex; align-items:center; }}
  .btn-slot {{ width:56px; flex-shrink:0; display:flex; align-items:center; justify-content:flex-end; }}
  .ver-btn {{ display:flex; align-items:center; justify-content:center; gap:4px; width:100%; height:28px;
              background:#e85d04; color:#fff; border:none; border-radius:7px; padding:0 10px;
              font-size:.68rem; font-weight:600; cursor:pointer; transition:background .15s; }}
  .ver-btn:hover {{ background:#c2410c; }}
  .ver-btn.open {{ background:#6b7280; }}
  .ver-btn svg {{ width:10px; height:10px; fill:#fff; display:block; }}
  .media-wrap {{ max-height:0; overflow:hidden; transition:max-height .35s ease; }}
  .media-wrap.open {{ max-height:760px; }}
  .media-video {{ background:#000; }}
  .video-aspect {{ position:relative; width:100%; padding-bottom:177.78%; }}
  .video-aspect iframe {{ position:absolute; top:0; left:0; width:100%; height:100%; border:none; }}
  .media-img {{ background:#fff; border-top:1px solid #f3f4f6; padding:14px; display:flex; justify-content:center; }}
  .media-img img {{ width:100%; max-width:300px; height:260px; object-fit:contain; }}
  .footer {{ text-align:center; padding:1.4rem 1rem 2.4rem; font-size:.65rem; color:#9ca3af; }}
</style>
</head>
<body>
  <div class="topbar">
    <div class="topbar-left"><img src="data:image/png;base64,{logo}" alt="BF"><span class="app-name">BF Treinamento</span></div>
    <span class="student">{aluno}</span>
  </div>
  <div class="tabs">{tabs}</div>
  <div class="content">
    {treinos}
    <div class="footer">BF Treinamento · Toque em "Ver" para a demonstração</div>
  </div>
<script>
  let frame = 0;
  setInterval(() => {{
    frame = 1 - frame;
    document.querySelectorAll(".media-wrap.open .media-img img").forEach(img => {{
      const t = frame ? img.dataset.b : img.dataset.a;
      if (t && img.src !== t) img.src = t;
    }});
  }}, 900);
  function fecharTodos() {{
    document.querySelectorAll(".media-wrap.open").forEach(w => {{
      w.classList.remove("open");
      const ifr = w.querySelector("iframe");
      if (ifr) ifr.src = "";
      const b = w.closest(".ex-item").querySelector(".ver-btn");
      if (b) {{ b.classList.remove("open"); b.querySelector(".btn-text").textContent = "Ver"; }}
    }});
  }}
  function toggleMedia(btn) {{
    const item = btn.closest(".ex-item");
    const wrap = item.querySelector(".media-wrap");
    const isOpen = wrap.classList.contains("open");
    fecharTodos();
    if (!isOpen) {{
      const ifr = wrap.querySelector("iframe");
      if (ifr) ifr.src = "https://www.youtube.com/embed/" + ifr.dataset.yt + "?autoplay=1&rel=0";
      const img = wrap.querySelector(".media-img img");
      if (img && !img.src) img.src = img.dataset.a;
      wrap.classList.add("open");
      btn.classList.add("open");
      btn.querySelector(".btn-text").textContent = "Fechar";
      setTimeout(() => item.scrollIntoView({{behavior:"smooth", block:"nearest"}}), 150);
    }}
  }}
  function showTreino(i) {{
    fecharTodos();
    document.querySelectorAll(".treino").forEach(s => s.classList.toggle("active", +s.dataset.treino === i));
    document.querySelectorAll(".tab").forEach((t, j) => t.classList.toggle("active", j === i));
    window.scrollTo({{top:0, behavior:"smooth"}});
  }}
</script>
</body>
</html>
"""
