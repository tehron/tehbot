# -*- coding: utf-8 -*-
from tehbot.plugins import *
import urllib
from random import *
import shlex
import irc.client
import re
from pony.orm import *

class BlamePlugin(StandardCommand):
    def commands(self):
        return "blame"

    def execute_parsed(self, connection, event, extra):
        botname = connection.get_nickname()
        forbidden = ["ChanServ", "NickServ", botname]
        two = [u for u,m in connection.tehbot.users[event.target] if u not in forbidden] if irc.client.is_channel(event.target) else [u"spaceone"]
        goats = zip((two for one in range(23)), 42 * [ reduce(random, [], two) ])
        shuffle(goats)
        goats.sort(key=lambda x: random())
        shuffle(goats)
        scapegoat = choice(goats[goats[randint(0, len(goats) - 1)][int(1337 * random()) % 2].index(choice(two))][1])
        return u"I blame %s." % scapegoat

class FamPlugin(StandardCommand):
    """This help at fam"""

    def commands(self):
        return "fam"

    def execute_parsed(self, connection, event, extra):
        return ".quoet fom"

class ListPlugin(StandardCommand):
    def __init__(self, db, what="item"):
        StandardCommand.__init__(self, db)
        self.what = what
        self.parser.add_argument("-a", "--add", metavar="who")

    def commands(self):
        return "list"

    def create_entities(self):
        if self.__class__.__name__ != ListPlugin.__name__:
            return

        class ListPluginData(self.db.Entity):
            what = Required(str)
            who = Required(str)
            composite_key(what, who)

    def execute_parsed(self, connection, event, extra):
        if self.pargs.add is None:
            with db_session:
                data = select(d for d in self.db.ListPluginData if d.what == self.what).order_by(self.db.ListPluginData.id)
                return ", ".join(d.who for d in data)

        who = self.pargs.add

        if not self.is_privileged(extra):
            return self.request_priv(extra)

        with db_session:
            if self.db.ListPluginData.exists(lambda d: d.who.lower() == who.lower()):
                return "Error: That %s has already been added!" % self.what

            try:
                self.db.ListPluginData(what=self.what, who=who)
            except:
                return "Error: Query failed. :("

        return "Okay"

class LiarsPlugin(ListPlugin):
    def __init__(self, db):
        ListPlugin.__init__(self, db, "liar")

    def commands(self):
        return "liars"

    def init(self):
        ListPlugin.init(self)
        with db_session:
            if not self.db.ListPluginData.select(lambda x: x.what == self.what):
                self.db.ListPluginData(what=self.what, who="roun")
                self.db.ListPluginData(what=self.what, who="Nimda3")
                self.db.ListPluginData(what=self.what, who="neoxquick")
                self.db.ListPluginData(what=self.what, who="dloser")
                self.db.ListPluginData(what=self.what, who="thefinder")

class PricksPlugin(ListPlugin):
    def __init__(self, db):
        ListPlugin.__init__(self, db, "prick")

    def commands(self):
        return "pricks"

    def init(self):
        ListPlugin.init(self)
        with db_session:
            if not self.db.ListPluginData.select(lambda x: x.what == self.what):
                self.db.ListPluginData(what=self.what, who="dloser")

