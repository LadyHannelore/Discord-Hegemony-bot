import random
import asyncio
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from models import BrigadeType, BrigadeStats, GENERAL_TRAITS

class BattlePhase(Enum):
    SKIRMISH = "Skirmish"
    PITCH = "Pitch" 
    RALLY = "Rally"
    ACTION_REPORT = "Action Report"

@dataclass
class BattleBrigade:
    id: int
    player_id: int
    type: BrigadeType
    enhancement: Optional[str]
    stats: BrigadeStats
    is_routed: bool = False
    is_destroyed: bool = False

@dataclass
class BattleGeneral:
    id: int
    player_id: int
    name: str
    level: int
    trait_id: int
    is_captured: bool = False

@dataclass
class BattleSide:
    player_id: int
    brigades: List[BattleBrigade]
    general: Optional[BattleGeneral]
    
class BattleSystem:
    def __init__(self):
        self.battle_log = []
    
    def log(self, message: str):
        """Add message to battle log."""
        self.battle_log.append(message)
        print(f"[BATTLE] {message}")
    
    async def conduct_battle(self, side1: BattleSide, side2: BattleSide, location: str, is_holy_war: bool = False) -> dict:
        """Conduct a full battle between two sides."""
        self.battle_log = []
        self.log(f"⚔️ **BATTLE AT {location.upper()}**")
        self.log(f"**{self._get_side_description(side1)}** vs **{self._get_side_description(side2)}**")
        
        # Apply general trait bonuses to all brigades
        self._apply_general_trait_bonuses(side1, is_holy_war)
        self._apply_general_trait_bonuses(side2, is_holy_war)
        
        # Determine positive/negative sides (random)
        if random.choice([True, False]):
            positive_side, negative_side = side1, side2
        else:
            positive_side, negative_side = side2, side1
        
        self.log(f"**Positive Side**: Player {positive_side.player_id}")
        self.log(f"**Negative Side**: Player {negative_side.player_id}")
        
        # Battle phases
        battle_result = await self._conduct_skirmish(positive_side, negative_side)
        if not battle_result['battle_continues']:
            return battle_result
        
        battle_result = await self._conduct_pitch_rally_cycle(positive_side, negative_side)
        
        # Action Report
        await self._conduct_action_report(battle_result['winner'], battle_result['loser'])
        
        battle_result['battle_log'] = self.battle_log
        return battle_result
    
    def _get_side_description(self, side: BattleSide) -> str:
        """Get description of a battle side."""
        brigade_count = len([b for b in side.brigades if not b.is_destroyed])
        general_name = side.general.name if side.general else "No General"
        return f"Player {side.player_id} ({brigade_count} brigades, Gen: {general_name})"
    
    async def _conduct_skirmish(self, positive_side: BattleSide, negative_side: BattleSide) -> dict:
        """Conduct the skirmish phase."""
        self.log("\n🗡️ **SKIRMISH PHASE**")
        
        # Check for Cautious trait - may skip skirmish
        pos_general = positive_side.general
        neg_general = negative_side.general
        
        if pos_general:
            trait_name, _ = GENERAL_TRAITS[pos_general.trait_id]
            if trait_name == "Cautious":
                self.log("Positive side general is Cautious - may skip skirmishing")
                # In a real implementation, this would prompt the player
                # For now, randomly decide
                if random.choice([True, False]):
                    self.log("Positive side chooses to skip skirmishing!")
                    return {'battle_continues': True}
        
        if neg_general:
            trait_name, _ = GENERAL_TRAITS[neg_general.trait_id]
            if trait_name == "Cautious":
                self.log("Negative side general is Cautious - may skip skirmishing")
                if random.choice([True, False]):
                    self.log("Negative side chooses to skip skirmishing!")
                    return {'battle_continues': True}
        
        # Each side selects 2 best skirmishers
        pos_skirmishers = self._select_skirmishers(positive_side)
        neg_skirmishers = self._select_skirmishers(negative_side)
        
        self.log(f"Positive skirmishers: {[f'#{b.id} {b.type.value}' for b in pos_skirmishers]}")
        self.log(f"Negative skirmishers: {[f'#{b.id} {b.type.value}' for b in neg_skirmishers]}")
        
        # Apply Bold trait bonus to one skirmisher
        self._apply_bold_trait_bonus(pos_skirmishers, positive_side.general)
        self._apply_bold_trait_bonus(neg_skirmishers, negative_side.general)
        
        # Conduct skirmish attacks
        await self._resolve_skirmish_attacks(pos_skirmishers, negative_side)
        await self._resolve_skirmish_attacks(neg_skirmishers, positive_side)
        
        return {'battle_continues': True}
    
    def _select_skirmishers(self, side: BattleSide) -> List[BattleBrigade]:
        """Select the 2 best skirmishers from a side."""
        available = [b for b in side.brigades if not b.is_destroyed and not b.is_routed]
        # Sort by skirmish value, take top 2
        available.sort(key=lambda b: b.stats.skirmish, reverse=True)
        return available[:2]
    
    async def _resolve_skirmish_attacks(self, skirmishers: List[BattleBrigade], defending_side: BattleSide):
        """Resolve skirmish attacks against defending side."""
        available_targets = [b for b in defending_side.brigades if not b.is_destroyed]
        
        for skirmisher in skirmishers:
            if not available_targets:
                break
                
            # Random target selection
            target = random.choice(available_targets)
            
            # Roll skirmish vs defense
            skirmish_roll = random.randint(1, 6) + skirmisher.stats.skirmish
            defense_roll = random.randint(1, 6) + target.stats.defense
            
            self.log(f"#{skirmisher.id} attacks #{target.id}: {skirmish_roll} vs {defense_roll}")
            
            if skirmish_roll > defense_roll:
                target.is_routed = True
                self.log(f"💥 #{target.id} is routed!")
                
                # Check for overrun (3+ difference)
                if skirmish_roll >= defense_roll + 3:
                    self.log(f"⚡ OVERRUN! #{target.id} must roll destruction die")
                    if random.randint(1, 6) <= 2:
                        target.is_destroyed = True
                        self.log(f"💀 #{target.id} is destroyed!")
            else:
                self.log(f"🛡️ #{target.id} holds firm")
    
    async def _conduct_pitch_rally_cycle(self, positive_side: BattleSide, negative_side: BattleSide) -> dict:
        """Conduct pitch and rally phases until battle ends."""
        pitch_tally = 0
        rally_count = 0
        max_rallies = 5
        
        while rally_count < max_rallies:
            self.log(f"\n📯 **PITCH PHASE - Round {rally_count + 1}**")
            
            # Conduct 3 rounds of pitch
            for round_num in range(1, 4):
                pitch_result = await self._conduct_pitch_round(positive_side, negative_side, round_num)
                pitch_tally += pitch_result
                self.log(f"Round {round_num} result: {pitch_result:+d} (Tally: {pitch_tally:+d})")
            
            # Check for decisive victory
            if pitch_tally >= 20:
                self.log(f"🏆 **DECISIVE VICTORY FOR POSITIVE SIDE!** (Tally: {pitch_tally:+d})")
                return {'winner': positive_side, 'loser': negative_side, 'type': 'decisive'}
            elif pitch_tally <= -20:
                self.log(f"🏆 **DECISIVE VICTORY FOR NEGATIVE SIDE!** (Tally: {pitch_tally:+d})")
                return {'winner': negative_side, 'loser': positive_side, 'type': 'decisive'}
            
            # Rally phase
            self.log(f"\n🚩 **RALLY PHASE - Round {rally_count + 1}**")
            
            pos_survivors = await self._conduct_rally(positive_side)
            neg_survivors = await self._conduct_rally(negative_side)
            
            # Check for victory by routing
            if pos_survivors == 0:
                # Check for Heroic sacrifice before declaring defeat
                if positive_side.general and not positive_side.general.is_captured:
                    trait_name, _ = GENERAL_TRAITS[positive_side.general.trait_id]
                    if trait_name == "Heroic":
                        self.log("🔥 HEROIC SACRIFICE! General sacrifices himself for new pitch!")
                        positive_side.general.is_captured = True  # General dies
                        
                        # Return all brigades to new pitch with general level bonus
                        for brigade in positive_side.brigades:
                            if brigade.is_routed:
                                brigade.is_routed = False
                                brigade.stats.pitch += positive_side.general.level
                        
                        self.log(f"All brigades return with +{positive_side.general.level} pitch bonus!")
                        rally_count += 1
                        pitch_tally = 0  # Reset for heroic charge
                        continue
                
                self.log("🏆 **NEGATIVE SIDE WINS BY ROUTING ALL ENEMIES!**")
                return {'winner': negative_side, 'loser': positive_side, 'type': 'rout'}
            elif neg_survivors == 0:
                # Check for Heroic sacrifice
                if negative_side.general and not negative_side.general.is_captured:
                    trait_name, _ = GENERAL_TRAITS[negative_side.general.trait_id]
                    if trait_name == "Heroic":
                        self.log("🔥 HEROIC SACRIFICE! General sacrifices himself for new pitch!")
                        negative_side.general.is_captured = True
                        
                        for brigade in negative_side.brigades:
                            if brigade.is_routed:
                                brigade.is_routed = False
                                brigade.stats.pitch += negative_side.general.level
                        
                        self.log(f"All brigades return with +{negative_side.general.level} pitch bonus!")
                        rally_count += 1
                        pitch_tally = 0
                        continue
                
                self.log("🏆 **POSITIVE SIDE WINS BY ROUTING ALL ENEMIES!**")
                return {'winner': positive_side, 'loser': negative_side, 'type': 'rout'}
            
            rally_count += 1
            pitch_tally = 0  # Reset for next cycle
        
        # Stalemate after 5 rallies
        self.log("🤝 **STALEMATE!** Both sides withdraw")
        return {'winner': None, 'loser': None, 'type': 'stalemate'}
    
    async def _conduct_pitch_round(self, positive_side: BattleSide, negative_side: BattleSide, round_num: int) -> int:
        """Conduct a single round of pitch combat."""
        
        # Get fighting brigades (not routed or destroyed)
        pos_fighters = [b for b in positive_side.brigades if not b.is_destroyed and not b.is_routed]
        neg_fighters = [b for b in negative_side.brigades if not b.is_destroyed and not b.is_routed]
        
        # Restore routed brigades for initial rally
        if round_num == 1:
            for brigade in positive_side.brigades + negative_side.brigades:
                if brigade.is_routed and not brigade.is_destroyed:
                    brigade.is_routed = False
        
        # Calculate pitch values
        pos_pitch = self._calculate_pitch_value(pos_fighters, positive_side.general)
        neg_pitch = self._calculate_pitch_value(neg_fighters, negative_side.general)
        
        self.log(f"Positive pitch: {pos_pitch}, Negative pitch: {neg_pitch}")
        
        return pos_pitch - neg_pitch
    
    def _apply_bold_trait_bonus(self, skirmishers: List[BattleBrigade], general: Optional[BattleGeneral]):
        """Apply Bold trait bonus to one skirmisher."""
        if not general:
            return
        
        trait_name, _ = GENERAL_TRAITS[general.trait_id]
        if trait_name == "Bold" and skirmishers:
            # Apply bonus to best skirmisher
            best_skirmisher = max(skirmishers, key=lambda b: b.stats.skirmish)
            bonus = (general.level + 1) // 2  # Half general level rounded up
            best_skirmisher.stats.skirmish += bonus
            self.log(f"Bold general grants +{bonus} skirmish to #{best_skirmisher.id}")
    
    def _apply_general_trait_bonuses(self, side: BattleSide, is_holy_war: bool = False):
        """Apply general trait bonuses to all brigades in army."""
        if not side.general:
            return
        
        trait_name, _ = GENERAL_TRAITS[side.general.trait_id]
        
        for brigade in side.brigades:
            if brigade.is_destroyed:
                continue
            
            # Apply stat bonuses based on trait
            if trait_name == "Confident":
                brigade.stats.defense += 2
                brigade.stats.rally += 1
            elif trait_name == "Defiant":
                brigade.stats.rally += 2
            elif trait_name == "Disciplined":
                brigade.stats.pitch += 1
                brigade.stats.rally += 1
            elif trait_name == "Heroic":
                brigade.stats.rally += 1
            elif trait_name == "Resolute":
                brigade.stats.defense += 3
            elif trait_name == "Zealous":
                if is_holy_war:
                    brigade.stats.rally += 2
                    brigade.stats.pitch += 1
                else:
                    brigade.stats.rally += 1
        
        self.log(f"Applied {trait_name} trait bonuses to army")
    
    def _calculate_pitch_value(self, brigades: List[BattleBrigade], general: Optional[BattleGeneral]) -> int:
        """Calculate total pitch value for a side."""
        total = 0
        
        # Brigade dice and bonuses
        for brigade in brigades:
            roll = random.randint(1, 6)
            total += roll + brigade.stats.pitch
        
        # General level bonus
        if general:
            general_bonus = general.level
            
            # Apply general trait bonuses
            trait_name, _ = GENERAL_TRAITS[general.trait_id]
            if trait_name == "Brilliant":
                general_bonus *= 2  # Double general level for pitch
                self.log(f"Brilliant general: {general_bonus} pitch bonus (doubled)")
            elif trait_name == "Prodigious":
                general_bonus += 2  # Additional 2 levels
                self.log(f"Prodigious general: +2 bonus levels")
            
            total += general_bonus
        
        return total
    
    async def _conduct_rally(self, side: BattleSide) -> int:
        """Conduct rally phase for a side, return number of survivors."""
        survivors = 0
        
        for brigade in side.brigades:
            if brigade.is_destroyed:
                continue
            
            rally_roll = random.randint(1, 6) + brigade.stats.rally
            
            # Apply general trait bonuses
            if side.general:
                trait_name, _ = GENERAL_TRAITS[side.general.trait_id]
                
                # Free reroll for Inspiring trait
                if trait_name == "Inspiring":
                    original_roll = rally_roll
                    reroll = random.randint(1, 6) + brigade.stats.rally
                    if reroll > rally_roll:
                        rally_roll = reroll
                        self.log(f"Inspiring general: #{brigade.id} rerolled {original_roll} → {rally_roll}")
                
                # Apply celebration bonus for Inspiring
                if hasattr(brigade, 'celebration_bonus') and trait_name == "Inspiring":
                    rally_roll += 1  # Extra +1 for Inspiring celebration
            
            if rally_roll >= 5:
                brigade.is_routed = False
                survivors += 1
                self.log(f"✅ #{brigade.id} rallies ({rally_roll})")
            else:
                brigade.is_routed = True
                self.log(f"❌ #{brigade.id} routs ({rally_roll})")
        
        return survivors
    
    async def _conduct_action_report(self, winner: Optional[BattleSide], loser: Optional[BattleSide]):
        """Conduct action report phase with casualty and promotion rolls."""
        self.log("\n📋 **ACTION REPORT**")
        
        # All brigades roll destruction dice
        for side in [winner, loser]:
            if side is None:
                continue
                
            self.log(f"\n**Player {side.player_id} Casualties:**")
            
            for brigade in side.brigades:
                if brigade.is_destroyed:
                    continue
                
                casualty_roll = random.randint(1, 6)
                
                # Check for enemy Merciless trait
                enemy_side = loser if side == winner else winner
                if enemy_side and enemy_side.general:
                    enemy_trait_name, _ = GENERAL_TRAITS[enemy_side.general.trait_id]
                    if enemy_trait_name == "Merciless" and side != winner:
                        # Enemy brigades destroyed on 1-3 instead of 1-2
                        destruction_threshold = 3
                    else:
                        destruction_threshold = 2
                else:
                    destruction_threshold = 2
                
                # Winner gets reroll
                if side == winner:
                    if casualty_roll <= destruction_threshold:
                        reroll = random.randint(1, 6)
                        self.log(f"#{brigade.id} casualty roll: {casualty_roll} → {reroll} (reroll)")
                        casualty_roll = reroll
                    else:
                        self.log(f"#{brigade.id} casualty roll: {casualty_roll}")
                else:
                    self.log(f"#{brigade.id} casualty roll: {casualty_roll}")
                
                if casualty_roll <= destruction_threshold:
                    brigade.is_destroyed = True
                    self.log(f"💀 #{brigade.id} is destroyed!")
            
            # General promotion/capture rolls
            if side.general:
                general = side.general
                promotion_roll = random.randint(1, 6)
                
                # Apply trait effects
                trait_name, _ = GENERAL_TRAITS[general.trait_id]
                promotion_threshold = 5
                
                if trait_name == "Ambitious":
                    promotion_threshold = 4  # -1 to promotion number needed
                elif trait_name == "Lucky" and promotion_roll == 1:
                    # Reroll once on a 1
                    reroll = random.randint(1, 6)
                    self.log(f"Lucky general rerolls promotion: {promotion_roll} → {reroll}")
                    promotion_roll = reroll
                
                # Check for Officer Corps enhancement effect
                for brigade in side.brigades:
                    if hasattr(brigade, 'enhancement') and brigade.enhancement == "Officer Corps":
                        promotion_threshold = 4  # Needs 4-6 instead of 5-6
                        break
                
                # Winner gets reroll
                if side == winner and promotion_roll == 1:
                    reroll = random.randint(1, 6)
                    self.log(f"General {general.name} promotion roll: {promotion_roll} → {reroll} (reroll)")
                    promotion_roll = reroll
                else:
                    self.log(f"General {general.name} promotion roll: {promotion_roll}")
                
                if promotion_roll == 1:
                    general.is_captured = True
                    self.log(f"🔒 General {general.name} is captured!")
                elif promotion_roll >= promotion_threshold:
                    general.level += 1
                    self.log(f"⭐ General {general.name} promoted to level {general.level}!")
                    
                    # Check for Life Guard enhancement effect
                    for brigade in side.brigades:
                        if hasattr(brigade, 'enhancement') and brigade.enhancement == "Life Guard":
                            self.log(f"Life Guard allows reroll of promotion roll once per battle")
                            break

# Factory functions for creating battle participants
def create_battle_brigade(brigade_data: dict, stats: BrigadeStats) -> BattleBrigade:
    """Create a BattleBrigade from database data."""
    brigade_type = next(bt for bt in BrigadeType if bt.value == brigade_data['type'])
    
    return BattleBrigade(
        id=brigade_data['id'],
        player_id=brigade_data['player_id'], 
        type=brigade_type,
        enhancement=brigade_data.get('enhancement'),
        stats=stats
    )

def create_battle_general(general_data: dict) -> BattleGeneral:
    """Create a BattleGeneral from database data."""
    return BattleGeneral(
        id=general_data['id'],
        player_id=general_data['player_id'],
        name=general_data['name'],
        level=general_data['level'],
        trait_id=general_data['trait_id']
    )
