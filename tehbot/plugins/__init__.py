from __future__ import absolute_import
import os, os.path
import traceback as sys_traceback
import time as sys_time
import re
import locale
encoding = locale.getdefaultlocale()[1] or "ascii"
import threading
import argparse
import irc.client
import sqlite3
import shlex
import datetime
import json

__all__ = ["Plugin", "StandardPlugin", "CorePlugin", "ChannelHandler", "ChannelJoinHandler", "Poller", "Announcer", "register_plugin", "register_channel_handler", "register_channel_join_handler", "register_poller", "register_announcer", "from_utf8", "to_utf8"]

_tehbot = None
_modules = []

class ArgumentParserError(Exception):
    pass

class ThrowingArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ArgumentParserError(message)

    def print_help(self, file=None):
        self.help_requested = True

    def parse_args(self, args=None, namespace=None, decode=True):
        self.help_requested = False
        if isinstance(args, basestring):
            args = mysplit(args, decode)

        try:
            return argparse.ArgumentParser.parse_args(self, args, namespace)
        except SystemExit:
            pass

class Plugin:
    """This is where the help text goes."""

    def __init__(self):
        self.tehbot = _tehbot
        self.logtodb = True
        self.pub_allowed = True
        self.priv_allowed = True
        self.initialize(self.tehbot.dbconn)

    def handle(self, connection, event, extra, dbconn):
        if not self.settings["enabled"]:
            return

        if irc.client.is_channel(event.target):
            target = event.target
            if not self.pub_allowed:
                return
        else:
            target = event.source.nick
            if not self.priv_allowed:
                return

        res = self.execute(connection, event, extra, dbconn)
        if isinstance(res, basestring):
            res = [("say", res)]
        elif res is None:
            res = [("none",)]

        for r in res:
            if r[0] == "say" or r[0] == "me":
                globals()[r[0]](connection, target, r[1], dbconn if self.logtodb else None)
            elif r[0] == "nopriv":
                say(connection, target, u"%s is NOT privileged" % event.source.nick, dbconn if self.logtodb else None)
                break
            elif r[0] == "doauth":
                extra["request_priv_called"] = True

                params = self.tehbot.settings.connection_params(connection)
                for t, s in params["operators"]:
                    if t == "host" and s == event.source.host:
                        self.tehbot.privusers[connection].add(event.source.nick)
                        self.tehbot.mainqueue.put((self, (connection, event, extra)))
                        return

                self.tehbot.privqueue[connection, event.source.nick].put((self, (connection, event, extra)))
                connection.whois(event.source.nick)
                return

        self.finalize()

    def privileged(self, connection, event):
        return event.source.nick in self.tehbot.privusers[connection]

    def request_priv(self, extra):
        return [("nopriv",)] if extra.has_key("request_priv_called") else [("doauth",)]

    def priv_override(self, connection, event):
        self.tehbot.privusers[connection].add(event.source.nick)

    def default_settings(self):
        return { }

    def initialize(self, dbconn):
        self.settings = {
                "enabled" : isinstance(self, CorePlugin)
                }
        self.settings.update(self.default_settings())

        c = dbconn.execute("select value from Settings where key=?", (self.__class__.__name__, ))
        res = c.fetchone()
        stored_settings = { }
        if res is not None:
            stored_settings = json.loads(res[0])

        self.settings.update(stored_settings)

        if stored_settings != self.settings:
            self.save(dbconn)

    def finalize(self):
        pass

    def config(self, args, dbconn):
        if args[0] == "modify":
            if args[1] == "set":
                if args[2] == "enabled":
                    state = bool(args[3])
                    self.settings["enabled"] = state
                    self.save(dbconn)
                    return "Ok"
                else:
                    key = args[2]
                    value = args[3]
                    self.settings[key] = value
                    self.save(dbconn)
                    return "Ok"

    def save(self, dbconn):
        value = json.dumps(self.settings)
        with dbconn:
            dbconn.execute("insert or replace into Settings values(?, ?)", (self.__class__.__name__, value))

    """
    def valid_target(self, where):
        for network, channels in where:
            if network == self.connection.name and self.target in channels:
                return True
        return False

    def help(self, cmd):
        plugin = self.tehbot.cmd_handlers["help"]
        plugin.handle(self.connection, self.target, self.nick, "help", cmd, self.dbconn)
    """

class ChannelHandler(Plugin):
    pass

class ChannelJoinHandler(Plugin):
    pass

class StandardPlugin(Plugin):
    def __init__(self):
        Plugin.__init__(self)
        self.parser = ThrowingArgumentParser(description=self.__doc__)
        self.mainthreadonly = False

class CorePlugin(StandardPlugin):
    pass

class Announcer(Plugin):
    def __init__(self):
        Plugin.__init__(self)
        self.quit = False

    def callme(self):
        #myprint("%s called" % self.__class__.__name__)
        tgts = []
        if "__all__" in self.where():
            for name, params in settings.connections().items():
                tgts.append((name, params["channels"]))
        else:
            tgts = self.where()

        for network, channels in tgts.items():
            conn = self.tehbot._get_connection(network)
            if conn is None:
                continue

            self.tehbot.core.queue.put((self, (conn, None, {"channels":channels})))

    def schedule(self, at):
        if self.quit or not self.settings["enabled"]:
            return

        self.tehbot.core.reactor.scheduler.execute_at(at, self.callme)

    def handle(self, connection, event, extra, dbconn):
        try:
            msg = self.execute(connection, event, extra, dbconn)

            for t in extra["channels"]:
                say(connection, t, msg, dbconn)
        finally:
            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            at = int(tomorrow.strftime("%s")) + self.at()
            myprint("%s scheduled at %d" % (self.__class__.__name__, at))
            self.schedule(at)

