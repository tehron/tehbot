from tehbot.plugins import *
import tehbot.plugins as plugins
import tehbot.settings as settings

class GreetingHandler(plugins.ChannelJoinHandler):
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

    def execute(self):
        for network, channels in settings.plugins[self.__class__.__name__].where:
            if self.connection.name != network or (self.target not in channels and channels != "__all__"):
                return

        if self.nick in settings.plugins[self.__class__.__name__].no_greet:
            return

        if self.nick == "RichardBrook":
            return "Oh look, it's RichardBrook!"

        c = self.dbconn.execute("select text from Greetings order by random() limit 1")
        res = c.fetchone()

        if res is not None:
            return res[0] % (self.nick)

register_channel_join_handler(GreetingHandler())
