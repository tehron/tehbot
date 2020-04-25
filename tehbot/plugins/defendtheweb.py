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
import tehbot
import traceback

class DefendTheWebOpener:
    def __init__(self):
        d = os.path.dirname(tehbot.__file__)
        self.cookiejar = cookielib.MozillaCookieJar(os.path.join(d, "..", "data", "defendtheweb.cookies"))
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar))
        self.url = "https://defendtheweb.net/"
        self.loginurl = self.url + "auth"
        self.logout_url = self.url + "auth/logout"
        self.logged_in = False

    def login(self, username, password):
        try:
            self.cookiejar.load()
            for c in self.cookiejar:
                if c.name == "auth_remember" and not c.is_expired():
                    self.logged_in = True
                    return
        except:
            pass

        tree = lxml.html.parse(self.opener.open(self.loginurl))
        token = tree.xpath("//div[contains(@class, 'auth-local-login')]/form/input[@name='token']/@value")[0]
        data = urllib.urlencode({"username" : username, "password" : password, "token" : token, "remember" : "on"})
        page = self.opener.open(self.loginurl, data).read()
        self.cookiejar.save()
        self.logged_in = True

    def logout(self):
        self.opener.open(self.logout_url).read()
        self.logged_in = False

    def open(self, url, data=None, timeout=None):
        return self.opener.open(url, data, timeout)

class ConductPlugin(StandardCommand):
    def __init__(self):
        StandardCommand.__init__(self)
        self.conducts = [
                "Answers to all levels will be my own work, unless otherwise instructed.",
                "I will not share answers to any level.",
                "I will not participate in, condone or encourage unlawful activity, including any breach of copyright, defamation, or contempt of court.",
                "I will not 'spam' other Defend the Web members by posting the same message multiple times or posting a message that is unrelated to the discussion.",
                "As the Defend the Web community's first language is English, I will always post contributions in English to enable all to understand",
                "I will not use Defend the Web to advertise products or services for profit or gain.",
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

class DefendTheWebForumPoller(Poller):
    def prefix(self):
        return u"[Defend the Web Forum]"

    def initialize(self, dbconn):
        Poller.initialize(self, dbconn)
        with dbconn:
            dbconn.execute("CREATE TABLE if not exists HackThisForumPoller(id integer primary key, url varchar unique, title text, replies integer, last_ts datetime, last_user text)")

        self.opener = DefendTheWebOpener()
        self.url = "https://defendtheweb.net/"
        self.forumurl = self.url + "discussions/all/latest"

    def execute(self, connection, event, extra, dbconn):
        if not self.opener.logged_in:
            self.opener.login(self.settings["hackthis.user"], self.settings["hackthis.password"])

        try:
            fp = self.opener.open(self.forumurl)
            tree = lxml.html.parse(fp)
        except (urllib2.URLError, ssl.SSLError):
            # ignore stupid SSL errors for DefendTheWeb
            return

        entries = []

        for thread in tree.xpath("//div[contains(@class, 'discussion-list-threads')]/div[contains(@class, 'discussion-list-thread') and contains(@class, 'feed-item')]"):
            replies = int(thread.xpath(".//div[@data-text='post_count']/text()")[0])
            anchor = thread.xpath(".//div[@class='feed-item-details']/a[contains(@class, 'feed-item-title')]")[0]
            url = anchor.xpath("@href")[0]
            title = anchor.text.strip()
            id = int(re.search(r'/[^/]*?(\d+)[^/]*', url).group(1))
            try:
                latest = thread.xpath(".//div[@class='feed-item-details']//a[@data-text='update_by']")[0]
            except IndexError:
                latest = thread.xpath(".//div[@class='feed-item-details']//a[@data-text='author']")[0]
            last_user = latest.xpath("@data-profile-card")[0]
            timestr = latest.xpath("following-sibling::span/@title")[0]
            last_ts = time.mktime(time.strptime(timestr, "%d/%m/%Y %H:%M (UTC)"))
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
                    dbconn.execute("update HackThisForumPoller set url=?, last_ts=?, last_user=? where id=?", (url, last_ts, last_user, id))
                    announce = True
                    newthread = False

                if announce:
                    if newthread:
                        msgs.append(Plugin.green(self.prefix()) + " New Thread %s by %s (id: %d)" % (Plugin.bold(title), Plugin.bold(last_user), id))
                    else:
                        msgs.append(Plugin.green(self.prefix()) + " New Reply in %s by %s (id: %d)" % (Plugin.bold(title), Plugin.bold(last_user), id))

        msg = u"\n".join(msgs)
        if msg:
            return [("announce", (self.where(), msg))]

class DefendTheWebForumPlugin(StandardCommand):
    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("what", nargs="?")
        self.opener = DefendTheWebOpener()
        self.splitter = re.compile("[\t\r\n ]*")

    def commands(self):
        return "dtwforum"

    def prefix(self):
        return u"[Defend the Web Forum]"

    def execute(self, connection, event, extra, dbconn):
        self.parser.set_defaults(what="latest")

        try:
            pargs = self.parser.parse_args(extra["args"])
            m = self.parser.get_help_msg()
            if m:
                return m.strip()
            what = pargs.what
        except Exception as e:
            return u"Error: %s" % unicode(e)

        if what != "latest":
            try:
                what = int(what)
            except:
                return Plugin.red(self.prefix()) + " Illegal id: %s" % what

        with dbconn:
            if what == "latest":
                c = dbconn.execute("select url from HackThisForumPoller order by last_ts desc limit 1")
            else:
                c = dbconn.execute("select url from HackThisForumPoller where id=?", (what,))
            res = c.fetchone()
            if res is None:
                return Plugin.red(self.prefix()) + " No such id: %s" % what
            url = res[0]

        if not self.opener.logged_in:
            self.opener.login(self.settings["hackthis.user"], self.settings["hackthis.password"])

        try:
            if not url.startswith("http"):
                url = "https://defendtheweb.net" + url
            fp = self.opener.open(url)
            tree = lxml.html.parse(fp)
        except (urllib2.URLError, ssl.SSLError) as e:
            return Plugin.red(self.prefix()) + u" %s" % unicode(e)

        try:
            last_post = tree.xpath("(//div[contains(concat(' ', normalize-space(@class), ' '), ' discussion-thread-message ')])[last()]")[0]
            user = last_post.xpath(".//a[@class='discussion-thread-message-author']/@data-profile-card")[0].strip()
            content = last_post.xpath(".//div[@class='discussion-thread-message-main']/div[@class='discussion-thread-message-content']")[0]
            body = content.xpath(".//text()[not(ancestor::p[ancestor::blockquote[ancestor::blockquote]])]")

            body = " ".join(filter(None, self.splitter.split(" ".join(body))))
            msg = Plugin.green(self.prefix()) + " %s: %s" % (user, body)
        except:
            try:
                errmsg = tree.xpath("//div[contains(@class, 'msg--error')]")[0].text_content().strip()
                msg = Plugin.red(self.prefix()) + " %s" % errmsg
            except:
                traceback.print_exc()
                msg = Plugin.red(self.prefix()) + " unparsable HTML"
        return Plugin.shorten(msg, 450)