class Poller(Announcer):
    def schedule(self, timeout):
        if self.quit or not self.settings["enabled"]:
            return

        self.tehbot.core.reactor.scheduler.execute_after(timeout, self.callme)

    def handle(self, connection, event, extra, dbconn):
        try:
            msg = self.execute(connection, event, extra, dbconn)

            for t in extra["channels"]:
                say(connection, t, msg, dbconn)
        finally:
            self.schedule(self.timeout())


pattern = r'[\x02\x0F\x16\x1D\x1F]|\x03(?:\d{1,2}(?:,\d{1,2})?)?'
regex = re.compile(pattern, re.UNICODE)

def myprint(s):
    s = regex.sub("", s)
    print sys_time.strftime("%H:%M:%S"), s.encode(encoding, "backslashreplace")

def logmsg(time, network, target, nick, msg, is_action, typ, dbconn=None):
    msg_clean = regex.sub("", msg)
    if is_action:
        s = "%s: %s: *%s %s" % (network, target, nick, msg_clean)
    else:
        s = "%s: %s: %s: %s" % (network, target, nick, msg_clean)

    print sys_time.strftime("%H:%M:%S", sys_time.localtime(time)), s.encode(encoding, "backslashreplace")

    if dbconn is not None:
        with dbconn:
            dbconn.execute("create table if not exists Messages(id integer primary key, ts datetime, server varchar, channel varchar, nick varchar, type integer, message varchar)")
            dbconn.execute("insert into Messages values(null, ?, ?, ?, ?, ?, ?)", (time, network, target, nick, typ, msg_clean))

def grouped(val):
    return "{:,}".format(val)

def is_windows():
    return os.name == 'nt'

def to_utf8(unistr):
    return unistr.encode("utf-8", "ignore")

def from_utf8(_str):
    return _str.decode("utf-8")

def to_latin1(unistr):
    return unistr.encode("latin1", "ignore")

def myfilter(s):
    return "".join([c if ord(c) >= 0x20 else "?" for c in s])

def mysplit(s, decode=True):
    res = shlex.split(to_utf8(s))
    if decode:
        res = map(from_utf8, res)
    return res

def say(connection, target, msg, dbconn):
    if not target or not msg: return
    if not connection.locks.has_key(target): connection.locks[target] = threading.Lock()
    with connection.locks[target]:
        for m in msg.split("\n"):
            m = m.replace("\r", "?");
            if m.strip():
                logmsg(sys_time.time(), connection.name, target, connection.get_nickname(), m, False, dbconn if irc.client.is_channel(target) else None)
                connection.privmsg(target, m)

def say_nick(connection, target, nick, msg, dbconn):
    if not target or not nick: return
    if not connection.locks.has_key(target): connection.locks[target] = threading.Lock()
    with connection.locks[target]:
        for m in msg.split("\n"):
            m = m.replace("\r", "?");
            if m.strip():
                m2 = "%s: %s" % (nick, m)
                logmsg(sys_time.time(), connection.name, target, connection.get_nickname(), m2, False, dbconn if irc.client.is_channel(target) else None)
                connection.privmsg(target, m2)

def me(connection, target, msg, dbconn):
    msg = msg.replace("\r", "?").replace("\n", "?")
    if not target or not msg: return
    if not connection.locks.has_key(target): connection.locks[target] = threading.Lock()
    with connection.locks[target]:
        logmsg(sys_time.time(), connection.name, target, connection.get_nickname(), msg, True, None)
        # b0rk for unicode
        #connection.action(target, msg)
        connection.privmsg(target, "\001ACTION " + msg + "\001")

def register_plugin(cmd, plugin):
    cmds = cmd if isinstance(cmd, list) else [cmd]
    plugin.parser.prog = cmds[0]
    for cmd in cmds:
        if cmd in _tehbot.cmd_handlers:
            myprint("Warning: Duplicate command \"%s\" defined!" % cmd)
        else:
            _tehbot.cmd_handlers[cmd] = plugin
            _tehbot.handlers.append(plugin)

def register_channel_handler(plugin):
    _tehbot.channel_handlers.append(plugin)
    _tehbot.handlers.append(plugin)

def register_channel_join_handler(plugin):
    _tehbot.channel_join_handlers.append(plugin)
    _tehbot.handlers.append(plugin)

def register_poller(plugin):
    _tehbot.pollers.append(plugin)
    _tehbot.handlers.append(plugin)

def register_announcer(plugin):
    _tehbot.announcers.append(plugin)
    _tehbot.handlers.append(plugin)

def split(s, mx=450):
    if len(s) <= mx:
        return s
    ret = []
    l = []
    for word in s.split():
        if len(word) > mx:
            word = [word[i:i+mx] for i in xrange(0, len(word), mx)]
            ret += word
        else:
            l.append(word)
            if len(" ".join(l)) > mx:
                ret.append(" ".join(l[:-1]))
                l = l[-1:]
    ret.append(" ".join(l))
    return "\n".join(ret)

def shorten(msg, maxlen):
    if len(msg) > maxlen:
        if maxlen < 3:
            return "..."
        return msg[:maxlen - 3] + "..."
    return msg

def collect():
    _path = os.path.dirname(__file__)
    _plugins = sorted(plugin for plugin in os.listdir(_path) if os.path.isdir("%s/%s" % (_path, plugin)))
    #print "plugins:", _plugins

    _modules = [__import__("%s.%s" % (__name__, p), fromlist=["*"], level=0) for p in _plugins]
    #print "modules:", _modules
