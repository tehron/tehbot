from tehbot.plugins.challenge import *
import urllib
import urllib2
import urlparse
import lxml.html
import re

class Site(BaseSite):
    def prefix(self):
        return u"[Security Traps]"

    def siteurl(self):
        return "https://www.securitytraps.pl"

    def userstats(self, user):
        return self.userstats_api(user)

    def userstats_api(self, user):
        url = "https://www.securitytraps.pl/wcscore.php?uname=%s&key=%s"
        authkey = self.settings["securitytraps_api_key"]
        html = urllib2.urlopen(url % (plugins.to_utf8(user), authkey), timeout=5).read()
        if html == "0":
            return None
        rank, challs_solved, challs_total, users_total, score = html.split(":")
        return user, str(int(challs_solved)), int(challs_total), str(int(rank)), int(users_total), int(score), None, None
