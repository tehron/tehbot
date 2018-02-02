from __future__ import absolute_import
import os, os.path
import traceback as sys_traceback
import time as sys_time
import re
import locale
_, encoding = locale.getdefaultlocale()
import threading
import argparse
import irc.client
import sqlite3
import shlex
import datetime
import tehbot.settings as settings

__all__ = ["Plugin", "ChannelHandler", "Poller", "Announcer", "register_cmd", "register_op_cmd", "register_pub_cmd", "register_priv_cmd", "register_channel_handler", "register_poller", "register_announcer"]

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
        if args == "" or isinstance(args, basestring):
            args = shlex.split(to_utf8(args))
            if decode:
                args = map(from_utf8, args)

        try:
            return argparse.ArgumentParser.parse_args(self, args, namespace)
        except SystemExit:
            pass

class Handler:
    def __init__(self):
        self.tehbot = _tehbot
        self.logtodb = True
        self._quit = False

    def finalize(self):
        pass

    def valid_target(self, where):
        for network, channels in where:
            if network == self.connection.name and self.target in channels:
                return True
        return False

    def help(self, cmd):
        plugin = self.tehbot.pub_cmd_handlers["help"]
        plugin.handle(self.connection, self.target, self.nick, "help", cmd, self.dbconn)

class ChannelHandler(Handler):
    def handle(self, connection, channel, nick, msg, dbconn):
        self.connection = connection
        self.target = channel
        self.nick = nick
        self.msg = msg
        self.dbconn = dbconn
        say(self.connection, self.target, self.execute(), self.dbconn if self.logtodb else None)

class ChannelJoinHandler(Handler):
    def handle(self, connection, channel, nick, dbconn):
        self.connection = connection
        self.target = channel
        self.nick = nick
        self.dbconn = dbconn
        say(self.connection, self.target, self.execute(), self.dbconn if self.logtodb else None)

class Plugin(Handler):
    def __init__(self):
        Handler.__init__(self)
        self.parser = ThrowingArgumentParser(description=self.__doc__)

    def handle(self, connection, target, nick, cmd, args, dbconn):
        self.connection = connection
        self.target = target
        self.nick = nick
        self.cmd = cmd
        self.args = args
        self.dbconn = dbconn
        self.parser.prog = cmd
        say(self.connection, self.target, self.execute(), self.dbconn if self.logtodb else None)
        self.finalize()

class Poller(Handler):
    def _callme(self):
        #myprint("%s called" % self.__class__.__name__)
        tgts = []
        if "__all__" in self.where():
            for name in settings.connections:
                params = settings.connections[name]
                tgts.append((name, params.channels))
        else:
            tgts = self.where()

        for network, channels in tgts:
            conn = self.tehbot._get_connection(network)
            if conn is None:
                continue

            self.tehbot.core.queue.put((self, (conn, channels)))

    def _schedule(self, timeout):
        if self._quit:
            return

        self.tehbot.core.reactor.scheduler.execute_after(timeout, self._callme)

    def handle(self, connection, targets, dbconn):
        self.connection = connection
        self.targets = targets
        self.dbconn = dbconn

        try:
            msg = self.execute()

            for t in self.targets:
                say(self.connection, t, msg, self.dbconn)
        finally:
            self._schedule(self.timeout())

class Announcer(Handler):
    def _callme(self):
        #myprint("%s called" % self.__class__.__name__)
        tgts = []
        if "__all__" in self.where():
            for name in settings.connections:
                params = settings.connections[name]
                tgts.append((name, params.channels))
        else:
            tgts = self.where()

        for network, channels in tgts:
            conn = self.tehbot._get_connection(network)
            if conn is None:
                continue

            self.tehbot.core.queue.put((self, (conn, channels)))

    def _schedule(self, at):
        if self._quit:
            return

        self.tehbot.core.reactor.scheduler.execute_at(at, self._callme)

    def handle(self, connection, targets, dbconn):
        self.connection = connection
        self.targets = targets
        self.dbconn = dbconn

        try:
            msg = self.execute()

            for t in self.targets:
                say(self.connection, t, msg, self.dbconn)
        finally:
            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            at = int(tomorrow.strftime("%s")) + self.at()
            myprint("%s scheduled at %d" % (self.__class__.__name__, at))
            self._schedule(at)


pattern = r'[\x02\x0F\x16\x1D\x1F]|\x03(?:\d{1,2}(?:,\d{1,2})?)?'
regex = re.compile(pattern, re.UNICODE)

def myprint(s):
    s = regex.sub("", s)
    print sys_time.strftime("%H:%M:%S"), s.encode(encoding, "backslashreplace")

def logmsg(time, network, target, nick, msg, is_action, dbconn=None):
    msg_clean = regex.sub("", msg)
    if is_action:
        s = "%s: %s: *%s %s" % (network, target, nick, msg_clean)
    else:
        s = "%s: %s: %s: %s" % (network, target, nick, msg_clean)

    print sys_time.strftime("%H:%M:%S", sys_time.localtime(time)), s.encode(encoding, "backslashreplace")

    if dbconn is not None:
        # create table Messages(id integer primary key, ts datetime, server varchar, channel varchar, nick varchar, message varchar)
        with dbconn:
            dbconn.execute("insert into Messages values(null, ?, ?, ?, ?, ?)", (time, network, target, nick, msg_clean))

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
        logmsg(sys_time.time(), connection.name, target, connection.get_nickname(), msg, True, dbconn if irc.client.is_channel(target) else None)
        # b0rk for unicode
        #connection.action(target, msg)
        connection.privmsg(target, "\001ACTION " + msg + "\001")

def register_op_cmd(cmd, plugin):
    if cmd in _tehbot.operator_cmd_handlers:
        myprint("Warning: Duplicate operator command \"%s\" defined!" % cmd)
    else:
        _tehbot.operator_cmd_handlers[cmd] = plugin

def register_pub_cmd(cmd, plugin):
    if cmd in _tehbot.pub_cmd_handlers:
        myprint("Warning: Duplicate public command \"%s\" defined!" % cmd)
    else:
        _tehbot.pub_cmd_handlers[cmd] = plugin

def register_priv_cmd(cmd, plugin):
    if cmd in _tehbot.priv_cmd_handlers:
        myprint("Warning: Duplicate private command \"%s\" defined!" % cmd)
    else:
        _tehbot.priv_cmd_handlers[cmd] = plugin

def register_cmd(cmd, plugin):
    register_pub_cmd(cmd, plugin)
    register_priv_cmd(cmd, plugin)

def register_channel_handler(plugin):
    _tehbot.channel_handlers.append(plugin)

def register_channel_join_handler(plugin):
    _tehbot.channel_join_handlers.append(plugin)

def register_poller(plugin):
    _tehbot.pollers.append(plugin)

def register_announcer(plugin):
    _tehbot.announcers.append(plugin)

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
