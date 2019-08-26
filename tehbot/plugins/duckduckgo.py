from tehbot.plugins import *
import urllib2
import json
import re
import urllib

class DuckDuckGoPlugin(StandardCommand):
    """DuckDuckGo web search"""

    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("query", nargs="+")

    def commands(self):
        return ["duckduckgo", "ddg", "search"]

    def execute_parsed(self, connection, event, extra, dbconn):
        prefix = u"[DuckDuckGo] "
        return self.result(" ".join(self.pargs.query), prefix)

    def query(self, what):
        params = {
            "q" : Plugin.to_utf8(what),
            "format" : "json",
            "no_html" : 1
        }
        h = {
            "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:63.0) Gecko/20100101 Firefox/63.0"
        }

        req = urllib2.Request("https://api.duckduckgo.com/?%s" % urllib.urlencode(params), headers=h)

        inp, res, misc = None, None, []

        try:
            fp = urllib2.urlopen(req)
        except Exception as e:
            raise PluginError(u"Network error: %s" % unicode(e))

        try:
            v = json.load(fp)
        except:
            raise PluginError(u"JSON parse error")

        typ = v["Type"]
        if typ == "D":
            topics = set()
            DuckDuckGoPlugin.collect_topics(v, "RelatedTopics", topics)
            res = Plugin.shorten(u"Did you mean %s" % DuckDuckGoPlugin.orstr(sorted(topics)), 400, "?")
            misc = topics
        elif typ == "A" or typ == "E":
            res = v["AbstractText"]
            misc = res
        else:
            if v["Answer"]:
                res = v["Answer"]
                misc = res
            else:
                print v

        return (inp, res, misc)

    def result(self, what, prefix):
        try:
            inp, res, misc = self.query(what)
            if isinstance(misc, set):
                topics = DuckDuckGoPlugin.orstr(sorted(misc))
                txt = Plugin.shorten(Plugin.green(prefix) + u"Did you mean " + topics, 450, "?")
            elif isinstance(misc, basestring):
                txt = Plugin.shorten(Plugin.green(prefix) + misc, 450)
            else:
                txt = Plugin.green(prefix) + "No results."
        except Exception as e:
            txt = Plugin.red(prefix) + unicode(e)

        return txt

    @staticmethod
    def orstr(lst):
        if not lst:
            return u""

        if len(lst) == 1:
            return lst[0]

        return u", ".join(lst[:-1]) + u", or %s" % lst[-1]

    @staticmethod
    def collect_topics(json, key, topics):
        for x in json[key]:
            if x.has_key("Topics"):
                DuckDuckGoPlugin.collect_topics(x, "Topics", topics)
            elif x.has_key("FirstURL"):
                url = x["FirstURL"]
                m = re.search(r'/?q=([^/]+)$', url)
                if m is not None:
                    top = m.group(1)
                else:
                    m = re.search(r'/([^/]+)$', url)
                    top = m.group(1).replace("_", " ")

                top = Plugin.from_utf8(urllib.unquote(str(top)))
                topics.add(u'\x02%s\x0f' % top)
