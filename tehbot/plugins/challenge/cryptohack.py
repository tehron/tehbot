from tehbot.plugins.challenge import *
import requests
import lxml.html
import re
import tehbot

class Site(BaseSite):
    def __init__(self):
        self.sess = requests.Session()
        self.logged_in = False

    def prefix(self):
        return u"[CryptoHack]"

    def siteurl(self):
        return "https://cryptohack.org"

    def loginurl(self):
        return "https://cryptohack.org/login/"

    def logouturl(self):
        return "https://cryptohack.org/logout/"

    def challurl(self):
        return "https://cryptohack.org/challenges/"

    def profileurl(self):
        return "https://cryptohack.org/user/%s/"

    def userstats(self, user):
        return self.userstats_api(user)

    def userstats_api(self, user):
        url = "https://cryptohack.org/wechall/userscore/?username=%s&authkey=%s"
        authkey = self.settings["cryptohack_api_key"]
        r = self.sess.get(url % (Plugin.to_utf8(user), authkey), timeout=5)
        html = r.text
        if html == "failed":
            return None
        user, rank, score, scoremax, challs_solved, challs_total, users_total = html.split(":")
        return user, str(int(challs_solved)), int(challs_total), str(int(rank)), int(users_total), int(score), int(scoremax), None

    def search_challs(self, challname):
        r = self.sess.get(self.challurl(), timeout=3)
        tree = lxml.html.fromstring(r.text)
        categories = tree.xpath("//ul[@class='listCards']/a/@href")
        urls = [requests.compat.urljoin(self.challurl(), u) for u in categories]

        for u in urls:
            r = self.sess.get(u, timeout=3)
            tree = lxml.html.fromstring(r.text)

            for row in tree.xpath("//li[@class='challenge']/div[@class='collapsible-header']"):
                ename = row.xpath("div[contains(concat(' ', normalize-space(@class), ' '), ' challenge-text ')]")
                eurl = row.xpath("span/span/a")

                if not ename or not eurl:
                    continue

                name = ename[0].text_content().strip()
                cnt = int(eurl[0].text_content().split()[0])
                surl = requests.compat.urljoin(u, eurl[0].xpath("@href")[0])

                if name.lower().startswith(challname.lower()):
                    return name, cnt, surl

        return None

    def solved(self, challname, user):
        url = self.profileurl() % Plugin.to_utf8(user)
        r = self.sess.get(url, timeout=3)
        tree = lxml.html.fromstring(r.text)

        euser = tree.xpath("//h1[contains(concat(' ', normalize-space(@class), ' '), ' username-title ')]")
        rows = tree.xpath("//div[@class='recentUserSolves'][2]/table/tbody/tr")

        if not euser or not rows:
            raise NoSuchUserError

        user = euser[0].text_content().strip()
        name = None
        solved = False

        for row in rows:
            ename = row.xpath("td[3]")

            if not ename:
                continue

            name = ename[0].text_content().strip()
            if name == challname:
                solved = True
                break

        return user, solved

    def chall_solvers(self, solversurl):
        r = self.sess.get(solversurl, timeout=3)
        tree = lxml.html.fromstring(r.text)

        solvers = []
        for row in tree.xpath("//td[@class='tableUserSolve']"):
            solvers.append(row.text_content().strip())
            if len(solvers) == 5:
                break

        return solvers

    def solvers(self, challname, challnr, user):
        if challnr:
            raise ChallengesNotNumberedError

        if not self.logged_in:
            self._login(self.settings["cryptohack.user"], self.settings["cryptohack.password"])

        if not self.logged_in:
            raise InvalidLoginError

        chall = self.search_challs(challname)

        if not chall:
            raise NoSuchChallengeError

        name, cnt, url = chall

        if user:
            user, solved = self.solved(name, user)
            cnt, solvers = None, None
        else:
            solved = None
            solvers = self.chall_solvers(url)

        return user, None, name, cnt, solvers, solved

    def _login(self, username, password):
        for c in self.sess.cookies:
            if c.name == "session" and not c.is_expired():
                self.logged_in = True
                return

        r = self.sess.get(self.loginurl(), timeout=5)
        tree = lxml.html.fromstring(r.text)
        e = tree.xpath("//input[@name='_csrf_token']/@value")
        if not e:
            return
        csrf_token = e[0]

        data = {"username" : username, "password" : password, "_csrf_token" : csrf_token}
        self.sess.post(self.loginurl(), data=data, timeout=3)
        self.logged_in = True

    def _logout(self):
        self.sess.get(self.logouturl())
        self.logged_in = False
