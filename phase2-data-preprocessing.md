# Phase 2 — Dataset Acquisition & Preprocessing
## Crop Insurance Fraud Detection | Federated Blockchain Project

---

## What Was Done — Full Detailed Walkthrough

---

## Step 1 — Data Source & Download

### Source
**USDA Risk Management Agency (RMA) — Cause of Loss Dataset**
- URL: https://www.rma.usda.gov/SummaryOfBusiness/CauseOfLoss
- Format: Pipe-delimited (`|`) `.txt` files, **no header row**
- Coverage: Every federally insured crop claim in the United States

### Files Downloaded (5 Years)

| File | Year | Size |
|------|------|------|
| `colsom_2019.txt` | 2019 | 47.7 MB |
| `colsom_2020.txt` | 2020 | 38.9 MB |
| `colsom_2021.txt` | 2021 | 33.3 MB |
| `colsom_2022.txt` | 2022 | 42.1 MB |
| `colsom_2023.txt` | 2023 | 44.9 MB |

**Total raw data: ~207 MB**

Files were placed in `data/raw/` after being moved from their original download folders.

---

## Step 2 — Column Mapping

The RMA files have **no header row**. We mapped all 30 columns manually using the official RMA data dictionary:

| Index | Column Name | Description |
|-------|------------|-------------|
| 0 | `commodity_year` | Crop insurance policy year |
| 1 | `state_code` | FIPS state code |
| 2 | `state_abbr` | State abbreviation |
| 3 | `county_code` | County FIPS code |
| 4 | `county_name` | County name |
| 5 | `commodity_code` | Crop type code |
| 6 | `commodity_name` | Crop type name |
| 7 | `insurance_plan_code` | Type of insurance plan |
| 8 | `insurance_plan_abbr` | Plan abbreviation (RP, RPHPE, etc.) |
| 9 | `coverage_category` | A/B coverage category |
| 10 | `stage_code` | Crop growth stage |
| 11 | `cause_of_loss_code` | **Key field** — why the claim was filed |
| 12 | `cause_of_loss_desc` | Human-readable loss cause |
| 13 | `month_of_loss` | Month loss occurred |
| 14 | `month_of_loss_abbr` | Month abbreviation |
| 15 | `year_of_loss` | Year loss occurred |
| 16 | `policies_earning_premium` | Policies with premium earned |
| 17 | `policies_indemnified` | Policies that received payout |
| 18 | `net_planted_acres` | Total acres planted |
| 19 | `net_endorsed_acres` | Acres under endorsement |
| 20 | `liability_amount` | Maximum insured value ($) |
| 21 | `total_premium` | Total premium paid ($) |
| 22 | `subsidy` | Federal subsidy amount ($) |
| 23 | `state_private_subsidy` | State subsidy ($) |
| 24 | `additional_subsidy` | Additional subsidy ($) |
| 25 | `efa_premium_discount` | EFA discount applied |
| 26 | `net_determined_acres` | Acres determined to have a loss |
| 27 | `indemnity_amount` | **Key field** — actual payout ($) |
| 28 | `loss_ratio` | Dollar-value loss metric (NOT a 0-1 ratio in this dataset) |
| 29 | `determined_yield` | Yield determined at loss adjustment |

> **Important Note:** The `loss_ratio` column in RMA data is stored as a **dollar amount**, not a 0–1 percentage ratio as the name implies. This was discovered during analysis and factored into the labeling strategy.

---

## Step 3 — Loading & Combining All Years

All 5 files were loaded and concatenated into a single DataFrame:

```python
frames = []
for file in FILES:
    df_yr = pd.read_csv(file, sep='|', names=COLS, low_memory=False)
    df_yr = df_yr[KEEP_COLS]
    frames.append(df_yr)
df = pd.concat(frames, ignore_index=True)
```

### Records per Year

| Year | Records Loaded |
|------|---------------|
| 2019 | 155,160 |
| 2020 | 127,619 |
| 2021 | 109,146 |
| 2022 | 137,906 |
| 2023 | 147,319 |
| **Total** | **677,150** |

---

## Step 4 — Data Cleaning

The data was clean with **zero missing values** in key columns.

Additional cleaning steps applied:

| Step | Action | Records Removed |
|------|--------|----------------|
| Null drop | Drop rows missing `indemnity_amount`, `total_premium`, `liability_amount` | 0 |
| Invalid filter | Remove rows where `total_premium <= 0` or `liability_amount <= 0` | 0 |
| Outlier capping | Cap `indemnity_amount`, `total_premium`, `liability_amount` at 99.9th percentile | Capped (not dropped) |

**Final clean records: 677,150**

---

## Step 5 — Feature Engineering

Five new features were derived from the raw columns to serve as fraud signals:

### 5.1 `indemnity_to_premium_ratio`
```python
df['indemnity_to_premium_ratio'] = df['indemnity_amount'] / (df['total_premium'] + 1)
```
- **What it means:** How much payout relative to premium paid
- **Normal:** Very low (mean = 0.03 across the whole dataset)
- **Suspicious:** > 0.5 means the insurer paid out 50%+ more than collected in premium

