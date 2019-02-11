from tehbot.plugins.challenge import *
import urllib
import urllib2
import urlparse
import lxml.html
import re

challurl = "https://www.rankk.org/stats.py"
userurl = "https://www.rankk.org/user/%s"

class Site(BaseSite):
    def prefix(self):
        return u"[Rankk]"

    def siteurl(self):
        return "https://www.rankk.org"

    def userstats(self, user):
        page = urllib2.urlopen(url2 % urllib.urlencode({"username" : plugins.to_utf8(user)})).read()

        match = re.search(r'(\w+) solved (\d+) of (\d+) Challenges with (\d+) of (\d+) possible points \(\d\d\.\d\d%\). Rank for the site WeChall: (\d+)', page)
        if not match:
            return None

        # ugly wechall parsing, thx a lot gizmore! ;PP
        tree = lxml.html.parse(urllib2.urlopen(profileurl % urllib.quote_plus(plugins.to_utf8(user))))
        users_total = int(tree.xpath("//div[@id='wc_sidebar']//div[@class='wc_side_content']//div/a[@href='/users']")[0].text_content().split()[0])

        real_user, challs_solved, challs_total, score, scoremax, rank = match.groups()
        return real_user, int(challs_solved), int(challs_total), str(int(rank)), int(users_total), int(score), int(scoremax), None

    def rankstats(self, rank):
        page = 1 + (rank - 1) / 50

        if page < 1:
            return None

        tree = lxml.html.parse(urllib2.urlopen(rankurl % page))

        for row in tree.xpath("//div[@id='page']/div[@class='gwf_table']/table//tr"):
            r = row.xpath("td[1]")
            n = row.xpath("td[3]")

            if not r or not n:
                continue

            if int(r[0].text_content()) == rank:
                res = self.userstats(n[0].text_content())
                real_user, challs_solved, challs_total, rank, users_total, score, score_max, _ = res
                return challs_solved, [real_user], challs_total

        return None

    def str2nr(self, s):
        try:
            match = re.search(r'(\d+)/(\d+)', s)
        except:
            raise ValueError('Expected format: %s' % r'\d+/d+')

        return (int(match.group(1)), int(match.group(2)))

    def nr2str(self, nr):
        return "%d/%d" % nr

    @staticmethod
    def parse(script):
        match = re.search(r"var\s+views\s*=\s*{\s*'solved'\s*:\s*'((?:[^'\\]|(?:\\'))*)'", script)
        return match.group(1).replace("\\'", "'") if match else ""

    def solvers(self, challname, challnr, user):
        tree = lxml.html.parse(urllib2.urlopen(challurl, timeout=5))
        escript = tree.xpath("//div[@id='page']/script")

        if not escript:
            raise UnknownReplyFormat

        content = Site.parse(escript[0].text_content())
        tree = lxml.html.fromstring(content)
        rows = tree.xpath("//table/tr")

        if not rows:
            raise UnknownReplyFormat

        res = None

        for row in rows:
            enr = row.xpath("td[@class='td'][1]")
            ename = row.xpath("td[@class='td'][2]")
            ecnt = row.xpath("td[@class='td'][3]")

            if not ename or not enr or not ecnt:
                continue

            nr = self.str2nr(enr[0].text_content().strip())
            name = ename[0].text_content().strip()
            cnt = int(ecnt[0].text_content().strip())

            if (challnr and nr == challnr) or (challname and name.lower().startswith(challname.lower())):
                res = (nr, name, cnt)
                break

            if not res and challname and challname.lower() in name.lower():
                res = (nr, name, cnt)

        if not res:
            raise NoSuchChallengeError

        nr, name, cnt = res
        solvers = None
        solved = Site.user_solved(user, name) if user else False
        return user, nr, name, cnt, solvers, solved

    @staticmethod
    def user_solved(user, challname):
        url = userurl % urllib.quote_plus(plugins.to_utf8(user))
        tree = lxml.html.parse(urllib2.urlopen(url, timeout=5))
        rows = tree.xpath("//div[@id='allsolved']/ul[@class='solved']/li")

        if not rows:
            raise UnknownReplyFormat

        for row in rows:
            e = row.xpath("span")

            if not e:
                continue

            match = re.search(r'(\d+)/(\d+)\s*-\s*(.*)', e[0].text_content().strip())

            if not match:
                continue

            a, b, name = match.groups()
            nr = (int(a), int(b))

            if challname == name:
                return True

        return False

    @staticmethod
    def get_last5_solvers(nr):
        url = solversurl % (nr, "dummy", 1)
        tree = lxml.html.parse(urllib2.urlopen(url))
        pages = tree.xpath("//div[@id='page']/div[@class='gwf_pagemenu']//a")
        solvers = []

        if not pages:
            for row in tree.xpath("//div[@id='page']/table//tr"):
                e = row.xpath("td[2]/a[1]")
                if e:
                    n = e[0].text_content()
                    solvers.append(n)
        else:
            lastpage = int(pages[-1].text_content())
            for p in [lastpage - 1, lastpage]:
                url = solversurl % (nr, "dummy", p)
                tree = lxml.html.parse(urllib2.urlopen(url))

                for row in tree.xpath("//div[@id='page']/table//tr"):
                    e = row.xpath("td[2]/a[1]")
                    if e:
                        n = e[0].text_content()
                        solvers.append(n)

        return solvers[::-1][:5]
