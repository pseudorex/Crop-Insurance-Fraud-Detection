// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title InsuranceAudit
 * @dev Ethereum / EVM compatible Smart Contract for Federated Crop Insurance Fraud Detection
 *      Provides decentralized, tamper-evident audit logging for claims, FL rounds, anomalies, and SHAP explanations.
 */
contract InsuranceAudit {

    // --- State Structures ---

    struct ClaimCommitment {
        string claimId;
        string insurerId;
        bytes32 claimHash;
        uint256 timestamp;
        bool exists;
    }

    struct FLRoundCommitment {
        uint256 roundNumber;
        bytes32 globalModelHash;
        string[] participants;
        bytes32[] updateHashes;
        uint256 timestamp;
        bool exists;
    }

    struct AnomalyRecord {
        uint256 anomalyId;
        uint256 roundNumber;
        string insurerId;
        string attackType;
        bytes32 updateHash;
        uint256 timestamp;
    }

    struct PredictionCommitment {
        string claimId;
        string modelVersion;
        bytes32 predictionHash;
        bytes32 shapHash;
        uint256 timestamp;
        bool exists;
    }

    // --- State Mappings & Arrays ---

    address public owner;
    
    // claimId => ClaimCommitment
    mapping(string => ClaimCommitment) private claims;
    
    // roundNumber => FLRoundCommitment
    mapping(uint256 => FLRoundCommitment) private flRounds;
    
    // claimId => PredictionCommitment
    mapping(string => PredictionCommitment) private predictions;
    
    // Anomaly logs
    AnomalyRecord[] private anomalies;

    // --- Events ---

    event ClaimRegistered(string indexed claimId, string indexed insurerId, bytes32 claimHash, uint256 timestamp);
    event FLRoundAnchored(uint256 indexed roundNumber, bytes32 globalModelHash, uint256 timestamp);
    event AnomalyFlagged(uint256 indexed anomalyId, uint256 indexed roundNumber, string insurerId, string attackType);
    event PredictionCommitted(string indexed claimId, string modelVersion, bytes32 predictionHash, bytes32 shapHash);

    // --- Modifiers ---

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can perform this action");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    // =========================================================================
    // 1. Claim Registration & Verification
    // =========================================================================

    /**
     * @notice Anchors a cryptographic commitment (SHA-256 hash) of a claim.
     * @param _claimId Unique claim identifier
     * @param _insurerId Insurer submitting the claim
     * @param _claimHash Cryptographic SHA-256 hash of (raw_claim + salt)
     */
    function registerClaimCommitment(
        string calldata _claimId,
        string calldata _insurerId,
        bytes32 _claimHash
    ) external {
        require(!claims[_claimId].exists, "Claim already registered");
        require(_claimHash != bytes32(0), "Invalid claim hash");

        claims[_claimId] = ClaimCommitment({
            claimId: _claimId,
            insurerId: _insurerId,
            claimHash: _claimHash,
            timestamp: block.timestamp,
            exists: true
        });

        emit ClaimRegistered(_claimId, _insurerId, _claimHash, block.timestamp);
    }

    /**
     * @notice Verifies whether a candidate claim hash matches the on-chain commitment.
     * @param _claimId The claim ID to verify
     * @param _candidateHash Recomputed SHA-256 hash of the claim data + salt
     */
    function verifyClaimIntegrity(
        string calldata _claimId,
        bytes32 _candidateHash
    ) external view returns (bool isValid, uint256 registeredAt) {
        require(claims[_claimId].exists, "Claim not found");
        ClaimCommitment memory c = claims[_claimId];
        isValid = (c.claimHash == _candidateHash);
        registeredAt = c.timestamp;
    }

    function getClaim(string calldata _claimId) external view returns (ClaimCommitment memory) {
        require(claims[_claimId].exists, "Claim not found");
        return claims[_claimId];
    }

    // =========================================================================
    // 2. Federated Learning Model & Round Anchoring
    // =========================================================================

    /**
     * @notice Anchors the aggregated global model hash and participant hashes for an FL round.
     * @param _roundNumber Round sequence number
     * @param _globalModelHash SHA-256 hash of the global XGBoost model weights
     * @param _participants List of participating insurer IDs
     * @param _updateHashes List of update hashes submitted by participants
     */
    function anchorFLRound(
        uint256 _roundNumber,
        bytes32 _globalModelHash,
        string[] calldata _participants,
        bytes32[] calldata _updateHashes
    ) external {
        require(!flRounds[_roundNumber].exists, "FL round already anchored");
        require(_globalModelHash != bytes32(0), "Invalid global model hash");

        flRounds[_roundNumber] = FLRoundCommitment({
            roundNumber: _roundNumber,
            globalModelHash: _globalModelHash,
            participants: _participants,
            updateHashes: _updateHashes,
            timestamp: block.timestamp,
            exists: true
        });

        emit FLRoundAnchored(_roundNumber, _globalModelHash, block.timestamp);
    }

    function getFLRound(uint256 _roundNumber) external view returns (FLRoundCommitment memory) {
        require(flRounds[_roundNumber].exists, "FL round not found");
        return flRounds[_roundNumber];
    }

    // =========================================================================
    // 3. Byzantine Anomaly / Poisoning Flags
    // =========================================================================

    /**
     * @notice Logs a tamper-evident anomaly flag when a poisoned update is detected.
     */
    function recordAnomalyFlag(
        uint256 _roundNumber,
        string calldata _insurerId,
        string calldata _attackType,
        bytes32 _updateHash
    ) external returns (uint256 anomalyId) {
        anomalyId = anomalies.length + 1;
        
        anomalies.push(AnomalyRecord({
            anomalyId: anomalyId,
            roundNumber: _roundNumber,
            insurerId: _insurerId,
            attackType: _attackType,
            updateHash: _updateHash,
            timestamp: block.timestamp
        }));

        emit AnomalyFlagged(anomalyId, _roundNumber, _insurerId, _attackType);
    }

    function getAnomalyCount() external view returns (uint256) {
        return anomalies.length;
    }

    function getAnomaly(uint256 _index) external view returns (AnomalyRecord memory) {
        require(_index < anomalies.length, "Index out of bounds");
        return anomalies[_index];
    }

    // =========================================================================
    // 4. Inference & SHAP Explanation Commitments
    // =========================================================================

    /**
     * @notice Anchors the prediction outcome and local SHAP feature explanation hash.
     */
    function commitPredictionAndSHAP(
        string calldata _claimId,
        string calldata _modelVersion,
        bytes32 _predictionHash,
        bytes32 _shapHash
    ) external {
        require(claims[_claimId].exists, "Associated claim does not exist");

        predictions[_claimId] = PredictionCommitment({
            claimId: _claimId,
            modelVersion: _modelVersion,
            predictionHash: _predictionHash,
            shapHash: _shapHash,
            timestamp: block.timestamp,
            exists: true
        });

        emit PredictionCommitted(_claimId, _modelVersion, _predictionHash, _shapHash);
    }

    function verifyPredictionAndSHAP(
        string calldata _claimId,
        bytes32 _candidatePredictionHash,
        bytes32 _candidateSHAPHash
    ) external view returns (bool isPredValid, bool isSHAPValid) {
        require(predictions[_claimId].exists, "Prediction record not found");
        PredictionCommitment memory p = predictions[_claimId];
        isPredValid = (p.predictionHash == _candidatePredictionHash);
        isSHAPValid = (p.shapHash == _candidateSHAPHash);
    }

    function getPrediction(string calldata _claimId) external view returns (PredictionCommitment memory) {
        require(predictions[_claimId].exists, "Prediction record not found");
        return predictions[_claimId];
    }
}
