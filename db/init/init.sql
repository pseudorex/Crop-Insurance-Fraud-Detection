-- =============================================================================
-- Crop Insurance Fraud Detection - Multi-Tenant Database Initialization
-- Provisions 6 isolated databases for Insurer 1 through 6 with schemas and roles
-- Note: CREATE DATABASE must run outside transaction blocks in PostgreSQL
-- =============================================================================

-- Insurer 1
CREATE USER insurer1_user WITH PASSWORD 'InsurerPass2026!';
CREATE DATABASE insurer1_db OWNER insurer1_user;
\c insurer1_db
CREATE TABLE IF NOT EXISTS claims (
    claim_id               UUID PRIMARY KEY,
    claim_ref              TEXT UNIQUE NOT NULL,
    claim_data_canonical   TEXT NOT NULL,
    claim_data             JSONB NOT NULL,
    features               JSONB NOT NULL,
    model_version          TEXT NOT NULL,
    fraud_score            NUMERIC(8,6) NOT NULL,
    risk_label             TEXT NOT NULL CHECK (risk_label IN ('HIGH','LOW')),
    claim_hash             CHAR(64) NOT NULL,
    claim_tx_id            TEXT,
    chain_status           TEXT NOT NULL DEFAULT 'PENDING' CHECK (chain_status IN ('PENDING','ANCHORED','FAILED')),
    status                 TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS explanations (
    claim_ref        TEXT PRIMARY KEY REFERENCES claims(claim_ref) ON DELETE CASCADE,
    shap_canonical   TEXT NOT NULL,
    shap_json        JSONB NOT NULL,
    shap_hash        CHAR(64) NOT NULL,
    shap_tx_id       TEXT,
    chain_status     TEXT NOT NULL DEFAULT 'PENDING',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    claim_ref   TEXT,
    check_type  TEXT,
    result      TEXT,
    checked_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_claims_ref ON claims(claim_ref);
CREATE INDEX IF NOT EXISTS idx_claims_risk ON claims(risk_label);
CREATE INDEX IF NOT EXISTS idx_audit_ref ON audit_log(claim_ref);
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO insurer1_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO insurer1_user;

-- Insurer 2
CREATE USER insurer2_user WITH PASSWORD 'InsurerPass2026!';
CREATE DATABASE insurer2_db OWNER insurer2_user;
\c insurer2_db
CREATE TABLE IF NOT EXISTS claims (
    claim_id               UUID PRIMARY KEY,
    claim_ref              TEXT UNIQUE NOT NULL,
    claim_data_canonical   TEXT NOT NULL,
    claim_data             JSONB NOT NULL,
    features               JSONB NOT NULL,
    model_version          TEXT NOT NULL,
    fraud_score            NUMERIC(8,6) NOT NULL,
    risk_label             TEXT NOT NULL CHECK (risk_label IN ('HIGH','LOW')),
    claim_hash             CHAR(64) NOT NULL,
    claim_tx_id            TEXT,
    chain_status           TEXT NOT NULL DEFAULT 'PENDING' CHECK (chain_status IN ('PENDING','ANCHORED','FAILED')),
    status                 TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS explanations (
    claim_ref        TEXT PRIMARY KEY REFERENCES claims(claim_ref) ON DELETE CASCADE,
    shap_canonical   TEXT NOT NULL,
    shap_json        JSONB NOT NULL,
    shap_hash        CHAR(64) NOT NULL,
    shap_tx_id       TEXT,
    chain_status     TEXT NOT NULL DEFAULT 'PENDING',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    claim_ref   TEXT,
    check_type  TEXT,
    result      TEXT,
    checked_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_claims_ref ON claims(claim_ref);
CREATE INDEX IF NOT EXISTS idx_claims_risk ON claims(risk_label);
CREATE INDEX IF NOT EXISTS idx_audit_ref ON audit_log(claim_ref);
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO insurer2_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO insurer2_user;

-- Insurer 3
CREATE USER insurer3_user WITH PASSWORD 'InsurerPass2026!';
CREATE DATABASE insurer3_db OWNER insurer3_user;
\c insurer3_db
CREATE TABLE IF NOT EXISTS claims (
    claim_id               UUID PRIMARY KEY,
    claim_ref              TEXT UNIQUE NOT NULL,
    claim_data_canonical   TEXT NOT NULL,
    claim_data             JSONB NOT NULL,
    features               JSONB NOT NULL,
    model_version          TEXT NOT NULL,
    fraud_score            NUMERIC(8,6) NOT NULL,
    risk_label             TEXT NOT NULL CHECK (risk_label IN ('HIGH','LOW')),
    claim_hash             CHAR(64) NOT NULL,
    claim_tx_id            TEXT,
    chain_status           TEXT NOT NULL DEFAULT 'PENDING' CHECK (chain_status IN ('PENDING','ANCHORED','FAILED')),
    status                 TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS explanations (
    claim_ref        TEXT PRIMARY KEY REFERENCES claims(claim_ref) ON DELETE CASCADE,
    shap_canonical   TEXT NOT NULL,
    shap_json        JSONB NOT NULL,
    shap_hash        CHAR(64) NOT NULL,
    shap_tx_id       TEXT,
    chain_status     TEXT NOT NULL DEFAULT 'PENDING',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    claim_ref   TEXT,
    check_type  TEXT,
    result      TEXT,
    checked_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_claims_ref ON claims(claim_ref);
CREATE INDEX IF NOT EXISTS idx_claims_risk ON claims(risk_label);
CREATE INDEX IF NOT EXISTS idx_audit_ref ON audit_log(claim_ref);
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO insurer3_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO insurer3_user;

-- Insurer 4
CREATE USER insurer4_user WITH PASSWORD 'InsurerPass2026!';
CREATE DATABASE insurer4_db OWNER insurer4_user;
\c insurer4_db
CREATE TABLE IF NOT EXISTS claims (
    claim_id               UUID PRIMARY KEY,
    claim_ref              TEXT UNIQUE NOT NULL,
    claim_data_canonical   TEXT NOT NULL,
    claim_data             JSONB NOT NULL,
    features               JSONB NOT NULL,
    model_version          TEXT NOT NULL,
    fraud_score            NUMERIC(8,6) NOT NULL,
    risk_label             TEXT NOT NULL CHECK (risk_label IN ('HIGH','LOW')),
    claim_hash             CHAR(64) NOT NULL,
    claim_tx_id            TEXT,
    chain_status           TEXT NOT NULL DEFAULT 'PENDING' CHECK (chain_status IN ('PENDING','ANCHORED','FAILED')),
    status                 TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS explanations (
    claim_ref        TEXT PRIMARY KEY REFERENCES claims(claim_ref) ON DELETE CASCADE,
    shap_canonical   TEXT NOT NULL,
    shap_json        JSONB NOT NULL,
    shap_hash        CHAR(64) NOT NULL,
    shap_tx_id       TEXT,
    chain_status     TEXT NOT NULL DEFAULT 'PENDING',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    claim_ref   TEXT,
    check_type  TEXT,
    result      TEXT,
    checked_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_claims_ref ON claims(claim_ref);
CREATE INDEX IF NOT EXISTS idx_claims_risk ON claims(risk_label);
CREATE INDEX IF NOT EXISTS idx_audit_ref ON audit_log(claim_ref);
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO insurer4_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO insurer4_user;

-- Insurer 5
CREATE USER insurer5_user WITH PASSWORD 'InsurerPass2026!';
CREATE DATABASE insurer5_db OWNER insurer5_user;
\c insurer5_db
CREATE TABLE IF NOT EXISTS claims (
    claim_id               UUID PRIMARY KEY,
    claim_ref              TEXT UNIQUE NOT NULL,
    claim_data_canonical   TEXT NOT NULL,
    claim_data             JSONB NOT NULL,
    features               JSONB NOT NULL,
    model_version          TEXT NOT NULL,
    fraud_score            NUMERIC(8,6) NOT NULL,
    risk_label             TEXT NOT NULL CHECK (risk_label IN ('HIGH','LOW')),
    claim_hash             CHAR(64) NOT NULL,
    claim_tx_id            TEXT,
    chain_status           TEXT NOT NULL DEFAULT 'PENDING' CHECK (chain_status IN ('PENDING','ANCHORED','FAILED')),
    status                 TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS explanations (
    claim_ref        TEXT PRIMARY KEY REFERENCES claims(claim_ref) ON DELETE CASCADE,
    shap_canonical   TEXT NOT NULL,
    shap_json        JSONB NOT NULL,
    shap_hash        CHAR(64) NOT NULL,
    shap_tx_id       TEXT,
    chain_status     TEXT NOT NULL DEFAULT 'PENDING',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    claim_ref   TEXT,
    check_type  TEXT,
    result      TEXT,
    checked_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_claims_ref ON claims(claim_ref);
CREATE INDEX IF NOT EXISTS idx_claims_risk ON claims(risk_label);
CREATE INDEX IF NOT EXISTS idx_audit_ref ON audit_log(claim_ref);
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO insurer5_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO insurer5_user;

-- Insurer 6
CREATE USER insurer6_user WITH PASSWORD 'InsurerPass2026!';
CREATE DATABASE insurer6_db OWNER insurer6_user;
\c insurer6_db
CREATE TABLE IF NOT EXISTS claims (
    claim_id               UUID PRIMARY KEY,
    claim_ref              TEXT UNIQUE NOT NULL,
    claim_data_canonical   TEXT NOT NULL,
    claim_data             JSONB NOT NULL,
    features               JSONB NOT NULL,
    model_version          TEXT NOT NULL,
    fraud_score            NUMERIC(8,6) NOT NULL,
    risk_label             TEXT NOT NULL CHECK (risk_label IN ('HIGH','LOW')),
    claim_hash             CHAR(64) NOT NULL,
    claim_tx_id            TEXT,
    chain_status           TEXT NOT NULL DEFAULT 'PENDING' CHECK (chain_status IN ('PENDING','ANCHORED','FAILED')),
    status                 TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS explanations (
    claim_ref        TEXT PRIMARY KEY REFERENCES claims(claim_ref) ON DELETE CASCADE,
    shap_canonical   TEXT NOT NULL,
    shap_json        JSONB NOT NULL,
    shap_hash        CHAR(64) NOT NULL,
    shap_tx_id       TEXT,
    chain_status     TEXT NOT NULL DEFAULT 'PENDING',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    claim_ref   TEXT,
    check_type  TEXT,
    result      TEXT,
    checked_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_claims_ref ON claims(claim_ref);
CREATE INDEX IF NOT EXISTS idx_claims_risk ON claims(risk_label);
CREATE INDEX IF NOT EXISTS idx_audit_ref ON audit_log(claim_ref);
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO insurer6_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO insurer6_user;
