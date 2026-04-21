"""
BF Treinamento — Módulo de persistência SQLite
"""

import sqlite3, json
from pathlib import Path

DB_PATH = Path("bf_treinamento.db")

# Paths dos JSONs legados (para migração)
_ALUNOS_JSON = Path("alunos.json")
_HISTORICO_JSON = Path("historico_treinos.json")


def _conn():
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


def init_db():
    con = _conn()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            nivel TEXT DEFAULT 'intermediario',
            objetivo TEXT DEFAULT '',
            restricoes TEXT DEFAULT '[]',
            obs TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS historico (
            id TEXT PRIMARY KEY,
            data_salvo TEXT NOT NULL,
            aluno TEXT DEFAULT '—',
            etiqueta TEXT DEFAULT '',
            n_treinos INTEGER NOT NULL,
            sessoes TEXT NOT NULL,
            configs TEXT DEFAULT NULL
        );
    """)
    con.commit()
    con.close()


def migrar_json_para_sqlite():
    if not _ALUNOS_JSON.exists() and not _HISTORICO_JSON.exists():
        return

    con = _conn()

    if _ALUNOS_JSON.exists():
        try:
            with open(_ALUNOS_JSON, encoding="utf-8") as f:
                alunos = json.load(f)
            for a in alunos:
                existente = con.execute("SELECT id FROM alunos WHERE nome = ?", (a["nome"],)).fetchone()
                if not existente:
                    con.execute(
                        "INSERT INTO alunos (nome, nivel, objetivo, restricoes, obs) VALUES (?, ?, ?, ?, ?)",
                        (a["nome"], a.get("nivel", "intermediario"), a.get("objetivo", ""),
                         json.dumps(a.get("restricoes", []), ensure_ascii=False),
                         a.get("obs", "")))
            con.commit()
            _ALUNOS_JSON.rename(_ALUNOS_JSON.with_suffix(".json.bak"))
            print(f"  Migrados {len(alunos)} alunos de JSON para SQLite")
        except Exception as e:
            print(f"  Erro ao migrar alunos: {e}")

    if _HISTORICO_JSON.exists():
        try:
            with open(_HISTORICO_JSON, encoding="utf-8") as f:
                historico = json.load(f)
            for reg in historico:
                existente = con.execute("SELECT id FROM historico WHERE id = ?", (reg["id"],)).fetchone()
                if not existente:
                    con.execute(
                        "INSERT INTO historico (id, data_salvo, aluno, etiqueta, n_treinos, sessoes) VALUES (?, ?, ?, ?, ?, ?)",
                        (reg["id"], reg["data"], reg.get("aluno", "—"),
                         reg.get("etiqueta", ""), reg["n_treinos"],
                         json.dumps(reg["sessoes"], ensure_ascii=False)))
            con.commit()
            _HISTORICO_JSON.rename(_HISTORICO_JSON.with_suffix(".json.bak"))
            print(f"  Migrados {len(historico)} registros de JSON para SQLite")
        except Exception as e:
            print(f"  Erro ao migrar historico: {e}")

    con.close()


# ══════════════════════════════════════════════════════════════
# ALUNOS
# ══════════════════════════════════════════════════════════════

def carregar_alunos():
    con = _conn()
    rows = con.execute("SELECT * FROM alunos ORDER BY nome").fetchall()
    con.close()
    return [{"id": r["id"], "nome": r["nome"], "nivel": r["nivel"],
             "objetivo": r["objetivo"],
             "restricoes": json.loads(r["restricoes"]),
             "obs": r["obs"]} for r in rows]


def salvar_aluno(nome, nivel, objetivo, restricoes, obs):
    con = _conn()
    con.execute(
        "INSERT INTO alunos (nome, nivel, objetivo, restricoes, obs) VALUES (?, ?, ?, ?, ?)",
        (nome, nivel, objetivo, json.dumps(restricoes, ensure_ascii=False), obs))
    con.commit()
    con.close()


def editar_aluno(aluno_id, nome, nivel, objetivo, restricoes, obs):
    con = _conn()
    con.execute(
        "UPDATE alunos SET nome=?, nivel=?, objetivo=?, restricoes=?, obs=? WHERE id=?",
        (nome, nivel, objetivo, json.dumps(restricoes, ensure_ascii=False), obs, aluno_id))
    con.commit()
    con.close()


def deletar_aluno(aluno_id):
    con = _conn()
    con.execute("DELETE FROM alunos WHERE id = ?", (aluno_id,))
    con.commit()
    con.close()


# ══════════════════════════════════════════════════════════════
# HISTÓRICO
# ══════════════════════════════════════════════════════════════

def carregar_historico():
    con = _conn()
    rows = con.execute("SELECT id, data_salvo, aluno, etiqueta, n_treinos FROM historico ORDER BY id DESC").fetchall()
    con.close()
    return [{"id": r["id"], "data": r["data_salvo"], "aluno": r["aluno"],
             "etiqueta": r["etiqueta"], "n_treinos": r["n_treinos"]} for r in rows]


def carregar_registro(reg_id):
    con = _conn()
    row = con.execute("SELECT * FROM historico WHERE id = ?", (reg_id,)).fetchone()
    con.close()
    if not row:
        return None
    return {"id": row["id"], "data": row["data_salvo"], "aluno": row["aluno"],
            "etiqueta": row["etiqueta"], "n_treinos": row["n_treinos"],
            "sessoes": json.loads(row["sessoes"]),
            "configs": json.loads(row["configs"]) if row["configs"] else None}


def salvar_historico_registro(reg_id, data_salvo, aluno, etiqueta, n_treinos, sessoes, configs=None):
    con = _conn()
    con.execute(
        "INSERT INTO historico (id, data_salvo, aluno, etiqueta, n_treinos, sessoes, configs) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (reg_id, data_salvo, aluno, etiqueta, n_treinos,
         json.dumps(sessoes, ensure_ascii=False),
         json.dumps(configs, ensure_ascii=False) if configs else None))
    con.commit()
    con.close()


def deletar_historico(reg_id):
    con = _conn()
    con.execute("DELETE FROM historico WHERE id = ?", (reg_id,))
    con.commit()
    con.close()


def nomes_unicos_historico():
    con = _conn()
    rows = con.execute(
        "SELECT DISTINCT aluno FROM historico WHERE aluno != '—' AND aluno != '' ORDER BY aluno"
    ).fetchall()
    con.close()
    return [r["aluno"] for r in rows]


def buscar_historico_por_aluno(nome):
    con = _conn()
    rows = con.execute(
        "SELECT id, data_salvo, aluno, etiqueta, n_treinos FROM historico WHERE aluno = ? ORDER BY id DESC",
        (nome,)).fetchall()
    con.close()
    return [{"id": r["id"], "data": r["data_salvo"], "aluno": r["aluno"],
             "etiqueta": r["etiqueta"], "n_treinos": r["n_treinos"]} for r in rows]
