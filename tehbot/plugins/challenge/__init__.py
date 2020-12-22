from tehbot.plugins import *
import importlib
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import irc.client

__all__ = [ "BaseSite", "NoSuchChallengeError", "NoSuchUserError", "ChallengesNotNumberedError", "UnknownReplyFormat", "Plugin" ]

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
    "ht" : "defendtheweb",
    "hackthis" : "defendtheweb",
    "dtw" : "defendtheweb",
    "defendtheweb" : "defendtheweb",
    "wix" : "wix",
    "wixxerd" : "wix",
    "tbs" : "tbs",
    "st" : "st",
    "securitytraps" : "st",
    "rankk" : "rankk",
    "pyramid" : "rankk",
    "247ctf" : "two47ctf",
    "cryptohack" : "cryptohack",
    "ch" : "cryptohack",
    "py" : "py",
    "pydefis" : "py"
}

class BaseSite:
    def prefix(self):
        return "[Challenge]"

    def siteurl(self):
        return "https://www.google.com"

    def str2nr(self, s):
        return int(s)

    def nr2str(self, nr):
        return str(nr)

    def userstats(self, user):
        raise NotImplementedError

    def rankstats(self, rank):
        raise NotImplementedError

    def solvers(self, challname, challnr, user):
        raise NotImplementedError

class NoSuchChallengeError(Exception):
    pass

class NoSuchUserError(Exception):
    pass

class ChallengesNotNumberedError(Exception):
    pass

class UnknownReplyFormat(Exception):
    pass

class InvalidLoginError(Exception):
    pass


class StatsPlugin(StandardCommand):
    """Shows current stats for a user on a challenge site."""

    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("user_or_rank", nargs="?")
        self.parser.add_argument("-n", "--numeric", action="store_true")
        group = self.parser.add_mutually_exclusive_group()
        group.add_argument("-s", "--site", choices=sorted(set(sitemap.keys())))
        group.add_argument("-g", "--global", action="store_true")

    def commands(self):
        return "stats"

    def stats(self, site, user, rank):
        try:
            if user:
                res = site.userstats(user)
                if res is None:
                    txt = "The requested user was not found. You can register at %s." % site.siteurl()
                else:
                    user, solved, solvedmax, rank, usercount, score, scoremax, extra = res
                    if rank is not None:
                        ranktext = " and is on rank %s (of %d)" % (rank, usercount) if usercount is not None else " and is on rank %s" % rank
                    else:
                        ranktext = ""
                    if score is not None:
                        ranktext += " scoring %d (of %d) points" % (score, scoremax) if scoremax is not None else " scoring %d points" % (score)
                    txt = "%s solved %s (of %d) challenges%s.%s"% (user, solved, solvedmax, ranktext, extra or "")
            else:
                res = site.rankstats(rank)
                if res is None:
                    txt = "No user is at rank %d." % rank
                else:
                    solved, who, solvedmax = res
                    txt = ", ".join(who) + (" is" if len(who) == 1 else " are") + " at rank %d with %s (of %d) challenge%s solved." % (rank, solved, solvedmax, "s" if solved else "")
        except Exception as e:
            return "%s %s" % (Plugin.red(site.prefix()), Plugin.exc2str(e))

        return "%s %s" % (Plugin.green(site.prefix()), txt)

    def values_to_set(self):
        return Plugin.values_to_set(self) + [ "securitytraps_api_key", "247ctf_api_key", "defendtheweb_auth_key", "cryptohack_api_key", "tbs.user", "tbs.password", "cryptohack.user", "cryptohack.password", "pydefis_api_key" ]

    def execute(self, connection, event, extra):
        self.parser.set_defaults(user_or_rank=event.source.nick)
        self.parser.set_defaults(site=event.target[1:] if irc.client.is_channel(event.target) else event.target)

        try:
            pargs = self.parser.parse_args(extra["args"])
            m = self.parser.get_help_msg()
            if m:
                return m.strip()
            user, rank = None, None
            if pargs.numeric:
                rank = int(pargs.user_or_rank)
            else:
                user = pargs.user_or_rank
            site = pargs.site.lower()
            glob = vars(pargs)["global"]
        except Exception as e:
            return "Error: %s" % str(e)

        if glob:
            wcurl = "https://www.wechall.net/wechall.php?%s"
            username = str(rank) if rank else user
            query = urllib.parse.urlencode({"username" : Plugin.to_utf8(username)})
            res = Plugin.from_utf8(urllib.request.urlopen(wcurl % query).read())
            return "\x0303[WeChall Global]\x03 " + res

        if site not in sitemap:
            return "Unknown site: %s" % site

        try:
            module = importlib.import_module("tehbot.plugins.challenge.%s" % sitemap[site])
            importlib.reload(module)
            site = module.Site()
            site.settings = self.settings
        except Exception as e:
            print(e)
            return "SiteImportError: %s" % site

        return self.stats(site, user, rank)

class SolversPlugin(StandardCommand):
    """Shows how many solved a challenge."""

    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("challenge_name_or_nr", nargs="+")
        self.parser.add_argument("-n", "--numeric", action="store_true")
        self.parser.add_argument("-s", "--site", choices=sorted(set(sitemap.keys())))
        self.parser.add_argument("-u", "--user")

    def commands(self):
        return "solvers"

    def solvers(self, sitename, challenge_name_or_nr, numeric, user):
        if sitename not in sitemap:
            return "Unknown site: %s" % sitename

        try:
            module = importlib.import_module("tehbot.plugins.challenge.%s" % sitemap[sitename])
            importlib.reload(module)
            site = module.Site()
            site.settings = self.settings
        except Exception as e:
            print(e)
            return "SiteImportError: %s" % sitename

        try:
            if numeric:
                challname, challnr = None, site.str2nr(challenge_name_or_nr)
            else:
                challname, challnr = challenge_name_or_nr, None
        except Exception as e:
            return "Error: %s" % str(e)

        try:
            user, nr, name, cnt, solvers, solved = site.solvers(challname, challnr, user)
            pre = "Challenge Nr. %s, %s, " % (site.nr2str(nr), name) if nr is not None else "Challenge '%s' " % name

            if user is not None:
                txt = pre + "has%s been solved by %s." % ("" if solved else " \x02not\x02", user)
            elif cnt == 0:
                txt = pre + "hasn't been solved by anyone yet."
            else:
                txt = pre + "has been solved by %d user%s." % (cnt, "" if cnt == 1 else "s")
                if solvers:
                    txt += " Last by %s." % ", ".join(solvers[:5])
        except Exception as e:
            import traceback
            traceback.print_exc()
            return "%s %s" % (Plugin.red(site.prefix()), Plugin.exc2str(e))

        return "%s %s" % (Plugin.green(site.prefix()), txt)

    def values_to_set(self):
        return Plugin.values_to_set(self) + [ "securitytraps_api_key", "247ctf_api_key", "defendtheweb_auth_key", "cryptohack_api_key", "tbs.user", "tbs.password", "cryptohack.user", "cryptohack.password" ]


    def execute(self, connection, event, extra):
        self.parser.set_defaults(site=event.target[1:] if irc.client.is_channel(event.target) else event.target)

        try:
            pargs = self.parser.parse_args(extra["args"])
            m = self.parser.get_help_msg()
            if m:
                return m.strip()
            challenge_name_or_nr = " ".join(pargs.challenge_name_or_nr)
            site = pargs.site.lower()
            user = pargs.user
            numeric = pargs.numeric
        except Exception as e:
            return "Error: %s" % str(e)

        return self.solvers(site, challenge_name_or_nr, numeric, user)
