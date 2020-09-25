from pony.orm import *
from pony.orm.dbapiprovider import StrConverter
import os.path
from enum import Enum
import time
import datetime
import tehbot

class EnumConverter(StrConverter):
    def validate(converter, val, obj=None):
        if not isinstance(val, Enum):
            raise ValueError('Must be an Enum.  Got {}'.format(type(val)))
        return val

    def py2sql(converter, val):
        return val.name

    def sql2py(converter, value):
        # Any enum type can be used, so py_type ensures the correct one is used to create the enum instance
        return converter.py_type[value]

d = os.path.abspath(os.path.dirname(tehbot.__file__))
db = Database("sqlite", os.path.join(d, "..", "data", "sldb.sqlite"), create_db=True)
db.provider.converter_classes.append((Enum, EnumConverter))


class PartyAction(Enum):
    delete = 0
    talk = 1
    fight = 2
    inside = 3
    outside = 4
    sleep = 5
    travel = 6
    explore = 7
    goto = 8
    hunt = 9
    hijack = 10


class Shadowlamb(db.Entity):
    id = PrimaryKey(int)
    db_version = Required(int)
    time = Required(float)
    settings = Required(str)

class Attributes(db.Entity):
    id = PrimaryKey(int, auto=True)
    gender = Optional("Gender")
    race = Optional("Race", reverse="attributes")
    base_race = Optional("Race", reverse="base_attributes")
    player = Optional("Player")
    modifiers = Optional("Modifiers")
    body = Required(float, default=0)
    magic = Required(float, default=0)
    strength = Required(float, default=0)
    quickness = Required(float, default=0)
    wisdom = Required(float, default=0)
    intelligence = Required(float, default=0)
    charisma = Required(float, default=0)
    luck = Required(float, default=0)
    reputation = Required(float, default=0)
    essence = Required(float, default=0)

class Skills(db.Entity):
    id = PrimaryKey(int, auto=True)
    player = Optional("Player")
    race = Optional("Race", reverse="skills")
    base_race = Optional("Race", reverse="base_skills")
    modifiers = Optional("Modifiers")
    melee = Required(float, default=0)
    ninja = Required(float, default=0)
    swordsman = Required(float, default=0)
    viking = Required(float, default=0)
    firearms = Required(float, default=0)
    bows = Required(float, default=0)
    pistols = Required(float, default=0)
    shotguns = Required(float, default=0)
    smgs = Required(float, default=0)
    hmgs = Required(float, default=0)
    computers = Required(float, default=0)
    electronics = Required(float, default=0)
    biotech = Required(float, default=0)
    negotiation = Required(float, default=0)
    sharpshooter = Required(float, default=0)
    searching = Required(float, default=0)
    lockpicking = Required(float, default=0)
    thief = Required(float, default=0)
    orcas = Required(float, default=0)
    elephants = Required(float, default=0)
    spellatk = Required(float, default=0)
    spelldef = Required(float, default=0)
    casting = Required(float, default=0)
    alchemy = Required(float, default=0)

class Properties(db.Entity):
    id = PrimaryKey(int, auto=True)
    race = Optional("Race")
    modifiers = Optional("Modifiers")
    attack = Required(float, default=0)
    defense = Required(float, default=0)
    min_dmg = Required(float, default=0)
    max_dmg = Required(float, default=0)
    marm = Required(float, default=0)
    farm = Required(float, default=0)
    attack_time = Required(float, default=0)

class Modifiers(db.Entity):
    id = PrimaryKey(int, auto=True)
    weapon = Optional("Weapon")
    player_item = Optional("PlayerItem")
    attributes = Optional(Attributes)
    skills = Optional(Skills)
    properties = Optional(Properties)

    def get(self, modifier):
        for m in [self.attributes, self.skills, self.properties]:
            try:
                v = getattr(m, modifier)
                return v
            except AttributeError:
                pass

        raise AttributeError("Unknown modifier: %s" % modifier)

class Conditions(db.Entity):
    id = PrimaryKey(int, auto=True)
    frozen = Required(float, default=0)
    sick = Required(float, default=0)
    cold = Required(float, default=0)
    alc = Required(float, default=0)
    poisoned = Required(float, default=0)
    caf = Required(float, default=0)
    happy = Required(float, default=0)
    weight = Required(float, default=0)

class Feelings(db.Entity):
    id = PrimaryKey(int, auto=True)
    player = Optional("Player")
    food = Required(float, default=0)
    water = Required(float, default=0)
    sleepy = Required(float, default=0)
    stomach = Required(float, default=0)

