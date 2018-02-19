from tehbot.plugins import *
import urllib2
import urllib
import lxml.html
import lxml.etree
import json

# patch XPath 2.0 function into XPath 1.0 API oO
etree_funcs = lxml.etree.FunctionNamespace(None)
etree_funcs["lower-case"] = lambda ctx, x: x[0].text_content().lower() if x else ""

url = "http://xkcd.com%s"

# http://stackoverflow.com/questions/6937525/escaping-xpath-literal-with-python
def toXPathStringLiteral(s):
    if "'" not in s: return "'%s'" % s
    if '"' not in s: return '"%s"' % s
    return "concat('%s')" % s.replace("'", "',\"'\",'")

class XkcdPlugin(Plugin):
    def __init__(self):
        Plugin.__init__(self)
        self.parser.add_argument("search_term", nargs="?")

    def execute(self, connection, event, extra, dbconn):
        self.parser.set_defaults(user=event.source.nick)

        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % str(e)

        txt = "\x0303[xkcd]\x03 "

        try:
            tree = lxml.html.parse(urllib2.urlopen(url % "/archive/"))
            res = [(e.text_content(), e.attrib["href"]) for e in tree.xpath("//a[contains(lower-case(.), %s)]" % toXPathStringLiteral(pargs.search_term))]

            if not res:
                txt += "No results."
            else:
                txt += ", ".join("%s (%s)" % (a, url % b) for a, b in res[:3])
        except:
            info = json.load(urllib2.urlopen(url % "/info.0.json"))
            p = "/%d/" % info["num"]
            txt += "%s - %s" % (url % p, info["safe_title"])

        return txt

register_plugin("xkcd", XkcdPlugin())
