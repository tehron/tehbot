from tehbot.plugins import *
import shlex
import urllib2
import urllib
import urlparse
import lxml.html
import cookielib
import json
import re
import datetime
import time
import re
import ssl
import os.path

class HackThisOpener:
    def __init__(self):
        d = os.path.dirname(__file__)
        self.cookiejar = cookielib.MozillaCookieJar(os.path.join(d, "cookies.txt"))
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar))
        self.url = "https://www.hackthis.co.uk/"
        self.loginurl = self.url + "?login"
        self.logged_in = False

    def login(self, username, password):
        try:
            self.cookiejar.load()
            for c in self.cookiejar:
                if c.name == "autologin" and not c.is_expired():
                    self.logged_in = True
                    return
        except:
            pass

        data = urllib.urlencode({"username" : username, "password" : password})
        page = self.opener.open(self.loginurl, data).read()
        self.logout_url = self.url + re.search(r'''<a href='/(\?logout[^']*)'>''', page).group(1)
        self.cookiejar.save()
        self.logged_in = True

    def logout(self):
        self.opener.open(self.logout_url).read()
        self.logged_in = False

    def open(self, url, data=None, timeout=None):
        return self.opener.open(url, data, timeout)

def ends_message():
    end = datetime.datetime(2015, 12, 11, 20)
    secs = (end - datetime.datetime.now()).seconds

    lst = []
    hours = secs / 3600
    if hours > 0:
        lst.append("%d hour%s" % (hours, "" if hours == 1 else "s"))
    secs -= 3600 * hours

    mins = secs / 60
    if mins > 0:
        lst.append("%d minute%s" % (mins, "" if mins == 1 else "s"))
    secs -= 60 * mins

    if secs > 0:
        lst.append("%d second%s" % (secs, "" if secs == 1 else "s"))

    return "CTF ends in %s." % (", ".join(lst))

class CtfPlugin(StandardCommand):
    """Shows rankings of HackThis!! CTF 2015"""

    def __init__(self):
        StandardCommand.__init__(self)
        group = self.parser.add_mutually_exclusive_group()
        group.add_argument("-u", "--user")
        group.add_argument("-r", "--rank", type=int)

    def commands(self):
        return "ctf"

    def execute_parsed(self, connection, event, extra, dbconn):
        if event.target.lower() != "#ctf":
            return

        prefix = "\x0303[HackThis!! CTF]\x03 "

        if self.pargs.user:
            user = Plugin.from_utf8(self.pargs.user)
        else:
            user = None
        rank = self.pargs.rank

        if user is not None:
            try:
                raw_data = urllib2.urlopen("http://ctf.hackthis.co.uk/ajax.php?action=stats", data="q=0").read()
            except:
                return "Network Error"

            try:
                data = json.loads(raw_data)
                if not data["status"]:
                    return "Status not ok"
            except:
                return "Unknown format in server reply"

            leaderboard = re.findall(r'"([^"]*)":(\d+)', raw_data)
            i = 1
            for name, solved in leaderboard:
                if name.lower() == user.lower():
                    return prefix + "%s has solved %s task%s and is at rank %d of %d. %s" % (name, solved, "" if int(solved) == 1 else "s", i, len(leaderboard), ends_message())
                i += 1

            return prefix + "%s not found in leaderboard." % (user)
        elif rank is not None and rank > 0:
            try:
                raw_data = urllib2.urlopen("http://ctf.hackthis.co.uk/ajax.php?action=stats", data="q=%d" % rank).read()
            except:
                return "Network Error"

            try:
                data = json.loads(raw_data)
                if not data["status"]:
                    return "Status not ok"
            except:
                return "Unknown format in server reply"

            leaderboard = re.findall(r'"([^"]*)":(\d+)', raw_data)
            if len(leaderboard) < rank:
                return "No one is at rank %d. %s" % (rank, ends_message())

            name, solved = leaderboard[-1]
            return prefix + "%s is at rank %d with %s solved task%s. %s" % (name, rank, solved, "" if int(solved) == 1 else "s", ends_message())
        else:
            try:
                raw_data = urllib2.urlopen("http://ctf.hackthis.co.uk/ajax.php?action=stats", data="q=10").read()
            except:
                return "Network Error"

            try:
                data = json.loads(raw_data)
                if not data["status"]:
                    return "Status not ok"
            except:
                return "Unknown format in server reply"

            leaderboard = re.findall(r'"([^"]*)":(\d+)', raw_data)
            return prefix + "Top 10: " + ", ".join("%s (%s)" % (a, b) for a, b in leaderboard) + ". " + ends_message()

