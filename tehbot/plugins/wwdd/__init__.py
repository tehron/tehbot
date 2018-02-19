from tehbot.plugins import *
import random

class WwddPlugin(Plugin):
    """Use this command to see what dloser would do"""

    def __init__(self):
        Plugin.__init__(self)

    def execute(self, connection, event, extra, dbconn):
        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % str(e)

        actions = [
                None,
                "dloser says: you're a moron!",
                "dloser says: i really like this (in a really high voice)",
                "dloser says: i love you (and dies)",
                "dloser pukes",
                "dloser says: i will give it. (but i won't)",
                "dloser says: so helpful"
                ]

        return random.choice(actions)

register_plugin("wwdd", WwddPlugin())
