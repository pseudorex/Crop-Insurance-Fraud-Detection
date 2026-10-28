"""
Role-Based Access Control (RBAC) & Tamper Detection Suite
Verifies:
1. Adjuster3 can submit a claim for insurer3; gets 403 submitting for insurer2.
2. Adjuster3 gets 403 on audit endpoints.
3. Admin3 can audit insurer3 claims; gets 403 on insurer2.
4. Auditor can audit insurer1..6; gets 403 on submit claim.
5. Full flow: adjuster submits -> tamper -> admin3 audit = TAMPERED -> auditor audit = TAMPERED -> restore -> VERIFIED.
6. Audit log hash chain verifies and contains entries for each step.
"""

import os
import sys
import uuid
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app import app
from backend import db

client = TestClient(app)

def test_rbac_suite():
    print("=" * 70)
    print("RUNNING RBAC & AUDIT LOG INTEGRATION TEST SUITE")
    print("=" * 70)

    # 1. Log in users
    print("\n--- 1. Authenticating Seed Users ---")
    
    # Adjuster 3 (insurer3)
    r_adj3 = client.post("/auth/login", json={"username": "adjuster3", "password": "AdjusterPass123!"})
    assert r_adj3.status_code == 200, r_adj3.text
    d_adj3 = r_adj3.json()
    token_adj3 = d_adj3["access_token"]
    headers_adj3 = {"Authorization": f"Bearer {token_adj3}"}
    print(f"[+] Adjuster3 Authenticated: role={d_adj3['role']}, insurer={d_adj3['insurer_id']}")

    # Admin 3 (insurer3)
    r_adm3 = client.post("/auth/login", json={"username": "admin3", "password": "AdminPass123!"})
    assert r_adm3.status_code == 200, r_adm3.text
    d_adm3 = r_adm3.json()
    token_adm3 = d_adm3["access_token"]
    headers_adm3 = {"Authorization": f"Bearer {token_adm3}"}
    print(f"[+] Admin3 Authenticated: role={d_adm3['role']}, insurer={d_adm3['insurer_id']}")

    # Auditor 1 (consortium-wide, ALL)
    r_aud = client.post("/auth/login", json={"username": "auditor1", "password": "AuditorPass123!"})
    assert r_aud.status_code == 200, r_aud.text
    d_aud = r_aud.json()
    token_aud = d_aud["access_token"]
    headers_aud = {"Authorization": f"Bearer {token_aud}"}
    print(f"[+] Auditor1 Authenticated: role={d_aud['role']}, insurer={d_aud['insurer_id']}")

    # 2. Test Scope & Submission Permissions
    print("\n--- 2. Testing Intake Permissions ---")
    claim_ref = f"CLM-INS3-RBAC-{uuid.uuid4().hex[:6].upper()}"
    claim_payload = {
        "farmer_id": "FARMER-RBAC-01",
        "state_code": "17",
        "county_code": "019",
        "commodity_code": 11,
        "cause_of_loss_code": 1,
        "commodity_year": 2026,
        "month_of_loss": 8,
        "net_determined_acres": 0.0,
        "net_planted_acres": 50.0,
        "liability_amount": 35000.0,
        "total_premium": 2800.0,
        "net_indemnity": 1200.0,
        "determined_yield": 42.0,
        "claim_ref": claim_ref
    }

    # 2a. Adjuster3 submits for insurer3 -> 200 SUCCESS
    sub_ok = client.post("/insurers/insurer3/claims", json=claim_payload, headers=headers_adj3)
    assert sub_ok.status_code == 200, sub_ok.text
    print(f"[+] 2a. Adjuster3 successfully submitted claim '{claim_ref}' for insurer3 (HTTP 200)")

    # 2b. Adjuster3 attempts to submit for insurer2 -> 403 FORBIDDEN
    claim_payload_cross = dict(claim_payload, claim_ref=f"CLM-CROSS-{uuid.uuid4().hex[:6]}")
    sub_cross = client.post("/insurers/insurer2/claims", json=claim_payload_cross, headers=headers_adj3)
    assert sub_cross.status_code == 403, f"Expected 403, got {sub_cross.status_code}: {sub_cross.text}"
    print(f"[+] 2b. Adjuster3 cross-tenant submission for insurer2 correctly blocked (HTTP 403)")

    # 2c. Admin3 attempts to submit claim -> 403 FORBIDDEN (only adjusters submit claims)
    sub_admin = client.post("/insurers/insurer3/claims", json=claim_payload_cross, headers=headers_adm3)
    assert sub_admin.status_code == 403, f"Expected 403, got {sub_admin.status_code}: {sub_admin.text}"
    print(f"[+] 2c. Admin3 submission correctly blocked (HTTP 403: only adjusters may submit)")

    # 2d. Auditor attempts to submit claim -> 403 FORBIDDEN (auditor is read-only)
    sub_aud = client.post("/insurers/insurer3/claims", json=claim_payload_cross, headers=headers_aud)
    assert sub_aud.status_code == 403, f"Expected 403, got {sub_aud.status_code}: {sub_aud.text}"
    print(f"[+] 2d. Auditor1 submission correctly blocked (HTTP 403: auditor cannot submit)")

    # 3. Test Audit Permissions
    print("\n--- 3. Testing Audit Permissions ---")

    # 3a. Adjuster3 attempts to run audit on claim -> 403 FORBIDDEN
    aud_adj = client.post(f"/insurers/insurer3/claims/{claim_ref}/audit", headers=headers_adj3)
    assert aud_adj.status_code == 403, f"Expected 403, got {aud_adj.status_code}"
    print(f"[+] 3a. Adjuster3 audit attempt correctly blocked (HTTP 403)")

    # 3b. Admin3 audits insurer3 claim -> 200 VERIFIED
    aud_adm = client.post(f"/insurers/insurer3/claims/{claim_ref}/audit", headers=headers_adm3)
    assert aud_adm.status_code == 200, aud_adm.text
    rep_adm = aud_adm.json()
    assert rep_adm["overall_status"] == "VERIFIED"
    print(f"[+] 3b. Admin3 audited insurer3 claim -> {rep_adm['overall_status']} (HTTP 200)")

    # 3c. Admin3 attempts to audit insurer2 claim -> 403 FORBIDDEN
    aud_adm_cross = client.post(f"/insurers/insurer2/claims/{claim_ref}/audit", headers=headers_adm3)
    assert aud_adm_cross.status_code == 403, f"Expected 403, got {aud_adm_cross.status_code}"
    print(f"[+] 3c. Admin3 cross-tenant audit on insurer2 correctly blocked (HTTP 403)")

    # 3d. Auditor audits insurer3 claim -> 200 VERIFIED
    aud_aud3 = client.post(f"/insurers/insurer3/claims/{claim_ref}/audit", headers=headers_aud)
    assert aud_aud3.status_code == 200, aud_aud3.text
    print(f"[+] 3d. Auditor1 successfully audited insurer3 claim (HTTP 200)")

    # 4. Full Flow: Adjuster submits -> Tamper -> Admin3 audit = TAMPERED -> Auditor audit = TAMPERED -> Restore -> VERIFIED
    print("\n--- 4. Full Story Flow (Intake -> Tamper -> Detect -> Restore) ---")

    # 4a. Attacker simulation: simulate compromised adjuster account tampering with database
    t_res = client.post(
        f"/simulate/tamper/claim/{claim_ref}",
        json={"insurer_id": "insurer3", "new_indemnity": 95000.0},
        headers=headers_adj3
    )
    assert t_res.status_code == 200, t_res.text
    print(f"[+] 4a. Attacker simulation: modified indemnity in insurer3_db to $95,000.00")

    # 4b. Auditor attempts to tamper -> 403 FORBIDDEN (auditor not exposed to tamper endpoint)
    t_aud = client.post(
        f"/simulate/tamper/claim/{claim_ref}",
        json={"insurer_id": "insurer3", "new_indemnity": 95000.0},
        headers=headers_aud
    )
    assert t_aud.status_code == 403, f"Expected 403, got {t_aud.status_code}"
    print(f"[+] 4b. Auditor tamper attempt correctly blocked (HTTP 403: auditor has no write privileges)")

    # 4c. Admin3 runs audit -> TAMPERED
    adm_audit_tampered = client.post(f"/insurers/insurer3/claims/{claim_ref}/audit", headers=headers_adm3)
    assert adm_audit_tampered.status_code == 200
    res_tampered = adm_audit_tampered.json()
    assert res_tampered["overall_status"] == "TAMPERED"
    print(f"[+] 4c. Admin3 audit caught tamper: {res_tampered['overall_status']} (Integrity Check: {res_tampered['checks']['claim_integrity']['status']})")
    assert "last_modified_by" in res_tampered, "Report should include last_modified_by"
    print(f"       Last modified by: {res_tampered['last_modified_by']['username']} ({res_tampered['last_modified_by']['action']})")

    # 4d. Auditor runs audit -> TAMPERED
    aud_audit_tampered = client.post(f"/insurers/insurer3/claims/{claim_ref}/audit", headers=headers_aud)
    assert aud_audit_tampered.status_code == 200
    assert aud_audit_tampered.json()["overall_status"] == "TAMPERED"
    print(f"[+] 4d. Auditor1 audit caught tamper: TAMPERED")

    # 4e. Restore database to legitimate state
    rst_res = client.post(f"/simulate/restore/{claim_ref}?insurer_id=insurer3", headers=headers_adm3)
    assert rst_res.status_code == 200
    print(f"[+] 4e. Restored original claim state in insurer3_db")

    # 4f. Admin3 runs audit after restore -> VERIFIED
    adm_audit_restored = client.post(f"/insurers/insurer3/claims/{claim_ref}/audit", headers=headers_adm3)
    assert adm_audit_restored.status_code == 200
    assert adm_audit_restored.json()["overall_status"] == "VERIFIED"
    print(f"[+] 4f. Admin3 post-restore audit: {adm_audit_restored.json()['overall_status']}")

    # 5. Audit Log Hash Chain Verification
    print("\n--- 5. Verifying Append-Only Audit Log Hash Chain ---")
    
    # 5a. Adjuster3 attempts to access audit log -> 403 FORBIDDEN
    adj_log = client.get("/insurers/insurer3/audit-log", headers=headers_adj3)
    assert adj_log.status_code == 403, f"Expected 403, got {adj_log.status_code}"
    print(f"[+] 5a. Adjuster3 attempt to read audit log correctly blocked (HTTP 403)")

    # 5b. Admin3 accesses audit log -> 200
    adm_log = client.get(f"/insurers/insurer3/audit-log?claim_ref={claim_ref}", headers=headers_adm3)
    assert adm_log.status_code == 200
    entries = adm_log.json()
    actions = [e["action"] for e in entries]
    print(f"[+] 5b. Admin3 retrieved audit log for claim: actions recorded = {actions}")
    assert "CLAIM_SUBMITTED" in actions
    assert "TAMPER_SIMULATED" in actions
    assert "AUDIT_RUN" in actions

    # 5c. Cryptographically verify hash chain via API
    v_res = client.get("/insurers/insurer3/audit-log/verify", headers=headers_adm3)
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["valid"] is True
    print(f"[+] 5c. Cryptographic hash chain verified! Total immutable entries: {v_data['total_entries']} (Status: {v_data['status']})")

    # 6. Optional: Missing records check
    print("\n--- 6. Testing Missing Records Check ---")
    miss_res = client.get("/insurers/insurer3/audit/missing-records", headers=headers_adm3)
    assert miss_res.status_code == 200
    miss_data = miss_res.json()
    print(f"[+] 6. Missing records check executed: status={miss_data['status']} | on-chain={miss_data['total_on_chain']}, local={miss_data['total_in_db']}")

    print("\n" + "=" * 70)
    print("ALL RBAC AND AUDIT TRAIL TESTS PASSED PERFECTLY!")
    print("=" * 70)


if __name__ == "__main__":
    test_rbac_suite()
