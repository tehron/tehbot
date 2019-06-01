from tehbot.plugins import *
import importlib
import urllib
import urllib2
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
    "ht" : "hackthis",
    "hackthis" : "hackthis",
    "wix" : "wix",
    "wixxerd" : "wix",
    "tbs" : "tbs",
    "st" : "st",
    "securitytraps" : "st",
    "rankk" : "rankk",
    "pyramid" : "rankk",
}

class BaseSite:
    def prefix(self):
        return u"[Challenge]"

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


class StatsPlugin(StandardCommand):
    """Shows current stats for a user on a challenge site."""

    def __init__(self):
        StandardCommand.__init__(self)
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
                    txt = u"The requested user was not found. You can register at %s." % site.siteurl()
                else:
                    user, solved, solvedmax, rank, usercount, score, scoremax, extra = res
                    if rank is not None:
                        ranktext = u" and is on rank %s (of %d)" % (rank, usercount) if usercount is not None else u" and is on rank %s" % rank
                    else:
                        ranktext = u""
                    if score is not None:
                        ranktext += u" scoring %d (of %d) points" % (score, scoremax) if scoremax is not None else u" scoring %d points" % (score)
                    txt = u"%s solved %s (of %d) challenges%s.%s"% (user, solved, solvedmax, ranktext, extra or "")
            else:
                res = site.rankstats(rank)
                if res is None:
                    txt = u"No user is at rank %d." % rank
                else:
                    solved, who, solvedmax = res
                    txt = ", ".join(who) + (" is" if len(who) == 1 else " are") + " at rank %d with %s (of %d) challenge%s solved." % (rank, solved, solvedmax, "s" if solved else "")
        except Exception as e:
            return u"%s %s" % (Plugin.red(site.prefix()), Plugin.exc2str(e))

        return u"%s %s" % (Plugin.green(site.prefix()), txt)

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
            return u"Error: %s" % unicode(e)

        if glob:
            wcurl = "https://www.wechall.net/wechall.php?%s"
            username = str(rank) if rank else user
            query = urllib.urlencode({"username" : Plugin.to_utf8(username)})
            res = Plugin.from_utf8(urllib2.urlopen(wcurl % query).read())
            return "\x0303[WeChall Global]\x03 " + res

        if not sitemap.has_key(site):
            return u"Unknown site: %s" % site

        try:
            module = importlib.import_module("tehbot.plugins.challenge.%s" % sitemap[site])
            reload(module)
            site = module.Site()
            site.settings = self.settings
        except Exception as e:
            print e
            return u"SiteImportError: %s" % site

        return self.stats(site, user, rank)

class SolversPlugin(StandardCommand):
    """Shows how many solved a challenge."""

    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("challenge_name_or_nr", nargs="+")
        self.parser.add_argument("-n", "--numeric", action="store_true")
        self.parser.add_argument("-s", "--site", choices=sorted(set(sitemap.keys())))
        self.parser.add_argument("-u", "--user")

    def commands(self):
        return "solvers"

    def solvers(self, sitename, challenge_name_or_nr, numeric, user):
        if not sitemap.has_key(sitename):
            return u"Unknown site: %s" % sitename

        try:
            module = importlib.import_module("tehbot.plugins.challenge.%s" % sitemap[sitename])
            reload(module)
            site = module.Site()
            site.settings = self.settings
        except Exception as e:
            print e
            return u"SiteImportError: %s" % sitename

        try:
            if numeric:
                challname, challnr = None, site.str2nr(challenge_name_or_nr)
            else:
                challname, challnr = challenge_name_or_nr, None
        except Exception as e:
            return u"Error: %s" % unicode(e)

        try:
            user, nr, name, cnt, solvers, solved = site.solvers(challname, challnr, user)
            pre = u"Challenge Nr. %s, %s, " % (site.nr2str(nr), name) if nr is not None else u"Challenge '%s' " % name

            if user is not None:
                txt = pre + u"has%s been solved by %s." % ("" if solved else " \x02not\x02", user)
            elif cnt == 0:
                txt = pre + u"hasn't been solved by anyone yet."
            else:
                txt = pre + u"has been solved by %d user%s." % (cnt, "" if cnt == 1 else "s")
                if solvers:
                    txt += u" Last by %s." % u", ".join(solvers[:5])
        except Exception as e:
            return u"%s %s" % (Plugin.red(site.prefix()), Plugin.exc2str(e))

        return u"%s %s" % (Plugin.green(site.prefix()), txt)

    def execute(self, connection, event, extra, dbconn):
        self.parser.set_defaults(site=event.target[1:] if irc.client.is_channel(event.target) else event.target)

        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
            challenge_name_or_nr = " ".join(pargs.challenge_name_or_nr)
            site = pargs.site.lower()
            user = pargs.user
            numeric = pargs.numeric
        except Exception as e:
            return u"Error: %s" % unicode(e)

        return self.solvers(site, challenge_name_or_nr, numeric, user)
