from tehbot.plugins import *

class DeathlistPlugin(Plugin):
    def execute(self, connection, event, extra, dbconn):
        return "blanky"

register_plugin("deathlist", DeathlistPlugin())
