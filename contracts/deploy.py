from web3 import Web3
from solcx import compile_source, install_solc, set_solc_version
import json
import os
from dotenv import load_dotenv
import time

load_dotenv()

def deploy_contract():
    SOLC_VERSION = "0.8.19"

    # ✅ Install and set Solidity version
    print(f"🔍 Installing Solidity {SOLC_VERSION}...")
    install_solc(SOLC_VERSION)
    set_solc_version(SOLC_VERSION)

    # ✅ Connect to blockchain
    blockchain_network = os.getenv('BLOCKCHAIN_NETWORK')
    print(f"🌐 Connecting to: {blockchain_network}")
    
    w3 = Web3(Web3.HTTPProvider(blockchain_network))
    if not w3.is_connected():
        print("❌ Failed to connect to blockchain network.")
        print("💡 Please check your BLOCKCHAIN_NETWORK URL in .env file")
        return

    print("✅ Connected to blockchain.")
    
    # Get network info
    try:
        chain_id = w3.eth.chain_id
        latest_block = w3.eth.block_number
        print(f"📊 Chain ID: {chain_id}")
        print(f"📦 Latest Block: {latest_block}")
        
        # Identify network
        network_names = {
            1: "Ethereum Mainnet",
            11155111: "Sepolia Testnet", 
            5: "Goerli Testnet",
            137: "Polygon Mainnet",
            80001: "Mumbai Testnet"
        }
        network_name = network_names.get(chain_id, f"Unknown Network (Chain ID: {chain_id})")
        print(f"🌍 Network: {network_name}")
        
        if chain_id == 1:
            print("⚠️  WARNING: You're deploying to MAINNET! This will cost real ETH!")
            response = input("Are you sure you want to continue? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Deployment cancelled.")
                return
                
    except Exception as e:
        print(f"⚠️  Could not fetch network info: {e}")

    # ✅ Read contract source
    with open('ComplaintContract.sol', 'r') as file:
        contract_source = file.read()

    # ✅ Compile contract using the installed version
    print("🔨 Compiling contract...")
    compiled_sol = compile_source(contract_source, solc_version=SOLC_VERSION)
    contract_interface = compiled_sol['<stdin>:ComplaintContract']

    # ✅ Get account from private key
    private_key = os.getenv('PRIVATE_KEY')
    if not private_key or private_key == "your_private_key_here":
        print("❌ Please set a valid PRIVATE_KEY in .env")
        return

    account = w3.eth.account.from_key(private_key)
    print(f"👤 Deploying from account: {account.address}")
    
    # Check balance
    balance = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance, 'ether')
    print(f"💰 Account balance: {balance_eth:.6f} ETH")
    
    if balance_eth < 0.01:
        print("⚠️  Low balance! You might not have enough ETH for gas fees.")
        if chain_id == 11155111:
            print("💡 Get Sepolia ETH from: https://sepoliafaucet.com/")
        elif chain_id == 5:
            print("💡 Get Goerli ETH from: https://goerlifaucet.com/")

    # ✅ Create contract instance
    contract = w3.eth.contract(
        abi=contract_interface['abi'],
        bytecode=contract_interface['bin']
    )

    # Estimate gas
    try:
        gas_estimate = contract.constructor().estimate_gas({'from': account.address})
        print(f"⛽ Estimated gas: {gas_estimate}")
    except Exception as e:
        print(f"⚠️  Could not estimate gas: {e}")
        gas_estimate = 3000000

    # ✅ Build transaction
    print("📝 Building transaction...")
    gas_price = w3.to_wei(str(os.getenv('GAS_PRICE', '20')), 'gwei')
    
    transaction = contract.constructor().build_transaction({
        'from': account.address,
        'gas': max(gas_estimate + 100000, 3000000),
        'gasPrice': gas_price,
        'nonce': w3.eth.get_transaction_count(account.address)
    })

    # Calculate estimated cost
    estimated_cost = transaction['gas'] * gas_price
    estimated_cost_eth = w3.from_wei(estimated_cost, 'ether')
    print(f"💸 Estimated deployment cost: {estimated_cost_eth:.6f} ETH")

    # ✅ Sign and send
    print("✍️  Signing transaction...")
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
    
    print("📤 Sending transaction...")
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)  # ✅ Updated for Web3 v7

    print(f"📋 Transaction hash: {tx_hash.hex()}")
    print("⏳ Waiting for transaction receipt...")
    
    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
    except Exception as e:
        print(f"❌ Transaction failed or timed out: {e}")
        return

    print(f"✅ Contract deployed successfully!")
    print(f"📍 Contract address: {receipt.contractAddress}")
    print(f"🔗 Transaction hash: {receipt.transactionHash.hex()}")
    print(f"⛽ Gas used: {receipt.gasUsed}")
    print(f"📦 Block number: {receipt.blockNumber}")

    if chain_id == 11155111:
        explorer_base = "https://sepolia.etherscan.io"
    elif chain_id == 5:
        explorer_base = "https://goerli.etherscan.io"
    elif chain_id == 1:
        explorer_base = "https://etherscan.io"
    else:
        explorer_base = None

    if explorer_base:
        print(f"🔍 View on Etherscan:")
        print(f"   Contract: {explorer_base}/address/{receipt.contractAddress}")
        print(f"   Transaction: {explorer_base}/tx/{receipt.transactionHash.hex()}")

    # ✅ Save contract details
    contract_info = {
        'address': receipt.contractAddress,
        'abi': contract_interface['abi'],
        'transaction_hash': receipt.transactionHash.hex(),
        'block_number': receipt.blockNumber,
        'gas_used': receipt.gasUsed,
        'network': network_name,
        'chain_id': chain_id,
        'deployment_cost_eth': float(estimated_cost_eth),
        'deployed_at': time.time()
    }

    with open('../contract_info.json', 'w') as f:
        json.dump(contract_info, f, indent=2)

    print("💾 Contract info saved to contract_info.json")
    return receipt.contractAddress


if __name__ == "__main__":
    deploy_contract()
