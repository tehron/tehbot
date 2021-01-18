from tehbot.plugins import *
import shlex
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import re
import lxml.html
import datetime
import time
from pony.orm import *

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
        return channel

    @staticmethod
    def remote_update(site, user):
        print("remote_update(%s, %s)" % (site, user))
        page = urllib.request.urlopen(url % (urllib.parse.quote(site), urllib.parse.quote(user))).read()
        page = page.decode("utf-8")
        match = re.search(r'<li>(.*)</li>', page)
        if match:
            out = match.group(1)
            if re.search(r'^(You) (:?lost|gained)', out) is not None:
                out = re.sub(r'^You', user, out)
            return out
        return page

    @staticmethod
    @db_session
    def wcstats(db, top, when):
        prefix = "\x0303[WeChall Statistics]\x03 "
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        startdate = when - datetime.timedelta(days=1)

        mindt = datetime.datetime.combine(startdate, datetime.time(20, 0))
        maxdt = datetime.datetime.combine(when, datetime.time(20, 0))

        topscorers = dict()
        query = select((x.wcusername, sum(x.gainabs)) for x in db.WeChallActivityPoller if x.datestamp > mindt and x.datestamp <= maxdt and x.type == "gain").order_by(lambda name, totalgain: desc(totalgain))
        for name, score in query:
            if score not in topscorers:
                topscorers[score] = []
            topscorers[score].append(name)

            if len(topscorers) == top:
                break

        if when == yesterday:
            whenstr = "yesterday"
        elif when == today:
            whenstr = "today"
        else:
            whenstr = when.strftime('%Y-%m-%d')

        if len(topscorers) == 0:
            return "No activity yet for %s" % whenstr

        def names(lst):
            a = ", ".join(lst[:len(lst) - 1])
            if a:
                a += " and "
            return a + lst[-1]

        return prefix + "Top Scorer of %s: %s" % (whenstr, " | ".join("%s (%d)" % (names(topscorers[score]), score) for score in sorted(topscorers, reverse=True)))

    @staticmethod
    @db_session
    def wcstats_all(db, top):
        prefix = "\x0303[WeChall Statistics]\x03 "

        topscorers = dict()
        query = select(((x.datestamp - datetime.timedelta(hours=20)).date(), sum(x.gainabs), x.wcusername) for x in db.WeChallActivityPoller if x.type == "gain").order_by(lambda date, totalgain, name: desc(totalgain))
        for date, score, name in query:
            if score not in topscorers:
                topscorers[score] = []
            topscorers[score].append((name, date))

            if len(topscorers) == top:
                break

        if len(topscorers) == 0:
            return "No activity yet"

        def names(lst):
            a = ", ".join("%s (%s)" % (name, date.strftime('%Y-%m-%d')) for name, date in lst[:len(lst) - 1])
            if a:
                a += " and "
            return a + ("%s (%s)" % (lst[-1][0], lst[-1][1].strftime('%Y-%m-%d')))

        return prefix + "All Time Top Scorers: %s" % (" | ".join("%d pts of %s" % (score, names(topscorers[score])) for score in sorted(topscorers, reverse=True)))

class RemoteUpdatePlugin(StandardCommand):
    """Updates WeChall score for a user on a site."""

    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("user", nargs="?")
        self.parser.add_argument("-s", "--site")

    def commands(self):
        return "wcup"

    def execute(self, connection, event, extra):
        self.parser.set_defaults(user=event.source.nick, site=Util.chan2wc(event.target))

        try:
            pargs = self.parser.parse_args(extra["args"])
            m = self.parser.get_help_msg()
            if m:
                return m.strip()
            user = pargs.user
            site = pargs.site

            if not site:
                raise Exception("Unknown site: %s" % event.target)
        except Exception as e:
            return "Error: %s" % str(e)

        return "\x0303[WeChall Update]\x03 " + Util.remote_update(site, user)

class HistoryPlugin(StandardCommand):
    """Shows latest activity for a user on WeChall."""

    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("user", nargs="?")

    def commands(self):
        return "wclast"

    def execute(self, connection, event, extra):
        self.parser.set_defaults(user=event.source.nick)

        try:
            pargs = self.parser.parse_args(extra["args"])
            m = self.parser.get_help_msg()
            if m:
                return m.strip()
            user = pargs.user
        except Exception as e:
            return "Error: %s" % str(e)

        url = "http://www.wechall.net/en/history/for/%s/by/userhist_date/DESC/page-1"
        query = urllib.parse.quote_plus(user)
        prefix = "\x0303[WeChall History]\x03 "

        try:
            req = urllib.request.urlopen(url % query)
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
                return prefix + "%s %s some unknown time ago." % (user, what)
            return prefix + "%s %s on %s." % (user, what, when)
        except Exception as e:
            print(e)
            return "Parse Error"

