-- Common schema applied to insurer databases

CREATE TABLE IF NOT EXISTS claims (
    claim_id               UUID PRIMARY KEY,
    claim_ref              TEXT UNIQUE NOT NULL,
    claim_data_canonical   TEXT NOT NULL,      -- exact string that was hashed
    claim_data             JSONB NOT NULL,     -- for display and queries
    features               JSONB NOT NULL,
    model_version          TEXT NOT NULL,
    fraud_score            NUMERIC(8,6) NOT NULL,
    risk_label             TEXT NOT NULL CHECK (risk_label IN ('HIGH','LOW')),
    claim_hash             CHAR(64) NOT NULL,
    claim_tx_id            TEXT,
    chain_status           TEXT NOT NULL DEFAULT 'PENDING'
                           CHECK (chain_status IN ('PENDING','ANCHORED','FAILED')),
    status                 TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS explanations (
    claim_ref        TEXT PRIMARY KEY REFERENCES claims(claim_ref) ON DELETE CASCADE,
    shap_canonical   TEXT NOT NULL,            -- exact string that was hashed
    shap_json        JSONB NOT NULL,
    shap_hash        CHAR(64) NOT NULL,
    shap_tx_id       TEXT,
    chain_status     TEXT NOT NULL DEFAULT 'PENDING',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    claim_ref   TEXT,
    check_type  TEXT,        -- CLAIM | EXPLANATION | MODEL | CONSISTENCY
    result      TEXT,
    checked_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexing for fast query resolution
CREATE INDEX IF NOT EXISTS idx_claims_ref ON claims(claim_ref);
CREATE INDEX IF NOT EXISTS idx_claims_risk ON claims(risk_label);
CREATE INDEX IF NOT EXISTS idx_audit_ref ON audit_log(claim_ref);
