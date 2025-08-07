#!/bin/bash

echo "Starting Discord Hegemony Bot..."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed!"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo
    echo "WARNING: .env file not found!"
    echo "Please create a .env file with your Discord bot token."
    echo "Example:"
    echo "DISCORD_TOKEN=your_bot_token_here"
    echo
    echo "Copy .env.example to .env and fill in your token."
    exit 1
fi

# Start the bot
echo
echo "Starting the bot..."
python main.py