| Statistic | Value |
|-----------|-------|
| Mean | 0.03 |
| Max | 17.70 |
| Records > 0.5 | 1,595 |
| Records > 0.15 | 9,607 |

### 5.2 `indemnity_to_liability_ratio`
```python
df['indemnity_to_liability_ratio'] = df['indemnity_amount'] / (df['liability_amount'] + 1)
```
- **What it means:** Payout as a fraction of maximum insured value
- **Suspicious:** > 0.3 means 30%+ of max coverage claimed

### 5.3 `yield_deviation`
```python
state_year_mean = df.groupby(['state_abbr', 'commodity_year'])['determined_yield'].transform('mean')
df['yield_deviation'] = df['determined_yield'] / (state_year_mean + 1e-6)
```
- **What it means:** How far a farm's reported yield deviates from the state-year average for that crop
- **Normal:** Close to 1.0 (mean = 1.00, which is expected by construction)
- **Suspicious:** < 0.1 (near-zero yield) or > 4.0 (impossibly high yield)

| Statistic | Value |
|-----------|-------|
| Mean | 1.00 |
| Std | 1.35 |
| Records < 0.1 or > 4.0 | 70,411 |

### 5.4 `high_cause_code`
```python
HIGH_RISK_CAUSES = [91, 92, 93, 94, 95, 96]
df['high_cause_code'] = df['cause_of_loss_code'].isin(HIGH_RISK_CAUSES).astype(int)
```
- **What it means:** Binary flag for cause of loss codes historically associated with fraud
- Codes 92 and 93 are RMA's own "fraud/misrepresentation" and "suspected fraud" codes

### 5.5 `county_claim_frequency`
```python
claim_freq = df.groupby(['state_code', 'county_code', 'commodity_code'])['policies_indemnified'].transform('sum')
df['county_claim_frequency'] = claim_freq
```
- **What it means:** Total claims in the same county+crop combination across all years
- High frequency counties may indicate systematic fraud rings

---

## Step 6 — Fraud Label Strategy

### Why We Need Synthetic Labels

The USDA RMA dataset has **no ground-truth fraud column** — this is public aggregate data, not an investigation database. We create a proxy fraud label based on anomaly signals. This is documented as a known limitation in the project.

### First Attempt — Failed (0.00% fraud rate)