class BeerPlugin(StandardCommand):
    """Serves the best beer on IRC (way better than Lamb3's!)"""

    def __init__(self, db):
        StandardCommand.__init__(self, db)
        group = self.parser.add_mutually_exclusive_group()
        group.add_argument("recipient", nargs="?")
        group.add_argument("--refill", action="store_true")
        group.add_argument("--status", action="store_true")

    def commands(self):
        return "beer"

    def create_entities(self):
        class BeerPluginData(self.db.Entity):
            key = Required(str, unique=True)
            value = Required(int)

    def init(self):
        StandardCommand.init(self)
        with db_session:
            if self.db.BeerPluginData.get(key="beers") is None:
                self.db.BeerPluginData(key="beers", value=10)

    @db_session
    def beers(self):
        return self.db.BeerPluginData.get(key="beers").value

    @db_session
    def get_beer(self):
        beers = self.db.BeerPluginData.get(key="beers")
        cnt = beers.value
        beers.value = max(0, beers.value - 1)
        return cnt

    @db_session
    def refill(self, beers=10):
        self.db.BeerPluginData.get(key="beers").value += beers

    def execute(self, connection, event, extra):
        self.parser.set_defaults(recipient=event.source.nick)

        try:
            pargs = self.parser.parse_args(extra["args"])
            m = self.parser.get_help_msg()
            if m:
                return m.strip()
        except Exception as e:
            msg = u"Error: %s"
            return msg % unicode(e)

        if pargs.status:
            beers = self.beers()
            if beers < 1:
                msg = u"has no beer left. :("
            elif beers == 1:
                msg = u"has one beer left."
            else:
                msg = u"has %d beers left." % beers
            return [("me", msg)]

        if pargs.refill:
            if not self.is_privileged(extra):
                return self.request_priv(extra)

            self.refill()
            msg = u"Ok, beer refilled. That was easy, hu?"
            return msg

        beers = self.get_beer()
        if beers == 0:
            msg = u"has no beer left. :("
            return [("me", msg)]

        if pargs.recipient == event.source.nick:
            if beers == 1:
                msg = u"passes the last bottle of cold beer around to %s." % event.source.nick
            else:
                msg = u"passes 1 of %d bottles of cold beer around to %s." % (beers, event.source.nick)
        else:
            if beers == 1:
                msg = u"and %s pass the last bottle of cold beer around to %s." % (event.source.nick, pargs.recipient)
            else:
                msg = u"and %s pass 1 of %d bottles of cold beer around to %s." % (event.source.nick, beers, pargs.recipient)
        return [("me", msg)]

class BeerGrabber(ChannelHandler):
    def execute(self, connection, event, extra):
        match = re.search(r'and (\w+) pass (\d+) of \d+ bottles of cold beer around to (\w+)\.', extra["msg"])
        if match is None:
            return

        donor = match.group(1)
        cnt = int(match.group(2))
        who = match.group(3)

        if cnt > 0 and who == connection.get_nickname():
            with db_session:
                beers = self.db.BeerPluginData.get(key="beers")
                beers.value += cnt
                total = beers.value

            return u"Thanks, %s, I put it into my store! Beer count is %d now." % (donor, total)

from socket import *
import string
import time
class BOSPlugin(StandardCommand):
    """Can you solve The BrownOS? [WeChall]"""
    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("data", nargs="+")

    def commands(self):
        return "bos"

    def execute_parsed(self, connection, event, extra):
        data = " ".join(self.pargs.data).lower()

        sock = socket()
        sock.connect(("wc3.wechall.net", 61221))
        data = data.replace("qd", "05 00 FD 00 05 00 FD 03 FD FE FD 02 FD FE FD FE")
        #data = filter(lambda x: x in string.hexdigits, data)
        data = data.replace(" ", "")
        ret = "hmpf"
        try:
            data = data.decode("hex")
            if data[-1] != "\xff":
                data += "\xff"
            sock.send(data)
            data = ""
            while True:
                time.sleep(0.01)
                d = sock.recv(1024)
                if not d:
                    break
                data += d
            for c in data:
                if not c in string.printable:
                    ret = " ".join(x.encode("hex") for x in data)
                    break
            if ret == "hmpf":
                ret = data
        except Exception as e:
            return unicode(e)
        finally:
            sock.close()

        return Plugin.shorten(ret, 450)

class DecidePlugin(StandardCommand):
    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("choice", nargs="*")
        self.parser.add_argument("-o", "--or", action="store_true")

    def commands(self):
        return "decide"

    @staticmethod
    def partition(args):
        parts = []
        arg = []
        while args:
            c = args.pop(0)
            if c.lower() in ["or", "||"]:
                if arg:
                    parts.append(arg)
                    arg = []
            else:
                arg.append(c)

        if arg:
            parts.append(arg)

        return parts

    def execute_parsed(self, connection, event, extra):
        choices = ["Yes", "No"]

        if self.pargs.choice:
            if vars(self.pargs)["or"]:
                choices = self.pargs.choice
            else:
                parts = DecidePlugin.partition(self.pargs.choice)
                if len(parts) > 1:
                    choices = map(" ".join, parts)

        return choice(choices)

