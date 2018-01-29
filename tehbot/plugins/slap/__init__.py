from tehbot.plugins import *
import tehbot.plugins as plugins
import random
import os.path

class SlapPlugin(Plugin):
    slaps = [
        "pulls out {victim}'s eyeballs{howmuch} and plays baseball with them.",
        "slaps {victim} around{howmuch}{withitem}."
    ]
    slaps_extra = [
        (plugins.me, "hops on a jet and flies away."),
        (plugins.say, "I pity the fool that doesnt slap back!")
    ]
    slapitems = open("%s/slaps.txt" % os.path.dirname(__file__)).read().splitlines()

    def execute(self):
        if not self.args:
            return

        victim = self.args.split()[0][:25]
        if random.randint(0, len(self.slapitems)) == len(self.slapitems):
            slap = self.slaps[0]
        else:
            slap = self.slaps[1]
        txt = slap.format(victim=plugins.myfilter(victim), howmuch=random.choice(["", " a bit", " a little bit"]), withitem=random.choice(self.slapitems))
        plugins.me(self.connection, self.target, txt, self.dbconn)

        if random.random() < 0.25:
            func, txt = random.choice(self.slaps_extra)
            func(self.connection, self.target, txt, self.dbconn)

class LivinSlapPlugin(Plugin):
    def slap2(self, victim):
        plugins.me(self.connection, self.target,  "slaps %s around a bit with a Piece of bacon" % victim, self.dbconn)
        plugins.say(self.connection, self.target, "Hey, %s, eat some pork!" % victim, self.dbconn)

    def execute(self):
        if self.args:
            return "no"

        self.slap2("livinskull")

register_pub_cmd("slap", SlapPlugin())
register_pub_cmd("livinslap", LivinSlapPlugin())
