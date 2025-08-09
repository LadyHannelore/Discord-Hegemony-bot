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
from siege_system import SiegeSystem
from temporary_structures import TemporaryStructureSystem, StructureType

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

# Initialize additional systems
siege_system = SiegeSystem(db)
structure_system = TemporaryStructureSystem(db)

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
    
    # Calculate dynamic values
    brigade_cap = calculate_brigade_cap(player)
    general_cap = calculate_general_cap(player.get('war_college_level', 1))
    
    embed = discord.Embed(
        title=f"{target.display_name}'s Profile",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="War College Level", value=player['war_college_level'], inline=True)
    embed.add_field(name="Brigade Cap", value=brigade_cap, inline=True)
    embed.add_field(name="General Cap", value=general_cap, inline=True)
    
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
    brigade_cap = calculate_brigade_cap(player)
    
    if len(current_brigades) >= brigade_cap:
        await interaction.response.send_message(f"You've reached your brigade cap of {brigade_cap}!")
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
    
    # Roll trait (with War College Level 2 double roll)
    war_college_level = player.get('war_college_level', 1)
    
    if war_college_level >= 2:
        # Roll twice and choose
        trait_id_1 = war_bot.roll_general_trait()
        trait_id_2 = war_bot.roll_general_trait()
        
        trait_1_name, trait_1_desc = GENERAL_TRAITS[trait_id_1]
        trait_2_name, trait_2_desc = GENERAL_TRAITS[trait_id_2]
        
        # For simplicity, randomly choose one (in real game, player would choose)
        trait_id = random.choice([trait_id_1, trait_id_2])
        trait_name, trait_desc = GENERAL_TRAITS[trait_id]
        
        trait_info = f"**{trait_name}** (chosen from {trait_1_name}/{trait_2_name})\n{trait_desc}"
    else:
        trait_id = war_bot.roll_general_trait()
        trait_name, trait_desc = GENERAL_TRAITS[trait_id]
        trait_info = f"**{trait_name}**\n{trait_desc}"
    
    # Create general
    general_id = await db.create_general(interaction.user.id, name, trait_id)
    
    # Deduct silver from player
    await db.deduct_silver(interaction.user.id, cost)
    
    embed = discord.Embed(
        title="General Recruited!",
        description=f"**{name}** has joined your forces!",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="General ID", value=str(general_id), inline=True)
    embed.add_field(name="Level", value="1", inline=True)
    embed.add_field(name="Cost", value=f"{cost} silver", inline=True)
    embed.add_field(name="Trait", value=trait_info, inline=False)
    
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
    
    # Roll for pillage success (6 on d6, or 5-6 with Brutal trait)
    roll = random.randint(1, 6)
    success_threshold = 6
    brutal_general = False
    
    # Check if brigade is in an army with a general
    army_id = brigade.get('army_id')
    if army_id:
        army = await db.get_army(army_id)
        if army and army.get('general_id'):
            general = await db.get_general(army['general_id'])
            if general:
                trait_name, _ = GENERAL_TRAITS[general['trait_id']]
                if trait_name == "Brutal":
                    success_threshold = 5
                    brutal_general = True
    
    embed = discord.Embed(title="Pillaging Attempt", color=discord.Color.orange())
    embed.add_field(name="Brigade", value=f"{brigade['type']} at {brigade.get('location', 'Unknown')}", inline=False)
    embed.add_field(name="Roll", value=f"🎲 {roll}/6", inline=True)
    
    if brutal_general:
        embed.add_field(name="Brutal General", value="Success on 5-6", inline=True)
    
    if roll >= success_threshold:
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

@bot.tree.command(name="enhance_brigade", description="Add an enhancement to a brigade")
@app_commands.describe(
    brigade_id="ID of the brigade to enhance",
    enhancement="Enhancement to add"
)
async def enhance_brigade_slash(interaction: discord.Interaction, brigade_id: str, enhancement: str):
    """Add an enhancement to a brigade."""
    if war_bot.current_phase != GamePhase.ORGANIZATION:
        await interaction.response.send_message("Brigades can only be enhanced during Organization phase!")
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
    
    if brigade.get('enhancement'):
        await interaction.response.send_message("This brigade already has an enhancement.")
        return
    
    # Check if enhancement exists and is valid for brigade type
    if enhancement not in ENHANCEMENTS:
        await interaction.response.send_message("Invalid enhancement.")
        return
    
    enhancement_data = ENHANCEMENTS[enhancement]
    brigade_type = next(bt for bt in BrigadeType if bt.value.split()[1].lower() == brigade['type'])
    
    # Check if enhancement is compatible with brigade type
    if enhancement_data.brigade_type and enhancement_data.brigade_type != brigade_type:
        await interaction.response.send_message(f"Enhancement '{enhancement}' cannot be applied to {brigade['type']} brigades.")
        return
    
    # Check if player can afford enhancement
    if player.get('silver', 0) < enhancement_data.cost_silver:
        await interaction.response.send_message(f"Insufficient silver! Need {enhancement_data.cost_silver} silver.")
        return
    
    # Check resource costs
    if enhancement_data.cost_resources:
        for resource, cost in enhancement_data.cost_resources.items():
            if player.get('resources', {}).get(resource, 0) < cost:
                await interaction.response.send_message(f"Insufficient {resource}! Need {cost}.")
                return
    
    # Deduct costs
    await db.deduct_silver(interaction.user.id, enhancement_data.cost_silver)
    if enhancement_data.cost_resources:
        await db.deduct_resources(interaction.user.id, enhancement_data.cost_resources)
    
    # Apply enhancement
    await db.update_brigade(brigade_id, {"enhancement": enhancement})
    
    embed = discord.Embed(
        title="Brigade Enhanced!",
        description=f"Brigade {brigade_id} has been enhanced",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="Enhancement", value=enhancement, inline=True)
    embed.add_field(name="Cost", value=f"{enhancement_data.cost_silver} silver", inline=True)
    
    if enhancement_data.cost_resources:
        resources_cost = ", ".join([f"{amount} {resource}" for resource, amount in enhancement_data.cost_resources.items()])
        embed.add_field(name="Resources", value=resources_cost, inline=True)
    
    if enhancement_data.special_ability:
        embed.add_field(name="Special Ability", value=enhancement_data.special_ability, inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="build_structure", description="Build a temporary structure")
