from tehbot.plugins.challenge import *
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import urllib.parse
import lxml.html
import re

class Site(BaseSite):
    def prefix(self):
        return "[Security Traps]"

    def siteurl(self):
        return "https://www.securitytraps.pl"

    def userstats(self, user):
        return self.userstats_api(user)

    def userstats_api(self, user):
        url = "https://www.securitytraps.pl/wcscore.php?uname=%s&key=%s"
        authkey = self.settings["securitytraps_api_key"]
        html = urllib.request.urlopen(url % (Plugin.to_utf8(user), authkey), timeout=5).read()
        html = html.decode()
        if html == "0":
            return None
        rank, challs_solved, challs_total, users_total, scoremax = html.split(":")
        return user, str(int(challs_solved)), int(challs_total), str(int(rank)), int(users_total), None, int(scoremax), None
