# Discord Hegemony Bot - Complete Documentation

## Overview

The Discord Hegemony Bot is a comprehensive war simulation game manager for Discord servers. It implements a complex military strategy game with brigades, generals, battles, sieges, and diplomatic elements.

## Key Features

### 🏗️ Brigade System
- **5 Brigade Types**: Cavalry, Heavy, Light, Ranged, Support
- **Individual Stats**: Each type has different Skirmish, Defense, Pitch, Rally, and Movement values
- **Enhancements**: Powerful upgrades that add special abilities and stat bonuses
- **Brigade Cap**: Limited by owned cities (Base 2 + city bonuses)

### 👑 General System  
- **20 Unique Traits**: Randomly assigned traits that provide army bonuses
- **Leveling System**: Generals gain experience through battles (1-10 levels)
- **Army Leadership**: Combine up to 8 brigades under a general
- **Retirement**: Level 10 generals can retire to boost War College

### ⚔️ Battle System
- **4-Phase Combat**: Skirmish → Pitch → Rally → Action Report
- **Automated Resolution**: Battles resolve automatically with detailed logs
- **Tactical Depth**: Positioning, terrain, and unit composition matter
- **Casualties**: Units can be destroyed or routed during combat

### 🏛️ War College
- **Progressive Benefits**: 10 levels of warfare mastery
- **Unlocks**: Higher levels unlock advanced justifications and bonuses
- **Multiple Paths**: Level up by winning wars or retiring generals

### ⚖️ War Justifications
- **8 Different Types**: From Border Disputes to Holy Wars
- **Victory Conditions**: Specific goals to achieve victory
- **Peace Terms**: Predetermined rewards and penalties
- **Requirements**: Each justification has prerequisites

### 🏰 Siege Mechanics
- **Multi-Stage Process**: Begin siege → Wait timer → Assault or Starve
- **City Tiers**: Different siege times and garrison strengths
- **Siege Options**: Occupy, Sack, or Raze captured cities
- **Automatic Garrisons**: Cities defend themselves with NPC troops

### 🗓️ 3-Day Cycle System
- **Organization Days**: Create/enhance brigades, recruit generals
- **Movement Days**: Move armies, pillage resources
- **Battle Days**: Fight battles, conduct sieges

## Command Reference

### Player Management
```
!register                           # Register as a new player
!profile [player]                   # View player profile and stats
```

### Brigade Commands
```
!create_brigade <type> [city]       # Create a new brigade
!list_brigades                      # List all your brigades
!enhance_brigade <id> <enhancement> # Add enhancement to brigade
!brigade_types                      # Show all brigade types and stats
!list_enhancements [type]           # Show available enhancements
```

### General Commands
```
!recruit_general [name]             # Recruit a new general
!list_generals                      # List all your generals
!general_traits                     # Show all possible traits
```

### War Commands
```
!list_justifications [target]       # Show available war justifications
!justification_details <name>       # Detailed info on a justification
!declare_war <target> <justification> # Declare war on another player
```

### Battle Commands
```
!start_siege <city>                 # Begin sieging an enemy city
!simulate_battle <id1> <id2>        # Test battle between brigades
```

### Information Commands
```
!game_status                        # Current game phase and timing
!war_college_benefits               # Show War College level benefits
!quick_reference                    # Essential game mechanics
!help_warfare                       # Detailed warfare guide
```

## Game Mechanics Deep Dive

### Brigade Types & Stats

| Type | Skirmish | Defense | Pitch | Rally | Movement |
|------|----------|---------|-------|--------|----------|
| 🐴 Cavalry | +1 | 0 | +1 | 0 | 5 |
| ⚔️ Heavy | 0 | +2 | +1 | +1 | 3 |
| 🪓 Light | +2 | 0 | 0 | +1 | 4 |
| 🏹 Ranged | 0 | +2 | +1 | 0 | 4 |
| 🛡️ Support | 0 | +2 | 0 | +1 | 4 |

### Battle Phase Details

1. **Skirmish Phase**
   - Each side selects 2 best skirmishers
   - Random target selection
   - Skirmish roll vs Defense roll
   - Winner routes target, 3+ difference = overrun

2. **Pitch Phase**
   - 3 rounds of d6 rolls + bonuses
   - Positive vs Negative sides
   - Tally tracked across rounds
   - ±20 = decisive victory

