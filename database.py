"""
BF Treinamento — Módulo de persistência SQLite
"""

import sqlite3, json, os
from pathlib import Path

# DATA_DIR: diretório dos dados mutáveis (DB, JSONs de sessão, páginas publicadas).
# Default = pasta do projeto → comportamento local inalterado. Em produção
# (Railway), setar DATA_DIR=/data (volume persistente) pra os dados sobreviverem
# a cada redeploy. Fonte única — app_flask e publicador referenciam este valor.
DATA_DIR = Path(os.environ.get("DATA_DIR") or Path(__file__).resolve().parent)
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "bf_treinamento.db"

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
            obs TEXT DEFAULT '',
            rotina_ativa_id TEXT DEFAULT NULL
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
    # Migração: adicionar coluna rotina_ativa_id se não existir (DBs já criados)
    try:
        con.execute("ALTER TABLE alunos ADD COLUMN rotina_ativa_id TEXT DEFAULT NULL")
        con.commit()
    except sqlite3.OperationalError:
        pass  # coluna já existe
    # Migração: adicionar coluna rascunho_rotina se não existir
    try:
        con.execute("ALTER TABLE alunos ADD COLUMN rascunho_rotina TEXT DEFAULT NULL")
        con.commit()
    except sqlite3.OperationalError:
        pass
    # Migração: adicionar coluna rascunho_etiqueta se não existir
    try:
        con.execute("ALTER TABLE alunos ADD COLUMN rascunho_etiqueta TEXT DEFAULT NULL")
        con.commit()
    except sqlite3.OperationalError:
        pass
    # Migração: adicionar coluna data_atualizada no histórico
    try:
        con.execute("ALTER TABLE historico ADD COLUMN data_atualizada TEXT DEFAULT NULL")
        con.commit()
    except sqlite3.OperationalError:
        pass
    # Migração: adicionar coluna rascunho_intent
    try:
        con.execute("ALTER TABLE alunos ADD COLUMN rascunho_intent TEXT DEFAULT NULL")
        con.commit()
    except sqlite3.OperationalError:
        pass
    # Migração: adicionar coluna aderencia (Frente D / Fatia 3, 2026-05-24)
    # Vetor de perfil do aluno — dimensão "Aderência ao Tier" (alta/media/baixa).
    # Default 'media' = comportamento neutro pré-Frente D.
    try:
        con.execute("ALTER TABLE alunos ADD COLUMN aderencia TEXT DEFAULT 'media'")
        con.commit()
    except sqlite3.OperationalError:
        pass
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
             "obs": r["obs"],
             "rotina_ativa_id": r["rotina_ativa_id"],
             "aderencia": (r["aderencia"] if "aderencia" in r.keys() else "media") or "media"} for r in rows]


def salvar_aluno(nome, nivel, objetivo, restricoes, obs, aderencia="media"):
    con = _conn()
    con.execute(
        "INSERT INTO alunos (nome, nivel, objetivo, restricoes, obs, aderencia) VALUES (?, ?, ?, ?, ?, ?)",
        (nome, nivel, objetivo, json.dumps(restricoes, ensure_ascii=False), obs, aderencia))
    con.commit()
    con.close()


def editar_aluno(aluno_id, nome, nivel, objetivo, restricoes, obs, aderencia="media"):
    con = _conn()
    con.execute(
        "UPDATE alunos SET nome=?, nivel=?, objetivo=?, restricoes=?, obs=?, aderencia=? WHERE id=?",
        (nome, nivel, objetivo, json.dumps(restricoes, ensure_ascii=False), obs, aderencia, aluno_id))
    con.commit()
    con.close()


def deletar_aluno(aluno_id):
    con = _conn()
    con.execute("DELETE FROM alunos WHERE id = ?", (aluno_id,))
    con.commit()
    con.close()


def definir_rotina_ativa(aluno_id, historico_id):
    con = _conn()
    con.execute("UPDATE alunos SET rotina_ativa_id = ? WHERE id = ?", (historico_id, aluno_id))
    con.commit()
    con.close()


def salvar_rascunho(aluno_id, sessoes_list):
    con = _conn()
    con.execute("UPDATE alunos SET rascunho_rotina = ? WHERE id = ?",
                (json.dumps(sessoes_list, ensure_ascii=False), aluno_id))
    con.commit()
    con.close()


def carregar_rascunho(aluno_id):
    con = _conn()
    row = con.execute("SELECT rascunho_rotina FROM alunos WHERE id = ?", (aluno_id,)).fetchone()
    con.close()
    if not row or not row["rascunho_rotina"]:
        return None
    return json.loads(row["rascunho_rotina"])


