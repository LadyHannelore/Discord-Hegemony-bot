import discord
from discord.ext import commands, tasks
import os
import json
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import asyncio
from dotenv import load_dotenv

from models import (
    BrigadeType, GamePhase, BRIGADE_STATS, 
    ENHANCEMENTS, GENERAL_TRAITS, Enhancement, BrigadeStats
)
from json_data_manager import JsonDataManager
from war_justifications import WAR_JUSTIFICATIONS, get_available_justifications, validate_justification
from battle_system import BattleSystem, BattleSide, create_battle_brigade, create_battle_general

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

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

@bot.command(name='register')
async def register_player(ctx):
    """Register as a new player."""
    user_id = ctx.author.id
    username = ctx.author.display_name
    
    existing_player = await db.get_player(user_id)
    if existing_player:
        await ctx.send(f"You're already registered, {username}!")
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
        await ctx.send(embed=embed)
    else:
        await ctx.send("Registration failed. Please try again.")

@bot.command(name='profile')
async def show_profile(ctx, member: Optional[discord.Member] = None):
    """Show player profile and statistics."""
    target = member or ctx.author
    player = await db.get_player(target.id)
    
    if not player:
        await ctx.send(f"{target.display_name} is not registered. Use `!register` to join.")
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
    
    await ctx.send(embed=embed)

@bot.command(name='create_brigade')
async def create_brigade(ctx, brigade_type: str, city: str = "Capital"):
    """Create a new brigade."""
    if war_bot.current_phase != GamePhase.ORGANIZATION:
        await ctx.send("Brigades can only be created during Organization phase (Tuesday/Friday)!")
        return
    
    player = await db.get_player(ctx.author.id)
    if not player:
        await ctx.send("You must register first! Use `!register`")
        return
    
    # Validate brigade type
    valid_types = [bt.value for bt in BrigadeType]
    if brigade_type not in valid_types:
        await ctx.send(f"Invalid brigade type. Valid types: {', '.join(valid_types)}")
        return
    
    # Check brigade cap
    current_brigades = await db.get_brigades(ctx.author.id)
    if len(current_brigades) >= player['brigade_cap']:
        await ctx.send(f"You've reached your brigade cap of {player['brigade_cap']}!")
        return
    
    # Check resources (2 food + 1 metal OR 40 silver)
    resources = player.get('resources', {})
    has_resources = resources.get('food', 0) >= 2 and resources.get('metal', 0) >= 1
    has_silver = player.get('silver', 0) >= 40
    
    if not (has_resources or has_silver):
        await ctx.send("Insufficient resources! Need 2 food + 1 metal OR 40 silver.")
        return
    
    # Create the brigade
    brigade_id = await db.create_brigade(ctx.author.id, brigade_type, city)
    
    # Deduct resources (prefer resources over silver)
    if has_resources:
        await db.deduct_resources(ctx.author.id, {"food": 2, "metal": 1})
        cost_text = "2 food + 1 metal"
    else:
        await db.deduct_silver(ctx.author.id, 40)
        cost_text = "40 silver"
    
    embed = discord.Embed(
        title="Brigade Created!",
        description=f"Created {brigade_type} brigade at {city}",
        color=discord.Color.green()
    )
    
    # Show brigade stats
    brigade_enum = next(bt for bt in BrigadeType if bt.value == brigade_type)
    stats = BRIGADE_STATS[brigade_enum]
    
    embed.add_field(name="Stats", value=(
        f"⚔️ Skirmish: {stats.skirmish}\n"
        f"🛡️ Defense: {stats.defense}\n"
        f"📯 Pitch: {stats.pitch}\n"
        f"🚩 Rally: {stats.rally}\n"
        f"🏃 Movement: {stats.movement}"
    ), inline=True)
    
    embed.add_field(name="Brigade ID", value=str(brigade_id), inline=True)
    embed.add_field(name="Cost", value=cost_text, inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='list_brigades')
