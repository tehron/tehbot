from tehbot.plugins import *
import tehbot.plugins as plugins
import json
import urllib
import locale
try:
    locale.setlocale(locale.LC_ALL, "US" if plugins.is_windows() else "en_US")
except:
    pass
import HTMLParser
html = HTMLParser.HTMLParser()
import shlex

def google_search(searchfor, what="web"):
    query = urllib.urlencode({'q': searchfor.encode("utf-8")})
    url = 'http://ajax.googleapis.com/ajax/services/search/%s?v=1.0&%s' % (what, query)
    search_response = urllib.urlopen(url)
    search_results = search_response.read()
    results = json.loads(search_results)
    data = results['responseData']
    hits = data['results']
    if hits:
        print 'Total results: %s' % data['cursor']['estimatedResultCount']
        print 'Top %d hits:' % len(hits)
        for h in hits: print ' ', h['url']
        count = int(data['cursor']['estimatedResultCount'])
    else:
        count = 0
    searchurl = data['cursor']['moreResultsUrl']
    print 'For more results, see %s' % searchurl
    return count, hits[:3], searchurl

class GooglePlugin(Plugin):
    what = "web"
    prefix = "\x0303[Google]\x03 "

    def execute(self):
        if not self.args:
            return self.help(self.cmd)

        count, hits, searchurl = google_search(self.args, self.what)

        txt = "Found no results. See for yourself: %s" % searchurl

        if hits:
            lst = [ "%s (%s hits)" % (searchurl, locale.format("%d", count, 1)) ]
            for h in hits:
                lst.append("%s | %s" % (html.unescape(h["titleNoFormatting"]), h["unescapedUrl"]))
            txt = "\n".join(lst)

        return self.prefix + txt

class GoogleImagesPlugin(GooglePlugin):
    what = "images"
    prefix = "\x0303[Google Images]\x03 "

class VersusPlugin(Plugin):
    """Usage: vs "search term 1" "search term 2" -- Compares the number of google results for both terms."""

    @staticmethod
    def create_bar(v1, v2, width=41):
        bar = [" "] * width
        if v1 == v2:
            bar[width/2] = "#"
        else:
            v = int(float(width) * v2 / (v1 + v2))
            if v < 0: v = 0
            if v > width - 1: v = width - 1
            bar[v] = "#"
        return "|" + "".join(bar) + "|"

    def execute(self):
        try:
            v = shlex.split(plugins.to_utf8(self.args or ""))
        except Exception as e:
            return str(e)

        if len(v) != 2:
            return self.help(self.cmd)

        term1, term2 = map(lambda x: plugins.from_utf8(x), v)
        hits1 = google_search(term1)[0]
        hits2 = google_search(term2)[0]
        h1 = locale.format("%d", hits1, 1)
        h2 = locale.format("%d", hits2, 1)

        return "%s %s %s %s %s" % (term1, h1, create_bar(hits1, hits2, 21), h2, term2)

register_cmd("google", GooglePlugin())
register_cmd("images", GoogleImagesPlugin())
register_cmd("vs", VersusPlugin())
