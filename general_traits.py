"""
General Trait Effects Handler
Centralizes all general trait effect implementations
"""

from typing import Dict, List, Optional, Tuple
from models import GENERAL_TRAITS

class GeneralTraitHandler:
    def __init__(self, data_manager):
        self.db = data_manager
    
    async def apply_wary_trait_effects(self, army_id: str, location: str) -> Dict:
        """Apply Wary trait effects: alert when enemy can see army, +1 sight, reveal enemy traits."""
        army = await self.db.get_army(army_id)
        if not army or not army.get('general_id'):
            return {"alerts": [], "revealed_traits": []}
        
        general = await self.db.get_general(army['general_id'])
        if not general:
            return {"alerts": [], "revealed_traits": []}
        
        trait_name, _ = GENERAL_TRAITS[general['trait_id']]
        if trait_name != "Wary":
            return {"alerts": [], "revealed_traits": []}
        
        alerts = []
        revealed_traits = []
        
        # Check for enemy armies in sight range (simplified)
        enemy_armies = await self._get_nearby_enemy_armies(army['player_id'], location)
        
        for enemy_army in enemy_armies:
            # Alert when enemy can see this army
            if self._can_see_army(enemy_army, location):
                alerts.append(f"Enemy army {enemy_army['id']} can see your position!")
            
            # Reveal enemy general traits
            if enemy_army.get('general_id'):
                enemy_general = await self.db.get_general(enemy_army['general_id'])
                if enemy_general:
                    enemy_trait_name, _ = GENERAL_TRAITS[enemy_general['trait_id']]
                    revealed_traits.append({
                        "general_name": enemy_general['name'],
                        "trait": enemy_trait_name,
                        "army_id": enemy_army['id']
                    })
        
        return {"alerts": alerts, "revealed_traits": revealed_traits}
    
    async def apply_dogged_trait_assistance(self, general_id: str, battle_location: str) -> List[str]:
        """Apply Dogged trait: choose 2 brigades to assist adjacent tile battles."""
        general = await self.db.get_general(general_id)
        if not general:
            return []
        
        trait_name, _ = GENERAL_TRAITS[general['trait_id']]
        if trait_name != "Dogged":
            return []
        
        # Get brigades from general's army
        armies = await self.db.get_armies(general['player_id'])
        general_army = None
        for army in armies:
            if army.get('general_id') == general_id:
                general_army = army
                break
        
        if not general_army:
            return []
        
        # Select up to 2 brigades to assist (simplified selection)
        brigade_ids = general_army.get('brigade_ids', [])
        assisting_brigades = brigade_ids[:2]  # Take first 2
        
        return assisting_brigades
    
    async def apply_chivalrous_trait_effect(self, general_id: str) -> Dict:
        """Apply Chivalrous trait: allow enemy reroll on destruction dice for -1 siege timer."""
        general = await self.db.get_general(general_id)
        if not general:
            return {"can_offer_chivalry": False}
        
        trait_name, _ = GENERAL_TRAITS[general['trait_id']]
        if trait_name != "Chivalrous":
            return {"can_offer_chivalry": False}
        
        return {
            "can_offer_chivalry": True,
            "effect": "Allow enemy reroll on destruction dice for -1 siege timer on next siege"
        }
    
    def apply_war_college_trait_bonuses(self, player_data: Dict, action: str) -> Dict:
        """Apply war college level bonuses to various actions."""
        war_college_level = player_data.get('war_college_level', 1)
        bonuses = {}
        
        if action == "pillaging" and war_college_level >= 5:
            bonuses["pillage_bonus"] = 1  # Pillaging die result +1
        
        if action == "sacking" and war_college_level >= 5:
            bonuses["sack_multiplier"] = 2  # Sacking worth double
        
        if action == "battle_rolls" and war_college_level >= 8:
            bonuses["skirmish_bonus"] = 1
            bonuses["defense_bonus"] = 1
        
        return bonuses
    
    async def check_general_level_floor(self, player_id: int) -> int:
        """Get the minimum general level based on war college."""
        player = await self.db.get_player(player_id)
        if not player:
            return 1
        
        war_college_level = player.get('war_college_level', 1)
        return min(((war_college_level - 1) // 3) + 1, 4)
    
    def apply_prodigious_trait(self, general_data: Dict) -> int:
        """Apply Prodigious trait: +2 levels (lost if trait rerolled)."""
        trait_name, _ = GENERAL_TRAITS[general_data['trait_id']]
        if trait_name == "Prodigious":
            return general_data.get('level', 1) + 2
        return general_data.get('level', 1)
    
    async def _get_nearby_enemy_armies(self, player_id: int, location: str) -> List[Dict]:
        """Get enemy armies near a location (simplified)."""
        all_armies = await self.db.get_all_armies()
        nearby_enemies = []
        
        for army in all_armies.values():
            if army.get('player_id') != player_id:
                # Simplified distance check (would need proper map system)
                if army.get('location', '').startswith(location[:3]):  # Very simplified
                    nearby_enemies.append(army)
        
        return nearby_enemies
    
    def _can_see_army(self, army: Dict, target_location: str) -> bool:
        """Check if an army can see a target location (simplified)."""
        # Simplified sight check (would need proper map/sight system)
        army_location = army.get('location', '')
        return army_location == target_location or army_location.startswith(target_location[:2])
    
    async def handle_general_retreat_choice(self, general_id: str, battle_result: Dict) -> Optional[str]:
        """Handle Officer Corps trait: choose retreat location."""
        general = await self.db.get_general(general_id)
        if not general:
            return None
        
        # Check if any brigade in army has Officer Corps enhancement
        armies = await self.db.get_armies(general['player_id'])
        for army in armies:
            if army.get('general_id') == general_id:
                for brigade_id in army.get('brigade_ids', []):
                    brigade = await self.db.get_brigade(brigade_id)
                    if brigade and brigade.get('enhancement') == "Officer Corps":
                        return "Can choose retreat location"
        
        return None
    
    def calculate_celebration_bonus(self, general_data: Optional[Dict]) -> int:
        """Calculate celebration rally bonus based on general trait."""
        if not general_data:
            return 1
        
        trait_name, _ = GENERAL_TRAITS[general_data['trait_id']]
        if trait_name == "Inspiring":
            return 2  # Celebrating gives +2 rally instead of +1
        
        return 1
