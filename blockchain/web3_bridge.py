import hashlib
import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

class DLTBridge:
    """
    Bridge to interact with DLT (Distributed Ledger Technology).
    Connects to local Hardhat node by default, with mock-mode fallback.
    
    Environment Variables:
    - WEB3_PROVIDER_URL: Ethereum/Polygon RPC endpoint (default: http://localhost:8545 for Hardhat)
    - WEB3_CONTRACT_ADDRESS: Smart contract address (optional)
    - WEB3_PRIVATE_KEY: Private key for transaction signing (optional)
    
    If Hardhat node is offline or credentials are not provided, operates in mock-mode.
    """
    
    def __init__(self):
        # Default to local Hardhat node
        self.provider_url = os.getenv('WEB3_PROVIDER_URL', 'http://localhost:8545')
        self.contract_address = os.getenv('WEB3_CONTRACT_ADDRESS')
        self.private_key = os.getenv('WEB3_PRIVATE_KEY')
        
        self.w3 = None
        self.mock_mode = True  # Start in mock mode until connection verified
        
        # Try to connect to Hardhat node
        try:
            self.w3 = Web3(Web3.HTTPProvider(self.provider_url, request_kwargs={'timeout': 5}))
            
            # Check if node is online
            if self.w3.is_connected():
                try:
                    # Try to get block number to verify connection
                    block_number = self.w3.eth.block_number
                    print(f"[DLT Bridge] Connected to Hardhat node at {self.provider_url} (Block: {block_number})")
                    
                    # Check if we have contract address and private key for real transactions
                    if self.contract_address and self.private_key:
                        # Verify contract address is valid
                        if Web3.is_address(self.contract_address):
                            self.mock_mode = False
                            print(f"[DLT Bridge] Ready for blockchain transactions (Contract: {self.contract_address[:10]}...)")
                        else:
                            print(f"[DLT Bridge] Invalid contract address. Running in mock mode.")
                    else:
                        print(f"[DLT Bridge] Contract address or private key not set. Running in mock mode.")
                        print(f"[DLT Bridge] Set WEB3_CONTRACT_ADDRESS and WEB3_PRIVATE_KEY for real transactions.")
                except Exception as e:
                    print(f"[DLT Bridge] Node connection test failed: {e}. Running in mock mode.")
                    self.mock_mode = True
            else:
                print(f"[DLT Bridge] Cannot connect to node at {self.provider_url}. Running in mock mode.")
                print(f"[DLT Bridge] Start Hardhat node with: npx hardhat node")
                self.mock_mode = True
        except Exception as e:
            print(f"[DLT Bridge] Connection error: {e}. Running in mock mode.")
            print(f"[DLT Bridge] Start Hardhat node with: npx hardhat node")
            self.mock_mode = True
    
    def log_commit_data(self, commit_hash, risk_score, status):
        """
        Logs commit data to blockchain or mock storage.
        
        Args:
            commit_hash: Hash of the commit (string)
            risk_score: Predicted risk score 0-100 (numeric)
            status: 'Accepted' or 'Rollback Enforced' (string)
        
        Returns:
            Transaction hash (mock or real)
        """
        if self.mock_mode:
            return self._mock_log(commit_hash, risk_score, status)
        else:
            try:
                return self._web3_log(commit_hash, risk_score, status)
            except Exception as e:
                print(f"[DLT Bridge] Web3 logging failed: {e}. Fallback to mock mode.")
                return self._mock_log(commit_hash, risk_score, status)
    
    def _mock_log(self, commit_hash, risk_score, status):
        """
        Mock logging for when blockchain is unavailable.
        """
        print(f"[DLT Bridge - MOCK] Logging commit:")
        print(f"  Commit Hash: {commit_hash}")
        print(f"  Risk Score: {risk_score}%")
        print(f"  Status: {status}")
        
        mock_tx_hash = hashlib.sha256(
            f"{commit_hash}{risk_score}{status}".encode()
        ).hexdigest()[:16]
        
        print(f"  Mock TX Hash: {mock_tx_hash}")
        
        return mock_tx_hash
    
    def _web3_log(self, commit_hash, risk_score, status):
        """
        Real blockchain logging via Web3.py to Hardhat node.
        """
        try:
            account = self.w3.eth.account.from_key(self.private_key)
            
            risk_score_int = int(risk_score)
            
            print(f"[DLT Bridge - WEB3] Sending to blockchain:")
            print(f"  Commit Hash: {commit_hash}")
            print(f"  Risk Score: {risk_score_int}%")
            print(f"  Status: {status}")
            print(f"  From: {account.address}")
            
            # Get current nonce
            nonce = self.w3.eth.get_transaction_count(account.address)
            
            # Get gas price (use 0 for Hardhat local network)
            try:
                gas_price = self.w3.eth.gas_price
            except:
                gas_price = 0  # Hardhat local network uses 0 gas price
            
            # Encode transaction data
            tx_data = self._encode_commit_data(commit_hash, risk_score_int, status)
            
            tx = {
                'from': account.address,
                'to': self.contract_address,
                'value': 0,
                'gas': 100000,
                'gasPrice': gas_price,
                'nonce': nonce,
                'data': tx_data
            }
            
            # Sign transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            
            # Send transaction
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = self.w3.to_hex(tx_hash)
            
            # Wait for transaction receipt (optional, for Hardhat it's instant)
            try:
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=10)
                print(f"  TX Hash: {tx_hash_hex}")
                print(f"  Status: {'Success' if receipt.status == 1 else 'Failed'}")
            except:
                print(f"  TX Hash: {tx_hash_hex}")
            
            return tx_hash_hex[:16]
            
        except Exception as e:
            raise Exception(f"Web3 transaction failed: {str(e)}")
    
    def _encode_commit_data(self, commit_hash, risk_score, status):
        """
        Encodes commit data for blockchain submission.
        """
        # Pad commit_hash to 32 bytes (64 hex chars)
        commit_hash_padded = commit_hash.ljust(64, '0')[:64]
        
        # Encode status (1 byte: 0x01 = Accepted, 0x00 = Rollback Enforced)
        status_byte = b'\x01' if status == 'Accepted' else b'\x00'
        
        # Encode risk score (1 byte: 0-100)
        risk_byte = bytes([min(100, max(0, int(risk_score)))])
        
        # Combine: commit_hash (32 bytes) + status (1 byte) + risk_score (1 byte)
        data_hex = commit_hash_padded + status_byte.hex() + risk_byte.hex()
        
        return '0x' + data_hex
    
    def is_connected(self) -> bool:
        """Check if connected to blockchain node."""
        return not self.mock_mode and self.w3 is not None and self.w3.is_connected()
    
    def get_mode(self) -> str:
        """Get current mode: 'blockchain' or 'mock'."""
        return 'blockchain' if not self.mock_mode else 'mock'
