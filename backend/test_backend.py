"""
Comprehensive Backend Integration Test
Tests:
  1. Health check
  2. Low-risk claim intake (anchored on ledger, no SHAP overhead)
  3. High-risk claim intake (anchored on ledger + SHAP explanation anchored)
  4. 4-phase audit on untampered claim (VERIFIED)
  5. Tamper simulation on local DB
  6. Audit on tampered claim (TAMPERED)
  7. Restore claim
  8. Audit after restore (VERIFIED)
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_full_pipeline():
    print("=" * 65)
    print("RUNNING BACKEND & DATABASE INTEGRATION TEST")
    print("=" * 65)

    # 1. Health check
    h = client.get("/health")
    assert h.status_code == 200
    print(f"[1] Health Check: {h.json()['status']} | DB Mode: {h.json()['database_mode']}")

    import uuid
    uid = uuid.uuid4().hex[:6].upper()
    ref_low = f"CLM-AUTO-LOW-{uid}"
    ref_high = f"CLM-AUTO-HIGH-{uid}"

    # 2. Intake low-risk claim
    claim_low = {
        "farmer_id": "FARMER-101",
        "state_code": "17",
        "county_code": "019",
        "commodity_code": 11,
        "cause_of_loss_code": 1,
        "commodity_year": 2026,
        "month_of_loss": 8,
        "net_determined_acres": 0.0,
        "net_planted_acres": 40.0,
        "liability_amount": 25000.0,
        "total_premium": 3200.0,
        "net_indemnity": 250.0,
        "determined_yield": 44.0,
        "claim_ref": ref_low
    }
    r1 = client.post("/insurers/insurer1/claims", json=claim_low)
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert d1["risk_label"] == "LOW", f"Expected LOW risk, got {d1['risk_label']}"
    assert d1.get("explanation") is None, "Low-risk claim should not produce SHAP overhead"
    print(f"[2] Intake Low-Risk Claim: {d1['claim_ref']} | Risk: {d1['risk_label']} (No SHAP) | On-Chain Tx: {d1['claim_tx_id']}")

    # 3. Intake high-risk claim
    claim_high = {
        "farmer_id": "FARMER-999",
        "state_code": "17",
        "county_code": "019",
        "commodity_code": 11,
        "cause_of_loss_code": 11,
        "commodity_year": 2026,
        "month_of_loss": 7,
        "net_determined_acres": 120.0,
        "net_planted_acres": 120.0,
        "liability_amount": 65000.0,
        "total_premium": 1500.0,
        "net_indemnity": 62000.0,
        "determined_yield": 5.0,
        "claim_ref": ref_high
    }
    r2 = client.post("/insurers/insurer1/claims", json=claim_high)
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    has_shap = d2.get("explanation") is not None
    print(f"[3] Intake High-Risk Claim: {d2['claim_ref']} | Risk: {d2['risk_label']} | SHAP Generated & Anchored: {has_shap}")

    # 4. Audit clean claim
    a1 = client.post(f"/insurers/insurer1/claims/{ref_low}/audit")
    assert a1.status_code == 200
    res1 = a1.json()
    print(f"[4] Initial Audit Check: {res1['overall_status']} (Expected: VERIFIED)")
    assert res1["overall_status"] == "VERIFIED"

    # 5. Tamper claim
    t = client.post(f"/demo/tamper/claim/{ref_low}", json={"insurer_id": "insurer1", "new_indemnity": 95000.0})
    assert t.status_code == 200
    print(f"[5] Malicious Database Edit Injected: Changed net_indemnity to $95,000.00")

    # 6. Audit tampered claim
    a2 = client.post(f"/insurers/insurer1/claims/{ref_low}/audit")
    assert a2.status_code == 200
    res2 = a2.json()
    claim_check = res2["checks"]["claim_integrity"]["status"]
    print(f"[6] Post-Tamper Audit Check: {res2['overall_status']} | Claim Check: {claim_check} (Expected: TAMPERED)")
    assert res2["overall_status"] == "TAMPERED"

    # 7. Restore claim
    rst = client.post(f"/demo/restore/{ref_low}?insurer_id=insurer1")
    assert rst.status_code == 200
    print(f"[7] Database Restored to Original Value")

    # 8. Audit restored claim
    a3 = client.post(f"/insurers/insurer1/claims/{ref_low}/audit")
    assert a3.status_code == 200
    res3 = a3.json()
    print(f"[8] Post-Restore Audit Check: {res3['overall_status']} (Expected: VERIFIED)")
    assert res3["overall_status"] == "VERIFIED"

    # 9. Verify HIGH claim with SHAP explanation
    a_high = client.post(f"/insurers/insurer1/claims/{ref_high}/audit")
    assert a_high.status_code == 200
    res_h = a_high.json()
    shap_st = res_h["checks"]["explanation_integrity"]["status"]
    print(f"[9] High-Risk Claim Audit: {res_h['overall_status']} | SHAP Integrity: {shap_st} (Expected: VERIFIED)")
    assert shap_st == "VERIFIED"

    # 10. Tamper SHAP explanation
    t_shap = client.post(f"/demo/tamper/explanation/{ref_high}", json={
        "insurer_id": "insurer1",
        "feature_name": "indemnity_to_liability_ratio",
        "new_value": 0.999
    })
    assert t_shap.status_code == 200
    print(f"[10] Malicious SHAP Edit Injected: Modified feature contribution value")

    # 11. Audit tampered SHAP explanation
    a_t_high = client.post(f"/insurers/insurer1/claims/{ref_high}/audit")
    assert a_t_high.status_code == 200
    res_th = a_t_high.json()
    tampered_shap_st = res_th["checks"]["explanation_integrity"]["status"]
    print(f"[11] Post-SHAP-Tamper Audit: {res_th['overall_status']} | SHAP Check: {tampered_shap_st} (Expected: TAMPERED)")
    assert tampered_shap_st == "TAMPERED"

    print("=" * 65)
    print("ALL INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 65)


if __name__ == "__main__":
    test_full_pipeline()
