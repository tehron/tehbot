# -*- coding: utf-8 -*-
from tehbot.plugins import *
import urllib
from random import *
import shlex
import irc.client
import re

class BlamePlugin(StandardCommand):
    def commands(self):
        return "blame"

    def execute_parsed(self, connection, event, extra, dbconn):
        two = connection.tehbot_users[event.target] if irc.client.is_channel(event.target) else [u"spaceone"]
        goats = zip((two for one in range(23)), 42 * [ reduce(random, [], two) ])
        shuffle(goats)
        goats.sort(key=lambda x: random())
        shuffle(goats)
        scapegoat = goats[goats[randint(0, len(goats) - 1)][int(1337 * random()) % 2].index(choice(two))][1][0]
        return u"I blame %s." % scapegoat

class FamPlugin(StandardCommand):
    """This help at fam"""

    def commands(self):
        return "fam"

    def execute_parsed(self, connection, event, extra, dbconn):
        return ".quoet fom"

class LiarsPlugin(StandardCommand):
    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("-a", "--add", metavar="who")

    def commands(self):
        return "liars"

    def initialize(self, dbconn):
        StandardCommand.initialize(self, dbconn)
        with dbconn:
            dbconn.execute("create table if not exists LiarsPlugin(id integer primary key, liar varchar)")
            dbconn.executemany("insert or ignore into LiarsPlugin values(?, ?)", [
                (1, "roun"),
                (2, "Nimda3"),
                (3, "neoxquick"),
                (4, "dloser"),
                (5, "thefinder"),
            ])

    def execute_parsed(self, connection, event, extra, dbconn):
        if self.pargs.add is None:
            c = dbconn.execute("select liar from LiarsPlugin order by id")
            return ", ".join(a for (a,) in c.fetchall())

        who = self.pargs.add

        if not self.privileged(connection, event):
            return self.request_priv(extra)

        if dbconn.execute("select 1 from LiarsPlugin where liar = ?", (who,)).fetchone() is not None:
            return "Error: That liar has already been added!"

        with dbconn:
            if dbconn.execute("insert into LiarsPlugin values(null, ?)", (who,)).rowcount != 1:
                return "Error: Query failed. :("

        return "Okay"

class PricksPlugin(StandardCommand):
    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("-a", "--add", metavar="who")

    def commands(self):
        return "pricks"

    def initialize(self, dbconn):
        StandardCommand.initialize(self, dbconn)
        with dbconn:
            dbconn.execute("create table if not exists PricksPlugin(id integer primary key, prick varchar)")
            dbconn.executemany("insert or ignore into PricksPlugin values(?, ?)", [
                (1, "dloser"),
            ])

    def execute_parsed(self, connection, event, extra, dbconn):
        if self.pargs.add is None:
            c = dbconn.execute("select prick from PricksPlugin order by id")
            return ", ".join(a for (a,) in c.fetchall())

        who = self.pargs.add

        if not self.privileged(connection, event):
            return self.request_priv(extra)

        if dbconn.execute("select 1 from PricksPlugin where prick = ?", (who,)).fetchone() is not None:
            return "Error: That prick has already been added!"

        with dbconn:
            if dbconn.execute("insert into PricksPlugin values(null, ?)", (who,)).rowcount != 1:
                return "Error: Query failed. :("

        return "Okay"

