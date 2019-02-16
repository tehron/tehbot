# -*- coding: utf-8 -*-
from tehbot.plugins import *
import urllib
from random import *
import shlex
import irc.client

class BlamePlugin(StandardPlugin):
    def command(self, connection, event, extra, dbconn):
        two = connection.tehbot_users[event.target] if irc.client.is_channel(event.target) else [u"spaceone"]
        goats = zip((two for one in range(23)), 42 * [ reduce(random, [], two) ])
        shuffle(goats)
        goats.sort(key=lambda x: random())
        shuffle(goats)
        scapegoat = goats[goats[randint(0, len(goats) - 1)][int(1337 * random()) % 2].index(choice(two))][1][0]
        return u"I blame %s." % scapegoat

register_plugin("blame", BlamePlugin())

class FamPlugin(StandardPlugin):
    """This help at fam"""

    def command(self, connection, event, extra, dbconn):
        return ".quoet fom"

register_plugin("fam", FamPlugin())


class LiarsPlugin(StandardPlugin):
    def __init__(self):
        StandardPlugin.__init__(self)
        self.parser.add_argument("-a", "--add", metavar="who")

    def initialize(self, dbconn):
        StandardPlugin.initialize(self, dbconn)
        with dbconn:
            dbconn.execute("create table if not exists LiarsPlugin(id integer primary key, liar varchar)")
            dbconn.executemany("insert or ignore into LiarsPlugin values(?, ?)", [
                (1, "roun"),
                (2, "Nimda3"),
                (3, "neoxquick"),
                (4, "dloser"),
                (5, "thefinder"),
            ])

    def command(self, connection, event, extra, dbconn):
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

register_plugin("liars", LiarsPlugin())


class PricksPlugin(StandardPlugin):
    def __init__(self):
        StandardPlugin.__init__(self)
        self.parser.add_argument("-a", "--add", metavar="who")

    def initialize(self, dbconn):
        StandardPlugin.initialize(self, dbconn)
        with dbconn:
            dbconn.execute("create table if not exists PricksPlugin(id integer primary key, prick varchar)")
            dbconn.executemany("insert or ignore into PricksPlugin values(?, ?)", [
                (1, "dloser"),
            ])

    def command(self, connection, event, extra, dbconn):
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

register_plugin("pricks", PricksPlugin())


class BeerPlugin(StandardPlugin):
    """Serves the best beer on IRC (way better than Lamb3's!)"""

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

    def __init__(self, lang):
        StandardPlugin.__init__(self)
        self.lang = lang
        group = self.parser.add_mutually_exclusive_group()
        group.add_argument("recipient", nargs="?")
        group.add_argument("--refill", action="store_true")
        group.add_argument("--status", action="store_true")

    def execute(self, connection, event, extra, dbconn):
        self.parser.set_defaults(recipient=event.source.nick)

        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            if self.lang == "de":
                msg = u"Fehler: %s"
            else:
                msg = u"Error: %s"
            return msg % unicode(e)

        if pargs.status:
            beers = self.beers(dbconn)
            if beers < 1:
                if self.lang == "de":
                    msg = u"hat kein Bier mehr. :("
                else:
                    msg = u"has no beer left. :("
            elif beers == 1:
                if self.lang == "de":
                    msg = u"hat noch ein Bier."
                else:
                    msg = u"has one beer left."
            else:
                if self.lang == "de":
                    msg = u"hat noch %d Biere." % beers
                else:
                    msg = u"has %d beers left." % beers
            return [("me", msg)]

        if pargs.refill:
            if not self.privileged(connection, event):
                return self.request_priv(extra)

            self.refill(dbconn)
            if self.lang == "de":
                msg = u"Ok, Bier wieder aufgefüllt. Das war einfach, hu?"
            else:
                msg = u"Ok, beer refilled. That was easy, hu?"
            return msg

        beers = self.get_beer(dbconn)
        if beers == 0:
            if self.lang == "de":
                msg = u"hat kein Bier mehr. :("
            else:
                msg = u"has no beer left. :("
            return [("me", msg)]

        if pargs.recipient == event.source.nick:
            if beers == 1:
                if self.lang == "de":
                    msg = u"reicht die letzte Flasche kaltes Bier rüber zu %s." % event.source.nick
                else:
                    msg = u"passes the last bottle of cold beer around to %s." % event.source.nick
            else:
                if self.lang == "de":
                    msg = u"reicht 1 von %d Flaschen kaltes Bier rüber zu %s." % (beers, event.source.nick)
                else:
                    msg = u"passes 1 of %d bottles of cold beer around to %s." % (beers, event.source.nick)
        else:
            if beers == 1:
                if self.lang == "de":
                    msg = u"und %s reichen die letzte Flasche kaltes Bier rüber zu %s." % (event.source.nick, pargs.recipient)
                else:
                    msg = u"and %s pass the last bottle of cold beer around to %s." % (event.source.nick, pargs.recipient)
            else:
                if self.lang == "de":
                    msg = u"und %s reichen 1 von %d Flaschen kaltes Bier rüber zu %s." % (event.source.nick, beers, pargs.recipient)
                else:
                    msg = u"and %s pass 1 of %d bottles of cold beer around to %s." % (event.source.nick, beers, pargs.recipient)
        return [("me", msg)]

