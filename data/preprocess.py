"""
Phase 2 — Data Preprocessing Pipeline
Crop Insurance Fraud Detection
"""

import pandas as pd
import numpy as np
import os

# ── Column names (RMA Cause of Loss standard layout) ──────────────────────────
COLS = [
    'commodity_year', 'state_code', 'state_abbr', 'county_code', 'county_name',
    'commodity_code', 'commodity_name', 'insurance_plan_code', 'insurance_plan_abbr',
    'coverage_category', 'stage_code', 'cause_of_loss_code', 'cause_of_loss_desc',
    'month_of_loss', 'month_of_loss_abbr', 'year_of_loss',
    'policies_earning_premium', 'policies_indemnified',
    'net_planted_acres', 'net_endorsed_acres', 'liability_amount',
    'total_premium', 'subsidy', 'state_private_subsidy',
    'additional_subsidy', 'efa_premium_discount',
    'net_determined_acres', 'indemnity_amount', 'loss_ratio',
    'determined_yield'
]

NUMERIC_COLS = [
    'indemnity_amount', 'total_premium', 'liability_amount',
    'net_determined_acres', 'net_planted_acres', 'loss_ratio',
    'determined_yield', 'policies_earning_premium', 'policies_indemnified'
]

KEEP_COLS = [
    'commodity_year', 'state_code', 'state_abbr', 'county_code',
    'commodity_code', 'commodity_name', 'cause_of_loss_code', 'cause_of_loss_desc',
    'month_of_loss', 'year_of_loss',
    'indemnity_amount', 'total_premium', 'liability_amount',
    'net_determined_acres', 'net_planted_acres', 'loss_ratio',
    'determined_yield', 'policies_earning_premium', 'policies_indemnified'
]

FILES = [
    'data/raw/colsom_2019.txt',
    'data/raw/colsom_2020.txt',
    'data/raw/colsom_2021.txt',
    'data/raw/colsom_2022.txt',
    'data/raw/colsom_2023.txt',
]

# ── Step 1: Load all years ─────────────────────────────────────────────────────
print("=" * 60)
print("STEP 1 — Loading all 5 years of data")
print("=" * 60)

frames = []
for f in FILES:
    year = f.split('colsom_')[1].split('.')[0]
    df_yr = pd.read_csv(f, sep='|', names=COLS, low_memory=False)
    df_yr = df_yr[KEEP_COLS]
    frames.append(df_yr)
    print(f"  {year}: {len(df_yr):>8,} records loaded")

df = pd.concat(frames, ignore_index=True)
print(f"\nTotal combined records: {len(df):,}")

# ── Step 2: Clean ─────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 2 — Cleaning data")
print("=" * 60)

# Convert numeric columns
for col in NUMERIC_COLS:
    df[col] = pd.to_numeric(df[col], errors='coerce')

before = len(df)
df = df.dropna(subset=['indemnity_amount', 'total_premium', 'liability_amount'])
print(f"  Dropped rows with missing key values: {before - len(df):,}")

# Remove zero/negative premiums (invalid records)
before = len(df)
df = df[df['total_premium'] > 0]
df = df[df['liability_amount'] > 0]
print(f"  Dropped zero/negative premium or liability: {before - len(df):,}")

# Cap extreme outliers at 99.9th percentile
for col in ['indemnity_amount', 'total_premium', 'liability_amount']:
    cap = df[col].quantile(0.999)
    df[col] = df[col].clip(upper=cap)

print(f"  Final clean records: {len(df):,}")

# ── Step 3: Feature Engineering ───────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 3 — Engineering features")
print("=" * 60)

# Primary fraud-signal features
df['indemnity_to_premium_ratio'] = df['indemnity_amount'] / (df['total_premium'] + 1)
df['indemnity_to_liability_ratio'] = df['indemnity_amount'] / (df['liability_amount'] + 1)

