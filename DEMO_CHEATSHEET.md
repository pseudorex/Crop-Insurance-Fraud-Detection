# Crop Insurance Fraud Consortium — Teacher Demo & Viva Cheatsheet

> **Quick Project Pitch (Say this to the teacher):**  
> *"Our project implements a multi-insurer consortium for crop insurance fraud detection. Each insurer keeps their raw agricultural data private in an isolated PostgreSQL database. Model training is federated using Differential Privacy (DP-XGBoost). To ensure zero fraud and immutable accountability, every claim's canonical RFC-8785 SHA-256 fingerprint, model weights, and AI TreeSHAP explanations are anchored into an Ethereum EVM smart contract (`InsuranceAudit.sol`) running on our private Ganache node."*

---

## 🚀 Live Terminal Demonstration (Step-by-Step Flow)

Run these commands in order from PowerShell inside `d:\Blockchain`:

---

### Step 1: Show Blockchain Node Health & Block Height
```powershell
d:\Blockchain\blockvenv\Scripts\python.exe blockchain/explore_blocks.py
```
* **What it outputs:** Ganache RPC status, current block height, gas price, deployed smart contract address, and recent mined blocks.
* 🗣️ **Say to teacher:**  
  *"This terminal explorer connects via Web3 JSON-RPC to our private Ethereum EVM node on port 8545. It shows that our Solidity 0.8.20 audit contract is deployed and actively mining transaction commitments."*

---

### Step 2: Show Gas Usage & Claim Registration (Block #1)
```powershell
d:\Blockchain\blockvenv\Scripts\python.exe blockchain/explore_blocks.py --block 1
```
* **What it outputs:** Full transaction receipt, gas used (`23,604 units`), and decoded parameters for `registerClaim()`.
* 🗣️ **Say to teacher:**  
  *"Here is Block #1 where a claim was registered. Notice the **Gas Used is only 23,604 units**. Storing raw 200KB JSON files on Ethereum would cost over 5,000,000 gas. By hashing off-chain with RFC-8785 canonical JSON and writing only a 32-byte SHA-256 hash, we achieved a **99.5% gas reduction**."*

---

### Step 3: Show Selective TreeSHAP Anchoring (Block #2)
```powershell
d:\Blockchain\blockvenv\Scripts\python.exe blockchain/explore_blocks.py --block 2
```
* **What it outputs:** Transaction receipt for `anchorSHAP()`, consuming `22,176 gas`.
* 🗣️ **Say to teacher:**  
  *"Block #2 demonstrates our selective explainability protocol. Our smart contract strictly enforces that only **HIGH-risk fraud claims** can anchor a TreeSHAP explanation on-chain. Legitimate low-risk claims skip SHAP anchoring, saving block space and gas across millions of claims."*

---

### Step 4: Query a Claim Directly from Smart Contract Storage
```powershell
d:\Blockchain\blockvenv\Scripts\python.exe blockchain/explore_blocks.py --claim CLM-INSURER3-3818
```
* **What it outputs:** The submitting insurer (`insurer3`), canonical hash, risk tier (`HIGH`), and SHAP hash directly from Solidity storage.
* 🗣️ **Say to teacher:**  
  *"This reads the smart contract's state mapping directly. Notice that zero personal farmer data or financial amounts are stored here — only the cryptographic fingerprint. The raw data remains private to Insurer 3, but is cryptographically bound to this immutable block."*

---

### Step 5: Verify Federated Model Weights Commitment (M1)
```powershell
d:\Blockchain\blockvenv\Scripts\python.exe blockchain/explore_blocks.py --model M1
```
* **What it outputs:** Verified SHA-256 hash of the Global Model M1 (`xgb_dp_federated.json`).
* 🗣️ **Say to teacher:**  
  *"This guarantees model governance. After Federated Learning Round 5, the certified model weights were hashed and locked into the smart contract. If an attacker swaps out the model file on disk, the SHA-256 will mismatch and trigger an immediate governance alert."*

---

### Step 6: List All Claims Committed on the Ledger
```powershell
d:\Blockchain\blockvenv\Scripts\python.exe blockchain/explore_blocks.py --all-claims
```
* **What it outputs:** An audit table scanning all mined blocks and displaying every claim reference, insurer, and canonical hash.
* 🗣️ **Say to teacher:**  
  *"An external auditor or regulatory body like the USDA RMA can scan the blockchain to view all claims committed across all 6 insurer nodes."*

