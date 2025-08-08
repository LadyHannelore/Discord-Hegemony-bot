import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import asyncio
from dotenv import load_dotenv

try:
    import aiofiles
except ImportError:
    aiofiles = None

from models import (
    BrigadeType, GamePhase, BRIGADE_STATS, 
    ENHANCEMENTS, GENERAL_TRAITS, Enhancement, BrigadeStats
)
from json_data_manager import JsonDataManager
from war_justifications import WAR_JUSTIFICATIONS, get_available_justifications, validate_justification
from battle_system import BattleSystem, BattleSide, create_battle_brigade, create_battle_general

# Import keep_alive for Replit hosting
try:
    from keep_alive import keep_alive
    REPLIT_HOSTING = True
except ImportError:
    REPLIT_HOSTING = False
    keep_alive = None

# Load environment variables
load_dotenv()

# Bot setup - Only use basic intents (no privileged intents required)
intents = discord.Intents.default()
# Remove message_content intent as it's privileged and we only use slash commands
# intents.message_content = True  # Not needed for slash commands

class HegemonyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='/', intents=intents)

    async def setup_hook(self):
        # Sync slash commands on startup
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} slash commands")
        except Exception as e:
            print(f"Failed to sync slash commands: {e}")

bot = HegemonyBot()

# Initialize JSON data manager
db = JsonDataManager()

class WarBot:
    def __init__(self):
        self.current_phase = GamePhase.ORGANIZATION
        self.battles_in_progress = {}

    def get_brigade_total_stats(self, brigade_type: BrigadeType, enhancement: Optional[str] = None, 
                               is_garrisoned: bool = False, general_level: int = 0) -> BrigadeStats:
        """Calculate total stats for a brigade including enhancements and bonuses."""
        base_stats = BRIGADE_STATS[brigade_type]
        total_stats = BrigadeStats(
            skirmish=base_stats.skirmish,
            defense=base_stats.defense,
            pitch=base_stats.pitch,
            rally=base_stats.rally,
            movement=base_stats.movement
        )
        
        # Apply enhancement bonuses
        if enhancement and enhancement in ENHANCEMENTS:
            enh = ENHANCEMENTS[enhancement]
            total_stats.skirmish += enh.stats.skirmish
            total_stats.defense += enh.stats.defense
            total_stats.pitch += enh.stats.pitch
            total_stats.rally += enh.stats.rally
            total_stats.movement += enh.stats.movement
        
        # Apply garrison bonuses
        if is_garrisoned:
            total_stats.defense += 2
            total_stats.rally += 2
        
        return total_stats

    def roll_general_trait(self) -> int:
        """Roll a random general trait."""
        return random.randint(1, 20)

    def calculate_brigade_cap(self, cities: List[dict]) -> int:
        """Calculate brigade cap based on owned cities."""
        base_cap = 2
        for city in cities:
            tier = city.get('tier', 1)
            if tier == 1:
                base_cap += 1
            elif tier == 2:
                base_cap += 3
            elif tier == 3:
                base_cap += 5
        return base_cap

war_bot = WarBot()
battle_system = BattleSystem()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    await db.init_data_files()
    # Start the game cycle task
    game_cycle_task.start()
    print("Bot is ready! Use slash commands (e.g., /register, /profile, /help_warfare)")

@tasks.loop(hours=24)  # Check daily for phase changes
async def game_cycle_task():
    """Manage the 3-day game cycle."""
    now = datetime.now()
    weekday = now.weekday()  # 0=Monday, 1=Tuesday, etc.
    
    # Tuesday(1) and Friday(4) = Organization
    # Wednesday(2) and Saturday(5) = Movement  
    # Thursday(3) and Sunday(6) = Battle
    # Monday(0) = Rest day
    
    if weekday in [1, 4]:  # Tuesday, Friday
        war_bot.current_phase = GamePhase.ORGANIZATION
    elif weekday in [2, 5]:  # Wednesday, Saturday
        war_bot.current_phase = GamePhase.MOVEMENT
    elif weekday in [3, 6]:  # Thursday, Sunday
        war_bot.current_phase = GamePhase.BATTLE

