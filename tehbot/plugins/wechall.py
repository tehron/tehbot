from tehbot.plugins import *
import shlex
import urllib
import urllib2
import re
import lxml.html
import datetime
import time

url = "http://www.wechall.net/remoteupdate.php?sitename=%s&username=%s"

class Util:
    @staticmethod
    def chan2wc(channel):
        if channel.startswith("#"):
            if channel == "#revolutionelite":
                return "RevEl"
            if channel == "#wechall":
                return "WC"
            if channel == "#hackthis":
                return "HT"
            if channel == "#happy-security":
                return "HS"
        return None

    @staticmethod
    def remote_update(site, user):
        print "remote_update(%s, %s)" % (site, user)
        page = urllib2.urlopen(url % (urllib.quote(site), urllib.quote(user))).read()
        page = page.decode("utf-8")
        match = re.search(r'<li>(.*)</li>', page)
        if match:
            out = match.group(1)
            if re.search(r'^(You) (:?lost|gained)', out) is not None:
                out = re.sub(r'^You', user, out)
            return out
        return page

    @staticmethod
    def wcstats(dbconn, top):
        prefix = "\x0303[WeChall Statistics]\x03 "
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)

        topscorers = dict()
        for row in dbconn.execute("select wcusername, sum(gainabs) as totalgain from WeChallActivityPoller where datestamp >= ? and type='gain' group by wcusername order by totalgain desc;", (today.strftime("%Y%m%d000000"), )):
            score = int(row[1])
            if not topscorers.has_key(score):
                topscorers[score] = []
            topscorers[score].append(row[0])

            if len(topscorers) == top:
                break

        if len(topscorers) == 0:
            return "No activity yet for today"

        def names(lst):
            a = ", ".join(lst[:len(lst) - 1])
            if a:
                a += " and "
            return a + lst[-1]

        return prefix + u"Today's Top Scorer: %s" % " | ".join("%s (%d)" % (names(topscorers[score]), score) for score in sorted(topscorers, reverse=True))

class RemoteUpdatePlugin(StandardCommand):
    """Updates WeChall score for a user on a site."""

    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("user", nargs="?")
        self.parser.add_argument("-s", "--site")

    def commands(self):
        return "wcup"

    def execute(self, connection, event, extra, dbconn):
        self.parser.set_defaults(user=event.source.nick, site=Util.chan2wc(event.target))

        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
            user = pargs.user
            site = pargs.site

            if not site:
                raise Exception("Unknown site: %s" % event.target)
        except Exception as e:
            return u"Error: %s" % str(e)

        return u"\x0303[WeChall Update]\x03 " + Util.remote_update(site, user)

class HistoryPlugin(StandardCommand):
    """Shows latest activity for a user on WeChall."""

    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("user", nargs="?")

    def commands(self):
        return "wclast"

    def execute(self, connection, event, extra, dbconn):
        self.parser.set_defaults(user=event.source.nick)

        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
            user = pargs.user
        except Exception as e:
            return u"Error: %s" % str(e)

        url = "http://www.wechall.net/en/history/for/%s/by/userhist_date/DESC/page-1"
        query = urllib.quote_plus(Plugin.to_utf8(user))
        prefix = "\x0303[WeChall History]\x03 "

        try:
            req = urllib2.urlopen(url % query)
        except:
            return "Network Error"

        try:
            tree = lxml.html.parse(req)
            err = tree.xpath("//div[@class='gwf_errors']/ul/li")
            if err:
                return prefix + err[0].text_content().strip()

            h = tree.xpath("//div[@id='page']/table/tr")[0]
            when = h.xpath("td[3]")[0].text_content().strip()
            what = h.xpath("td[4]")[0].text_content().strip()
            what = what[0].lower() + what[1:]

            if when.lower() == "unknown":
                return prefix + u"%s %s some unknown time ago." % (user, what)
            return prefix + u"%s %s on %s." % (user, what, when)
        except Exception as e:
            print e
            return "Parse Error"


