import plugins
import json
import urllib
import locale
locale.setlocale(locale.LC_ALL, "US" if plugins.is_windows() else "en_US")
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

def helper(connection, channel, nick, cmd, args, what):
    if not args:
        return plugins.print_help(connection, channel, nick, None, cmd)

    count, hits, searchurl = google_search(args, what)
    for h in hits:
        plugins.say(connection, channel, "%s | %s" % (html.unescape(h["titleNoFormatting"]), h["unescapedUrl"]))
    if hits:
        plugins.say(connection, channel, "For more results, see %s (%s hits)" % (searchurl, locale.format("%d", count, 1)))
    else:
        plugins.say(connection, channel, "Found no results. See for yourself: %s" % searchurl)

def images(connection, channel, nick, cmd, args):
    helper(connection, channel, nick, cmd, args, "images")

def google(connection, channel, nick, cmd, args):
    helper(connection, channel, nick, cmd, args, "web")

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

def vs(connection, channel, nick, cmd, args):
    """Usage: vs "search term 1" "search term 2" -- Compares the number of google results for both terms."""
    if not args:
        return plugins.print_help(connection, channel, nick, None, cmd)

    try:
        v = shlex.split(args)
    except Exception as e:
        return plugins.say(connection, channel, str(e))
    
    if len(v) != 2:
        return plugins.print_help(connection, channel, nick, None, cmd)
    
    term1, term2 = v
    hits1 = google_search(term1.encode("utf-8"))[0]
    hits2 = google_search(term2.encode("utf-8"))[0]
    h1 = locale.format("%d", hits1, 1)
    h2 = locale.format("%d", hits2, 1)
    plugins.say(connection, channel, "%s %s %s %s %s" % (term1, h1, create_bar(hits1, hits2, 21), h2, term2))

plugins.register_pub_cmd("vs", vs)
plugins.register_pub_cmd("google", google)
plugins.register_pub_cmd("images", images)
