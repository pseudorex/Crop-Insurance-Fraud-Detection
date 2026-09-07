package main

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// InsuranceAuditContract provides functions for managing crop insurance audit trail and model provenance
type InsuranceAuditContract struct {
	contractapi.Contract
}

// ClaimRecord represents the cryptographic commitment of a submitted claim
type ClaimRecord struct {
	ClaimRef      string `json:"claimRef"`
	InsurerID     string `json:"insurerID"`
	ClaimHash     string `json:"claimHash"`
	Timestamp     string `json:"timestamp"`
	SchemaVersion string `json:"schemaVersion"`
}

// FLUpdateRecord represents the pre-mask update hash of a federated learning client
type FLUpdateRecord struct {
	Round        int    `json:"round"`
	InsurerID    string `json:"insurerID"`
	ModelVersion string `json:"modelVersion"`
	UpdateHash   string `json:"updateHash"`
	Timestamp    string `json:"timestamp"`
}

// AnomalyFlag records evidence of an anomalous/poisoned model update rejected during robust aggregation
type AnomalyFlag struct {
	Round      int    `json:"round"`
	InsurerRef string `json:"insurerRef"`
	ReasonCode string `json:"reasonCode"`
	UpdateHash string `json:"updateHash"`
	Timestamp  string `json:"timestamp"`
}

// GlobalModelRecord represents an aggregated global model version and its SHA-256 hash
type GlobalModelRecord struct {
	ModelVersion string `json:"modelVersion"`
	ModelHash    string `json:"modelHash"`
	Round        int    `json:"round"`
	Timestamp    string `json:"timestamp"`
}

// PredictionRecord represents the prediction commitment anchored for every evaluated claim
type PredictionRecord struct {
	ClaimRef     string `json:"claimRef"`
	ModelVersion string `json:"modelVersion"`
	PredHash     string `json:"predictionHash"`
	RiskBucket   string `json:"riskBucket"`
	Timestamp    string `json:"timestamp"`
}

// ExplanationRecord represents the SHAP explanation hash anchored for suspicious claims
type ExplanationRecord struct {
	ClaimRef     string `json:"claimRef"`
	ModelVersion string `json:"modelVersion"`
	SHAPHash     string `json:"shapHash"`
	Timestamp    string `json:"timestamp"`
}

// ClaimAuditTrail packages all on-chain commitments associated with a single claim
type ClaimAuditTrail struct {
	Claim       *ClaimRecord       `json:"claim,omitempty"`
	Prediction  *PredictionRecord  `json:"prediction,omitempty"`
	Explanation *ExplanationRecord `json:"explanation,omitempty"`
}

// InitLedger initializes the ledger with base model M0
func (c *InsuranceAuditContract) InitLedger(ctx contractapi.TransactionContextInterface) error {
	m0 := GlobalModelRecord{
		ModelVersion: "M0",
		ModelHash:    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", // Central initialization hash
		Round:        0,
		Timestamp:    time.Now().UTC().Format(time.RFC3339),
	}
	data, err := json.Marshal(m0)
	if err != nil {
		return fmt.Errorf("failed to marshal M0 record: %w", err)
	}
	return ctx.GetStub().PutState("MODEL_M0", data)
}

// RegisterClaim anchors a new claim's cryptographic fingerprint on the ledger
func (c *InsuranceAuditContract) RegisterClaim(ctx contractapi.TransactionContextInterface,
	claimRef string, insurerID string, claimHash string, schemaVer string) error {

	if len(claimRef) == 0 || len(claimHash) == 0 {
		return fmt.Errorf("claimRef and claimHash must not be empty")
	}

	exists, err := ctx.GetStub().GetState("CLAIM_" + claimRef)
	if err != nil {
		return fmt.Errorf("failed to read from world state: %w", err)
	}
	if exists != nil {
		return fmt.Errorf("claim reference %s is already registered", claimRef)
	}

	record := ClaimRecord{
		ClaimRef:      claimRef,
		InsurerID:     insurerID,
		ClaimHash:     claimHash,
		Timestamp:     time.Now().UTC().Format(time.RFC3339),
		SchemaVersion: schemaVer,
	}

	data, err := json.Marshal(record)
	if err != nil {
		return fmt.Errorf("failed to marshal claim record: %w", err)
	}

	return ctx.GetStub().PutState("CLAIM_"+claimRef, data)
}

