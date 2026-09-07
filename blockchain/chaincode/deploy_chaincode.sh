#!/usr/bin/env bash
# ==============================================================================
# Fabric 2.x Chaincode Lifecycle Deployment Script (Linux/macOS/WSL)
# Smart Contract: insurance_audit
# Project: Federated, Blockchain-Audited Crop Insurance Fraud Detection
# ==============================================================================

set -euo pipefail

CHANNEL_NAME="${1:-insurance-channel}"
CC_NAME="${2:-insurance_audit}"
CC_VERSION="${3:-1.0}"
CC_SEQUENCE="${4:-1}"

echo "=================================================================="
echo "DEPLOYING CHAINCODE: ${CC_NAME} (v${CC_VERSION}, Sequence: ${CC_SEQUENCE})"
echo "=================================================================="

# 1. Package Chaincode
echo ">>> [1/5] Packaging Chaincode (${CC_NAME})..."
docker exec cli.insurance.com bash -c "
    cd /opt/gopath/src/github.com/hyperledger/fabric/peer/chaincode && \
    peer lifecycle chaincode package ${CC_NAME}_${CC_VERSION}.tar.gz \
      --path /opt/gopath/src/github.com/hyperledger/fabric/peer/chaincode \
      --lang golang \
      --label ${CC_NAME}_${CC_VERSION}
"
echo ">>> Chaincode packaged: ${CC_NAME}_${CC_VERSION}.tar.gz"

# 2. Install on all 6 peers
peers=(
    "InsurerAMSP:insurera.insurance.com:7051"
    "InsurerBMSP:insurerb.insurance.com:8051"
    "InsurerCMSP:insurerc.insurance.com:9051"
    "InsurerDMSP:insurerd.insurance.com:10051"
    "InsurerEMSP:insurere.insurance.com:11051"
    "InsurerFMSP:insurerf.insurance.com:12051"
)

echo ">>> [2/5] Installing Chaincode on all 6 Insurer Peers..."
for item in "${peers[@]}"; do
    IFS=":" read -r org domain port <<< "${item}"
    echo ">>> Installing on peer0.${domain}:${port} (${org})..."
    docker exec -e CORE_PEER_LOCALMSPID="${org}" \
        -e CORE_PEER_MSPCONFIGPATH="/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/${domain}/users/Admin@${domain}/msp" \
        -e CORE_PEER_TLS_ROOTCERT_FILE="/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/${domain}/peers/peer0.${domain}/tls/ca.crt" \
        -e CORE_PEER_ADDRESS="peer0.${domain}:${port}" \
        cli.insurance.com \
        peer lifecycle chaincode install "/opt/gopath/src/github.com/hyperledger/fabric/peer/chaincode/${CC_NAME}_${CC_VERSION}.tar.gz"
done

# 3. Query Package ID
echo ">>> [3/5] Querying Installed Package ID..."
PKG_OUTPUT=$(docker exec cli.insurance.com peer lifecycle chaincode queryinstalled)
PACKAGE_ID=$(echo "${PKG_OUTPUT}" | grep "${CC_NAME}_${CC_VERSION}" | head -n 1 | awk -F'[, ]+' '{print $3}')
echo ">>> Package ID: ${PACKAGE_ID}"

# 4. Approve for each of the 6 Orgs
echo ">>> [4/5] Approving Chaincode Definition for all 6 Insurer Orgs..."
for item in "${peers[@]}"; do
    IFS=":" read -r org domain port <<< "${item}"
    echo ">>> Approving for ${org}..."
    docker exec -e CORE_PEER_LOCALMSPID="${org}" \
        -e CORE_PEER_MSPCONFIGPATH="/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/${domain}/users/Admin@${domain}/msp" \
        -e CORE_PEER_TLS_ROOTCERT_FILE="/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/${domain}/peers/peer0.${domain}/tls/ca.crt" \
        -e CORE_PEER_ADDRESS="peer0.${domain}:${port}" \
        cli.insurance.com \
        peer lifecycle chaincode approveformyorg -o orderer.insurance.com:7050 \
        --channelID "${CHANNEL_NAME}" --name "${CC_NAME}" --version "${CC_VERSION}" \
        --package-id "${PACKAGE_ID}" --sequence "${CC_SEQUENCE}" \
        --collections-config /opt/gopath/src/github.com/hyperledger/fabric/peer/chaincode/collections_config.json \
        --tls --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/insurance.com/orderers/orderer.insurance.com/tls/ca.crt
done

# 5. Commit Chaincode Definition
echo ">>> [5/5] Committing Chaincode Definition to ${CHANNEL_NAME}..."
docker exec cli.insurance.com \
    peer lifecycle chaincode commit -o orderer.insurance.com:7050 \
    --channelID "${CHANNEL_NAME}" --name "${CC_NAME}" --version "${CC_VERSION}" \
    --sequence "${CC_SEQUENCE}" \
    --collections-config /opt/gopath/src/github.com/hyperledger/fabric/peer/chaincode/collections_config.json \
    --peerAddresses peer0.insurera.insurance.com:7051 --tlsRootCertFiles /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurera.insurance.com/peers/peer0.insurera.insurance.com/tls/ca.crt \
    --peerAddresses peer0.insurerb.insurance.com:8051 --tlsRootCertFiles /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurerb.insurance.com/peers/peer0.insurerb.insurance.com/tls/ca.crt \
    --peerAddresses peer0.insurerc.insurance.com:9051 --tlsRootCertFiles /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurerc.insurance.com/peers/peer0.insurerc.insurance.com/tls/ca.crt \
    --tls --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/insurance.com/orderers/orderer.insurance.com/tls/ca.crt

echo ">>> [SUCCESS] Chaincode ${CC_NAME} successfully deployed to channel ${CHANNEL_NAME}!"
