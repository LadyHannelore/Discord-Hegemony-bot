"""
Temporary Structures System for Discord Hegemony Bot
Handles trenches, watchtowers, and forts
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime

class StructureType(Enum):
    TRENCH = "trench"
    WATCHTOWER = "watchtower"
    FORT = "fort"

@dataclass
class TemporaryStructure:
    id: str
    type: StructureType
    location: str
    owner_id: int
    built_at: str
    expires_at: str  # Next map update
    
class TemporaryStructureSystem:
    def __init__(self, data_manager):
        self.db = data_manager
        self.structure_costs = {
            StructureType.TRENCH: {"stone": 1},
            StructureType.WATCHTOWER: {"stone": 2}, 
            StructureType.FORT: {"stone": 3}
        }
        
        self.structure_effects = {
            StructureType.TRENCH: "Enemy brigades require +1 movement to pass through",
            StructureType.WATCHTOWER: "Unmoved brigades get +1 sight range",
            StructureType.FORT: "Unmoved brigades become garrisoned (+2 defense, +2 rally)"
        }
    
    async def build_structure(self, player_id: int, structure_type: StructureType, 
                            location: str) -> Dict:
        """Build a temporary structure."""
        from models import GamePhase
        
        # Check if it's organization day
        game_state = await self.db.get_game_state()
        if game_state.get("current_phase") != GamePhase.ORGANIZATION.value:
            return {
                "success": False,
                "message": "Structures can only be built during Organization phase"
            }
        
        # Check player resources
        player = await self.db.get_player(player_id)
        if not player:
            return {"success": False, "message": "Player not found"}
        
        cost = self.structure_costs[structure_type]
        for resource, amount in cost.items():
            if player.get("resources", {}).get(resource, 0) < amount:
                return {
                    "success": False,
                    "message": f"Insufficient {resource}. Need {amount}, have {player['resources'].get(resource, 0)}"
                }
        
        # Check if location is in player territory
        if not await self._is_in_territory(player_id, location):
            return {
                "success": False,
                "message": "Can only build structures in your territory"
            }
        
        # Deduct resources
        await self.db.deduct_resources(player_id, cost)
        
        # Create structure
        structures = await self._load_structures()
        structure_id = f"struct_{len(structures) + 1}_{int(datetime.now().timestamp())}"
        
        structure = {
            "id": structure_id,
            "type": structure_type.value,
            "location": location,
            "owner_id": player_id,
            "built_at": datetime.now().isoformat(),
            "expires_at": self._get_next_map_update(),
            "active": True
        }
        
        structures[structure_id] = structure
        await self._save_structures(structures)
        
        return {
            "success": True,
            "message": f"{structure_type.value.title()} built at {location}",
            "structure_id": structure_id,
            "effect": self.structure_effects[structure_type]
        }
    
    async def get_structures_at_location(self, location: str) -> List[Dict]:
        """Get all active structures at a location."""
        structures = await self._load_structures()
        location_structures = []
        
        for structure in structures.values():
            if (structure["location"] == location and 
                structure["active"] and 
                not self._is_expired(structure)):
                location_structures.append(structure)
        
        return location_structures
    
    async def get_player_structures(self, player_id: int) -> List[Dict]:
        """Get all structures owned by a player."""
        structures = await self._load_structures()
        player_structures = []
        
        for structure in structures.values():
            if (structure["owner_id"] == player_id and 
                structure["active"] and 
                not self._is_expired(structure)):
                player_structures.append(structure)
        
        return player_structures
    
    async def cleanup_expired_structures(self):
        """Remove expired structures (called during map updates)."""
        structures = await self._load_structures()
        active_structures = {}
        
        for structure_id, structure in structures.items():
            if not self._is_expired(structure):
                active_structures[structure_id] = structure
        
        await self._save_structures(active_structures)
        
        expired_count = len(structures) - len(active_structures)
        return expired_count
    
    def apply_structure_effects(self, brigade_data: Dict, location: str, 
                              structures: List[Dict]) -> Dict:
        """Apply structure effects to a brigade at a location."""
        modified_brigade = brigade_data.copy()
        effects_applied = []
        
        for structure in structures:
            if structure["type"] == StructureType.TRENCH.value:
                # Trench effect handled in movement system
                pass
            
            elif structure["type"] == StructureType.WATCHTOWER.value:
                # Check if brigade hasn't moved this cycle
                if not brigade_data.get("moved_this_cycle", False):
                    modified_brigade["sight_range"] = modified_brigade.get("sight_range", 1) + 1
                    effects_applied.append("Extended sight (+1)")
            
            elif structure["type"] == StructureType.FORT.value:
                # Check if brigade hasn't moved this cycle
                if not brigade_data.get("moved_this_cycle", False):
                    modified_brigade["is_garrisoned"] = True
                    modified_brigade["garrison_bonus"] = {
                        "defense": 2,
                        "rally": 2
                    }
                    effects_applied.append("Garrisoned (+2 defense, +2 rally)")
        
        modified_brigade["structure_effects"] = effects_applied
        return modified_brigade
    
    def calculate_movement_cost(self, from_location: str, to_location: str, 
                              brigade_data: Dict) -> int:
        """Calculate movement cost including trench penalties."""
        base_cost = 1
        
        # Check for trenches at destination
        # This would integrate with the movement system
        # For now, return base cost
        return base_cost
    
    async def _load_structures(self) -> Dict:
        """Load structures from file."""
        try:
            if hasattr(self.db, '_load_json'):
                return await self.db._load_json("bot_data/structures.json")
            return {}
        except Exception:
            return {}
    
    async def _save_structures(self, structures: Dict):
        """Save structures to file."""
        try:
            if hasattr(self.db, '_save_json'):
                await self.db._save_json("bot_data/structures.json", structures)
        except Exception:
            pass
    
    async def _is_in_territory(self, player_id: int, location: str) -> bool:
        """Check if location is in player's territory."""
        # Simplified check - would need proper map system
        player = await self.db.get_player(player_id)
        if not player:
            return False
        
        # For now, allow building anywhere (would need proper territory system)
        return True
    
    def _get_next_map_update(self) -> str:
        """Get timestamp of next map update."""
        # Simplified - structures expire after next cycle
        from datetime import timedelta
        next_update = datetime.now() + timedelta(days=1)
        return next_update.isoformat()
    
    def _is_expired(self, structure: Dict) -> bool:
        """Check if structure has expired."""
        try:
            expires_at = datetime.fromisoformat(structure["expires_at"])
            return datetime.now() > expires_at
        except Exception:
            return True

    async def get_structure_info(self) -> Dict:
        """Get information about all structure types."""
        return {
            "types": {
                "trench": {
                    "cost": self.structure_costs[StructureType.TRENCH],
                    "effect": self.structure_effects[StructureType.TRENCH]
                },
                "watchtower": {
                    "cost": self.structure_costs[StructureType.WATCHTOWER],
                    "effect": self.structure_effects[StructureType.WATCHTOWER]
                },
                "fort": {
                    "cost": self.structure_costs[StructureType.FORT],
                    "effect": self.structure_effects[StructureType.FORT]
                }
            },
            "rules": [
                "Structures can only be built during Organization phase",
                "Must be built in your territory",
                "Structures expire at next map update",
                "Towers and Forts can be used by opponents"
            ]
        }
