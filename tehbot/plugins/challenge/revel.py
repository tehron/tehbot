from tehbot.plugins.challenge import *
import urllib2
import urllib
import urlparse
import lxml.html
import re

class Site(BaseSite):
    def prefix(self):
        return u"[Revolution Elite]"

    def siteurl(self):
        return "https://www.revolutionelite.co.uk"

    @staticmethod
    def challurl():
        return "https://www.revolutionelite.co.uk/credits.php"

    @staticmethod
    def profileurl():
        return "https://www.revolutionelite.co.uk/profile.php?user=%s"

    def userstats(self, user):
        url = "https://www.revolutionelite.co.uk/w3ch4ll/userscore.php?username=%s"
        page = urllib2.urlopen(url % (plugins.to_utf8(user)), timeout=5).read()

        if page == "0":
            return None

        match = page.split(":")
        if len(match) != 7:
            raise Exception("Unexpected format in reply. Try ?blame.")

        _, rank, pts, ptsmax, solved, solvedmax, usercount = match

        # sabre can't make up his mind!
        ## fix rank reported incorrectly by sabretooth's script
        #try:
        #    rank = str(int(rank) + 1)
        #except:
        #    pass

        return user, solved, int(solvedmax), rank, int(usercount), None, None, None

    @staticmethod
    def parsescores(page):
        url = "https://www.revolutionelite.co.uk/rank.php?page=%d"
        scores = []

        tree = lxml.html.parse(urllib2.urlopen(url % page, timeout=5))
        for e in tree.xpath("//div[@class='content']/center/table/tr"):
            e2 = e.xpath("td[2]")
            if not e2:
                continue
            name = e2[0].text_content().strip()
            e2 = e.xpath("td[3]")
            if not e2:
                continue
            try:
                score = int(e2[0].text_content().strip())
            except ValueError:
                continue
            scores.append((score, name))
        return scores

    @staticmethod
    def updateranks(scores):
        sc = dict()
        for s, name in scores:
            if not sc.has_key(s):
                sc[s] = []
            sc[s].append(name)

        keys = sorted(sc.keys(), reverse=True)
        ranks = dict([(i + 1, (k, sc[k])) for i, k in enumerate(keys)])
        return ranks

    @staticmethod
    def maxscore():
        url = "https://www.revolutionelite.co.uk/credits.php"
        tree = lxml.html.parse(urllib2.urlopen(url, timeout=5))

        return len(tree.xpath("//div[@class='content']/center/table/tr")) - 1

    def rankstats(self, rank):
        page = 1
        scores = []
        ranks = dict()

        for page in range(1, 12):
            if rank <= 0 or rank in ranks:
                break
            scores += Site.parsescores(page)
            ranks = Site.updateranks(scores)

        if rank not in ranks:
            return None

        return ranks[rank] + (Site.maxscore(),)

    @staticmethod
    def fixurl(url):
        # damn sabre still hasn't fixed url encoding in query string?
        scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
        query = urllib.urlencode(urlparse.parse_qsl(query))
        return urlparse.urlunsplit((scheme, netloc, path, query, fragment))

    @staticmethod
    def get_solvers(page):
        tree = lxml.html.fromstring(page)
        solvers = []
        for p in tree.xpath("//div[@class='content']/center/table/tr/td/a"):
            solvers.append(p.text_content().strip())
        return solvers

    def solvers(self, challname, challnr, user):
        if user:
            url = Site.profileurl() % plugins.to_utf8(user)
            xp = "//div[@class='content']/center[2]/table/tr"
            xpnr = "td[1]"
            xpname = "td[2]"
            xpsolved = "td[3]"
            xpuser = "//div[@class='content']/h3"
        else:
            url = Site.challurl()
            xp = "//div[@class='content']/center/table/tr"
            xpnr = "td[2]"
            xpname = "td[3]"
            xpsolved = "/foobar"
            xpuser = "/foobar"

        tree = lxml.html.parse(urllib2.urlopen(url, timeout=5))
        rows = tree.xpath(xp)

        if not rows:
            if user:
                raise NoSuchUserError
            raise UnknownReplyFormat

        res = None

        for row in rows:
            enr = row.xpath(xpnr)
            ename = row.xpath(xpname)
            esolved = row.xpath(xpsolved)
            euser = row.xpath(xpuser)

            if not enr or not ename:
                continue

            nr = int(enr[0].text_content().strip())
            name = ename[0].text_content().strip()
            u = urlparse.urljoin(url, ename[0].xpath(".//a/@href")[0])
            u = Site.fixurl(u)
            solved = esolved and esolved[0].text_content().strip().lower() == "solved"
            if euser:
                user = re.search(r'Profile for (\w+)', euser[0].text_content()).group(1)

            if (challnr and nr == challnr) or (challname and name.lower().startswith(challname.lower())):
                res = (nr, name, u, solved)
                break

            if not res and challname and challname.lower() in name.lower():
                res = (nr, name, u, solved)

        if not res:
            raise NoSuchChallengeError

        nr, name, u, solved = res
        cnt = 0
        solvers = None
        
        if not user:
            page = urllib2.urlopen(u, timeout=5).read()
            match = re.search(r'\((\d+) solvers\) \(latest first\)', page)
            cnt, solvers = 0, []

            if match:
                cnt = int(match.group(1))
                solvers = Site.get_solvers(page)

        return user, nr, name, cnt, solvers, solved
