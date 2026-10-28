"""
FastAPI Backend Application for Crop Insurance Fraud Detection
Implements:
  - Multi-tenant insurer claim intake with feature engineering and ML inference
  - Immutable smart contract anchoring (Solidity / EVM client)
  - Selective SHAP generation and commitment anchoring for flagged claims
  - 4-phase cryptographic audit and tamper detection
  - Demo tampering endpoints for live presentation
"""

import os
import uuid
import json
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Query, Path, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend import db, hashing, inference, audit, auth
from blockchain.chain_client import InsuranceAuditClient

app = FastAPI(
    title="Crop Insurance Fraud Detection Consortium API",
    description="Federated Differential Privacy ML + Blockchain Audit Ledger API",
    version="2.0.0"
)

@app.on_event("startup")
def startup_event():
    if db.is_postgres_available():
        db.init_auth_db()

# Enable CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chain_client = InsuranceAuditClient()
engine = inference.get_inference_engine()
auditor = audit.AuditorService(chain_client)


# =============================================================================
# Request & Response Models
# =============================================================================

class ClaimInput(BaseModel):
    farmer_id: str = Field(..., examples=["FARMER-88401"])
    state_code: str = Field("17", examples=["17"])
    county_code: str = Field("019", examples=["019"])
    commodity_code: int = Field(11, examples=[11])
    cause_of_loss_code: int = Field(11, examples=[11])
    commodity_year: int = Field(2026, examples=[2026])
    month_of_loss: int = Field(7, examples=[7])
    net_determined_acres: float = Field(120.0, examples=[120.0])
    net_planted_acres: float = Field(120.0, examples=[120.0])
    liability_amount: float = Field(65000.0, examples=[65000.0])
    total_premium: float = Field(4200.0, examples=[4200.0])
    net_indemnity: float = Field(52000.0, examples=[52000.0])
    determined_yield: float = Field(18.5, examples=[18.5])
    claim_ref: Optional[str] = Field(None, examples=["CLM-2026-LIVE-01"])


class TamperClaimInput(BaseModel):
    insurer_id: str = Field(..., examples=["insurer1"])
    new_indemnity: float = Field(..., examples=[95000.0])


class TamperExplanationInput(BaseModel):
    insurer_id: str = Field(..., examples=["insurer1"])
    feature_name: str = Field(..., examples=["indemnity_to_liability_ratio"])
    new_value: float = Field(..., examples=[0.99])


class LoginInput(BaseModel):
    username: str = Field(..., examples=["admin_insurer1"])
    password: str = Field(..., examples=["InsurerPass2026!"])


class RegisterInput(BaseModel):
    insurer_id: Optional[str] = Field("insurer1", examples=["insurer1"])
    username: str = Field(..., examples=["jane_officer"])
    password: str = Field(..., min_length=6, examples=["SecurePass2026!"])
    insurer_name: Optional[str] = Field(None, examples=["Alliance Agri"])
    email: Optional[str] = Field(None, examples=["jane@alliance.com"])
    role: Optional[str] = Field("INSURER_ADMIN", examples=["INSURER_ADMIN"])
    individual_name: Optional[str] = Field(None, examples=["Dr. Aris Thorne"])


# =============================================================================
# Endpoints
# =============================================================================

@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "database_mode": "POSTGRES" if db.is_postgres_available() else "OFFLINE",
        "blockchain_mode": "ON_CHAIN_EVM" if chain_client.is_onchain_active else "SIMULATED_FALLBACK",
        "contract_address": chain_client.contract_address,
        "model_version": engine.model_version
    }


# =============================================================================
# Authentication Endpoints
# =============================================================================

