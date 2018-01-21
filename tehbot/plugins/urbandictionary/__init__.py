from tehbot.plugins import *
import tehbot.plugins as plugins
import urllib2
import urllib
import lxml.html
import shlex
import json

class UrbanDictionaryPlugin(Plugin):
    """Looks up definitions in Urban Dictionary"""

    def __init__(self):
        Plugin.__init__(self)
        self.parser = plugins.ThrowingArgumentParser(
            prog="wtf",
            description=UrbanDictionaryPlugin.__doc__
        )
        self.parser.add_argument("search_term", nargs="+")
        self.parser.add_argument("-n", "--nr", type=int, help="request definition number NR")

    def execute(self):
        try:
            pargs = self.parser.parse_args(shlex.split(plugins.to_utf8(self.args or "")))
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except plugins.ArgumentParserError as e:
            return "error: %s" % str(e)
        except (SystemExit, NameError, ValueError):
            return self.help(self.cmd)

        url = "http://api.urbandictionary.com/v0/define?%s"

        index = (pargs.nr or 1) - 1
        page = index / 10 + 1
        index %= 10
        term = " ".join(pargs.search_term)

        data = {
            "page" : page,
            "term" : term
        }

        prefix = "\x0303[Urban Dictionary]\x03 "
        req = urllib2.Request(url % urllib.urlencode(data))

        try:
            all_entries = json.load(urllib2.urlopen(req))["list"]
            count = 10 * (page - 1) + len(all_entries)
            entry = all_entries[index]

            txt = "%s (%d/%d)\n" % (term, index + 1, count)
            definition = "\n".join(entry["definition"].splitlines())
            txt += plugins.shorten(definition, 300)

            if entry.has_key("example"):
                example = "\n".join(entry["example"].splitlines())
                txt += "\n\x02Example:\x0f " + plugins.shorten(example, 300)
        except:
            if term == "dloser":
                return prefix + "The unstabliest D-System ever!"
            return prefix + "Definition not available."

        return prefix + txt

p = UrbanDictionaryPlugin()
register_cmd("wtf", p)
register_cmd("define", p)
