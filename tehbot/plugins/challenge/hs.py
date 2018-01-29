import tehbot.plugins as plugins
import urllib2
import urlparse
import lxml.html
import re

url1 = "http://www.happy-security.de/utilities/hotlink/userscoring.php?username=%s"
url2 = "http://www.happy-security.de/?modul=hacking-zone&action=highscore&start=%s&level_id="

def stats(user, rank):
    if rank:
        return userstats(hs_rank_to_user(rank))

    return userstats(user)

def hs_rank_to_user(rank):
    tree = lxml.html.parse(url2 % rank)
    rows = tree.xpath("//td[@class='middle']//table[@class='mtable']/tr")
    if len(rows) < 2:
        return ""
    return rows[1].xpath("td[2]")[0].text_content().split()[0]

def userstats(user):
    txt = "\x0303[Happy-Security]\x03 "

    try:
        page = urllib2.urlopen(url1 % plugins.to_latin1(user)).read()
        page = page.decode("latin1")
    except Exception as e:
        return txt + "Network error."

    match = page.split(":")
    if len(match) != 6:
        return txt + "The requested user was not found, you can register at http://www.happy-security.de"
    else:
        rank, challs_solved, challs_total, users_total, challs_contributed, user = match
        txt += "%s solved %d (of %d) challenges and is on rank %d (of %d)." % (user, int(challs_solved), int(challs_total), int(rank), int(users_total))
        txt += " %s has contributed %d challenge%s." % (user, int(challs_contributed), "" if int(challs_contributed) == 1 else "s")
        if int(rank) > 1:
            try:
                user2 = hs_rank_to_user(int(rank) - 1)
                result = urllib2.urlopen(url1 % plugins.to_latin1(user2)).read().decode("latin1").split(":")
                if len(result) == 6:
                    rank2, challs_solved2, challs_total2, users_total2, challs_contributed2, user2 = result
                    count = int(challs_solved2) - int(challs_solved)
                    if int(challs_contributed) <= int(challs_contributed2):
                        count += 1
                    txt += " %s needs to solve %d more challenge%s to rank up." % (user, count, "" if count == 1 else "s")
            except:
                pass
        return txt

def parse_challs(url):
    challs = {}
    tree = lxml.html.parse(urllib2.urlopen(url))
    for e in tree.xpath("//td[@class='middle']//table[@class='mtable']/tr"):
        e2 = e.xpath("td[2]//a[1]")
        e3 = e.xpath("td[4]/a")
        if not e2 or not e3 or not e2[0].text_content() or not e3[0].text_content(): continue
        solvers = int(filter(str.isdigit, e3[0].text_content()))
        match = re.search(r'level_id=(\d+)', e2[0].xpath("@href")[0])
        if match:
            chall_nr = int(match.group(1))
            d = e2[0].text_content()
            challs[chall_nr] = (e2[0].text_content().strip(), urlparse.urljoin(url, e3[0].xpath("@href")[0]), solvers)

    return challs

def get_last_solvers(url):
    print "foobar", url
    tree = lxml.html.parse(urllib2.urlopen(url))
    solvers = []
    for p in tree.xpath("//td[@class='middle']//table[@class='mtable']/tr/td[2]/a"):
        solvers.append(p.text_content().strip())
    return solvers

def solvers(challenge_name_or_nr, user=None):
    prefix = "\x0303[Happy-Security]\x03 "

    challs = parse_challs("http://www.happy-security.de/index.php?modul=hacking-zone")
    nr, name, url, solvers = None, None, None, None

    if isinstance(challenge_name_or_nr, int):
        if challs.has_key(challenge_name_or_nr):
            nr = challenge_name_or_nr
            name, url, solvers = challs[challenge_name_or_nr]
    else:
        for key, val in challs.items():
            if val[0].lower().startswith(challenge_name_or_nr.lower()):
                nr = key
                name, url, solvers = val
                break
            if challenge_name_or_nr.lower() in val[0].lower():
                nr = key
                name, url, solvers = val

    txt = "No such challenge."

    if name:
        txt = "Challenge Nr. %d, %s, hasn't been solved by anyone yet." % (nr, name)

        if solvers:
            cnt = solvers
            txt = "Challenge Nr. %d, %s, has been solved by %d user%s." % (nr, name, cnt, "" if cnt == 1 else "s")
            last_solvers = get_last_solvers(url)
            if cnt > 0 and last_solvers:
                txt += " Last by %s." % ", ".join(last_solvers[:5])

    return prefix + txt
