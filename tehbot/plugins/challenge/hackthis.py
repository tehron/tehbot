from tehbot.plugins.challenge import *
import urllib
import urllib2
import urlparse
import lxml.html
import re
import cookielib
import json

class Site(BaseSite):
    def __init__(self):
        self.url = self.siteurl() + "/"
        self.url2 = self.url + "user/%s"
        self.url3 = self.url + "files/ajax/user.php?action=graph&type=levels&uid=%d"
        self.cookies = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookies))

    def prefix(self):
        return u"[HackThis!!]"

    def siteurl(self):
        return "https://www.hackthis.co.uk"

    def login(self):
        data = urllib.urlencode({"username" : self.settings["hackthis.user"], "password" : self.settings["hackthis.password"]})
        page = self.opener.open(self.url + "?login", data).read()
        self.logout_url = self.url + re.search(r'''<a href='/(\?logout[^']*)'>''', page).group(1)

    def logout(self):
        self.opener.open(self.logout_url).read()

    @staticmethod
    def count_lvldata(data):
        a, b = 0, 0
        try:
            for typ in data["data"].keys():
                for lvl in data["data"][typ]["levels"]:
                    b += 1
                    if lvl["progress"] == "2":
                        a += 1
        except:
            pass

        return a, b

    @staticmethod
    def extract_data(tree):
        try:
            uid = int(tree.xpath("//article[@class='profile']/@data-uid")[0])
            real_user = tree.xpath("//article[@class='profile']//h1[@class='lower']")[0].text_content()
            users_total = None
            rank = None
            score = int(tree.xpath("//a[@class='show-levels']//span")[0].text_content().replace(",", ""))
            return (uid, real_user, users_total, rank, score)
        except:
            return None

    def helper(self, u):
        tree = lxml.html.parse(self.opener.open(self.url2 % u))
        data = Site.extract_data(tree)

        if data is None:
            self.login()
            tree = lxml.html.parse(self.opener.open(self.url2 % u))
            data = Site.extract_data(tree)

        return (tree, data)

    def userstats(self, user):
        tree, data = self.helper(urllib.quote(plugins.to_utf8(user).replace("/", "")))

        if data is None:
            return None

        uid, real_user, users_total, rank, score = data

        lvldata = json.load(self.opener.open(self.url3 % uid))
        challs_solved, challs_total = Site.count_lvldata(lvldata)

        return real_user, str(challs_solved), challs_total, rank, users_total, score, None, None

    def solvers(self, challname, challnr, user):
        if challname is None:
            raise ChallengesNotNumberedError

        data = {"action" : "stats.level", "level" : challname}
        if user is not None:
            data["user"] = user
        data = urllib.urlencode(data)

        try:
            page = urllib2.urlopen("https://www.hackthis.co.uk/?api&key=%s" % self.settings["hackthis_api_key"], data).read()
        except urllib2.HTTPError as e:
            if e.code == 400:
                raise NoSuchChallengeError
            raise e

        jdata = json.loads(page)

        if jdata.has_key("status") and jdata["status"] == "error":
            raise Exception(jdata["message"])

        nr, name, cnt, solvers, solved = None, jdata["name"], None, [], False

        if user is not None:
            solved = jdata["solved"]
        else:
            cnt = int(jdata["completed"])
            solvers = [s["user"] for s in jdata["solvers"][:5]]

        return user, nr, name, cnt, solvers, solved
