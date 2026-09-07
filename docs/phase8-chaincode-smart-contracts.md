# Phase 8 — Smart Contract (Chaincode) Development & Deployment

> Implementation and deployment of the `insurance_audit` Go smart contract (chaincode) and Private Data Collections across the 6-insurer Hyperledger Fabric consortium network.

---

## 1. Overview & Architectural Role

In Phase 7, we established the multi-organization blockchain network topology. **Phase 8** implements the decentralized, tamper-evident business rules governing:
1. **Intake Claim Commitments**: Anchoring deterministic SHA-256 fingerprints before inference to prevent retroactive claim manipulation.
2. **Federated Learning Auditability**: Storing pre-mask local model updates and anchoring Byzantine anomaly rejection flags from Phase 6.
3. **Model Provenance Lineage**: Committing global model hashes ($M_0, M_1, \dots, M_{10}$) so predictions can be tied to the exact verified model version used.
4. **Explainability & Prediction Commitments**: Anchoring prediction risk buckets for every claim and SHAP explanation fingerprints for suspicious claims.
5. **Private Data Scoping**: Restricting cross-insurer metadata access via Fabric Private Data Collections (`collections_config.json`).

```
                       HYPERLEDGER FABRIC STATE
 ┌────────────────────────────────────────────────────────────────────────┐
 │ 1. CLAIM_<claimRef>       -> { claimRef, insurerID, claimHash, ver }   │
 │ 2. UPDATE_<round>_<org>   -> { round, insurerID, modelVer, updateHash }│
 │ 3. ANOMALY_<round>_<ref>  -> { round, insurerRef, reasonCode, hash }   │
 │ 4. MODEL_<modelVersion>   -> { modelVersion, modelHash, round, time }  │
 │ 5. PRED_<claimRef>        -> { claimRef, modelVersion, predHash }      │
 │ 6. SHAP_<claimRef>        -> { claimRef, modelVersion, shapHash }      │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 2. On-Chain State Models (Data Structures)

All state records are serialized to deterministic JSON and committed to the Fabric World State database:

### 1. `ClaimRecord` (`CLAIM_<claimRef>`)
```json
{
  "claimRef": "REF_C1001",
  "insurerID": "InsurerA",
  "claimHash": "3b7b8972e9d29c8e889311090412bfa40685be9b...",
  "timestamp": "2026-09-06T12:00:00Z",
  "schemaVersion": "schema_v1"
}
```

### 2. `FLUpdateRecord` (`UPDATE_<round>_<insurerID>`)
```json
{
  "round": 1,
  "insurerID": "InsurerA",
  "modelVersion": "M1",
  "updateHash": "d826c71004812a14b3017a42ec34...",
  "timestamp": "2026-09-06T12:00:00Z"
}
```

### 3. `AnomalyFlag` (`ANOMALY_<round>_<insurerRef>`)
```json
{
  "round": 6,
  "insurerRef": "7f83b1657ff1fc53...",
  "reasonCode": "EXCESSIVE_L2_NORM_OUTLIER",
  "updateHash": "b45cffe084dd3d20d928bee85e7b0f21...",
  "timestamp": "2026-09-06T12:00:00Z"
}
```

### 4. `GlobalModelRecord` (`MODEL_<modelVersion>`)
```json
{
  "modelVersion": "M10",
  "modelHash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4...",
  "round": 10,
  "timestamp": "2026-09-06T12:00:00Z"
}
```

### 5. `PredictionRecord` (`PRED_<claimRef>`)
```json
{
  "claimRef": "REF_C1001",
  "modelVersion": "M10",
  "predictionHash": "8f48a57173b9846b412...",
  "riskBucket": "HIGH",
  "timestamp": "2026-09-06T12:00:00Z"
}
```

### 6. `ExplanationRecord` (`SHAP_<claimRef>`)
```json
{
  "claimRef": "REF_C1001",
  "modelVersion": "M10",
  "shapHash": "4a7d1ed414474e4033ac29ccb8653d9b...",
  "timestamp": "2026-09-06T12:00:00Z"
}
```

---

## 3. Smart Contract Functions & Transaction API

| Function | Type | Parameters | Return / Behavior |
| :--- | :--- | :--- | :--- |
| `InitLedger` | Write | — | Initializes ledger state with Genesis model `MODEL_M0`. |
| `RegisterClaim` | Write | `claimRef`, `insurerID`, `claimHash`, `schemaVer` | Commits intake claim commitment. Rejects duplicate references. |
| `RegisterModelUpdate` | Write | `round`, `insurerID`, `modelVer`, `updateHash` | Anchors pre-mask local FL update hash. |
| `FlagAnomalousUpdate` | Write | `round`, `insurerRef`, `reasonCode`, `updateHash` | Anchors Byzantine anomaly rejection flag. |
| `RegisterGlobalModel` | Write | `modelVer`, `modelHash`, `round` | Commits aggregated global model hash. |
| `RegisterPrediction` | Write | `claimRef`, `modelVer`, `predHash`, `riskBucket` | Commits prediction hash (mandatory for every claim). |
| `RegisterExplanation` | Write | `claimRef`, `modelVer`, `shapHash` | Commits SHAP explanation hash for flagged claims. |
| `VerifyClaim` | Query | `claimRef`, `claimHashToVerify` | Returns `CONSISTENT` or `MISMATCH_POSSIBLE_TAMPERING`. |
| `VerifyModel` | Query | `modelVer`, `modelHashToVerify` | Returns `CONSISTENT` or `MISMATCH`. |
| `VerifyExplanation` | Query | `claimRef`, `shapHashToVerify` | Returns `CONSISTENT` or `MISMATCH_POSSIBLE_TAMPERING`. |
| `GetClaimAuditTrail` | Query | `claimRef` | Returns combined `Claim + Prediction + SHAP` provenance. |
| `GetModelHistory` | Query | — | Returns full global model version history ($M_0 \dots M_r$). |

---

## 4. Private Data Collections (`collections_config.json`)

To prevent competitor snooping while preserving tamper-evidence, Private Data Collections isolate sensitive insurer metadata:
```json
[
  {
    "name": "InsurerAPrivate",
    "policy": "OR('InsurerAMSP.member')",
    "requiredPeerCount": 1,
    "maxPeerCount": 1,
    "blockToLive": 0,
    "memberOnlyRead": true,
    "memberOnlyWrite": true
  }
]
```
- **Scoped Read Access**: Only authenticated peers of `InsurerAMSP` can query `InsurerAPrivate`.
- **Public Audit Hashes**: Hashes remain on the shared `insurance-channel` state for independent audit verification.

---

## 5. Deployment Commands

### On Windows PowerShell
```powershell
.\blockchain\chaincode\deploy_chaincode.ps1 -ChannelName insurance-channel -CC_Name insurance_audit -CC_Version 1.0
```

### On Linux / WSL
```bash
chmod +x blockchain/chaincode/deploy_chaincode.sh
./blockchain/chaincode/deploy_chaincode.sh insurance-channel insurance_audit 1.0 1
```

---

## 6. Next Step — Phase 9

With the smart contracts implemented and verified, **Phase 9** implements the **Python-Blockchain Integration Bridge** (`crypto_utils.py`, `local_db.py`, and `fabric_client.py`), connecting Flower FL and claim intake directly to the blockchain.
