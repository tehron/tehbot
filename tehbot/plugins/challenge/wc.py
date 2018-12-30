from tehbot.plugins.challenge import *
import urllib
import urllib2
import urlparse
import lxml.html
import re

url = "https://www.wechall.net/profile/%s"
url2 = "https://www.wechall.net/wechallchalls.php?username=%s"
challurl = "https://www.wechall.net/challs"
rankurl = "https://www.wechall.net/site/ranking/for/1/WeChall/page-%d"
solversurl = "https://www.wechall.net/challenge_solvers_for/%d/%s/page-%d"

class Site(BaseSite):
    def prefix(self):
        return u"[WeChall]"

    def userstats(self, user):
        page = urllib2.urlopen(url2 % plugins.to_utf8(user)).read()

        match = re.search(r'(\w+) solved (\d+) of (\d+) Challenges with (\d+) of (\d+) possible points \(\d\d\.\d\d%\). Rank for the site WeChall: (\d+)', page)
        if not match:
            return None

        # ugly wechall parsing, thx a lot gizmore! ;PP
        tree = lxml.html.parse(urllib2.urlopen(url % plugins.to_utf8(user)))
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
                return challs_solved, [real_user]

        return None

    @staticmethod
    def parse_challs(url):
        challs = {}
        tree = lxml.html.parse(urllib2.urlopen(url))
        for e in tree.xpath("//table[@class='wc_chall_table']/tr"):
            e2 = e.xpath("td[2]/a[1]")
            if not e2:
                continue
            name = e2[0].text_content().strip()
            e2 = e.xpath("td[3]/a")
            if not e2:
                continue
            solvers = int(e2[0].text_content().strip())
            e2 = e.xpath("td[3]/a/@href")
            if not e2:
                continue
            match = re.search(r'challenge_solvers_for/(\d+)/', e2[0])
            if not match:
                continue
            nr = int(match.group(1))
            challs[nr] = (name, urlparse.urljoin(url, e2[0]), solvers)

        return challs

    @staticmethod
    def user_solved(user, nr, name):
        tree = lxml.html.parse(urllib2.urlopen(url % plugins.to_utf8(user)))

        for row in tree.xpath("//div[@id='page']/table[@id='wc_profile_challenges']//tr"):
            e = row.xpath("td[2]/a[1]")
            if e:
                n = e[0].text_content()
                if n.lower().startswith(name.lower()):
                    e2 = e[0].xpath("@class")
                    return e2 and e2[0] == "wc_chall_solved_1"

        return False

    def solvers(self, challname, challnr, user):
        challs = Site.parse_challs(challurl)
        nr, name, url, solvers = None, None, None, None

        if challname is not None:
            for key, val in challs.items():
                if val[0].lower().startswith(challname.lower()):
                    nr = key
                    name, url, solvers = val
                    break
                if challname.lower() in val[0].lower():
                    nr = key
                    name, url, solvers = val
        else:
            if challs.has_key(challnr):
                nr = challnr
                name, url, solvers = challs[challnr]

        if name is None:
            raise NoSuchChallengeError

        cnt = solvers
        solved = Site.user_solved(user, nr, name) if user else False

        return nr, name, cnt, [], solved
