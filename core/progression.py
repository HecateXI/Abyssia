"""Dynamic progression system that guides players through the game."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProgressionStage:
    """A stage in the player progression guide."""
    key: str
    title: str
    goal: str
    steps: tuple[tuple[str, str], ...]  # (step_name, check_description)
    next_command: str
    reward_souls: int
    reward_gems: int


PROGRESSION_STAGES = (
    ProgressionStage(
        key="start",
        title="First Steps into the Void",
        goal="Learn the hunt",
        steps=(
            ("Start hunting", "Use b hunt to begin your first hunt"),
            ("Catch your first creature", "Successfully catch a creature in a hunt"),
            ("Visit your collection", "Use b collection to see your caught creatures"),
        ),
        next_command="b hunt",
        reward_souls=50,
        reward_gems=5,
    ),
    ProgressionStage(
        key="collect",
        title="Build Your Collection",
        goal="Catch 10 monsters",
        steps=(
            ("Hunt 5 times", "Complete 5 hunts with b hunt"),
            ("Catch 10 creatures", "Successfully catch 10 creatures"),
            ("Check rarity", "Look for Uncommon or Rare creatures"),
        ),
        next_command="b hunt",
        reward_souls=150,
        reward_gems=10,
    ),
    ProgressionStage(
        key="currency",
        title="Master the Economy",
        goal="Earn your first souls",
        steps=(
            ("Sell duplicates", "Use b sellall to sell duplicate creatures"),
            ("Open a cache", "Use b shardcrate cache to buy and open a Void Cache with Weapon Shards"),
            ("Earn 1000 gold", "Accumulate 1000 gold from hunts"),
        ),
        next_command="b sellall",
        reward_souls=100,
        reward_gems=8,
    ),
    ProgressionStage(
        key="weapons",
        title="Forge Your Arsenal",
        goal="Equip your first weapon",
        steps=(
            ("Open 3 caches", "Use b shardcrate cache or open owned Void Caches 3 times"),
            ("Find a weapon", "Get a weapon from a cache"),
            ("Equip to creature", "Use b weaponequip to equip a weapon to a creature"),
        ),
        next_command="b weapons",
        reward_souls=200,
        reward_gems=15,
    ),
    ProgressionStage(
        key="team",
        title="Assemble Your War Band",
        goal="Build your battle team",
        steps=(
            ("Have 3 strong creatures", "Catch or evolve 3 creatures"),
            ("Create your team", "Use b team to form a team of 3"),
            ("Equip your team", "Equip weapons to all 3 team members"),
        ),
        next_command="b team",
        reward_souls=250,
        reward_gems=20,
    ),
    ProgressionStage(
        key="battle",
        title="Enter the Arena",
        goal="Win your first battle",
        steps=(
            ("Join matchmaking", "Use b battle to find an opponent"),
            ("Win a battle", "Defeat an opponent in PvP combat"),
            ("Check your rank", "Use b arena to see your rating"),
        ),
        next_command="b battle",
        reward_souls=500,
        reward_gems=25,
    ),
    ProgressionStage(
        key="progression",
        title="Hunt for Power",
        goal="Hunt better zones",
        steps=(
            ("Reach level 5", "Gain enough XP to reach level 5"),
            ("Unlock new zones", "Access higher-level hunting zones"),
            ("Hunt rare creatures", "Catch Rare or better creatures in new zones"),
        ),
        next_command="b hunt",
        reward_souls=300,
        reward_gems=20,
    ),
    ProgressionStage(
        key="veteran",
        title="Master of the Hunt",
        goal="Become unstoppable",
        steps=(
            ("Level 20 creatures", "Get creatures to level 20+"),
            ("Build a 5-win streak", "Win 5 consecutive battles"),
            ("Open legendary crates", "Open Abyssal Treasure chests"),
        ),
        next_command="b battle",
        reward_souls=1000,
        reward_gems=50,
    ),
)

PROGRESSION_BY_KEY = {stage.key: stage for stage in PROGRESSION_STAGES}


def check_progression_stage(player: dict, stage: ProgressionStage) -> bool:
    """
    Determine if a player has completed a progression stage.
    
    Args:
        player: Player row from database
        stage: Progression stage to check
        
    Returns:
        True if the player meets the requirements for this stage
    """
    if stage.key == "start":
        return player["hunts_done"] == 0
    elif stage.key == "collect":
        return player["hunts_done"] < 5
    elif stage.key == "currency":
        return player["hunts_done"] < 10
    elif stage.key == "weapons":
        return player["hunts_done"] < 15
    elif stage.key == "team":
        return player["hunts_done"] < 25
    elif stage.key == "battle":
        return player["arena_rating"] == 1000  # Haven't battled yet
    elif stage.key == "progression":
        return player["level"] < 20
    elif stage.key == "veteran":
        return player["level"] < 50
    return True


def get_current_stage(player: dict) -> ProgressionStage:
    """
    Get the current progression stage for a player.
    
    Args:
        player: Player row from database
        
    Returns:
        The current stage the player should focus on
    """
    for stage in PROGRESSION_STAGES:
        if check_progression_stage(player, stage):
            return stage
    return PROGRESSION_STAGES[-1]  # Return veteran stage as final
