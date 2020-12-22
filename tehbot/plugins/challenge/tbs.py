from tehbot.plugins.challenge import *
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import urllib.parse
import lxml.html
import re
import os
import tehbot
import http.cookiejar

class TbsOpener:
    def __init__(self):
        d = os.path.dirname(tehbot.__file__)
        self.cookiejar = http.cookiejar.MozillaCookieJar(os.path.join(d, "..", "data", "tbs.cookies"))
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookiejar))
        self.url = "http://www.bright-shadows.net/"
        self.loginurl = self.url + "login.php"
        self.logout_url = self.url + "logout.php"
        self.logged_in = False

    def login(self, username, password):
        try:
            self.cookiejar.load()
            for c in self.cookiejar:
                if c.name == "PHPSESSID" and not c.is_expired():
                    self.logged_in = True
                    return
        except:
            pass

        data = urllib.parse.urlencode({"retry" : "no", "submitted" : "1", "edit_username" : username, "edit_password" : password, "edit_email" : ""})
        page = self.opener.open(self.loginurl, data).read()
        self.cookiejar.save()
        self.logged_in = True

    def logout(self):
        self.opener.open(self.logout_url).read()
        self.logged_in = False

    def open(self, url, data=None, timeout=None):
        return self.opener.open(url, data, timeout)

class Site(BaseSite):
    def __init__(self):
        self.opener = TbsOpener()

    def prefix(self):
        return "[TheBlackSheep]"

    def siteurl(self):
        return "http://www.bright-shadows.net"

    def challurl(self):
        return "http://www.bright-shadows.net/hackchallenge.php"

    def profileurl(self):
        return "http://www.bright-shadows.net/userstats.php?username=%s"

    def userstats(self, user):
        return self.userstats_api(user)

    def userstats_api(self, user):
        url = "http://www.bright-shadows.net/userdata.php?username=%s"
        html = urllib.request.urlopen(url % Plugin.to_utf8(user), timeout=5).read()
        if html == "Unknown User":
            return None
        real_user, rank, users_total, challs_cnt, challs_total = html.split(":")
        return real_user, str(int(challs_cnt)), int(challs_total), str(int(rank)), int(users_total), None, None, None

    def userstats_html(self, user):
        url = "http://www.bright-shadows.net/ranking.php?perpage=1&showuser=%s"
        tree = lxml.html.parse(urllib.request.urlopen(url % (Plugin.to_utf8(user))))
        rank = int(float(tree.xpath("//td[@class='rank_rank']")[0].text_content()))
        real_user = tree.xpath("//td[@class='rank_user']")[0].text_content()
        challs = int(tree.xpath("//td[@class='rank_cnt']")[0].text_content())

        if user.lower() != real_user.lower():
            return None

        users_total = re.search(r'''(\d+) users ranked''', tree.xpath("//div[@class='module']/h1")[0].text_content()).group(1)
        return real_user, challs, 342, str(rank), int(users_total), None, None, None

    def solvers(self, challname, challnr, user):
        if challnr:
            raise ChallengesNotNumberedError

        if not self.opener.logged_in:
            self.opener.login(self.settings["tbs.user"], self.settings["tbs.password"])

        xpath = "//table[@class='cl_challs']/tr"
        xpath_name = "td[@class='name']"
        xpath_cnt = "td[@class='doneby']"
        xpath_solved = "td[@class='done' or @class='notdone']"

        if user:
            url = self.profileurl() % Plugin.to_utf8(user)
            xpath_user = "//div[@class='module']/h1"
        else:
            url = self.challurl()

        tree = lxml.html.parse(self.opener.open(url, timeout=5))
        rows = tree.xpath(xpath)

        if not rows:
            if user:
                raise NoSuchUserError
            raise UnknownReplyFormat

        res = None

        for row in rows:
            ename = row.xpath(xpath_name)
            ecnt = row.xpath(xpath_cnt)
            esolved = row.xpath(xpath_solved)

            if not ename or not ecnt or not esolved:
                continue

            name = ename[0].text_content().split(":", 1)[1].strip()
            u = urllib.parse.urljoin(url, ename[0].xpath(".//a/@href")[0])
            cnt = int(ecnt[0].text_content().strip())
            solved = esolved[0].xpath("@class")[0] == "done"

            if challname and name.lower().startswith(challname.lower()):
                res = (None, name, u, cnt, solved)

            if user:
                euser = row.xpath(xpath_user)
                if euser:
                    user = euser[0].text_content().split(":", 1)[1].strip()

        if not res:
            raise NoSuchChallengeError

        nr, name, u, cnt, solved = res
        solvers = None

        return user, nr, name, cnt, solvers, solved
