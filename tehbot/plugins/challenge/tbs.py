from tehbot.plugins.challenge import *
import urllib
import urllib2
import urlparse
import lxml.html
import re

class Site(BaseSite):
    def prefix(self):
        return u"[TheBlackSheep]"

    def siteurl(self):
        return "http://www.bright-shadows.net"

    def userstats(self, user):
        return self.userstats_api(user)

    def userstats_api(self, user):
        url = "http://www.bright-shadows.net/userdata.php?username=%s"
        html = urllib2.urlopen(url % plugins.to_utf8(user), timeout=5).read()
        if html == "Unknown User":
            return None
        real_user, rank, users_total, challs_solved, challs_total = html.split(":")
        return real_user, str(int(challs_solved)), int(challs_total), str(int(rank)), int(users_total), None, None, None

    def userstats_html(self, user):
        url = "http://www.bright-shadows.net/ranking.php?perpage=1&showuser=%s"
        tree = lxml.html.parse(urllib2.urlopen(url % (plugins.to_utf8(user))))
        rank = int(float(tree.xpath("//td[@class='rank_rank']")[0].text_content()))
        real_user = tree.xpath("//td[@class='rank_user']")[0].text_content()
        challs = int(tree.xpath("//td[@class='rank_solved']")[0].text_content())

        if user.lower() != real_user.lower():
            return None

        users_total = re.search(r'''(\d+) users ranked''', tree.xpath("//div[@class='module']/h1")[0].text_content()).group(1)
        return real_user, challs, 342, str(rank), int(users_total), None, None, None
