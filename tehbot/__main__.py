import readline
import sys
import os
import psutil
import threading
import traceback
from tehbot import *
import irc.client
from Queue import Queue, Empty

def kbdinput():
    while True:
        try:
            inp = raw_input().strip()
            if inp == "":
                continue
            if inp[0] == "/": # command mode
                tmp = inp[1:].split(None, 1)

                if len(tmp) > 0:
                    cmd = tmp[0].lower()
                    args = tmp[1] if len(tmp) > 1 else None
                    queue.put(("kbd_" + cmd, args))

        except EOFError, SystemExit:
            break
        except:
            Tehbot.print_exc()


queue = Queue()
kbdthread = threading.Thread(target=kbdinput)
kbdthread.daemon = True
kbdthread.start()


try:
    bot = Tehbot()
    bot.connect()
except:
    Tehbot.print_exc()
    try:
        bot.quit()
    finally:
        raise SystemExit


#import plugins
#if not plugins.is_windows():
    #def sighandler(signum, frame):
        #bot.reload()

    #import signal
    #signal.signal(signal.SIGHUP, sighandler)

while True:
    if bot.quit_called:
        break

    try:
        bot.process_once(0.2)

        try:
            cmd, args = queue.get(False)
        except Empty:
            continue

        queue.task_done()

        try:
            func = getattr(bot, cmd)
        except AttributeError as e:
            print "Unknown command:", cmd
            continue

        func(args)
    except KeyboardInterrupt:
        bot.quit()
    except:
        Tehbot.print_exc()

if bot.restart_called:
    try:
        p = psutil.Process(os.getpid())
        for handler in p.open_files() + p.connections():
            os.close(handler.fd)
    except:
        Tehbot.print_exc()

    python = sys.executable
    # somehow "python -m tehbot" gets turned into "python -c ..."!?
    #os.execl(python, python, *sys.argv)
    os.execl(python, python, '-m', 'tehbot')
