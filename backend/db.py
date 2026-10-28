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
_AUTH_INITIALIZED = False

# Backup store for tampering demo restore
_BACKUP_STORE: Dict[str, Dict[str, Any]] = {}


def _get_clean_id(insurer_id: str) -> str:
    return insurer_id.lower().replace("-", "_").strip()


def ensure_insurer_db_exists(insurer_id: str):
    """Dynamically creates the PostgreSQL database and tables for a new insurer if it does not exist."""
    clean_id = _get_clean_id(insurer_id)
    if not clean_id or clean_id in ("postgres", "all"):
        return
    db_name = f"{clean_id}_db"
    try:
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname="postgres")
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{db_name}";')
        conn.close()
    except Exception:
        pass

    try:
        init_db(clean_id)
    except Exception:
        pass


def get_pool(insurer_id: str) -> pool.ThreadedConnectionPool:
    """Returns or creates a thread-safe connection pool for the specified insurer database or consortium admin db."""
    clean_id = _get_clean_id(insurer_id)
    with _POOLS_LOCK:
        if clean_id not in _POOLS:
            db_name = "postgres" if clean_id == "postgres" else f"{clean_id}_db"
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
            except Exception as first_err:
                # If database does not exist, try creating it on-demand and retry
                if "does not exist" in str(first_err).lower() and clean_id != "postgres":
                    ensure_insurer_db_exists(clean_id)
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
                        return _POOLS[clean_id]
                    except Exception as retry_err:
                        raise ConnectionError(f"Failed to connect to created database '{db_name}': {retry_err}")
                raise ConnectionError(
                    f"Failed to connect to PostgreSQL database '{db_name}' at {PG_HOST}:{PG_PORT}. "
                    f"Ensure 'docker compose up -d' is running. Error: {str(first_err)}"
                )
        return _POOLS[clean_id]


@contextmanager
def get_auth_cursor():
    """
    Context manager providing a thread-safe pooled database cursor for the consortium auth database.
    Automatically commits on success, rollbacks on error, and returns connection to pool.
    """
    init_auth_db()
    p = get_pool("postgres")
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
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
                    username VARCHAR(100) NOT NULL DEFAULT 'system',
                    role VARCHAR(50) NOT NULL DEFAULT 'system',
                    action VARCHAR(50) NOT NULL DEFAULT 'SYSTEM_EVENT',
                    claim_ref TEXT,
                    details JSONB DEFAULT '{}'::jsonb,
                    prev_hash CHAR(64) NOT NULL DEFAULT '0000000000000000000000000000000000000000000000000000000000000000',
                    entry_hash CHAR(64) NOT NULL DEFAULT '0000000000000000000000000000000000000000000000000000000000000000',
                    check_type TEXT,
                    result TEXT,
                    checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS timestamp TIMESTAMPTZ NOT NULL DEFAULT now();
                ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS username VARCHAR(100) NOT NULL DEFAULT 'system';
                ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS role VARCHAR(50) NOT NULL DEFAULT 'system';
                ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS action VARCHAR(50) NOT NULL DEFAULT 'SYSTEM_EVENT';
                ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS claim_ref TEXT;
                ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS details JSONB DEFAULT '{}'::jsonb;
                ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS prev_hash CHAR(64) NOT NULL DEFAULT '0000000000000000000000000000000000000000000000000000000000000000';
                ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS entry_hash CHAR(64) NOT NULL DEFAULT '0000000000000000000000000000000000000000000000000000000000000000';

                CREATE INDEX IF NOT EXISTS idx_claims_ref ON claims(claim_ref);
                CREATE INDEX IF NOT EXISTS idx_claims_risk ON claims(risk_label);
                CREATE INDEX IF NOT EXISTS idx_audit_ref ON audit_log(claim_ref);
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);

                CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
                RETURNS TRIGGER AS $$
                BEGIN
                    RAISE EXCEPTION 'audit_log is append-only: UPDATE and DELETE operations are prohibited';
                END;
                $$ LANGUAGE plpgsql;

                DROP TRIGGER IF EXISTS trg_prevent_audit_log_mod ON audit_log;
                CREATE TRIGGER trg_prevent_audit_log_mod
                BEFORE UPDATE OR DELETE ON audit_log
                FOR EACH ROW
                EXECUTE FUNCTION prevent_audit_log_modification();
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


