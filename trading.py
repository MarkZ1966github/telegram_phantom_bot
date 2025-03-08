"""
Trading module for automated Solana token trading.
"""

import logging
import time
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
import base58
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solana.publickey import PublicKey

logger = logging.getLogger(__name__)

class JupiterSwapAPI:
    """
    Class to interact with Jupiter Aggregator API for token swaps.
    """
    
    def __init__(self, network: str = "mainnet-beta"):
        """Initialize the Jupiter API client."""
        self.network = network
        self.api_url = "https://quote-api.jup.ag/v6"
        self.solana_client = Client(f"https://api.{network}.solana.com")
    
    async def get_quote(self, 
                      input_mint: str, 
                      output_mint: str, 
                      amount: int, 
                      slippage_bps: int = 50) -> Dict[str, Any]:
        """
        Get a swap quote from Jupiter.
        
        Args:
            input_mint: Input token mint address
            output_mint: Output token mint address
            amount: Amount in lamports/smallest unit
            slippage_bps: Slippage tolerance in basis points (1% = 100)
            
        Returns:
            Dictionary with quote information
        """
        try:
            url = f"{self.api_url}/quote"
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount),
                "slippageBps": slippage_bps
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error getting quote: {response.status_code} - {response.text}")
                return {'error': f"API request failed with status {response.status_code}"}
        
        except Exception as e:
            logger.error(f"Error getting Jupiter quote: {e}")
            return {'error': str(e)}
    
    async def get_swap_transaction(self, 
                                 quote_response: Dict[str, Any], 
                                 user_public_key: str) -> Dict[str, Any]:
        """
        Get a swap transaction from Jupiter.
        
        Args:
            quote_response: Response from get_quote
            user_public_key: User's wallet public key
            
        Returns:
            Dictionary with transaction information
        """
        try:
            url = f"{self.api_url}/swap"
            
            payload = {
                "quoteResponse": quote_response,
                "userPublicKey": user_public_key,
                "wrapAndUnwrapSol": True
            }
            
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error getting swap transaction: {response.status_code} - {response.text}")
                return {'error': f"API request failed with status {response.status_code}"}
        
        except Exception as e:
            logger.error(f"Error getting swap transaction: {e}")
            return {'error': str(e)}

