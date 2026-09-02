"""
Phase 3 — Centralized Baseline Training
Crop Insurance Fraud Detection

Trains 3 models on full combined dataset:
  1. Logistic Regression  (interpretable baseline)
  2. Random Forest        (strong tree baseline)
  3. XGBoost             (primary model → goes into FL pipeline)

Saves:
  - models/xgb_centralized.json
  - ml/baseline/baseline_results.csv
  - evaluation/baseline_results.md
"""

import pandas as pd
import numpy as np
import os
import json
import time
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    f1_score, precision_score, recall_score,
    roc_auc_score, average_precision_score,
    classification_report, confusion_matrix
)
import xgboost as xgb

# ── Config ────────────────────────────────────────────────────────────────────
FEATURE_COLS = [
    'commodity_code',
    'cause_of_loss_code',
    'month_of_loss',
    'indemnity_amount',
    'total_premium',
    'liability_amount',
    'net_determined_acres',
    'net_planted_acres',
    'determined_yield',
    'indemnity_to_premium_ratio',
    'indemnity_to_liability_ratio',
    'yield_deviation',
    'high_cause_code',
    'county_claim_frequency',
]
TARGET_COL = 'fraud_label'
RANDOM_STATE = 42
TEST_SIZE = 0.2

os.makedirs('models', exist_ok=True)
os.makedirs('evaluation', exist_ok=True)

# ── Step 1: Load Data ─────────────────────────────────────────────────────────
print("=" * 65)
print("PHASE 3 — CENTRALIZED BASELINE TRAINING")
print("=" * 65)
print("\n[1/6] Loading dataset...")

df = pd.read_csv('data/processed/full_dataset.csv', low_memory=False)

# cause_of_loss_code has mixed types — convert to numeric
df['cause_of_loss_code'] = pd.to_numeric(df['cause_of_loss_code'], errors='coerce').fillna(0)

X = df[FEATURE_COLS].fillna(0)
y = df[TARGET_COL]

print(f"      Total records : {len(df):,}")
print(f"      Features      : {len(FEATURE_COLS)}")
print(f"      Fraud (1)     : {y.sum():,}  ({y.mean()*100:.2f}%)")
print(f"      Normal (0)    : {(y==0).sum():,}  ({(1-y.mean())*100:.2f}%)")

# ── Step 2: Train/Test Split ──────────────────────────────────────────────────
print("\n[2/6] Splitting data (80% train / 20% test, stratified)...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
    stratify=y
)
print(f"      Train : {len(X_train):,} records  |  Fraud: {y_train.sum():,} ({y_train.mean()*100:.2f}%)")
print(f"      Test  : {len(X_test):,}  records  |  Fraud: {y_test.sum():,}  ({y_test.mean()*100:.2f}%)")

# ── Helper: Evaluate Model ────────────────────────────────────────────────────
def evaluate(name, model, X_test, y_test, y_prob):
    y_pred = (y_prob >= 0.5).astype(int)
    f1        = f1_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall    = recall_score(y_test, y_pred)
    roc_auc   = roc_auc_score(y_test, y_prob)
    pr_auc    = average_precision_score(y_test, y_prob)
    cm        = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()

    print(f"\n      --- {name} Results ---")
    print(f"      F1 Score   : {f1:.4f}")
    print(f"      Precision  : {precision:.4f}  (of flagged claims, how many are real fraud)")
    print(f"      Recall     : {recall:.4f}  (of all fraud, how many were caught)")
    print(f"      ROC-AUC    : {roc_auc:.4f}")
    print(f"      PR-AUC     : {pr_auc:.4f}  (best metric for imbalanced data)")
    print(f"      Confusion Matrix:")
    print(f"        True Negatives  (correct normal)  : {tn:,}")
    print(f"        False Positives (wrong alarm)      : {fp:,}")
    print(f"        False Negatives (missed fraud)     : {fn:,}")
    print(f"        True Positives  (caught fraud)     : {tp:,}")

    return {
        'model': name,
        'f1': round(f1, 4),
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'roc_auc': round(roc_auc, 4),
        'pr_auc': round(pr_auc, 4),
        'true_negatives': int(tn),
        'false_positives': int(fp),
        'false_negatives': int(fn),
        'true_positives': int(tp),
    }

results = []

# ── Step 3: Logistic Regression ───────────────────────────────────────────────
print("\n[3/6] Training Logistic Regression...")
t0 = time.time()
lr = LogisticRegression(
    class_weight='balanced',
    max_iter=1000,
    random_state=RANDOM_STATE,
    solver='lbfgs',
    n_jobs=-1
)
lr.fit(X_train, y_train)
lr_time = time.time() - t0
print(f"      Training time : {lr_time:.1f}s")
lr_prob = lr.predict_proba(X_test)[:, 1]
results.append(evaluate("Logistic Regression", lr, X_test, y_test, lr_prob))

