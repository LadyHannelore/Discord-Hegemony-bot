"""
Siege System for Discord Hegemony Bot
Handles city sieges, occupations, and related mechanics
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import random
from datetime import datetime, timedelta

class SiegeAction(Enum):
    ASSAULT = "assault"
    STARVE = "starve"

class SiegeOutcome(Enum):
    OCCUPY = "occupy"
    SACK = "sack" 
    RAZE = "raze"

@dataclass
class CityGarrison:
    """Automatic city garrison based on tier"""
    heavy_count: int
    ranged_count: int
    
    @classmethod
    def from_tier(cls, tier: int) -> 'CityGarrison':
        garrison_map = {
            1: cls(heavy_count=1, ranged_count=2),
            2: cls(heavy_count=2, ranged_count=3),
            3: cls(heavy_count=3, ranged_count=4)
        }
        return garrison_map.get(tier, cls(heavy_count=1, ranged_count=2))

@dataclass
class Siege:
    id: str
    city_name: str
    city_tier: int
    attacker_id: int
    defender_id: int
    siege_timer: int  # Action cycles remaining
    started_at: str
    status: str = "active"  # active, completed, failed
    
class SiegeSystem:
    def __init__(self, data_manager):
        self.db = data_manager
    
    async def start_siege(self, city_name: str, city_tier: int, attacker_id: int, 
                         defender_id: int, brigades: List[str], general_id: Optional[str] = None) -> str:
        """Start a siege on a city."""
        sieges = await self.db._load_json("bot_data/sieges.json") if hasattr(self.db, '_load_json') else {}
        
        # Calculate siege timer with Combat Engineers bonus
        siege_timer = city_tier
        
        # Check for Combat Engineers enhancement
        for brigade_id in brigades:
            brigade = await self.db.get_brigade(brigade_id)
            if brigade and brigade.get('enhancement') == "Combat Engineers":
                siege_timer = max(1, siege_timer - 1)  # Decrease by 1, minimum 1
                break
        
        # Create siege
        siege_id = f"siege_{len(sieges) + 1}_{int(datetime.now().timestamp())}"
        siege = Siege(
            id=siege_id,
            city_name=city_name,
            city_tier=city_tier,
            attacker_id=attacker_id,
            defender_id=defender_id,
            siege_timer=siege_timer,
            started_at=datetime.now().isoformat()
        )
        
        sieges[siege_id] = {
            "id": siege_id,
            "city_name": city_name,
            "city_tier": city_tier,
            "attacker_id": attacker_id,
            "defender_id": defender_id,
            "siege_timer": siege_timer,
            "brigades": brigades,
            "general_id": general_id,
            "started_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        if hasattr(self.db, '_save_json'):
            await self.db._save_json("bot_data/sieges.json", sieges)
        
        return siege_id
    
    async def advance_siege_timers(self):
        """Advance all active siege timers by 1 cycle."""
        sieges = await self.db._load_json("bot_data/sieges.json") if hasattr(self.db, '_load_json') else {}
        
        for siege_id, siege_data in sieges.items():
            if siege_data["status"] == "active":
                siege_data["siege_timer"] -= 1
                
                if siege_data["siege_timer"] <= 0:
                    siege_data["status"] = "ready_for_assault"
        
        if hasattr(self.db, '_save_json'):
            await self.db._save_json("bot_data/sieges.json", sieges)
    
    async def can_assault(self, siege_id: str) -> bool:
        """Check if siege is ready for assault."""
        sieges = await self.db._load_json("bot_data/sieges.json") if hasattr(self.db, '_load_json') else {}
        siege = sieges.get(siege_id)
        
        return siege is not None and siege["siege_timer"] <= 0
    
    def create_city_garrison(self, city_tier: int) -> List[Dict]:
        """Create automatic city garrison brigades."""
        garrison = CityGarrison.from_tier(city_tier)
        brigades = []
        
        # Create heavy brigades
        for i in range(garrison.heavy_count):
            brigades.append({
                "id": f"garrison_heavy_{i+1}",
                "type": "heavy",
                "enhancement": None,
                "stats": {
                    "skirmish": 0,
                    "defense": 2,
                    "pitch": 1,
                    "rally": 1,
                    "movement": 3
                }
            })
        
        # Create ranged brigades
        for i in range(garrison.ranged_count):
            brigades.append({
                "id": f"garrison_ranged_{i+1}",
                "type": "ranged", 
                "enhancement": None,
                "stats": {
                    "skirmish": 0,
                    "defense": 2,
                    "pitch": 1,
                    "rally": 0,
                    "movement": 4
                }
            })
        
        # Garrison bonuses: +2 defense, +2 rally
        for brigade in brigades:
            brigade["stats"]["defense"] += 2
            brigade["stats"]["rally"] += 2
        
        return brigades
    
    async def conduct_assault(self, siege_id: str, attacking_brigades: List[Dict]) -> Dict:
        """Conduct an assault on a besieged city."""
        from battle_system import BattleSystem, BattleSide, create_battle_brigade
        
        sieges = await self.db._load_json("bot_data/sieges.json") if hasattr(self.db, '_load_json') else {}
        siege = sieges.get(siege_id)
        
        if not siege or siege["status"] != "ready_for_assault":
            return {"success": False, "message": "Siege not ready for assault"}
        
        # Create garrison
        garrison_brigades = self.create_city_garrison(siege["city_tier"])
        
        # Convert to BattleBrigade objects
        from models import BrigadeType, BrigadeStats
        from battle_system import BattleBrigade
        
        garrison_battle_brigades = []
        for brigade_data in garrison_brigades:
            brigade_type = BrigadeType.HEAVY if brigade_data["type"] == "heavy" else BrigadeType.RANGED
            stats = BrigadeStats(
                skirmish=brigade_data["stats"]["skirmish"],
                defense=brigade_data["stats"]["defense"],
                pitch=brigade_data["stats"]["pitch"],
                rally=brigade_data["stats"]["rally"],
                movement=brigade_data["stats"]["movement"]
            )
            garrison_battle_brigades.append(BattleBrigade(
                id=brigade_data["id"],
                player_id=siege["defender_id"],
                type=brigade_type,
                enhancement=None,
                stats=stats
            ))
        
        # Convert attacking brigades to BattleBrigade objects
        attacking_battle_brigades = []
        for brigade_data in attacking_brigades:
            if "stats" in brigade_data and brigade_data["stats"]:
                stats = BrigadeStats(**brigade_data["stats"])
                attacking_battle_brigades.append(create_battle_brigade(brigade_data, stats))
            else:
                # Create default stats if missing
                default_stats = BrigadeStats(skirmish=0, defense=2, pitch=1, rally=0, movement=3)
                attacking_battle_brigades.append(create_battle_brigade(brigade_data, default_stats))
        
        # Set up battle
        battle_system = BattleSystem()
        
        attacker_side = BattleSide(
            player_id=siege["attacker_id"],
            brigades=attacking_battle_brigades,
            general=None  # Would get from army if applicable
        )
        
        defender_side = BattleSide(
            player_id=siege["defender_id"], 
            brigades=garrison_battle_brigades,
            general=None  # Garrisons don't have generals
        )
        
        # Conduct battle
        battle_result = await battle_system.conduct_battle(
            attacker_side, defender_side, f"Siege of {siege['city_name']}"
        )
        
        # Update siege status
        if battle_result.get("winner") == attacker_side:
            siege["status"] = "victory"
            siege["completed_at"] = datetime.now().isoformat()
        else:
            siege["status"] = "failed"
            siege["completed_at"] = datetime.now().isoformat()
        
        if hasattr(self.db, '_save_json'):
            await self.db._save_json("bot_data/sieges.json", sieges)
        
        return {
            "success": True,
            "battle_result": battle_result,
            "siege_result": "victory" if battle_result.get("winner") == attacker_side else "failed"
        }
    
    async def starve_out_city(self, siege_id: str) -> Dict:
        """Attempt to starve out a city (requires 2x city tier additional cycles)."""
        sieges = await self.db._load_json("bot_data/sieges.json") if hasattr(self.db, '_load_json') else {}
        siege = sieges.get(siege_id)
        
        if not siege:
            return {"success": False, "message": "Siege not found"}
        
        # Check if enough time has passed (2x tier additional cycles after timer expired)
        cycles_since_ready = siege.get("cycles_since_ready", 0)
        required_additional_cycles = siege["city_tier"] * 2
        
        if cycles_since_ready >= required_additional_cycles:
            siege["status"] = "starved"
            siege["completed_at"] = datetime.now().isoformat()
            
            if hasattr(self.db, '_save_json'):
                await self.db._save_json("bot_data/sieges.json", sieges)
            
            return {"success": True, "message": f"{siege['city_name']} starved out!"}
        else:
            cycles_remaining = required_additional_cycles - cycles_since_ready
            return {
                "success": False, 
                "message": f"Need {cycles_remaining} more cycles to starve out the city"
            }
    
    async def resolve_siege_victory(self, siege_id: str, outcome: SiegeOutcome, 
                                  attacker_id: int, defender_id: int) -> Dict:
        """Resolve the outcome of a successful siege."""
        result = {"action": outcome.value}
        
        if outcome == SiegeOutcome.OCCUPY:
            # Transfer city control temporarily
            result["message"] = "City occupied until end of war"
            result["effect"] = "temporary_control"
            
        elif outcome == SiegeOutcome.SACK:
            # Take 2 random resources
            resource_types = ["food", "metal", "stone", "timber", "fuel", "gems"]
            taken_resources = random.choices(resource_types, k=2)
            
            result["message"] = f"City sacked! Gained {', '.join(taken_resources)}"
            result["effect"] = "resource_gain"
            result["resources_gained"] = ", ".join(taken_resources)
            
            # Actually transfer resources
            for resource in taken_resources:
                await self.db.add_resource(attacker_id, resource, 1)
                # Note: Should also deduct from defender if they have it
            
        elif outcome == SiegeOutcome.RAZE:
            # Decrease city tier by 1
            result["message"] = "City razed! Tier decreased by 1"
            result["effect"] = "city_damaged"
            
            # Check for Brutal general trait
            attacker = await self.db.get_player(attacker_id)
            brutal_general = False
            
            if attacker:
                generals = await self.db.get_generals(attacker_id)
                for general in generals:
                    from models import GENERAL_TRAITS
                    trait_name, _ = GENERAL_TRAITS[general['trait_id']]
                    if trait_name == "Brutal":
                        brutal_general = True
                        break
            
            # Brutal trait: razing also counts as sacking
            if brutal_general:
                resource_types = ["food", "metal", "stone", "timber", "fuel", "gems"]
                taken_resources = random.choices(resource_types, k=2)
                result["message"] += f" + Sacked for {', '.join(taken_resources)} (Brutal trait)"
                result["brutal_bonus"] = ", ".join(taken_resources)
                
                for resource in taken_resources:
                    await self.db.add_resource(attacker_id, resource, 1)
            
            # Would need to update city data in player profile
            # This would require additional implementation
        
        return result

    async def get_active_sieges(self, player_id: Optional[int] = None) -> List[Dict]:
        """Get all active sieges, optionally filtered by player."""
        sieges = await self.db._load_json("bot_data/sieges.json") if hasattr(self.db, '_load_json') else {}
        
        active_sieges = [s for s in sieges.values() if s["status"] in ["active", "ready_for_assault"]]
        
        if player_id:
            active_sieges = [s for s in active_sieges 
                           if s["attacker_id"] == player_id or s["defender_id"] == player_id]
        
        return active_sieges
