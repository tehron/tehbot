from tehbot.plugins import *
import tehbot.plugins as plugins
import urllib2
import json
import re
import urllib

__all__ = ["ddgsearch"]

def search(query, useragent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:63.0) Gecko/20100101 Firefox/63.0"):
    params = {
            "q" : query,
            "format" : "json",
            "no_html" : 1
            }
    h = {

            "User-Agent" : useragent
            }

    req = urllib2.Request("https://api.duckduckgo.com/?%s" % urllib.urlencode(params), headers=h)
    res = urllib2.urlopen(req).read()

    return res

def orstr(lst):
    if not lst:
        return u""

    if len(lst) == 1:
        return lst[0]

    return u", ".join(lst[:-1]) + u", or %s" % lst[-1]

def collect_topics(json, key, topics):
    for x in json[key]:
        if x.has_key("Topics"):
            collect_topics(x, "Topics", topics)
        elif x.has_key("FirstURL"):
            url = x["FirstURL"]
            m = re.search(r'/?q=([^/]+)$', url)
            if m is not None:
                top = m.group(1)
            else:
                m = re.search(r'/([^/]+)$', url)
                top = m.group(1).replace("_", " ")

            top = from_utf8(urllib.unquote(str(top)))
            topics.add(u'\x02%s\x0f' % top)

def ddgsearch(query, prefix=""):
    try:
        res = search(to_utf8(query))
    except Exception as e:
        print e
        return u"Network Error"

    try:
        v = json.loads(res)
        typ = v["Type"]
        if typ == "D":
            topics = set()
            collect_topics(v, "RelatedTopics", topics)
            result = u"Did you mean %s" % orstr(sorted(topics))
            result = plugins.shorten(prefix + result, 350) + u"?"
        elif typ == "A" or typ == "E":
            result = v["AbstractText"]
            result = plugins.shorten(prefix + result, 350)
        else:
            if v["Answer"]:
                return plugins.shorten(prefix + v["Answer"], 350)

            print res
            result = prefix + u"I don't know what you mean."
    except Exception as e:
        print e
        return prefix + u"Parse Error"

    return result

class DuckDuckGoPlugin(StandardPlugin):
    """DuckDuckGo web search"""
    def __init__(self):
        StandardPlugin.__init__(self)
        self.parser.add_argument("query", nargs="+")

    def command(self, connection, event, extra, dbconn):
        query = " ".join(self.pargs.query)

        txt = u"\x0303[DuckDuckGo]\x03 "

        return ddgsearch(query, txt)

register_plugin(["duckduckgo", "ddg", "search"], DuckDuckGoPlugin())
