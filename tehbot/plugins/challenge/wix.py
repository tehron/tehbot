import tehbot.plugins as plugins
import urllib
import urllib2
import urlparse
import lxml.html
import re

prefix = "\x0303[wixxerd.com]\x03 "
url = "https://www.wixxerd.com/challenges/userScore.cfm?username=%s&authkey=%s"

def stats(user, rank):
    if rank:
        return "Not implemented yet :/"

    return userstats(user)

def userstats(user):
    try:
        page = urllib.urlopen(url % (urllib.quote_plus(user), settings["wixxerd_api_key"])).read()
    except:
        return "Network error"

    match = page.split(":")
    if len(match) != 6:
        return prefix + "The requested user was not found, you can register at http://www.wixxerd.com"

    score, score_total, users_total, challs_solved, challs_total, rank = map(int, match)
    return prefix + "%s solved %d (of %d) challenges and is on rank %d (of %d)." % (user, challs_solved, challs_total, rank, users_total)

def solvers(challenge_name_or_nr, user=None):
    return "Not implemented yet :/"