@app.post("/auth/login")
def login(payload: LoginInput):
    """
    Authenticates a consortium user by verifying password against stored hash in PostgreSQL.
    Accepts username, email, or insurer_id (e.g. 'adjuster3', 'admin3', 'auditor1').
    Returns JWT access token with role and insurer claims.
    """
    user = db.get_user_by_identifier(payload.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not auth.verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    db.update_user_last_login(user["id"])
    raw_role = str(user.get("role", "adjuster")).lower()
    if "admin" in raw_role:
        user_role = "admin"
    elif "auditor" in raw_role:
        user_role = "auditor"
    else:
        user_role = "adjuster"
    insurer_id = user.get("insurer_id", "insurer1")

    token = auth.create_access_token({
        "sub": user["username"],
        "user_id": user["id"],
        "insurer_id": insurer_id,
        "insurer_name": user["insurer_name"],
        "role": user_role
    })

    # Log successful login into the insurer's append-only audit log
    target_ins = insurer_id if insurer_id.lower() not in ("all", "individual") else "insurer1"
    try:
        db.append_audit_log(
            insurer_id=target_ins,
            username=user["username"],
            role=user_role,
            action="LOGIN",
            details={"status": "SUCCESS", "client": "consortium_portal"}
        )
    except Exception:
        pass

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user_role,
        "insurer_id": insurer_id,
        "user": {
            "id": user["id"],
            "insurer_id": insurer_id,
            "username": user["username"],
            "insurer_name": user["insurer_name"],
            "email": user.get("email"),
            "role": user_role
        }
    }


@app.post("/auth/register")
def register(payload: RegisterInput):
    """
    Registers a new insurer officer or an independent individual auditor.
    Stores password securely hashed with bcrypt / Argon2id in PostgreSQL.
    """
    existing = db.get_user_by_identifier(payload.username)
    if existing and existing["username"].lower() == payload.username.strip().lower():
        raise HTTPException(status_code=400, detail=f"Username '{payload.username}' is already registered.")

    raw_role = (payload.role or "admin").strip().lower()
    if "admin" in raw_role:
        normalized_role = "admin"
    elif "auditor" in raw_role:
        normalized_role = "auditor"
    else:
        normalized_role = "adjuster"

    VALID_INSURERS = {
        "insurer1": "Alliance Agri",
        "insurer2": "Midwest Mutual",
        "insurer3": "Great Plains Corp",
        "insurer4": "National Crop",
        "insurer5": "Pioneer Harvest",
        "insurer6": "Frontier Farm"
    }

    if normalized_role == "auditor":
        # Auditor is registered as an independent individual, unaffiliated with any insurer
        insurer_id = "INDIVIDUAL"
        raw_name = (payload.individual_name or payload.insurer_name or "").strip()
        if raw_name and raw_name.lower() not in (
            "insurer1", "insurer2", "insurer3", "insurer4", "insurer5", "insurer6",
            "alliance agri", "midwest mutual", "great plains corp", "national crop",
            "pioneer harvest", "frontier farm", "consortium auditor"
        ):
            insurer_name = raw_name
        else:
            insurer_name = "Individual Auditor"
    else:
        insurer_id = (payload.insurer_id or "insurer1").lower().replace("-", "_").strip()
        if insurer_id not in VALID_INSURERS:
            if payload.insurer_name and payload.insurer_name.strip():
                insurer_name = payload.insurer_name.strip()
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid insurer '{insurer_id}'. Only the 6 consortium insurers (insurer1 - insurer6) or registered custom insurers are allowed."
                )
        else:
            insurer_name = VALID_INSURERS[insurer_id]

    hashed_pass = auth.hash_password(payload.password)
    try:
        user = db.create_insurer_user(
            insurer_id=insurer_id,
            username=payload.username.strip(),
            password_hash=hashed_pass,
            insurer_name=insurer_name,
            email=payload.email,
            role=normalized_role
        )
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=400, detail="Username or email already exists.")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

    token = auth.create_access_token({
        "sub": user["username"],
        "user_id": user["id"],
        "insurer_id": user["insurer_id"],
        "insurer_name": user["insurer_name"],
        "role": normalized_role
    })

    user_dict = {
        "id": user["id"],
        "insurer_id": user["insurer_id"],
        "username": user["username"],
        "insurer_name": user["insurer_name"],
        "email": user.get("email"),
        "role": normalized_role
    }

    return {
        "status": "SUCCESS",
        "access_token": token,
        "token_type": "bearer",
        "role": normalized_role,
        "insurer_id": user["insurer_id"],
        "user": user_dict
    }


