import plugins
import settings
import irc.client
import threading
from Queue import Empty
import traceback

import os.path
from types import ModuleType

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
        self.operator_cmd_handlers = {}
        self.pub_cmd_handlers = {}
        self.priv_cmd_handlers = {}
        self.channel_handlers = []
        plugins._tehbot = self.core
        self._start_workers()

    def collect_plugins(self):
        plugins.collect()
        print "pub  cmd handlers:", sorted(self.pub_cmd_handlers.keys())
        print "priv cmd handlers:", sorted(self.priv_cmd_handlers.keys())
        print "channel  handlers:", sorted(h.__class__.__name__ for h in self.channel_handlers)

    def gather_modules(self):
        modules = set()
        _gather(plugins, modules)
        modules.remove(plugins)
        return modules

    def _process(self):
        while True:
            try:
                plugin, args = self.core.queue.get(timeout=1)
                plugin.handle(*args)
                self.core.queue.task_done()
            except Empty:
                pass
            except:
                traceback.print_exc()

            if self.core.quit_called:
                return

    def _start_workers(self):
        while len(self.core.workers) < settings.nr_worker_threads:
            worker = threading.Thread(target=self._process)
            self.core.workers.append(worker)
            worker.start()

    def connect(self):
        for c in settings.connections:
            conn = self.core.reactor.server()
            conn.params = c
            conn.locks = dict()
            self.reconnect(conn)

    def reconnect(self, connection):
        name, host, port, use_ssl, password, bot_password, channels, ops = connection.params
        if use_ssl:
            import ssl
            factory = irc.client.connection.Factory(wrapper=ssl.wrap_socket)
        else:
            factory = irc.client.connection.Factory()
        connection.connect(host, port, settings.bot_name, bot_password, settings.bot_name, settings.bot_name, factory)
        connection.set_rate_limit(4)
        connection.set_keepalive(60)

    def process_once(self, timeout):
        self.core.reactor.process_once(timeout)

    def quit(self, msg=None):
        print "quit called"
        self.core.quit_called = True
        self.core.reactor.disconnect_all(msg or "bye-bye")
        raise SystemExit


