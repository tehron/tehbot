from tehbot.plugins import *
import shlex
import sqlite3
import time

class SeenPlugin(Plugin):
    """Shows when a user was last seen."""

    def __init__(self):
        Plugin.__init__(self)
        self.logtodb = False
        self.parser.add_argument("user", nargs=1)

    def execute(self, connection, event, extra, dbconn):
        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
            user = pargs.user[0]
        except Exception as e:
            return u"Error: %s" % str(e)

        c = dbconn.cursor()
        c.execute(u"select * from Messages where nick=? order by ts desc limit 1", (user,))
        res = c.fetchone()

        if res is None:
            return u"I've never seen %s." % user

        _, ts, server, channel, nick, message = res
        return u"I saw %s on %s in %s at %s saying '%s'." % (user, server, channel, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)), message)

register_plugin(["seen", "last"], SeenPlugin())