class Equipment(db.Entity):
    id = PrimaryKey(int, auto=True)
    player = Optional("Player")
    weapon = Optional("Weapon")

    def summods(self, mod):
        v = 0
        for e in [self.weapon]:
            v += e.modifiers.get(mod)
        return v

    def level(self):
        return 0

    def body(self):
        return 0

    def magic(self):
        return 0

    def strength(self):
        return 0

    def quickness(self):
        return 0

    def wisdom(self):
        return 0

    def intelligence(self):
        return 0

    def charisma(self):
        return 0

    def luck(self):
        return 0

    def reputation(self):
        return 0

    def essence(self):
        return 0

    def casting(self):
        return 0

    def base_defense(self):
        return 0

    def defense(self):
        return 0

    def attack(self):
        attack, min_dmg, max_dmg = self.weapon.combat_modifiers(self.player)
        return self.summods("attack") + attack

    def min_dmg(self):
        attack, min_dmg, max_dmg = self.weapon.combat_modifiers(self.player)
        return self.summods("min_dmg") + min_dmg

    def max_dmg(self):
        attack, min_dmg, max_dmg = self.weapon.combat_modifiers(self.player)
        return self.summods("max_dmg") + max_dmg

    def marm(self):
        return 0

    def farm(self):
        return 0



class PlayerItem(db.Entity):
    id = PrimaryKey(int, auto=True)
    player = Required("Player")
    base = Required("Item")
    modifiers = Optional(Modifiers)

class Item(db.Entity):
    id = PrimaryKey(int, auto=True)
    player_item = Set(PlayerItem)
    name = Required(str, unique=True, max_len=64)
    description = Optional(str)
    level = Required(int, default=-1)
    weight = Required(float)
    price = Required(float)
    #health = Required(float, default=0)
    #duration = Required(float, default=0)

class Weapon(Item):
    equipment = Set(Equipment)
    modifiers = Required(Modifiers)
    attack_time = Required(float)
    range = Required(float)
    equip_time = Required(float)
    unequip_time = Required(float)

    def __init__(self, **kwargs):
        params = {
                "equip_time" : 30,
                "unequip_time" : 30
                }
        params.update(kwargs)
        Item.__init__(self, **params)

class Rune(Item):
    pass

class MeleeWeapon(Weapon):
    def __init__(self, **kwargs):
        params = {
                "range" : 2.0,
                "equip_time" : 35,
                "unequip_time" : 25
                }
        params.update(kwargs)
        Weapon.__init__(self, **params)

    def combat_modifiers(self, player):
        strength = player.strength()
        melee = player.melee()

        attack =  3.0 + 1.0 * strength + 2.5 * melee
        min_dmg = 0.7 + 0.2 * strength + 0.5 * melee
        max_dmg = 1.7 + 0.5 * strength + 1.2 * melee

        return attack, min_dmg, max_dmg


class NinjaWeapon(MeleeWeapon):
    def combat_modifiers(self, player):
        strength = player.strength()
        melee = player.melee()
        ninja = player.ninja()

        attack =  3.0 + 0.8 * strength + 0.8 * melee + 2.3 * ninja
        min_dmg = 0.9 + 0.2 * strength + 0.1 * melee + 0.6 * ninja
        max_dmg = 1.5 + 0.5 * strength + 0.2 * melee + 0.8 * ninja

        return attack, min_dmg, max_dmg

class FireWeapon(Weapon):
    ammo = Required(int, default=0)



class PlayerStats(db.Entity):
    id = PrimaryKey(int, auto=True)
    player = Optional("Player")
    xp_total = Required(float, default=0)
    karma_total = Required(float, default=0)
    bad_karma_total = Required(float, default=0)
    nr_items_looted = Required(int, default=0)
    nr_items_sold = Required(int, default=0)
    nr_items_bought = Required(int, default=0)
    nr_items_dropped = Required(int, default=0)
    nr_items_given = Required(int, default=0)
    nr_items_received = Required(int, default=0)
    ny_looted = Required(float, default=0)
    ny_spent = Required(float, default=0)
    ny_income = Required(float, default=0)
    ny_given = Required(float, default=0)
    ny_received = Required(float, default=0)
    nr_kills_mob = Required(int, default=0)
    nr_kills_npc = Required(int, default=0)
    nr_kills_human = Required(int, default=0)
    nr_kills_runner = Required(int, default=0)


