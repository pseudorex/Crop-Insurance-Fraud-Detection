# Federated, Blockchain-Audited Crop Insurance Fraud Detection

> A multi-insurer federated learning system with Hyperledger Fabric audit layer for detecting crop insurance fraud — without sharing raw claims data.

---

## Project Summary

| Property | Value |
|----------|-------|
| **Type** | Research / Engineering Project |
| **Domain** | InsureTech, Federated Learning, Blockchain |
| **Dataset** | USDA RMA Cause of Loss (2019–2023) |
| **Records** | 677,150 crop insurance claims |
| **Nodes** | 6 simulated insurer nodes |
| **Primary Model** | XGBoost (Federated via Flower) |
| **Blockchain** | Hyperledger Fabric (etcdraft consensus) |

---

## Key System Features & Capabilities

1. 🔒 **Local Data Ownership (Zero Data Sharing)**: Raw claim records never leave the insurer node. Each insurer trains exclusively on its private local dataset.
2. 🤝 **Federated Model Aggregation**: Flower FL aggregates gradient/tree weight updates across nodes using `FedAvg` and `FedProx` for non-IID data.
3. ⛓️ **Blockchain-Based Model Versioning & Lineage**: Every global model version (`M_0`, `M_1`, ... `M_r`) has its SHA-256 hash and contributor metadata immutably anchored on Hyperledger Fabric, establishing a tamper-proof version history.
4. 🛡️ **Claim & Prediction Audit Commitments**: Prediction hashes and model version references are committed to the ledger to prevent post-hoc claim manipulation.
5. 🔍 **Local Privacy-Preserving Explainability**: SHAP explanations are computed locally at the insurer node; only explanation hashes are anchored on-chain.
6. 📊 **Investigator Dashboard**: Interactive web dashboard for fraud investigators to audit claims, verify blockchain provenance, and inspect SHAP feature attributions.

---

## Architecture

```
 Insurer 1        Insurer 2   ...   Insurer 6
 (96K claims)     (62K claims)      (118K claims)
     │                 │                 │
     └──── Local XGBoost Training ───────┘
                        │
              Flower FL Aggregator
              (FedAvg / FedProx)
                        │
              Global Model Update
                        │
          ┌─────────────────────────┐
          │  Hyperledger Fabric     │
          │  Audit & Version Ledger │
          │  (SHA-256 hashes only)  │
          └─────────────────────────┘
                        │
              SHAP Explanations
              (local, per-claim)
                        │
              Investigator Dashboard
```

---

## 💡 Important Research Note: Why Centralized Training in Phase 3?

> **Question: Did training on the complete dataset in Phase 3 violate privacy?**
>
> **Answer:** In a real production deployment across competing insurance companies, pooling all raw data in one place **does violate data privacy regulations (GDPR/HIPAA/CCPA)** and anti-trust laws. 
>
> In Machine Learning research, Phase 3 is the **"Centralized Upper-Bound Benchmark"**:
> - We intentionally train a hypothetical centralized model first to find the **theoretical maximum accuracy (F1: `0.9848`)**.
> - This provides the **scientific reference point** against which our decentralized Federated Learning system (Phases 4–14) is evaluated.
> - **The Goal of the Project:** Prove that our Federated system achieves near-identical fraud detection performance (`F1 ≥ 0.95`) **without ever sharing or pooling raw data across insurers**.

---

## Phase Documentation

