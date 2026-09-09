// Web3 Integration for Wallet Connection
class WalletManager {
    constructor() {
        this.web3 = null;
        this.account = null;
        this.isConnected = false;
        this.mobileConnectRequested = new URLSearchParams(window.location.search).get('metamask') === 'connect';
        this.init();
    }

    async init() {
        if (this.mobileConnectRequested) {
            const url = new URL(window.location.href);
            url.searchParams.delete('metamask');
            window.history.replaceState({}, document.title, url.toString());
        }

        // Check if MetaMask is installed
        if (typeof window.ethereum !== 'undefined') {
            this.web3 = new Web3(window.ethereum);
            console.log('MetaMask detected');
            
            // Check if already connected
            const accounts = await window.ethereum.request({ method: 'eth_accounts' });
            if (accounts.length > 0) {
                this.account = accounts[0];
                this.isConnected = true;
                this.updateUI();
            } else if (this.mobileConnectRequested && this.isMobileDevice()) {
                await this.connectMetaMask();
            }
        } else {
            console.log('MetaMask not detected');
            this.showError('MetaMask not installed. Please install MetaMask to continue.');
        }
    }

    isMobileDevice() {
        return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    }

    openMetaMaskMobile() {
        const dappUrl = new URL(window.location.href);
        dappUrl.searchParams.set('metamask', 'connect');
        const dappPath = `${dappUrl.host}${dappUrl.pathname}${dappUrl.search}${dappUrl.hash}`;
        const metamaskUrl = `https://metamask.app.link/dapp/${dappPath}`;
        window.location.assign(metamaskUrl);
    }

    async connectMetaMask() {
        try {
            if (!window.ethereum) {
                if (this.isMobileDevice()) {
                    this.openMetaMaskMobile();
                    return;
                }
                throw new Error('MetaMask not installed');
            }

            // Request account access
            const accounts = await window.ethereum.request({
                method: 'eth_requestAccounts'
            });

            if (accounts.length === 0) {
                throw new Error('No accounts found');
            }

            this.account = accounts[0];
            this.isConnected = true;

            // Sign a message for authentication (optional)
            const message = `Login to Complaint System at ${new Date().toISOString()}`;
            const signature = await this.signMessage(message);

            // Send to backend
            const response = await fetch('/api/connect_wallet', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    address: this.account,
                    signature: signature,
                    message: message
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.updateUI();
                // Redirect to home after 2 seconds
                setTimeout(() => {
                    window.location.href = '/home';
                }, 2000);
            } else {
                throw new Error(result.message);
            }

        } catch (error) {
            console.error('Connection error:', error);
            this.showError(error.message);
        }
    }

    async signMessage(message) {
        try {
            const signature = await window.ethereum.request({
                method: 'personal_sign',
                params: [message, this.account]
            });
            return signature;
        } catch (error) {
            console.error('Signing error:', error);
            return '';
        }
    }

    updateUI() {
        const connectionDiv = document.getElementById('wallet-connection');
        const statusDiv = document.getElementById('wallet-status');
        const addressSpan = document.getElementById('connected-address');

        if (this.isConnected && this.account) {
            connectionDiv.classList.add('d-none');
            statusDiv.classList.remove('d-none');
            addressSpan.textContent = `${this.account.substring(0, 6)}...${this.account.substring(38)}`;
        }
    }

    showError(message) {
        const errorDiv = document.getElementById('wallet-error');
        const errorMessage = document.getElementById('error-message');
        
        errorDiv.classList.remove('d-none');
        errorMessage.textContent = message;
    }
}

// Initialize wallet manager
const walletManager = new WalletManager();

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    const connectBtn = document.getElementById('connect-metamask');
    
    if (connectBtn) {
        connectBtn.addEventListener('click', () => {
            walletManager.connectMetaMask();
        });
    }

    // Listen for account changes
    if (window.ethereum) {
        window.ethereum.on('accountsChanged', function(accounts) {
            if (accounts.length === 0) {
                // User disconnected
                window.location.href = '/logout';
            } else if (accounts[0] !== walletManager.account) {
                // User switched accounts
                window.location.reload();
            }
        });

        window.ethereum.on('chainChanged', function(chainId) {
            // User switched networks
            window.location.reload();
        });
    }
});