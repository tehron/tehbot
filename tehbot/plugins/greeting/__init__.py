from tehbot.plugins import *
import tehbot.settings as settings

class GreetingHandler(ChannelJoinHandler):
    def initialize(self, dbconn):
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

    def execute(self, connection, event, extra, dbconn):
        for network, channels in settings.plugins[self.__class__.__name__].where:
            if connection.name != network or (event.target not in channels and channels != "__all__"):
                return

        if event.source.nick in settings.plugins[self.__class__.__name__].no_greet:
            return

        if event.source.nick == "RichardBrook":
            return "Oh look, it's RichardBrook!"

        c = dbconn.execute("select text from Greetings order by random() limit 1")
        res = c.fetchone()

        if res is not None:
            return res[0] % (event.source.nick)

register_channel_join_handler(GreetingHandler())

class GreetPlugin(Plugin):
    def __init__(self):
        Plugin.__init__(self)
        group = self.parser.add_mutually_exclusive_group(required=True)
        group.add_argument("who", nargs="?")
        group.add_argument("-a", "--add", metavar="greeting")

    def execute(self, connection, event, extra, dbconn):
        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % str(e)

        if pargs.add:
            if not self.privileged(connection, event):
                return self.request_priv(extra)

            greeting = pargs.add
            if greeting.find("%s") < 0:
                return "Error: You forgot to add %s."

            if dbconn.execute("select 1 from Greetings where text like ?", ("%%%s%%" % greeting,)).fetchone() is not None:
                return "Error: That greeting has already been added!"

            with dbconn:
                if dbconn.execute("insert into Greetings values(null, ?)", (greeting,)).rowcount != 1:
                    return "Error: Query failed. :("
        else:
            c = dbconn.execute("select text from Greetings order by random() limit 1")
            res = c.fetchone()

            if res is not None:
                return res[0] % (pargs.who)

register_plugin("greet", GreetPlugin())
