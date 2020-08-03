import irc.client
import irc.modes
from Queue import Queue, Empty
import traceback
import time
import re
import datetime
import functools
import threading
from pony.orm import Database, db_session, set_sql_debug
import model
from collections import *
import inspect

import os.path
from types import ModuleType

import ctypes
import shlex
import argparse
import pipes

import tehbot.plugins
from tehbot.plugins import *
import locale
encoding = locale.getdefaultlocale()[1] or "ascii"
import random
import socket

def _terminate_thread(thread):
    """Terminates a python thread from another thread.

    :param thread: a threading.Thread instance
    """
    if not thread.isAlive():
        return

    exc = ctypes.py_object(SystemExit)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread.ident), exc)
    if res == 0:
        raise ValueError("nonexistent thread id")
    elif res > 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread.ident, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")

def _gather(module, modules):
    if module in modules:
        return

    try:
        path = os.path.dirname(module.__file__)
    except:
        return

    if path.startswith(os.path.dirname(__file__)) and os.path.exists(path):
        modules.add(module)
        for attribute_name in dir(module):
            attribute = getattr(module, attribute_name)
            if type(attribute) is ModuleType:
                _gather(attribute, modules)


class ImplementationError(Exception):
    def __init__(self, clazz, what, pyfile):
        msg = "%s has no attribute '%s' in %s" % (clazz.__name__, what, pyfile)
        Exception.__init__(self, msg)

class SocketFactory:
    family = socket.AF_INET

    def identity(x):
            return x

    def __init__(self, bind_address=None, wrapper=identity, ipv6=False, connect_timeout=10):
        self.bind_address = bind_address
        self.wrapper = wrapper
        if ipv6:
            self.family = socket.AF_INET6
        self.connect_timeout = connect_timeout

    def connect(self, server_address):
        sock = self.wrapper(socket.socket(self.family, socket.SOCK_STREAM))
        self.bind_address and sock.bind(self.bind_address)
        sock.settimeout(self.connect_timeout)
        try:
            sock.connect(server_address)
        except Exception as e:
            raise e
        finally:
            sock.settimeout(None)
        return sock
    __call__ = connect

