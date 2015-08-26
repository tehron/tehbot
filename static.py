import irc.client
import plugins
import settings
import dynamic
import functools
from Queue import Queue, Empty
from threading import Thread

class Tehbot:
    def __init__(self):
        self.reactor = irc.client.Reactor()
        self.quit_called = False
        self.is_reloading = False
        self.dispatcher = None
        self._init()
        self.queue = Queue(maxsize=0)
        for i in xrange(10):
            worker = Thread(target=self._process)
            worker.start()

    def _init(self):
        if self.dispatcher:
            self.reactor.remove_global_handler("all_events", self.dispatcher.dispatch)
        self.dispatcher = dynamic.Dispatcher(self)
        self.reactor.add_global_handler("all_events", self.dispatcher.dispatch, -10)
        print "pub cmd handlers:", plugins.pub_cmd_handlers
        print "channel handlers:", plugins.channel_handlers

    def _process(self):
        while True:
            try:
                fnc, args = self.queue.get(timeout=1)
                if not self.is_reloading:
                    fnc(*args)
                self.queue.task_done()
            except Empty:
                pass
            if self.quit_called:
                return
            
    def connect(self):
        for c in settings.connections:
            conn = self.reactor.server()
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
        
    def reload(self):
        self.is_reloading = True
        res = None
        try:
            reload(settings)
            reload(dynamic)
            plugins.plugins_reload(),
            self._init()
        except Exception as e:
            res = e
        self.is_reloading = False
        return res

    def quit(self, msg="bye-bye"):
        print "quit called"
        self.quit_called = True
        self.reactor.disconnect_all(msg)
        raise SystemExit
