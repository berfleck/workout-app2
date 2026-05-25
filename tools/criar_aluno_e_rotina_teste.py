"""Script ad-hoc — cria aluno de teste e gera rotina Full Body 2T via CSP.

Atalha a UI pra produzir uma rotina determinística pra avaliação clínica.
Usa o mesmo wiring que `/gerar` (Frente E.1): mapeamento de demandas + pesos.
"""
from __future__ import annotations
import json
import random
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import database as db
from app_flask import (
    _PESO_EVITAR_AGONISTAS_DEFAULT, _PESO_TAMANHO_BLOCO_DEFAULT,
    _nivel_aluno_csp, _peso_aderencia_csp,
    _treino_dict_csp_pra_sessao, _distribuir_avisos_rotina_csp,
    _sessao_to_dict,
)
from gerador_csp import ConfigVariedade, gerar_rotina_csp
from gerador_treino import carregar_banco

ALUNO_NOME = "Teste CSP"
SEED = 42


def garantir_aluno():
    db.init_db()
    alunos = db.carregar_alunos()
    existente = next((a for a in alunos if a["nome"] == ALUNO_NOME), None)
    if existente:
        print(f"[OK] Aluno '{ALUNO_NOME}' já existia (id={existente['id']}).")
        return existente
    db.salvar_aluno(
        nome=ALUNO_NOME,
        nivel="intermediario",
        objetivo="hipertrofia",
        restricoes=[],
        obs="Aluno de teste — criado por tools/criar_aluno_e_rotina_teste.py",
        aderencia="media",
    )
    aluno = db.buscar_aluno_por_nome(ALUNO_NOME)
    print(f"[OK] Aluno '{ALUNO_NOME}' criado (id={aluno['id']}).")
    return aluno


def gerar_rotina(aluno):
    banco = carregar_banco("banco_exercicios.xlsx")
    demandas_t = [
        ("regiao", "upper", 3),
        ("regiao", "lower", 3),
        ("regiao", "core", 2),
    ]
    demandas_por_treino = [demandas_t, demandas_t]

    nivel = _nivel_aluno_csp(aluno)
    peso_aderencia = _peso_aderencia_csp(aluno)

    resultado = gerar_rotina_csp(
        demandas_por_treino,
        banco,
        nivel_aluno=nivel,
        seed=SEED,
        variedade=ConfigVariedade(),
        peso_aderencia=peso_aderencia,
        peso_evitar_agonistas=_PESO_EVITAR_AGONISTAS_DEFAULT,
        tamanho_preferido=2,
        peso_tamanho_bloco=_PESO_TAMANHO_BLOCO_DEFAULT,
        relaxar_familia=True,
    )

    if not resultado.get("viavel"):
        print(f"[FAIL] CSP devolveu inviável: {resultado.get('status')}")
        return None

    print(f"[OK] CSP viável. solve_time={resultado.get('solve_time'):.2f}s "
          f"status={resultado.get('status')} "
          f"inversoes_totais={resultado.get('inversoes_totais')}")

    sessoes = []
    for ti, t_dict in enumerate(resultado["treinos"]):
        tipo_label = f"Treino {ti+1} — Full Body"
        s = _treino_dict_csp_pra_sessao(t_dict, tipo_label)
        sessoes.append(s)

    _distribuir_avisos_rotina_csp(resultado, sessoes, demandas_por_treino)
    return sessoes, resultado


def salvar(aluno, sessoes):
    reg_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + f"{random.randint(0, 0xFFFF):04x}"
    db.salvar_historico_registro(
        reg_id=reg_id,
        data_salvo=datetime.now().isoformat(),
        aluno=ALUNO_NOME,
        etiqueta="Full Body 2T (avaliação clínica)",
        n_treinos=len(sessoes),
        sessoes=[_sessao_to_dict(s) for s in sessoes],
        configs=None,
    )
    db.definir_rotina_ativa(aluno["id"], reg_id)
    print(f"[OK] Rotina salva no histórico (id={reg_id}) e ativada pro aluno.")


def imprimir(sessoes, resultado):
    print("\n" + "=" * 72)
    print(f"ROTINA — {ALUNO_NOME}")
    print("=" * 72)
    for ti, s in enumerate(sessoes):
        print(f"\n┌─ TREINO {ti+1} ── {s.tipo}")
        for b in s.blocos:
            exs = [b.ex1, b.ex2, b.ex3]
            exs = [e for e in exs if e]
            head = f"│  Bloco {b.label}  ({len(exs)}-ex)"
            print(head)
            for e in exs:
                rel = " ↻" if e.nome in (s.relaxados or []) else ""
                lat = f" [{e.unilateral}]" if e.unilateral else ""
                fad = f" fad={e.fadiga}" if hasattr(e, "fadiga") else ""
                cpx = f" cpx={e.complexidade}" if hasattr(e, "complexidade") else ""
                print(f"│    • {e.nome}{rel}")
                print(f"│      {e.regiao}/{e.subregiao}/{e.padrao}  "
                      f"({e.purpose}){lat}{fad}{cpx}  eq:{e.eq_primario}")
        if s.relaxados:
            print(f"│  Relaxados: {', '.join(s.relaxados)}")
        if s.avisos:
            for a in s.avisos:
                print(f"│  Aviso: {a}")
        print("└" + "─" * 60)

    print("\n— Avisos cross-rotina —")
    for chave in ("h_a1_aplicadas", "h_r1_aplicadas"):
        for a in resultado.get(chave, []):
            print(f"  [{chave}] {a}")


def main():
    aluno = garantir_aluno()
    out = gerar_rotina(aluno)
    if out is None:
        return 1
    sessoes, resultado = out
    salvar(aluno, sessoes)
    imprimir(sessoes, resultado)
    return 0


if __name__ == "__main__":
    sys.exit(main())
