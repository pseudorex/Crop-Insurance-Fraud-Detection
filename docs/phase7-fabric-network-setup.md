# Phase 7 — Hyperledger Fabric Network & Consortium Topology

> Implementation and deployment of the permissioned Hyperledger Fabric blockchain consortium network for multi-insurer fraud audit and model provenance.

---

## 1. Network Topology & Consortium Structure

The network models a production consortium comprising **6 competing crop insurance organizations** and an independent **Orderer organization**:

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

### Participant Specification

| Organization | Node Name | External Port | MSP ID | Anchor Peer |
| :--- | :--- | :--- | :--- | :--- |
| **Orderer Org** | `orderer.insurance.com` | `7050` | `OrdererMSP` | N/A (Raft Consenter) |
| **Insurer A** | `peer0.insurera.insurance.com` | `7051` | `InsurerAMSP` | `peer0.insurera.insurance.com:7051` |
| **Insurer B** | `peer0.insurerb.insurance.com` | `8051` | `InsurerBMSP` | `peer0.insurerb.insurance.com:8051` |
| **Insurer C** | `peer0.insurerc.insurance.com` | `9051` | `InsurerCMSP` | `peer0.insurerc.insurance.com:9051` |
| **Insurer D** | `peer0.insurerd.insurance.com` | `10051` | `InsurerDMSP` | `peer0.insurerd.insurance.com:10051` |
| **Insurer E** | `peer0.insurere.insurance.com` | `11051` | `InsurerEMSP` | `peer0.insurere.insurance.com:11051` |
| **Insurer F** | `peer0.insurerf.insurance.com` | `12051` | `InsurerFMSP` | `peer0.insurerf.insurance.com:12051` |
| **Tools CLI** | `cli.insurance.com` | Internal | InsurerAMSP (switchable) | N/A |

---

## 2. Configuration & Architecture Files

All blockchain infrastructure files are organized inside `blockchain/fabric-network/`:

```
d:\Blockchain\blockchain\fabric-network\
├── crypto-config.yaml         # Cryptographic identity specifications (Orderer + 6 Insurers)
├── configtx.yaml              # Channel profiles, consortium definition, MSP policies, Raft consenters
├── docker-compose.yaml        # 8-container orchestration (Orderer + 6 Peers + CLI)
├── network.ps1                # Automated Windows PowerShell lifecycle manager
├── network.sh                 # Automated Linux/WSL/macOS lifecycle script
├── channel-artifacts/         # Output: genesis.block, insurance-channel.tx, anchor updates
└── crypto-config/             # Output: X.509 MSP certificates, TLS credentials, private keys
```

---

## 3. Cryptographic Hierarchy & Identity Model

- **Root Certificate Authorities**: Each organization operates an independent CA identity scope under standard MSP (`Membership Service Provider`) hierarchies:
  - `cacerts/`: Root CA certificate.
  - `tlscacerts/`: TLS Root CA certificate.
  - `signcerts/`: Peer/Admin public identity certificate.
  - `keystore/`: Node private signing key.
  - `admincerts/`: Authorized administrative identities.
- **NodeOUs Enabled**: Granular classification separating `peer`, `admin`, and `client` roles.
- **Mutual TLS**: All inter-node and client-to-peer communications enforce TLS authentication on dedicated communication ports.

---

## 4. Channel Configuration (`insurance-channel`)

1. **Consensus**: Crash Fault Tolerant (CFT) `etcdraft` Raft protocol managed by `OrdererMSP`.
2. **Channel Capabilities**: `V2_0` application and channel capabilities ensuring support for Fabric 2.x lifecycle chaincode management and Private Data Collections.
3. **Endorsement Policies**: `MAJORITY Endorsement` requiring endorsement across insurer peers for channel-wide state commits.

---

## 5. Network Lifecycle Commands

### Generate Cryptographic and Channel Artifacts
```powershell
.\blockchain\fabric-network\network.ps1 generate
```

### Start Network Containers
```powershell
.\blockchain\fabric-network\network.ps1 up
```

### Create Channel & Join All 6 Peers
```powershell
.\blockchain\fabric-network\network.ps1 createChannel
```

### Inspect Container Status
```powershell
.\blockchain\fabric-network\network.ps1 status
```

### Teardown Network
```powershell
.\blockchain\fabric-network\network.ps1 down
```

---

## 6. Next Step — Phase 8

With the consortium network and channel configuration established, **Phase 8** implements and deploys the Go-based `insurance_audit` Smart Contract (Chaincode) and Private Data Collections across `insurance-channel`.