"""
TODO: create table WeChallActivityPoller(id integer primary key, datetime integer, type text, wcusername text, sitename text, siteclass text,
"""
import time
class WeChallActivityPoller(Poller):
    def initialize(self, dbconn):
        Poller.initialize(self, dbconn)
        with dbconn:
            dbconn.execute("create table if not exists WeChallActivityPoller(id integer primary key, datestamp integer, type text, wcusername text, sitename text, siteusername text, siterank integer, sitescore integer, sitemaxscore integer, sitepercent text, gainpercent text, score integer, gainabs integer)")
            dbconn.execute("create table if not exists Timeouts(id integer primary key, poller text, ts datetime)")

    def lastDatestamp(self, dbconn):
        c = dbconn.execute("select datestamp from WeChallActivityPoller order by datestamp desc limit 1")
        res = c.fetchone()
        datestamp = 20171102193855
        if res is not None:
            datestamp = int(res[0])
        return datestamp

    def execute(self, connection, event, extra, dbconn):
        prefix = "\x0303[WeChall Activity]\x03 "
        url = "http://www.wechall.net/index.php?mo=WeChall&me=API_History&no_session=1&datestamp=%d"
        msgs = []
        page = urllib2.urlopen(url % self.lastDatestamp(dbconn))

        with dbconn:
            for line in page.readlines()[1:]:
                line = Plugin.from_utf8(line)
                datestamp, typ, wcusername, sitename, siteusername, siterank, sitescore, sitemaxscore, sitepercent, gainpercent, score, gainabs = line.strip().replace("\\:", ":").replace("\\n", "\n").split("::")
                dbconn.execute("insert into WeChallActivityPoller values(null, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (int(datestamp), typ, wcusername, sitename, siteusername, int(siterank), int(sitescore), int(sitemaxscore), sitepercent, gainpercent, int(score), int(gainabs)))
                if 0 < int(siterank) <= 10 and (typ == "gain" or typ == "lost"):
                    msgs.append(prefix + u"%s just %s %s on %s totaling %s." % (wcusername, "gained" if typ == "gain" else "lost", gainpercent, sitename, sitepercent))

        msg = u"\n".join(msgs)
        if msg:
            return [("announce", (self.where(), msg))]

class WcStatsPlugin(StandardCommand):
    """Shows latest WeChall statistics."""

    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("-t", "--top", type=int, choices=range(1, 10))

    def commands(self):
        return "wcstats"

    def execute(self, connection, event, extra, dbconn):
        self.parser.set_defaults(top=3)

        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % str(e)

        return Util.wcstats(dbconn, pargs.top)

class WeChallStatsAnnouncer(Announcer):
    def at(self):
        return self.settings.get("at", 72000)

    def execute(self, connection, event, extra, dbconn):
        return [("announce", (self.where(), Util.wcstats(dbconn, 3)))]

class WeChallSitesPoller(Poller):
    def initialize(self, dbconn):
        Poller.initialize(self, dbconn)
        with dbconn:
            dbconn.execute("create table if not exists WeChallSitesPoller(id integer primary key, ts datetime, sitename text, classname text, status text, url text, profileurl text, usercount integer, linkcount integer, challcount integer, basescore integer, average real, score integer, challts datetime)")

    def _sites(self, dbconn):
        sites = dict()
        with dbconn:
            for row in dbconn.execute("select * from WeChallSitesPoller"):
                sites[row[2]] = row
        return sites

    def execute(self, connection, event, extra, dbconn):
        prefix = "\x0303[WeChall Sites]\x03 "
        url = "https://www.wechall.net/index.php?mo=WeChall&me=API_Site&no_session=1"
        msgs = []
        page = urllib2.urlopen(url)
        sites = self._sites(dbconn)

        with dbconn:
            now = time.time()
            for line in page.readlines():
                line = Plugin.from_utf8(line)
                sitename, classname, status, url, profileurl, usercount, linkcount, challcount, basescore, average, score = map(lambda x: x.replace("\\:", ":").replace("\\n", "\n"), line.strip().split("::", 10))

                if not sites.has_key(sitename):
                    dbconn.execute("insert into WeChallSitesPoller values(null, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (now, sitename, classname, status, url, profileurl, int(usercount), int(linkcount), int(challcount), int(basescore), float(average.replace("%", "")), int(score), now))
                    msgs.append(prefix + u"A new challenge site just spawned! Check out %s at %s" % (sitename, url))
                else:
                    site = sites[sitename]
                    diff = int(challcount) - int(site[9])
                    if diff != 0:
                        dbconn.execute("update WeChallSitesPoller set challcount=?, ts=?, where id=?", (int(challcount), now, site[0]))
                        if diff > 0:
                            dbconn.execute("update WeChallSitesPoller set challts=?, where id=?", (now, site[0]))

                        if diff == 1:
                            msgs.append(prefix + u"There is 1 new challenge on %s" % sitename)
                        elif diff > 1:
                            msgs.append(prefix + u"There are %d new challenges on %s" % (diff, sitename))
                        else:
                            msgs.append(prefix + u"%s just deleted %d of their challenges" % (sitename, -diff))
                    elif status != site[4]:
                        dbconn.execute("update WeChallSitesPoller set status=?, ts=? where id=?", (status, now, site[0]))
                        if status == "down":
                            msgs.append(prefix + u"Another one bites the dust: %s just vanished." % sitename)
                        elif status == "up":
                            msgs.append(prefix + u"Uh!? %s is online again! wb" % sitename)

        msg = u"\n".join(msgs)
        if msg:
            return [("announce", (self.where(), msg))]



class WcSitePlugin(StandardCommand):
    """Shows information about a site on WeChall"""

    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("site", nargs="?")
        self.parser.add_argument("--last", action="store_true")

    def commands(self):
        return "wcsite"

    def prefix(self):
        return "[WcSite] "

    def execute(self, connection, event, extra, dbconn):
        self.parser.set_defaults(site=event.target)

        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
            sitename = pargs.site
        except Exception as e:
            return Plugin.red(self.prefix()) + u"Error: %s" % str(e)

        if sitename.startswith("#"):
            site = Util.chan2wc(sitename)
        else:
            site = sitename

        with dbconn:
            row = dbconn.cursor().execute("select * from WeChallSitesPoller where classname=? collate NOCASE", (site,)).fetchone()

        if row is None:
            return Plugin.red(self.prefix()) + u"Unknown site: %s" % sitename

        id_, ts, sitename, classname, status, url, profileurl, usercount, linkcount, challcount, basescore, average, score, challts = row

        if pargs.last:
            now = time.time()
            timestr = "just now" if now - challts < 3600 else Plugin.time2str(now, challts)
            return Plugin.green(self.prefix()) + "Time since last challenge on %s: %s" % (sitename, timestr)
        else:
            timestr = Plugin.time2str(time.time(), challts)
            return Plugin.green(self.prefix()) + "%s (%s) has %d challenges. %d users are registered to the site. The site is %s. The latest challenge is %s old." % (sitename, classname, challcount, usercount, status, timestr)
