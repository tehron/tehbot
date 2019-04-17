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

import tehbot.plugins as plugins
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
        self.handlers = []
        self.cmd_handlers = {}
        self.channel_handlers = []
        self.channel_join_handlers = []
        self.pollers = []
        self.announcers = []
        self.prefix_handlers = []
        self.queue = Queue(maxsize=0)
        self.workers = []
        self.restart_workers = False
        self.quit_called = False
        self.restart_called = False
        self.dbfile = os.path.join(os.path.dirname(__file__), "../data/tehbot.sqlite")
        self.dbconn = sqlite3.connect(self.dbfile)
        self.dbconn.execute("create table if not exists Messages(id integer primary key, ts datetime, server varchar, channel varchar, nick varchar, type integer, message varchar)")
        self.actionqueue = Queue()
        self.privusers = defaultdict(set)
        self.authusers = defaultdict(set)
        self.privqueue = defaultdict(Queue)
        self.settings = Settings()
        self.settings.load(self.dbconn)
        self.plugins = []
        pattern = r'[\x02\x0F\x16\x1D\x1F]|\x03(?:\d{1,2}(?:,\d{1,2})?)?'
        self.regex = re.compile(pattern, re.UNICODE)

    def postinit(self):
        self.core.reactor.add_global_handler("all_events", self.dispatcher.dispatch, -10)

        for p in self.pollers:
            p.schedule(20)

        for a in self.announcers:
            today = datetime.date.today()
            at = int(today.strftime("%s")) + a.at()
            if at < time.time():
                at += int(datetime.timedelta(days=1).total_seconds())
            print "Scheduling %s at %d" % (a.__class__.__name__, at)
            a.schedule(at)

        self.start_workers()

    def deinit(self):
        self.core.reactor.remove_global_handler("all_events", self.dispatcher.dispatch)

        for h in self.pollers + self.announcers:
            h.quit = True

        with self.core.reactor.mutex:
            for cmd in self.core.reactor.scheduler.queue[:]:
                try:
                    if cmd.target.im_func.func_name == "callme":
                        print "removing", cmd.target
                        self.core.reactor.scheduler.queue.remove(cmd)
                except:
                    pass

        for h in self.handlers:
            h.deinit(self.dbconn)

        self.dbconn.close()

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

        with self.dbconn:
            self.dbconn.execute("insert into Messages values(null, ?, ?, ?, ?, ?, ?)", (when, network, target, nick, typ, msg))

    def collect_plugins(self):
        self.plugins = plugins.collect()

        for p in self.plugins:
            for name, clazz in inspect.getmembers(p, lambda x: inspect.isclass(x) and issubclass(x, plugins.Plugin) and x.__module__ == p.__name__):
                o = clazz()
                o.initialize(self.dbconn)

                if isinstance(o, plugins.Command):
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
                elif isinstance(o, plugins.ChannelHandler):
                    self.channel_handlers.append(o)
                elif isinstance(o, plugins.ChannelJoinHandler):
                    self.channel_join_handlers.append(o)
                elif isinstance(o, plugins.Poller):
                    self.pollers.append(o)
                elif isinstance(o, plugins.Announcer):
                    self.announcers.append(o)
                elif isinstance(o, plugins.PrefixHandler):
                    self.prefix_handlers.append(o)
                else:
                    continue

                self.handlers.append(o)

        print " command handlers:", sorted(self.cmd_handlers)
        print " channel handlers:", sorted(h.__class__.__name__ for h in self.channel_handlers)
        print "chn join handlers:", sorted(h.__class__.__name__ for h in self.channel_join_handlers)
        print "          pollers:", sorted(h.__class__.__name__ for h in self.pollers)
        print "       announcers:", sorted(h.__class__.__name__ for h in self.announcers)
        print "   prefix handlers", sorted(h.__class__.__name__ for h in self.prefix_handlers)

    def gather_modules(self):
        modules = set()
        _gather(plugins, modules)
        modules.remove(plugins)
        return modules

    def exec_plugin(self, plugin, connection, event, extra, dbconn):
        if not plugin.is_enabled():
            return

        if irc.client.is_channel(event.target):
            if not plugin.pub_allowed:
                return
        else:
            if not plugin.priv_allowed:
                return

        if isinstance(plugin, plugins.PrivilegedPlugin) and not self.privileged(connection, event):
            res = self.request_priv(extra)
        elif isinstance(plugin, plugins.AuthedPlugin) and not self.authed(connection, event):
            res = self.request_auth(extra)
        else:
            res = plugin.execute(connection, event, extra, dbconn)

        return res

    def privileged(self, connection, event):
        return event.source.nick in self.privusers[connection]

    def authed(self, connection, event):
        return event.source.nick in self.authusers[connection]

    def request_priv(self, extra):
        return [("nopriv", None)] if extra.has_key("auth_requested") else [("doauth", None)]

    def request_auth(self, extra):
        return [("noauth", None)] if extra.has_key("auth_requested") else [("doauth", None)]

    def priv_override(self, connection, event):
        self.privusers[connection].add(event.source.nick)

    def _process(self):
        dbconn = sqlite3.connect(self.dbfile)

        while True:
            try:
                plugin, args = self.queue.get(timeout=1)
                connection, event, extra = args
                res = self.exec_plugin(plugin, connection, event, extra, dbconn)
                self.actionqueue.put((res, plugin, connection, event, extra))
                self.queue.task_done()
            except Empty:
                pass
            except SystemExit:
                raise
            except:
                traceback.print_exc()

            if self.quit_called or self.restart_workers:
                break

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
            if c.name == name:
                return c
        return None

    def connect(self):
        for name in self.settings.connections():
            conn = self._get_connection(name)
            if conn is None:
                print "Connecting to %s" % name
                conn = self.core.reactor.server()
                conn.name = name
                self.reconnect(conn)
            else:
                self.dispatcher.join_channels(conn)

    def reconnect(self, connection):
        connection.channels = set()
        connection.locks = dict()
        connection.tehbot_users = dict()

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
            for msplit in plugins.Plugin.split(m2).split("\n"):
                func(target, msplit)
                self.logmsg(time.time(), connection.name, target, connection.get_nickname(), msplit, False, typ)

    def process_once(self, timeout):
        self.core.reactor.process_once(timeout)

        try:
            actions, plugin, connection, event, extra = self.actionqueue.get(False)
        except Empty:
            return

        try:
            if irc.client.is_channel(event.target):
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
                if action == "say" or action == "me" or action == "notice":
                    msg = args
                    getattr(self, action)(connection, target, typ, msg)
                elif action == "say_nolog":
                    msg = args
                    getattr(self, action)(connection, target, 2, msg)
                elif action == "say_nick":
                    msg = args
                    getattr(self, action)(connection, target, event.source.nick, typ, msg)
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
                        enabled_cmds = sorted(cmd(p) for p in self.handlers if isinstance(p, plugins.Command) and list_all or p.is_enabled())
                        msg = "Available commands: %s" % ", ".join(enabled_cmds)
                    else:
                        if self.cmd_handlers.has_key(cmd):
                            msg = self.cmd_handlers[cmd].parser.format_help().strip()
                        else:
                            msg = "Unknown command: %s" % cmd
                    self.say(connection, target, typ, msg)
                elif action == "reload":
                    res = self.reload()

                    if res is None:
                        msg = "Okay"
                    else:
                        mod, lineno, exc = res
                        msg = u"Error in %s(%d): %s" % (mod, lineno, plugins.Plugin.exc2str(exc))
                    self.say(connection, target, typ, msg)

                    if res is None:
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
                    elif not extra.has_key("auth_requested"):
                        self.actionqueue.put(([("doauth", None)], plugin, connection, event, extra))
                        return

                    priv = "" if self.privileged(connection, event) else " \x02not\x02"
                    self.say(connection, target, typ, "%s is%s privileged" % (event.source.nick, priv))
        finally:
            self.actionqueue.task_done()

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
        self.restart_workers = True
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
            print " * %s: %s" % (c.name, "connected" if c.is_connected() else "not connected")

        print "Delayed Commands"
        for c in self.core.reactor.scheduler.queue:
            print " * %s at %s" % (c.target.func if isinstance(c.target, functools.partial) else c.target, c)

        print "Privileged Users"
        for c, nicks in self.privusers.items():
            print " * %s: %r" % (c.name, sorted(nicks))

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
            for h in self.handlers:
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
        print "%s: Nick name in use" % connection.name
        print event.type, event.source, event.target, event.arguments
        try:
            newnick = event.arguments[0] + "_"
        except:
            newnick = connection.get_nickname() + "_"
        print "trying new nick: %s" % newnick
        connection.nick(newnick)

    def on_welcome(self, connection, event):
        self.tehbot.logmsg(time.time(), connection.name, None, None, "connected to %s" % connection.server, False, 0)

        params = self.tehbot.settings.connection_params(connection)
        nickservpw = params.get("password", None)
        if nickservpw:
            connection.privmsg("NickServ", "IDENTIFY %s" % nickservpw)

        self.tehbot.core.reactor.scheduler.execute_after(2, functools.partial(self.join_channels, connection))

    def join_channels(self, connection):
        params = self.tehbot.settings.connection_params(connection)
        channels = set(params.get("channels", []))

        channels_to_join = channels.difference(connection.channels)
        channels_to_part = connection.channels.difference(channels)

        for ch in channels_to_join:
            connection.locks[ch] = threading.Lock()

        for ch in channels_to_part:
            del connection.locks[ch]

        if channels_to_join:
            mchans = ",".join(channels_to_join)
            self.tehbot.myprint("%s: joining %s" % (connection.name, mchans))
            connection.send_raw("JOIN %s" % mchans)

        if channels_to_part:
            mchans = ",".join(channels_to_part)
            self.tehbot.myprint("%s: parting %s" % (connection.name, mchans))
            connection.part(channels_to_part)

    def on_disconnect(self, connection, event):
        if self.tehbot.quit_called:
            return

        delay = 120
        self.tehbot.logmsg(time.time(), connection.name, None, None, "lost connection", False, 0)
        self.tehbot.myprint("%s: reconnecting in %d seconds" % (connection.name, delay))

        with self.tehbot.core.reactor.mutex:
            for cmd in self.tehbot.core.reactor.scheduler.queue[:]:
                if isinstance(cmd.target, functools.partial) and cmd.target.args == ('keep-alive',) and cmd.target.func.__self__ == connection:
                    print "removing cmd", cmd
                    self.tehbot.core.reactor.scheduler.queue.remove(cmd)

        self.tehbot.core.reactor.scheduler.execute_after(delay, functools.partial(self.tehbot.reconnect, connection))

    def on_join(self, connection, event):
        self.tehbot.logmsg(time.time(), connection.name, None, None, "%s: %s joined" % (event.target, event.source.nick), False, 0)
        nick = event.source.nick
        channel = event.target
        botname = self.tehbot.settings.value("botname", connection)

        if nick == botname:
            connection.tehbot_users[channel] = []
            connection.channels.add(channel.lower())

            params = self.tehbot.settings.connection_params(connection)
            channels = set(params.get("channels", []))

            if channel.lower() not in channels:
                connection.part(channel)

        connection.tehbot_users[channel].append(nick)

        if nick == botname:
            return

        for h in self.tehbot.channel_join_handlers:
            self.tehbot.queue.put((h, (connection, event, {})))

    def on_part(self, connection, event):
        self.tehbot.logmsg(time.time(), connection.name, event.target, None, "%s left" % event.source.nick, False, 0)
        nick = event.source.nick
        channel = event.target
        botname = self.tehbot.settings.value("botname", connection)

        try:
            connection.tehbot_users[channel].remove(nick)
        except ValueError as e:
            pass

        if nick == botname:
            del connection.tehbot_users[channel]
            connection.channels.remove(channel.lower())

        try:
            self.tehbot.privusers[connection].remove(event.source.nick)
        except:
            pass

        try:
            self.tehbot.authusers[connection].remove(event.source.nick)
        except:
            pass

    def on_quit(self, connection, event):
        self.tehbot.logmsg(time.time(), connection.name, None, None, "%s has quit (%s)" % (event.source.nick, event.arguments[0]), False, 0)
        botname = self.tehbot.settings.value("botname", connection)
        nick = event.source.nick

        for channel in connection.tehbot_users.keys():
            try:
                connection.tehbot_users[channel].remove(nick)
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

        self.tehbot.logmsg(time.time(), connection.name, target, nick, msg, True, 0)

    def react_to_command(self, connection, event, msg, plugin=None):
        if not msg:
            return

        cmd = msg.split(" ", 1)[0]
        args = msg[len(cmd) + 1:]

        if not plugin and cmd in self.tehbot.cmd_handlers:
            plugin = self.tehbot.cmd_handlers[cmd]

        if plugin:
            self.tehbot.queue.put((plugin, (connection, event, {"msg":msg, "cmd":cmd, "args":args})))

    def on_pubmsg(self, connection, event):
        msg = event.arguments[0]
        typ = self.tehbot.settings.log_type(connection.name, event.target)
        self.tehbot.logmsg(time.time(), connection.name, event.target, event.source.nick, msg, False, typ)
        cmdprefix = self.tehbot.settings.value("cmdprefix", connection)

        if msg:
            if msg[0] == cmdprefix:
                self.react_to_command(connection, event, msg[1:])
            else:
                for ph in self.tehbot.prefix_handlers:
                    if msg[0] == ph.command_prefix():
                        self.react_to_command(connection, event, msg[1:], ph)

            for h in self.tehbot.channel_handlers:
                self.tehbot.queue.put((h, (connection, event, {"msg":msg})))

    def on_privmsg(self, connection, event):
        msg = event.arguments[0]
        self.tehbot.logmsg(time.time(), connection.name, event.source.nick, event.source.nick, msg, False, 1)
        cmdprefix = self.tehbot.settings.value("cmdprefix", connection)

        if msg:
            if msg[0] == cmdprefix:
                self.react_to_command(connection, event, msg[1:])
            else:
                for ph in self.tehbot.prefix_handlers:
                    if msg[0] == ph.command_prefix():
                        self.react_to_command(connection, event, msg[1:], ph)

    def on_nick(self, connection, event):
        oldnick = event.source.nick
        newnick = event.target
        self.tehbot.logmsg(time.time(), connection.name, None, None, "%s is now known as %s" % (oldnick, newnick), False, 0)
        botname = self.tehbot.settings.value("botname", connection)

        for channel in connection.tehbot_users.keys():
            try:
                connection.tehbot_users[channel].remove(oldnick)
            except ValueError:
                pass
            connection.tehbot_users[channel].append(newnick)

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

        connection.tehbot_users[channel] = []

        for nick in nick_list.split():
            nick_modes = []

            if nick[0] in connection.features.prefix:
                nick_modes.append(connection.features.prefix[nick[0]])
                nick = nick[1:]

            # for mode in nick_modes:
                # self.channels[channel].set_mode(mode, nick)

            connection.tehbot_users[channel].append(nick)
