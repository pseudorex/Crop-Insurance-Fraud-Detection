# Federated, Blockchain-Audited Crop-Insurance Fraud Detection
## Revised Project Plan (Privacy-Hardened Version)

---

## 1. Project Overview

The project builds a simulated multi-insurer crop-insurance fraud detection system.
Multiple insurer nodes hold private claims data and collaboratively train a
fraud-detection model using **Federated Learning (FL)**. Raw claims never leave the
insurer. A permissioned **Hyperledger Fabric** network provides a blockchain-based
audit and provenance layer. Instead of storing sensitive claim data on-chain, the
system stores cryptographic commitments/hashes and selected metadata.

This revised plan keeps the original four-capability design — (1) local data
ownership, (2) collaborative FL training, (3) tamper-evident blockchain
auditability, (4) local SHAP explanations — but **closes the privacy and integrity
gaps** identified during design review: FL update leakage, poisoning risk,
on-chain metadata leakage, nonce/key management, and Fabric access scoping.

---

## 2. Main Research Question

Can multiple crop insurers collaboratively improve fraud detection **without
sharing raw claims or leaking information through the training process itself**,
while creating an independently verifiable, tamper-evident history of claims,
model updates, model versions, predictions and explanations?

The added clause — "without leaking information through the training process
itself" — is the core upgrade over the original plan: it's not enough that raw
claims stay local; the *model updates* must not become a side channel either.

---

## 3. What Each Technology Does

| Component | Primary responsibility |
|---|---|
| XGBoost | Predicts whether a claim is suspicious / high-risk |
| SHAP | Explains why a claim received a high or low risk score |
| Federated Learning (Flower) | Trains a shared model without exchanging raw claims |
| **Secure Aggregation** | Prevents the aggregator from seeing any individual insurer's update |
| **DP / clipping on updates** | Bounds how much any single record can influence, or be reconstructed from, an update |
| **Robust aggregation** | Prevents one malicious/anomalous insurer from corrupting the global model |
| SHA-256 | Creates cryptographic fingerprints/commitments of claims, model artifacts, explanations |
| Hyperledger Fabric | Permissioned, immutable/tamper-evident audit and provenance ledger |
| Chaincode | Defines rules for registering and verifying audit records |
| Private insurer database | Stores actual claims, labels, investigation results, sensitive SHAP details |

---

## 4. Final Architecture

Two connected flows: a periodic **training flow** (now with secure/robust
aggregation) and a continuous **new-claim/investigation flow**.

```
                         HYPERLEDGER FABRIC
       Claim commitments | FL update hashes | Anomaly flags | Model hashes
       Prediction/SHAP commitments | timestamps | audit trail
                                  ▲
                                  │ hash / verify
     ┌───────────┬───────────┬───────────┬───────────┬───────────┐
     │           │           │           │           │           │
  INSURER A   INSURER B   INSURER C   INSURER D  ...  INSURER N (≥6-8 nodes)
  Private DB  Private DB  Private DB  Private DB       Private DB
     │           │           │           │           │           │
  Local ML +  Local ML +  Local ML +  Local ML +      Local ML +
  clip+noise  clip+noise  clip+noise  clip+noise      clip+noise
     │           │           │           │           │           │
     └───────────┴─────┬─────┴───────────┴───────────┴───────────┘
                        ▼
              SECURE AGGREGATION LAYER
        (masked updates in → only sum/avg out)
                        ▼
              ROBUST FEDAVG / ANOMALY CHECK
        (trimmed mean / norm-clipping / outlier flag)
                        ▼
                   GLOBAL MODEL
                        │
              distributed to insurers
                        │
                        ▼
             LOCAL NEW-CLAIM PREDICTION
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
           Normal              Suspicious
                                   │
                                   ▼
                              Local SHAP
                                   │
                                   ▼
                              Investigator
```

**Key changes from the original architecture:**
- Insurer node count raised from 3 to **6–8+** to reduce isolation risk of any
  single contribution.
- A **secure aggregation layer** sits between insurers and FedAvg — the
  aggregator never sees an individual update, only the combined result.
