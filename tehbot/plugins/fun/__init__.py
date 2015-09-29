from tehbot.plugins import *
import urllib
import random

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

        random.shuffle(puns)
        if puns:
            return puns[0]

register_cmd("pun", PunsPlugin())



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
