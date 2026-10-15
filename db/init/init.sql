-- =============================================================================
-- Crop Insurance Fraud Detection - Multi-Tenant Database Initialization
-- Provisions 6 isolated databases for Insurer 1 through 6 with schemas and roles
-- =============================================================================

-- Step 1: Create 6 Insurer Users & Databases
DO $$
DECLARE
    i INT;
    db_name TEXT;
    user_name TEXT;
BEGIN
    FOR i IN 1..6 LOOP
        db_name := 'insurer' || i || '_db';
        user_name := 'insurer' || i || '_user';

        -- Create user if not exists
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = user_name) THEN
            EXECUTE format('CREATE USER %I WITH PASSWORD %L', user_name, 'InsurerPass2026!');
        END IF;

        -- Create database if not exists
        IF NOT EXISTS (SELECT FROM pg_database WHERE datname = db_name) THEN
            EXECUTE format('CREATE DATABASE %I OWNER %I', db_name, user_name);
        END IF;
    END LOOP;
END $$;

-- Step 2: Provision Tables and Permissions in each Database
-- (PostgreSQL init entrypoint connects per DB or runs dynamic table creation)

\c insurer1_db
\ir init_tables.sql

\c insurer2_db
\ir init_tables.sql

\c insurer3_db
\ir init_tables.sql

\c insurer4_db
\ir init_tables.sql

\c insurer5_db
\ir init_tables.sql

\c insurer6_db
\ir init_tables.sql
