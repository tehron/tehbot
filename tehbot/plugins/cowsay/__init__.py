from tehbot.plugins import *
from cowsay import cowsay

class CowSayPlugin(Plugin):
    def execute(self):
        if not self.args:
            return

        return cowsay(self.args)

register_op_cmd("cowsay", CowSayPlugin())
