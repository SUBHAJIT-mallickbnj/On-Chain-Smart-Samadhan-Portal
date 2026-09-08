#!/usr/bin/env python3
"""
Quick test script to verify blockchain connection and contract interaction
"""

import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from blockchain_manager import BlockchainManager
from config import Config

def test_blockchain_connection():
    """Test basic blockchain connectivity"""
    print("🔍 Testing Blockchain Connection")
    print("=" * 40)
    
    # Initialize blockchain manager
    bm = BlockchainManager()
    
    # Test connection
    if not bm.is_connected():
        print("❌ Blockchain connection failed!")
        return False
    
    # Get network info
    network_info = bm.get_network_info()
    print(f"✅ Connected to: {network_info['network_name']}")
    print(f"📊 Chain ID: {network_info['chain_id']}")
    print(f"📦 Latest Block: {network_info['latest_block']}")
    print(f"📍 Contract: {network_info['contract_address']}")
    
    if network_info['explorer_url']:
        print(f"🔍 Explorer: {network_info['explorer_url']}")
    
    return True

def test_wallet_balance():
    """Test wallet balance"""
    print("\n💰 Testing Wallet Balance")
    print("=" * 40)
    
    try:
        from web3 import Web3
        w3 = Web3(Web3.HTTPProvider(Config.BLOCKCHAIN_NETWORK))
        account = w3.eth.account.from_key(Config.PRIVATE_KEY)
        
        balance = w3.eth.get_balance(account.address)
        balance_eth = w3.from_wei(balance, 'ether')
        
        print(f"👤 Wallet: {account.address}")
        print(f"💸 Balance: {balance_eth:.6f} ETH")
        
        if balance_eth < 0.001:
            print("⚠️  Warning: Low balance for gas fees!")
            return False
        else:
            print("✅ Sufficient balance for transactions")
            return True
            
    except Exception as e:
        print(f"❌ Error checking balance: {e}")
        return False

def test_contract_call():
    """Test a simple contract read call"""
    print("\n📄 Testing Contract Read Call")
    print("=" * 40)
    
    bm = BlockchainManager()
    
    try:
        # Try to call a view function that doesn't modify state
        # This should work even without gas
        if hasattr(bm.contract.functions, 'owner'):
            owner = bm.contract.functions.owner().call()
            print(f"✅ Contract owner: {owner}")
        else:
            print("ℹ️  Owner function not available, but contract is accessible")
        
        return True
        
    except Exception as e:
        print(f"❌ Contract call failed: {e}")
        return False

def test_simple_transaction():
    """Test a simple blockchain transaction (gas estimation)"""
    print("\n⛽ Testing Transaction Gas Estimation")
    print("=" * 40)
    
    bm = BlockchainManager()
    
    try:
        # Test data
        test_ref = "TEST123"
        test_hash = "0x" + "a" * 64  # Mock hash
        test_dept = "Testing"
        test_status = "Test"
        test_wallet = "0x" + "1" * 40  # Mock wallet address
        
        # Try to estimate gas for submitComplaintForUser
        if hasattr(bm.contract.functions, 'submitComplaintForUser'):
            gas_estimate = bm.contract.functions.submitComplaintForUser(
                test_ref, test_hash, test_dept, test_status, test_wallet
            ).estimate_gas({'from': bm.w3.eth.account.from_key(Config.PRIVATE_KEY).address})
            
            print(f"✅ Gas estimate for complaint submission: {gas_estimate:,}")
            
            # Calculate cost
            gas_price = bm.w3.to_wei(str(Config.GAS_PRICE), 'gwei')
            cost_wei = gas_estimate * gas_price
            cost_eth = bm.w3.from_wei(cost_wei, 'ether')
            
            print(f"💸 Estimated cost: {cost_eth:.6f} ETH")
            
        else:
            print("ℹ️  submitComplaintForUser function not found, trying submitComplaint")
            
            gas_estimate = bm.contract.functions.submitComplaint(
                test_ref, test_hash, test_dept, test_status
            ).estimate_gas({'from': bm.w3.eth.account.from_key(Config.PRIVATE_KEY).address})
            
            print(f"✅ Gas estimate for complaint submission: {gas_estimate:,}")
        
        return True
        
    except Exception as e:
        print(f"❌ Gas estimation failed: {e}")
        print("💡 This might be normal if the contract function doesn't exist yet")
        return False

def main():
    """Run all tests"""
    print("🧪 Blockchain Manager Test Suite")
    print("=" * 50)
    print(f"⏰ Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("Blockchain Connection", test_blockchain_connection),
        ("Wallet Balance", test_wallet_balance), 
        ("Contract Read Call", test_contract_call),
        ("Transaction Gas Estimation", test_simple_transaction),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} threw exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your blockchain setup is working correctly.")
        print("\n📝 You can now submit complaints to the blockchain!")
    else:
        print(f"⚠️  {total - passed} test(s) failed. Please check the issues above.")
        
        if passed >= 2:  # At least connection and balance work
            print("💡 Basic connectivity works - you may still be able to submit complaints.")

if __name__ == "__main__":
    main()
