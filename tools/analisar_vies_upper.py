"""Analise estatistica descritiva de vies do gerador — upper(4) x 2 treinos.

Roda N iteracoes da rotina-base e gera relatorio markdown respondendo:
  Q1. Existem exercicios predominantes? (top-N + Gini + entropia)
  Q2. Exercicios que nunca aparecem? (never-seen list + cobertura)
  Q3. Categorias dominantes/sub-representadas? (obs vs esp Hamilton)
  Q4. T1 vs T2 (chi2 de homogeneidade por exercicio + subregiao + purpose)

Plano: ~/.claude/plans/preciso-de-uma-bateria-golden-elephant.md

Uso:
    python tools/analisar_vies_upper.py                 # N=1000, default
    python tools/analisar_vies_upper.py --n-iter 10     # dry-run
    python tools/analisar_vies_upper.py --out ''        # so stdout
"""
from __future__ import annotations

import argparse
import math
import random
import subprocess
import sys
from collections import Counter
from datetime import datetime
from io import StringIO
from pathlib import Path

# Permite rodar de tools/ sem PYTHONPATH manual
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gerador_treino import (  # noqa: E402
    _eh_composto,
    carregar_banco,
    gerar_multiplos_treinos,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

XLSX_PATH = "banco_exercicios.xlsx"
OUT_PATH_DEFAULT = "docs/refatoracao/logs/analise_vies_upper.md"

# Esperados teoricos derivados do Hamilton sobre ANCORAS_POR_REGIAO['upper']
# (peito:2/obrig, costas:2/obrig, ombro:1/obrig). 4 vagas, 8 slots/rotina,
# 2 treinos. Ver plano para derivacao detalhada.
#
# Nivel regiao->subregiao (4 vagas):
#   ideais peito=1.6, costas=1.6, ombro=0.8 -> floors 1,1,0 -> resto 0.6,0.6,0.8
#   sobra 1 vaga -> maior resto = ombro -> ombro=1 inicial
#   re-rodar Hamilton sobre 3 vagas distribui peito=1, costas=1, ombro=1
#   restante: peito e costas empatam em resto 0.6, ombro ja teve 0.8
#   resultado MODAL: peito=2, costas=1, ombro=1 OU peito=1, costas=2, ombro=1
#   dependendo de ordem de tie-break (estavel pela ordem em ANCORAS).
#   Como ordem em ANCORAS_POR_REGIAO['upper'] e peito,costas,ombro -> peito leva.
#   Esperado por treino: peito=2, costas=1, ombro=1, bracos=0.
ESPERADO_SUB_PCT = {
    "peito":  2.0 / 4.0,
    "costas": 1.0 / 4.0,
    "ombro":  1.0 / 4.0,
    "bracos": 0.0,
}

# Nivel subregiao->padrao:
#   peito (2 vagas, comp:3 obrig + iso:2): floors 1,0; resto 0.2,0.8;
#     sobra 1 -> iso ganha -> 1 comp + 1 iso = 25% + 25% do total
#   costas (1 vaga, 2 obrig): vagas < n_obrig -> sorteia 1 entre remadas/puxadas
#     -> esperado 50/50 -> 12.5% cada
#   ombro (1 vaga, comp:3 obrig + iso:2 + posterior:1): comp dominante por peso
#     e obrig -> 1 comp = 25% do total; iso e posterior = 0
ESPERADO_PAD_PCT = {
    "empurrar_compostos": 1.0 / 4.0,
    "empurrar_isolados":  1.0 / 4.0,
    "remadas":            0.5 * (1.0 / 4.0),
    "puxadas":            0.5 * (1.0 / 4.0),
    "ombro_composto":     1.0 / 4.0,
    "ombro_isolado":      0.0,
    "posterior_ombro":    0.0,
    "biceps":             0.0,
    "triceps":            0.0,
}

# Composto vs isolado teorico por treino:
#   peito: 1 comp + 1 iso
#   costas: 1 comp (remadas/puxadas ambos sao 'compound' no banco)
#   ombro: 1 comp (ombro_composto)
#   total: 3 comp + 1 iso = 75% / 25%
# Obs: a diretriz "60% compostos" da PROPORCAO_COMPOSTOS e mais frouxa;
# upper(4) Hamilton naturalmente fica em ~75%.
ESPERADO_PURPOSE_PCT = {"composto": 0.75, "isolado": 0.25}

CHI2_CRIT_005 = 3.84  # df=1, p<0.05


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _exercicios_da_sessao(sessao):
    for b in sessao.blocos:
        for ex in (b.ex1, b.ex2, b.ex3):
            if ex:
                yield ex


def _git_rev() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return out
    except Exception:
        return "unknown"


def _gini(values) -> float:
    xs = sorted(v for v in values if v > 0)
    n = len(xs)
    s = sum(xs)
    if n == 0 or s == 0:
        return 0.0
    cum = 0.0
    for i, v in enumerate(xs, start=1):
        cum += (2 * i - n - 1) * v
    return cum / (n * s)


def _entropia_norm(counter) -> float:
    total = sum(counter.values())
    if total == 0:
        return 0.0
    k = len([v for v in counter.values() if v > 0])
    if k <= 1:
        return 0.0
    h = 0.0
    for v in counter.values():
        if v <= 0:
            continue
        p = v / total
        h -= p * math.log(p)
    return h / math.log(k)


def _chi2_2x2(a: int, b: int, c: int, d: int) -> float:
    """Chi-quadrado de homogeneidade 2x2, df=1, sem correcao de Yates."""
    n = a + b + c + d
    row1, row2 = a + b, c + d
    col1, col2 = a + c, b + d
    if n == 0 or row1 == 0 or row2 == 0 or col1 == 0 or col2 == 0:
        return 0.0
    chi2 = 0.0
    for obs, r, c_ in (
        (a, row1, col1), (b, row1, col2),
        (c, row2, col1), (d, row2, col2),
    ):
        esp = r * c_ / n
        chi2 += (obs - esp) ** 2 / esp
    return chi2


# ---------------------------------------------------------------------------
# Loop de simulacao
# ---------------------------------------------------------------------------

def analisar(banco, n_iter: int, seed_base: int, relaxar_familia: bool, verbose: bool) -> dict:
    upper_exs = [e for e in banco if e.regiao == "upper"]
    assert len(upper_exs) >= 20, f"banco upper muito pequeno: {len(upper_exs)}"
    nomes_upper = {e.nome for e in upper_exs}
    info_por_nome = {e.nome: e for e in upper_exs}

    cnt_pad = Counter(e.padrao for e in upper_exs)
    for pad in ("empurrar_compostos", "empurrar_isolados", "remadas",
                "puxadas", "ombro_composto", "ombro_isolado"):
        assert cnt_pad[pad] >= 2, f"padrao {pad} tem {cnt_pad[pad]} ex (<2)"

    configs = [
        {"demandas": [("regiao", "upper", 4)]},
        {"demandas": [("regiao", "upper", 4)]},
    ]

    freq_rotina: Counter = Counter()
    freq_slot: Counter = Counter()
    freq_por_treino = {0: Counter(), 1: Counter()}
    padrao_por_treino = {0: Counter(), 1: Counter()}
    sub_por_treino = {0: Counter(), 1: Counter()}
    purpose_por_treino = {
        0: {"composto": 0, "isolado": 0},
        1: {"composto": 0, "isolado": 0},
    }
    slots_por_treino = {0: 0, 1: 0}
    n_rotinas_avisos = {"incompleta": 0, "familia_repetida": 0}
    n_rotinas_com_relaxados = 0
    n_sessoes_incompletas = 0

    for i in range(n_iter):
        random.seed(seed_base + i)
        sessoes = gerar_multiplos_treinos(banco, configs, relaxar_familia=relaxar_familia)
        assert len(sessoes) == 2, f"iter {i}: esperava 2 sessoes, vi {len(sessoes)}"

        nomes_na_rotina = set()
        avisos_rotina = []
        relaxados_rotina = []
        for t_idx, sessao in enumerate(sessoes):
            exs = list(_exercicios_da_sessao(sessao))
            slots_por_treino[t_idx] += len(exs)
            if len(exs) < 4:
                n_sessoes_incompletas += 1
            for ex in exs:
                freq_slot[ex.nome] += 1
                nomes_na_rotina.add(ex.nome)
                freq_por_treino[t_idx][ex.nome] += 1
                padrao_por_treino[t_idx][ex.padrao] += 1
                sub_por_treino[t_idx][ex.subregiao] += 1
                key = "composto" if _eh_composto(ex) else "isolado"
                purpose_por_treino[t_idx][key] += 1
            avisos_rotina.extend(sessao.avisos)
            relaxados_rotina.extend(sessao.relaxados)

        for nome in nomes_na_rotina:
            freq_rotina[nome] += 1
        if any(a.get("tipo") == "incompleta" for a in avisos_rotina):
            n_rotinas_avisos["incompleta"] += 1
        if any(a.get("tipo") == "familia_repetida" for a in avisos_rotina):
            n_rotinas_avisos["familia_repetida"] += 1
        if relaxados_rotina:
            n_rotinas_com_relaxados += 1

        if verbose and (i + 1) % 100 == 0:
            print(f"  ...iter {i+1}/{n_iter}", file=sys.stderr)

    return {
        "n_iter": n_iter,
        "seed_base": seed_base,
        "relaxar_familia": relaxar_familia,
        "info_por_nome": info_por_nome,
        "nomes_upper": nomes_upper,
        "freq_rotina": freq_rotina,
        "freq_slot": freq_slot,
        "freq_por_treino": freq_por_treino,
        "padrao_por_treino": padrao_por_treino,
        "sub_por_treino": sub_por_treino,
        "purpose_por_treino": purpose_por_treino,
        "slots_por_treino": slots_por_treino,
        "n_rotinas_avisos": n_rotinas_avisos,
        "n_rotinas_com_relaxados": n_rotinas_com_relaxados,
        "n_sessoes_incompletas": n_sessoes_incompletas,
    }


# ---------------------------------------------------------------------------
# Relatorio
# ---------------------------------------------------------------------------

def gerar_relatorio(res: dict) -> str:
    out = StringIO()

    def p(*args, **kw):
        print(*args, file=out, **kw)

    N = res["n_iter"]
    total_slots = sum(res["slots_por_treino"].values())

    p("# Analise de vies — upper(4) x 2 treinos")
    p()
    p(f"- Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    p(f"- Git: `{_git_rev()}`")
    p(f"- N iteracoes: **{N}** (seeds {res['seed_base']}..{res['seed_base']+N-1})")
    p(f"- relaxar_familia: `{res['relaxar_familia']}` | historico_r1: `None`")
    p(f"- Slots esperados: {N*8} | observados: {total_slots}")
    p()

    warnings = []
    for t in (0, 1):
        media = res["slots_por_treino"][t] / N if N else 0
        if media < 3.95:
            warnings.append(f"T{t+1} media de slots = {media:.2f} < 3.95 (sessoes incompletas)")
    pct_inc = res["n_rotinas_avisos"]["incompleta"] / N if N else 0
    if pct_inc > 0.05:
        warnings.append(f"Taxa aviso `incompleta`: **{pct_inc:.1%}** (> 5%)")
    bracos_t1 = res["sub_por_treino"][0].get("bracos", 0)
    bracos_t2 = res["sub_por_treino"][1].get("bracos", 0)
    if bracos_t1 > 0 or bracos_t2 > 0:
        warnings.append(f"Bracos apareceu (T1={bracos_t1}, T2={bracos_t2}) — Hamilton deveria garantir 0")
    if warnings:
        p("## Sanity warnings")
        for w in warnings:
            p(f"- ⚠️ {w}")
        p()

    # ---- Q1 ----
    p("## Q1 — Exercicios predominantes")
    p()
    top = res["freq_rotina"].most_common(20)
    p(f"Top-20 por numero de rotinas (de {N}) em que o exercicio apareceu pelo menos 1×.")
    p()
    p("| # | Exercicio | Padrao | Subreg | n_rot | % rot | freq_slot |")
    p("|---|---|---|---|---:|---:|---:|")
    for i, (nome, n_rot) in enumerate(top, start=1):
        ex = res["info_por_nome"].get(nome)
        pad = ex.padrao if ex else "?"
        sub = ex.subregiao if ex else "?"
        slots = res["freq_slot"][nome]
        p(f"| {i} | {nome} | {pad} | {sub} | {n_rot} | {n_rot/N:.1%} | {slots} |")
    p()
    gini = _gini(list(res["freq_rotina"].values()))
    ent = _entropia_norm(res["freq_rotina"])
    p(f"**Concentracao:** Gini = `{gini:.3f}` (0=uniforme, 1=concentrado em 1) | "
      f"Entropia normalizada = `{ent:.3f}` (1=uniforme entre exs vistos)")
    p()

    # ---- Q2 ----
    seen = set(res["freq_rotina"].keys())
    never_seen = sorted(res["nomes_upper"] - seen)
    cobertura = len(seen) / len(res["nomes_upper"]) if res["nomes_upper"] else 0
    p(f"## Q2 — Exercicios que nunca apareceram ({len(never_seen)} de {len(res['nomes_upper'])})")
    p()
    p(f"Cobertura: **{cobertura:.1%}** ({len(seen)}/{len(res['nomes_upper'])} exercicios upper vistos)")
    p()
    if never_seen:
        # Agrupar por padrao pra leitura mais facil
        por_padrao_ns = {}
        for nome in never_seen:
            ex = res["info_por_nome"].get(nome)
            pad = ex.padrao if ex else "?"
            por_padrao_ns.setdefault(pad, []).append(nome)
        p("| Exercicio | Padrao | Subreg |")
        p("|---|---|---|")
        # Ordem: padroes upper esperados primeiro
        ordem_pad = list(ESPERADO_PAD_PCT.keys())
        outros = [p_ for p_ in por_padrao_ns if p_ not in ordem_pad]
        for pad in ordem_pad + outros:
            for nome in sorted(por_padrao_ns.get(pad, [])):
                ex = res["info_por_nome"].get(nome)
                p(f"| {nome} | {pad} | {ex.subregiao if ex else '?'} |")
    else:
        p("_(todos os exercicios upper apareceram pelo menos 1×)_")
    p()

    # ---- Q3 ----
    p("## Q3 — Categorias dominantes/sub-representadas")
    p()
    p("### Por padrao (slots, agregado T1+T2)")
    p()
    pad_agreg: Counter = Counter()
    for t in (0, 1):
        pad_agreg.update(res["padrao_por_treino"][t])
    p("| Padrao | Obs | % Obs | % Esp | Δ pp | Razao O/E |")
    p("|---|---:|---:|---:|---:|---:|")
    upper_pads = list(ESPERADO_PAD_PCT.keys())
    outros_pads = sorted(p_ for p_ in pad_agreg if p_ not in upper_pads)
    for pad in upper_pads + outros_pads:
        obs = pad_agreg.get(pad, 0)
        pct_obs = obs / total_slots if total_slots else 0
        pct_esp = ESPERADO_PAD_PCT.get(pad, 0)
        delta = (pct_obs - pct_esp) * 100
        if pct_esp > 0:
            razao_str = f"{pct_obs / pct_esp:.2f}"
        elif obs > 0:
            razao_str = "∞ (esperado=0)"
        else:
            razao_str = "—"
        p(f"| {pad} | {obs} | {pct_obs:.1%} | {pct_esp:.1%} | {delta:+.1f} | {razao_str} |")
    p()

    p("### Por subregiao (slots, agregado T1+T2)")
    p()
    sub_agreg: Counter = Counter()
    for t in (0, 1):
        sub_agreg.update(res["sub_por_treino"][t])
    p("| Subregiao | Obs | % Obs | % Esp | Δ pp |")
    p("|---|---:|---:|---:|---:|")
    upper_subs = list(ESPERADO_SUB_PCT.keys())
    outros_subs = sorted(s for s in sub_agreg if s not in upper_subs)
    for sub in upper_subs + outros_subs:
        obs = sub_agreg.get(sub, 0)
        pct_obs = obs / total_slots if total_slots else 0
        pct_esp = ESPERADO_SUB_PCT.get(sub, 0)
        delta = (pct_obs - pct_esp) * 100
        p(f"| {sub} | {obs} | {pct_obs:.1%} | {pct_esp:.1%} | {delta:+.1f} |")
    p()

    p("### Composto vs isolado (agregado T1+T2)")
    p()
    comp = sum(res["purpose_por_treino"][t]["composto"] for t in (0, 1))
    iso = sum(res["purpose_por_treino"][t]["isolado"] for t in (0, 1))
    tot = comp + iso
    p("| Tipo | Obs | % Obs | % Esp | Δ pp |")
    p("|---|---:|---:|---:|---:|")
    for k, obs in (("composto", comp), ("isolado", iso)):
        pct_obs = obs / tot if tot else 0
        pct_esp = ESPERADO_PURPOSE_PCT[k]
        p(f"| {k} | {obs} | {pct_obs:.1%} | {pct_esp:.1%} | {(pct_obs-pct_esp)*100:+.1f} |")
    p()

    # ---- Q4 ----
    p("## Q4 — Distribuicao T1 vs T2")
    p()
    p("### Composto vs isolado por treino")
    p()
    p("| Tipo | T1 | % T1 | T2 | % T2 | Δ pp |")
    p("|---|---:|---:|---:|---:|---:|")
    s1 = sum(res["purpose_por_treino"][0].values())
    s2 = sum(res["purpose_por_treino"][1].values())
    for k in ("composto", "isolado"):
        t1 = res["purpose_por_treino"][0][k]
        t2 = res["purpose_por_treino"][1][k]
        pct1 = t1/s1 if s1 else 0
        pct2 = t2/s2 if s2 else 0
        p(f"| {k} | {t1} | {pct1:.1%} | {t2} | {pct2:.1%} | {(pct1-pct2)*100:+.1f} |")
    chi_purpose = _chi2_2x2(
        res["purpose_por_treino"][0]["composto"], res["purpose_por_treino"][0]["isolado"],
        res["purpose_por_treino"][1]["composto"], res["purpose_por_treino"][1]["isolado"],
    )
    sig_p = " (significativo p<0.05)" if chi_purpose > CHI2_CRIT_005 else ""
    p()
    p(f"χ² (composto vs isolado × T1/T2) = `{chi_purpose:.2f}`{sig_p}")
    p()

    p("### Por subregiao por treino")
    p()
    p("| Subreg | T1 | % T1 | T2 | % T2 | Δ pp | χ² |")
    p("|---|---:|---:|---:|---:|---:|---:|")
    s1_tot = sum(res["sub_por_treino"][0].values())
    s2_tot = sum(res["sub_por_treino"][1].values())
    for sub in upper_subs:
        t1 = res["sub_por_treino"][0].get(sub, 0)
        t2 = res["sub_por_treino"][1].get(sub, 0)
        pct1 = t1/s1_tot if s1_tot else 0
        pct2 = t2/s2_tot if s2_tot else 0
        chi = _chi2_2x2(t1, s1_tot - t1, t2, s2_tot - t2)
        sig = " *" if chi > CHI2_CRIT_005 else ""
        p(f"| {sub} | {t1} | {pct1:.1%} | {t2} | {pct2:.1%} | {(pct1-pct2)*100:+.1f} | {chi:.2f}{sig} |")
    p()

    p("### Top 15 exercicios com maior vies posicional T1 vs T2")
    p()
    p(f"Top-30 por freq_rotina, ordenado por |T1−T2|. χ² > {CHI2_CRIT_005} = p<0.05.")
    p()
    p("| Exercicio | T1 | T2 | Δ pp | χ² | sig |")
    p("|---|---:|---:|---:|---:|:---:|")
    candidates = res["freq_rotina"].most_common(30)
    deltas = []
    for nome, _ in candidates:
        t1 = res["freq_por_treino"][0][nome]
        t2 = res["freq_por_treino"][1][nome]
        chi = _chi2_2x2(t1, N - t1, t2, N - t2)
        deltas.append((nome, t1, t2, chi))
    deltas.sort(key=lambda r: abs(r[1] - r[2]), reverse=True)
    for nome, t1, t2, chi in deltas[:15]:
        sig = "*" if chi > CHI2_CRIT_005 else ""
        delta_pp = (t1 - t2) / N * 100
        p(f"| {nome} | {t1} | {t2} | {delta_pp:+.1f} | {chi:.2f} | {sig} |")
    n_sig = sum(1 for d in deltas if d[3] > CHI2_CRIT_005)
    p()
    p(f"Exercicios com χ² significativo (p<0.05) no top-30: **{n_sig}** / 30")
    p()

    # ---- Anexos ----
    p("## Anexos")
    p()
    p(f"- Rotinas com aviso `incompleta`: {res['n_rotinas_avisos']['incompleta']} ({res['n_rotinas_avisos']['incompleta']/N:.1%})")
    p(f"- Rotinas com aviso `familia_repetida`: {res['n_rotinas_avisos']['familia_repetida']} ({res['n_rotinas_avisos']['familia_repetida']/N:.1%})")
    p(f"- Rotinas com ≥1 exercicio escolhido via relaxamento de familia: {res['n_rotinas_com_relaxados']} ({res['n_rotinas_com_relaxados']/N:.1%})")
    p(f"- Sessoes com <4 exercicios: {res['n_sessoes_incompletas']} de {2*N}")
    p(f"- Total exercicios upper no banco: {len(res['nomes_upper'])}")
    p()

    return out.getvalue()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Analise de vies upper(4) x 2 treinos")
    ap.add_argument("--n-iter", type=int, default=1000)
    ap.add_argument("--seed-base", type=int, default=1000)
    ap.add_argument("--xlsx", default=XLSX_PATH)
    ap.add_argument("--out", default=OUT_PATH_DEFAULT,
                    help="Path do .md ('' para nao salvar)")
    ap.add_argument("--no-relax", action="store_true",
                    help="relaxar_familia=False (default ON)")
    ap.add_argument("--quiet", action="store_true", help="suprime progresso")
    args = ap.parse_args()

    # Forca UTF-8 no stdout (Windows usa cp1252 por default, quebra em chi2/Delta)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    print(f"Carregando banco de {args.xlsx}...", file=sys.stderr)
    banco = carregar_banco(args.xlsx)
    print(f"  {len(banco)} exercicios carregados", file=sys.stderr)

    print(f"Rodando {args.n_iter} iteracoes (seed_base={args.seed_base})...",
          file=sys.stderr)
    res = analisar(
        banco,
        n_iter=args.n_iter,
        seed_base=args.seed_base,
        relaxar_familia=not args.no_relax,
        verbose=not args.quiet,
    )

    relatorio = gerar_relatorio(res)
    print(relatorio)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(relatorio, encoding="utf-8")
        print(f"\nRelatorio salvo em {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