register_plugin("beer", BeerPlugin("en"))
register_plugin("bier", BeerPlugin("de"))


from socket import *
import string
import time
import tehbot.plugins as plugins
class BOSPlugin(StandardPlugin):
    """Can you solve The BrownOS? [WeChall]"""
    def __init__(self):
        StandardPlugin.__init__(self)
        self.parser.add_argument("data", nargs="+")

    def command(self, connection, event, extra, dbconn):
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

        return plugins.shorten(ret, 450)

register_plugin("bos", BOSPlugin())


import pipes
class DecidePlugin(StandardPlugin):
    def __init__(self):
        StandardPlugin.__init__(self)
        self.parser.add_argument("choices", nargs="+")
        self.parser.add_argument("-o", "--or", action="store_true")

    def command(self, connection, event, extra, dbconn):
        choices = []

        if vars(self.pargs)["or"]:
            choices = self.pargs.choices
        else:
            ch = []
            for c in self.pargs.choices:
                if c.lower() in ["or", "||"]:
                    if ch:
                        choices.append(" ".join(ch))
                        ch = []
                    else:
                        choices = []
                        break
                else:
                    ch.append(c)

            if not choices:
                choices = ["Yes", "No"]

        return choice(choices)

register_plugin("decide", DecidePlugin())


class HugPlugin(StandardPlugin):
    """Use this command if you really like (or dislike) someone."""

    def __init__(self):
        StandardPlugin.__init__(self)
        self.parser.add_argument("huggee")
        self.parser.add_argument("-l", "--long", action="store_true")
        self.parser.add_argument("-t", "--tight", action="store_true")
        self.parser.add_argument("-c", "--creepy", action="store_true")
        self.parser.add_argument("--with-a-certain-something", action="store_true")
        self.parser.add_argument("--from-behind", action="store_true")
        self.parser.add_argument("--surprise-me", action="store_true")

    def command(self, connection, event, extra, dbconn):
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

register_plugin("hug", HugPlugin())

class RoflcopterPlugin(PrivilegedPlugin):
    def command(self, connection, event, extra, dbconn):
        return """    ROFL:ROFL:ROFL:ROFL
         ___^___ _
 L    __/      [] \\
LOL===__           \\
 L      \___ ___ ___]
              I   I
          ----------/"""

register_plugin("roflcopter", RoflcopterPlugin())





class DestinyHandler(ChannelJoinHandler):
    def execute(self, connection, event, extra, dbconn):
        if event.source.nick != "destiny":
            return

        return ">> https://www.youtube.com/watch?v=fNmDgRwNFsI <<"

plugins.register_channel_join_handler(DestinyHandler())



class RouletteHandler(ChannelHandler):
    def execute(self, connection, event, extra, dbconn):
        msg = extra["msg"]
        if msg.find("BANG") > -1 or msg.find("BOOM") > -1:
            return "!roulette"

plugins.register_channel_handler(RouletteHandler())



class WixxerdPlugin(PrivilegedPlugin):
    def command(self, connection, event, extra, dbconn):
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

register_plugin("wixxerd", WixxerdPlugin())


import re
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

plugins.register_channel_handler(BeerGrabber())
