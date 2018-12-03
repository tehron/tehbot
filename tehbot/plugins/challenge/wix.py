from tehbot.plugins.challenge import *
import urllib
import urllib2
import urlparse
import lxml.html
import re

class Site(BaseSite):
    def prefix(self):
        return u"[wixxerd.com]"

    def siteurl(self):
        return "https://www.wixxerd.com"

    @staticmethod
    def user2id(user):
        url = "https://www.wixxerd.com/challenges/compare.cfm"
        tree = lxml.html.parse(urllib2.urlopen(url, timeout=3))

        for e in tree.xpath("//select[@id='hack1']/option"):
            name = e.text_content()
            if name == user:
                return int(e.get("value"))

        return None

    @staticmethod
    def profile(user):
        uid = Site.user2id(user)

        if uid is None:
            return None

        url = "https://www.wixxerd.com/challenges/hackers.cfm?hi=%d" % uid
        tree = lxml.html.parse(urllib2.urlopen(url, timeout=5))

        for e in tree.xpath("//table[@class='challengeTable']//td//a"):
            challname = e.text_content()
            print challname

    def userstats(self, user):
        url = "https://www.wixxerd.com/challenges/userScore.cfm?username=%s&authkey=%s"

        page = urllib2.urlopen(url % (urllib.quote_plus(user), self.settings["wixxerd_api_key"])).read()

        match = page.split(":")
        if len(match) != 6:
            return None

        score, score_total, users_total, challs_solved, challs_total, rank = map(int, match)
        return user, challs_solved, challs_total, str(rank), users_total, score, score_total, None

    @staticmethod
    def challenges():
        url = "https://www.wixxerd.com/challenges/"
        tree = lxml.html.parse(urllib2.urlopen(url, timeout=5))
        challs = []

        for e in tree.xpath("//table[@class='challengeTable']//td[1]//a"):
            challname = e.text_content()
            challurl = e.get("href")
            if challurl == "https://www.wixxerd.com/challenges/stego-what/":
                challurl = "https://www.wixxerd.com/challenges/showChallenge.cfm?cid=1"
            challid = int(re.search(r'cid=(\d+)', challurl).group(1))
            challs.append((challid, challname))

        return challs

    @staticmethod
    def contains(challs, challname, challnr):
        for cid, name in challs:
            if cid == challnr or (challname and name.lower().startswith(challname.lower())):
                return cid, name
        for cid, name in challs:
            if challname and name.lower().find(challname.lower()) > -1:
                return cid, name
        return None

    @staticmethod
    def get_solvers(cid):
        url = "https://www.wixxerd.com/challenges/hackers.cfm?ci=%d" % cid
        tree = lxml.html.parse(urllib2.urlopen(url, timeout=5))
        lst = []

        for e in tree.xpath("//table[@class='challengeTable']//td[1]//a"):
            hacker = e.text_content()
            lst.append(hacker)

        return lst

    def solvers(self, challname, challnr, user):
        challs = Site.challenges()

        res = Site.contains(challs, challname, challnr)

        if res is None:
            raise NoSuchChallengeError

        cid, name = res
        solvers = Site.get_solvers(cid)
        return cid, name, len(solvers), solvers, user in solvers