def salvar_etiqueta_rascunho(aluno_id, etiqueta):
    con = _conn()
    con.execute("UPDATE alunos SET rascunho_etiqueta = ? WHERE id = ?",
                (etiqueta or None, aluno_id))
    con.commit()
    con.close()


def carregar_etiqueta_rascunho(aluno_id):
    con = _conn()
    row = con.execute("SELECT rascunho_etiqueta FROM alunos WHERE id = ?", (aluno_id,)).fetchone()
    con.close()
    return (row["rascunho_etiqueta"] or "") if row else ""


def limpar_rascunho(aluno_id):
    con = _conn()
    con.execute("UPDATE alunos SET rascunho_rotina = NULL, rascunho_etiqueta = NULL, rascunho_intent = NULL WHERE id = ?", (aluno_id,))
    con.commit()
    con.close()


def salvar_intent_rascunho(aluno_id, intent):
    con = _conn()
    con.execute("UPDATE alunos SET rascunho_intent = ? WHERE id = ?",
                (intent or None, aluno_id))
    con.commit()
    con.close()


def carregar_intent_rascunho(aluno_id):
    con = _conn()
    row = con.execute("SELECT rascunho_intent FROM alunos WHERE id = ?", (aluno_id,)).fetchone()
    con.close()
    return (row["rascunho_intent"] or "") if row else ""


def _row_to_registro(row):
    return {"id": row["id"], "data": row["data_salvo"],
            "data_atualizada": row["data_atualizada"] if "data_atualizada" in row.keys() else None,
            "aluno": row["aluno"],
            "etiqueta": row["etiqueta"], "n_treinos": row["n_treinos"],
            "sessoes": json.loads(row["sessoes"]),
            "configs": json.loads(row["configs"]) if row["configs"] else None}


def carregar_rotina_ativa(aluno_id):
    con = _conn()
    row = con.execute(
        "SELECT h.* FROM historico h JOIN alunos a ON a.rotina_ativa_id = h.id WHERE a.id = ?",
        (aluno_id,)).fetchone()
    con.close()
    return _row_to_registro(row) if row else None


def carregar_rotina_anterior(aluno_nome, rotina_ativa_id):
    con = _conn()
    row = con.execute(
        "SELECT * FROM historico WHERE aluno = ? AND id != ? ORDER BY id DESC LIMIT 1",
        (aluno_nome, rotina_ativa_id or "")).fetchone()
    con.close()
    return _row_to_registro(row) if row else None


def buscar_aluno_por_nome(nome):
    con = _conn()
    row = con.execute("SELECT * FROM alunos WHERE nome = ?", (nome,)).fetchone()
    con.close()
    if not row:
        return None
    return {"id": row["id"], "nome": row["nome"], "nivel": row["nivel"],
            "objetivo": row["objetivo"],
            "restricoes": json.loads(row["restricoes"]),
            "obs": row["obs"],
            "rotina_ativa_id": row["rotina_ativa_id"],
            "aderencia": (row["aderencia"] if "aderencia" in row.keys() else "media") or "media"}


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
    return _row_to_registro(row) if row else None


def salvar_historico_registro(reg_id, data_salvo, aluno, etiqueta, n_treinos, sessoes, configs=None):
    con = _conn()
    con.execute(
        "INSERT INTO historico (id, data_salvo, aluno, etiqueta, n_treinos, sessoes, configs) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (reg_id, data_salvo, aluno, etiqueta, n_treinos,
         json.dumps(sessoes, ensure_ascii=False),
         json.dumps(configs, ensure_ascii=False) if configs else None))
    con.commit()
    con.close()


def atualizar_historico_registro(reg_id, data_atualizada, etiqueta, n_treinos, sessoes, configs=None):
    """Sobrescreve um registro existente do histórico mantendo o mesmo id."""
    con = _conn()
    con.execute(
        "UPDATE historico SET data_atualizada=?, etiqueta=?, n_treinos=?, sessoes=?, configs=? WHERE id=?",
        (data_atualizada, etiqueta, n_treinos,
         json.dumps(sessoes, ensure_ascii=False),
         json.dumps(configs, ensure_ascii=False) if configs else None,
         reg_id))
    con.commit()
    con.close()


def atualizar_etiqueta_historico(reg_id, etiqueta):
    """Atualiza apenas a etiqueta de um registro do histórico."""
    con = _conn()
    con.execute("UPDATE historico SET etiqueta = ? WHERE id = ?", (etiqueta or "", reg_id))
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
