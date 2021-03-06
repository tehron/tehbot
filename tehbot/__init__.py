import sys
import traceback
import inspect
import time
import importlib
import irc.client
import tehbot.plugins as plugins
import tehbot.impl as impl
import tehbot.model as model

class Tehbot:
    def __init__(self):
        self.reactor = irc.client.Reactor()
        self.impl = None
        res = self.reload()
        self.finalize()

        if res is not None:
            mod, lineno, exc = res
            msg = "Error in %s(%d): %s" % (mod, lineno, plugins.Plugin.exc2str(exc))
            raise exc

    def __getattr__(self, attr):
        return getattr(self.impl, attr)

    def reload(self):
        try:
            importlib.reload(model)
            importlib.reload(impl)
            importlib.reload(plugins)
            self.newimpl = impl.TehbotImpl(self)
            modules = self.newimpl.gather_modules()
            for m in modules:
                try:
                    importlib.reload(m)
                except ImportError:
                    pass
            self.newimpl.load_plugins(modules)
        except Exception as e:
            Tehbot.print_exc()
            self.newimpl = None
            frm = inspect.trace()[-1]
            mod = inspect.getmodule(frm[0])
            lineno = frm[0].f_lineno
            try:
                modname = mod.__name__
            except:
                modname = "<unknown module>"
            return (modname, lineno, e)

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
        del self.newimpl

    @staticmethod
    def print_exc(handler="GLOBAL"):
        exctype, value = sys.exc_info()[:2]
        print("%s %s: %s" % (handler, Tehbot.ts(), exctype))
        traceback.print_exc()

    @staticmethod
    def ts():
        return time.strftime('%Y-%m-%d %H:%M:%S')
