from tehbot.plugins import *
from cowsay import cowsay

class CowsayPlugin(StandardCommand):
    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("msg", nargs="+")

    def commands(self):
        return "cowsay"

    def execute_parsed(self, connection, event, extra, dbconn):
        if not self.is_privileged(extra):
            return self.request_priv(extra)

        return cowsay(" ".join(self.pargs.msg))
