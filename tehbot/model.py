from pony.orm import *
from datetime import datetime

def define_entities(db):
    class Setting(db.Entity):
        name = Required(str, unique=True)
        value = Optional(Json)

    class Message(db.Entity):
        ts = Required(datetime)
        event = Required(str)
        type = Required(int)
        ircid = Required(str)
        target = Optional(str, nullable=True)
        nick = Optional(str, nullable=True)
        message = Optional(str, nullable=True)
        composite_index(ts, nick, ircid)
