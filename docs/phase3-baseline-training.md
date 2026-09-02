# Phase 3 — Centralized Baseline Training
## Crop Insurance Fraud Detection | Federated Blockchain Project

---

## What Was Done — Full Detailed Walkthrough

---

## Overview

Before running Federated Learning, we need a **centralized benchmark** — train all models on the full combined dataset as if one entity owned everything. This gives us:

1. A reference F1/AUC score to beat with FL
2. Justification for choosing XGBoost as the primary model
3. The saved XGBoost model that the FL pipeline will start from

---

## Step 1 — Feature Selection

From the 20 columns in `full_dataset.csv`, we selected **14 features** as model inputs:

| Feature | Type | Why Chosen |
|---------|------|-----------|
| `commodity_code` | Categorical int | Crop type affects claim patterns |
| `cause_of_loss_code` | Categorical | Direct fraud signal (codes 92, 93) |
| `month_of_loss` | Ordinal | Seasonal fraud patterns |
| `indemnity_amount` | Numeric | Raw payout amount |
| `total_premium` | Numeric | Premium paid — normalizes payout |
| `liability_amount` | Numeric | Max insured value |
| `net_determined_acres` | Numeric | Acres with confirmed loss |
| `net_planted_acres` | Numeric | Total planted acres |
| `determined_yield` | Numeric | Reported yield at loss |
| `indemnity_to_premium_ratio` | Engineered | Key fraud signal |
| `indemnity_to_liability_ratio` | Engineered | Key fraud signal |
| `yield_deviation` | Engineered | State-year normalized yield |
| `high_cause_code` | Engineered binary | Fraud cause code flag (0/1) |
| `county_claim_frequency` | Engineered | Claim density in that county+crop |

**Excluded columns:**
- `loss_ratio` — dollar amount mislabeled as ratio, confusing for models
- `state_code`, `state_abbr`, `county_code` — geographic ID, not a pattern signal
- `commodity_year`, `year_of_loss` — temporal leakage risk

**Target:** `fraud_label` (0 = normal, 1 = fraud)

---

## Step 2 — Train / Test Split

```
677,150 total records
    │
    ├── 541,720 TRAIN (80%)  →  model learns from this
    │     └── Fraud in train: 20,339  (3.75%)
    │
    └── 135,430 TEST  (20%)  →  model never sees during training
          └── Fraud in test:   5,085  (3.75%)
```

**Why stratified split?**
`stratify=y` ensures **both halves maintain the same 3.75% fraud rate**. Without this, by chance the test set might have very few fraud cases, making evaluation unreliable.

---

## Step 3 — Class Imbalance Handling

The dataset is heavily imbalanced:
```
Normal  →  651,726 records  (96.25%)
Fraud   →   25,424 records  ( 3.75%)
```

**Why this matters:**
A model that predicts "normal" for every single record gets **96.25% accuracy** but catches **zero fraud**. Accuracy is useless here.

**Fix applied per model:**

| Model | Imbalance Fix |
|-------|--------------|
| Logistic Regression | `class_weight='balanced'` — sklearn auto-weights |
| Random Forest | `class_weight='balanced'` — same |
| XGBoost | `scale_pos_weight = 651726 / 25424 = 25.63` |

`scale_pos_weight=25.63` tells XGBoost:
> "Every fraud case is worth 25.63× a normal case during training."

This forces the model to focus on catching fraud rather than ignoring it.

---

## Step 4 — Model 1: Logistic Regression

**What it is:** Draws a single straight-line decision boundary between fraud and normal.

```python
LogisticRegression(
    class_weight='balanced',  # auto-weights fraud class
    max_iter=1000,            # max iterations to converge
    solver='lbfgs'            # optimization algorithm
)
```

**Training time:** 59.8 seconds (slowest — math convergence on 541K rows)

### Results

| Metric | Value | Interpretation |
|--------|-------|---------------|
| F1 Score | 0.2632 | Very poor overall score |
| Precision | 0.1535 | Only 15% of flagged claims were actually fraud |
| Recall | 0.9217 | Caught 92% of all fraud BUT... |
| ROC-AUC | 0.9347 | Good discrimination ability |
| PR-AUC | 0.4440 | Poor for imbalanced data |