# Slash Commands
@bot.tree.command(name="register", description="Register as a new player to start your nation")
async def register_slash(interaction: discord.Interaction):
    """Register as a new player."""
    user_id = interaction.user.id
    username = interaction.user.display_name
    
    existing_player = await db.get_player(user_id)
    if existing_player:
        await interaction.response.send_message(f"You're already registered, {username}!")
        return
    
    success = await db.create_player(user_id, username)
    if success:
        embed = discord.Embed(
            title="Welcome to Hegemony!",
            description=f"{username} has been registered as a new player.",
            color=discord.Color.green()
        )
        embed.add_field(name="Starting Resources", value="Food: 10, Metal: 10, Silver: 100", inline=False)
        embed.add_field(name="Brigade Cap", value="2", inline=True)
        embed.add_field(name="War College Level", value="1", inline=True)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("Registration failed. Please try again.")

@bot.tree.command(name="profile", description="View player profile and statistics")
@app_commands.describe(member="The player to view (optional, defaults to yourself)")
async def profile_slash(interaction: discord.Interaction, member: Optional[discord.Member] = None):
    """Show player profile and statistics."""
    target = member or interaction.user
    player = await db.get_player(target.id)
    
    if not player:
        await interaction.response.send_message(f"{target.display_name} is not registered. Use `/register` to join.")
        return
    
    resources = player.get('resources', {})
    cities = player.get('cities', [])
    
    embed = discord.Embed(
        title=f"{target.display_name}'s Profile",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="War College Level", value=player['war_college_level'], inline=True)
    embed.add_field(name="Brigade Cap", value=player['brigade_cap'], inline=True)
    embed.add_field(name="General Cap", value=player['general_cap'], inline=True)
    
    resource_text = ", ".join([f"{k.title()}: {v}" for k, v in resources.items()])
    embed.add_field(name="Resources", value=resource_text or "None", inline=False)
    
    embed.add_field(name="Cities", value=str(len(cities)), inline=True)
    embed.add_field(name="Silver", value=player['silver'], inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="create_brigade", description="Create a new military brigade")
@app_commands.describe(
    brigade_type="Type of brigade to create",
    city="City to create the brigade in"
)
@app_commands.choices(brigade_type=[
    app_commands.Choice(name="🐴 Cavalry", value="🐴 Cavalry"),
    app_commands.Choice(name="⚔️ Heavy", value="⚔️ Heavy"),
    app_commands.Choice(name="🪓 Light", value="🪓 Light"),
    app_commands.Choice(name="🏹 Ranged", value="🏹 Ranged"),
    app_commands.Choice(name="🛡️ Support", value="🛡️ Support")
])
async def create_brigade_slash(interaction: discord.Interaction, brigade_type: str, city: str = "Capital"):
    """Create a new brigade."""
    if war_bot.current_phase != GamePhase.ORGANIZATION:
        await interaction.response.send_message("Brigades can only be created during Organization phase (Tuesday/Friday)!")
        return
    
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    # Check brigade cap
    current_brigades = await db.get_brigades(interaction.user.id)
    if len(current_brigades) >= player['brigade_cap']:
        await interaction.response.send_message(f"You've reached your brigade cap of {player['brigade_cap']}!")
        return
    
    # Check resources (2 food + 1 metal OR 40 silver)
    resources = player.get('resources', {})
    has_resources = resources.get('food', 0) >= 2 and resources.get('metal', 0) >= 1
    has_silver = player.get('silver', 0) >= 40
    
    if not (has_resources or has_silver):
        await interaction.response.send_message("Insufficient resources! Need 2 food + 1 metal OR 40 silver.")
        return
    
    # Create the brigade
    brigade_id = await db.create_brigade(interaction.user.id, brigade_type, city)
    
    # Deduct resources (prefer resources over silver)
    if has_resources:
        await db.deduct_resources(interaction.user.id, {"food": 2, "metal": 1})
        cost_text = "2 food + 1 metal"
    else:
        await db.deduct_silver(interaction.user.id, 40)
        cost_text = "40 silver"
    
    embed = discord.Embed(
        title="Brigade Created!",
        description=f"Created {brigade_type} brigade at {city}",
        color=discord.Color.green()
    )
    
    # Show brigade stats - find matching brigade type
    try:
        brigade_enum = next(bt for bt in BrigadeType if bt.value == brigade_type)
        stats = BRIGADE_STATS[brigade_enum]
        
        embed.add_field(name="Stats", value=(
            f"⚔️ Skirmish: {stats.skirmish}\n"
            f"🛡️ Defense: {stats.defense}\n"
            f"📯 Pitch: {stats.pitch}\n"
            f"🚩 Rally: {stats.rally}\n"
            f"🏃 Movement: {stats.movement}"
        ), inline=True)
    except StopIteration:
        # Fallback if brigade type not found
        embed.add_field(name="Stats", value="Stats will be available after creation", inline=True)
    
    embed.add_field(name="Brigade ID", value=str(brigade_id), inline=True)
    embed.add_field(name="Cost", value=cost_text, inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="list_brigades", description="List all your brigades")
