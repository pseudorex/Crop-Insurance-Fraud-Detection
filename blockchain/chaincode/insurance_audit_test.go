package main

import (
	"encoding/json"
	"fmt"
	"sort"
	"testing"

	"github.com/hyperledger/fabric-chaincode-go/shim"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
	"github.com/hyperledger/fabric-protos-go/ledger/queryresult"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// MockIterator implements shim.StateQueryIteratorInterface for testing range queries
type MockIterator struct {
	items []*queryresult.KV
	index int
}

func (m *MockIterator) HasNext() bool {
	return m.index < len(m.items)
}

func (m *MockIterator) Next() (*queryresult.KV, error) {
	if !m.HasNext() {
		return nil, fmt.Errorf("no next element")
	}
	item := m.items[m.index]
	m.index++
	return item, nil
}

func (m *MockIterator) Close() error {
	return nil
}

// MockStub implements state operations for ChaincodeStubInterface
type MockStub struct {
	shim.ChaincodeStubInterface
	state map[string][]byte
}

func NewMockStub() *MockStub {
	return &MockStub{
		state: make(map[string][]byte),
	}
}

func (m *MockStub) GetState(key string) ([]byte, error) {
	if val, ok := m.state[key]; ok {
		return val, nil
	}
	return nil, nil
}

func (m *MockStub) PutState(key string, value []byte) error {
	m.state[key] = value
	return nil
}

func (m *MockStub) GetStateByRange(startKey, endKey string) (shim.StateQueryIteratorInterface, error) {
	var keys []string
	for k := range m.state {
		if (startKey == "" || k >= startKey) && (endKey == "" || k <= endKey) {
			keys = append(keys, k)
		}
	}
	sort.Strings(keys)
	var kvs []*queryresult.KV
	for _, k := range keys {
		kvs = append(kvs, &queryresult.KV{
			Key:   k,
			Value: m.state[k],
		})
	}
	return &MockIterator{items: kvs, index: 0}, nil
}

// MockTxContext implements contractapi.TransactionContextInterface
type MockTxContext struct {
	contractapi.TransactionContextInterface
	stub *MockStub
}

func (m *MockTxContext) GetStub() shim.ChaincodeStubInterface {
	return m.stub
}

func TestInitLedger(t *testing.T) {
	contract := new(InsuranceAuditContract)
	stub := NewMockStub()
	ctx := &MockTxContext{stub: stub}

	err := contract.InitLedger(ctx)
	require.NoError(t, err)

	data, err := stub.GetState("MODEL_M0")
	require.NoError(t, err)
	require.NotNil(t, data)

	var m0 GlobalModelRecord
	err = json.Unmarshal(data, &m0)
	require.NoError(t, err)
	assert.Equal(t, "M0", m0.ModelVersion)
	assert.Equal(t, 0, m0.Round)
	assert.NotEmpty(t, m0.ModelHash)
}

func TestRegisterAndVerifyClaim(t *testing.T) {
	contract := new(InsuranceAuditContract)
	stub := NewMockStub()
	ctx := &MockTxContext{stub: stub}

	claimRef := "REF_C1001"
	insurerID := "InsurerA"
	claimHash := "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
	schemaVer := "schema_v1"

	// 1. Validation for empty inputs
	err := contract.RegisterClaim(ctx, "", insurerID, claimHash, schemaVer)
	assert.Error(t, err)
	err = contract.RegisterClaim(ctx, claimRef, insurerID, "", schemaVer)
	assert.Error(t, err)

	// 2. Successful Registration
	err = contract.RegisterClaim(ctx, claimRef, insurerID, claimHash, schemaVer)
	require.NoError(t, err)

	// 3. Duplicate Registration rejection
	err = contract.RegisterClaim(ctx, claimRef, insurerID, claimHash, schemaVer)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "already registered")

	// 4. Verify Claim - Consistent
	status, err := contract.VerifyClaim(ctx, claimRef, claimHash)
	require.NoError(t, err)
	assert.Equal(t, "CONSISTENT", status)

	// 5. Verify Claim - Tampered Hash
	tamperedHash := "0000000000000000000000000000000000000000"
	status, err = contract.VerifyClaim(ctx, claimRef, tamperedHash)
	require.NoError(t, err)
	assert.Equal(t, "MISMATCH_POSSIBLE_TAMPERING", status)

	// 6. Verify Claim - Non-existent
	status, err = contract.VerifyClaim(ctx, "NON_EXISTENT", claimHash)
	require.NoError(t, err)
	assert.Equal(t, "NOT_FOUND", status)

	// 7. GetClaim
	claim, err := contract.GetClaim(ctx, claimRef)
	require.NoError(t, err)
	assert.Equal(t, claimRef, claim.ClaimRef)
	assert.Equal(t, insurerID, claim.InsurerID)
}

