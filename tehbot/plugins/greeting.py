from tehbot.plugins import *

class GreetingHandler(ChannelJoinHandler):
    def default_settings(self):
        return {
                "no_greet" : [ ]
                }

    def initialize(self, dbconn):
        ChannelJoinHandler.initialize(self, dbconn)
        with dbconn:
            dbconn.execute("create table if not exists Greetings(id integer primary key, text varchar)")
            dbconn.executemany("insert or ignore into Greetings values(?, ?)", [
                (1, "Konnichiwa %s"),
                (2, "Welcome %s"),
                (3, "Hi %s"),
                (4, "Salut %s"),
                (5, "Salam aleikum, %s"),
                (6, "Hello %s"),
                (7, "Ciao %s"),
                (8, "Hei %s"),
                (9, "Ahoj %s"),
                (10, "Hola %s"),
            ])

    def execute(self, connection, event, extra):
        def enabled():
            for w in self.settings["where"]:
                network, channel = w.split(":")
                if connection.tehbot.ircid == network and event.target.lower() == channel.lower():
                    return True
            return False

        if not enabled() or event.source.nick in self.settings["no_greet"]:
            return

        if event.source.nick == "RichardBrook":
            return "Oh look, it's RichardBrook!"

        c = dbconn.execute("select text from Greetings order by random() limit 1")
        res = c.fetchone()

        if res is not None:
            return res[0] % (event.source.nick)

class GreetPlugin(StandardCommand):
    def __init__(self, db):
        StandardCommand.__init__(self, db)
        group = self.parser.add_mutually_exclusive_group(required=True)
        group.add_argument("who", nargs="?")
        group.add_argument("-a", "--add", metavar="greeting")

    def commands(self):
        return "greet"

    def execute_parsed(self, connection, event, extra, dbconn):
        if self.pargs.add:
            if not self.is_privileged(extra):
                return self.request_priv(extra)

            greeting = self.pargs.add
            if greeting.find("%s") < 0:
                return "Error: You forgot to add %s."

            if dbconn.execute("select 1 from Greetings where text like ?", ("%%%s%%" % greeting,)).fetchone() is not None:
                return "Error: That greeting has already been added!"

            with dbconn:
                if dbconn.execute("insert into Greetings values(null, ?)", (greeting,)).rowcount != 1:
                    return "Error: Query failed. :("
            return "Okay"
        else:
            c = dbconn.execute("select text from Greetings order by random() limit 1")
            res = c.fetchone()

            if res is not None:
                return res[0] % (self.pargs.who)