| Phase | Status | Doc | What Was Done |
|-------|--------|-----|---------------|
| **Phase 1** | ✅ Done | — | Environment setup (Python, Go, Docker, Node, Fabric) |
| **Phase 2** | ✅ Done | [phase2-data-preprocessing.md](./phase2-data-preprocessing.md) | Dataset download, cleaning, feature engineering, node partitioning |
| **Phase 3** | ✅ Done | [phase3-baseline-training.md](./phase3-baseline-training.md) | Centralized XGBoost baseline benchmark — F1: 0.9848 |
| **Phase 4** | ✅ Done | [phase4-federated-learning-flower.md](./phase4-federated-learning-flower.md) | Federated Learning with Flower (6 insurer nodes) — F1: 0.9938 |
| **Phase 5** | ✅ Done | [phase5-differential-privacy.md](./phase5-differential-privacy.md) | Differential privacy & secure aggregation (SecAgg) — F1: 0.9938 |
| **Phase 6** | ✅ Done | [phase6-poisoning-defense.md](./phase6-poisoning-defense.md) | Poisoning attack simulation & robust Byzantine defense (Trimmed Mean, Multi-Krum, Norm-Outlier Rejection) |
| **Phase 7** | ✅ Done | [phase7-fabric-network-setup.md](./phase7-fabric-network-setup.md) | Hyperledger Fabric network setup & 6-insurer consortium topology |
| **Phase 8** | ⏳ Next | — | Chaincode (smart contract) & model versioning |
| **Phase 9** | ⏳ Pending | — | Blockchain-Python client integration |
| **Phase 10** | ⏳ Pending | — | Claim commitment & prediction anchoring |
| **Phase 11** | ⏳ Pending | — | SHAP explanations (local, privacy-safe) |
| **Phase 12** | ⏳ Pending | — | Investigator dashboard |
| **Phase 13** | ⏳ Pending | — | End-to-end auditability & tamper-evidence verification |
| **Phase 14** | ⏳ Pending | — | Comprehensive evaluation, benchmarking & bias analysis |

---

## Key Results So Far

### Phase 3 — Centralized Baseline Benchmark

| Model | F1 | PR-AUC | Verdict |
|-------|-----|--------|---------|
| Logistic Regression | 0.2632 | 0.4440 | Too weak — eliminated |
| Random Forest | 0.9992 | 0.9999 | Overfit to heuristic rules — not chosen |
| **XGBoost** | **0.9848** | **0.9998** | **Primary benchmark model** |

**FL Target:** Achieve F1 ≥ 0.95 without sharing raw data across insurers.

### Phase 4–6 Federated Multi-Tier Evolution

| Phase | Architecture | Raw Claims Private? | Aggregator Sees Weights? | Byzantine Poisoning Defense | Global F1 | PR-AUC |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Phase 3** | Centralized Benchmark | ❌ No (Pooled) | N/A | None | **0.9848** | **0.9998** |
| **Phase 4** | Plain FL (Flower) | 🔒 Yes | ⚠️ Yes | None | **0.9938** | **0.9983** |
| **Phase 5** | DP-Hardened FL | 🔒 Yes | 🔒 No (SecAgg) | Gaussian DP | **0.9938** | **0.9983** |
| **Phase 6** | Byzantine-Defended FL | 🔒 Yes | 🔒 No (SecAgg) | Norm Filter + Trimmed Mean + Multi-Krum | **0.9938** | **0.9983** |

---

## Repository Structure