- Each local update is **clipped and noised** before it even reaches secure
  aggregation, as defense-in-depth.
- FedAvg is replaced with a **robust aggregation rule**, with anomaly flags
  optionally written to the ledger.

---

## 5. Threat Model (new section — freeze this before coding)

Explicitly naming the threat model is itself a deliverable; it shows the
reviewer you designed against real adversaries rather than only against "raw
data leaving the insurer."

| Adversary | Capability assumed | What they should NOT be able to do |
|---|---|---|
| FL aggregator (honest-but-curious) | Sees whatever is sent to it | Recover/reconstruct any individual insurer's local update or infer membership of a specific claim |
| Malicious/compromised insurer node | Can submit a crafted update | Meaningfully degrade or bias the global model beyond a bounded tolerance |
| Ledger reader with authorized access | Sees on-chain metadata (IDs, timestamps, hashes) | Re-identify individual farmers/claims or infer claim-level outcomes purely from metadata patterns |
| External attacker (no chain access) | Sees nothing privileged | N/A — out of scope beyond standard network security |
| Investigator (authorized) | Full access to their own insurer's private data + chain | Should NOT get cross-insurer raw data access; scoped to their organization + shared chain metadata |

State clearly in the report: **this project defends against the aggregator and
against a bounded number of malicious insurers; it does not attempt to defend
against a fully colluding majority of insurers**, which is a standard, honest
limitation to state for FL systems at this scale.

---

## 6. Phase A — Initial Model and Federated Training (hardened)

### 6.1 Initial model M0
XGBoost, either untrained or centrally initialized. Learning happens through FL
from this point forward.

### 6.2 Local insurer datasets
- USDA RMA public data partitioned into **6–8 simulated insurer/region nodes**
  (increased from 3) using a state-, region-, or county-like non-IID split.
- Suspicious/fraud label created via the agreed labeling strategy (Section 15).
- Actual data, labels, and nonces remain local. Nothing raw is sent to the
  aggregator or the ledger.

### 6.3 One FL round (revised sequence)

1. Global model distributed to each insurer.
2. Each insurer trains locally on private data only.
3. **Each insurer clips its update's norm and adds calibrated noise**
   (clipping bound and noise scale fixed as hyperparameters, documented and
   justified — see Section 7).
4. **Each insurer masks its update for secure aggregation** (e.g., Flower's
   secure-aggregation protocol, or a simple pairwise-additive-mask
   implementation for the class project).
5. Masked, noised updates go to the aggregator.
6. Aggregator computes the **combined** update — it never sees an individual
   insurer's raw update.
7. Each insurer separately hashes its **pre-mask** local update and anchors
   the hash + round + insurer ID + timestamp on Hyperledger Fabric (for
   provenance/audit — this does not defeat secure aggregation, since the hash
   reveals nothing about the update's content, only that *something specific*
   was committed and can later be checked for consistency if disputes arise).
8. Aggregator applies **robust aggregation** (trimmed mean / norm-based
   outlier rejection) instead of plain FedAvg, and flags any round where an
   update was excluded as an outlier.
9. New global model receives a version number and hash, anchored on-chain.
   Any anomaly flags from step 8 are anchored alongside it.

### 6.4 Ten-round example (unchanged structure, now with robustness evidence)

| Round | Result | Blockchain evidence |
|---|---|---|
| 0 | Initial model M0 | Optional initial model hash |
| 1 | Global M1 | Update hashes (×N insurers) + anomaly flags (if any) + M1 hash |
| 2 | Global M2 | Update hashes + anomaly flags + M2 hash |
| ... | ... | ... |
| 10 | Final experimental global model M10 | Update hashes + anomaly flags + M10 hash |

Monitor convergence with validation metrics; extend rounds if not yet
stabilized.

---

## 7. Privacy & Robustness Mechanisms — Implementation Notes

### 7.1 Secure Aggregation
- **Recommended approach for project scope:** use Flower's built-in secure
  aggregation support (`flwr.server.strategy` + secure-agg extension), citing
  it directly rather than implementing cryptographic protocols from scratch.