---

### Step 7: Live Real-Time Block Streaming (Interactive Demo)
```powershell
d:\Blockchain\blockvenv\Scripts\python.exe blockchain/explore_blocks.py --watch
```
* **What to do:**
  1. Leave this running in your terminal.
  2. Open the React Dashboard at `http://localhost:3000`.
  3. Go to the **Claim Intake** tab and click **Submit Claim**.
* 🗣️ **Say to teacher:**  
  *"Watch the terminal — the second a claim is submitted in the web dashboard, Ganache immediately mines a new block, and our stream displays the transaction hash and block number in real-time."*
  *(Press `Ctrl + C` to stop watching).*

---

### Step 8: Run Full Automated 11-Step Cryptographic Audit & Tamper Test
```powershell
d:\Blockchain\blockvenv\Scripts\python.exe backend/test_backend.py
```
* **What it outputs:**
  - `[1] Health Check: HEALTHY | DB Mode: POSTGRES`
  - `[2] Low-risk intake (No SHAP overhead)`
  - `[3] High-risk intake (SHAP generated & anchored)`
  - `[4] Initial Audit: VERIFIED`
  - `[5] Injects malicious indemnity tamper ($95,000)`
  - `[6] Auditor Check: TAMPERED (Caught!)`
  - `[7] Restore database value`
  - `[8] Post-restore Audit: VERIFIED`
  - `[10] Injects malicious SHAP explanation weight tamper`
  - `[11] Post-SHAP-Tamper Audit: TAMPERED (Caught!)`
* 🗣️ **Say to teacher:**  
  *"This automated test mathematically proves that any database tampering — whether changing an indemnity payout or modifying AI feature weights — is caught immediately by our 4-phase cryptographic auditor."*

---

### Step 9: Quick Node & Test ETH Balance Check
```powershell
d:\Blockchain\blockvenv\Scripts\python.exe -c "from web3 import Web3; w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545')); acct = w3.eth.accounts[0]; print('Block:', w3.eth.block_number, '| Deployer:', acct, '| Balance:', w3.from_wei(w3.eth.get_balance(acct), 'ether'), 'ETH')"
```
* **What it outputs:** Current block number, deployer account address, and remaining test ETH balance.

---

## 🎓 Top 5 Teacher Questions & How to Answer Them

### Q1: Why use Ganache instead of public Ethereum Mainnet?
> **Answer:**  
> *"Ethereum Mainnet requires paying real currency ($) for gas and publicizes all transactions. For an agricultural insurance consortium, Ganache gives us a private, zero-cost, enterprise-controlled Ethereum EVM node with instant mining (`blockTime = 0`), ideal for high-throughput testing and multi-tenant consortiums."*

### Q2: What is Gas and why does each operation cost a different amount?
> **Answer:**  
> *"Gas is the measure of computational effort on the Ethereum Virtual Machine. It prevents infinite loops (Halting Problem) and spam attacks. Heavy operations like creating permanent contract storage (`SSTORE`) cost 20,000 gas, while read-only functions like `verifyClaim` cost **0 gas** because they execute locally without modifying blockchain state."*

### Q3: What happens if a corrupt employee edits the PostgreSQL database directly?
> **Answer:**  
> *"They can modify the local SQL row, but they cannot alter the Ethereum blockchain. When the auditor runs, it re-computes the SHA-256 hash of the modified data and compares it to the immutable hash stored on Ganache. The hashes mismatch, and the system immediately flags `SECURITY TAMPER DETECTED`."*

### Q4: Why not store all the claim data on the blockchain?
> **Answer:**  
> *"For two reasons: **Privacy** and **Cost**. Farmers' financial data is legally protected and competitors shouldn't see each other's customers. Furthermore, storing 200KB of raw JSON on-chain costs millions of gas, whereas storing a 32-byte SHA-256 hash costs only ~23,000 gas."*

### Q5: How does the AI model connect to the Blockchain?
> **Answer:**  
> *"The DP-XGBoost model infers fraud probability. If the score is >= 0.50 (`HIGH`), the system calculates local TreeSHAP feature contributions and calls `anchorSHAP()` to commit the explanation hash to the blockchain, creating an immutable audit trail for contested claims."*
