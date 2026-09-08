import os
from dotenv import load_dotenv
import json

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Blockchain Configuration
    BLOCKCHAIN_NETWORK = os.getenv('BLOCKCHAIN_NETWORK', 'https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID')
    PRIVATE_KEY = os.getenv('PRIVATE_KEY')
    INFURA_PROJECT_ID = os.getenv('INFURA_PROJECT_ID')
    
    # Network Detection
    IS_TESTNET = 'sepolia' in BLOCKCHAIN_NETWORK.lower() or 'goerli' in BLOCKCHAIN_NETWORK.lower() or 'mumbai' in BLOCKCHAIN_NETWORK.lower()
    
    # Load contract info if exists
    CONTRACT_ADDRESS = None
    CONTRACT_ABI = None
    
    if os.path.exists('contract_info.json'):
        with open('contract_info.json', 'r') as f:
            contract_info = json.load(f)
            CONTRACT_ADDRESS = contract_info.get('address')
            CONTRACT_ABI = contract_info.get('abi')
    
    # Gas configuration (adjusted for testnet)
    GAS_LIMIT = int(os.getenv('GAS_LIMIT', 3000000))
    GAS_PRICE = int(os.getenv('GAS_PRICE', 20))  # gwei

    # Cloudinary media storage
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', '')
    CLOUDINARY_API_KEY    = os.getenv('CLOUDINARY_API_KEY', '')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', '')
    
    # Testnet specific configurations
    SEPOLIA_CHAIN_ID = 11155111
    GOERLI_CHAIN_ID = 5
    
    # Block explorers for different networks
    BLOCK_EXPLORERS = {
        'sepolia': 'https://sepolia.etherscan.io',
        'goerli': 'https://goerli.etherscan.io',
        'mainnet': 'https://etherscan.io'
    }
    
    @classmethod
    def get_block_explorer_url(cls):
        """Get the appropriate block explorer URL based on the network"""
        if 'sepolia' in cls.BLOCKCHAIN_NETWORK.lower():
            return cls.BLOCK_EXPLORERS['sepolia']
        elif 'goerli' in cls.BLOCKCHAIN_NETWORK.lower():
            return cls.BLOCK_EXPLORERS['goerli']
        else:
            return cls.BLOCK_EXPLORERS['mainnet']