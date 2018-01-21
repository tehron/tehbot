from tehbot.plugins import *
import tehbot.plugins as plugins
import shlex
import sqlite3
import time

class SeenPlugin(Plugin):
    """"""

    def __init__(self):
        Plugin.__init__(self)
        self.parser = plugins.ThrowingArgumentParser(
                prog="stats",
                description=SeenPlugin.__doc__
        )

    def execute(self):
        if not self.args:
            return

        user = self.args.split()[0]
        c = self.dbconn.cursor()
        c.execute("select * from Messages where nick=? order by ts desc limit 1", (user,))
        res = c.fetchone()

        if res is None:
            return "I've never seen %s." % user

        _, ts, server, channel, nick, message = res
        return "I saw %s on %s in %s at %s saying '%s'." % (user, server, channel, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)), message)

p = SeenPlugin()
register_cmd("seen", p)
register_cmd("last", p)
