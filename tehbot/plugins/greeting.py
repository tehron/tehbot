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

    def config(self, args, dbconn):
        if args[0] == "modify":
            if args[1] in ["add", "rm"] and args[2] == "no_greet":
                who = args[3]
                if not self.settings.has_key("no_greet"):
                    self.settings["no_greet"] = []
                no_greet = set(self.settings["no_greet"])

                if args[1] == "add":
                    if who in no_greet:
                        return "%s already is in no_greet" % who
                    no_greet.add(who)
                elif args[1] == "rm":
                    if who not in no_greet:
                        return "%s is not in no_greet" % who
                    no_greet.remove(who)
                self.settings["no_greet"] = list(no_greet)
                self.save(dbconn)
                return "Okay"

        return ChannelJoinHandler.config(self, args, dbconn)

    def execute(self, connection, event, extra, dbconn):
        for network, channels in self.settings["where"].items():
            if connection.name != network or (event.target not in channels and channels != "__all__"):
                return

        if event.source.nick in self.settings["no_greet"]:
            return

        if event.source.nick == "RichardBrook":
            return "Oh look, it's RichardBrook!"

        c = dbconn.execute("select text from Greetings order by random() limit 1")
        res = c.fetchone()

        if res is not None:
            return res[0] % (event.source.nick)

class GreetPlugin(StandardCommand):
    def __init__(self):
        StandardCommand.__init__(self)
        group = self.parser.add_mutually_exclusive_group(required=True)
        group.add_argument("who", nargs="?")
        group.add_argument("-a", "--add", metavar="greeting")

    def commands(self):
        return "greet"

    def execute_parsed(self, connection, event, extra, dbconn):
        if self.pargs.add:
            if not self.privileged(connection, event):
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
