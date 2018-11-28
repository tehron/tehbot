from tehbot.plugins import *
import tehbot.plugins as plugins
import urllib2
import json
import re
import urllib

class DuckDuckGoPlugin(StandardPlugin):
    """DuckDuckGo web search"""
    def __init__(self):
        StandardPlugin.__init__(self)
        self.parser.add_argument("query", nargs="+")

    def search(self, query, useragent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:63.0) Gecko/20100101 Firefox/63.0"):
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

    def orstr(self, lst):
        if not lst:
            return u""

        if len(lst) == 1:
            return lst[0]

        return u", ".join(lst[:-1]) + u", or %s" % lst[-1]

    def collect_topics(self, json, key, topics):
        for x in json[key]:
            if x.has_key("Topics"):
                self.collect_topics(x, "Topics", topics)
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

    def execute(self, connection, event, extra, dbconn):
        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
            query = " ".join(pargs.query)
        except Exception as e:
            return u"Error: %s" % unicode(e)

        txt = u"\x0303[DuckDuckGo]\x03 "

        try:
            res = self.search(to_utf8(query))
        except Exception as e:
            print e
            return txt + u"Network Error"

        try:
            v = json.loads(res)
            typ = v["Type"]
            if typ == "D":
                topics = set()
                self.collect_topics(v, "RelatedTopics", topics)
                result = u"Did you mean %s" % self.orstr(sorted(topics))
                result = plugins.shorten(txt + result, 350) + u"?"
            elif typ == "A":
                result = v["AbstractText"]
                result = plugins.shorten(txt + result, 350)
            else:
                print res
                result = txt + u"I don't know what you mean."
        except Exception as e:
            print e
            return txt + u"Parse Error"

        return result

register_plugin(["duckduckgo", "ddg", "search"], DuckDuckGoPlugin())
