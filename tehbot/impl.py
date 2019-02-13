import plugins
from settings import Settings
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

import os.path
from types import ModuleType

import ctypes
import shlex
import argparse

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
        self.quit_called = False
        self.restart_called = False
        self.dbfile = os.path.join(os.path.dirname(__file__), "../data/tehbot.sqlite")
        self.dbconn = sqlite3.connect(self.dbfile)
        self.mainqueue = Queue()
        self.privusers = defaultdict(set)
        self.authusers = defaultdict(set)
        self.privqueue = defaultdict(Queue)
        self.settings = Settings()
        self.settings.load(self.dbconn)

    def collect_plugins(self):
        plugins.collect()
        print " command handlers:", sorted(self.cmd_handlers)
        print " channel handlers:", sorted(h.__class__.__name__ for h in self.channel_handlers)
        print "chn join handlers:", sorted(h.__class__.__name__ for h in self.channel_join_handlers)
        print "          pollers:", sorted(h.__class__.__name__ for h in self.pollers)
        print "       announcers:", sorted(h.__class__.__name__ for h in self.announcers)
        print "   prefix handlers", sorted(h.__class__.__name__ for h in self.prefix_handlers)

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

        self.dbconn.close()
        self.quit_called = True
        self.restart_called = False

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

    def gather_modules(self):
        modules = set()
        _gather(plugins, modules)
        modules.remove(plugins)
        return modules

    def _process(self):
        dbconn = sqlite3.connect(self.dbfile)

        while True:
            try:
                plugin, args = self.queue.get(timeout=1)
                plugin.handle(*args, dbconn=dbconn)
                self.queue.task_done()
            except Empty:
                pass
            except SystemExit:
                raise
            except:
                traceback.print_exc()

            if self.quit_called:
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
                conn.channels = set()
                conn.locks = dict()
                conn.tehbot_users = dict()
                self.reconnect(conn)
            else:
                self.dispatcher.join_channels(conn)

    def reconnect(self, connection):
        params = self.settings.connection_params(connection)

        if params["ssl"]:
            import ssl
            factory = irc.client.connection.Factory(wrapper=ssl.wrap_socket)
        else:
            factory = irc.client.connection.Factory()
        botname = self.settings.value("botname", connection)
        username = self.settings.value("username", connection)
        ircname = self.settings.value("ircname", connection)
        connection.connect(params["host"], params["port"], botname, None, username, ircname, factory)
        connection.set_rate_limit(2)
        connection.set_keepalive(60)
        
        nickservpw = params.get("password", None)
        if nickservpw:
            connection.privmsg("NickServ", "IDENTIFY %s" % password)

    def process_once(self, timeout):
        self.core.reactor.process_once(timeout)

        try:
            plugin, args = self.mainqueue.get(False)
            plugin.handle(*args, dbconn=self.dbconn)
            self.mainqueue.task_done()
        except Empty:
            pass

    def quit(self, msg=None):
        print "quit called"
        self.quit_called = True
        self.core.reactor.disconnect_all(msg or "bye-bye")

    def restart(self, msg=None):
        print "restart called"
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
                            "operators" : [ ]
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
                q = self.tehbot.mainqueue if plugin.mainthreadonly else self.tehbot.queue
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
        plugins.myprint("%s: connected to %s" % (connection.name, connection.server))
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
            plugins.myprint("%s: joining %s" % (connection.name, mchans))
            connection.send_raw("JOIN %s" % mchans)

        if channels_to_part:
            mchans = ",".join(channels_to_part)
            plugins.myprint("%s: parting %s" % (connection.name, mchans))
            connection.part(channels_to_part)

    def on_disconnect(self, connection, event):
        if self.tehbot.quit_called:
            return

        delay = 120
        plugins.myprint("%s: lost connection" % (connection.name))
        plugins.myprint("%s: reconnecting in %d seconds" % (connection.name, delay))

        with self.tehbot.core.reactor.mutex:
            for cmd in self.tehbot.core.reactor.scheduler.queue[:]:
                if isinstance(cmd.target, functools.partial) and cmd.target.args == ('keep-alive',) and cmd.target.func.__self__ == connection:
                    print "removing cmd", cmd
                    self.tehbot.core.reactor.scheduler.queue.remove(cmd)

        self.tehbot.core.reactor.scheduler.execute_after(delay, functools.partial(self.tehbot.reconnect, connection))

    def on_join(self, connection, event):
        plugins.myprint("%s: %s: %s joined" % (connection.name, event.target, event.source.nick))
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
        plugins.myprint("%s: %s: %s left" % (connection.name, event.target, event.source.nick))
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
        plugins.myprint("%s: %s has quit (%s)" % (connection.name, event.source.nick, event.arguments[0]))
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

        plugins.myprint("%s: %s: *%s %s" % (connection.name, target, nick, msg))

    def react_to_command(self, connection, event, msg, plugin=None):
        if not msg:
            return

        cmd = msg.split(" ", 1)[0]
        args = msg[len(cmd) + 1:]

        if not plugin and cmd in self.tehbot.cmd_handlers:
            plugin = self.tehbot.cmd_handlers[cmd]

        if plugin:
            q = self.tehbot.mainqueue if plugin.mainthreadonly else self.tehbot.queue
            q.put((plugin, (connection, event, {"cmd":cmd, "args":args})))

    def on_pubmsg(self, connection, event):
        msg = event.arguments[0]
        typ = self.tehbot.settings.log_type(connection.name, event.target)
        plugins.logmsg(time.time(), connection.name, event.target, event.source.nick, msg, False, typ, self.tehbot.dbconn)
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
        plugins.logmsg(time.time(), connection.name, event.source.nick, event.source.nick, msg, False, 1, self.tehbot.dbconn)
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
        plugins.myprint("%s: %s is now known as %s" % (connection.name, oldnick, newnick))
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