class BeerPlugin(StandardCommand):
    """Serves the best beer on IRC (way better than Lamb3's!)"""

    def __init__(self):
        StandardCommand.__init__(self)
        group = self.parser.add_mutually_exclusive_group()
        group.add_argument("recipient", nargs="?")
        group.add_argument("--refill", action="store_true")
        group.add_argument("--status", action="store_true")

    def commands(self):
        return "beer"

    def initialize(self, dbconn):
        StandardCommand.initialize(self, dbconn)
        with dbconn:
            dbconn.execute("CREATE TABLE if not exists BeerPlugin(id integer primary key, key varchar unique, value varchar)")
            dbconn.executemany("insert or ignore into BeerPlugin values(?, ?, ?)", [
                (1, "beers", 10),
            ])

    def beers(self, dbconn):
        c = dbconn.execute("select value from BeerPlugin where key='beers'")
        res = c.fetchone()
        if res is None:
            return 0
        return int(res[0])

    def get_beer(self, dbconn):
        beers = self.beers(dbconn)

        if beers > 0:
            with dbconn:
                dbconn.execute("update BeerPlugin set value=? where key='beers'", (str(beers - 1), ))

        return beers

    def refill(self, dbconn, beers=10):
        with dbconn:
            dbconn.execute("update BeerPlugin set value=value+? where key='beers'", (str(beers), ))

    def execute(self, connection, event, extra, dbconn):
        self.parser.set_defaults(recipient=event.source.nick)

        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            msg = u"Error: %s"
            return msg % unicode(e)

        if pargs.status:
            beers = self.beers(dbconn)
            if beers < 1:
                msg = u"has no beer left. :("
            elif beers == 1:
                msg = u"has one beer left."
            else:
                msg = u"has %d beers left." % beers
            return [("me", msg)]

        if pargs.refill:
            if not self.privileged(connection, event):
                return self.request_priv(extra)

            self.refill(dbconn)
            msg = u"Ok, beer refilled. That was easy, hu?"
            return msg

        beers = self.get_beer(dbconn)
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
    def execute(self, connection, event, extra, dbconn):
        match = re.search(r'and (\w+) pass (\d+) of \d+ bottles of cold beer around to (\w+)\.', extra["msg"])
        if match is None:
            return

        donor = match.group(1)
        cnt = int(match.group(2))
        who = match.group(3)

        if cnt > 0 and who == connection.get_nickname():
            with dbconn:
                dbconn.execute("update BeerPlugin set value=value+? where key='beers'", (str(cnt), ))

            c = dbconn.execute("select value from BeerPlugin where key='beers'")
            res = c.fetchone()
            beers = int(res[0])

            return u"Thanks, %s, I put it into my store! Beer count is %d now." % (donor, beers)

from socket import *
import string
import time
class BOSPlugin(StandardCommand):
    """Can you solve The BrownOS? [WeChall]"""
    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("data", nargs="+")

    def commands(self):
        return "bos"

    def execute_parsed(self, connection, event, extra, dbconn):
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
    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("choices", nargs="+")
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

    def execute_parsed(self, connection, event, extra, dbconn):
        choices = []

        if vars(self.pargs)["or"]:
            choices = self.pargs.choices
        else:
            parts = DecidePlugin.partition(self.pargs.choices)
            if len(parts) > 1:
                choices = map(" ".join, parts)
            else:
                choices = ["Yes", "No"]

        return choice(choices)

class HugPlugin(StandardCommand):
    """Use this command if you really like (or dislike) someone."""

    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("huggee")
        self.parser.add_argument("-l", "--long", action="store_true")
        self.parser.add_argument("-t", "--tight", action="store_true")
        self.parser.add_argument("-c", "--creepy", action="store_true")
        self.parser.add_argument("--with-a-certain-something", action="store_true")
        self.parser.add_argument("--from-behind", action="store_true")
        self.parser.add_argument("--surprise-me", action="store_true")

    def commands(self):
        return "hug"

    def execute_parsed(self, connection, event, extra, dbconn):
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

    def execute(self, connection, event, extra, dbconn):
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
    def execute(self, connection, event, extra, dbconn):
        if event.source.nick != "destiny":
            return

        return ">> https://www.youtube.com/watch?v=fNmDgRwNFsI <<"

class RouletteHandler(ChannelHandler):
    def execute(self, connection, event, extra, dbconn):
        msg = extra["msg"]
        if msg.find("BANG") > -1 or msg.find("BOOM") > -1:
            return "!roulette"

class WixxerdPlugin(Command):
    def commands(self):
        return "wixxerd"

    def execute(self, connection, event, extra, dbconn):
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

