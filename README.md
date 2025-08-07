# Discord Hegemony Bot

A Discord bot for managing a war simulator game with complex military mechanics.

## Features

- **Brigade Management**: Create, enhance, and command different types of military units
- **General System**: Recruit generals with unique traits and level them up
- **War College**: Progress system that unlocks new capabilities
- **Battle System**: Automated combat with skirmish, pitch, and rally phases
- **War Justifications**: Formal reasons for declaring war with specific victory conditions
- **Siege Mechanics**: Multi-stage city sieges with assault or starvation options
- **Army Formation**: Combine brigades under generals for coordinated operations

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your Discord bot token:
```
DISCORD_TOKEN=your_bot_token_here
```

3. Run the bot:
```bash
python main.py
```

## Commands

### Player Management
- `/register` - Register as a new player
- `/profile [player]` - View player profile and statistics

### Brigade Commands
- `/create_brigade <type> [city]` - Create a new brigade
- `/enhance_brigade <brigade_id> <enhancement>` - Add enhancement to brigade
- `/list_brigades` - List all your brigades

### General Commands
- `/recruit_general` - Recruit a new general
- `/reroll_trait <general_id>` - Reroll general trait (costs 3 gems)
- `/retire_general <general_id>` - Retire a level 10 general

### Army Commands
- `/form_army <general_id> <brigade_ids>` - Form an army
- `/disband_army <army_id>` - Disband an army
- `/move_army <army_id> <direction>` - Move army

### Data Management Commands
- `/backup_data` - Create backup of all game data
- `/export_player [player]` - Export player data to JSON
- `/data_stats` - Show game statistics

### War Commands
- `/declare_war <target> <justification>` - Declare war
- `/list_justifications` - Show available war justifications
- `/peace_treaty` - Propose peace treaty

### Battle Commands
- `/battle_status` - Check ongoing battles
- `/siege <target_city>` - Begin sieging a city

### Utility Commands
- `/help` - Show command help
- `/game_status` - Show current game cycle and phase

## Game Mechanics

The bot implements the full warfare system including:
- 3-day action cycles (Tuesday-Thursday, Friday-Sunday)
- Brigade types: Cavalry, Heavy, Light, Ranged, Support
- Battle phases: Skirmish → Pitch → Rally → Action Report
- City sieges with timers and garrison defense
- General traits and promotion system
- War college progression

## Database

The bot uses JSON files for data storage in the `bot_data/` directory:
- `players.json` - Player data and statistics
- `brigades.json` - Individual military units
- `generals.json` - Army commanders with traits
- `armies.json` - Combined brigade formations
- `wars.json` - Active conflicts between players
- `battles.json` - Combat encounters and results
- `game_state.json` - Current phase and timing

## Data Management

### Viewing Data
Use the data viewer to inspect game data:
```bash
python view_data.py
```

### Backup & Export
- `!backup_data` - Create backup of all data
- `!export_player [player]` - Export specific player data
- `!data_stats` - Show game statistics

### JSON Structure
All data is stored in human-readable JSON format, making it easy to:
- Backup and restore game state
- Inspect data manually
- Transfer between servers
- Debug issues