class Gender(db.Entity):
    id = PrimaryKey(int, auto=True)
    players = Set("Player")
    name = Required(str, unique=True, max_len=20)
    attributes = Required(Attributes)

class Race(db.Entity):
    id = PrimaryKey(int, auto=True)
    players = Set("Player")
    name = Required(str, unique=True, max_len=64)
    is_npc = Required(bool, default=False)
    base_hp = Required(float)
    base_mp = Required(float)
    height = Required(float)
    age = Required(float)
    own_weight = Required(float)
    attributes = Required(Attributes)
    skills = Required(Skills)
    base_attributes = Required(Attributes)
    base_skills = Required(Skills)
    properties = Required(Properties)

class Knowledge(db.Entity):
    id = PrimaryKey(int, auto=True)
    players = Set("Player")
    indian_culture = Required(float, default=0)
    indian_language = Required(float, default=0)
    math = Required(float, default=0)
    crypto = Required(float, default=0)
    stegano = Required(float, default=0)

class Word(db.Entity):
    id = PrimaryKey(int, auto=True)
    players = Set("Player")
    name = Required(str, unique=True, max_len=64)

class Place(db.Entity):
    id = PrimaryKey(int, auto=True)
    players = Set("Player")
    name = Required(str, unique=True, max_len=64)

class Spell(db.Entity):
    id = PrimaryKey(int, auto=True)
    players = Set("Player")
    name = Required(str, unique=True, max_len=64)