```
d:\Blockchain\
│
├── docs/                          ← Phase-wise documentation
│   ├── README.md                  ← Master documentation & project summary
│   ├── phase2-data-preprocessing.md
│   ├── phase3-baseline-training.md
│   ├── phase4-federated-learning-flower.md
│   ├── phase5-differential-privacy.md
│   └── phase6-poisoning-defense.md
│
├── data/
│   ├── raw/                       ← Raw RMA .txt files (gitignored, 207MB)
│   ├── processed/
│   │   └── full_dataset.csv       ← 677,150 records, 20 features (LFS)
│   ├── nodes/
│   │   ├── insurer_1.csv          ← Node 1: IL,SC,NJ,VT,LA... (8.66% fraud)
│   │   ├── insurer_2.csv          ← Node 2: MD,ID,CA,PA,FL... (5.65% fraud)
│   │   ├── insurer_3.csv          ← Node 3: WI,KS,GA,KY,MS... (3.54% fraud)
│   │   ├── insurer_4.csv          ← Node 4: VA,ND,NY,CO,NH... (2.61% fraud)
│   │   ├── insurer_5.csv          ← Node 5: MI,AR,UT,OK,MO... (2.47% fraud)
│   │   └── insurer_6.csv          ← Node 6: MA,WY,ME,DE,TX... (1.68% fraud)
│   ├── preprocess.py              ← Phase 2 pipeline script
│   └── fix_labels.py              ← Phase 2 label calibration script
│
├── ml/
│   ├── baseline/
│   │   ├── train_baseline.py      ← Phase 3 training script
│   │   └── baseline_results.csv   ← Metrics for all 3 models
│   ├── federated/
│   │   ├── fl_client.py           ← Phase 4: Insurer node Flower client
│   │   ├── fl_server.py           ← Phase 4: Custom FedAvg server
│   │   ├── train_federated.py     ← Phase 4: Plain FL simulation
│   │   ├── dp_mechanism.py        ← Phase 5: L2 clipping & SecAgg
│   │   ├── train_dp_federated.py  ← Phase 5: DP training & noise sweep
│   │   ├── robust_aggregation.py  ← Phase 6: Byzantine defenses & Anomaly Logger
│   │   └── simulate_poisoning.py  ← Phase 6: Attack simulation & defense runner
│   └── shap/
│       └── explanations/          ← Phase 11 — SHAP outputs (coming)
│
├── blockchain/
│   ├── fabric-network/            ← Phase 7 — Fabric config (coming)
│   ├── chaincode/                 ← Phase 8 — Smart contracts & Model versioning (coming)
│   └── client/                    ← Phase 9 — Python-Fabric bridge (coming)
│
├── models/
│   ├── xgb_centralized.json       ← Benchmark XGBoost model (all 200 trees)
│   ├── xgb_federated.json         ← Phase 4 Federated global model
│   └── xgb_dp_federated.json      ← Phase 5 Privacy-hardened model
│
├── evaluation/
│   ├── baseline_results.md        ← Phase 3 model comparison report
│   ├── fl_vs_centralized.md       ← Phase 4 federated evaluation
│   ├── privacy_vs_accuracy.md     ← Phase 5 DP tradeoff report
│   ├── poisoning_defense_report.md← Phase 6 attack resilience report
│   └── anomaly_audit_log.json     ← Phase 6 cryptographic audit ledger
│
├── notebooks/                     ← Jupyter notebooks (coming)
├── dashboard/                     ← Phase 12 — Investigator UI (coming)
│
├── implementation-guide.md        ← Full 14-phase implementation roadmap
├── crop-insurance-fraud-fl-blockchain-plan.md  ← Original project plan
├── requirements.txt               ← All Python packages (129 packages)
├── .gitignore
└── .gitattributes                 ← Git LFS rules for large CSVs
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Federated Learning | Flower (flwr) 1.7.0 |
| ML Model | XGBoost 3.2.0 |
| Explainability | SHAP 0.49.1 |
| Imbalance Handling | imbalanced-learn 0.14.2 |
| Blockchain | Hyperledger Fabric 2.5 |
| Smart Contract | Go (chaincode) |
| Blockchain Client | Python + fabric-sdk-py |
| Data Processing | pandas 2.3.3, numpy 1.26.4 |
| Visualization | matplotlib, seaborn |
| Dashboard | HTML/JS/CSS |
| Environment | Python 3.10.11, Docker 29.1.2, Go 1.21.13 |

---

## Dataset

**USDA RMA Cause of Loss Dataset**
- Source: https://www.rma.usda.gov/tools-reports/summary-of-business/cause-loss
- Format: Pipe-delimited `.txt`, no header row, 30 columns
- Years: 2019, 2020, 2021, 2022, 2023
- Total raw size: ~207 MB

> Raw files are excluded from the repo (`.gitignore`). Processed CSVs are stored via **Git LFS**.

---

## How to Reproduce

```bash
# 1. Clone the repo
git clone https://github.com/pseudorex/Crop-Insurance-Fraud-Detection.git
cd Crop-Insurance-Fraud-Detection

# 2. Create virtual environment
python -m venv blockvenv
.\blockvenv\Scripts\activate        # Windows
source blockvenv/bin/activate       # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download raw data (manual step)
# Visit: https://www.rma.usda.gov/tools-reports/summary-of-business/cause-loss
# Download 2019-2023 .txt files → place in data/raw/

# 5. Run preprocessing
python data/preprocess.py
python data/fix_labels.py

# 6. Run baseline training
python ml/baseline/train_baseline.py
```
