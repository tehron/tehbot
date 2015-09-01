import plugins
import shlex
import importlib

path = "plugins.challenge"

sitemap = {
    "rev" : "revel",
    "revel" : "revel",
    "revolutionelite" : "revel",
    "hs" : "hs",
    "happy-security" : "hs",
    "happysecurity" : "hs",
    "happysec" : "hs"
}

parser = plugins.ThrowingArgumentParser(
    prog=stats.__name__,
    description=stats.__doc__)
parser.add_argument("user", nargs="?")
parser.add_argument("-s", "--site", choices=sorted(set(sitemap.values())))

def stats(connection, channel, nick, cmd, args):
    """Shows current stats for a user on a challenge site."""

    parser.set_defaults(user=nick, site=channel[1:])

    try:
        pargs = parser.parse_args(shlex.split(args or ""))
        if parser.help_requested:
            return plugins.say(connection, channel, parser.format_help().strip())
        user = pargs.user
        site = pargs.site.lower()
    except plugins.ArgumentParserError as e:
        return plugins.say(connection, channel, "Error: %s" % str(e))
    except (SystemExit, NameError, ValueError):
        return plugins.print_help(connection, channel, nick, None, cmd)

    if not sitemap.has_key(site):
        return plugins.say(connection, channel, "Unknown site: %s" % site)

    module = importlib.import_module("." + sitemap[site], path)
    globals()[module.__name__] = module
    plugins.say(connection, channel, module.stats(user))

plugins.register_pub_cmd("stats", stats)
