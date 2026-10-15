"""
Hashing Specification for Crop Insurance Fraud Detection
Implements Section 9 of Project Architecture:
  - Canonical JSON string generation (no salts/nonces; UUID claim_id ensures uniqueness)
  - Claim SHA-256 hash
  - SHAP explanation SHA-256 hash (6 decimals, sorted keys)
  - Model binary SHA-256 hash
"""

import json
import hashlib
from typing import Dict, Any


def canonical_claim_json(data: Dict[str, Any]) -> str:
    """
    Builds canonical string with exact specified fields and fixed ordering:
      claim_id, insurer_id, farmer_id, commodity_code, cause_of_loss_code,
      net_indemnity, premium_amount, state_code, county_code, commodity_year,
      model_version, fraud_score (6 decimals), risk_label
    """
    fraud_score = float(data.get("fraud_score", 0.0))
    net_indemnity = float(data.get("net_indemnity", data.get("indemnity_amount", 0.0)))
    premium_amount = float(data.get("premium_amount", data.get("total_premium", 0.0)))

    ordered = {
        "claim_id": str(data.get("claim_id", "")),
        "insurer_id": str(data.get("insurer_id", "")),
        "farmer_id": str(data.get("farmer_id", "")),
        "commodity_code": str(data.get("commodity_code", "")),
        "cause_of_loss_code": str(data.get("cause_of_loss_code", "")),
        "net_indemnity": f"{net_indemnity:.2f}",
        "premium_amount": f"{premium_amount:.2f}",
        "state_code": str(data.get("state_code", "")),
        "county_code": str(data.get("county_code", "")),
        "commodity_year": int(data.get("commodity_year", 2026)),
        "model_version": str(data.get("model_version", "M1")),
        "fraud_score": f"{fraud_score:.6f}",
        "risk_label": str(data.get("risk_label", "LOW"))
    }
    return json.dumps(ordered, sort_keys=True, separators=(',', ':'))


def hash_claim(data: Dict[str, Any]) -> str:
    """Computes SHA-256 hex string from canonical claim JSON."""
    c_str = canonical_claim_json(data)
    return hashlib.sha256(c_str.encode("utf-8")).hexdigest()


def canonical_shap_json(shap_data: Dict[str, Any]) -> str:
    """
    Builds canonical JSON for SHAP explanation:
      Sorted keys, floats rounded to 6 decimals, includes claim_ref and model_version.
    """
    raw_contribs = shap_data.get("feature_contributions", {})
    rounded_contribs = {
        k: round(float(v), 6) for k, v in sorted(raw_contribs.items())
    }

    ordered = {
        "claim_ref": str(shap_data.get("claim_ref", shap_data.get("claim_id", ""))),
        "model_version": str(shap_data.get("model_version", "M1")),
        "base_value": round(float(shap_data.get("base_value", 0.0)), 6),
        "feature_contributions": rounded_contribs
    }
    return json.dumps(ordered, sort_keys=True, separators=(',', ':'))


def hash_shap(shap_data: Dict[str, Any]) -> str:
    """Computes SHA-256 hex string from canonical SHAP explanation JSON."""
    s_str = canonical_shap_json(shap_data)
    return hashlib.sha256(s_str.encode("utf-8")).hexdigest()


def hash_model_file(model_path: str) -> str:
    """Computes SHA-256 hash of the model weights file bytes."""
    with open(model_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
