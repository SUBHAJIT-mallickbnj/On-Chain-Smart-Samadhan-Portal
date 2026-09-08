#!/usr/bin/env python3
"""
Testnet Setup Helper Script
This script helps you configure and deploy to Ethereum testnets
"""

import os
import sys
from web3 import Web3
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def check_environment():
    """Check if all required environment variables are set"""
    print("🔍 Checking environment configuration...")
    
    required_vars = [
        'BLOCKCHAIN_NETWORK',
        'PRIVATE_KEY',
        'INFURA_PROJECT_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var) or os.getenv(var) == f"your_{var.lower()}_here":
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("📝 Please update your .env file with the correct values")
        return False
    
    print("✅ Environment variables configured")
    return True

def check_network_connection():
    """Test connection to the blockchain network"""
    print("🌐 Testing blockchain network connection...")
    
    try:
        blockchain_network = os.getenv('BLOCKCHAIN_NETWORK')
        w3 = Web3(Web3.HTTPProvider(blockchain_network))
        
        if not w3.is_connected():
            print("❌ Failed to connect to blockchain network")
            print(f"Network URL: {blockchain_network}")
            return False
        
        # Get network info
        chain_id = w3.eth.chain_id
        latest_block = w3.eth.block_number
        
        network_names = {
            1: "Ethereum Mainnet",
            11155111: "Sepolia Testnet", 
            5: "Goerli Testnet",
            137: "Polygon Mainnet",
            80001: "Mumbai Testnet"
        }
        
        network_name = network_names.get(chain_id, f"Unknown Network (Chain ID: {chain_id})")
        
        print(f"✅ Connected to {network_name}")
        print(f"📊 Chain ID: {chain_id}")
        print(f"📦 Latest Block: {latest_block}")
        
        if chain_id == 1:
            print("⚠️  WARNING: You're connected to MAINNET! Switch to testnet for development.")
            return False
            
        return True, chain_id, network_name
        
    except Exception as e:
        print(f"❌ Network connection error: {e}")
        return False

def check_wallet_balance():
    """Check wallet balance and provide faucet links if needed"""
    print("💰 Checking wallet balance...")
    
    try:
        blockchain_network = os.getenv('BLOCKCHAIN_NETWORK')
        private_key = os.getenv('PRIVATE_KEY')
        
        w3 = Web3(Web3.HTTPProvider(blockchain_network))
        account = w3.eth.account.from_key(private_key)
        
        balance = w3.eth.get_balance(account.address)
        balance_eth = w3.from_wei(balance, 'ether')
        
        print(f"👤 Wallet Address: {account.address}")
        print(f"💸 Balance: {balance_eth:.6f} ETH")
        
        chain_id = w3.eth.chain_id
        
        if balance_eth < 0.01:
            print("⚠️  Low balance! You need more ETH for gas fees.")
            
            if chain_id == 11155111:  # Sepolia
                print("🚰 Get Sepolia ETH from these faucets:")
                print("   • https://sepoliafaucet.com/")
                print("   • https://sepolia-faucet.pk910.de/")
                print("   • https://faucet.quicknode.com/ethereum/sepolia")
            elif chain_id == 5:  # Goerli
                print("🚰 Get Goerli ETH from these faucets:")
                print("   • https://goerlifaucet.com/")
                print("   • https://faucets.chain.link/goerli")
            
            return False
        
        print("✅ Sufficient balance for deployment")
        return True
        
    except Exception as e:
        print(f"❌ Error checking wallet balance: {e}")
        return False

def estimate_deployment_cost():
    """Estimate the cost of deploying the contract"""
    print("⛽ Estimating deployment cost...")
    
    try:
        blockchain_network = os.getenv('BLOCKCHAIN_NETWORK')
        w3 = Web3(Web3.HTTPProvider(blockchain_network))
        
        # Estimate gas (rough estimate)
        estimated_gas = 2500000  # Typical contract deployment
        gas_price = w3.to_wei(str(os.getenv('GAS_PRICE', '20')), 'gwei')
        
        estimated_cost = estimated_gas * gas_price
        estimated_cost_eth = w3.from_wei(estimated_cost, 'ether')
        
        print(f"📊 Estimated gas: {estimated_gas:,}")
        print(f"💸 Estimated cost: {estimated_cost_eth:.6f} ETH")
        
        return True
        
    except Exception as e:
        print(f"❌ Error estimating costs: {e}")
        return False

def check_contract_deployed():
    """Check if contract is already deployed"""
    print("📄 Checking contract deployment status...")
    
    if os.path.exists('contract_info.json'):
        try:
            with open('contract_info.json', 'r') as f:
                contract_info = json.load(f)
            
            print("✅ Contract already deployed!")
            print(f"📍 Address: {contract_info.get('address')}")
            print(f"🌍 Network: {contract_info.get('network', 'Unknown')}")
            
            if contract_info.get('chain_id') == 11155111:
                print(f"🔍 View on Sepolia Etherscan: https://sepolia.etherscan.io/address/{contract_info.get('address')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error reading contract info: {e}")
    
    print("📄 No contract deployed yet")
    return False

def main():
    """Main setup verification function"""
    print("🚀 Complaint Classifier Testnet Setup Checker")
    print("=" * 50)
    
    # Check each requirement
    checks = [
        ("Environment Configuration", check_environment),
        ("Network Connection", check_network_connection),
        ("Wallet Balance", check_wallet_balance),
        ("Deployment Cost Estimation", estimate_deployment_cost),
        ("Contract Status", check_contract_deployed),
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}")
        print("-" * 30)
        
        try:
            result = check_func()
            if not result:
                all_passed = False
        except Exception as e:
            print(f"❌ {check_name} failed: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 All checks passed! You're ready to deploy.")
        print("\n📝 Next steps:")
        print("1. cd contracts")
        print("2. python deploy.py")
        print("3. cd ..")
        print("4. python app.py")
    else:
        print("❌ Some checks failed. Please fix the issues above before deploying.")
        print("\n💡 See TESTNET_DEPLOYMENT_GUIDE.md for detailed instructions")

if __name__ == "__main__":
    main()