@app.get("/auth/me")
def get_current_user_profile(current_user: Dict[str, Any] = Depends(auth.get_current_user)):
    """Returns the authenticated insurer profile from token / DB."""
    user = db.get_user_by_identifier(current_user["sub"])
    if not user:
        return current_user
    return {
        "id": user["id"],
        "insurer_id": user["insurer_id"],
        "username": user["username"],
        "insurer_name": user["insurer_name"],
        "email": user.get("email"),
        "role": user["role"]
    }


@app.get("/auth/insurers")
def list_insurers():
    """Lists registered consortium insurers."""
    return db.list_consortium_insurers()


@app.post("/insurers/{insurer_id}/claims")
def submit_claim(
    insurer_id: str = Path(..., examples=["insurer1"]),
    payload: ClaimInput = ...,
    current_user: Dict[str, Any] = Depends(auth.require_roles("adjuster"))
):
    """
    Claim Intake Pipeline:
      1. Role check: Adjuster only, strictly scoped to their own insurer
      2. Validates and generates unique claim_id and claim_ref
      3. Computes features via preprocess_stats
      4. Infers fraud_score & risk_label via XGBoost
      5. Inserts claim to PostgreSQL with chain_status='PENDING'
      6. Anchors claim hash onto Solidity smart contract
      7. If HIGH risk, calculates SHAP explanation, stores in DB, and anchors SHAP hash
      8. Updates claim chain_status to 'ANCHORED'
      9. Records immutable CLAIM_SUBMITTED entry in append-only audit_log
    """
    auth.require_insurer_scope(insurer_id, current_user)
    claim_id = str(uuid.uuid4())
    claim_ref = payload.claim_ref or f"CLM-{insurer_id.upper()}-{uuid.uuid4().hex[:6].upper()}"

    raw_dict = payload.model_dump()
    raw_dict["claim_id"] = claim_id
    raw_dict["claim_ref"] = claim_ref
    raw_dict["insurer_id"] = insurer_id
    raw_dict["model_version"] = engine.model_version

    # 1. Feature Engineering & Inference
    features = engine.build_features(raw_dict)
    fraud_score, risk_label = engine.predict(features)
    raw_dict["fraud_score"] = fraud_score
    raw_dict["risk_label"] = risk_label

    # 2. Canonical Claim JSON & Hash
    canonical_str = hashing.canonical_claim_json(raw_dict)
    claim_hash = hashing.hash_claim(raw_dict)

    # 3. Insert claim into DB as PENDING
    record = {
        "claim_id": claim_id,
        "claim_ref": claim_ref,
        "claim_data_canonical": canonical_str,
        "claim_data": raw_dict,
        "features": features,
        "model_version": engine.model_version,
        "fraud_score": fraud_score,
        "risk_label": risk_label,
        "claim_hash": claim_hash,
        "claim_tx_id": None,
        "chain_status": "PENDING",
        "status": "FLAGGED" if risk_label == "HIGH" else "APPROVED"
    }

    try:
        db.insert_claim(insurer_id, record)
    except (ValueError, Exception) as e:
        if "unique" in str(e).lower() or "already" in str(e).lower():
            raise HTTPException(status_code=400, detail=f"Claim reference '{claim_ref}' already exists (write-once violation)")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # 4. Anchor on Smart Contract
    try:
        tx_res = chain_client.register_claim(
            claim_id=claim_ref,
            insurer_id=insurer_id,
            claim_data=raw_dict,
            model_version=engine.model_version,
            risk_label=risk_label,
            claim_hash=claim_hash
        )
        tx_id = tx_res.get("tx_hash") or f"0x{uuid.uuid4().hex}"
        db.update_claim_chain_status(insurer_id, claim_ref, "ANCHORED", tx_id)
        record["chain_status"] = "ANCHORED"
        record["claim_tx_id"] = tx_id
    except Exception as e:
        db.update_claim_chain_status(insurer_id, claim_ref, "FAILED")
        raise HTTPException(status_code=500, detail=f"Chain anchoring failed: {str(e)}")

    # 5. SHAP for Flagged Claims Only (HIGH risk)
    shap_record = None
    if risk_label == "HIGH":
        shap_data = engine.compute_shap(claim_ref, features)
        shap_canonical = hashing.canonical_shap_json(shap_data)
        shap_hash = hashing.hash_shap(shap_data)

        # Store explanation in DB
        db.insert_explanation(insurer_id, {
            "claim_ref": claim_ref,
            "shap_canonical": shap_canonical,
            "shap_json": shap_data,
            "shap_hash": shap_hash,
            "chain_status": "PENDING"
        })

        # Anchor SHAP hash on-chain
        try:
            shap_res = chain_client.anchor_shap(claim_ref, shap_data, shap_hash=shap_hash)
            shap_tx = shap_res.get("tx_hash") or f"0x{uuid.uuid4().hex}"
            db.update_explanation_chain_status(insurer_id, claim_ref, "ANCHORED", shap_tx)
            shap_record = {
                "shap_hash": shap_hash,
                "chain_status": "ANCHORED",
                "shap_tx_id": shap_tx,
                "feature_contributions": shap_data["feature_contributions"]
            }
        except Exception as e:
            db.update_explanation_chain_status(insurer_id, claim_ref, "FAILED")

    # Record immutable audit log entry
    try:
        db.append_audit_log(
            insurer_id=insurer_id,
            username=current_user.get("sub", "adjuster"),
            role=current_user.get("role", "adjuster"),
            action="CLAIM_SUBMITTED",
            claim_ref=claim_ref,
            details={
                "risk_label": risk_label,
                "fraud_score": fraud_score,
                "claim_hash": claim_hash,
                "claim_tx_id": record["claim_tx_id"]
            }
        )
    except Exception:
        pass

    return {
        "status": "SUCCESS",
        "claim_id": claim_id,
        "claim_ref": claim_ref,
        "fraud_score": fraud_score,
        "risk_label": risk_label,
        "claim_hash": claim_hash,
        "claim_tx_id": record["claim_tx_id"],
        "explanation": shap_record
    }


