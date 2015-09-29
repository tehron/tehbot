import tehbot.plugins as plugins
import urllib
import urllib2
import urlparse
import lxml.html
import re

def stats(user):
    url = "http://sabrefilms.co.uk/revolutionelite/w3ch4ll/userscore.php?username=%s"
    txt = "\x0303[Revolution Elite]\x03 "

    try:
        page = urllib2.urlopen(url % (plugins.to_utf8(user))).read()
    except Exception as e:
        return txt + "Network error."
        #raise e

    if page == "0":
        return txt + "The requested user was not found. You can register at http://revolutionelite.co.uk"

    match = page.split(":")
    if len(match) != 7:
        return txt + "Unexpected format in reply. Try ?blame."
    else:
        _, rank, pts, ptsmax, solved, solvedmax, usercount = match
        txt += "%s solved %s (of %s) challenges and is on rank %s (of %s)." % (user, solved, solvedmax, rank, usercount)
        return txt

def parse_challs(url):
    challs = {}
    tree = lxml.html.parse(urllib2.urlopen(url))
    for e in tree.xpath("//div[@class='content']/center/table/tr"):
        e2 = e.xpath("td[2]")
        if not e2:
            continue
        try:
            nr = int(e2[0].text_content().strip())
        except ValueError:
            continue
        e2 = e.xpath("td[3]")
        if not e2:
            continue
        name = e2[0].text_content().strip()
        e2 = e.xpath("td[3]/center/a/@href")
        if not e2:
            continue

        challs[nr] = (name, urlparse.urljoin(url, e2[0]))

    return challs

def get_solvers(page):
    tree = lxml.html.fromstring(page)
    solvers = []
    for p in tree.xpath("//div[@class='content']/center/table/tr/td/a"):
        solvers.append(p.text_content().strip())
    return solvers

def solvers(challenge_name_or_nr, user=None):
    prefix = "\x0303[Revolution Elite]\x03 "

    challs = parse_challs("https://www.sabrefilms.co.uk/revolutionelite/credits.php")
    nr, name, url = None, None, None

    if isinstance(challenge_name_or_nr, int):
        if challs.has_key(challenge_name_or_nr):
            nr = challenge_name_or_nr
            name, url = challs[challenge_name_or_nr]
    else:
        for key, val in challs.items():
            if val[0].lower().startswith(challenge_name_or_nr.lower()):
                nr = key
                name, url = val
                break
            if challenge_name_or_nr.lower() in val[0].lower():
                nr = key
                name, url = val

    txt = "No such challenge."
    match, solvers = None, None
    if url:
        txt = "Challenge Nr. %d, %s, hasn't been solved by anyone yet." % (nr, name)
        page = urllib.urlopen(url).read()
        match = re.search(r'\((\d+) solvers\) \(latest first\)', page)
        solvers = get_solvers(page)

    if match:
        if user:
            solved = user in solvers
            txt = "Challenge Nr. %d, %s, has%s been solved by %s." % (nr, name, "" if solved else " not", user)
        else:
            cnt = int(match.group(1))
            txt = "Challenge Nr. %d, %s, has been solved by %d user%s." % (nr, name, cnt, "" if cnt == 1 else "s")
            if cnt > 0 and solvers:
                txt += " Last by %s." % ", ".join(solvers[:5])

    return prefix + txt
