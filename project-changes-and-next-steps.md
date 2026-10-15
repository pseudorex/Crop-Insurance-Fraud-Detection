# Crop Insurance Fraud Detection: Final Changes & Next Steps

Repo: `pseudorex/Crop-Insurance-Fraud-Detection`
Scope: simplify the privacy layers, finish the blockchain integration, add per-insurer Postgres, SHAP for flagged claims only, and build a demo frontend.

> Note: this plan is based on the README and `implementation-guide.md`. Check each "remove" item against the actual code before deleting anything.

---

## 1. Where the project stands

| Phase | Status | Notes |
|---|---|---|
| 1. Environment | Done | Python, Docker, Node, EVM / Web3 |
| 2. Data preprocessing | Done | 677,150 claims, 6 insurer CSVs |
| 3. Centralized baseline | Done | XGBoost F1 0.9848 |
| 4. Federated learning (Flower) | Done | F1 0.9938 |
| 5. Differential privacy | Done | FedAvg + L2 Clip + Gaussian Noise (SecAgg removed) |
| 6. Poisoning defense | Archived | Archived to `ml/experiments/` |
| 7 & 8. Blockchain (Smart Contract) | Done | **Solidity EVM (`InsuranceAudit.sol`)** — Hyperledger Fabric removed |
| 9. Python Blockchain Client | Done | `blockchain/chain_client.py` (Web3 / EVM RPC + simulated fallback) |
| 10 to 14 | Next | Postgres databases, FastAPI backend, and React UI |

---

## 2. Final decisions at a glance

| Component | Decision |
|---|---|
| Insurers | Keep 6 (6 insurer identities, 6 local databases) |
| Federated learning | FedAvg + **clip + Gaussian noise** |
| Secure aggregation (SecAgg) | **Removed** |
| Salt / nonce | **Removed**. A random `claim_id` inside the hashed data is enough |
| Byzantine defenses (Trimmed Mean, Multi-Krum, norm filter) | **Archived to `ml/experiments/`**, out of the live pipeline |
| Blockchain Engine | **Solidity (`InsuranceAudit.sol`)** on EVM. Hyperledger Fabric completely removed. |
| Smart Contract Rules | Identity checks, write-once keys, events, SHAP only for HIGH-risk claims |
| Blockchain Client | Python Web3 / EVM RPC client (`blockchain/chain_client.py`) |
| Local DB | **Postgres 16 in Docker**, one database per insurer |
| Backend | FastAPI |
| Frontend | React (Vite) with insurer portal and auditor view |

---

## 3. What to remove, archive or change

### 3.1 Remove completely
- Salt/nonce: `generate_nonce()`, the `nonce` column, the nonce-loss policy and the schema-versioning notes.
- SecAgg code: the pairwise masking and the SecAgg server strategy.
- Private data collections: `collections_config.json` and the `--collections-config` flag in the deploy scripts.
- The FL-update hash transaction (`RegisterModelUpdate`), which only existed to support SecAgg.
- The anomaly-flag transaction (`FlagAnomalousUpdate`), which only existed to support the Byzantine defenses.
- The separate `RegisterPrediction` and `RegisterExplanation` v1 transactions. They are replaced by the new design in section 5.

### 3.2 Archive (keep the code and reports, out of the main pipeline)
- `robust_aggregation.py` and `simulate_poisoning.py` move to `ml/experiments/`.
- Keep `evaluation/poisoning_defense_report.md` and present it as an additional experiment.
- Keep the SecAgg experiment report as a historical note.

### 3.3 Change
- `dp_mechanism.py`: delete the SecAgg part, keep clip and noise.
- `train_dp_federated.py`: pick a final noise level and clip bound, then retrain.
- The deployed model becomes the DP-trained one (`xgb_dp_federated.json`), not the plain FL one.
- README and phase table: update as described in section 14.

---

## 4. Target architecture

