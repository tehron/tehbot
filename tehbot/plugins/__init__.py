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
from dateutil import relativedelta
from tehbot.impl import TehbotImpl

__all__ = ["Plugin", "Command", "StandardCommand", "ChannelHandler", "ChannelJoinHandler", "Poller", "Announcer", "PrefixHandler",
        "ThrowingArgumentParser", "PluginError"]

class ArgumentParserError(Exception):
    pass

class PluginError(Exception):
    pass

class ThrowingArgumentParser(argparse.ArgumentParser):
    def __init__(self, **kwargs):
        self.subparseractions = []
        self.help_msg = None
        argparse.ArgumentParser.__init__(self, **kwargs)

    def error(self, message):
        raise ArgumentParserError(message)

    def add_subparsers(self, **kwargs):
        sub = argparse.ArgumentParser.add_subparsers(self, **kwargs)
        self.subparseractions.append(sub)
        return sub

    def get_help_msg(self):
        if self.help_msg is not None:
            return self.help_msg

        for a in self.subparseractions:
            for p in a.choices.values():
                h = p.get_help_msg()
                if h is not None:
                    return h

        return None

    def print_help(self, file=None):
        self.help_msg = self.format_help()

    def parse_args(self, args=None, namespace=None, decode=True):
        self.help_msg = None
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
                "enabled" : inspect.getmodule(self).__name__ == "tehbot.plugins.core",
                "channel_enabled" : { }
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

    def convert_value(self, key, value):
        if key in ["enabled"]:
            v = Plugin.str2bool(value)
        else:
            v = value
        return v

    def set_value(self, args, dbconn):
        v = self.convert_value(args.key, args.value)
        self.settings[args.key] = v
        self.save(dbconn)

    def show_value(self, args, dbconn):
        v = self.settings[args.key]
        return '%s["%s"] = %s' % (self.__class__.__name__, args.key, v)

    def values_to_set(self):
        return ["enabled"]

    def integrate_parser(self, parseraction):
        p = parseraction.add_parser(self.__class__.__name__)
        self.parser_cmds = p.add_subparsers(title="commands", help="additional help")
        set_parser = self.parser_cmds.add_parser("set")
        show_parser = self.parser_cmds.add_parser("show")
        set_parser.add_argument("key", choices=self.values_to_set())
        set_parser.add_argument("value")
        set_parser.set_defaults(func=self.set_value)
        show_parser.add_argument("key", choices=self.values_to_set())
        show_parser.set_defaults(func=self.show_value)

    def is_enabled(self, ircid=None, channel=None):
        if not self.settings["enabled"]:
            return False
        if ircid is None or channel is None:
            return True
        return self.settings["channel_enabled"].get("%s:%s" % (ircid, channel), True)

    def is_privileged(self, extra):
        return extra["priv"]

    def is_authed(self, extra):
        return extra["auth"]

    def request_priv(self, extra):
        return [("nopriv", None)] if extra.has_key("auth_requested") else [("doauth", None)]

    def request_auth(self, extra):
        return [("noauth", None)] if extra.has_key("auth_requested") else [("doauth", None)]

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
    def shorten(msg, maxlen, post=""):
        plen = len(post)
        if len(msg) + plen <= maxlen:
            return msg + post

        if maxlen < 3:
            return "..." + post

        return msg[:maxlen - 3 - plen] + "..." + post

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

    @staticmethod
    def time2str(a, b, granularity=2):
        diff = relativedelta.relativedelta(datetime.datetime.fromtimestamp(a), datetime.datetime.fromtimestamp(b))
        avail = [ "years", "months", "weeks", "days", "hours", "minutes", "seconds" ]
        infos = []

        for what in avail:
            val = getattr(diff, what)
            if val != 0:
                w = what[:-1] if val == 1 else what
                infos.append("%d %s" % (val, w))

                if len(infos) == granularity:
                    break

        return ", ".join(infos) or "less than a second"

    @staticmethod
    def str2bool(s):
        return s.lower() in ("true", "yes", "t", "1")

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
            m = self.parser.get_help_msg()
            if m:
                return m.strip()
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
        return { "at" : 0, "where" : [] }

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

    def add_value(self, args, dbconn):
        arr = args.value.split(":")
        if len(arr) != 2 or not TehbotImpl.is_valid_id(arr[0]) or (not arr[1].startswith("#") and arr[1] != "__all__"):
            return "illegal value for %s: %s" % (args.key, args.value)
        if args.value in self.settings[args.key]:
            return "already added to %s: %s" (args.key, args.value)
        self.settings[args.key].append(args.value)
        self.save(dbconn)

    def remove_value(self, args, dbconn):
        arr = args.value.split(":")
        if len(arr) != 2 or not TehbotImpl.is_valid_id(arr[0]) or (not arr[1].startswith("#") and arr[1] != "__all__"):
            return "illegal value for %s: %s" % (args.key, args.value)
        if not args.value in self.settings[args.key]:
            return "not contained in %s: %s" (args.key, args.value)
        self.settings[args.key].remove(args.value)
        self.save(dbconn)

    def values_to_set(self):
        return Plugin.values_to_set(self) + ["at"]

    def convert_value(self, key, value):
        if key in ["at"]:
            v = int(value)
        else:
            v = Plugin.convert_value(self, key, value)
        return v

    def integrate_parser(self, parseraction):
        Plugin.integrate_parser(self, parseraction)
        add_parser = self.parser_cmds.add_parser("add")
        remove_parser = self.parser_cmds.add_parser("remove")
        add_parser.add_argument("key", choices=["where"])
        add_parser.add_argument("value")
        add_parser.set_defaults(func=self.add_value)
        remove_parser.add_argument("key", choices=["where"])
        remove_parser.add_argument("value")
        remove_parser.set_defaults(func=self.remove_value)

class Poller(Announcer):
    def default_settings(self):
        return { "timeout" : 10, "where" : [] }

    def timeout(self):
        return self.settings["timeout"]

    def next_at(self):
        at = time.time() + self.timeout()
        return at

    def values_to_set(self):
        return Announcer.values_to_set(self) + ["timeout"]

    def convert_value(self, key, value):
        if key in ["timeout"]:
            v = int(value)
        else:
            v = Announcer.convert_value(self, key, value)
        return v
