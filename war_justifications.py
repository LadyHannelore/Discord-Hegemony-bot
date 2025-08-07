from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

@dataclass
class WarJustification:
    name: str
    requirements: List[str]
    victory_conditions: List[str]
    victory_peace_terms: List[str]
    defeat_conditions: List[str]
    defeat_peace_terms: List[str]
    special_conditions: List[str]
    tile_cost: int = 0  # Number of tiles can be taken

# War Justifications Database
WAR_JUSTIFICATIONS = {
    "Border Dispute": WarJustification(
        name="Border Dispute",
        requirements=[
            "Must share a border with target",
            "No active Non-Aggression Pact"
        ],
        victory_conditions=[
            "Occupy 1 enemy city for 2 action cycles",
            "Enemy must have less than 3 brigades"
        ],
        victory_peace_terms=[
            "Take up to 3 border tiles",
            "1 week Non-Aggression Pact"
        ],
        defeat_conditions=[
            "Lose all your border cities",
            "Have no brigades for 1 action cycle"
        ],
        defeat_peace_terms=[
            "Give up 2 border tiles",
            "Pay 100 silver"
        ],
        special_conditions=[
            "Cannot target players with less than 3 cities"
        ],
        tile_cost=3
    ),
    
    "Trade War": WarJustification(
        name="Trade War",
        requirements=[
            "Target must have a trade port",
            "You must have a trade port",
            "No trade agreement with target"
        ],
        victory_conditions=[
            "Destroy or occupy target's trade port",
            "Control sea routes for 2 cycles"
        ],
        victory_peace_terms=[
            "Exclusive trade rights for 4 weeks",
            "Take 2 coastal tiles",
            "Gain 200 silver"
        ],
        defeat_conditions=[
            "Lose your trade port",
            "No naval presence for 2 cycles"
        ],
        defeat_peace_terms=[
            "Pay 300 silver",
            "Grant trade concessions"
        ],
        special_conditions=[
            "Both players must have coastal access"
        ],
        tile_cost=2
    ),
    
    "Religious War": WarJustification(
        name="Religious War",
        requirements=[
            "Must have different state religions",
            "Target must have religious building",
            "You must have Level 2+ War College"
        ],
        victory_conditions=[
            "Destroy 2 enemy religious buildings",
            "Occupy their capital for 3 cycles"
        ],
        victory_peace_terms=[
            "Convert 1 enemy city to your religion",
            "Take up to 4 tiles",
            "Enemy pays 200 silver"
        ],
        defeat_conditions=[
            "Lose your capital",
            "All your religious buildings destroyed"
        ],
        defeat_peace_terms=[
            "Convert 1 of your cities to enemy religion",
            "Give up 3 tiles",
            "Pay 150 silver"
        ],
        special_conditions=[
            "Zealous generals get +1 Pitch and +2 Rally",
            "Religious buildings provide +1 defense when garrisoned"
        ],
        tile_cost=4
    ),
    
    "Conquest": WarJustification(
        name="Conquest", 
        requirements=[
            "Must have Level 3+ War College",
            "Target must have fewer cities than you",
            "You must have 5+ brigades"
        ],
        victory_conditions=[
            "Occupy 50% of enemy cities",
            "Destroy 75% of enemy brigades"
        ],
        victory_peace_terms=[
            "Take up to 6 tiles",
            "Gain 1 enemy city permanently",
            "Enemy pays 400 silver"
        ],
        defeat_conditions=[
            "Lose 50% of your cities",
            "Lose 75% of your brigades"
        ],
        defeat_peace_terms=[
            "Give up 4 tiles",
            "Pay 300 silver",
            "2 week Non-Aggression Pact"
        ],
        special_conditions=[
            "Cannot target players with only 1 city",
            "War lasts minimum 3 full cycles"
        ],
        tile_cost=6
    ),
    
    "Liberation": WarJustification(
        name="Liberation",
        requirements=[
            "Target must have recently conquered territory",
            "You must share culture/religion with conquered territory",
            "Conquered territory must be within 2 tiles of your border"
        ],
        victory_conditions=[
            "Occupy the recently conquered territory",
            "Hold it for 2 action cycles"
        ],
        victory_peace_terms=[
            "Gain the liberated territory",
            "Take 2 additional border tiles"
        ],
        defeat_conditions=[
            "Unable to reach the territory for 3 cycles",
            "Lose 2 border cities"
        ],
        defeat_peace_terms=[
            "Give up 2 border tiles",
            "Pay 150 silver",
            "Recognize enemy's territorial claims"
        ],
        special_conditions=[
            "Territory must have been conquered within last 4 weeks",
            "Can only be used once per conquered territory"
        ],
        tile_cost=2
    ),
    
    "Punitive Expedition": WarJustification(
        name="Punitive Expedition",
        requirements=[
            "Target must have recently attacked your allies",
            "Or target must have broken a treaty with you",
            "You must have Level 2+ War College"
        ],
        victory_conditions=[
            "Sack 1 enemy city",
            "Destroy 3 enemy brigades"
        ],
        victory_peace_terms=[
            "Take 300 silver",
            "Take 3 tiles",
            "Enemy apologizes publicly"
        ],
        defeat_conditions=[
            "Fail to sack any cities within 4 cycles",
            "Lose more brigades than enemy"
        ],
        defeat_peace_terms=[
            "Pay 200 silver",
            "Public apology to target"
        ],
        special_conditions=[
            "War automatically ends after 6 cycles",
            "Cannot escalate to full conquest"
        ],
        tile_cost=3
    ),
    
    "Succession Crisis": WarJustification(
        name="Succession Crisis",
        requirements=[
            "Target ruler must have died recently (within 1 week)",
            "You must have dynastic claim",
            "No clear heir established"
        ],
        victory_conditions=[
            "Occupy target's capital",
            "Eliminate all other claimants"
        ],
        victory_peace_terms=[
            "Gain full control of enemy nation",
            "All cities and resources transfer"
        ],
        defeat_conditions=[
            "Enemy establishes clear succession",
            "You lose your capital"
        ],
        defeat_peace_terms=[
            "Renounce all claims",
            "Pay 500 silver",
            "4 week Non-Aggression Pact"
        ],
        special_conditions=[
            "Extremely rare justification",
            "Requires moderator approval",
            "Only available in specific RP scenarios"
        ],
        tile_cost=0  # Special case - all or nothing
    ),
    
    "Holy War": WarJustification(
        name="Holy War",
        requirements=[
            "Must have state religion",
            "Target must be 'heretical' or 'heathen'",
            "Religious authority must declare holy war",
            "You must have Level 3+ War College"
        ],
        victory_conditions=[
            "Convert or destroy all enemy religious buildings",
            "Occupy enemy capital for 4 cycles"
        ],
        victory_peace_terms=[
            "Convert enemy to your religion",
            "Take up to 5 tiles",
            "Gain 300 silver",
            "Build religious building in enemy territory"
        ],
        defeat_conditions=[
            "Lose all religious buildings",
            "Enemy converts one of your cities"
        ],
        defeat_peace_terms=[
            "Convert to enemy religion",
            "Give up 4 tiles",
            "Pay 400 silver",
            "Allow enemy religious building in your territory"
        ],
        special_conditions=[
            "All brigades with Zealous generals get bonuses",
            "Religious buildings provide defensive bonuses",
            "Other nations of your religion may send aid"
        ],
        tile_cost=5
    )
}

