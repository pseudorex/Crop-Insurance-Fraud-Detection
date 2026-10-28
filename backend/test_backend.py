"""
Comprehensive Backend Integration Test with Authentication & Tenant Isolation
Tests:
  1. Health check
  2. Insurer authentication (Argon2 hash verification, JWT issuance, 401 & 403 checks)
  3. Low-risk claim intake (anchored on ledger, no SHAP overhead)
  4. High-risk claim intake (anchored on ledger + SHAP explanation anchored)
  5. 4-phase audit on untampered claim (VERIFIED)
  6. Tamper simulation on local DB
  7. Audit on tampered claim (TAMPERED)
  8. Restore claim
  9. Audit after restore (VERIFIED)
  10. High-risk claim audit & selective SHAP verification
  11. SHAP tampering and audit detection
"""

import os
import sys
import uuid
sys.path.insert(0, os.path.abspath("."))
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_full_pipeline():
    print("=" * 65)
    print("RUNNING BACKEND & DATABASE INTEGRATION TEST WITH PROPER AUTH")
    print("=" * 65)

    # 1. Health check
    h = client.get("/health")
    assert h.status_code == 200
    print(f"[1] Health Check: {h.json()['status']} | DB Mode: {h.json()['database_mode']}")

    # 2. Authentication & Multi-Tenant Access Control Tests
    print("\n--- Testing Insurer Authentication & Password Hashing ---")

    # 2a. Reject wrong password
    bad_login = client.post("/auth/login", json={"username": "insurer1", "password": "WrongPassword!"})
    assert bad_login.status_code == 401
    print("[2a] Rejected invalid password credentials (HTTP 401)")

    # 2b. Successful login with Argon2 verified hash
    good_login = client.post("/auth/login", json={"username": "insurer1", "password": "InsurerPass2026!"})
    assert good_login.status_code == 200, good_login.text
    login_data = good_login.json()
    token1 = login_data["access_token"]
    user1 = login_data["user"]
    headers1 = {"Authorization": f"Bearer {token1}"}
    print(f"[2b] Insurer Adjuster Authenticated: {user1['insurer_name']} ({user1['username']}) | Token Issued")

    # 2b-2. Authenticate admin for audit operations
    adm_login = client.post("/auth/login", json={"username": "admin1", "password": "AdminPass123!"})
    assert adm_login.status_code == 200, adm_login.text
    headers_admin = {"Authorization": f"Bearer {adm_login.json()['access_token']}"}
    print(f"[2b-2] Insurer Admin Authenticated: admin1 | Admin Token Issued")

    # 2b-3. Authenticate Adjuster3, Admin3, and Auditor1 for RBAC & Scope checks
    r_adj3 = client.post("/auth/login", json={"username": "adjuster3", "password": "AdjusterPass123!"})
    assert r_adj3.status_code == 200
    headers_adj3 = {"Authorization": f"Bearer {r_adj3.json()['access_token']}"}

    r_adm3 = client.post("/auth/login", json={"username": "admin3", "password": "AdminPass123!"})
    assert r_adm3.status_code == 200
    headers_adm3 = {"Authorization": f"Bearer {r_adm3.json()['access_token']}"}

    r_aud = client.post("/auth/login", json={"username": "auditor1", "password": "AuditorPass123!"})
    assert r_aud.status_code == 200
    headers_aud = {"Authorization": f"Bearer {r_aud.json()['access_token']}"}
    print("[2b-3] Seed Roles Authenticated: Adjuster3, Admin3, Auditor1")

    # 2c. Unauthenticated request rejected
    unauth_req = client.get("/insurers/insurer1/claims")
    assert unauth_req.status_code == 401
    print("[2c] Unauthenticated request rejected (HTTP 401)")

    # 2d. Cross-tenant isolation & Role-based submission enforcement
    cross_tenant = client.get("/insurers/insurer2/claims", headers=headers1)
    assert cross_tenant.status_code == 403
    print("[2d-1] Cross-tenant unauthorized access blocked (HTTP 403)")

    dummy_claim = {
        "farmer_id": "FARMER-TEST",
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
        "claim_ref": "CLM-FORBIDDEN-TEST"
    }

    # Adjuster3 attempting to submit for insurer2 -> 403
    cross_sub = client.post("/insurers/insurer2/claims", json=dummy_claim, headers=headers_adj3)
    assert cross_sub.status_code == 403
    print("[2d-2] Adjuster3 cross-tenant submission for insurer2 blocked (HTTP 403)")

    # Admin3 attempting to submit claim -> 403
    adm_sub = client.post("/insurers/insurer3/claims", json=dummy_claim, headers=headers_adm3)
    assert adm_sub.status_code == 403
    print("[2d-3] Admin3 submission attempt blocked (HTTP 403: only adjusters submit)")

    # Auditor attempting to submit claim -> 403
    aud_sub = client.post("/insurers/insurer3/claims", json=dummy_claim, headers=headers_aud)
    assert aud_sub.status_code == 403
    print("[2d-4] Auditor1 submission attempt blocked (HTTP 403: auditor is read-only)")

    uid = uuid.uuid4().hex[:6].upper()
    ref_low = f"CLM-AUTO-LOW-{uid}"
    ref_high = f"CLM-AUTO-HIGH-{uid}"

    # 3. Intake low-risk claim with valid auth
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
    r1 = client.post("/insurers/insurer1/claims", json=claim_low, headers=headers1)
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert d1["risk_label"] == "LOW", f"Expected LOW risk, got {d1['risk_label']}"
    assert d1.get("explanation") is None, "Low-risk claim should not produce SHAP overhead"
    print(f"[3] Intake Low-Risk Claim: {d1['claim_ref']} | Risk: {d1['risk_label']} (No SHAP) | On-Chain Tx: {d1['claim_tx_id']}")

    # 4. Intake high-risk claim with valid auth
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
    r2 = client.post("/insurers/insurer1/claims", json=claim_high, headers=headers1)
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    has_shap = d2.get("explanation") is not None
    print(f"[4] Intake High-Risk Claim: {d2['claim_ref']} | Risk: {d2['risk_label']} | SHAP Generated & Anchored: {has_shap}")

    # 5a. Verify adjuster is blocked from running audits (HTTP 403)
    a_blocked = client.post(f"/insurers/insurer1/claims/{ref_low}/audit", headers=headers1)
    assert a_blocked.status_code == 403, f"Expected 403, got {a_blocked.status_code}"
    print(f"[5a] Adjuster audit attempt correctly blocked (HTTP 403: separation of duties)")

    # 5b. Audit clean claim with Admin credentials (HTTP 200)
    a1 = client.post(f"/insurers/insurer1/claims/{ref_low}/audit", headers=headers_admin)
    assert a1.status_code == 200
    res1 = a1.json()
    print(f"[5b] Admin Initial Audit Check: {res1['overall_status']} (Expected: VERIFIED)")
    assert res1["overall_status"] == "VERIFIED"

    # 6. Tamper claim (simulating attacker using compromised adjuster credentials)
    t = client.post(f"/demo/tamper/claim/{ref_low}", json={"insurer_id": "insurer1", "new_indemnity": 95000.0}, headers=headers1)
    assert t.status_code == 200
    print(f"[6] Malicious Database Edit Injected: Changed net_indemnity to $95,000.00")

    # 7. Audit tampered claim with Admin credentials
    a2 = client.post(f"/insurers/insurer1/claims/{ref_low}/audit", headers=headers_admin)
    assert a2.status_code == 200
    res2 = a2.json()
    claim_check = res2["checks"]["claim_integrity"]["status"]
    print(f"[7] Post-Tamper Audit Check: {res2['overall_status']} | Claim Check: {claim_check} (Expected: TAMPERED)")
    assert res2["overall_status"] == "TAMPERED"

    # 8. Restore claim
    rst = client.post(f"/demo/restore/{ref_low}?insurer_id=insurer1", headers=headers_admin)
    assert rst.status_code == 200
    print(f"[8] Database Restored to Original Value")

    # 9. Audit restored claim with Admin credentials
    a3 = client.post(f"/insurers/insurer1/claims/{ref_low}/audit", headers=headers_admin)
    assert a3.status_code == 200
    res3 = a3.json()
    print(f"[9] Post-Restore Audit Check: {res3['overall_status']} (Expected: VERIFIED)")
    assert res3["overall_status"] == "VERIFIED"

    # 10. Verify HIGH claim with SHAP explanation
    a_high = client.post(f"/insurers/insurer1/claims/{ref_high}/audit", headers=headers_admin)
    assert a_high.status_code == 200
    res_h = a_high.json()
    shap_st = res_h["checks"]["explanation_integrity"]["status"]
    print(f"[10] High-Risk Claim Audit: {res_h['overall_status']} | SHAP Integrity: {shap_st} (Expected: VERIFIED)")
    assert shap_st == "VERIFIED"

    # 11. Tamper SHAP explanation
    t_shap = client.post(f"/demo/tamper/explanation/{ref_high}", json={
        "insurer_id": "insurer1",
        "feature_name": "indemnity_to_liability_ratio",
        "new_value": 0.999
    }, headers=headers1)
    assert t_shap.status_code == 200
    print(f"[11] Malicious SHAP Edit Injected: Modified feature contribution value")

    # 12. Audit tampered SHAP explanation
    a_t_high = client.post(f"/insurers/insurer1/claims/{ref_high}/audit", headers=headers_admin)
    assert a_t_high.status_code == 200
    res_th = a_t_high.json()
    tampered_shap_st = res_th["checks"]["explanation_integrity"]["status"]
    print(f"[12] Post-SHAP-Tamper Audit: {res_th['overall_status']} | SHAP Check: {tampered_shap_st} (Expected: TAMPERED)")
    assert tampered_shap_st == "TAMPERED"

    # 13. Verify Audit Log hash chain
    v_log = client.get("/insurers/insurer1/audit-log/verify", headers=headers_admin)
    assert v_log.status_code == 200
    assert v_log.json()["valid"] is True
    print(f"[13] Append-Only Audit Log Hash Chain Verified: Status = {v_log.json()['status']}")

    print("=" * 65)
    print("ALL INTEGRATION TESTS (INCLUDING AUTH & ISOLATION) PASSED!")
    print("=" * 65)


if __name__ == "__main__":
    test_full_pipeline()