# Yield deviation from state-year mean
state_year_mean = df.groupby(['state_abbr', 'commodity_year'])['determined_yield'].transform('mean')
df['yield_deviation'] = df['determined_yield'] / (state_year_mean + 1e-6)

# High-risk cause of loss codes (historically fraud-prone categories)
HIGH_RISK_CAUSES = [91, 92, 93, 94, 95, 96]
df['high_cause_code'] = df['cause_of_loss_code'].isin(HIGH_RISK_CAUSES).astype(int)

# Repeat claimant flag
claim_freq = df.groupby(['state_code', 'county_code', 'commodity_code'])['policies_indemnified'].transform('sum')
df['county_claim_frequency'] = claim_freq

print(f"  indemnity_to_premium_ratio  — min: {df['indemnity_to_premium_ratio'].min():.2f}, max: {df['indemnity_to_premium_ratio'].max():.2f}, mean: {df['indemnity_to_premium_ratio'].mean():.2f}")
print(f"  yield_deviation             — mean: {df['yield_deviation'].mean():.2f}")
print(f"  high_cause_code flag rate   — {df['high_cause_code'].mean()*100:.1f}%")

# ── Step 4: Fraud Label (Heuristic) ───────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 4 — Creating fraud labels (heuristic method)")
print("=" * 60)

def label_fraud(row):
    """
    Heuristic fraud-risk label.
    NOT ground truth — a proxy anomaly signal for simulation.
    Score >= 3 is flagged as high-risk.
    """
    score = 0
    if row['indemnity_to_premium_ratio'] > 5:
        score += 2
    if row['indemnity_to_liability_ratio'] > 0.8:
        score += 1
    if row['high_cause_code'] == 1:
        score += 1
    if row['yield_deviation'] > 2.5 or row['yield_deviation'] < 0.2:
        score += 1
    return int(score >= 3)

df['fraud_label'] = df.apply(label_fraud, axis=1)

fraud_rate = df['fraud_label'].mean()
print(f"  Total records:   {len(df):,}")
print(f"  Fraud-flagged:   {df['fraud_label'].sum():,}  ({fraud_rate*100:.2f}%)")
print(f"  Normal:          {(df['fraud_label']==0).sum():,}  ({(1-fraud_rate)*100:.2f}%)")

# ── Step 5: Partition into 6 Insurer Nodes (by state, non-IID) ────────────────
print("\n" + "=" * 60)
print("STEP 5 — Partitioning into 6 insurer nodes")
print("=" * 60)

states = sorted(df['state_abbr'].str.strip().unique())
print(f"  Total unique states/territories: {len(states)}")

np.random.seed(42)
shuffled_states = np.random.permutation(states)
state_splits = np.array_split(shuffled_states, 6)

os.makedirs('data/nodes', exist_ok=True)

FEATURE_COLS = [
    'commodity_year', 'state_code', 'state_abbr', 'county_code',
    'commodity_code', 'cause_of_loss_code', 'month_of_loss', 'year_of_loss',
    'indemnity_amount', 'total_premium', 'liability_amount',
    'net_determined_acres', 'net_planted_acres', 'loss_ratio',
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
    print(f"  Insurer {node_id}: {len(node_df):>8,} records | States: {node_states} | Fraud rate: {fraud_pct:.2f}%")

# ── Step 6: Save full processed dataset ───────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 6 — Saving full processed dataset")
print("=" * 60)

os.makedirs('data/processed', exist_ok=True)
df[FEATURE_COLS].to_csv('data/processed/full_dataset.csv', index=False)
print(f"  Saved: data/processed/full_dataset.csv  ({len(df):,} records)")

print("\n" + "=" * 60)
print("PHASE 2 COMPLETE")
print("=" * 60)
print(f"  data/raw/         — 5 raw files")
print(f"  data/processed/   — full_dataset.csv")
print(f"  data/nodes/       — insurer_1.csv through insurer_6.csv")