- **Fallback/teaching version:** implement simple pairwise additive masking
  across the (now 6–8) insurer nodes to demonstrate the concept concretely in
  your evaluation section, even if the production-grade version uses Flower's
  library implementation.
- **What to demonstrate in the report:** show that the aggregator's logged
  intermediate state contains only the combined update, never an individual
  insurer's update — e.g., by instrumenting the aggregator and showing the
  masked values are unrecoverable without the missing mask share.

### 7.2 Differential Privacy / Update Clipping
- Clip each local update's L2 norm to a fixed bound **C** before noising.
- Add Gaussian noise scaled to **C** and a chosen noise multiplier **σ**.
- **XGBoost caveat:** formal DP-SGD assumes gradient-descent-trained models;
  DP for tree-boosting is less standardized. Two acceptable paths:
  - Treat clip+noise as an **empirical defense** (not a formally proven DP
    guarantee) against reconstruction/inversion attacks, and demonstrate this
    empirically (attempt a simple reconstruction attack against noised vs.
    unnoised updates, show the difference).
  - Optionally add a **secondary DP-SGD-trained model track** (e.g., logistic
    regression or a small neural net) purely to show a formally-DP-compatible
    alternative, compared against the XGBoost baseline. This is optional but
    strengthens the report if time allows.
- Document the clipping bound and noise scale choice and the accuracy/privacy
  tradeoff observed.

### 7.3 Robust Aggregation
- Replace plain FedAvg with **coordinate-wise trimmed mean** or **norm-based
  outlier rejection** (e.g., reject updates whose norm exceeds K× the median
  norm that round).
- **Poisoning demonstration for evaluation:** inject a deliberately corrupted
  update from one simulated insurer in a test round; show plain FedAvg absorbs
  it (visible accuracy/behavior shift) while robust aggregation neutralizes it.
- Log any rejected/flagged update's metadata (not content) to the ledger via
  a `flagAnomalousUpdate()` chaincode call.

### 7.4 Increasing Node Count
- Repartition RMA data into 6–8 nodes instead of 3. This is a data-prep change
  only (no new infrastructure) and materially reduces the risk of isolating
  one insurer's contribution by differencing global models round-over-round.

---

## 8. Phase B — Blockchain Design (hardened)

Blockchain remains the audit/provenance layer, never the claims store.
Hyperledger Fabric is used for the same reasons as before (permissioned,
identity-based, no cryptocurrency/gas overhead), with two additions:

### 8.1 Fabric Private Data Collections (new)
Instead of relying only on channel-level separation, use **Fabric private
data collections** so that:
- Metadata visible to one insurer's authorized peers is not automatically
  replicated to all peers.
- Investigator identities are scoped to the specific collection(s) relevant
  to their case, not given blanket read access across all insurers.
- This directly closes the "on-chain metadata leakage / cross-insurer
  profiling" gap identified during design review.

### 8.2 What is stored on-chain (unchanged categories, same "no sensitive data" rule)

| Record type | Example on-chain fields | Actual sensitive data? |
|---|---|---|
| Claim registration | Pseudonymous claim reference, insurer ID, claim hash, timestamp | No |
| FL update | Round, insurer ID, model version, **pre-mask** update hash, timestamp | No raw training data |
| Anomaly flag | Round, flagged insurer ref (or anonymized), reason code | No |
| Global model | Model version, global model hash, round, timestamp | No full private dataset |
| Prediction commitment | Claim reference, model version, prediction/commitment hash, timestamp | Commitment only — written for **every claim**, not just flagged ones (see 8.4) |
| SHAP commitment | Claim reference, model version, explanation hash, timestamp | No full SHAP explanation |

### 8.3 Claim hashing with proper nonce management

```
Claim Hash = SHA-256(CanonicalClaimData || SecretNonce)
```

- **Nonce generation:** one nonce per claim, generated with a CSPRNG at claim
  intake, never reused across claims.
- **Nonce storage:** stored in the insurer's private DB alongside the claim
  record — same trust boundary, no separate key-management system needed at
  project scope.
