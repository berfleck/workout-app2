# -*- coding: utf-8 -*-
"""Mockup da PÁGINA DO ALUNO — apenas dados de exemplo.

O template/lógica vivem em `pagina_aluno.py` (fonte de verdade). Este script só
monta uma rotina de exemplo (com vídeo YouTube DEMO + imagem + sem-mídia) e gera
`mockup_pagina_aluno.html` pra validação visual.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pagina_aluno  # noqa: E402

# rotina no formato normalizado de pagina_aluno.gerar_html.
# 'yt' = youtube id (DEMO p/ mostrar vídeo embedded). Sem yt -> tenta imagem do
# catálogo. Sem imagem -> sem botão.
ROTINA = {
    "aluno": "Luciano Paludo",
    "treinos": [
        {"nome": "Treino A", "blocos": [
            {"label": "A", "exs": [
                {"nome": "Agachamento Livre", "presc": "4×8-10 · RIR 2", "yt": "Zc4CNHExc0A"},
                {"nome": "Prancha", "presc": "3×30-45s", "yt": None}]},
            {"label": "B", "exs": [
                {"nome": "Supino Com Halteres", "presc": "4×10-12 · RIR 2", "yt": None},
                {"nome": "Crunch Chão", "presc": "3×15", "yt": None}]},
            {"label": "C", "exs": [
                {"nome": "Remada Curvada Halteres", "presc": "3×10-12 · RIR 2", "yt": None},
                {"nome": "Side Clams", "presc": "3×10", "yt": None}]},
        ]},
        {"nome": "Treino B", "blocos": [
            {"label": "A", "exs": [
                {"nome": "Stiff Halteres", "presc": "4×8-10 · RIR 2", "yt": None},
                {"nome": "Desenvolvimento Barra", "presc": "3×8-10 · RIR 2", "yt": "s_8PheAKUYk"}]},
            {"label": "B", "exs": [
                {"nome": "Puxada Aberta", "presc": "3×10-12", "yt": None},
                {"nome": "Bíceps Halteres", "presc": "3×12-15 · RIR 1", "yt": None}]},
            {"label": "C", "exs": [
                {"nome": "Elevação Lateral ", "presc": "3×12-15", "yt": None},
                {"nome": "Hollow Hold", "presc": "3×20-30s", "yt": None}]},
        ]},
    ],
}


def main():
    html = pagina_aluno.gerar_html(ROTINA)
    saida = os.path.join(pagina_aluno._RAIZ, "mockup_pagina_aluno.html")
    with open(saida, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Gerado: {saida}")


if __name__ == "__main__":
    main()
