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
