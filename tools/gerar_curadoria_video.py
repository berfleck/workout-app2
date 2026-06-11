# -*- coding: utf-8 -*-
"""Gera ferramenta HTML de curadoria de links YouTube por exercício.

Saída: tools/curadoria_video.html (abre no browser, sem servidor).
UX: campo de URL por exercício, preview embedded, auto-save localStorage,
export JSON {nome: youtube_id} → salvar como tools/escolhas_youtube.json
e rodar tools/merge_youtube_catalogo.py pra incorporar ao catálogo.

Abrange todos os 148 exercícios do banco (não só os 97 com imagem).
"""
import json
import os
import sys
import webbrowser

import openpyxl

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANCO = os.path.join(RAIZ, "banco_exercicios.xlsx")
CATALOGO = os.path.join(RAIZ, "midia_exercicios.json")
SAIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "curadoria_video.html")
ESCOLHAS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "escolhas_youtube.json")


def _carregar_banco():
    wb = openpyxl.load_workbook(BANCO, read_only=True)
    ws = wb["Exercícios"]
    headers = [c.value for c in next(ws.rows)]
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0]:
            d = {headers[i]: row[i] for i in range(len(headers))}
            rows.append(d)
    return rows


def _carregar_catalogo():
    if os.path.exists(CATALOGO):
        with open(CATALOGO, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _carregar_escolhas_existentes():
    """Carrega escolhas_youtube.json se existir (pré-preenche a ferramenta)."""
    if os.path.exists(ESCOLHAS_JSON):
        with open(ESCOLHAS_JSON, encoding="utf-8") as f:
            return json.load(f)
    return {}


def gerar(saida=SAIDA):
    banco = _carregar_banco()
    catalogo = _carregar_catalogo()
    escolhas_existentes = _carregar_escolhas_existentes()

    exercicios = []
    for ex in banco:
        nome = ex["nome"] or ""
        m = catalogo.get(nome.strip()) or catalogo.get(nome)
        tem_imagem = bool(m and m.get("img0"))
        youtube_atual = (m.get("youtube") if m else None) or escolhas_existentes.get(nome)
        exercicios.append({
            "nome": nome,
            "padrao": ex.get("padrao") or "",
            "subregiao": ex.get("subregiao") or "",
            "eq": ex.get("eq_primario") or "",
            "tem_imagem": tem_imagem,
            "youtube": youtube_atual or "",
        })

    dados_js = json.dumps(exercicios, ensure_ascii=False)

    html = _TEMPLATE.replace("__DADOS__", dados_js)
    with open(saida, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Gerado: {saida}")
    print(f"  {len(exercicios)} exercícios listados")
    com_yt = sum(1 for e in exercicios if e["youtube"])
    print(f"  {com_yt} já têm YouTube cadastrado")
    sem_img = sum(1 for e in exercicios if not e["tem_imagem"])
    print(f"  {sem_img} sem imagem (precisam de vídeo mais)")
    webbrowser.open(saida)


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Curadoria de vídeo — BF Treinamento</title>
<style>
  :root { --laranja:#e85d04; --bg:#f9fafb; }
  * { box-sizing:border-box; }
  body { font-family:"DM Sans",system-ui,Arial,sans-serif; margin:0; background:var(--bg); color:#1f2937; }
  header { position:sticky; top:0; z-index:10; background:#fff; border-bottom:2px solid var(--laranja);
           padding:12px 20px; display:flex; align-items:center; gap:16px; flex-wrap:wrap;
           box-shadow:0 1px 4px rgba(0,0,0,.06); }
  header h1 { font-size:18px; margin:0; color:var(--laranja); }
  .prog { font-weight:600; white-space:nowrap; }
  .prog b { color:var(--laranja); }
  button { font:inherit; padding:8px 14px; border-radius:8px; border:1px solid #d1d5db;
           background:#fff; cursor:pointer; }
  button.primary { background:var(--laranja); color:#fff; border-color:var(--laranja); font-weight:600; }
  select { font:inherit; padding:8px 12px; border-radius:8px; border:1px solid #d1d5db; background:#fff; cursor:pointer; }
  main { max-width:860px; margin:0 auto; padding:20px; }
  .ex { background:#fff; border-radius:12px; padding:16px 18px; margin-bottom:14px;
        box-shadow:0 1px 3px rgba(0,0,0,.08); transition:.15s; }
  .ex.tem-video { border-left:3px solid #16a34a; }
  .ex.sem-imagem { border-left:3px solid #e85d04; }
  .ex.tem-video.sem-imagem { border-left:3px solid #d97706; }
  .ex-head { display:flex; align-items:baseline; gap:10px; flex-wrap:wrap; margin-bottom:10px; }
  .ex-head h2 { font-size:16px; margin:0; }
  .meta { font-size:12px; color:#6b7280; }
  .badges { display:flex; gap:6px; align-items:center; flex-wrap:wrap; margin-left:auto; }
  .badge { font-size:10px; font-weight:700; padding:2px 8px; border-radius:99px; }
  .badge-img { background:#dcfce7; color:#166534; }
  .badge-noimg { background:#fee2e2; color:#991b1b; }
  .badge-yt { background:#dcfce7; color:#166534; }
  .url-row { display:flex; gap:8px; align-items:center; }
  .url-input { flex:1; padding:10px 12px; border:1.5px solid #d1d5db; border-radius:8px;
               font:inherit; font-size:14px; transition:.15s; }
  .url-input:focus { outline:none; border-color:var(--laranja); }
  .url-input.ok { border-color:#16a34a; background:#f0fdf4; }
  .url-input.erro { border-color:#dc2626; background:#fef2f2; }
  .btn-limpar { padding:10px 12px; color:#6b7280; font-size:12px; white-space:nowrap; }
  .preview-wrap { margin-top:12px; display:none; }
  .preview-wrap.open { display:block; }
  .video-container { position:relative; width:100%; max-width:340px;
                     padding-bottom:calc(177.78% * 340px / 100%); }
  .yt-preview { width:100%; max-width:340px; aspect-ratio:9/16;
                border-radius:10px; border:none; display:block; }
  .id-chip { display:inline-block; margin-top:6px; font-size:11px; font-weight:700;
             color:#6b7280; background:#f3f4f6; padding:2px 10px; border-radius:99px; }
  .filtros { margin-left:auto; display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
  .hint { font-size:12px; color:#6b7280; width:100%; }
</style>
</head>
<body>
<header>
  <h1>▶ Curadoria de vídeo YouTube</h1>
  <span class="prog">Com vídeo: <b id="cnt">0</b> / <span id="tot">0</span></span>
  <div class="filtros">
    <select id="filtro" onchange="render()">
      <option value="todos">Mostrar todos</option>
      <option value="pendentes">Só sem vídeo</option>
      <option value="sem_imagem">Prioridade: sem imagem</option>
      <option value="com_video">Só com vídeo</option>
    </select>
    <button class="primary" id="baixar" onclick="baixar()">⬇ Baixar JSON</button>
  </div>
  <div class="hint">
    Cole o link do YouTube em qualquer formato (<b>watch?v=</b>, <b>youtu.be/</b>, <b>/shorts/</b>).
    O ID é extraído automaticamente e o vídeo aparece embedded. Salva automático.
    Ao terminar, clique <b>⬇ Baixar JSON</b> e salve como <code>tools/escolhas_youtube.json</code>.
    Depois rode <code>python tools/merge_youtube_catalogo.py</code> para atualizar o catálogo.
  </div>
</header>
<main id="lista"></main>

<script>
const DADOS = __DADOS__;
const LS = "curadoria_video_v1";
let escolhas = JSON.parse(localStorage.getItem(LS) || "{}");

// Pré-preencher com dados já no catálogo (campo "youtube" dos exercicios)
DADOS.forEach(ex => {
  if (ex.youtube && !escolhas[ex.nome]) {
    escolhas[ex.nome] = ex.youtube;
  }
});

function salvar() {
  localStorage.setItem(LS, JSON.stringify(escolhas));
  render();
}

function extrairId(url) {
  url = url.trim();
  if (!url) return "";
  // ID direto (11 chars alfanum + hífen/underscore)
  if (/^[A-Za-z0-9_-]{11}$/.test(url)) return url;
  // watch?v=
  let m = url.match(/[?&]v=([A-Za-z0-9_-]{11})/);
  if (m) return m[1];
  // youtu.be/ID
  m = url.match(/youtu\.be\/([A-Za-z0-9_-]{11})/);
  if (m) return m[1];
  // /shorts/ID ou /embed/ID
  m = url.match(/\/(?:shorts|embed)\/([A-Za-z0-9_-]{11})/);
  if (m) return m[1];
  return "";
}

function onInput(nome, input) {
  const id = extrairId(input.value);
  if (id) {
    input.classList.add("ok"); input.classList.remove("erro");
    escolhas[nome] = id;
  } else if (input.value.trim()) {
    input.classList.add("erro"); input.classList.remove("ok");
    delete escolhas[nome];
  } else {
    input.classList.remove("ok", "erro");
    delete escolhas[nome];
  }
  salvar();
  // Atualiza preview inline sem re-render total
  atualizarPreview(nome, id);
}

function atualizarPreview(nome, id) {
  const wrap = document.getElementById("prev_" + CSS.escape(nome));
  if (!wrap) return;
  if (id) {
    wrap.classList.add("open");
    let ifr = wrap.querySelector("iframe");
    const chip = wrap.querySelector(".id-chip");
    if (ifr) ifr.src = "https://www.youtube.com/embed/" + id + "?rel=0";
    if (chip) chip.textContent = "ID: " + id;
  } else {
    wrap.classList.remove("open");
    const ifr = wrap.querySelector("iframe");
    if (ifr) ifr.src = "";
  }
}

function limpar(nome) {
  delete escolhas[nome];
  salvar();
}

function render() {
  const lista = document.getElementById("lista");
  const filtro = document.getElementById("filtro").value;
  lista.innerHTML = "";
  let comVideo = 0;
  DADOS.forEach((ex, i) => {
    const id = escolhas[ex.nome] || "";
    if (id) comVideo++;
    if (filtro === "pendentes" && id) return;
    if (filtro === "sem_imagem" && ex.tem_imagem) return;
    if (filtro === "com_video" && !id) return;

    let classes = "ex";
    if (id) classes += " tem-video";
    if (!ex.tem_imagem) classes += " sem-imagem";

    const badgeImg = ex.tem_imagem
      ? '<span class="badge badge-img">📸 Imagem</span>'
      : '<span class="badge badge-noimg">Sem imagem</span>';
    const badgeYt = id ? '<span class="badge badge-yt">▶ Vídeo ✓</span>' : "";

    const iframeHtml = id
      ? `<iframe class="yt-preview" src="https://www.youtube.com/embed/${id}?rel=0" allow="encrypted-media" allowfullscreen></iframe><div class="id-chip">ID: ${id}</div>`
      : `<iframe class="yt-preview" src="" allow="encrypted-media" allowfullscreen></iframe><div class="id-chip"></div>`;

    const card = document.createElement("div");
    card.className = classes;
    card.innerHTML = `
      <div class="ex-head">
        <h2>${esc(ex.nome)}</h2>
        <span class="meta">${esc(ex.padrao)} · ${esc(ex.eq)}</span>
        <div class="badges">${badgeImg}${badgeYt}</div>
      </div>
      <div class="url-row">
        <input class="url-input${id ? ' ok' : ''}" type="text" placeholder="Cole o link do YouTube aqui..."
               value="${id ? 'https://youtu.be/' + id : ''}"
               oninput="onInput('${esc(ex.nome)}', this)"
               onpaste="setTimeout(()=>onInput('${esc(ex.nome)}',this),50)">
        <button class="btn-limpar" onclick="limpar('${esc(ex.nome)}')">✕ Limpar</button>
      </div>
      <div class="preview-wrap${id ? ' open' : ''}" id="prev_${CSS_ID(ex.nome)}">${iframeHtml}</div>`;
    lista.appendChild(card);
  });
  document.getElementById("cnt").textContent = comVideo;
  document.getElementById("tot").textContent = DADOS.length;
}

function CSS_ID(nome) { return nome.replace(/[^a-zA-Z0-9]/g, "_"); }

function esc(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");
}

function baixar() {
  const saida = {};
  Object.entries(escolhas).forEach(([k,v]) => { if(v) saida[k] = v; });
  const blob = new Blob([JSON.stringify(saida, null, 2)], {type:"application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "escolhas_youtube.json";
  a.click();
}

render();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    saida = SAIDA
    if len(sys.argv) > 1:
        saida = sys.argv[1]
    gerar(saida)
