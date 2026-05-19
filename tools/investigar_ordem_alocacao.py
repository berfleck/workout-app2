"""Investiga o problema de ORDEM DE ALOCACAO no pre_alocar_rotina.

Pergunta 1: Quao frequente eh costas=2 (ambos remada+puxada coexistem)?
Pergunta 2: Quando coexistem, qual eh alocado primeiro?
Pergunta 3: Esse efeito acontece em outras categorias tambem?
            (ombro_composto vs isolado, peito compostos vs isolados, etc.)
Pergunta 4: Familias-de-remada — distribuicao por familia e dentro de
            cada familia (LM vs vanilla curvada, etc.)

Roda N=2000 iters de upper(4)+lower(2)x1T e instrumenta
`_selecionar_cand_score_aware` pra logar ordem de chegada de cada
slot + se alocados_intra estava vazio na hora do sorteio.
"""
from __future__ import annotations

import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gerador_treino as gt
from gerador_treino import carregar_banco, gerar_multiplos_treinos

XLSX_PATH = "banco_exercicios.xlsx"
N_ITER = 2000

CONFIGS = [{"demandas": [("regiao", "upper", 4), ("regiao", "lower", 2)]}]
LM_NAMES = {"Remada LM Neutra", "Remada LM Aberta"}


# Variavel global pra capturar ordem de alocacao
_LOG: list[dict] = []
_orig_select = gt._selecionar_cand_score_aware


def _selecionar_instrumentado(cands, alocados_intra, alocados_inter=None,
                              historico_r1=None, pesos_config=None,
                              slot_info=None, pre_alocacao_info=None):
    """Wrapper que loga: padrao do slot, padroes dos peers, vazio?"""
    # Identifica padrao representativo dos candidatos
    padroes_cand = set(c.padrao for c in cands)
    pad_slot = next(iter(padroes_cand)) if len(padroes_cand) == 1 else "MIX"
    subregioes_cand = set(c.subregiao for c in cands)
    sub_slot = next(iter(subregioes_cand)) if len(subregioes_cand) == 1 else "MIX"

    peer_padroes_intra = [e.padrao for e in (alocados_intra or [])]
    peer_subs_intra = [e.subregiao for e in (alocados_intra or [])]
    peer_padroes_mesma_sub_intra = [
        e.padrao for e in (alocados_intra or [])
        if e.subregiao == sub_slot
    ]
    n_alocados_intra = len(alocados_intra or [])

    # Chama original
    if pesos_config is None:
        from pesos_proximidade import PESOS_DEFAULT
        pesos_config = PESOS_DEFAULT
    escolhido = _orig_select(cands, alocados_intra, alocados_inter,
                              historico_r1, pesos_config, slot_info,
                              pre_alocacao_info)

    _LOG.append({
        "sub_slot": sub_slot,
        "pad_slot": pad_slot,
        "n_peers_intra": n_alocados_intra,
        "peer_pads_mesma_sub": peer_padroes_mesma_sub_intra,
        "escolhido_nome": escolhido.nome,
        "escolhido_pad": escolhido.padrao,
        "n_cands": len(cands),
    })
    return escolhido


def rodar(n_iter=N_ITER):
    banco = carregar_banco(XLSX_PATH)
    # Mapeamento nome -> variacao_de (familia)
    fam = {e.nome: (e.variacao_de or e.nome) for e in banco}

    gt._selecionar_cand_score_aware = _selecionar_instrumentado
    try:
        for i in range(n_iter):
            random.seed(i)
            _ = gerar_multiplos_treinos(banco, CONFIGS, relaxar_familia=True)
    finally:
        gt._selecionar_cand_score_aware = _orig_select

    return _LOG, fam


