import sys
import os
import signal
import platform
import psutil
import threading
import traceback
from tehbot import *
import irc.client
from Queue import Queue, Empty
import cmd

class CommandLine(cmd.Cmd):
    def do_config(self, line):
        cliqueue.put(("kbd_config", line))

    def do_stats(self, line):
        cliqueue.put(("kbd_stats", line))

    def do_quit(self, line):
        cliqueue.put(("kbd_quit", line))

    def do_reload(self, line):
        cliqueue.put(("kbd_reload", line))

    def do_EOF(self, line):
        self.do_quit(line)

    def complete_config(self, text, line, start_index, end_index):
        handlers = []
        arr = line[:start_index].split()
        l = " ".join(arr)

        if l == "config":
            handlers = ["global", "connection", "channel", "plugin"]
        elif l == "config global":
            handlers = ["set", "unset", "add", "remove", "show"]
        elif l == "config global set" or l == "config global show":
            handlers = ["botname", "username", "ircname", "cmdprefix", "privpassword", "nr_worker_threads"]
        elif l == "config global unset":
            handlers = ["privpassword"]
        elif l == "config global add" or l == "config global remove":
            handlers = ["connection"]
        elif l == "config global remove connection":
            handlers = bot.settings.connections().keys()
        elif l.startswith("config connection"):
            conns = bot.settings.connections().keys()
            if len(arr) == 2:
                handlers = conns
            elif len(arr) == 3:
                handlers = ["set", "unset", "add", "remove", "show"]
            elif len(arr) == 4:
                if l.endswith(" set"):
                    handlers = ["name", "host", "port", "ssl", "botname", "password", "enabled"]
                elif l.endswith(" unset"):
                    handlers = ["botname", "password"]
                elif l.endswith(" add") or l.endswith(" remove"):
                    handlers = ["channels", "operators"]
                elif l.endswith(" show"):
                    handlers = ["host", "port", "ssl", "botname", "password", "enabled", "channels", "operators"]
        elif l.startswith("config channel"):
            conns = bot.settings.connections()
            if len(arr) == 2:
                handlers = conns.keys()
            elif len(arr) == 3:
                channels = conns[arr[-1]]["channels"]
                handlers = channels
            elif len(arr) == 4:
                handlers = ["set", "unset", "show"]
            elif len(arr) == 5:
                if l.endswith(" set") or l.endswith(" unset") or l.endswith(" show"):
                    handlers = ["logging"]
        elif l.startswith("config plugin"):
            plugins = [p.__class__.__name__ for p in bot.plugins]
            if len(arr) == 2:
                handlers = plugins
            elif len(arr) == 3:
                handlers = ["set", "show"]
            elif len(arr) == 4:
                if l.endswith(" set") or l.endswith(" show"):
                    handlers = ["enabled"]

        if not text:
            return handlers
        
        return [h for h in handlers if h.startswith(text)]

    def emptyline(self):
        pass

def botloop():
    global bot, restart

    try:
        bot = Tehbot()
    except:
        Tehbot.print_exc()

    if bot:
        try:
            bot.connect()
        except:
            Tehbot.print_exc()

        while not bot.quit_called:
            try:
                process_cliqueue()
                bot.process_once(0.2)
            except:
                Tehbot.print_exc()

        restart = bot.restart_called

    os.kill(os.getpid(), signal.SIGABRT) # interrupt raw_input() used in cli.cmdloop()!

def process_cliqueue():
    try:
        cmd, args = cliqueue.get(False)
    except Empty:
        return

    cliqueue.task_done()

    try:
        func = getattr(bot, cmd)
    except AttributeError as e:
        print "Unknown command:", cmd
        return

    func(args)

def sighandler(signum, frame):
    raise SystemExit()




print "Initializing tehbot..."
cliqueue = Queue()
cli = CommandLine()
cli.prompt = "tehbot> "
signal.signal(signal.SIGABRT, sighandler)
bot, restart = None, False
botthread = threading.Thread(target=botloop)
botthread.start()

while True:
    try:
        cli.cmdloop()
    except KeyboardInterrupt:
        print "^C"
    except SystemExit:
        break # some signal interrupted readline() in raw_input()

botthread.join()

if restart:
    try:
        p = psutil.Process(os.getpid())
        for handler in p.open_files() + p.connections():
            os.close(handler.fd)
    except:
        Tehbot.print_exc()

    python = sys.executable
    os.execl(python, python, '-m', 'tehbot')
