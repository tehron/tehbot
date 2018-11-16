from tehbot.plugins import *
import shlex
import sqlite3
import time

class SeenPlugin(StandardPlugin):
    """Shows when a user was last seen."""

    def __init__(self):
        StandardPlugin.__init__(self)
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

class PingPlugin(CorePlugin):
    def __init__(self):
        CorePlugin.__init__(self)
        self.parser.add_argument("--verbose", "-v", action="store_true")

    def execute(self, connection, event, extra, dbconn):
        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
            verbose = vars(pargs)["verbose"]
        except Exception as e:
            return u"Error: %s" % unicode(e)

        if verbose:
            return u"pong from Thread %s at %f" % (threading.current_thread().name, time.time())

        return "pong!"

register_plugin("ping", PingPlugin())

class OpHandler(ChannelJoinHandler):
    def execute(self, connection, event, extra, dbconn):
        for network, channels in self.settings["where"].items():
            if connection.name != network or (event.target not in channels and channels != "__all__"):
                return

        if event.source.nick not in self.settings["who"] and self.settings["who"] != "__all__":
            return

        if event.source.nick in self.settings["whonot"]:
            return

        connection.mode(event.target, "+o " + event.source.nick)

    def config(self, args, dbconn):
        ChannelJoinHandler.config(self, args, dbconn)

        if args[0] == "modify":
            if args[1] == "add":
                if args[2] == "whonot":
                    nick = args[3]
                    if not self.settings.has_key("whonot"):
                        self.settings["whonot"] = []
                    self.settings["whonot"].append(nick)
                    print self.settings
                    self.save(dbconn)

register_channel_join_handler(OpHandler())
