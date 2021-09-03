from tehbot.plugins import *
import time
from pony.orm import *
from datetime import datetime
import re
import json
from urllib.request import urlopen
from subprocess import check_output
import socket

class SeenPlugin(StandardCommand):
    """Shows when a user was last seen."""

    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("user", nargs=1)
        self.ircid_arg = self.parser.add_argument("-i", "--ircid")

    def commands(self):
        return ["seen", "last"]

    @db_session
    def ircid2name(self, ircid):
        settings = select(s for s in self.db.Setting if s.name == "tehbot").first()
        try:
            return settings.get_value()["connections"][ircid]["name"]
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

        if v == "i":
            verb = "be"
        elif v[-2:] == "ie":
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

    @db_session
    def execute(self, connection, event, extra):
        ircids = select(m.ircid for m in self.db.Message)[:]
        self.ircid_arg.choices = sorted(ircids)
        return StandardCommand.execute(self, connection, event, extra)

    @db_session
    def execute_parsed(self, connection, event, extra):
        user = self.pargs.user[0]
        ircid = self.pargs.ircid
        msgs = select(m for m in self.db.Message if m.nick == user and m.type == 0 and (ircid is None or m.ircid == ircid)).order_by(desc(self.db.Message.ts))[:1]
        if not msgs:
            wherestr = " on %s" % self.ircid2name(ircid) if ircid else ""
            return [("say_nolog", "I've never seen %s%s." % (user, wherestr))]

        m = msgs[0]
        timestr = Plugin.time2str(time.time(), time.mktime(m.ts.timetuple()))
        name = self.ircid2name(m.ircid)
        action = self.get_action(m.message)
        if m.event == "action" and action is not None:
            msg = "I saw %s %s ago on %s in %s %s." % (user, timestr, name, m.target, action)
        else:
            msg =  "I saw %s %s ago on %s in %s saying '%s'." % (user, timestr, name, m.target, m.message)
        return [("say_nolog", msg)]

class OpHandler(ChannelJoinHandler):
    def default_settings(self):
        return { "who" : [], "whonot" : [] }

    def execute(self, connection, event, extra):
        who = event.source.nick

        if self.settings["who"] and who not in self.settings["who"]:
            return

        if self.settings["whonot"] and who in self.settings["whonot"]:
            return

        connection.mode(event.target, "+o " + who)
        print("ok")

    def values_to_add(self):
        return ChannelJoinHandler.values_to_add(self) + [ "who", "whonot" ]

class LocatePlugin(StandardCommand):
    """Shows a user's location based on ipinfo.io"""

    def init(self):
        StandardCommand.init(self)
        self.parser.add_argument("user")

    def commands(self):
        return "locate"

    def values_to_set(self):
        return StandardCommand.values_to_set(self) + ["cloak_key"]

    def get_info(self, ip):
        url = "http://ipinfo.io/%s/json" % ip
        response = urlopen(url)
        data = json.load(response)
        try:
            return data["country"], data["region"], data["city"]
        except:
            return "WC3", "Local", "Host"

    def execute_parsed(self, connection, event, extra):
        if not self.pargs.user in extra["hosts"]:
            if "whois_requested" in extra:
                return "no such user"
            return [("dowhois", (self.pargs.user, ))]

        host = extra["hosts"][self.pargs.user]

        try:
            ip = socket.gethostbyname(host)
        except:
            if connection.tehbot.ircid == "wcirc":
                if not self.is_privileged(extra):
                    return self.request_priv(extra)
            try:
                cloak = re.search(r'wechall-(...\....\.......)\.IP', host).group(1)
                ip = check_output(["/home/tehron/bin/decloak", self.settings["cloak_key"], cloak]).decode().strip()
            except:
                ip = None

        if not ip:
            return "%s is cloaked" % self.pargs.user

        try:
            country, region, city = self.get_info(ip)
        except:
            return "Network Error"

        return "%s is located in %s, %s, %s" % (self.pargs.user, country, region, city)
