from tehbot.plugins import *
import irc.client

class ReloadPlugin(Plugin):
    def execute(self):
        self.res = self.tehbot.core.reload()
        if self.res is None:
            return "Okay, ready to crush ricer!"
        else:
            return "Error: %s" % self.res

    def finalize(self):
        if self.res is None:
            self.tehbot.core.finalize()

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

import threading
import time
class PingPlugin(Plugin):
    def __init__(self):
        Plugin.__init__(self)
        self.parser.add_argument("--verbose", "-v", action="store_true")

    def execute(self):
        try:
            pargs = self.parser.parse_args(self.args)
            verbose = vars(pargs)["verbose"]
        except Exception as e:
            return "Error: %s" % str(e)

        if verbose:
            return "pong from Thread %s at %f" % (threading.current_thread().name, time.time())

        return "pong!"

register_cmd("ping", PingPlugin())