@app.get("/insurers/{insurer_id}/claims")
def list_insurer_claims(
    insurer_id: str,
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(auth.require_roles("adjuster", "admin", "auditor"))
):
    """
    Retrieves claims for the insurer:
      - adjuster: views own claims (status only)
      - admin: views own claims
      - auditor: views claims across any insurer
    """
    auth.require_insurer_scope(insurer_id, current_user)
    return db.list_claims(insurer_id, limit=limit)


@app.get("/insurers/{insurer_id}/claims/{claim_ref}")
def get_single_claim(
    insurer_id: str,
    claim_ref: str,
    current_user: Dict[str, Any] = Depends(auth.require_roles("adjuster", "admin", "auditor"))
):
    """Retrieves claim details for authorized users."""
    auth.require_insurer_scope(insurer_id, current_user)
    claim = db.get_claim(insurer_id, claim_ref)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@app.get("/insurers/{insurer_id}/claims/{claim_ref}/explanation")
def get_claim_explanation(
    insurer_id: str,
    claim_ref: str,
    current_user: Dict[str, Any] = Depends(auth.require_roles("admin", "auditor"))
):
    """Retrieves SHAP explanation for a flagged claim (admin or auditor only; adjuster forbidden)."""
    auth.require_insurer_scope(insurer_id, current_user)
    exp = db.get_explanation(insurer_id, claim_ref)
    if not exp:
        raise HTTPException(status_code=404, detail="No explanation found for this claim")
    return exp