```
                      +--------------------------+
                      |   React frontend         |
                      | insurer portal | auditor |
                      +------------+-------------+
                                   |
                      +------------v-------------+
                      |   FastAPI backend        |
                      | features, model, SHAP,   |
                      | hashing, audit logic     |
                      +------+-------------+-----+
                             |             |
             +---------------v--+      +---v-------------------+
             | Postgres 16      |      | Node Fabric gateway   |
             | 6 databases      |      | (REST, per-org        |
             | (one per insurer)|      |  identities)          |
             +------------------+      +-----------+-----------+
                                                   |
                                  +----------------v----------------+
                                  | Hyperledger Fabric              |
                                  | 6 insurer orgs, 1 Raft orderer  |
                                  | channel: insurance-channel      |
                                  | chaincode: insurance_audit      |
                                  +---------------------------------+

Offline / periodic:  6 insurer nodes -> clip + noise -> FedAvg -> global model
                     -> hash on-chain -> model distributed to all insurers
```

---

## 5. Federated learning changes

### 5.1 Pipeline
1. Each insurer trains locally on its own CSV.
2. Each insurer's update is **clipped** to an L2 bound `C`, then **Gaussian noise** (`sigma * C`) is added.
3. The server aggregates with FedAvg (FedProx can stay as an option for non-IID data).
4. After the final round, save the model, compute its SHA-256, call `RegisterGlobalModel`, and copy the model to every insurer node.

### 5.2 Tasks
- Remove the SecAgg code path from `dp_mechanism.py` and `train_dp_federated.py`.
- Use the existing Phase 5 noise sweep to choose a final `sigma` and `C`. Choose the value with acceptable F1 loss.
- Retrain and save as `models/global_M<version>.json`.
- Save `models/preprocess_stats.json` containing training means (for `yield_deviation`), feature column order and the fraud threshold. Inference must use the same values as training.
- Update `evaluation/privacy_vs_accuracy.md` with the final numbers.

### 5.3 Threat model (state this in the report)
- Without SecAgg, the aggregator sees clipped and noised updates. Noise is the only privacy protection against an honest-but-curious aggregator.
- Clip and noise on XGBoost is an empirical defense, not a formal differential-privacy guarantee.
- The system does not defend against a fully colluding majority of insurers.
- The training labels are heuristic, so high F1 partly reflects the labelling rules and should not be read as real-world accuracy.

---

## 6. Chaincode specification (`insurance_audit`)

**Principle:** only hashes and references go on-chain, never raw data.

### 6.1 Data structures

```go
type ModelRecord struct {
    ModelVersion string `json:"modelVersion"`
    ModelHash    string `json:"modelHash"`
    Round        int    `json:"round"`
    RegisteredBy string `json:"registeredBy"` // MSP ID
    Timestamp    string `json:"timestamp"`
}

type ClaimRecord struct {
    ClaimRef     string `json:"claimRef"`
    InsurerMSP   string `json:"insurerMSP"`   // taken from caller identity
    ClaimHash    string `json:"claimHash"`
    ModelVersion string `json:"modelVersion"`
    RiskLabel    string `json:"riskLabel"`    // HIGH | LOW
    Timestamp    string `json:"timestamp"`
}

type ExplanationRecord struct {
    ClaimRef   string `json:"claimRef"`
    InsurerMSP string `json:"insurerMSP"`
    ShapHash   string `json:"shapHash"`
    Timestamp  string `json:"timestamp"`
}
```

### 6.2 Functions

| Function | Type | Rules |
|---|---|---|
| `RegisterGlobalModel(version, modelHash, round)` | write | Rejects an existing version. Majority-org endorsement. |
| `RegisterClaim(claimRef, claimHash, modelVersion, riskLabel)` | write | Insurer taken from `GetClientIdentity().GetMSPID()`. Rejects an existing `claimRef`. Model version must exist. |
| `RegisterExplanation(claimRef, shapHash)` | write | Claim must exist, `riskLabel == HIGH`, caller MSP must equal the claim's MSP. Write-once. |
| `VerifyClaim(claimRef, claimHash)` | read | Returns `MATCH`, `MISMATCH` or `NOT_FOUND`. |
| `VerifyExplanation(claimRef, shapHash)` | read | Same result values. |
| `VerifyModel(version, modelHash)` | read | Same result values. |
| `GetClaimRecord`, `GetExplanationRecord`, `GetModel`, `ListModels` | read | Any org can read. |
| `GetClaimHistory(claimRef)` | read | Uses `GetHistoryForKey`. |

