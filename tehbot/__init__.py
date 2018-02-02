import irc.client
import plugins
import impl
import traceback
import time
import settings

class Tehbot:
    def __init__(self):
        self.reactor = irc.client.Reactor()
        self.impl = None
        self.reload()
        self.finalize()

    def __getattr__(self, attr):
        return getattr(self.impl, attr)

    def reload(self):
        try:
            reload(settings)
            reload(impl)
            reload(plugins)
            self.newimpl = impl.TehbotImpl(self)
            plugins._tehbot = self.newimpl
            modules = self.newimpl.gather_modules()
            map(reload, modules)
            self.newimpl.collect_plugins()
        except Exception as e:
            print Tehbot.ts()
            traceback.print_exc()
            self.newimpl = None
            return e

    def finalize(self):
        if self.newimpl is None:
            return

        try:
            self.impl and self.impl.deinit()
        except:
            print Tehbot.ts()
            traceback.print_exc()

        try:
            self.newimpl.postinit()
        except:
            print Tehbot.ts()
            traceback.print_exc()

        self.impl = self.newimpl
        self.newimpl = None

    @staticmethod
    def ts():
        return time.strftime('%Y-%m-%d %H:%M:%S')
