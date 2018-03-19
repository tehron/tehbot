import plugins
import settings
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
        self.cmd_handlers = {}
        self.channel_handlers = []
        self.channel_join_handlers = []
        self.pollers = []
        self.announcers = []
        self.queue = Queue(maxsize=0)
        self.workers = []
        self.quit_called = False
        self.dbfile = os.path.join(os.path.dirname(__file__), "../tehbot.sqlite")
        self.dbconn = sqlite3.connect(self.dbfile)
        self.mainqueue = Queue()
        self.privusers = defaultdict(set)
        self.privqueue = defaultdict(Queue)

    def collect_plugins(self):
        plugins.collect()
        print " command handlers:", sorted(self.cmd_handlers)
        print " channel handlers:", sorted(h.__class__.__name__ for h in self.channel_handlers)
        print "chn join handlers:", sorted(h.__class__.__name__ for h in self.channel_join_handlers)
        print "          pollers:", sorted(h.__class__.__name__ for h in self.pollers)
        print "       announcers:", sorted(h.__class__.__name__ for h in self.announcers)

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
            except:
                traceback.print_exc()

            if self.quit_called:
                break

        dbconn.close()

    def start_workers(self):
        while len(self.workers) < settings.nr_worker_threads:
            worker = threading.Thread(target=self._process)
            self.workers.append(worker)
            worker.start()

    def _kill_workers(self):
        while self.workers:
            _terminate_thread(self.workers.pop())

    def _get_connection(self, name):
        for c in self.core.reactor.connections:
            if c.name == name:
                return c
        return None

    def connect(self):
        for name in settings.connections:
            print "Connecting to %s" % name
            conn = self.core.reactor.server()
            conn.name = name
            conn.locks = dict()
            self.reconnect(conn)

    def reconnect(self, connection):
        params = settings.connections[connection.name]

        if params.use_ssl:
            import ssl
            factory = irc.client.connection.Factory(wrapper=ssl.wrap_socket)
        else:
            factory = irc.client.connection.Factory()
        connection.connect(params.host, params.port, settings.bot_name, params.bot_password, settings.bot_name, settings.bot_name, factory)
        connection.set_rate_limit(2)
        connection.set_keepalive(60)

    def process_once(self, timeout):
        self.core.reactor.process_once(timeout)

        try:
            plugin, args = self.mainqueue.get(False)
            plugin.handle(*args, dbconn=self.dbconn)
            self.mainqueue.task_done()
        except Empty:
            pass
        except:
            traceback.print_exc()

    def quit(self, msg=None):
        print "quit called"
        self.quit_called = True
        self.core.reactor.disconnect_all(msg or "bye-bye")
        raise SystemExit

    def kbd_reload(self, args):
        self.core.reload()
        self.core.finalize()

    def kbd_quit(self, args):
        self.quit(args)

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


class Dispatcher:
    def __init__(self, tehbot):
        self.tehbot = tehbot

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
        params = settings.connections[connection.name]

        for t, s in params.ops:
            if t == "nickserv" and s == account:
                self.tehbot.privusers[connection].add(nick)
                break

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
        params = settings.connections[connection.name]
        for ch in params.channels:
            connection.locks[ch] = threading.Lock()

        mchans = ",".join(params.channels)
        plugins.myprint("%s: joining %s" % (connection.name, mchans))
        connection.send_raw("JOIN %s" % mchans)

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

        if nick == settings.bot_name:
            return

        for h in self.tehbot.channel_join_handlers:
            self.tehbot.queue.put((h, (connection, event, {})))

    def on_part(self, connection, event):
        plugins.myprint("%s: %s: %s left" % (connection.name, event.target, event.source.nick))
        try:
            self.tehbot.privusers[connection].remove(event.source.nick)
        except:
            pass

    def on_quit(self, connection, event):
        plugins.myprint("%s: %s has quit (%s)" % (connection.name, event.source.nick, event.arguments[0]))

        # reconquer our nick!
        if event.source.nick == settings.bot_name:
            connection.nick(settings.bot_name)

        try:
            self.tehbot.privusers[connection].remove(event.source.nick)
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

    def react_to_command(self, connection, event, msg):
        if not msg:
            return

        cmd = msg.split(" ", 1)[0]
        args = msg[len(cmd) + 1:]

        if cmd in self.tehbot.cmd_handlers:
            plugin = self.tehbot.cmd_handlers[cmd]
            q = self.tehbot.mainqueue if plugin.mainthreadonly else self.tehbot.queue
            q.put((plugin, (connection, event, {"cmd":cmd, "args":args})))

    def on_pubmsg(self, connection, event):
        msg = event.arguments[0]
        plugins.logmsg(time.time(), connection.name, event.target, event.source.nick, msg, False, self.tehbot.dbconn)

        if msg:
            if msg[0] == settings.cmd_prefix:
                self.react_to_command(connection, event, msg[1:])

            for h in self.tehbot.channel_handlers:
                self.tehbot.queue.put((h, (connection, event, {"msg":msg})))

    def on_privmsg(self, connection, event):
        msg = event.arguments[0]
        plugins.logmsg(time.time(), connection.name, event.source.nick, event.source.nick, msg, False, self.tehbot.dbconn)

        if msg:
            if msg[0] == settings.cmd_prefix:
                self.react_to_command(connection, event, msg[1:])

    def on_nick(self, connection, event):
        oldnick = event.source.nick
        newnick = event.target
        plugins.myprint("%s: %s is now known as %s" % (connection.name, oldnick, newnick))

        # reconquer our nick!
        if oldnick == settings.bot_name:
            connection.nick(settings.bot_name)

        try:
            self.tehbot.privusers[connection].remove(event.source.nick)
        except:
            pass

    def on_396(self, connection, event):
        # TODO join channel before 5s wait time is over
        pass
