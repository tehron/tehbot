import plugins
import urllib
import random

def pun(connection, channel, nick, cmd, args):
    """Print a random pun from jhype.co.uk"""
    page = urllib.urlopen("http://jhype.co.uk/puns.php").read()
    init = False
    puns = []
    currpun = []
    for line in page.splitlines():
        if line.startswith('<p class="emph2">'):
            init = True
            if currpun:
                puns.append("\n".join(currpun))
                currpun = []
            continue
        if init and line.find("</div>") > -1:
            init = False
            break
        if init:
            if line.startswith("<br />"):
                if currpun:
                    puns.append("\n".join(currpun))
                    currpun = []
            else:
                currpun.append(line.replace("<br />", ""))
    if currpun:
        puns.append("\n".join(currpun))

    print puns

    random.shuffle(puns)
    if puns:
        plugins.say_nick(connection, channel, nick, puns[0])

plugins.register_cmd("pun", pun)
