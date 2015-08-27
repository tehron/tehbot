import plugins
import urllib
import urllib2
import json
import lxml.html

url = "https://en.wikipedia.org/w/api.php?%s"

def get_text(tree, xpath):
    return "\n".join(e.text_content() for e in tree.xpath(xpath))

def wiki(connection, channel, nick, cmd, args):
    """Looks up a search term on Wikipedia"""

    if not args:
        return plugins.print_help(connection, channel, nick, None, cmd)

    data = {
        "action" : "opensearch",
        "limit" : 1,
        "format" : "json",
        "search" : plugins.to_utf8(args)
    }
    req = urllib2.Request(url % urllib.urlencode(data))
    pageurl = json.load(urllib2.urlopen(req))[-1]
    txt = "[Wikipedia] "
    
    if not pageurl:
        return plugins.say(connection, channel, txt + "Search didn't find anything.")

    tree = lxml.html.parse(urllib2.urlopen(pageurl[0]))
    title = get_text(tree, "//h1[@id='firstHeading']")
    short = get_text(tree, "//div[@id='mw-content-text']/p")

    if not title or not short:
        return plugins.say(connection, channel, txt + "Something went wrong.")
    
    txt += "\x02%s\x0f\n%s" % (title, short[:300])
    plugins.say(connection, channel, txt)

plugins.register_pub_cmd("wiki", wiki)
