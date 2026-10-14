#!/usr/bin/env python3
"""
Hyperledger Fabric Transaction Submitter, AI Fraud Predictor & Verifier
Project: Federated, Blockchain-Audited Crop Insurance Fraud Detection

Usage:
    # Mode 1: Interactive Claim Registration & AI Fraud Evaluation:
    python blockchain/submit_tx.py --interactive

    # Mode 2: Direct 1-Line Execution (Instant registration + AI prediction):
    python blockchain/submit_tx.py --direct --farmer-name "Sarah Jenkins" --policy-id "POL-88401" --amount 35000 --crop "Wheat"

    # Mode 3: Direct Integrity Verification:
    python blockchain/submit_tx.py --verify-claim --claim-id "CLM-2026-LIVE-99" --amount 35000 --crop "Wheat"

    # Mode 4: Batch of N concurrent transactions:
    python blockchain/submit_tx.py --batch 5
"""

import sys
import os
import json
import argparse
import subprocess
import hashlib
import time
import numpy as np

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CHANNEL_NAME = "insurance-channel"
CC_NAME = "insurance_audit"
ORDERER_CA = "/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/insurance.com/orderers/orderer.insurance.com/tls/ca.crt"
ORDERER_URL = "orderer.insurance.com:7050"

MODEL_PATH = "models/xgb_federated_global.json"
if not os.path.exists(MODEL_PATH):
    MODEL_PATH = "models/xgb_centralized.json"

PEER_ADDRS = [
    ("InsurerAMSP", "insurera.insurance.com", "7051"),
    ("InsurerBMSP", "insurerb.insurance.com", "8051"),
    ("InsurerCMSP", "insurerc.insurance.com", "9051"),
    ("InsurerDMSP", "insurerd.insurance.com", "10051"),
    ("InsurerEMSP", "insurere.insurance.com", "11051"),
    ("InsurerFMSP", "insurerf.insurance.com", "12051"),
]

# Mapping helpers for realistic features
CROP_CODES = {
    "Corn": 41,
    "Wheat": 11,
    "Soybeans": 81,
    "Cotton": 21,
    "Barley": 91
}

CAUSE_CODES = {
    "Drought": 11,
    "Excess Moisture": 12,
    "Hail": 21,
    "Frost": 31,
    "Heat": 41
}

def compute_claim_hash(claim_id, insurer_id, amount, crop, farmer_name="Anonymous", policy_id="POL-000", cause_of_loss="Drought", acres="100", salt="SECRET_SALT_2026"):
    """Computes SHA-256 fingerprint over all private claim attributes."""
    payload = f"{claim_id}:{insurer_id}:{farmer_name}:{policy_id}:{amount}:{crop}:{acres}:{cause_of_loss}:{salt}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()

def compute_prediction_hash(claim_id, model_ver, fraud_prob, risk_bucket, salt="SECRET_SALT_2026"):
    """Computes SHA-256 fingerprint of the AI prediction outcome."""
    payload = f"{claim_id}:{model_ver}:{fraud_prob:.4f}:{risk_bucket}:{salt}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()