class WeChallInfoPlugin(StandardCommand):
    """Shows various information about a user on WeChall."""

    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("user", nargs="?")

    def commands(self):
        return "wcinfo"

    def execute(self, connection, event, extra):
        self.parser.set_defaults(user=event.source.nick)

        try:
            pargs = self.parser.parse_args(extra["args"])
            m = self.parser.get_help_msg()
            if m:
                return m.strip()
            user = pargs.user
        except Exception as e:
            return "Error: %s" % str(e)

        profileurl = "http://www.wechall.net/en/profile/%s"
        xpuser = "//div[@id='page']/div[@class='fl']/table/tr"
        xpactivity = "//div[@id='page']/table[@class='cl']/tr"
        prefix = "\x0303[WeChall Info]\x03 "
        timefmt = "%b %d, %Y - %H:%M:%S"

        try:
            tree = lxml.html.parse(urllib.request.urlopen(profileurl % urllib.parse.quote_plus(user)))
            user, score, rank, regdate, lastlogin, views, email, lastact, birthdate = None, None, None, None, None, None, None, None, None
            lastacttxt = None
            country = None

            for row in tree.xpath(xpuser):
                etag = row.xpath("th")
                evalue = row.xpath("td")
                if etag and evalue:
                    s = etag[0].text_content().strip().lower()
                    v = evalue[0].text_content().strip()
                    if s == "country":
                        country = evalue[0].xpath("img/@alt")[0]
                    if s == "username":
                        user = v
                    elif s == "score":
                        score = int(v)
                    elif s == "global rank" and v.lower() != "hidden":
                        rank = int(v)
                    elif s == "register date":
                        regdate = time.mktime(time.strptime(v, timefmt))
                    elif s == "last activity" and v.lower() != "unknown":
                        lastlogin = time.mktime(time.strptime(v, timefmt))
                    elif s == "profile views":
                        views = int(v)
                    elif s == "email":
                        email = v
                    elif s == "birthdate":
                        birthdate = datetime.datetime.strptime(v, "%a, %b %d, %Y").date()

            for row in tree.xpath(xpactivity):
                ev1 = row.xpath("td[1]")
                ev2 = row.xpath("td[2]")
                if ev1 and ev2:
                    v = ev1[0].text_content().strip()
                    t = ev2[0].text_content().strip()
                    if v.lower() != "unknown":
                        lastact = time.mktime(time.strptime(v, timefmt))
                        lastacttxt = t[0].lower() + t[1:]
                        break

        except Exception as e:
            print(e)
            return "Parse Error"

        if user is None:
            return prefix + "The requested user was not found."

        now = time.time()
        timestr1 = "moments" if now - regdate < 120 else Plugin.time2str(now, regdate)
        rankstr = "" if rank is None else " (holding rank %d)" % rank
        res = "%s registered to WeChall %s ago. The user has a score of %d point%s%s and their profile has been viewed %d times since." % (user, timestr1, score, "" if score == 1 else "s", rankstr, views)
        if country is not None:
            res += " %s comes from %s." % (user, country)
        if lastlogin is not None:
            timestr2 = "moments" if now - lastlogin < 120 else Plugin.time2str(now, lastlogin)
            res += " The last user's login was %s ago." % timestr2
        if lastact is not None:
            timestr2 = "moments" if now - lastact < 120 else Plugin.time2str(now, lastact)
            res += " The user %s %s ago." % (lastacttxt, timestr2)
        if rank is not None:
            res += " %s is %son page 1." % (user, "\x02not\x02 " if rank > 50 else "")
        if birthdate is not None:
            today = datetime.date.today()
            age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
            res += " The user is %d years old." % age
            if today.month == birthdate.month and today.day == birthdate.day:
                res += " Happy birthday, %s!" % user
        return prefix + res


