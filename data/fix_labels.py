"""
Phase 2b — Fix Fraud Labels with correct thresholds
Based on actual data distribution analysis
"""

import pandas as pd
import numpy as np

print("Loading processed dataset...")
df = pd.read_csv('data/processed/full_dataset.csv')
print(f"Records: {len(df):,}")

# ── Revised Heuristic Label Strategy ─────────────────────────────────────────
# Based on actual distribution:
# - indemnity_to_premium_ratio: mean=0.03, >1.0 is already very high
# - cause_of_loss codes 92 (fraud/misrepresentation), 93 (suspected fraud) exist
# - yield_deviation: std=1.35, extremes are suspicious
# - indemnity_to_liability_ratio: high payout relative to insured value

# Fix cause code — they are strings in this dataset
df['cause_of_loss_code_str'] = df['cause_of_loss_code'].astype(str).str.strip()

FRAUD_CAUSE_CODES = ['92', '93']   # fraud/misrepresentation codes

def label_fraud_revised(row):
    """
    Revised heuristic fraud-risk label calibrated to actual data distribution.
    Target: ~5% fraud rate for realistic imbalanced dataset simulation.
    Score >= 2 is flagged as high-risk.
    """
    score = 0

    # Strong signal: very high indemnity relative to premium
    if row['indemnity_to_premium_ratio'] > 0.5:
        score += 2
    elif row['indemnity_to_premium_ratio'] > 0.15:
        score += 1

    # Strong signal: fraud/misrepresentation cause codes
    if str(row['cause_of_loss_code']).strip() in FRAUD_CAUSE_CODES:
        score += 2

    # Anomalous yield (extreme deviation from state-year mean)
    yd = row['yield_deviation']
    if yd > 4.0 or yd < 0.1:
        score += 1

    # High indemnity relative to liability
    if row['indemnity_to_liability_ratio'] > 0.3:
        score += 1

    return int(score >= 2)

print("\nApplying revised fraud labels...")
df['fraud_label'] = df.apply(label_fraud_revised, axis=1)

fraud_rate = df['fraud_label'].mean()
print(f"\nFraud-flagged : {df['fraud_label'].sum():,}  ({fraud_rate*100:.2f}%)")
print(f"Normal        : {(df['fraud_label']==0).sum():,}  ({(1-fraud_rate)*100:.2f}%)")

# ── Show breakdown by signal ───────────────────────────────────────────────────
print("\n=== Fraud signal breakdown ===")
print(f"High ratio (>0.5)         : {(df['indemnity_to_premium_ratio'] > 0.5).sum():,}")
print(f"Moderate ratio (0.15-0.5) : {((df['indemnity_to_premium_ratio'] > 0.15) & (df['indemnity_to_premium_ratio'] <= 0.5)).sum():,}")
print(f"Fraud cause codes (92,93) : {df['cause_of_loss_code_str'].isin(FRAUD_CAUSE_CODES).sum():,}")
print(f"Extreme yield deviation   : {((df['yield_deviation'] > 4.0) | (df['yield_deviation'] < 0.1)).sum():,}")
print(f"High indemnity/liability  : {(df['indemnity_to_liability_ratio'] > 0.3).sum():,}")

# ── Re-save processed dataset ─────────────────────────────────────────────────
df.drop(columns=['cause_of_loss_code_str'], inplace=True)
df.to_csv('data/processed/full_dataset.csv', index=False)
print(f"\nUpdated: data/processed/full_dataset.csv")

# ── Re-partition into 6 nodes ─────────────────────────────────────────────────
print("\n=== Re-partitioning into 6 insurer nodes ===")
states = sorted(df['state_abbr'].str.strip().unique())
np.random.seed(42)
shuffled_states = np.random.permutation(states)
state_splits = np.array_split(shuffled_states, 6)

FEATURE_COLS = [
    'commodity_year', 'state_code', 'state_abbr', 'county_code',
    'commodity_code', 'cause_of_loss_code', 'month_of_loss', 'year_of_loss',
    'indemnity_amount', 'total_premium', 'liability_amount',
    'net_determined_acres', 'net_planted_acres',
    'determined_yield', 'indemnity_to_premium_ratio',
    'indemnity_to_liability_ratio', 'yield_deviation',
    'high_cause_code', 'county_claim_frequency', 'fraud_label'
]

for i, state_group in enumerate(state_splits):
    node_id = i + 1
    node_states = [s.strip() for s in state_group]
    node_df = df[df['state_abbr'].str.strip().isin(node_states)][FEATURE_COLS].copy()
    out_path = f'data/nodes/insurer_{node_id}.csv'
    node_df.to_csv(out_path, index=False)
    fraud_pct = node_df['fraud_label'].mean() * 100
    print(f"  Insurer {node_id}: {len(node_df):>8,} records | Fraud rate: {fraud_pct:.2f}% | States: {node_states}")

print("\nPHASE 2 — LABELS FIXED & COMPLETE")