- **Loss handling:** explicitly document that nonce loss makes that claim's
  commitment unverifiable (a verification failure), but does **not** affect
  the claim record itself — this distinction should be stated in the report
  so the audit-trail limitation is transparent, not silent.
- **Canonicalization:** freeze the exact field list, order, and formatting for
  canonical representation *before* implementation, and version it (e.g.,
  `schema_v1`) so future schema changes don't produce false tamper alarms
  against old commitments.

### 8.4 Commit every claim, not just flagged ones

Per the original plan's own Section 24 recommendation — adopted here as a firm
design decision: **every new claim gets a claim hash and a lightweight
prediction commitment**, regardless of risk score. Only the **full SHAP
explanation commitment** is reserved for flagged/high-value claims or a
controlled evaluation subset. This removes the "absence of a commitment
reveals the claim was low-risk" side channel.

---

## 9. Phase C — New Claim Lifecycle (unchanged logic, same privacy boundary)

1. New claim arrives at an insurer (e.g., Insurer A, claim C1001).
2. Full record stored locally; canonical form + nonce created; claim hash
   computed; claim reference + hash + insurer ID + timestamp anchored on-chain.
3. Latest global model (e.g., M10) deployed to Insurer A; claim scored locally.
4. Below threshold → not flagged → local record + prediction commitment
   on-chain (now mandatory per 8.4, not optional).
5. Above threshold → flagged → local SHAP run → explanation hash committed →
   routed to human investigation.

---

## 10. Phase D — SHAP Explainability (unchanged, still local-only)

SHAP runs at the insurer that owns the claim — never centrally — because SHAP
needs both the claim's features and the model, and centralizing that would
reintroduce the privacy problem FL was designed to avoid.

Example feature attribution table and interpretation stays as in the original
plan (indemnity, yield deviation, regional anomaly, cause of loss, premium).

The full SHAP explanation stays private; only its SHA-256 commitment is
anchored on-chain, alongside claim reference and model version.

---

## 11. Phase E — Human Investigation and Verification (unchanged, plus scoped access)

Investigator dashboard combines authorized private-system access with
blockchain audit records, but now with **collection-scoped** chain access
(Section 8.1) rather than blanket cross-insurer visibility.

Verification logic is unchanged:

```
Current Claim Hash == Blockchain Claim Hash  → consistent with committed state
Current Claim Hash != Blockchain Claim Hash  → possible modification — investigate
```

Applies equally to model and SHAP commitments. This proves artifact
consistency, not claim truthfulness.

---

## 12. Model Provenance

Unchanged: every global model gets a version + hash, so any prediction can be
tied to the exact model version used at inference time (`Claim → Model version
→ Prediction → SHAP`).

---

## 13. After Investigation

Unchanged mechanics: resolved claims can feed the next local training round
without ever being sent to the aggregator as raw data — only through the next
round's (now secure-aggregated, robust-aggregated) local update.

---

## 14. Complete End-to-End Flow (revised)

```
TRAINING
M0 → distribute → local training → clip+noise → mask (secure agg)
   → hash pre-mask update → anchor hash on-chain
   → aggregator combines masked updates → robust aggregation (+ anomaly flag if any)
   → M1 → hash M1 → anchor on-chain → repeat → M10

NEW CLAIM
New claim → private insurer DB → claim hash → anchor on-chain
   → M10 locally → risk score → prediction commitment anchored (every claim)

IF SUSPICIOUS
Risk above threshold → local SHAP → explanation → SHAP hash → anchor on-chain
   → human investigation (scoped chain + private access)

AUDIT
Private claim + SHAP + model artifact ↔ blockchain commitments → verify integrity

NEXT TRAINING CYCLE
Resolved local outcomes → local training → clip+noise → mask → hash → anchor
   → robust aggregation → new global model M11
```

---

## 15. Chaincode Functions (extended)

