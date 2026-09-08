@echo off
echo 🚀 Complaint Classifier Testnet Deployment Script
echo ================================================

echo.
echo 📋 Step 1: Checking setup...
python testnet_setup_checker.py

echo.
echo ⏸️  Press any key to continue with deployment (or Ctrl+C to cancel)...
pause >nul

echo.
echo 📋 Step 2: Installing dependencies...
pip install -r requirements.txt

echo.
echo 📋 Step 3: Deploying smart contract...
cd contracts
python deploy.py
cd ..

echo.
echo 📋 Step 4: Starting the application...
echo 🌐 Your complaint classifier will be available at: http://localhost:5000
echo 📱 Connect your MetaMask wallet to interact with the blockchain
echo.
python app.py

pause
