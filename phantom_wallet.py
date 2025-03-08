"""
Phantom wallet integration module for Solana transactions.
"""

import base64
import json
import time
import logging
import asyncio
import hashlib
from typing import Dict, Any, Optional
import requests
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solana.keypair import Keypair
from solana.publickey import PublicKey

logger = logging.getLogger(__name__)

class PhantomWalletIntegration:
    """
    Class to handle Phantom wallet integration via deep linking protocol
    and secure communication for transaction signing.
    """
    
    def __init__(self, network: str = "mainnet-beta"):
        """Initialize the Phantom wallet integration."""
        self.network = network
        self.solana_client = Client(f"https://api.{network}.solana.com")
        self.connected_wallets = {}
        
    def generate_connection_url(self, callback_url: str, user_id: str) -> str:
        """
        Generate a Phantom connection URL with callback.
        
        In a real implementation, this would create a deep link that opens
        Phantom and prompts the user to connect their wallet.
        
        Args:
            callback_url: URL where Phantom will send the connection response
            user_id: Unique identifier for the user
            
        Returns:
            Connection URL string
        """
        # Create a unique state to prevent CSRF attacks
        state = hashlib.sha256(f"{user_id}_{int(time.time())}".encode()).hexdigest()
        
        # In a real implementation, this would be a proper Phantom deep link
        # See: https://docs.phantom.app/integrating/deeplinks-protocol
        phantom_url = (
            f"https://phantom.app/ul/v1/connect?"
            f"app_url={callback_url}&"
            f"dapp_encryption_public_key={self._generate_dummy_key()}&"
            f"redirect_link={callback_url}/callback&"
            f"state={state}"
        )
        
        return phantom_url
    
    def _generate_dummy_key(self) -> str:
        """Generate a dummy public key for demonstration purposes."""
        return base64.b64encode(Keypair().public_key.to_bytes()).decode('utf-8')
    
    def process_connection_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the connection response from Phantom.
        
        Args:
            response_data: Data received from Phantom callback
            
        Returns:
            Dictionary with connection details
        """
        # In a real implementation, this would:
        # 1. Decrypt the data using our private key
        # 2. Verify the signature
        # 3. Store the connection details
        
        try:
            # Extract the public key
            public_key = response_data.get('public_key')
            if not public_key:
                return {'success': False, 'error': 'No public key provided'}
            
            # Store the connection
            user_id = response_data.get('user_id')
            self.connected_wallets[user_id] = {
                'public_key': public_key,
                'connection_time': time.time(),
                'last_active': time.time()
            }
            
            return {
                'success': True,
                'public_key': public_key,
                'user_id': user_id
            }
        
        except Exception as e:
            logger.error(f"Error processing connection response: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_wallet_balance(self, public_key: str) -> Dict[str, Any]:
        """
        Get the SOL balance for a wallet.
        
        Args:
            public_key: The wallet's public key
            
        Returns:
            Dictionary with balance information
        """
        try:
            # Convert string to PublicKey if needed
            if isinstance(public_key, str):
                public_key = PublicKey(public_key)
            
            response = self.solana_client.get_balance(public_key)
            
            if 'result' in response and 'value' in response['result']:
                lamports = response['result']['value']
                sol = lamports / 10**9  # Convert lamports to SOL
                
                return {
                    'success': True,
                    'balance_lamports': lamports,
                    'balance_sol': sol
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to get balance',
                    'response': response
                }
        
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            return {'success': False, 'error': str(e)}
    
    def create_transaction_link(self, 
                               transaction_data: Dict[str, Any], 
                               callback_url: str,
                               user_id: str) -> str:
        """
        Create a deep link for Phantom to sign and send a transaction.
        
        Args:
            transaction_data: Transaction data to be signed
            callback_url: URL where Phantom will send the transaction response
            user_id: Unique identifier for the user
            
        Returns:
            Deep link URL string
        """
        # Create a unique state to prevent CSRF attacks
        state = hashlib.sha256(f"{user_id}_{int(time.time())}".encode()).hexdigest()
        
        # In a real implementation, this would be a proper Phantom deep link
        # with the serialized transaction data
        # See: https://docs.phantom.app/integrating/deeplinks-protocol/signing-a-transaction
        phantom_url = (
            f"https://phantom.app/ul/v1/signTransaction?"
            f"app_url={callback_url}&"
            f"redirect_link={callback_url}/tx_callback&"
            f"state={state}"
        )
        
        return phantom_url
    
    async def process_transaction_response(self, 
                                         response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the transaction response from Phantom.
        
        Args:
            response_data: Data received from Phantom callback
            
        Returns:
            Dictionary with transaction details
        """
        # In a real implementation, this would:
        # 1. Verify the signature
        # 2. Submit the transaction to the network if needed
        # 3. Return the transaction details
        
        try:
            # Extract the signature
            signature = response_data.get('signature')
            if not signature:
                return {'success': False, 'error': 'No signature provided'}
            
            # In a real implementation, we might submit the transaction here
            # or verify that it was submitted
            
            return {
                'success': True,
                'signature': signature,
                'transaction_id': signature
            }
        
        except Exception as e:
            logger.error(f"Error processing transaction response: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_token_accounts(self, public_key: str) -> Dict[str, Any]:
        """
        Get all token accounts for a wallet.
        
        Args:
            public_key: The wallet's public key
            
        Returns:
            Dictionary with token account information
        """
        try:
            # Convert string to PublicKey if needed
            if isinstance(public_key, str):
                public_key = PublicKey(public_key)
            
            response = self.solana_client.get_token_accounts_by_owner(
                public_key,
                {'programId': PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')}
            )
            
            if 'result' in response and 'value' in response['result']:
                token_accounts = response['result']['value']
                
                return {
                    'success': True,
                    'token_accounts': token_accounts
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to get token accounts',
                    'response': response
                }
        
        except Exception as e:
            logger.error(f"Error getting token accounts: {e}")
            return {'success': False, 'error': str(e)}