from tehbot.plugins import *
import tehbot.plugins as plugins
import urllib2
import urllib
import lxml.html
import json
import re

class UrbanDictionaryPlugin(StandardCommand):
    """Looks up definitions in Urban Dictionary"""

    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("search_term", nargs="+")
        self.parser.add_argument("-n", "--nr", type=int, help="request definition number NR")

    def commands(self):
        return ["wtf", "define"]

    def execute_parsed(self, connection, event, extra, dbconn):
        url = "http://api.urbandictionary.com/v0/define?%s"

        index = (self.pargs.nr or 1) - 1
        page = index / 10 + 1
        index %= 10
        term = " ".join(self.pargs.search_term)

        data = {
            "page" : page,
            "term" : plugins.to_utf8(term)
        }

        prefix = "\x0303[Urban Dictionary]\x03 "
        req = urllib2.Request(url % urllib.urlencode(data))

        try:
            all_entries = json.load(urllib2.urlopen(req))["list"]
            count = 10 * (page - 1) + len(all_entries)
            entry = all_entries[index]

            txt = "%s (%d/%d)\n" % (term, index + 1, count)
            definition = "\n".join(entry["definition"].splitlines())
            definition = re.sub(r'\[([^\[]*)\]', "\x02\\1\x0f", definition)
            txt += plugins.shorten(definition, 300)

            if entry.has_key("example"):
                example = "\n".join(entry["example"].splitlines())
                example = re.sub(r'\[([^\[]*)\]', "\x02\\1\x0f", example)
                txt += "\n\x02Example:\x0f " + plugins.shorten(example, 300)
        except Exception as e:
            print e
            if term == "dloser":
                return prefix + "The unstabliest D-System ever!"
            return prefix + "Definition not available."

        return prefix + txt
