from tehbot.plugins import *
import urllib2
import urllib
import lxml.html
import lxml.etree
import json

class UnicodePlugin(StandardPlugin):
    def __init__(self):
        StandardPlugin.__init__(self)
        self.parser.add_argument("search_term", nargs="+")

    @staticmethod
    def prefix():
        return "[UnicodePlugin]"

    def command(self, connection, event, extra, dbconn):
        url = "https://emojipedia.org/search/?%s" % urllib.urlencode(
                { "q" : to_utf8(" ".join(self.pargs.search_term)) }
                )
        try:
            opener = urllib2.build_opener()
            opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
            tree = lxml.html.parse(opener.open(url))
        except:
            return u"%s %s" % (red(UnicodePlugin.prefix()), "Network Error")

        try:
            sign = tree.xpath("//div[@class='content']/ol[@class='search-results']/li/h2/a/span[@class='emoji']")[0].text_content()
        except:
            return u"%s %s" % (red(UnicodePlugin.prefix()), "Unknown Format in Reply")

        return u"%s %s" % (green(UnicodePlugin.prefix()), sign)

register_plugin("uc", UnicodePlugin())