class Party(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Optional(str)
    members = Set("Player")
    contact_eta = Required(float, default=0)
    action = Required(PartyAction, default=PartyAction.delete)
    target = Optional(str)
    eta = Required(float, default=0)
    last_action = Required(PartyAction, default=PartyAction.delete)
    last_target = Optional(str)
    last_eta = Required(float, default=0)
    options = Required(str)
    ban = Optional(str)
    distance = Optional(str)
    xp = Required(int, default=0)
    xp_total = Required(int, default=0)
    level = Required(int, default=0)

class Player(db.Entity):
    id = PrimaryKey(int, auto=True)
    nick = Required(str)
    network_id = Required(str)
    party = Optional(Party)
    name = Required(str)
    classname = Optional(str)
    title = Optional(str)
    gender = Required(Gender)
    race = Required(Race)
    birthday = Required(float)
    height = Required(float)
    own_weight = Required(float)
    options = Required(str)
    distance = Required(float)

    level = Required(int)
    hp = Required(float)
    mp = Required(float)
    xp = Required(float)
    xp_level = Required(float)
    karma = Required(float)
    bad_karma = Required(float)
    nuyen = Required(float)
    known_words = Set(Word)
    known_places = Set(Place)
    known_spells = Set(Spell)

    bounty = Required(int)
    bounty_done = Required(int)
    quests_done = Required(int)
    bank_nuyen = Required(float)
    bank_items = Optional(str)
    stats = Required(PlayerStats)

    effects = Optional(str)
    const_vars = Optional(str)
    combat_ai = Optional(str)
    game_ai = Optional(str)
    feelings = Required(Feelings)
    attributes = Required(Attributes)
    skills = Required(Skills)
    equipment = Required(Equipment)
    knowledge = Required(Knowledge)

    inventory = Set(PlayerItem)
    lock = Required(int)
    transport = Required(int)

    @staticmethod
    def hp_per_body():
        return 3.0

    @staticmethod
    def mp_per_magic():
        return 5.0

    @staticmethod
    def mp_per_casting():
        return 5.0

    @staticmethod
    def weight_per_strength():
        return 1.5

    @staticmethod
    def base_nuyen():
        return 0.0

    def fullname(self):
        return "%s{%s}" % (self.name, self.network_id)
    def option(self, key, default=None):
        return self.options[key] if self.options.has_key(key) else default

    def set_option(self, key, value):
        self.options[key] = value

    def init_player(self):
        self.nuyen = Player.base_nuyen()
        sk = self.skills.to_dict(exclude=["id", "player", "race", "base_race", "modifiers"])
        for k in sk:
            sk[k] = -1
        self.skills.set(**sk)

        attr = ["body", "magic", "strength", "quickness", "wisdom", "intelligence", "charisma", "luck", "reputation", "essence"]
        for a in attr:
            setattr(self.attributes, a, getattr(self.race.attributes, a))

        self.hp = self.max_hp()
        self.mp = self.max_mp()
        self.equipment = Equipment(weapon=Weapon.get(name="Fists"))
        #self.properties.

    def effective_level(self):
        return self.equipment.level()

    def body(self):
        return self.race.base_attributes.body + self.gender.attributes.body + self.attributes.body + self.equipment.body()

    def magic(self):
        return self.race.base_attributes.magic + self.gender.attributes.magic + self.attributes.magic + self.equipment.magic()

    def strength(self):
        return self.race.base_attributes.strength + self.gender.attributes.strength + self.attributes.strength + self.equipment.strength()

    def quickness(self):
        return self.race.base_attributes.quickness + self.gender.attributes.quickness + self.attributes.quickness + self.equipment.quickness()

    def wisdom(self):
        return self.race.base_attributes.wisdom + self.gender.attributes.wisdom + self.attributes.wisdom + self.equipment.wisdom()

    def intelligence(self):
        return self.race.base_attributes.intelligence + self.gender.attributes.intelligence + self.attributes.intelligence + self.equipment.intelligence()

    def charisma(self):
        return self.race.base_attributes.charisma + self.gender.attributes.charisma + self.attributes.charisma + self.equipment.charisma()

    def luck(self):
        return self.race.base_attributes.luck + self.gender.attributes.luck + self.attributes.luck + self.equipment.luck()

    def reputation(self):
        return self.race.base_attributes.reputation + self.gender.attributes.reputation + self.attributes.reputation + self.equipment.reputation()

    def essence(self):
        return self.race.base_attributes.essence + self.gender.attributes.essence + self.attributes.essence + self.equipment.essence()

    def melee(self):
        return self.race.base_skills.melee + self.skills.melee

    def ninja(self):
        return self.race.base_skills.ninja + self.skills.ninja

    def casting(self):
        return self.race.base_skills.casting + self.skills.casting + self.equipment.casting()

    def combat_stats(self):
        attack = self.race.properties.attack + self.equipment.attack()
        base_defense = self.race.properties.defense + self.equipment.defense()
        defense = self.quickness() / 4 + base_defense
        min_dmg = max(0, self.race.properties.min_dmg + self.equipment.min_dmg())
        max_dmg = max(min_dmg, self.race.properties.max_dmg + self.equipment.max_dmg())
        marm = self.race.properties.marm + self.equipment.marm()
        farm = self.race.properties.farm + self.equipment.farm()
        return (attack, defense, min_dmg, max_dmg, marm, farm)

    def weight(self):
        #TODO
        return 0.0

    def base_hp_type(self):
        return 1.0 if self.race.is_npc else 4.0

    def base_mp_type(self):
        return 0.0

    def base_hp(self):
        return self.race.base_hp + self.base_hp_type()

    def base_mp(self):
        return self.race.base_mp + self.base_mp_type()

    def base_weight(self):
        return 6.5

    def max_hp(self):
        return max(0, self.body() * Player.hp_per_body() + self.base_hp())

    def max_mp(self):
        return max(0, self.magic() * Player.mp_per_magic() + (self.casting() + 1) * Player.mp_per_casting() + self.base_mp())

    def max_weight(self):
        return max(0, self.strength() * Player.weight_per_strength() + self.base_weight())


@db_session
def populate_database():
    Word(name="Renraku")
    Word(name="Hello")
    Word(name="Yes")
    Word(name="No")
    Word(name="Shadowrun")
    Word(name="Hire")
    Word(name="Blackmarket")
    Word(name="Cyberware")
    Word(name="Magic")
    Word(name="Redmond")
    Word(name="Seattle")
    Word(name="Delaware")

    Place(name="Redmond_Hotel")

    male = Gender(name="male", attributes=Attributes(strength=1, wisdom=1))
    female = Gender(name="female", attributes=Attributes(charisma=2, intelligence=1))

    fairy = Race(name="fairy", base_hp=3, base_mp=6, height=1.20, age=20, own_weight=40,
            base_attributes=Attributes(essence=6, body=1, magic=1, strength=0, quickness=3, wisdom=1, intelligence=4, charisma=3, luck=1),
            base_skills=Skills(),
            attributes=Attributes(body=0, magic=5, strength=-2, quickness=3, wisdom=4, intelligence=4, charisma=4, luck=3),
            skills=Skills(),
            properties=Properties(attack=1))
    elve = Race(name="elve", base_hp=4, base_mp=4, height=1.40, age=32, own_weight=50,
            base_attributes=Attributes(essence=6, body=1, magic=1, strength=0, quickness=3, wisdom=0, intelligence=2, charisma=1, luck=0),
            base_skills=Skills(),
            attributes=Attributes(body=1, magic=4, strength=-1, quickness=3, wisdom=2, intelligence=3, charisma=2),
            skills=Skills(bows=1),
            properties=Properties(attack=2))
    halfelve = Race(name="half-elve", base_hp=5, base_mp=2, height=1.60, age=28, own_weight=60,
            base_attributes=Attributes(essence=6, body=1, magic=-1, strength=1, quickness=2, wisdom=0, intelligence=1, charisma=1, luck=0),
            base_skills=Skills(),
            attributes=Attributes(body=1, magic=3, strength=0, quickness=3, wisdom=2, intelligence=2, charisma=2),
            skills=Skills(bows=2),
            properties=Properties(attack=3))
    vampire = Race(name="vampire", base_hp=5, base_mp=3, height=1.85, age=140, own_weight=70,
            base_attributes=Attributes(essence=6, body=0, magic=1, strength=2, quickness=2, wisdom=0, intelligence=2, charisma=0, luck=0),
            base_skills=Skills(),
            attributes=Attributes(body=0, magic=3, strength=0, quickness=4, wisdom=2, intelligence=3, charisma=1),
            skills=Skills(),
            properties=Properties(attack=4))
    darkelve = Race(name="dark-elve", base_hp=5, base_mp=1, height=1.70, age=26, own_weight=70,
            base_attributes=Attributes(essence=6, body=1, magic=-1, strength=2, quickness=2, wisdom=0, intelligence=1, charisma=1, luck=0),
            base_skills=Skills(),
            attributes=Attributes(body=1, magic=2, strength=0, quickness=3, wisdom=2, intelligence=2, charisma=2),
            skills=Skills(bows=2),
            properties=Properties(attack=5))
    woodelve = Race(name="wood-elve", base_hp=5, base_mp=2, height=1.80, age=24, own_weight=75,
            base_attributes=Attributes(essence=6, body=1, magic=-1, strength=1, quickness=2, wisdom=0, intelligence=1, charisma=1, luck=0),
            base_skills=Skills(),
            attributes=Attributes(body=1, magic=1, strength=0, quickness=3, wisdom=1, intelligence=2, charisma=2),
            skills=Skills(bows=2),
            properties=Properties(attack=6))
    human = Race(name="human", base_hp=6, base_mp=0, height=1.85, age=30, own_weight=80,
            base_attributes=Attributes(essence=6, body=2, magic=-1, strength=1, quickness=1, wisdom=0, intelligence=0, charisma=0, luck=0),
            base_skills=Skills(),
            attributes=Attributes(body=2, magic=0, strength=0, quickness=3, wisdom=1, intelligence=2, charisma=2),
            skills=Skills(),
            properties=Properties(attack=7))
    gnome = Race(name="gnome", base_hp=6, base_mp=0, height=1.30, age=32, own_weight=55,
            base_attributes=Attributes(essence=6, body=2, magic=-1, strength=1, quickness=1, wisdom=0, intelligence=0, charisma=0, luck=0),
            base_skills=Skills(),
            attributes=Attributes(body=2, magic=0, strength=0, quickness=3, wisdom=1, intelligence=2, charisma=1, luck=1),
            skills=Skills(),
            properties=Properties(attack=8))
    dwarf = Race(name="dwarf", base_hp=6, base_mp=0, height=1.45, age=34, own_weight=65,
            base_attributes=Attributes(essence=6, body=2, magic=-1, strength=1, quickness=1, wisdom=0, intelligence=0, charisma=0, luck=0),
            base_skills=Skills(),
            attributes=Attributes(body=3, magic=0, strength=1, quickness=2, wisdom=1, intelligence=2, charisma=1, luck=1),
            skills=Skills(),
            properties=Properties(attack=9))
    halfork = Race(name="half-ork", base_hp=7, base_mp=-1, height=1.95, age=24, own_weight=80,
            base_attributes=Attributes(essence=6, body=2, magic=-1, strength=2, quickness=1, wisdom=0, intelligence=0, charisma=0, luck=0),
            base_skills=Skills(),
            attributes=Attributes(body=3, magic=-1, strength=1, quickness=2, wisdom=1, intelligence=2, charisma=1),
            skills=Skills(),
            properties=Properties(attack=10))
    halftroll = Race(name="half-troll", base_hp=8, base_mp=-2, height=2.00, age=24, own_weight=90,
            base_attributes=Attributes(essence=6, body=3, magic=-1, strength=2, quickness=0, wisdom=0, intelligence=0, charisma=0, luck=0),
            base_skills=Skills(),
            attributes=Attributes(body=3, magic=-2, strength=2, quickness=2, wisdom=0, intelligence=1, charisma=0),
            skills=Skills(),
            properties=Properties(attack=11))
    ork = Race(name="ork", base_hp=9, base_mp=-3, height=2.05, age=22, own_weight=100,
            base_attributes=Attributes(essence=6, body=3, magic=-2, strength=3, quickness=0, wisdom=0, intelligence=0, charisma=0, luck=0),
            base_skills=Skills(),
            attributes=Attributes(body=4, magic=-3, strength=3, quickness=1, wisdom=1, intelligence=1, charisma=0),
            skills=Skills(),
            properties=Properties(attack=12))
    troll = Race(name="troll", base_hp=10, base_mp=-4, height=2.15, age=18, own_weight=110,
            base_attributes=Attributes(essence=6, body=3, magic=-2, strength=3, quickness=0, wisdom=0, intelligence=0, charisma=0, luck=0),
            base_skills=Skills(),
            attributes=Attributes(body=4, magic=-4, strength=4, quickness=0, wisdom=0, intelligence=0, charisma=0, essence=-0.2),
            skills=Skills(),
            properties=Properties(attack=13))
    gremlin = Race(name="gremlin", base_hp=11, base_mp=-6, height=0.50, age=1, own_weight=10,
            base_attributes=Attributes(essence=6, body=1, magic=-3, strength=0, quickness=2, wisdom=0, intelligence=0, charisma=0, luck=0),
            base_skills=Skills(),
            attributes=Attributes(body=4, magic=-5, strength=3, quickness=1, wisdom=0, intelligence=0, charisma=-1, reputation=2, essence=-0.5),
            skills=Skills(),
            properties=Properties(attack=14))
    # NPC races
    animal = Race(name="animal", is_npc=True, base_hp=0, base_mp=0, height=1.60, age=2, own_weight=70,
            base_attributes=Attributes(body=0, magic=0, strength=0, quickness=0, wisdom=0, intelligence=0, charisma=0, luck=0),
            base_skills=Skills(),
            attributes=Attributes(body=0, magic=0, strength=0, quickness=0, wisdom=0, intelligence=0, charisma=0),
            skills=Skills(),
            properties=Properties(attack=5))
    droid = Race(name="droid", is_npc=True, base_hp=0, base_mp=0, height=1.60, age=2, own_weight=70,
            base_attributes=Attributes(body=0, magic=0, strength=0, quickness=0, wisdom=0, intelligence=0, charisma=0, luck=0),
            base_skills=Skills(),
            attributes=Attributes(body=0, magic=0, strength=0, quickness=0, wisdom=0, intelligence=0, charisma=-3, reputation=0, essence=0),
            skills=Skills(),
            properties=Properties(attack=10))
    dragon = Race(name="dragon", is_npc=True, base_hp=0, base_mp=0, height=5.00, age=6000, own_weight=400,
            base_attributes=Attributes(body=8, magic=8, strength=12, quickness=3, wisdom=12, intelligence=12, charisma=0, luck=0),
            base_skills=Skills(),
            attributes=Attributes(body=8, magic=8, strength=8, quickness=0, wisdom=8, intelligence=8, charisma=0, reputation=12, essence=2),
            skills=Skills(),
            properties=Properties(attack=15))

    Item(name="Pen", description="A pen from the Renraku office.",
            weight=0.050, price=0)
    NinjaWeapon(name="Fists", description="Your fists. You got two of them.",
            weight=0, price=0,
            attack_time=35, range=1,
            modifiers=Modifiers(attributes=Attributes(), skills=Skills(), properties=Properties(attack=3.5, min_dmg=0, max_dmg=3)))
    MeleeWeapon(name="Pike", description="An ancient looking pike. Maybe nice for ranged melee.",
            level=8, weight=1.75, price=175,
            attack_time=35, range=5,
            modifiers=Modifiers(attributes=Attributes(), skills=Skills(), properties=Properties(attack=6, min_dmg=3.5, max_dmg=7)))

    Shadowlamb(id=1, time=time.mktime(datetime.date(2038, 1, 1).timetuple()), db_version=1, settings={})

@db_session
def upgrade_database_1():
    Shadowlamb[1].db_version += 1

def init():
    db.generate_mapping(create_tables=True)

    while True:
        with db_session:
            try:
                ver = Shadowlamb[1].db_version
            except:
                populate_database()
                continue

            try:
                f = globals()["upgrade_database_%d" % ver]
            except:
                break

            f()
