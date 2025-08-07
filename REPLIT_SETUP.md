# Discord Hegemony Bot - Replit Deployment

## Quick Setup for Replit

### 1. Environment Variables
- Go to the "Secrets" tab in your Replit project
- Add a new secret:
  - **Key**: `DISCORD_TOKEN`
  - **Value**: Your Discord bot token

### 2. Bot Setup
If you haven't created a Discord bot yet:
1. Go to https://discord.com/developers/applications
2. Create a new application
3. Go to the "Bot" section
4. Create a bot and copy the token
5. In "OAuth2" → "URL Generator", select:
   - **Scopes**: `bot`, `applications.commands`
   - **Permissions**: `Send Messages`, `Use Slash Commands`, `Embed Links`

### 3. Run the Bot
- Click the "Run" button in Replit
- The bot will automatically install dependencies and start
- You should see "Keep-alive server started for Replit hosting" in the console

### 4. Invite Bot to Server
Use the OAuth2 URL from step 2 to invite your bot to a Discord server.

### 5. Test the Bot
In your Discord server, try:
- `/register` - Register as a player
- `/help` - See all available commands
- `/recruit_brigade` - Recruit your first brigade

## Features
- **War Simulation**: Complete military strategy game
- **JSON Storage**: All data saved in human-readable files
- **Phase System**: Organization, Mobilization, and War phases
- **Battle System**: Automated combat resolution
- **Keep-Alive**: Automatic server to prevent Replit sleeping

## Data Files
The bot creates a `bot_data/` folder with:
- `players.json` - Player information
- `brigades.json` - Military units
- `generals.json` - Army commanders
- `armies.json` - Organized forces
- `wars.json` - Active conflicts
- `game_state.json` - Current game phase

## Need Help?
Check the main README.md for detailed command documentation and game mechanics.
