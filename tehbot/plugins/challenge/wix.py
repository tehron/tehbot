from tehbot.plugins.challenge import *
import urllib
import urllib2
import urlparse
import lxml.html
import re

class Site(BaseSite):
    def prefix(self):
        return u"[wixxerd.com]"

    def siteurl(self):
        return "https://www.wixxerd.com"

    def userstats(self, user):
        url = "https://www.wixxerd.com/challenges/userScore.cfm?username=%s&authkey=%s"

        page = urllib2.urlopen(url % (urllib.quote_plus(user), self.settings["wixxerd_api_key"])).read()

        match = page.split(":")
        if len(match) != 6:
            return None

        score, score_total, users_total, challs_solved, challs_total, rank = map(int, match)
        return user, challs_solved, challs_total, str(rank), users_total, score, score_total, None
