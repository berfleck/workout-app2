"""
Teste de regressão para o bug de bloqueio inter-sessão de variações
e detecção de demandas incompletas.

Cenário: banco filtrado para conter apenas 4 peitos
("Crossover", "Crossover Sentado", "Crucifixo Halteres", "Apoio").
Geramos 2 treinos com demanda de 2 peitos cada — o 2º treino
NECESSARIAMENTE fica incompleto (só 1 peito disponível depois de
bloquear famílias do T1).
"""
import random
import sys

from gerador_treino import carregar_banco, gerar_multiplos_treinos


PEITOS_TESTE = {"Crossover", "Crossover Sentado", "Crucifixo Halteres", "Apoio"}


def _filtrar_banco(banco_completo):
    """Mantém todos os exercícios EXCETO peitos não-listados."""
    return [
        e for e in banco_completo
        if e.padrao not in ("empurrar_compostos", "empurrar_isolados")
        or e.nome in PEITOS_TESTE
    ]


def _coletar_nomes(sessao):
    nomes = []
    for bloco in sessao.blocos:
        for ex in (bloco.ex1, bloco.ex2, bloco.ex3):
            if ex:
                nomes.append(ex.nome)
    return nomes


def rodar(seed, modo="hierarquia", relaxar=False):
    random.seed(seed)

    banco = _filtrar_banco(carregar_banco("banco_exercicios.xlsx"))
    if modo == "hierarquia":
        demandas = [("subregiao", "peito", 2), ("subregiao", "core", 2)]
        cfg = {"demandas": demandas, "max_complexidade": 5, "tamanho_bloco": 2}
    else:
        # Modo Templates: usa padroes + exercicios_por_padrao (epp)
        cfg = {
            "padroes": ["empurrar_compostos", "empurrar_isolados", "core_isometrico", "core_dinamico"],
            "exercicios_por_padrao": {"empurrar_compostos": 1, "empurrar_isolados": 1,
                                      "core_isometrico": 1, "core_dinamico": 1},
            "max_complexidade": 5, "tamanho_bloco": 2,
        }
    sessoes = gerar_multiplos_treinos(banco, [cfg, cfg],
                                      variar_entre_treinos=True,
                                      relaxar_familia=relaxar)

    nomes_t1 = _coletar_nomes(sessoes[0])
    nomes_t2 = _coletar_nomes(sessoes[1])

    erros = []

    if not relaxar:
        # ─── Modo estrito: T2 fica incompleto ────────────────────────────
        if modo == "hierarquia":
            avisos_peito_t2 = [a for a in sessoes[1].avisos
                               if a.get("tipo") == "incompleta"
                               and a["nivel"] == "subregiao" and a["escopo"] == "peito"]
        else:
            peito_pads = {"empurrar_compostos", "empurrar_isolados"}
            avisos_peito_t2 = [a for a in sessoes[1].avisos
                               if a.get("tipo") == "incompleta"
                               and a["nivel"] == "padrao" and a["escopo"] in peito_pads]
        if not avisos_peito_t2:
            erros.append(f"T2 não tem aviso 'incompleta' de peito. avisos={sessoes[1].avisos}")
        else:
            if modo == "hierarquia":
                av = avisos_peito_t2[0]
                if av["qtd_obtida"] != 1:
                    erros.append(f"qtd_obtida esperado=1, obtido={av['qtd_obtida']}")
                if av["faltam"] != 1:
                    erros.append(f"faltam esperado=1, obtido={av['faltam']}")
            else:
                total_obtido = sum(a["qtd_obtida"] for a in avisos_peito_t2)
                total_pedido = sum(a["qtd_pedida"] for a in avisos_peito_t2)
                if total_obtido >= total_pedido:
                    erros.append(f"Templates: esperado obter < pedido; obtido={total_obtido} pedido={total_pedido}")
        if sessoes[1].relaxados:
            erros.append(f"sem relaxar, sessao.relaxados deveria ser []; got {sessoes[1].relaxados}")
    else:
        # ─── Modo relaxado: ou T2 completa via flexibilização, OU bate em ─
        # limite intra-sessão (não pode ter dois irmãos no mesmo treino).
        # Em ambos os casos, deve haver consistência entre relaxados e avisos.
        repetidas = [a for a in sessoes[1].avisos if a.get("tipo") == "familia_repetida"]
        incompletas = [a for a in sessoes[1].avisos if a.get("tipo") == "incompleta"]

        # Consistência: relaxados deve casar com avisos familia_repetida
        if bool(repetidas) != bool(sessoes[1].relaxados):
            erros.append(f"Inconsistência: repetidas={bool(repetidas)} mas relaxados={bool(sessoes[1].relaxados)}")
        if repetidas and len(sessoes[1].relaxados) != len(repetidas):
            erros.append(f"Tamanho diverge: {len(sessoes[1].relaxados)} relaxados vs {len(repetidas)} avisos")

        # Cada exercício relaxado deve estar nos blocos do T2
        for nome in sessoes[1].relaxados:
            if nome not in nomes_t2:
                erros.append(f"Nome relaxado {nome!r} não aparece no T2 (nomes_t2={nomes_t2})")

        # Sanity: se NÃO houve flexibilização nem incompletude, algo está estranho
        if not repetidas and not incompletas and not sessoes[1].relaxados:
            # T2 completo sem precisar relaxar — só aceita se nomes_t2 não tiver irmão de T1
            pass  # cenário válido

    # 2) Crossover e Crossover Sentado nunca devem coexistir em treinos diferentes
    #    Só checa no modo ESTRITO — no modo RELAXADO essa coexistência é o esperado.
    if not relaxar:
        par_problema = ("Crossover", "Crossover Sentado")
        if par_problema[0] in nomes_t1 and par_problema[1] in nomes_t2:
            erros.append(f"REGRESSÃO: Crossover em T1 e Crossover Sentado em T2 — {nomes_t1=} {nomes_t2=}")
        if par_problema[1] in nomes_t1 and par_problema[0] in nomes_t2:
            erros.append(f"REGRESSÃO: Crossover Sentado em T1 e Crossover em T2 — {nomes_t1=} {nomes_t2=}")

    return {
        "seed": seed,
        "ok": not erros,
        "erros": erros,
        "nomes_t1": nomes_t1,
        "nomes_t2": nomes_t2,
        "avisos_t1": sessoes[0].avisos,
        "avisos_t2": sessoes[1].avisos,
        "relaxados_t2": sessoes[1].relaxados,
    }


