"""Gera tools/curadoria_links.md — tabela mobile-friendly com link de busca
YouTube por exercício, para curadoria pelo celular. Lê o array DADOS embutido
em tools/curadoria_video.html para manter os nomes idênticos."""
import json
import re
import urllib.parse
from pathlib import Path

AQUI = Path(__file__).resolve().parent
HTML = AQUI / "curadoria_video.html"
SAIDA = AQUI / "curadoria_links.md"

txt = HTML.read_text(encoding="utf-8")
m = re.search(r"const DADOS = (\[.*?\]);", txt, re.S)
DADOS = json.loads(m.group(1))

# Tradução opcional pra melhorar a busca (só onde o termo EN ajuda muito).
EN = {
    "Copenhagen Adduction": "copenhagen adduction",
    "Dead Bug": "dead bug",
    "Hollow Hold": "hollow hold",
    "Hip Thrust": "hip thrust",
    "Good Morning": "good morning",
    "Nordic Curl": "nordic curl",
    "Pallof Press": "pallof press",
    "Box Jump": "box jump",
    "Step Up": "step up",
    "Walking Lunges": "walking lunges",
    "Russian Twist": "russian twist",
    "V-Up": "v-up",
    "Side Clams": "side lying clamshell",
    "Face Pull (Polia)": "face pull cable",
    "Kickback Polia": "cable glute kickback",
    "Pullover Polia": "cable pullover",
    "Crossover": "cable crossover chest",
    "Leg Press": "leg press",
}

def link_busca(nome):
    base = EN.get(nome, nome)
    query = f"{base} exercício execução shorts" if nome not in EN else f"{base} exercise form shorts"
    return "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)

# Agrupa por subregião na ordem de aparição.
ordem, grupos = [], {}
for ex in DADOS:
    sub = ex["subregiao"]
    if sub not in grupos:
        grupos[sub] = []
        ordem.append(sub)
    grupos[sub].append(ex)

linhas = []
linhas.append("# ▶ Curadoria de vídeos — links de busca\n")
linhas.append(f"**{len(DADOS)} exercícios.** Toque em **buscar** → assista um short → copie o link → "
              "cole na ferramenta de curadoria (`curadoria_video.html`).\n")
linhas.append("> Dica: a busca já vem com filtro pra *shorts*. Escolha um de ~10-20s, "
              "câmera fixa, execução limpa.\n")

# Índice
linhas.append("## Índice\n")
for sub in ordem:
    anchor = sub.replace("_", "-")
    linhas.append(f"- [{sub}](#{anchor}) ({len(grupos[sub])})")
linhas.append("")

for sub in ordem:
    linhas.append(f"\n## {sub}\n")
    linhas.append("| Exercício | Equip. | Img | Buscar |")
    linhas.append("|---|---|:-:|:-:|")
    for ex in grupos[sub]:
        img = "✅" if ex["tem_imagem"] else "⚠️"
        eq = ex["eq"].strip() or "—"
        linhas.append(f"| {ex['nome'].strip()} | {eq} | {img} | [▶ buscar]({link_busca(ex['nome'])}) |")

SAIDA.write_text("\n".join(linhas) + "\n", encoding="utf-8")
print(f"OK: {SAIDA} ({len(DADOS)} exercícios, {len(ordem)} grupos)")
