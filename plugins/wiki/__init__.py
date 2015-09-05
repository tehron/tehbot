import plugins
import urllib
import urllib2
import json
import lxml.html

url = "https://en.wikipedia.org/w/api.php?%s"

def get_text(tree, xpath):
    return "\n".join(e.text_content() for e in tree.xpath(xpath))

def wikify(title):
    return urllib.quote(title.replace(" ", "_"))

def wiki(connection, channel, nick, cmd, args):
    """Looks up a search term on Wikipedia"""

    if not args:
        return plugins.print_help(connection, channel, nick, None, cmd)

    data = {
        "action" : "query",
        "list" : "search",
        "srsearch" : plugins.to_utf8(args),
        "srlimit" : 1,
        "srprop" : "",
        "format" : "json",
        "continue" : ""
    }

    txt = "\x0303[Wikipedia]\x03 "
    req = urllib2.Request(url % urllib.urlencode(data))

    try:
        title = json.load(urllib2.urlopen(req))["query"]["search"][0]["title"]
    except:
        return plugins.say(connection, channel, txt + "Search didn't find anything.")

    pageurl = "https://en.wikipedia.org/wiki/%s" % wikify(title)

    tree = lxml.html.parse(urllib2.urlopen(pageurl))
    title = get_text(tree, "//h1[@id='firstHeading']")
    content = get_text(tree, "//div[@id='mw-content-text']/p")

    if not title or not content:
        return plugins.say(connection, channel, txt + "Something went wrong.")

    if tree.xpath("//div[@id='mw-content-text']//table[@id='disambigbox']"):
        content += " " + ", ".join(tree.xpath("//div[@id='mw-content-text']/ul/li//a[1]/@title"))

    txt += "%s (%s)\n%s" % (title, pageurl, plugins.shorten(content, 300))
    plugins.say(connection, channel, txt)

plugins.register_cmd("wiki", wiki)
