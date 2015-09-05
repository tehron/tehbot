import plugins
import urllib
import re
import lxml.html
import time
from collections import defaultdict
import shlex
    
nr_to_url = {}

parser = plugins.ThrowingArgumentParser(
    prog="solvers",
    description="Shows solvers for RevEl challenge.")
parser.add_argument("chall_name_or_nr")
parser.add_argument("-n", "--nr", action="store_true")
parser.add_argument("-u", "--user")

def get_solvers(page):
    tree = lxml.html.fromstring(page)
    solvers = []
    for p in tree.xpath("//div[@class='content']/center/table/tr/td/a"):
        solvers.append(p.text_content().strip())
    return solvers

def build_cache():
    url = "https://www.sabrefilms.co.uk/revolutionelite/credits.php"
    tree = lxml.html.parse(urllib.urlopen(url))
    for e in tree.xpath("//div[@class='content']/center/table/tr"):
        e2 = e.xpath("td[2]")
        if not e2:
            continue
        nr = e2[0].text_content().strip()
        e2 = e.xpath("td[3]")
        if not e2:
            continue
        name = e2[0].text_content().strip()
        e2 = e.xpath("td[3]/center/a/@href")
        if not e2:
            continue
        url = "https://www.sabrefilms.co.uk/revolutionelite/%s" % e2[0]

        nr_to_url[nr] = (name, url)

def rev(connection, channel, nick, cmd, args):
    """Shows the ranking on Revolution Elite. Usage: rev [user | rank]"""
    user, rank = None, None
    if not args or not args.strip():
        user = nick
    else:
        arg = args.strip()
        if arg.isdigit():
            rank = int(arg)
        else:
            user = arg

    if user:
        rev_user(connection, channel, nick, cmd, args, user)
    else:
        rev_rank(connection, channel, nick, cmd, args, rank)

rank_cache = {}
rank_ts = 0

def build_rank_cache():
    global rank_ts
    url = "https://www.sabrefilms.co.uk/revolutionelite/rank.php?page=%d"
    i = 1
    users = defaultdict(list)
    try:
        #while True:
        for i in xrange(1, 8):
            u = url % i
            print "Getting " + u
            print "users", users
            tree = lxml.html.parse(urllib.urlopen(u))
            for e in tree.xpath("//div[@class='content']/center/table/tr"):
                e2 = e.xpath("td[2]")
                if not e2: continue
                e3 = e.xpath("td[3]")
                if not e3: continue
                users[int(e3[0].text_content())].append(e2[0].text_content().strip())
            #i += 1
    except Exception as e:
        print e
        pass

    rank_cache.clear()
    rank_ts = time.time()
    i = 1
    for key, val in sorted(users.items(), reverse=True):
        rank_cache[i] = val
        i += len(val)

def rev_rank(connection, channel, nick, cmd, args, rank):
    if time.time() - rank_ts > 5 * 60:
        print "time diff", (time.time() - rank_ts)
        build_rank_cache()

    if not rank_cache.has_key(rank):
        plugins.say(connection, channel, "The requested user was not found. You can register at http://revolutionelite.co.uk")
        return

    users = rank_cache[rank]
    if len(users) == 1:
        rev_user(connection, channel, nick, cmd, args, users[0])
    else:
        plugins.say(connection, channel, "%s are at rank %d at http://revolutionelite.co.uk" % (", ".join(users), rank))

def rev_user(connection, channel, nick, cmd, args, user):
    try:
        page = urllib.urlopen("http://sabrefilms.co.uk/revolutionelite/w3ch4ll/userscore.php?username=%s" % (plugins.to_utf8(user))).read()
    except Exception as e:
        plugins.say(connection, channel, "Network error.")
        raise e

    if page == "0":
        plugins.say(connection, channel, "The requested user was not found. You can register at http://revolutionelite.co.uk")
        return

    match = page.split(":")
    if len(match) != 7:
        plugins.say(connection, channel, "Unexpected format in reply. Try .blame")
    else:
        _, rank, pts, ptsmax, solved, solvedmax, usercount = match
        plugins.say(connection, channel, "%s solved %s (of %s) challenges and is on rank %s (of %s) scoring %s (of %s) points at http://revolutionelite.co.uk" % (user, solved, solvedmax, rank, usercount, pts, ptsmax))

def revsolve(connection, channel, nick, cmd, args):
    print "revsolve", args

    if channel != "#revolutionelite":
        return

    try:
        pargs = parser.parse_args(shlex.split(args or ""))
        if parser.help_requested:
            return plugins.say(connection, channel, parser.format_help().strip())
        if pargs.nr:
            int(pargs.chall_name_or_nr)
    except plugins.ArgumentParserError as e:
        return plugins.say(connection, channel, "error: %s" % str(e))
    except (SystemExit, NameError, ValueError):
        return plugins.print_help(connection, channel, nick, None, cmd)

    build_cache()

    nr, name, url = None, None, None
    if pargs.nr:
        nr = pargs.chall_name_or_nr
        if nr_to_url.has_key(nr):
            name, url = nr_to_url[nr]
    else:
        for key, val in nr_to_url.items():
            if val[0].lower().startswith(pargs.chall_name_or_nr.lower()):
                nr = key
                name, url = val
                break
            if pargs.chall_name_or_nr.lower() in val[0].lower():
                nr = key
                name, url = val

    match = None
    if url:
        page = urllib.urlopen(url).read()
        match = re.search(r'\((\d+) solvers\) \(latest first\)', page)

        solvers = get_solvers(page)
        print solvers

    txt = "No such challenge."
    if match:
        if pargs.user:
            solved = pargs.user in solvers
            txt = "Challenge Nr. %s, %s, has%s been solved by %s." % (nr, name, "" if solved else " not", pargs.user)
        else:
            cnt = int(match.group(1))
            txt = "Challenge Nr. %s, %s, has been solved by %d user%s." % (nr, name, cnt, "" if cnt == 1 else "s")
            if cnt > 0:
                txt += " Last by %s." % ", ".join(solvers[:5])

    plugins.say(connection, channel, txt)

def clubsoda(connection, channel, nick, cmd, args):
    if not args or not args.strip():
        rec = nick
    else:
        rec = args.split()[0].strip()
    plugins.say(connection, channel, "tehbot hands %s a nice club soda." % rec)

def badumm(connection, channel, nick, cmd, args):
    plugins.say(connection, channel, ".badjoke")

plugins.register_cmd("rev", rev)
plugins.register_cmd("solvers", revsolve)
plugins.register_cmd("clubsoda", clubsoda)
plugins.register_cmd("badumm", badumm)

revsolve.__doc__ = parser.description + " " + parser.format_usage().strip()
