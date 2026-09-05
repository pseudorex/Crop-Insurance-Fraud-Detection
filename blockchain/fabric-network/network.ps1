# ==============================================================================
# Hyperledger Fabric Network Automation Script for Windows (PowerShell)
# Project: Federated, Blockchain-Audited Crop Insurance Fraud Detection
# Consortium: 6 Insurers (InsurerA - InsurerF) + 1 Orderer
# ==============================================================================

param (
    [Parameter(Position=0)]
    [ValidateSet("generate", "up", "createChannel", "down", "restart", "status", "clean")]
    [string]$Action = "status"
)

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $SCRIPT_DIR

$FABRIC_TOOLS_IMG = "hyperledger/fabric-tools:2.5"
$CHANNEL_NAME = "insurance-channel"

function Generate-Artifacts {
    Write-Host ">>> [1/4] Cleaning previous cryptographic and channel artifacts..." -ForegroundColor Cyan
    if (Test-Path "crypto-config") { Remove-Item -Recurse -Force "crypto-config" }
    if (Test-Path "channel-artifacts") { Remove-Item -Recurse -Force "channel-artifacts" }
    New-Item -ItemType Directory -Force -Path "channel-artifacts" | Out-Null

    Write-Host ">>> [2/4] Generating cryptographic material (cryptogen)..." -ForegroundColor Cyan
    docker run --rm -v "${SCRIPT_DIR}:/network" -w /network $FABRIC_TOOLS_IMG `
        cryptogen generate --config=/network/crypto-config.yaml --output=/network/crypto-config

    Write-Host ">>> [3/4] Generating Genesis Block (configtxgen)..." -ForegroundColor Cyan
    docker run --rm -v "${SCRIPT_DIR}:/network" -w /network `
        -e FABRIC_CFG_PATH=/network $FABRIC_TOOLS_IMG `
        configtxgen -profile InsuranceOrdererGenesis -channelID system-channel -outputBlock /network/channel-artifacts/genesis.block

    Write-Host ">>> [4/4] Generating Channel Creation Transaction (${CHANNEL_NAME})..." -ForegroundColor Cyan
    docker run --rm -v "${SCRIPT_DIR}:/network" -w /network `
        -e FABRIC_CFG_PATH=/network $FABRIC_TOOLS_IMG `
        configtxgen -profile InsuranceChannel -channelID $CHANNEL_NAME -outputCreateChannelTx /network/channel-artifacts/${CHANNEL_NAME}.tx

    $orgs = @("InsurerAMSP", "InsurerBMSP", "InsurerCMSP", "InsurerDMSP", "InsurerEMSP", "InsurerFMSP")
    foreach ($org in $orgs) {
        Write-Host ">>> Generating Anchor Peer update for ${org}..." -ForegroundColor Yellow
        docker run --rm -v "${SCRIPT_DIR}:/network" -w /network `
            -e FABRIC_CFG_PATH=/network $FABRIC_TOOLS_IMG `
            configtxgen -profile InsuranceChannel -outputAnchorPeersUpdate "/network/channel-artifacts/${org}anchors.tx" `
            -channelID $CHANNEL_NAME -asOrg $org
    }

    Write-Host ">>> Cryptographic and Channel Artifacts successfully created in channel-artifacts/ and crypto-config/." -ForegroundColor Green
}

function Start-Network {
    Write-Host ">>> Starting Hyperledger Fabric Network (Orderer + 6 Insurer Peers + CLI)..." -ForegroundColor Cyan
    docker-compose -f docker-compose.yaml up -d
    Write-Host ">>> Network containers started." -ForegroundColor Green
}

