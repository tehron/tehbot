from pony.orm import *
from datetime import datetime
import json

def define_entities(db):
    class Setting(db.Entity):
        name = Required(str, unique=True)
        value = Optional(str, max_len=2048)

        def get_value(self):
            return json.loads(self.value)

        def set_value(self, value):
            self.value = json.dumps(value)

    class Message(db.Entity):
        ts = Required(datetime)
        event = Required(str)
        type = Required(int)
        ircid = Required(str)
        target = Optional(str, nullable=True)
        nick = Optional(str, nullable=True)
        message = Optional(str, nullable=True, max_len=510)
        composite_index(ts, nick, ircid)
