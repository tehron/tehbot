from tehbot.plugins import *

class DeathlistPlugin(StandardPlugin):
    def execute(self, connection, event, extra, dbconn):
        return "blanky"

register_plugin("deathlist", DeathlistPlugin())
