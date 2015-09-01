import plugins
import urllib2
import urllib
import lxml.html
import shlex
import json

parser = plugins.ThrowingArgumentParser(
    prog="wtf",
    description="Looks up definitions in Urban Dictionary")
parser.add_argument("search_term", nargs="+")
parser.add_argument("-n", "--nr", help="request definition number NR")

url = "http://api.urbandictionary.com/v0/define?%s"

def wtf(connection, channel, nick, cmd, args):
    index = 0

    try:
        pargs = parser.parse_args(shlex.split(args or ""))
        if parser.help_requested:
            return plugins.say(connection, channel, parser.format_help().strip())
        if pargs.nr:
            index = int(pargs.nr) - 1
    except plugins.ArgumentParserError as e:
        return plugins.say(connection, channel, "error: %s" % str(e))
    except (SystemExit, NameError, ValueError):
        return plugins.print_help(connection, channel, nick, None, cmd)

    page = index / 10 + 1
    index %= 10
    term = plugins.to_utf8(" ".join(pargs.search_term))

    data = {
        "page" : page,
        "term" : term
    }

    txt = "\x0303[Urban Dictionary]\x03 "
    req = urllib2.Request(url % urllib.urlencode(data))

    try:
        all_entries = json.load(urllib2.urlopen(req))["list"]
        count = 10 * (page - 1) + len(all_entries)
        entry = all_entries[index]

        txt += "%s (%d/%d)\n" % (term, index + 1, count)
        definition = "\n".join(entry["definition"].splitlines())
        txt += plugins.shorten(definition, 300)

        if entry.has_key("example"):
            example = "\n".join(entry["example"].splitlines())
            txt += "\n\x02Example:\x0f " + plugins.shorten(example, 300)
    except:
        return plugins.say(connection, channel, txt + "Definition not available.")

    plugins.say(connection, channel, txt)

plugins.register_pub_cmd("wtf", wtf)
plugins.register_pub_cmd("define", wtf)