@app.post("/insurers/{insurer_id}/claims/{claim_ref}/audit")
def run_claim_audit(
    insurer_id: str,
    claim_ref: str,
    current_user: Dict[str, Any] = Depends(auth.require_roles("admin", "auditor"))
):
    """
    Executes the 4-phase cryptographic audit on a claim:
      - Allowed: admin (own insurer) or auditor (consortium-wide).
      - Adjuster forbidden (403).
      - Claim integrity (recomputed from raw claim_data vs ledger)
      - Explanation integrity (recomputed SHAP vs ledger)
      - Model integrity (weights file vs ledger)
      - Consistency (risk label and model version vs ledger)
    """
    auth.require_insurer_scope(insurer_id, current_user)
    try:
        report = auditor.run_full_audit(
            insurer_id,
            claim_ref,
            username=current_user.get("sub", "auditor"),
            role=current_user.get("role", "admin")
        )
        db.append_audit_log(
            insurer_id=insurer_id,
            username=current_user.get("sub", "auditor"),
            role=current_user.get("role", "admin"),
            action="AUDIT_RUN",
            claim_ref=claim_ref,
            details={"overall_status": report["overall_status"]}
        )
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/insurers/{insurer_id}/audit-log")
def get_insurer_audit_log(
    insurer_id: str,
    claim_ref: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(auth.require_roles("admin", "auditor"))
):
    """Retrieves immutable append-only audit log records for the insurer (admin/auditor only)."""
    auth.require_insurer_scope(insurer_id, current_user)
    return db.get_audit_logs(insurer_id, claim_ref=claim_ref, limit=limit)


@app.get("/insurers/{insurer_id}/audit-log/verify")
def verify_insurer_audit_chain(
    insurer_id: str,
    current_user: Dict[str, Any] = Depends(auth.require_roles("admin", "auditor"))
):
    """Cryptographically verifies the SHA-256 hash chain of the insurer's audit log."""
    auth.require_insurer_scope(insurer_id, current_user)
    return db.verify_audit_chain(insurer_id)


@app.get("/insurers/{insurer_id}/audit/missing-records")
def audit_missing_records(
    insurer_id: str,
    current_user: Dict[str, Any] = Depends(auth.require_roles("admin", "auditor"))
):
    """
    Missing records check:
    Compares on-chain ClaimRegistered events against local database rows.
    Flags any claims that exist on-chain but are missing in the insurer DB.
    """
    auth.require_insurer_scope(insurer_id, current_user)
    return auditor.check_missing_records(insurer_id)


@app.get("/models")
def get_models(current_user: Dict[str, Any] = Depends(auth.require_roles("admin", "auditor"))):
    """Returns registered model versions and SHA-256 hashes (admin/auditor only)."""
    models_info = [
        {"version": "M1", "name": "xgb_dp_federated", "description": "Federated DP (Clip=1.0, Sigma=0.01)"},
        {"version": "M0", "name": "xgb_centralized", "description": "Centralized Baseline"}
    ]
    for m in models_info:
        file_path = os.path.join(inference.MODELS_DIR, f"{m['name']}.json")
        if os.path.exists(file_path):
            m["sha256"] = hashing.hash_model_file(file_path)
            m["status"] = "AVAILABLE"
        else:
            m["status"] = "UNAVAILABLE"
    return models_info


@app.post("/models/{version}/verify")
def verify_model(
    version: str,
    current_user: Dict[str, Any] = Depends(auth.require_roles("admin", "auditor"))
):
    """Verifies local model file against the registered on-chain commitment (admin/auditor only)."""
    model_file = os.path.join(inference.MODELS_DIR, "xgb_dp_federated.json")
    if not os.path.exists(model_file):
        model_file = os.path.join(inference.MODELS_DIR, "xgb_centralized.json")

    valid, status = chain_client.verify_model(version, model_file)
    return {
        "version": version,
        "is_valid": valid,
        "status": status,
        "local_hash": hashing.hash_model_file(model_file)
    }


