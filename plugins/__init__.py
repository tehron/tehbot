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

pattern = r'[\x02\x0F\x16\x1D\x1F]|\x03(?:\d{1,2}(?:,\d{1,2})?)?'
regex = re.compile(pattern, re.UNICODE)

def print_help(connection, target, nick, cmd, args):
    if args:
        h = pub_cmd_handlers[args] if args in pub_cmd_handlers else priv_cmd_handlers[args] if args in priv_cmd_handlers[args] else None
        if h and h.__doc__:
                say(connection, target, "%s: %s" % (args, h.__doc__))
        else:
            print "no help for %s" % args
    else:
        say(connection, target, "Available commands:")
        if irc.client.is_channel(target):
            say(connection, target, ", ".join(sorted(pub_cmd_handlers)))
        else:
            say(connection, target, ", ".join(sorted(priv_cmd_handlers)))

operator_cmd_handlers = { }
pub_cmd_handlers = {
    "help" : print_help
}
priv_cmd_handlers = {
    "help" : print_help
}
channel_handlers = [ ]

def myprint(s):
    s = regex.sub("", s)
    print sys_time.strftime("%H:%M:%S"), s.encode(encoding, "backslashreplace")

def is_windows():
    return os.name == 'nt'

def to_utf8(unistr):
    return unistr.encode("utf-8", "ignore")

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

def register_op_cmd(cmd, fnc):
    if cmd in operator_cmd_handlers:
        myprint("Warning: Duplicate operator command \"%s\" defined!" % cmd)
    else:
        operator_cmd_handlers[cmd] = fnc

def register_pub_cmd(cmd, fnc):
    if cmd in pub_cmd_handlers:
        myprint("Warning: Duplicate public command \"%s\" defined!" % cmd)
    else:
        pub_cmd_handlers[cmd] = fnc

def register_priv_cmd(cmd, fnc):
    if cmd in priv_cmd_handlers:
        myprint("Warning: Duplicate private command \"%s\" defined!" % cmd)
    else:
        priv_cmd_handlers[cmd] = fnc

def register_cmd(cmd, fnc):
    register_pub_cmd(cmd, fnc)
    register_priv_cmd(cmd, fnc)

def register_channel_handler(fnc):
    channel_handlers.append(fnc)

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


_plugins = sorted([plugin for plugin in os.listdir("plugins") if os.path.isdir("plugins/%s" % plugin)])
print "plugins:", _plugins

_modules = [__import__("plugins." + p, fromlist=["*"], level=0) for p in _plugins]
#print "modules:", _modules