| Function | Purpose |
|---|---|
| `registerClaim()` | Register a claim commitment, insurer ID, timestamp |
| `registerModelUpdate()` | Store an FL round's **pre-mask** local update hash and metadata |
| `flagAnomalousUpdate()` | **New** — record that an update was rejected/flagged by robust aggregation, with reason code |
| `registerGlobalModel()` | Store global model version and hash |
| `registerPrediction()` | Commit prediction/provenance info — **now called for every claim**, not only flagged ones |
| `registerExplanation()` | Store a SHAP explanation commitment (flagged/high-value claims) |
| `verifyClaim()` | Compare/retrieve committed claim hash for audit |
| `verifyModel()` | Verify a model version/hash |
| `verifyExplanation()` | Verify a SHAP explanation commitment |

---

## 16. Dataset and Fraud Label Strategy

Unchanged from original: USDA RMA public data, with either **heuristic
labeling** (fraud/anomaly signal construction) or **synthetic fraud
injection**, clearly stated and justified in the final report. The model score
is a fraud-risk indicator, not proof of criminal fraud.

**New note:** explicitly flag in the report that the labeling strategy may
introduce bias that the FL/blockchain pipeline does not correct — provenance
verification proves artifact integrity, not label fairness or ground-truth
correctness (see Section 17.7 in the evaluation plan below).

---

## 17. ML Model Strategy (unchanged)

| Model | Use in project |
|---|---|
| Logistic Regression | Baseline / interpretability benchmark |
| Random Forest | Strong tabular comparison model |
| XGBoost | Primary supervised fraud model |
| Isolation Forest | Optional unsupervised anomaly signal |
| Autoencoder | Optional anomaly-detection comparison |
| SHAP | Explanation layer |

Recommended path: centralized XGBoost baseline first, then Flower-based FL
reproduction, compared against the centralized benchmark.

---

## 18. Evaluation Plan (extended)

| Dimension | Metrics / demonstration |
|---|---|
| Fraud detection | Precision, Recall, F1, ROC-AUC, PR-AUC (class imbalance) |
| Centralized vs FL | Detection performance and convergence comparison |
| **FL privacy (new)** | Attempt gradient inversion/membership inference against noised vs. unnoised, masked vs. unmasked updates; show defense effectiveness |
| **FL robustness (new)** | Inject a poisoned update; show plain FedAvg vs. robust aggregation outcome difference |
| Blockchain overhead | Transaction latency, throughput, ledger growth, CPU/memory overhead |
| FL + blockchain vs FL-only | Added blockchain cost |
| **FL + secure agg + robust agg overhead (new)** | Added compute/communication cost of the hardened pipeline vs. plain FedAvg |
| Tamper detection | Modify a claim/update/model/explanation; show hash mismatch |
| Explainability | SHAP for representative flagged claims |
| Privacy architecture | Demonstrate raw claims never transmitted to aggregator/blockchain, **and** that individual updates are never exposed to the aggregator |
| **Label bias check (new)** | Compare flagging rates across regions/crop types; report any disparity as a limitation, not resolve it as "verified fair" |

---

## 19. Suggested Final Demonstration (extended)

1. Show 6–8 insurer nodes with separate private datasets.
2. Start an FL round; show each insurer producing a **clipped, noised, masked**
   local update.
3. Show the aggregator can only access the **combined** update — instrument
   and display that individual updates are not recoverable.
4. Show update hashes (pre-mask) registered on Hyperledger Fabric.
5. Run robust aggregation; **deliberately inject a poisoned update** from one
   node and show it gets flagged/neutralized rather than corrupting the model.
6. Register the new global model hash on-chain.
7. Introduce two new claims at Insurer A: one normal, one suspicious. Both get
   claim commitments **and** prediction commitments on-chain.
8. Run the latest global model locally on both; show one low-risk, one
   high-risk prediction.
9. Run SHAP only for the suspicious claim; display feature contributions;
   register the SHAP commitment.
10. Open the investigator view: private claim/SHAP info + **collection-scoped**
    blockchain audit metadata.
11. Modify a local claim or explanation deliberately; rerun verification to
    show a hash mismatch.
12. Optionally resolve the investigation and show the new local data
    participating in the next FL round via the hardened pipeline.

---

## 20. Anticipated Questions — Updated Answers

**Why is 3 insurers not enough, and why 6–8?**
With only 3 nodes, differencing the global model before/after any single
insurer's contribution can approximate that insurer's individual update even
without direct access to it. More nodes dilute any single contribution's
signal, and this combines with — rather than replaces — secure aggregation.

