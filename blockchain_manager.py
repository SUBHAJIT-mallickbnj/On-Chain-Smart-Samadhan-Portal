# -*- coding: utf-8 -*-
import sys
import io
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from web3 import Web3
from web3.providers import HTTPProvider
import hashlib
import json
from datetime import datetime
from config import Config
from requests import Session
import requests
import threading
import time

class BlockchainManager:
    def __init__(self):
        self.w3 = Web3()
        self.contract = None
        self.network_info = None
        self.connected = False
        self._connection_lock = threading.Lock()
        
        try:
            # Try to connect to blockchain in a separate thread with timeout
            connection_thread = threading.Thread(target=self._connect_to_blockchain, daemon=True)
            connection_thread.start()
            connection_thread.join(timeout=5)  # Wait max 5 seconds for connection
            
            if not self.connected:
                print("[ERROR] Blockchain connection timeout - network may be unreachable or too slow")
            
        except Exception as e:
            print(f"[ERROR] Failed to initialize blockchain manager: {e}")
            self.w3 = Web3()
            self.contract = None
            self.network_info = None
    
    def _connect_to_blockchain(self):
        """Connect to blockchain in a separate thread"""
        try:
            # Create a session with timeout for the HTTP provider
            session = Session()
            session.timeout = 5
            provider = HTTPProvider(
                Config.BLOCKCHAIN_NETWORK,
                session=session,
                request_kwargs={"timeout": 5},
            )
            self.w3 = Web3(provider)
            
            # Try to connect
            if self.w3.is_connected():
                try:
                    self.network_info = {
                        'chain_id': self.w3.eth.chain_id,
                        'latest_block': self.w3.eth.block_number,
                        'is_testnet': Config.IS_TESTNET,
                        'explorer_url': Config.get_block_explorer_url()
                    }
                    print(f"[OK] Connected to {self._get_network_name()}")
                except Exception as e:
                    print(f"[ERROR] Error getting network info: {e}")
            
                if Config.CONTRACT_ADDRESS and Config.CONTRACT_ABI:
                    try:
                        self.contract = self.w3.eth.contract(
                            address=Web3.to_checksum_address(Config.CONTRACT_ADDRESS),
                            abi=Config.CONTRACT_ABI
                        )
                        print("[OK] Blockchain connected and contract loaded")
                        print(f"[INFO] Contract address: {Config.CONTRACT_ADDRESS}")
                        if self.network_info:
                            print(f"[INFO] View contract: {self.network_info['explorer_url']}/address/{Config.CONTRACT_ADDRESS}")
                    except Exception as e:
                        print(f"[ERROR] Contract loading failed: {e}")
                else:
                    print("[ERROR] Blockchain connection or contract loading failed")
                
                self.connected = True
            else:
                print("[ERROR] Failed to connect to blockchain")
                
        except requests.exceptions.Timeout:
            print("[ERROR] Blockchain connection timeout - network may be unreachable")
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Blockchain connection error: {e}")
        except Exception as e:
            print(f"[ERROR] Error connecting to blockchain: {e}")
    
    def _get_network_name(self):
        """Get human-readable network name"""
        if not self.network_info:
            return "Unknown Network"
        
        network_names = {
            1: "Ethereum Mainnet",
            11155111: "Sepolia Testnet", 
            5: "Goerli Testnet",
            137: "Polygon Mainnet",
            80001: "Mumbai Testnet"
        }
        return network_names.get(self.network_info['chain_id'], f"Unknown Network (Chain ID: {self.network_info['chain_id']})")
    
    def get_network_info(self):
        """Get current network information"""
        return {
            **(self.network_info or {
                'chain_id': None,
                'latest_block': None,
                'is_testnet': Config.IS_TESTNET,
                'explorer_url': Config.get_block_explorer_url(),
            }),
            'network_name': self._get_network_name(),
            'contract_address': Config.CONTRACT_ADDRESS
        }
    
    def is_connected(self):
        if self.connected and self.contract is not None:
            try:
                return self.w3.is_connected()
            except Exception:
                self.connected = False

        with self._connection_lock:
            if not self.connected:
                self._connect_to_blockchain()
        return self.connected and self.contract is not None
    
    def is_valid_address(self, address):
        """Validate Ethereum address"""
        try:
            return Web3.is_address(address)
        except:
            return False
    
    def hash_complaint_data(self, complaint_data):
        """Create a hash of sensitive complaint data"""
        data_string = f"{complaint_data['name']}{complaint_data['email']}{complaint_data['complaint']}{complaint_data['phone']}"
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def submit_complaint_to_blockchain(self, reference_no, complaint_data, department, user_wallet_address):
        """Submit complaint to blockchain with user's wallet address"""
        if not self.is_connected():
            return {"success": False, "message": "Blockchain not available"}
        
        try:
            # Hash sensitive data for privacy
            complaint_hash = self.hash_complaint_data(complaint_data)
            
            # Get account from private key (this is the contract owner/admin account)
            admin_account = self.w3.eth.account.from_key(Config.PRIVATE_KEY)
            
            # Check admin account balance
            balance = self.w3.eth.get_balance(admin_account.address)
            balance_eth = self.w3.from_wei(balance, 'ether')
            
            if balance_eth < 0.001:  # Less than 0.001 ETH
                return {
                    "success": False, 
                    "message": f"Insufficient balance for gas fees. Current balance: {balance_eth:.6f} ETH"
                }
            
            # Estimate gas for the transaction
            try:
                gas_estimate = self.contract.functions.submitComplaintForUser(
                    reference_no,
                    complaint_hash,
                    department,
                    "Submitted",
                    Web3.to_checksum_address(user_wallet_address)
                ).estimate_gas({'from': admin_account.address})
                
                # Add 20% buffer to gas estimate
                gas_limit = int(gas_estimate * 1.2)
            except Exception as e:
                print(f"⚠️  Could not estimate gas, using default: {e}")
                gas_limit = Config.GAS_LIMIT
            
            # Build transaction - submit on behalf of user but from admin account
            transaction = self.contract.functions.submitComplaintForUser(
                reference_no,
                complaint_hash,
                department,
                "Submitted",
                Web3.to_checksum_address(user_wallet_address)  # Pass user's wallet address
            ).build_transaction({
                'from': admin_account.address,
                'gas': gas_limit,
                'gasPrice': self.w3.to_wei(str(Config.GAS_PRICE), 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(admin_account.address)
            })
            
            # Calculate estimated cost
            estimated_cost = transaction['gas'] * transaction['gasPrice']
            estimated_cost_eth = self.w3.from_wei(estimated_cost, 'ether')
            
            print(f"💸 Estimated transaction cost: {estimated_cost_eth:.6f} ETH")
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, Config.PRIVATE_KEY)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            
            print(f"📤 Transaction sent: {tx_hash.hex()}")
            
            # Wait for transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            
            print(f"✅ Complaint {reference_no} submitted to blockchain for user {user_wallet_address}")
            
            # Generate explorer URLs
            explorer_url = self.network_info['explorer_url'] if self.network_info else Config.get_block_explorer_url()
            
            return {
                "success": True,
                "tx_hash": receipt.transactionHash.hex(),
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "actual_cost_eth": float(self.w3.from_wei(receipt.gasUsed * transaction['gasPrice'], 'ether')),
                "network": self._get_network_name(),
                "explorer_urls": {
                    "transaction": f"{explorer_url}/tx/0x{receipt.transactionHash.hex()}",
                    "contract": f"{explorer_url}/address/{Config.CONTRACT_ADDRESS}"
                }
            }
            
        except Exception as e:
            print(f"❌ Blockchain submission failed: {e}")
            # Fallback: Try with original method if the new method fails
            try:
                transaction = self.contract.functions.submitComplaint(
                    reference_no,
                    complaint_hash,
                    department,
                    "Submitted"
                ).build_transaction({
                    'from': admin_account.address,
                    'gas': Config.GAS_LIMIT,
                    'gasPrice': self.w3.to_wei(str(Config.GAS_PRICE), 'gwei'),
                    'nonce': self.w3.eth.get_transaction_count(admin_account.address)
                })
                
                signed_txn = self.w3.eth.account.sign_transaction(transaction, Config.PRIVATE_KEY)
                tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                
                explorer_url = self.network_info['explorer_url'] if self.network_info else Config.get_block_explorer_url()
                
                return {
                    "success": True,
                    "tx_hash": receipt.transactionHash.hex(),
                    "block_number": receipt.blockNumber,
                    "gas_used": receipt.gasUsed,
                    "network": self._get_network_name(),
                    "explorer_urls": {
                        "transaction": f"{explorer_url}/tx/0x{receipt.transactionHash.hex()}",
                        "contract": f"{explorer_url}/address/{Config.CONTRACT_ADDRESS}"
                    }
                }
            except Exception as e2:
                print(f"❌ Fallback blockchain submission also failed: {e2}")
                return {"success": False, "message": str(e2)}
    
    def get_complaint_from_blockchain(self, reference_no):
        """Retrieve complaint from blockchain"""
        if not self.is_connected():
            print("❌ Blockchain not connected")
            return None
        
        try:
            result = self.contract.functions.getComplaint(reference_no).call()
            return {
                "user": result[0],
                "complaint_hash": result[1],
                "department": result[2],
                "status": result[3],
                "timestamp": result[4],
                "formatted_date": datetime.fromtimestamp(result[4]).strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"❌ Error retrieving complaint {reference_no} from blockchain: {e}")
            return None
    
    def get_user_complaints(self, user_address):
        """Get all complaint reference numbers for a user"""
        if not self.is_connected():
            print("❌ Blockchain not connected")
            return []
        
        try:
            # Convert to checksum address
            checksum_address = Web3.to_checksum_address(user_address)
            result = self.contract.functions.getUserComplaints(checksum_address).call()
            print(f"✅ Found {len(result)} complaints on blockchain for {user_address}")
            return result
        except Exception as e:
            print(f"❌ Error retrieving user complaints for {user_address}: {e}")
            return []
    
    def verify_complaint_ownership(self, reference_no, user_address):
        """Verify if a complaint belongs to a specific user"""
        if not self.is_connected():
            print("❌ Blockchain not connected")
            return False
        
        try:
            checksum_address = Web3.to_checksum_address(user_address)
            result = self.contract.functions.verifyComplaintOwnership(reference_no, checksum_address).call()
            print(f"✅ Ownership verification for {reference_no}: {result}")
            return result
        except Exception as e:
            print(f"❌ Error verifying complaint ownership for {reference_no}: {e}")
            return False
    
    def get_transaction_details(self, tx_hash):
        """Get detailed information about a transaction"""
        if not self.w3.is_connected():
            return None
        
        try:
            # Get transaction details
            tx = self.w3.eth.get_transaction(tx_hash)
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            
            # Get current block for confirmations
            current_block = self.w3.eth.block_number
            confirmations = current_block - receipt.blockNumber
            
            explorer_url = self.network_info['explorer_url'] if self.network_info else Config.get_block_explorer_url()
            
            return {
                "hash": tx_hash,
                "block_number": receipt.blockNumber,
                "confirmations": confirmations,
                "gas_used": receipt.gasUsed,
                "gas_price": tx.gasPrice,
                "cost_eth": float(self.w3.from_wei(receipt.gasUsed * tx.gasPrice, 'ether')),
                "status": "Success" if receipt.status == 1 else "Failed",
                "timestamp": self.w3.eth.get_block(receipt.blockNumber).timestamp,
                "explorer_url": f"{explorer_url}/tx/{tx_hash if tx_hash.startswith('0x') else '0x' + tx_hash}",
                "from_address": tx["from"],
                "to_address": tx.to
            }
        except Exception as e:
            print(f"❌ Error getting transaction details: {e}")
            return None

    def update_complaint_status(self, reference_no, new_status):
        """Update complaint status (admin function)"""
        if not self.is_connected():
            return {"success": False, "message": "Blockchain not available"}
        
        try:
            account = self.w3.eth.account.from_key(Config.PRIVATE_KEY)
            
            # Estimate gas
            try:
                gas_estimate = self.contract.functions.updateComplaintStatus(
                    reference_no, new_status
                ).estimate_gas({'from': account.address})
                gas_limit = int(gas_estimate * 1.2)
            except:
                gas_limit = Config.GAS_LIMIT
            
            transaction = self.contract.functions.updateComplaintStatus(
                reference_no,
                new_status
            ).build_transaction({
                'from': account.address,
                'gas': gas_limit,
                'gasPrice': self.w3.to_wei(str(Config.GAS_PRICE), 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(account.address)
            })
            
            signed_txn = self.w3.eth.account.sign_transaction(transaction, Config.PRIVATE_KEY)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            explorer_url = self.network_info['explorer_url'] if self.network_info else Config.get_block_explorer_url()
            
            return {
                "success": True,
                "tx_hash": receipt.transactionHash.hex(),
                "explorer_url": f"{explorer_url}/tx/0x{receipt.transactionHash.hex()}"
            }
            
        except Exception as e:
            return {"success": False, "message": str(e)}

    def mark_complaint_as_solved(self, reference_no, user_wallet_address):
        """Mark complaint as solved on blockchain"""
        if not self.is_connected():
            return {"success": False, "message": "Blockchain not available"}
        
        try:
            # Verify user owns this complaint
            if not self.verify_complaint_ownership(reference_no, user_wallet_address):
                return {"success": False, "message": "You don't own this complaint"}
            
            account = self.w3.eth.account.from_key(Config.PRIVATE_KEY)
            
            # Estimate gas
            try:
                gas_estimate = self.contract.functions.updateComplaintStatus(
                    reference_no, "Solved"
                ).estimate_gas({'from': account.address})
                gas_limit = int(gas_estimate * 1.2)
            except:
                gas_limit = Config.GAS_LIMIT
            
            # Build transaction to mark as solved
            transaction = self.contract.functions.updateComplaintStatus(
                reference_no, 
                "Solved"
            ).build_transaction({
                'from': account.address,
                'gas': gas_limit,
                'gasPrice': self.w3.to_wei(str(Config.GAS_PRICE), 'gwei'),
                'nonce': self.w3.eth.get_transaction_count(account.address)
            })
            
            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(transaction, Config.PRIVATE_KEY)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            explorer_url = self.network_info['explorer_url'] if self.network_info else Config.get_block_explorer_url()
            
            print(f"✅ Complaint {reference_no} marked as solved on blockchain")
            
            return {
                "success": True,
                "tx_hash": receipt.transactionHash.hex(),
                "explorer_url": f"{explorer_url}/tx/0x{receipt.transactionHash.hex()}"
            }
            
        except Exception as e:
            print(f"❌ Failed to mark complaint as solved: {e}")
            return {"success": False, "message": str(e)}