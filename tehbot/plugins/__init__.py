#from __future__ import absolute_import
import os, os.path
import traceback as sys_traceback
import time
import re
import threading
import argparse
import irc.client
import sqlite3
import shlex
import datetime
import json
import importlib
import inspect

__all__ = ["Plugin", "Command", "StandardCommand", "ChannelHandler", "ChannelJoinHandler", "Poller", "Announcer", "PrefixHandler"]

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
            args = Plugin.mysplit(args, decode)

        try:
            return argparse.ArgumentParser.parse_args(self, args, namespace)
        except SystemExit:
            pass

class Plugin:
    def __init__(self):
        self.pub_allowed = True
        self.priv_allowed = True

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

    def deinit(self, dbconn):
        pass

    def is_enabled(self):
        return self.settings["enabled"]

    def is_privileged(self, extra):
        return extra["priv"]

    def is_authed(self, extra):
        return extra["auth"]

    def request_priv(self, extra):
        return [("nopriv", None)] if extra.has_key("auth_requested") else [("doauth", None)]

    def request_auth(self, extra):
        return [("noauth", None)] if extra.has_key("auth_requested") else [("doauth", None)]

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

    @staticmethod
    def grouped(val):
        return "{:,}".format(val)

    @staticmethod
    def is_windows():
        return os.name == 'nt'

    @staticmethod
    def to_utf8(unistr):
        return unistr.encode("utf-8", "ignore")

    @staticmethod
    def from_utf8(_str):
        return _str.decode("utf-8")

    @staticmethod
    def to_latin1(unistr):
        return unistr.encode("latin1", "ignore")

    @staticmethod
    def myfilter(s):
        return "".join([c if ord(c) >= 0x20 else "?" for c in s])

    @staticmethod
    def mysplit(s, decode=True):
        res = shlex.split(Plugin.to_utf8(s))
        if decode:
            res = map(Plugin.from_utf8, res)
        return res

    @staticmethod
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

    @staticmethod
    def shorten(msg, maxlen):
        if len(msg) > maxlen:
            if maxlen < 3:
                return "..."
            return msg[:maxlen - 3] + "..."
        return msg

    @staticmethod
    def green(msg):
        return u"\x0303%s\x03" % msg

    @staticmethod
    def red(msg):
        return u"\x0304%s\x03" % msg

    @staticmethod
    def bold(msg):
        return u"\x02%s\x0f" % msg

    @staticmethod
    def exc2str(ex):
        cls = ex.__class__.__name__
        msg = unicode(ex)
        return u"%s: %s" % (cls, msg) if msg else cls

    @staticmethod
    def collect():
        path = os.path.dirname(__file__)
        modules = []

        for n in sorted(os.listdir(path)):
            if os.path.isdir("%s/%s" % (path, n)):
                m = n
            else:
                base, ext = os.path.splitext(n)
                if ext != ".py" or base == "__init__":
                    continue
                m = base

            p = importlib.import_module("tehbot.plugins.%s" % m)
            modules.append(p)

        return modules

class Command(Plugin):
    """This is where the help text goes."""

    def commands(self):
        return None

class StandardCommand(Command):
    def __init__(self):
        Command.__init__(self)
        cmd = self.commands()
        mcmd = cmd if isinstance(cmd, basestring) else cmd[0]
        self.parser = ThrowingArgumentParser(prog=mcmd, description=self.__doc__)

    def execute(self, connection, event, extra, dbconn):
        try:
            self.pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % Plugin.exc2str(e)

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

    def default_settings(self):
        return { "at" : 0, "where" : {} }

    def at(self):
        return self.settings["at"]

    def where(self):
        return self.settings["where"]

    def next_at(self):
        today = datetime.date.today()
        at = int(today.strftime("%s")) + self.at()
        if at < time.time():
            at += int(datetime.timedelta(days=1).total_seconds())
        return at

    def config(self, args, dbconn):
        if args[0] == "modify":
            if args[1] == "add" and args[2] == "where":
                network = args[3]
                channel = args[4]
                if not self.settings.has_key("where"):
                    self.settings["where"] = dict()
                if not self.settings["where"].has_key(network):
                    self.settings["where"][network] = []
                self.settings["where"][network].append(channel)
                self.save(dbconn)
                return "Okay"
            elif args[1] == "set" and args[2] in ["timeout", "at"]:
                self.settings[args[2]] = int(args[3])
                self.save(dbconn)
                return "Okay"

        return Plugin.config(self, args, dbconn)

class Poller(Announcer):
    def default_settings(self):
        return { "timeout" : 10, "where" : {} }

    def timeout(self):
        return self.settings["timeout"]

    def next_at(self):
        at = time.time() + self.timeout()
        return at