**Doesn't hashing the pre-mask update defeat secure aggregation?**
No — the hash is a one-way commitment used only for later integrity
verification (e.g., in a dispute, an insurer can prove what it actually
submitted). It reveals nothing about the update's content and is never
published alongside anything that would allow reconstruction.

**Why not just trust FedAvg?**
FedAvg has no built-in defense against a poisoned or anomalous update; one
misbehaving or compromised node can meaningfully shift the global model.
Robust aggregation bounds that influence.

**Does this project achieve formal differential privacy?**
For the XGBoost track: not a formal DP guarantee, since DP-SGD theory assumes
gradient-descent training; the clip+noise mechanism is presented as an
empirical defense, demonstrated via a reconstruction-attack test. A secondary
DP-SGD-compatible model track is offered as optional strengthening.

**Does blockchain fix FL privacy?**
No — blockchain only makes commitments tamper-evident; it does not protect
what is computed or transmitted during training. FL privacy is addressed by
secure aggregation, clipping/noising and robust aggregation; blockchain
addresses provenance and integrity, a separate concern.

*(All original Section 19 Q&A from the base plan still applies and is
retained — this section only adds the new questions raised by the hardening
work.)*

---

## 21. Technology Stack (extended)

| Area | Technology |
|---|---|
| Language | Python |
| Federated Learning | Flower (flwr), incl. secure-aggregation extension |
| **Secure aggregation** | Flower secure-agg strategy, or custom pairwise-mask implementation |
| **Robust aggregation** | Custom trimmed-mean / norm-clipping strategy plugin for Flower |
| ML | XGBoost; scikit-learn for baselines; optional DP-SGD model (logistic regression / small NN) via Opacus or TF-Privacy |
| Explainability | SHAP |
| Data processing | pandas, NumPy |
| Imbalanced data | imbalanced-learn if required |
| Blockchain | Hyperledger Fabric, with private data collections |
| Smart contract | Fabric chaincode (Go/JavaScript/TypeScript) |
| Containers | Docker |
| Experimentation | Jupyter + scripted reproducible pipeline |
| Version control | Git/GitHub |

---

## 22. Development Plan (revised timeline)

| Phase | Target |
|---|---|
| 1 | Literature review, final architecture, **threat model** (Section 5) |
| 2 | RMA data acquisition, preprocessing, partitioning into **6–8 nodes** |
| 3 | Fraud-label strategy and centralized XGBoost baseline |
| 4 | Flower FL simulation — plain FedAvg baseline across all nodes |
| 5 | **Add secure aggregation** (Flower secure-agg or pairwise mask) |
| 6 | **Add clip + noise on local updates**; run reconstruction-attack test |
| 7 | **Add robust aggregation**; run poisoning demonstration |
| 8 | Hyperledger Fabric network, chaincode, **private data collections** |
| 9 | Claim registration + claim hash workflow (with nonce management) |
| 10 | Model-update/global-model blockchain anchoring (pre-mask hashes + anomaly flags) |
| 11 | Local inference + SHAP explanation; mandatory prediction commitments for every claim |
| 12 | Investigator audit/verification workflow, scoped access |
| 13 | Tampering demonstration + FL privacy/robustness benchmarks + blockchain overhead benchmarks |
| 14 | Final evaluation, report and presentation |

*(Phases 5–7 are the net-new work versus the original plan; everything else
maps directly onto the original 11-phase timeline, just re-numbered and
sequenced to put the hardened FL pipeline in place before wiring it to the
ledger.)*

---

## 23. Design Decisions to Freeze Before Coding (extended)

Original list, plus new items in **bold**:

1. Exact RMA dataset fields and final insurer partitioning method — **now
   targeting 6–8 nodes, not 3**.
2. Heuristic labels vs. synthetic fraud injection vs. hybrid.
3. Primary model fixed as XGBoost unless experiments justify otherwise.
4. Suspicious-score threshold defined via validation data.
5. Exact canonical claim representation and **versioned schema** + secret
   nonce handling (generation, storage, loss-handling policy).
