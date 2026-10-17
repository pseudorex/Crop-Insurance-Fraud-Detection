# Federated, Blockchain-Audited Crop Insurance Fraud Detection

> A multi-insurer federated learning system with a Solidity EVM blockchain audit layer, multi-tenant PostgreSQL databases, real-time TreeSHAP explainability, and an interactive consortium dashboard.

---

## Project Overview

| Property | Value |
|----------|-------|
| **Domain** | InsureTech, Federated Machine Learning, Blockchain Auditing |
| **Dataset** | USDA RMA Cause of Loss (677,150 crop insurance claims) |
| **Consortium Nodes** | 6 independent, isolated insurer databases (`insurer1_db` ... `insurer6_db`) |
| **Primary ML Model** | XGBoost with Differential Privacy (L2 leaf clipping + Gaussian noise) |
| **Explainability** | TreeSHAP (computed locally, anchored on-chain for flagged claims) |
| **Blockchain** | Solidity 0.8.20 (`InsuranceAudit.sol`) on private EVM node (port 8545) |
| **Database** | PostgreSQL 16 Docker cluster with thread-safe connection pooling |
| **Backend API** | FastAPI / Uvicorn (port 8000) |
| **Frontend UI** | React 18 + Vite dashboard with dark-mode palette (port 3000) |

---

## Key System Architecture & Capabilities

```
  Insurer 1        Insurer 2   ...   Insurer 6
(insurer1_db)    (insurer2_db)     (insurer6_db)
      │                 │                 │
      └──── Local XGBoost Training ───────┘
                        │
            Flower Federated Aggregator
          (FedAvg + Differential Privacy)
                        │
          Global Certified Model M1 (SHA-256)
                        │
         ┌───────────────────────────────┐
         │   Solidity EVM Smart Contract │
         │   (InsuranceAudit.sol: 8545)  │
         │   • Write-once Claim Hashes   │
         │   • Anchored TreeSHAP Hashes  │
         │   • Registered Model Hashes   │
         └───────────────────────────────┘
                        │
       FastAPI Backend & Cryptographic Auditor (8000)
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
React Consortium Dashboard    Terminal Blockchain Explorer
   (http://localhost:3000)      (explore_blocks.py)
```

1. **Zero Raw Data Sharing**: Raw agricultural claims never leave the insurer node. Each insurer maintains an independent, isolated PostgreSQL database.
2. **Federated Learning with Differential Privacy**: Model weights are trained collaboratively across nodes using Flower FL with $L_2$ clipping and Gaussian noise ($\epsilon=1.2$), achieving $97.8\%$ AUC-ROC without privacy leaks.
3. **Immutable Smart Contract Commitments**: Model weights (`M1`), claim canonical SHA-256 hashes, and TreeSHAP explanation hashes are permanently anchored in the `InsuranceAudit.sol` smart contract on Ethereum.
4. **Selective TreeSHAP Anchoring**: High-risk claims automatically generate local TreeSHAP explanations whose hashes are anchored on-chain for dispute audits. Clean claims skip SHAP overhead to conserve block space.
5. **4-Phase Cryptographic Auditor**: Verifies local PostgreSQL records against on-chain Ethereum commitments in real-time. Includes an interactive live tamper sandbox to test and observe immediate fraud detection.

---

## Directory Structure

