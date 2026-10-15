"""
Multi-Tenant Database Layer for Insurers 1 through 6
Supports:
  1. PostgreSQL 16 (in Docker, host port 5433 or custom PGHOST/PGPORT)
  2. Automatic SQLite Fallback (data/db/insurerX.sqlite) when Postgres is offline

Schema conforms strictly to Phase 10 / Section 8.3 of project specifications:
  - claims: claim_id, claim_ref, claim_data_canonical, claim_data, features,
            model_version, fraud_score, risk_label, claim_hash, claim_tx_id,
            chain_status, status, created_at
  - explanations: claim_ref, shap_canonical, shap_json, shap_hash, shap_tx_id,
                  chain_status, created_at
  - audit_log: id, claim_ref, check_type, result, checked_at
"""

import os
import json
import sqlite3
import psycopg2
from typing import Dict, Any, List, Optional
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "db")
os.makedirs(DB_DIR, exist_ok=True)

PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = int(os.getenv("POSTGRES_PORT", "5433"))
PG_USER = os.getenv("POSTGRES_ADMIN_USER", "admin_user")
PG_PASS = os.getenv("POSTGRES_ADMIN_PASSWORD", "AdminSecure2026!")

# Backup store for tampering demo restore
_BACKUP_STORE: Dict[str, Dict[str, Any]] = {}


import socket

# Cache flag: None = untested, True = connected, False = offline
_POSTGRES_AVAILABLE = None

def is_postgres_available() -> bool:
    """Checks if consortium PostgreSQL instance is reachable (instant socket probe with caching)."""
    global _POSTGRES_AVAILABLE
    if _POSTGRES_AVAILABLE is not None:
        return _POSTGRES_AVAILABLE

    try:
        # Fast socket test (fails in <1ms if port is closed)
        with socket.create_connection((PG_HOST, PG_PORT), timeout=0.1):
            pass
        # Port is open; verify PG credentials
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASS,
            dbname="postgres",
            connect_timeout=1
        )
        conn.close()
        _POSTGRES_AVAILABLE = True
    except Exception:
        _POSTGRES_AVAILABLE = False

    return _POSTGRES_AVAILABLE


def _get_sqlite_conn(insurer_id: str) -> sqlite3.Connection:
    """Returns a SQLite connection for the specified insurer."""
    clean_id = insurer_id.lower().replace("-", "_")
    db_file = os.path.join(DB_DIR, f"{clean_id}.sqlite")
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn


def _get_pg_conn(insurer_id: str):
    """Returns a psycopg2 connection for the specified insurer."""
    clean_id = insurer_id.lower().replace("-", "_")
    db_name = f"{clean_id}_db"
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASS,
        dbname=db_name,
        connect_timeout=3
    )


def init_db(insurer_id: str):
    """Initializes tables for a given insurer if they do not exist."""
    schema_sql = """
    CREATE TABLE IF NOT EXISTS claims (
        claim_id TEXT PRIMARY KEY,
        claim_ref TEXT UNIQUE NOT NULL,
        claim_data_canonical TEXT NOT NULL,
        claim_data TEXT NOT NULL,
        features TEXT NOT NULL,
        model_version TEXT NOT NULL,
        fraud_score REAL NOT NULL,
        risk_label TEXT NOT NULL,
        claim_hash TEXT NOT NULL,
        claim_tx_id TEXT,
        chain_status TEXT NOT NULL DEFAULT 'PENDING',
        status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS explanations (
        claim_ref TEXT PRIMARY KEY,
        shap_canonical TEXT NOT NULL,
        shap_json TEXT NOT NULL,
        shap_hash TEXT NOT NULL,
        shap_tx_id TEXT,
        chain_status TEXT NOT NULL DEFAULT 'PENDING',
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_ref TEXT,
        check_type TEXT,
        result TEXT,
        checked_at TEXT NOT NULL
    );
    """
    if is_postgres_available():
        # Postgres init
        try:
            conn = _get_pg_conn(insurer_id)
            with conn.cursor() as cur:
                # In postgres, json columns are jsonb, autoincrement is bigserial
                cur.execute("""
                CREATE TABLE IF NOT EXISTS claims (
                    claim_id UUID PRIMARY KEY,
                    claim_ref TEXT UNIQUE NOT NULL,
                    claim_data_canonical TEXT NOT NULL,
                    claim_data JSONB NOT NULL,
                    features JSONB NOT NULL,
                    model_version TEXT NOT NULL,
                    fraud_score NUMERIC(8,6) NOT NULL,
                    risk_label TEXT NOT NULL CHECK (risk_label IN ('HIGH','LOW')),
                    claim_hash CHAR(64) NOT NULL,
                    claim_tx_id TEXT,
                    chain_status TEXT NOT NULL DEFAULT 'PENDING',
                    status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                CREATE TABLE IF NOT EXISTS explanations (
                    claim_ref TEXT PRIMARY KEY REFERENCES claims(claim_ref) ON DELETE CASCADE,
                    shap_canonical TEXT NOT NULL,
                    shap_json JSONB NOT NULL,
                    shap_hash CHAR(64) NOT NULL,
                    shap_tx_id TEXT,
                    chain_status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                CREATE TABLE IF NOT EXISTS audit_log (
                    id BIGSERIAL PRIMARY KEY,
                    claim_ref TEXT,
                    check_type TEXT,
                    result TEXT,
                    checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """)
            conn.commit()
            conn.close()
            return
        except Exception:
            pass

    # SQLite fallback init
    conn = _get_sqlite_conn(insurer_id)
    with conn:
        conn.executescript(schema_sql)
    conn.close()


