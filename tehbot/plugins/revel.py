from tehbot.plugins import *
import urllib
import urllib2
import time
import ssl
import lxml.html
import re

class RevelSolvedPoller(Poller):
    def prefix(self):
        return u"[Revolution Elite]"

    def datestamp(self, ts):
        return time.strftime('%Y%m%d%H%M%S', time.localtime(ts))

    def timestamp(self, datestamp):
        try:
            t = time.strptime(datestamp, '%Y%m%d%H%M%S')
            ts = time.mktime(t)
        except:
            ts = 0
        return ts

    def execute(self, connection, event, extra, dbconn):
        url = "https://www.revolutionelite.co.uk/w3ch4ll/solvers_revel.php?datestamp=%s"

        try:
            ts = self.settings["ts"]
        except:
            ts = 0

        try:
            reply = urllib2.urlopen(url % self.datestamp(ts), timeout=3)
        except (urllib2.URLError, ssl.SSLError):
            # ignore stupid SSL errors for RevEl
            return

        entries = []

        for entry in reply.readlines():
            try:
                uid, cid, solvedate, firstdate, views, options, timetaken, tries, username, challname, solvercount, challurl = map(lambda x: x.replace(r"\:", ":"), entry.split("::"))
                uid = int(uid)
                cid = int(cid)
                tssolve = self.timestamp(solvedate)
                ts1stsolve = self.timestamp(firstdate)
                views = int(views)
                tries = int(tries)
                solvercount = int(solvercount) - 1
                entries.append((tssolve, username, challname, solvercount))
            except:
                pass

        msgs = []
        for tssolve, username, challname, solvercount in sorted(entries):
            ts = tssolve

            msg = "%s has just solved %s." % (Plugin.bold(username), Plugin.bold(challname))
            if solvercount <= 0:
                msg += " This challenge has never been solved before!"
            else:
                msg += " This challenge has been solved %d time%s before." % (solvercount, "" if solvercount == 1 else "s")

            msgs.append(u"%s %s" % (Plugin.green(self.prefix()), msg))

        self.settings["ts"] = ts
        self.save(dbconn)

        msg = u"\n".join(msgs)
        if msg:
            return [("announce", (self.where(), msg))]



class RevelPoller(Poller):
    def initialize(self, dbconn):
        Poller.initialize(self, dbconn)
        with dbconn:
            dbconn.execute("create table if not exists RevelPollerNews(id integer, ts datetime, content text)")
            dbconn.execute("create table if not exists RevelPollerUser(id integer, name text, ts datetime)")
            dbconn.execute("create table if not exists RevelPollerChallenge(id integer, name text, ts datetime)")
            dbconn.execute("create table if not exists RevelPollerForum(id integer, forum integer, ts datetime, title text, url text, who text)")

    def execute(self, connection, event, extra, dbconn):
        url = "https://www.revolutionelite.co.uk/index.php"

        try:
            reply = urllib2.urlopen(url, timeout=5)
        except (urllib2.URLError, ssl.SSLError):
            # ignore stupid SSL errors for RevEl
            return

        tree = lxml.html.parse(reply)

        news = []
        for ni in tree.xpath("//div[@class='sidebar']/h4[text()='Latest News']/following-sibling::ul[1]/li"):
            match = re.search(r'''(\d+)(?:st|nd|rd|th)\s+(\w+)\s+(\d+)\s*-\s*(.*)''', ni.text_content())
            ts = time.mktime(time.strptime(" ".join(match.groups()[:3]), "%d %B %Y"))
            content = match.group(4)
            news.append((ts, content))

        latest_user = tree.xpath("//div[@class='sidebar']/h4[text()='Latest Stats:']/following-sibling::ul[1]/li//h5[text()='Latest Registered User:']/following-sibling::a/text()")[0].strip()
        latest_challenge = tree.xpath("//div[@class='sidebar']/h4[text()='Latest Stats:']/following-sibling::ul[1]/li//h5[text()='Latest Challenge Online:']/following-sibling::a/text()")[0].strip()

        forum_posts = []
        for post in tree.xpath("//div[@class='sidebar']/h4[text()='Latest Message Board Posts:']/following-sibling::center/ul/li"):
            ts = time.mktime(time.strptime(post.xpath(".//text()[2]")[0], "%B %d, %Y, %H:%M:%S %p"))
            title = post.xpath(".//a[1]/text()")[0].strip()
            url = post.xpath(".//a[1]/@href")[0].strip()
            who = post.xpath(".//a[2]/text()")[0].strip()
            forum_posts.append((0, ts, title, url, who))

        solution_forum_posts = []
        for post in tree.xpath("//div[@class='sidebar']//h4[text()='Latest Solutions Posts:']/following-sibling::center/ul/li"):
            ts = time.mktime(time.strptime(post.xpath(".//text()[2]")[0], "%B %d, %Y, %H:%M:%S %p"))
            title = post.xpath(".//a[1]/text()")[0].strip()
            url = post.xpath(".//a[1]/@href")[0].strip()
            who = post.xpath(".//a[2]/text()")[0].strip()
            solution_forum_posts.append((1, ts, title, url, who))

        msgs = []
        with dbconn:
            for n in news[::-1]:
                c = dbconn.execute("select 1 from RevelPollerNews where ts=? and content=?", n)
                if not c.fetchone():
                    dbconn.execute("insert into RevelPollerNews values(null, ?, ?)", n)
                    msgs.append(Plugin.green("[Revolution Elite News]") + " " + n[1])

            c = dbconn.execute("select 1 from RevelPollerUser where name=?", (latest_user, ))
            if not c.fetchone():
                dbconn.execute("insert into RevelPollerUser values(null, ?, ?)", (latest_user, time.time()))
                msgs.append(Plugin.green("[Revolution Elite Users]") + " " + ("%s just joined" % Plugin.bold(latest_user)))

            for p in forum_posts[::-1]:
                c = dbconn.execute("select 1 from RevelPollerForum where forum=? and ts=? and title=?", (p[0], p[1], p[2]))
                if not c.fetchone():
                    dbconn.execute("insert into RevelPollerForum values(null, ?, ?, ?, ?, ?)", p)
                    msgs.append(Plugin.green("[Revolution Elite Forum]") + " " + ("New post in %s by %s" % (Plugin.bold(p[2]), Plugin.bold(p[4]))))

            for p in solution_forum_posts[::-1]:
                c = dbconn.execute("select 1 from RevelPollerForum where forum=? and ts=? and title=?", (p[0], p[1], p[2]))
                if not c.fetchone():
                    dbconn.execute("insert into RevelPollerForum values(null, ?, ?, ?, ?, ?)", p)
                    msgs.append(Plugin.green("[Revolution Elite Forum]") + " " + ("New solution post in %s by %s" % (Plugin.bold(p[2]), Plugin.bold(p[4]))))
            
        msg = u"\n".join(msgs)
        if msg:
            return [("announce", (self.where(), msg))]