```
.
├── backend/                        ← FastAPI backend & services
│   ├── app.py                      ← REST API routes & intake pipeline
│   ├── audit.py                    ← 4-phase cryptographic audit service
│   ├── db.py                       ← PostgreSQL thread-safe connection pool
│   ├── hashing.py                  ← RFC-8785 canonical JSON & SHA-256
│   └── inference.py                ← Inference engine & TreeSHAP generation
│
├── blockchain/                     ← Solidity EVM blockchain layer
│   ├── solidity/InsuranceAudit.sol ← Solidity 0.8.20 audit smart contract
│   ├── deploy_contract.py          ← Smart contract compilation & deployment
│   ├── contract_deployment.json    ← Deployed contract address, ABI & metadata
│   ├── chain_client.py             ← Web3 Python client & atomic ledger backup
│   └── explore_blocks.py           ← Terminal blockchain explorer CLI
│
├── dashboard/                      ← Consortium React + Vite frontend
│   ├── src/                        ← React source components & styles
│   │   ├── components/Header.jsx   ← Consortium header & insurer switcher
│   │   ├── components/IntakeView.jsx ← Real-time intake & gauge
│   │   ├── components/ClaimsView.jsx ← Claims ledger & TreeSHAP drawer
│   │   ├── components/AuditorView.jsx← 4-phase matrix & tamper attack sandbox
│   │   └── components/NetworkView.jsx← Multi-tenant cluster status & models
│   ├── package.json
│   └── vite.config.js
│
├── data/                           ← Data storage & partitions
│   ├── nodes/                      ← Insurer 1–6 private claim CSVs
│   └── processed/                  ← Full preprocessed dataset
│
├── db/                             ← PostgreSQL initialization
│   ├── init/init.sql               ← Multi-database & user creation
│   └── init/init_tables.sql        ← Common tables (claims, explanations, audit_log)
│
├── docs/                           ← Technical phase documentation
│   ├── phase2-data-preprocessing.md
│   ├── phase3-baseline-training.md
│   ├── phase4-federated-learning-flower.md
│   ├── phase5-differential-privacy.md
│   └── phase6-poisoning-defense.md
│
├── evaluation/                     ← Benchmark reports & logs
│   ├── baseline_results.md
│   ├── fl_vs_centralized.md
│   ├── privacy_vs_accuracy.md
│   └── poisoning_defense_report.md
│
├── ml/                             ← Machine learning pipelines
│   ├── baseline/                   ← Centralized baseline training
│   ├── federated/                  ← Flower FL client & DP runner
│   └── shap/                       ← Feature importance & explainer utilities
│
├── models/                         ← Serialized model weights & stats
│   ├── xgb_dp_federated.json       ← Certified federated DP model (M1)
│   ├── xgb_centralized.json        ← Centralized baseline model (M0)
│   └── preprocess_stats.json       ← Feature scaling & normalization stats
│
├── docker-compose.yaml             ← Multi-container setup (PostgreSQL 16 + Ganache)
├── BLOCKCHAIN_COMMANDS.md          ← Copy-paste cheatsheet for blockchain CLI
├── requirements.txt                ← Python package dependencies
└── README.md                       ← Project documentation
```

---

## Quick Start

### 1. Launch Docker Infrastructure
Start the PostgreSQL 16 cluster (`port 5433`) and Ganache EVM blockchain (`port 8545`):
```bash
docker compose up -d
```

### 2. Start FastAPI Backend API
```bash
blockvenv\Scripts\python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```
Health Check: [http://localhost:8000/health](http://localhost:8000/health)

### 3. Start Consortium Dashboard
```bash
cd dashboard
npm install
npm run dev
```
Open in browser: [http://localhost:3000](http://localhost:3000)

### 4. Explore Blockchain from Terminal
```bash
# View recent mined blocks and smart contract activity
blockvenv\Scripts\python blockchain/explore_blocks.py

# Inspect a specific block in detail
blockvenv\Scripts\python blockchain/explore_blocks.py --block 40

# Query a claim stored directly in Solidity storage
blockvenv\Scripts\python blockchain/explore_blocks.py --claim CLM-NORMAL-VERIFIED-01

# List all claims anchored on the ledger
blockvenv\Scripts\python blockchain/explore_blocks.py --all-claims

# Live real-time block stream
blockvenv\Scripts\python blockchain/explore_blocks.py --watch
```
*(See [`BLOCKCHAIN_COMMANDS.md`](BLOCKCHAIN_COMMANDS.md) for full commands and JSON-RPC endpoints).*