function Create-And-Join-Channel {
    Write-Host ">>> Creating Channel: ${CHANNEL_NAME}..." -ForegroundColor Cyan
    
    # 1. Create Channel (as InsurerA Admin)
    docker exec -e CORE_PEER_LOCALMSPID=InsurerAMSP `
        -e CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurera.insurance.com/users/Admin@insurera.insurance.com/msp `
        -e CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurera.insurance.com/peers/peer0.insurera.insurance.com/tls/ca.crt `
        -e CORE_PEER_ADDRESS=peer0.insurera.insurance.com:7051 `
        cli.insurance.com `
        peer channel create -o orderer.insurance.com:7050 -c $CHANNEL_NAME `
        -f /opt/gopath/src/github.com/hyperledger/fabric/peer/channel-artifacts/${CHANNEL_NAME}.tx `
        --outputBlock /opt/gopath/src/github.com/hyperledger/fabric/peer/channel-artifacts/${CHANNEL_NAME}.block `
        --tls --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/insurance.com/orderers/orderer.insurance.com/tls/ca.crt

    Start-Sleep -Seconds 3

    # 2. Join all 6 peers to the channel
    $peerConfigs = @(
        @{ Org="InsurerAMSP"; Domain="insurera.insurance.com"; Port="7051" },
        @{ Org="InsurerBMSP"; Domain="insurerb.insurance.com"; Port="8051" },
        @{ Org="InsurerCMSP"; Domain="insurerc.insurance.com"; Port="9051" },
        @{ Org="InsurerDMSP"; Domain="insurerd.insurance.com"; Port="10051" },
        @{ Org="InsurerEMSP"; Domain="insurere.insurance.com"; Port="11051" },
        @{ Org="InsurerFMSP"; Domain="insurerf.insurance.com"; Port="12051" }
    )

    foreach ($cfg in $peerConfigs) {
        $org = $cfg.Org
        $domain = $cfg.Domain
        $port = $cfg.Port
        Write-Host ">>> Joining peer0.${domain}:${port} (${org}) to channel ${CHANNEL_NAME}..." -ForegroundColor Cyan

        docker exec -e CORE_PEER_LOCALMSPID=$org `
            -e CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/${domain}/users/Admin@${domain}/msp `
            -e CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/${domain}/peers/peer0.${domain}/tls/ca.crt `
            -e CORE_PEER_ADDRESS=peer0.${domain}:${port} `
            cli.insurance.com `
            peer channel join -b /opt/gopath/src/github.com/hyperledger/fabric/peer/channel-artifacts/${CHANNEL_NAME}.block `
            --tls --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/insurance.com/orderers/orderer.insurance.com/tls/ca.crt
    }

    # 3. Update Anchor Peers
    foreach ($cfg in $peerConfigs) {
        $org = $cfg.Org
        $domain = $cfg.Domain
        $port = $cfg.Port
        Write-Host ">>> Updating Anchor Peer for ${org}..." -ForegroundColor Cyan

        docker exec -e CORE_PEER_LOCALMSPID=$org `
            -e CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/${domain}/users/Admin@${domain}/msp `
            -e CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/${domain}/peers/peer0.${domain}/tls/ca.crt `
            -e CORE_PEER_ADDRESS=peer0.${domain}:${port} `
            cli.insurance.com `
            peer channel update -o orderer.insurance.com:7050 -c $CHANNEL_NAME `
            -f /opt/gopath/src/github.com/hyperledger/fabric/peer/channel-artifacts/${org}anchors.tx `
            --tls --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/insurance.com/orderers/orderer.insurance.com/tls/ca.crt
    }

    Write-Host ">>> Channel ${CHANNEL_NAME} successfully created and all 6 insurer peers joined!" -ForegroundColor Green
}

function Stop-Network {
    Write-Host ">>> Stopping Hyperledger Fabric network..." -ForegroundColor Yellow
    docker-compose -f docker-compose.yaml down --volumes --remove-orphans
    Write-Host ">>> Network stopped." -ForegroundColor Green
}

function Show-Status {
    Write-Host "=== Fabric Network Container Status ===" -ForegroundColor Cyan
    docker ps --filter "network=insurance_net" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

switch ($Action) {
    "generate"      { Generate-Artifacts }
    "up"            { Start-Network }
    "createChannel" { Create-And-Join-Channel }
    "down"          { Stop-Network }
    "restart"       { Stop-Network; Start-Network; Create-And-Join-Channel }
    "status"        { Show-Status }
    "clean"         { Stop-Network; if (Test-Path "crypto-config") { Remove-Item -Recurse -Force "crypto-config" }; if (Test-Path "channel-artifacts") { Remove-Item -Recurse -Force "channel-artifacts" } }
    Default         { Show-Status }
}
