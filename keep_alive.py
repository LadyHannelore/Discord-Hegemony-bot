"""
Keep-alive script for Replit hosting.
This creates a simple web server to keep the Replit alive.
"""

from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return """
    <html>
        <head><title>Discord Hegemony Bot</title></head>
        <body>
            <h1>Discord Hegemony Bot is Running!</h1>
            <p>This is a war simulator Discord bot.</p>
            <p>The bot is currently active and processing commands.</p>
        </body>
    </html>
    """

@app.route('/status')
def status():
    return {"status": "online", "bot": "Discord Hegemony Bot"}

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
