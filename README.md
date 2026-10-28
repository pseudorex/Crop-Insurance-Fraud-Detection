# 🌾 Crop Insurance Fraud Consortium — Enterprise Architecture & System Guide

> **A Multi-Tenant Federated Learning & EVM Blockchain Consortium for Agricultural Fraud Detection with Explainable AI (TreeSHAP), Strict Role-Based Access Control (RBAC), and Cryptographic Audit Hash Chains.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Node: 18+](https://img.shields.io/badge/Node-18+-green.svg)](https://nodejs.org/)
[![Solidity: 0.8.20](https://img.shields.io/badge/Solidity-0.8.20-lightgrey.svg)](https://soliditylang.org/)
[![PostgreSQL: 16](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![FastAPI: 0.110+](https://img.shields.io/badge/FastAPI-0.110+-teal.svg)](https://fastapi.tiangolo.com/)
[![React: 18 + Vite](https://img.shields.io/badge/React-18_Vite-61dafb.svg)](https://react.dev/)

---

## 📌 Executive Summary & Academic Pitch

Agricultural crop insurance fraud causes billions of dollars in unjustified payouts worldwide, yet insurers cannot easily detect cross-regional syndicates because agricultural datasets are proprietary and siloed due to privacy regulations and competitive concerns. 

This project solves this dilemma by building a **decentralized, privacy-preserving consortium**:
1. **Multi-Tenant Database Isolation**: Six independent insurers maintain dedicated PostgreSQL databases (`insurer1_db` through `insurer6_db`), ensuring strict physical separation of proprietary claim data.
2. **Federated Learning with Differential Privacy**: Competing insurers collaboratively train a high-accuracy XGBoost fraud classifier using Flower (`flwr`), adding Gaussian Differential Privacy ($L_2$ clipping bound $C=1.0$, noise $\sigma=0.02$, $\epsilon=1.2$) and Byzantine-robust defenses (Multi-Krum, Trimmed Mean, Coordinate-Wise Median) without pooling raw data.
3. **EVM Blockchain Audit Layer**: An Ethereum smart contract (`InsuranceAudit.sol`) running on a Ganache consortium node anchors canonical RFC-8785 SHA-256 fingerprints of claims, certified global model weights, and TreeSHAP explainability attributions. By storing only 32-byte cryptographic hashes rather than raw records, the system achieves a **99.53% gas reduction** while guaranteeing non-repudiation and permanent immutability.
4. **Enterprise Role-Based Access Control (RBAC)**: Enforces strict separation of duties:
   - **Intake Officers / Adjusters**: Confined to their respective insurer, authorized solely to submit claims.
   - **Insurer Admins**: Full access to claims, ledger, and cryptographic audit logs for their own insurer only (cross-tenant access is blocked with HTTP 403).
   - **Independent Individual Auditor (`INDIVIDUAL`)**: An independent external regulator signed in as an individual, with cross-consortium read-only audit permissions across all 6 member insurers.
5. **Cryptographic Append-Only Audit Trail**: Every database state change is tracked in an immutable hash chain linking parent hashes ($h_i = \text{SHA-256}(h_{i-1} \parallel \text{event}_i)$), exposing any unauthorized tampering in real time.

---

## 🏗️ Multi-Tier System Architecture

```
                          ┌────────────────────────────────────────────────────────┐
                          │         Consortium React 18 + Vite Dashboard           │
                          │                 (http://localhost:3000)                │
                          └───────────┬────────────────────────────────┬───────────┘
                                      │ REST API / JWT                 │
                                      ▼                                ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application Server (Port 8000)                          │
│  • RBAC & Tenant Scoping     • 4-Phase Cryptographic Auditor     • TreeSHAP Explainer  │
│  • Argon2id Auth & JWT       • Append-Only Audit Log Hash Chain  • Tamper Sandbox      │
└──────────────┬──────────────────────────────┬───────────────────────────┬──────────────┘
               │ PostgreSQL (asyncpg/psycopg2)│ Web3.py JSON-RPC          │
               ▼                              ▼                           ▼
┌───────────────────────────────┐ ┌───────────────────────────┐ ┌────────────────────────┐
│  Multi-Tenant Database Engine │ │ Solidity EVM Smart        │ │ Flower Federated       │
│  (Port 5433 / 5432)           │ │ Contract (Ganache: 8545)  │ │ Learning Cluster       │
│  • insurer1_db (Alliance)     │ │                           │ │                        │
│  • insurer2_db (Midwest)      │ │ InsuranceAudit.sol:       │ │ • 6 Non-IID Nodes      │
│  • insurer3_db (Great Plains) │ │ • Write-once Claim Hashes │ │ • Differential Privacy │
│  • insurer4_db (National)     │ │ • Gated TreeSHAP Hashes   │ │ • Byzantine-Robust     │
│  • insurer5_db (Pioneer)      │ │ • Registered Model Hashes │ │   Filters              │
│  • insurer6_db (Frontier)     │ │ • View/Verify Functions   │ │ • Global Model M1      │
└───────────────────────────────┘ └───────────────────────────┘ └────────────────────────┘
```

### Technology Stack Mapping

| Tier | Component | Technology | Role & Specification |
| :--- | :--- | :--- | :--- |
| **Blockchain** | EVM Node | Truffle Ganache | Port `8545`, Network ID `5777`, Chain ID `1337`, instant block sealing |
| **Smart Contract**| Audit Ledger | Solidity `0.8.20` | Write-once mappings, gas-optimized 32-byte storage |
| **Web3 Client** | Node Bridge | Python `web3.py` | JSON-RPC provider, gas estimator, ABI transaction encoder |
| **Database** | Multi-Tenant DB | PostgreSQL 16 Alpine | 6 dedicated tenant databases (`insurer1_db` ... `insurer6_db`) |
| **Authentication**| Identity & RBAC | JWT + Passlib (Argon2id/Bcrypt) | Stateless Bearer tokens with strict tenant scope and role claims |
| **Machine Learning**| Fraud Model | XGBoost / Scikit-Learn | Depth 6, 15 trees/round, feature scaling, TreeSHAP explainer |
| **Federated Learning**| Model Training | Flower (`flwr` 1.7) | FedAvg + FedProx with Differential Privacy & Byzantine defense |
| **Backend API** | App Server | FastAPI + Uvicorn | Port `8000`, async routes, 4-phase cryptographic audit engine |
| **Frontend UI** | Dashboard | React 18 + Vite + Tailwind | Port `3000`, dark-mode telemetry, tamper sandbox, audit log viewer |

---

## 🏢 Multi-Tenant Consortium Organizations & RBAC

The consortium consists of **6 predefined regional crop insurance organizations** and **1 independent regulatory body**:

### Consortium Members

| Insurer ID | Organization Name | Default Database | Primary Region & Agricultural Profile |
| :--- | :--- | :--- | :--- |
| `insurer1` | **Alliance Agri** | `insurer1_db` | Midwest / Great Lakes (Corn, Soybeans, High Loss History) |
| `insurer2` | **Midwest Mutual** | `insurer2_db` | Central Plains (Wheat, Sorghum, Severe Drought Exposure) |
| `insurer3` | **Great Plains Corp** | `insurer3_db` | Southern Plains & Delta (Cotton, Rice, Hail & Flood) |
| `insurer4` | **National Crop** | `insurer4_db` | Northern Plains (Barley, Canola, Early Frost) |
| `insurer5` | **Pioneer Harvest** | `insurer5_db` | Pacific & Western (Specialty Crops, Wildfire & Heat) |
| `insurer6` | **Frontier Farm** | `insurer6_db` | Eastern Seaboard (Apples, Tobacco, Hurricane & Wind) |

---

### Role-Based Access Matrix

| Capability / API Route | Intake Officer / Adjuster | Insurer Admin | Independent Individual Auditor (`INDIVIDUAL`) |
| :--- | :---: | :---: | :---: |
| **Submit New Claims** (`POST /claims/intake`) | ✅ **Allowed** (Own Tenant) | ❌ **Forbidden (403)** | ❌ **Forbidden (403)** |
| **View Claims Ledger** (`GET /claims`) | ✅ **Own Tenant** | ✅ **Own Tenant** | ✅ **All Consortium Insurers** |
| **Run 4-Phase Audit** (`POST /audit/run`) | ❌ **Forbidden (403)** | ✅ **Own Tenant** | ✅ **All Consortium Insurers** |
| **View Audit Hash Chain** (`GET /audit/log`) | ❌ **Forbidden (403)** | ✅ **Own Tenant** | ✅ **All Consortium Insurers** |
| **Simulate Database Tamper** (`POST /audit/tamper`) | ❌ **Forbidden (403)** | ✅ **Sandbox Mode** | ❌ **Forbidden (403)** |
| **Restore Database State** (`POST /audit/restore`) | ❌ **Forbidden (403)** | ✅ **Sandbox Mode** | ❌ **Forbidden (403)** |
| **Cross-Tenant Inspection** | ❌ **Blocked (403)** | ❌ **Blocked (403)** | ✅ **Consortium-Wide Read-Only** |

#### Why Strict Role Separation Matters
1. **Adjuster vs. Admin Separation**: In insurance governance, the officer who inputs and adjusts claims must never have authority to alter or audit the master ledger. Separating Adjusters from Admins prevents internal collusion.
2. **Cross-Tenant Isolation**: Competing insurance carriers cannot view each other's claim volumes, premiums, or payout amounts. Any attempt by `admin2` to access `insurer3` yields an immediate `HTTP 403 Forbidden` and logs a security event.
3. **Independent Auditor Role**: The auditor is signed in as an individual (**Dr. Aris Thorne**, `INDIVIDUAL`) with no corporate affiliation to any single insurer. The auditor has complete cross-consortium read-only access to verify blockchain hashes, detect tampering, and confirm regulatory compliance.

---

## 🤖 Federated Learning, Privacy & Explainability

### 1. USDA RMA Dataset & Non-IID Partitioning
- **Data Source**: USDA Risk Management Agency (RMA) — 5 Years of Historical Data (2019–2023).
- **Volume**: 677,150 federal crop insurance records (~207 MB raw data).
- **Fraud Distribution**: 3.75% overall synthetic baseline calibrated via RMA agricultural anomaly heuristics.
- **Non-IID Partitioning**: Claim records are partitioned into 6 regional non-identically distributed subsets reflecting real-world agricultural disparity (e.g., higher drought frequency in Plains, excess moisture in the Delta).

### 2. Feature Engineering & TreeSHAP Importance

The model evaluates 14 critical predictors for each claim:

| Rank | Feature Name | Description | Importance |
| :---: | :--- | :--- | :---: |
| 1 | `cause_of_loss_code` | Primary cause of loss (Drought, Hail, Flood, Freeze) | **0.7961** |
| 2 | `indemnity_to_premium_ratio` | Payout divided by premium (Anomalously high ratios trigger suspicion) | **0.1300** |
| 3 | `yield_deviation` | Divergence between historical county benchmark and reported farm yield | **0.0272** |
| 4 | `total_premium` | Total dollar premium paid for coverage | **0.0085** |
| 5 | `net_planted_acres` | Total acreage planted and insured | **0.0077** |
| 6 | `indemnity_to_liability_ratio`| Indemnity payout relative to total policy liability | **0.0070** |
| 7 | `commodity_code` | Insured crop variety (Corn, Soybeans, Wheat, Cotton, Rice) | **0.0067** |
| 8 | `month_of_loss` | Month loss occurred (Checks seasonal validity) | **0.0053** |
| 9 | `determined_yield` | Yield assessed by loss adjuster | **0.0047** |
| 10 | `indemnity_amount` | Actual indemnity claim payout dollar amount | **0.0031** |
| 11 | `county_claim_frequency` | Historical claim frequency density in that county | **0.0027** |
| 12 | `liability_amount` | Total insured dollar liability | **0.0008** |
| 13 | `net_determined_acres` | Acreage verified by adjuster to have suffered loss | 0.0000 |
| 14 | `high_cause_code` | Indicator for rare / anomalous cause codes | 0.0000 |

### 3. Centralized vs. Privacy-Hardened Federated Performance

| Metric | Centralized Baseline (M0) | Plain Federated (Flower) | Privacy-Hardened FL (M1) |
| :--- | :---: | :---: | :---: |
| **Raw Data Shared** | 100% Pooled | **0% (Zero)** | **0% (Zero)** |
| **Privacy Guarantees** | None | Distributed updates | Gaussian DP ($\sigma=0.02, \epsilon=1.2$) + SecAgg |
| **F1-Score** | 0.9848 | **0.9938** | **0.9938** |
| **Precision** | 0.9711 | **0.9927** | **0.9927** |
| **Recall (Fraud Caught)** | 0.9988 | **0.9949** | **0.9949** |
| **ROC-AUC** | 1.0000 | 1.0000 | 1.0000 |
| **False Alarms (FP)** | 148 | **37** | **37** |
| **Missed Fraud (FN)** | 6 | 26 | 26 |

### 4. Byzantine Attack Defense Benchmarks

| Attack Scenario | Adversary Action | Defense Strategy | Global F1 | Defense Verdict |
| :--- | :--- | :--- | :---: | :---: |
| **Weight Scaling** | Multiplies weights $\times 50$ | **$L_2$ Norm Filter + Trimmed Mean** | **0.9938** | **Fully Mitigated** (Outliers rejected) |
| **Label Flipping** | Inverts labels $0 \leftrightarrow 1$ | **Multi-Krum Consensus** | **0.9743** | **Isolated Geometrically** |
| **Noise Sabotage** | Injects $\mathcal{N}(0, 25.0)$ noise | **Coordinate-Wise Median** | **0.9938** | **Fully Mitigated** |

---

## ⛓️ EVM Smart Contract & 99.5% Gas Reduction

Storing raw JSON claims (~200 KB) directly in Ethereum storage slots (`SSTORE`) consumes over 5,000,000 gas per claim, making on-chain storage economically unviable. 

Our architecture hashes canonical RFC-8785 JSON off-chain and registers only **32-byte cryptographic SHA-256 digests** on-chain:

$$\text{Gas Savings} = \frac{5,000,000 - 23,604}{5,000,000} \times 100\% = \mathbf{99.53\%}$$

### Smart Contract Gas Economics (`InsuranceAudit.sol`)

| Smart Contract Function | Gas Consumed | Transaction Type | Description |
| :--- | :---: | :---: | :--- |
| `registerClaim(...)` | **23,604** | On-Chain State Change | Anchors canonical claim SHA-256 fingerprint (write-once) |
| `anchorSHAP(...)` | **22,176** | On-Chain State Change | Anchors 32-byte TreeSHAP explanation hash (gated to high-risk claims) |
| `anchorModel(...)` | **28,450** | On-Chain State Change | Anchors certified global model weights hash |
| `verifyClaim(...)` | **0** | Local View (`eth_call`) | Constant-time on-chain hash lookup |
| `verifyModel(...)` | **0** | Local View (`eth_call`) | Constant-time model checkpoint hash lookup |
| `getClaim(...)` | **0** | Local View (`eth_call`) | Retrieves registration timestamp and block number |

---

## 🛡️ 4-Phase Cryptographic Auditor & Hash Chain

The system includes a real-time verification suite executing four sequential cryptographic checks:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      4-Phase Cryptographic Auditor                     │
├───────────────────┬───────────────────┬────────────────────────────────┤
│ Phase 1: Claims   │ Phase 2: SHAP     │ Phase 3: Model Governance      │
│ Local RFC-8785    │ Local TreeSHAP    │ Current Model Weights          │
│ SHA-256 Hash      │ SHA-256 Hash      │ Checkpoint SHA-256 Hash        │
│        vs.        │        vs.        │              vs.               │
│ On-Chain Hash     │ On-Chain Hash     │ On-Chain Registered Model Hash │
├───────────────────┴───────────────────┴────────────────────────────────┤
│ Phase 4: Local Database vs. On-Chain Consistency & Missing Records     │
│ • Detects orphaned claims, unregistered records, or unanchored updates │
└────────────────────────────────────────────────────────────────────────┘
```

### Cryptographic Append-Only Audit Log Hash Chain
Every consortium event (`CLAIM_SUBMITTED`, `AUDIT_RUN`, `AUDIT_CLAIM`, `TAMPER_SIMULATED`, `CLAIM_RESTORED`) is committed to an immutable append-only ledger in PostgreSQL:

$$h_i = \text{SHA-256}(id \parallel action \parallel insurer\_id \parallel user\_id \parallel target\_id \parallel h_{i-1} \parallel payload \parallel timestamp)$$

- If any record inside the PostgreSQL database is manually modified or deleted via raw SQL, the audit chain's parent pointer breaks.
- The auditor's **Verify Hash Chain** tool verifies DAG-continuity across all entries and reports exact breakdown coordinates.

---

## ⚡ Quickstart & Setup Guide

### 1. Prerequisites
- **Python 3.10+** (with virtual environment recommended)
- **Node.js 18+** & **npm 9+**
- **PostgreSQL 16** (running on port `5432` or `5433`)
- **Truffle Ganache** (running on port `8545`)

---

### 2. Clone Repository & Setup Virtual Environment
```powershell
git clone https://github.com/pseudorex/Crop-Insurance-Fraud-Detection.git
cd Crop-Insurance-Fraud-Detection

# Create and activate Python virtual environment
python -m venv blockvenv
.\blockvenv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

---

### 3. Initialize Multi-Tenant PostgreSQL Databases
Make sure PostgreSQL is running, then create the consortium databases:
```powershell
# Execute the multi-tenant database initialization script
psql -U postgres -h localhost -p 5432 -f db/init/init.sql
```
*(This sets up `insurer1_db` through `insurer6_db`, seeds user credentials with Argon2id password hashes, and configures isolated tables.)*

---

### 4. Deploy EVM Smart Contract to Ganache
Ensure Ganache is running on port `8545`:
```powershell
python blockchain/deploy_contract.py
```
**Expected Output:**
```
[+] Compiling Solidity smart contract: InsuranceAudit.sol (0.8.20)...
[+] Connecting to Ganache at http://127.0.0.1:8545...
[+] Contract successfully deployed at: 0xafBaC0373745c3e653e2fFf117c8684dc0d31258
[+] Gas used: 1,248,390
[+] Initializing model anchor M1 (xgb_dp_federated.json)...
[+] Deployed contract metadata written to blockchain/contract_deployment.json
```

---

### 5. Launch FastAPI Backend Application
```powershell
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation and Swagger UI will be available at:
`http://localhost:8000/docs`

---

### 6. Launch React Consortium Dashboard
In a separate terminal:
```powershell
cd dashboard
npm install
npm run dev
```
Open your browser and navigate to:
`http://localhost:3000`

---

## 🧪 Automated Testing & Verification

Run the comprehensive integration and RBAC test suites:

### 1. Run Complete Backend Integration & Tamper Test
```powershell
python backend/test_backend.py
```
**Verifies:**
- Insurer authentication, Argon2id password hashing, and token issuance.
- Cross-tenant isolation (HTTP 403 on tenant boundary violation).
- Claim intake and automatic Ganache blockchain anchoring.
- Live tamper simulation (modifies SQL indemnity value to $95,000.00).
- Immediate tamper detection by 4-phase auditor.
- Clean database restoration and re-verification.
- Cryptographic append-only hash chain integrity.

### 2. Run Strict RBAC & Audit Trail Test Suite
```powershell
python backend/test_rbac.py
```
**Verifies:**
- Adjuster permission checks (Adjuster submits, cannot audit).
- Admin permission checks (Admin audits, cannot submit claims).
- Auditor permission checks (Auditor is read-only across all tenants).
- Cross-tenant audit blocks and missing records detection.
- Complete hash chain provenance across 400+ ledger entries.

---

## 🔑 Default Test Credentials (1-Click Quick Login)

The dashboard includes one-click quick authentication buttons for rapid demonstration:

| User Account | Password | Role Badge | Organization | Assigned Privileges |
| :--- | :--- | :--- | :--- | :--- |
| **`adjuster3`** | `AdjusterPass123!` | `ADJUSTER` | Insurer 3 (Great Plains) | Submit claims for Insurer 3; intake only |
| **`admin3`** | `AdminPass123!` | `ADMIN` | Insurer 3 (Great Plains) | Audit Insurer 3 claims, view audit log, tamper sandbox |
| **`auditor1`** | `AuditorPass123!` | `INDIVIDUAL AUDITOR` | **Independent / Individual** | Consortium-wide cross-tenant audit across Insurers 1–6 |
| **`adjuster1`** | `AdjusterPass123!` | `ADJUSTER` | Insurer 1 (Alliance Agri) | Submit claims for Insurer 1 |
| **`admin1`** | `AdminPass123!` | `ADMIN` | Insurer 1 (Alliance Agri) | Audit Insurer 1 claims & logs |
| **`admin2`** | `AdminPass123!` | `ADMIN` | Insurer 2 (Midwest Mutual)| Audit Insurer 2 claims & logs |

---

## 📁 Repository Structure

```
Crop-Insurance-Fraud-Detection/
├── backend/
│   ├── app.py                      # FastAPI REST application & routing
│   ├── audit.py                    # 4-phase cryptographic audit engine
│   ├── auth.py                     # JWT token generation, Argon2id & RBAC scopes
│   ├── db.py                       # PostgreSQL multi-tenant connection pool & audit trail
│   ├── hashing.py                  # Canonical RFC-8785 JSON & SHA-256 digest tools
│   ├── inference.py                # TreeSHAP explainer & ML inference engine
│   ├── test_backend.py             # 13-phase end-to-end integration test
│   └── test_rbac.py                # Strict RBAC permission & audit trail test
│
├── blockchain/
│   ├── solidity/InsuranceAudit.sol # Solidity 0.8.20 audit smart contract
│   ├── deploy_contract.py          # Web3.py compilation & deployment script
│   ├── contract_deployment.json    # Deployed contract address, ABI & network metadata
│   ├── chain_client.py             # Web3 client bridge with graceful fallback
│   └── explore_blocks.py           # Terminal blockchain explorer CLI
│
├── dashboard/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AuthModal.jsx       # Consortium login & insurer staff registration modal
│   │   │   ├── AuditorView.jsx     # 4-phase audit matrix & tamper attack sandbox
│   │   │   ├── AuditLogView.jsx    # Cryptographic append-only hash chain explorer
│   │   │   ├── ClaimsView.jsx      # Immutable claims ledger & TreeSHAP drawer
│   │   │   ├── Header.jsx          # Tenant switcher, user badge, and session controls
│   │   │   ├── IntakeView.jsx      # Claim intake form, live scoring gauge & anchoring
│   │   │   └── NetworkView.jsx     # Consortium cluster health & registered models
│   │   ├── App.jsx                 # Main application controller
│   │   └── api.js                  # Axios client with JWT interceptor & tenant headers
│   ├── package.json
│   └── vite.config.js
│
├── db/
│   └── init/
│       ├── init.sql                # Multi-database and user setup script
│       └── init_tables.sql         # Common tables schema (claims, explanations, audit_log)
│
├── models/
│   ├── xgb_dp_federated.json       # Certified privacy-hardened federated model (M1)
│   ├── xgb_centralized.json        # Centralized benchmark model (M0)
│   └── preprocess_stats.json       # Normalization statistics
│
├── requirements.txt                # Python dependencies
├── package.json                    # Dashboard configuration
└── README.md                       # Master Architecture & Implementation Guide
```

---

## 🎓 Teacher / Viva Defense Q&A Cheatsheet

### Q1: "Why use Ganache and EVM instead of Hyperledger Fabric?"
> **Answer:**  
> *"While Hyperledger Fabric is enterprise-focused, an EVM architecture using Solidity provides broad industry standardization, gas-optimized state structures, and compatibility with standard Web3 tooling. Ganache gives us a private consortium EVM node with instant mining. Furthermore, our Solidity contract (`InsuranceAudit.sol`) can deploy directly to enterprise permissioned EVM networks like Polygon Supernets or Hyperledger Besu without rewriting a single line of code."*

### Q2: "What is Gas and why does our architecture save 99.5% gas?"
> **Answer:**  
> *"Gas measures the computational effort and persistent storage allocation on the Ethereum Virtual Machine. Writing raw agricultural claims (~200 KB) to Ethereum storage (`SSTORE`) costs over 5,000,000 gas per claim. By hashing the canonical RFC-8785 JSON off-chain and storing only a 32-byte SHA-256 fingerprint on-chain (`registerClaim`), the gas cost drops to **23,604 gas**, achieving a **99.53% gas reduction** while preserving 100% cryptographic proof of integrity."*

### Q3: "What happens if a rogue employee modifies the PostgreSQL database directly?"
> **Answer:**  
> *"They can modify the local SQL row (e.g., inflating `net_indemnity` from $250 to $95,000), but they cannot alter the Ethereum blockchain or the cryptographic audit hash chain. When the 4-phase auditor runs, it re-computes the SHA-256 hash of the modified data and queries `verifyClaim` on the smart contract. Because the local hash differs from the immutable hash on Ganache, the auditor immediately flags the claim as `SECURITY TAMPER DETECTED` and attributes the modification."*

### Q4: "Why are TreeSHAP explanations anchored only for HIGH-risk claims?"
> **Answer:**  
> *"In federal crop insurance, over 90% of claims are legitimate low-risk filings. Calculating TreeSHAP and paying transaction gas for clean claims would bloat block storage unnecessarily. Our smart contract enforces that only claims classified as `HIGH`-risk ($\ge 0.50$) can call `anchorSHAP`, reserving immutable explainability for claims that may face regulatory scrutiny or farmer disputes while saving consortium resources."*

### Q5: "How does the Federated Learning model achieve higher F1 than Centralized?"
> **Answer:**  
> *"Centralized training suffered from class imbalance across the aggregate 677,150 records, yielding lower precision (0.9711). In Federated Learning, each insurer node trains on its local distribution (with regional fraud rates varying between 1.68% and 8.66%). FedAvg acts as a natural regularizer across non-IID partitions, producing a model with significantly fewer false alarms (37 vs. 148 FP) and achieving an F1-score of **0.9938**."*

### Q6: "Why is the Auditor signed in as an Individual rather than through an Insurer?"
> **Answer:**  
> *"Regulatory watchdogs (such as USDA RMA or state insurance commissioners) must be completely independent third parties. If an auditor belonged to Insurer 1, they would have an inherent conflict of interest when auditing Insurer 2 or 3. By signing in as an independent individual (`INDIVIDUAL` / Dr. Aris Thorne), the auditor possesses consortium-wide read-only visibility without being beholden to any single member company."*

---

## 📄 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
