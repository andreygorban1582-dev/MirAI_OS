"""
MirAI_OS – 24/7 Game Engine
Runs a persistent simulation with all 303 characters:
  - Turn-based combat rounds every 30 seconds
  - XP / levelling
  - Economy (gold drops, market)
  - Leaderboard saved to game_state.json
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import random
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from characters import ALL_CHARACTERS, CHARACTER_MAP, Character

logger = logging.getLogger("GameEngine")

STATE_FILE = Path("game_state.json")
ROUND_INTERVAL = 30        # seconds between combat rounds
MARKET_INTERVAL = 300      # seconds between market events
HEAL_PER_ROUND = 5         # HP healed each round (out of combat)
XP_PER_WIN = 50
GOLD_PER_WIN = 20
LEVEL_XP_BASE = 200        # XP needed to reach level 2 (doubles per level)

# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def xp_for_level(level: int) -> int:
    return LEVEL_XP_BASE * (2 ** (level - 1))


def _stat(c: Character, key: str) -> int:
    base = getattr(c, key)
    bonus = (c.level - 1) * 5
    return base + bonus


# --------------------------------------------------------------------------- #
# Combat                                                                       #
# --------------------------------------------------------------------------- #

def calculate_damage(attacker: Character, defender: Character) -> int:
    atk = _stat(attacker, "attack") + random.randint(-10, 10)
    dfc = _stat(defender, "defense")
    raw = max(1, atk - dfc // 2)
    crit = 1.5 if random.random() < 0.15 else 1.0
    return int(raw * crit)


def run_combat(a: Character, b: Character) -> Tuple[Character, Character, List[str]]:
    """Simulate a battle; returns (winner, loser, log_lines)."""
    log: List[str] = []
    hp_a = _stat(a, "hp")
    hp_b = _stat(b, "hp")
    spd_a = _stat(a, "speed")
    spd_b = _stat(b, "speed")
    round_num = 0

    log.append(f"⚔  {a.name} [{a.universe}] vs {b.name} [{b.universe}]")

    while hp_a > 0 and hp_b > 0 and round_num < 50:
        round_num += 1
        # Faster character goes first
        first, second = (a, b) if spd_a >= spd_b else (b, a)
        hp_first = hp_a if first is a else hp_b
        hp_second = hp_b if second is b else hp_a

        # First attacks
        dmg = calculate_damage(first, second)
        if second is b:
            hp_b -= dmg
        else:
            hp_a -= dmg
        ability = random.choice(first.abilities) if first.abilities else "Basic Attack"
        log.append(f"  R{round_num} {first.name} uses {ability} → -{dmg} HP")

        if (hp_b if second is b else hp_a) <= 0:
            break

        # Second attacks
        dmg2 = calculate_damage(second, first)
        if first is a:
            hp_a -= dmg2
        else:
            hp_b -= dmg2
        ability2 = random.choice(second.abilities) if second.abilities else "Basic Attack"
        log.append(f"  R{round_num} {second.name} uses {ability2} → -{dmg2} HP")

    winner = a if hp_a > 0 else b
    loser = b if winner is a else a
    log.append(f"🏆 {winner.name} WINS!")
    return winner, loser, log


# --------------------------------------------------------------------------- #
# State persistence                                                            #
# --------------------------------------------------------------------------- #

def load_state(chars: List[Character]) -> None:
    if not STATE_FILE.exists():
        return
    try:
        data: dict = json.loads(STATE_FILE.read_text())
        for cid_str, vals in data.items():
            cid = int(cid_str)
            if cid in CHARACTER_MAP:
                c = CHARACTER_MAP[cid]
                c.level = vals.get("level", 1)
                c.xp = vals.get("xp", 0)
                c.gold = vals.get("gold", 100)
                c.wins = vals.get("wins", 0)
                c.losses = vals.get("losses", 0)
                c.alive = vals.get("alive", True)
    except Exception as exc:
        logger.warning("Could not load state: %s", exc)


def save_state(chars: List[Character]) -> None:
    data = {
        str(c.id): {
            "level": c.level,
            "xp": c.xp,
            "gold": c.gold,
            "wins": c.wins,
            "losses": c.losses,
            "alive": c.alive,
        }
        for c in chars
    }
    STATE_FILE.write_text(json.dumps(data, indent=2))


# --------------------------------------------------------------------------- #
# Game loop                                                                    #
# --------------------------------------------------------------------------- #

class GameEngine:
    def __init__(self) -> None:
        self.characters: List[Character] = ALL_CHARACTERS
        self.round: int = 0
        self.battle_log: List[str] = []
        self.running: bool = False
        load_state(self.characters)
        logger.info("GameEngine: %d characters loaded.", len(self.characters))

    def _alive_chars(self) -> List[Character]:
        return [c for c in self.characters if c.alive]

    def _level_up(self, c: Character) -> None:
        needed = xp_for_level(c.level)
        while c.xp >= needed:
            c.xp -= needed
            c.level += 1
            needed = xp_for_level(c.level)
            logger.info("🆙 %s levelled up to %d!", c.name, c.level)

    def _revive_fallen(self) -> None:
        for c in self.characters:
            if not c.alive:
                if random.random() < 0.1:   # 10 % chance per round
                    c.alive = True
                    c.gold = max(0, c.gold - 50)
                    logger.info("✨ %s has been revived!", c.name)

    async def _run_round(self) -> None:
        self.round += 1
        alive = self._alive_chars()
        if len(alive) < 2:
            self._revive_fallen()
            return

        # Pick 3–5 random matches this round
        num_matches = min(len(alive) // 2, random.randint(3, 5))
        combatants = random.sample(alive, k=num_matches * 2)
        round_log: List[str] = [f"\n=== Round {self.round} ==="]

        for i in range(num_matches):
            a, b = combatants[i * 2], combatants[i * 2 + 1]
            winner, loser, fight_log = run_combat(a, b)
            round_log.extend(fight_log)

            winner.wins += 1
            winner.xp += XP_PER_WIN
            winner.gold += GOLD_PER_WIN
            self._level_up(winner)

            loser.losses += 1
            loser.hp = max(1, loser.hp - 20)
            if random.random() < 0.05:   # 5 % chance to be knocked out
                loser.alive = False
                round_log.append(f"💀 {loser.name} has been knocked out!")

        # Passive heal for non-fighters that are still alive
        fighters = set(combatants)
        for c in alive:
            if c not in fighters and c.alive:
                c.hp = min(_stat(c, "hp"), c.hp + HEAL_PER_ROUND)

        self._revive_fallen()
        save_state(self.characters)

        log_text = "\n".join(round_log)
        self.battle_log.append(log_text)
        self.battle_log = self.battle_log[-50:]   # keep last 50 rounds
        logger.info("Round %d complete.", self.round)

    async def _market_event(self) -> None:
        alive = self._alive_chars()
        if not alive:
            return
        winners = random.sample(alive, k=min(5, len(alive)))
        event_types = [
            "found a treasure chest",
            "won a tournament",
            "crafted a rare item",
            "raided a dungeon",
            "received a bounty",
        ]
        event = random.choice(event_types)
        gold_bonus = random.randint(50, 200)
        for c in winners:
            c.gold += gold_bonus
        names = ", ".join(c.name for c in winners)
        logger.info("💰 Market event [%s]: %s each gain %d gold.", event, names, gold_bonus)

    async def run(self) -> None:
        self.running = True
        logger.info("Game engine started with %d characters.", len(self.characters))
        last_market = time.monotonic()
        while self.running:
            await self._run_round()
            if time.monotonic() - last_market >= MARKET_INTERVAL:
                await self._market_event()
                last_market = time.monotonic()
            await asyncio.sleep(ROUND_INTERVAL)

    def stop(self) -> None:
        self.running = False

    def leaderboard(self, top: int = 20) -> List[dict]:
        ranked = sorted(self.characters, key=lambda c: c.wins, reverse=True)
        return [
            {
                "rank": i + 1,
                "name": c.name,
                "universe": c.universe,
                "level": c.level,
                "wins": c.wins,
                "losses": c.losses,
                "gold": c.gold,
                "power": c.power_score,
                "alive": c.alive,
            }
            for i, c in enumerate(ranked[:top])
        ]

    def character_info(self, name: str) -> Optional[dict]:
        name_lower = name.lower()
        # Prefer exact match first, then substring
        exact = next((c for c in self.characters if c.name.lower() == name_lower), None)
        c = exact or next((c for c in self.characters if name_lower in c.name.lower()), None)
        if not c:
            return None
        return {
            "id": c.id,
            "name": c.name,
            "universe": c.universe,
            "role": c.role,
            "level": c.level,
            "hp": c.hp,
            "attack": c.attack,
            "defense": c.defense,
            "speed": c.speed,
            "intelligence": c.intelligence,
            "xp": c.xp,
            "gold": c.gold,
            "wins": c.wins,
            "losses": c.losses,
            "alive": c.alive,
            "abilities": c.abilities,
            "power_score": c.power_score,
        }


# Allow running standalone
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    engine = GameEngine()
    asyncio.run(engine.run())
