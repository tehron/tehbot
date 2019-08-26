import irc.client
from Queue import Queue, Empty
import traceback
import time
import re
import datetime
import functools
import threading
import sqlite3
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
from tehbot.settings import Settings
import locale
encoding = locale.getdefaultlocale()[1] or "ascii"

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
        self.dbfile = os.path.join(os.path.dirname(__file__), "../data/tehbot.sqlite")
        self.dbconn = sqlite3.connect(self.dbfile)
        self.privusers = defaultdict(set)
        self.authusers = defaultdict(set)
        self.privqueue = defaultdict(Queue)
        self.settings = Settings()
        self.settings.load(self.dbconn)
        pattern = r'[\x02\x0F\x16\x1D\x1F]|\x03(?:\d{1,2}(?:,\d{1,2})?)?'
        self.regex = re.compile(pattern, re.UNICODE)

    def postinit(self):
        with self.dbconn:
            self.dbconn.execute("create table if not exists Messages(id integer primary key, ts datetime, server varchar, channel varchar, nick varchar, type integer, message varchar)")
            self.dbconn.execute("create index if not exists idx_Messages_seen on Messages(nick, ts desc)")

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
                        print "removing", cmd.target
                        self.core.reactor.scheduler.queue.remove(cmd)
                except:
                    pass

        for h in self.plugins:
            h.deinit(self.dbconn)

        self.dbconn.close()
        self.stop_workers = True
        self.stop_logthread = True

    def myprint(self, s):
        s = self.regex.sub("", s)
        print time.strftime("%H:%M:%S"), s.encode(encoding, "backslashreplace")

    def logmsg(self, when, network, target, nick, msg, is_action, typ):
        msg = self.regex.sub("", msg)
        if nick is None:
            s = msg
        else:
            if is_action:
                s = "*%s %s" % (nick, msg)
            else:
                s = "%s: %s" % (nick, msg)

        ts = time.strftime("%H:%M:%S", time.localtime(when))
        if target is None:
            s = "%s %s: %s" % (ts, network, s)
        else:
            s = "%s %s: %s: %s" % (ts, network, target, s)
        print s.encode(encoding, "backslashreplace")
        self.logqueue.put((when, network, target, nick, typ, msg))

    def load_plugins(self, modules):
        for p in modules:
            for name, clazz in inspect.getmembers(p, lambda x: inspect.isclass(x) and issubclass(x, tehbot.plugins.Plugin) and x.__module__ == p.__name__):
                o = clazz()
                o.initialize(self.dbconn)

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

    def exec_plugin(self, plugin, connection, event, extra, dbconn):
        if not plugin.is_enabled():
            return

        if event:
            if irc.client.is_channel(event.target):
                if not plugin.pub_allowed:
                    return
            else:
                if not plugin.priv_allowed:
                    return

            extra["priv"] = event.source.nick in self.privusers[connection]
            extra["auth"] = event.source.nick in self.authusers[connection]

        res = plugin.execute(connection, event, extra, dbconn)
        return res

    def priv_override(self, connection, event):
        self.privusers[connection].add(event.source.nick)

    def privileged(self, connection, event):
        return event.source.nick in self.privusers[connection]

    def _logger(self):
        dbconn = sqlite3.connect(self.dbfile)

        while True:
            try:
                when, network, target, nick, typ, msg = self.logqueue.get(timeout=0.1)
                with dbconn:
                    dbconn.execute("insert into Messages values(null, ?, ?, ?, ?, ?, ?)", (when, network, target, nick, typ, msg))
                self.logqueue.task_done()
            except Empty:
                pass
            except:
                self.core.print_exc()

            if self.stop_logthread:
                break

        dbconn.close()

    def _process(self):
        dbconn = sqlite3.connect(self.dbfile)

        while True:
            if self.stop_workers:
                break

            try:
                plugin, args = self.queue.get(timeout=0.1)
            except Empty:
                continue

            connection, event, extra = args

            try:
                res = self.exec_plugin(plugin, connection, event, extra, dbconn)
            except:
                res = None
                self.core.print_exc()

            self.actionqueue.put((res, plugin, connection, event, extra))
            self.queue.task_done()

        dbconn.close()

    def start_workers(self):
        while len(self.workers) < self.settings.value("nr_worker_threads"):
            worker = threading.Thread(target=self._process)
            self.workers.append(worker)
            worker.start()

    def __kill_workers(self):
        while self.workers:
            _terminate_thread(self.workers.pop())

    def _get_connection(self, name):
        for c in self.core.reactor.connections:
            if c.tehbot.name == name:
                return c
        return None

    def _get_plugin(self, pname):
        for p in self.plugins:
            name = p.__class__.__name__
            if name.endswith(pname):
                return p

        return None

    def connect(self):
        conns = self.settings.connections()

        for name in conns:
            conn = self._get_connection(name)

            if conn is None:
                print "Connecting to %s" % name
                conn = self.core.reactor.server()
                conn.tehbot = lambda: None
                conn.tehbot.name = name
                conn.tehbot.params = conns[name]
                conn.tehbot.network_id = conn.tehbot.params.get("id", name)

                try:
                    self.reconnect(conn)
                except:
                    self.core.print_exc()
                    conn.close()
            else:
                self.dispatcher.join_channels(conn)

    def reconnect(self, connection):
        connection.tehbot.channels = set()
        connection.tehbot.users = dict()

        params = self.settings.connection_params(connection)

        if params["ssl"]:
            import ssl
            factory = irc.client.connection.Factory(wrapper=ssl.wrap_socket)
        else:
            factory = irc.client.connection.Factory()
        botname = self.settings.value("botname", connection)
        username = self.settings.value("username", connection)
        ircname = self.settings.value("ircname", connection)
        nickservpw = params.get("password", None)
        connection.connect(params["host"], params["port"], botname, nickservpw, username, ircname, factory)
        connection.set_rate_limit(2)
        connection.set_keepalive(60)

    def say(self, connection, target, typ, msg):
        self.ircsend(connection.privmsg, connection, target, typ, None, msg)

    def notice(self, connection, target, typ, msg):
        self.ircsend(connection.notice, connection, target, typ, None, msg)

    def say_nick(self, connection, target, typ, nick, msg):
        self.ircsend(connection.privmsg, connection, target, typ, nick, msg)

    def me(self, connection, target, typ, msg):
        msg = msg.replace("\r", "?").replace("\n", "?")
        self.ircsend(connection.action, connection, target, typ, None, msg)

    def ircsend(self, func, connection, target, typ, nick, msg):
        if not target or not msg:
            return

        for m in msg.split("\n"):
            m = m.replace("\r", "?");
            if not m.strip():
                continue
            m2 = "%s: %s" % (nick, m) if nick else m
            for msplit in tehbot.plugins.Plugin.split(m2).split("\n"):
                func(target, msplit)
                self.logmsg(time.time(), connection.tehbot.name, target, connection.get_nickname(), msplit, False, typ)

    def process_once(self, timeout):
        self.core.reactor.process_once(timeout)

        now = time.time()
        try:
            actions, plugin, connection, event, extra = self.actionqueue.get(False)
        except Empty:
            return

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
            typ = 0
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

                    params = self.settings.connection_params(connection)
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
                    if not args:
                        msg = "That won't work"
                    else:
                        handler = args[0]
                        args = args[1:]
                        msg = self.config(handler, args, self.dbconn)
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
                    where, msg = args

                    tgts = []
                    if "__all__" in where:
                        for conn in self.core.reactor.connections:
                            for ch in conn.tehbot.channels:
                                tgts.append((conn, ch))
                    else:
                        for network in where:
                            conn = self._get_connection(network)
                            if conn is None:
                                continue
                            if "__all__" in where[network]:
                                for ch in conn.tehbot.channels:
                                    tgts.append((conn, ch))
                            else:
                                for ch in where[network]:
                                    if ch in conn.tehbot.channels:
                                        tgts.append((conn, ch))

                    for conn, channel in tgts:
                        self.say(conn, channel, typ, msg)
                elif action == "mode":
                    network, channel, modes = args
                    conn = self._get_connection(network)
                    if conn is not None:
                        print conn.mode(channel, modes)
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
            print " * %s: %s" % (c.tehbot.name, "connected" if c.is_connected() else "not connected")

        print "Delayed Commands"
        for c in self.core.reactor.scheduler.queue:
            print " * %s at %s" % (c.target.func if isinstance(c.target, functools.partial) else c.target, c)

        print "Privileged Users"
        for c, nicks in self.privusers.items():
            print " * %s: %r" % (c.tehbot.name, sorted(nicks))

    def kbd_config(self, args):
        arr = shlex.split(args or "")
        if not arr:
            return
        print self.config(arr[0], arr[1:], self.dbconn)

    def config(self, handler, arr, dbconn):
        if handler == "tehbot":
            if arr[0] == "connections":
                if arr[1] == "add":
                    name = arr[2]

                    if name in self.settings.connections():
                        return "That name already exists!"

                    self.settings["connections"][name] = {
                            "host" : None,
                            "port" : 6667,
                            "ssl" : False,
                            "channels" : [ ],
                            "operators" : [ ],
                            "id" : None
                            }
                    self.settings.save(dbconn)
                    return "Okay"
                elif arr[1] == "modify":
                    name = arr[2]
                    action = arr[3]
                    key = arr[4]
                    value = arr[5]

                    if name not in self.settings.connections():
                        return "Connction not found: %s" % name

                    if action not in ["set", "add"]:
                        return "Illegal action: %s" % action

                    if key == "ssl":
                        value = bool(value)
                    elif key == "port":
                        value = int(value)

                    if key == "channels":
                        if not self.settings["connections"][name].has_key(key):
                            self.settings["connections"][name][key] = []
                        self.settings["connections"][name][key].append(value)
                    elif key == "operators":
                        if not self.settings["connections"][name].has_key(key):
                            self.settings["connections"][name][key] = []
                        self.settings["connections"][name][key].append(("nickserv", value))
                    elif key == "id":
                        for cname, conn in self.settings.connections().items():
                            if cname != name and conn.has_key(key) and conn[key] == value:
                                return "That id already exists in connection '%s'!" % cname
                            self.settings["connections"][name][key] = value
                    else:
                        self.settings["connections"][name][key] = value

                        if key == "botname":
                            self.settings["connections"][name]["username"] = value
                            self.settings["connections"][name]["ircname"] = value

                    self.settings.save(dbconn)
                    return "Okay"
                elif arr[1] == "show":
                    return "no!"
                    #return repr(self.settings["connections"])
            elif arr[0] == "logging":
                if arr[1] == "modify":
                    action = arr[2]
                    key = arr[3]
                    value = arr[4]

                    if action != "add":
                        return "Illegal action: %s" % action

                    network, channel = value.split(",")

                    dt = self.settings["logging"][key]
                    if not dt.has_key(network):
                        dt[network] = []
                    dt[network].append(channel)
                    self.settings.save(dbconn)
                    return "Okay"
            elif arr[0] == "modify":
                if arr[1] == "set":
                    key = arr[2]
                    value = arr[3]
                    self.settings[key] = value
                    self.settings.save(dbconn)
                    return "Okay"
        else:
            for h in self.plugins:
                if h.__class__.__name__ == handler:
                    return h.config(arr, dbconn)


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
        params = self.tehbot.settings.connection_params(connection)

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
        print "%s: Nick name in use" % connection.tehbot.name
        print event.type, event.source, event.target, event.arguments
        try:
            newnick = event.arguments[0] + "_"
        except:
            newnick = connection.get_nickname() + "_"
        print "trying new nick: %s" % newnick
        connection.nick(newnick)

    def on_welcome(self, connection, event):
        self.tehbot.logmsg(time.time(), connection.tehbot.name, None, None, "connected to %s" % connection.server, False, 0)

        params = self.tehbot.settings.connection_params(connection)
        nickservpw = params.get("password", None)
        if nickservpw:
            connection.privmsg("NickServ", "IDENTIFY %s" % nickservpw)

        self.tehbot.core.reactor.scheduler.execute_after(2, functools.partial(self.join_channels, connection))

    def join_channels(self, connection):
        params = self.tehbot.settings.connection_params(connection)
        channels = set(params.get("channels", []))

        channels_to_join = channels.difference(connection.tehbot.channels)
        channels_to_part = connection.tehbot.channels.difference(channels)

        if channels_to_join:
            mchans = ",".join(channels_to_join)
            self.tehbot.myprint("%s: joining %s" % (connection.tehbot.name, mchans))
            connection.send_raw("JOIN %s" % mchans)

        if channels_to_part:
            mchans = ",".join(channels_to_part)
            self.tehbot.myprint("%s: parting %s" % (connection.tehbot.name, mchans))
            connection.part(channels_to_part)

    def on_disconnect(self, connection, event):
        if self.tehbot.quit_called:
            return

        delay = 120
        self.tehbot.logmsg(time.time(), connection.tehbot.name, None, None, "lost connection", False, 0)
        self.tehbot.myprint("%s: reconnecting in %d seconds" % (connection.tehbot.name, delay))

        with self.tehbot.core.reactor.mutex:
            for cmd in self.tehbot.core.reactor.scheduler.queue[:]:
                if isinstance(cmd.target, functools.partial) and cmd.target.args == ('keep-alive',) and cmd.target.func.__self__ == connection:
                    print "removing cmd", cmd
                    self.tehbot.core.reactor.scheduler.queue.remove(cmd)

        self.tehbot.core.reactor.scheduler.execute_after(delay, functools.partial(self.tehbot.reconnect, connection))

    def on_join(self, connection, event):
        self.tehbot.logmsg(time.time(), connection.tehbot.name, None, None, "%s: %s joined" % (event.target, event.source.nick), False, 0)
        nick = event.source.nick
        channel = event.target
        botname = self.tehbot.settings.value("botname", connection)

        if nick == botname:
            connection.tehbot.users[channel] = []
            connection.tehbot.channels.add(channel.lower())

            params = self.tehbot.settings.connection_params(connection)
            channels = set(params.get("channels", []))

            if channel.lower() not in channels:
                connection.part(channel)

        connection.tehbot.users[channel].append(nick)

        if nick == botname:
            return

        for h in self.tehbot.channel_join_handlers:
            self.tehbot.queue.put((h, (connection, event, {})))

    def on_part(self, connection, event):
        self.tehbot.logmsg(time.time(), connection.tehbot.name, event.target, None, "%s left" % event.source.nick, False, 0)
        nick = event.source.nick
        channel = event.target
        botname = self.tehbot.settings.value("botname", connection)

        try:
            connection.tehbot.users[channel].remove(nick)
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
        self.tehbot.logmsg(time.time(), connection.tehbot.name, None, None, "%s has quit (%s)" % (event.source.nick, event.arguments[0]), False, 0)
        botname = self.tehbot.settings.value("botname", connection)
        nick = event.source.nick

        for channel in connection.tehbot.users.keys():
            try:
                connection.tehbot.users[channel].remove(nick)
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
            target = event.target
            for h in self.tehbot.channel_handlers:
                self.tehbot.queue.put((h, (connection, event, {"msg":msg})))
        else:
            target = nick

        self.tehbot.logmsg(time.time(), connection.tehbot.name, target, nick, msg, True, 0)

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
        typ = self.tehbot.settings.log_type(connection.tehbot.name, event.target)
        self.tehbot.logmsg(time.time(), connection.tehbot.name, event.target, event.source.nick, msg, False, typ)
        cmdprefix = self.tehbot.settings.value("cmdprefix", connection)

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
        self.tehbot.logmsg(time.time(), connection.tehbot.name, event.source.nick, event.source.nick, msg, False, 1)
        cmdprefix = self.tehbot.settings.value("cmdprefix", connection)

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
        self.tehbot.logmsg(time.time(), connection.tehbot.name, None, None, "%s is now known as %s" % (oldnick, newnick), False, 0)
        botname = self.tehbot.settings.value("botname", connection)

        for channel in connection.tehbot.users.keys():
            try:
                connection.tehbot.users[channel].remove(oldnick)
            except ValueError:
                pass
            connection.tehbot.users[channel].append(newnick)

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
            nick_modes = []

            if nick[0] in connection.features.prefix:
                nick_modes.append(connection.features.prefix[nick[0]])
                nick = nick[1:]

            # for mode in nick_modes:
                # self.channels[channel].set_mode(mode, nick)

            connection.tehbot.users[channel].append(nick)