@app_commands.describe(
    structure_type="Type of structure to build",
    location="Location to build the structure"
)
@app_commands.choices(structure_type=[
    app_commands.Choice(name="Trench (1 stone)", value="trench"),
    app_commands.Choice(name="Watchtower (2 stone)", value="watchtower"),
    app_commands.Choice(name="Fort (3 stone)", value="fort")
])
async def build_structure_slash(interaction: discord.Interaction, structure_type: str, location: str):
    """Build a temporary structure."""
    structure_enum = StructureType(structure_type)
    result = await structure_system.build_structure(interaction.user.id, structure_enum, location)
    
    if result["success"]:
        embed = discord.Embed(
            title="Structure Built!",
            description=result["message"],
            color=discord.Color.green()
        )
        embed.add_field(name="Effect", value=result["effect"], inline=False)
        embed.add_field(name="Expires", value="Next map update", inline=True)
    else:
        embed = discord.Embed(
            title="Construction Failed",
            description=result["message"],
            color=discord.Color.red()
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="list_structures", description="List your temporary structures")
async def list_structures_slash(interaction: discord.Interaction):
    """List player's temporary structures."""
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    structures = await structure_system.get_player_structures(interaction.user.id)
    
    if not structures:
        await interaction.response.send_message("You have no active structures.")
        return
    
    embed = discord.Embed(
        title=f"{interaction.user.display_name}'s Structures",
        color=discord.Color.blue()
    )
    
    for structure in structures:
        structure_type = structure['type'].title()
        embed.add_field(
            name=f"{structure_type} at {structure['location']}",
            value=f"Built: {structure['built_at'][:10]}\nExpires: Next map update",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="form_army", description="Form an army with a general and brigades")
@app_commands.describe(
    general_id="ID of the general to lead the army",
    brigade_ids="Comma-separated list of brigade IDs (max 8)"
)
async def form_army_slash(interaction: discord.Interaction, general_id: str, brigade_ids: str):
    """Form an army with a general and brigades."""
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    # Validate general
    general = await db.get_general(general_id)
    if not general:
        await interaction.response.send_message("General not found.")
        return
    
    if general['player_id'] != interaction.user.id:
        await interaction.response.send_message("You don't own this general.")
        return
    
    if general.get('army_id'):
        await interaction.response.send_message("This general is already leading an army.")
        return
    
    # Parse brigade IDs
    brigade_id_list = [bid.strip() for bid in brigade_ids.split(',')]
    if len(brigade_id_list) > 8:
        await interaction.response.send_message("Armies cannot have more than 8 brigades.")
        return
    
    # Validate brigades
    valid_brigades = []
    for brigade_id in brigade_id_list:
        brigade = await db.get_brigade(brigade_id)
        if not brigade:
            await interaction.response.send_message(f"Brigade {brigade_id} not found.")
            return
        
        if brigade['player_id'] != interaction.user.id:
            await interaction.response.send_message(f"You don't own brigade {brigade_id}.")
            return
        
        if brigade.get('army_id'):
            await interaction.response.send_message(f"Brigade {brigade_id} is already in an army.")
            return
        
        valid_brigades.append(brigade)
    
    # Create army
    army_id = await db.create_army(interaction.user.id, general_id, brigade_id_list)
    
    embed = discord.Embed(
        title="Army Formed!",
        description=f"**{general['name']}'s Army** has been formed",
        color=discord.Color.purple()
    )
    
    embed.add_field(name="Army ID", value=army_id, inline=True)
    embed.add_field(name="General", value=f"{general['name']} (Level {general['level']})", inline=True)
    embed.add_field(name="Brigades", value=f"{len(valid_brigades)} brigades", inline=True)
    
    brigade_list = "\n".join([f"• {b['id']} ({b['type']})" for b in valid_brigades])
    embed.add_field(name="Brigade Composition", value=brigade_list, inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="enhancements", description="Show all available brigade enhancements")
async def enhancements_slash(interaction: discord.Interaction):
    """Show all available enhancements."""
    embed = discord.Embed(
        title="🛠️ Brigade Enhancements",
        description="Available enhancements for brigades",
        color=discord.Color.orange()
    )
    
    # Group by brigade type
    enhancement_groups = {}
    for name, enhancement in ENHANCEMENTS.items():
        if enhancement.brigade_type:
            type_name = enhancement.brigade_type.value
        else:
            type_name = "Universal"
        
        if type_name not in enhancement_groups:
            enhancement_groups[type_name] = []
        
        enhancement_groups[type_name].append((name, enhancement))
    
    for group_name, enhancements in enhancement_groups.items():
        enhancement_text = ""
        for name, enhancement in enhancements:
            cost_text = f"{enhancement.cost_silver} silver"
            if enhancement.cost_resources:
                resources = ", ".join([f"{amount} {resource}" for resource, amount in enhancement.cost_resources.items()])
                cost_text += f" + {resources}"
            
            enhancement_text += f"**{name}** ({cost_text})\n"
            if enhancement.special_ability:
                enhancement_text += f"_{enhancement.special_ability}_\n"
            enhancement_text += "\n"
        
        embed.add_field(name=group_name, value=enhancement_text, inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="retire_general", description="Retire a level 10 general to increase War College level")
@app_commands.describe(general_id="ID of the level 10 general to retire")
async def retire_general_slash(interaction: discord.Interaction, general_id: str):
    """Retire a level 10 general."""
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    general = await db.get_general(general_id)
    if not general:
        await interaction.response.send_message("General not found.")
        return
    
    if general['player_id'] != interaction.user.id:
        await interaction.response.send_message("You don't own this general.")
        return
    
    if general['level'] < 10:
        await interaction.response.send_message(f"General must be level 10 to retire. Currently level {general['level']}.")
        return
    
    # Check current war college level
    current_war_college = player.get('war_college_level', 1)
    
    if current_war_college >= 10:
        # Max level - give 300 silver instead
        await db.add_resource(interaction.user.id, 'silver', 300)
        reward_text = "300 silver (War College already at max level)"
    else:
        # Increase war college level
        new_war_college = current_war_college + 1
        await db.update_player(interaction.user.id, {'war_college_level': new_war_college})
        
        # Update general cap based on new war college level
        new_general_cap = calculate_general_cap(new_war_college)
        await db.update_player(interaction.user.id, {'general_cap': new_general_cap})
        
        reward_text = f"War College Level {new_war_college} (General Cap: {new_general_cap})"
    
    # Remove the general (retirement)
    await db.update_general(general_id, {'status': 'retired', 'retired_at': datetime.now().isoformat()})
    
    embed = discord.Embed(
        title="General Retired",
        description=f"**{general['name']}** has retired from service",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="Reward", value=reward_text, inline=False)
    embed.add_field(name="Service Record", value=f"Level {general['level']} at retirement", inline=True)
    
    trait_name, _ = GENERAL_TRAITS[general['trait_id']]
    embed.add_field(name="Final Trait", value=trait_name, inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="war_college", description="View your War College level and benefits")
