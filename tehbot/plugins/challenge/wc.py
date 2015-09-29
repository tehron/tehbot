import tehbot.plugins as plugins
import urllib2
import urlparse
import lxml.html
import re

url = "https://www.wechall.net/profile/%s"
url2 = "https://www.wechall.net/wechallchalls.php?username=%s"
challurl = "https://www.wechall.net/challs"
prefix = "\x0303[WeChall]\x03 "

def stats(user):
    txt = "\x0303[WeChall]\x03 "

    try:
        tree = lxml.html.parse(urllib2.urlopen(url % plugins.to_utf8(user)))
        page = urllib2.urlopen(url2 % plugins.to_utf8(user)).read()
    except Exception as e:
        return txt + "Network error."

    # ugly wechall parsing, thx a lot gizmore! ;PP
    try:
        real_user = tree.xpath("//div[@id='page']//th[text()='Username']/../td")[0].text_content()
        challs_solved = int(tree.xpath("count(//table[@id='wc_profile_challenges']/tr//a[@class='wc_chall_solved_1'])"))
        challs_total = int(tree.xpath("count(//table[@id='wc_profile_challenges']/tr)"))
        users_total = int(tree.xpath("//div[@id='wc_sidebar']//div[@class='wc_side_content']//div/a[@href='/users']")[0].text_content().split()[0])
        rank = int(re.findall(r'\d+', page)[-1])
    except:
        return txt + "The requested user was not found, you can register at https://www.wechall.net"

    txt += "%s solved %d (of %d) challenges and is on rank %s (of %d)." % (real_user, challs_solved, challs_total, rank, users_total)
    return txt

def parse_challs(url):
    challs = {}
    tree = lxml.html.parse(urllib2.urlopen(url))
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
        nr = int(match.group(1))
        challs[nr] = (name, urlparse.urljoin(url, e2[0]), solvers)

    return challs

def solvers(challenge_name_or_nr, user=None):
    challs = parse_challs(challurl)
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
    if solvers is not None:
        txt = "Challenge Nr. %d, %s, hasn't been solved by anyone yet." % (nr, name)

        if solvers > 0:
            txt = "Challenge Nr. %d, %s, has been solved by %d user%s." % (nr, name, solvers, "" if solvers == 1 else "s")

    return prefix + txt
