from tehbot.plugins import *
import tehbot.plugins as plugins
import urllib
import urllib2
import json
import lxml.html

url = "https://en.wikipedia.org/w/api.php?%s"

def get_text(tree, xpath):
    return "\n".join(e.text_content() for e in tree.xpath(xpath))

def wikify(title):
    return urllib.quote(to_utf8(title.replace(" ", "_")))

class WikipediaPlugin(StandardPlugin):
    """Looks up a search term on Wikipedia"""

    def __init__(self):
        StandardPlugin.__init__(self)
        self.parser.add_argument("term")

    def execute(self, connection, event, extra, dbconn):
        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % str(e)

        data = {
            "action" : "query",
            "list" : "search",
            "srsearch" : plugins.to_utf8(pargs.term),
            "srlimit" : 1,
            "srprop" : "",
            "format" : "json",
            "continue" : ""
        }

        prefix = "\x0303[Wikipedia]\x03 "
        req = urllib2.Request(url % urllib.urlencode(data))

        try:
            title = json.load(urllib2.urlopen(req))["query"]["search"][0]["title"]
        except:
            return prefix + "Search didn't find anything."

        pageurl = "https://en.wikipedia.org/wiki/%s" % wikify(title)

        tree = lxml.html.parse(urllib2.urlopen(pageurl))
        title = get_text(tree, "//h1[@id='firstHeading']")
        content = get_text(tree, "//div[@id='mw-content-text']/div/p")

        if not title or not content:
            return prefix + "Something went wrong."

        if tree.xpath("//div[@id='mw-content-text']//table[@id='disambigbox']"):
            content += " " + ", ".join(tree.xpath("//div[@id='mw-content-text']/ul/li//a[1]/@title"))

        txt = "%s (%s)\n%s" % (title, pageurl, plugins.shorten(content, 300))
        return prefix + txt

register_plugin("wiki", WikipediaPlugin())
