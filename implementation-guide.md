# Step-by-Step Implementation Guide
# Federated, Blockchain-Audited Crop Insurance Fraud Detection

---

## Table of Contents

1. [Environment Setup](#1-environment-setup)
2. [Dataset Acquisition & Preprocessing](#2-dataset-acquisition--preprocessing)
3. [Fraud Label Strategy & Centralized Baseline](#3-fraud-label-strategy--centralized-baseline)
4. [Federated Learning — Plain FedAvg Baseline](#4-federated-learning--plain-fedavg-baseline)
5. [Secure Aggregation](#5-secure-aggregation)
6. [Differential Privacy — Clip + Noise](#6-differential-privacy--clip--noise)
7. [Robust Aggregation + Poisoning Defense](#7-robust-aggregation--poisoning-defense)
8. [Hyperledger Fabric Network Setup](#8-hyperledger-fabric-network-setup)
9. [Chaincode Development & Deployment](#9-chaincode-development--deployment)
10. [Claim Registration & Hashing Workflow](#10-claim-registration--hashing-workflow)
11. [FL Update & Global Model Anchoring on Blockchain](#11-fl-update--global-model-anchoring-on-blockchain)
12. [Local Inference + SHAP + Prediction Commitments](#12-local-inference--shap--prediction-commitments)
13. [Investigator Audit & Verification Dashboard](#13-investigator-audit--verification-dashboard)
14. [Benchmarks, Tampering Demo & Final Evaluation](#14-benchmarks-tampering-demo--final-evaluation)

---

## 1. Environment Setup

### 1.1 Prerequisites

Install the following before starting:

- Python 3.10+
- Docker Desktop (latest stable)
- Git
- Node.js 18+ (for Fabric SDK / chaincode in JS/TS)
- Go 1.21+ (if writing chaincode in Go)

### 1.2 Create Project Structure

```bash
mkdir crop-insurance-fl-blockchain
cd crop-insurance-fl-blockchain

mkdir -p data/{raw,processed,nodes}
mkdir -p ml/{baseline,federated,shap}
mkdir -p blockchain/{fabric-network,chaincode,client}
mkdir -p notebooks
mkdir -p evaluation
mkdir -p dashboard
```

### 1.3 Python Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 1.4 Install Python Dependencies

```bash
pip install flwr==1.7.0
pip install xgboost scikit-learn shap imbalanced-learn
pip install pandas numpy matplotlib seaborn
pip install opacus torch          # Optional: for DP-SGD track
pip install jupyter notebook
pip install cryptography          # For SHA-256, CSPRNG utilities
pip install requests              # For Fabric REST API calls
```

Save to `requirements.txt`:

```bash
pip freeze > requirements.txt
```

### 1.5 Verify Docker

```bash
docker --version
docker-compose --version
docker run hello-world
```

---

## 2. Dataset Acquisition & Preprocessing

### 2.1 Download USDA RMA Data

Go to: https://www.rma.usda.gov/SummaryOfBusiness/CauseOfLoss

Download the **Cause of Loss** dataset for years 2018–2022 (CSV format).

Place raw files in `data/raw/`.

### 2.2 Explore the Data

```python
# notebooks/01_eda.ipynb
import pandas as pd

df = pd.read_csv('data/raw/colsom_2022.txt', sep='|', low_memory=False)
print(df.shape)
print(df.columns.tolist())
print(df.dtypes)
print(df.isnull().sum())
df.head()
```

### 2.3 Key Fields to Keep

```python
SELECTED_COLS = [
    'commodity_year',
    'state_code',
    'county_code',
    'commodity_code',
    'cause_of_loss_code',
    'month_of_loss',
    'net_indemnity',
    'net_determined_acres',
    'liability_amount',
    'premium_amount',
    'indemnity_count',
    'determined_yield',
]
df = df[SELECTED_COLS].dropna()
```

### 2.4 Feature Engineering

```python
df['indemnity_to_premium_ratio'] = df['net_indemnity'] / (df['premium_amount'] + 1)
df['yield_deviation'] = df['determined_yield'] / (df['determined_yield'].mean() + 1)
df['high_cause_code'] = df['cause_of_loss_code'].isin([91, 92, 93]).astype(int)
```

### 2.5 Fraud Label Strategy

Choose **one** of two strategies and document it clearly:

**Strategy A — Heuristic Labeling:**

```python
def label_fraud_heuristic(row):
    score = 0
    if row['indemnity_to_premium_ratio'] > 5:
        score += 2
    if row['high_cause_code'] == 1:
        score += 1
    if row['net_indemnity'] > df['net_indemnity'].quantile(0.95):
        score += 1
    return int(score >= 3)

df['fraud_label'] = df.apply(label_fraud_heuristic, axis=1)
print("Fraud rate:", df['fraud_label'].mean())
```

**Strategy B — Synthetic Injection:**

```python
import numpy as np

np.random.seed(42)
n = len(df)
fraud_idx = np.random.choice(n, size=int(n * 0.05), replace=False)
df['fraud_label'] = 0
df.loc[fraud_idx, 'fraud_label'] = 1
df.loc[fraud_idx, 'indemnity_to_premium_ratio'] *= np.random.uniform(3, 8, size=len(fraud_idx))
```

### 2.6 Partition Data into 6–8 Insurer Nodes

```python
state_groups = df.groupby('state_code')
states = list(state_groups.groups.keys())

import numpy as np
np.random.seed(0)
np.random.shuffle(states)

n_nodes = 6
node_states = np.array_split(states, n_nodes)

for i, state_list in enumerate(node_states):
    node_df = df[df['state_code'].isin(state_list)].copy()
    node_df.to_csv(f'data/nodes/insurer_{i+1}.csv', index=False)
    print(f"Node {i+1}: {len(node_df)} records | States: {state_list}")
```

### 2.7 Save Processed Data

```python
df.to_csv('data/processed/full_dataset.csv', index=False)
print("Preprocessing complete.")
```

---

## 3. Fraud Label Strategy & Centralized Baseline

### 3.1 Feature Matrix

```python
# ml/baseline/train_baseline.py
import pandas as pd
from sklearn.model_selection import train_test_split

FEATURE_COLS = [
    'indemnity_to_premium_ratio',
    'yield_deviation',
    'high_cause_code',
    'net_determined_acres',
    'liability_amount',
    'month_of_loss',
    'cause_of_loss_code',
]

df = pd.read_csv('data/processed/full_dataset.csv')
X = df[FEATURE_COLS]
y = df['fraud_label']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
```

### 3.2 Logistic Regression Baseline

```python
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score

lr = LogisticRegression(class_weight='balanced', max_iter=1000)
lr.fit(X_train, y_train)
y_pred = lr.predict(X_test)
print(classification_report(y_test, y_pred))
print("ROC-AUC:", roc_auc_score(y_test, lr.predict_proba(X_test)[:, 1]))
```

### 3.3 Random Forest Baseline

```python
from sklearn.ensemble import RandomForestClassifier

rf = RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42)
rf.fit(X_train, y_train)
y_pred_rf = rf.predict(X_test)
print(classification_report(y_test, y_pred_rf))
print("ROC-AUC:", roc_auc_score(y_test, rf.predict_proba(X_test)[:, 1]))
```

### 3.4 XGBoost Centralized Baseline

```python
import xgboost as xgb
from sklearn.metrics import f1_score, precision_score, recall_score, average_precision_score

scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

model = xgb.XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.05,
    scale_pos_weight=scale_pos_weight,
    eval_metric='aucpr',
    use_label_encoder=False,
    random_state=42,
)

model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

print("F1:", f1_score(y_test, y_pred))
print("Precision:", precision_score(y_test, y_pred))
print("Recall:", recall_score(y_test, y_pred))
print("ROC-AUC:", roc_auc_score(y_test, y_prob))
print("PR-AUC:", average_precision_score(y_test, y_prob))

model.save_model('ml/baseline/xgb_centralized.json')
```

---

## 4. Federated Learning — Plain FedAvg Baseline

### 4.1 FL Architecture Overview

```
Flower Server (aggregator)
    |-- Insurer Client 1 (data/nodes/insurer_1.csv)
    |-- Insurer Client 2 (data/nodes/insurer_2.csv)
    |-- ...
    `-- Insurer Client 6 (data/nodes/insurer_6.csv)
```

### 4.2 Define XGBoost FL Client

```python
# ml/federated/fl_client.py
import flwr as fl
import xgboost as xgb
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from typing import List

FEATURE_COLS = [
    'indemnity_to_premium_ratio', 'yield_deviation', 'high_cause_code',
    'net_determined_acres', 'liability_amount', 'month_of_loss', 'cause_of_loss_code',
]

class InsuranceFLClient(fl.client.NumPyClient):
    def __init__(self, insurer_id: int):
        self.insurer_id = insurer_id
        df = pd.read_csv(f'data/nodes/insurer_{insurer_id}.csv')
        X = df[FEATURE_COLS].values
        y = df['fraud_label'].values
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        self.model = None

    def get_parameters(self, config) -> List[np.ndarray]:
        if self.model is None:
            return [np.zeros(1)]
        return [np.array([0])]  # simplified placeholder

    def set_parameters(self, parameters):
        if parameters and len(parameters) > 0:
            self.model = xgb.XGBClassifier()
            self.model.load_model('global_model.json')

    def fit(self, parameters, config):
        self.set_parameters(parameters)
        if self.model is None:
            scale_pos_weight = (self.y_train == 0).sum() / max((self.y_train == 1).sum(), 1)
            self.model = xgb.XGBClassifier(
                n_estimators=10,
                max_depth=4,
                learning_rate=0.1,
                scale_pos_weight=scale_pos_weight,
                use_label_encoder=False,
                eval_metric='logloss',
            )
        self.model.fit(self.X_train, self.y_train, verbose=False)
        return self.get_parameters(config={}), len(self.X_train), {}

    def evaluate(self, parameters, config):
        from sklearn.metrics import log_loss, roc_auc_score
        self.set_parameters(parameters)
        y_prob = self.model.predict_proba(self.X_test)[:, 1]
        loss = log_loss(self.y_test, y_prob)
        auc = roc_auc_score(self.y_test, y_prob)
        return float(loss), len(self.X_test), {"roc_auc": float(auc)}
```

### 4.3 Define FL Server

```python
# ml/federated/fl_server.py
import flwr as fl

strategy = fl.server.strategy.FedAvg(
    fraction_fit=1.0,
    fraction_evaluate=1.0,
    min_fit_clients=6,
    min_evaluate_clients=6,
    min_available_clients=6,
)

fl.server.start_server(
    server_address="0.0.0.0:8080",
    config=fl.server.ServerConfig(num_rounds=10),
    strategy=strategy,
)
```

### 4.4 Flower Simulation Mode (Recommended for Local Dev)

```python
# ml/federated/simulate_fl.py
import flwr as fl
from fl_client import InsuranceFLClient

def client_fn(cid: str):
    return InsuranceFLClient(insurer_id=int(cid) + 1)

fl.simulation.start_simulation(
    client_fn=client_fn,
    num_clients=6,
    config=fl.server.ServerConfig(num_rounds=10),
    strategy=fl.server.strategy.FedAvg(
        fraction_fit=1.0,
        min_fit_clients=6,
        min_available_clients=6,
    ),
)
```

---

## 5. Secure Aggregation

### 5.1 Option A — Flower Built-in SecAgg (Recommended)

```python
# ml/federated/fl_server_secagg.py
import flwr as fl
from flwr.server.strategy import SecAgg  # Flower >= 1.7

strategy = SecAgg(
    num_shares=6,
    reconstruction_threshold=5,
    fraction_fit=1.0,
    min_fit_clients=6,
    min_available_clients=6,
)

fl.server.start_server(
    server_address="0.0.0.0:8080",
    config=fl.server.ServerConfig(num_rounds=10),
    strategy=strategy,
)
```

### 5.2 Option B — Custom Pairwise Additive Masking

```python
# ml/federated/secure_agg_utils.py
import numpy as np
from typing import List

def generate_pairwise_masks(n_clients: int, update_shape: int, seed: int = 42) -> np.ndarray:
    """
    Generate pairwise random masks. mask[i][j] = -mask[j][i].
    Aggregator sums all masked updates -> masks cancel -> gets true sum.
    """
    rng = np.random.default_rng(seed)
    masks = np.zeros((n_clients, n_clients, update_shape))
    for i in range(n_clients):
        for j in range(i + 1, n_clients):
            m = rng.standard_normal(update_shape)
            masks[i][j] = m
            masks[j][i] = -m
    return masks

def apply_mask(update: np.ndarray, client_id: int, masks: np.ndarray) -> np.ndarray:
    net_mask = masks[client_id].sum(axis=0)
    return update + net_mask

def aggregate_masked_updates(masked_updates: List[np.ndarray]) -> np.ndarray:
    combined = np.sum(masked_updates, axis=0)
    print("[AGGREGATOR] Only sees combined sum. Individual updates are NOT recoverable.")
    return combined / len(masked_updates)
```

---

## 6. Differential Privacy — Clip + Noise

### 6.1 DP Utilities

```python
# ml/federated/dp_utils.py
import numpy as np

CLIP_BOUND = 1.0     # C — L2 norm clipping bound
NOISE_SCALE = 0.1    # sigma — Gaussian noise multiplier

def clip_update(update: np.ndarray, clip_bound: float = CLIP_BOUND) -> np.ndarray:
    norm = np.linalg.norm(update)
    if norm > clip_bound:
        update = update * (clip_bound / norm)
    return update

def add_gaussian_noise(update: np.ndarray, clip_bound: float = CLIP_BOUND,
                       noise_scale: float = NOISE_SCALE) -> np.ndarray:
    noise = np.random.normal(0, noise_scale * clip_bound, size=update.shape)
    return update + noise

def privatize_update(update: np.ndarray) -> np.ndarray:
    """Full DP pipeline: clip then noise. Apply BEFORE masking."""
    clipped = clip_update(update)
    noised = add_gaussian_noise(clipped)
    return noised
```

### 6.2 Reconstruction Attack Test

```python
# evaluation/reconstruction_attack.py
import numpy as np

def reconstruction_error(original, recovered):
    return np.linalg.norm(original - recovered)

# Run with noise OFF vs ON — expect higher error with noise
print("Error without noise:", reconstruction_error(original, recovered_no_noise))
print("Error with noise:", reconstruction_error(original, recovered_with_noise))
```

Document the clipping bound (C) and noise scale (sigma) choice, and the accuracy vs. privacy tradeoff observed.

---

## 7. Robust Aggregation + Poisoning Defense

### 7.1 Coordinate-Wise Trimmed Mean

```python
# ml/federated/robust_aggregation.py
import numpy as np
from typing import List, Tuple

def trimmed_mean(updates: List[np.ndarray], trim_fraction: float = 0.1) -> np.ndarray:
    """Discard top and bottom trim_fraction of values per coordinate."""
    stacked = np.stack(updates, axis=0)
    n = stacked.shape[0]
    k = max(1, int(n * trim_fraction))
    sorted_vals = np.sort(stacked, axis=0)
    trimmed = sorted_vals[k: n - k, :]
    return np.mean(trimmed, axis=0)

def norm_outlier_rejection(updates: List[np.ndarray], multiplier: float = 2.0) -> Tuple[List, List]:
    """Reject updates whose L2 norm exceeds multiplier x median norm."""
    norms = np.array([np.linalg.norm(u) for u in updates])
    median_norm = np.median(norms)
    threshold = multiplier * median_norm
    good, flagged = [], []
    for i, (u, n) in enumerate(zip(updates, norms)):
        if n <= threshold:
            good.append(u)
        else:
            flagged.append(i)
            print(f"[ANOMALY] Client {i} flagged — norm {n:.3f} > threshold {threshold:.3f}")
    return good, flagged
```

### 7.2 Inject Poisoned Update (Demo)

```python
# evaluation/poisoning_demo.py
import numpy as np

def create_poisoned_update(normal_update: np.ndarray, scale: float = 100.0) -> np.ndarray:
    """Simulate model poisoning — dramatically scaled malicious update."""
    return normal_update * scale

updates = [get_update(i) for i in range(6)]
updates[0] = create_poisoned_update(updates[0])   # Insurer 0 is compromised

# Compare FedAvg vs. Robust
fedavg_result = np.mean(updates, axis=0)
robust_result, flagged = norm_outlier_rejection(updates)
robust_aggregated = np.mean(robust_result, axis=0)

print("FedAvg norm (corrupted):", np.linalg.norm(fedavg_result))
print("Robust norm (cleaned):", np.linalg.norm(robust_aggregated))
print("Flagged clients:", flagged)
```

### 7.3 Log Anomaly Flag to Blockchain

```python
# Called after robust aggregation detects outlier
blockchain_client.flag_anomalous_update(
    round_number=current_round,
    insurer_ref="INSURER_REF_HASH",   # anonymized reference
    reason_code="NORM_OUTLIER",
)
```

---

## 8. Hyperledger Fabric Network Setup

### 8.1 Install Fabric Binaries and Docker Images

```bash
curl -sSLO https://raw.githubusercontent.com/hyperledger/fabric/main/scripts/install-fabric.sh
chmod +x install-fabric.sh
./install-fabric.sh docker binary samples

export PATH=$PWD/bin:$PATH
peer version
```

### 8.2 Network Topology

```
Orgs:
  - InsurerA through InsurerF (1 peer each)
  - OrdererOrg (1 orderer)
  - 1 channel: insurance-channel
  - Private data collections per org
```

### 8.3 Create `crypto-config.yaml`

```yaml
# blockchain/fabric-network/crypto-config.yaml
OrdererOrgs:
  - Name: Orderer
    Domain: orderer.insurance.com
    Specs:
      - Hostname: orderer

PeerOrgs:
  - Name: InsurerA
    Domain: insurera.insurance.com
    EnableNodeOUs: true
    Template:
      Count: 1
    Users:
      Count: 2

  - Name: InsurerB
    Domain: insurerb.insurance.com
    EnableNodeOUs: true
    Template:
      Count: 1
    Users:
      Count: 2

  # Repeat for InsurerC through InsurerF
```

### 8.4 Generate Crypto Material

```bash
cd blockchain/fabric-network
cryptogen generate --config=./crypto-config.yaml
```

### 8.5 Generate Genesis Block & Channel Artifacts

```bash
configtxgen -profile InsuranceGenesis -channelID insurance-channel \
  -outputBlock ./channel-artifacts/genesis.block

configtxgen -profile InsuranceGenesis -channelID insurance-channel \
  -outputCreateChannelTx ./channel-artifacts/channel.tx
```

### 8.6 Start the Network

```bash
docker-compose up -d

peer channel create -o orderer.insurance.com:7050 \
  -c insurance-channel \
  -f ./channel-artifacts/channel.tx

peer channel join -b insurance-channel.block
```

---

## 9. Chaincode Development & Deployment

### 9.1 Chaincode Structure (Go)

```
blockchain/chaincode/
    |-- go.mod
    |-- go.sum
    `-- insurance_audit.go
```

### 9.2 Chaincode — Key Functions

```go
// blockchain/chaincode/insurance_audit.go
package main

import (
    "encoding/json"
    "fmt"
    "time"
    "github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type InsuranceAuditContract struct {
    contractapi.Contract
}

type ClaimRecord struct {
    ClaimRef  string `json:"claimRef"`
    InsurerID string `json:"insurerID"`
    ClaimHash string `json:"claimHash"`
    Timestamp string `json:"timestamp"`
    SchemaVer string `json:"schemaVersion"`
}

type FLUpdateRecord struct {
    Round        int    `json:"round"`
    InsurerID    string `json:"insurerID"`
    ModelVersion string `json:"modelVersion"`
    UpdateHash   string `json:"updateHash"`
    Timestamp    string `json:"timestamp"`
}

type AnomalyFlag struct {
    Round      int    `json:"round"`
    InsurerRef string `json:"insurerRef"`
    ReasonCode string `json:"reasonCode"`
    Timestamp  string `json:"timestamp"`
}

type GlobalModelRecord struct {
    ModelVersion string `json:"modelVersion"`
    ModelHash    string `json:"modelHash"`
    Round        int    `json:"round"`
    Timestamp    string `json:"timestamp"`
}

type PredictionRecord struct {
    ClaimRef     string `json:"claimRef"`
    ModelVersion string `json:"modelVersion"`
    PredHash     string `json:"predictionHash"`
    Timestamp    string `json:"timestamp"`
}

type ExplanationRecord struct {
    ClaimRef     string `json:"claimRef"`
    ModelVersion string `json:"modelVersion"`
    SHAPHash     string `json:"shapHash"`
    Timestamp    string `json:"timestamp"`
}

func (c *InsuranceAuditContract) RegisterClaim(ctx contractapi.TransactionContextInterface,
    claimRef, insurerID, claimHash, schemaVer string) error {

    record := ClaimRecord{
        ClaimRef: claimRef, InsurerID: insurerID, ClaimHash: claimHash,
        Timestamp: time.Now().UTC().Format(time.RFC3339), SchemaVer: schemaVer,
    }
    data, _ := json.Marshal(record)
    return ctx.GetStub().PutState("CLAIM_"+claimRef, data)
}

func (c *InsuranceAuditContract) RegisterModelUpdate(ctx contractapi.TransactionContextInterface,
    round int, insurerID, modelVersion, updateHash string) error {

    key := fmt.Sprintf("UPDATE_%d_%s", round, insurerID)
    record := FLUpdateRecord{
        Round: round, InsurerID: insurerID, ModelVersion: modelVersion,
        UpdateHash: updateHash, Timestamp: time.Now().UTC().Format(time.RFC3339),
    }
    data, _ := json.Marshal(record)
    return ctx.GetStub().PutState(key, data)
}

func (c *InsuranceAuditContract) FlagAnomalousUpdate(ctx contractapi.TransactionContextInterface,
    round int, insurerRef, reasonCode string) error {

    key := fmt.Sprintf("ANOMALY_%d_%s", round, insurerRef)
    record := AnomalyFlag{
        Round: round, InsurerRef: insurerRef, ReasonCode: reasonCode,
        Timestamp: time.Now().UTC().Format(time.RFC3339),
    }
    data, _ := json.Marshal(record)
    return ctx.GetStub().PutState(key, data)
}

func (c *InsuranceAuditContract) RegisterGlobalModel(ctx contractapi.TransactionContextInterface,
    modelVersion, modelHash string, round int) error {

    record := GlobalModelRecord{
        ModelVersion: modelVersion, ModelHash: modelHash,
        Round: round, Timestamp: time.Now().UTC().Format(time.RFC3339),
    }
    data, _ := json.Marshal(record)
    return ctx.GetStub().PutState("MODEL_"+modelVersion, data)
}

func (c *InsuranceAuditContract) RegisterPrediction(ctx contractapi.TransactionContextInterface,
    claimRef, modelVersion, predHash string) error {

    record := PredictionRecord{
        ClaimRef: claimRef, ModelVersion: modelVersion,
        PredHash: predHash, Timestamp: time.Now().UTC().Format(time.RFC3339),
    }
    data, _ := json.Marshal(record)
    return ctx.GetStub().PutState("PRED_"+claimRef, data)
}

func (c *InsuranceAuditContract) RegisterExplanation(ctx contractapi.TransactionContextInterface,
    claimRef, modelVersion, shapHash string) error {

    record := ExplanationRecord{
        ClaimRef: claimRef, ModelVersion: modelVersion,
        SHAPHash: shapHash, Timestamp: time.Now().UTC().Format(time.RFC3339),
    }
    data, _ := json.Marshal(record)
    return ctx.GetStub().PutState("SHAP_"+claimRef, data)
}

func (c *InsuranceAuditContract) VerifyClaim(ctx contractapi.TransactionContextInterface,
    claimRef, claimHashToVerify string) (string, error) {

    data, err := ctx.GetStub().GetState("CLAIM_" + claimRef)
    if err != nil || data == nil {
        return "NOT_FOUND", nil
    }
    var record ClaimRecord
    json.Unmarshal(data, &record)
    if record.ClaimHash == claimHashToVerify {
        return "CONSISTENT", nil
    }
    return "MISMATCH_POSSIBLE_TAMPERING", nil
}

func (c *InsuranceAuditContract) VerifyModel(ctx contractapi.TransactionContextInterface,
    modelVersion, modelHashToVerify string) (string, error) {

    data, _ := ctx.GetStub().GetState("MODEL_" + modelVersion)
    var record GlobalModelRecord
    json.Unmarshal(data, &record)
    if record.ModelHash == modelHashToVerify {
        return "CONSISTENT", nil
    }
    return "MISMATCH", nil
}

func main() {
    contract := new(InsuranceAuditContract)
    cc, _ := contractapi.NewChaincode(contract)
    cc.Start()
}
```

### 9.3 Deploy Chaincode

```bash
# Package
peer lifecycle chaincode package insurance_audit.tar.gz \
  --path ./blockchain/chaincode \
  --lang golang \
  --label insurance_audit_1.0

# Install on each peer
peer lifecycle chaincode install insurance_audit.tar.gz

# Approve for each org
peer lifecycle chaincode approveformyorg \
  --channelID insurance-channel \
  --name insurance_audit \
  --version 1.0 \
  --sequence 1

# Commit to channel
peer lifecycle chaincode commit \
  --channelID insurance-channel \
  --name insurance_audit \
  --version 1.0 \
  --sequence 1
```

### 9.4 Private Data Collections Config

```json
// blockchain/chaincode/collections_config.json
[
  {
    "name": "InsurerAPrivate",
    "policy": "OR('InsurerAMSP.member')",
    "requiredPeerCount": 1,
    "maxPeerCount": 1,
    "blockToLive": 0,
    "memberOnlyRead": true
  },
  {
    "name": "InsurerBPrivate",
    "policy": "OR('InsurerBMSP.member')",
    "requiredPeerCount": 1,
    "maxPeerCount": 1,
    "blockToLive": 0,
    "memberOnlyRead": true
  }
]
```

Add `--collections-config ./collections_config.json` to the chaincode commit command.

---

## 10. Claim Registration & Hashing Workflow

### 10.1 Cryptographic Utilities

```python
# blockchain/client/crypto_utils.py
import hashlib
import secrets
import json
from datetime import datetime, timezone

def generate_nonce() -> str:
    """Generate a cryptographically secure 256-bit nonce. One per claim. Never reuse."""
    return secrets.token_hex(32)

def canonical_claim(claim_dict: dict, schema_version: str = "schema_v1") -> str:
    """
    Deterministic string from claim fields.
    Field order is FROZEN. Never change without bumping schema_version.
    """
    ordered_fields = [
        "claim_id", "insurer_id", "farmer_id", "commodity_code",
        "cause_of_loss_code", "net_indemnity", "premium_amount",
        "state_code", "county_code", "commodity_year"
    ]
    canonical = {k: str(claim_dict.get(k, "")) for k in ordered_fields}
    canonical["schema_version"] = schema_version
    return json.dumps(canonical, separators=(',', ':'), sort_keys=False)

def compute_claim_hash(claim_dict: dict, nonce: str, schema_version: str = "schema_v1") -> str:
    """SHA-256(canonical_claim_data || nonce)"""
    data = canonical_claim(claim_dict, schema_version) + nonce
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def compute_model_hash(model_path: str) -> str:
    with open(model_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def compute_shap_hash(shap_values: dict) -> str:
    data = json.dumps(shap_values, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(data.encode('utf-8')).hexdigest()
```

### 10.2 Local SQLite DB for Insurer

```python
# blockchain/client/local_db.py
import sqlite3, json
from datetime import datetime, timezone

def init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS claims (
            claim_id TEXT PRIMARY KEY,
            claim_data TEXT NOT NULL,
            nonce TEXT NOT NULL,
            claim_hash TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            created_at TEXT NOT NULL,
            prediction_score REAL,
            shap_values TEXT,
            is_flagged INTEGER DEFAULT 0,
            is_resolved INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def store_claim(db_path: str, claim_id: str, claim_data: dict, nonce: str,
                claim_hash: str, schema_version: str = "schema_v1"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO claims VALUES (?,?,?,?,?,?,NULL,NULL,0,0)',
        (claim_id, json.dumps(claim_data), nonce, claim_hash, schema_version,
         datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()
```

### 10.3 Blockchain Client (Python)

```python
# blockchain/client/fabric_client.py
import requests

FABRIC_REST_URL = "http://localhost:8801"

class FabricClient:
    def __init__(self, insurer_id: str, token: str):
        self.insurer_id = insurer_id
        self.headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _invoke(self, function: str, args: list):
        payload = {
            "chaincode": "insurance_audit",
            "channel": "insurance-channel",
            "function": function,
            "args": [str(a) for a in args]
        }
        return requests.post(f"{FABRIC_REST_URL}/invoke", headers=self.headers, json=payload).json()

    def _query(self, function: str, args: list):
        payload = {
            "chaincode": "insurance_audit",
            "channel": "insurance-channel",
            "function": function,
            "args": [str(a) for a in args]
        }
        return requests.post(f"{FABRIC_REST_URL}/query", headers=self.headers, json=payload).json()

    def register_claim(self, claim_ref, claim_hash, schema_ver="schema_v1"):
        return self._invoke("RegisterClaim", [claim_ref, self.insurer_id, claim_hash, schema_ver])

    def register_model_update(self, round_num, model_version, update_hash):
        return self._invoke("RegisterModelUpdate", [round_num, self.insurer_id, model_version, update_hash])

    def flag_anomalous_update(self, round_num, insurer_ref, reason_code):
        return self._invoke("FlagAnomalousUpdate", [round_num, insurer_ref, reason_code])

    def register_global_model(self, model_version, model_hash, round_num):
        return self._invoke("RegisterGlobalModel", [model_version, model_hash, round_num])

    def register_prediction(self, claim_ref, model_version, pred_hash):
        return self._invoke("RegisterPrediction", [claim_ref, model_version, pred_hash])

    def register_explanation(self, claim_ref, model_version, shap_hash):
        return self._invoke("RegisterExplanation", [claim_ref, model_version, shap_hash])

    def verify_claim(self, claim_ref, claim_hash) -> str:
        return self._query("VerifyClaim", [claim_ref, claim_hash]).get("result", "ERROR")

    def verify_model(self, model_version, model_hash) -> str:
        return self._query("VerifyModel", [model_version, model_hash]).get("result", "ERROR")
```

### 10.4 Intake a New Claim

```python
# blockchain/client/intake_claim.py
import uuid
from crypto_utils import generate_nonce, compute_claim_hash
from local_db import store_claim
from fabric_client import FabricClient

def intake_claim(claim_data: dict, db_path: str, fabric: FabricClient):
    claim_id = str(uuid.uuid4())
    claim_ref = f"REF_{claim_id[:8].upper()}"  # pseudonymous on-chain reference
    nonce = generate_nonce()
    claim_hash = compute_claim_hash(claim_data, nonce)

    # 1. Store full record locally (sensitive data stays here)
    store_claim(db_path, claim_id, claim_data, nonce, claim_hash)

    # 2. Anchor commitment on-chain (no sensitive data)
    fabric.register_claim(claim_ref, claim_hash)

    print(f"Claim {claim_ref} registered on-chain. Hash: {claim_hash[:16]}...")
    return claim_id, claim_ref, nonce, claim_hash
```

---

## 11. FL Update & Global Model Anchoring on Blockchain

### 11.1 Hash Pre-Mask Update

```python
import hashlib, json

def hash_update(update_array) -> str:
    data = json.dumps(update_array.tolist())
    return hashlib.sha256(data.encode()).hexdigest()

# After local training, BEFORE masking for secure aggregation:
pre_mask_hash = hash_update(raw_update)
fabric.register_model_update(
    round_num=current_round,
    model_version=f"M{current_round}",
    update_hash=pre_mask_hash
)
```

### 11.2 Anchor Global Model After Each FL Round

```python
from crypto_utils import compute_model_hash

model.save_model(f'models/global_M{round_num}.json')
model_hash = compute_model_hash(f'models/global_M{round_num}.json')

fabric.register_global_model(
    model_version=f"M{round_num}",
    model_hash=model_hash,
    round_num=round_num
)
print(f"Global model M{round_num} anchored. Hash: {model_hash[:16]}...")
```

---

## 12. Local Inference + SHAP + Prediction Commitments

### 12.1 Score Claim and Register Prediction Commitment

```python
# ml/shap/inference.py
import xgboost as xgb
import numpy as np
import shap
import json, hashlib
from crypto_utils import compute_shap_hash
from fabric_client import FabricClient

FEATURE_COLS = [
    'indemnity_to_premium_ratio', 'yield_deviation', 'high_cause_code',
    'net_determined_acres', 'liability_amount', 'month_of_loss', 'cause_of_loss_code',
]
FRAUD_THRESHOLD = 0.5

def score_claim(claim_features: dict, model_version: str, claim_ref: str, fabric: FabricClient):
    model = xgb.XGBClassifier()
    model.load_model(f'models/global_{model_version}.json')

    X = np.array([[claim_features[f] for f in FEATURE_COLS]])
    risk_score = float(model.predict_proba(X)[0][1])

    # Prediction commitment — EVERY claim (no exceptions)
    pred_commitment = {
        "claim_ref": claim_ref,
        "model_version": model_version,
        "risk_bucket": "HIGH" if risk_score >= FRAUD_THRESHOLD else "LOW",
    }
    pred_hash = hashlib.sha256(json.dumps(pred_commitment, sort_keys=True).encode()).hexdigest()
    fabric.register_prediction(claim_ref, model_version, pred_hash)

    status = "FLAGGED" if risk_score >= FRAUD_THRESHOLD else "Normal"
    print(f"Claim {claim_ref} | Score: {risk_score:.4f} | {status}")

    if risk_score >= FRAUD_THRESHOLD:
        run_shap_explanation(model, X, claim_features, claim_ref, model_version, fabric)

    return risk_score
```

### 12.2 Run SHAP Locally

```python
def run_shap_explanation(model, X, claim_features, claim_ref, model_version, fabric):
    """SHAP runs locally. Full explanation stays local. Only hash goes on-chain."""
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)

    shap_result = {
        "claim_ref": claim_ref,
        "model_version": model_version,
        "feature_attributions": {
            FEATURE_COLS[i]: float(shap_values[0][i]) for i in range(len(FEATURE_COLS))
        }
    }

    # Store full SHAP locally
    with open(f'ml/shap/explanations/{claim_ref}_shap.json', 'w') as f:
        json.dump(shap_result, f, indent=2)

    # Anchor only the hash on-chain
    shap_hash = compute_shap_hash(shap_result)
    fabric.register_explanation(claim_ref, model_version, shap_hash)

    print("\nSHAP Feature Attributions:")
    for feat, val in sorted(shap_result["feature_attributions"].items(),
                             key=lambda x: abs(x[1]), reverse=True):
        direction = "+" if val > 0 else "-"
        bar = "|" * int(abs(val) * 20)
        print(f"  {feat:<35} {direction}{abs(val):.4f}  {bar}")
```

---

## 13. Investigator Audit & Verification Dashboard

### 13.1 Verification Engine

```python
# dashboard/verify.py
from crypto_utils import compute_claim_hash, compute_model_hash, compute_shap_hash
import json, sqlite3

class AuditVerifier:
    def __init__(self, fabric, db_path):
        self.fabric = fabric
        self.db_path = db_path

    def _get_claim(self, claim_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM claims WHERE claim_id=?", (claim_id,))
        row = cursor.fetchone()
        conn.close()
        return row

    def verify_claim_integrity(self, claim_ref, claim_id) -> dict:
        row = self._get_claim(claim_id)
        claim_data = json.loads(row[1])
        nonce = row[2]
        schema_version = row[4]
        current_hash = compute_claim_hash(claim_data, nonce, schema_version)
        chain_result = self.fabric.verify_claim(claim_ref, current_hash)
        return {
            "claim_ref": claim_ref,
            "local_hash": current_hash[:16] + "...",
            "status": chain_result,
            "tampered": chain_result == "MISMATCH_POSSIBLE_TAMPERING"
        }

    def verify_model_integrity(self, model_version) -> dict:
        model_hash = compute_model_hash(f'models/global_{model_version}.json')
        chain_result = self.fabric.verify_model(model_version, model_hash)
        return {
            "model_version": model_version,
            "local_hash": model_hash[:16] + "...",
            "status": chain_result,
            "tampered": chain_result == "MISMATCH"
        }
```

### 13.2 CLI Dashboard

```python
# dashboard/investigator_cli.py
import argparse
from verify import AuditVerifier
from fabric_client import FabricClient

parser = argparse.ArgumentParser()
parser.add_argument("--insurer", required=True)
parser.add_argument("--claim-ref", required=True)
parser.add_argument("--claim-id", required=True)
parser.add_argument("--model-version", default="M10")
args = parser.parse_args()

fabric = FabricClient(insurer_id=args.insurer, token="<JWT_TOKEN>")
verifier = AuditVerifier(fabric, db_path=f"data/{args.insurer}.db")

print("=" * 60)
print("INVESTIGATOR AUDIT DASHBOARD")
print("=" * 60)

# Claim verification
claim_result = verifier.verify_claim_integrity(args.claim_ref, args.claim_id)
icon = "OK" if not claim_result["tampered"] else "TAMPERED"
print(f"\nClaim Integrity : [{icon}]")
print(f"  Ref           : {claim_result['claim_ref']}")
print(f"  Local Hash    : {claim_result['local_hash']}")
print(f"  Chain Status  : {claim_result['status']}")

# Model verification
model_result = verifier.verify_model_integrity(args.model_version)
micon = "OK" if not model_result["tampered"] else "TAMPERED"
print(f"\nModel Integrity : [{micon}]")
print(f"  Version       : {model_result['model_version']}")
print(f"  Chain Status  : {model_result['status']}")
```

---

## 14. Benchmarks, Tampering Demo & Final Evaluation

### 14.1 Tampering Demonstration

```python
# evaluation/tampering_demo.py
import sqlite3, json

def tamper_claim_in_db(db_path: str, claim_id: str):
    """Simulate a malicious modification of a claim record in the local DB."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT claim_data FROM claims WHERE claim_id=?", (claim_id,))
    claim = json.loads(cursor.fetchone()[0])

    original_indemnity = claim['net_indemnity']
    claim['net_indemnity'] = original_indemnity * 10   # inflate payout

    cursor.execute("UPDATE claims SET claim_data=? WHERE claim_id=?",
                   (json.dumps(claim), claim_id))
    conn.commit()
    conn.close()
    print(f"[TAMPER] Claim {claim_id}: indemnity changed from {original_indemnity} to {claim['net_indemnity']}")
    print(">>> Now run verify_claim — expect MISMATCH_POSSIBLE_TAMPERING from chain.")
```

### 14.2 Blockchain Overhead Benchmark

```python
# evaluation/blockchain_benchmark.py
import time
import numpy as np
from fabric_client import FabricClient

def benchmark_transactions(fabric: FabricClient, n: int = 100):
    latencies = []
    for i in range(n):
        start = time.time()
        fabric.register_claim(f"BENCH_{i:05d}", "a" * 64)
        latencies.append(time.time() - start)

    print(f"Transactions   : {n}")
    print(f"Avg Latency    : {np.mean(latencies)*1000:.1f} ms")
    print(f"P95 Latency    : {np.percentile(latencies,95)*1000:.1f} ms")
    print(f"Throughput     : {n/sum(latencies):.1f} TPS")
```

### 14.3 FL Privacy Benchmark

```python
# evaluation/fl_privacy_benchmark.py
configs = [
    {"name": "no_defense",       "clip": False, "noise": False, "secagg": False},
    {"name": "clip_noise",       "clip": True,  "noise": True,  "secagg": False},
    {"name": "full_hardened",    "clip": True,  "noise": True,  "secagg": True},
]

for cfg in configs:
    error = run_reconstruction_attack(cfg)
    print(f"{cfg['name']:25s}  Reconstruction Error: {error:.4f}")
```

### 14.4 Label Bias Check

```python
# evaluation/bias_check.py
import pandas as pd

df = pd.read_csv('data/processed/full_dataset.csv')

print("=== Flagging Rate by State ===")
print(df.groupby('state_code')['fraud_label'].mean().sort_values(ascending=False).head(10))

print("\n=== Flagging Rate by Commodity ===")
print(df.groupby('commodity_code')['fraud_label'].mean().sort_values(ascending=False).head(10))

# Report disparities as LIMITATIONS in final report — do not claim the model is fair
```

### 14.5 Final Metrics Table

Compile all results:

| Metric | Centralized | FL FedAvg | FL + SecAgg + Robust |
|--------|-------------|-----------|----------------------|
| F1 Score | | | |
| ROC-AUC | | | |
| PR-AUC | | | |
| Reconstruction Error (attack) | | | |
| Poisoning Impact (Delta AUC) | | absorbed | neutralized |
| Avg Blockchain Latency (ms) | N/A | N/A | |
| SecAgg Overhead (%) | N/A | N/A | |

---

## Quick Reference — Key Commands

```bash
# 1. Start Fabric network
cd blockchain/fabric-network && docker-compose up -d

# 2. Run FL simulation (all 6 nodes)
python ml/federated/simulate_fl.py

# 3. Intake a new claim
python blockchain/client/intake_claim.py

# 4. Score and explain a claim
python ml/shap/inference.py --claim-ref REF_ABC123 --model-version M10

# 5. Investigator audit verification
python dashboard/investigator_cli.py --insurer A --claim-ref REF_ABC123 \
  --claim-id <uuid> --model-version M10

# 6. Run tampering demo
python evaluation/tampering_demo.py

# 7. Run all benchmarks
python evaluation/blockchain_benchmark.py
python evaluation/fl_privacy_benchmark.py
python evaluation/bias_check.py
```

---

## Important Reminders

**Nonce Loss Policy**
If a nonce is lost, that claim's commitment becomes unverifiable.
The claim record itself is unaffected. State this limitation explicitly in your report.

**Schema Versioning**
Never change the canonical claim field list without bumping `schema_version`.
Old commitments (`schema_v1`) must always be verified against the v1 schema.

**XGBoost FL Caveat**
Formal DP-SGD guarantees apply only to gradient-descent models.
The clip+noise here is an *empirical* defense for XGBoost.
Present it as such and demonstrate it via reconstruction attack tests.

**Secure Aggregation Proof**
Instrument the aggregator to log received values and show they are masked sums —
not recoverable individual updates. Include this demonstration in your report.

**Threat Model Limitation**
This system defends against an honest-but-curious aggregator and a *bounded* number
of malicious insurer nodes. It does NOT defend against a fully colluding majority.
State this explicitly in the final report and presentation.
