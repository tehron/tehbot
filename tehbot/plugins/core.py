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

        if pw is not None and pw[0] == self.tehbot.settings["privpassword"]:
            self.priv_override(connection, event)

        if not self.privileged(connection, event):
            return self.request_priv(extra)

        return "%s is privileged" % (event.source.nick)

class ReloadPlugin(StandardCommand, PrivilegedPlugin):
    def __init__(self):
        StandardCommand.__init__(self)
        self.mainthreadonly = True

    def commands(self):
        return "reload"

    def execute_parsed(self, connection, event, extra, dbconn):
        self.res = self.tehbot.reload()

        if self.res is None:
            return "Okay"
        
        mod, lineno, exc = self.res
        return u"Error in %s(%d): %s" % (mod, lineno, exc2str(exc))

    def finalize(self):
        try:
            if self.res is None:
                self.tehbot.finalize()
        except:
            pass

class QuitPlugin(StandardCommand, PrivilegedPlugin):
    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("msg", nargs="*")
        self.parser.add_argument("-r", "--restart", action="store_true")

    def commands(self):
        return "quit"

    def execute_parsed(self, connection, event, extra, dbconn):
        msg = " ".join(self.pargs.msg)
        if self.pargs.restart:
            self.tehbot.restart(msg)
        else:
            self.tehbot.quit(msg)

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

    def commands(self):
        return "help"

    def execute_parsed(self, connection, event, extra, dbconn):
        cmd = self.pargs.command

        try:
            txt = self.tehbot.cmd_handlers[cmd].parser.format_help().strip()
        except:
            txt = u"Available commands: "
            txt += u", ".join(sorted(self.tehbot.cmd_handlers))

        return txt

class ConfigPlugin(StandardCommand, PrivilegedPlugin):
    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("args", nargs="*")

    def commands(self):
        return "config"

    def execute_parsed(self, connection, event, extra, dbconn):
        args = self.pargs.args
        if not args:
            return "This should be the help :P"

        return self.tehbot.config(args[0], args[1:], dbconn)

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
