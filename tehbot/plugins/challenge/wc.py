from tehbot.plugins.challenge import *
import urllib
import urllib2
import urlparse
import lxml.html
import re

profileurl = "https://www.wechall.net/profile/%s"
url2 = "https://www.wechall.net/wechallchalls.php?username=%s"
challurl = "https://www.wechall.net/challs"
rankurl = "https://www.wechall.net/site/ranking/for/1/WeChall/page-%d"
solversurl = "https://www.wechall.net/challenge_solvers_for/%d/%s/page-%d"

class Site(BaseSite):
    def prefix(self):
        return u"[WeChall]"

    def siteurl(self):
        return "https://www.wechall.net"

    def userstats(self, user):
        page = urllib2.urlopen(url2 % plugins.to_utf8(user)).read()

        match = re.search(r'(\w+) solved (\d+) of (\d+) Challenges with (\d+) of (\d+) possible points \(\d\d\.\d\d%\). Rank for the site WeChall: (\d+)', page)
        if not match:
            return None

        # ugly wechall parsing, thx a lot gizmore! ;PP
        tree = lxml.html.parse(urllib2.urlopen(profileurl % plugins.to_utf8(user)))
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

    def solvers(self, challname, challnr, user):
        if user:
            url = profileurl % plugins.to_utf8(user)
            xp = "//div[@id='page']/table[@id='wc_profile_challenges']//tr"
        else:
            url = challurl
            xp = "//table[@class='wc_chall_table']/tr"

        tree = lxml.html.parse(urllib2.urlopen(url, timeout=5))
        rows = tree.xpath(xp)

        if not rows:
            if user:
                raise NoSuchUserError
            raise UnknownReplyFormat

        res = None

        for row in rows:
            ename = row.xpath("td[2]/a[1]")
            enr = row.xpath("td[3]/a/@href")
            ecnt = row.xpath("td[3]/a")

            if not ename or not enr or not ecnt:
                continue

            name = ename[0].text_content().strip()
            cnt = int(ecnt[0].text_content().strip())
            nr = int(re.search(r'challenge_solvers_for/(\d+)/', enr[0]).group(1))
            esolved = ename[0].xpath("@class")
            solved = esolved and esolved[0] == "wc_chall_solved_1"

            if (challnr and nr == challnr) or (challname and name.lower().startswith(challname.lower())):
                res = (nr, name, cnt, solved)
                break

            if not res and challname and challname.lower() in name.lower():
                res = (nr, name, cnt, solved)

        if not res:
            raise NoSuchChallengeError

        nr, name, cnt, solved = res
        solvers = None if user or cnt == 0 else Site.get_last5_solvers(nr)
        return nr, name, cnt, solvers, solved

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
