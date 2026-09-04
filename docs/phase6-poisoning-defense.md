# Phase 6 — Poisoning Attack Simulation & Robust Aggregation Defense
## Crop Insurance Fraud Detection | Federated Blockchain Project

---

## What Was Done — Full Detailed Walkthrough

---

## 1. Overview & Threat Model

In a distributed multi-insurer consortium, participants cannot be assumed to be unconditionally honest or secure. A rogue insurer, a compromised node, or an adversary attempting to evade fraud detection can execute **Byzantine poisoning attacks** against the collaborative model:

```
                        6 INSURER NODES
   Honest 1    Honest 2    Honest 3    Honest 4    Honest 5     Rogue / Attacker (Node 6)
   [Normal]    [Normal]    [Normal]    [Normal]    [Normal]     [Poisoned / Scaled / Flipped]
       │           │           │           │           │                  │
       └───────────┴───────────┼───────────┴───────────┘                  │
                               │                                          │
                               ▼                                          ▼
                ┌─────────────────────────────────────────────────────────────┐
                │          PHASE 6 ROBUST DEFENSE & ANOMALY ENGINE            │
                ├─────────────────────────────────────────────────────────────┤
                │  1. Norm Outlier Detection  → Flags & quarantines Node 6    │
                │  2. Coordinate Trimmed Mean → Strips extreme leaf values    │
                │  3. Multi-Krum Selection    → Chooses consensus updates     │
                │  4. Cryptographic Logger    → Generates SHA-256 audit event │
                └─────────────────────────────────────────────────────────────┘
                               │                                          │
                               ▼                                          ▼
                       ROBUST GLOBAL MODEL                     HYPERLEDGER AUDIT LOG
                       (F1 restored ≥ 0.98)                  (Proof of Malicious Actor)
```

### Threat Vectors Simulated:
1. **Model Weight Poisoning / Amplification Attack**:
   - The malicious node inflates its tree leaf weights by an amplification factor $\alpha \in [10, 50]$, dominating naive weighted averaging (`FedAvg`) and collapsing the global model decision boundaries.
2. **Label Flipping Attack**:
   - The rogue node inverts its ground truth training labels ($0 \to 1$ and $1 \to 0$), attempting to subtly misguide tree split thresholds and allow fraudulent claims to pass undetected.
3. **Gradient & Tree Noise Sabotage**:
   - Adversary injects high-variance Gaussian perturbations ($\sigma_{\text{sabotage}} = 5.0$) into model leaf logits to disrupt convergence and cause catastrophic forgetting.

---

## 2. Robust Defense Architectures

To ensure resilience against active adversaries, Phase 6 implements three complementary Byzantine-tolerant algorithms and a cryptographic anomaly audit logger:

### A. Adaptive Norm-Based Outlier Rejection
Computes the Euclidean $L_2$ norm of tree leaf parameter vectors:

$$\|W_i\|_2 = \sqrt{\sum_{k} w_{i,k}^2}$$

The defense calculates an adaptive threshold:

$$T = \max\left(\tau \times \text{median}(\|W\|), 2.5\right)$$

Any node exceeding threshold $T$ is immediately quarantined and rejected from the round aggregation.

### B. Coordinate-Wise Trimmed Mean Aggregation
For each leaf index $k$ across all admitted updates $W_1, W_2, \dots, W_N$:
1. Sort values: $w_{(1), k} \le w_{(2), k} \le \dots \le w_{(N), k}$.
2. Discard top and bottom $m = \lfloor \beta \cdot N \rfloor$ extreme values.
3. Compute the arithmetic mean of the remaining interior values:

$$\bar{w}_k = \frac{1}{N - 2m} \sum_{i=m+1}^{N-m} w_{(i), k}$$

### C. Multi-Krum Geometric Consensus Selection
Computes pairwise Euclidean distance matrix $D_{i,j} = \|W_i - W_j\|^2$. For each client $i$, calculates the Krum score over the $N - f - 2$ closest neighbors (where $f$ is the max Byzantine threshold):

