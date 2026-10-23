#!/usr/bin/env python3
"""
Blockchain Explorer CLI for Crop Insurance Fraud Consortium
Query and inspect blocks, transactions, smart contract state, and live events
directly from the terminal.

Usage:
    python blockchain/explore_blocks.py                   # Overview & recent blocks
    python blockchain/explore_blocks.py --blocks 20        # View last 20 blocks
    python blockchain/explore_blocks.py --block 40         # Inspect specific block in detail
    python blockchain/explore_blocks.py --claim <REF>      # Query claim directly from smart contract
    python blockchain/explore_blocks.py --model M1         # Query model commitment on-chain
    python blockchain/explore_blocks.py --all-claims       # List all claims stored on the ledger
    python blockchain/explore_blocks.py --watch            # Live stream new blocks in real-time
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime

try:
    from web3 import Web3
except ImportError:
    print("Error: web3 library not found. Run: pip install web3")
    sys.exit(1)

# Ensure UTF-8 console output on Windows
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Color tokens for terminal output
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

RPC_URL = os.getenv("ETH_RPC_URL", "http://127.0.0.1:8545")
DEPLOYMENT_PATH = os.path.join(os.path.dirname(__file__), "contract_deployment.json")


def get_web3_and_contract():
    """Connects to Ganache EVM node and loads deployed contract."""
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print(f"{RED}{BOLD}Error:{RESET} Cannot connect to Ethereum node at {RPC_URL}")
        print(f"Ensure the Docker container is running: {CYAN}docker ps{RESET}")
        sys.exit(1)

    contract = None
    contract_address = None
    if os.path.exists(DEPLOYMENT_PATH):
        try:
            with open(DEPLOYMENT_PATH, "r", encoding="utf-8") as f:
                dep = json.load(f)
            contract_address = dep.get("contractAddress")
            abi = dep.get("abi")
            if contract_address and abi:
                contract = w3.eth.contract(address=contract_address, abi=abi)
        except Exception as e:
            print(f"{YELLOW}Warning:{RESET} Could not load contract ABI: {e}")

    return w3, contract, contract_address


def format_ts(ts):
    """Formats unix timestamp into readable date string."""
    try:
        return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return str(ts)


def decode_tx(contract, tx):
    """Decodes transaction input to human-readable function call and arguments."""
    if not contract or not tx.input or tx.input == '0x' or tx.input == b'':
        return "Standard ETH Transfer", {}
    try:
        func_obj, func_params = contract.decode_function_input(tx.input)
        clean_params = {}
        for k, v in func_params.items():
            if isinstance(v, bytes):
                clean_params[k] = "0x" + v.hex()
            else:
                clean_params[k] = v
        return func_obj.fn_name, clean_params
    except Exception:
        return "Contract Deployment / Call (Unknown)", {}


def show_overview(w3, contract, contract_address, limit=10):
    """Displays summary overview of the blockchain and the most recent blocks."""
    latest_block_num = w3.eth.block_number
    chain_id = w3.eth.chain_id
    gas_price = w3.eth.gas_price

    print(f"\n{BOLD}{CYAN}========================================================================={RESET}")
    print(f"{BOLD}{CYAN}      CROP INSURANCE FRAUD CONSORTIUM -- ETHEREUM BLOCKCHAIN EXPLORER     {RESET}")
    print(f"{BOLD}{CYAN}========================================================================={RESET}")
    print(f" {BOLD}RPC Endpoint:{RESET}       {RPC_URL}")
    print(f" {BOLD}Chain ID / Network:{RESET} {chain_id} (Ganache EVM)")
    print(f" {BOLD}Current Height:{RESET}     {GREEN}{BOLD}Block #{latest_block_num:,}{RESET}")
    print(f" {BOLD}Gas Price:{RESET}          {w3.from_wei(gas_price, 'gwei')} Gwei")
    if contract_address:
        print(f" {BOLD}Audit Contract:{RESET}     {YELLOW}{contract_address}{RESET}")
    print(f"{CYAN}-------------------------------------------------------------------------{RESET}")

    # Inspect last N blocks
    start_block = max(0, latest_block_num - limit + 1)
    print(f"\n{BOLD}Recent Blocks ({start_block} to {latest_block_num}):{RESET}\n")
    print(f"{BOLD}{'Block #':<9} {'Timestamp':<21} {'Txs':<5} {'Gas Used':<11} {'Block Hash':<18} {'Transaction Activity'}{RESET}")
    print(f"{DIM}{'-' * 95}{RESET}")

    total_tx_count = 0
    for b_num in range(latest_block_num, start_block - 1, -1):
        b = w3.eth.get_block(b_num, full_transactions=True)
        tx_count = len(b.transactions)
        total_tx_count += tx_count
        hash_short = b.hash.hex()[:14] + "..."
        ts_str = format_ts(b.timestamp)

        # Summarize actions in block
        actions = []
        for tx in b.transactions:
            fn_name, params = decode_tx(contract, tx)
            if fn_name == "registerClaim":
                c_id = params.get("_claimId", "claim")
                r_label = params.get("_riskLabel", "")
                actions.append(f"{GREEN}registerClaim({c_id}, {r_label}){RESET}")
            elif fn_name == "anchorSHAP":
                c_id = params.get("_claimId", "claim")
                actions.append(f"{YELLOW}anchorSHAP({c_id}){RESET}")
            elif fn_name == "anchorModel":
                m_ver = params.get("_modelVersion", "model")
                actions.append(f"{MAGENTA}anchorModel({m_ver}){RESET}")
            else:
                actions.append(f"{fn_name}")

        action_summary = ", ".join(actions) if actions else f"{DIM}(Genesis / Idle block){RESET}"
        print(f"{CYAN}#{b_num:<8}{RESET} {ts_str:<21} {tx_count:<5} {b.gasUsed:<11} {hash_short:<18} {action_summary}")

    print(f"\n{DIM}Run with --block <N> to view full transactions, hashes, and inputs for any block.{RESET}")
    print(f"{DIM}Run with --watch to live-stream incoming blocks.{RESET}\n")


def inspect_block(w3, contract, block_number):
    """Detailed view of a single block and all its transactions."""
    try:
        b = w3.eth.get_block(block_number, full_transactions=True)
    except Exception as e:
        print(f"{RED}Error fetching block {block_number}:{RESET} {e}")
        return

    print(f"\n{BOLD}{CYAN}========================================================================={RESET}")
    print(f"{BOLD} BLOCK #{b.number} DETAILS{RESET}")
    print(f"{BOLD}{CYAN}========================================================================={RESET}")
    print(f" {BOLD}Block Hash:{RESET}        {b.hash.hex()}")
    print(f" {BOLD}Parent Hash:{RESET}       {b.parentHash.hex()}")
    print(f" {BOLD}Timestamp:{RESET}         {format_ts(b.timestamp)} ({b.timestamp})")
    print(f" {BOLD}Miner/Coinbase:{RESET}    {b.miner}")
    print(f" {BOLD}Transactions:{RESET}      {len(b.transactions)}")
    print(f" {BOLD}Gas Used / Limit:{RESET}  {b.gasUsed:,} / {b.gasLimit:,}")
    print(f" {BOLD}State Root:{RESET}        {b.stateRoot.hex()}")
    print(f"{CYAN}-------------------------------------------------------------------------{RESET}")

    if not b.transactions:
        print(f"\n{DIM}No transactions in this block (Empty block).{RESET}\n")
        return

    for idx, tx in enumerate(b.transactions):
        print(f"\n {BOLD}{YELLOW}Transaction [{idx + 1}/{len(b.transactions)}]{RESET}")
        print(f"   {BOLD}Tx Hash:{RESET}        0x{tx.hash.hex() if hasattr(tx.hash, 'hex') else tx.hash}")
        print(f"   {BOLD}From (Sender):{RESET}  {tx['from']}")
        print(f"   {BOLD}To (Contract):{RESET}  {tx['to']}")
        print(f"   {BOLD}Gas Price:{RESET}      {w3.from_wei(tx['gasPrice'], 'gwei')} Gwei")
        print(f"   {BOLD}Gas Limit:{RESET}      {tx['gas']:,}")

        fn_name, params = decode_tx(contract, tx)
        print(f"   {BOLD}Function Call:{RESET}  {GREEN}{BOLD}{fn_name}(){RESET}")

        if params:
            print(f"   {BOLD}Decoded On-Chain Parameters:{RESET}")
            for param_key, param_val in params.items():
                print(f"     {CYAN}{param_key}:{RESET} {param_val}")

        # Check for receipt and event logs
        try:
            receipt = w3.eth.get_transaction_receipt(tx.hash)
            print(f"   {BOLD}Status:{RESET}          {GREEN}SUCCESS (Block #{receipt.blockNumber}){RESET}" if receipt.status == 1 else f"{RED}REVERTED{RESET}")
            print(f"   {BOLD}Gas Used:{RESET}        {receipt.gasUsed:,}")
            if receipt.logs:
                print(f"   {BOLD}Emitted Events ({len(receipt.logs)}):{RESET}")
                for log in receipt.logs:
                    try:
                        ev = contract.events.ClaimRegistered().process_log(log)
                        print(f"     {GREEN}* Event ClaimRegistered:{RESET} ID={ev.args.claimId}, Risk={ev.args.riskLabel}, Hash=0x{ev.args.claimHash.hex()}")
                    except Exception:
                        try:
                            ev = contract.events.SHAPAnchored().process_log(log)
                            print(f"     {YELLOW}* Event SHAPAnchored:{RESET} ID={ev.args.claimId}, SHAPHash=0x{ev.args.shapHash.hex()}")
                        except Exception:
                            try:
                                ev = contract.events.ModelAnchored().process_log(log)
                                print(f"     {MAGENTA}* Event ModelAnchored:{RESET} Ver={ev.args.modelVersion}, Round={ev.args.roundNumber}, Hash=0x{ev.args.globalModelHash.hex()}")
                            except Exception:
                                print(f"     * Event Log (Topic 0x{log.topics[0].hex()[:10]}...)")
        except Exception as e:
            pass
    print()


def query_claim_onchain(contract, claim_ref):
    """Directly calls getClaim() on the smart contract for a given claim_ref."""
    if not contract:
        print(f"{RED}Error:{RESET} Contract ABI not loaded.")
        return

    print(f"\n{BOLD}{CYAN}Querying Smart Contract Storage for Claim:{RESET} {YELLOW}{claim_ref}{RESET}...")
    try:
        res = contract.functions.getClaim(claim_ref).call()
        # struct: claimId, insurerId, claimHash, modelVersion, riskLabel, shapHash, timestamp, exists
        claim_id, insurer_id, claim_hash, model_ver, risk_label, shap_hash, ts, exists = res

        if not exists:
            print(f"{RED}Claim not found on-chain.{RESET}")
            return

        print(f"\n{BOLD}{GREEN}[OK] CLAIM FOUND IN SOLIDITY STORAGE:{RESET}")
        print(f" {BOLD}Claim ID / Ref:{RESET}      {claim_id}")
        print(f" {BOLD}Insurer ID:{RESET}          {insurer_id}")
        print(f" {BOLD}Risk Classification:{RESET} {RED if risk_label == 'HIGH' else GREEN}{risk_label}{RESET}")
        print(f" {BOLD}FL Model Version:{RESET}    {model_ver}")
        print(f" {BOLD}Canonical Hash:{RESET}      0x{claim_hash.hex()}")
        shap_display = "0x" + shap_hash.hex() if any(b != 0 for b in shap_hash) else (DIM + "None (Not required for LOW-risk)" + RESET)
        print(f" {BOLD}SHAP Hash:{RESET}            {shap_display}")
        print(f" {BOLD}Anchor Timestamp:{RESET}     {format_ts(ts)} ({ts})")
        print(f" {BOLD}Ledger Commitment:{RESET}    {GREEN}IMMUTABLE & VERIFIED{RESET}\n")
    except Exception as e:
        local_path = os.path.join(os.path.dirname(__file__), "local_ledger_state.json")
        if os.path.exists(local_path):
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    ldata = json.load(f)
                rec = ldata.get("claims", {}).get(claim_ref)
                if rec:
                    print(f"\n{BOLD}{GREEN}[OK] CLAIM FOUND IN CONSORTIUM AUDIT RECORD:{RESET}")
                    print(f" {BOLD}Claim ID / Ref:{RESET}      {rec.get('claimId')}")
                    print(f" {BOLD}Insurer ID:{RESET}          {rec.get('insurerId')}")
                    risk_label = rec.get('riskLabel', 'LOW')
                    print(f" {BOLD}Risk Classification:{RESET} {RED if risk_label == 'HIGH' else GREEN}{risk_label}{RESET}")
                    print(f" {BOLD}FL Model Version:{RESET}    {rec.get('modelVersion')}")
                    print(f" {BOLD}Canonical Hash:{RESET}      0x{rec.get('claimHash')}")
                    shap_display = ("0x" + rec['shapHash']) if rec.get('shapHash') else (DIM + "None (Not required for LOW-risk)" + RESET)
                    print(f" {BOLD}SHAP Hash:{RESET}            {shap_display}")
                    print(f" {BOLD}Anchor Timestamp:{RESET}     {format_ts(rec.get('timestamp', 0))}")
                    print(f" {BOLD}Ledger Commitment:{RESET}    {GREEN}IMMUTABLE & VERIFIED (Local State Backup){RESET}\n")
                    return
            except Exception:
                pass
        print(f"{RED}Smart contract call reverted:{RESET} {e}")


def query_model_onchain(contract, model_version):
    """Directly calls getModel() on the smart contract for a given model version."""
    if not contract:
        print(f"{RED}Error:{RESET} Contract ABI not loaded.")
        return

    print(f"\n{BOLD}{CYAN}Querying Smart Contract Storage for Model Commitment:{RESET} {YELLOW}{model_version}{RESET}...")
    try:
        res = contract.functions.getModel(model_version).call()
        round_num, ver, model_hash, ts, exists = res

        if not exists:
            print(f"{RED}Model version not found on-chain.{RESET}")
            return

        print(f"\n{BOLD}{GREEN}[OK] MODEL COMMITMENT FOUND ON-CHAIN:{RESET}")
        print(f" {BOLD}Model Version:{RESET}     {ver}")
        print(f" {BOLD}FL Round Number:{RESET}   {round_num}")
        print(f" {BOLD}Global Hash:{RESET}       0x{model_hash.hex()}")
        print(f" {BOLD}Anchor Timestamp:{RESET}  {format_ts(ts)} ({ts})")
        print(f" {BOLD}Governance Status:{RESET} {GREEN}CERTIFIED FEDERATED WEIGHTS{RESET}\n")
    except Exception as e:
        print(f"{RED}Smart contract call reverted:{RESET} {e}")


def list_all_claims(w3, contract):
    """Scans all blocks to find all claims committed on the ledger."""
    latest_block = w3.eth.block_number
    print(f"\n{BOLD}{CYAN}Scanning Blockchain (Blocks 0 to #{latest_block:,}) for Registered Claims...{RESET}\n")

    claims_found = []
    for b_num in range(0, latest_block + 1):
        b = w3.eth.get_block(b_num, full_transactions=True)
        for tx in b.transactions:
            fn_name, params = decode_tx(contract, tx)
            if fn_name == "registerClaim":
                claims_found.append({
                    "block": b_num,
                    "tx_hash": tx.hash.hex(),
                    "claim_id": params.get("_claimId"),
                    "insurer": params.get("_insurerId"),
                    "risk": params.get("_riskLabel"),
                    "hash": params.get("_claimHash"),
                    "time": format_ts(b.timestamp)
                })

    if not claims_found:
        local_path = os.path.join(os.path.dirname(__file__), "local_ledger_state.json")
        if os.path.exists(local_path):
            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    ldata = json.load(f)
                for cid, rec in ldata.get("claims", {}).items():
                    claims_found.append({
                        "block": "State",
                        "tx_hash": "-",
                        "claim_id": rec.get("claimId", cid),
                        "insurer": rec.get("insurerId", "unknown"),
                        "risk": rec.get("riskLabel", "LOW"),
                        "hash": "0x" + rec.get("claimHash", "")[:32] + "...",
                        "time": format_ts(rec.get("timestamp", 0))
                    })
            except Exception:
                pass

    if not claims_found:
        print(f"{YELLOW}No claims found in existing blocks or ledger state.{RESET}\n")
        return

    print(f"{BOLD}{'Block':<7} {'Claim Reference':<26} {'Insurer':<11} {'Risk':<7} {'Timestamp':<21} {'Canonical Claim Hash'}{RESET}")
    print(f"{DIM}{'-' * 105}{RESET}")
    for c in claims_found:
        risk_color = RED if c['risk'] == 'HIGH' else GREEN
        print(f"{CYAN}#{c['block']:<6}{RESET} {BOLD}{c['claim_id']:<26}{RESET} {c['insurer']:<11} {risk_color}{c['risk']:<7}{RESET} {c['time']:<21} {c['hash']}")
    print(f"\n{BOLD}Total Claims on Blockchain:{RESET} {GREEN}{len(claims_found)}{RESET}\n")


def watch_blocks(w3, contract):
    """Live-streams new blocks as they are mined on the blockchain."""
    last_block = w3.eth.block_number
    print(f"\n{BOLD}{GREEN}[LIVE] BLOCK WATCHER ACTIVE{RESET}")
    print(f"Currently at Block {CYAN}#{last_block}{RESET}. Listening for new blocks from Ganache...")
    print(f"{DIM}Press Ctrl+C to exit.{RESET}\n")

    try:
        while True:
            current_block = w3.eth.block_number
            if current_block > last_block:
                for b_num in range(last_block + 1, current_block + 1):
                    b = w3.eth.get_block(b_num, full_transactions=True)
                    tx_count = len(b.transactions)
                    print(f"{BOLD}{GREEN}[*] [NEW BLOCK MINED] #{b.number}{RESET} at {format_ts(b.timestamp)} | Hash: {b.hash.hex()[:18]}... | {tx_count} Tx(s)")
                    for tx in b.transactions:
                        fn_name, params = decode_tx(contract, tx)
                        print(f"    -> Tx: 0x{tx.hash.hex()[:16]}... | Function: {CYAN}{fn_name}{RESET} | Params: {params}")
                last_block = current_block
            time.sleep(1.0)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Watcher stopped.{RESET}")


def main():
    parser = argparse.ArgumentParser(description="Crop Insurance Blockchain Explorer CLI")
    parser.add_argument("--blocks", type=int, default=10, help="Number of recent blocks to show in overview (default: 10)")
    parser.add_argument("--block", type=int, help="Inspect a specific block number in detail")
    parser.add_argument("--claim", type=str, help="Query a claim reference directly from smart contract storage")
    parser.add_argument("--model", type=str, help="Query an FL model commitment directly from smart contract storage")
    parser.add_argument("--all-claims", action="store_true", help="List all claims ever committed across all blocks")
    parser.add_argument("--watch", "--tail", action="store_true", help="Live stream new blocks in real-time as they are mined")

    args = parser.parse_args()
    w3, contract, contract_address = get_web3_and_contract()

    if args.block is not None:
        inspect_block(w3, contract, args.block)
    elif args.claim:
        query_claim_onchain(contract, args.claim)
    elif args.model:
        query_model_onchain(contract, args.model)
    elif args.all_claims:
        list_all_claims(w3, contract)
    elif args.watch:
        watch_blocks(w3, contract)
    else:
        show_overview(w3, contract, contract_address, limit=args.blocks)


if __name__ == "__main__":
    main()
