from tehbot.plugins import *

class DeathlistPlugin(Plugin):
    def execute(self):
        return "blanky"

register_cmd("deathlist", DeathlistPlugin())
