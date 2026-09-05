# Phase 7 — Hyperledger Fabric Network & Consortium Topology

> Multi-organization Hyperledger Fabric (v2.5) blockchain infrastructure establishing a decentralized, tamper-evident audit ledger and provenance tracking system across 6 competing crop insurance providers.

---

## 1. Consortium Architecture

```
                                  CONSORTIUM TOPOLOGY
                        ┌─────────────────────────────────────┐
                        │        Orderer Organization         │
                        │    (orderer.insurance.com:7050)     │
                        │        etcdraft Consensus           │
                        └──────────────────┬──────────────────┘
                                           │
                 ┌─────────────────────────┴─────────────────────────┐
                 │             CHANNEL: insurance-channel            │
                 └─────────────────────────┬─────────────────────────┘
                                           │
       ┌──────────────┬──────────────┬─────┴────────┬──────────────┬──────────────┐
       │              │              │              │              │              │
       ▼              ▼              ▼              ▼              ▼              ▼
   InsurerA       InsurerB       InsurerC       InsurerD       InsurerE       InsurerF
 (Port: 7051)   (Port: 8051)   (Port: 9051)  (Port: 10051)  (Port: 11051)  (Port: 12051)
  InsurerAMSP    InsurerBMSP    InsurerCMSP    InsurerDMSP    InsurerEMSP    InsurerFMSP
```

### Consortium Organizations

| Organization | Node Name | Endpoint / Port | MSP ID | Anchor Peer | State DB |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Orderer Org** | `orderer.insurance.com` | `localhost:7050` | `OrdererMSP` | Raft Consenter | Embedded |
| **Insurer A** | `peer0.insurera.insurance.com` | `localhost:7051` | `InsurerAMSP` | `peer0.insurera.insurance.com:7051` | GoLevelDB |
| **Insurer B** | `peer0.insurerb.insurance.com` | `localhost:8051` | `InsurerBMSP` | `peer0.insurerb.insurance.com:8051` | GoLevelDB |
| **Insurer C** | `peer0.insurerc.insurance.com` | `localhost:9051` | `InsurerCMSP` | `peer0.insurerc.insurance.com:9051` | GoLevelDB |
| **Insurer D** | `peer0.insurerd.insurance.com` | `localhost:10051` | `InsurerDMSP` | `peer0.insurerd.insurance.com:10051` | GoLevelDB |
| **Insurer E** | `peer0.insurere.insurance.com` | `localhost:11051` | `InsurerEMSP` | `peer0.insurere.insurance.com:11051` | GoLevelDB |
| **Insurer F** | `peer0.insurerf.insurance.com` | `localhost:12051` | `InsurerFMSP` | `peer0.insurerf.insurance.com:12051` | GoLevelDB |
| **Admin CLI** | `cli.insurance.com` | Internal bridge | `InsurerAMSP` | N/A | N/A |

---

## 2. Directory Structure & Files

```
d:\Blockchain\blockchain\fabric-network\
├── README.md                  ← This document (Phase 7 overview & guide)
├── crypto-config.yaml         ← Cryptographic identities for Orderer + 6 Insurer Orgs
├── configtx.yaml              ← Channel profiles, consortium policies & Raft consensus
├── docker-compose.yaml        ← Multi-container service definitions
├── generate_crypto.py         ← Standalone pure-Python X.509 ECDSA certificate generator
├── network.ps1                ← Automated Windows PowerShell lifecycle manager
├── network.sh                 ← Automated Linux/macOS/WSL lifecycle script
├── channel-artifacts/         ← Genesis block & channel creation transaction
└── crypto-config/             ← X.509 MSP credentials & TLS certificates
```

---

## 3. Cryptographic Security & Identity Model

1. **X.509 ECDSA (secp256r1) Certificates**: Standard elliptic-curve cryptography for secure signing and authentication.
2. **Mutual TLS (mTLS)**: Enforced on all peer-to-peer, peer-to-orderer, and client-to-peer communication channels.
3. **Role Separation (`NodeOUs`)**: Explicit certificate organizational units differentiating between `peer`, `admin`, and `client` identities.
4. **Privacy-Preserving Audit**: Peer MSP credentials verify the authenticity of transactions without exposing private insurance records.

---

## 4. Quick Start & Network Management

### On Windows (PowerShell)

```powershell
# 1. Generate cryptographic identities & channel artifacts
.\blockchain\fabric-network\network.ps1 generate

# 2. Start Orderer, 6 Peer nodes, and CLI container
.\blockchain\fabric-network\network.ps1 up

# 3. Create insurance-channel and join all 6 insurer peers
.\blockchain\fabric-network\network.ps1 createChannel

# 4. Check status of running containers
.\blockchain\fabric-network\network.ps1 status

# 5. Teardown network
.\blockchain\fabric-network\network.ps1 down
```

### On Linux / macOS / WSL (Bash)

```bash
chmod +x blockchain/fabric-network/network.sh
./blockchain/fabric-network/network.sh generate
./blockchain/fabric-network/network.sh up
./blockchain/fabric-network/network.sh createChannel
./blockchain/fabric-network/network.sh status
./blockchain/fabric-network/network.sh down
```

---

## 5. Transition to Phase 8

Phase 7 establishes the live blockchain infrastructure. **Phase 8** implements and deploys the Go-based `insurance_audit` Smart Contract (Chaincode) and Private Data Collections on `insurance-channel`.
