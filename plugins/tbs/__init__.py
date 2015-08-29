import plugins
import urllib
import re
import lxml.html
import time
from collections import defaultdict

solved_cache = []

def build_cache():
    global solved_cache
    solved_cache = []
    tree = lxml.html.parse("http://www.bright-shadows.net/hackchallenge.php")
    for e in tree.xpath("//div[@class='cl_challs']//tr"):
        e2 = e.xpath("td[@class='name']")
        if not e2:
            continue
        name = e2[0].text_content().split(":", 1)[1].strip()
        e2 = e.xpath("td[@class='name']//@href")
        if not e2:
            continue
        url = "http://www.bright-shadows.net/%s" % e2[0]
        e2 = e.xpath("td[@class='doneby']")
        if not e2:
            continue
        solvers = int(e2[0].text_content())

        solved_cache.append((name, url, solvers))

def tbssolve(connection, channel, nick, cmd, args):
    #"""Usage: tbssolve chall_name"""
    """Shows how many solved a challenge. Usage: tbssolve chall_name"""

    if not args:
        plugins.print_help(connection, channel, nick, None, cmd)
        return

    build_cache()
    print solved_cache
    name, url, solved = None, None, None
    for n, u, s in solved_cache:
        if n.lower().startswith(args.lower()):
            name = n
            url = u
            solved = s
            break

    txt = "No such challenge."
    if name:
        txt = "Challenge '%s' has been solved by %d user%s." % (name, solved, "" if solved == 1 else "s")

    plugins.say(connection, channel, txt)

plugins.register_pub_cmd("tbssolve", tbssolve)