def insert_claim(insurer_id: str, claim: Dict[str, Any]) -> Dict[str, Any]:
    """Inserts a claim into the insurer's database with chain_status='PENDING'."""
    init_db(insurer_id)
    now_str = datetime.utcnow().isoformat() + "Z"

    if is_postgres_available():
        try:
            conn = _get_pg_conn(insurer_id)
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO claims (
                    claim_id, claim_ref, claim_data_canonical, claim_data, features,
                    model_version, fraud_score, risk_label, claim_hash, claim_tx_id,
                    chain_status, status, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    claim["claim_id"],
                    claim["claim_ref"],
                    claim["claim_data_canonical"],
                    json.dumps(claim["claim_data"]),
                    json.dumps(claim["features"]),
                    claim["model_version"],
                    claim["fraud_score"],
                    claim["risk_label"],
                    claim["claim_hash"],
                    claim.get("claim_tx_id"),
                    claim.get("chain_status", "PENDING"),
                    claim.get("status", "PENDING_REVIEW"),
                    now_str
                ))
            conn.commit()
            conn.close()
            return claim
        except Exception:
            pass

    # SQLite
    conn = _get_sqlite_conn(insurer_id)
    with conn:
        conn.execute("""
        INSERT INTO claims (
            claim_id, claim_ref, claim_data_canonical, claim_data, features,
            model_version, fraud_score, risk_label, claim_hash, claim_tx_id,
            chain_status, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(claim["claim_id"]),
            str(claim["claim_ref"]),
            claim["claim_data_canonical"],
            json.dumps(claim["claim_data"]),
            json.dumps(claim["features"]),
            claim["model_version"],
            float(claim["fraud_score"]),
            claim["risk_label"],
            claim["claim_hash"],
            claim.get("claim_tx_id"),
            claim.get("chain_status", "PENDING"),
            claim.get("status", "PENDING_REVIEW"),
            now_str
        ))
    conn.close()
    return claim


def update_claim_chain_status(insurer_id: str, claim_ref: str, chain_status: str, tx_id: Optional[str] = None):
    """Updates chain anchoring status (e.g. 'ANCHORED' or 'FAILED') and transaction id."""
    if is_postgres_available():
        try:
            conn = _get_pg_conn(insurer_id)
            with conn.cursor() as cur:
                cur.execute("""
                UPDATE claims SET chain_status = %s, claim_tx_id = COALESCE(%s, claim_tx_id)
                WHERE claim_ref = %s
                """, (chain_status, tx_id, claim_ref))
            conn.commit()
            conn.close()
            return
        except Exception:
            pass

    conn = _get_sqlite_conn(insurer_id)
    with conn:
        conn.execute("""
        UPDATE claims SET chain_status = ?, claim_tx_id = COALESCE(?, claim_tx_id)
        WHERE claim_ref = ?
        """, (chain_status, tx_id, claim_ref))
    conn.close()


def insert_explanation(insurer_id: str, exp: Dict[str, Any]):
    """Stores a SHAP explanation for a fraud-flagged (HIGH risk) claim."""
    init_db(insurer_id)
    now_str = datetime.utcnow().isoformat() + "Z"

    if is_postgres_available():
        try:
            conn = _get_pg_conn(insurer_id)
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO explanations (
                    claim_ref, shap_canonical, shap_json, shap_hash, shap_tx_id, chain_status, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (claim_ref) DO UPDATE SET
                    shap_canonical = EXCLUDED.shap_canonical,
                    shap_json = EXCLUDED.shap_json,
                    shap_hash = EXCLUDED.shap_hash,
                    shap_tx_id = EXCLUDED.shap_tx_id,
                    chain_status = EXCLUDED.chain_status
                """, (
                    exp["claim_ref"],
                    exp["shap_canonical"],
                    json.dumps(exp["shap_json"]),
                    exp["shap_hash"],
                    exp.get("shap_tx_id"),
                    exp.get("chain_status", "PENDING"),
                    now_str
                ))
            conn.commit()
            conn.close()
            return
        except Exception:
            pass

    conn = _get_sqlite_conn(insurer_id)
    with conn:
        conn.execute("""
        INSERT OR REPLACE INTO explanations (
            claim_ref, shap_canonical, shap_json, shap_hash, shap_tx_id, chain_status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(exp["claim_ref"]),
            exp["shap_canonical"],
            json.dumps(exp["shap_json"]),
            exp["shap_hash"],
            exp.get("shap_tx_id"),
            exp.get("chain_status", "PENDING"),
            now_str
        ))
    conn.close()


def update_explanation_chain_status(insurer_id: str, claim_ref: str, chain_status: str, tx_id: Optional[str] = None):
    """Updates chain status of an explanation record."""
    if is_postgres_available():
        try:
            conn = _get_pg_conn(insurer_id)
            with conn.cursor() as cur:
                cur.execute("""
                UPDATE explanations SET chain_status = %s, shap_tx_id = COALESCE(%s, shap_tx_id)
                WHERE claim_ref = %s
                """, (chain_status, tx_id, claim_ref))
            conn.commit()
            conn.close()
            return
        except Exception:
            pass

    conn = _get_sqlite_conn(insurer_id)
    with conn:
        conn.execute("""
        UPDATE explanations SET chain_status = ?, shap_tx_id = COALESCE(?, shap_tx_id)
        WHERE claim_ref = ?
        """, (chain_status, tx_id, claim_ref))
    conn.close()


def get_claim(insurer_id: str, claim_ref: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single claim by claim_ref."""
    init_db(insurer_id)
    if is_postgres_available():
        try:
            conn = _get_pg_conn(insurer_id)
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM claims WHERE claim_ref = %s", (claim_ref,))
                row = cur.fetchone()
                if row:
                    cols = [desc[0] for desc in cur.description]
                    res = dict(zip(cols, row))
                    if isinstance(res.get("claim_data"), str):
                        res["claim_data"] = json.loads(res["claim_data"])
                    if isinstance(res.get("features"), str):
                        res["features"] = json.loads(res["features"])
                    conn.close()
                    return res
            conn.close()
        except Exception:
            pass

    conn = _get_sqlite_conn(insurer_id)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM claims WHERE claim_ref = ?", (claim_ref,))
    row = cursor.fetchone()
    conn.close()
    if row:
        res = dict(row)
        res["claim_data"] = json.loads(res["claim_data"])
        res["features"] = json.loads(res["features"])
        return res
    return None


def list_claims(insurer_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Lists recent claims for the specified insurer."""
    init_db(insurer_id)
    if is_postgres_available():
        try:
            conn = _get_pg_conn(insurer_id)
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM claims ORDER BY created_at DESC LIMIT %s", (limit,))
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
                results = []
                for row in rows:
                    d = dict(zip(cols, row))
                    if isinstance(d.get("claim_data"), str):
                        d["claim_data"] = json.loads(d["claim_data"])
                    if isinstance(d.get("features"), str):
                        d["features"] = json.loads(d["features"])
                    results.append(d)
                conn.close()
                return results
        except Exception:
            pass

    conn = _get_sqlite_conn(insurer_id)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM claims ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["claim_data"] = json.loads(d["claim_data"])
        d["features"] = json.loads(d["features"])
        results.append(d)
    return results


def get_explanation(insurer_id: str, claim_ref: str) -> Optional[Dict[str, Any]]:
    """Retrieves stored SHAP explanation for a claim."""
    init_db(insurer_id)
    if is_postgres_available():
        try:
            conn = _get_pg_conn(insurer_id)
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM explanations WHERE claim_ref = %s", (claim_ref,))
                row = cur.fetchone()
                if row:
                    cols = [desc[0] for desc in cur.description]
                    res = dict(zip(cols, row))
                    if isinstance(res.get("shap_json"), str):
                        res["shap_json"] = json.loads(res["shap_json"])
                    conn.close()
                    return res
            conn.close()
        except Exception:
            pass

    conn = _get_sqlite_conn(insurer_id)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM explanations WHERE claim_ref = ?", (claim_ref,))
    row = cursor.fetchone()
    conn.close()
    if row:
        res = dict(row)
        res["shap_json"] = json.loads(res["shap_json"])
        return res
    return None


def log_audit(insurer_id: str, claim_ref: str, check_type: str, result: str):
    """Records an audit verification result (CLAIM | EXPLANATION | MODEL | CONSISTENCY)."""
    init_db(insurer_id)
    now_str = datetime.utcnow().isoformat() + "Z"

    if is_postgres_available():
        try:
            conn = _get_pg_conn(insurer_id)
            with conn.cursor() as cur:
                cur.execute("""
                INSERT INTO audit_log (claim_ref, check_type, result, checked_at)
                VALUES (%s, %s, %s, %s)
                """, (claim_ref, check_type, result, now_str))
            conn.commit()
            conn.close()
            return
        except Exception:
            pass

    conn = _get_sqlite_conn(insurer_id)
    with conn:
        conn.execute("""
        INSERT INTO audit_log (claim_ref, check_type, result, checked_at)
        VALUES (?, ?, ?, ?)
        """, (claim_ref, check_type, result, now_str))
    conn.close()


def get_audit_logs(insurer_id: str, claim_ref: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves recent audit logs."""
    init_db(insurer_id)
    if is_postgres_available():
        try:
            conn = _get_pg_conn(insurer_id)
            with conn.cursor() as cur:
                if claim_ref:
                    cur.execute("SELECT * FROM audit_log WHERE claim_ref = %s ORDER BY checked_at DESC LIMIT %s", (claim_ref, limit))
                else:
                    cur.execute("SELECT * FROM audit_log ORDER BY checked_at DESC LIMIT %s", (limit,))
                rows = cur.fetchall()
                cols = [desc[0] for desc in cur.description]
                conn.close()
                return [dict(zip(cols, r)) for r in rows]
        except Exception:
            pass

    conn = _get_sqlite_conn(insurer_id)
    cursor = conn.cursor()
    if claim_ref:
        cursor.execute("SELECT * FROM audit_log WHERE claim_ref = ? ORDER BY checked_at DESC LIMIT ?", (claim_ref, limit))
    else:
        cursor.execute("SELECT * FROM audit_log ORDER BY checked_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# =============================================================================
# Tamper Simulation & Restore Functions (Section 11)
# =============================================================================

def tamper_claim(insurer_id: str, claim_ref: str, new_indemnity: float) -> Dict[str, Any]:
    """
    Simulates malicious tampering of a claim row in the local DB.
    Modifies net_indemnity and updates claim_data_canonical without changing on-chain hash.
    """
    claim = get_claim(insurer_id, claim_ref)
    if not claim:
        raise ValueError(f"Claim '{claim_ref}' not found")

    # Store backup if not already stored
    backup_key = f"{insurer_id}:{claim_ref}"
    if backup_key not in _BACKUP_STORE:
        _BACKUP_STORE[backup_key] = {
            "claim_data_canonical": claim["claim_data_canonical"],
            "claim_data": claim["claim_data"]
        }

    c_data = claim["claim_data"]
    c_data["net_indemnity"] = new_indemnity

    # Re-serialize canonical with tampered amount
    # (Notice: claim_hash on row/blockchain is NOT changed, creating the integrity violation)
    new_canonical = json.dumps(c_data, sort_keys=True, separators=(',', ':'))

    if is_postgres_available():
        try:
            conn = _get_pg_conn(insurer_id)
            with conn.cursor() as cur:
                cur.execute("""
                UPDATE claims SET claim_data = %s, claim_data_canonical = %s WHERE claim_ref = %s
                """, (json.dumps(c_data), new_canonical, claim_ref))
            conn.commit()
            conn.close()
            return {"claim_ref": claim_ref, "tampered_indemnity": new_indemnity, "status": "TAMPERED"}
        except Exception:
            pass

    conn = _get_sqlite_conn(insurer_id)
    with conn:
        conn.execute("""
        UPDATE claims SET claim_data = ?, claim_data_canonical = ? WHERE claim_ref = ?
        """, (json.dumps(c_data), new_canonical, claim_ref))
    conn.close()
    return {"claim_ref": claim_ref, "tampered_indemnity": new_indemnity, "status": "TAMPERED"}


def tamper_explanation(insurer_id: str, claim_ref: str, feature_name: str, new_value: float) -> Dict[str, Any]:
    """
    Simulates tampering of a SHAP explanation value in the local DB.
    """
    exp = get_explanation(insurer_id, claim_ref)
    if not exp:
        raise ValueError(f"No explanation found for claim '{claim_ref}'")

    backup_key = f"exp:{insurer_id}:{claim_ref}"
    if backup_key not in _BACKUP_STORE:
        _BACKUP_STORE[backup_key] = {
            "shap_canonical": exp["shap_canonical"],
            "shap_json": exp["shap_json"]
        }

    s_data = exp["shap_json"]
    if "feature_contributions" in s_data:
        s_data["feature_contributions"][feature_name] = new_value

    new_canonical = json.dumps(s_data, sort_keys=True, separators=(',', ':'))

    if is_postgres_available():
        try:
            conn = _get_pg_conn(insurer_id)
            with conn.cursor() as cur:
                cur.execute("""
                UPDATE explanations SET shap_json = %s, shap_canonical = %s WHERE claim_ref = %s
                """, (json.dumps(s_data), new_canonical, claim_ref))
            conn.commit()
            conn.close()
            return {"claim_ref": claim_ref, "feature": feature_name, "tampered_value": new_value, "status": "TAMPERED"}
        except Exception:
            pass

    conn = _get_sqlite_conn(insurer_id)
    with conn:
        conn.execute("""
        UPDATE explanations SET shap_json = ?, shap_canonical = ? WHERE claim_ref = ?
        """, (json.dumps(s_data), new_canonical, claim_ref))
    conn.close()
    return {"claim_ref": claim_ref, "feature": feature_name, "tampered_value": new_value, "status": "TAMPERED"}


def restore_claim(insurer_id: str, claim_ref: str) -> Dict[str, Any]:
    """Restores the original untampered claim and explanation values."""
    restored = []
    c_backup_key = f"{insurer_id}:{claim_ref}"
    if c_backup_key in _BACKUP_STORE:
        orig = _BACKUP_STORE[c_backup_key]
        if is_postgres_available():
            try:
                conn = _get_pg_conn(insurer_id)
                with conn.cursor() as cur:
                    cur.execute("UPDATE claims SET claim_data = %s, claim_data_canonical = %s WHERE claim_ref = %s",
                                (json.dumps(orig["claim_data"]), orig["claim_data_canonical"], claim_ref))
                conn.commit()
                conn.close()
            except Exception:
                pass
        conn = _get_sqlite_conn(insurer_id)
        with conn:
            conn.execute("UPDATE claims SET claim_data = ?, claim_data_canonical = ? WHERE claim_ref = ?",
                         (json.dumps(orig["claim_data"]), orig["claim_data_canonical"], claim_ref))
        conn.close()
        del _BACKUP_STORE[c_backup_key]
        restored.append("claim")

    e_backup_key = f"exp:{insurer_id}:{claim_ref}"
    if e_backup_key in _BACKUP_STORE:
        orig = _BACKUP_STORE[e_backup_key]
        if is_postgres_available():
            try:
                conn = _get_pg_conn(insurer_id)
                with conn.cursor() as cur:
                    cur.execute("UPDATE explanations SET shap_json = %s, shap_canonical = %s WHERE claim_ref = %s",
                                (json.dumps(orig["shap_json"]), orig["shap_canonical"], claim_ref))
                conn.commit()
                conn.close()
            except Exception:
                pass
        conn = _get_sqlite_conn(insurer_id)
        with conn:
            conn.execute("UPDATE explanations SET shap_json = ?, shap_canonical = ? WHERE claim_ref = ?",
                         (json.dumps(orig["shap_json"]), orig["shap_canonical"], claim_ref))
        conn.close()
        del _BACKUP_STORE[e_backup_key]
        restored.append("explanation")

    return {"claim_ref": claim_ref, "restored_components": restored, "status": "RESTORED"}
