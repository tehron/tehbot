from tehbot.plugins import *
import urllib.request, urllib.error, urllib.parse
import urllib.request, urllib.parse, urllib.error
import lxml.html
import lxml.etree
import json

class UnicodePlugin(StandardCommand):
    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("search_term", nargs="+")

    @staticmethod
    def prefix():
        return "[UnicodePlugin]"

    def commands(self):
        return "uc"

    def execute_parsed(self, connection, event, extra):
        url = "https://emojipedia.org/search/?%s" % urllib.parse.urlencode(
                { "q" : Plugin.to_utf8(" ".join(self.pargs.search_term)) }
                )
        try:
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
            tree = lxml.html.parse(opener.open(url))
        except:
            return "%s %s" % (red(UnicodePlugin.prefix()), "Network Error")

        try:
            sign = tree.xpath("//div[@class='content']/ol[@class='search-results']/li/h2/a/span[@class='emoji']")[0].text_content()
        except:
            try:
                noresults = tree.xpath("//div[@class='content']/ol[@class='search-results']/li/p")[0].text_content()
                if "no results" in noresults.lower():
                    sign = "No Results"
                else:
                    raise Exception
            except:
                return "%s %s" % (Plugin.red(UnicodePlugin.prefix()), "Unknown Format in Reply")

        return "%s %s" % (Plugin.green(UnicodePlugin.prefix()), sign)
