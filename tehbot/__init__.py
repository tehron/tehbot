import irc.client
import plugins
import impl
import sys
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
            Tehbot.print_exc()
            self.newimpl = None
            return e

    def finalize(self):
        if self.newimpl is None:
            return

        try:
            self.impl and self.impl.deinit()
        except:
            Tehbot.print_exc()

        try:
            self.newimpl.postinit()
        except:
            Tehbot.print_exc()

        self.impl = self.newimpl
        self.newimpl = None

    @staticmethod
    def print_exc():
        exctype, value = sys.exc_info()[:2]
        print u"%s: %s" % (Tehbot.ts(), exctype)
        traceback.print_exc()

    @staticmethod
    def ts():
        return time.strftime('%Y-%m-%d %H:%M:%S')
