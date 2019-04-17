from tehbot.plugins import *
import threading
import time

class PrivPlugin(StandardCommand):
    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("-p", "--password", nargs=1)

    def commands(self):
        return "priv"

    def execute_parsed(self, connection, event, extra, dbconn):
        pw = vars(self.pargs)["password"]
        return [("reqpriv", pw)]

class ReloadPlugin(StandardCommand, PrivilegedPlugin):
    def __init__(self):
        StandardCommand.__init__(self)

    def commands(self):
        return "reload"

    def execute_parsed(self, connection, event, extra, dbconn):
        return [("reload", None)]

class QuitPlugin(StandardCommand, PrivilegedPlugin):
    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("msg", nargs="*")
        self.parser.add_argument("-r", "--restart", action="store_true")

    def commands(self):
        return "quit"

    def execute_parsed(self, connection, event, extra, dbconn):
        print "here QuitPlugin"
        msg = " ".join(self.pargs.msg)
        if self.pargs.restart:
            return [("restart", msg)]
        return [("quit", msg)]

class RawPlugin(StandardCommand, PrivilegedPlugin):
    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("args", nargs="+")

    def commands(self):
        return "raw"

    def execute_parsed(self, connection, event, extra, dbconn):
        args = self.pargs.args
        if args:
            connection.send_raw(u" ".join(args))

class HelpPlugin(StandardCommand):
    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("command", nargs="?")
        self.parser.add_argument("-a", "--list-all", action='store_true')

    def commands(self):
        return "help"

    def execute_parsed(self, connection, event, extra, dbconn):
        cmd = self.pargs.command
        return [("help", (cmd, self.pargs.list_all))]

class ConfigPlugin(StandardCommand, PrivilegedPlugin):
    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("args", nargs="*")

    def commands(self):
        return "config"

    def execute_parsed(self, connection, event, extra, dbconn):
        args = self.pargs.args
        return [("config", args)]

class PingPlugin(StandardCommand):
    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("-v", "--verbose", action="store_true")

    def commands(self):
        return "ping"

    def execute_parsed(self, connection, event, extra, dbconn):
        verbose = vars(self.pargs)["verbose"]

        if verbose:
            return u"pong from Thread %s at %f" % (threading.current_thread().name, time.time())

        return "pong!"
