from tehbot.plugins import *
import tehbot.plugins as plugins
import urllib
from random import *
import shlex

class BlamePlugin(Plugin):
    def execute(self):
        space = u"\u0455paceone"
        goats = zip((space for one in range(23)), 42 * [ reduce(random, [], space) ])
        shuffle(goats)
        goats.sort(key=lambda x: random())
        shuffle(goats)
        scapegoat = goats[randint(0, len(goats) - 1)][int(1337 * random()) % 2]
        return "I blame %s." % scapegoat

register_cmd("blame", BlamePlugin())

class FamPlugin(Plugin):
    """This help at fam"""

    def execute(self):
        return ".quoet fom"

register_pub_cmd("fam", FamPlugin())
import tehbot.plugins as plugins

class PunsPlugin(Plugin):
    """Prints a random pun from jhype.co.uk"""

    def execute(self):
        page = urllib.urlopen("http://jhype.co.uk/puns.php").read()
        init = False
        puns = []
        currpun = []
        for line in page.splitlines():
            if line.startswith('<p class="emph2">'):
                init = True
                if currpun:
                    puns.append("\n".join(currpun))
                    currpun = []
                continue
            if init and line.find("</div>") > -1:
                init = False
                break
            if init:
                if line.startswith("<br />"):
                    if currpun:
                        puns.append("\n".join(currpun))
                        currpun = []
                else:
                    currpun.append(line.replace("<br />", ""))
        if currpun:
            puns.append("\n".join(currpun))

        shuffle(puns)
        if puns:
            return puns[0]

register_cmd("pun", PunsPlugin())

class LiarsPlugin(Plugin):
    def execute(self):
        return "roun, Nimda3, neoxquick, dloser, thefinder"

register_cmd("liars", LiarsPlugin())

class PricksPlugin(Plugin):
    def execute(self):
        return "dloser"

register_cmd("pricks", PricksPlugin())


class BeerPlugin(Plugin):
    """Serves the best beer on IRC (way better than Lamb3's!)"""

    def query_beers(self):
        c = self.dbconn.execute("select value from BeerPlugin where key='beers'")
        res = c.fetchone()
        if res is None:
            return 0
        beers = int(res[0])

        if beers > 0:
            with self.dbconn:
                self.dbconn.execute("update BeerPlugin set value=? where key='beers'", (str(beers - 1), ))

        return beers

    def refill(self, beers=10):
        with self.dbconn:
            self.dbconn.execute("update BeerPlugin set value=? where key='beers'", (str(beers), ))

    def __init__(self):
        Plugin.__init__(self)
        self.parser.add_argument("recpt", nargs="?")
        self.parser.add_argument("--refill", action="store_true")

    def execute(self):
        self.parser.set_defaults(recpt=self.nick)

        try:
            pargs = self.parser.parse_args(self.args)
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % e.message

        if pargs.refill:
            self.refill()
            return u"Ok, beer refilled. That was easy, hu?"

        beers = self.query_beers()
        if beers == 0:
            return plugins.me(self.connection, self.target, u"has no beer left :(")

        if pargs.recpt == self.nick:
            plugins.me(self.connection, self.target, u"passes 1 of %d bottles of cold beer around to %s" % (beers, self.nick))
        else:
            plugins.me(self.connection, self.target, u"and %s pass 1 of %d bottles of cold beer around to %s" % (self.nick, beers, pargs.recpt))

register_cmd("beer", BeerPlugin())


from socket import *
import string
import time
class BOSPlugin(Plugin):
    """Can you solve The BrownOS? [WeChall]"""
    def execute(self):
        if not self.args:
            return
        sock = socket()
        sock.connect(("wc3.wechall.net", 61221))
        data = "".join(self.args).lower()
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
            return str(e)
        finally:
            sock.close()

        return plugins.shorten(ret, 450)

register_cmd("bos", BOSPlugin())


#shotmap = {}
#
#def shots(connection, channel, nick, cmd, args):
    #plugins.say_nick(connection, channel, nick, "|~|")
    #plugins.say_nick(connection, channel, nick, "+-+  Cheers, %s!" % nick)
    #if not shotmap.has_key(nick):
        #shotmap[nick] = 0
    #shotmap[nick] += 1
#
#def shoot(connection, channel, nick, cmd, args):
    #if not shotmap.has_key(nick) or shotmap[nick] == 0:
        #return plugins.say_nick(connection, channel, nick, "Your glass is empty!")
#
    #shotmap[nick] -= 1
    #plugins.say_nick(connection, channel, nick, "| |  AH!")
    #plugins.say_nick(connection, channel, nick, "+-+  Want another one, %s?" % nick)
#
#plugins.register_cmd("shots", shots)
#plugins.register_cmd("shoot", shoot)

class DecidePlugin(Plugin):
    def execute(self):
        if not self.args:
            return

        vals = self.args.split(" or ")
        if len(vals) > 1:
            return choice(vals).strip()

        vals = self.args.split("||")
        if len(vals) > 1:
            return choice(vals).strip()

        return choice(["Yes", "No"])

register_cmd("decide", DecidePlugin())


class HugPlugin(Plugin):
    """Use this command if you really like (or dislike) someone."""

    def __init__(self):
        Plugin.__init__(self)
        self.parser.add_argument("huggee")
        self.parser.add_argument("-l", "--long", action="store_true")
        self.parser.add_argument("-t", "--tight", action="store_true")
        self.parser.add_argument("-c", "--creepy", action="store_true")
        self.parser.add_argument("--with-a-certain-something", action="store_true")
        self.parser.add_argument("--from-behind", action="store_true")
        self.parser.add_argument("--surprise-me", action="store_true")

    def execute(self):
        try:
            pargs = self.parser.parse_args(self.args)
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % e.message

        options = []

        if pargs.surprise_me:
            pargs.long = choice([True, False])
            pargs.tight = choice([True, False])
            pargs.creepy = choice([True, False])
            pargs.from_behind = choice([True, False])
            pargs.with_a_certain_something = choice([True, False])

        if pargs.long:
            options.append("long")
        if pargs.tight:
            options.append("tight")
        if pargs.creepy:
            options.append("creepy")

        if not options:
            msg = u"hugs %s" % pargs.huggee
        else:
            msg = u"gives %s a %s hug" % (pargs.huggee, " and ".join(options))

        if pargs.from_behind:
            msg += " from behind"

        if pargs.with_a_certain_something:
            msg += " with a certain something"

        return plugins.me(self.connection, self.target, msg)

register_cmd("hug", HugPlugin())

class MirrorPlugin(Plugin):
    def execute(self):
        return "tehron" if self.nick == "dloser" else "dloser"

register_cmd("mirror", MirrorPlugin())

class RoflcopterPlugin(Plugin):
    def execute(self):
        return """    ROFL:ROFL:ROFL:ROFL
         ___^___ _
 L    __/      [] \\
LOL===__           \\
 L      \___ ___ ___]
              I   I
          ----------/"""

register_op_cmd("roflcopter", RoflcopterPlugin())





class DestinyHandler(plugins.ChannelJoinHandler):
    def execute(self):
        if self.nick != "destiny":
            return

        return ">> https://www.youtube.com/watch?v=fNmDgRwNFsI <<"

#plugins.register_channel_join_handler(DestinyHandler())
