from tehbot.plugins import *
import threading
import time

class PrivPlugin(StandardCommand):
    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("-p", "--password", nargs=1)

    def commands(self):
        return "priv"

    def execute_parsed(self, connection, event, extra):
        pw = vars(self.pargs)["password"]
        return [("reqpriv", pw)]

class ReloadPlugin(StandardCommand):
    def commands(self):
        return "reload"

    def execute_parsed(self, connection, event, extra):
        if not self.is_privileged(extra):
            return self.request_priv(extra)

        return [("reload", None)]

class QuitPlugin(StandardCommand):
    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("msg", nargs="*")
        self.parser.add_argument("-r", "--restart", action="store_true")

    def commands(self):
        return "quit"

    def execute_parsed(self, connection, event, extra):
        if not self.is_privileged(extra):
            return self.request_priv(extra)

        msg = " ".join(self.pargs.msg)
        if self.pargs.restart:
            return [("restart", msg)]
        return [("quit", msg)]

class RawPlugin(StandardCommand):
    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("args", nargs="+")

    def commands(self):
        return "raw"

    def execute_parsed(self, connection, event, extra):
        if not self.is_privileged(extra):
            return self.request_priv(extra)

        args = self.pargs.args
        if args:
            connection.send_raw(" ".join(args))

class HelpPlugin(StandardCommand):
    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("command", nargs="?")
        self.parser.add_argument("-a", "--list-all", action='store_true')

    def commands(self):
        return "help"

    def execute_parsed(self, connection, event, extra):
        cmd = self.pargs.command
        return [("help", (cmd, self.pargs.list_all))]

class PluginsPlugin(StandardCommand):
    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("-a", "--list-all", action='store_true')

    def commands(self):
        return "plugins"

    def execute_parsed(self, connection, event, extra):
        if not self.is_privileged(extra):
            return self.request_priv(extra)

        list_all = self.pargs.list_all
        return [("plugins", (list_all,))]

class ConfigPlugin(Command):
    def __init__(self, db):
        Command.__init__(self, db)

    def commands(self):
        return "config"

    def execute(self, connection, event, extra):
        if not self.is_privileged(extra):
            return self.request_priv(extra)

        return [("config", extra["args"])]

class PingPlugin(StandardCommand):
    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("-v", "--verbose", action="store_true")

    def commands(self):
        return "ping"

    def execute_parsed(self, connection, event, extra):
        now = time.time()
        ts = extra["ts"]
        verbose = vars(self.pargs)["verbose"]

        if verbose:
            return "pong from Thread %s at %f (%.2fms)" % (threading.current_thread().name, now, (now - ts) * 1000.0)

        return "pong!"