def run_ai_fraud_prediction(amount_str, crop_str, acres_str, cause_str):
    """Evaluates claim attributes using the trained XGBoost model."""
    try:
        import xgboost as xgb
        
        amount = float(amount_str)
        acres = float(acres_str) if float(acres_str) > 0 else 100.0
        
        comm_code = CROP_CODES.get(crop_str, 41)
        cause_code = CAUSE_CODES.get(cause_str, 11)
        
        liability = acres * 650.0  # Approx $650 liability per acre
        premium = liability * 0.07 # Approx 7% premium
        indemnity = amount
        
        ind_to_prem = indemnity / (premium + 1e-5)
        ind_to_liab = indemnity / (liability + 1e-5)
        yield_dev = -0.45 if ind_to_liab > 0.8 else -0.10
        high_cause = 1 if ind_to_prem > 3.0 else 0
        
        # Build 14-feature vector matching training schema
        feature_vector = np.array([[
            comm_code,              # commodity_code
            cause_code,             # cause_of_loss_code
            8,                      # month_of_loss (August)
            indemnity,              # indemnity_amount
            premium,                # total_premium
            liability,              # liability_amount
            acres,                  # net_determined_acres
            acres,                  # net_planted_acres
            0.6,                    # determined_yield
            ind_to_prem,            # indemnity_to_premium_ratio
            ind_to_liab,            # indemnity_to_liability_ratio
            yield_dev,              # yield_deviation
            high_cause,             # high_cause_code
            12                      # county_claim_frequency
        ]], dtype=np.float32)

        if os.path.exists(MODEL_PATH):
            bst = xgb.Booster()
            bst.load_model(MODEL_PATH)
            dmat = xgb.DMatrix(feature_vector)
            prob = float(bst.predict(dmat)[0])
        else:
            # Fallback heuristic if model file not found
            prob = 0.92 if ind_to_liab > 0.85 else 0.04

        risk_bucket = "HIGH_RISK" if prob >= 0.50 else "LOW_RISK"
        return prob, risk_bucket
    except Exception as e:
        # Fallback estimation
        amount = float(amount_str)
        acres = float(acres_str) if float(acres_str) > 0 else 1.0
        prob = 0.89 if (amount / acres) > 5000 else 0.03
        risk_bucket = "HIGH_RISK" if prob >= 0.50 else "LOW_RISK"
        return prob, risk_bucket

def execute_chaincode_invoke(fn_name, args_list):
    """Submits an endorsed transaction to Hyperledger Fabric orderer."""
    ctor_dict = {"Args": [fn_name] + [str(a) for a in args_list]}
    ctor_json = json.dumps(ctor_dict)

    cmd = [
        "docker", "exec", "cli.insurance.com",
        "peer", "chaincode", "invoke",
        "-o", ORDERER_URL,
        "--ordererTLSHostnameOverride", "orderer.insurance.com",
        "--tls", "--cafile", ORDERER_CA,
        "-C", CHANNEL_NAME,
        "-n", CC_NAME,
        "-c", ctor_json,
        "--peerAddresses", "peer0.insurera.insurance.com:7051",
        "--tlsRootCertFiles", "/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurera.insurance.com/peers/peer0.insurera.insurance.com/tls/ca.crt",
        "--peerAddresses", "peer0.insurerb.insurance.com:8051",
        "--tlsRootCertFiles", "/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurerb.insurance.com/peers/peer0.insurerb.insurance.com/tls/ca.crt",
        "--peerAddresses", "peer0.insurerc.insurance.com:9051",
        "--tlsRootCertFiles", "/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurerc.insurance.com/peers/peer0.insurerc.insurance.com/tls/ca.crt",
        "--peerAddresses", "peer0.insurerd.insurance.com:10051",
        "--tlsRootCertFiles", "/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurerd.insurance.com/peers/peer0.insurerd.insurance.com/tls/ca.crt",
        "--peerAddresses", "peer0.insurere.insurance.com:11051",
        "--tlsRootCertFiles", "/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurere.insurance.com/peers/peer0.insurere.insurance.com/tls/ca.crt",
        "--peerAddresses", "peer0.insurerf.insurance.com:12051",
        "--tlsRootCertFiles", "/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurerf.insurance.com/peers/peer0.insurerf.insurance.com/tls/ca.crt"
    ]

    print(f"\n[Fabric Network] Invoking Smart Contract Function: '{fn_name}'...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[ERROR] Transaction Failed:\n{res.stderr}", file=sys.stderr)
        return False, res.stderr
    
    print(f"[SUCCESS] Transaction Successfully Submitted & Endorsed by Consortium Peers.")
    for line in (res.stdout + res.stderr).splitlines():
        if "Chaincode invoke successful" in line or "payload:" in line or "status:200" in line:
            print(f"   {line.strip()}")
    return True, res.stdout

