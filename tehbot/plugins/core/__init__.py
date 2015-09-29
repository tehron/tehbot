from tehbot.plugins import *
import irc.client

class ReloadPlugin(Plugin):
    def execute(self):
        res = self.tehbot.reload()
        if res is None:
            return "Okay"
        else:
            return "Error: %s" % res

register_op_cmd("reload", ReloadPlugin())

class QuitPlugin(Plugin):
    def execute(self):
        self.tehbot.quit(self.args)

register_op_cmd("quit", QuitPlugin())

class RawPlugin(Plugin):
    def execute(self):
        if self.args:
            self.connection.send_raw(self.args)

register_op_cmd("raw", RawPlugin())

class HelpPlugin(Plugin):
    def execute(self):
        if self.args:
            txt = "No help for '%s'" % self.args
            if self.tehbot.pub_cmd_handlers.has_key(self.args):
                p = self.tehbot.pub_cmd_handlers[self.args]
                if p.__doc__:
                    txt = p.__doc__
            elif self.tehbot.priv_cmd_handlers.has_key(self.args):
                p = self.tehbot.priv_cmd_handlers[self.args]
                if p.__doc__:
                    txt = p.__doc__
        else:
            txt = "Available commands: "
            if irc.client.is_channel(self.target):
                txt += ", ".join(sorted(self.tehbot.pub_cmd_handlers))
            else:
                txt += ", ".join(sorted(self.tehbot.priv_cmd_handlers))
        return txt

register_cmd("help", HelpPlugin())