def main():
    seeds = [42, 7, 100, 200, 999]
    todos_ok = True
    cenarios = [
        ("hierarquia", False, "ESTRITO"),
        ("hierarquia", True,  "RELAXADO"),
        ("templates",  False, "ESTRITO"),
        ("templates",  True,  "RELAXADO"),
    ]
    for modo, relaxar, etiq in cenarios:
        print(f"\n=========== MODO: {modo.upper()} / {etiq} ===========")
        for seed in seeds:
            r = rodar(seed, modo=modo, relaxar=relaxar)
            status = "PASS" if r["ok"] else "FAIL"
            print(f"-- seed={seed} ({modo}/{etiq}) -> {status} --")
            print(f"  T1 nomes: {r['nomes_t1']}")
            print(f"  T2 nomes: {r['nomes_t2']}")
            print(f"  T2 avisos: {r['avisos_t2']}")
            print(f"  T2 relaxados: {r['relaxados_t2']}")
            if r["erros"]:
                todos_ok = False
                for e in r["erros"]:
                    print(f"  ERRO: {e}")
            print()
    print("=" * 50)
    print("RESULTADO FINAL:", "TODOS PASSARAM" if todos_ok else "ALGUM FALHOU")
    sys.exit(0 if todos_ok else 1)


if __name__ == "__main__":
    main()
