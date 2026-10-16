"""
Multi-Tenant PostgreSQL Database Layer for Insurers 1 through 6
Uses connection pooling (psycopg2.pool.ThreadedConnectionPool) for high concurrency,
thread-safety, and zero catalog deadlocks.

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
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = int(os.getenv("POSTGRES_PORT", "5433"))
PG_USER = os.getenv("POSTGRES_ADMIN_USER", "admin_user")
PG_PASS = os.getenv("POSTGRES_ADMIN_PASSWORD", "AdminSecure2026!")

# Threaded connection pools per insurer database: {"insurer1": pool, ...}
_POOLS: Dict[str, pool.ThreadedConnectionPool] = {}
_POOLS_LOCK = threading.RLock()

# Cache for initialized insurer databases
_INITIALIZED_INSURERS = set()

# Backup store for tampering demo restore
_BACKUP_STORE: Dict[str, Dict[str, Any]] = {}


def _get_clean_id(insurer_id: str) -> str:
    return insurer_id.lower().replace("-", "_")


def get_pool(insurer_id: str) -> pool.ThreadedConnectionPool:
    """Returns or creates a thread-safe connection pool for the specified insurer database."""
    clean_id = _get_clean_id(insurer_id)
    with _POOLS_LOCK:
        if clean_id not in _POOLS:
            db_name = f"{clean_id}_db"
            try:
                p = pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=20,
                    host=PG_HOST,
                    port=PG_PORT,
                    user=PG_USER,
                    password=PG_PASS,
                    dbname=db_name,
                    connect_timeout=5
                )
                _POOLS[clean_id] = p
            except Exception as e:
                raise ConnectionError(
                    f"Failed to connect to PostgreSQL database '{db_name}' at {PG_HOST}:{PG_PORT}. "
                    f"Ensure 'docker compose up -d' is running. Error: {str(e)}"
                )
        return _POOLS[clean_id]


@contextmanager
def get_cursor(insurer_id: str):
    """
    Context manager providing a thread-safe pooled database cursor.
    Automatically commits on success, rollbacks on error, and returns connection to pool.
    """
    init_db(insurer_id)
    p = get_pool(insurer_id)
    conn = p.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        p.putconn(conn)


def is_postgres_available() -> bool:
    """Checks if the PostgreSQL consortium container is online."""
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASS,
            dbname="postgres",
            connect_timeout=2
        )
        conn.close()
        return True
    except Exception:
        return False


def init_db(insurer_id: str):
    """
    Ensures insurer database tables are initialized.
    Runs once per insurer during process lifecycle to avoid catalog deadlocks.
    """
    clean_id = _get_clean_id(insurer_id)
    if clean_id in _INITIALIZED_INSURERS:
        return

    with _POOLS_LOCK:
        if clean_id in _INITIALIZED_INSURERS:
            return
        p = get_pool(insurer_id)
        conn = p.getconn()
        try:
            with conn.cursor() as cur:
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
                    chain_status TEXT NOT NULL DEFAULT 'PENDING' CHECK (chain_status IN ('PENDING','ANCHORED','FAILED')),
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
                CREATE INDEX IF NOT EXISTS idx_claims_ref ON claims(claim_ref);
                CREATE INDEX IF NOT EXISTS idx_claims_risk ON claims(risk_label);
                CREATE INDEX IF NOT EXISTS idx_audit_ref ON audit_log(claim_ref);
                """)
            conn.commit()
            _INITIALIZED_INSURERS.add(clean_id)
        finally:
            p.putconn(conn)


def insert_claim(insurer_id: str, claim: Dict[str, Any]) -> Dict[str, Any]:
    """Inserts a claim into the insurer's PostgreSQL database with chain_status='PENDING'."""
    now_str = datetime.utcnow().isoformat() + "Z"
    try:
        with get_cursor(insurer_id) as cur:
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
        return claim
    except psycopg2.IntegrityError as e:
        if "unique" in str(e).lower() or "claims_claim_ref_key" in str(e).lower():
            raise ValueError(f"Write-once violation: Claim reference '{claim['claim_ref']}' already exists.")
        raise


