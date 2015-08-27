import plugins
import urllib
import re
import lxml.html
import time
from collections import defaultdict
from random import *

cache_ts = 0
nr_to_url = {}

def build_cache():
    global cache_ts
    tree = lxml.html.parse("http://www.wechall.net/challs")
    nr_to_url.clear()
    cache_ts = time.time()
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
        nr = match.group(1)
        url = "http://www.wechall.net/%s" % e2[0]
        nr_to_url[nr] = (name, url, solvers)

def wcsolve(connection, channel, nick, cmd, args):
    #"""Usage: revsolve (chall nr | chall name) [user]"""
    """Shows how many solved a challenge. Usage: wcsolve (chall nr | chall name)"""
    print "wcsolve", args
    if time.time() - cache_ts > 1 * 60:
        print "time diff", (time.time() - cache_ts)
        build_cache()

    if not args:
        plugins.print_help(connection, channel, nick, None, cmd)
        return

    nr, name, url, solvers = None, None, None, None
    if args.isdigit():
        nr = args
        if nr_to_url.has_key(nr):
            name, url, solvers = nr_to_url[nr]
    else:
        for key, val in nr_to_url.items():
            if val[0].lower().startswith(args.lower()):
                nr = key
                name, url, solvers = val
                break
            if args.lower() in val[0].lower():
                nr = key
                name, url, solvers = val

    txt = "No such challenge."
    if solvers is not None:
        txt = "Challenge Nr. %s, %s, has been solved by %d user%s." % (nr, name, solvers, "" if solvers == 1 else "s")

    plugins.say(connection, channel, txt)

def blame(connection, channel, nick, cmd, args):
    space = u"\u0455paceone"
    goats = zip((space for one in range(23)), 42 * [ reduce(random, [], space) ])
    shuffle(goats)
    goats.sort(key=lambda x: random())
    shuffle(goats)
    scapegoat = goats[randint(0, len(goats) - 1)][int(1337 * random()) % 2]
    plugins.say(connection, channel, "I blame %s." % scapegoat)

plugins.register_pub_cmd("wcsolve", wcsolve)
plugins.register_pub_cmd("blame", blame)