def main():
    log, fam = rodar(N_ITER)
    print(f"Total chamadas de selecao logadas: {len(log)}")

    # ========== Pergunta 1+2: ordem de alocacao pra costas ==========
    print()
    print("=" * 80)
    print("PERGUNTA 1+2: Ordem de alocacao quando padroes coexistem em costas")
    print("=" * 80)

    # Slots de costas (remadas ou puxadas)
    costas_slots = [l for l in log if l["sub_slot"] == "costas"]
    print(f"\nTotal de slots costas alocados em {N_ITER} rotinas: {len(costas_slots)}")

    # Frequencia: rem ou pux alocado primeiro quando ambos coexistem na rotina
    # Pra detectar coexistencia, comparo timestamps via posicao no log dentro
    # da mesma rotina. Mais simples: agrupar por janela de 6 selecoes (1 rotina = 6 slots)
    rotinas = [log[i:i+6] for i in range(0, len(log), 6)]

    rotinas_com_costas_2 = 0
    primeiro_quando_2 = Counter()  # "remada", "puxada"
    rotinas_so_remada = 0
    rotinas_so_puxada = 0
    rotinas_sem_costas = 0

    for rot in rotinas:
        slots_costas_rot = [l for l in rot if l["sub_slot"] == "costas"]
        pads = [l["pad_slot"] for l in slots_costas_rot]
        if len(slots_costas_rot) == 0:
            rotinas_sem_costas += 1
        elif len(slots_costas_rot) == 1:
            if pads[0] == "remadas":
                rotinas_so_remada += 1
            elif pads[0] == "puxadas":
                rotinas_so_puxada += 1
        elif len(slots_costas_rot) >= 2:
            rotinas_com_costas_2 += 1
            # Primeiro slot costas na ordem do log
            primeiro = pads[0]
            primeiro_quando_2[primeiro] += 1

    print(f"\nClassificacao de rotinas por composicao costas:")
    print(f"  sem costas         : {rotinas_sem_costas}/{N_ITER}  ({100*rotinas_sem_costas/N_ITER:.1f}%)")
    print(f"  so 1 remada        : {rotinas_so_remada}/{N_ITER}  ({100*rotinas_so_remada/N_ITER:.1f}%)")
    print(f"  so 1 puxada        : {rotinas_so_puxada}/{N_ITER}  ({100*rotinas_so_puxada/N_ITER:.1f}%)")
    print(f"  costas >= 2 slots  : {rotinas_com_costas_2}/{N_ITER}  ({100*rotinas_com_costas_2/N_ITER:.1f}%)")

    if rotinas_com_costas_2 > 0:
        print(f"\nQuando costas=2, qual padrao foi alocado PRIMEIRO:")
        for pad, ct in primeiro_quando_2.most_common():
            print(f"  {pad:12s}: {ct}/{rotinas_com_costas_2}  ({100*ct/rotinas_com_costas_2:.1f}%)")

    # Quem ja estava em alocados_intra quando o slot remada foi escolhido?
    remada_slots = [l for l in log if l["sub_slot"] == "costas" and l["pad_slot"] == "remadas"]
    puxada_slots = [l for l in log if l["sub_slot"] == "costas" and l["pad_slot"] == "puxadas"]

    print(f"\nQuando slot REMADA eh escolhido (total={len(remada_slots)}):")
    n_com_puxada_peer = sum(1 for l in remada_slots if "puxadas" in l["peer_pads_mesma_sub"])
    n_com_remada_peer = sum(1 for l in remada_slots if "remadas" in l["peer_pads_mesma_sub"])
    n_sem_peer_costas = sum(1 for l in remada_slots if not l["peer_pads_mesma_sub"])
    print(f"  Sem peer em costas      : {n_sem_peer_costas}/{len(remada_slots)}  ({100*n_sem_peer_costas/len(remada_slots):.1f}%)")
    print(f"  Com PUXADA peer in costas: {n_com_puxada_peer}/{len(remada_slots)}  ({100*n_com_puxada_peer/len(remada_slots):.1f}%)")
    print(f"  Com REMADA peer in costas: {n_com_remada_peer}/{len(remada_slots)}  ({100*n_com_remada_peer/len(remada_slots):.1f}%)")

    print(f"\nQuando slot PUXADA eh escolhido (total={len(puxada_slots)}):")
    n_com_remada_peer_p = sum(1 for l in puxada_slots if "remadas" in l["peer_pads_mesma_sub"])
    n_com_puxada_peer_p = sum(1 for l in puxada_slots if "puxadas" in l["peer_pads_mesma_sub"])
    n_sem_peer_p = sum(1 for l in puxada_slots if not l["peer_pads_mesma_sub"])
    print(f"  Sem peer em costas      : {n_sem_peer_p}/{len(puxada_slots)}  ({100*n_sem_peer_p/len(puxada_slots):.1f}%)")
    print(f"  Com REMADA peer in costas: {n_com_remada_peer_p}/{len(puxada_slots)}  ({100*n_com_remada_peer_p/len(puxada_slots):.1f}%)")
    print(f"  Com PUXADA peer in costas: {n_com_puxada_peer_p}/{len(puxada_slots)}  ({100*n_com_puxada_peer_p/len(puxada_slots):.1f}%)")

    # ========== Pergunta 3: efeito em outras subregioes? ==========
    print()
    print("=" * 80)
    print("PERGUNTA 3: Efeito de ORDEM em outras subregioes")
    print("=" * 80)
    print()
    print("Pra cada padrao, qual % das vezes foi escolhido SEM peer same-subregiao?")
    print("(% alto = padrao quase sempre eh PRIMEIRO da subregiao = imune ao INTRA)")
    print()
    print(f"  {'subregiao':18s}  {'padrao':25s}  {'total':>6s}  {'sem peer':>10s}  {'%':>7s}")
    print("  " + "-" * 72)

    # Agrupar por (sub, pad)
    grupo: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for l in log:
        if l["pad_slot"] != "MIX" and l["sub_slot"] != "MIX":
            grupo[(l["sub_slot"], l["pad_slot"])].append(l)

    rows = []
    for (sub, pad), entries in grupo.items():
        if len(entries) < 50:
            continue
        n_total = len(entries)
        n_sem_peer = sum(1 for l in entries if not l["peer_pads_mesma_sub"])
        pct = 100 * n_sem_peer / n_total
        rows.append((sub, pad, n_total, n_sem_peer, pct))

    rows.sort(key=lambda r: (r[0], -r[4]))
    for sub, pad, total, sem_peer, pct in rows:
        marker = " ⚠️" if pct > 95 else ("  ⚡" if pct < 70 else "   ")
        print(f"  {sub:18s}  {pad:25s}  {total:6d}  {sem_peer:10d}  {pct:6.1f}%{marker}")

    print()
    print("  Legenda:")
    print("    ⚠️  = >95% sem peer: alocado primeiro, scoring INTRA nunca dispara")
    print("    ⚡  = <70% sem peer: frequentemente alocado depois, INTRA fica ativo")

    # ========== Pergunta 4: distribuicao por familia ==========
    print()
    print("=" * 80)
    print("PERGUNTA 4: Distribuicao por FAMILIA de remada (variacao_de)")
    print("=" * 80)

    # Conta cada familia
    fam_count = Counter()
    fam_por_remada = defaultdict(Counter)
    remadas_total = 0
    for l in log:
        if l["pad_slot"] == "remadas":
            f = fam[l["escolhido_nome"]]
            fam_count[f] += 1
            fam_por_remada[f][l["escolhido_nome"]] += 1
            remadas_total += 1

    print(f"\nTotal slots remada: {remadas_total}")
    print()
    print(f"  {'familia':18s}  {'membros':>7s}  {'slots':>6s}  {'%':>6s}  {'membros do banco':30s}")
    print("  " + "-" * 75)

    # Lista de exs por familia
    banco = carregar_banco(XLSX_PATH)
    fam_membros: dict[str, list[str]] = defaultdict(list)
    for e in banco:
        if e.padrao == "remadas":
            f = e.variacao_de or e.nome
            fam_membros[f].append(e.nome)

    fams_sorted = sorted(fam_count.keys(), key=lambda f: -fam_count[f])
    for f in fams_sorted:
        n = fam_count[f]
        pct = 100 * n / remadas_total
        membros = fam_membros.get(f, [])
        membros_str = ", ".join(m.replace("Remada ", "") for m in membros)[:30]
        print(f"  {f:18s}  {len(membros):>7d}  {n:6d}  {pct:5.1f}%  {membros_str}")

    print()
    print("--- Dentro de cada familia, distribuicao por exercicio ---")
    for f in fams_sorted:
        membros = sorted(fam_por_remada[f].items(), key=lambda x: -x[1])
        if len(membros) <= 1:
            continue
        print(f"\n  Familia '{f}' ({fam_count[f]} slots):")
        for nome, ct in membros:
            marker = " ⭐ LM" if nome in LM_NAMES else ""
            pct_fam = 100 * ct / fam_count[f]
            pct_unif = 100 / len(fam_membros[f])
            razao = pct_fam / pct_unif
            print(f"    {nome:30s}  {ct:5d}  {pct_fam:5.2f}%  (uniforme={pct_unif:.1f}%, razao={razao:.2f}x){marker}")


if __name__ == "__main__":
    main()