3. **Rally Phase**
   - All brigades roll d6 + rally bonuses
   - 5+ = stay in battle, <5 = rout
   - Continue to new pitch or end battle

4. **Action Report**
   - All brigades roll destruction dice (1-2 = destroyed)
   - Generals roll promotion dice (1 = captured, 5-6 = promoted)
   - Winners get rerolls

### War Justifications Summary

| Justification | War College Req | Main Victory Condition | Main Reward |
|---------------|-----------------|------------------------|-------------|
| Border Dispute | 1 | Occupy 1 city for 2 cycles | 3 border tiles |
| Trade War | 1 | Destroy/occupy trade port | Exclusive trade rights |
| Religious War | 2 | Destroy 2 religious buildings | Convert enemy city |
| Conquest | 3 | Occupy 50% of enemy cities | 6 tiles + 1 city |
| Liberation | 1 | Occupy recently conquered territory | Gain liberated territory |
| Punitive Expedition | 2 | Sack 1 city, destroy 3 brigades | 300 silver + 3 tiles |
| Succession Crisis | Special | Occupy enemy capital | Full control of nation |
| Holy War | 3 | Convert/destroy all religious buildings | Convert enemy nation |

### Enhancement Categories

**Cavalry Enhancements:**
- Life Guard: +2 Rally, general reroll ability
- Lancers: +2 Skirmish, auto-overrun
- Dragoons: +2 Defense, +1 Pitch, +1 Rally

**Heavy Enhancements:**
- Artillery Team: +1 Defense/Pitch, -1 enemy defense
- Grenadiers: +2 Skirmish, +2 Pitch  
- Stormtroopers: +1 Pitch/Rally/Movement, ignore trenches

**Light Enhancements:**
- Rangers: +2 Skirmish, +1 Pitch
- Assault Team: +1 Skirmish, choose targets
- Commando: +2 Defense, +1 Pitch, stealth

**Ranged Enhancements:**
- Sharpshooters: +2 Defense, rout attackers
- Mobile Platforms: +1 Skirmish/Defense/Movement
- Mortar Team: +1 Pitch/Rally, negate garrison

**Support Enhancements:**
- Field Hospital: Reroll destruction dice
- Combat Engineers: Build structures, reduce siege time
- Officer Corps: +2 Rally, general promotion bonus

**Universal Enhancements:**
- Sentry Team: +3 Defense, +1 sight range
- Marines: Immediate siege, sea movement bonus

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- Discord bot token
- Discord server with appropriate permissions

### Installation Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/LadyHannelore/Discord-Hegemony-bot.git
   cd Discord-Hegemony-bot
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Bot Token**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add your bot token
   DISCORD_TOKEN=your_bot_token_here
   ```

4. **Run the Bot**
   ```bash
   # Windows
   start.bat
   
   # Linux/Mac
   chmod +x start.sh
   ./start.sh
   
   # Or directly
   python main.py
   ```

### Discord Bot Setup

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Go to "Bot" section and create a bot
4. Copy the bot token to your `.env` file
5. Under "Privileged Gateway Intents", enable:
   - Message Content Intent
6. Go to "OAuth2" → "URL Generator"
7. Select scopes: `bot`, `applications.commands`
8. Select permissions: 
   - Send Messages
   - Use Slash Commands  
   - Embed Links
   - Read Message History
9. Use the generated URL to invite the bot to your server

## Database Schema

The bot uses SQLite with the following tables:

- **players**: User registration and resources
- **brigades**: Individual military units
- **generals**: Army commanders with traits
- **armies**: Combined brigade formations
- **wars**: Active conflicts between players
- **battles**: Combat encounters and results
- **game_state**: Current phase and timing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions, bug reports, or feature requests, please open an issue on GitHub or contact the development team.

## Roadmap

### Planned Features
- [ ] Interactive map system
- [ ] Diplomatic treaties and alliances
- [ ] Economic trade systems
- [ ] Naval units and sea battles
- [ ] Temporary structures (forts, trenches)
- [ ] Advanced AI opponents
- [ ] Tournament and league systems
- [ ] Web dashboard for game state

### Known Issues
- Battle simulation needs more testing
- Resource management system incomplete
- Map movement system not yet implemented

## Credits

Developed by LadyHannelore for Lex's war simulation community.

Special thanks to the Discord.py community and all beta testers.
