"""
DexScreener API integration for monitoring Solana tokens.
"""

import logging
import time
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Generator, AsyncGenerator
import requests
import aiohttp

logger = logging.getLogger(__name__)

class DexScreenerAPI:
    """
    Class to interact with DexScreener API for monitoring DEX pairs.
    """
    
    def __init__(self, api_url: str = "https://api.dexscreener.com/latest/dex"):
        """Initialize the DexScreener API client."""
        self.api_url = api_url
        self.rate_limit_remaining = 30  # Default rate limit
        self.rate_limit_reset = 0
        self.last_request_time = 0
    
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a request to the DexScreener API with rate limiting.
        
        Args:
            endpoint: API endpoint to call
            params: Query parameters
            
        Returns:
            API response as dictionary
        """
        # Respect rate limits
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if self.rate_limit_remaining <= 1 and current_time < self.rate_limit_reset:
            wait_time = max(0, self.rate_limit_reset - current_time + 1)
            logger.info(f"Rate limit approaching, waiting {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)
        elif time_since_last < 0.5:  # Be nice to the API, max 2 requests per second
            await asyncio.sleep(0.5 - time_since_last)
        
        url = f"{self.api_url}/{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    # Update rate limit info from headers if available
                    if 'X-RateLimit-Remaining' in response.headers:
                        self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
                    if 'X-RateLimit-Reset' in response.headers:
                        self.rate_limit_reset = int(response.headers['X-RateLimit-Reset'])
                    
                    self.last_request_time = time.time()
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"API request failed: {response.status} - {await response.text()}")
                        return {'error': f"API request failed with status {response.status}"}
        
        except Exception as e:
            logger.error(f"Error making API request: {e}")
            return {'error': str(e)}
    
    async def get_pairs(self, chain: str = "solana", first: int = 100) -> Dict[str, Any]:
        """
        Get DEX pairs for a specific blockchain.
        
        Args:
            chain: Blockchain name (e.g., 'solana', 'ethereum')
            first: Number of results to return
            
        Returns:
            Dictionary with pairs information
        """
        return await self._make_request(f"pairs/{chain}", {'first': first})
    
    async def search_pairs(self, query: str) -> Dict[str, Any]:
        """
        Search for pairs by token name, symbol, or address.
        
        Args:
            query: Search query string
            
        Returns:
            Dictionary with search results
        """
        return await self._make_request(f"search", {'q': query})
    
    async def get_pair(self, pair_address: str, chain: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about a specific pair.
        
        Args:
            pair_address: Address of the trading pair
            chain: Optional blockchain name
            
        Returns:
            Dictionary with pair details
        """
        endpoint = f"pairs/{pair_address}"
        if chain:
            endpoint = f"pairs/{chain}/{pair_address}"
        
        return await self._make_request(endpoint)
    
    async def get_token_pairs(self, token_address: str, chain: str = "solana") -> Dict[str, Any]:
        """
        Get all pairs for a specific token.
        
        Args:
            token_address: Token address
            chain: Blockchain name
            
        Returns:
            Dictionary with token pairs
        """
        return await self._make_request(f"tokens/{chain}/{token_address}")