def get_available_justifications(attacker_data: dict, target_data: dict) -> List[WarJustification]:
    """Get list of valid war justifications for attacker against target."""
    available = []
    
    # This would check the actual requirements against player data
    # For now, return a subset based on basic criteria
    
    basic_justifications = ["Border Dispute", "Punitive Expedition"]
    
    # Add advanced justifications based on war college level
    if attacker_data.get('war_college_level', 1) >= 2:
        basic_justifications.extend(["Trade War", "Religious War"])
    
    if attacker_data.get('war_college_level', 1) >= 3:
        basic_justifications.extend(["Conquest", "Holy War"])
    
    # Add contextual justifications
    # This would check for recent conquests, broken treaties, etc.
    # For now, always include Liberation as an option
    basic_justifications.append("Liberation")
    
    return [WAR_JUSTIFICATIONS[name] for name in basic_justifications if name in WAR_JUSTIFICATIONS]

def validate_justification(justification_name: str, attacker_data: dict, target_data: dict) -> tuple[bool, str]:
    """Validate if a war justification can be used."""
    if justification_name not in WAR_JUSTIFICATIONS:
        return False, "Invalid justification"
    
    justification = WAR_JUSTIFICATIONS[justification_name]
    
    # Check basic requirements
    if justification_name == "Conquest":
        if attacker_data.get('war_college_level', 1) < 3:
            return False, "Requires War College Level 3+"
        
        attacker_cities = len(attacker_data.get('cities', []))
        target_cities = len(target_data.get('cities', []))
        
        if target_cities >= attacker_cities:
            return False, "Target must have fewer cities than you"
    
    elif justification_name == "Trade War":
        # Check for trade ports (simplified)
        if not attacker_data.get('has_trade_port', False):
            return False, "You must have a trade port"
        if not target_data.get('has_trade_port', False):
            return False, "Target must have a trade port"
    
    elif justification_name == "Religious War":
        if attacker_data.get('war_college_level', 1) < 2:
            return False, "Requires War College Level 2+"
    
    return True, "Valid justification"

def calculate_city_tile_cost(city_tier: int) -> int:
    """Calculate tile cost for taking a city based on tier."""
    cost_map = {1: 2, 2: 3, 3: 4}
    return cost_map.get(city_tier, 2)