async def list_brigades_slash(interaction: discord.Interaction):
    """List all your brigades."""
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    brigades = await db.get_brigades(interaction.user.id)
    
    if not brigades:
        await interaction.response.send_message("You have no brigades. Create one with `/create_brigade`")
        return
    
    embed = discord.Embed(
        title=f"{interaction.user.display_name}'s Brigades",
        color=discord.Color.blue()
    )
    
    for brigade in brigades:
        enhancement_text = f" ({brigade['enhancement']})" if brigade['enhancement'] else ""
        status_text = ""
        if brigade['is_garrisoned']:
            status_text += " 🏰"
        if brigade['is_fatigued']:
            status_text += " 😴"
        
        embed.add_field(
            name=f"{brigade['id']} {brigade['type']}{enhancement_text}",
            value=f"📍 {brigade['location']}{status_text}",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="recruit_general", description="Recruit a new general for your army")
@app_commands.describe(name="Custom name for the general (optional)")
async def recruit_general_slash(interaction: discord.Interaction, name: Optional[str] = None):
    """Recruit a new general."""
    if war_bot.current_phase != GamePhase.ORGANIZATION:
        await interaction.response.send_message("Generals can only be recruited during Organization phase (Tuesday/Friday)!")
        return
    
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    # Check general cap
    current_generals = await db.get_generals(interaction.user.id)
    if len(current_generals) >= player['general_cap']:
        await interaction.response.send_message(f"You've reached your general cap of {player['general_cap']}!")
        return
    
    # Calculate cost (100 silver per existing general)
    cost = len(current_generals) * 100
    if player.get('silver', 0) < cost:
        await interaction.response.send_message(f"Insufficient silver! Need {cost} silver.")
        return
    
    # Generate random name if not provided
    if not name:
        name_options = ["Alexander", "Caesar", "Napoleon", "Hannibal", "Wellington", 
                       "Scipio", "Patton", "Rommel", "Montgomery", "Zhukov"]
        name = random.choice(name_options)
    
    # Roll trait
    trait_id = war_bot.roll_general_trait()
    
    # Create general
    general_id = await db.create_general(interaction.user.id, name, trait_id)
    
    # Deduct silver from player
    await db.deduct_silver(interaction.user.id, cost)
    
    trait_name, trait_desc = GENERAL_TRAITS[trait_id]
    
    embed = discord.Embed(
        title="General Recruited!",
        description=f"**{name}** has joined your forces!",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="General ID", value=str(general_id), inline=True)
    embed.add_field(name="Level", value="1", inline=True)
    embed.add_field(name="Cost", value=f"{cost} silver", inline=True)
    embed.add_field(name="Trait", value=f"**{trait_name}**\n{trait_desc}", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="list_generals", description="List all your generals")
