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
          │  Audit Ledger           │
          │  (hashes only, no data) │
          └─────────────────────────┘
                        │
              SHAP Explanations
              (local, per-claim)
                        │
              Investigator Dashboard
```

---

## Phase Documentation

| Phase | Status | Doc | What Was Done |
|-------|--------|-----|---------------|
| **Phase 1** | ✅ Done | — | Environment setup (Python, Go, Docker, Node, Fabric) |
| **Phase 2** | ✅ Done | [phase2-data-preprocessing.md](./phase2-data-preprocessing.md) | Dataset download, cleaning, feature engineering, node partitioning |
| **Phase 3** | ✅ Done | [phase3-baseline-training.md](./phase3-baseline-training.md) | Centralized XGBoost baseline — F1: 0.9848 |
| **Phase 4** | ⏳ Next | — | Federated Learning with Flower (6 insurer nodes) |
| **Phase 5** | ⏳ Pending | — | Differential privacy & secure aggregation |
| **Phase 6** | ⏳ Pending | — | Poisoning attack simulation & defense |
| **Phase 7** | ⏳ Pending | — | Robust aggregation (FedMedian, Krum) |
| **Phase 8** | ⏳ Pending | — | Hyperledger Fabric network setup |
| **Phase 9** | ⏳ Pending | — | Chaincode (smart contract) development |
| **Phase 10** | ⏳ Pending | — | Blockchain-Python integration |
| **Phase 11** | ⏳ Pending | — | Claim commitment & prediction anchoring |
| **Phase 12** | ⏳ Pending | — | SHAP explanations (local, privacy-safe) |
| **Phase 13** | ⏳ Pending | — | Investigator dashboard |
| **Phase 14** | ⏳ Pending | — | Evaluation, benchmarking & bias analysis |

---

## Key Results So Far

### Phase 3 — Centralized Baseline

| Model | F1 | PR-AUC | Verdict |
|-------|-----|--------|---------|
| Logistic Regression | 0.2632 | 0.4440 | Too weak — eliminated |
| Random Forest | 0.9992 | 0.9999 | Overfit to labels — not chosen |
| **XGBoost** | **0.9848** | **0.9998** | **Primary model** |

**FL Target:** Achieve F1 ≥ 0.95 without sharing raw data across insurers.

---

## Repository Structure

```
d:\Blockchain\
│
├── docs/                          ← Phase-wise documentation (YOU ARE HERE)
│   ├── README.md                  ← This file
│   ├── phase2-data-preprocessing.md
│   └── phase3-baseline-training.md
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
│   ├── federated/                 ← Phase 4 — FL scripts (coming)
│   └── shap/
│       └── explanations/          ← Phase 12 — SHAP outputs (coming)
│
├── blockchain/
│   ├── fabric-network/            ← Phase 8 — Fabric config (coming)
│   ├── chaincode/                 ← Phase 9 — Smart contracts (coming)
│   └── client/                    ← Phase 10 — Python-Fabric bridge (coming)
│
├── models/
│   └── xgb_centralized.json       ← Trained XGBoost model (all 200 trees)
│
├── evaluation/
│   └── baseline_results.md        ← Phase 3 model comparison report
│
├── notebooks/                     ← Jupyter notebooks (coming)
├── dashboard/                     ← Phase 13 — Investigator UI (coming)
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
