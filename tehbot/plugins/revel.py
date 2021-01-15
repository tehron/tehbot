from tehbot.plugins import *
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import time
import ssl
import lxml.html
import re
from pony.orm import *
from datetime import datetime, timedelta

class RevelSolvedPoller(Poller):
    def prefix(self):
        return "[Revolution Elite]"

    def datestamp(self, ts):
        return time.strftime('%Y%m%d%H%M%S', time.localtime(ts))

    def timestamp(self, datestamp):
        try:
            t = time.strptime(datestamp, '%Y%m%d%H%M%S')
            ts = time.mktime(t)
        except:
            ts = 0
        return ts

    def execute(self, connection, event, extra):
        url = "https://www.revolutionelite.co.uk/w3ch4ll/solvers_revel.php?datestamp=%s"

        try:
            ts = self.settings["ts"]
        except:
            ts = 0

        try:
            reply = urllib.request.urlopen(url % self.datestamp(ts), timeout=3)
        except (urllib.error.URLError, ssl.SSLError):
            # ignore stupid SSL errors for RevEl
            return

        entries = []

        for entry in reply.readlines():
            entry = entry.decode().strip()
            if not entry:
                continue
            uid, cid, solvedate, firstdate, views, options, timetaken, tries, username, challname, solvercount, challurl = [x.replace(r"\:", ":") for x in entry.split("::")]
            uid = int(uid)
            cid = int(cid)
            tssolve = self.timestamp(solvedate)
            ts1stsolve = self.timestamp(firstdate)
            views = int(views)
            tries = int(tries)
            solvercount = int(solvercount) - 1
            entries.append((tssolve, username, challname, solvercount))

        msgs = []
        for tssolve, username, challname, solvercount in sorted(entries):
            ts = tssolve

            msg = "%s has just solved %s." % (Plugin.bold(username), Plugin.bold(challname))
            if solvercount <= 0:
                msg += " This challenge has never been solved before!"
            else:
                msg += " This challenge has been solved %d time%s before." % (solvercount, "" if solvercount == 1 else "s")

            msgs.append("%s %s" % (Plugin.green(self.prefix()), msg))

        self.settings["ts"] = ts
        self.save_settings()

        msg = "\n".join(msgs)
        if msg:
            return [("announce", (self.where(), msg))]



class RevelPoller(Poller):
    @db_session
    def create_entities(self):
        class RevelPollerNews(self.db.Entity):
            ts = Required(datetime)
            content = Required(str)

        class RevelPollerUser(self.db.Entity):
            ts = Required(datetime)
            name = Required(str)

        class RevelPollerChallenge(self.db.Entity):
            ts = Required(datetime)
            name = Required(str)

        class RevelPollerForum(self.db.Entity):
            ts = Required(datetime)
            forum = Required(int)
            title = Required(str)
            url = Required(str)
            who = Required(str)

    def execute(self, connection, event, extra):
        url = "https://www.revolutionelite.co.uk/index.php"

        try:
            reply = urllib.request.urlopen(url, timeout=5)
        except (urllib.error.URLError, ssl.SSLError):
            # ignore stupid SSL errors for RevEl
            return

        tree = lxml.html.parse(reply)

        news = []
        for ni in tree.xpath("//div[@class='sidebar']/h4[text()='Latest News']/following-sibling::ul[1]/li"):
            match = re.search(r'''(\d+)(?:st|nd|rd|th)\s+(\w+)\s+(\d+)\s*-\s*(.*)''', ni.text_content())
            ts = datetime.strptime(" ".join(match.groups()[:3]), "%d %B %Y")
            content = match.group(4)
            news.append((ts, content))

        latest_user = tree.xpath("//div[@class='sidebar']/h4[text()='Latest Stats:']/following-sibling::ul[1]/li//h5[text()='Latest Registered User:']/following-sibling::a/text()")[0].strip()
        latest_challenge = tree.xpath("//div[@class='sidebar']/h4[text()='Latest Stats:']/following-sibling::ul[1]/li//h5[text()='Latest Challenge Online:']/following-sibling::a/text()")[0].strip()

        forum_posts = []
        for post in tree.xpath("//div[@class='sidebar']/h4[text()='Latest Message Board Posts:']/following-sibling::center/ul/li"):
            ts = datetime.strptime(post.xpath(".//text()[2]")[0], "%B %d, %Y, %H:%M:%S %p")
            title = post.xpath(".//a[1]/text()")[0].strip()
            url = post.xpath(".//a[1]/@href")[0].strip()
            who = post.xpath(".//a[2]/text()")[0].strip()
            forum_posts.append((0, ts, title, url, who))

        solution_forum_posts = []
        for post in tree.xpath("//div[@class='sidebar']//h4[text()='Latest Solutions Posts:']/following-sibling::center/ul/li"):
            ts = datetime.strptime(post.xpath(".//text()[2]")[0], "%B %d, %Y, %H:%M:%S %p")
            title = post.xpath(".//a[1]/text()")[0].strip()
            url = post.xpath(".//a[1]/@href")[0].strip()
            who = post.xpath(".//a[2]/text()")[0].strip()
            solution_forum_posts.append((1, ts, title, url, who))

        msgs = []
        with db_session:
            for ts, content in news[::-1]:
                if not select(n for n in self.db.RevelPollerNews if n.ts == ts and n.content == content):
                    self.db.RevelPollerNews(ts=ts, content=content)
                    msgs.append(Plugin.green("[Revolution Elite News]") + " " + content)

            if not select(u for u in self.db.RevelPollerUser if u.name == latest_user):
                self.db.RevelPollerUser(ts=datetime.now(), name=latest_user)
                msgs.append(Plugin.green("[Revolution Elite Users]") + " " + ("%s just joined" % Plugin.bold(latest_user)))

            for forum, ts, title, url, who in forum_posts[::-1] + solution_forum_posts[::-1]:
                if not select(f for f in self.db.RevelPollerForum if f.forum == forum and f.ts == ts and f.title == title):
                    self.db.RevelPollerForum(forum=forum, ts=ts, title=title, url=url, who=who)
                    forumstr = "solution " if forum == 1 else ""
                    msgs.append(Plugin.green("[Revolution Elite Forum]") + " " + ("New %spost in %s by %s - %s" % (forumstr, Plugin.bold(title), Plugin.bold(who), url)))

        msg = "\n".join(msgs)
        if msg:
            return [("announce", (self.where(), msg))]
