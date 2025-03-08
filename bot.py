#!/usr/bin/env python3
"""
Telegram Bot for automated Solana memecoin trading using Phantom wallet.
"""

import os
import logging
import json
import asyncio
import time
from datetime import datetime
import base64
import hashlib
import requests
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, ConversationHandler, MessageHandler, filters
)
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solana.keypair import Keypair
import solana.system_program as sys_program
from solana.publickey import PublicKey
import websocket
import threading

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DEXSCREENER_API_URL = os.getenv('DEXSCREENER_API_URL', 'https://api.dexscreener.com/latest/dex')
SOLANA_NETWORK = os.getenv('SOLANA_NETWORK', 'mainnet-beta')

# Trading parameters
MIN_LIQUIDITY = float(os.getenv('MIN_LIQUIDITY', 10000))  # Minimum liquidity in USD
MAX_MARKET_CAP = float(os.getenv('MAX_MARKET_CAP', 5000000))  # Maximum market cap in USD
MIN_BUY_AMOUNT = float(os.getenv('MIN_BUY_AMOUNT', 0.1))  # SOL
MAX_BUY_AMOUNT = float(os.getenv('MAX_BUY_AMOUNT', 1.0))  # SOL
STOP_LOSS_PERCENTAGE = float(os.getenv('STOP_LOSS_PERCENTAGE', 10))  # %
TAKE_PROFIT_PERCENTAGE = float(os.getenv('TAKE_PROFIT_PERCENTAGE', 30))  # %
MAX_SLIPPAGE = float(os.getenv('MAX_SLIPPAGE', 2))  # %
MAX_WALLET_EXPOSURE = float(os.getenv('MAX_WALLET_EXPOSURE', 20))  # % of total wallet

# Conversation states
CONNECT_WALLET, TRADING_SETTINGS = range(2)

# Global variables
user_wallets = {}  # Store connected phantom wallets
active_trades = {}  # Track active trades
monitored_tokens = {}  # Tokens being monitored

# Initialize Solana client
solana_client = Client(f"https://api.{SOLANA_NETWORK}.solana.com")

class PhantomWallet:
    """Class to handle Phantom wallet interactions"""
    
    def __init__(self, public_key, wallet_connection_data=None):
        self.public_key = public_key
        self.wallet_connection_data = wallet_connection_data
        self.balance = 0
        self.update_balance()
    
    def update_balance(self):
        """Update wallet balance"""
        try:
            response = solana_client.get_balance(self.public_key)
            if response["result"]["value"]:
                self.balance = response["result"]["value"] / 10**9  # Convert lamports to SOL
                return self.balance
        except Exception as e:
            logger.error(f"Error updating balance: {e}")
        return 0
    
    async def execute_transaction(self, transaction_data):
        """Execute a transaction via Phantom wallet"""
        # This would require actual implementation with Phantom wallet
        # For now, this is a placeholder
        try:
            # In a real implementation, we would send this transaction to Phantom
            # and get back a signature
            logger.info(f"Executing transaction: {transaction_data}")
            return {"success": True, "signature": "simulated_signature"}
        except Exception as e:
            logger.error(f"Transaction error: {e}")
            return {"success": False, "error": str(e)}

class DexScreenerMonitor:
    """Class to monitor DexScreener for new tokens"""
    
    def __init__(self):
        self.last_check = datetime.now()
        self.promising_tokens = []
    
    async def scan_for_new_tokens(self):
        """Scan DexScreener for new promising tokens on Solana"""
        try:
            # Get pairs from DexScreener
            response = requests.get(f"{DEXSCREENER_API_URL}/pairs/solana")
            if response.status_code == 200:
                pairs = response.json().get('pairs', [])
                
                # Filter promising tokens based on criteria
                for pair in pairs:
                    # Check if it's a new token (within last 24 hours)
                    created_at = datetime.fromtimestamp(pair.get('pairCreatedAt', 0)/1000)
                    hours_since_creation = (datetime.now() - created_at).total_seconds() / 3600
                    
                    if hours_since_creation <= 24:
                        # Check liquidity
                        liquidity_usd = float(pair.get('liquidity', {}).get('usd', 0))
                        
                        # Check if token meets our criteria
                        if liquidity_usd >= MIN_LIQUIDITY:
                            token_data = {
                                'address': pair.get('baseToken', {}).get('address'),
                                'symbol': pair.get('baseToken', {}).get('symbol'),
                                'name': pair.get('baseToken', {}).get('name'),
                                'liquidity_usd': liquidity_usd,
                                'price_usd': float(pair.get('priceUsd', 0)),
                                'pair_address': pair.get('pairAddress'),
                                'dex_id': pair.get('dexId'),
                                'created_at': created_at,
                                'url': f"https://dexscreener.com/solana/{pair.get('pairAddress')}"
                            }
                            
                            # Add to promising tokens if not already there
                            if token_data['address'] not in [t['address'] for t in self.promising_tokens]:
                                self.promising_tokens.append(token_data)
                                logger.info(f"Found promising new token: {token_data['symbol']} - {token_data['name']}")
                                yield token_data
            
            self.last_check = datetime.now()
        except Exception as e:
            logger.error(f"Error scanning DexScreener: {e}")
    
    async def analyze_token(self, token_data):
        """Analyze if a token is worth buying based on various metrics"""
        try:
            # Additional analysis could include:
            # - Check contract code if available
            # - Check token distribution
            # - Check trading volume trends
            # - Social media mentions
            
            # For now, using simple criteria
            if token_data['liquidity_usd'] >= MIN_LIQUIDITY:
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error analyzing token {token_data['symbol']}: {e}")
            return False