class ConductPlugin(StandardCommand):
    def __init__(self):
        StandardCommand.__init__(self)
        self.conducts = [
                "Answers to all levels will be my own work, unless otherwise instructed.",
                "I will not share answers to any level.",
                "I will not participate in, condone or encourage unlawful activity, including any breach of copyright, defamation, or contempt of court.",
                "I will not 'spam' other HackThis!! members by posting the same message multiple times or posting a message that is unrelated to the discussion.",
                "As the HackThis!! community's first language is English, I will always post contributions in English to enable all to understand",
                "I will not use HackThis!! to advertise products or services for profit or gain.",
                "I will not use racist, sexist, homophobic, sexually explicit or abusive terms or images, or swear words or language that is likely to cause offence."
        ]
        self.parser.add_argument("nr", type=int, choices=range(1, len(self.conducts) + 1))

    def commands(self):
        return ["conduct", "rule"]

    def default_settings(self):
        return {
                "where" : ["macak:#hackthis" ]
                }

    def target_valid(self, name):
        return name in self.settings["where"]

    def execute_parsed(self, connection, event, extra, dbconn):
        if not self.target_valid(connection.tehbot.ircid+":"+event.target.lower()):
            return

        return self.conducts[self.pargs.nr - 1]

class HackThisStatusPlugin(StandardCommand):
    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("challenge", nargs="+")

    def commands(self):
        return "htstatus"

    def status(self, filename):
        d = os.path.dirname(__file__)
        code = open(os.path.join(d, filename)).read()
        try:
            exec code
        except:
            res = False
        return res

    def execute_parsed(self, connection, event, extra, dbconn):
        chall = " ".join(self.pargs.challenge)
        chall = re.sub(r'''\s|\+|level''', "", chall.lower())
        chall = chall.replace("b7", "basic7").replace("r6", "real6")
        prefix = "[HackThis!! Status]"

        try:
            succ = self.status("status_%s.py" % chall)
            col = Plugin.green if succ else Plugin.red
            return col(prefix) + " Level is " + ("online" if succ else "offline")
        except:
            return Plugin.red(prefix) + " No status for this level implemented"

class HackThisForumPoller(Poller):
    def prefix(self):
        return u"[HackThis!! Forum]"

    def initialize(self, dbconn):
        Poller.initialize(self, dbconn)
        with dbconn:
            dbconn.execute("CREATE TABLE if not exists HackThisForumPoller(id integer primary key, url varchar unique, title text, replies integer, last_ts datetime, last_user text)")

        self.opener = HackThisOpener()
        self.url = "https://www.hackthis.co.uk/"
        self.forumurl = self.url + "forum"

    def execute(self, connection, event, extra, dbconn):
        if not self.opener.logged_in:
            self.opener.login(self.settings["hackthis.user"], self.settings["hackthis.password"])

        try:
            fp = self.opener.open(self.forumurl, timeout=10)
            tree = lxml.html.parse(fp)
        except (urllib2.URLError, ssl.SSLError):
            # ignore stupid SSL errors for HackThis!!
            return

        topics_node = tree.xpath("//div[@class='forum-topics']")[0]
        entries = []

        for thread in topics_node.xpath(".//li[@class='forum-section']//li[contains(@class, 'row')]"):
            anchor = thread.xpath(".//div[contains(@class, 'section_info')]/a")[0]
            url = anchor.xpath("@href")[0]
            title = anchor.text
            id = int(re.search(r'/(\d+)-[^/]+', url).group(1))
            replies = int(thread.xpath(".//div[contains(@class, 'section_replies')]/text()")[0])
            latest = thread.xpath(".//div[contains(@class, 'section_latest')]")[0]
            timestr = latest.xpath("./time/@datetime")[0]
            last_ts = time.mktime(time.strptime(timestr, "%Y-%m-%dT%H:%M:%S+00:00"))
            last_user = latest.xpath("./a/text()")[0].strip()
            entries.append((id, url, title, replies, last_ts, last_user))

        msgs = []

        with dbconn:
            for e in entries:
                id, url, title, replies, last_ts, last_user = e
                c = dbconn.execute("select last_ts from HackThisForumPoller where id = ?", (id, ))
                res = c.fetchone()
                announce, newthread = False, False
                if res is None:
                    dbconn.execute("insert into HackThisForumPoller values(?, ?, ?, ?, ?, ?)", e)
                    announce = True
                    newthread = replies == 0
                elif res[0] < last_ts:
                    dbconn.execute("update HackThisForumPoller set last_ts=?, last_user=? where id=?", (last_ts, last_user, id))
                    announce = True
                    newthread = False

                if announce:
                    if newthread:
                        msgs.append(Plugin.green(self.prefix()) + " New Thread %s by %s" % (Plugin.bold(title), Plugin.bold(last_user)))
                    else:
                        msgs.append(Plugin.green(self.prefix()) + " New Reply in %s by %s" % (Plugin.bold(title), Plugin.bold(last_user)))

        msg = u"\n".join(msgs)
        if msg:
            return [("announce", (self.where(), msg))]
