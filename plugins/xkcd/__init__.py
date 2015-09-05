import plugins
import urllib2
import urllib
import lxml.html
import lxml.etree

# patch XPath 2.0 function into XPath 1.0 API oO
etree_funcs = lxml.etree.FunctionNamespace(None)
etree_funcs["lower-case"] = lambda ctx, x: x[0].text_content().lower() if x else ""

url = "http://xkcd.com%s"

# http://stackoverflow.com/questions/6937525/escaping-xpath-literal-with-python
def toXPathStringLiteral(s):
    if "'" not in s: return "'%s'" % s
    if '"' not in s: return '"%s"' % s
    return "concat('%s')" % s.replace("'", "',\"'\",'")

def xkcd(connection, channel, nick, cmd, args):
    if not args:
        return

    tree = lxml.html.parse(urllib2.urlopen(url % "/archive/"))
    res = [(e.text_content(), e.attrib["href"]) for e in tree.xpath("//a[contains(lower-case(.), %s)]" % toXPathStringLiteral(args))]
    txt = "\x0303[xkcd]\x03 "

    if not res:
        txt += "No results."
    else:
        txt += ", ".join("%s (%s)" % (a, url % b) for a, b in res[:3])

    plugins.say(connection, channel, txt)

plugins.register_cmd("xkcd", xkcd)
