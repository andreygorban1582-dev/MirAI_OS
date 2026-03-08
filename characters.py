"""
MirAI_OS – 303 Characters
Each character has: name, universe, role, hp, attack, defense, speed, intelligence, abilities
"""
from dataclasses import dataclass, field
from typing import List

@dataclass
class Character:
    id: int
    name: str
    universe: str
    role: str
    hp: int
    attack: int
    defense: int
    speed: int
    intelligence: int
    abilities: List[str] = field(default_factory=list)
    level: int = 1
    xp: int = 0
    gold: int = 100
    wins: int = 0
    losses: int = 0
    alive: bool = True

    @property
    def power_score(self) -> int:
        return self.attack + self.defense + self.speed + self.intelligence + (self.hp // 10)


def get_all_characters() -> List[Character]:
    raw = [
        # ── Steins;Gate ──────────────────────────────────────────────
        (1,  "Rintaro Okabe",        "Steins;Gate",  "Mad Scientist",   120, 60, 50, 65, 98, ["Reading Steiner", "D-Mail", "Time Leap"]),
        (2,  "Kurisu Makise",        "Steins;Gate",  "Neuroscientist",  100, 55, 45, 70, 99, ["Time Machine Theory", "Neural Hack", "Deduction"]),
        (3,  "Mayuri Shiina",        "Steins;Gate",  "Support",          90, 30, 60, 75, 65, ["Tuturu Heal", "Cosplay Buff", "Innocence"]),
        (4,  "Itaru Hashida",        "Steins;Gate",  "Hacker",          110, 50, 55, 55, 92, ["Super Hacker", "IBN 5100 Attack", "Data Nuke"]),
        (5,  "Suzuha Amane",         "Steins;Gate",  "Time Traveler",   130, 80, 70, 95, 78, ["Time Jump", "Rifle Shot", "Future Sight"]),
        # ── Attack on Titan ──────────────────────────────────────────
        (6,  "Eren Yeager",          "Attack on Titan", "Titan Shifter", 200, 95, 80, 85, 72, ["Attack Titan", "Founding Titan", "Rumbling"]),
        (7,  "Mikasa Ackerman",      "Attack on Titan", "Soldier",       160, 98, 85, 99, 80, ["ODM Slash", "Ackerman Power", "Blade Storm"]),
        (8,  "Levi Ackerman",        "Attack on Titan", "Captain",       150, 99, 90, 100, 85, ["Meteor Slash", "Clean Sweep", "Thunder Spears"]),
        (9,  "Armin Arlert",         "Attack on Titan", "Strategist",    120, 55, 60, 65, 99, ["Colossal Titan", "Tactical Mind", "Nape Strike"]),
        (10, "Historia Reiss",       "Attack on Titan", "Queen",         110, 50, 70, 72, 82, ["Royal Blood", "Morale Boost", "Historia's Will"]),
        # ── Demon Slayer ─────────────────────────────────────────────
        (11, "Tanjiro Kamado",       "Demon Slayer", "Demon Slayer",    150, 85, 75, 80, 80, ["Water Breathing", "Hinokami Kagura", "Selfless State"]),
        (12, "Nezuko Kamado",        "Demon Slayer", "Demon",           140, 90, 70, 88, 65, ["Blood Demon Art", "Exploding Blood", "Demon Shrink"]),
        (13, "Zenitsu Agatsuma",     "Demon Slayer", "Thunder Slayer",  120, 88, 55, 99, 58, ["Thunderclap Flash", "Godspeed", "Seven Fold"]),
        (14, "Inosuke Hashibira",    "Demon Slayer", "Beast Slayer",    145, 92, 68, 90, 55, ["Beast Breathing", "Sudden Throwing Strike", "Wild Fang"]),
        (15, "Rengoku Kyojuro",      "Demon Slayer", "Flame Hashira",   160, 97, 80, 93, 78, ["Flame Breathing", "Ninth Form", "Esoteric Art"]),
        # ── Naruto ───────────────────────────────────────────────────
        (16, "Naruto Uzumaki",       "Naruto",       "Hokage",          250, 95, 85, 90, 75, ["Rasengan", "Shadow Clone", "Nine-Tails Mode"]),
        (17, "Sasuke Uchiha",        "Naruto",       "Avenger",         200, 97, 82, 95, 90, ["Chidori", "Susanoo", "Amaterasu"]),
        (18, "Sakura Haruno",        "Naruto",       "Medic",           150, 80, 90, 72, 88, ["Cherry Blossom Impact", "Mystical Palm", "Hundred Seals"]),
        (19, "Kakashi Hatake",       "Naruto",       "Jonin",           190, 93, 88, 93, 95, ["Kamui", "Raikiri", "Copy Wheel Eye"]),
        (20, "Itachi Uchiha",        "Naruto",       "Prodigy",         180, 98, 80, 90, 99, ["Tsukuyomi", "Izanami", "Totsuka Blade"]),
        # ── My Hero Academia ─────────────────────────────────────────
        (21, "Izuku Midoriya",       "My Hero Academia", "Hero",        170, 90, 80, 85, 92, ["One For All", "Detroit Smash", "Full Cowling"]),
        (22, "Katsuki Bakugo",       "My Hero Academia", "Hero",        160, 95, 75, 92, 80, ["AP Shot", "Howitzer Impact", "Grenadier Bracers"]),
        (23, "Shoto Todoroki",       "My Hero Academia", "Hero",        165, 92, 82, 80, 85, ["Half Cold Half Hot", "Flashfreeze Heatwave", "Giant Ice Wall"]),
        (24, "All Might",            "My Hero Academia", "Symbol",      200, 99, 85, 90, 88, ["United States of Smash", "Carolina Smash", "Texas Smash"]),
        (25, "Eraserhead",           "My Hero Academia", "Teacher",     140, 75, 80, 88, 96, ["Erasure", "Capture Weapon", "Blackwhip"]),
        # ── Dragon Ball ──────────────────────────────────────────────
        (26, "Goku",                 "Dragon Ball",  "Saiyan",          300, 99, 90, 99, 75, ["Kamehameha", "Ultra Instinct", "Spirit Bomb"]),
        (27, "Vegeta",               "Dragon Ball",  "Saiyan Prince",   280, 98, 88, 97, 78, ["Final Flash", "Big Bang Attack", "Ultra Ego"]),
        (28, "Gohan",                "Dragon Ball",  "Hybrid Saiyan",   260, 96, 85, 90, 92, ["Masenko", "Super Saiyan Rage", "Beast Form"]),
        (29, "Piccolo",              "Dragon Ball",  "Namekian",        220, 88, 85, 82, 90, ["Special Beam Cannon", "Giant Form", "Regeneration"]),
        (30, "Frieza",               "Dragon Ball",  "Emperor",         290, 97, 87, 95, 88, ["Death Beam", "Nova Strike", "Black Frieza"]),
        # ── One Piece ────────────────────────────────────────────────
        (31, "Monkey D. Luffy",      "One Piece",    "Pirate King",     250, 95, 85, 90, 72, ["Gear Fifth", "Red Roc", "Gomu Gomu Thunder"]),
        (32, "Roronoa Zoro",         "One Piece",    "Swordsman",       220, 97, 82, 88, 75, ["Shishi Sonson", "1080 Pound Phoenix", "Enma"]),
        (33, "Nami",                 "One Piece",    "Navigator",       110, 65, 55, 85, 95, ["Thunderbolt Tempo", "Zeus", "Clima-Tact"]),
        (34, "Usopp",               "One Piece",    "Sniper",          100, 70, 50, 78, 82, ["Kabuto", "Pop Green", "Haki Snipe"]),
        (35, "Sanji",               "One Piece",    "Chef",            200, 93, 78, 96, 80, ["Ifrit Jambe", "Sky Walk", "Diable Jambe"]),
        # ── Cyberpunk 2077 ───────────────────────────────────────────
        (36, "V",                   "Cyberpunk 2077", "Merc",          150, 85, 75, 88, 82, ["Sandevistan", "Mantis Blades", "Netrunner Hack"]),
        (37, "Johnny Silverhand",   "Cyberpunk 2077", "Rockerboy",     160, 88, 72, 85, 78, ["Relic Arm", "Guitar Smash", "Rebel Yell"]),
        (38, "Judy Alvarez",        "Cyberpunk 2077", "Braindance Tech", 110, 62, 60, 72, 90, ["BD Trap", "Optics Hack", "Trauma Dive"]),
        (39, "Panam Palmer",        "Cyberpunk 2077", "Nomad",         140, 82, 72, 80, 78, ["Basilisk Cannon", "Nomad Drive", "IED"]),
        (40, "Adam Smasher",        "Cyberpunk 2077", "Full Borg",     220, 97, 95, 80, 72, ["Missile Barrage", "Smasher Fist", "Sandevistan Blitz"]),
        # ── Halo ─────────────────────────────────────────────────────
        (41, "Master Chief",        "Halo",         "Spartan",         200, 92, 95, 88, 85, ["Energy Sword", "Plasma Grenade", "Spartan Charge"]),
        (42, "Arbiter",             "Halo",         "Elite",           190, 90, 88, 85, 82, ["Energy Blade", "Active Camo", "Fuel Rod"]),
        (43, "Cortana",             "Halo",         "AI",              100, 70, 50, 99, 100, ["Network Hack", "Construct", "Domain Access"]),
        (44, "Sergeant Johnson",    "Halo",         "Marine",          140, 80, 75, 78, 75, ["Sniper Volley", "Battle Rifle", "Cigar Bomb"]),
        (45, "Guilty Spark",        "Halo",         "Monitor",         120, 65, 60, 90, 95, ["Flood Scan", "Sentinel Beam", "Activation"]),
        # ── Mass Effect ──────────────────────────────────────────────
        (46, "Commander Shepard",   "Mass Effect",  "Spectre",         170, 88, 82, 85, 92, ["Biotic Charge", "Warp", "N7 Smash"]),
        (47, "Garrus Vakarian",     "Mass Effect",  "Turian Calibrator", 155, 90, 80, 82, 88, ["Calibration Shot", "Overload", "Concussive Shot"]),
        (48, "Liara T'Soni",        "Mass Effect",  "Asari",           140, 80, 72, 75, 97, ["Singularity", "Stasis", "Shadow Broker"]),
        (49, "Tali'Zorah",          "Mass Effect",  "Quarian",         120, 72, 68, 80, 93, ["Combat Drone", "AI Hacking", "Energy Drain"]),
        (50, "Wrex",                "Mass Effect",  "Krogan",          210, 93, 90, 72, 70, ["Charge", "Fortification", "Headbutt"]),
        # ── The Witcher ──────────────────────────────────────────────
        (51, "Geralt of Rivia",     "The Witcher",  "Witcher",         180, 94, 85, 88, 88, ["Aard", "Igni", "Quen"]),
        (52, "Yennefer",            "The Witcher",  "Sorceress",       150, 85, 72, 78, 98, ["Elven Bolt", "Portal", "Shield"]),
        (53, "Ciri",                "The Witcher",  "Witcher",         170, 90, 80, 95, 85, ["Blink", "Swallow", "Spiral"]),
        (54, "Triss Merigold",      "The Witcher",  "Sorceress",       140, 82, 70, 78, 95, ["Firebolt", "Trance", "Stamina Potion"]),
        (55, "Dandelion",           "The Witcher",  "Bard",            100, 45, 55, 72, 88, ["Battle Hymn", "Lute Bash", "Charm"]),
        # ── Elden Ring ───────────────────────────────────────────────
        (56, "Tarnished",           "Elden Ring",   "Hero",            200, 92, 88, 82, 78, ["Moonveil", "Rennala Moon", "Flame of Frenzy"]),
        (57, "Malenia",             "Elden Ring",   "Demigod",         220, 98, 85, 97, 82, ["Scarlet Rot Bloom", "Waterfowl Dance", "Goddess of Rot"]),
        (58, "Radahn",              "Elden Ring",   "Demigod",         250, 97, 92, 78, 75, ["Meteor Barrage", "Stars of Ruin", "Lion Slash"]),
        (59, "Ranni",               "Elden Ring",   "Witch",           150, 80, 72, 85, 99, ["Dark Moon Greatsword", "Snow Witch", "Age of Stars"]),
        (60, "Melina",              "Elden Ring",   "Guidance",        130, 72, 68, 80, 95, ["Kindling", "Erdtree Flame", "Guidance"]),
        # ── Dark Souls ───────────────────────────────────────────────
        (61, "Chosen Undead",       "Dark Souls",   "Undead",          180, 88, 85, 80, 78, ["Sunlight Spear", "Dark Bead", "Black Flame"]),
        (62, "Ornstein",            "Dark Souls",   "Knight",          200, 93, 88, 88, 75, ["Lightning Thrust", "Super Ornstein", "Dragoon Charge"]),
        (63, "Sif",                 "Dark Souls",   "Wolf",            170, 90, 80, 92, 65, ["Moonlight Bite", "Wolf Slash", "Great Sword Slam"]),
        (64, "Solaire",             "Dark Souls",   "Knight",          160, 85, 80, 78, 78, ["Sunlight Spear", "Praise the Sun", "Great Lightning"]),
        (65, "Artorias",            "Dark Souls",   "Knight",          210, 97, 90, 92, 80, ["Wolf Ring Slash", "Abyss Walk", "Greatshield Smash"]),
        # ── Ghost in the Shell ───────────────────────────────────────
        (66, "Motoko Kusanagi",     "Ghost in the Shell", "Major",     160, 90, 85, 95, 98, ["Cyberbrain Hack", "Thermo-Optic Camo", "Spider Tank"]),
        (67, "Batou",               "Ghost in the Shell", "Agent",     170, 88, 88, 85, 82, ["Optical Cam Shot", "Gorilla Punch", "Cybervision"]),
        (68, "Togusa",              "Ghost in the Shell", "Detective",  130, 72, 70, 80, 90, ["Mateba Autorevolver", "Deductive Reasoning", "Undercover"]),
        (69, "Puppet Master",       "Ghost in the Shell", "AI",         110, 80, 65, 98, 100, ["Ghost Merge", "Network Breach", "Consciousness Fork"]),
        (70, "Tachikoma",           "Ghost in the Shell", "Think-Tank", 200, 85, 92, 90, 88, ["Spider Crawl", "Sticky Bomb", "Net Dive"]),
        # ── Sword Art Online ─────────────────────────────────────────
        (71, "Kirito",              "SAO",          "Black Swordsman",  170, 95, 82, 95, 85, ["Dual Blades", "Star Splash", "Vorpal Strike"]),
        (72, "Asuna",               "SAO",          "Knight",           155, 90, 78, 97, 82, ["Linear", "Rapier Storm", "Mother's Rosario"]),
        (73, "Sinon",               "SAO",          "Sniper",           130, 88, 65, 85, 88, ["Hecate II", "Phantom Bullet", "Cold Heart"]),
        (74, "Leafa",               "SAO",          "Sylph",            140, 80, 72, 90, 78, ["Wind Ride", "Leaf Blade", "Sylph Storm"]),
        (75, "Yui",                 "SAO",          "AI Cardinal",      100, 65, 60, 90, 99, ["System Manipulation", "Cardinal Override", "Emotional Link"]),
        # ── Fullmetal Alchemist ──────────────────────────────────────
        (76, "Edward Elric",        "FMA",          "Alchemist",        150, 88, 75, 88, 96, ["Alchemy Spear", "Automail Cannon", "Gate of Truth"]),
        (77, "Alphonse Elric",      "FMA",          "Alchemist",        200, 82, 95, 72, 90, ["Armor Fist", "Bind Seal", "Transmutation"]),
        (78, "Roy Mustang",         "FMA",          "Colonel",          145, 90, 70, 78, 92, ["Flame Alchemy", "Snap Inferno", "Oxygen Depletion"]),
        (79, "Riza Hawkeye",        "FMA",          "Sharpshooter",     130, 88, 72, 85, 88, ["Precision Shot", "Double Pistol", "Target Lock"]),
        (80, "Greed",               "FMA",          "Homunculus",       180, 90, 97, 80, 80, ["Ultimate Shield", "Carbon Skin", "Lust Spear"]),
        # ── Hunter x Hunter ──────────────────────────────────────────
        (81, "Gon Freecss",         "HxH",          "Hunter",           160, 90, 78, 88, 75, ["Jajanken Rock", "Nen Force", "Enhancer Punch"]),
        (82, "Killua Zoldyck",      "HxH",          "Assassin",         155, 93, 80, 99, 85, ["Godspeed", "Lightning Palm", "Alluka Wish"]),
        (83, "Kurapika",            "HxH",          "Chain User",       140, 85, 72, 82, 92, ["Emperor Time", "Chain Jail", "Dowsing Chain"]),
        (84, "Leorio Paradinight",  "HxH",          "Doctor",           120, 70, 65, 72, 88, ["Teleport Punch", "Medical Skills", "Nen Briefcase"]),
        (85, "Hisoka",              "HxH",          "Magician",         180, 97, 78, 95, 90, ["Bungee Gum", "Texture Surprise", "Rubber Clown"]),
        # ── JoJo's Bizarre Adventure ─────────────────────────────────
        (86, "Jotaro Kujo",         "JoJo",         "Stand User",       170, 95, 85, 85, 88, ["Star Platinum", "The World", "ORA ORA ORA"]),
        (87, "Giorno Giovanna",     "JoJo",         "Gang Star",        160, 92, 80, 85, 92, ["Gold Experience", "Requiem", "Life Reset"]),
        (88, "Dio Brando",          "JoJo",         "Vampire",          200, 98, 90, 88, 90, ["The World", "Road Roller", "Blades"]),
        (89, "Yoshikage Kira",      "JoJo",         "Serial Killer",    155, 88, 82, 78, 85, ["Killer Queen", "Bites the Dust", "Sheer Heart Attack"]),
        (90, "Bruno Bucciarati",    "JoJo",         "Gangster",         150, 85, 80, 80, 85, ["Sticky Fingers", "Zipper Space", "Arrivederci"]),
        # ── Bleach ───────────────────────────────────────────────────
        (91, "Ichigo Kurosaki",     "Bleach",       "Soul Reaper",      200, 96, 85, 92, 82, ["Getsuga Tensho", "Bankai", "Hollowification"]),
        (92, "Rukia Kuchiki",       "Bleach",       "Soul Reaper",      140, 80, 75, 82, 85, ["Sode no Shirayuki", "Ode to Snowfall", "Some No Mai"]),
        (93, "Byakuya Kuchiki",     "Bleach",       "Captain",          180, 93, 85, 85, 88, ["Senbonzakura", "Bankai Scatter", "Petal Storm"]),
        (94, "Kenpachi Zaraki",     "Bleach",       "Captain",          220, 99, 85, 82, 65, ["Eye Patch Release", "No Shikai", "Yachiru"]),
        (95, "Sosuke Aizen",        "Bleach",       "Traitor",          200, 97, 90, 85, 99, ["Kyoka Suigetsu", "Hogyoku", "Complete Hypnosis"]),
        # ── Evangelion ───────────────────────────────────────────────
        (96, "Shinji Ikari",        "Evangelion",   "Pilot",            150, 80, 75, 72, 80, ["Eva Unit-01", "AT Field", "100% Sync"]),
        (97, "Rei Ayanami",         "Evangelion",   "Pilot",            140, 78, 78, 70, 82, ["Eva Unit-00", "Self Destruct", "Rei Clone"]),
        (98, "Asuka Langley",       "Evangelion",   "Pilot",            155, 85, 78, 80, 80, ["Eva Unit-02", "Beast Mode", "Flaming Swords"]),
        (99, "Misato Katsuragi",    "Evangelion",   "Commander",        120, 70, 68, 75, 90, ["NERV Command", "Tactical Orders", "Yebisu Beer"]),
        (100, "Kaworu Nagisa",      "Evangelion",   "Angel",            160, 82, 80, 78, 98, ["AT Field Crush", "Adam Soul", "Space Collapse"]),
        # ── Overwatch ────────────────────────────────────────────────
        (101, "Tracer",             "Overwatch",    "Hero",             120, 80, 65, 99, 82, ["Blink", "Recall", "Pulse Bomb"]),
        (102, "Genji",              "Overwatch",    "Hero",             140, 88, 72, 97, 80, ["Dragonblade", "Deflect", "Swift Strike"]),
        (103, "Widowmaker",         "Overwatch",    "Assassin",         130, 92, 62, 82, 85, ["Widow's Kiss", "Venom Mine", "Infra-Sight"]),
        (104, "D.Va",               "Overwatch",    "Hero",             180, 82, 92, 80, 78, ["Mech Barrage", "Self-Destruct", "Defense Matrix"]),
        (105, "Reaper",             "Overwatch",    "Wraith",           160, 90, 80, 80, 78, ["Death Blossom", "Shadow Step", "Hellfire"]),
        # ── League of Legends ────────────────────────────────────────
        (106, "Jinx",               "League of Legends", "Marksman",   130, 90, 60, 88, 78, ["Super Mega Death Rocket", "Flame Chompers", "Switcheroo"]),
        (107, "Vi",                 "League of Legends", "Fighter",     160, 88, 82, 82, 72, ["Vault Breaker", "Excessive Force", "Assault and Battery"]),
        (108, "Ekko",               "League of Legends", "Assassin",   145, 85, 72, 92, 88, ["Chronobreak", "Time Winder", "Parallel Convergence"]),
        (109, "Caitlyn",            "League of Legends", "Marksman",   125, 88, 65, 82, 82, ["Ace in the Hole", "Yordle Snap Trap", "90 Caliber Net"]),
        (110, "Arcane Jayce",       "League of Legends", "Fighter",    165, 90, 78, 80, 88, ["Mercury Hammer", "Cannon Form", "Transform"]),
        # ── Baldur's Gate ────────────────────────────────────────────
        (111, "Astarion",           "Baldur's Gate 3", "Rogue",         140, 88, 72, 95, 85, ["Sneak Attack", "Spawn Form", "Charm"]),
        (112, "Shadowheart",        "Baldur's Gate 3", "Cleric",        135, 78, 78, 75, 88, ["Guiding Bolt", "Shar's Darkness", "Inflict Wounds"]),
        (113, "Gale",               "Baldur's Gate 3", "Wizard",        130, 82, 65, 72, 97, ["Netherese Bomb", "Fireball", "Arcane Recovery"]),
        (114, "Lae'zel",            "Baldur's Gate 3", "Fighter",       165, 93, 85, 85, 75, ["Githyanki Cleave", "Action Surge", "Indomitable"]),
        (115, "Wyll",               "Baldur's Gate 3", "Warlock",       140, 85, 72, 78, 85, ["Eldritch Blast", "Devil's Sight", "Hunger of Hadar"]),
        # ── Dota 2 ───────────────────────────────────────────────────
        (116, "Dragon Knight",      "Dota 2",       "Carry",           185, 88, 88, 75, 72, ["Breathe Fire", "Dragon Form", "Elder Dragon Flame"]),
        (117, "Invoker",            "Dota 2",       "Mage",            145, 87, 68, 82, 99, ["Sun Strike", "Cold Snap", "Chaos Meteor"]),
        (118, "Crystal Maiden",     "Dota 2",       "Support",         110, 78, 60, 65, 90, ["Frost Bite", "Crystal Nova", "Freezing Field"]),
        (119, "Pudge",              "Dota 2",       "Offlane",         220, 88, 82, 60, 70, ["Meat Hook", "Dismember", "Flesh Heap"]),
        (120, "Anti-Mage",          "Dota 2",       "Carry",           155, 90, 78, 97, 72, ["Mana Break", "Blink", "Mana Void"]),
        # ── Persona ──────────────────────────────────────────────────
        (121, "Yu Narukami",        "Persona 4",    "Protagonist",     165, 90, 82, 85, 90, ["Izanagi", "Ziodyne", "Magatsu-Izanagi"]),
        (122, "Ryuji Sakamoto",     "Persona 5",    "Phantom Thief",   155, 88, 75, 80, 72, ["Captain Kidd", "Shock Blast", "Skull Bash"]),
        (123, "Morgana",            "Persona 5",    "Phantom Thief",   100, 72, 68, 90, 88, ["Zorro", "Healing Circle", "Whiplash"]),
        (124, "Makoto Niijima",     "Persona 5",    "Phantom Thief",   145, 85, 82, 80, 88, ["Johanna", "Nuke Bomb", "Checkmate"]),
        (125, "Futaba Sakura",      "Persona 5",    "Phantom Thief",   100, 65, 60, 85, 99, ["Necronomicon", "Navigation", "Analysis"]),
        # ── Resident Evil ─────────────────────────────────────────────
        (126, "Leon S. Kennedy",    "Resident Evil", "Agent",           155, 85, 78, 88, 85, ["Blacktail", "Riot Gun", "Knife Parry"]),
        (127, "Claire Redfield",    "Resident Evil", "Survivor",        140, 80, 72, 85, 82, ["Grenade Launcher", "Revolver", "Grapple Hook"]),
        (128, "Jill Valentine",     "Resident Evil", "STARS",           150, 83, 75, 88, 88, ["Lockpick", "Grenade Launcher", "BSAA Combat"]),
        (129, "Ada Wong",           "Resident Evil", "Spy",             140, 82, 72, 92, 90, ["Grapple Shot", "Ganados Knife", "Crossbow"]),
        (130, "Chris Redfield",     "Resident Evil", "BSAA",            170, 88, 85, 82, 80, ["Magnum", "Boulder Punch", "BSAA Strike"]),
        # ── Silent Hill ──────────────────────────────────────────────
        (131, "Pyramid Head",       "Silent Hill",  "Monster",         200, 97, 90, 65, 72, ["Great Knife", "Spear", "Instant Kill"]),
        (132, "James Sunderland",   "Silent Hill",  "Survivor",        120, 68, 65, 68, 72, ["Plank of Wood", "Handgun", "Pipe"]),
        (133, "Heather Mason",      "Silent Hill",  "Survivor",        130, 72, 68, 75, 78, ["Katana", "Flamethrower", "Beam Saber"]),
        (134, "Claudia Wolf",       "Silent Hill",  "Cultist",         110, 70, 65, 68, 80, ["Otherworld Summon", "God's Ritual", "Faith Shield"]),
        (135, "Dahlia Gillespie",   "Silent Hill",  "Cult Leader",     105, 68, 62, 65, 82, ["Otherworld Seal", "Cult Bind", "Demon Summon"]),
        # ── Hollow Knight ────────────────────────────────────────────
        (136, "The Knight",         "Hollow Knight", "Vessel",         140, 88, 80, 88, 72, ["Nail Strike", "Vengeful Spirit", "Sharp Shadow"]),
        (137, "Hornet",             "Hollow Knight", "Guardian",       145, 90, 78, 95, 78, ["Needle", "Spidersilk", "Venomous Stab"]),
        (138, "Grimm",              "Hollow Knight", "Nightmare",      160, 93, 80, 90, 80, ["Nightmare Flames", "Grimmchild", "Troupe Master"]),
        (139, "Radiance",           "Hollow Knight", "Ancient Being",  180, 95, 88, 85, 90, ["Light Spear", "Sun Beam", "Divine Wind"]),
        (140, "Silksong Hornet",    "Hollow Knight", "Hero",           150, 92, 80, 97, 82, ["Needle Dance", "Ascension", "Silk Dash"]),
        # ── Undertale / Deltarune ────────────────────────────────────
        (141, "Sans",               "Undertale",    "Skeleton",        140, 92, 85, 92, 90, ["Gaster Blasters", "Bone Wall", "Karmic Retribution"]),
        (142, "Undyne",             "Undertale",    "Captain",         160, 90, 88, 85, 80, ["Spear of Justice", "Anime Mode", "Blue Attack"]),
        (143, "Toriel",             "Undertale",    "Caretaker",       130, 72, 80, 68, 88, ["Fireball", "Protect", "Mild Cinnamon"]),
        (144, "Flowey",             "Undertale",    "Flower",          120, 85, 75, 80, 88, ["Friendliness Pellets", "SAVE Steal", "Photoshop Flowey"]),
        (145, "Kris",               "Deltarune",    "Hero",            145, 82, 78, 82, 80, ["Rude Buster", "Dream Saber", "ACT"]),
        # ── Portal ───────────────────────────────────────────────────
        (146, "Chell",              "Portal",       "Test Subject",    130, 72, 70, 82, 85, ["Portal Gun", "Long Fall Boots", "Cube Throw"]),
        (147, "GLaDOS",             "Portal",       "AI",              100, 80, 60, 90, 100, ["Neurotoxin", "Core Transfer", "Turret Deploy"]),
        (148, "Wheatley",           "Portal",       "AI Core",          90, 55, 50, 85, 65, ["Core Combine", "Turret Misfire", "Dopey Plan"]),
        (149, "Cave Johnson",       "Portal",       "Founder",          95, 60, 55, 60, 80, ["Combustible Lemon", "Science Rant", "Test Chamber"]),
        (150, "Atlas",              "Portal 2",     "Co-op Robot",     150, 80, 75, 85, 72, ["Portal Gun", "Turret Deploy", "Cooperative Smash"]),
        # ── Bioshock ─────────────────────────────────────────────────
        (151, "Jack",               "BioShock",     "Rapture Survivor", 155, 85, 75, 80, 80, ["Electro Bolt", "Telekinesis", "Incinerate"]),
        (152, "Andrew Ryan",        "BioShock",     "Visionary",        120, 70, 65, 65, 92, ["Rapture Order", "Ideological Strength", "Golf Club"]),
        (153, "Elizabeth",          "BioShock Inf.", "Tear Opener",     130, 72, 70, 78, 97, ["Infusion", "Tear Open", "First Lady Vigor"]),
        (154, "Booker DeWitt",      "BioShock Inf.", "Agent",           155, 85, 78, 82, 80, ["Skyhook", "Hand Cannon", "Bucking Bronco"]),
        (155, "Big Daddy",          "BioShock",     "Protector",        220, 95, 95, 60, 60, ["Drill Charge", "Rivet Gun", "Stomp"]),
        # ── Metal Gear ───────────────────────────────────────────────
        (156, "Solid Snake",        "Metal Gear",   "Soldier",          165, 88, 80, 88, 92, ["CQC", "PSG-1 Snipe", "Cardboard Box"]),
        (157, "Big Boss",           "Metal Gear",   "Legend",           180, 95, 85, 90, 93, ["CQC Combo", "Missile Launcher", "Diamond Dogs"]),
        (158, "Revolver Ocelot",    "Metal Gear",   "Triple Agent",     160, 90, 78, 88, 92, ["Revolver Fan", "Ricochet Shot", "Hypnosis"]),
        (159, "Raiden",             "Metal Gear",   "Cyborg",           170, 92, 80, 95, 80, ["Blade Mode", "Lightning Raiden", "Zandatsu"]),
        (160, "Quiet",              "Metal Gear",   "Sniper",           145, 93, 70, 92, 80, ["Butterfly Sniper", "Parasite Skin", "AM MRS-4"]),
        # ── Hollow Knight 2 (extra Silk) / Celeste ─────────────────
        (161, "Madeline",           "Celeste",      "Climber",          120, 68, 70, 88, 80, ["Dash", "Crystal Heart", "Badeline Merge"]),
        (162, "Badeline",           "Celeste",      "Shadow",           130, 80, 72, 90, 82, ["Dark Blast", "Shadow Form", "Reflection"]),
        # ── Fate / Stay Night ─────────────────────────────────────────
        (163, "Saber (Artoria)",    "Fate",         "Servant",          180, 95, 88, 88, 82, ["Excalibur", "Avalon", "Saber Strike"]),
        (164, "Archer (EMIYA)",     "Fate",         "Servant",          165, 93, 80, 90, 88, ["Unlimited Blade Works", "Caladbolg II", "Hrunting"]),
        (165, "Gilgamesh",          "Fate",         "Servant",          200, 99, 88, 85, 90, ["Gate of Babylon", "Ea", "King's Words"]),
        (166, "Rin Tohsaka",        "Fate",         "Mage",             140, 82, 72, 80, 93, ["Gandr", "Jewel Magic", "Clock Tower"]),
        (167, "Medusa",             "Fate",         "Servant",          170, 90, 82, 95, 80, ["Bellerophon", "Mystic Eyes", "Pegasus"]),
        # ── Re:Zero ───────────────────────────────────────────────────
        (168, "Subaru Natsuki",     "Re:Zero",      "Protagonist",      130, 65, 62, 72, 78, ["Return by Death", "Cor Leonis", "Madness"]),
        (169, "Emilia",             "Re:Zero",      "Half-Elf",         150, 82, 78, 78, 88, ["Ice Blade", "Freeze", "Icy Terrain"]),
        (170, "Rem",                "Re:Zero",      "Maid",             155, 88, 80, 82, 78, ["Oni Form", "Morning Star", "Water Magic"]),
        (171, "Ram",                "Re:Zero",      "Maid",             140, 82, 75, 80, 80, ["Wind Blade", "Fura", "Clairvoyance"]),
        (172, "Beatrice",           "Re:Zero",      "Spirit",           145, 80, 75, 72, 95, ["Dona Dona", "Passage", "Al Shamac"]),
        # ── Vinland Saga ──────────────────────────────────────────────
        (173, "Thorfinn",           "Vinland Saga", "Warrior",          160, 93, 80, 95, 82, ["Twin Daggers", "Thors' Blood", "True Warrior"]),
        (174, "Askeladd",           "Vinland Saga", "Warlord",          170, 90, 82, 85, 92, ["Swordplay", "Tactical Command", "Welsh Blood"]),
        (175, "Thorkell",           "Vinland Saga", "Giant",            230, 97, 90, 80, 72, ["Axe Throw", "Giant Charge", "Laughter Roar"]),
        # ── Chainsaw Man ──────────────────────────────────────────────
        (176, "Denji",              "Chainsaw Man", "Devil Hunter",     175, 92, 85, 88, 65, ["Chainsaw Rip", "Pochita Core", "Blood Chainsaw"]),
        (177, "Makima",             "Chainsaw Man", "Control Devil",    170, 88, 82, 82, 97, ["Control", "Spinal Crush", "Gunshot"]),
        (178, "Power",              "Chainsaw Man", "Blood Devil",      155, 90, 78, 85, 68, ["Blood Cannon", "Spike Hammer", "Bat Form"]),
        (179, "Aki Hayakawa",       "Chainsaw Man", "Devil Hunter",     145, 82, 75, 80, 82, ["Curse Devil", "Future Devil", "Sword Slash"]),
        (180, "Reze",               "Chainsaw Man", "Bomb Devil",       160, 88, 78, 85, 80, ["Bomb Detonate", "Grenade Spew", "Explosion"]),
        # ── Hunter x Hunter 2 ────────────────────────────────────────
        (181, "Meruem",             "HxH",          "Chimera King",     280, 99, 98, 97, 99, ["Royal Guard", "Rose Bomb", "En"]),
        (182, "Neferpitou",         "HxH",          "Royal Guard",      220, 97, 92, 97, 90, ["Terpsichora", "Doctor Blythe", "Puppetmaster"]),
        (183, "Netero",             "HxH",          "Chairman",         200, 97, 85, 90, 95, ["100-Type Guanyin Bodhisattva", "Poor Man's Rose", "Zero Hand"]),
        # ── Tokyo Ghoul ──────────────────────────────────────────────
        (184, "Ken Kaneki",         "Tokyo Ghoul",  "Ghoul",            175, 92, 85, 88, 85, ["Kagune", "Centipede Form", "Black Reaper"]),
        (185, "Touka Kirishima",    "Tokyo Ghoul",  "Ghoul",            155, 85, 80, 88, 80, ["Kagune Wing", "Ukaku", "Blue Moon"]),
        (186, "Ayato Kirishima",    "Tokyo Ghoul",  "Ghoul",            160, 88, 80, 90, 78, ["Ukaku Barrage", "Speed Strike", "Ghoul Rush"]),
        # ── Black Clover ──────────────────────────────────────────────
        (187, "Asta",               "Black Clover", "Magic Knight",     165, 90, 82, 88, 68, ["Black Asta", "Anti-Magic", "Devil Union"]),
        (188, "Yuno",               "Black Clover", "Magic Knight",     170, 92, 80, 90, 82, ["Spirit Storm", "Star Magic", "Mana Zone"]),
        (189, "Noelle Silva",       "Black Clover", "Magic Knight",     155, 85, 80, 80, 80, ["Valkyrie Dress", "Sea Dragon", "Water Bullet"]),
        # ── Overlord ─────────────────────────────────────────────────
        (190, "Ainz Ooal Gown",     "Overlord",     "Undead King",      250, 98, 95, 78, 99, ["Dark Wisdom", "Fallen Down", "Greater Death"]),
        (191, "Albedo",             "Overlord",     "Guardian",         200, 92, 97, 82, 88, ["Hermes Trismegistus", "Shield Bash", "Fly"]),
        (192, "Shalltear Bloodfallen", "Overlord",  "Vampire",          210, 97, 90, 90, 85, ["Blood Frenzy", "Spuit Lance", "Einherjar"]),
        # ── That Time I Got Reincarnated as a Slime ──────────────────
        (193, "Rimuru Tempest",     "Slime",        "Demon Lord",       230, 96, 92, 90, 98, ["Predator", "Merging", "Ultraspeed Regeneration"]),
        (194, "Milim Nava",         "Slime",        "Demon Lord",       250, 99, 95, 98, 85, ["Dragon Bullet", "Dragon Nova", "True Dragon"]),
        (195, "Shuna",              "Slime",        "Priestess",        130, 75, 72, 72, 90, ["Magic Weaving", "Holy Barrier", "Spiritual Flame"]),
        # ── No Game No Life ──────────────────────────────────────────
        (196, "Sora",               "NGNL",         "Gamer",            120, 72, 65, 80, 99, ["Blank Strategy", "Mind Game", "Cheating Master"]),
        (197, "Shiro",              "NGNL",         "Gamer",            100, 65, 60, 75, 100, ["Chess Master", "Calculation", "Pattern Recognition"]),
        # ── Cyberpunk Edgerunners ────────────────────────────────────
        (198, "David Martinez",     "Edgerunners",  "Edgerunner",       160, 90, 82, 92, 80, ["Sandevistan Full", "Chrome Body", "Cyberpunk Rush"]),
        (199, "Lucy",               "Edgerunners",  "Netrunner",        130, 72, 68, 85, 95, ["ICE Pick", "Moon Dream", "Deep Dive"]),
        (200, "Maine",              "Edgerunners",  "Edgerunner",       190, 93, 85, 80, 72, ["Heavy Chrome", "Berserker", "Maxed Out"]),
        # ── Arcane ───────────────────────────────────────────────────
        (201, "Powder/Jinx",        "Arcane",       "Chaos Agent",      140, 90, 65, 88, 80, ["Fishbones", "Flame Chompers", "Mania"]),
        (202, "Silco",              "Arcane",       "Undercity Boss",   125, 75, 72, 70, 92, ["Shimmer", "Political Power", "Eye Toxin"]),
        (203, "Sevika",             "Arcane",       "Enforcer",         175, 90, 85, 78, 75, ["Chrome Arm", "Shimmer Slam", "Shield Rush"]),
        # ── Spy x Family ─────────────────────────────────────────────
        (204, "Loid Forger",        "Spy x Family", "Spy",              155, 85, 80, 88, 95, ["Disguise", "Pistol", "Tactical Punch"]),
        (205, "Yor Forger",         "Spy x Family", "Assassin",         165, 93, 82, 92, 75, ["Rose Kick", "Poison Flower", "Thorn"]),
        (206, "Anya Forger",        "Spy x Family", "Telepath",         90, 55, 55, 70, 85, ["Telepathy", "Secret Peek", "Heh Face"]),
        # ── Blue Lock ────────────────────────────────────────────────
        (207, "Yoichi Isagi",       "Blue Lock",    "Footballer",       140, 82, 72, 88, 90, ["Direct Shot", "Meta Vision", "Isagi World"]),
        (208, "Bachira Meguru",     "Bachira",      "Footballer",       135, 80, 68, 90, 82, ["Monster Dribble", "Team Trick", "Dual Strike"]),
        # ── Jujutsu Kaisen ───────────────────────────────────────────
        (209, "Yuji Itadori",       "JJK",          "Sorcerer",         165, 92, 82, 90, 78, ["Divergent Fist", "Mahoraga", "Sukuna Finger"]),
        (210, "Megumi Fushiguro",   "JJK",          "Sorcerer",         155, 88, 80, 82, 85, ["Ten Shadows", "Divine Dog", "Mahoraga"]),
        (211, "Nobara Kugisaki",    "JJK",          "Sorcerer",         140, 83, 75, 80, 82, ["Straw Doll", "Resonance", "Hairpin"]),
        (212, "Satoru Gojo",        "JJK",          "Teacher",          210, 99, 92, 95, 97, ["Infinity", "Hollow Purple", "Unlimited Void"]),
        (213, "Sukuna",             "JJK",          "King of Curses",   250, 99, 95, 93, 97, ["Dismantle", "Cleave", "Malevolent Shrine"]),
        (214, "Nanami Kento",       "JJK",          "Sorcerer",         160, 90, 85, 80, 88, ["Ratio Technique", "Overtime", "Blunt Sword"]),
        (215, "Toge Inumaki",       "JJK",          "Sorcerer",         145, 85, 78, 82, 85, ["Cursed Speech", "Don't Move", "Explode"]),
        # ── Solo Leveling ────────────────────────────────────────────
        (216, "Sung Jinwoo",        "Solo Leveling", "Hunter",          230, 97, 90, 97, 92, ["Shadow Army", "Ruler's Authority", "Monarch's Domain"]),
        (217, "Cha Hae-In",         "Solo Leveling", "Hunter",          180, 92, 82, 92, 82, ["Sword Dance", "Detect Mana", "Flash Strike"]),
        (218, "Thomas Andre",       "Solo Leveling", "National Hunter", 200, 95, 92, 85, 80, ["Collapse", "Dominator's Touch", "Titan Body"]),
        # ── The Rising of the Shield Hero ─────────────────────────────
        (219, "Naofumi Iwatani",    "Shield Hero",  "Shield Hero",      160, 72, 97, 72, 82, ["Iron Maiden", "Curse Shield", "Shield Prison"]),
        (220, "Raphtalia",          "Shield Hero",  "Demi-Human",       150, 88, 75, 85, 82, ["Illusion Sword", "Mist Strike", "Dimensional Rift"]),
        # ── Mushoku Tensei ────────────────────────────────────────────
        (221, "Rudeus Greyrat",     "Mushoku Tensei", "Mage",           155, 85, 75, 75, 97, ["Touki", "Stone Bullet", "Displacement Magic"]),
        (222, "Sylphiette",         "Mushoku Tensei", "Mage",           140, 80, 72, 72, 92, ["Teleport", "Wind Barrier", "Green Flash"]),
        # ── Inuyasha ──────────────────────────────────────────────────
        (223, "Inuyasha",           "Inuyasha",     "Half-Demon",       175, 92, 82, 88, 72, ["Wind Scar", "Backlash Wave", "Tetsusaiga"]),
        (224, "Sesshomaru",         "Inuyasha",     "Demon Lord",       200, 97, 90, 92, 85, ["Tokijin", "Bakusaiga", "Meidou"]),
        # ── Rurouni Kenshin ───────────────────────────────────────────
        (225, "Kenshin Himura",     "Rurouni Kenshin", "Rurouni",       155, 93, 78, 97, 82, ["Hiten Mitsurugi", "Ryu Tsui Sen", "Amakakeru Ryu"]),
        (226, "Makoto Shishio",     "Rurouni Kenshin", "Villain",       165, 95, 80, 90, 85, ["Honoo no Hajiki", "Guren Kaina", "Mugenjin"]),
        # ── Cowboy Bebop ──────────────────────────────────────────────
        (227, "Spike Spiegel",      "Cowboy Bebop", "Bounty Hunter",    155, 88, 75, 90, 82, ["Jeet Kune Do", "Jet Shot", "Punch-Kick"]),
        (228, "Faye Valentine",     "Cowboy Bebop", "Bounty Hunter",    135, 78, 70, 85, 80, ["Blaster", "Escape", "Con Artist"]),
        # ── Trigun ───────────────────────────────────────────────────
        (229, "Vash the Stampede",  "Trigun",       "Humanoid Typhoon", 160, 90, 78, 92, 82, ["Angel Arm", "Premium Shot", "Mercy Shot"]),
        (230, "Millions Knives",    "Trigun",       "Villain",          175, 95, 85, 88, 85, ["Blade Barrage", "Plant Power", "Death Knives"]),
        # ── Black Mirror ──────────────────────────────────────────────
        (231, "Mikael Colman",      "Black Mirror", "Hacker",           110, 72, 65, 78, 90, ["Memory Edit", "Record Replay", "Grain Wipe"]),
        # ── Rick and Morty ────────────────────────────────────────────
        (232, "Rick Sanchez",       "Rick and Morty", "Mad Scientist",  120, 75, 65, 72, 100, ["Portal Gun", "Meeseeks Box", "Microverse Battery"]),
        (233, "Morty Smith",        "Rick and Morty", "Sidekick",        90, 55, 50, 70, 68, ["Mega Tree Seed", "Alien Gun", "Luck"]),
        # ── Doctor Who ───────────────────────────────────────────────
        (234, "The Doctor",         "Doctor Who",   "Time Lord",        150, 72, 70, 85, 100, ["Sonic Screwdriver", "TARDIS", "Regeneration"]),
        (235, "Dalek",              "Doctor Who",   "Villain",          180, 92, 92, 68, 75, ["Exterminate", "Force Shield", "Self-Destruct"]),
        # ── Star Wars ────────────────────────────────────────────────
        (236, "Luke Skywalker",     "Star Wars",    "Jedi",             175, 93, 85, 88, 88, ["Force Push", "Lightsaber", "Battle Meditation"]),
        (237, "Darth Vader",        "Star Wars",    "Sith",             200, 97, 90, 82, 90, ["Force Choke", "Lightsaber Fury", "Imperial March"]),
        (238, "Rey Skywalker",      "Star Wars",    "Jedi",             165, 88, 82, 85, 85, ["Dyad Bond", "Force Heal", "Lightsaber Rush"]),
        (239, "Mandalorian",        "Star Wars",    "Bounty Hunter",    155, 85, 82, 85, 80, ["Beskar Armor", "Whistling Birds", "Jetpack"]),
        (240, "Ahsoka Tano",        "Star Wars",    "Jedi",             170, 92, 85, 90, 88, ["Twin Sabers", "Force Jump", "Fulcrum"]),
        # ── Marvel ───────────────────────────────────────────────────
        (241, "Iron Man",           "Marvel",       "Hero",             200, 95, 92, 88, 97, ["Repulsor Blast", "Proton Cannon", "Extremis"]),
        (242, "Spider-Man",         "Marvel",       "Hero",             160, 88, 80, 97, 90, ["Web Swing", "Spidey Sense", "Web Barrage"]),
        (243, "Doctor Strange",     "Marvel",       "Sorcerer",         170, 90, 85, 82, 97, ["Mirror Dimension", "Eye of Agamotto", "Sling Ring"]),
        (244, "Wolverine",          "Marvel",       "Hero",             185, 93, 90, 88, 78, ["Adamantium Claws", "Berserker Rage", "Regenerate"]),
        (245, "Black Panther",      "Marvel",       "Hero",             175, 90, 90, 92, 88, ["Vibranium Suit", "Kinetic Pulse", "Panther Habit"]),
        # ── DC ───────────────────────────────────────────────────────
        (246, "Superman",           "DC",           "Hero",             300, 98, 98, 99, 88, ["Heat Vision", "Super Speed", "Flight"]),
        (247, "Batman",             "DC",           "Hero",             170, 88, 88, 90, 99, ["Batarang", "Detective Mode", "Batsuit"]),
        (248, "Wonder Woman",       "DC",           "Hero",             200, 95, 92, 90, 88, ["Lasso of Truth", "Godkiller", "Shield Bash"]),
        (249, "The Flash",          "DC",           "Hero",             180, 90, 80, 100, 85, ["Infinite Mass Punch", "Time Travel", "Speed Force"]),
        (250, "Green Lantern",      "DC",           "Hero",             180, 88, 85, 88, 88, ["Constructs", "Power Ring", "Oath"]),
        # ── Warhammer ────────────────────────────────────────────────
        (251, "Space Marine",       "Warhammer 40K", "Soldier",         210, 95, 95, 80, 72, ["Bolter", "Chainsword", "Power Fist"]),
        (252, "Commissar",          "Warhammer 40K", "Officer",         170, 85, 82, 78, 80, ["Execute Coward", "Bolt Pistol", "Command"]),
        # ── Sekiro ───────────────────────────────────────────────────
        (253, "Wolf (Sekiro)",      "Sekiro",       "Shinobi",          165, 93, 82, 95, 82, ["Perilous Sweep", "Mortal Blade", "Dragon Flash"]),
        (254, "Isshin",             "Sekiro",       "Ashina Sword",     200, 98, 88, 92, 88, ["Dragon Flash", "Ashina Cross", "Shockwave"]),
        # ── Bloodborne ───────────────────────────────────────────────
        (255, "The Hunter",         "Bloodborne",   "Hunter",           175, 92, 80, 90, 80, ["Whirligig Saw", "Ludwig's Holy Blade", "Cannon"]),
        (256, "Lady Maria",         "Bloodborne",   "Hunter",           180, 95, 82, 93, 82, ["Rakuyo", "Bloodflame", "Phantasms"]),
        (257, "Gehrman",            "Bloodborne",   "First Hunter",     190, 97, 85, 90, 88, ["Burial Blade", "Flamesprayer", "First Hunter's Badge"]),
        # ── God of War ────────────────────────────────────────────────
        (258, "Kratos",             "God of War",   "God",              230, 98, 93, 88, 82, ["Leviathan Axe", "Blades of Chaos", "Spartan Rage"]),
        (259, "Atreus",             "God of War",   "Demigod",          150, 80, 72, 90, 82, ["Shock Arrows", "Runic Summon", "Spartan Charge"]),
        (260, "Freya",              "God of War",   "Goddess",          165, 85, 80, 82, 90, ["Nornir Magic", "Summon", "Valkyrie Form"]),
        # ── Horizon ───────────────────────────────────────────────────
        (261, "Aloy",               "Horizon",      "Hunter",           155, 85, 75, 88, 90, ["Override", "Sharpshot Bow", "Blast Trap"]),
        (262, "Sylens",             "Horizon",      "Rogue",            140, 80, 72, 85, 92, ["Lance Override", "HEPHAESTUS", "Spear Throw"]),
        # ── Ghost of Tsushima ─────────────────────────────────────────
        (263, "Jin Sakai",          "Ghost of Tsushima", "Samurai",     165, 92, 82, 88, 82, ["Ghost Strike", "Stone Stand", "Mythic Tale"]),
        (264, "Lady Masako",        "Ghost of Tsushima", "Samurai",     155, 88, 78, 85, 80, ["Masako's Pursuit", "Blade Strike", "Archery"]),
        # ── Cyberpunk (misc) ──────────────────────────────────────────
        (265, "Morgan Blackhand",   "Cyberpunk",    "Solo",             170, 93, 82, 90, 82, ["Militech Assault", "Black Hand Strike", "Net Sever"]),
        (266, "Samurai Cyberpunk",  "Cyberpunk",    "Rockerboy",        140, 78, 70, 82, 78, ["Stage Dive", "Thrash Riff", "Riot"]),
        # ── Anime (misc) ──────────────────────────────────────────────
        (267, "Rimuru (God form)",  "Slime S3",     "True Dragon",      300, 99, 99, 99, 99, ["Infinite Predator", "Void God", "Harvest Festival"]),
        (268, "Anos Voldigoad",     "Misfit Demon Lord", "Demon King",  300, 99, 99, 95, 99, ["Venuzdonoa", "Revive", "Eye of Destruction"]),
        (269, "Escanor",            "Seven Deadly Sins", "The One",     280, 99, 97, 90, 85, ["Rhitta", "The One", "Cruel Sun"]),
        (270, "Meliodas",           "Seven Deadly Sins", "Dragon Sin",  260, 98, 92, 95, 88, ["Full Counter", "Assault Mode", "Lostvayne"]),
        # ── Berserk ───────────────────────────────────────────────────
        (271, "Guts",               "Berserk",      "Black Swordsman",  200, 97, 85, 88, 80, ["Dragonslayer", "Berserker Armor", "Canon Arm"]),
        (272, "Griffith",           "Berserk",      "Hawk",             190, 95, 88, 92, 90, ["Beherit", "Band of Hawk", "Apostle Form"]),
        (273, "Casca",              "Berserk",      "Swordwoman",       160, 88, 80, 90, 82, ["Dragon Slayer (small)", "Hawk Strike", "Femto Guard"]),
        # ── Code Geass ───────────────────────────────────────────────
        (274, "Lelouch vi Britannia", "Code Geass", "Emperor",         145, 72, 68, 78, 99, ["Geass", "Zero Requiem", "Chess Stratagem"]),
        (275, "C.C.",               "Code Geass",   "Immortal",         140, 70, 68, 72, 90, ["Geass Transfer", "Immortality", "Cheese-kun"]),
        (276, "Suzaku Kururugi",    "Code Geass",   "Knight",           170, 92, 82, 97, 80, ["Lancelot Albion", "Gefjun Disturber", "FLEIJA"]),
        # ── Evangelion (misc) ─────────────────────────────────────────
        (277, "Unit-02 Beast Mode", "Evangelion",   "Eva",              230, 97, 90, 90, 55, ["Frenzy", "Spear Throw", "Beast Screech"]),
        # ── Trigun (misc) ─────────────────────────────────────────────
        (278, "Legato Bluesummers", "Trigun",       "Villain",          140, 85, 72, 78, 88, ["Marionette", "Psychokinesis", "Death Wish"]),
        # ── Samurai Champloo ──────────────────────────────────────────
        (279, "Mugen",              "Samurai Champloo", "Swordsman",    165, 92, 78, 95, 72, ["Breakdance Sword", "Chaos Slash", "Vagabond"]),
        (280, "Jin",                "Samurai Champloo", "Ronin",        160, 90, 82, 90, 82, ["Mugen Slash", "Ronin Strike", "Mujushin"]),
        # ── Anime extra ───────────────────────────────────────────────
        (281, "Giorno (GER)",       "JoJo S5",      "Boss",             240, 99, 95, 90, 99, ["Gold Experience Requiem", "Life Overflow", "Reset"]),
        (282, "Diavolo",            "JoJo S5",      "Villain",          200, 97, 90, 90, 90, ["King Crimson", "Epitaph", "Erase Time"]),
        (283, "Funny Valentine",    "JoJo S7",      "President",        195, 93, 88, 85, 92, ["Dirty Deeds Done Dirt Cheap", "Love Train", "Parallel Alternate"]),
        (284, "Kars",               "JoJo S2",      "Pillar Man",       220, 97, 92, 92, 88, ["Ultimate Life Form", "Blade Arms", "Vampire Mask"]),
        (285, "Wamuu",              "JoJo S2",      "Pillar Man",       200, 95, 90, 90, 82, ["Divine Sandstorm", "Holy Sandstorm", "Wind Mode"]),
        # ── Avatar ───────────────────────────────────────────────────
        (286, "Aang",               "Avatar",       "Avatar",           170, 85, 82, 90, 88, ["Avatar State", "Energybending", "All Elements"]),
        (287, "Zuko",               "Avatar",       "Prince",           160, 88, 80, 85, 82, ["Firebending", "Blue Dragon", "Comet Form"]),
        (288, "Toph Beifong",       "Avatar",       "Earthbender",      155, 90, 88, 80, 85, ["Metalbending", "Seismic Sense", "Earth Wall"]),
        (289, "Katara",             "Avatar",       "Waterbender",      150, 82, 78, 78, 88, ["Bloodbending", "Healing", "Water Whip"]),
        (290, "Azula",              "Avatar",       "Princess",         165, 92, 80, 85, 92, ["Blue Fire", "Lightning", "Domination"]),
        # ── Random sci-fi / misc ─────────────────────────────────────
        (291, "Commander Shepard F", "Mass Effect", "Spectre",          170, 88, 82, 85, 92, ["Vanguard Charge", "Pull", "N7 Special"]),
        (292, "SHODAN",             "System Shock", "AI",               100, 82, 65, 98, 100, ["Cyber Takeover", "Bot Army", "Genetic Override"]),
        (293, "Master (Doom)",      "Doom",         "Slayer",           220, 97, 92, 90, 75, ["BFG 9000", "Chainsaw", "Glory Kill"]),
        (294, "GLaDOS Awakened",    "Portal 2",     "AI",               110, 85, 72, 95, 100, ["Moonshotgun", "Neurotoxin II", "Panel Storm"]),
        (295, "HAL 9000",           "2001",         "AI",               100, 75, 65, 92, 100, ["Airlock", "System Control", "I'm Sorry Dave"]),
        (296, "Samus Aran",         "Metroid",      "Bounty Hunter",    200, 93, 90, 90, 88, ["Hyper Beam", "Screw Attack", "Morph Ball Bomb"]),
        (297, "Mega Man X",         "Mega Man",     "Reploid",          175, 90, 85, 88, 85, ["Nova Strike", "Giga Attack", "Ultimate Armor"]),
        (298, "Zero (Mega Man)",    "Mega Man",     "Reploid",          180, 95, 85, 92, 82, ["Z-Saber", "Dark Hold", "Rekkoha"]),
        (299, "Kirby",              "Kirby",        "Star Warrior",     140, 80, 82, 80, 72, ["Inhale", "Ultra Sword", "Star Rod"]),
        (300, "Dark Samus",         "Metroid",      "Phazon Entity",    200, 93, 90, 88, 82, ["Phazon Beam", "Dark Burst", "Phazon Overdrive"]),
        # ── Final three ──────────────────────────────────────────────
        (301, "Shovel Knight",      "Shovel Knight", "Knight",          150, 85, 82, 80, 72, ["Shovel Slash", "Anchor", "Phase Locket"]),
        (302, "Cuphead",            "Cuphead",      "Gambler",          110, 78, 70, 85, 68, ["EX Charge", "Peashooter", "Smoke Bomb"]),
        (303, "Okabe (Mad Scientist)", "Steins;Gate", "Organization",   125, 68, 65, 70, 95, ["Phone Microwave", "El Psy Kongroo", "Mad Scientist Howl"]),
    ]

    return [
        Character(
            id=r[0], name=r[1], universe=r[2], role=r[3],
            hp=r[4], attack=r[5], defense=r[6], speed=r[7], intelligence=r[8],
            abilities=list(r[9]),
        )
        for r in raw
    ]


ALL_CHARACTERS: List[Character] = get_all_characters()
CHARACTER_MAP: dict = {c.id: c for c in ALL_CHARACTERS}