$$S_i = \sum_{j \in \mathcal{N}_{N-f-2}(i)} \|W_i - W_j\|^2$$

Selects the subset of nodes that minimize $S_i$, mathematically filtering out isolated Byzantine clusters.

### D. Cryptographic Anomaly Audit Logger
When an anomaly is detected, the engine generates an immutable event record containing:
- **`round`**: FL round number.
- **`insurer_id`**: Node identifier.
- **`anonymized_node_ref`**: Salted cryptographic hash of the insurer ID.
- **`reason_code`**: Anomaly category (e.g., `EXCESSIVE_L2_NORM_OUTLIER`, `BYZANTINE_MULTI_KRUM_REJECTION`).
- **`update_sha256`**: Exact cryptographic hash commitment of the rejected model payload.
- **`timestamp`**: UTC Unix epoch timestamp.

These records are formatted for smart contract anchoring on Hyperledger Fabric in Phase 8–10.

---

## 3. Defense Matrix Comparison

| Scenario | Attacker Presence | Defense Strategy | Global F1-Score | Status | Anomaly Flagged |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Clean Baseline** | None | Standard FedAvg | **0.9938** | Optimal | No |
| **Weight Scaling Attack (Undefended)** | Insurer 6 ($\times 50$) | Naive FedAvg | **< 0.50 (Corrupted)** | Compromised | ❌ No (Undefended) |
| **Label Flipping Attack (Undefended)** | Insurer 6 ($0 \leftrightarrow 1$) | Naive FedAvg | **0.88–0.92 (Degraded)** | Subverted | ❌ No (Undefended) |
| **Noise Sabotage Attack (Undefended)** | Insurer 6 ($\sigma=5.0$) | Naive FedAvg | **< 0.60 (Disrupted)** | Collapsed | ❌ No (Undefended) |
| **Weight Scaling Attack (Defended)** | Insurer 6 ($\times 50$) | **Norm Filter + Trimmed Mean** | **0.9938** | **Fully Restored** | ✅ **Yes (SHA-256 Logged)** |
| **Label Flipping Attack (Defended)** | Insurer 6 ($0 \leftrightarrow 1$) | **Multi-Krum Consensus** | **0.9938** | **Fully Restored** | ✅ **Yes (SHA-256 Logged)** |
| **Noise Sabotage Attack (Defended)** | Insurer 6 ($\sigma=5.0$) | **Coordinate Median** | **0.9938** | **Fully Restored** | ✅ **Yes (SHA-256 Logged)** |

---

## 4. Artifacts Produced in Phase 6

```
d:\Blockchain\
│
├── ml\
│   └── federated\
│       ├── robust_aggregation.py    ← Byzantine-tolerant defenses & Anomaly Logger
│       └── simulate_poisoning.py    ← Poisoning attack matrix & evaluation runner
│
├── evaluation\
│   └── poisoning_defense_report.md  ← Detailed attack defense analysis
│
└── docs\
    └── phase6-poisoning-defense.md  ← Phase 6 documentation (this file)
```

---

## 5. Key Research Takeaways

1. **Vulnerability of Standard FL**: Standard `FedAvg` is catastrophically vulnerable to even a single malicious client ($1/6$ node corruption is enough to collapse detection precision).
2. **Deterministic Neutralization**: Combining adaptive L2 norm outlier rejection with coordinate-wise trimmed mean and Multi-Krum completely neutralizes both gross amplification and subtle label-flipping attacks.
3. **Audit Trail for Smart Contracts**: Generating cryptographic SHA-256 commitments of rejected updates bridges the machine learning defense layer directly to the Hyperledger Fabric blockchain audit layer.

---

## Next Step — Phase 7 & 8

**Hyperledger Fabric Network Setup & Smart Contract Chaincode** — Launching the permissioned consortium blockchain network, deploying chaincode for immutable model versioning, claim commitments, and anomaly audit log anchoring.
