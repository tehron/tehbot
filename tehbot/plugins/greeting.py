from tehbot.plugins import *
from pony.orm import *

class GreetingHandler(ChannelJoinHandler):
    def default_settings(self):
        return {
                "no_greet" : [ ]
                }

    @db_session
    def greet(self, who):
        g = self.db.GreetingPluginData.select_random(1)

        if g:
            return g[0].greeting % who

    def execute(self, connection, event, extra):
        if event.source.nick in self.settings["no_greet"]:
            return

        if event.source.nick == "RichardBrook":
            return "Oh look, it's RichardBrook!"

        return self.greet(event.source.nick)

class GreetPlugin(StandardCommand):
    def __init__(self, db):
        StandardCommand.__init__(self, db)
        group = self.parser.add_mutually_exclusive_group(required=True)
        group.add_argument("who", nargs="?")
        group.add_argument("-a", "--add", metavar="greeting")

    def commands(self):
        return "greet"

    def create_entities(self):
        class GreetingPluginData(self.db.Entity):
            greeting = Required(str, unique=True, max_len=128)

    def init(self):
        StandardCommand.init(self)
        with db_session:
            if not self.db.GreetingPluginData.select():
                self.db.GreetingPluginData(greeting="Konnichiwa %s")
                self.db.GreetingPluginData(greeting="Welcome %s")
                self.db.GreetingPluginData(greeting="Hi %s")
                self.db.GreetingPluginData(greeting="Salut %s")
                self.db.GreetingPluginData(greeting="Salam aleikum, %s")
                self.db.GreetingPluginData(greeting="Hello %s")
                self.db.GreetingPluginData(greeting="Ciao %s")
                self.db.GreetingPluginData(greeting="Hei %s")
                self.db.GreetingPluginData(greeting="Ahoj %s")
                self.db.GreetingPluginData(greeting="Hola %s")

    @db_session
    def greet(self, who):
        g = self.db.GreetingPluginData.select_random(1)

        if g:
            return g[0].greeting % who

    @db_session
    def execute_parsed(self, connection, event, extra):
        if self.pargs.add:
            if not self.is_privileged(extra):
                return self.request_priv(extra)

            greeting = self.pargs.add
            if greeting.find("%s") < 0:
                return "Error: You forgot to add %s."

            if select(g for g in self.db.GreetingPluginData if greeting in g.greeting):
                return "Error: That greeting has already been added!"

            try:
                self.db.GreetingPluginData(greeting=greeting)
            except:
                return "Error: Query failed. :("

            return "Okay"

        return self.greet(self.pargs.who)
