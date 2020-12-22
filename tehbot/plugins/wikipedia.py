from tehbot.plugins import *
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import json
import lxml.html

url = "https://en.wikipedia.org/w/api.php?%s"

def get_text(tree, xpath):
    return "\n".join(e.text_content() for e in tree.xpath(xpath))

def wikify(title):
    return urllib.parse.quote(Plugin.to_utf8(title.replace(" ", "_")))

class WikipediaPlugin(StandardCommand):
    """Looks up a search term on Wikipedia"""

    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("term", nargs="+")

    def commands(self):
        return "wiki"

    def execute_parsed(self, connection, event, extra):
        data = {
            "action" : "query",
            "list" : "search",
            "srsearch" : Plugin.to_utf8(" ".join(self.pargs.term)),
            "srlimit" : 1,
            "srprop" : "",
            "format" : "json",
            "continue" : ""
        }

        prefix = "\x0303[Wikipedia]\x03 "
        req = urllib.request.Request(url % urllib.parse.urlencode(data))

        try:
            title = json.load(urllib.request.urlopen(req))["query"]["search"][0]["title"]
        except:
            return prefix + "Search didn't find anything."

        pageurl = "https://en.wikipedia.org/wiki/%s" % wikify(title)

        tree = lxml.html.parse(urllib.request.urlopen(pageurl))
        title = get_text(tree, "//h1[@id='firstHeading']")
        content = get_text(tree, "//div[@id='mw-content-text']/div/p")

        if not title or not content:
            return prefix + "Something went wrong."

        if tree.xpath("//div[@id='mw-content-text']//table[@id='disambigbox']"):
            content += " " + ", ".join(tree.xpath("//div[@id='mw-content-text']/ul/li//a[1]/@title"))

        txt = "%s (%s)\n%s" % (title, pageurl, Plugin.shorten(content, 300))
        return prefix + txt
