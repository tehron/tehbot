from tehbot.plugins.challenge import *
import urllib
import urllib2
import urlparse
import lxml.html
import re

class Site(BaseSite):
    def prefix(self):
        return u"[Defend the Web]"

    def siteurl(self):
        return "https://defendtheweb.net"

    def userstats(self, user):
        url = "https://defendtheweb.net/wechall/userscore?username=%s&authkey=%s"
        authkey = self.settings["defendtheweb_auth_key"]
        html = urllib2.urlopen(url % (Plugin.to_utf8(user), authkey), timeout=5).read()
        if html == "0":
            return None
        user, rank, score, scoremax, challs_solved, challs_total, users_total = html.split(":")
        return user, str(int(challs_solved)), int(challs_total), str(int(rank)), int(users_total), int(score), int(scoremax), None
