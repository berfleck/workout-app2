"""Recalibra HIB2 sobre a base pós-Etapas 2 e 3.

Gera 20 casos clínicos com filtro OFF (estado atual do motor) e simula em
pós-hoc o efeito de HIB (6/5/5) e HIB2 (6/5/6) sobre os pares dentro de
cada bloco. NÃO regera blocos — apenas anota quais pares seriam bloqueados
se o filtro estivesse ligado. Saída em
docs/refatoracao/logs/casos_clinicos_hib2_pos_etapa3.md.

O personal trainer revisa o md case-a-case e decide:
  (A) HIB2 6/5/6 continua justificado → manter defaults
  (B) Algum bloqueio é clinicamente questionável → ajustar threshold
  (C) Falta cobertura (par perigoso passando) → apertar thresholds

Uso: `python tools/recalibrar_cargas_hib2.py`
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gerador_treino import (  # noqa: E402
    _bloqueio_cargas,
    carregar_banco,
    gerar_multiplos_treinos,
)

XLSX = ROOT / "banco_exercicios.xlsx"
OUT = ROOT / "docs" / "refatoracao" / "logs" / "casos_clinicos_hib2_pos_etapa3.md"

# 20 seeds para cobrir variação no sorteio. Ímpares + alguns redondos.
SEEDS = [
    1, 7, 13, 23, 42, 99, 100, 117, 200, 314,
    555, 777, 1000, 1234, 1492, 1789, 1984, 2024, 4096, 9999,
]

# Config representativo: split B "Full body focado inferior", 2 treinos, bloco=2.
# Replica a configuração que originou a calibração HIB2 no contexto histórico.
CFG_BASE = {
    "demandas": [("regiao", "lower", 4), ("regiao", "upper", 3), ("regiao", "core", 1)],
    "tamanho_bloco": 2,
    "max_complexidade": 5,
    "equipamentos_bloqueados": [],
    "evitar_agonistas": True,
}

THR_HIB = {"grip": 6, "lombar": 5, "core": 5}
THR_HIB2 = {"grip": 6, "lombar": 5, "core": 6}

# Mapa dimensão → atributo (espelha _DIMS_CARGA do gerador, sem importar privado).
DIMS = (("grip", "carga_grip"), ("lombar", "carga_lombar"), ("core", "demanda_core"))


def _motivo(a, b, thr):
    """Retorna lista de tuplas (dim, soma, threshold) das dimensões violadas."""
    motivos = []
    for dim, attr in DIMS:
        t = thr.get(dim)
        if not t:
            continue
        va, vb = getattr(a, attr, 0), getattr(b, attr, 0)
        if va >= 1 and vb >= 1 and (va + vb) >= t:
            motivos.append((dim, va + vb, t))
    return motivos


def _fmt_motivo(motivos):
    if not motivos:
        return "livre"
    return "; ".join(f"{dim}={soma}≥{thr}" for dim, soma, thr in motivos)


def _gerar_caso(banco, seed, cfg):
    random.seed(seed)
    sessoes = gerar_multiplos_treinos(banco, [cfg, cfg], relaxar_familia=True)
    pares = []
    for ti, sessao in enumerate(sessoes):
        for bloco in sessao.blocos:
            ex_list = [e for e in (bloco.ex1, bloco.ex2, bloco.ex3) if e is not None]
            if len(ex_list) < 2:
                continue
            for i in range(len(ex_list)):
                for j in range(i + 1, len(ex_list)):
                    a, b = ex_list[i], ex_list[j]
                    pares.append({
                        "treino": ti + 1,
                        "bloco": bloco.label,
                        "par": (a.nome, b.nome),
                        "hib": _motivo(a, b, THR_HIB),
                        "hib2": _motivo(a, b, THR_HIB2),
                        # Para depuração: cargas dos dois exercícios.
                        "cargas_a": (a.carga_grip, a.carga_lombar, a.demanda_core),
                        "cargas_b": (b.carga_grip, b.carga_lombar, b.demanda_core),
                    })
    return sessoes, pares


def main():
    banco = carregar_banco(str(XLSX))
    OUT.parent.mkdir(parents=True, exist_ok=True)

    detalhes = []
    for seed in SEEDS:
        sessoes, pares = _gerar_caso(banco, seed, CFG_BASE)
        detalhes.append((seed, sessoes, pares))

    # Agregados
    n_pares = sum(len(p) for _, _, p in detalhes)
    blq_hib = sum(1 for _, _, p in detalhes for x in p if x["hib"])
    blq_hib2 = sum(1 for _, _, p in detalhes for x in p if x["hib2"])
    repermitidos = sum(
        1 for _, _, p in detalhes for x in p if x["hib"] and not x["hib2"]
    )
    persistentes = sum(1 for _, _, p in detalhes for x in p if x["hib2"])
    so_hib2 = sum(
        1 for _, _, p in detalhes for x in p if x["hib2"] and not x["hib"]
    )

    # Agrupar pares persistentes (bloqueados em HIB2) por par exclusivo
    par_persist_freq: dict[tuple[str, str], int] = {}
    for _, _, pares in detalhes:
        for x in pares:
            if not x["hib2"]:
                continue
            key = tuple(sorted(x["par"]))
            par_persist_freq[key] = par_persist_freq.get(key, 0) + 1

    par_repermit_freq: dict[tuple[str, str], int] = {}
    for _, _, pares in detalhes:
        for x in pares:
            if x["hib"] and not x["hib2"]:
                key = tuple(sorted(x["par"]))
                par_repermit_freq[key] = par_repermit_freq.get(key, 0) + 1

    lines = [
        "# Casos clínicos HIB2 — recalibração pós-Etapa 3",
        "",
        "Gerado por `tools/recalibrar_cargas_hib2.py`. Base: branch `refator-gerador`",
        "pós-Etapa 3 (âncoras protegidas em região e subregião).",
        "",
        "**Cada caso:** 1 seed × cfg `lower(4) + upper(3) + core(1)` × 2 treinos × bloco=2.",
        "**OFF** = sem filtro (estado atual do motor pós-Etapa 3).",
        "**HIB** = thresholds 6/5/5 (lombar=5, core=5).",
        "**HIB2** = thresholds 6/5/6 (lombar=5, core=6 — calibração escolhida).",
        "",
        "Modos HIB e HIB2 são **simulações pós-hoc** sobre os blocos OFF — a",
        "geração não muda. Cada par dentro de um bloco é avaliado contra os",
        "thresholds e marcado como bloqueado se a soma >= threshold E ambos têm",
        "valor >= 1 na dimensão.",
        "",
        "## Agregado",
        "",
        f"- Pares avaliados: **{n_pares}**",
        f"- Bloqueados em HIB: **{blq_hib}**",
        f"- Bloqueados em HIB2: **{blq_hib2}**",
        f"- Repermitidos HIB→HIB2 (eram bloqueados, agora passam): **{repermitidos}**",
        f"- Persistentes (bloqueados em ambos): **{persistentes}**",
        f"- Só em HIB2 (sentinela de inconsistência — esperado 0): **{so_hib2}**",
        "",
        "### Pares persistentes em HIB2 (top 10 por frequência)",
        "",
        "Estes são os pares que o filtro HIB2 mais bloqueia. Devem ser",
        "clinicamente justificados (lombar ou grip pesados juntos).",
        "",
    ]
    if par_persist_freq:
        top_persist = sorted(par_persist_freq.items(), key=lambda kv: -kv[1])[:10]
        lines.append("| # | Par | Frequência |")
        lines.append("|---|-----|-----------:|")
        for i, ((a, b), n) in enumerate(top_persist, 1):
            lines.append(f"| {i} | `{a}` + `{b}` | {n} |")
        lines.append("")
    else:
        lines.append("_Nenhum par bloqueado em HIB2._")
        lines.append("")

    lines.append("### Pares repermitidos HIB→HIB2 (top 10 por frequência)")
    lines.append("")
    lines.append(
        "Pares que HIB bloqueava mas HIB2 deixa passar (relaxamento do core 5→6)."
    )
    lines.append("Validar caso-a-caso: continua sendo seguro permitir?")
    lines.append("")
    if par_repermit_freq:
        top_rep = sorted(par_repermit_freq.items(), key=lambda kv: -kv[1])[:10]
        lines.append("| # | Par | Frequência |")
        lines.append("|---|-----|-----------:|")
        for i, ((a, b), n) in enumerate(top_rep, 1):
            lines.append(f"| {i} | `{a}` + `{b}` | {n} |")
        lines.append("")
    else:
        lines.append("_Nenhum par foi repermitido._")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Casos individuais")
    lines.append("")

    for seed, sessoes, pares in detalhes:
        lines.append(f"### seed={seed}")
        lines.append("")
        for ti, sessao in enumerate(sessoes):
            lines.append(f"**Treino {ti + 1}** ({sessao.tipo})")
            lines.append("")
            for bloco in sessao.blocos:
                exs = [e.nome for e in (bloco.ex1, bloco.ex2, bloco.ex3) if e is not None]
                lines.append(f"- **{bloco.label}**: {' + '.join(exs) if exs else '(vazio)'}")
            lines.append("")
        relevantes = [c for c in pares if c["hib"] or c["hib2"]]
        if relevantes:
            lines.append("**Pares com bloqueio simulado:**")
            lines.append("")
            for c in relevantes:
                a, b = c["par"]
                lines.append(
                    f"- T{c['treino']} {c['bloco']}: "
                    f"`{a}` (g={c['cargas_a'][0]} l={c['cargas_a'][1]} c={c['cargas_a'][2]}) + "
                    f"`{b}` (g={c['cargas_b'][0]} l={c['cargas_b'][1]} c={c['cargas_b'][2]}) "
                    f"— HIB: {_fmt_motivo(c['hib'])}; HIB2: {_fmt_motivo(c['hib2'])}"
                )
            lines.append("")
        else:
            lines.append("_Nenhum par bloqueado em HIB ou HIB2._")
            lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Escrito: {OUT}")
    print(
        f"Pares: {n_pares} | HIB: {blq_hib} | HIB2: {blq_hib2} | "
        f"repermitidos: {repermitidos} | persistentes: {persistentes}"
    )


if __name__ == "__main__":
    main()
