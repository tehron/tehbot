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

    def userstats(self, user):
        url = "https://www.revolutionelite.co.uk/w3ch4ll/userscore.php?username=%s"
        page = urllib2.urlopen(url % (plugins.to_utf8(user)), timeout=5).read()

        if page == "0":
            return None

        match = page.split(":")
        if len(match) != 7:
            raise Exception("Unexpected format in reply. Try ?blame.")

        _, rank, pts, ptsmax, solved, solvedmax, usercount = match

        # fix rank reported incorrectly by sabretooth's script
        try:
            rank = str(int(rank) + 1)
        except:
            pass

        return user, int(solved), int(solvedmax), rank, int(usercount), None, None, None

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

        return ranks[rank]

    @staticmethod
    def fixurl(url):
        # damn sabre still hasn't fixed url encoding in query string?
        scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
        query = urllib.urlencode(urlparse.parse_qsl(query))
        return urlparse.urlunsplit((scheme, netloc, path, query, fragment))

    @staticmethod
    def parse_challs(url):
        challs = {}
        tree = lxml.html.parse(urllib2.urlopen(url, timeout=5))
        for e in tree.xpath("//div[@class='content']/center/table/tr"):
            e2 = e.xpath("td[2]")
            if not e2:
                continue
            try:
                nr = int(e2[0].text_content().strip())
            except ValueError:
                continue
            e2 = e.xpath("td[3]")
            if not e2:
                continue
            name = e2[0].text_content().strip()
            e2 = e.xpath("td[3]/center/a/@href")
            if not e2:
                continue

            u = urlparse.urljoin(url, e2[0])
            u = Site.fixurl(u)
            challs[nr] = (name, u)

        return challs

    @staticmethod
    def get_solvers(page):
        tree = lxml.html.fromstring(page)
        solvers = []
        for p in tree.xpath("//div[@class='content']/center/table/tr/td/a"):
            solvers.append(p.text_content().strip())
        return solvers

    def solvers(self, challname, challnr, user):
        url = "https://www.revolutionelite.co.uk/credits.php"
        challs = Site.parse_challs(url)
        nr, name, url = None, None, None

        if challname is not None:
            for key, val in challs.items():
                if val[0].lower().startswith(challname.lower()):
                    nr = key
                    name, url = val
                    break
                if challname.lower() in val[0].lower():
                    nr = key
                    name, url = val
        else:
            if challs.has_key(challnr):
                nr = challnr
                name, url = challs[challnr]

        if not name:
            raise NoSuchChallengeError

        cnt = 0
        page = urllib2.urlopen(url, timeout=5).read()
        solvers = Site.get_solvers(page)
        match = re.search(r'\((\d+) solvers\) \(latest first\)', page)

        if match:
            cnt = int(match.group(1))

        return nr, name, cnt, solvers, user in solvers
