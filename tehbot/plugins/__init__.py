#from __future__ import absolute_import
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
import importlib
import inspect

__all__ = ["Plugin", "PrivilegedPlugin", "AuthedPlugin", "Command", "StandardCommand", "ChannelHandler", "ChannelJoinHandler", "Poller", "Announcer", "PrefixHandler",
    "from_utf8", "to_utf8", "green", "red", "bold", "exc2str"]

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
    def __init__(self):
        self.logtodb = True
        self.pub_allowed = True
        self.priv_allowed = True
        self.mainthreadonly = False

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

        if isinstance(self, PrivilegedPlugin) and not self.privileged(connection, event):
            res = self.request_priv(extra)
        elif isinstance(self, AuthedPlugin) and not self.authed(connection, event):
            res = self.request_auth(extra)
        else:
            res = self.execute(connection, event, extra, dbconn)

        if isinstance(res, basestring):
            res = [("say", res)]
        elif res is None:
            res = [("none",)]

        for r in res:
            if r[0] == "say" or r[0] == "me" or r[0] == "notice":
                globals()[r[0]](connection, target, r[1], dbconn if self.logtodb else None)
            elif r[0] == "say_nick":
                globals()[r[0]](connection, target, event.source.nick, r[1], dbconn if self.logtodb else None)
            elif r[0] == "nopriv":
                say(connection, target, u"%s is \x02not\x02 privileged" % event.source.nick, dbconn if self.logtodb else None)
                break
            elif r[0] == "noauth":
                say(connection, target, u"%s is \x02not\x02 authorized with Services" % event.source.nick, dbconn if self.logtodb else None)
                break
            elif r[0] == "doauth":
                extra["auth_requested"] = True

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

    def authed(self, connection, event):
        return event.source.nick in self.tehbot.authusers[connection]

    def request_priv(self, extra):
        return [("nopriv",)] if extra.has_key("auth_requested") else [("doauth",)]

    def request_auth(self, extra):
        return [("noauth",)] if extra.has_key("auth_requested") else [("doauth",)]

    def priv_override(self, connection, event):
        self.tehbot.privusers[connection].add(event.source.nick)

    def default_settings(self):
        return { }

    def initialize(self, dbconn):
        self.settings = {
                "enabled" : inspect.getmodule(self).__name__ == "tehbot.plugins.core"
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

    def postinit(self, dbconn):
        pass

    def deinit(self, dbconn):
        pass

    def finalize(self):
        pass

    def config(self, args, dbconn):
        if args[0] == "modify":
            if args[1] == "set":
                if args[2] == "enabled":
                    state = args[3].lower() == "true"
                    self.settings["enabled"] = state
                    self.save(dbconn)
                    return "Okay"
                else:
                    key = args[2]
                    value = args[3]
                    self.settings[key] = value
                    self.save(dbconn)
                    return "Okay"

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

class PrivilegedPlugin(Plugin):
    pass

class AuthedPlugin(Plugin):
    pass

class Command(Plugin):
    """This is where the help text goes."""

class StandardCommand(Command):
    def __init__(self):
        Command.__init__(self)
        self.parser = ThrowingArgumentParser(description=self.__doc__)

    def execute(self, connection, event, extra, dbconn):
        try:
            self.pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % exc2str(e)

        return self.execute_parsed(connection, event, extra, dbconn)

class ChannelHandler(Plugin):
    pass

class ChannelJoinHandler(Plugin):
    pass

class PrefixHandler(Plugin):
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
        if not self.settings["enabled"]:
            return

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
        if not self.settings["enabled"]:
            return

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

def logmsg(time, network, target, nick, msg, is_action, typ, dbconn):
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
    if irc.client.is_channel(target):
        typ = _tehbot.settings.log_type(connection.name, target)
    else:
        typ = 1
    with connection.locks[target]:
        for m in msg.split("\n"):
            m = m.replace("\r", "?");
            if m.strip():
                logmsg(sys_time.time(), connection.name, target, connection.get_nickname(), m, False, typ, dbconn)
                connection.privmsg(target, m)

def notice(connection, target, msg, dbconn):
    if not target or not msg: return
    if not connection.locks.has_key(target): connection.locks[target] = threading.Lock()
    if irc.client.is_channel(target):
        typ = _tehbot.settings.log_type(connection.name, target)
    else:
        typ = 1
    with connection.locks[target]:
        for m in msg.split("\n"):
            m = m.replace("\r", "?");
            if m.strip():
                logmsg(sys_time.time(), connection.name, target, connection.get_nickname(), m, False, typ, dbconn)
                connection.notice(target, m)

def say_nick(connection, target, nick, msg, dbconn):
    if not target or not nick: return
    if not connection.locks.has_key(target): connection.locks[target] = threading.Lock()
    if irc.client.is_channel(target):
        typ = _tehbot.settings.log_type(connection.name, target)
    else:
        typ = 1
    with connection.locks[target]:
        for m in msg.split("\n"):
            m = m.replace("\r", "?");
            if m.strip():
                m2 = "%s: %s" % (nick, m)
                logmsg(sys_time.time(), connection.name, target, connection.get_nickname(), m2, False, typ, dbconn)
                connection.privmsg(target, m2)

def me(connection, target, msg, dbconn):
    msg = msg.replace("\r", "?").replace("\n", "?")
    if not target or not msg: return
    if not connection.locks.has_key(target): connection.locks[target] = threading.Lock()
    if irc.client.is_channel(target):
        typ = _tehbot.settings.log_type(connection.name, target)
    else:
        typ = 1
    with connection.locks[target]:
        logmsg(sys_time.time(), connection.name, target, connection.get_nickname(), msg, True, typ, dbconn)
        # b0rk for unicode
        #connection.action(target, msg)
        connection.privmsg(target, "\001ACTION " + msg + "\001")

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

def green(msg):
    return u"\x0303%s\x03" % msg

def red(msg):
    return u"\x0304%s\x03" % msg

def bold(msg):
    return u"\x02%s\x0f" % msg

def exc2str(ex):
    cls = ex.__class__.__name__
    msg = unicode(ex)
    return u"%s: %s" % (cls, msg) if msg else cls

def collect():
    path = os.path.dirname(__file__)
    plugins = []

    for n in sorted(os.listdir(path)):
        if os.path.isdir("%s/%s" % (path, n)):
            m = n
        else:
            base, ext = os.path.splitext(n)
            if ext != ".py" or base == "__init__":
                continue
            m = base

        p = importlib.import_module("tehbot.plugins.%s" % m)
        plugins.append(p)

    return plugins