// RegisterModelUpdate stores a pre-mask local FL update hash for a given round
func (c *InsuranceAuditContract) RegisterModelUpdate(ctx contractapi.TransactionContextInterface,
	round int, insurerID string, modelVersion string, updateHash string) error {

	if len(insurerID) == 0 || len(updateHash) == 0 {
		return fmt.Errorf("insurerID and updateHash must not be empty")
	}

	key := fmt.Sprintf("UPDATE_%d_%s", round, insurerID)
	record := FLUpdateRecord{
		Round:        round,
		InsurerID:    insurerID,
		ModelVersion: modelVersion,
		UpdateHash:   updateHash,
		Timestamp:    time.Now().UTC().Format(time.RFC3339),
	}

	data, err := json.Marshal(record)
	if err != nil {
		return fmt.Errorf("failed to marshal update record: %w", err)
	}

	return ctx.GetStub().PutState(key, data)
}

// FlagAnomalousUpdate records evidence of a poisoned update rejected during robust aggregation
func (c *InsuranceAuditContract) FlagAnomalousUpdate(ctx contractapi.TransactionContextInterface,
	round int, insurerRef string, reasonCode string, updateHash string) error {

	key := fmt.Sprintf("ANOMALY_%d_%s", round, insurerRef)
	record := AnomalyFlag{
		Round:      round,
		InsurerRef: insurerRef,
		ReasonCode: reasonCode,
		UpdateHash: updateHash,
		Timestamp:  time.Now().UTC().Format(time.RFC3339),
	}

	data, err := json.Marshal(record)
	if err != nil {
		return fmt.Errorf("failed to marshal anomaly record: %w", err)
	}

	return ctx.GetStub().PutState(key, data)
}

// RegisterGlobalModel anchors a newly aggregated global model version and its SHA-256 hash
func (c *InsuranceAuditContract) RegisterGlobalModel(ctx contractapi.TransactionContextInterface,
	modelVersion string, modelHash string, round int) error {

	if len(modelVersion) == 0 || len(modelHash) == 0 {
		return fmt.Errorf("modelVersion and modelHash must not be empty")
	}

	record := GlobalModelRecord{
		ModelVersion: modelVersion,
		ModelHash:    modelHash,
		Round:        round,
		Timestamp:    time.Now().UTC().Format(time.RFC3339),
	}

	data, err := json.Marshal(record)
	if err != nil {
		return fmt.Errorf("failed to marshal model record: %w", err)
	}

	return ctx.GetStub().PutState("MODEL_"+modelVersion, data)
}

// RegisterPrediction commits a prediction result (mandatory for every intake claim)
func (c *InsuranceAuditContract) RegisterPrediction(ctx contractapi.TransactionContextInterface,
	claimRef string, modelVersion string, predHash string, riskBucket string) error {

	if len(claimRef) == 0 || len(predHash) == 0 {
		return fmt.Errorf("claimRef and predHash must not be empty")
	}

	record := PredictionRecord{
		ClaimRef:     claimRef,
		ModelVersion: modelVersion,
		PredHash:     predHash,
		RiskBucket:   riskBucket,
		Timestamp:    time.Now().UTC().Format(time.RFC3339),
	}

	data, err := json.Marshal(record)
	if err != nil {
		return fmt.Errorf("failed to marshal prediction record: %w", err)
	}

	return ctx.GetStub().PutState("PRED_"+claimRef, data)
}

// RegisterExplanation stores a SHAP explanation hash for a flagged/suspicious claim
func (c *InsuranceAuditContract) RegisterExplanation(ctx contractapi.TransactionContextInterface,
	claimRef string, modelVersion string, shapHash string) error {

	if len(claimRef) == 0 || len(shapHash) == 0 {
		return fmt.Errorf("claimRef and shapHash must not be empty")
	}

	record := ExplanationRecord{
		ClaimRef:     claimRef,
		ModelVersion: modelVersion,
		SHAPHash:     shapHash,
		Timestamp:    time.Now().UTC().Format(time.RFC3339),
	}

	data, err := json.Marshal(record)
	if err != nil {
		return fmt.Errorf("failed to marshal explanation record: %w", err)
	}

	return ctx.GetStub().PutState("SHAP_"+claimRef, data)
}

// VerifyClaim audits a local claim against its on-chain registered commitment
func (c *InsuranceAuditContract) VerifyClaim(ctx contractapi.TransactionContextInterface,
	claimRef string, claimHashToVerify string) (string, error) {

	data, err := ctx.GetStub().GetState("CLAIM_" + claimRef)
	if err != nil {
		return "", fmt.Errorf("failed to read from world state: %w", err)
	}
	if data == nil {
		return "NOT_FOUND", nil
	}

	var record ClaimRecord
	if err := json.Unmarshal(data, &record); err != nil {
		return "", fmt.Errorf("failed to unmarshal claim record: %w", err)
	}

	if record.ClaimHash == claimHashToVerify {
		return "CONSISTENT", nil
	}
	return "MISMATCH_POSSIBLE_TAMPERING", nil
}

