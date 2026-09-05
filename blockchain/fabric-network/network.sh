#!/usr/bin/env bash
# ==============================================================================
# Hyperledger Fabric Network Automation Script for Linux/macOS/WSL
# Project: Federated, Blockchain-Audited Crop Insurance Fraud Detection
# Consortium: 6 Insurers (InsurerA - InsurerF) + 1 Orderer
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

FABRIC_TOOLS_IMG="hyperledger/fabric-tools:2.5"
CHANNEL_NAME="insurance-channel"

function generate_artifacts() {
    echo ">>> [1/4] Cleaning previous cryptographic and channel artifacts..."
    rm -rf crypto-config channel-artifacts
    mkdir -p channel-artifacts

    echo ">>> [2/4] Generating cryptographic material (cryptogen)..."
    docker run --rm -v "${SCRIPT_DIR}:/network" -w /network "${FABRIC_TOOLS_IMG}" \
        cryptogen generate --config=/network/crypto-config.yaml --output=/network/crypto-config

    echo ">>> [3/4] Generating Genesis Block (configtxgen)..."
    docker run --rm -v "${SCRIPT_DIR}:/network" -w /network \
        -e FABRIC_CFG_PATH=/network "${FABRIC_TOOLS_IMG}" \
        configtxgen -profile InsuranceOrdererGenesis -channelID system-channel -outputBlock /network/channel-artifacts/genesis.block

    echo ">>> [4/4] Generating Channel Creation Transaction (${CHANNEL_NAME})..."
    docker run --rm -v "${SCRIPT_DIR}:/network" -w /network \
        -e FABRIC_CFG_PATH=/network "${FABRIC_TOOLS_IMG}" \
        configtxgen -profile InsuranceChannel -channelID "${CHANNEL_NAME}" -outputCreateChannelTx "/network/channel-artifacts/${CHANNEL_NAME}.tx"

    orgs=("InsurerAMSP" "InsurerBMSP" "InsurerCMSP" "InsurerDMSP" "InsurerEMSP" "InsurerFMSP")
    for org in "${orgs[@]}"; do
        echo ">>> Generating Anchor Peer update for ${org}..."
        docker run --rm -v "${SCRIPT_DIR}:/network" -w /network \
            -e FABRIC_CFG_PATH=/network "${FABRIC_TOOLS_IMG}" \
            configtxgen -profile InsuranceChannel -outputAnchorPeersUpdate "/network/channel-artifacts/${org}anchors.tx" \
            -channelID "${CHANNEL_NAME}" -asOrg "${org}"
    done

    echo ">>> Cryptographic and Channel Artifacts successfully created."
}

function start_network() {
    echo ">>> Starting Hyperledger Fabric Network (Orderer + 6 Insurer Peers + CLI)..."
    docker-compose -f docker-compose.yaml up -d
    echo ">>> Network containers started."
}

function create_and_join_channel() {
    echo ">>> Creating Channel: ${CHANNEL_NAME}..."
    docker exec -e CORE_PEER_LOCALMSPID=InsurerAMSP \
        -e CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurera.insurance.com/users/Admin@insurera.insurance.com/msp \
        -e CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurera.insurance.com/peers/peer0.insurera.insurance.com/tls/ca.crt \
        -e CORE_PEER_ADDRESS=peer0.insurera.insurance.com:7051 \
        cli.insurance.com \
        peer channel create -o orderer.insurance.com:7050 -c "${CHANNEL_NAME}" \
        -f "/opt/gopath/src/github.com/hyperledger/fabric/peer/channel-artifacts/${CHANNEL_NAME}.tx" \
        --outputBlock "/opt/gopath/src/github.com/hyperledger/fabric/peer/channel-artifacts/${CHANNEL_NAME}.block" \
        --tls --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/insurance.com/orderers/orderer.insurance.com/tls/ca.crt

    sleep 3

    peers=(
        "InsurerAMSP:insurera.insurance.com:7051"
        "InsurerBMSP:insurerb.insurance.com:8051"
        "InsurerCMSP:insurerc.insurance.com:9051"
        "InsurerDMSP:insurerd.insurance.com:10051"
        "InsurerEMSP:insurere.insurance.com:11051"
        "InsurerFMSP:insurerf.insurance.com:12051"
    )

    for item in "${peers[@]}"; do
        IFS=":" read -r org domain port <<< "${item}"
        echo ">>> Joining peer0.${domain}:${port} (${org}) to channel ${CHANNEL_NAME}..."
        docker exec -e CORE_PEER_LOCALMSPID="${org}" \
            -e CORE_PEER_MSPCONFIGPATH="/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/${domain}/users/Admin@${domain}/msp" \
            -e CORE_PEER_TLS_ROOTCERT_FILE="/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/${domain}/peers/peer0.${domain}/tls/ca.crt" \
            -e CORE_PEER_ADDRESS="peer0.${domain}:${port}" \
            cli.insurance.com \
            peer channel join -b "/opt/gopath/src/github.com/hyperledger/fabric/peer/channel-artifacts/${CHANNEL_NAME}.block" \
            --tls --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/insurance.com/orderers/orderer.insurance.com/tls/ca.crt
    done

    for item in "${peers[@]}"; do
        IFS=":" read -r org domain port <<< "${item}"
        echo ">>> Updating Anchor Peer for ${org}..."
        docker exec -e CORE_PEER_LOCALMSPID="${org}" \
            -e CORE_PEER_MSPCONFIGPATH="/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/${domain}/users/Admin@${domain}/msp" \
            -e CORE_PEER_TLS_ROOTCERT_FILE="/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/${domain}/peers/peer0.${domain}/tls/ca.crt" \
            -e CORE_PEER_ADDRESS="peer0.${domain}:${port}" \
            cli.insurance.com \
            peer channel update -o orderer.insurance.com:7050 -c "${CHANNEL_NAME}" \
            -f "/opt/gopath/src/github.com/hyperledger/fabric/peer/channel-artifacts/${org}anchors.tx" \
            --tls --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/insurance.com/orderers/orderer.insurance.com/tls/ca.crt
    done

    echo ">>> Channel ${CHANNEL_NAME} successfully created and all 6 insurer peers joined!"
}

function stop_network() {
    echo ">>> Stopping Hyperledger Fabric network..."
    docker-compose -f docker-compose.yaml down --volumes --remove-orphans
    echo ">>> Network stopped."
}

function show_status() {
    echo "=== Fabric Network Container Status ==="
    docker ps --filter "network=insurance_net" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

ACTION="${1:-status}"
case "${ACTION}" in
    generate)      generate_artifacts ;;
    up)            start_network ;;
    createChannel) create_and_join_channel ;;
    down)          stop_network ;;
    restart)       stop_network; start_network; create_and_join_channel ;;
    status)        show_status ;;
    clean)         stop_network; rm -rf crypto-config channel-artifacts ;;
    *)             show_status ;;
esac