class Dispatcher:
    def __init__(self, tehbot):
        self.tehbot = tehbot

    def dispatch(self, connection, event):
        method = getattr(self, "on_" + event.type, None)
        types = [ "all_raw_messages", "pong", "ctcp", "motd", "motdstart", "endofmotd" ]
        if method:
            method(connection, event)
        elif event.type not in types:
            print event.type, event.source, event.target, event.arguments

    def is_op(self, connection, fullnick):
        ops = connection.params[7]
        val = False
        for t, s in ops:
            if t == "host" and s == fullnick.host:
                val = True
                break
            if t == "nick" and s == fullnick.nick:
                val = True
                break

        if val:
            print "%s is an operator" % (fullnick)
        else:
            print "%s is no operator" % (fullnick)

        return val

    def on_nicknameinuse(self, connection, event):
        print "%s: Nick name in use" % connection.params[0]
        print event
        connection.nick(connection.get_nickname() + "_")

    def on_welcome(self, connection, event):
        plugins.myprint("%s: connected to %s" % (connection.params[0], connection.server))
        self.tehbot.core.reactor.execute_delayed(10, self.join_channels, (connection,))

    def join_channels(self, connection):
        for ch in connection.params[6]:
            connection.locks[ch] = threading.Lock()

        mchans = ",".join(connection.params[6])
        plugins.myprint("%s: joining %s" % (connection.params[0], mchans))
        connection.send_raw("JOIN %s" % mchans)

    def on_disconnect(self, connection, event):
        if self.tehbot.core.quit_called:
            return

        delay = 120
        plugins.myprint("%s: lost connection" % (connection.params[0]))
        plugins.myprint("%s: reconnecting in %d seconds" % (connection.params[0], delay))

        with self.tehbot.core.reactor.mutex:
            for cmd in self.tehbot.core.reactor.delayed_commands[:]:
                if cmd.function.func.args == ('keep-alive',) and cmd.function.func.func.__self__ == connection:
                    print "removing cmd", cmd
                    self.tehbot.core.reactor.delayed_commands.remove(cmd)

        self.tehbot.core.reactor.execute_delayed(delay, self.tehbot.reconnect, (connection,))

    def on_join(self, connection, event):
        plugins.myprint("%s: %s joined" % (event.target, event.source.nick))

    def on_part(self, connection, event):
        plugins.myprint("%s: %s left" % (event.target, event.source.nick))

    def on_quit(self, connection, event):
        plugins.myprint("%s: %s has quit (%s)" % (connection.params[0], event.source.nick, event.arguments[0]))

        # reconquer our nick!
        if event.source.nick == settings.bot_name:
            connection.nick(settings.bot_name)

    def on_action(self, connection, event):
        msg = event.arguments[0]
        nick = event.source.nick

        if irc.client.is_channel(event.target):
            target = event.target
        else:
            target = nick

        plugins.myprint("%s: *%s %s" % (target, nick, msg))

    def react_to_command(self, connection, event, msg):
        tmp = msg.split(" ", 1)
        cmd = tmp[0]
        args = tmp[1] if len(tmp) == 2 else None
        nick = event.source.nick

        if irc.client.is_channel(event.target):
            target = event.target
        else:
            target = nick

        if cmd in self.tehbot.operator_cmd_handlers:
            if not self.is_op(connection, event.source):
                return plugins.say_nick(connection, target, nick, "You are no operator.")
            self.tehbot.operator_cmd_handlers[cmd].handle(connection, target, nick, cmd, args)
        elif irc.client.is_channel(event.target):
            if cmd in self.tehbot.pub_cmd_handlers:
                self.tehbot.core.queue.put((self.tehbot.pub_cmd_handlers[cmd], (connection, target, nick, cmd, args)))
        else:
            if cmd in self.tehbot.priv_cmd_handlers:
                self.tehbot.core.queue.put((self.tehbot.priv_cmd_handlers[cmd], (connection, target, nick, cmd, args)))

    def on_pubmsg(self, connection, event):
        nick = event.source.nick
        channel = event.target
        msg = event.arguments[0]
        plugins.myprint("%s: %s: %s" % (channel, nick, msg))

        # possible command
        if msg and msg[0] == settings.cmd_prefix:
            self.react_to_command(connection, event, msg[1:])
        elif msg:
            tmp = msg.split(" ", 1)
            tonick = tmp[0]
            args = tmp[1] if len(tmp) == 2 else None
            if (tonick == settings.bot_name or tonick[:-1] == settings.bot_name) and args:
                self.react_to_command(connection, event, args)
            for h in self.tehbot.channel_handlers:
                self.tehbot.core.queue.put((h, (connection, channel, nick, msg)))

    def on_privmsg(self, connection, event):
        nick = event.source.nick
        chat = nick
        msg = event.arguments[0]
        plugins.myprint("%s: %s: %s" % (chat, nick, msg))

        # possible command
        if msg and msg[0] == settings.cmd_prefix:
            self.react_to_command(connection, event, msg[1:])
        elif msg:
            tmp = msg.split(" ", 1)
            tonick = tmp[0]
            args = tmp[1] if len(tmp) == 2 else None
            if (tonick == settings.bot_name or tonick[:-1] == settings.bot_name) and args:
                self.react_to_command(connection, event, args)

    def on_nick(self, connection, event):
        oldnick = event.source.nick
        newnick = event.target
        plugins.myprint("%s: %s is now known as %s" % (connection.params[0], oldnick, newnick))

        # reconquer our nick!
        if oldnick == settings.bot_name:
            connection.nick(settings.bot_name)

    def on_396(self, connection, event):
        # TODO join channel before 5s wait time is over
        pass
