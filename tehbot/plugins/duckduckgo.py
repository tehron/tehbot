from tehbot.plugins import *
import urllib.request, urllib.error, urllib.parse
import json
import re
import urllib.request, urllib.parse, urllib.error

class DuckDuckGoPlugin(StandardCommand):
    """DuckDuckGo web search"""

    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("query", nargs="+")

    def commands(self):
        return ["duckduckgo", "ddg", "search"]

    def execute_parsed(self, connection, event, extra):
        prefix = "[DuckDuckGo] "
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

        req = urllib.request.Request("https://api.duckduckgo.com/?%s" % urllib.parse.urlencode(params), headers=h)

        inp, res, misc = None, None, []

        try:
            fp = urllib.request.urlopen(req)
        except Exception as e:
            raise PluginError("Network error: %s" % str(e))

        try:
            v = json.load(fp)
        except:
            raise PluginError("JSON parse error")

        typ = v["Type"]
        if typ == "D":
            topics = set()
            DuckDuckGoPlugin.collect_topics(v, "RelatedTopics", topics)
            res = Plugin.shorten("Did you mean %s" % DuckDuckGoPlugin.orstr(sorted(topics)), 400, "?")
            misc = topics
        elif typ == "A" or typ == "E":
            res = v["AbstractText"]
            misc = res
        else:
            if v["Answer"]:
                res = v["Answer"]
                misc = res
            else:
                print(v)

        return (inp, res, misc)

    def result(self, what, prefix):
        try:
            inp, res, misc = self.query(what)
            if isinstance(misc, set):
                topics = DuckDuckGoPlugin.orstr(sorted(misc))
                txt = Plugin.shorten(Plugin.green(prefix) + "Did you mean " + topics, 450, "?")
            elif isinstance(misc, str):
                txt = Plugin.shorten(Plugin.green(prefix) + misc, 450)
            else:
                txt = Plugin.green(prefix) + "No results."
        except Exception as e:
            txt = Plugin.red(prefix) + str(e)

        return txt

    @staticmethod
    def orstr(lst):
        if not lst:
            return ""

        if len(lst) == 1:
            return lst[0]

        return ", ".join(lst[:-1]) + ", or %s" % lst[-1]

    @staticmethod
    def collect_topics(json, key, topics):
        for x in json[key]:
            if "Topics" in x:
                DuckDuckGoPlugin.collect_topics(x, "Topics", topics)
            elif "FirstURL" in x:
                url = x["FirstURL"]
                m = re.search(r'/?q=([^/]+)$', url)
                if m is not None:
                    top = m.group(1)
                else:
                    m = re.search(r'/([^/]+)$', url)
                    top = m.group(1).replace("_", " ")

                top = urllib.parse.unquote(str(top))
                topics.add('\x02%s\x0f' % top)
