from tehbot.plugins.challenge import *
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import urllib.parse
import lxml.html
import re

class Site(BaseSite):
    def prefix(self):
        return "[247CTF]"

    def siteurl(self):
        return "https://247ctf.com"

    def userstats(self, user):
        return self.userstats_api(user)

    def userstats_api(self, user):
        url = "https://247ctf.com/wechall_validate_score_service?username=%s&authkey=%s"
        authkey = self.settings["247ctf_api_key"]
        html = urllib.request.urlopen(url % (Plugin.to_utf8(user), authkey), timeout=5).read()
        html = html.decode()
        if html == "":
            return None
        user, rank, score, scoremax, challs_solved, challs_total, users_total = html.split(":")
        return user, str(int(challs_solved)), int(challs_total), str(int(rank)), int(users_total), int(score), int(scoremax), None