class WeChallActivityPoller(Poller):
    @db_session
    def create_entities(self):
        class WeChallActivityPoller(self.db.Entity):
            datestamp = Required(datetime.datetime)
            type = Required(str)
            wcusername = Required(str)
            sitename = Required(str)
            siteusername = Required(str)
            siterank = Required(int)
            sitescore = Required(int)
            sitemaxscore = Required(int)
            sitepercent = Required(str)
            gainpercent = Required(str)
            score = Required(int)
            gainabs = Required(int)

    @db_session
    def lastDatestamp(self):
        x = select(x for x in self.db.WeChallActivityPoller).order_by(desc(self.db.WeChallActivityPoller.datestamp))[:1]
        return x[0].datestamp if x else datetime.datetime(2017, 11, 2, 19, 38, 55)

    def execute(self, connection, event, extra):
        prefix = "\x0303[WeChall Activity]\x03 "
        url = "http://www.wechall.net/index.php?mo=WeChall&me=API_History&no_session=1&datestamp=%s"
        msgs = []
        page = urllib.request.urlopen(url % self.lastDatestamp().strftime("%Y%m%d%H%M%S"))

        with db_session:
            for line in page.readlines()[1:]:
                line = Plugin.from_utf8(line)
                datestamp, typ, wcusername, sitename, siteusername, siterank, sitescore, sitemaxscore, sitepercent, gainpercent, score, gainabs = line.strip().replace("\\:", ":").replace("\\n", "\n").split("::")
                self.db.WeChallActivityPoller(datestamp=datetime.datetime.strptime(datestamp, "%Y%m%d%H%M%S"), type=typ, wcusername=wcusername, sitename=sitename, siteusername=siteusername, siterank=int(siterank), sitescore=int(sitescore), sitemaxscore=int(sitemaxscore), sitepercent=sitepercent, gainpercent=gainpercent, score=int(score), gainabs=int(gainabs))

                if 0 < int(siterank) <= 10 and (typ == "gain" or typ == "lost"):
                    msgs.append(prefix + "%s just %s %s on %s totaling %s." % (Plugin.bold(wcusername), "gained" if typ == "gain" else "lost", gainpercent, Plugin.bold(sitename), sitepercent))

        msg = "\n".join(msgs)
        if msg:
            return [("announce", (self.where(), msg))]

class WcStatsPlugin(StandardCommand):
    """Shows latest WeChall statistics."""

    def __init__(self, db):
        def checkdate(s):
            if s == "today":
                return datetime.date.today()
            if s == "yesterday":
                return datetime.date.today() - datetime.timedelta(days=1)
            return datetime.date.fromtimestamp(time.mktime(time.strptime(s, '%Y-%m-%d')))

        StandardCommand.__init__(self, db)
        self.parser.add_argument("-t", "--top", type=int, choices=list(range(1, 10 + 1)))
        group = self.parser.add_mutually_exclusive_group()
        group.add_argument("-d", "--date", type=checkdate, help="format '%%Y-%%m-%%d'")
        group.add_argument("-a", "--all-time", action="store_true")

    def commands(self):
        return "wcstats"

    def execute(self, connection, event, extra):
        self.parser.set_defaults(top=3, date=datetime.date.today())

        try:
            pargs = self.parser.parse_args(extra["args"])
            m = self.parser.get_help_msg()
            if m:
                return m.strip()
        except Exception as e:
            return "Error: %s" % str(e)

        with db_session:
            if pargs.all_time:
                return Util.wcstats_all(self.db, pargs.top)
            return Util.wcstats(self.db, pargs.top, pargs.date)

class WeChallStatsAnnouncer(Announcer):
    def default_settings(self):
        return { "at" : 72000 }

    def execute(self, connection, event, extra):
        today = datetime.date.today()
        return [("announce", (self.where(), Util.wcstats(self.db, 3, today)))]

