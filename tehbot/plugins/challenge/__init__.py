from tehbot.plugins import *
import tehbot.plugins as plugins
import shlex
import importlib
import urllib
import urllib2
import re
import irc.client

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
    "wc" : "wc",
    "nf" : "nf",
    "net-force" : "nf",
    "ht" : "hackthis",
    "hackthis" : "hackthis",
    "wix" : "wix",
    "wixxerd" : "wix"
}

class StatsPlugin(Plugin):
    """Shows current stats for a user on a challenge site."""

    def __init__(self):
        Plugin.__init__(self)
        self.parser.add_argument("user_or_rank", nargs="?")
        self.parser.add_argument("-n", "--numeric", action="store_true")
        group = self.parser.add_mutually_exclusive_group()
        group.add_argument("-s", "--site", choices=sorted(set(sitemap.keys())))
        group.add_argument("-g", "--global", action="store_true")

    def execute(self, connection, event, extra, dbconn):
        self.parser.set_defaults(user_or_rank=event.source.nick)
        self.parser.set_defaults(site=event.target[1:] if irc.client.is_channel(event.target) else event.target)

        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
            user, rank = None, None
            if pargs.numeric:
                rank = int(pargs.user_or_rank)
            else:
                user = pargs.user_or_rank
            site = pargs.site.lower()
            glob = vars(pargs)["global"]
        except Exception as e:
            return u"Error: %s" % str(e)

        if glob:
            wcurl = "https://www.wechall.net/wechall.php?%s"
            username = str(rank) if rank else user
            query = urllib.urlencode({"username" : plugins.to_utf8(username)})
            res = plugins.from_utf8(urllib2.urlopen(wcurl % query).read())
            return "\x0303[WeChall Global]\x03 " + res

        if not sitemap.has_key(site):
            return "Unknown site: %s" % site

        module = importlib.import_module("." + sitemap[site], path)
        globals()[module.__name__] = module
        return module.stats(user, rank)

register_plugin("stats", StatsPlugin())

class SolversPlugin(Plugin):
    """Shows how many solved a challenge."""

    def __init__(self):
        Plugin.__init__(self)
        self.parser.add_argument("challenge_name_or_nr")
        self.parser.add_argument("-n", "--numeric", action="store_true")
        self.parser.add_argument("-s", "--site", choices=sorted(set(sitemap.keys())))
        self.parser.add_argument("-u", "--user")

    def execute(self, connection, event, extra, dbconn):
        self.parser.set_defaults(site=event.target[1:] if irc.client.is_channel(event.target) else event.target)

        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
            challenge_name_or_nr = pargs.challenge_name_or_nr
            if pargs.numeric:
                challenge_name_or_nr = int(challenge_name_or_nr)
            site = pargs.site.lower()
            user = pargs.user
        except Exception as e:
            return u"Error: %s" % str(e)

        if not sitemap.has_key(site):
            return u"Unknown site: %s" % site

        module = importlib.import_module("." + sitemap[site], path)
        globals()[module.__name__] = module
        return module.solvers(challenge_name_or_nr, user=user)

class SolvedHandler(ChannelHandler):
    def __init__(self):
        ChannelHandler.__init__(self)
        self.regex = []
        self.regex.append(re.compile(r'''\s*ok\s+tehbot,\s*has\s+(\w+)\s+solved\s+["']?(.+?)["']?\s*\??$''', re.I))
        self.regex.append(re.compile(r'''\s*ok\s+tehbot,\s*did\s+(\w+)\s+solve\s+["']?(.+?)["']?\s*\??$''', re.I))

    def execute(self, connection, event, extra, dbconn):
        for r in self.regex:
            match = r.search(extra["msg"])
            if match is not None:
                user = match.group(1)
                chall = match.group(2)

                plugin = self.tehbot.cmd_handlers["solvers"]
                plugin.handle(connection, event, {"args":'-u %s "%s"' % (user, chall)}, dbconn)
                break

register_plugin("solvers", SolversPlugin())
register_channel_handler(SolvedHandler())
