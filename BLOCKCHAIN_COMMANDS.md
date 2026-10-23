# Ethereum Blockchain CLI Cheatsheet

Quick copy-paste commands to inspect blocks, smart contract storage, transaction hashes, gas usage, and live events on the **Ganache EVM Blockchain** (`http://127.0.0.1:8545`).

---

## 1. Blockchain Explorer Commands (Primary CLI Tool)

All commands run using the project virtual environment `blockvenv`.

### A. View Blockchain Overview & Last 10 Blocks
```bash
blockvenv\Scripts\python blockchain/explore_blocks.py
```
> Shows Ganache RPC status, chain height, gas price, contract address, and recent block activities.

---

### B. View Last N Blocks (e.g. 25 blocks)
```bash
blockvenv\Scripts\python blockchain/explore_blocks.py --blocks 25
```

---

### C. Deep-Dive Into a Specific Block (Inputs, Hashes, Gas)
```bash
blockvenv\Scripts\python blockchain/explore_blocks.py --block 40
```
*(Replace `40` with any block number you wish to inspect).*

---

### D. Query a Specific Claim Stored on Blockchain
```bash
blockvenv\Scripts\python blockchain/explore_blocks.py --claim CLM-NORMAL-VERIFIED-01
```
```bash
blockvenv\Scripts\python blockchain/explore_blocks.py --claim CLM-INSURER6-8106
```
*(Shows Claim ID, submitting insurer, canonical hash, risk tier, SHAP hash, and timestamp directly from the Solidity smart contract storage).*

---

### E. List All Claims Ever Committed on the Blockchain
```bash
blockvenv\Scripts\python blockchain/explore_blocks.py --all-claims
```
> Scans all blocks from Block #0 to latest and renders a table of all registered claims.

---

### F. Query Federated Learning Model Weights Commitment (M1)
```bash
blockvenv\Scripts\python blockchain/explore_blocks.py --model M1
```
> Verifies the on-chain SHA-256 commitment of the DP-XGBoost model (`xgb_dp_federated.json`).

---

### G. Live Real-Time Block Watcher (Stream New Blocks)
```bash
blockvenv\Scripts\python blockchain/explore_blocks.py --watch
```
> Keeps running in your terminal. Whenever you submit a claim or test tampering in the Web Dashboard, the newly mined block immediately appears in your console. Press `Ctrl + C` to stop.

---

## 2. Check Gas & Account Balance

### Check Sender Account & Remaining Test ETH
```bash
blockvenv\Scripts\python -c "from web3 import Web3; w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545')); acct = w3.eth.accounts[0]; print(f'Sender Address: {acct}\nBalance: {w3.from_wei(w3.eth.get_balance(acct), \"ether\")} test ETH\nCurrent Block: #{w3.eth.block_number}')"
```

### List All 10 Ganache Pre-Funded Test Accounts
```bash
blockvenv\Scripts\python -c "from web3 import Web3; w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545')); [print(f'Account [{i}]: {a} | Balance: {w3.from_wei(w3.eth.get_balance(a), \"ether\")} ETH') for i, a in enumerate(w3.eth.accounts)]"
```

---

## 3. Direct JSON-RPC `curl` Commands (Raw EVM Node API)

You can also talk directly to Ganache without Python using `curl`:

### Get Latest Block Number (Hex)
```bash
curl -X POST http://127.0.0.1:8545 -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_blockNumber\",\"params\":[],\"id\":1}"
```

### Get Gas Price
```bash
curl -X POST http://127.0.0.1:8545 -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_gasPrice\",\"params\":[],\"id\":1}"
```

### Get Block Details by Number (e.g. Block #40 in hex = `0x28`)
```bash
curl -X POST http://127.0.0.1:8545 -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getBlockByNumber\",\"params\":[\"0x28\", true],\"id\":1}"
```

---

## 4. Docker Container Commands

### View Live Ganache Container Logs
```bash
docker logs --tail 50 -f crop_insurance_blockchain
```

### Check Container Status
```bash
docker ps --filter "name=crop_insurance"
```

### Restart Blockchain Node (If needed)
```bash
docker restart crop_insurance_blockchain
```

---

## 5. Network & Smart Contract Metadata

| Parameter | Value |
| :--- | :--- |
| **RPC Endpoint** | `http://127.0.0.1:8545` |
| **Network / Chain ID** | `1337` (Ganache Private EVM) |
| **Audit Smart Contract** | `0x4FE8258090542D96c71DCbDFaC59c3828B6FA718` |
| **Solidity Version** | `0.8.20` |
| **Deployer / Sender** | `0x21dE14aD353B78498843c0F888E9A55443755404` |
| **Default Gas Limit** | `300,000` |
| **Default Gas Price** | `2 Gwei` ($0.000000002$ test ETH) |
| **Deployed File Config** | [`blockchain/contract_deployment.json`](file:///d:/Blockchain/blockchain/contract_deployment.json) |