def update_claim_chain_status(insurer_id: str, claim_ref: str, chain_status: str, tx_id: Optional[str] = None):
    """Updates chain anchoring status (e.g. 'ANCHORED' or 'FAILED') and transaction id."""
    with get_cursor(insurer_id) as cur:
        cur.execute("""
        UPDATE claims SET chain_status = %s, claim_tx_id = COALESCE(%s, claim_tx_id)
        WHERE claim_ref = %s
        """, (chain_status, tx_id, claim_ref))


def insert_explanation(insurer_id: str, exp: Dict[str, Any]):
    """Stores a SHAP explanation for a fraud-flagged (HIGH risk) claim."""
    now_str = datetime.utcnow().isoformat() + "Z"
    with get_cursor(insurer_id) as cur:
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


def update_explanation_chain_status(insurer_id: str, claim_ref: str, chain_status: str, tx_id: Optional[str] = None):
    """Updates chain status of an explanation record."""
    with get_cursor(insurer_id) as cur:
        cur.execute("""
        UPDATE explanations SET chain_status = %s, shap_tx_id = COALESCE(%s, shap_tx_id)
        WHERE claim_ref = %s
        """, (chain_status, tx_id, claim_ref))


def get_claim(insurer_id: str, claim_ref: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single claim by claim_ref."""
    with get_cursor(insurer_id) as cur:
        cur.execute("SELECT * FROM claims WHERE claim_ref = %s", (claim_ref,))
        row = cur.fetchone()
        if not row:
            return None
        res = dict(row)
        if isinstance(res.get("claim_data"), str):
            res["claim_data"] = json.loads(res["claim_data"])
        if isinstance(res.get("features"), str):
            res["features"] = json.loads(res["features"])
        # Format timestamps and UUIDs as strings for JSON serialization
        res["claim_id"] = str(res["claim_id"])
        res["created_at"] = res["created_at"].isoformat() if hasattr(res["created_at"], "isoformat") else str(res["created_at"])
        res["fraud_score"] = float(res["fraud_score"])
        return res


def list_claims(insurer_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Lists recent claims for the specified insurer."""
    with get_cursor(insurer_id) as cur:
        cur.execute("SELECT * FROM claims ORDER BY created_at DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("claim_data"), str):
                d["claim_data"] = json.loads(d["claim_data"])
            if isinstance(d.get("features"), str):
                d["features"] = json.loads(d["features"])
            d["claim_id"] = str(d["claim_id"])
            d["created_at"] = d["created_at"].isoformat() if hasattr(d["created_at"], "isoformat") else str(d["created_at"])
            d["fraud_score"] = float(d["fraud_score"])
            results.append(d)
        return results


def get_explanation(insurer_id: str, claim_ref: str) -> Optional[Dict[str, Any]]:
    """Retrieves stored SHAP explanation for a claim."""
    with get_cursor(insurer_id) as cur:
        cur.execute("SELECT * FROM explanations WHERE claim_ref = %s", (claim_ref,))
        row = cur.fetchone()
        if not row:
            return None
        res = dict(row)
        if isinstance(res.get("shap_json"), str):
            res["shap_json"] = json.loads(res["shap_json"])
        res["created_at"] = res["created_at"].isoformat() if hasattr(res["created_at"], "isoformat") else str(res["created_at"])
        return res


def log_audit(insurer_id: str, claim_ref: str, check_type: str, result: str):
    """Records an audit verification result (CLAIM | EXPLANATION | MODEL | CONSISTENCY)."""
    now_str = datetime.utcnow().isoformat() + "Z"
    with get_cursor(insurer_id) as cur:
        cur.execute("""
        INSERT INTO audit_log (claim_ref, check_type, result, checked_at)
        VALUES (%s, %s, %s, %s)
        """, (claim_ref, check_type, result, now_str))


def get_audit_logs(insurer_id: str, claim_ref: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves recent audit logs."""
    with get_cursor(insurer_id) as cur:
        if claim_ref:
            cur.execute("SELECT * FROM audit_log WHERE claim_ref = %s ORDER BY checked_at DESC LIMIT %s", (claim_ref, limit))
        else:
            cur.execute("SELECT * FROM audit_log ORDER BY checked_at DESC LIMIT %s", (limit,))
        rows = cur.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["checked_at"] = d["checked_at"].isoformat() if hasattr(d["checked_at"], "isoformat") else str(d["checked_at"])
            results.append(d)
        return results


# =============================================================================
# Tamper Simulation & Restore Functions (Section 11)
# =============================================================================

def tamper_claim(insurer_id: str, claim_ref: str, new_indemnity: float) -> Dict[str, Any]:
    """
    Simulates malicious tampering of a claim row in PostgreSQL.
    Modifies net_indemnity and updates claim_data_canonical without changing on-chain hash.
    """
    claim = get_claim(insurer_id, claim_ref)
    if not claim:
        raise ValueError(f"Claim '{claim_ref}' not found in insurer '{insurer_id}' database")

    backup_key = f"{insurer_id}:{claim_ref}"
    if backup_key not in _BACKUP_STORE:
        _BACKUP_STORE[backup_key] = {
            "claim_data_canonical": claim["claim_data_canonical"],
            "claim_data": claim["claim_data"]
        }

    c_data = claim["claim_data"]
    c_data["net_indemnity"] = new_indemnity

    # Build tampered canonical JSON (deliberately causing cryptographic mismatch)
    from backend.hashing import canonical_claim_json
    new_canonical = canonical_claim_json(c_data)

    with get_cursor(insurer_id) as cur:
        cur.execute("""
        UPDATE claims SET claim_data = %s, claim_data_canonical = %s WHERE claim_ref = %s
        """, (json.dumps(c_data), new_canonical, claim_ref))

    return {"claim_ref": claim_ref, "tampered_indemnity": new_indemnity, "status": "TAMPERED"}


def tamper_explanation(insurer_id: str, claim_ref: str, feature_name: str, new_value: float) -> Dict[str, Any]:
    """Simulates tampering of a SHAP explanation value in PostgreSQL."""
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

    from backend.hashing import canonical_shap_json
    new_canonical = canonical_shap_json(s_data)

    with get_cursor(insurer_id) as cur:
        cur.execute("""
        UPDATE explanations SET shap_json = %s, shap_canonical = %s WHERE claim_ref = %s
        """, (json.dumps(s_data), new_canonical, claim_ref))

    return {"claim_ref": claim_ref, "feature": feature_name, "tampered_value": new_value, "status": "TAMPERED"}


def restore_claim(insurer_id: str, claim_ref: str) -> Dict[str, Any]:
    """Restores the original untampered claim and explanation values in PostgreSQL."""
    restored = []
    c_backup_key = f"{insurer_id}:{claim_ref}"
    if c_backup_key in _BACKUP_STORE:
        orig = _BACKUP_STORE[c_backup_key]
        with get_cursor(insurer_id) as cur:
            cur.execute("""
            UPDATE claims SET claim_data = %s, claim_data_canonical = %s WHERE claim_ref = %s
            """, (json.dumps(orig["claim_data"]), orig["claim_data_canonical"], claim_ref))
        del _BACKUP_STORE[c_backup_key]
        restored.append("claim")

    e_backup_key = f"exp:{insurer_id}:{claim_ref}"
    if e_backup_key in _BACKUP_STORE:
        orig = _BACKUP_STORE[e_backup_key]
        with get_cursor(insurer_id) as cur:
            cur.execute("""
            UPDATE explanations SET shap_json = %s, shap_canonical = %s WHERE claim_ref = %s
            """, (json.dumps(orig["shap_json"]), orig["shap_canonical"], claim_ref))
        del _BACKUP_STORE[e_backup_key]
        restored.append("explanation")

    return {"claim_ref": claim_ref, "restored_components": restored, "status": "RESTORED"}