func TestFLUpdateAndAnomalyCommitments(t *testing.T) {
	contract := new(InsuranceAuditContract)
	stub := NewMockStub()
	ctx := &MockTxContext{stub: stub}

	// 1. Register FL Update
	err := contract.RegisterModelUpdate(ctx, 1, "InsurerA", "M1", "update_hash_round_1")
	require.NoError(t, err)

	// Empty parameters validation
	err = contract.RegisterModelUpdate(ctx, 1, "", "M1", "hash")
	assert.Error(t, err)

	// 2. Flag Anomalous Update
	err = contract.FlagAnomalousUpdate(ctx, 6, "INSURER_6_HASH_REF", "BYZANTINE_NORM_OUTLIER", "poisoned_update_hash")
	require.NoError(t, err)

	anomalyBytes, err := stub.GetState("ANOMALY_6_INSURER_6_HASH_REF")
	require.NoError(t, err)
	var anomaly AnomalyFlag
	err = json.Unmarshal(anomalyBytes, &anomaly)
	require.NoError(t, err)
	assert.Equal(t, 6, anomaly.Round)
	assert.Equal(t, "BYZANTINE_NORM_OUTLIER", anomaly.ReasonCode)
	assert.Equal(t, "poisoned_update_hash", anomaly.UpdateHash)
}

func TestModelLineageAndVerification(t *testing.T) {
	contract := new(InsuranceAuditContract)
	stub := NewMockStub()
	ctx := &MockTxContext{stub: stub}

	modelVer := "M10"
	modelHash := "b45cffe084dd3d20d928bee85e7b0f21"

	// 1. Register Global Model
	err := contract.RegisterGlobalModel(ctx, modelVer, modelHash, 10)
	require.NoError(t, err)

	// Empty validation
	err = contract.RegisterGlobalModel(ctx, "", modelHash, 10)
	assert.Error(t, err)

	// 2. Verify Model - Consistent
	status, err := contract.VerifyModel(ctx, modelVer, modelHash)
	require.NoError(t, err)
	assert.Equal(t, "CONSISTENT", status)

	// 3. Verify Model - Mismatch
	status, err = contract.VerifyModel(ctx, modelVer, "wrong_hash")
	require.NoError(t, err)
	assert.Equal(t, "MISMATCH", status)

	// 4. Verify Model - Not Found
	status, err = contract.VerifyModel(ctx, "M99", modelHash)
	require.NoError(t, err)
	assert.Equal(t, "NOT_FOUND", status)

	// 5. Get Model History
	_ = contract.RegisterGlobalModel(ctx, "M1", "hash_m1", 1)
	_ = contract.RegisterGlobalModel(ctx, "M2", "hash_m2", 2)

	history, err := contract.GetModelHistory(ctx)
	require.NoError(t, err)
	assert.GreaterOrEqual(t, len(history), 3)
}

func TestClaimAuditTrail(t *testing.T) {
	contract := new(InsuranceAuditContract)
	stub := NewMockStub()
	ctx := &MockTxContext{stub: stub}

	claimRef := "REF_C2002"
	modelVer := "M10"
	claimHash := "c0ffee1234567890abcdef"
	predHash := "pred_hash_89abcdef"
	shapHash := "shap_hash_456789abc"

	// Register Claim
	err := contract.RegisterClaim(ctx, claimRef, "InsurerB", claimHash, "v1")
	require.NoError(t, err)

	// Register Prediction
	err = contract.RegisterPrediction(ctx, claimRef, modelVer, predHash, "HIGH")
	require.NoError(t, err)

	// Register Explanation (SHAP)
	err = contract.RegisterExplanation(ctx, claimRef, modelVer, shapHash)
	require.NoError(t, err)

	// Verify Explanation
	status, err := contract.VerifyExplanation(ctx, claimRef, shapHash)
	require.NoError(t, err)
	assert.Equal(t, "CONSISTENT", status)

	status, err = contract.VerifyExplanation(ctx, claimRef, "tampered_shap")
	require.NoError(t, err)
	assert.Equal(t, "MISMATCH_POSSIBLE_TAMPERING", status)

	status, err = contract.VerifyExplanation(ctx, "NON_EXISTENT", shapHash)
	require.NoError(t, err)
	assert.Equal(t, "NOT_FOUND", status)

	// Get full Claim Audit Trail
	trail, err := contract.GetClaimAuditTrail(ctx, claimRef)
	require.NoError(t, err)
	require.NotNil(t, trail.Claim)
	require.NotNil(t, trail.Prediction)
	require.NotNil(t, trail.Explanation)

	assert.Equal(t, claimRef, trail.Claim.ClaimRef)
	assert.Equal(t, "HIGH", trail.Prediction.RiskBucket)
	assert.Equal(t, shapHash, trail.Explanation.SHAPHash)
}