async def war_college_slash(interaction: discord.Interaction):
    """Show War College information."""
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    war_college_level = player.get('war_college_level', 1)
    
    embed = discord.Embed(
        title="🎓 War College",
        description=f"Level {war_college_level}",
        color=discord.Color.dark_gold()
    )
    
    # Current benefits
    benefits = get_war_college_benefits(war_college_level)
    embed.add_field(name="Current Benefits", value=benefits, inline=False)
    
    # Next level benefits
    if war_college_level < 10:
        next_benefits = get_war_college_benefits(war_college_level + 1)
        embed.add_field(name=f"Level {war_college_level + 1} Benefits", value=next_benefits, inline=False)
        embed.add_field(name="To Advance", value="Retire a Level 10 General or Win a War", inline=False)
    else:
        embed.add_field(name="Status", value="Maximum Level Reached!", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="siege", description="Start a siege on an enemy city")
@app_commands.describe(
    city_name="Name of the city to siege",
    brigade_ids="Comma-separated list of brigade IDs to use in siege"
)
async def siege_slash(interaction: discord.Interaction, city_name: str, brigade_ids: str):
    """Start a siege on an enemy city."""
    if war_bot.current_phase != GamePhase.BATTLE:
        await interaction.response.send_message("Sieges can only be started during Battle phase!")
        return
    
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    # Parse brigade IDs
    brigade_id_list = [bid.strip() for bid in brigade_ids.split(',')]
    
    # Validate brigades
    valid_brigades = []
    for brigade_id in brigade_id_list:
        brigade = await db.get_brigade(brigade_id)
        if not brigade:
            await interaction.response.send_message(f"Brigade {brigade_id} not found.")
            return
        
        if brigade['player_id'] != interaction.user.id:
            await interaction.response.send_message(f"You don't own brigade {brigade_id}.")
            return
        
        valid_brigades.append(brigade)
    
    # For demo purposes, assume city tier 1 and defender ID 0 (would need proper city/map system)
    city_tier = 1
    defender_id = 0  # Would need to determine actual city owner
    
    siege_id = await siege_system.start_siege(city_name, city_tier, interaction.user.id, defender_id, brigade_id_list)
    
    embed = discord.Embed(
        title="Siege Begun!",
        description=f"Siege of {city_name} has started",
        color=discord.Color.dark_red()
    )
    
    embed.add_field(name="Siege ID", value=siege_id, inline=True)
    embed.add_field(name="City Tier", value=str(city_tier), inline=True)
    embed.add_field(name="Siege Timer", value=f"{city_tier} action cycles", inline=True)
    embed.add_field(name="Brigades", value=f"{len(valid_brigades)} brigades", inline=True)
    
    embed.add_field(
        name="Next Steps",
        value="Wait for siege timer to expire, then use `/assault_city` or continue waiting to starve out the city",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

def calculate_general_cap(war_college_level: int) -> int:
    """Calculate general cap based on war college level."""
    if war_college_level >= 10:
        return 4
    elif war_college_level >= 7:
        return 3
    elif war_college_level >= 4:
        return 2
    else:
        return 1

def calculate_brigade_cap(player: Dict) -> int:
    """Calculate brigade cap based on cities owned."""
    base_cap = 2
    cities = player.get('cities', [])
    
    for city in cities:
        tier = city.get('tier', 1)
        if tier == 1:
            base_cap += 1
        elif tier == 2:
            base_cap += 3
        elif tier == 3:
            base_cap += 5
    
    return base_cap

def get_war_college_benefits(level: int) -> str:
    """Get description of war college benefits for a level."""
    benefits = []
    
    if level >= 1:
        general_cap = calculate_general_cap(level)
        general_floor = min(((level - 1) // 3) + 1, 4)
        benefits.append(f"General Cap: {general_cap}")
        benefits.append(f"General Level Floor: {general_floor}")
    
    if level >= 2:
        benefits.append("Roll for general traits twice, choose result")
    
    if level >= 5:
        benefits.append("Pillaging +1, Sacking worth double")
    
    if level >= 8:
        benefits.append("+1 to Skirmish and Defense rolls")
    
    return "\n".join([f"• {benefit}" for benefit in benefits])

def calculate_army_movement(army_data: Dict, general_data: Optional[Dict] = None) -> int:
    """Calculate army movement speed including general trait bonuses."""
    # Base movement is speed of slowest brigade (would need to implement)
    base_movement = 3  # Placeholder
    
    if general_data:
        trait_name, _ = GENERAL_TRAITS[general_data['trait_id']]
        if trait_name == "Relentless":
            base_movement += 1  # +1 army movement on land
        elif trait_name == "Mariner":
            # +1 army movement while embarked (would need embarkation system)
            pass
    
    return base_movement

@bot.tree.command(name="list_armies", description="List all your armies")
async def list_armies_slash(interaction: discord.Interaction):
    """List all player's armies."""
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    armies = await db.get_armies(interaction.user.id)
    
    if not armies:
        await interaction.response.send_message("You have no armies. Use `/form_army` to create one.")
        return
    
    embed = discord.Embed(
        title=f"{interaction.user.display_name}'s Armies",
        color=discord.Color.purple()
    )
    
    for army in armies:
        general = await db.get_general(army['general_id'])
        brigade_count = len(army.get('brigade_ids', []))
        
        embed.add_field(
            name=f"#{army['id']} - {army.get('name', 'Unnamed Army')}",
            value=f"General: {general['name'] if general else 'None'} (Level {general['level'] if general else 'N/A'})\nBrigades: {brigade_count}\nLocation: {army.get('location', 'Unknown')}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="disband_army", description="Disband an army, returning brigades to individual control")
@app_commands.describe(army_id="ID of the army to disband")
async def disband_army_slash(interaction: discord.Interaction, army_id: str):
    """Disband an army."""
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    army = await db.get_army(army_id)
    if not army:
        await interaction.response.send_message("Army not found.")
        return
    
    if army['player_id'] != interaction.user.id:
        await interaction.response.send_message("You don't own this army.")
        return
    
    # Remove army references from general and brigades
    if army.get('general_id'):
        await db.update_general(army['general_id'], {'army_id': None})
    
    for brigade_id in army.get('brigade_ids', []):
        await db.update_brigade(brigade_id, {'army_id': None})
    
    # Delete army
    await db.delete_army(army_id)
    
    embed = discord.Embed(
        title="Army Disbanded",
        description=f"Army {army_id} has been disbanded",
        color=discord.Color.orange()
    )
    
    embed.add_field(name="General", value="Returned to city", inline=True)
    embed.add_field(name="Brigades", value="Returned to individual control", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="celebrate", description="Celebrate with an army after victory for rally bonus")
@app_commands.describe(army_id="ID of the army to celebrate")
async def celebrate_slash(interaction: discord.Interaction, army_id: str):
    """Celebrate with an army."""
    if war_bot.current_phase != GamePhase.MOVEMENT:
        await interaction.response.send_message("Celebrating can only be done during Movement phase!")
        return
    
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    army = await db.get_army(army_id)
    if not army:
        await interaction.response.send_message("Army not found.")
        return
    
    if army['player_id'] != interaction.user.id:
        await interaction.response.send_message("You don't own this army.")
        return
    
    # Check if army can celebrate (must have won a battle recently)
    if not army.get('can_celebrate', False):
        await interaction.response.send_message("This army cannot celebrate (must have won a battle in the previous cycle).")
        return
    
    # Apply celebration effects
    celebration_bonus = 1
    general = await db.get_general(army['general_id']) if army.get('general_id') else None
    
    if general:
        trait_name, _ = GENERAL_TRAITS[general['trait_id']]
        if trait_name == "Inspiring":
            celebration_bonus = 2
    
    # Mark brigades as celebrated (would need to track this)
    for brigade_id in army.get('brigade_ids', []):
        await db.update_brigade(brigade_id, {
            'is_fatigued': True,
            'celebration_bonus': celebration_bonus
        })
    
    # Remove ability to celebrate again
    await db.update_army(army_id, {'can_celebrate': False})
    
    embed = discord.Embed(
        title="Army Celebrates!",
        description=f"Army {army_id} celebrates their recent victory",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="Rally Bonus", value=f"+{celebration_bonus} rally in next battle", inline=True)
    embed.add_field(name="Status", value="All brigades are now fatigued", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="general_traits", description="Show all general traits and their effects")
async def general_traits_slash(interaction: discord.Interaction):
    """Show detailed information about all general traits."""
    embed = discord.Embed(
        title="🎖️ General Traits",
        description="All possible traits and their effects",
        color=discord.Color.gold()
    )
    
    # Group traits for better display
    trait_groups = {
        "Combat Traits": [1, 2, 3, 5, 11, 13, 15, 18],  # Ambitious, Bold, Brilliant, Cautious, Heroic, Lucky, Merciless, Resolute
        "Leadership Traits": [7, 8, 9, 12, 20],  # Confident, Defiant, Disciplined, Inspiring, Zealous
        "Strategic Traits": [4, 6, 10, 14, 17, 19],  # Brutal, Chivalrous, Dogged, Mariner, Relentless, Wary
        "Special Traits": [16]  # Prodigious
    }
    
    for group_name, trait_ids in trait_groups.items():
        trait_text = ""
        for trait_id in trait_ids:
            trait_name, trait_desc = GENERAL_TRAITS[trait_id]
            trait_text += f"**{trait_name}**: {trait_desc}\n"
        
        embed.add_field(name=group_name, value=trait_text, inline=False)
    
    embed.add_field(
        name="Notes",
        value="• Trait effects apply automatically in battles and actions\n• War College Level 2+ allows rolling twice for traits\n• Prodigious trait levels are lost if trait is rerolled",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="reroll_trait", description="Reroll a general's trait (costs 3 gems)")
@app_commands.describe(general_id="ID of the general whose trait to reroll")
async def reroll_trait_slash(interaction: discord.Interaction, general_id: str):
    """Reroll a general's trait for 3 gems."""
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    general = await db.get_general(general_id)
    if not general:
        await interaction.response.send_message("General not found.")
        return
    
    if general['player_id'] != interaction.user.id:
        await interaction.response.send_message("You don't own this general.")
        return
    
    # Check gem cost
    if player.get('resources', {}).get('gems', 0) < 3:
        await interaction.response.send_message("Insufficient gems! Need 3 gems to reroll trait.")
        return
    
    # Get old trait info
    old_trait_name, _ = GENERAL_TRAITS[general['trait_id']]
    old_level = general['level']
    
    # Check if losing Prodigious levels
    level_adjustment = 0
    if old_trait_name == "Prodigious":
        level_adjustment = -2
    
    # Deduct gems
    await db.deduct_resources(interaction.user.id, {"gems": 3})
    
    # Roll new trait (with War College benefits)
    war_college_level = player.get('war_college_level', 1)
    
    if war_college_level >= 2:
        trait_id_1 = war_bot.roll_general_trait()
        trait_id_2 = war_bot.roll_general_trait()
        trait_id = random.choice([trait_id_1, trait_id_2])  # Simplified choice
    else:
        trait_id = war_bot.roll_general_trait()
    
    new_trait_name, new_trait_desc = GENERAL_TRAITS[trait_id]
    
    # Apply level adjustments
    new_level = max(1, old_level + level_adjustment)
    if new_trait_name == "Prodigious":
        # Don't add levels here, they're added by the trait effect
        pass
    
    # Update general
    await db.update_general(general_id, {
        'trait_id': trait_id,
        'level': new_level
    })
    
    embed = discord.Embed(
        title="General Trait Rerolled",
        description=f"**{general['name']}** has a new trait!",
        color=discord.Color.purple()
    )
    
    embed.add_field(name="Old Trait", value=old_trait_name, inline=True)
    embed.add_field(name="New Trait", value=new_trait_name, inline=True)
    embed.add_field(name="Cost", value="3 gems", inline=True)
    embed.add_field(name="New Effect", value=new_trait_desc, inline=False)
    
    if level_adjustment != 0:
        embed.add_field(name="Level Change", value=f"{old_level} → {new_level}", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="add_resources", description="Add resources to a player (Admin)")
@app_commands.describe(
    player="Player to give resources to",
    gold="Amount of gold to add",
    gems="Amount of gems to add",
    population="Amount of population to add"
)
async def add_resources_slash(interaction: discord.Interaction, player: discord.Member, gold: int = 0, gems: int = 0, population: int = 0):
    """Add resources to a player."""
    # In a real implementation, you'd check for admin permissions here
    # if not interaction.user.guild_permissions.administrator:
    #     await interaction.response.send_message("You need admin permissions to use this command.")
    #     return
    
    target_player = await db.get_player(player.id)
    if not target_player:
        await interaction.response.send_message(f"{player.display_name} is not registered.")
        return
    
    # Add resources
    resources_to_add = {}
    if gold > 0:
        resources_to_add['gold'] = gold
    if gems > 0:
        resources_to_add['gems'] = gems
    if population > 0:
        resources_to_add['population'] = population
    
    if resources_to_add:
        await db.add_resources(player.id, resources_to_add)
    
    # Get updated player data
    updated_player = await db.get_player(player.id)
    if updated_player:
        current_resources = updated_player.get('resources', {})
    else:
        current_resources = {}
    
    embed = discord.Embed(
        title="Resources Added",
        description=f"Resources added to {player.display_name}",
        color=discord.Color.green()
    )
    
    if gold > 0:
        embed.add_field(name="Gold Added", value=f"+{gold}", inline=True)
    if gems > 0:
        embed.add_field(name="Gems Added", value=f"+{gems}", inline=True)
    if population > 0:
        embed.add_field(name="Population Added", value=f"+{population}", inline=True)
    
    embed.add_field(
        name="Current Resources",
        value=f"Gold: {current_resources.get('gold', 0)}\nGems: {current_resources.get('gems', 0)}\nPopulation: {current_resources.get('population', 0)}",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="set_resources", description="Set a player's resources to specific amounts (Admin)")
@app_commands.describe(
    player="Player to set resources for",
    gold="Gold amount to set",
    gems="Gems amount to set",
    population="Population amount to set"
)
async def set_resources_slash(interaction: discord.Interaction, player: discord.Member, gold: Optional[int] = None, gems: Optional[int] = None, population: Optional[int] = None):
    """Set a player's resources to specific amounts."""
    target_player = await db.get_player(player.id)
    if not target_player:
        await interaction.response.send_message(f"{player.display_name} is not registered.")
        return
    
    current_resources = target_player.get('resources', {})
    new_resources = current_resources.copy()
    
    changes = []
    if gold is not None:
        old_gold = current_resources.get('gold', 0)
        new_resources['gold'] = gold
        changes.append(f"Gold: {old_gold} → {gold}")
    
    if gems is not None:
        old_gems = current_resources.get('gems', 0)
        new_resources['gems'] = gems
        changes.append(f"Gems: {old_gems} → {gems}")
    
    if population is not None:
        old_pop = current_resources.get('population', 0)
        new_resources['population'] = population
        changes.append(f"Population: {old_pop} → {population}")
    
    if changes:
        await db.update_player(player.id, {'resources': new_resources})
    
    embed = discord.Embed(
        title="Resources Set",
        description=f"Resources updated for {player.display_name}",
        color=discord.Color.blue()
    )
    
    if changes:
        embed.add_field(name="Changes", value="\n".join(changes), inline=False)
    else:
        embed.add_field(name="Status", value="No changes made", inline=False)
    
    embed.add_field(
        name="Current Resources",
        value=f"Gold: {new_resources.get('gold', 0)}\nGems: {new_resources.get('gems', 0)}\nPopulation: {new_resources.get('population', 0)}",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="add_city", description="Add a city to a player (Admin)")
@app_commands.describe(
    player="Player to give the city to",
    city_name="Name of the city",
    tier="City tier (1-3)",
    location="City location/coordinates"
)
async def add_city_slash(interaction: discord.Interaction, player: discord.Member, city_name: str, tier: int = 1, location: str = "Unknown"):
    """Add a city to a player."""
    if tier < 1 or tier > 3:
        await interaction.response.send_message("City tier must be between 1 and 3.")
        return
    
    target_player = await db.get_player(player.id)
    if not target_player:
        await interaction.response.send_message(f"{player.display_name} is not registered.")
        return
    
    # Create city data
    city_data = {
        'name': city_name,
        'tier': tier,
        'location': location,
        'owner_id': player.id,
        'garrison': [],
        'under_siege': False,
        'structures': []
    }
    
    # Add city to player's cities list
    current_cities = target_player.get('cities', [])
    current_cities.append(city_data)
    
    # Update brigade cap based on new city
    new_brigade_cap = calculate_brigade_cap({'cities': current_cities})
    
    await db.update_player(player.id, {
        'cities': current_cities,
        'brigade_cap': new_brigade_cap
    })
    
    embed = discord.Embed(
        title="City Added",
        description=f"New city granted to {player.display_name}",
        color=discord.Color.green()
    )
    
    embed.add_field(name="City Name", value=city_name, inline=True)
    embed.add_field(name="Tier", value=f"Tier {tier}", inline=True)
    embed.add_field(name="Location", value=location, inline=True)
    
    # Calculate tier benefits
    tier_benefits = {
        1: "+1 brigade cap",
        2: "+3 brigade cap",
        3: "+5 brigade cap"
    }
    
    embed.add_field(name="Benefits", value=tier_benefits[tier], inline=True)
    embed.add_field(name="New Brigade Cap", value=str(new_brigade_cap), inline=True)
    embed.add_field(name="Total Cities", value=str(len(current_cities)), inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="remove_city", description="Remove a city from a player (Admin)")
@app_commands.describe(
    player="Player to remove city from",
    city_name="Name of the city to remove"
)
async def remove_city_slash(interaction: discord.Interaction, player: discord.Member, city_name: str):
    """Remove a city from a player."""
    target_player = await db.get_player(player.id)
    if not target_player:
        await interaction.response.send_message(f"{player.display_name} is not registered.")
        return
    
    current_cities = target_player.get('cities', [])
    city_to_remove = None
    
    # Find the city
    for i, city in enumerate(current_cities):
        if city['name'].lower() == city_name.lower():
            city_to_remove = current_cities.pop(i)
            break
    
    if not city_to_remove:
        await interaction.response.send_message(f"City '{city_name}' not found for {player.display_name}.")
        return
    
    # Update brigade cap
    new_brigade_cap = calculate_brigade_cap({'cities': current_cities})
    
    await db.update_player(player.id, {
        'cities': current_cities,
        'brigade_cap': new_brigade_cap
    })
    
    embed = discord.Embed(
        title="City Removed",
        description=f"City removed from {player.display_name}",
        color=discord.Color.red()
    )
    
    embed.add_field(name="City Name", value=city_to_remove['name'], inline=True)
    embed.add_field(name="Tier", value=f"Tier {city_to_remove['tier']}", inline=True)
    embed.add_field(name="Location", value=city_to_remove['location'], inline=True)
    
    embed.add_field(name="New Brigade Cap", value=str(new_brigade_cap), inline=True)
    embed.add_field(name="Remaining Cities", value=str(len(current_cities)), inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="list_cities", description="List all cities owned by a player")
@app_commands.describe(player="Player to list cities for (optional, defaults to yourself)")
async def list_cities_slash(interaction: discord.Interaction, player: Optional[discord.Member] = None):
    """List all cities owned by a player."""
    target_player_id = player.id if player else interaction.user.id
    target_player_data = await db.get_player(target_player_id)
    
    if not target_player_data:
        target_name = player.display_name if player else "You"
        await interaction.response.send_message(f"{target_name} must register first! Use `/register`")
        return
    
    cities = target_player_data.get('cities', [])
    target_name = player.display_name if player else interaction.user.display_name
    
    if not cities:
        await interaction.response.send_message(f"{target_name} owns no cities.")
        return
    
    embed = discord.Embed(
        title=f"{target_name}'s Cities",
        description=f"Total cities: {len(cities)}",
        color=discord.Color.blue()
    )
    
    tier_counts = {1: 0, 2: 0, 3: 0}
    total_brigade_bonus = 0
    
    for city in cities:
        tier = city.get('tier', 1)
        tier_counts[tier] += 1
        
        if tier == 1:
            total_brigade_bonus += 1
        elif tier == 2:
            total_brigade_bonus += 3
        elif tier == 3:
            total_brigade_bonus += 5
        
        siege_status = " 🏴 (Under Siege)" if city.get('under_siege', False) else ""
        garrison_count = len(city.get('garrison', []))
        
        embed.add_field(
            name=f"{city['name']} (Tier {tier}){siege_status}",
            value=f"Location: {city.get('location', 'Unknown')}\nGarrison: {garrison_count} brigades",
            inline=True
        )
    
    embed.add_field(
        name="Summary",
        value=f"Tier 1: {tier_counts[1]} cities\nTier 2: {tier_counts[2]} cities\nTier 3: {tier_counts[3]} cities",
        inline=True
    )
    
    embed.add_field(
        name="Brigade Cap Bonus",
        value=f"+{total_brigade_bonus} from cities\nTotal Cap: {calculate_brigade_cap(target_player_data)}",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="upgrade_city", description="Upgrade a city's tier (Admin)")
@app_commands.describe(
    player="Player who owns the city",
    city_name="Name of the city to upgrade",
    new_tier="New tier for the city (1-3)"
)
async def upgrade_city_slash(interaction: discord.Interaction, player: discord.Member, city_name: str, new_tier: int):
    """Upgrade or downgrade a city's tier."""
    if new_tier < 1 or new_tier > 3:
        await interaction.response.send_message("City tier must be between 1 and 3.")
        return
    
    target_player = await db.get_player(player.id)
    if not target_player:
        await interaction.response.send_message(f"{player.display_name} is not registered.")
        return
    
    current_cities = target_player.get('cities', [])
    city_found = False
    old_tier = 0
    
    # Find and update the city
    for city in current_cities:
        if city['name'].lower() == city_name.lower():
            old_tier = city['tier']
            city['tier'] = new_tier
            city_found = True
            break
    
    if not city_found:
        await interaction.response.send_message(f"City '{city_name}' not found for {player.display_name}.")
        return
    
    # Update brigade cap
    new_brigade_cap = calculate_brigade_cap({'cities': current_cities})
    
    await db.update_player(player.id, {
        'cities': current_cities,
        'brigade_cap': new_brigade_cap
    })
    
    embed = discord.Embed(
        title="City Upgraded",
        description=f"City tier changed for {player.display_name}",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="City Name", value=city_name, inline=True)
    embed.add_field(name="Tier Change", value=f"{old_tier} → {new_tier}", inline=True)
    embed.add_field(name="New Brigade Cap", value=str(new_brigade_cap), inline=True)
    
    # Show tier benefits
    tier_benefits = {
        1: "+1 brigade cap",
        2: "+3 brigade cap",
        3: "+5 brigade cap"
    }
    
    embed.add_field(name="New Benefits", value=tier_benefits[new_tier], inline=True)
    
    if new_tier > old_tier:
        embed.color = discord.Color.green()
        embed.add_field(name="Status", value="Upgraded! 📈", inline=True)
    elif new_tier < old_tier:
        embed.color = discord.Color.orange()
        embed.add_field(name="Status", value="Downgraded 📉", inline=True)
    else:
        embed.add_field(name="Status", value="No change", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="transfer_resources", description="Transfer resources to another player")
@app_commands.describe(
    recipient="Player to transfer resources to",
    gold="Amount of gold to transfer",
    gems="Amount of gems to transfer",
    population="Amount of population to transfer"
)
async def transfer_resources_slash(interaction: discord.Interaction, recipient: discord.Member, gold: int = 0, gems: int = 0, population: int = 0):
    """Transfer resources to another player."""
    if recipient.id == interaction.user.id:
        await interaction.response.send_message("You cannot transfer resources to yourself.")
        return
    
    if gold <= 0 and gems <= 0 and population <= 0:
        await interaction.response.send_message("You must transfer at least some resources.")
        return
    
    sender = await db.get_player(interaction.user.id)
    if not sender:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    recipient_data = await db.get_player(recipient.id)
    if not recipient_data:
        await interaction.response.send_message(f"{recipient.display_name} is not registered.")
        return
    
    sender_resources = sender.get('resources', {})
    
    # Check if sender has enough resources
    if gold > sender_resources.get('gold', 0):
        await interaction.response.send_message(f"Insufficient gold! You have {sender_resources.get('gold', 0)}, need {gold}.")
        return
    if gems > sender_resources.get('gems', 0):
        await interaction.response.send_message(f"Insufficient gems! You have {sender_resources.get('gems', 0)}, need {gems}.")
        return
    if population > sender_resources.get('population', 0):
        await interaction.response.send_message(f"Insufficient population! You have {sender_resources.get('population', 0)}, need {population}.")
        return
    
    # Perform transfer
    resources_to_deduct = {}
    resources_to_add = {}
    
    if gold > 0:
        resources_to_deduct['gold'] = gold
        resources_to_add['gold'] = gold
    if gems > 0:
        resources_to_deduct['gems'] = gems
        resources_to_add['gems'] = gems
    if population > 0:
        resources_to_deduct['population'] = population
        resources_to_add['population'] = population
    
    await db.deduct_resources(interaction.user.id, resources_to_deduct)
    await db.add_resources(recipient.id, resources_to_add)
    
    embed = discord.Embed(
        title="Resources Transferred",
        description=f"{interaction.user.display_name} → {recipient.display_name}",
        color=discord.Color.green()
    )
    
    transfer_text = []
    if gold > 0:
        transfer_text.append(f"Gold: {gold}")
    if gems > 0:
        transfer_text.append(f"Gems: {gems}")
    if population > 0:
        transfer_text.append(f"Population: {population}")
    
    embed.add_field(name="Transferred", value="\n".join(transfer_text), inline=False)
    
    # Show remaining resources for sender
    updated_sender = await db.get_player(interaction.user.id)
    if updated_sender:
        sender_resources = updated_sender.get('resources', {})
        embed.add_field(
            name="Your Remaining Resources",
            value=f"Gold: {sender_resources.get('gold', 0)}\nGems: {sender_resources.get('gems', 0)}\nPopulation: {sender_resources.get('population', 0)}",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="view_resources", description="View detailed resource information")
@app_commands.describe(player="Player to view resources for (optional, defaults to yourself)")
async def view_resources_slash(interaction: discord.Interaction, player: Optional[discord.Member] = None):
    """View detailed resource information for a player."""
    target_player_id = player.id if player else interaction.user.id
    target_player_data = await db.get_player(target_player_id)
    
    if not target_player_data:
        target_name = player.display_name if player else "You"
        await interaction.response.send_message(f"{target_name} must register first! Use `/register`")
        return
    
    target_name = player.display_name if player else interaction.user.display_name
    resources = target_player_data.get('resources', {})
    
    embed = discord.Embed(
        title=f"{target_name}'s Resources",
        color=discord.Color.gold()
    )
    
    # Current resources
    gold = resources.get('gold', 0)
    gems = resources.get('gems', 0)
    population = resources.get('population', 0)
    
    embed.add_field(name="💰 Gold", value=str(gold), inline=True)
    embed.add_field(name="💎 Gems", value=str(gems), inline=True)
    embed.add_field(name="👥 Population", value=str(population), inline=True)
    
    # Calculate income/expenses
    cities = target_player_data.get('cities', [])
    brigades = await db.get_brigades(target_player_id)
    generals = await db.get_generals(target_player_id)
    
    # Income calculation
    city_income = len(cities) * 5  # Base city income
    total_income = city_income
    
    # Expense calculation
    brigade_upkeep = len(brigades) * 2  # Base brigade upkeep
    general_upkeep = len(generals) * 1  # Base general upkeep
    total_expenses = brigade_upkeep + general_upkeep
    
    net_income = total_income - total_expenses
    
    embed.add_field(
        name="💹 Income (per turn)",
        value=f"Cities: +{city_income} gold\nTotal: +{total_income} gold",
        inline=True
    )
    
    embed.add_field(
        name="💸 Expenses (per turn)",
        value=f"Brigades: -{brigade_upkeep} gold\nGenerals: -{general_upkeep} gold\nTotal: -{total_expenses} gold",
        inline=True
    )
    
    embed.add_field(
        name="📊 Net Income",
        value=f"{'+'if net_income >= 0 else ''}{net_income} gold per turn",
        inline=True
    )
    
    # Resource capacity/limits
    brigade_cap = calculate_brigade_cap(target_player_data)
    general_cap = calculate_general_cap(target_player_data.get('war_college_level', 1))
    
    embed.add_field(
        name="📋 Capacity",
        value=f"Brigades: {len(brigades)}/{brigade_cap}\nGenerals: {len(generals)}/{general_cap}",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="update_brigade_cap", description="Recalculate brigade cap based on cities (Admin)")
async def update_brigade_cap_slash(interaction: discord.Interaction):
    """Update brigade cap calculation for all players."""
    # This would be an admin command in a real implementation
    players = await db.get_all_players()
    updated_count = 0
    
    for player_id, player_data in players.items():
        new_brigade_cap = calculate_brigade_cap(player_data)
        old_brigade_cap = player_data.get('brigade_cap', 2)
        
        if new_brigade_cap != old_brigade_cap:
            await db.update_player(int(player_id), {'brigade_cap': new_brigade_cap})
            updated_count += 1
    
    embed = discord.Embed(
        title="Brigade Caps Updated",
        description=f"Updated {updated_count} players' brigade caps",
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="siege_city", description="Lay siege to an enemy city")
@app_commands.describe(
    army_id="ID of the army to conduct the siege",
    city_name="Name of the city to siege",
    target_player="Player who owns the city"
)
async def siege_city_slash(interaction: discord.Interaction, army_id: str, city_name: str, target_player: discord.Member):
    """Lay siege to an enemy city."""
    if war_bot.current_phase != GamePhase.MOVEMENT:
        await interaction.response.send_message("Sieges can only be initiated during Movement phase!")
        return
    
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    army = await db.get_army(army_id)
    if not army:
        await interaction.response.send_message("Army not found.")
        return
    
    if army['player_id'] != interaction.user.id:
        await interaction.response.send_message("You don't own this army.")
        return
    
    target_data = await db.get_player(target_player.id)
    if not target_data:
        await interaction.response.send_message(f"{target_player.display_name} is not registered.")
        return
    
    # Find the target city
    target_cities = target_data.get('cities', [])
    target_city = None
    
    for city in target_cities:
        if city['name'].lower() == city_name.lower():
            target_city = city
            break
    
    if not target_city:
        await interaction.response.send_message(f"City '{city_name}' not found for {target_player.display_name}.")
        return
    
    if target_city.get('under_siege', False):
        await interaction.response.send_message(f"City '{city_name}' is already under siege!")
        return
    
    # Start siege using siege system
    army_brigade_ids = army.get('brigade_ids', [])
    general_id = army.get('general_id')
    
    siege_id = await siege_system.start_siege(
        target_city['name'], 
        target_city['tier'], 
        interaction.user.id, 
        target_player.id, 
        army_brigade_ids, 
        general_id
    )
    
    if siege_id:
        # Mark city as under siege
        target_city['under_siege'] = True
        target_city['besieging_army'] = army_id
        await db.update_player(target_player.id, {'cities': target_cities})
        
        embed = discord.Embed(
            title="Siege Begun!",
            description=f"Army {army_id} has laid siege to {city_name}",
            color=discord.Color.red()
        )
        
        embed.add_field(name="Target City", value=f"{city_name} (Tier {target_city['tier']})", inline=True)
        embed.add_field(name="Defender", value=target_player.display_name, inline=True)
        embed.add_field(name="Siege Duration", value="7 days", inline=True)
        
        garrison_count = len(target_city.get('garrison', []))
        embed.add_field(name="Garrison", value=f"{garrison_count} brigades", inline=True)
        
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("Failed to start siege.")

@bot.tree.command(name="garrison_city", description="Move brigades to garrison a city")
@app_commands.describe(
    city_name="Name of your city to garrison",
    brigade_ids="Comma-separated list of brigade IDs to garrison"
)
async def garrison_city_slash(interaction: discord.Interaction, city_name: str, brigade_ids: str):
    """Move brigades to garrison a city."""
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    # Find the city
    cities = player.get('cities', [])
    target_city = None
    city_index = -1
    
    for i, city in enumerate(cities):
        if city['name'].lower() == city_name.lower():
            target_city = city
            city_index = i
            break
    
    if not target_city:
        await interaction.response.send_message(f"You don't own a city named '{city_name}'.")
        return
    
    # Parse brigade IDs
    try:
        brigade_id_list = [bid.strip() for bid in brigade_ids.split(',')]
    except:
        await interaction.response.send_message("Invalid brigade ID format. Use comma-separated IDs.")
        return
    
    # Validate brigades
    valid_brigades = []
    for brigade_id in brigade_id_list:
        brigade = await db.get_brigade(brigade_id)
        if not brigade:
            await interaction.response.send_message(f"Brigade {brigade_id} not found.")
            return
        if brigade['player_id'] != interaction.user.id:
            await interaction.response.send_message(f"You don't own brigade {brigade_id}.")
            return
        if brigade.get('army_id'):
            await interaction.response.send_message(f"Brigade {brigade_id} is already in an army.")
            return
        valid_brigades.append(brigade)
    
    # Add brigades to garrison
    current_garrison = target_city.get('garrison', [])
    
    for brigade in valid_brigades:
        current_garrison.append(brigade['id'])
        # Update brigade to show it's garrisoning
        await db.update_brigade(brigade['id'], {'garrison_city': city_name})
    
    # Update city
    cities[city_index]['garrison'] = current_garrison
    await db.update_player(interaction.user.id, {'cities': cities})
    
    embed = discord.Embed(
        title="City Garrisoned",
        description=f"Brigades added to {city_name} garrison",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="City", value=f"{city_name} (Tier {target_city['tier']})", inline=True)
    embed.add_field(name="Brigades Added", value=str(len(valid_brigades)), inline=True)
    embed.add_field(name="Total Garrison", value=str(len(current_garrison)), inline=True)
    
    brigade_names = []
    for brigade in valid_brigades:
        brigade_names.append(f"{brigade['type']} #{brigade['id']}")
    
    embed.add_field(name="Added Brigades", value="\n".join(brigade_names), inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ungarrison_city", description="Remove brigades from city garrison")
@app_commands.describe(
    city_name="Name of your city to ungarrison",
    brigade_ids="Comma-separated list of brigade IDs to remove (or 'all' for all brigades)"
)
async def ungarrison_city_slash(interaction: discord.Interaction, city_name: str, brigade_ids: str):
    """Remove brigades from city garrison."""
    player = await db.get_player(interaction.user.id)
    if not player:
        await interaction.response.send_message("You must register first! Use `/register`")
        return
    
    # Find the city
    cities = player.get('cities', [])
    target_city = None
    city_index = -1
    
    for i, city in enumerate(cities):
        if city['name'].lower() == city_name.lower():
            target_city = city
            city_index = i
            break
    
    if not target_city:
        await interaction.response.send_message(f"You don't own a city named '{city_name}'.")
        return
    
    current_garrison = target_city.get('garrison', [])
    if not current_garrison:
        await interaction.response.send_message(f"{city_name} has no garrison.")
        return
    
    # Parse brigade IDs
    if brigade_ids.lower() == 'all':
        brigade_id_list = current_garrison.copy()
    else:
        try:
            brigade_id_list = [bid.strip() for bid in brigade_ids.split(',')]
        except:
            await interaction.response.send_message("Invalid brigade ID format. Use comma-separated IDs or 'all'.")
            return
    
    # Remove brigades from garrison
    removed_brigades = []
    for brigade_id in brigade_id_list:
        if brigade_id in current_garrison:
            current_garrison.remove(brigade_id)
            # Update brigade to remove garrison status
            await db.update_brigade(brigade_id, {'garrison_city': None})
            
            brigade = await db.get_brigade(brigade_id)
            if brigade:
                removed_brigades.append(brigade)
    
    if not removed_brigades:
        await interaction.response.send_message("No valid brigades found in garrison.")
        return
    
    # Update city
    cities[city_index]['garrison'] = current_garrison
    await db.update_player(interaction.user.id, {'cities': cities})
    
    embed = discord.Embed(
        title="Brigades Ungarrisoned",
        description=f"Brigades removed from {city_name} garrison",
        color=discord.Color.orange()
    )
    
    embed.add_field(name="City", value=f"{city_name} (Tier {target_city['tier']})", inline=True)
    embed.add_field(name="Brigades Removed", value=str(len(removed_brigades)), inline=True)
    embed.add_field(name="Remaining Garrison", value=str(len(current_garrison)), inline=True)
    
    brigade_names = []
    for brigade in removed_brigades:
        brigade_names.append(f"{brigade['type']} #{brigade['id']}")
    
    embed.add_field(name="Removed Brigades", value="\n".join(brigade_names), inline=False)
    
    await interaction.response.send_message(embed=embed)

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
