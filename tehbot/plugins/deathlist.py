from tehbot.plugins import *

class DeathlistPlugin(Command):
    def commands(self):
        return "deathlist"

    def execute(self, connection, event, extra):
        return "blanky"