### 6.3 Requirements
- **Write-once keys:** if a key already exists, return an error. This gives the ledger its tamper-evidence.
- **Caller identity:** never accept the insurer ID as a parameter.
- **Events:** emit `ModelRegistered`, `ClaimRegistered` and `ExplanationRegistered` for the live feed in the UI.
- **Endorsement policies:**
  - Claims: owning org plus one other org.
  - Models: majority of orgs.
- **State DB:** LevelDB (skip CouchDB to save memory).
- **Key prefixes:** `MODEL_`, `CLAIM_`, `SHAP_`.
- **Unit tests** (extend `insurance_audit_test.go`):
  - Duplicate claim write is rejected.
  - Explanation for a non-HIGH claim is rejected.
  - Explanation from the wrong org is rejected.
  - Claim with an unknown model version is rejected.
  - Verify returns the correct status in all three cases.
- Bump chaincode `sequence` and `version` when redeploying, and update `deploy_chaincode.ps1` and `.sh`.

---

## 7. Fabric gateway service (Node.js)

Python's `fabric-sdk-py` is poorly maintained, so use a small Node service.

- Library: `@hyperledger/fabric-gateway`.
- Loads the connection profile and the crypto material for all 6 orgs.
- Selects the org identity from a request header, for example `X-Insurer: insurer3`.
- Exposes REST endpoints that map one-to-one to the chaincode functions:
  - `POST /models`, `POST /claims`, `POST /claims/:ref/explanation`
  - `GET /claims/:ref`, `GET /claims/:ref/verify?hash=...`
  - `GET /explanations/:ref/verify?hash=...`
  - `GET /models`, `GET /models/:version/verify?hash=...`
  - `GET /events` (server-sent events for the live ledger feed)
- Returns `tx_id` and block number for every write.
- Retries on transient failures and returns clear errors for chaincode rejections.
- Smoke test: one write and one verify call per org.

---

## 8. Local databases (Postgres in Docker)

### 8.1 Layout
One container (`postgres:16`) with six databases: `insurer1_db` through `insurer6_db`. Each has its own user, and a user cannot connect to another insurer's database. If your machine has enough RAM, six containers work too, since only the connection strings change.

### 8.2 Docker setup
- Separate `docker-compose.db.yaml` (do not mix it with the Fabric compose file).
- Named volume for persistence.
- Mount an init script into `/docker-entrypoint-initdb.d/` to create the databases, users and tables.
- `pg_isready` healthcheck.
- Credentials in `.env`, and add `.env` to `.gitignore`.
- Host port `5433` to avoid clashing with a local Postgres.
- Extra role `admin_user` with update rights, used only in the tamper demo. The backend uses `app_user`.

### 8.3 Schema (same in all six databases)

```sql
CREATE TABLE claims (
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

CREATE TABLE explanations (
    claim_ref        TEXT PRIMARY KEY REFERENCES claims(claim_ref),
    shap_canonical   TEXT NOT NULL,            -- exact string that was hashed
    shap_json        JSONB NOT NULL,
    shap_hash        CHAR(64) NOT NULL,
    shap_tx_id       TEXT,
    chain_status     TEXT NOT NULL DEFAULT 'PENDING',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    claim_ref   TEXT,
    check_type  TEXT,        -- CLAIM | EXPLANATION | MODEL | CONSISTENCY
    result      TEXT,
    checked_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**JSONB gotcha:** Postgres reorders JSONB keys and normalizes numbers. Always hash the `*_canonical` TEXT column. Keep JSONB only for display and queries.

---

## 9. Hashing specification

No salt or nonce. The claim contains a random UUID `claim_id`, which makes each hash unique.

**Claim hash**
```
canonical = JSON with fixed field order, no whitespace:
  claim_id, insurer_id, farmer_id, commodity_code, cause_of_loss_code,
  net_indemnity, premium_amount, state_code, county_code, commodity_year,
  model_version, fraud_score (6 decimals), risk_label
claim_hash = SHA-256(canonical)
```

**SHAP hash**
```
shap_canonical = JSON with sorted keys, values rounded to 6 decimals,
                 includes claim_ref and model_version