@app.get("/metrics")
def get_metrics(current_user: Dict[str, Any] = Depends(auth.require_roles("admin", "auditor"))):
    """Returns comparative model performance metrics (admin/auditor only)."""
    return {
        "centralized": {
            "model": "XGBoost Centralized",
            "f1_score": 0.9848,
            "precision": 0.9812,
            "recall": 0.9884,
            "privacy": "None"
        },
        "federated": {
            "model": "FedAvg (6 Insurers)",
            "f1_score": 0.9938,
            "precision": 0.9920,
            "recall": 0.9956,
            "privacy": "Distributed (No Raw Data Sharing)"
        },
        "federated_dp": {
            "model": "FedAvg + Differential Privacy (Clip + Noise)",
            "f1_score": 0.9912,
            "precision": 0.9895,
            "recall": 0.9930,
            "privacy": "L2 Clip (1.0) + Gaussian Noise (0.01)"
        }
    }


# =============================================================================
# Attacker Simulation (Tamper Demo Endpoints)
# =============================================================================

@app.post("/simulate/tamper/claim/{claim_ref}")
@app.post("/demo/tamper/claim/{claim_ref}")
def tamper_claim_endpoint(
    claim_ref: str,
    payload: TamperClaimInput,
    current_user: Dict[str, Any] = Depends(auth.require_roles("adjuster", "admin"))
):
    """
    Attacker Simulation: modifies net_indemnity in local DB to trigger integrity mismatch.
    Simulates an outside breach or compromised account. Not available to auditor.
    """
    auth.require_insurer_scope(payload.insurer_id, current_user)
    try:
        res = db.tamper_claim(payload.insurer_id, claim_ref, payload.new_indemnity)
        db.append_audit_log(
            insurer_id=payload.insurer_id,
            username=current_user.get("sub", "attacker"),
            role=current_user.get("role", "adjuster"),
            action="TAMPER_SIMULATED",
            claim_ref=claim_ref,
            details={
                "attack": "claim_indemnity_modified",
                "new_indemnity": payload.new_indemnity,
                "account": current_user.get("sub")
            }
        )
        res["simulation_label"] = "Attacker Simulation (demo only)"
        res["warning"] = "Simulates an outside breach or compromised account. Not available in production."
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/simulate/tamper/explanation/{claim_ref}")
@app.post("/demo/tamper/explanation/{claim_ref}")
def tamper_explanation_endpoint(
    claim_ref: str,
    payload: TamperExplanationInput,
    current_user: Dict[str, Any] = Depends(auth.require_roles("adjuster", "admin"))
):
    """Attacker Simulation: modifies a SHAP feature contribution in local DB."""
    auth.require_insurer_scope(payload.insurer_id, current_user)
    try:
        res = db.tamper_explanation(payload.insurer_id, claim_ref, payload.feature_name, payload.new_value)
        db.append_audit_log(
            insurer_id=payload.insurer_id,
            username=current_user.get("sub", "attacker"),
            role=current_user.get("role", "adjuster"),
            action="TAMPER_SIMULATED",
            claim_ref=claim_ref,
            details={
                "attack": "shap_modified",
                "feature": payload.feature_name,
                "new_value": payload.new_value
            }
        )
        res["simulation_label"] = "Attacker Simulation (demo only)"
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/simulate/restore/{claim_ref}")
@app.post("/demo/restore/{claim_ref}")
def restore_claim_endpoint(
    claim_ref: str,
    insurer_id: str = Query("insurer1"),
    current_user: Dict[str, Any] = Depends(auth.require_roles("adjuster", "admin"))
):
    """Restores the original untampered claim and explanation records."""
    auth.require_insurer_scope(insurer_id, current_user)
    try:
        res = db.restore_claim(insurer_id, claim_ref)
        db.append_audit_log(
            insurer_id=insurer_id,
            username=current_user.get("sub", "admin"),
            role=current_user.get("role", "admin"),
            action="CLAIM_RESTORED",
            claim_ref=claim_ref,
            details={"restored_components": res.get("restored_components")}
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
