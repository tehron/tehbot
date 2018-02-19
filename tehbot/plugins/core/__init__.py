from tehbot.plugins import *
import threading
import time

class ReloadPlugin(Plugin):
    def execute(self, connection, event, extra, dbconn):
        if not self.privileged(connection, event):
            return self.request_priv(extra)

        self.res = self.tehbot.core.reload()
        if self.res is None:
            return u"Okay, ready to crush ricer!"
        else:
            return u"Error: %s" % self.res

    def finalize(self):
        try:
            if self.res is None:
                self.tehbot.core.finalize()
        except:
            pass

register_plugin("reload", ReloadPlugin())

class QuitPlugin(Plugin):
    def execute(self, connection, event, extra, dbconn):
        if not self.privileged(connection, event):
            return self.request_priv(extra)

        self.tehbot.quit(extra["args"])

register_plugin("quit", QuitPlugin())

class RawPlugin(Plugin):
    def execute(self, connection, event, extra, dbconn):
        if not self.privileged(connection, event):
            return self.request_priv(extra)

        args = extra["args"]
        if args:
            connection.send_raw(args)

register_plugin("raw", RawPlugin())

class HelpPlugin(Plugin):
    def __init__(self):
        Plugin.__init__(self)
        self.parser.add_argument("command", nargs="?")

    def execute(self, connection, event, extra, dbconn):
        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % str(e)

        try:
            cmd = pargs.command
            txt = self.tehbot.cmd_handlers[cmd].parser.format_help().strip()
        except:
            txt = u"Available commands: "
            txt += u", ".join(sorted(self.tehbot.cmd_handlers))

        return txt

register_plugin("help", HelpPlugin())

class PingPlugin(Plugin):
    def __init__(self):
        Plugin.__init__(self)
        self.parser.add_argument("--verbose", "-v", action="store_true")

    def execute(self, connection, event, extra, dbconn):
        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
            verbose = vars(pargs)["verbose"]
        except Exception as e:
            return u"Error: %s" % str(e)

        if verbose:
            return u"pong from Thread %s at %f" % (threading.current_thread().name, time.time())

        return "pong!"

register_plugin("ping", PingPlugin())