class TradingManager:
    """
    Class to manage automated token trading.
    """
    
    def __init__(self, 
                solana_client: Client,
                jupiter_api: JupiterSwapAPI,
                stop_loss_percentage: float = 10,
                take_profit_percentage: float = 30,
                max_slippage_bps: int = 200):
        """
        Initialize the trading manager.
        
        Args:
            solana_client: Solana RPC client
            jupiter_api: Jupiter API client
            stop_loss_percentage: Stop loss percentage
            take_profit_percentage: Take profit percentage
            max_slippage_bps: Maximum slippage in basis points
        """
        self.solana_client = solana_client
        self.jupiter_api = jupiter_api
        self.stop_loss_percentage = stop_loss_percentage
        self.take_profit_percentage = take_profit_percentage
        self.max_slippage_bps = max_slippage_bps
        self.active_trades = {}
        self.trade_history = []
        
        # SOL token mint address (wrapped SOL)
        self.SOL_MINT = "So11111111111111111111111111111111111111112"
    
    async def execute_buy(self, 
                        token_data: Dict[str, Any], 
                        wallet_public_key: str, 
                        amount_sol: float) -> Dict[str, Any]:
        """
        Execute a buy order for a token.
        
        Args:
            token_data: Token information
            wallet_public_key: User's wallet public key
            amount_sol: Amount of SOL to spend
            
        Returns:
            Dictionary with trade information
        """
        try:
            # Convert SOL to lamports
            amount_lamports = int(amount_sol * 10**9)
            
            # Get quote from Jupiter
            quote = await self.jupiter_api.get_quote(
                input_mint=self.SOL_MINT,
                output_mint=token_data['address'],
                amount=amount_lamports,
                slippage_bps=self.max_slippage_bps
            )
            
            if 'error' in quote:
                return {'success': False, 'error': quote['error']}
            
            # Get swap transaction
            swap_tx = await self.jupiter_api.get_swap_transaction(
                quote_response=quote,
                user_public_key=wallet_public_key
            )
            
            if 'error' in swap_tx:
                return {'success': False, 'error': swap_tx['error']}
            
            # In a real implementation, the transaction would be sent to Phantom
            # for signing via deep linking or a wallet adapter
            
            # For now, we'll simulate a successful trade
            buy_price = token_data['price_usd']
            tokens_bought = float(quote['outAmount']) / 10**9  # Adjust decimals as needed
            
            # Calculate stop loss and take profit levels
            stop_loss = buy_price * (1 - self.stop_loss_percentage/100)
            take_profit = buy_price * (1 + self.take_profit_percentage/100)
            
            # Create trade record
            trade_id = f"{token_data['address']}_{int(time.time())}"
            trade_data = {
                'token_address': token_data['address'],
                'token_symbol': token_data['symbol'],
                'token_name': token_data['name'],
                'amount_sol': amount_sol,
                'tokens_bought': tokens_bought,
                'buy_price_usd': buy_price,
                'buy_time': datetime.now(),
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'wallet': wallet_public_key,
                'status': 'active',
                'transaction': {
                    'type': 'simulated',  # In a real implementation, this would be the actual transaction
                    'signature': f"simulated_{trade_id}"
                }
            }
            
            # Store the trade
            self.active_trades[trade_id] = trade_data
            
            logger.info(f"Bought {tokens_bought} {token_data['symbol']} for {amount_sol} SOL at ${buy_price}")
            
            return {
                'success': True,
                'trade_id': trade_id,
                'trade_data': trade_data
            }
        
        except Exception as e:
            logger.error(f"Error executing buy for {token_data['symbol']}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def execute_sell(self, 
                         trade_id: str, 
                         current_price: Optional[float] = None) -> Dict[str, Any]:
        """
        Execute a sell order for a token.
        
        Args:
            trade_id: ID of the trade to sell
            current_price: Current token price (optional, for simulation)
            
        Returns:
            Dictionary with sell information
        """
        if trade_id not in self.active_trades:
            return {'success': False, 'error': 'Trade not found'}
        
        trade_data = self.active_trades[trade_id]
        
        try:
            # In a real implementation, we would:
            # 1. Get the current price from an oracle or DEX
            # 2. Execute the sell transaction via Jupiter
            # 3. Update the trade record
            
            # For simulation, use the provided price or simulate one
            if current_price is None:
                # Simulate a price (20% increase for demo)
                current_price = trade_data['buy_price_usd'] * 1.2
            
            # Convert token amount to lamports/smallest unit
            token_amount = int(trade_data['tokens_bought'] * 10**9)  # Adjust decimals as needed
            
            # Get quote from Jupiter (in reverse)
            quote = await self.jupiter_api.get_quote(
                input_mint=trade_data['token_address'],
                output_mint=self.SOL_MINT,
                amount=token_amount,
                slippage_bps=self.max_slippage_bps
            )
            
            if 'error' in quote:
                return {'success': False, 'error': quote['error']}
            
            # Get swap transaction
            swap_tx = await self.jupiter_api.get_swap_transaction(
                quote_response=quote,
                user_public_key=trade_data['wallet']
            )
            
            if 'error' in swap_tx:
                return {'success': False, 'error': swap_tx['error']}
            
            # Simulate a successful sell
            sold_for_sol = float(quote['outAmount']) / 10**9
            
            # Calculate profit/loss
            profit_loss = sold_for_sol - trade_data['amount_sol']
            profit_percentage = (profit_loss / trade_data['amount_sol']) * 100
            
            # Create sell record
            sell_data = {
                'token_address': trade_data['token_address'],
                'token_symbol': trade_data['token_symbol'],
                'tokens_sold': trade_data['tokens_bought'],
                'sell_price_usd': current_price,
                'sell_time': datetime.now(),
                'sold_for_sol': sold_for_sol,
                'profit_loss_sol': profit_loss,
                'profit_percentage': profit_percentage,
                'transaction': {
                    'type': 'simulated',  # In a real implementation, this would be the actual transaction
                    'signature': f"simulated_sell_{trade_id}"
                }
            }
            
            # Update trade history
            completed_trade = {
                **trade_data,
                **sell_data,
                'status': 'closed'
            }
            self.trade_history.append(completed_trade)
            
            # Remove from active trades
            del self.active_trades[trade_id]
            
            logger.info(f"Sold {sell_data['tokens_sold']} {trade_data['token_symbol']} for {sold_for_sol} SOL at ${current_price} ({profit_percentage:.2f}%)")
            
            return {
                'success': True,
                'sell_data': sell_data,
                'completed_trade': completed_trade
            }
        
        except Exception as e:
            logger.error(f"Error executing sell for {trade_data['token_symbol']}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def check_trade_conditions(self, trade_id: str) -> Dict[str, Any]:
        """
        Check if a trade meets sell conditions.
        
        Args:
            trade_id: ID of the trade to check
            
        Returns:
            Dictionary with check results
        """
        if trade_id not in self.active_trades:
            return {'should_sell': False, 'error': 'Trade not found'}
        
        trade_data = self.active_trades[trade_id]
        
        try:
            # In a real implementation, get the current price from an oracle or DEX
            # For simulation, we'll generate a random price movement
            import random
            price_change = random.uniform(-0.15, 0.35)
            current_price = trade_data['buy_price_usd'] * (1 + price_change)
            
            # Check stop loss
            hit_stop_loss = current_price <= trade_data['stop_loss']
            
            # Check take profit
            hit_take_profit = current_price >= trade_data['take_profit']
            
            # Check for suspicious activity (e.g., sudden price drop)
            suspicious_activity = price_change < -0.1
            
            # Calculate current profit/loss
            current_pl_percentage = ((current_price / trade_data['buy_price_usd']) - 1) * 100
            
            result = {
                'trade_id': trade_id,
                'token_symbol': trade_data['token_symbol'],
                'buy_price': trade_data['buy_price_usd'],
                'current_price': current_price,
                'current_pl_percentage': current_pl_percentage,
                'hit_stop_loss': hit_stop_loss,
                'hit_take_profit': hit_take_profit,
                'suspicious_activity': suspicious_activity,
                'should_sell': hit_stop_loss or hit_take_profit or suspicious_activity
            }
            
            if result['should_sell']:
                if hit_stop_loss:
                    result['sell_reason'] = 'stop_loss'
                elif hit_take_profit:
                    result['sell_reason'] = 'take_profit'
                else:
                    result['sell_reason'] = 'suspicious_activity'
            
            return result
        
        except Exception as e:
            logger.error(f"Error checking trade conditions for {trade_data['token_symbol']}: {e}")
            return {'should_sell': False, 'error': str(e)}
    
    def get_active_trades(self, wallet_public_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get active trades, optionally filtered by wallet.
        
        Args:
            wallet_public_key: Optional wallet to filter by
            
        Returns:
            List of active trades
        """
        if wallet_public_key:
            return [
                {'trade_id': trade_id, **trade_data}
                for trade_id, trade_data in self.active_trades.items()
                if trade_data['wallet'] == wallet_public_key
            ]
        else:
            return [
                {'trade_id': trade_id, **trade_data}
                for trade_id, trade_data in self.active_trades.items()
            ]
    
    def get_trade_history(self, wallet_public_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get trade history, optionally filtered by wallet.
        
        Args:
            wallet_public_key: Optional wallet to filter by
            
        Returns:
            List of completed trades
        """
        if wallet_public_key:
            return [
                trade for trade in self.trade_history
                if trade['wallet'] == wallet_public_key
            ]
        else:
            return self.trade_history