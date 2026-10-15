// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title InsuranceAudit
 * @dev EVM-compatible smart contract for Federated Crop Insurance Fraud Detection.
 *      Provides tamper-evident audit logging for claims, SHAP explanations, and FL model rounds.
 *
 *      Design principles:
 *        - Only SHA-256 hashes and references go on-chain, never raw data.
 *        - All write operations are write-once (no overwriting existing keys).
 *        - SHAP explanations are anchored only for HIGH-risk (fraud-flagged) claims.
 */
contract InsuranceAudit {

    // =========================================================================
    // State Structures
    // =========================================================================

    struct ClaimCommitment {
        string  claimId;
        string  insurerId;
        bytes32 claimHash;      // SHA-256 of the canonical claim JSON (includes UUID claim_id)
        string  modelVersion;   // FL model version used for inference
        string  riskLabel;      // "HIGH" or "LOW"
        bytes32 shapHash;       // SHA-256 of SHAP canonical JSON — zero for LOW-risk claims
        uint256 timestamp;
        bool    exists;
    }

    struct FLRoundCommitment {
        uint256 roundNumber;
        string  modelVersion;
        bytes32 globalModelHash;  // SHA-256 of the model file bytes
        uint256 timestamp;
        bool    exists;
    }

    // =========================================================================
    // State Variables
    // =========================================================================

    address public owner;

    // claimId => ClaimCommitment
    mapping(string => ClaimCommitment) private claims;

    // modelVersion => FLRoundCommitment
    mapping(string => FLRoundCommitment) private models;

    // =========================================================================
    // Events
    // =========================================================================

    event ClaimRegistered(
        string indexed claimId,
        string indexed insurerId,
        bytes32 claimHash,
        string  riskLabel,
        uint256 timestamp
    );

    event SHAPAnchored(
        string indexed claimId,
        bytes32 shapHash,
        uint256 timestamp
    );

    event ModelAnchored(
        string  indexed modelVersion,
        bytes32 globalModelHash,
        uint256 roundNumber,
        uint256 timestamp
    );

    // =========================================================================
    // Modifiers
    // =========================================================================

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
     * @notice Anchors a cryptographic commitment of a claim.
     *         Write-once: reverts if the claimId already exists.
     * @param _claimId      Unique claim reference (UUID-based)
     * @param _insurerId    Insurer submitting the claim
     * @param _claimHash    SHA-256 of canonical claim JSON
     * @param _modelVersion FL model version used for this prediction
     * @param _riskLabel    "HIGH" or "LOW"
     */
    function registerClaim(
        string  calldata _claimId,
        string  calldata _insurerId,
        bytes32          _claimHash,
        string  calldata _modelVersion,
        string  calldata _riskLabel
    ) external {
        require(!claims[_claimId].exists, "Claim already registered");
        require(_claimHash != bytes32(0),  "Invalid claim hash");

        claims[_claimId] = ClaimCommitment({
            claimId:      _claimId,
            insurerId:    _insurerId,
            claimHash:    _claimHash,
            modelVersion: _modelVersion,
            riskLabel:    _riskLabel,
            shapHash:     bytes32(0),
            timestamp:    block.timestamp,
            exists:       true
        });

        emit ClaimRegistered(_claimId, _insurerId, _claimHash, _riskLabel, block.timestamp);
    }

    /**
     * @notice Anchors the SHAP explanation hash for a HIGH-risk claim.
     *         Write-once: reverts if SHAP was already anchored.
     *         Reverts if the claim is not HIGH-risk.
     * @param _claimId   Claim to attach the explanation to
     * @param _shapHash  SHA-256 of canonical SHAP JSON (includes claimId + modelVersion)
     */
    function anchorSHAP(
        string  calldata _claimId,
        bytes32          _shapHash
    ) external {
        require(claims[_claimId].exists,           "Claim not found");
        require(claims[_claimId].shapHash == bytes32(0), "SHAP already anchored");
        require(_shapHash != bytes32(0),           "Invalid SHAP hash");

        // Only HIGH-risk claims get SHAP explanations
        require(
            keccak256(bytes(claims[_claimId].riskLabel)) == keccak256(bytes("HIGH")),
            "SHAP only allowed for HIGH-risk claims"
        );

        claims[_claimId].shapHash = _shapHash;

        emit SHAPAnchored(_claimId, _shapHash, block.timestamp);
    }

    /**
     * @notice Verifies a candidate claim hash against the on-chain commitment.
     * @return isValid      true if the hash matches
     * @return registeredAt block.timestamp at registration
     */
    function verifyClaim(
        string  calldata _claimId,
        bytes32          _candidateHash
    ) external view returns (bool isValid, uint256 registeredAt) {
        require(claims[_claimId].exists, "Claim not found");
        ClaimCommitment memory c = claims[_claimId];
        isValid      = (c.claimHash == _candidateHash);
        registeredAt = c.timestamp;
    }

    /**
     * @notice Verifies the SHAP hash for a HIGH-risk claim.
     * @return isValid true if the hash matches
     */
    function verifySHAP(
        string  calldata _claimId,
        bytes32          _candidateSHAPHash
    ) external view returns (bool isValid) {
        require(claims[_claimId].exists,           "Claim not found");
        require(claims[_claimId].shapHash != bytes32(0), "No SHAP anchored for this claim");
        isValid = (claims[_claimId].shapHash == _candidateSHAPHash);
    }

    /**
     * @notice Returns the full claim record.
     */
    function getClaim(string calldata _claimId) external view returns (ClaimCommitment memory) {
        require(claims[_claimId].exists, "Claim not found");
        return claims[_claimId];
    }

    // =========================================================================
    // 2. Federated Learning Model Anchoring
    // =========================================================================

    /**
     * @notice Anchors the SHA-256 hash of a global FL model.
     *         Write-once: reverts if the modelVersion already exists.
     * @param _modelVersion   Version string, e.g. "M1"
     * @param _globalModelHash SHA-256 of the model file bytes
     * @param _roundNumber    FL round that produced this model
     */
    function anchorModel(
        string  calldata _modelVersion,
        bytes32          _globalModelHash,
        uint256          _roundNumber
    ) external {
        require(!models[_modelVersion].exists,       "Model version already anchored");
        require(_globalModelHash != bytes32(0),      "Invalid model hash");

        models[_modelVersion] = FLRoundCommitment({
            roundNumber:     _roundNumber,
            modelVersion:    _modelVersion,
            globalModelHash: _globalModelHash,
            timestamp:       block.timestamp,
            exists:          true
        });

        emit ModelAnchored(_modelVersion, _globalModelHash, _roundNumber, block.timestamp);
    }

    /**
     * @notice Verifies a candidate model hash against the on-chain commitment.
     * @return isValid      true if the hash matches
     * @return registeredAt block.timestamp at anchoring
     */
    function verifyModel(
        string  calldata _modelVersion,
        bytes32          _candidateHash
    ) external view returns (bool isValid, uint256 registeredAt) {
        require(models[_modelVersion].exists, "Model version not found");
        FLRoundCommitment memory m = models[_modelVersion];
        isValid      = (m.globalModelHash == _candidateHash);
        registeredAt = m.timestamp;
    }

    /**
     * @notice Returns the full model record.
     */
    function getModel(string calldata _modelVersion) external view returns (FLRoundCommitment memory) {
        require(models[_modelVersion].exists, "Model version not found");
        return models[_modelVersion];
    }
}