class MemeTokenScanner:
    """
    Scanner for finding promising new memecoin tokens on Solana.
    """
    
    def __init__(self, 
                api_client: DexScreenerAPI,
                min_liquidity: float = 10000,
                max_market_cap: float = 5000000,
                max_age_hours: int = 24):
        """
        Initialize the memecoin scanner.
        
        Args:
            api_client: DexScreenerAPI instance
            min_liquidity: Minimum liquidity in USD
            max_market_cap: Maximum market cap in USD
            max_age_hours: Maximum age of token in hours
        """
        self.api_client = api_client
        self.min_liquidity = min_liquidity
        self.max_market_cap = max_market_cap
        self.max_age_hours = max_age_hours
        self.seen_tokens = set()  # Keep track of tokens we've already seen
    
    async def scan_for_new_tokens(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Scan for new promising memecoin tokens.
        
        Yields:
            Dictionary with token information for each promising token
        """
        try:
            # Get latest pairs from DexScreener
            pairs_data = await self.api_client.get_pairs("solana", 100)
            
            if 'error' in pairs_data:
                logger.error(f"Error getting pairs: {pairs_data['error']}")
                return
            
            pairs = pairs_data.get('pairs', [])
            current_time = datetime.now()
            
            for pair in pairs:
                # Skip if we've seen this token before
                token_address = pair.get('baseToken', {}).get('address')
                if not token_address or token_address in self.seen_tokens:
                    continue
                
                # Check if it's a new token
                created_at = datetime.fromtimestamp(pair.get('pairCreatedAt', 0)/1000)
                hours_since_creation = (current_time - created_at).total_seconds() / 3600
                
                if hours_since_creation <= self.max_age_hours:
                    # Check liquidity
                    liquidity_usd = float(pair.get('liquidity', {}).get('usd', 0))
                    
                    # Check market cap if available
                    market_cap = float(pair.get('fdv', 0))  # Fully Diluted Valuation
                    
                    # Check if token meets our criteria
                    if (liquidity_usd >= self.min_liquidity and 
                        (market_cap == 0 or market_cap <= self.max_market_cap)):
                        
                        token_data = {
                            'address': token_address,
                            'symbol': pair.get('baseToken', {}).get('symbol'),
                            'name': pair.get('baseToken', {}).get('name'),
                            'liquidity_usd': liquidity_usd,
                            'price_usd': float(pair.get('priceUsd', 0)),
                            'market_cap': market_cap,
                            'pair_address': pair.get('pairAddress'),
                            'dex_id': pair.get('dexId'),
                            'created_at': created_at,
                            'hours_since_creation': hours_since_creation,
                            'url': f"https://dexscreener.com/solana/{pair.get('pairAddress')}"
                        }
                        
                        # Add to seen tokens
                        self.seen_tokens.add(token_address)
                        
                        logger.info(f"Found promising new token: {token_data['symbol']} - {token_data['name']}")
                        yield token_data
        
        except Exception as e:
            logger.error(f"Error scanning for new tokens: {e}")
    
    async def analyze_token(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform detailed analysis on a token to determine if it's worth buying.
        
        Args:
            token_data: Basic token information
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Get more detailed information about the token's pairs
            token_pairs = await self.api_client.get_token_pairs(token_data['address'])
            
            if 'error' in token_pairs:
                return {
                    'token': token_data,
                    'is_promising': False,
                    'reasons': [f"Error getting token pairs: {token_pairs['error']}"]
                }
            
            pairs = token_pairs.get('pairs', [])
            
            # Initialize analysis metrics
            total_liquidity = 0
            volume_24h = 0
            holders_count = 0  # This would require additional API
            price_change_24h = 0
            txns_24h = {'buys': 0, 'sells': 0}
            reasons = []
            red_flags = []
            
            # Analyze all pairs for this token
            for pair in pairs:
                # Sum up liquidity across all pairs
                total_liquidity += float(pair.get('liquidity', {}).get('usd', 0))
                
                # Get 24h volume
                volume_24h += float(pair.get('volume', {}).get('h24', 0))
                
                # Get price change
                price_change = float(pair.get('priceChange', {}).get('h24', 0))
                if abs(price_change) > abs(price_change_24h):
                    price_change_24h = price_change
                
                # Get transaction counts
                txns = pair.get('txns', {}).get('h24', {})
                txns_24h['buys'] += int(txns.get('buys', 0))
                txns_24h['sells'] += int(txns.get('sells', 0))
            
            # Analyze buy/sell ratio
            buy_sell_ratio = txns_24h['buys'] / max(1, txns_24h['sells'])
            
            # Check for red flags
            if total_liquidity < self.min_liquidity:
                red_flags.append(f"Low liquidity (${total_liquidity})")
            
            if buy_sell_ratio < 0.5:
                red_flags.append(f"High sell pressure (buy/sell ratio: {buy_sell_ratio:.2f})")
            
            if price_change_24h < -30:
                red_flags.append(f"Significant price drop ({price_change_24h}% in 24h)")
            
            # Check for promising indicators
            if total_liquidity >= self.min_liquidity * 2:
                reasons.append(f"Strong liquidity (${total_liquidity})")
            
            if buy_sell_ratio > 1.5:
                reasons.append(f"Strong buy pressure (buy/sell ratio: {buy_sell_ratio:.2f})")
            
            if price_change_24h > 20:
                reasons.append(f"Positive price momentum ({price_change_24h}% in 24h)")
            
            if volume_24h > total_liquidity * 0.3:
                reasons.append(f"High trading volume (${volume_24h} in 24h)")
            
            # Make a decision
            is_promising = len(reasons) >= 2 and len(red_flags) <= 1
            
            analysis_result = {
                'token': token_data,
                'is_promising': is_promising,
                'total_liquidity': total_liquidity,
                'volume_24h': volume_24h,
                'price_change_24h': price_change_24h,
                'txns_24h': txns_24h,
                'buy_sell_ratio': buy_sell_ratio,
                'reasons': reasons,
                'red_flags': red_flags
            }
            
            return analysis_result
        
        except Exception as e:
            logger.error(f"Error analyzing token {token_data['symbol']}: {e}")
            return {
                'token': token_data,
                'is_promising': False,
                'reasons': [f"Error during analysis: {str(e)}"]
            }
    
    def calculate_risk_score(self, analysis_result: Dict[str, Any]) -> float:
        """
        Calculate a risk score for a token (0-100, lower is safer).
        
        Args:
            analysis_result: Token analysis result
            
        Returns:
            Risk score (0-100)
        """
        try:
            token = analysis_result['token']
            
            # Base risk score starts at 50
            risk_score = 50
            
            # Age factor (newer = riskier)
            hours_since_creation = token.get('hours_since_creation', 24)
            age_factor = max(0, 24 - hours_since_creation) / 24 * 20
            risk_score += age_factor
            
            # Liquidity factor (lower = riskier)
            liquidity = analysis_result.get('total_liquidity', token.get('liquidity_usd', 0))
            liquidity_factor = max(0, min(20, 20 - (liquidity / self.min_liquidity * 10)))
            risk_score += liquidity_factor
            
            # Buy/sell ratio (lower = riskier)
            buy_sell_ratio = analysis_result.get('buy_sell_ratio', 1)
            if buy_sell_ratio < 0.5:
                risk_score += 15
            elif buy_sell_ratio < 1:
                risk_score += 5
            elif buy_sell_ratio > 2:
                risk_score -= 10
            
            # Price change factor
            price_change = analysis_result.get('price_change_24h', 0)
            if price_change < -20:
                risk_score += 10
            elif price_change > 100:
                risk_score += 5  # Extreme growth can also be risky
            
            # Number of red flags
            red_flags = len(analysis_result.get('red_flags', []))
            risk_score += red_flags * 5
            
            # Cap the risk score between 0 and 100
            risk_score = max(0, min(100, risk_score))
            
            return risk_score
        
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return 75  # Default to high risk if calculation fails
    
    def calculate_investment_amount(self, risk_score: float, max_amount: float) -> float:
        """
        Calculate suggested investment amount based on risk score.
        
        Args:
            risk_score: Risk score (0-100)
            max_amount: Maximum amount available to invest
            
        Returns:
            Suggested investment amount
        """
        # Lower risk score = higher investment percentage
        investment_percentage = max(0.1, (100 - risk_score) / 100)
        
        # Calculate amount
        amount = max_amount * investment_percentage
        
        return amount