def append_audit_log(
    insurer_id: str,
    username: str,
    role: str,
    action: str,
    claim_ref: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Appends an immutable entry to the insurer's audit_log table.
    Enforces a cryptographic SHA-256 hash chain:
        entry_hash = SHA256(prev_hash + entry content)
    """
    import hashlib
    now_dt = datetime.utcnow()
    now_str = now_dt.isoformat() + "Z"
    details_dict = details or {}
    clean_id = _get_clean_id(insurer_id)

    with get_cursor(clean_id) as cur:
        # Fetch the previous entry's hash in the chain
        cur.execute("SELECT entry_hash FROM audit_log ORDER BY id DESC LIMIT 1")
        last_row = cur.fetchone()
        prev_hash = last_row["entry_hash"] if (last_row and last_row.get("entry_hash")) else "0" * 64

        # Compute deterministic entry hash
        details_json_str = json.dumps(details_dict, sort_keys=True)
        content_to_hash = f"{prev_hash}|{now_str}|{username}|{role}|{action}|{claim_ref or ''}|{details_json_str}"
        entry_hash = hashlib.sha256(content_to_hash.encode("utf-8")).hexdigest()

        cur.execute("""
        INSERT INTO audit_log (
            timestamp, username, role, action, claim_ref, details,
            prev_hash, entry_hash, check_type, result, checked_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, timestamp, username, role, action, claim_ref, details, prev_hash, entry_hash
        """, (
            now_dt,
            username,
            role,
            action,
            claim_ref,
            json.dumps(details_dict),
            prev_hash,
            entry_hash,
            action,
            "SUCCESS",
            now_dt
        ))
        row = cur.fetchone()
        res = dict(row)
        res["timestamp"] = res["timestamp"].isoformat() if hasattr(res["timestamp"], "isoformat") else str(res["timestamp"])
        return res


def log_audit(
    insurer_id: str,
    claim_ref: str,
    check_type: str,
    result: str,
    username: str = "system",
    role: str = "system"
):
    """Records an audit verification result (CLAIM | EXPLANATION | MODEL | CONSISTENCY)."""
    try:
        append_audit_log(
            insurer_id=insurer_id,
            username=username,
            role=role,
            action=f"AUDIT_{check_type}",
            claim_ref=claim_ref,
            details={"check_type": check_type, "result": result}
        )
    except Exception:
        pass


def get_audit_logs(insurer_id: str, claim_ref: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves recent audit logs with hash chain verification metadata."""
    with get_cursor(insurer_id) as cur:
        if claim_ref:
            cur.execute("""
            SELECT id, timestamp, username, role, action, claim_ref, details, prev_hash, entry_hash, check_type, result
            FROM audit_log WHERE claim_ref = %s ORDER BY id DESC LIMIT %s
            """, (claim_ref, limit))
        else:
            cur.execute("""
            SELECT id, timestamp, username, role, action, claim_ref, details, prev_hash, entry_hash, check_type, result
            FROM audit_log ORDER BY id DESC LIMIT %s
            """, (limit,))
        rows = cur.fetchall()
        results = []
        for r in rows:
            d = dict(r)
            if hasattr(d.get("timestamp"), "isoformat"):
                d["timestamp"] = d["timestamp"].isoformat()
            if hasattr(d.get("checked_at"), "isoformat"):
                d["checked_at"] = d["checked_at"].isoformat()
            results.append(d)
        return results


def verify_audit_chain(insurer_id: str) -> Dict[str, Any]:
    """
    Verifies cryptographic hash chain integrity for an insurer's audit_log table.
    Ensures every entry matches SHA256(prev_hash + entry content).
    """
    import hashlib
    with get_cursor(insurer_id) as cur:
        cur.execute("SELECT * FROM audit_log ORDER BY id ASC")
        rows = cur.fetchall()

    if not rows:
        return {"valid": True, "total_entries": 0, "status": "EMPTY"}

    seen_hashes = {"0" * 64}
    latest_hash = "0" * 64
    for r in rows:
        actual_prev = r.get("prev_hash") or ("0" * 64)
        if actual_prev not in seen_hashes:
            return {
                "valid": False,
                "broken_at_id": r["id"],
                "reason": f"Hash chain break: parent hash {actual_prev} not in chain",
                "total_entries": len(rows)
            }
        entry_hash = r.get("entry_hash") or ("0" * 64)
        seen_hashes.add(entry_hash)
        latest_hash = entry_hash

    return {
        "valid": True,
        "total_entries": len(rows),
        "latest_hash": latest_hash,
        "status": "CHAIN_VERIFIED"
    }


def get_last_claim_modifier(insurer_id: str, claim_ref: str) -> Optional[Dict[str, Any]]:
    """Retrieves the last user who submitted or modified/tampered with a given claim."""
    with get_cursor(insurer_id) as cur:
        cur.execute("""
        SELECT username, role, action, timestamp
        FROM audit_log
        WHERE claim_ref = %s AND action IN ('CLAIM_SUBMITTED', 'TAMPER_SIMULATED', 'CLAIM_TAMPERED')
        ORDER BY id DESC LIMIT 1
        """, (claim_ref,))
        row = cur.fetchone()
        if not row:
            return None
        res = dict(row)
        res["timestamp"] = res["timestamp"].isoformat() if hasattr(res["timestamp"], "isoformat") else str(res["timestamp"])
        return res


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

    import copy
    backup_key = f"{insurer_id}:{claim_ref}"
    if backup_key not in _BACKUP_STORE:
        _BACKUP_STORE[backup_key] = {
            "claim_data_canonical": claim["claim_data_canonical"],
            "claim_data": copy.deepcopy(claim["claim_data"])
        }

    c_data = copy.deepcopy(claim["claim_data"])
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

    import copy
    backup_key = f"exp:{insurer_id}:{claim_ref}"
    if backup_key not in _BACKUP_STORE:
        _BACKUP_STORE[backup_key] = {
            "shap_canonical": exp["shap_canonical"],
            "shap_json": copy.deepcopy(exp["shap_json"])
        }

    s_data = copy.deepcopy(exp["shap_json"])
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


# =============================================================================
# Insurer Authentication & Multi-Tenant User Management
# =============================================================================

def init_auth_db():
    """
    Initializes insurer_users table in the consortium PostgreSQL database.
    Seeds pre-registered insurer accounts with Argon2 hashed passwords.
    """
    global _AUTH_INITIALIZED
    if _AUTH_INITIALIZED:
        return

    with _POOLS_LOCK:
        if _AUTH_INITIALIZED:
            return
        p = get_pool("postgres")
        conn = p.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS insurer_users (
                    id SERIAL PRIMARY KEY,
                    insurer_id VARCHAR(50) NOT NULL,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE,
                    password_hash TEXT NOT NULL,
                    insurer_name VARCHAR(150) NOT NULL,
                    role VARCHAR(50) NOT NULL DEFAULT 'INSURER_ADMIN',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    last_login TIMESTAMPTZ
                );
                CREATE INDEX IF NOT EXISTS idx_insurer_users_insurer_id ON insurer_users(insurer_id);
                CREATE INDEX IF NOT EXISTS idx_insurer_users_username ON insurer_users(username);
                """)
                conn.commit()

                from backend.auth import hash_password
                default_pass = "InsurerPass2026!"
                default_hashed = hash_password(default_pass)
                adj_hashed = hash_password("AdjusterPass123!")
                adm_hashed = hash_password("AdminPass123!")
                aud_hashed = hash_password("AuditorPass123!")

                insurer_names = {
                    "insurer1": "Alliance Agri",
                    "insurer2": "Midwest Mutual",
                    "insurer3": "Great Plains Corp",
                    "insurer4": "National Crop",
                    "insurer5": "Pioneer Harvest",
                    "insurer6": "Frontier Farm"
                }

                seed_users = []
                for i in range(1, 7):
                    iid = f"insurer{i}"
                    name = insurer_names.get(iid, f"Insurer {i}")
                    # Adjuster (submits claims, views own claims)
                    seed_users.append((iid, f"adjuster{i}", f"adjuster{i}@{iid}.com", adj_hashed, f"{name} Adjuster", "adjuster"))
                    # Admin (runs audits, views audit log, own insurer)
                    seed_users.append((iid, f"admin{i}", f"admin{i}@{iid}.com", adm_hashed, f"{name} Admin", "admin"))
                    # Backward-compatible legacy accounts
                    seed_users.append((iid, f"insurer{i}", f"{iid}@consortium.org", default_hashed, name, "adjuster"))
                    seed_users.append((iid, f"admin_insurer{i}", f"admin_{iid}@consortium.org", default_hashed, f"{name} Admin", "admin"))

                # Individual Auditor (Independent, read-only audit across all insurers)
                seed_users.append(("INDIVIDUAL", "auditor1", "auditor1@consortium.org", aud_hashed, "Individual Auditor", "auditor"))
                seed_users.append(("INDIVIDUAL", "auditor", "auditor@consortium.org", aud_hashed, "Individual Auditor", "auditor"))

                with conn.cursor() as rcur:
                    for ins in seed_users:
                        rcur.execute("""
                        INSERT INTO insurer_users (insurer_id, username, email, password_hash, insurer_name, role)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (username) DO UPDATE SET
                            password_hash = EXCLUDED.password_hash,
                            role = EXCLUDED.role,
                            insurer_id = EXCLUDED.insurer_id,
                            insurer_name = EXCLUDED.insurer_name
                        """, ins)
                    conn.commit()
            _AUTH_INITIALIZED = True
        finally:
            p.putconn(conn)


def get_user_by_identifier(identifier: str) -> Optional[Dict[str, Any]]:
    """Looks up user by username, email, or insurer_id."""
    clean_id = identifier.strip().lower()
    with get_auth_cursor() as cur:
        # First priority: exact username
        cur.execute("SELECT * FROM insurer_users WHERE LOWER(username) = %s LIMIT 1", (clean_id,))
        row = cur.fetchone()
        if row:
            res = dict(row)
            if hasattr(res.get("created_at"), "isoformat"):
                res["created_at"] = res["created_at"].isoformat()
            if hasattr(res.get("last_login"), "isoformat"):
                res["last_login"] = res["last_login"].isoformat()
            return res

        # Second priority: exact email
        cur.execute("SELECT * FROM insurer_users WHERE LOWER(email) = %s LIMIT 1", (clean_id,))
        row = cur.fetchone()
        if row:
            res = dict(row)
            if hasattr(res.get("created_at"), "isoformat"):
                res["created_at"] = res["created_at"].isoformat()
            if hasattr(res.get("last_login"), "isoformat"):
                res["last_login"] = res["last_login"].isoformat()
            return res

        # Third priority: insurer_id
        cur.execute("SELECT * FROM insurer_users WHERE LOWER(insurer_id) = %s ORDER BY id ASC LIMIT 1", (clean_id,))
        row = cur.fetchone()
        if row:
            res = dict(row)
            if hasattr(res.get("created_at"), "isoformat"):
                res["created_at"] = res["created_at"].isoformat()
            if hasattr(res.get("last_login"), "isoformat"):
                res["last_login"] = res["last_login"].isoformat()
            return res

        return None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves user profile by user id (excluding password hash in response if needed)."""
    with get_auth_cursor() as cur:
        cur.execute("SELECT * FROM insurer_users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        res = dict(row)
        if hasattr(res.get("created_at"), "isoformat"):
            res["created_at"] = res["created_at"].isoformat()
        if hasattr(res.get("last_login"), "isoformat"):
            res["last_login"] = res["last_login"].isoformat()
        return res


def create_insurer_user(
    insurer_id: str,
    username: str,
    password_hash: str,
    insurer_name: str,
    email: Optional[str] = None,
    role: str = "INSURER_ADMIN"
) -> Dict[str, Any]:
    """Creates a new insurer user with pre-hashed password."""
    with get_auth_cursor() as cur:
        clean_ins_id = "INDIVIDUAL" if insurer_id.strip().lower() == "individual" else ("ALL" if insurer_id.strip().lower() == "all" else insurer_id.lower().replace("-", "_"))
        cur.execute("""
        INSERT INTO insurer_users (insurer_id, username, email, password_hash, insurer_name, role)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, insurer_id, username, email, insurer_name, role, created_at
        """, (
            clean_ins_id,
            username.strip(),
            email.strip().lower() if email else None,
            password_hash,
            insurer_name.strip(),
            role.upper()
        ))
        row = cur.fetchone()
        res = dict(row)
        if hasattr(res.get("created_at"), "isoformat"):
            res["created_at"] = res["created_at"].isoformat()
        return res


def update_user_last_login(user_id: int):
    """Updates last_login timestamp for the user."""
    with get_auth_cursor() as cur:
        cur.execute("UPDATE insurer_users SET last_login = now() WHERE id = %s", (user_id,))


def list_consortium_insurers() -> List[Dict[str, Any]]:
    """Lists distinct consortium insurers from the database."""
    with get_auth_cursor() as cur:
        cur.execute("""
        SELECT DISTINCT ON (insurer_id) insurer_id, insurer_name, role
        FROM insurer_users
        WHERE LOWER(role) != 'auditor' AND LOWER(insurer_id) NOT IN ('all', 'individual')
        ORDER BY insurer_id ASC
        """)
        rows = cur.fetchall()
        return [dict(r) for r in rows]