### Confusion Matrix

```
                    Predicted Normal   Predicted Fraud
Actually Normal  │  104,507 (TN ✅)  │  25,838 (FP ❌) ← 25K false alarms!
Actually Fraud   │      398 (FN ❌)  │   4,687 (TP ✅)
```

**Verdict:** High recall but terrible precision. Caught most fraud but raised **25,838 false alarms** — 1 in every 5 normal claims was wrongly flagged. Too impractical for real use. **Eliminated.**

---

## Step 5 — Model 2: Random Forest

**What it is:** Builds 100 independent decision trees, each on a random data subset. Final prediction = majority vote.

```python
RandomForestClassifier(
    n_estimators=100,         # 100 trees
    class_weight='balanced',  # fraud weighted equally
    max_depth=12,             # trees max 12 levels deep
    n_jobs=-1                 # all CPU cores
)
```

**Training time:** 16.7 seconds

### Results

| Metric | Value | Interpretation |
|--------|-------|---------------|
| F1 Score | 0.9992 | Near perfect |
| Precision | 0.9998 | 99.98% of flags were real fraud |
| Recall | 0.9986 | Caught 99.86% of all fraud |
| ROC-AUC | 1.0000 | Perfect discrimination |
| PR-AUC | 0.9999 | Near-perfect on imbalanced data |

### Confusion Matrix

```
                    Predicted Normal   Predicted Fraud
Actually Normal  │  130,344 (TN ✅)  │       1 (FP ❌)  ← only 1 false alarm!
Actually Fraud   │       7  (FN ❌)  │   5,078 (TP ✅)
```

**Verdict:** Suspiciously perfect. Our fraud labels were created **by rules** — Random Forest essentially memorized those exact rules from the training set. This is called **overfitting to the labeling function**. Not a trustworthy real-world score. **Not chosen as primary** — too brittle.

---

## Step 6 — Model 3: XGBoost (PRIMARY)

**What it is:** Builds 200 trees **sequentially** — each new tree corrects the mistakes of all previous trees. This is called **gradient boosting**.

```python
XGBClassifier(
    n_estimators=200,          # 200 sequential boosting rounds
    max_depth=6,               # max 6 levels per tree
    learning_rate=0.05,        # small steps to avoid overfit
    subsample=0.8,             # each tree uses 80% of rows
    colsample_bytree=0.8,      # each tree uses 80% of features
    scale_pos_weight=25.63,    # fraud weight = 651726/25424
    eval_metric='aucpr'        # optimize PR-AUC (best for imbalanced)
)
```

**Training time:** 13.3 seconds (fastest of the three!)

### Training Progress (PR-AUC per round)

```
Round   0:  0.99957  ← already excellent from first round
Round  20:  0.99819
Round  40:  0.99724  ← brief dip (exploring)
Round  60:  0.99927  ← recovering
Round 100:  0.99972
Round 140:  0.99975
Round 199:  0.99977  ← converged, stopped improving
```

### Results

| Metric | Value | Interpretation |
|--------|-------|---------------|
| F1 Score | 0.9848 | Excellent |
| Precision | 0.9711 | 97% of flags were real fraud |
| Recall | 0.9988 | Missed only 6 fraud cases |
| ROC-AUC | 1.0000 | Perfect discrimination |
| PR-AUC | 0.9998 | Near-perfect on imbalanced data |

### Confusion Matrix

```
                    Predicted Normal   Predicted Fraud
Actually Normal  │  130,194 (TN ✅)  │     151 (FP ❌)  ← only 151 false alarms
Actually Fraud   │       6  (FN ❌)  │   5,079 (TP ✅)  ← missed only 6 fraud cases
```

**Verdict:** Slightly lower F1 than Random Forest (0.9848 vs 0.9992) but **more honest** — it generalizes better rather than memorizing rules. Fastest training. Best suited for federated deployment. **SELECTED as primary model.**

---

## Step 7 — Model Comparison

