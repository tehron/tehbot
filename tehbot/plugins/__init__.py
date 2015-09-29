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

__all__ = ["Plugin", "ChannelHandler", "register_cmd", "register_op_cmd", "register_pub_cmd", "register_priv_cmd", "register_channel_handler"]

_tehbot = None
_modules = []

class ArgumentParserError(Exception):
    pass

class ThrowingArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ArgumentParserError(message)

    def print_help(self, file=None):
        self.help_requested = True

    def parse_args(self, args=None, namespace=None):
        self.help_requested = False
        try:
            return argparse.ArgumentParser.parse_args(self, args, namespace)
        except SystemExit:
            pass

class Handler:
    def __init__(self):
        self.tehbot = _tehbot

    def help(self, cmd):
        plugin = self.tehbot.pub_cmd_handlers["help"]
        plugin.handle(self.connection, self.target, self.nick, "help", cmd)

class ChannelHandler(Handler):
    def handle(self, connection, channel, nick, msg):
        self.connection = connection
        self.target = channel
        self.nick = nick
        self.msg = msg
        say(self.connection, self.target, self.execute())

class Plugin(Handler):
    def handle(self, connection, target, nick, cmd, args):
        self.connection = connection
        self.target = target
        self.nick = nick
        self.cmd = cmd
        self.args = args
        say(self.connection, self.target, self.execute())


pattern = r'[\x02\x0F\x16\x1D\x1F]|\x03(?:\d{1,2}(?:,\d{1,2})?)?'
regex = re.compile(pattern, re.UNICODE)

def myprint(s):
    s = regex.sub("", s)
    print sys_time.strftime("%H:%M:%S"), s.encode(encoding, "backslashreplace")

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

def say(connection, target, msg):
    if not target or not msg: return
    if not connection.locks.has_key(target): connection.locks[target] = threading.Lock()
    with connection.locks[target]:
        for m in msg.split("\n"):
            if m.strip():
                myprint("%s: %s: %s" % (target, connection.get_nickname(), m))
                connection.privmsg(target, m)

def say_nick(connection, target, nick, msg):
    if not target or not nick: return
    if not connection.locks.has_key(target): connection.locks[target] = threading.Lock()
    with connection.locks[target]:
        for m in msg.split("\n"):
            if m.strip():
                myprint("%s: %s: %s: %s" % (target, connection.get_nickname(), nick, m))
                connection.privmsg(target, "%s: %s" % (nick, m))

def me(connection, target, msg):
    if not target or not msg: return
    if not connection.locks.has_key(target): connection.locks[target] = threading.Lock()
    with connection.locks[target]:
        myprint("%s: *%s %s" % (target, connection.get_nickname(), msg))
        connection.action(target, msg)

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
