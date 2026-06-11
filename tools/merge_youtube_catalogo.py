# -*- coding: utf-8 -*-
"""Merge de escolhas de YouTube no catálogo midia_exercicios.json.

Uso:
    python tools/merge_youtube_catalogo.py [tools/escolhas_youtube.json]

Lê tools/escolhas_youtube.json (output da ferramenta de curadoria),
adiciona/atualiza o campo `youtube` em midia_exercicios.json SEM perder
imagens existentes. Exercícios ainda não no catálogo são adicionados só
com o campo `youtube` (sem imagem).

Para remover um YouTube de um exercício, exclua a entrada do JSON de escolhas
e rode este script novamente com --limpar (remove entradas com youtube="" ou null).
"""
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOGO_PATH = os.path.join(RAIZ, "midia_exercicios.json")
ESCOLHAS_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "escolhas_youtube.json")


def merge(escolhas_path=ESCOLHAS_DEFAULT, limpar=False):
    if not os.path.exists(escolhas_path):
        print(f"Arquivo não encontrado: {escolhas_path}")
        sys.exit(1)

    with open(escolhas_path, encoding="utf-8") as f:
        escolhas = json.load(f)  # {nome: youtube_id}

    catalogo = {}
    if os.path.exists(CATALOGO_PATH):
        with open(CATALOGO_PATH, encoding="utf-8") as f:
            catalogo = json.load(f)

    adicionados, atualizados, removidos, sem_mudanca = 0, 0, 0, 0

    # Aplicar escolhas
    for nome, yt_id in escolhas.items():
        if not yt_id:
            continue
        nome_key = nome.strip()
        # Procurar chave com ou sem espaço
        chave = nome_key if nome_key in catalogo else (nome if nome in catalogo else None)
        if chave is None:
            catalogo[nome_key] = {"youtube": yt_id}
            adicionados += 1
        else:
            anterior = catalogo[chave].get("youtube")
            if anterior != yt_id:
                catalogo[chave]["youtube"] = yt_id
                if anterior:
                    atualizados += 1
                else:
                    adicionados += 1
            else:
                sem_mudanca += 1

    # Limpar entradas youtube vazia/null do catálogo (quando flag --limpar)
    if limpar:
        for chave in list(catalogo.keys()):
            entry = catalogo[chave]
            if "youtube" in entry and not entry["youtube"]:
                del entry["youtube"]
                removidos += 1

    with open(CATALOGO_PATH, "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)

    print(f"midia_exercicios.json atualizado:")
    print(f"  {adicionados} youtube(s) adicionados")
    print(f"  {atualizados} youtube(s) atualizados")
    if removidos:
        print(f"  {removidos} youtube(s) removidos (--limpar)")
    print(f"  {sem_mudanca} sem mudança")
    print(f"  Total no catálogo: {len(catalogo)} exercícios")

    com_yt = sum(1 for v in catalogo.values() if v.get("youtube"))
    com_img = sum(1 for v in catalogo.values() if v.get("img0"))
    print(f"  Com imagem: {com_img} | Com YouTube: {com_yt}")


if __name__ == "__main__":
    path = ESCOLHAS_DEFAULT
    do_limpar = "--limpar" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        path = args[0]
    merge(path, limpar=do_limpar)
