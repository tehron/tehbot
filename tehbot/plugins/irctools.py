from tehbot.plugins import *
import shlex
import sqlite3
import time
import irc.client
import threading

class SeenPlugin(StandardCommand):
    """Shows when a user was last seen."""

    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("user", nargs=1)

    def commands(self):
        return ["seen", "last"]

    def execute_parsed(self, connection, event, extra, dbconn):
        user = self.pargs.user[0]
        requser = event.source.nick
        c = dbconn.cursor()
        c.execute(u"select * from Messages where nick=? and type=0 order by ts desc limit 2", (user,))
        res = c.fetchone()

        if res is None:
            return [("say_nolog", u"I've never seen %s." % user)]

        if user == requser and irc.client.is_channel(event.target):
            res = c.fetchone()

        _, ts, server, channel, nick, _, message = res
        timestr = Plugin.time2str(time.time(), ts)
        msg =  u"I saw %s %s ago on %s in %s saying '%s'." % (user, timestr, server, channel, message)
        return [("say_nolog", msg)]

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
        res = ChannelJoinHandler.config(self, args, dbconn)

        if res:
            return res

        if args[0] == "modify":
            if args[1] == "add":
                if args[2] == "whonot":
                    nick = args[3]
                    if not self.settings.has_key("whonot"):
                        self.settings["whonot"] = []
                    self.settings["whonot"].append(nick)
                    print self.settings
                    self.save(dbconn)
                    return "Okay"
