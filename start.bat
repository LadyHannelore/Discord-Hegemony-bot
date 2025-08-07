@echo off
echo Starting Discord Hegemony Bot...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Check if .env file exists
if not exist ".env" (
    echo.
    echo WARNING: .env file not found!
    echo Please create a .env file with your Discord bot token.
    echo Example:
    echo DISCORD_TOKEN=your_bot_token_here
    echo.
    echo Copy .env.example to .env and fill in your token.
    pause
    exit /b 1
)

REM Start the bot
echo.
echo Starting the bot...
python main.py

pause
