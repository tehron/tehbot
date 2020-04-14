from tehbot.plugins.challenge import *
import urllib
import urllib2
import urlparse
import lxml.html
import re

class Site(BaseSite):
    def prefix(self):
        return u"[CryptoHack]"

    def siteurl(self):
        return "https://cryptohack.org"

    def userstats(self, user):
        return self.userstats_api(user)

    def userstats_api(self, user):
        url = "https://cryptohack.org/wechall/userscore/?username=%s&authkey=%s"
        authkey = self.settings["cryptohack_api_key"]
        html = urllib2.urlopen(url % (Plugin.to_utf8(user), authkey), timeout=5).read()
        if html == "failed":
            return None
        user, rank, score, scoremax, challs_solved, challs_total, users_total = html.split(":")
        return user, str(int(challs_solved)), int(challs_total), str(int(rank)), int(users_total), int(score), int(scoremax), None
