from tehbot.plugins.challenge import *
import urllib.request, urllib.error, urllib.parse
import urllib.parse
import lxml.html
import re

url1 = "http://www.happy-security.de/utilities/hotlink/userscoring.php?username=%s"
url2 = "http://www.happy-security.de/?modul=hacking-zone&action=highscore&start=%s&level_id="
url3 = "http://www.happy-security.de/index.php?modul=hacking-zone&action=highscore_details&user=%s"

class Site(BaseSite):
    def prefix(self):
        return "[Happy-Security]"

    def siteurl(self):
        return "http://www.happy-security.de"

    def userstats(self, user):
        page = urllib.request.urlopen(url1 % Plugin.to_latin1(user), timeout=5).read()
        page = page.decode("latin1")

        match = page.split(":")
        if len(match) != 6:
            return None

        rank, challs_solved, challs_total, users_total, challs_contributed, user = match
        extra = None

        if int(challs_contributed) > 0:
            extra = " %s has contributed %d challenge%s." % (user, int(challs_contributed), "" if int(challs_contributed) == 1 else "s")

        if int(rank) > 1:
            try:
                user2 = Site.hs_rank_to_user(int(rank) - 1)
                result = urllib.request.urlopen(url1 % Plugin.to_latin1(user2), timeout=5).read().decode("latin1").split(":")
                if len(result) == 6:
                    rank2, challs_solved2, challs_total2, users_total2, challs_contributed2, user2 = result
                    count = int(challs_solved2) - int(challs_solved)
                    if int(challs_contributed) <= int(challs_contributed2):
                        count += 1
                    if extra is None:
                        extra = ""
                    extra += " %s needs to solve %d more challenge%s to rank up." % (user, count, "" if count == 1 else "s")
            except:
                pass

        return user, str(int(challs_solved)), int(challs_total), rank, int(users_total), None, None, extra

    @staticmethod
    def hs_rank_to_user(rank):
        tree = lxml.html.parse(urllib.request.urlopen(url2 % rank, timeout=3))
        rows = tree.xpath("//td[@class='middle']//table[@class='mtable']/tr")
        if len(rows) < 2:
            return ""
        return rows[1].xpath("td[2]")[0].text_content().split()[0]

    def rankstats(self, rank):
        res = self.userstats(Site.hs_rank_to_user(rank))
        user, solved, solvedmax, rank, usercount, score, scoremax, extra = res
        return solved, [user], solvedmax

    @staticmethod
    def parse_challs(url):
        challs = {}
        tree = lxml.html.parse(urllib.request.urlopen(url, timeout=5))
        for e in tree.xpath("//td[@class='middle']//table[@class='mtable']/tr"):
            e2 = e.xpath("td[2]//a[1]")
            e3 = e.xpath("td[4]/a")
            if not e2 or not e3 or not e2[0].text_content() or not e3[0].text_content(): continue
            solvers = int(list(filter(str.isdigit, e3[0].text_content())))
            match = re.search(r'level_id=(\d+)', e2[0].xpath("@href")[0])
            if match:
                chall_nr = int(match.group(1))
                d = e2[0].text_content()
                challs[chall_nr] = (e2[0].text_content().strip(), urllib.parse.urljoin(url, e3[0].xpath("@href")[0]), solvers)

        return challs

    @staticmethod
    def get_last_solvers(url):
        tree = lxml.html.parse(urllib.request.urlopen(url, timeout=5))
        solvers = []
        for p in tree.xpath("//td[@class='middle']//table[@class='mtable']/tr/td[2]/a"):
            solvers.append(p.text_content().strip())
        return solvers

    @staticmethod
    def solved(user, challenge_name):
        tree = lxml.html.parse(urllib.request.urlopen(url3 % Plugin.to_latin1(user), timeout=3))
        for cat in tree.xpath("//td[@class='middle']//table[@class='mtable']"):
            for row in cat.xpath("tr"):
                chall_link = row.xpath("td[2]//a[1]")
                title = row.xpath("td[8]//img/@title")
                if chall_link and title and chall_link[0].text_content() == challenge_name:
                    return title[0].lower().find("solved=yes") > -1
        return False

    def solvers(self, challname, challnr, user):
        challs = Site.parse_challs("http://www.happy-security.de/index.php?modul=hacking-zone")
        nr, name, url, solvers = None, None, None, None

        if challname is not None:
            for key, val in list(challs.items()):
                if val[0].lower().startswith(challname.lower()):
                    nr = key
                    name, url, solvers = val
                    break
                if challname.lower() in val[0].lower():
                    nr = key
                    name, url, solvers = val
        else:
            if challnr in challs:
                nr = challnr
                name, url, solvers = challs[challnr]

        if not name:
            raise NoSuchChallengeError

        cnt = solvers
        solvers = Site.get_last_solvers(url)

        return user, nr, name, cnt, solvers, user and Site.solved(user, name)
