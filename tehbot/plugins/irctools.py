from tehbot.plugins import *
import shlex
import sqlite3
import time
import irc.client
import threading
from tehbot.settings import Settings

class SeenPlugin(StandardCommand):
    """Shows when a user was last seen."""

    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("user", nargs=1)

    def commands(self):
        return ["seen", "last"]

    def ircid2name(self, ircid, dbconn):
        settings = Settings()
        settings.load(dbconn)
        try:
            return settings.value("connections")[ircid]["name"]
        except:
            return ircid

    def get_action(self, message):
        arr = message.split()
        if not arr:
            return None
        verb = arr[0]
        if len(verb) < 2 or verb[-1].lower() != "s":
            return None
        verb = verb[:-1]
        v = verb.lower()

        if v[-2:] == "ie":
            verb = verb[:-2] + "y"
        elif v[-1] == "e":
            if not v.endswith("ee"):
                verb = verb[:-1]
        elif v[-2:] == "ic":
            verb = verb + "k"
        elif v[-1] not in "aeiou" and v[-2:-1] in "aeiou":
            if v[-3:-2] not in "aeiou":
                verb = verb + verb[-1]
        args = " ".join(arr[1:])
        msg = verb + "ing"
        if args:
            msg += " " + args
        return msg

    def execute_parsed(self, connection, event, extra, dbconn):
        user = self.pargs.user[0]
        requser = event.source.nick
        c = dbconn.cursor()
        c.execute(u"select * from Messages where nick=? and type=0 order by ts desc limit 1", (user,))
        res = c.fetchone()

        if res is None:
            return [("say_nolog", u"I've never seen %s." % user)]

        _, ts, server, channel, nick, _, message, is_action = res
        timestr = Plugin.time2str(time.time(), ts)
        name = self.ircid2name(server, dbconn)
        action = self.get_action(message)
        if is_action and action is not None:
            msg = u"I saw %s %s ago on %s in %s %s." % (user, timestr, name, channel, action)
        else:
            msg =  u"I saw %s %s ago on %s in %s saying '%s'." % (user, timestr, name, channel, message)
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