class TehbotImpl:
    def __init__(self, tehbot):
        self.core = tehbot
        self.dispatcher = Dispatcher(self)
        self.plugins = []
        self.cmd_handlers = {}
        self.channel_handlers = []
        self.channel_join_handlers = []
        self.pollers = []
        self.announcers = []
        self.prefix_handlers = []
        self.queue = Queue(maxsize=0)
        self.actionqueue = Queue()
        self.logqueue = Queue()
        self.stop_logthread = False
        self.logthread = threading.Thread(target=self._logger)
        self.workers = []
        self.stop_workers = False
        self.quit_called = False
        self.restart_called = False
        self.db = Database()
        model.define_entities(self.db)
        self.privusers = defaultdict(set)
        self.authusers = defaultdict(set)
        self.privqueue = defaultdict(Queue)
        pattern = r'[\x02\x0F\x16\x1D\x1F]|\x03(?:\d{1,2}(?:,\d{1,2})?)?'
        self.regex = re.compile(pattern, re.UNICODE)

    def default_settings(self):
        return {
                "botname" : "tehbot",
                "username" : "tehbot",
                "ircname" : "tehbot",
                "cmdprefix" : "?",
                "privpassword" : None,
                "nr_worker_threads" : 10,
                "connections" : { }
        }

    @db_session
    def set_setting(self, key, value):
        self.settings[key] = value
        self.save_settings()

    @db_session
    def save_settings(self):
        self.db.Setting.get(name="tehbot").value = self.settings

    def postinit(self):
        self.db.bind(provider='sqlite', filename="../data/tehbot_ponyorm.sqlite", create_db=True)
        self.db.generate_mapping(create_tables=True)
        set_sql_debug(False)

        self.settings = self.default_settings()

        with db_session:
            s = self.db.Setting.get(name="tehbot")

            if s is None:
                s = self.db.Setting(name="tehbot", value=self.settings)

            self.settings.update(s.value)
            self.save_settings()

        for p in self.plugins:
            p.init()

        self.core.reactor.add_global_handler("all_events", self.dispatcher.dispatch, -10)

        for p in self.pollers + self.announcers:
            self.schedule(p)

        self.logthread.start()
        self.start_workers()

    def schedule(self, p):
        def callme():
            self.queue.put((p, (None, None, None)))

        at = p.next_at()
        #self.myprint("Scheduling %s at %s" % (p.__class__.__name__, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(at))))
        self.core.reactor.scheduler.execute_at(at, callme)

    def deinit(self):
        self.core.reactor.remove_global_handler("all_events", self.dispatcher.dispatch)

        for h in self.pollers + self.announcers:
            h.quit = True

        with self.core.reactor.mutex:
            for cmd in self.core.reactor.scheduler.queue[:]:
                try:
                    if cmd.target.func_name == "callme":
                        self.core.reactor.scheduler.queue.remove(cmd)
                except:
                    pass

        for p in self.plugins:
            p.deinit()

        self.stop_workers = True
        self.stop_logthread = True

    def pick(self, connection, what):
        params = self.settings["connections"][connection.tehbot.ircid]
        v = params.get(what)
        return v if v else self.settings[what]

    def connection_name(self, conn):
        return self.settings["connections"][conn.tehbot.ircid].get("name", conn.tehbot.ircid)

    def channel_options(self, connection, channel):
        return self.settings["connections"][connection.tehbot.ircid]["channel_options"].get(channel, { })

    def myprint(self, s):
        s = self.regex.sub("", s)
        print time.strftime("%H:%M:%S"), s.encode(encoding, "backslashreplace")

    def logmsg(self, when, event, typ, ircid, network, target, nick, msg):
        msg = self.regex.sub("", msg)
        if nick is None:
            s = msg
        else:
            if event == "action":
                s = "*%s %s" % (nick, msg)
            else:
                s = "%s: %s" % (nick, msg)

        ts = time.strftime("%H:%M:%S", time.localtime(when))
        if target is None:
            s = "%s %s: %s" % (ts, network, s)
        else:
            s = "%s %s: %s: %s" % (ts, network, target, s)
        print s.encode(encoding, "backslashreplace")
        self.logqueue.put((datetime.datetime.fromtimestamp(when), event, typ, ircid, target, nick, msg))

    def load_plugins(self, modules):
        for p in modules:
            for name, clazz in inspect.getmembers(p, lambda x: inspect.isclass(x) and issubclass(x, tehbot.plugins.Plugin) and x.__module__ == p.__name__):
                o = clazz(self.db)
                o.create_entities()

                if isinstance(o, tehbot.plugins.Command):
                    try:
                        cmds = o.commands()
                    except AttributeError as e:
                        raise ImplementationError(clazz, "commands", p.__file__)

                    if isinstance(cmds, basestring):
                        cmds = [cmds]
                    for cmd in cmds:
                        if cmd in self.cmd_handlers:
                            self.myprint('Warning: Duplicate command "%s" defined (class %s)!' % (cmd, name))
                        else:
                            self.cmd_handlers[cmd] = o
                elif isinstance(o, tehbot.plugins.ChannelHandler):
                    self.channel_handlers.append(o)
                elif isinstance(o, tehbot.plugins.ChannelJoinHandler):
                    self.channel_join_handlers.append(o)
                elif isinstance(o, tehbot.plugins.Poller):
                    self.pollers.append(o)
                elif isinstance(o, tehbot.plugins.Announcer):
                    self.announcers.append(o)
                elif isinstance(o, tehbot.plugins.PrefixHandler):
                    self.prefix_handlers.append(o)
                else:
                    continue

                self.plugins.append(o)

        print " command handlers:", sorted(self.cmd_handlers)
        print " channel handlers:", sorted(h.__class__.__name__ for h in self.channel_handlers)
        print "chn join handlers:", sorted(h.__class__.__name__ for h in self.channel_join_handlers)
        print "          pollers:", sorted(h.__class__.__name__ for h in self.pollers)
        print "       announcers:", sorted(h.__class__.__name__ for h in self.announcers)
        print "   prefix handlers", sorted(h.__class__.__name__ for h in self.prefix_handlers)

    def gather_modules(self):
        modules = set(tehbot.plugins.Plugin.collect())
        _gather(tehbot.plugins, modules)
        modules.remove(tehbot.plugins)
        return modules

    def exec_plugin(self, plugin, connection, event, extra):
        if not plugin.is_enabled():
            return

        if event:
            if irc.client.is_channel(event.target):
                if not plugin.pub_allowed:
                    return
                if not plugin.is_enabled(connection.tehbot.ircid, event.target):
                    return
            else:
                if not plugin.priv_allowed:
                    return

            extra["priv"] = event.source.nick in self.privusers[connection]
            extra["auth"] = event.source.nick in self.authusers[connection]

        res = plugin.execute(connection, event, extra)
        return res

    def priv_override(self, connection, event):
        self.privusers[connection].add(event.source.nick)

    def privileged(self, connection, event):
        return event.source.nick in self.privusers[connection]

    def _logger(self):
        while True:
            try:
                when, event, typ, ircid, target, nick, msg = self.logqueue.get(timeout=0.1)
                with db_session:
                    self.db.Message(ts=when, event=event, type=typ, ircid=ircid, target=target, nick=nick, message=msg)
                self.logqueue.task_done()
            except Empty:
                pass
            except:
                self.core.print_exc()

            if self.stop_logthread:
                break

    def _process(self):
        while True:
            if self.stop_workers:
                break

            try:
                plugin, args = self.queue.get(timeout=0.1)
            except Empty:
                continue

            connection, event, extra = args

            try:
                res = self.exec_plugin(plugin, connection, event, extra)
            except:
                res = None
                self.core.print_exc()

            self.actionqueue.put((res, plugin, connection, event, extra))
            self.queue.task_done()

    def start_workers(self):
        while len(self.workers) < self.settings["nr_worker_threads"]:
            worker = threading.Thread(name="WorkerThread-%d" % len(self.workers), target=self._process)
            self.workers.append(worker)
            worker.start()

    def __kill_workers(self):
        while self.workers:
            _terminate_thread(self.workers.pop())

    def _get_connection(self, name):
        for c in self.core.reactor.connections:
            if c.tehbot.ircid == name:
                return c
        return None

    def _get_plugin(self, pname):
        for p in self.plugins:
            name = p.__class__.__name__
            if name.endswith(pname):
                return p

        return None

    def connect(self):
        conns = self.settings["connections"]

        for ircid in conns:
            conn = self._get_connection(ircid)

            if not conns[ircid].get("enabled", True):
                if conn is not None:
                    conn.disconnect("Network has been disabled")
                continue

            if conn is None:
                conn = self.core.reactor.server()
                conn.tehbot = lambda: None
                conn.tehbot.ircid = ircid

                print "Connecting to %s" % self.connection_name(conn)
                self.reconnect(conn)
            elif conn.is_connected():
                self.dispatcher.join_channels(conn)

    def reconnect(self, connection):
        params = self.settings["connections"][connection.tehbot.ircid]

        if not params.get("enabled", True):
            self.myprint("%s: giving up reconnect attempt: network has been disabled" % self.connection_name(connection))
            return

        connection.tehbot.channels = set()
        connection.tehbot.users = dict()

        if params["ssl"]:
            import ssl
            factory = SocketFactory(connect_timeout=3, wrapper=ssl.wrap_socket)
        else:
            factory = SocketFactory(connect_timeout=3)

        botname = self.pick(connection, "botname")
        username = self.pick(connection, "username")
        ircname = self.pick(connection, "ircname")
        nickservpw = params.get("password")

        try:
            connection.connect(params["host"], params["port"], botname, nickservpw, username, ircname, factory)
        except irc.client.ServerConnectionError as e:
            self.dispatcher.on_disconnect(connection, None)
            return

        connection.set_rate_limit(2)
        connection.set_keepalive(60)

    def say(self, connection, target, typ, msg):
        self.ircsend("privmsg", connection, target, typ, None, msg)

    def notice(self, connection, target, typ, msg):
        self.ircsend("notice", connection, target, typ, None, msg)

    def say_nick(self, connection, target, typ, nick, msg):
        self.ircsend("privmsg", connection, target, typ, nick, msg)

    def me(self, connection, target, typ, msg):
        msg = msg.replace("\r", "?").replace("\n", "?")
        self.ircsend("action", connection, target, typ, None, msg)

    def ircsend(self, event, connection, target, typ, nick, msg):
        if not target or not msg:
            return

        for m in msg.split("\n"):
            m = m.replace("\r", "?");
            if not m.strip():
                continue
            m2 = "%s: %s" % (nick, m) if nick else m
            for msplit in tehbot.plugins.Plugin.split(m2).split("\n"):
                getattr(connection, event)(target, msplit)
                self.logmsg(time.time(), event, typ, connection.tehbot.ircid, self.connection_name(connection), target, connection.get_nickname(), msplit)

    def process_once(self, timeout):
        self.core.reactor.process_once(timeout)

        while True:
            try:
                actions, plugin, connection, event, extra = self.actionqueue.get(timeout=0.1)
            except Empty:
                break

            try:
                self.process_actions(actions, plugin, connection, event, extra)
            finally:
                try:
                    if isinstance(plugin, tehbot.plugins.Announcer):
                        self.schedule(plugin)
                except:
                    self.core.print_exc()

                self.actionqueue.task_done()

    def process_actions(self, actions, plugin, connection, event, extra):
        if event is None:
            target = None
            typ = 0
        elif irc.client.is_channel(event.target):
            target = event.target
            typ = 0 if self.channel_options(connection, event.target).get("logging", True) else 2
        else:
            target = event.source.nick
            typ = 1

        if isinstance(actions, basestring):
            actions = [("say", actions)]
        elif actions is None:
            actions = [("none", None)]

        for action, args in actions:
            try:
                if action == "say" or action == "me":
                    msg = args
                    getattr(self, action)(connection, target, typ, msg)
                elif action == "notice":
                    target, msg = args
                    self.notice(connection, target, typ, msg)
                elif action == "say_nolog":
                    msg = args
                    self.say(connection, target, 2, msg)
                elif action == "say_nick":
                    nick, msg = args
                    self.say_nick(connection, target, nick, typ, msg)
                elif action == "nopriv":
                    self.say(connection, target, typ, u"%s is \x02not\x02 privileged" % event.source.nick)
                    break
                elif action == "noauth":
                    self.say(connection, target, typ, u"%s is \x02not\x02 authorized with Services" % event.source.nick)
                    break
                elif action == "doauth":
                    extra["auth_requested"] = True

                    params = self.settings["connections"][connection.tehbot.ircid]
                    for t, s in params["operators"]:
                        if t == "host" and s == event.source.host:
                            self.privusers[connection].add(event.source.nick)
                            self.queue.put((plugin, (connection, event, extra)))
                            return

                    self.privqueue[connection, event.source.nick].put((plugin, (connection, event, extra)))
                    connection.whois(event.source.nick)
                elif action == "quit":
                    self.quit(args)
                elif action == "restart":
                    self.restart(args)
                elif action == "help":
                    cmd, list_all = args
                    if cmd is None:
                        def cmd(p):
                            c = p.commands()
                            return c if isinstance(c, basestring) else "%s (%s)" % (c[0], ", ".join(c[1:]))
                        enabled_cmds = sorted(cmd(p) for p in self.plugins if isinstance(p, tehbot.plugins.Command) and (list_all or p.is_enabled()))
                        msg = "Available commands: %s" % ", ".join(enabled_cmds)
                    else:
                        if self.cmd_handlers.has_key(cmd):
                            msg = self.cmd_handlers[cmd].parser.format_help().strip()
                        else:
                            msg = "Unknown command: %s" % cmd
                    self.say(connection, target, typ, msg)
                elif action == "reload":
                    try:
                        res = self.reload()

                        if res is None:
                            msg = "Okay"
                        else:
                            mod, lineno, exc = res
                            msg = u"Error in %s(%d): %s" % (mod, lineno, tehbot.plugins.Plugin.exc2str(exc))

                        self.say(connection, target, typ, msg)
                    finally:
                        self.finalize()
                elif action == "config":
                    msg = self.config(args)
                    self.say(connection, target, typ, msg)
                elif action == "reqpriv":
                    pw = args
                    if pw is not None and pw[0] == self.settings["privpassword"]:
                        self.priv_override(connection, event)
                    elif not self.privileged(connection, event) and not extra.has_key("auth_requested"):
                        self.actionqueue.put(([("doauth", None)], plugin, connection, event, extra))
                        return

                    priv = "" if self.privileged(connection, event) else " \x02not\x02"
                    self.say(connection, target, typ, "%s is%s privileged" % (event.source.nick, priv))
                elif action == "solvers":
                    site, chall, numeric, user = args

                    p = self._get_plugin("SolversPlugin")
                    if p is None:
                        return

                    cmd = "solvers"
                    newargs = ""
                    newargs = '-u %s %s' % (user, pipes.quote(chall))
                    if site is not None:
                        newargs = newargs + " -s %s" % pipes.quote(site)
                    self.queue.put((p, (connection, event, {"msg":"", "cmd":cmd, "args":newargs})))
                elif action == "plugins":
                    list_all, = args
                    pre = "Loaded Plugins" if list_all else "Enabled Plugins"
                    pl = []
                    for p in self.plugins:
                        name = p.__class__.__name__
                        if list_all:
                            pl.append(name + ("[x]" if p.is_enabled() else "[ ]"))
                        elif p.is_enabled():
                            pl.append(name)
                    msg = "%s: %s" % (pre, ", ".join(sorted(pl)))
                    self.say(connection, target, typ, msg)
                elif action == "announce":
                    targets, msg = args

                    tgts = []
                    conns = self.core.reactor.connections
                    for t in targets:
                        ircid, ch = t.split(":")
                        for conn in conns:
                            if conn.tehbot.ircid == ircid:
                                tgts.append((conn, ch))

                    for conn, channel in tgts:
                        self.say(conn, channel, typ, msg)
                elif action == "mode":
                    conn, channel, modes = args
                    conn.mode(channel, modes)
                elif action == "extquery":
                    plugin_name, what, maxlen = args

                    p = self._get_plugin(plugin_name)
                    if p is None:
                        return

                    msg = "Hm, I don't know."

                    try:
                        inp, res, misc = p.query(what)
                        print inp
                        if res:
                            msg = res
                    except:
                        pass

                    self.say(connection, target, typ, Plugin.shorten(msg, maxlen))
            except:
                self.core.print_exc()

    def quit(self, msg=None):
        print "quit called"
        self.deinit()
        self.quit_called = True
        self.core.reactor.disconnect_all(msg or "bye-bye")

    def restart(self, msg=None):
        print "restart called"
        self.deinit()
        self.quit_called = True
        self.restart_called = True
        self.core.reactor.disconnect_all(msg or "I'll be back!")

    def reload(self):
        return self.core.reload()

    def finalize(self):
        self.core.finalize()
        self.connect()

    def kbd_reload(self, args):
        self.reload()
        self.finalize()

    def kbd_quit(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument("msg", nargs="*")
        parser.add_argument("-r", "--restart", action="store_true")
        pargs = parser.parse_args(shlex.split(args or ""))

        msg = " ".join(pargs.msg)
        if pargs.restart:
            self.restart(msg)
        else:
            self.quit(msg)

    def kbd_stats(self, args):
        print "Connections"
        for c in self.core.reactor.connections:
            print " * %s: %s" % (self.connection_name(c), "connected" if c.is_connected() else "not connected")

        print "Delayed Commands"
        for c in self.core.reactor.scheduler.queue:
            print " * %s at %s" % (c.target.func if isinstance(c.target, functools.partial) else c.target, c)

        print "Privileged Users"
        for c, nicks in self.privusers.items():
            print " * %s: %r" % (self.connection_name(c), sorted(nicks))

    def kbd_users(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument("ircid")
        parser.add_argument("channel")
        pargs = parser.parse_args(shlex.split(args or ""))

        try:
            conn = [c for c in self.core.reactor.connections if c.tehbot.ircid == pargs.ircid][0]
        except:
            print "No such connection:", pargs.ircid
            return

        try:
            users = conn.tehbot.users[pargs.channel]
        except:
            print "No such channel:", pargs.channel
            return

        print ", ".join(sorted(a for a, b in users))

    def kbd_config(self, args):
        arr = shlex.split(args or "")
        print self.config(arr)

    @staticmethod
    def valid_id(ircid):
        if re.search(r'''[a-zA-Z][a-zA-Z0-9_]*''', ircid) is None:
            raise argparse.ArgumentTypeError("Illegal ircid! (doesn't match [a-z][a-z0-9_]*')")
        return ircid

    @staticmethod
    def is_valid_id(ircid):
        try:
            TehbotImpl.valid_id(ircid)
        except argparse.ArgumentTypeError:
            return False
        return True

    def set_value(self, args):
        self.set_setting(args.key, args.value)

    def unset_value(self, args):
        if args.key not in ["privpassword"]:
            return "unsetting %s not allowed" % args.key
        self.set_setting(args.key, None)

    def show_value(self, args):
        v = self.settings[args.key]
        if v is not None and args.key == "privpassword":
            v = len(v) * "*"
        return 'tehbot["%s"] = %s' % (args.key, "None" if v is None else v)

    def add_connection(self, args):
        conns = self.settings["connections"]
        if args.ircid in conns:
            return "duplicate ircid: %s" % args.ircid

        conns[args.ircid] = {
                "name" : args.ircid,
                "host" : args.host,
                "port" : args.port,
                "ssl" : False,
                "botname" : None,
                "password" : None,
                "channels" : [],
                "operators" : [],
                "enabled" : True,
                "channel_options" : { }
        }
        self.set_setting("connections", conns)

    def remove_connection(self, args):
        conns = self.settings["connections"]
        if args.ircid not in conns:
            return "no such ircid: %s" % args.ircid
        del conns[args.ircid]
        self.set_setting("connections", conns)

    def connection_set_value(self, args):
        conns = self.settings["connections"]
        if args.ircid not in conns:
            return "no such ircid: %s" % args.ircid
        if args.key == "port":
            v = int(args.value)
        elif args.key in ["ssl", "enabled"]:
            v = Plugin.str2bool(args.value)
        else:
            v = args.value
        conns[args.ircid][args.key] = v
        self.set_setting("connections", conns)

    def connection_unset_value(self, args):
        conns = self.settings["connections"]
        if args.ircid not in conns:
            return "no such ircid: %s" % args.ircid
        if args.key not in ["botname", "password"]:
            return "unsetting %s not allowed" % args.key
        conns[args.ircid][args.key] = None
        self.set_setting("connections", conns)

    def connection_show_value(self, args):
        conns = self.settings["connections"]
        if args.ircid not in conns:
            return "no such ircid: %s" % args.ircid
        v = conns[args.ircid][args.key]
        if v is not None and args.key == "password":
            v = len(v) * "*"
        return 'connections["%s"]["%s"] = %s' % (args.ircid, args.key, "None" if v is None else v)

    def connection_add_value(self, args):
        conns = self.settings["connections"]
        if args.ircid not in conns:
            return "no such ircid: %s" % args.ircid
        v = args.value
        if args.key == "channels":
            options = {}
            if args.password is not None:
                options["password"] = args.password
            conns[args.ircid]["channel_options"][args.value] = options
        elif args.key == "operators":
            v = ("nickserv", v)
        if v in conns[args.ircid][args.key]:
            return "already added to %s: %s" % (args.key, args.value)
        conns[args.ircid][args.key].append(v)
        self.set_setting("connections", conns)

    def connection_remove_value(self, args):
        conns = self.settings["connections"]
        if args.ircid not in conns:
            return "no such ircid: %s" % args.ircid
        v = args.value
        if args.key == "channels":
            del conns[args.ircid]["channel_options"][args.value]
        elif args.key == "operators":
            v = ("nickserv", v)
        conns[args.ircid][args.key].remove(v)
        self.set_setting("connections", conns)

    def channel_set_value(self, args):
        conns = self.settings["connections"]
        if args.ircid not in conns:
            return "no such ircid: %s" % args.ircid
        c = conns[args.ircid]
        if args.channel not in c["channels"]:
            return "no such channel: %s" % args.channel
        v = args.value
        if args.key in ["logging"]:
            v = Plugin.str2bool(v)
            c["channel_options"][args.channel][args.key] = v
        self.set_setting("connections", conns)

    def channel_unset_value(self, args):
        conns = self.settings["connections"]
        if args.ircid not in conns:
            return "no such ircid: %s" % args.ircid
        c = conns[args.ircid]
        if args.channel not in c["channels"]:
            return "no such channel: %s" % args.channel
        del c["channel_options"][args.channel][args.key]
        self.set_setting("connections", conns)

    def channel_show_value(self, args):
        conns = self.settings["connections"]
        if args.ircid not in conns:
            return "no such ircid: %s" % args.ircid
        c = conns[args.ircid]
        if args.channel not in c["channels"]:
            return "no such channel: %s" % args.channel
        v = c["channel_options"][args.channel][args.key]
        return 'connections["%s"]["%s"]["%s"] = %s' % (args.ircid, args.channel, args.key, "None" if v is None else v)

    def config(self, args):
        parser = ThrowingArgumentParser(prog="config")
        handlers = parser.add_subparsers(title="handlers", help="additional help")
        global_parser = handlers.add_parser("global")
        connection_parser = handlers.add_parser("connection")
        connection_parser.add_argument("ircid")
        channel_parser = handlers.add_parser("channel")
        channel_parser.add_argument("ircid")
        channel_parser.add_argument("channel")
        plugin_parser = handlers.add_parser("plugin")
        
        global_cmds = global_parser.add_subparsers(title="commands", help="additional help")
        global_set_parser = global_cmds.add_parser("set")
        global_unset_parser = global_cmds.add_parser("unset")
        global_add_parser = global_cmds.add_parser("add")
        global_remove_parser = global_cmds.add_parser("remove")
        global_show_parser = global_cmds.add_parser("show")
        global_keys = ["botname", "username", "ircname", "cmdprefix", "privpassword", "nr_worker_threads"]
        global_set_parser.add_argument("key", choices=global_keys)
        global_set_parser.add_argument("value")
        global_set_parser.set_defaults(func=self.set_value)
        global_unset_parser.add_argument("key", choices=global_keys)
        global_unset_parser.set_defaults(func=self.unset_value)
        global_add_handlers = global_add_parser.add_subparsers()
        global_add_connection_parser = global_add_handlers.add_parser("connection")
        global_add_connection_parser.add_argument("ircid", type=TehbotImpl.valid_id)
        global_add_connection_parser.add_argument("host")
        global_add_connection_parser.add_argument("port", type=int)
        global_add_connection_parser.set_defaults(func=self.add_connection)
        global_remove_handlers = global_remove_parser.add_subparsers()
        global_remove_connection_parser = global_remove_handlers.add_parser("connection")
        global_remove_connection_parser.add_argument("ircid", type=TehbotImpl.valid_id)
        global_remove_connection_parser.set_defaults(func=self.remove_connection)
        global_show_parser.add_argument("key", choices=global_keys)
        global_show_parser.set_defaults(func=self.show_value)

        connection_cmds = connection_parser.add_subparsers(title="commands", help="additional help")
        connection_set_parser = connection_cmds.add_parser("set")
        connection_unset_parser = connection_cmds.add_parser("unset")
        connection_add_parser = connection_cmds.add_parser("add")
        connection_remove_parser = connection_cmds.add_parser("remove")
        connection_show_parser = connection_cmds.add_parser("show")
        connection_set_keys = ["name", "host", "port", "ssl", "botname", "password", "enabled"]
        connection_add_keys = ["channels", "operators"]
        connection_set_parser.add_argument("key", choices=connection_set_keys)
        connection_set_parser.add_argument("value")
        connection_set_parser.set_defaults(func=self.connection_set_value)
        connection_unset_parser.add_argument("key", choices=connection_set_keys)
        connection_unset_parser.set_defaults(func=self.connection_unset_value)
        connection_add_parser.add_argument("key", choices=connection_add_keys)
        connection_add_parser.add_argument("value")
        connection_add_parser.add_argument("password", nargs="?")
        connection_add_parser.set_defaults(func=self.connection_add_value)
        connection_remove_parser.add_argument("key", choices=connection_add_keys)
        connection_remove_parser.add_argument("value")
        connection_remove_parser.set_defaults(func=self.connection_remove_value)
        connection_show_parser.add_argument("key", choices=connection_set_keys+connection_add_keys)
        connection_show_parser.set_defaults(func=self.connection_show_value)

        channel_cmds = channel_parser.add_subparsers(title="commands", help="additional help")
        channel_set_parser = channel_cmds.add_parser("set")
        channel_unset_parser = channel_cmds.add_parser("unset")
        channel_show_parser = channel_cmds.add_parser("show")
        channel_set_keys = ["logging", "password"]
        channel_set_parser.add_argument("key", choices=channel_set_keys)
        channel_set_parser.add_argument("value")
        channel_set_parser.set_defaults(func=self.channel_set_value)
        channel_unset_parser.add_argument("key", choices=channel_set_keys)
        channel_unset_parser.set_defaults(func=self.channel_unset_value)
        channel_show_parser.add_argument("key", choices=channel_set_keys)
        channel_show_parser.set_defaults(func=self.channel_show_value)

        plugin_cmds = plugin_parser.add_subparsers(title="plugins", help="additional help")
        for p in sorted(self.plugins, key=lambda x: x.__class__.__name__):
            p.integrate_parser(plugin_cmds)

        try:
            pargs = parser.parse_args(args)
            m = parser.get_help_msg()
            if m:
                return m.strip()
            res = pargs.func(pargs)
        except Exception as e:
            res = u"Error: %s" % Plugin.exc2str(e)

        return "Okay" if res is None else res

class Dispatcher:
    def __init__(self, tehbot):
        self.tehbot = tehbot

    def value(self, key, connection=None):
        return self.tehbot.value(key, connection)

    def dispatch(self, connection, event):
        method = getattr(self, "on_" + event.type, None)
        types = [ "all_raw_messages", "ping", "pong", "ctcp", "motd", "motdstart", "endofmotd" ]
        if method:
            method(connection, event)
        elif event.type not in types:
            print event.type, event.source, event.target, event.arguments

    def on_whoisaccount(self, connection, event):
        nick = event.arguments[0]
        account = event.arguments[1]
        params = self.tehbot.settings["connections"][connection.tehbot.ircid]

        for t, s in params["operators"]:
            if t == "nickserv" and s == account:
                self.tehbot.privusers[connection].add(nick)
                break

        self.tehbot.authusers[connection].add(nick)

    def on_endofwhois(self, connection, event):
        nick = event.arguments[0]

        pq = self.tehbot.privqueue[connection, nick]
        while True:
            try:
                plugin, args = pq.get(False)
                q = self.tehbot.queue
                q.put((plugin, args))
                pq.task_done()
            except Empty:
                break

    def on_nicknameinuse(self, connection, event):
        print "%s: Nick name in use" % self.tehbot.connection_name(connection)
        print event.type, event.source, event.target, event.arguments
        try:
            newnick = event.arguments[0] + "_"
        except:
            newnick = connection.get_nickname() + "_"
        print "trying new nick: %s" % newnick
        connection.nick(newnick)

    def on_welcome(self, connection, event):
        self.tehbot.logmsg(time.time(), "welcome", 0, connection.tehbot.ircid, self.tehbot.connection_name(connection), None, None, "connected to %s" % connection.server)

        params = self.tehbot.settings["connections"][connection.tehbot.ircid]
        nickservpw = params.get("password", None)
        if nickservpw:
            connection.privmsg("NickServ", "IDENTIFY %s" % nickservpw)

        self.tehbot.core.reactor.scheduler.execute_after(2, functools.partial(self.join_channels, connection))

    def join_channels(self, connection):
        params = self.tehbot.settings["connections"][connection.tehbot.ircid]
        channels = set(params.get("channels", []))

        channels_to_join = channels.difference(connection.tehbot.channels)
        channels_to_part = connection.tehbot.channels.difference(channels)

        if channels_to_join:
            mchans = ",".join(channels_to_join)
            mpasswords = ",".join(self.tehbot.channel_options(connection, channel).get("password", "") for channel in channels_to_join)
            multi = mchans
            if len(mpasswords) > len(channels_to_join):
                multi += " %s" % mpasswords
            self.tehbot.myprint("%s: joining %s" % (self.tehbot.connection_name(connection), mchans))
            connection.send_raw("JOIN %s" % multi)

        if channels_to_part:
            mchans = ",".join(channels_to_part)
            self.tehbot.myprint("%s: parting %s" % (self.tehbot.connection_name(connection), mchans))
            connection.part(channels_to_part)

    def on_disconnect(self, connection, event):
        if self.tehbot.quit_called:
            return

        if not self.tehbot.settings["connections"][connection.tehbot.ircid].get("enabled", True):
            return

        self.tehbot.logmsg(time.time(), "disconnect", 0, connection.tehbot.ircid, self.tehbot.connection_name(connection), None, None, "lost connection")
        delay = 60 + 60 * random.random()
        self.tehbot.myprint("%s: reconnecting in %d seconds" % (self.tehbot.connection_name(connection), delay))

        with self.tehbot.core.reactor.mutex:
            for cmd in self.tehbot.core.reactor.scheduler.queue[:]:
                if isinstance(cmd.target, functools.partial) and cmd.target.args == ('keep-alive',) and cmd.target.func.__self__ == connection:
                    self.tehbot.core.reactor.scheduler.queue.remove(cmd)

        self.tehbot.core.reactor.scheduler.execute_after(delay, functools.partial(self.tehbot.reconnect, connection))

    def on_join(self, connection, event):
        self.tehbot.logmsg(time.time(), "join", 0, connection.tehbot.ircid, self.tehbot.connection_name(connection), event.target, None, "%s joined" % event.source.nick)
        nick = event.source.nick
        channel = event.target
        botname = connection.get_nickname()

        if nick == botname:
            connection.tehbot.users[channel] = []
            connection.tehbot.channels.add(channel.lower())

            params = self.tehbot.settings["connections"][connection.tehbot.ircid]
            channels = set(params.get("channels", []))

            if channel.lower() not in channels:
                connection.part(channel)

        connection.tehbot.users[channel].append((nick, set()))

        if nick == botname:
            return

        for h in self.tehbot.channel_join_handlers:
            self.tehbot.queue.put((h, (connection, event, {})))

    def on_kick(self, connection, event):
        kicker = event.source.nick
        channel = event.target
        kicked = event.arguments[0]
        reason = event.arguments[1]
        self.tehbot.logmsg(time.time(), "kick", 0, connection.tehbot.ircid, self.tehbot.connection_name(connection), channel, None, "%s has kicked %s from %s (%s)" % (kicker, kicked, channel, reason))
        botname = connection.get_nickname()

        try:
            lst = connection.tehbot.users[channel]
            idx = [u for u,m in lst].index(kicked)
            del connection.tehbot.users[channel][idx]
        except ValueError as e:
            pass

        if kicked == botname:
            del connection.tehbot.users[channel]
            connection.tehbot.channels.remove(channel.lower())

        try:
            self.tehbot.privusers[connection].remove(event.source.kicked)
        except:
            pass

        try:
            self.tehbot.authusers[connection].remove(event.source.kicked)
        except:
            pass

    def on_part(self, connection, event):
        self.tehbot.logmsg(time.time(), "part", 0, connection.tehbot.ircid, self.tehbot.connection_name(connection), event.target, None, "%s left" % event.source.nick)
        nick = event.source.nick
        channel = event.target
        botname = connection.get_nickname()

        try:
            lst = connection.tehbot.users[channel]
            idx = [u for u,m in lst].index(nick)
            del connection.tehbot.users[channel][idx]
        except ValueError as e:
            pass

        if nick == botname:
            del connection.tehbot.users[channel]
            connection.tehbot.channels.remove(channel.lower())

        try:
            self.tehbot.privusers[connection].remove(event.source.nick)
        except:
            pass

        try:
            self.tehbot.authusers[connection].remove(event.source.nick)
        except:
            pass

    def on_quit(self, connection, event):
        self.tehbot.logmsg(time.time(), "quit", 0, connection.tehbot.ircid, self.tehbot.connection_name(connection), None, None, "%s has quit (%s)" % (event.source.nick, event.arguments[0]))
        botname = self.tehbot.pick(connection, "botname")
        nick = event.source.nick

        for channel in connection.tehbot.users.keys():
            try:
                lst = connection.tehbot.users[channel]
                idx = [u for u,m in lst].index(nick)
                del connection.tehbot.users[channel][idx]
            except ValueError as e:
                pass

        # reconquer our nick!
        if nick == botname:
            connection.nick(botname)

        try:
            self.tehbot.privusers[connection].remove(nick)
        except:
            pass

        try:
            self.tehbot.authusers[connection].remove(nick)
        except:
            pass

    def on_action(self, connection, event):
        msg = event.arguments[0]

        if not msg:
            return

        nick = event.source.nick

        if irc.client.is_channel(event.target):
            typ = 0 if self.tehbot.channel_options(connection, event.target).get("logging", True) else 2
            target = event.target
            for h in self.tehbot.channel_handlers:
                self.tehbot.queue.put((h, (connection, event, {"msg":msg})))
        else:
            typ = 1
            target = nick

        self.tehbot.logmsg(time.time(), "action", typ, connection.tehbot.ircid, self.tehbot.connection_name(connection), target, nick, msg)

    def react_to_command(self, connection, event, msg, ts, plugin=None):
        if not msg:
            return

        cmd = msg.split(" ", 1)[0]
        args = msg[len(cmd) + 1:]

        if not plugin and cmd in self.tehbot.cmd_handlers:
            plugin = self.tehbot.cmd_handlers[cmd]

        if plugin:
            self.tehbot.queue.put((plugin, (connection, event, {"msg":msg, "cmd":cmd, "args":args, "ts":ts})))

    def on_pubmsg(self, connection, event):
        now = time.time()
        msg = event.arguments[0]
        typ = 0 if self.tehbot.channel_options(connection, event.target).get("logging", True) else 2
        self.tehbot.logmsg(time.time(), "pubmsg", typ, connection.tehbot.ircid, self.tehbot.connection_name(connection), event.target, event.source.nick, msg)
        cmdprefix = self.tehbot.pick(connection, "cmdprefix")

        if msg:
            if msg[0] == cmdprefix:
                self.react_to_command(connection, event, msg[1:], now)
            else:
                for ph in self.tehbot.prefix_handlers:
                    if msg[0] == ph.command_prefix():
                        self.react_to_command(connection, event, msg[1:], now, ph)

            for h in self.tehbot.channel_handlers:
                self.tehbot.queue.put((h, (connection, event, {"msg":msg})))

    def on_privmsg(self, connection, event):
        now = time.time()
        msg = event.arguments[0]
        self.tehbot.logmsg(time.time(), "privmsg", 1, connection.tehbot.ircid, self.tehbot.connection_name(connection), event.source.nick, event.source.nick, msg)
        cmdprefix = self.tehbot.pick(connection, "cmdprefix")

        if msg:
            if msg[0] == cmdprefix:
                self.react_to_command(connection, event, msg[1:], now)
            else:
                for ph in self.tehbot.prefix_handlers:
                    if msg[0] == ph.command_prefix():
                        self.react_to_command(connection, event, msg[1:], now, ph)

    def on_nick(self, connection, event):
        oldnick = event.source.nick
        newnick = event.target
        self.tehbot.logmsg(time.time(), "nick", 0, connection.tehbot.ircid, self.tehbot.connection_name(connection), None, None, "%s is now known as %s" % (oldnick, newnick))
        botname = self.tehbot.pick(connection, "botname")

        for channel in connection.tehbot.users.keys():
            try:
                lst = connection.tehbot.users[channel]
                idx = [u for u,m in lst].index(oldnick)
                _, mode = lst[idx]
                connection.tehbot.users[channel][idx] = (newnick, mode)
            except ValueError as e:
                pass

        # reconquer our nick!
        if oldnick == botname:
            connection.nick(botname)

        try:
            self.tehbot.privusers[connection].remove(event.source.nick)
        except:
            pass

        try:
            self.tehbot.authusers[connection].remove(event.source.nick)
        except:
            pass

    def on_396(self, connection, event):
        # TODO join channel before 5s wait time is over
        pass

    def on_namreply(self, connection, event):
        ch_type, channel, nick_list = event.arguments

        if channel == "*":
            return

        connection.tehbot.users[channel] = []

        for nick in nick_list.split():
            nick_modes = set()

            if nick[0] in connection.features.prefix:
                nick_modes.add(connection.features.prefix[nick[0]])
                nick = nick[1:]

            connection.tehbot.users[channel].append((nick, nick_modes))

    def on_mode(self, connection, event):
        if not irc.client.is_channel(event.target):
            return

        modes = irc.modes.parse_channel_modes(" ".join(event.arguments))
        channel = event.target
        lst = connection.tehbot.users[channel]

        for op, mode, arg in modes:
            if arg is None:
                continue

            idx = [u for u,m in lst].index(arg)
            _, m = lst[idx]

            if op == "+":
                m.add(mode)
            elif mode in m:
                m.remove(mode)

            connection.tehbot.users[channel][idx] = (arg, m)
