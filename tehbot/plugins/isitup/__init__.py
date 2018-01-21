from tehbot.plugins import *
import tehbot.plugins as plugins
from urlparse import urlparse
import httplib

class IsitupPlugin(Plugin):
    """Checks if a web server is up."""

    def __init__(self):
        Plugin.__init__(self)
        self.parser = plugins.ThrowingArgumentParser(
                prog="isitup",
                description=IsitupPlugin.__doc__
        )
        self.parser.add_argument("host", nargs="?", default="google.com")

    def execute(self):
        try:
            pargs = self.parser.parse_args(self.args)
            if self.parser.help_requested:
                return self.parser.format_help().strip()
            parts = urlparse(pargs.host)
        except Exception as e:
            return "Error: %s" % str(e)

        if parts.scheme:
            host = parts.netloc
            prot = parts.scheme
        else:
            host = parts.path
            prot = "http"

        if prot != "http" and prot != "https":
            return "Error: only scheme http and https supported"

        try:
            clazz = httplib.HTTPSConnection if prot == "https" else httplib.HTTPConnection
            conn = clazz(host, timeout=5)
            conn.request("HEAD", "/")
            res = conn.getresponse()
        except Exception as e:
            res = None

        prefix = "\x0303[Isitup]\x03 "
        msg = u"%s is \x0303up \U0001f44d\x03." if res else u"%s seems to be \x0304down \U0001f44e\x03."
        return prefix + msg % (prot + "://" + host)

register_cmd("isitup", IsitupPlugin())