class TradingBot:
    """Class to handle automated trading"""
    
    def __init__(self, wallet):
        self.wallet = wallet
        self.active_trades = {}
        self.trade_history = []
    
    async def buy_token(self, token_data, amount_sol):
        """Buy token using Jupiter aggregator or other DEX"""
        try:
            # In a real implementation, we would:
            # 1. Get the best route via Jupiter API
            # 2. Create and sign the transaction
            # 3. Execute via connected Phantom wallet
            
            # Simulated buy for now
            buy_price = token_data['price_usd']
            tokens_bought = amount_sol * 10 / buy_price  # Assuming SOL price is ~$10
            
            trade_data = {
                'token_address': token_data['address'],
                'token_symbol': token_data['symbol'],
                'amount_sol': amount_sol,
                'tokens_bought': tokens_bought,
                'buy_price_usd': buy_price,
                'buy_time': datetime.now(),
                'stop_loss': buy_price * (1 - STOP_LOSS_PERCENTAGE/100),
                'take_profit': buy_price * (1 + TAKE_PROFIT_PERCENTAGE/100),
                'status': 'active'
            }
            
            trade_id = f"{token_data['address']}_{int(time.time())}"
            self.active_trades[trade_id] = trade_data
            
            logger.info(f"Bought {tokens_bought} {token_data['symbol']} for {amount_sol} SOL at ${buy_price}")
            return {'success': True, 'trade_id': trade_id, 'trade_data': trade_data}
        
        except Exception as e:
            logger.error(f"Error buying token {token_data['symbol']}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def sell_token(self, trade_id):
        """Sell token using Jupiter aggregator or other DEX"""
        if trade_id not in self.active_trades:
            return {'success': False, 'error': 'Trade not found'}
        
        trade_data = self.active_trades[trade_id]
        
        try:
            # In a real implementation, we would:
            # 1. Get the best route via Jupiter API
            # 2. Create and sign the transaction
            # 3. Execute via connected Phantom wallet
            
            # Simulated sell for now
            current_price = trade_data['buy_price_usd'] * 1.2  # Simulating a 20% increase
            sold_for_sol = (trade_data['tokens_bought'] * current_price) / 10  # Assuming SOL price is ~$10
            
            profit_loss = sold_for_sol - trade_data['amount_sol']
            profit_percentage = (profit_loss / trade_data['amount_sol']) * 100
            
            sell_data = {
                'token_address': trade_data['token_address'],
                'token_symbol': trade_data['token_symbol'],
                'tokens_sold': trade_data['tokens_bought'],
                'sell_price_usd': current_price,
                'sell_time': datetime.now(),
                'sold_for_sol': sold_for_sol,
                'profit_loss_sol': profit_loss,
                'profit_percentage': profit_percentage
            }
            
            # Update trade history
            self.trade_history.append({
                **trade_data,
                **sell_data,
                'status': 'closed'
            })
            
            # Remove from active trades
            del self.active_trades[trade_id]
            
            logger.info(f"Sold {sell_data['tokens_sold']} {trade_data['token_symbol']} for {sold_for_sol} SOL at ${current_price} ({profit_percentage:.2f}%)")
            return {'success': True, 'sell_data': sell_data}
        
        except Exception as e:
            logger.error(f"Error selling token {trade_data['token_symbol']}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def monitor_price(self, token_address):
        """Monitor token price for stop loss or take profit"""
        # In a real implementation, this would connect to websocket API
        # or poll DexScreener API regularly
        pass

# Bot command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        f"Hi {user.mention_html()}! I'm your automated Solana memecoin trading bot.\n\n"
        f"To get started, you'll need to connect your Phantom wallet using /connect"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        "Here are the available commands:\n\n"
        "/start - Start the bot\n"
        "/connect - Connect your Phantom wallet\n"
        "/disconnect - Disconnect your wallet\n"
        "/balance - Check your wallet balance\n"
        "/settings - Adjust trading settings\n"
        "/status - View bot status and active trades\n"
        "/history - View your trading history\n"
        "/help - Show this help message"
    )
    await update.message.reply_text(help_text)

async def connect_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Connect Phantom wallet."""
    user_id = update.effective_user.id
    
    # In a real implementation, we would:
    # 1. Generate a unique connection URL or QR code for Phantom
    # 2. Set up a callback endpoint for the wallet to connect to
    
    # For now, simulate a connection button that would open Phantom
    keyboard = [
        [InlineKeyboardButton("Connect Phantom Wallet", callback_data='phantom_connect')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Click the button below to connect your Phantom wallet:",
        reply_markup=reply_markup
    )
    
    return CONNECT_WALLET

async def wallet_connect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle wallet connection callback."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # In a real implementation, this would be the actual public key from Phantom
    # For demo, generate a simulated public key
    simulated_public_key = f"simu1ated{hashlib.sha256(str(user_id).encode()).hexdigest()[:20]}"
    
    # Create PhantomWallet instance
    user_wallets[user_id] = PhantomWallet(simulated_public_key)
    
    await query.edit_message_text(
        f"✅ Wallet connected successfully!\n\n"
        f"Address: {simulated_public_key[:6]}...{simulated_public_key[-4:]}\n"
        f"Balance: {user_wallets[user_id].balance} SOL\n\n"
        f"You can now use the bot for trading. Use /settings to configure trading parameters."
    )
    
    return ConversationHandler.END

async def disconnect_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disconnect Phantom wallet."""
    user_id = update.effective_user.id
    
    if user_id in user_wallets:
        del user_wallets[user_id]
        await update.message.reply_text("Wallet disconnected successfully.")
    else:
        await update.message.reply_text("No wallet is currently connected.")

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check wallet balance."""
    user_id = update.effective_user.id
    
    if user_id in user_wallets:
        wallet = user_wallets[user_id]
        balance = wallet.update_balance()
        await update.message.reply_text(f"Current wallet balance: {balance} SOL")
    else:
        await update.message.reply_text(
            "No wallet connected. Please use /connect to connect your Phantom wallet."
        )

async def trading_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Configure trading settings."""
    user_id = update.effective_user.id
    
    if user_id not in user_wallets:
        await update.message.reply_text(
            "No wallet connected. Please use /connect to connect your Phantom wallet first."
        )
        return ConversationHandler.END
    
    # Display current settings
    settings_text = (
        "Current Trading Settings:\n\n"
        f"Min Liquidity: ${MIN_LIQUIDITY}\n"
        f"Max Market Cap: ${MAX_MARKET_CAP}\n"
        f"Min Buy Amount: {MIN_BUY_AMOUNT} SOL\n"
        f"Max Buy Amount: {MAX_BUY_AMOUNT} SOL\n"
        f"Stop Loss: {STOP_LOSS_PERCENTAGE}%\n"
        f"Take Profit: {TAKE_PROFIT_PERCENTAGE}%\n"
        f"Max Slippage: {MAX_SLIPPAGE}%\n"
        f"Max Wallet Exposure: {MAX_WALLET_EXPOSURE}%\n\n"
        "What would you like to change? Reply with setting=value (e.g., min_buy=0.2)"
    )
    
    await update.message.reply_text(settings_text)
    
    return TRADING_SETTINGS

async def update_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update trading settings."""
    user_id = update.effective_user.id
    text = update.message.text
    
    try:
        # Parse setting=value format
        setting, value = text.split('=')
        setting = setting.strip().lower()
        value = float(value.strip())
        
        # Update the appropriate setting
        if setting == 'min_liquidity':
            global MIN_LIQUIDITY
            MIN_LIQUIDITY = value
        elif setting == 'max_market_cap':
            global MAX_MARKET_CAP
            MAX_MARKET_CAP = value
        elif setting == 'min_buy':
            global MIN_BUY_AMOUNT
            MIN_BUY_AMOUNT = value
        elif setting == 'max_buy':
            global MAX_BUY_AMOUNT
            MAX_BUY_AMOUNT = value
        elif setting == 'stop_loss':
            global STOP_LOSS_PERCENTAGE
            STOP_LOSS_PERCENTAGE = value
        elif setting == 'take_profit':
            global TAKE_PROFIT_PERCENTAGE
            TAKE_PROFIT_PERCENTAGE = value
        elif setting == 'max_slippage':
            global MAX_SLIPPAGE
            MAX_SLIPPAGE = value
        elif setting == 'max_exposure':
            global MAX_WALLET_EXPOSURE
            MAX_WALLET_EXPOSURE = value
        else:
            await update.message.reply_text(f"Unknown setting: {setting}")
            return TRADING_SETTINGS
        
        await update.message.reply_text(f"Updated {setting} to {value}")
        
        # Show updated settings
        settings_text = (
            "Updated Trading Settings:\n\n"
            f"Min Liquidity: ${MIN_LIQUIDITY}\n"
            f"Max Market Cap: ${MAX_MARKET_CAP}\n"
            f"Min Buy Amount: {MIN_BUY_AMOUNT} SOL\n"
            f"Max Buy Amount: {MAX_BUY_AMOUNT} SOL\n"
            f"Stop Loss: {STOP_LOSS_PERCENTAGE}%\n"
            f"Take Profit: {TAKE_PROFIT_PERCENTAGE}%\n"
            f"Max Slippage: {MAX_SLIPPAGE}%\n"
            f"Max Wallet Exposure: {MAX_WALLET_EXPOSURE}%\n\n"
            "Settings updated. You can update another setting or use /cancel to finish."
        )
        
        await update.message.reply_text(settings_text)
        return TRADING_SETTINGS
        
    except ValueError:
        await update.message.reply_text(
            "Invalid format. Please use setting=value (e.g., min_buy=0.2)"
        )
        return TRADING_SETTINGS

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current conversation."""
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

async def bot_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot status and active trades."""
    user_id = update.effective_user.id
    
    if user_id not in user_wallets:
        await update.message.reply_text(
            "No wallet connected. Please use /connect to connect your Phantom wallet."
        )
        return
    
    wallet = user_wallets[user_id]
    
    # Get active trades (in a real implementation, this would be per user)
    if hasattr(wallet, 'trading_bot') and wallet.trading_bot.active_trades:
        trades_text = "Active trades:\n\n"
        for trade_id, trade in wallet.trading_bot.active_trades.items():
            trades_text += (
                f"Token: {trade['token_symbol']}\n"
                f"Buy price: ${trade['buy_price_usd']:.6f}\n"
                f"Amount: {trade['amount_sol']} SOL\n"
                f"Stop loss: ${trade['stop_loss']:.6f}\n"
                f"Take profit: ${trade['take_profit']:.6f}\n"
                f"Buy time: {trade['buy_time'].strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )
    else:
        trades_text = "No active trades."
    
    status_text = (
        f"Bot Status: Running\n"
        f"Wallet: {wallet.public_key[:6]}...{wallet.public_key[-4:]}\n"
        f"Balance: {wallet.balance} SOL\n\n"
        f"{trades_text}"
    )
    
    await update.message.reply_text(status_text)

async def trade_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show trading history."""
    user_id = update.effective_user.id
    
    if user_id not in user_wallets:
        await update.message.reply_text(
            "No wallet connected. Please use /connect to connect your Phantom wallet."
        )
        return
    
    wallet = user_wallets[user_id]
    
    # Get trade history (in a real implementation, this would be per user)
    if hasattr(wallet, 'trading_bot') and wallet.trading_bot.trade_history:
        history_text = "Trading history:\n\n"
        for trade in wallet.trading_bot.trade_history:
            history_text += (
                f"Token: {trade['token_symbol']}\n"
                f"Buy price: ${trade['buy_price_usd']:.6f}\n"
                f"Sell price: ${trade['sell_price_usd']:.6f}\n"
                f"Profit/Loss: {trade['profit_percentage']:.2f}%\n"
                f"Buy time: {trade['buy_time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Sell time: {trade['sell_time'].strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )
    else:
        history_text = "No trading history yet."
    
    await update.message.reply_text(history_text)

# Background monitoring task
async def token_monitoring_task(app):
    """Background task to monitor for new tokens and manage trades"""
    dex_monitor = DexScreenerMonitor()
    
    while True:
        try:
            # Scan for new promising tokens
            async for token in dex_monitor.scan_for_new_tokens():
                logger.info(f"Analyzing token: {token['symbol']}")
                
                # Analyze if the token is worth buying
                is_promising = await dex_monitor.analyze_token(token)
                
                if is_promising:
                    logger.info(f"Token {token['symbol']} looks promising, initiating buy")
                    
                    # For each connected user, check if they have a trading bot
                    # and execute trades
                    for user_id, wallet in user_wallets.items():
                        if not hasattr(wallet, 'trading_bot'):
                            wallet.trading_bot = TradingBot(wallet)
                        
                        # Calculate buy amount based on wallet balance and settings
                        balance = wallet.update_balance()
                        max_trade_amount = balance * (MAX_WALLET_EXPOSURE / 100)
                        buy_amount = min(MAX_BUY_AMOUNT, max_trade_amount)
                        
                        if buy_amount >= MIN_BUY_AMOUNT:
                            # Execute buy
                            result = await wallet.trading_bot.buy_token(token, buy_amount)
                            
                            if result['success']:
                                # Notify user about the trade
                                try:
                                    trade_data = result['trade_data']
                                    notification_text = (
                                        f"🚀 Automatic trade executed!\n\n"
                                        f"Bought {trade_data['tokens_bought']:.2f} {token['symbol']}\n"
                                        f"Price: ${trade_data['buy_price_usd']:.6f}\n"
                                        f"Amount: {trade_data['amount_sol']} SOL\n"
                                        f"Stop loss: ${trade_data['stop_loss']:.6f}\n"
                                        f"Take profit: ${trade_data['take_profit']:.6f}\n"
                                        f"View on DexScreener: {token['url']}"
                                    )
                                    await app.bot.send_message(chat_id=user_id, text=notification_text)
                                except Exception as e:
                                    logger.error(f"Error sending notification: {e}")
            
            # Monitor active trades for each user
            for user_id, wallet in user_wallets.items():
                if hasattr(wallet, 'trading_bot'):
                    trading_bot = wallet.trading_bot
                    
                    # Check each active trade for sell conditions
                    for trade_id, trade in list(trading_bot.active_trades.items()):
                        # In a real implementation, get current price from DexScreener or DEX API
                        # For simulation, let's assume the price has changed
                        current_price = trade['buy_price_usd'] * (1 + np.random.uniform(-0.15, 0.35))
                        
                        # Check stop loss and take profit conditions
                        if current_price <= trade['stop_loss'] or current_price >= trade['take_profit']:
                            logger.info(f"Selling {trade['token_symbol']} at ${current_price}")
                            
                            # Execute sell
                            sell_result = await trading_bot.sell_token(trade_id)
                            
                            if sell_result['success']:
                                sell_data = sell_result['sell_data']
                                # Notify user about the sale
                                try:
                                    notification_text = (
                                        f"💰 Automatic sell executed!\n\n"
                                        f"Sold {sell_data['tokens_sold']:.2f} {sell_data['token_symbol']}\n"
                                        f"Price: ${sell_data['sell_price_usd']:.6f}\n"
                                        f"Profit/Loss: {sell_data['profit_percentage']:.2f}%\n"
                                        f"Received: {sell_data['sold_for_sol']:.4f} SOL"
                                    )
                                    await app.bot.send_message(chat_id=user_id, text=notification_text)
                                except Exception as e:
                                    logger.error(f"Error sending notification: {e}")
        
        except Exception as e:
            logger.error(f"Error in monitoring task: {e}")
        
        # Sleep for a short period before next check
        await asyncio.sleep(30)  # Check every 30 seconds

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add conversation handler for wallet connection
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('connect', connect_wallet)],
        states={
            CONNECT_WALLET: [CallbackQueryHandler(wallet_connect_callback, pattern='^phantom_connect$')],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Add conversation handler for trading settings
    settings_handler = ConversationHandler(
        entry_points=[CommandHandler('settings', trading_settings)],
        states={
            TRADING_SETTINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, update_settings)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("disconnect", disconnect_wallet))
    application.add_handler(CommandHandler("balance", check_balance))
    application.add_handler(settings_handler)
    application.add_handler(CommandHandler("status", bot_status))
    application.add_handler(CommandHandler("history", trade_history))
    
    # Start the background monitoring task
    application.job_queue.run_once(
        lambda context: asyncio.create_task(token_monitoring_task(application)),
        0
    )
    
    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()