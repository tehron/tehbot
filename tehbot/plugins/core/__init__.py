from tehbot.plugins import *
import threading
import time

class PrivilegedPlugin(CorePlugin):
    def __init__(self):
        CorePlugin.__init__(self)
        self.parser.add_argument("--password", "-p", nargs=1)

    def execute(self, connection, event, extra, dbconn):
        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
            pw = vars(pargs)["password"]
        except Exception as e:
            return u"Error: %s" % unicode(e)

        if pw is not None and pw[0] == self.tehbot.settings["privpassword"]:
            self.priv_override(connection, event)

        if not self.privileged(connection, event):
            return self.request_priv(extra)

        return "%s is privileged" % (event.source.nick)

register_plugin("priv", PrivilegedPlugin())

class ReloadPlugin(CorePlugin):
    def __init__(self):
        CorePlugin.__init__(self)
        self.mainthreadonly = True

    def execute(self, connection, event, extra, dbconn):
        if not self.privileged(connection, event):
            return self.request_priv(extra)

        self.res = self.tehbot.reload()
        if self.res is None:
            return u"Okay"
        else:
            return u"Error: %s" % self.res

    def finalize(self):
        try:
            if self.res is None:
                self.tehbot.finalize()
        except:
            pass

register_plugin("reload", ReloadPlugin())

class QuitPlugin(CorePlugin):
    def execute(self, connection, event, extra, dbconn):
        if not self.privileged(connection, event):
            return self.request_priv(extra)

        self.tehbot.quit(extra["args"])

register_plugin("quit", QuitPlugin())

class RawPlugin(CorePlugin):
    def execute(self, connection, event, extra, dbconn):
        if not self.privileged(connection, event):
            return self.request_priv(extra)

        args = extra["args"]
        if args:
            connection.send_raw(args)

register_plugin("raw", RawPlugin())

class HelpPlugin(CorePlugin):
    def __init__(self):
        CorePlugin.__init__(self)
        self.parser.add_argument("command", nargs="?")

    def execute(self, connection, event, extra, dbconn):
        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % unicode(e)

        try:
            cmd = pargs.command
            txt = self.tehbot.cmd_handlers[cmd].parser.format_help().strip()
        except:
            txt = u"Available commands: "
            txt += u", ".join(sorted(self.tehbot.cmd_handlers))

        return txt

register_plugin("help", HelpPlugin())

class ConfigPlugin(CorePlugin):
    def __init__(self):
        CorePlugin.__init__(self)
        self.parser.add_argument("args", nargs="*")

    def execute(self, connection, event, extra, dbconn):
        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % unicode(e)

        if not self.privileged(connection, event):
            return self.request_priv(extra)

        args = pargs.args
        if not args:
            return "This should be the help :P"

        return self.tehbot.config(args[0], args[1:], dbconn)

register_plugin("config", ConfigPlugin())