async def list_brigades(ctx):
    """List all your brigades."""
    player = await db.get_player(ctx.author.id)
    if not player:
        await ctx.send("You must register first! Use `!register`")
        return
    
    brigades = await db.get_brigades(ctx.author.id)
    
    if not brigades:
        await ctx.send("You have no brigades. Create one with `!create_brigade <type>`")
        return
    
    embed = discord.Embed(
        title=f"{ctx.author.display_name}'s Brigades",
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
    
    await ctx.send(embed=embed)

@bot.command(name='enhance_brigade')
async def enhance_brigade(ctx, brigade_id: int, enhancement: str):
    """Add enhancement to a brigade."""
    if war_bot.current_phase != GamePhase.ORGANIZATION:
        await ctx.send("Brigades can only be enhanced during Organization phase (Tuesday/Friday)!")
        return
    
    player = await db.get_player(ctx.author.id)
    if not player:
        await ctx.send("You must register first! Use `!register`")
        return
    
    # Validate enhancement exists
    if enhancement not in ENHANCEMENTS:
        available = ", ".join(ENHANCEMENTS.keys())
        await ctx.send(f"Invalid enhancement. Available: {available}")
        return
    
    # TODO: Get brigade from database and validate ownership
    # TODO: Check if enhancement is compatible with brigade type
    # TODO: Check if player has required resources
    # TODO: Apply enhancement
    
    await ctx.send(f"Enhancement '{enhancement}' applied to brigade #{brigade_id}!")

@bot.command(name='recruit_general')
async def recruit_general(ctx, name: Optional[str] = None):
    """Recruit a new general."""
    if war_bot.current_phase != GamePhase.ORGANIZATION:
        await ctx.send("Generals can only be recruited during Organization phase (Tuesday/Friday)!")
        return
    
    player = await db.get_player(ctx.author.id)
    if not player:
        await ctx.send("You must register first! Use `!register`")
        return
    
    # Check general cap
    current_generals = await db.get_generals(ctx.author.id)
    if len(current_generals) >= player['general_cap']:
        await ctx.send(f"You've reached your general cap of {player['general_cap']}!")
        return
    
    # Calculate cost (100 silver per existing general)
    cost = len(current_generals) * 100
    if player.get('silver', 0) < cost:
        await ctx.send(f"Insufficient silver! Need {cost} silver.")
        return
    
    # Generate random name if not provided
    if not name:
        name_options = ["Alexander", "Caesar", "Napoleon", "Hannibal", "Wellington", 
                       "Scipio", "Patton", "Rommel", "Montgomery", "Zhukov"]
        name = random.choice(name_options)
    
    # Roll trait
    trait_id = war_bot.roll_general_trait()
    
    # Create general
    general_id = await db.create_general(ctx.author.id, name, trait_id)
    
    # Deduct silver from player
    await db.deduct_silver(ctx.author.id, cost)
    
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
    
    await ctx.send(embed=embed)

@bot.command(name='list_generals')
async def list_generals(ctx):
    """List all your generals."""
    player = await db.get_player(ctx.author.id)
    if not player:
        await ctx.send("You must register first! Use `!register`")
        return
    
    generals = await db.get_generals(ctx.author.id)
    
    if not generals:
        await ctx.send("You have no generals. Recruit one with `!recruit_general [name]`")
        return
    
    embed = discord.Embed(
        title=f"{ctx.author.display_name}'s Generals",
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
    
    await ctx.send(embed=embed)

@bot.command(name='game_status')
async def game_status(ctx):
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
    
    await ctx.send(embed=embed)

@bot.command(name='help_warfare')
async def help_warfare(ctx):
    """Show detailed warfare help."""
    embed = discord.Embed(
        title="Hegemony Warfare Guide",
        description="Comprehensive guide to the warfare system",
        color=discord.Color.dark_blue()
    )
    
    embed.add_field(name="🏗️ Organization Phase (Tue/Fri)", value=(
        "`!create_brigade <type>` - Create new brigade\n"
        "`!enhance_brigade <id> <enhancement>` - Enhance brigade\n"
        "`!recruit_general [name]` - Recruit new general"
    ), inline=False)
    
    embed.add_field(name="🚶 Movement Phase (Wed/Sat)", value=(
        "`!move_brigade <id> <direction>` - Move brigade\n"
        "`!move_army <id> <direction>` - Move army\n"
        "`!pillage <brigade_id>` - Pillage resources"
    ), inline=False)
    
    embed.add_field(name="⚔️ Battle Phase (Thu/Sun)", value=(
        "`!siege <city>` - Begin siege\n"
        "`!assault <city>` - Assault besieged city\n"
        "Battles are automated when units clash"
    ), inline=False)
    
    embed.add_field(name="📊 Information", value=(
        "`!profile [player]` - View player profile\n"
        "`!list_brigades` - List your brigades\n"
        "`!list_generals` - List your generals\n"
        "`!game_status` - Current phase and timing"
    ), inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='brigade_types')
async def show_brigade_types(ctx):
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
    
    await ctx.send(embed=embed)

@bot.command(name='list_justifications')
async def list_justifications(ctx, target: Optional[discord.Member] = None):
    """Show available war justifications."""
    player = await db.get_player(ctx.author.id)
    if not player:
        await ctx.send("You must register first! Use `!register`")
        return
    
    embed = discord.Embed(
        title="War Justifications",
        description="Available reasons for declaring war",
        color=discord.Color.red()
    )
    
    if target:
        target_player = await db.get_player(target.id)
        if target_player:
            # Show specific justifications available against target
            available = get_available_justifications(
                dict(player), dict(target_player)
            )
            for just in available:
                embed.add_field(
                    name=just.name,
                    value=f"Victory: {just.victory_conditions[0]}\nReward: {just.victory_peace_terms[0]}",
                    inline=True
                )
        else:
            await ctx.send(f"{target.display_name} is not registered.")
            return
    else:
        # Show all justifications with requirements
        for name, just in WAR_JUSTIFICATIONS.items():
            embed.add_field(
                name=name,
                value=f"Requirements: {just.requirements[0]}\nVictory: {just.victory_conditions[0]}",
                inline=True
            )
    
    await ctx.send(embed=embed)

@bot.command(name='justification_details')
async def justification_details(ctx, *, justification_name: str):
    """Show detailed information about a specific war justification."""
    if justification_name not in WAR_JUSTIFICATIONS:
        available = ", ".join(WAR_JUSTIFICATIONS.keys())
        await ctx.send(f"Invalid justification. Available: {available}")
        return
    
    just = WAR_JUSTIFICATIONS[justification_name]
    
    embed = discord.Embed(
        title=f"War Justification: {just.name}",
        color=discord.Color.red()
    )
    
    embed.add_field(
        name="📋 Requirements",
        value="\n".join([f"• {req}" for req in just.requirements]),
        inline=False
    )
    
    embed.add_field(
        name="🏆 Victory Conditions", 
        value="\n".join([f"• {cond}" for cond in just.victory_conditions]),
        inline=False
    )
    
    embed.add_field(
        name="💰 Victory Rewards",
        value="\n".join([f"• {term}" for term in just.victory_peace_terms]),
        inline=False
    )
    
    embed.add_field(
        name="💀 Defeat Conditions",
        value="\n".join([f"• {cond}" for cond in just.defeat_conditions]),
        inline=False
    )
    
    embed.add_field(
        name="💸 Defeat Penalties", 
        value="\n".join([f"• {term}" for term in just.defeat_peace_terms]),
        inline=False
    )
    
    if just.special_conditions:
        embed.add_field(
            name="⚠️ Special Conditions",
            value="\n".join([f"• {cond}" for cond in just.special_conditions]),
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='declare_war')
async def declare_war(ctx, target: discord.Member, *, justification_name: str):
    """Declare war against another player."""
    if war_bot.current_phase != GamePhase.ORGANIZATION:
        await ctx.send("Wars can only be declared during Organization phase!")
        return
    
    # Validate players
    attacker = await db.get_player(ctx.author.id)
    defender = await db.get_player(target.id)
    
    if not attacker:
        await ctx.send("You must register first! Use `!register`")
        return
    
    if not defender:
        await ctx.send(f"{target.display_name} is not registered.")
        return
    
    if ctx.author.id == target.id:
        await ctx.send("You cannot declare war on yourself!")
        return
    
    # Validate justification
    is_valid, error_msg = validate_justification(
        justification_name, dict(attacker), dict(defender)
    )
    
    if not is_valid:
        await ctx.send(f"Invalid justification: {error_msg}")
        return
    
    # TODO: Check for existing wars, NAPs, etc.
    
    # Create war in database
    # TODO: Implement war creation in database
    
    justification = WAR_JUSTIFICATIONS[justification_name]
    
    embed = discord.Embed(
        title="⚔️ WAR DECLARED!",
        description=f"**{ctx.author.display_name}** has declared war on **{target.display_name}**",
        color=discord.Color.dark_red()
    )
    
    embed.add_field(name="Justification", value=justification.name, inline=True)
    embed.add_field(name="Attacker", value=ctx.author.display_name, inline=True)
    embed.add_field(name="Defender", value=target.display_name, inline=True)
    
    embed.add_field(
        name="Victory Conditions (Attacker)",
        value="\n".join([f"• {cond}" for cond in justification.victory_conditions]),
        inline=False
    )
    
    embed.add_field(
        name="Defeat Conditions (Attacker)", 
        value="\n".join([f"• {cond}" for cond in justification.defeat_conditions]),
        inline=False
    )
    
    embed.set_footer(text="The war has begun! Prepare your forces!")
    
    # Notify both players
    await ctx.send(embed=embed)
    
    # Send private war room creation message
    try:
        await ctx.author.send("Your war room has been created! Plan your strategy in secret.")
        await target.send("You are under attack! Your war room is ready for defensive preparations.")
    except discord.Forbidden:
        await ctx.send("⚠️ Could not send private war room notifications. Check your DM settings.")

@bot.command(name='simulate_battle')
async def simulate_battle(ctx, brigade1_id: int, brigade2_id: int):
    """Simulate a battle between two brigades (for testing)."""
    if war_bot.current_phase != GamePhase.BATTLE:
        await ctx.send("Battles can only occur during Battle phase!")
        return
    
    # This is a simplified test command
    # In reality, battles would be triggered by movement conflicts
    
    embed = discord.Embed(
        title="🛡️ Battle Simulation",
        description="Simulating battle between brigades...",
        color=discord.Color.orange()
    )
    
    # Simulate simple battle outcome
    winner = random.choice([brigade1_id, brigade2_id])
    
    embed.add_field(name="Participants", value=f"Brigade #{brigade1_id} vs Brigade #{brigade2_id}", inline=False)
    embed.add_field(name="Winner", value=f"Brigade #{winner}", inline=True)
    embed.add_field(name="Battle Type", value="Quick Skirmish", inline=True)
    
    # Add some battle phases
    skirmish_result = random.choice(["Attacker routes defender", "Defender holds firm", "Both sides exchange blows"])
    pitch_result = f"Pitch tally: {random.randint(-15, 15)}"
    
    embed.add_field(name="Skirmish Phase", value=skirmish_result, inline=False)
    embed.add_field(name="Pitch Phase", value=pitch_result, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='start_siege')
async def start_siege(ctx, target_city: str):
    """Begin sieging an enemy city."""
    if war_bot.current_phase != GamePhase.BATTLE:
        await ctx.send("Sieges can only be started during Battle phase!")
        return
    
    player = await db.get_player(ctx.author.id)
    if not player:
        await ctx.send("You must register first! Use `!register`")
        return
    
    # TODO: Validate player has brigades at target city
    # TODO: Check if city is enemy-controlled
    # TODO: Create siege in database
    
    embed = discord.Embed(
        title="🏰 Siege Begun!",
        description=f"Your forces have begun sieging **{target_city}**",
        color=discord.Color.orange()
    )
    
    # Determine siege timer based on city tier (simplified)
    city_tier = 1  # TODO: Get actual city tier from database
    siege_timer = city_tier  # Action cycles needed
    
    embed.add_field(name="Target", value=target_city, inline=True)
    embed.add_field(name="Siege Timer", value=f"{siege_timer} action cycles", inline=True)
    embed.add_field(name="Options", value="Assault when timer expires, or wait to starve out", inline=False)
    
    # Show garrison strength
    garrison_info = {
        1: "1 Heavy, 2 Ranged",
        2: "2 Heavy, 3 Ranged", 
        3: "3 Heavy, 4 Ranged"
    }
    
    embed.add_field(name="Garrison Strength", value=garrison_info[city_tier], inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='list_enhancements')
async def list_enhancements(ctx, brigade_type: Optional[str] = None):
    """Show available brigade enhancements."""
    embed = discord.Embed(
        title="Brigade Enhancements",
        description="Available enhancements for brigades",
        color=discord.Color.purple()
    )
    
    if brigade_type:
        # Show enhancements for specific brigade type
        try:
            target_type = next(bt for bt in BrigadeType if bt.value.lower() == brigade_type.lower())
        except StopIteration:
            await ctx.send("Invalid brigade type. Use `!brigade_types` to see valid types.")
            return
        
        # Filter enhancements for this type
        relevant_enhancements = {name: enh for name, enh in ENHANCEMENTS.items() 
                               if enh.brigade_type == target_type or enh.brigade_type is None}
    else:
        relevant_enhancements = ENHANCEMENTS
    
    for name, enhancement in relevant_enhancements.items():
        type_text = enhancement.brigade_type.value if enhancement.brigade_type else "Universal"
        
        # Build resource cost text
        resource_costs = []
        for resource, amount in enhancement.cost_resources.items():
            resource_costs.append(f"{amount} {resource}")
        
        cost_text = ", ".join(resource_costs) + f" OR {enhancement.cost_silver} silver"
        
        # Build stats text
        stats_text = []
        if enhancement.stats.skirmish: stats_text.append(f"⚔️+{enhancement.stats.skirmish}")
        if enhancement.stats.defense: stats_text.append(f"🛡️+{enhancement.stats.defense}")
        if enhancement.stats.pitch: stats_text.append(f"📯+{enhancement.stats.pitch}")
        if enhancement.stats.rally: stats_text.append(f"🚩+{enhancement.stats.rally}")
        if enhancement.stats.movement: stats_text.append(f"🏃+{enhancement.stats.movement}")
        
        stats_display = " ".join(stats_text) if stats_text else "No stat bonuses"
        
        field_value = f"**Type**: {type_text}\n**Cost**: {cost_text}\n**Stats**: {stats_display}"
        if enhancement.special_ability:
            field_value += f"\n**Special**: {enhancement.special_ability}"
        
        embed.add_field(name=name, value=field_value, inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='general_traits')
async def show_general_traits(ctx):
    """Show all possible general traits."""
    embed = discord.Embed(
        title="General Traits",
        description="Possible traits for generals (rolled randomly)",
        color=discord.Color.gold()
    )
    
    # Split traits into chunks to avoid embed limit
    traits_per_page = 10
    trait_items = list(GENERAL_TRAITS.items())
    
    for i in range(0, len(trait_items), traits_per_page):
        chunk = trait_items[i:i + traits_per_page]
        
        for trait_id, (name, description) in chunk:
            embed.add_field(
                name=f"{trait_id}. {name}",
                value=description,
                inline=False
            )
        
        if len(trait_items) > traits_per_page:
            embed.set_footer(text=f"Showing traits {i+1}-{min(i+traits_per_page, len(trait_items))} of {len(trait_items)}")
        
        await ctx.send(embed=embed)
        
        # If there are more traits, create a new embed
        if i + traits_per_page < len(trait_items):
            embed = discord.Embed(
                title="General Traits (continued)",
                color=discord.Color.gold()
            )

@bot.command(name='war_college_benefits')
async def show_war_college_benefits(ctx):
    """Show War College level benefits."""
    embed = discord.Embed(
        title="War College Benefits",
        description="Benefits gained from leveling up your War College",
        color=discord.Color.dark_blue()
    )
    
    benefits = {
        1: "General Cap: 1, General Level Floor: 1",
        2: "Roll for general traits twice, choose either result",
        3: "General Level Floor: 2",
        4: "General Cap: 2",
        5: "Pillaging die result +1, Sacking worth double",
        6: "General Level Floor: 3", 
        7: "General Cap: 3",
        8: "+1 to Skirmish and Defense rolls",
        9: "General Level Floor: 4",
        10: "General Cap: 4"
    }
    
    for level, benefit in benefits.items():
        embed.add_field(
            name=f"Level {level}",
            value=benefit,
            inline=False
        )
    
    embed.add_field(
        name="How to Level Up",
        value="• Win a war\n• Retire a Level 10 general",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='quick_reference')
async def quick_reference(ctx):
    """Show quick reference for game mechanics."""
    embed = discord.Embed(
        title="Quick Reference",
        description="Essential game mechanics at a glance",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🗓️ Game Cycle",
        value=(
            "**Tuesday/Friday**: Organization\n"
            "**Wednesday/Saturday**: Movement\n"
            "**Thursday/Sunday**: Battle"
        ),
        inline=True
    )
    
    embed.add_field(
        name="⚔️ Battle Phases",
        value=(
            "1. **Skirmish** - Best 2 units attack\n"
            "2. **Pitch** - 3 rounds of combat\n"
            "3. **Rally** - Stay or rout check\n"
            "4. **Action Report** - Casualties"
        ),
        inline=True
    )
    
    embed.add_field(
        name="🏰 Brigade Cap",
        value=(
            "Base: 2\n"
            "Tier 1 City: +1\n"
            "Tier 2 City: +3\n"
            "Tier 3 City: +5"
        ),
        inline=True
    )
    
    embed.add_field(
        name="🎲 Key Dice Rolls",
        value=(
            "**Destruction**: 1-2 = destroyed\n"
            "**Rally**: 5+ = stay in battle\n" 
            "**Promotion**: 1 = captured, 5-6 = level up\n"
            "**Pillage**: 6 = gain resource"
        ),
        inline=True
    )
    
    embed.add_field(
        name="🏛️ City Siege Times",
        value=(
            "**Tier 1**: 1 cycle\n"
            "**Tier 2**: 2 cycles\n"
            "**Tier 3**: 3 cycles\n"
            "**Starve**: +2x tier cycles"
        ),
        inline=True
    )
    
    embed.add_field(
        name="🛡️ Garrison Bonus",
        value=(
            "**Defense**: +2\n"
            "**Rally**: +2\n"
            "**Restriction**: Cannot skirmish"
        ),
        inline=True
    )
    
    await ctx.send(embed=embed)

@bot.command(name='backup_data')
async def backup_data(ctx):
    """Create a backup of all game data."""
    # Only allow certain users to backup (add role check here if needed)
    try:
        backup_path = await db.backup_data()
        await ctx.send(f"✅ Data backup created successfully at: `{backup_path}`")
    except Exception as e:
        await ctx.send(f"❌ Backup failed: {e}")

@bot.command(name='export_player')
async def export_player_data(ctx, target: Optional[discord.Member] = None):
    """Export all data for a player to a JSON file."""
    target_user = target or ctx.author
    
    try:
        player_data = await db.export_player_data(target_user.id)
        
        if not player_data['player']:
            await ctx.send(f"{target_user.display_name} is not registered.")
            return
        
        # Save to file
        filename = f"player_export_{target_user.id}_{int(datetime.now().timestamp())}.json"
        filepath = os.path.join("bot_data", filename)
        
        import aiofiles
        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(player_data, indent=2, ensure_ascii=False, default=str))
        
        embed = discord.Embed(
            title="Player Data Exported",
            description=f"Data for {target_user.display_name} exported successfully",
            color=discord.Color.green()
        )
        embed.add_field(name="File", value=filename, inline=True)
        embed.add_field(name="Size", value=f"{len(json.dumps(player_data))} characters", inline=True)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Export failed: {e}")

@bot.command(name='enhance_brigade')
async def enhance_brigade(ctx, brigade_id: str, enhancement: str):
    """Add enhancement to a brigade."""
    if war_bot.current_phase != GamePhase.ORGANIZATION:
        await ctx.send("Brigades can only be enhanced during Organization phase (Tuesday/Friday)!")
        return
    
    player = await db.get_player(ctx.author.id)
    if not player:
        await ctx.send("You must register first! Use `!register`")
        return
    
    # Validate enhancement exists
    if enhancement not in ENHANCEMENTS:
        available = ", ".join(ENHANCEMENTS.keys())
        await ctx.send(f"Invalid enhancement. Available: {available}")
        return
    
    # Get brigade and validate ownership
    brigade = await db.get_brigade(brigade_id)
    if not brigade:
        await ctx.send("Brigade not found.")
        return
    
    if brigade['player_id'] != ctx.author.id:
        await ctx.send("You don't own this brigade.")
        return
    
    if brigade['enhancement']:
        await ctx.send("This brigade already has an enhancement.")
        return
    
    enhancement_data = ENHANCEMENTS[enhancement]
    
    # Check if enhancement is compatible with brigade type
    if enhancement_data.brigade_type and enhancement_data.brigade_type.value != brigade['type']:
        await ctx.send(f"This enhancement is only for {enhancement_data.brigade_type.value} brigades.")
        return
    
    # Check if player has required resources
    resources = player.get('resources', {})
    silver = player.get('silver', 0)
    
    has_resources = all(resources.get(resource, 0) >= amount 
                       for resource, amount in enhancement_data.cost_resources.items())
    has_silver = silver >= enhancement_data.cost_silver
    
    if not (has_resources or has_silver):
        resource_cost = ", ".join([f"{amount} {resource}" 
                                 for resource, amount in enhancement_data.cost_resources.items()])
        await ctx.send(f"Insufficient resources! Need {resource_cost} OR {enhancement_data.cost_silver} silver.")
        return
    
    # Apply enhancement
    await db.update_brigade(brigade_id, {"enhancement": enhancement})
    
    # Deduct cost
    if has_resources:
        await db.deduct_resources(ctx.author.id, enhancement_data.cost_resources)
        cost_text = ", ".join([f"{amount} {resource}" 
                             for resource, amount in enhancement_data.cost_resources.items()])
    else:
        await db.deduct_silver(ctx.author.id, enhancement_data.cost_silver)
        cost_text = f"{enhancement_data.cost_silver} silver"
    
    embed = discord.Embed(
        title="Brigade Enhanced!",
        description=f"Enhancement '{enhancement}' applied to brigade {brigade_id}",
        color=discord.Color.purple()
    )
    
    embed.add_field(name="Enhancement", value=enhancement, inline=True)
    embed.add_field(name="Cost", value=cost_text, inline=True)
    embed.add_field(name="Special Ability", value=enhancement_data.special_ability or "None", inline=False)
    
    await ctx.send(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument: {error.param}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"Invalid argument: {error}")
    else:
        await ctx.send(f"An error occurred: {error}")

if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("ERROR: DISCORD_TOKEN not found in environment variables!")
        print("Please create a .env file with your bot token.")
    else:
        bot.run(token)
