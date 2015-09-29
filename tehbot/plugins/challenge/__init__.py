from tehbot.plugins import *
import tehbot.plugins as plugins
import shlex
import importlib

path = __name__

sitemap = {
    "rev" : "revel",
    "revel" : "revel",
    "revolutionelite" : "revel",
    "hs" : "hs",
    "happy-security" : "hs",
    "happysecurity" : "hs",
    "happysec" : "hs",
    "wechall" : "wc",
    "wc" : "wc"
}

class StatsPlugin(Plugin):
    """Shows current stats for a user on a challenge site."""

    def __init__(self):
        Plugin.__init__(self)
        self.parser = plugins.ThrowingArgumentParser(
                prog="stats",
                description=StatsPlugin.__doc__
        )
        self.parser.add_argument("user", nargs="?")
        self.parser.add_argument("-s", "--site", choices=sorted(set(sitemap.keys())))

    def execute(self):
        self.parser.set_defaults(user=self.nick, site=self.target[1:])

        try:
            pargs = self.parser.parse_args(shlex.split(plugins.to_utf8(self.args or "")))
            if self.parser.help_requested:
                return self.parser.format_help().strip()
            user = plugins.from_utf8(pargs.user)
            site = plugins.from_utf8(pargs.site).lower()
        except plugins.ArgumentParserError as e:
            return "Error: %s" % str(e)
        except (SystemExit, NameError, ValueError):
            return self.help(self.cmd)

        if not sitemap.has_key(site):
            return "Unknown site: %s" % site

        module = importlib.import_module("." + sitemap[site], path)
        globals()[module.__name__] = module
        return module.stats(user)

register_cmd("stats", StatsPlugin())

class SolversPlugin(Plugin):
    """Shows how many solved a challenge."""

    def __init__(self):
        Plugin.__init__(self)
        self.parser = plugins.ThrowingArgumentParser(
                prog="solvers",
                description=SolversPlugin.__doc__
        )
        self.parser.add_argument("challenge_name_or_nr")
        self.parser.add_argument("-n", "--numeric", action="store_true")
        self.parser.add_argument("-s", "--site", choices=sorted(set(sitemap.keys())))

    def execute(self):
        self.parser.set_defaults(site=self.target[1:])

        try:
            pargs = self.parser.parse_args(shlex.split(plugins.to_utf8(self.args or "")))
            if self.parser.help_requested:
                return self.parser.format_help().strip()
            challenge_name_or_nr = plugins.from_utf8(pargs.challenge_name_or_nr)
            if pargs.numeric:
                challenge_name_or_nr = int(challenge_name_or_nr)
            site = plugins.from_utf8(pargs.site).lower()
        except plugins.ArgumentParserError as e:
            return "Error: %s" % str(e)
        except (SystemExit, NameError, ValueError):
            return self.help(self.cmd)

        if not sitemap.has_key(site):
            return "Unknown site: %s" % site

        module = importlib.import_module("." + sitemap[site], path)
        globals()[module.__name__] = module
        return module.solvers(challenge_name_or_nr)

register_cmd("solvers", SolversPlugin())
