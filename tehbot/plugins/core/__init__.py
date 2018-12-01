from tehbot.plugins import *
import threading
import time

class PrivPlugin(CorePlugin):
    def __init__(self):
        CorePlugin.__init__(self)
        self.parser.add_argument("-p", "--password", nargs=1)

    def command(self, connection, event, extra, dbconn):
        pw = vars(self.pargs)["password"]

        if pw is not None and pw[0] == self.tehbot.settings["privpassword"]:
            self.priv_override(connection, event)

        if not self.privileged(connection, event):
            return self.request_priv(extra)

        return "%s is privileged" % (event.source.nick)

register_plugin("priv", PrivPlugin())

class ReloadPlugin(PrivilegedCorePlugin):
    def __init__(self):
        PrivilegedCorePlugin.__init__(self)
        self.mainthreadonly = True

    def command(self, connection, event, extra, dbconn):
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

register_plugin("reload", ReloadPlugin())

class QuitPlugin(PrivilegedCorePlugin):
    def __init__(self):
        PrivilegedCorePlugin.__init__(self)
        self.parser.add_argument("msg", nargs="*")
        self.parser.add_argument("-r", "--restart", action="store_true")

    def command(self, connection, event, extra, dbconn):
        msg = " ".join(self.pargs.msg)
        if self.pargs.restart:
            self.tehbot.restart(msg)
        else:
            self.tehbot.quit(msg)

register_plugin("quit", QuitPlugin())

class RawPlugin(PrivilegedCorePlugin):
    def command(self, connection, event, extra, dbconn):
        args = extra["args"]
        if args:
            connection.send_raw(args)

register_plugin("raw", RawPlugin())

class HelpPlugin(CorePlugin):
    def __init__(self):
        CorePlugin.__init__(self)
        self.parser.add_argument("command", nargs="?")

    def command(self, connection, event, extra, dbconn):
        cmd = self.pargs.command

        try:
            txt = self.tehbot.cmd_handlers[cmd].parser.format_help().strip()
        except:
            txt = u"Available commands: "
            txt += u", ".join(sorted(self.tehbot.cmd_handlers))

        return txt

register_plugin("help", HelpPlugin())

class ConfigPlugin(PrivilegedCorePlugin):
    def __init__(self):
        PrivilegedCorePlugin.__init__(self)
        self.parser.add_argument("args", nargs="*")

    def command(self, connection, event, extra, dbconn):
        args = self.pargs.args
        if not args:
            return "This should be the help :P"

        return self.tehbot.config(args[0], args[1:], dbconn)

register_plugin("config", ConfigPlugin())
