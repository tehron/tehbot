from tehbot.plugins import *
from cowsay import cowsay

class CowsayPlugin(PrivilegedPlugin):
    def __init__(self):
        PrivilegedPlugin.__init__(self)
        self.parser.add_argument("msg", nargs="+")

    def command(self, connection, event, extra, dbconn):
        return cowsay(" ".join(self.pargs.msg))

register_plugin("cowsay", CowsayPlugin())