async def list_generals_slash(interaction: discord.Interaction):
    """List all your generals."""
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    generals = await db.get_generals(interaction.user.id)
    
    if not generals:
        await interaction.response.send_message("You have no generals. Recruit one with `/recruit_general`")
        return
    
    embed = discord.Embed(
        title=f"{interaction.user.display_name}'s Generals",
        color=discord.Color.gold()
    )
    
    for general in generals:
        trait_name, trait_desc = GENERAL_TRAITS[general['trait_id']]
        status = "🏰" if general['army_id'] else "🏠"
        
        embed.add_field(
            name=f"#{general['id']} {general['name']} (Level {general['level']}) {status}",
            value=f"**{trait_name}**: {trait_desc}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="game_status", description="Check current game phase and timing")
async def game_status_slash(interaction: discord.Interaction):
    """Show current game cycle and phase."""
    now = datetime.now()
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    current_day = weekday_names[now.weekday()]
    
    embed = discord.Embed(
        title="Game Status",
        color=discord.Color.purple()
    )
    
    embed.add_field(name="Current Day", value=current_day, inline=True)
    embed.add_field(name="Current Phase", value=war_bot.current_phase.value, inline=True)
    
    # Phase descriptions
    phase_info = {
        GamePhase.ORGANIZATION: "Create/enhance brigades, recruit generals, build structures",
        GamePhase.MOVEMENT: "Move brigades/armies, pillage resources", 
        GamePhase.BATTLE: "Fight battles, siege cities"
    }
    
    embed.add_field(name="Phase Actions", value=phase_info[war_bot.current_phase], inline=False)
    
    # Next phase timing
    next_phase_day = {
        GamePhase.ORGANIZATION: "Wednesday/Saturday",
        GamePhase.MOVEMENT: "Thursday/Sunday",
        GamePhase.BATTLE: "Tuesday/Friday"
    }
    
    embed.add_field(name="Next Phase", value=next_phase_day[war_bot.current_phase], inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="brigade_types", description="Show all available brigade types and their stats")
async def brigade_types_slash(interaction: discord.Interaction):
    """Show all brigade types and their stats."""
    embed = discord.Embed(
        title="Brigade Types & Stats",
        color=discord.Color.green()
    )
    
    for brigade_type, stats in BRIGADE_STATS.items():
        embed.add_field(
            name=brigade_type.value,
            value=(
                f"⚔️ Skirmish: {stats.skirmish}\n"
                f"🛡️ Defense: {stats.defense}\n"
                f"📯 Pitch: {stats.pitch}\n"
                f"🚩 Rally: {stats.rally}\n"
                f"🏃 Movement: {stats.movement}"
            ),
            inline=True
        )
    
    embed.add_field(name="Cost", value="2 food + 1 metal OR 40 silver", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="declare_war", description="Declare war against another player")
@app_commands.describe(
    target="The player to declare war on",
    justification="Reason for declaring war"
)
async def declare_war_slash(interaction: discord.Interaction, target: discord.Member, justification: str):
    """Declare war against another player."""
    if war_bot.current_phase != GamePhase.ORGANIZATION:
        await interaction.response.send_message("Wars can only be declared during Organization phase!")
        return
    
    # Validate players
    attacker = await db.get_player(interaction.user.id)
    defender = await db.get_player(target.id)
    
    if not attacker:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    if not defender:
        await interaction.response.send_message(f"{target.display_name} is not registered.")
        return
    
    if interaction.user.id == target.id:
        await interaction.response.send_message("You cannot declare war on yourself!")
        return
    
    # Validate justification
    is_valid, error_msg = validate_justification(
        justification, dict(attacker), dict(defender)
    )
    
    if not is_valid:
        await interaction.response.send_message(f"Invalid justification: {error_msg}")
        return
    
    # Check for existing active wars
    existing_wars = await db.get_active_wars(interaction.user.id)
    for war in existing_wars:
        if (war.get('attacker_id') == interaction.user.id and war.get('defender_id') == target.id) or \
           (war.get('attacker_id') == target.id and war.get('defender_id') == interaction.user.id):
            await interaction.response.send_message("There is already an active war between these players!")
            return
    
    # Create war in database
    justification_data = WAR_JUSTIFICATIONS[justification]
    war_id = await db.create_war(
        interaction.user.id, 
        target.id, 
        justification,
        justification_data.victory_conditions,
        justification_data.defeat_conditions
    )
    
    embed = discord.Embed(
        title="⚔️ WAR DECLARED!",
        description=f"**{interaction.user.display_name}** has declared war on **{target.display_name}**",
        color=discord.Color.dark_red()
    )
    
    embed.add_field(name="Justification", value=justification_data.name, inline=True)
    embed.add_field(name="Attacker", value=interaction.user.display_name, inline=True)
    embed.add_field(name="Defender", value=target.display_name, inline=True)
    
    embed.add_field(
        name="Victory Conditions (Attacker)",
        value="\n".join([f"• {cond}" for cond in justification_data.victory_conditions]),
        inline=False
    )
    
    embed.set_footer(text="The war has begun! Prepare your forces!")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Show comprehensive help for the war game")
async def help_slash(interaction: discord.Interaction):
    """Show detailed warfare help."""
    embed = discord.Embed(
        title="🎮 Hegemony War Game Commands",
        description="Complete guide to playing the war simulation",
        color=discord.Color.dark_blue()
    )
    
    embed.add_field(name="🏗️ Getting Started", value=(
        "`/register` - Register as a new player\n"
        "`/profile` - View your nation's status\n"
        "`/game_status` - Check current game phase"
    ), inline=False)
    
    embed.add_field(name="⚔️ Military Commands", value=(
        "`/create_brigade` - Create new military unit\n"
        "`/list_brigades` - View your brigades\n"
        "`/recruit_general` - Recruit general\n"
        "`/list_generals` - View your generals"
    ), inline=False)
    
    embed.add_field(name="🌍 Combat & Diplomacy", value=(
        "`/declare_war` - Declare war on another player\n"
        "`/brigade_types` - View unit types and stats\n"
        "`/move_brigade` - Move military units\n"
        "`/pillage` - Raid for resources"
    ), inline=False)
    
    embed.add_field(name="📅 Game Phases", value=(
        "**Tuesday/Friday**: Organization (create units)\n"
        "**Wednesday/Saturday**: Movement (move & pillage)\n"
        "**Thursday/Sunday**: Battle (fight & siege)"
    ), inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="move_brigade", description="Move a brigade in a direction")
@app_commands.describe(
    brigade_id="ID of the brigade to move",
    direction="Direction to move the brigade"
)
@app_commands.choices(direction=[
    app_commands.Choice(name="North", value="north"),
    app_commands.Choice(name="South", value="south"),
    app_commands.Choice(name="East", value="east"),
    app_commands.Choice(name="West", value="west"),
    app_commands.Choice(name="Northeast", value="northeast"),
    app_commands.Choice(name="Northwest", value="northwest"),
    app_commands.Choice(name="Southeast", value="southeast"),
    app_commands.Choice(name="Southwest", value="southwest")
])
async def move_brigade_slash(interaction: discord.Interaction, brigade_id: str, direction: str):
    """Move a brigade in a direction."""
    if war_bot.current_phase != GamePhase.MOVEMENT:
        await interaction.response.send_message("Brigades can only be moved during Movement phase (Wednesday/Saturday)!")
        return
    
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    brigade = await db.get_brigade(brigade_id)
    if not brigade:
        await interaction.response.send_message("Brigade not found.")
        return
    
    if brigade['player_id'] != interaction.user.id:
        await interaction.response.send_message("You don't own this brigade.")
        return
    
    if brigade.get('army_id'):
        await interaction.response.send_message("This brigade is part of an army. Use `/move_army` instead.")
        return
    
    # Update brigade location (simplified - just append direction)
    current_location = brigade.get('location', 'Unknown')
    new_location = f"{current_location} -> {direction.title()}"
    await db.update_brigade(brigade_id, {"location": new_location})
    
    embed = discord.Embed(
        title="Brigade Moved",
        description=f"Brigade {brigade_id} moved {direction}",
        color=discord.Color.green()
    )
    embed.add_field(name="New Location", value=new_location, inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="pillage", description="Pillage resources with a brigade")
@app_commands.describe(brigade_id="ID of the brigade to use for pillaging")
async def pillage_slash(interaction: discord.Interaction, brigade_id: str):
    """Pillage resources with a brigade."""
    if war_bot.current_phase != GamePhase.MOVEMENT:
        await interaction.response.send_message("Pillaging can only be done during Movement phase (Wednesday/Saturday)!")
        return
    
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    brigade = await db.get_brigade(brigade_id)
    if not brigade:
        await interaction.response.send_message("Brigade not found.")
        return
    
    if brigade['player_id'] != interaction.user.id:
        await interaction.response.send_message("You don't own this brigade.")
        return
    
    if brigade.get('is_garrisoned'):
        await interaction.response.send_message("Garrisoned brigades cannot pillage.")
        return
    
    # Roll for pillage success (6 on d6)
    roll = random.randint(1, 6)
    
    embed = discord.Embed(title="Pillaging Attempt", color=discord.Color.orange())
    embed.add_field(name="Brigade", value=f"{brigade['type']} at {brigade.get('location', 'Unknown')}", inline=False)
    embed.add_field(name="Roll", value=f"🎲 {roll}/6", inline=True)
    
    if roll == 6:
        # Successful pillage - gain random resource
        resources = ['food', 'metal', 'wood', 'stone']
        gained_resource = random.choice(resources)
        amount = 1
        
        await db.add_resource(interaction.user.id, gained_resource, amount)
        
        embed.add_field(name="Result", value="✅ Success!", inline=True)
        embed.add_field(name="Gained", value=f"{amount} {gained_resource}", inline=True)
        embed.color = discord.Color.green()
    else:
        embed.add_field(name="Result", value="❌ Failed", inline=True)
        embed.add_field(name="Gained", value="Nothing", inline=True)
        embed.color = discord.Color.red()
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="data_stats", description="Show game statistics and player counts")
async def data_stats_slash(interaction: discord.Interaction):
    """Show game data statistics."""
    try:
        players = await db.get_all_players()
        brigades = await db.get_all_brigades()
        generals = await db.get_all_generals()
        armies = await db.get_all_armies()
        wars = await db.get_all_wars()
        
        embed = discord.Embed(
            title="📊 Game Statistics",
            description="Current state of the game world",
            color=discord.Color.blue()
        )
        
        # Basic counts
        embed.add_field(name="👥 Players", value=str(len(players)), inline=True)
        embed.add_field(name="⚔️ Brigades", value=str(len(brigades)), inline=True)
        embed.add_field(name="🎖️ Generals", value=str(len(generals)), inline=True)
        embed.add_field(name="🚩 Armies", value=str(len(armies)), inline=True)
        embed.add_field(name="⚔️ Wars", value=str(len(wars)), inline=True)
        
        # Active wars
        active_wars = len([w for w in wars.values() if w.get('status') == 'active'])
        embed.add_field(name="🔥 Active Wars", value=str(active_wars), inline=True)
        
        embed.add_field(name="Current Phase", value=war_bot.current_phase.value, inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    except Exception as e:
        await interaction.response.send_message(f"❌ Error retrieving statistics: {e}")

# Error handling
@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"Command is on cooldown. Try again in {error.retry_after:.2f} seconds.")
    else:
        await interaction.response.send_message(f"An error occurred: {error}")

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("ERROR: DISCORD_TOKEN not found in environment variables!")
        print("Please create a .env file with your bot token.")
    else:
        # Start keep-alive server for Replit hosting
        if REPLIT_HOSTING and keep_alive:
            try:
                keep_alive()
                print("Keep-alive server started for Replit hosting")
            except Exception as e:
                print(f"Could not start keep-alive server: {e}")
        
        bot.run(token)