# ── Step 4: Random Forest ─────────────────────────────────────────────────────
print("\n[4/6] Training Random Forest (100 trees)...")
t0 = time.time()
rf = RandomForestClassifier(
    n_estimators=100,
    class_weight='balanced',
    max_depth=12,
    random_state=RANDOM_STATE,
    n_jobs=-1
)
rf.fit(X_train, y_train)
rf_time = time.time() - t0
print(f"      Training time : {rf_time:.1f}s")
rf_prob = rf.predict_proba(X_test)[:, 1]
results.append(evaluate("Random Forest", rf, X_test, y_test, rf_prob))

# ── Step 5: XGBoost ───────────────────────────────────────────────────────────
print("\n[5/6] Training XGBoost (PRIMARY MODEL)...")
scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
print(f"      scale_pos_weight : {scale_pos_weight:.2f}  (handles class imbalance)")

t0 = time.time()
xgb_model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=scale_pos_weight,
    eval_metric='aucpr',
    use_label_encoder=False,
    random_state=RANDOM_STATE,
    n_jobs=-1,
    verbosity=0,
)
xgb_model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=20,   # print every 20 rounds
)
xgb_time = time.time() - t0
print(f"\n      Training time : {xgb_time:.1f}s")
xgb_prob = xgb_model.predict_proba(X_test)[:, 1]
results.append(evaluate("XGBoost", xgb_model, X_test, y_test, xgb_prob))

# Save XGBoost model
xgb_model.save_model('models/xgb_centralized.json')
print("\n      Saved: models/xgb_centralized.json")

# ── Step 6: Save Results ──────────────────────────────────────────────────────
print("\n[6/6] Saving results...")

# CSV
results_df = pd.DataFrame(results)
results_df.to_csv('ml/baseline/baseline_results.csv', index=False)
print("      Saved: ml/baseline/baseline_results.csv")

# Feature importance from XGBoost
importance = pd.DataFrame({
    'feature': FEATURE_COLS,
    'importance': xgb_model.feature_importances_
}).sort_values('importance', ascending=False)

# Markdown report
md_content = f"""# Phase 3 — Centralized Baseline Results

## Dataset
| Property | Value |
|----------|-------|
| Total Records | {len(df):,} |
| Train Records | {len(X_train):,} |
| Test Records  | {len(X_test):,} |
| Fraud Rate    | {y.mean()*100:.2f}% |
| Features Used | {len(FEATURE_COLS)} |

## Model Comparison

| Model | F1 | Precision | Recall | ROC-AUC | PR-AUC |
|-------|-----|-----------|--------|---------|--------|
"""
for r in results:
    bold = "**" if r['model'] == "XGBoost" else ""
    md_content += f"| {bold}{r['model']}{bold} | {bold}{r['f1']}{bold} | {bold}{r['precision']}{bold} | {bold}{r['recall']}{bold} | {bold}{r['roc_auc']}{bold} | {bold}{r['pr_auc']}{bold} |\n"

md_content += f"""
> XGBoost selected as primary model for the Federated Learning pipeline.

## XGBoost Feature Importance

| Rank | Feature | Importance |
|------|---------|-----------|
"""
for i, row in enumerate(importance.itertuples(), 1):
    md_content += f"| {i} | `{row.feature}` | {row.importance:.4f} |\n"

md_content += f"""
## Training Times
| Model | Time (seconds) |
|-------|---------------|
| Logistic Regression | {lr_time:.1f}s |
| Random Forest | {rf_time:.1f}s |
| XGBoost | {xgb_time:.1f}s |

## Saved Model
- `models/xgb_centralized.json` — XGBoost model for FL pipeline
"""

with open('evaluation/baseline_results.md', 'w') as f:
    f.write(md_content)
print("      Saved: evaluation/baseline_results.md")

# ── Final Summary ─────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("PHASE 3 COMPLETE — SUMMARY")
print("=" * 65)
print(f"\n{'Model':<25} {'F1':>6} {'ROC-AUC':>8} {'PR-AUC':>7}")
print("-" * 50)
for r in results:
    marker = " <-- PRIMARY" if r['model'] == "XGBoost" else ""
    print(f"{r['model']:<25} {r['f1']:>6.4f} {r['roc_auc']:>8.4f} {r['pr_auc']:>7.4f}{marker}")
print("\nXGBoost model saved to: models/xgb_centralized.json")
print("Full results saved to:  evaluation/baseline_results.md")
