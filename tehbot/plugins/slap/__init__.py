from tehbot.plugins import *
import tehbot.plugins as plugins
import random
import os.path

class SlapPlugin(Plugin):
    def __init__(self):
        Plugin.__init__(self)
        self.parser.add_argument("victim")

        self.slaps = [
            "pulls out {victim}'s eyeballs{howmuch} and plays baseball with them.",
            "slaps {victim} around{howmuch} with {withitem}."
        ]
        self.slaps_extra = [
            ("me", "hops on a jet and flies away."),
            ("say", "I pity the fool that doesnt slap back!")
        ]
        self.slapitems = open("%s/slaps.txt" % os.path.dirname(__file__)).read().splitlines()

    def execute(self, connection, event, extra, dbconn):
        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % str(e)

        if random.randint(0, len(self.slapitems)) == len(self.slapitems):
            slap = self.slaps[0]
        else:
            slap = self.slaps[1]
        txt = slap.format(victim=pargs.victim, howmuch=random.choice(["", " a bit", " a little bit"]), withitem=random.choice(self.slapitems))
        res = [("me", txt)]

        if random.random() < 0.5:
            res.append(random.choice(self.slaps_extra))

        return res

register_plugin("slap", SlapPlugin())

class LivinSlapPlugin(Plugin):
    def slap2(self, victim):
        return [
                ("me", "slaps %s around a bit with a Piece of bacon" % victim),
                ("say", "Hey, %s, eat some pork!" % victim)
                ]

    def execute(self, connection, event, extra, dbconn):
        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % str(e)

        return self.slap2("livinskull")

register_plugin("livinslap", LivinSlapPlugin())