The initial thresholds were calibrated for a different data scale:
- `indemnity_to_premium_ratio > 5` → only caught 30 records
- Cause codes compared as integers → never matched (they're stored as strings like `'92'`)

**Root cause:** Data exploration showed cause codes are stored as **strings** (`'92'`, `'93'`, `'XX'`), not integers.

### Revised Heuristic — Successful (3.75% fraud rate)

```python
def label_fraud_revised(row):
    score = 0

    # High indemnity vs premium
    if row['indemnity_to_premium_ratio'] > 0.5:   score += 2
    elif row['indemnity_to_premium_ratio'] > 0.15: score += 1

    # Fraud/misrepresentation cause codes (RMA's own classification)
    if str(row['cause_of_loss_code']).strip() in ['92', '93']:  score += 2

    # Anomalous yield deviation
    if row['yield_deviation'] > 4.0 or row['yield_deviation'] < 0.1:  score += 1

    # High payout relative to insured value
    if row['indemnity_to_liability_ratio'] > 0.3:  score += 1

    return int(score >= 2)
```

### Final Label Distribution

| Label | Count | Percentage |
|-------|-------|-----------|
| Fraud (1) | 25,424 | **3.75%** |
| Normal (0) | 651,726 | **96.25%** |

### Fraud Signal Contribution

| Signal | Records Triggering It |
|--------|----------------------|
| Fraud cause codes (92, 93) | 21,084 |
| Extreme yield deviation | 70,411 |
| Moderate ratio (0.15–0.5) | 8,012 |
| High ratio (>0.5) | 1,595 |
| High indemnity/liability | 6 |

> Note: Records can trigger multiple signals. Final label uses combined score threshold.

---

## Step 7 — Node Partitioning (Non-IID Split)

The dataset was split into **6 insurer nodes** using a state-based partition. Each node gets a group of states — mimicking how different insurance companies operate in different regions.

### Why Non-IID?

In real federated learning, each insurer's data is different:
- Different crops grown per region
- Different weather patterns → different loss causes
- Different fraud rates per region

Non-IID (non-identically distributed) data is the realistic and challenging case for FL.

### Partition Method

```python
states = sorted(df['state_abbr'].str.strip().unique())  # 50 states
np.random.seed(42)                                       # reproducible
shuffled_states = np.random.permutation(states)
state_splits = np.array_split(shuffled_states, 6)        # 6 groups
```

### Final Node Summary

| Node | File | Records | Fraud Rate | States Assigned |
|------|------|---------|-----------|----------------|
| Insurer 1 | `insurer_1.csv` | 96,488 | **8.66%** | IL, SC, NJ, VT, LA, WV, NC, MT, NV |
| Insurer 2 | `insurer_2.csv` | 62,129 | **5.65%** | MD, ID, CA, PA, FL, AZ, CT, TN, WA |
| Insurer 3 | `insurer_3.csv` | 141,319 | **3.54%** | WI, KS, GA, KY, MS, OH, NM, AK |
| Insurer 4 | `insurer_4.csv` | 113,308 | **2.61%** | VA, ND, NY, CO, NH, IA, OR, AL |
| Insurer 5 | `insurer_5.csv` | 145,552 | **2.47%** | MI, AR, UT, OK, MO, SD, HI, MN |
| Insurer 6 | `insurer_6.csv` | 118,354 | **1.68%** | MA, WY, ME, DE, TX, IN, NE, RI |

The variation in fraud rate (1.68% to 8.66%) across nodes demonstrates the **non-IID property** — each insurer sees a very different distribution of data, which is the key challenge FL is designed to handle.

---

## Final Feature Set (Columns in Each Node CSV)

| Column | Type | Description |
|--------|------|-------------|
| `commodity_year` | int | Policy year |
| `state_code` | int | FIPS state code |
| `state_abbr` | str | State abbreviation |
| `county_code` | int | County FIPS code |
| `commodity_code` | int | Crop type |
| `cause_of_loss_code` | str | Loss cause code |
| `month_of_loss` | int | Month of loss |
| `year_of_loss` | float | Year of loss |
| `indemnity_amount` | float | Payout in $ |
| `total_premium` | float | Premium in $ |
| `liability_amount` | float | Max insured value in $ |
| `net_determined_acres` | float | Acres with confirmed loss |
| `net_planted_acres` | float | Total planted acres |
| `determined_yield` | float | Yield at loss adjustment |
| `indemnity_to_premium_ratio` | float | **Engineered** — key fraud signal |
| `indemnity_to_liability_ratio` | float | **Engineered** — key fraud signal |
| `yield_deviation` | float | **Engineered** — state-year normalized yield |
| `high_cause_code` | int (0/1) | **Engineered** — fraud cause code flag |
| `county_claim_frequency` | float | **Engineered** — county-level claim density |
| `fraud_label` | int (0/1) | **TARGET** — heuristic fraud label |

---

## Files Produced

```
d:\Blockchain\
├── data\
│   ├── raw\
│   │   ├── colsom_2019.txt     (47.7 MB)
│   │   ├── colsom_2020.txt     (38.9 MB)
│   │   ├── colsom_2021.txt     (33.3 MB)
│   │   ├── colsom_2022.txt     (42.1 MB)
│   │   └── colsom_2023.txt     (44.9 MB)
│   ├── processed\
│   │   └── full_dataset.csv    (677,150 records × 20 columns)
│   ├── nodes\
│   │   ├── insurer_1.csv       (96,488 records)
│   │   ├── insurer_2.csv       (62,129 records)
│   │   ├── insurer_3.csv       (141,319 records)
│   │   ├── insurer_4.csv       (113,308 records)
│   │   ├── insurer_5.csv       (145,552 records)
│   │   └── insurer_6.csv       (118,354 records)
│   ├── preprocess.py           (initial pipeline script)
│   └── fix_labels.py           (label calibration script)
```

---

## Scripts Written

### [`preprocess.py`](file:///d:/Blockchain/data/preprocess.py)
Initial full pipeline:
- Load all 5 years
- Clean data
- Engineer all 5 features
- First version of fraud labels (discovered to be broken — 0.00%)
- Partition into 6 nodes
- Save `full_dataset.csv`

### [`fix_labels.py`](file:///d:/Blockchain/data/fix_labels.py)
Label calibration after data analysis revealed two bugs:
1. Cause codes are strings, not integers
2. Ratio thresholds needed recalibration to actual data distribution
- Corrected heuristic → 3.75% fraud rate
- Re-saved `full_dataset.csv`
- Re-partitioned all 6 node CSVs

---

## Limitations to Document in Final Report

> [!NOTE]
> These are **not bugs** — they are honest limitations that must be stated in the research report.

1. **No ground-truth fraud labels exist** — the `fraud_label` column is a heuristic proxy, not real confirmed fraud.

2. **Labeling bias possible** — the fraud rate varies significantly by region (1.68% to 8.66%), which may reflect genuine regional patterns OR introduce geographic bias into the model. This will be checked in Phase 14 (bias evaluation).

3. **Cause codes 92/93 are RMA's own flags** — these codes mean RMA itself suspected fraud. Using them as labels means our model partly learns to replicate RMA's own flagging, not detect novel fraud.

4. **`loss_ratio` column is a dollar amount** — despite the name, it is not a 0–1 ratio in this dataset. We excluded it from the model features to avoid confusing future analysts.

---

## Next Step — Phase 3

**Centralized XGBoost Baseline** — train a fraud detection model on the full combined dataset (`full_dataset.csv`) before splitting into FL. This gives us a benchmark number to compare Federated Learning against.