class HugPlugin(StandardCommand):
    """Use this command if you really like (or dislike) someone."""

    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("huggee")
        self.parser.add_argument("-l", "--long", action="store_true")
        self.parser.add_argument("-t", "--tight", action="store_true")
        self.parser.add_argument("-c", "--creepy", action="store_true")
        self.parser.add_argument("--with-a-certain-something", action="store_true")
        self.parser.add_argument("--from-behind", action="store_true")
        self.parser.add_argument("--surprise-me", action="store_true")

    def commands(self):
        return "hug"

    def execute_parsed(self, connection, event, extra):
        options = []

        if self.pargs.surprise_me:
            self.pargs.long = choice([True, False])
            self.pargs.tight = choice([True, False])
            self.pargs.creepy = choice([True, False])
            self.pargs.from_behind = choice([True, False])
            self.pargs.with_a_certain_something = choice([True, False])

        if self.pargs.long:
            options.append("long")
        if self.pargs.tight:
            options.append("tight")
        if self.pargs.creepy:
            options.append("creepy")

        if not options:
            msg = u"hugs %s" % self.pargs.huggee
        else:
            msg = u"gives %s a %s hug" % (self.pargs.huggee, " and ".join(options))

        if self.pargs.from_behind:
            msg += " from behind"

        if self.pargs.with_a_certain_something:
            msg += " with a certain something"

        return [("me", msg)]

class RoflcopterPlugin(Command):
    def commands(self):
        return "roflcopter"

    def execute(self, connection, event, extra):
        if not self.is_privileged(extra):
            return self.request_priv(extra)

        return r"""    ROFL:ROFL:ROFL:ROFL
         ___^___ _
 L    __/      [] \
LOL===__           \
 L      \___ ___ ___]
              I   I
          ----------/"""






class DestinyHandler(ChannelJoinHandler):
    def execute(self, connection, event, extra):
        if event.source.nick != "destiny":
            return

        return ">> https://www.youtube.com/watch?v=fNmDgRwNFsI <<"

class RouletteHandler(ChannelHandler):
    def execute(self, connection, event, extra):
        msg = extra["msg"]
        if msg.find("BANG") > -1 or msg.find("BOOM") > -1:
            return "!roulette"

class WixxerdPlugin(Command):
    def commands(self):
        return "wixxerd"

    def execute(self, connection, event, extra):
        if not self.is_privileged(extra):
            return self.request_priv(extra)

        return r"""       .##...##..######..##..##..##..##..######..#####...#####..
       .##...##....##.....####....####...##......##..##..##..##.
       .##.#.##....##......##......##....####....#####...##..##.
       .#######....##.....####....####...##......##..##..##..##.
       ..##.##...######..##..##..##..##..######..##..##..#####..
       ......................................................... 
                    .........  ... . ... . ..  . ........
                          .....   .. . .   . .  .....
                              ...  .  ...  .  .....
                               ``,           ,.,
                                `\\_  |    _//'
                                  \(  |\    )/
                                  //\ |_\  /\\
                                 (/ /\(" )/\ \)
                                  \/\ (  ) /\/
                                     |(  )|
                                     | \( \
                                     |  )  \
                                     |      \
                                     |       \
                                     |        `.__,
                                     \_________.-"""



class DeadHourPlugin(Command):
    def commands(self):
        return "dead_hour"

    def default_settings(self):
        return {
                "max_modes" : 20
                }

    def execute(self, connection, event, extra):
        if not self.is_privileged(extra):
            return self.request_priv(extra)

        if not irc.client.is_channel(event.target):
            return

        channel = event.target
        users = connection.tehbot.users[channel][:]
        botname = connection.get_nickname()
        idx = [u for u,m in users].index(botname)

        if not users[idx][1].intersection("qo"):
            return "I don't have enough privileges in this channel to do that."

        skip_users = ["Lamb3", "ChanServ", botname]

        try:
            max_modes = connection.features.modes
        except AttributeError:
            max_modes = self.settings["max_modes"]

        def modelist(users):
            def check(ulist, mlist):
                s = "-" + "".join(mlist) + " " + " ".join(ulist)
                return len(s) <= 450 and len(ulist) <= max_modes

            mlist = []
            ulist = []

            while users:
                u, mods = users.pop()
                if u in skip_users:
                    continue

                if "o" in mods:
                    m = "o"
                elif "h" in mods:
                    m = "h"
                elif "v" in mods:
                    m = "v"
                else:
                    continue

                if check(ulist + [u], mlist + [m]):
                    ulist.append(u)
                    mlist.append(m)
                else:
                    users.append((u, mods))
                    break

            return "-" + "".join(mlist) + " " + " ".join(ulist)

        res = []
        while users:
            modes = modelist(users)
            res.append(("mode", (connection, event.target, modes)))

        return res
