#!/bin/bash

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if virtual environment exists, if not create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install or update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists, if not create from example
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "Creating .env file from example..."
        cp .env.example .env
        echo "Please edit the .env file with your Telegram Bot Token and other settings."
    else
        echo "Error: .env.example file not found."
        exit 1
    fi
fi

# Run the bot
echo "Starting the Telegram bot..."
python3 bot.py