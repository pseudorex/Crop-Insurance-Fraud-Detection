"""
Automated Contract Compiler & Deployer for InsuranceAudit.sol
Connects to the local EVM blockchain container (Ganache on http://localhost:8545),
compiles InsuranceAudit.sol using solc 0.8.20, deploys it,
and persists contract address + ABI to blockchain/contract_deployment.json.
"""

import os
import json
import solcx
from web3 import Web3

CONTRACT_PATH = os.path.join(os.path.dirname(__file__), "solidity", "InsuranceAudit.sol")
DEPLOYMENT_PATH = os.path.join(os.path.dirname(__file__), "contract_deployment.json")
RPC_URL = os.getenv("EVM_RPC_URL", "http://localhost:8545")


def compile_and_deploy():
    print(f"Connecting to EVM Node at {RPC_URL}...")
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        raise ConnectionError(f"Cannot connect to EVM node at {RPC_URL}. Is Docker running?")

    account = w3.eth.accounts[0]
    print(f"Deploying with account: {account} (Balance: {w3.from_wei(w3.eth.get_balance(account), 'ether')} ETH)")

    # Ensure solc 0.8.20 is installed
    solc_version = "0.8.20"
    if solc_version not in [str(v) for v in solcx.get_installed_solc_versions()]:
        solcx.install_solc(solc_version)
    solcx.set_solc_version(solc_version)

    print("Compiling InsuranceAudit.sol...")
    with open(CONTRACT_PATH, "r", encoding="utf-8") as f:
        contract_source = f.read()

    compiled = solcx.compile_source(
        contract_source,
        output_values=["abi", "bin"],
        solc_version=solc_version
    )

    contract_id = "<stdin>:InsuranceAudit"
    contract_interface = compiled[contract_id]
    abi = contract_interface["abi"]
    bytecode = contract_interface["bin"]

    print("Submitting deployment transaction to EVM blockchain...")
    InsuranceAuditContract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx_hash = InsuranceAuditContract.constructor().transact({"from": account, "gas": 4000000})
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    contract_address = tx_receipt.contractAddress
    print(f"-> Contract successfully deployed at: {contract_address}")
    print(f"-> Gas used: {tx_receipt.gasUsed} | Block: {tx_receipt.blockNumber} | Tx: {tx_hash.hex()}")

    # Persist deployment
    metadata = {
        "contractAddress": contract_address,
        "deployer": account,
        "blockNumber": tx_receipt.blockNumber,
        "transactionHash": tx_hash.hex(),
        "networkId": w3.net.version if hasattr(w3, 'net') else 1337,
        "abi": abi
    }
    with open(DEPLOYMENT_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"-> Deployment metadata saved to: {DEPLOYMENT_PATH}")

    # Anchor actual Federated DP Model M1
    import hashlib
    models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
    m1_path = os.path.join(models_dir, "xgb_dp_federated.json")
    if os.path.exists(m1_path):
        with open(m1_path, "rb") as f:
            m1_hash = hashlib.sha256(f.read()).hexdigest()
        deployed_contract = w3.eth.contract(address=contract_address, abi=abi)
        m_tx = deployed_contract.functions.anchorModel("M1", bytes.fromhex(m1_hash), 5).transact({"from": account, "gas": 200000})
        w3.eth.wait_for_transaction_receipt(m_tx)
        print(f"-> Anchored Global Model M1 on-chain | SHA-256: {m1_hash}")

    return metadata


if __name__ == "__main__":
    compile_and_deploy()
