import json
import os
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import asdict
import aiofiles

class JsonDataManager:
    def __init__(self, data_dir: str = "bot_data"):
        self.data_dir = data_dir
        self.players_file = os.path.join(data_dir, "players.json")
        self.brigades_file = os.path.join(data_dir, "brigades.json")
        self.generals_file = os.path.join(data_dir, "generals.json")
        self.armies_file = os.path.join(data_dir, "armies.json")
        self.wars_file = os.path.join(data_dir, "wars.json")
        self.battles_file = os.path.join(data_dir, "battles.json")
        self.game_state_file = os.path.join(data_dir, "game_state.json")
        self.structures_file = os.path.join(data_dir, "structures.json")
        self.sieges_file = os.path.join(data_dir, "sieges.json")
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)

    async def init_data_files(self):
        """Initialize all data files with default structures."""
        default_data = {
            "players": {},
            "brigades": {},
            "generals": {},
            "armies": {},
            "wars": {},
            "battles": {},
            "game_state": {
                "current_phase": "Organization",
                "cycle_start_date": datetime.now().isoformat(),
                "phase_end_time": None,
                "updated_at": datetime.now().isoformat()
            }
        }
        
        files_and_data = [
            (self.players_file, {}),
            (self.brigades_file, {}),
            (self.generals_file, {}),
            (self.armies_file, {}),
            (self.wars_file, {}),
            (self.battles_file, {}),
            (self.structures_file, {}),
            (self.sieges_file, {}),
            (self.game_state_file, default_data["game_state"])
        ]
        
        for file_path, default_content in files_and_data:
            if not os.path.exists(file_path):
                await self._save_json(file_path, default_content)

    async def _load_json(self, file_path: str) -> Dict:
        """Load JSON data from file."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content) if content.strip() else {}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    async def _save_json(self, file_path: str, data: Dict):
        """Save JSON data to file."""
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, indent=2, ensure_ascii=False, default=str))

    async def get_player(self, user_id: int) -> Optional[Dict]:
        """Get player data by user ID."""
        players = await self._load_json(self.players_file)
        return players.get(str(user_id))

    async def create_player(self, user_id: int, username: str) -> bool:
        """Create a new player."""
        try:
            players = await self._load_json(self.players_file)
            
            if str(user_id) in players:
                return False  # Player already exists
            
            players[str(user_id)] = {
                "user_id": user_id,
                "username": username,
                "war_college_level": 1,
                "general_cap": 1,
                "brigade_cap": 2,
                "cities": [{"name": "Capital", "tier": 1}],  # Default starting city
                "resources": {
                    "food": 10,
                    "metal": 10,
                    "stone": 5,
                    "timber": 5,
                    "fuel": 2,
                    "gems": 1
                },
                "silver": 100,
                "created_at": datetime.now().isoformat()
            }
            
            await self._save_json(self.players_file, players)
            return True
        except Exception:
            return False

    async def update_player(self, user_id: int, updates: Dict) -> bool:
        """Update player data."""
        try:
            players = await self._load_json(self.players_file)
            
            if str(user_id) not in players:
                return False
            
            players[str(user_id)].update(updates)
            players[str(user_id)]["updated_at"] = datetime.now().isoformat()
            
            await self._save_json(self.players_file, players)
            return True
        except Exception:
            return False

    async def get_brigades(self, player_id: int) -> List[Dict]:
        """Get all brigades for a player."""
        brigades = await self._load_json(self.brigades_file)
        return [brigade for brigade in brigades.values() if brigade.get("player_id") == player_id]

    async def create_brigade(self, player_id: int, brigade_type: str, location: str = "Capital") -> str:
        """Create a new brigade and return its ID."""
        brigades = await self._load_json(self.brigades_file)
        
        # Generate unique ID
        brigade_id = f"brigade_{len(brigades) + 1}_{int(datetime.now().timestamp())}"
        
        brigades[brigade_id] = {
            "id": brigade_id,
            "player_id": player_id,
            "type": brigade_type,
            "enhancement": None,
            "location": location,
            "army_id": None,
            "is_garrisoned": False,
            "is_fatigued": False,
            "created_at": datetime.now().isoformat()
        }
        
        await self._save_json(self.brigades_file, brigades)
        return brigade_id

    async def get_brigade(self, brigade_id: str) -> Optional[Dict]:
        """Get specific brigade by ID."""
        brigades = await self._load_json(self.brigades_file)
        return brigades.get(brigade_id)

    async def update_brigade(self, brigade_id: str, updates: Dict) -> bool:
        """Update brigade data."""
        try:
            brigades = await self._load_json(self.brigades_file)
            
            if brigade_id not in brigades:
                return False
            
            brigades[brigade_id].update(updates)
            brigades[brigade_id]["updated_at"] = datetime.now().isoformat()
            
            await self._save_json(self.brigades_file, brigades)
            return True
        except Exception:
            return False

    async def get_generals(self, player_id: int) -> List[Dict]:
        """Get all generals for a player."""
        generals = await self._load_json(self.generals_file)
        return [general for general in generals.values() if general.get("player_id") == player_id]

    async def create_general(self, player_id: int, name: str, trait_id: int) -> str:
        """Create a new general and return its ID."""
        generals = await self._load_json(self.generals_file)
        
        # Generate unique ID
        general_id = f"general_{len(generals) + 1}_{int(datetime.now().timestamp())}"
        
        generals[general_id] = {
            "id": general_id,
            "player_id": player_id,
            "name": name,
            "level": 1,
            "trait_id": trait_id,
            "location": "Capital",
            "army_id": None,
            "is_captured": False,
            "created_at": datetime.now().isoformat()
        }
        
        await self._save_json(self.generals_file, generals)
        return general_id

    async def get_general(self, general_id: str) -> Optional[Dict]:
        """Get specific general by ID."""
        generals = await self._load_json(self.generals_file)
        return generals.get(general_id)

    async def update_general(self, general_id: str, updates: Dict) -> bool:
        """Update general data."""
        try:
            generals = await self._load_json(self.generals_file)
            
            if general_id not in generals:
                return False
            
            generals[general_id].update(updates)
            generals[general_id]["updated_at"] = datetime.now().isoformat()
            
            await self._save_json(self.generals_file, generals)
            return True
        except Exception:
            return False

    async def create_army(self, player_id: int, general_id: str, brigade_ids: List[str], name: Optional[str] = None) -> str:
        """Create a new army."""
        armies = await self._load_json(self.armies_file)
        
        # Generate unique ID
        army_id = f"army_{len(armies) + 1}_{int(datetime.now().timestamp())}"
        
        if not name:
            general = await self.get_general(general_id)
            name = f"{general['name']}'s Army" if general else f"Army {len(armies) + 1}"
        
        armies[army_id] = {
            "id": army_id,
            "player_id": player_id,
            "general_id": general_id,
            "brigade_ids": brigade_ids,
            "name": name,
            "location": "Capital",
            "movement_orders": None,
            "created_at": datetime.now().isoformat()
        }
        
        # Update general and brigades to reference this army
        await self.update_general(general_id, {"army_id": army_id})
        for brigade_id in brigade_ids:
            await self.update_brigade(brigade_id, {"army_id": army_id})
        
        await self._save_json(self.armies_file, armies)
        return army_id

    async def get_armies(self, player_id: int) -> List[Dict]:
        """Get all armies for a player."""
        armies = await self._load_json(self.armies_file)
        return [army for army in armies.values() if army.get("player_id") == player_id]

    async def create_war(self, attacker_id: int, defender_id: int, justification: str, 
                        victory_conditions: List[str], defeat_conditions: List[str]) -> str:
        """Create a new war."""
        wars = await self._load_json(self.wars_file)
        
        # Generate unique ID
        war_id = f"war_{len(wars) + 1}_{int(datetime.now().timestamp())}"
        
        wars[war_id] = {
            "id": war_id,
            "attacker_id": attacker_id,
            "defender_id": defender_id,
            "justification": justification,
            "status": "active",
            "victory_conditions": victory_conditions,
            "defeat_conditions": defeat_conditions,
            "started_at": datetime.now().isoformat(),
            "ended_at": None
        }
        
        await self._save_json(self.wars_file, wars)
        return war_id

    async def get_active_wars(self, player_id: Optional[int] = None) -> List[Dict]:
        """Get active wars, optionally filtered by player."""
        wars = await self._load_json(self.wars_file)
        active_wars = [war for war in wars.values() if war.get("status") == "active"]
        
        if player_id:
            active_wars = [war for war in active_wars 
                          if war.get("attacker_id") == player_id or war.get("defender_id") == player_id]
        
        return active_wars

    async def create_battle(self, war_id: str, location: str, participants: List[int]) -> str:
        """Create a new battle."""
        battles = await self._load_json(self.battles_file)
        
        # Generate unique ID
        battle_id = f"battle_{len(battles) + 1}_{int(datetime.now().timestamp())}"
        
        battles[battle_id] = {
            "id": battle_id,
            "war_id": war_id,
            "location": location,
            "participants": participants,
            "status": "pending",
            "battle_log": [],
            "winner_id": None,
            "started_at": datetime.now().isoformat(),
            "ended_at": None
        }
        
        await self._save_json(self.battles_file, battles)
        return battle_id

    async def update_battle(self, battle_id: str, updates: Dict) -> bool:
        """Update battle data."""
        try:
            battles = await self._load_json(self.battles_file)
            
            if battle_id not in battles:
                return False
            
            battles[battle_id].update(updates)
            battles[battle_id]["updated_at"] = datetime.now().isoformat()
            
            await self._save_json(self.battles_file, battles)
            return True
        except Exception:
            return False

    async def get_game_state(self) -> Dict:
        """Get current game state."""
        return await self._load_json(self.game_state_file)

    async def update_game_state(self, updates: Dict) -> bool:
        """Update game state."""
        try:
            game_state = await self._load_json(self.game_state_file)
            game_state.update(updates)
            game_state["updated_at"] = datetime.now().isoformat()
            
            await self._save_json(self.game_state_file, game_state)
            return True
        except Exception:
            return False

    async def deduct_resources(self, player_id: int, resource_costs: Dict[str, int]) -> bool:
        """Deduct resources from a player."""
        player = await self.get_player(player_id)
        if not player:
            return False
        
        # Check if player has enough resources
        for resource, cost in resource_costs.items():
            if player.get("resources", {}).get(resource, 0) < cost:
                return False
        
        # Deduct resources
        for resource, cost in resource_costs.items():
            player["resources"][resource] -= cost
        
        return await self.update_player(player_id, {"resources": player["resources"]})

    async def deduct_silver(self, player_id: int, amount: int) -> bool:
        """Deduct silver from a player."""
        player = await self.get_player(player_id)
        if not player or player.get("silver", 0) < amount:
            return False
        
        new_silver = player["silver"] - amount
        return await self.update_player(player_id, {"silver": new_silver})

    async def add_resources(self, player_id: int, resource_gains: Dict[str, int]) -> bool:
        """Add resources to a player."""
        player = await self.get_player(player_id)
        if not player:
            return False
        
        resources = player.get("resources", {})
        for resource, amount in resource_gains.items():
            resources[resource] = resources.get(resource, 0) + amount
        
        return await self.update_player(player_id, {"resources": resources})

    async def backup_data(self, backup_dir: str = "backups") -> str:
        """Create a backup of all data files."""
        import shutil
        
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"backup_{timestamp}")
        
        shutil.copytree(self.data_dir, backup_path)
        return backup_path

    async def get_all_players(self) -> Dict[str, Dict]:
        """Get all players data."""
        return await self._load_json(self.players_file)

    async def get_all_brigades(self) -> Dict[str, Dict]:
        """Get all brigades data."""
        return await self._load_json(self.brigades_file)

    async def get_all_generals(self) -> Dict[str, Dict]:
        """Get all generals data."""
        return await self._load_json(self.generals_file)

    async def get_all_armies(self) -> Dict[str, Dict]:
        """Get all armies data."""
        return await self._load_json(self.armies_file)

    async def get_all_wars(self) -> Dict[str, Dict]:
        """Get all wars data."""
        return await self._load_json(self.wars_file)

    async def get_army(self, army_id: str) -> Optional[Dict]:
        """Get specific army by ID."""
        armies = await self._load_json(self.armies_file)
        return armies.get(army_id)

    async def update_army(self, army_id: str, updates: Dict) -> bool:
        """Update army data."""
        armies = await self._load_json(self.armies_file)
        if army_id in armies:
            armies[army_id].update(updates)
            armies[army_id]['updated_at'] = datetime.now().isoformat()
            await self._save_json(self.armies_file, armies)
            return True
        return False

    async def delete_army(self, army_id: str) -> bool:
        """Delete an army."""
        armies = await self._load_json(self.armies_file)
        if army_id in armies:
            del armies[army_id]
            await self._save_json(self.armies_file, armies)
            return True
        return False

    async def add_resource(self, player_id: int, resource_type: str, amount: int) -> bool:
        """Add a single resource to player."""
        return await self.add_resources(player_id, {resource_type: amount})

    async def export_player_data(self, player_id: int) -> Dict:
        """Export all data for a specific player."""
        player = await self.get_player(player_id)
        brigades = await self.get_brigades(player_id)
        generals = await self.get_generals(player_id)
        armies = await self.get_armies(player_id)
        wars = await self.get_active_wars(player_id)
        
        return {
            "player": player,
            "brigades": brigades,
            "generals": generals,
            "armies": armies,
            "wars": wars,
            "exported_at": datetime.now().isoformat()
        }