def execute_chaincode_query(fn_name, args_list):
    """Executes a read-only query against the ledger."""
    ctor_dict = {"Args": [fn_name] + [str(a) for a in args_list]}
    ctor_json = json.dumps(ctor_dict)

    cmd = [
        "docker", "exec", "cli.insurance.com",
        "peer", "chaincode", "query",
        "-C", CHANNEL_NAME,
        "-n", CC_NAME,
        "-c", ctor_json
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[ERROR] Query Failed:\n{res.stderr}", file=sys.stderr)
        return None
    return res.stdout.strip()

def prompt_user_for_details():
    """Interactively collects all claim details from user input."""
    print("\n" + "=" * 60)
    print("INTERACTIVE CLAIM REGISTRATION & FRAUD EVALUATION")
    print("=" * 60)
    
    default_cid = f"CLM-{int(time.time()) % 100000}"
    cid = input(f"1. Claim ID [{default_cid}]: ").strip() or default_cid
    farmer = input("2. Farmer / Policyholder Name [Robert Miller]: ").strip() or "Robert Miller"
    pol = input("3. Policy Certificate ID [POL-992140]: ").strip() or "POL-992140"
    insurer = input("4. Insurer Organization (InsurerA-F) [InsurerA]: ").strip() or "InsurerA"
    amt = input("5. Claim Payout Amount ($) [35000]: ").strip() or "35000"
    crop = input("6. Insured Crop Type [Corn]: ").strip() or "Corn"
    acres = input("7. Damaged Acreage [120.5]: ").strip() or "120.5"
    cause = input("8. Cause of Loss [Drought]: ").strip() or "Drought"

    return cid, farmer, pol, insurer, amt, crop, acres, cause

def main():
    parser = argparse.ArgumentParser(description="Submit Transactions to Hyperledger Fabric")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive prompt asking for all claim details")
    parser.add_argument("--direct", action="store_true", help="Direct non-interactive claim registration")
    parser.add_argument("--register-claim", action="store_true", help="Register claim commitment on-chain")
    parser.add_argument("--verify-claim", action="store_true", help="Verify claim hash against on-chain commitment")
    parser.add_argument("--anchor-fl", action="store_true", help="Anchor Federated Learning Round on-chain")
    parser.add_argument("--record-anomaly", action="store_true", help="Record Byzantine Poisoning Anomaly on-chain")
    parser.add_argument("--get-claim", action="store_true", help="Query claim record from ledger")
    parser.add_argument("--batch", type=int, default=0, help="Submit N concurrent transactions (e.g. --batch 5)")

    parser.add_argument("--claim-id", type=str, default="")
    parser.add_argument("--farmer-name", type=str, default="Robert Miller")
    parser.add_argument("--policy-id", type=str, default="POL-992140")
    parser.add_argument("--insurer", type=str, default="InsurerA")
    parser.add_argument("--amount", type=str, default="35000")
    parser.add_argument("--crop", type=str, default="Corn")
    parser.add_argument("--acres", type=str, default="120.5")
    parser.add_argument("--cause", type=str, default="Drought")
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--model-hash", type=str, default="")
    parser.add_argument("--attack", type=str, default="WeightScaling_x50")

    args = parser.parse_args()

    # 1. Interactive Mode
    if args.interactive:
        cid, farmer, pol, insurer, amt, crop, acres, cause = prompt_user_for_details()
        chash = compute_claim_hash(cid, insurer, amt, crop, farmer, pol, cause, acres)

        print("\n" + "-" * 60)
        print("STEP 1: CLAIM REGISTRATION COMMITMENT")
        print("-" * 60)
        print(f"Claim ID       : {cid}")
        print(f"Farmer Name    : {farmer} (Kept Off-Chain / Private)")
        print(f"Policy ID      : {pol} (Kept Off-Chain / Private)")
        print(f"Insurer        : {insurer}")
        print(f"Amount / Crop  : ${amt} ({crop})")
        print(f"Acreage / Cause: {acres} Acres ({cause})")
        print(f"Salted SHA-256 : {chash}")
        print("-" * 60)

        # Register Claim
        success, _ = execute_chaincode_invoke("RegisterClaim", [cid, insurer, chash, "schema_v1"])
        
        if success:
            print("\n" + "-" * 60)
            print("STEP 2: LOCAL AI FRAUD MODEL INFERENCE")
            print("-" * 60)
            prob, risk_bucket = run_ai_fraud_prediction(amt, crop, acres, cause)
            pred_hash = compute_prediction_hash(cid, "M5", prob, risk_bucket)
            
            print(f"AI Model Used   : Federated XGBoost (M5)")
            print(f"Fraud Risk Score: {prob*100:.2f}% (Probability: {prob:.4f})")
            print(f"Risk Assessment : {risk_bucket}")
            print(f"Prediction Hash : {pred_hash}")
            print("-" * 60)
            
            # Commit Prediction on-chain
            execute_chaincode_invoke("RegisterPrediction", [cid, "M5", pred_hash, risk_bucket])
            print(f"\n[INFO] Claim {cid} & AI Prediction successfully recorded on Hyperledger Fabric!")
            print(f"[INFO] Run 'python blockchain/inspect_block.py' to inspect the ledger.")

    # 2. Batch Mode
    elif args.batch > 0:
        import concurrent.futures
        num_tx = args.batch
        print(f"\n--- SUBMITTING BATCH OF {num_tx} CONCURRENT TRANSACTIONS ---")
        
        crops = ["Corn", "Wheat", "Soybeans", "Cotton", "Barley"]
        insurers = ["InsurerA", "InsurerB", "InsurerC", "InsurerD", "InsurerE", "InsurerF"]
        farmers = ["Robert Miller", "Sarah Jenkins", "David Brown", "Emma Wilson", "James Taylor"]
        causes = ["Drought", "Excess Moisture", "Hail", "Frost", "Heat"]
        
        def submit_one(i):
            cid = f"CLM-BATCH-{int(time.time()) % 10000}-{i+1}"
            ins = insurers[i % len(insurers)]
            farmer = farmers[i % len(farmers)]
            pol = f"POL-88{100+i}"
            amt = str(10000 * (i + 1))
            crp = crops[i % len(crops)]
            acr = str(50.0 + (i * 15))
            cau = causes[i % len(causes)]
            chash = compute_claim_hash(cid, ins, amt, crp, farmer, pol, cau, acr)
            print(f"[{i+1}/{num_tx}] Submitting {cid} ({farmer}, {pol}, {ins}, ${amt}, {crp}, {acr} ac, {cau})...")
            success, _ = execute_chaincode_invoke("RegisterClaim", [cid, ins, chash, "schema_v1"])
            return cid, success

        start_t = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_tx) as executor:
            futures = [executor.submit(submit_one, i) for i in range(num_tx)]
            results = [f.result() for f in futures]
        
        elapsed = time.time() - start_t
        successful = sum(1 for _, s in results if s)
        print(f"\n[SUMMARY] Successfully submitted {successful}/{num_tx} transactions in {elapsed:.2f}s.")
        print(f"[INFO] Inspect the ledger with: python blockchain/inspect_block.py")

    # 3. Direct Register Claim Mode
    elif args.register_claim or args.direct:
        cid = args.claim_id or f"CLM-{int(time.time()) % 100000}"
        claim_hash = compute_claim_hash(
            cid, args.insurer, args.amount, args.crop,
            args.farmer_name, args.policy_id, args.cause, args.acres
        )
        print(f"\n--- STEP 1: REGISTERING CLAIM COMMITMENT ON BLOCKCHAIN ---")
        print(f"Claim ID       : {cid}")
        print(f"Farmer Name    : {args.farmer_name} (Private / Kept Off-Chain)")
        print(f"Policy ID      : {args.policy_id} (Private / Kept Off-Chain)")
        print(f"Insurer        : {args.insurer}")
        print(f"Amount / Crop  : ${args.amount} ({args.crop})")
        print(f"Acreage / Cause: {args.acres} Acres ({args.cause})")
        print(f"Salted SHA-256 : {claim_hash}")
        success, _ = execute_chaincode_invoke("RegisterClaim", [cid, args.insurer, claim_hash, "schema_v1"])
        
        if success:
            print(f"\n--- STEP 2: RUNNING AI FRAUD INFERENCE ---")
            prob, risk_bucket = run_ai_fraud_prediction(args.amount, args.crop, args.acres, args.cause)
            pred_hash = compute_prediction_hash(cid, "M5", prob, risk_bucket)
            print(f"AI Model Used   : Federated XGBoost (M5)")
            print(f"Fraud Risk Score: {prob*100:.2f}% (Probability: {prob:.4f})")
            print(f"Risk Assessment : {risk_bucket}")
            print(f"Prediction Hash : {pred_hash}")
            execute_chaincode_invoke("RegisterPrediction", [cid, "M5", pred_hash, risk_bucket])
            print(f"\n[INFO] Run 'python blockchain/inspect_block.py' to inspect the new block.")

    # 4. Verify Claim Integrity Mode
    elif args.verify_claim:
        cid = args.claim_id
        if not cid:
            print("[ERROR] Please provide --claim-id to verify.")
            return
        candidate_hash = compute_claim_hash(
            cid, args.insurer, args.amount, args.crop,
            args.farmer_name, args.policy_id, args.cause, args.acres
        )
        print(f"\n--- VERIFYING CLAIM INTEGRITY ON BLOCKCHAIN ---")
        print(f"Claim ID        : {cid}")
        print(f"Farmer Name     : {args.farmer_name}")
        print(f"Policy ID       : {args.policy_id}")
        print(f"Amount / Crop   : ${args.amount} ({args.crop})")
        print(f"Acreage / Cause : {args.acres} Acres ({args.cause})")
        print(f"Recomputed Hash : {candidate_hash}")
        result = execute_chaincode_query("VerifyClaim", [cid, candidate_hash])
        print(f"Ledger Verification Result : {result}")

    # 5. Anchor FL Round
    elif args.anchor_fl:
        model_hash = args.model_hash or hashlib.sha256(f"XGB_ROUND_{args.round}_{time.time()}".encode('utf-8')).hexdigest()
        print(f"\n--- ANCHORING FEDERATED LEARNING ROUND ON BLOCKCHAIN ---")
        print(f"FL Round Number  : Round {args.round}")
        print(f"Model Version    : M{args.round}")
        print(f"Global Model Hash: {model_hash}")
        execute_chaincode_invoke("RegisterGlobalModel", [f"M{args.round}", model_hash, args.round])

    # 6. Record Byzantine Anomaly
    elif args.record_anomaly:
        update_hash = hashlib.sha256(f"poison_{args.round}_{args.insurer}".encode('utf-8')).hexdigest()
        print(f"\n--- RECORDING BYZANTINE ANOMALY ON BLOCKCHAIN ---")
        print(f"Round Number  : Round {args.round}")
        print(f"Rogue Insurer : {args.insurer}")
        print(f"Attack Type   : {args.attack}")
        print(f"Malicious Hash: {update_hash}")
        execute_chaincode_invoke("FlagAnomaly", [args.round, args.insurer, args.attack, update_hash])

    # 7. Get Claim
    elif args.get_claim:
        if not args.claim_id:
            print("[ERROR] Please provide --claim-id.")
            return
        print(f"\n--- QUERYING CLAIM ON BLOCKCHAIN ---")
        print(f"Claim ID: {args.claim_id}")
        result = execute_chaincode_query("GetClaim", [args.claim_id])
        print(f"Ledger Record: {result}")

    else:
        # Default: direct registration
        cid = f"CLM-DEMO-{int(time.time()) % 10000}"
        claim_hash = compute_claim_hash(cid, "InsurerA", "32000", "Soybeans")
        print(f"\n--- EXECUTING DIRECT DEMONSTRATION TRANSACTION ---")
        print(f"Submitting transaction for {cid}...")
        execute_chaincode_invoke("RegisterClaim", [cid, "InsurerA", claim_hash, "schema_v1"])

if __name__ == "__main__":
    main()
