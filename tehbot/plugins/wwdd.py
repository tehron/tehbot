from tehbot.plugins import *
import random
from pony.orm import *

class WwddPlugin(StandardCommand):
    """What would dloser do?"""

    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("-a", "--add", metavar="what")

    def commands(self):
        return "wwdd"

    def create_entities(self):
        class WwddPluginData(self.db.Entity):
            text = Required(str)

    def init(self):
        StandardCommand.init(self)
        with db_session:
            if not self.db.WwddPluginData.select():
                self.db.WwddPluginData(text="%s says: ... (can you feel the silence?)")
                self.db.WwddPluginData(text="%s says: you're a moron!")
                self.db.WwddPluginData(text="%s says: i really like this (in a really high voice)")
                self.db.WwddPluginData(text="%s says: i love you (and dies)")
                self.db.WwddPluginData(text="%s pukes")
                self.db.WwddPluginData(text="%s says: i will give it. (but i won't)")
                self.db.WwddPluginData(text="%s says: so helpful")

    @db_session
    def execute_parsed(self, connection, event, extra):
        if self.pargs.add is None:
            what = self.db.WwddPluginData.select_random(1)

            if what:
                return what[0].text % "dloser"
            return

        what = self.pargs.add

        if not self.is_privileged(extra):
            return self.request_priv(extra)

        if what.find("%s") < 0:
            return "Error: You forgot to add %s. that wouldn't have happened to dloser..."

        if select(t for t in self.db.WwddPluginData if what.lower() in t.text.lower()):
            return "Error: That what has already been added!"

        self.db.WwddPluginData(text=what)
        return "Okay"
