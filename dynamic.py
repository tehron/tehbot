import plugins
import settings
import functools
import irc.schedule
import irc.client
import threading

class Dispatcher:
    def __init__(self, tehbot):
        self.tehbot = tehbot
        self.operator_cmd_handlers = {
            "reload" : self.reload,
            "quit" : self.quit,
            "raw" : self.raw
        }

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
        self.tehbot.reactor.execute_delayed(10, self.join_channels, (connection,))

    def join_channels(self, connection):
        for ch in connection.params[6]:
            connection.locks[ch] = threading.Lock()

        mchans = ",".join(connection.params[6])
        plugins.myprint("%s: joining %s" % (connection.params[0], mchans))
        connection.send_raw("JOIN %s" % mchans)

    def on_disconnect(self, connection, event):
        if self.tehbot.quit_called:
            return

        delay = 120
        plugins.myprint("%s: lost connection" % (connection.params[0]))
        plugins.myprint("%s: reconnecting in %d seconds" % (connection.params[0], delay))

        with self.tehbot.reactor.mutex:
            for cmd in self.tehbot.reactor.delayed_commands[:]:
                if cmd.function.func.args == ('keep-alive',) and cmd.function.func.func.__self__ == connection:
                    print "removing cmd", cmd
                    self.tehbot.reactor.delayed_commands.remove(cmd)

        self.tehbot.reactor.execute_delayed(delay, self.tehbot.reconnect, (connection,))

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

        if irc.client.is_channel(event.target):
            target = event.target
        else:
            target = event.source.nick

        nick = event.source.nick

        print target, nick

        if cmd in self.operator_cmd_handlers:
            if not self.is_op(connection, event.source):
                return plugins.say_nick(connection, target, nick, "You are no operator.")
            self.operator_cmd_handlers[cmd](connection, target, nick, cmd, args)
        elif cmd in plugins.operator_cmd_handlers:
            if not self.is_op(connection, event.source):
                return plugins.say_nick(connection, target, nick, "You are no operator.")
            self.tehbot.queue.put((plugins.operator_cmd_handlers[cmd], (connection, target, nick, cmd, args)))
        elif irc.client.is_channel(event.target):
            if cmd in plugins.pub_cmd_handlers:
                self.tehbot.queue.put((plugins.pub_cmd_handlers[cmd], (connection, target, nick, cmd, args)))
        else:
            print "priv"
            if cmd in plugins.priv_cmd_handlers:
                print "priv cmd found"
                self.tehbot.queue.put((plugins.priv_cmd_handlers[cmd], (connection, target, nick, cmd, args)))

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
            for h in plugins.channel_handlers:
                h(connection, channel, nick, msg)

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

    def reload(self, connection, channel, nick, cmd, args):
        res = self.tehbot.reload()
        if res is None:
            plugins.say(connection, channel, "Okay")
        else:
            plugins.say(connection, channel, "Error: %s" % res)

    def quit(self, connection, channel, nick, cmd, args):
        self.tehbot.quit(args or "bye-bye")

    def raw(self, connection, channel, nick, cmd, args):
        if not args:
            return

        connection.send_raw(args)
