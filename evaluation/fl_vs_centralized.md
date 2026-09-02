# Phase 4 — Federated vs. Centralized Performance Comparison

## Architecture Comparison

| Property | Centralized Baseline (Phase 3) | Federated Learning (Phase 4) |
| :--- | :--- | :--- |
| **Data Privacy** | ❌ All 677K claims pooled in 1 database | 🔒 **Zero raw data shared (6 private nodes)** |
| **Training Architecture** | Single-server training | Multi-node Federated Learning |
| **Nodes** | 1 central server | 6 independent Insurer Nodes |
| **FL Rounds** | N/A (1 central run) | 5 Federated Rounds |
| **Total Training Time** | 13.3s | 9.2s |

## Metric Comparison on Global Test Set

| Metric | Centralized XGBoost (Phase 3) | Federated XGBoost (Phase 4) | Delta |
| :--- | :--- | :--- | :--- |
| **F1 Score** | **0.9848** | **0.9938** | **+0.0090** |
| **PR-AUC** | **0.9998** | **0.9983** | **-0.0015** |
| **ROC-AUC** | 1.0000 | 1.0000 | +0.0000 |
| **Precision** | 0.9711 | 0.9927 | +0.0216 |
| **Recall (Fraud Caught)** | 0.9988 | 0.9949 | -0.0039 |

## Round-by-Round FL Convergence

| Round | F1-Score | PR-AUC | Precision | Recall | False Alarms (FP) | Missed Fraud (FN) | Duration |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 0.9764 | 0.9915 | 0.9550 | 0.9986 | 239 | 7 | 3.6s |
| 2 | 0.9910 | 0.9989 | 0.9864 | 0.9957 | 70 | 22 | 1.0s |
| 3 | 0.9937 | 0.9983 | 0.9922 | 0.9953 | 40 | 24 | 1.4s |
| 4 | 0.9938 | 0.9981 | 0.9929 | 0.9947 | 36 | 27 | 1.5s |
| 5 | 0.9938 | 0.9983 | 0.9927 | 0.9949 | 37 | 26 | 1.6s |

## Key Takeaways
1. **Zero Data Leakage**: All 6 insurer nodes trained strictly on their local partition without moving any raw claims data.
2. **Benchmark Achieved**: Federated model achieved an F1 of **0.9938** on the global holdout set, successfully matching the Centralized benchmark.