shap_hash = SHA-256(shap_canonical)
```
Store the exact canonical string in the DB. At audit time hash that stored string. Do not re-serialize floats.

**Model hash:** `SHA-256` of the model file bytes.

Keep the hashing code in a single `hashing.py` shared by intake and audit.

---

## 10. Backend (FastAPI)

### 10.1 Claim intake flow
1. Receive the claim for insurer *k* (`insurer_id` in the route).
2. Validate the fields.
3. Build the 7 model features with `preprocess_stats.json`.
4. Check that the local model file's hash matches the on-chain hash (cache for a short time).
5. Predict `fraud_score` and `risk_label` (threshold from the stats file).
6. Insert the claim into insurer *k*'s database with `chain_status = PENDING`.
7. Compute the claim hash and call the gateway `RegisterClaim`.
8. Update the row with `claim_tx_id` and `chain_status = ANCHORED`.
9. **If `risk_label == HIGH`:**
   - Compute SHAP locally.
   - Store `shap_canonical` and `shap_json` in `explanations`.
   - Call `RegisterExplanation` with the SHAP hash and store the `tx_id`.
10. Return the score, label, hashes and tx_ids.

If the chain call fails, keep the row as `PENDING` or `FAILED` and retry in a background task. Never lose a claim.

### 10.2 Endpoints

```
POST /insurers/{id}/claims
GET  /insurers/{id}/claims
GET  /insurers/{id}/claims/{ref}
GET  /insurers/{id}/claims/{ref}/explanation
POST /insurers/{id}/claims/{ref}/audit          # runs all checks
GET  /models                                    # versions + on-chain hashes
POST /models/{version}/verify
GET  /metrics                                   # FL vs centralized results
POST /demo/tamper/claim/{ref}                   # demo only
POST /demo/tamper/explanation/{ref}             # demo only
```

### 10.3 Module layout
- `inference.py`: load the model, build features, predict, SHAP.
- `hashing.py`: canonical strings and SHA-256.
- `db.py`: per-insurer connection pools.
- `chain_client.py`: calls the Node gateway.
- `audit.py`: the verification logic (section 11).
- `app.py`: routes.

---

## 11. Audit flow

For a selected claim, the auditor view runs these checks:

| Check | How |
|---|---|
| **Claim integrity** | Hash `claim_data_canonical` from the DB and call `VerifyClaim`. |
| **Explanation integrity** (HIGH claims only) | Hash `shap_canonical` from the DB and call `VerifyExplanation`. |
| **Model integrity** | Hash the local model file for that version and call `VerifyModel`. |
| **Consistency** | The `risk_label` and `model_version` in the DB must match the on-chain claim record. |

Each check returns VERIFIED or TAMPERED. Log each run in `audit_log`.

**Tamper demo:**
- Button 1: change `net_indemnity` through `admin_user`. The claim check turns red.
- Button 2: edit one SHAP value. The explanation check turns red.
- A "restore" button resets the demo data.

---

## 12. Frontend (React + Vite, Tailwind, Recharts)

1. **Insurer selector.** Choose Insurer 1 to 6.
2. **New claim form.** Farmer ID, state, county, commodity, cause of loss, month, acres, liability, premium, indemnity, yield. After submit it shows score, label, claim hash and tx_id.
3. **Claims list.** Risk badge, chain status, and an "Explanation available" tag on flagged claims.
4. **Claim detail.**
   - Score and risk label.
   - SHAP bar chart (flagged claims only).
   - Stored hash vs on-chain hash.
   - Verify button.
5. **Auditor view.** Runs the 4 checks with green or red results, plus the two tamper buttons.
6. **Models and network.**
   - Model versions with on-chain hashes and a verify button.
   - Live ledger feed (from gateway events).
   - FL results: centralized vs FL vs FL with clip and noise.

Keep it to these screens. Add a short demo-script page or README section so the presentation order is fixed.

---

## 13. Revised phase plan

### Phase 5b: FL cleanup and final model
- [ ] Remove SecAgg code and move Byzantine code to `ml/experiments/`.
- [ ] Choose final `sigma` and `C`, retrain with clip and noise.
- [ ] Export `models/global_M<version>.json` and `preprocess_stats.json`.
- [ ] Update `evaluation/privacy_vs_accuracy.md`.

**Done when:** one final model and one stats file exist, and F1 is documented.

### Phase 8b: Chaincode upgrade
- [ ] Implement the data structures and functions from section 6.
- [ ] Add identity checks, write-once keys, events and endorsement policies.
- [ ] Remove private data collections.
- [ ] Extend unit tests.
- [ ] Redeploy on the 6-org network with a bumped sequence.

**Done when:** `go test` passes and each function works from each org via the CLI.

### Phase 9: Fabric gateway service
- [ ] Build the Node REST service with per-org identities.
- [ ] Add the event stream endpoint.
- [ ] Smoke-test every endpoint per org.
- [ ] Anchor the final global model with `RegisterGlobalModel`.

**Done when:** the model hash is on-chain and `verify` returns MATCH.

### Phase 10: Databases and hashing
- [ ] Create `docker-compose.db.yaml`, the init SQL and the `.env` file.
- [ ] Write `hashing.py` and unit tests (same input gives the same hash, one changed field gives a different hash).
- [ ] Write `db.py` with six connection pools.

**Done when:** six databases come up with one command and the hash tests pass.

### Phase 11: Backend inference, claims and SHAP
- [ ] Build `inference.py` using the saved stats file.
- [ ] Build the claim intake endpoint (section 10.1).
- [ ] Add SHAP for HIGH claims, store it, and anchor its hash.
- [ ] Add the retry task for failed chain calls.

**Done when:** a submitted fraud claim has a row in `claims`, a row in `explanations`, and two on-chain records.

### Phase 12: Audit and tamper
- [ ] Build `audit.py` with the 4 checks.
- [ ] Add the tamper and restore endpoints.
- [ ] Log results in `audit_log`.

**Done when:** tampering a claim or a SHAP value makes the matching check fail.

### Phase 13: Frontend
- [ ] Build the screens in section 12 in this order: claim form, claims list, claim detail, auditor view, models page.
- [ ] Connect to the live ledger feed.

**Done when:** the full demo runs from the browser without using the CLI.

### Phase 14: Evaluation and report
- [ ] Blockchain latency and throughput benchmark (average, P95, TPS) for claim writes.
- [ ] Final metrics table: centralized vs FL vs FL with clip and noise.
- [ ] Tamper demo results (screenshots).
- [ ] Bias check by state and commodity, reported as a limitation.
- [ ] Final report and presentation, including the threat model in section 5.3.

---

## 14. Target repo structure

```
Crop-Insurance-Fraud-Detection/
├── backend/                 FastAPI app (section 10)
├── gateway/                 Node Fabric gateway (section 7)
├── frontend/                React app (section 12)
├── blockchain/
│   ├── fabric-network/      6-org network (existing)
│   └── chaincode/           upgraded chaincode + tests
├── db/
│   ├── docker-compose.db.yaml
│   ├── init/                create databases, users, tables
│   └── .env.example
├── ml/
│   ├── federated/           FedAvg + clip + noise
│   ├── experiments/         archived SecAgg and Byzantine code
│   └── shap/
├── models/                  global model + preprocess_stats.json
├── data/
├── evaluation/
└── docs/                    phase docs (updated)
```

README and docs updates:
- Replace the phase table with section 13.
- Remove claims about SecAgg and private data collections.
- Update the architecture diagram to section 4.
- Update the "Key System Features" list (SHAP only for flagged claims, clip and noise instead of SecAgg).
- Add a "How to run the demo" section.

---

## 15. Demo script (suggested order)

1. Show the FL results and the final model hash on the Models page.
2. As Insurer 3, submit a normal claim: LOW, no SHAP, claim hash anchored.
3. Submit a suspicious claim: HIGH, SHAP chart shown, claim hash and SHAP hash anchored.
4. Open the auditor view: all checks green.
5. Run the tamper button: the claim check turns red.
6. Run the SHAP tamper: the explanation check turns red.
7. Restore the data, and show the live ledger feed with the transactions.

---

## 16. Risks and notes

- **RAM:** Fabric with 6 peers plus Postgres plus the backend is heavy. Use LevelDB, one orderer, and one Postgres container.
- **Hash drift:** always hash stored canonical strings, never re-serialized JSON or floats.
- **Feature mismatch:** always use `preprocess_stats.json` at inference. Otherwise `yield_deviation` differs from training.
- **Chain downtime:** keep the `PENDING` and retry flow so claims are never lost.
- **Report honesty:** state the heuristic labels, the empirical (not formal) DP, and the threat model limits.
