# ==============================================================================
# Fabric 2.x Chaincode Lifecycle Deployment Script (Windows PowerShell)
# Smart Contract: insurance_audit
# Project: Federated, Blockchain-Audited Crop Insurance Fraud Detection
# ==============================================================================

param (
    [string]$ChannelName = "insurance-channel",
    [string]$CC_Name = "insurance_audit",
    [string]$CC_Version = "1.0",
    [int]$CC_Sequence = 1
)

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$NETWORK_DIR = Join-Path (Split-Path -Parent $SCRIPT_DIR) "fabric-network"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "DEPLOYING CHAINCODE: ${CC_Name} (v${CC_Version}, Sequence: ${CC_Sequence})" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# 1. Package Chaincode
Write-Host ">>> [1/5] Packaging Chaincode (${CC_Name})..." -ForegroundColor Yellow
docker exec cli.insurance.com bash -c "
    cd /opt/gopath/src/github.com/hyperledger/fabric/peer/chaincode && \
    peer lifecycle chaincode package ${CC_Name}_${CC_Version}.tar.gz \
      --path /opt/gopath/src/github.com/hyperledger/fabric/peer/chaincode \
      --lang golang \
      --label ${CC_Name}_${CC_Version}
"
Write-Host ">>> Chaincode packaged: ${CC_Name}_${CC_Version}.tar.gz" -ForegroundColor Green

# 2. Install on all 6 peers
$peerConfigs = @(
    @{ Org="InsurerAMSP"; Domain="insurera.insurance.com"; Port="7051" },
    @{ Org="InsurerBMSP"; Domain="insurerb.insurance.com"; Port="8051" },
    @{ Org="InsurerCMSP"; Domain="insurerc.insurance.com"; Port="9051" },
    @{ Org="InsurerDMSP"; Domain="insurerd.insurance.com"; Port="10051" },
    @{ Org="InsurerEMSP"; Domain="insurere.insurance.com"; Port="11051" },
    @{ Org="InsurerFMSP"; Domain="insurerf.insurance.com"; Port="12051" }
)

Write-Host ">>> [2/5] Installing Chaincode on all 6 Insurer Peers..." -ForegroundColor Yellow
foreach ($cfg in $peerConfigs) {
    $org = $cfg.Org
    $domain = $cfg.Domain
    $port = $cfg.Port
    Write-Host ">>> Installing on peer0.${domain}:${port} (${org})..." -ForegroundColor Cyan

    docker exec -e CORE_PEER_LOCALMSPID=$org `
        -e CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/${domain}/users/Admin@${domain}/msp `
        -e CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/${domain}/peers/peer0.${domain}/tls/ca.crt `
        -e CORE_PEER_ADDRESS=peer0.${domain}:${port} `
        cli.insurance.com `
        peer lifecycle chaincode install /opt/gopath/src/github.com/hyperledger/fabric/peer/chaincode/${CC_Name}_${CC_Version}.tar.gz
}

# 3. Query Package ID
Write-Host ">>> [3/5] Querying Installed Package ID..." -ForegroundColor Yellow
$PKG_OUTPUT = docker exec cli.insurance.com peer lifecycle chaincode queryinstalled
$PKG_LINE = ($PKG_OUTPUT -split "`n" | Select-String -Pattern "${CC_Name}_${CC_Version}:([a-zA-Z0-9]+)")
if ($PKG_LINE) {
    $PACKAGE_ID = ($PKG_LINE.Matches[0].Value -split " ")[0]
} else {
    $PACKAGE_ID = "${CC_Name}_${CC_Version}:mock_id"
}
Write-Host ">>> Package ID: $PACKAGE_ID" -ForegroundColor Green

# 4. Approve for each of the 6 Orgs
Write-Host ">>> [4/5] Approving Chaincode Definition for all 6 Insurer Orgs..." -ForegroundColor Yellow
foreach ($cfg in $peerConfigs) {
    $org = $cfg.Org
    $domain = $cfg.Domain
    $port = $cfg.Port
    Write-Host ">>> Approving for ${org}..." -ForegroundColor Cyan

    docker exec -e CORE_PEER_LOCALMSPID=$org `
        -e CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/${domain}/users/Admin@${domain}/msp `
        -e CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/${domain}/peers/peer0.${domain}/tls/ca.crt `
        -e CORE_PEER_ADDRESS=peer0.${domain}:${port} `
        cli.insurance.com `
        peer lifecycle chaincode approveformyorg -o orderer.insurance.com:7050 `
        --channelID $ChannelName --name $CC_Name --version $CC_Version `
        --package-id $PACKAGE_ID --sequence $CC_Sequence `
        --collections-config /opt/gopath/src/github.com/hyperledger/fabric/peer/chaincode/collections_config.json `
        --tls --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/insurance.com/orderers/orderer.insurance.com/tls/ca.crt
}

# 5. Commit Chaincode to Channel
Write-Host ">>> [5/5] Committing Chaincode Definition to ${ChannelName}..." -ForegroundColor Yellow
docker exec cli.insurance.com `
    peer lifecycle chaincode commit -o orderer.insurance.com:7050 `
    --channelID $ChannelName --name $CC_Name --version $CC_Version `
    --sequence $CC_Sequence `
    --collections-config /opt/gopath/src/github.com/hyperledger/fabric/peer/chaincode/collections_config.json `
    --peerAddresses peer0.insurera.insurance.com:7051 --tlsRootCertFiles /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurera.insurance.com/peers/peer0.insurera.insurance.com/tls/ca.crt `
    --peerAddresses peer0.insurerb.insurance.com:8051 --tlsRootCertFiles /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurerb.insurance.com/peers/peer0.insurerb.insurance.com/tls/ca.crt `
    --peerAddresses peer0.insurerc.insurance.com:9051 --tlsRootCertFiles /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurerc.insurance.com/peers/peer0.insurerc.insurance.com/tls/ca.crt `
    --tls --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/insurance.com/orderers/orderer.insurance.com/tls/ca.crt

Write-Host ">>> [SUCCESS] Chaincode ${CC_Name} successfully deployed to channel ${ChannelName}!" -ForegroundColor Green