class WeChallSitesPoller(Poller):
    @db_session
    def create_entities(self):
        class WeChallSitesPoller(self.db.Entity):
            ts = Required(datetime.datetime)
            sitename = Required(str)
            classname = PrimaryKey(str, max_len=20)
            status = Required(str)
            url = Optional(str)
            profileurl = Optional(str)
            usercount = Required(int)
            linkcount = Required(int)
            challcount = Required(int)
            basescore = Required(int)
            average = Required(float)
            score = Required(int)
            challts = Required(datetime.datetime)

            def needs_update(self, sitename, status, url, profileurl, usercount, linkcount, challcount, basescore, average, score):
                return self.sitename != sitename or self.status != status or self.url != url or self.profileurl != profileurl or self.usercount != usercount or self.linkcount != linkcount or self.challcount != challcount or self.basescore != basescore or self.average != average or self.score != score

    def execute(self, connection, event, extra):
        prefix = "\x0303[WeChall Sites]\x03 "
        url = "https://www.wechall.net/index.php?mo=WeChall&me=API_Site&no_session=1"
        msgs = []
        page = urllib.request.urlopen(url)
        now = datetime.datetime.now()

        with db_session:
            for line in page.readlines():
                line = Plugin.from_utf8(line)
                sitename, classname, status, url, profileurl, usercount, linkcount, challcount, basescore, average, score = [x.replace("\\:", ":").replace("\\n", "\n") for x in line.strip().split("::", 10)]
                usercount, linkcount, challcount, basescore, score = int(usercount), int(linkcount), int(challcount), int(basescore), int(score)
                average = float(average.replace("%", ""))
                site = self.db.WeChallSitesPoller.get(classname=classname)

                if not site and status == "up":
                    self.db.WeChallSitesPoller(ts=now, sitename=sitename, classname=classname, status=status, url=url, profileurl=profileurl, usercount=usercount, linkcount=linkcount, challcount=challcount, basescore=basescore, average=average, score=score, challts=now)
                    msgs.append(prefix + "A new challenge site just spawned! Check out %s at %s" % (sitename, url))

                if site and site.needs_update(sitename, status, url, profileurl, usercount, linkcount, challcount, basescore, average, score):
                    diff = challcount - site.challcount
                    status_changed = status != site.status
                    site.ts = now
                    site.sitename = sitename
                    site.status = status
                    site.url = url
                    site.profileurl = profileurl
                    site.usercount = usercount
                    site.linkcount = linkcount
                    site.challcount = challcount
                    site.basescore = basescore
                    site.average = average
                    site.score = score

                    if diff != 0:
                        if diff > 0:
                            site.challts = now

                        if diff == 1:
                            msgs.append(prefix + "There is 1 new challenge on %s" % sitename)
                        elif diff > 1:
                            msgs.append(prefix + "There are %d new challenges on %s" % (diff, sitename))
                        else:
                            msgs.append(prefix + "%s just deleted %d of their challenges" % (sitename, -diff))
                    elif status_changed:
                        if status == "dead":
                            msgs.append(prefix + "Another one bites the dust: %s just vanished." % sitename)
                        elif status == "up":
                            msgs.append(prefix + "Uh!? %s is online again! wb" % sitename)

        msg = "\n".join(msgs)
        if msg:
            return [("announce", (self.where(), msg))]


class WcSitePlugin(StandardCommand):
    """Shows information about a site on WeChall"""

    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("site", nargs="?")
        self.parser.add_argument("--last", action="store_true")

    def commands(self):
        return "wcsite"

    def prefix(self):
        return "[WcSite] "

    def execute(self, connection, event, extra):
        dbchange = datetime.datetime.fromtimestamp(1566070200.0)
        self.parser.set_defaults(site=event.target)

        try:
            pargs = self.parser.parse_args(extra["args"])
            m = self.parser.get_help_msg()
            if m:
                return m.strip()
            sitename = pargs.site
        except Exception as e:
            return Plugin.red(self.prefix()) + "Error: %s" % str(e)

        if sitename.startswith("#"):
            site = Util.chan2wc(sitename)
        else:
            site = sitename

        now = datetime.datetime.now()

        with db_session:
            data = select(s for s in self.db.WeChallSitesPoller if s.classname.lower() == site.lower())

            if not data:
                return Plugin.red(self.prefix()) + "Unknown site: %s" % sitename

            site = data.first()

            if pargs.last:
                if site.challts < dbchange:
                    timestr = "unknown"
                else:
                    timestr = "just now" if (now - site.challts).total_seconds() < 3600 else Plugin.time2str(now, site.challts)
                return Plugin.green(self.prefix()) + "Time since last challenge on %s: %s" % (site.sitename, timestr)
            else:
                if site.challts < dbchange:
                    challstr = "The latest challenge age is unknown."
                else:
                    timestr = Plugin.time2str(now, site.challts)
                    challstr = "The latest challenge is %s old." % timestr

                if site.linkcount == 0:
                    linkstr = "No user has"
                elif site.linkcount == 1:
                    linkstr = "1 user has"
                else:
                    linkstr = "%d users have" % site.linkcount
                return Plugin.green(self.prefix()) + "%s (%s) has %d challenges. %d users are registered to the site. The site is %s. %s linked their account. WeChall score is %d. %s" % (site.sitename, site.classname, site.challcount, site.usercount, site.status, linkstr, site.score, challstr)