6. Exact blockchain transactions for every claim and every FL round,
   **including anomaly-flag transactions**.
7. **Every new claim gets a claim hash + prediction commitment; SHAP
   commitments reserved for flagged/high-value claims** (firm decision, not
   optional).
8. **Secure aggregation mechanism chosen** (Flower built-in vs. custom
   pairwise mask) and documented.
9. **Clipping bound (C) and noise scale (σ) chosen and justified**, with the
   accuracy/privacy tradeoff reported.
10. **Robust aggregation rule chosen** (trimmed mean vs. norm-clipping vs.
    Krum) and its poisoning-defense demonstrated.
11. Fabric participants, identities, endorsement rules, **and private data
    collection boundaries**.
12. What the investigator is authorized to query, **scoped by collection**.
13. Benchmark blockchain overhead against FL without blockchain, **and
    benchmark secure/robust aggregation overhead against plain FedAvg**.

---

## 24. Final Contribution Statement (updated)

This project's contribution is architectural and defensive, not purely
architectural: Federated Learning enables cross-insurer model training without
raw-data pooling; **secure aggregation and update clipping/noising prevent the
FL process itself from becoming a privacy side channel**; **robust
aggregation prevents any single insurer from unilaterally corrupting the
shared model**; and Hyperledger Fabric provides a shared, permissioned,
access-scoped audit/provenance layer for the lifecycle of claims and model
artifacts. Local SHAP preserves explainability without centralizing private
claims.

The resulting system answers four questions, not three:
1. **Is this claim high-risk?** — XGBoost
2. **Why was it flagged?** — SHAP
3. **Can we verify what claim/model/explanation was recorded and whether it
   was altered?** — Blockchain
4. **Can any single party — the aggregator or a misbehaving insurer — learn
   more than it should, or corrupt the shared model?** — Secure aggregation +
   robust aggregation (this is the added question this revision answers)

---

## 25. One-Minute Explanation (updated)

"Our system simulates multiple crop insurers that keep their claims data
private. They collaboratively train an XGBoost fraud-detection model using
Federated Learning — but instead of trusting the central aggregator with raw
model updates, each insurer clips and noises its update and masks it through
secure aggregation, so the aggregator only ever sees the combined result,
never any individual insurer's contribution. A robust aggregation rule also
protects the shared model against a misbehaving or compromised insurer. After
each round, hashes of the local updates and the resulting global model are
anchored on a permissioned Hyperledger Fabric blockchain, scoped so
participants only see what they're authorized to see. When a new claim
arrives, the complete claim stays in the insurer's private database, while a
cryptographic commitment is recorded on-chain for every claim — not just
flagged ones, to avoid leaking information through silence. The latest global
model evaluates the claim locally; if it's high-risk, SHAP runs locally to
explain the prediction, and its commitment is anchored too. Investigators see
the real claim and explanation through authorized, scoped access, and use
blockchain commitments to verify integrity and the exact model version used.
Resolved claims can feed future FL rounds through the same hardened pipeline,
creating a continuous, privacy-preserving, tamper-evident, and
poisoning-resistant cycle of collaborative learning."

---

## Summary of What Changed vs. the Original Plan

| Area | Original | This revision |
|---|---|---|
| Insurer nodes | 3 | 6–8+ |
| Aggregator sees | Individual raw updates | Only combined update (secure agg) |
| Update protection | None | Clip + noise before transmission |
| Aggregation rule | Plain FedAvg | Robust aggregation (trimmed mean / outlier rejection) |
| Poisoning defense | None | Anomaly detection + flagging on-chain |
| On-chain access | Channel-level | Fabric private data collections, scoped by party |
| Nonce management | Mentioned, unspecified | Per-claim CSPRNG, storage and loss-handling defined |
| Prediction commitments | Optional / flagged-only implied | Mandatory for every claim (closes silence side channel) |
| Threat model | Implicit | Explicit adversary table (Section 5) |
| Evaluation | Accuracy + blockchain overhead | + FL privacy attack test, poisoning test, bias check |