// VerifyModel verifies whether a local model artifact matches the committed version hash
func (c *InsuranceAuditContract) VerifyModel(ctx contractapi.TransactionContextInterface,
	modelVersion string, modelHashToVerify string) (string, error) {

	data, err := ctx.GetStub().GetState("MODEL_" + modelVersion)
	if err != nil {
		return "", fmt.Errorf("failed to read from world state: %w", err)
	}
	if data == nil {
		return "NOT_FOUND", nil
	}

	var record GlobalModelRecord
	if err := json.Unmarshal(data, &record); err != nil {
		return "", fmt.Errorf("failed to unmarshal model record: %w", err)
	}

	if record.ModelHash == modelHashToVerify {
		return "CONSISTENT", nil
	}
	return "MISMATCH", nil
}

// VerifyExplanation audits a SHAP explanation hash against the ledger commitment
func (c *InsuranceAuditContract) VerifyExplanation(ctx contractapi.TransactionContextInterface,
	claimRef string, shapHashToVerify string) (string, error) {

	data, err := ctx.GetStub().GetState("SHAP_" + claimRef)
	if err != nil {
		return "", fmt.Errorf("failed to read from world state: %w", err)
	}
	if data == nil {
		return "NOT_FOUND", nil
	}

	var record ExplanationRecord
	if err := json.Unmarshal(data, &record); err != nil {
		return "", fmt.Errorf("failed to unmarshal explanation record: %w", err)
	}

	if record.SHAPHash == shapHashToVerify {
		return "CONSISTENT", nil
	}
	return "MISMATCH_POSSIBLE_TAMPERING", nil
}

// GetClaim retrieves the claim record from ledger
func (c *InsuranceAuditContract) GetClaim(ctx contractapi.TransactionContextInterface, claimRef string) (*ClaimRecord, error) {
	data, err := ctx.GetStub().GetState("CLAIM_" + claimRef)
	if err != nil {
		return nil, fmt.Errorf("failed to read from world state: %w", err)
	}
	if data == nil {
		return nil, fmt.Errorf("claim %s not found", claimRef)
	}

	var record ClaimRecord
	if err := json.Unmarshal(data, &record); err != nil {
		return nil, err
	}
	return &record, nil
}

// GetClaimAuditTrail returns all ledger commitments (Claim + Prediction + SHAP) for a claim
func (c *InsuranceAuditContract) GetClaimAuditTrail(ctx contractapi.TransactionContextInterface, claimRef string) (*ClaimAuditTrail, error) {
	trail := &ClaimAuditTrail{}

	// 1. Claim Commitment
	claimBytes, _ := ctx.GetStub().GetState("CLAIM_" + claimRef)
	if claimBytes != nil {
		var cr ClaimRecord
		_ = json.Unmarshal(claimBytes, &cr)
		trail.Claim = &cr
	}

	// 2. Prediction Commitment
	predBytes, _ := ctx.GetStub().GetState("PRED_" + claimRef)
	if predBytes != nil {
		var pr PredictionRecord
		_ = json.Unmarshal(predBytes, &pr)
		trail.Prediction = &pr
	}

	// 3. SHAP Commitment
	shapBytes, _ := ctx.GetStub().GetState("SHAP_" + claimRef)
	if shapBytes != nil {
		var er ExplanationRecord
		_ = json.Unmarshal(shapBytes, &er)
		trail.Explanation = &er
	}

	return trail, nil
}

// GetModelHistory returns all anchored global model versions
func (c *InsuranceAuditContract) GetModelHistory(ctx contractapi.TransactionContextInterface) ([]*GlobalModelRecord, error) {
	resultsIterator, err := ctx.GetStub().GetStateByRange("MODEL_", "MODEL_\uffff")
	if err != nil {
		return nil, err
	}
	defer resultsIterator.Close()

	var models []*GlobalModelRecord
	for resultsIterator.HasNext() {
		response, err := resultsIterator.Next()
		if err != nil {
			return nil, err
		}
		var record GlobalModelRecord
		if err := json.Unmarshal(response.Value, &record); err == nil {
			models = append(models, &record)
		}
	}
	return models, nil
}

func main() {
	contract := new(InsuranceAuditContract)
	cc, err := contractapi.NewChaincode(contract)
	if err != nil {
		panic(fmt.Sprintf("Error creating insurance_audit chaincode: %v", err))
	}

	if err := cc.Start(); err != nil {
		panic(fmt.Sprintf("Error starting insurance_audit chaincode: %v", err))
	}
}
