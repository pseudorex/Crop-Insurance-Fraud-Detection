#!/usr/bin/env python3
"""
Hyperledger Fabric Block Inspector & Audit Viewer
Project: Federated, Blockchain-Audited Crop Insurance Fraud Detection
Usage:
    python blockchain/inspect_block.py               # Inspects latest block
    python blockchain/inspect_block.py --block 14    # Inspects block 14
    python blockchain/inspect_block.py --summary     # Shows ledger overview & block height
"""

import sys
import os
import json
import argparse
import subprocess
import base64

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

CHANNEL_NAME = "insurance-channel"
ORDERER_CA = "/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ordererOrganizations/insurance.com/orderers/orderer.insurance.com/tls/ca.crt"
PEER_TLS_CA = "/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurera.insurance.com/peers/peer0.insurera.insurance.com/tls/ca.crt"
ADMIN_MSP = "/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/insurera.insurance.com/users/Admin@insurera.insurance.com/msp"

def run_cmd(cmd_list):
    res = subprocess.run(cmd_list, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[ERROR] Command failed:\n{res.stderr}", file=sys.stderr)
    return res.stdout, res.returncode

def get_channel_info():
    cmd = [
        "docker", "exec",
        "-e", "CORE_PEER_LOCALMSPID=InsurerAMSP",
        "-e", f"CORE_PEER_MSPCONFIGPATH={ADMIN_MSP}",
        "-e", f"CORE_PEER_TLS_ROOTCERT_FILE={PEER_TLS_CA}",
        "-e", "CORE_PEER_ADDRESS=peer0.insurera.insurance.com:7051",
        "cli.insurance.com",
        "peer", "channel", "getinfo", "-c", CHANNEL_NAME
    ]
    stdout, code = run_cmd(cmd)
    if code != 0:
        return None
    for line in stdout.splitlines():
        if "Blockchain info:" in line:
            json_str = line.split("Blockchain info:")[1].strip()
            return json.loads(json_str)
    return None

def fetch_and_decode_block(block_target="newest"):
    temp_block = f"/opt/gopath/src/github.com/hyperledger/fabric/peer/channel-artifacts/inspect_{block_target}.block"
    fetch_cmd = [
        "docker", "exec",
        "-e", "CORE_PEER_LOCALMSPID=InsurerAMSP",
        "-e", f"CORE_PEER_MSPCONFIGPATH={ADMIN_MSP}",
        "-e", f"CORE_PEER_TLS_ROOTCERT_FILE={PEER_TLS_CA}",
        "-e", "CORE_PEER_ADDRESS=peer0.insurera.insurance.com:7051",
        "cli.insurance.com",
        "peer", "channel", "fetch", str(block_target), temp_block,
        "-c", CHANNEL_NAME,
        "-o", "orderer.insurance.com:7050",
        "--tls", "--cafile", ORDERER_CA
    ]
    _, code = run_cmd(fetch_cmd)
    if code != 0:
        return None

    decode_cmd = [
        "docker", "exec",
        "cli.insurance.com",
        "configtxlator", "proto_decode",
        "--input", temp_block,
        "--type", "common.Block"
    ]
    stdout, code = run_cmd(decode_cmd)
    if code != 0:
        return None

    try:
        return json.loads(stdout)
    except Exception as e:
        print(f"[ERROR] Failed to parse block JSON: {e}")
        return None

def display_block(block_json, block_num_arg=None):
    if not block_json:
        print("❌ Could not retrieve or decode block.")
        return

    header = block_json.get("header", {})
    block_num = header.get("number", block_num_arg or "Unknown")
    prev_hash = header.get("previous_hash", "None (Genesis Block 0)")
    data_hash = header.get("data_hash", "N/A")

    print("\n" + "=" * 75)
    print("=" * 75)
    print(f"HYPERLEDGER FABRIC BLOCK #{block_num}")
    print("=" * 75)
    print(f"Previous Block Hash : {prev_hash}")
    print(f"Current Data Hash   : {data_hash}")
    print(f"Channel             : {CHANNEL_NAME}")
    print("-" * 75)

    envelope_data = block_json.get("data", {}).get("data", [])
    print(f"Transactions Count  : {len(envelope_data)}")

    for idx, env in enumerate(envelope_data, start=1):
        try:
            payload = env.get("payload", {})
            ch_header = payload.get("header", {}).get("channel_header", {})
            sig_header = payload.get("header", {}).get("signature_header", {})

            tx_id = ch_header.get("tx_id", "N/A")
            timestamp = ch_header.get("timestamp", "N/A")
            creator_msp = sig_header.get("creator", {}).get("mspid", "Unknown")

            print(f"\n  [Transaction #{idx}]:")
            print(f"    - TxID         : {tx_id}")
            print(f"    - Timestamp    : {timestamp}")
            print(f"    - Submitter Org: {creator_msp}")

            # Extract actions and chaincode calls
            actions = payload.get("data", {}).get("actions", [])
            for a_idx, action in enumerate(actions, start=1):
                cc_proposal = action.get("payload", {}).get("chaincode_proposal_payload", {})
                cc_spec = cc_proposal.get("input", {}).get("chaincode_spec", {})
                cc_name = cc_spec.get("chaincode_id", {}).get("name", "N/A")
                raw_args = cc_spec.get("input", {}).get("args", [])
                
                decoded_args = []
                for arg in raw_args:
                    try:
                        decoded = base64.b64decode(arg).decode('utf-8', errors='replace')
                        decoded_args.append(decoded)
                    except:
                        decoded_args.append(str(arg))

                func_name = decoded_args[0] if decoded_args else "N/A"
                print(f"    - Chaincode    : {cc_name}")
                print(f"    - Function     : {func_name}")
                if len(decoded_args) > 1:
                    print(f"    - Arguments    : {decoded_args[1:]}")

                # Endorsements
                endorsements = action.get("payload", {}).get("action", {}).get("endorsements", [])
                print(f"    - Endorsements : {len(endorsements)} peers verified & endorsed")
        except Exception as e:
            print(f"    [!] Raw envelope entry (Index {idx})")

    print("=" * 75 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Hyperledger Fabric Block Inspector")
    parser.add_argument("--block", type=str, default="newest", help="Block number (e.g. 0, 1, 14) or 'newest'")
    parser.add_argument("--summary", action="store_true", help="Show summary ledger height and current hash")
    parser.add_argument("--json", action="store_true", help="Print full raw JSON of the block")
    args = parser.parse_args()

    info = get_channel_info()
    if info:
        print(f"[Ledger Info] Current Height: {info.get('height')} blocks | Latest Block Hash: {info.get('currentBlockHash')}")
    else:
        print("[WARNING] Could not connect to peer0.insurera.insurance.com to fetch ledger info.")

    if args.summary:
        return

    block_data = fetch_and_decode_block(args.block)
    if args.json:
        print(json.dumps(block_data, indent=2))
    else:
        display_block(block_data, args.block)

if __name__ == "__main__":
    main()
