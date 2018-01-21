import irc.client
from Queue import Queue
import plugins
import impl
import traceback
import time

class Tehbot:
    def __init__(self):
        self.reactor = irc.client.Reactor()
        self.queue = Queue(maxsize=0)
        self.quit_called = False
        self.workers = []
        self.impl = impl.TehbotImpl(self)
        self.impl.collect_plugins()
        self.reactor.add_global_handler("all_events", self.impl.dispatcher.dispatch, -10)

    def __getattr__(self, attr):
        return getattr(self.impl, attr)

    def reload(self):
        oldimpl = self.impl
        try:
            reload(settings)
            reload(impl)
            reload(plugins)
            self.impl = impl.TehbotImpl(self)
            modules = self.impl.gather_modules()
            print modules
            map(reload, modules)
            self.impl.collect_plugins()
            self.reactor.remove_global_handler("all_events", oldimpl.dispatcher.dispatch)
            self.reactor.add_global_handler("all_events", self.impl.dispatcher.dispatch, -10)
        except Exception as e:
            self.impl = oldimpl
            traceback.print_exc()
            return e

    @staticmethod
    def ts():
        return time.strftime('%Y-%m-%d %H:%M:%S')
