# Telegram Solana Memecoin Trading Bot

An automated Telegram bot that connects to Phantom wallet and performs automated trading of Solana memecoins. The bot monitors DexScreener for promising new tokens, executes trades, and implements exit strategies to maximize profits while minimizing risk of rug pulls.

## Features

- **One-Click Phantom Wallet Connection**: Easily connect your Phantom wallet via Telegram
- **Automated Memecoin Detection**: Monitors DexScreener for promising new tokens
- **Smart Entry & Exit Strategies**: Identifies optimal entry points and implements stop-loss and take-profit mechanisms
- **Risk Management**: Configurable risk parameters and wallet exposure limits
- **Real-time Notifications**: Get notified about trades and performance
- **Detailed Analytics**: View your trading history and performance statistics
- **Customizable Settings**: Adjust trading parameters to match your risk tolerance

## Requirements

- Python 3.8+
- Telegram Bot Token (from BotFather)
- Solana RPC endpoint (optional, uses public endpoints by default)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/telegram-phantom-bot.git
cd telegram-phantom-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a configuration file:
```bash
cp .env.example .env
```

4. Edit the `.env` file with your Telegram Bot Token and other settings:
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

## Setup

1. **Create a Telegram Bot**:
   - Contact [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` and follow the instructions
   - Copy the API token provided

2. **Configure the Bot**:
   - Update the `.env` file with your Telegram Bot Token
   - Adjust trading parameters as needed

3. **Run the Bot**:
```bash
python bot.py
```

## Usage

Once the bot is running, you can interact with it on Telegram:

1. Start a chat with your bot
2. Send `/start` to initialize the bot
3. Use `/connect` to connect your Phantom wallet
4. Configure trading settings with `/settings`
5. The bot will automatically monitor for new tokens and execute trades

### Available Commands

- `/start` - Start the bot
- `/connect` - Connect your Phantom wallet
- `/disconnect` - Disconnect your wallet
- `/balance` - Check your wallet balance
- `/settings` - Adjust trading settings
- `/status` - View bot status and active trades
- `/history` - View your trading history
- `/help` - Show help message

## Trading Parameters

You can customize the following parameters in the `.env` file or via the `/settings` command:

- `MIN_LIQUIDITY`: Minimum liquidity in USD (default: 10,000)
- `MAX_MARKET_CAP`: Maximum market cap in USD (default: 5,000,000)
- `MIN_BUY_AMOUNT`: Minimum amount to buy in SOL (default: 0.1)
- `MAX_BUY_AMOUNT`: Maximum amount to buy in SOL (default: 1.0)
- `STOP_LOSS_PERCENTAGE`: Stop loss percentage (default: 10%)
- `TAKE_PROFIT_PERCENTAGE`: Take profit percentage (default: 30%)
- `MAX_SLIPPAGE`: Maximum slippage percentage (default: 2%)
- `MAX_WALLET_EXPOSURE`: Maximum wallet exposure percentage (default: 20%)

## Security Considerations

- The bot never stores your private keys
- All transactions are signed by your Phantom wallet
- Wallet connection is done via secure deep linking
- Set appropriate `MAX_WALLET_EXPOSURE` to limit risk

## Disclaimer

This bot is provided for educational and informational purposes only. Trading cryptocurrencies involves significant risk. Use this bot at your own risk. The developers are not responsible for any financial losses incurred while using this bot.

## License

[MIT License](LICENSE)