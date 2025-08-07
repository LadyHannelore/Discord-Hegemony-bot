#!/usr/bin/env python3
"""
Data viewer for Discord Hegemony Bot JSON files
Provides easy inspection of game data
"""

import json
import os
from datetime import datetime
from typing import Dict, Any

class DataViewer:
    def __init__(self, data_dir: str = "bot_data"):
        self.data_dir = data_dir
        
    def load_json_file(self, filename: str) -> Dict[str, Any]:
        """Load a JSON file and return its contents."""
        filepath = os.path.join(self.data_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error reading {filename}: {e}")
            return {}
    
    def display_players(self):
        """Display all players and their stats."""
        players = self.load_json_file("players.json")
        
        print("=" * 60)
        print("PLAYERS")
        print("=" * 60)
        
        if not players:
            print("No players found.")
            return
        
        for user_id, player in players.items():
            print(f"\nPlayer: {player['username']} (ID: {user_id})")
            print(f"  War College Level: {player.get('war_college_level', 1)}")
            print(f"  Brigade Cap: {player.get('brigade_cap', 2)}")
            print(f"  General Cap: {player.get('general_cap', 1)}")
            print(f"  Silver: {player.get('silver', 0)}")
            
            resources = player.get('resources', {})
            if resources:
                resource_str = ", ".join([f"{k}: {v}" for k, v in resources.items()])
                print(f"  Resources: {resource_str}")
            
            cities = player.get('cities', [])
            print(f"  Cities: {len(cities)}")
            
            if player.get('created_at'):
                print(f"  Joined: {player['created_at']}")
    
    def display_brigades(self):
        """Display all brigades."""
        brigades = self.load_json_file("brigades.json")
        players = self.load_json_file("players.json")
        
        print("=" * 60)
        print("BRIGADES")
        print("=" * 60)
        
        if not brigades:
            print("No brigades found.")
            return
        
        # Group by player
        by_player = {}
        for brigade_id, brigade in brigades.items():
            player_id = str(brigade['player_id'])
            if player_id not in by_player:
                by_player[player_id] = []
            by_player[player_id].append((brigade_id, brigade))
        
        for player_id, player_brigades in by_player.items():
            player_name = players.get(player_id, {}).get('username', f'Unknown ({player_id})')
            print(f"\n{player_name}'s Brigades:")
            
            for brigade_id, brigade in player_brigades:
                enhancement = f" ({brigade['enhancement']})" if brigade['enhancement'] else ""
                status = []
                if brigade.get('is_garrisoned'):
                    status.append("Garrisoned")
                if brigade.get('is_fatigued'):
                    status.append("Fatigued")
                if brigade.get('army_id'):
                    status.append(f"Army: {brigade['army_id']}")
                
                status_str = f" [{', '.join(status)}]" if status else ""
                print(f"  {brigade_id}: {brigade['type']}{enhancement} @ {brigade['location']}{status_str}")
    
    def display_generals(self):
        """Display all generals."""
        generals = self.load_json_file("generals.json")
        players = self.load_json_file("players.json")
        
        print("=" * 60)
        print("GENERALS")
        print("=" * 60)
        
        if not generals:
            print("No generals found.")
            return
        
        # Import trait names for display
        try:
            from models import GENERAL_TRAITS
        except ImportError:
            GENERAL_TRAITS = {}
        
        # Group by player
        by_player = {}
        for general_id, general in generals.items():
            player_id = str(general['player_id'])
            if player_id not in by_player:
                by_player[player_id] = []
            by_player[player_id].append((general_id, general))
        
        for player_id, player_generals in by_player.items():
            player_name = players.get(player_id, {}).get('username', f'Unknown ({player_id})')
            print(f"\n{player_name}'s Generals:")
            
            for general_id, general in player_generals:
                trait_id = general.get('trait_id', 1)
                trait_name = GENERAL_TRAITS.get(trait_id, ("Unknown", ""))[0] if GENERAL_TRAITS else "Unknown"
                
                status = []
                if general.get('is_captured'):
                    status.append("Captured")
                if general.get('army_id'):
                    status.append(f"Army: {general['army_id']}")
                
                status_str = f" [{', '.join(status)}]" if status else ""
                print(f"  {general_id}: {general['name']} (Level {general['level']}, {trait_name}){status_str}")
    
    def display_armies(self):
        """Display all armies."""
        armies = self.load_json_file("armies.json")
        players = self.load_json_file("players.json")
        
        print("=" * 60)
        print("ARMIES")
        print("=" * 60)
        
        if not armies:
            print("No armies found.")
            return
        
        # Group by player
        by_player = {}
        for army_id, army in armies.items():
            player_id = str(army['player_id'])
            if player_id not in by_player:
                by_player[player_id] = []
            by_player[player_id].append((army_id, army))
        
        for player_id, player_armies in by_player.items():
            player_name = players.get(player_id, {}).get('username', f'Unknown ({player_id})')
            print(f"\n{player_name}'s Armies:")
            
            for army_id, army in player_armies:
                brigade_count = len(army.get('brigade_ids', []))
                print(f"  {army_id}: {army['name']} ({brigade_count} brigades)")
                print(f"    General: {army.get('general_id', 'None')}")
                print(f"    Location: {army.get('location', 'Unknown')}")
                
                if army.get('brigade_ids'):
                    print(f"    Brigades: {', '.join(army['brigade_ids'])}")
    
    def display_wars(self):
        """Display all wars."""
        wars = self.load_json_file("wars.json")
        players = self.load_json_file("players.json")
        
        print("=" * 60)
        print("WARS")
        print("=" * 60)
        
        if not wars:
            print("No wars found.")
            return
        
        for war_id, war in wars.items():
            attacker_name = players.get(str(war['attacker_id']), {}).get('username', f"Player {war['attacker_id']}")
            defender_name = players.get(str(war['defender_id']), {}).get('username', f"Player {war['defender_id']}")
            
            print(f"\nWar {war_id}: {attacker_name} vs {defender_name}")
            print(f"  Justification: {war['justification']}")
            print(f"  Status: {war['status']}")
            print(f"  Started: {war.get('started_at', 'Unknown')}")
            
            if war.get('ended_at'):
                print(f"  Ended: {war['ended_at']}")
    
    def display_game_state(self):
        """Display current game state."""
        game_state = self.load_json_file("game_state.json")
        
        print("=" * 60)
        print("GAME STATE")
        print("=" * 60)
        
        if not game_state:
            print("No game state found.")
            return
        
        print(f"Current Phase: {game_state.get('current_phase', 'Unknown')}")
        print(f"Cycle Start: {game_state.get('cycle_start_date', 'Unknown')}")
        print(f"Last Updated: {game_state.get('updated_at', 'Unknown')}")
        
        if game_state.get('phase_end_time'):
            print(f"Phase Ends: {game_state['phase_end_time']}")
    
    def display_summary(self):
        """Display a summary of all data."""
        players = self.load_json_file("players.json")
        brigades = self.load_json_file("brigades.json")
        generals = self.load_json_file("generals.json")
        armies = self.load_json_file("armies.json")
        wars = self.load_json_file("wars.json")
        
        print("=" * 60)
        print("GAME SUMMARY")
        print("=" * 60)
        
        print(f"Players: {len(players)}")
        print(f"Brigades: {len(brigades)}")
        print(f"Generals: {len(generals)}")
        print(f"Armies: {len(armies)}")
        print(f"Wars: {len(wars)}")
        
        # Active wars
        active_wars = [w for w in wars.values() if w.get('status') == 'active']
        print(f"Active Wars: {len(active_wars)}")
        
        # Brigade type breakdown
        brigade_types = {}
        for brigade in brigades.values():
            btype = brigade.get('type', 'Unknown')
            brigade_types[btype] = brigade_types.get(btype, 0) + 1
        
        if brigade_types:
            print("\nBrigade Types:")
            for btype, count in sorted(brigade_types.items()):
                print(f"  {btype}: {count}")
        
        # War college levels
        wc_levels = {}
        for player in players.values():
            level = player.get('war_college_level', 1)
            wc_levels[level] = wc_levels.get(level, 0) + 1
        
        if wc_levels:
            print("\nWar College Levels:")
            for level, count in sorted(wc_levels.items()):
                print(f"  Level {level}: {count} players")

def main():
    """Main function with interactive menu."""
    viewer = DataViewer()
    
    # Check if data directory exists
    if not os.path.exists(viewer.data_dir):
        print(f"Data directory '{viewer.data_dir}' not found.")
        print("Make sure the bot has been run at least once to create data files.")
        return
    
    while True:
        print("\n" + "=" * 60)
        print("DISCORD HEGEMONY BOT - DATA VIEWER")
        print("=" * 60)
        print("1. Summary")
        print("2. Players")
        print("3. Brigades")
        print("4. Generals")
        print("5. Armies")
        print("6. Wars")
        print("7. Game State")
        print("8. Exit")
        
        choice = input("\nSelect option (1-8): ").strip()
        
        if choice == '1':
            viewer.display_summary()
        elif choice == '2':
            viewer.display_players()
        elif choice == '3':
            viewer.display_brigades()
        elif choice == '4':
            viewer.display_generals()
        elif choice == '5':
            viewer.display_armies()
        elif choice == '6':
            viewer.display_wars()
        elif choice == '7':
            viewer.display_game_state()
        elif choice == '8':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please select 1-8.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
