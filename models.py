import asyncio
import aiosqlite
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import random

class BrigadeType(Enum):
    CAVALRY = "🐴 Cavalry"
    HEAVY = "⚔️ Heavy"  
    LIGHT = "🪓 Light"
    RANGED = "🏹 Ranged"
    SUPPORT = "🛡️ Support"

class GamePhase(Enum):
    ORGANIZATION = "Organization"  # Tuesday/Friday
    MOVEMENT = "Movement"  # Wednesday/Saturday  
    BATTLE = "Battle"  # Thursday/Sunday

@dataclass
class BrigadeStats:
    skirmish: int = 0
    defense: int = 0
    pitch: int = 0
    rally: int = 0
    movement: int = 0

# Brigade base stats
BRIGADE_STATS = {
    BrigadeType.CAVALRY: BrigadeStats(skirmish=1, pitch=1, movement=5),
    BrigadeType.HEAVY: BrigadeStats(defense=2, pitch=1, rally=1, movement=3),
    BrigadeType.LIGHT: BrigadeStats(skirmish=2, rally=1, movement=4),
    BrigadeType.RANGED: BrigadeStats(defense=2, pitch=1, movement=4),
    BrigadeType.SUPPORT: BrigadeStats(defense=2, rally=1, movement=4)
}

@dataclass
class Enhancement:
    name: str
    brigade_type: Optional[BrigadeType]  # None for universal enhancements
    cost_resources: Dict[str, int]
    cost_silver: int
    stats: BrigadeStats
    special_ability: str = ""

# Enhancement definitions
ENHANCEMENTS = {
    # Cavalry Enhancements
    "Life Guard": Enhancement(
        "Life Guard", BrigadeType.CAVALRY, 
        {"food": 1, "gem": 1, "metal": 1}, 40,
        BrigadeStats(rally=2),
        "Allows General to reroll a 1 on promotion roll once per battle"
    ),
    "Lancers": Enhancement(
        "Lancers", BrigadeType.CAVALRY,
        {"food": 1, "gem": 1, "metal": 1}, 40,
        BrigadeStats(skirmish=2),
        "Overrun automatically if they win skirmish"
    ),
    "Dragoons": Enhancement(
        "Dragoons", BrigadeType.CAVALRY,
        {"food": 1, "gem": 1, "metal": 1}, 40,
        BrigadeStats(defense=2, pitch=1, rally=1)
    ),
    
    # Heavy Enhancements
    "Artillery Team": Enhancement(
        "Artillery Team", BrigadeType.HEAVY,
        {"fuel": 1, "metal": 2}, 40,
        BrigadeStats(defense=1, pitch=1),
        "When garrisoned +1 Pitch. Applies -1 defense to all enemy brigades in battle"
    ),
    "Grenadiers": Enhancement(
        "Grenadiers", BrigadeType.HEAVY,
        {"fuel": 1, "metal": 2}, 40,
        BrigadeStats(skirmish=2, pitch=2)
    ),
    "Stormtroopers": Enhancement(
        "Stormtroopers", BrigadeType.HEAVY,
        {"fuel": 1, "metal": 2}, 40,
        BrigadeStats(pitch=1, rally=1, movement=1),
        "Ignores trench movement penalties"
    ),
    
    # Light Enhancements  
    "Rangers": Enhancement(
        "Rangers", BrigadeType.LIGHT,
        {"food": 1, "metal": 1, "timber": 1}, 40,
        BrigadeStats(skirmish=2, pitch=1)
    ),
    "Assault Team": Enhancement(
        "Assault Team", BrigadeType.LIGHT,
        {"food": 1, "metal": 1, "timber": 1}, 40,
        BrigadeStats(skirmish=1),
        "May select skirmish target, negates garrison modifier"
    ),
    "Commando": Enhancement(
        "Commando", BrigadeType.LIGHT,
        {"food": 1, "metal": 1, "timber": 1}, 40,
        BrigadeStats(defense=2, pitch=1),
        "Cannot be seen by enemy Sentry Teams"
    ),
    
    # Ranged Enhancements
    "Sharpshooters": Enhancement(
        "Sharpshooters", BrigadeType.RANGED,
        {"stone": 1, "timber": 2}, 40,
        BrigadeStats(defense=2),
        "When garrisoned +1 Pitch. Routs failed skirmishers, force destruction roll"
    ),
    "Mobile Platforms": Enhancement(
        "Mobile Platforms", BrigadeType.RANGED,
        {"stone": 1, "timber": 2}, 40,
        BrigadeStats(skirmish=1, defense=2, movement=1)
    ),
    "Mortar Team": Enhancement(
        "Mortar Team", BrigadeType.RANGED,
        {"stone": 1, "timber": 2}, 40,
        BrigadeStats(pitch=1, rally=1),
        "Negates garrison bonus for one random enemy brigade"
    ),
    
    # Support Enhancements
    "Field Hospital": Enhancement(
        "Field Hospital", BrigadeType.SUPPORT,
        {"fuel": 1, "stone": 2}, 40,
        BrigadeStats(),
        "May reroll Action Report destruction die, extends to army"
    ),
    "Combat Engineers": Enhancement(
        "Combat Engineers", BrigadeType.SUPPORT,
        {"fuel": 1, "stone": 2}, 40,
        BrigadeStats(),
        "Build temp structures, negate trench penalty, reduce siege time by 1"
    ),
    "Officer Corps": Enhancement(
        "Officer Corps", BrigadeType.SUPPORT,
        {"fuel": 1, "stone": 2}, 40,
        BrigadeStats(rally=2),
        "General needs 4-6 to level up, choose retreat location"
    ),
    
    # Universal Enhancements
    "Sentry Team": Enhancement(
        "Sentry Team", None,
        {"food": 2, "metal": 1}, 40,
        BrigadeStats(defense=3),
        "+1 tile sight"
    ),
    "Marines": Enhancement(
        "Marines", None,
        {"food": 2, "metal": 1}, 40,
        BrigadeStats(),
        "Immediate siege when landing, +1 sea tile movement for army"
    )
}

