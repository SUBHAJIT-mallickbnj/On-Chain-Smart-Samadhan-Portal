# 🌐 Deploy Complaint Classifier to Blockchain Testnet

This guide will help you deploy your complaint classifier to a real blockchain testnet (Sepolia) instead of running locally.

## 📋 Prerequisites

1. **MetaMask Wallet** - Install from [metamask.io](https://metamask.io)
2. **Infura Account** - Sign up at [infura.io](https://infura.io) for RPC access
3. **Sepolia Test ETH** - Get from faucets for gas fees

## 🛠️ Setup Steps

### Step 1: Configure Environment

1. **Copy the environment template:**
   ```powershell
   copy .env.example .env
   ```

2. **Edit the `.env` file with your details:**
   ```env
   # Flask Configuration
   FLASK_SECRET_KEY=your-super-secret-key-here-change-in-production

   # Blockchain Configuration - Sepolia Testnet
   BLOCKCHAIN_NETWORK=https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID

   # Your Ethereum Private Key (with Sepolia ETH for gas fees)
   PRIVATE_KEY=your_private_key_here

   # Infura Project ID
   INFURA_PROJECT_ID=your_infura_project_id_here

   # Gas Configuration for Sepolia
   GAS_LIMIT=3000000
   GAS_PRICE=20
   ```

### Step 2: Get Infura Project ID

1. Go to [infura.io](https://infura.io) and create an account
2. Create a new project
3. Select "Ethereum" network
4. Copy your Project ID from the dashboard
5. Replace `YOUR_INFURA_PROJECT_ID` in your `.env` file

### Step 3: Setup MetaMask for Sepolia

1. Open MetaMask
2. Click on the network dropdown (usually shows "Ethereum Mainnet")
3. Enable "Show test networks" in Settings > Advanced
4. Select "Sepolia test network"

### Step 4: Get Sepolia Test ETH

You need Sepolia ETH to pay for gas fees. Get it from these faucets:

1. **Official Sepolia Faucet:** https://sepoliafaucet.com/
2. **Alchemy Faucet:** https://sepoliafaucet.com/
3. **Chainlink Faucet:** https://faucets.chain.link/

**Requirements:**
- You'll need at least 0.1 ETH for deployment
- Some faucets require social media verification

### Step 5: Export Your Private Key

⚠️ **WARNING: Never share your private key or commit it to version control!**

1. Open MetaMask
2. Click on account menu (3 dots)
3. Go to "Account Details"
4. Click "Export Private Key"
5. Enter your MetaMask password
6. Copy the private key (starts with 0x)
7. Add it to your `.env` file

### Step 6: Deploy Smart Contract

1. **Navigate to the contracts directory:**
   ```powershell
   cd contracts
   ```

2. **Run the deployment script:**
   ```powershell
   python deploy.py
   ```

3. **Expected output:**
   ```
   🔍 Installing Solidity 0.8.19...
   🌐 Connecting to: https://sepolia.infura.io/v3/your_project_id
   ✅ Connected to blockchain.
   📊 Chain ID: 11155111
   📦 Latest Block: 4567890
   🌍 Network: Sepolia Testnet
   👤 Deploying from account: 0xYourAddress...
   💰 Account balance: 0.123456 ETH
   🔨 Compiling contract...
   📝 Building transaction...
   ⛽ Estimated gas: 2456789
   💸 Estimated deployment cost: 0.049136 ETH
   ✍️  Signing transaction...
   📤 Sending transaction...
   📋 Transaction hash: 0xabcd1234...
   ⏳ Waiting for transaction receipt...
   ✅ Contract deployed successfully!
   📍 Contract address: 0x1234567890abcdef...
   🔗 Transaction hash: 0xabcd1234...
   ⛽ Gas used: 2344567
   📦 Block number: 4567891
   🔍 View on Sepolia Etherscan:
      Contract: https://sepolia.etherscan.io/address/0x1234567890abcdef...
      Transaction: https://sepolia.etherscan.io/tx/0xabcd1234...
   💾 Contract info saved to contract_info.json
   ```

### Step 7: Start Your Application

1. **Return to main directory:**
   ```powershell
   cd ..
   ```

2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```powershell
   python app.py
   ```

## 🔍 Tracking Your Complaints

### On Sepolia Etherscan

1. Visit [sepolia.etherscan.io](https://sepolia.etherscan.io)
2. Search for your contract address or transaction hash
3. View all transactions and contract interactions

### In Your Application

1. **Submit a complaint** - Get transaction hash and block confirmation
2. **Track complaints** - Use reference number to see blockchain status
3. **View history** - See all your complaints with blockchain links

## 🌍 Network Information

### Sepolia Testnet Details:
- **Chain ID:** 11155111
- **Explorer:** https://sepolia.etherscan.io
- **Faucets:** Multiple available (see Step 4)
- **Purpose:** Ethereum test network

### Alternative Networks:

You can also use other testnets by changing the `BLOCKCHAIN_NETWORK` in `.env`:

- **Goerli:** `https://goerli.infura.io/v3/YOUR_PROJECT_ID`
- **Mumbai (Polygon):** `https://rpc-mumbai.maticvigil.com`

## 🚨 Security Best Practices

1. **Never share your private key**
2. **Use test networks only** for development
3. **Keep your `.env` file secure** (add to .gitignore)
4. **Use separate wallets** for development and production
5. **Regular backups** of important data

## 🐛 Troubleshooting

### Common Issues:

1. **"Insufficient funds for gas"**
   - Get more Sepolia ETH from faucets
   - Check gas price settings

2. **"Connection failed"**
   - Verify Infura project ID
   - Check network connectivity

3. **"Contract deployment failed"**
   - Ensure sufficient ETH balance
   - Check Solidity compiler version

4. **"Transaction stuck"**
   - Increase gas price
   - Wait for network congestion to clear

### Getting Help:

1. Check the console output for error messages
2. Verify all environment variables are set correctly
3. Ensure you have sufficient test ETH
4. Check Sepolia network status

## 📊 Monitoring

After deployment, you can monitor:

1. **Contract activity** on Sepolia Etherscan
2. **Gas costs** for optimization
3. **Transaction confirmations** for reliability
4. **User complaints** through the application

Your complaints are now permanently recorded on the Sepolia blockchain and can be tracked and verified by anyone! 🎉
