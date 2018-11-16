from tehbot.plugins import *
from cowsay import cowsay

class CowSayPlugin(StandardPlugin):
    def __init__(self):
        StandardPlugin.__init__(self)
        self.parser.add_argument("msg", nargs=1)

    def execute(self, connection, event, extra, dbconn):
        if not self.privileged(connection, event):
            return self.request_priv(extra)

        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
            msg = pargs.msg[0]
        except Exception as e:
            return u"Error: %s" % str(e)

        return cowsay(msg)

register_plugin("cowsay", CowSayPlugin())