# General traits
GENERAL_TRAITS = {
    1: ("Ambitious", "-1 to promotion number needed after battle"),
    2: ("Bold", "One skirmisher gets bonus equal to half general level (rounded up)"),
    3: ("Brilliant", "Double general level during Pitch"),
    4: ("Brutal", "Pillaging succeeds on 5-6, razing also counts as sacking"),
    5: ("Cautious", "May skip skirmishing stage"),
    6: ("Chivalrous", "Allow enemy reroll on destruction dice for -1 siege timer"),
    7: ("Confident", "+2 Defense, +1 Rally for all brigades"),
    8: ("Defiant", "+2 Rally for all brigades"),
    9: ("Disciplined", "+1 Pitch, +1 Rally for all brigades"),
    10: ("Dogged", "Choose 2 brigades to assist adjacent tile battles"),
    11: ("Heroic", "+1 Rally. May sacrifice for new pitch with general level bonus"),
    12: ("Inspiring", "Free reroll on rally rolls, celebrating gives +2 rally"),
    13: ("Lucky", "May reroll promotion die once per battle when rolling 1"),
    14: ("Mariner", "+1 army movement while embarked, siege from landing"),
    15: ("Merciless", "Enemy brigades destroyed on 1-3 during action report"),
    16: ("Prodigious", "Gets additional 2 levels (lost if trait rerolled)"),
    17: ("Relentless", "+1 army movement on land, may pursue retreating enemies"),
    18: ("Resolute", "+3 Defense for all brigades"),
    19: ("Wary", "Alerted when enemy can see army, +1 sight, reveal enemy traits"),
    20: ("Zealous", "+1 Rally (+2 Rally +1 Pitch in holy wars)")
}

class DatabaseManager:
    def __init__(self, db_path: str = "hegemony.db"):
        self.db_path = db_path

    async def init_database(self):
        async with aiosqlite.connect(self.db_path) as db:
            # Players table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    war_college_level INTEGER DEFAULT 1,
                    general_cap INTEGER DEFAULT 1,
                    brigade_cap INTEGER DEFAULT 2,
                    cities TEXT DEFAULT '[]',
                    resources TEXT DEFAULT '{}',
                    silver INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Brigades table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS brigades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER,
                    type TEXT NOT NULL,
                    enhancement TEXT,
                    location TEXT,
                    army_id INTEGER,
                    is_garrisoned BOOLEAN DEFAULT FALSE,
                    is_fatigued BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (player_id) REFERENCES players (user_id)
                )
            """)
            
            # Generals table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS generals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER,
                    name TEXT NOT NULL,
                    level INTEGER DEFAULT 1,
                    trait_id INTEGER,
                    location TEXT,
                    army_id INTEGER,
                    is_captured BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (player_id) REFERENCES players (user_id)
                )
            """)
            
            # Armies table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS armies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER,
                    general_id INTEGER,
                    name TEXT,
                    location TEXT,
                    movement_orders TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (player_id) REFERENCES players (user_id),
                    FOREIGN KEY (general_id) REFERENCES generals (id)
                )
            """)
            
            # Wars table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS wars (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attacker_id INTEGER,
                    defender_id INTEGER,
                    justification TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    victory_conditions TEXT,
                    defeat_conditions TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    FOREIGN KEY (attacker_id) REFERENCES players (user_id),
                    FOREIGN KEY (defender_id) REFERENCES players (user_id)
                )
            """)
            
            # Battles table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS battles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    war_id INTEGER,
                    location TEXT NOT NULL,
                    participants TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    battle_log TEXT DEFAULT '[]',
                    winner_id INTEGER,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    FOREIGN KEY (war_id) REFERENCES wars (id)
                )
            """)
            
            # Game state table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS game_state (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    current_phase TEXT DEFAULT 'Organization',
                    cycle_start_date TEXT,
                    phase_end_time TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert default game state if not exists
            await db.execute("""
                INSERT OR IGNORE INTO game_state (id) VALUES (1)
            """)
            
            await db.commit()

    async def get_player(self, user_id: int) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM players WHERE user_id = ?", (user_id,)
            )
            return await cursor.fetchone()

    async def create_player(self, user_id: int, username: str) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO players (user_id, username, resources) 
                    VALUES (?, ?, ?)
                """, (user_id, username, '{"food": 10, "metal": 10, "silver": 100}'))
                await db.commit()
                return True
        except aiosqlite.IntegrityError:
            return False

    async def get_brigades(self, player_id: int) -> List[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM brigades WHERE player_id = ?", (player_id,)
            )
            return await cursor.fetchall()

    async def create_brigade(self, player_id: int, brigade_type: str, location: str = "Capital") -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO brigades (player_id, type, location) 
                VALUES (?, ?, ?)
            """, (player_id, brigade_type, location))
            await db.commit()
            return cursor.lastrowid

    async def get_generals(self, player_id: int) -> List[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM generals WHERE player_id = ?", (player_id,)
            )
            return await cursor.fetchall()

    async def create_general(self, player_id: int, name: str, trait_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO generals (player_id, name, trait_id) 
                VALUES (?, ?, ?)
            """, (player_id, name, trait_id))
            await db.commit()
            return cursor.lastrowid