| Model | F1 | Precision | Recall | ROC-AUC | PR-AUC | Time |
|-------|-----|-----------|--------|---------|--------|------|
| Logistic Regression | 0.2632 | 0.1535 | 0.9217 | 0.9347 | 0.4440 | 59.8s |
| Random Forest | 0.9992 | 0.9998 | 0.9986 | 1.0000 | 0.9999 | 16.7s |
| **XGBoost** ⭐ | **0.9848** | **0.9711** | **0.9988** | **1.0000** | **0.9998** | **13.3s** |

> **XGBoost chosen** — best balance of performance, speed, and generalization.
> Its F1 score of **0.9848** becomes the benchmark for Federated Learning.
> FL must come within ~2-3% of this to be considered successful.

---

## Step 8 — Feature Importance (XGBoost)

XGBoost reveals which features it relied on most:

| Rank | Feature | What it means |
|------|---------|--------------|
| 1 | `indemnity_to_premium_ratio` | Primary fraud signal — engineered feature |
| 2 | `cause_of_loss_code` | Fraud cause codes (92, 93) |
| 3 | `yield_deviation` | Abnormal yield — engineered feature |
| 4 | `county_claim_frequency` | Repeat fraud hotspots |
| 5 | `indemnity_amount` | Raw payout size |
| ... | ... | ... |

> All top features are either **engineered features** (Phase 2) or **fraud-specific codes** — confirms our feature engineering was effective.

---

## Files Produced

```
d:\Blockchain\
├── ml\
│   └── baseline\
│       ├── train_baseline.py        ← training script (all 3 models)
│       └── baseline_results.csv     ← raw metrics table (all 3 models)
│
├── models\
│   └── xgb_centralized.json        ← saved XGBoost model (all 200 trees)
│
└── evaluation\
    └── baseline_results.md          ← formatted results report
```

---

## What Each File Stores

### `baseline_results.csv`
A simple table — one row per model, all metrics in columns:
```
model, f1, precision, recall, roc_auc, pr_auc, TP, FP, FN, TN
Logistic Regression, 0.2632, 0.1535, 0.9217, 0.9347, 0.4440, 4687, 25838, 398, 104507
Random Forest,       0.9992, 0.9998, 0.9986, 1.0000, 0.9999, 5078, 1, 7, 130344
XGBoost,             0.9848, 0.9711, 0.9988, 1.0000, 0.9998, 5079, 151, 6, 130194
```
Used for charts and comparison tables in the final report.

### `baseline_results.md`
Human-readable version of the CSV — formatted as a markdown table with feature importance section. The file you're reading now is the detailed version of this.

### `xgb_centralized.json`
The full XGBoost model serialized to disk. Stores:
- All **200 decision trees** (each as a JSON object with nodes, splits, weights)
- **14 feature names** and their types
- All **hyperparameters** used during training
- Internal statistics for each tree node

This file is loaded in **Phase 4** as the starting point for Federated Learning. Each insurer node gets a copy, trains locally on their data, and sends back only the weight updates — not this file.

---

## Limitations

> [!NOTE]
> These are **not bugs** — document them in the final research report.

1. **Labels are synthetic** — F1=0.9848 reflects how well models learn our heuristic rules, not real-world fraud detection accuracy.

2. **Random Forest overfitting** — F1=0.9992 is artificially high because RF memorized the same rules used to create labels.

3. **No time-series split** — we used random 80/20 split. A more rigorous approach would train on 2019–2022 and test on 2023 (temporal split). This is noted for Phase 14.

4. **Centralized assumption** — in this phase, all 6 insurers' data was pooled. In reality, this is illegal/impractical. Phase 4 onwards uses only local data per node.

---

## Next Step — Phase 4

**Federated Learning with Flower** — train XGBoost across 6 insurer nodes using the Flower FL framework. Each node trains locally on its own CSV. Only model updates (not data) are shared. Target: FL F1 ≥ 0.95 (within 3-4% of centralized baseline).

---

## Baseline to Beat in FL

```
XGBoost Centralized (Phase 3):
  F1       = 0.9848  ← FL must be ≥ 0.95
  PR-AUC   = 0.9998  ← FL must be ≥ 0.96
  Recall   = 0.9988  ← FL must be ≥ 0.97  (critical — missing fraud is dangerous)
```
