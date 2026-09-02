# Phase 3 — Centralized Baseline Results

## Dataset
| Property | Value |
|----------|-------|
| Total Records | 677,150 |
| Train Records | 541,720 |
| Test Records  | 135,430 |
| Fraud Rate    | 3.75% |
| Features Used | 14 |

## Model Comparison

| Model | F1 | Precision | Recall | ROC-AUC | PR-AUC |
|-------|-----|-----------|--------|---------|--------|
| Logistic Regression | 0.2632 | 0.1535 | 0.9217 | 0.9347 | 0.444 |
| Random Forest | 0.9992 | 0.9998 | 0.9986 | 1.0 | 0.9999 |
| **XGBoost** | **0.9848** | **0.9711** | **0.9988** | **1.0** | **0.9998** |

> XGBoost selected as primary model for the Federated Learning pipeline.

## XGBoost Feature Importance

| Rank | Feature | Importance |
|------|---------|-----------|
| 1 | `cause_of_loss_code` | 0.7961 |
| 2 | `indemnity_to_premium_ratio` | 0.1300 |
| 3 | `yield_deviation` | 0.0272 |
| 4 | `total_premium` | 0.0085 |
| 5 | `net_planted_acres` | 0.0077 |
| 6 | `indemnity_to_liability_ratio` | 0.0070 |
| 7 | `commodity_code` | 0.0067 |
| 8 | `month_of_loss` | 0.0053 |
| 9 | `determined_yield` | 0.0047 |
| 10 | `indemnity_amount` | 0.0031 |
| 11 | `county_claim_frequency` | 0.0027 |
| 12 | `liability_amount` | 0.0008 |
| 13 | `net_determined_acres` | 0.0000 |
| 14 | `high_cause_code` | 0.0000 |

## Training Times
| Model | Time (seconds) |
|-------|---------------|
| Logistic Regression | 59.8s |
| Random Forest | 16.7s |
| XGBoost | 13.3s |

## Saved Model
- `models/xgb_centralized.json` — XGBoost model for FL pipeline
