from pony.orm import *
from pony.orm.dbapiprovider import StrConverter
import os.path
from enum import Enum
import time
import datetime

class EnumConverter(StrConverter):
    def validate(self, val):
        if not isinstance(val, Enum):
            raise ValueError('Must be an Enum.  Got {}'.format(type(val)))
        return val

    def py2sql(self, val):
        return val.name

    def sql2py(self, value):
        # Any enum type can be used, so py_type ensures the correct one is used to create the enum instance
        return self.py_type[value]

db = Database("sqlite", "sldb.sqlite", create_db=True)
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
    settings = Required(Json)

class Attributes(db.Entity):
    id = PrimaryKey(int, auto=True)
    gender = Optional("Gender")
    race = Optional("Race")
    player = Optional("Player")
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
    race = Optional("Race")
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
    player = Optional("Player")
    race = Optional("Race")
    attack = Required(float, default=0)
    defense = Required(float, default=0)
    min_dmg = Required(float, default=0)
    max_dmg = Required(float, default=0)
    marm = Required(float, default=0)
    farm = Required(float, default=0)
    attack_time = Required(float, default=0)
    max_hp = Required(float, default=0)
    max_mp = Required(float, default=0)
    max_weight = Required(float, default=0)

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

class Item(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Required(str)
    ammo = Required(int, default=0)
    amount = Required(int, default=1)
    health = Required(float, default=0)
    modifiers = Required(str)
    duration = Required(float, default=0)
    microtime = Required(float)

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
    name = Required(str, unique=True)
    attributes = Required(Attributes)

class Race(db.Entity):
    id = PrimaryKey(int, auto=True)
    players = Set("Player")
    name = Required(str, unique=True)
    is_npc = Required(bool, default=False)
    base_hp = Required(float)
    base_mp = Required(float)
    height = Required(float)
    age = Required(float)
    weight = Required(float)
    attributes = Required(Attributes)
    skills = Required(Skills)
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
    content = Required(str)

class Spell(db.Entity):
    id = PrimaryKey(int, auto=True)
    players = Set("Player")
    name = Required(str)

class Party(db.Entity):
    id = PrimaryKey(int, auto=True)
    name = Optional(str)
    members = Set("Player")
    contact_eta = Required(float)
    action = Required(PartyAction)
    target = Optional(str)
    eta = Required(int)
    last_action = Required(PartyAction)
    last_target = Optional(str)
    last_eta = Required(int)
    options = Required(int)
    ban = Required(str)
    distance = Required(str)
    xp = Required(int)
    xp_total = Required(int)
    level = Required(int)

class Player(db.Entity):
    id = PrimaryKey(int, auto=True)
    network_id = Required(str)
    party = Optional(Party)
    classname = Optional(str)
    name = Optional(str)
    title = Optional(str)
    gender = Required(Gender)
    race = Required(Race)
    birthday = Required(float)
    height = Required(float)
    weight = Required(float)
    options = Required(Json)
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

    bounty = Required(int)
    bounty_done = Required(int)
    quests_done = Required(int)
    known_spells = Set(Spell)
    known_places = Optional(str)
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
    properties = Required(Properties)
    knowledge = Required(Knowledge)
    lock = Required(int)
    transport = Required(int)

    @staticmethod
    def hp_per_body():
        return 3.0

    def option(self, key, default=None):
        return self.options[key] if self.options.has_key(key) else default

    def effective_level(self):
        # TODO
        return self.level

    def init_player(self):
        self.attributes.essence += 6.0
        self.hp = self.max_hp()

    def body(self):
        return self.race.attributes.body + self.gender.attributes.body + self.attributes.body

    def base_hp_type(self):
        return 1.0 if self.race.is_npc else 4.0

    def base_hp(self):
        return self.race.base_hp + self.base_hp_type()

    def max_hp(self):
        return self.body() * Player.hp_per_body() + self.base_hp()


@db_session
def populate_database():
    male = Gender(name="male", attributes=Attributes(strength=1, wisdom=1))
    female = Gender(name="female", attributes=Attributes(charisma=2, intelligence=1))
    w = Word(content="Renraku")
    w = Word(content="Hello")
    w = Word(content="Yes")
    w = Word(content="No")
    w = Word(content="Shadowrun")
    w = Word(content="Hire")
    w = Word(content="Blackmarket")
    w = Word(content="Cyberware")
    w = Word(content="Magic")
    w = Word(content="Redmond")
    w = Word(content="Seattle")
    w = Word(content="Delaware")

    fairy = Race(name="fairy", base_hp=3, base_mp=6, height=1.20, age=20, weight=40,
            attributes=Attributes(body=1, magic=1, strength=0, quickness=3, wisdom=1, intelligence=4, charisma=3, luck=1),
            properties=Properties(),
            skills=Skills())
    elve = Race(name="elve", base_hp=4, base_mp=4, height=1.40, age=32, weight=50,
            attributes=Attributes(body=1, magic=1, strength=0, quickness=3, wisdom=0, intelligence=2, charisma=1, luck=0),
            properties=Properties(),
            skills=Skills())
    halfelve = Race(name="half-elve", base_hp=5, base_mp=2, height=1.60, age=28, weight=60,
            attributes=Attributes(body=1, magic=-1, strength=1, quickness=2, wisdom=0, intelligence=1, charisma=1, luck=0),
            properties=Properties(),
            skills=Skills())
    vampire = Race(name="vampire", base_hp=5, base_mp=3, height=1.85, age=140, weight=70,
            attributes=Attributes(body=0, magic=1, strength=2, quickness=2, wisdom=0, intelligence=2, charisma=0, luck=0),
            properties=Properties(),
            skills=Skills())
    darkelve = Race(name="dark-elve", base_hp=5, base_mp=1, height=1.70, age=26, weight=70,
            attributes=Attributes(body=1, magic=-1, strength=2, quickness=2, wisdom=0, intelligence=1, charisma=1, luck=0),
            properties=Properties(),
            skills=Skills())
    woodelve = Race(name="wood-elve", base_hp=5, base_mp=2, height=1.80, age=24, weight=75,
            attributes=Attributes(body=1, magic=-1, strength=1, quickness=2, wisdom=0, intelligence=1, charisma=1, luck=0),
            properties=Properties(),
            skills=Skills())
    human = Race(name="human", base_hp=6, base_mp=0, height=1.85, age=30, weight=80,
            attributes=Attributes(body=2, magic=-1, strength=1, quickness=1, wisdom=0, intelligence=0, charisma=0, luck=0),
            properties=Properties(),
            skills=Skills())
    gnome = Race(name="gnome", base_hp=6, base_mp=0, height=1.30, age=32, weight=55,
            attributes=Attributes(body=2, magic=-1, strength=1, quickness=1, wisdom=0, intelligence=0, charisma=0, luck=0),
            properties=Properties(),
            skills=Skills())
    dwarf = Race(name="dwarf", base_hp=6, base_mp=0, height=1.45, age=34, weight=65,
            attributes=Attributes(body=2, magic=-1, strength=1, quickness=1, wisdom=0, intelligence=0, charisma=0, luck=0),
            properties=Properties(),
            skills=Skills())
    halfork = Race(name="half-ork", base_hp=7, base_mp=-1, height=1.95, age=24, weight=80,
            attributes=Attributes(body=2, magic=-1, strength=2, quickness=1, wisdom=0, intelligence=0, charisma=0, luck=0),
            properties=Properties(),
            skills=Skills())
    halftroll = Race(name="half-troll", base_hp=8, base_mp=-2, height=2.00, age=24, weight=90,
            attributes=Attributes(body=3, magic=-1, strength=2, quickness=0, wisdom=0, intelligence=0, charisma=0, luck=0),
            properties=Properties(),
            skills=Skills())
    ork = Race(name="ork", base_hp=9, base_mp=-3, height=2.05, age=22, weight=100,
            attributes=Attributes(body=3, magic=-2, strength=3, quickness=0, wisdom=0, intelligence=0, charisma=0, luck=0),
            properties=Properties(),
            skills=Skills())
    troll = Race(name="troll", base_hp=10, base_mp=-4, height=2.15, age=18, weight=110,
            attributes=Attributes(body=3, magic=-2, strength=3, quickness=0, wisdom=0, intelligence=0, charisma=0, luck=0),
            properties=Properties(),
            skills=Skills())
    gremlin = Race(name="gremlin", base_hp=11, base_mp=-6, height=0.50, age=1, weight=10,
            attributes=Attributes(body=1, magic=-3, strength=0, quickness=2, wisdom=0, intelligence=0, charisma=0, luck=0),
            properties=Properties(),
            skills=Skills())
    # NPC races
    animal = Race(name="animal", is_npc=True, base_hp=0, base_mp=0, height=1.60, age=2, weight=70,
            attributes=Attributes(body=0, magic=0, strength=0, quickness=0, wisdom=0, intelligence=0, charisma=0, luck=0),
            properties=Properties(),
            skills=Skills())
    droid = Race(name="droid", is_npc=True, base_hp=0, base_mp=0, height=1.60, age=2, weight=70,
            attributes=Attributes(body=0, magic=0, strength=0, quickness=0, wisdom=0, intelligence=0, charisma=0, luck=0),
            properties=Properties(),
            skills=Skills())
    dragon = Race(name="dragon", is_npc=True, base_hp=0, base_mp=0, height=5.00, age=6000, weight=400,
            attributes=Attributes(body=8, magic=8, strength=12, quickness=3, wisdom=12, intelligence=12, charisma=0, luck=0),
            properties=Properties(),
            skills=Skills())
    Shadowlamb(id=1, time=time.mktime(datetime.date(2038, 1, 1).timetuple()), db_version=1, settings={})

@db_session
def upgrade_database_1():
    def uprace(race, **kwargs):
        r = Race.get(name=race)
        for k, v in kwargs.items():
            for x in [r.attributes, r.skills, r.properties]:
                dt = x.to_dict()
                found = dt.has_key(k)
                if found:
                    dt[k] += v
                    x.set(**dt)
                    break
            if not found:
                raise Exception("Key not found in Race: %s" % k)

    uprace("fairy", body=0, magic=5, strength=-2, quickness=3, wisdom=4, intelligence=4, charisma=4, attack=1, luck=3)
    uprace("elve", body=1, magic=4, strength=-1, quickness=3, wisdom=2, intelligence=3, charisma=2, attack=2, bows=1)
    uprace("half-elve", body=1, magic=3, strength=0, quickness=3, wisdom=2, intelligence=2, charisma=2, attack=3, bows=2)
    uprace("vampire", body=0, magic=3, strength=0, quickness=4, wisdom=2, intelligence=3, charisma=1, attack=4)
    uprace("dark-elve", body=1, magic=2, strength=0, quickness=3, wisdom=2, intelligence=2, charisma=2, attack=5, bows=2)
    uprace("wood-elve", body=1, magic=1, strength=0, quickness=3, wisdom=1, intelligence=2, charisma=2, attack=6, bows=2)
    uprace("human", body=2, magic=0, strength=0, quickness=3, wisdom=1, intelligence=2, charisma=2, attack=7)
    uprace("gnome", body=2, magic=0, strength=0, quickness=3, wisdom=1, intelligence=2, charisma=1, attack=8, luck=1)
    uprace("dwarf", body=3, magic=0, strength=1, quickness=2, wisdom=1, intelligence=2, charisma=1, attack=9, luck=1)
    uprace("half-ork", body=3, magic=-1, strength=1, quickness=2, wisdom=1, intelligence=2, charisma=1, attack=10)
    uprace("half-troll", body=3, magic=-2, strength=2, quickness=2, wisdom=0, intelligence=1, charisma=0, attack=11)
    uprace("ork", body=4, magic=-3, strength=3, quickness=1, wisdom=1, intelligence=1, charisma=0, attack=12)
    uprace("troll", body=4, magic=-4, strength=4, quickness=0, wisdom=0, intelligence=0, charisma=0, attack=13, essence=-0.2)
    uprace("gremlin", body=4, magic=-5, strength=3, quickness=1, wisdom=0, intelligence=0, charisma=-1, attack=14, reputation=2, essence=-0.5)
    # NPC races
    uprace("animal", body=0, magic=0, strength=0, quickness=0, wisdom=0, intelligence=0, charisma=0, attack=5)
    uprace("droid", body=0, magic=0, strength=0, quickness=0, wisdom=0, intelligence=0, charisma=-3, attack=10, reputation=0, essence=0)
    uprace("dragon", body=8, magic=8, strength=8, quickness=0, wisdom=8, intelligence=8, charisma=0, attack=15, reputation=12, essence=2)

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
