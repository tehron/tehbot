import sys
import os
import select
import psutil
import threading
import traceback
from tehbot import *
import irc.client
from Queue import Queue, Empty

def kbdinput():
    def process_cmd():
        while True:
            r, _, _ = select.select([sys.stdin], [], [], 0.1)
            if bot.quit_called:
                return False

            if r:
                break

        inp = sys.stdin.readline()

        if inp[0] == "/": # command mode
            tmp = inp[1:].split(None, 1)

            if len(tmp) > 0:
                cmd = tmp[0].lower()
                args = tmp[1] if len(tmp) > 1 else None
                queue.put(("kbd_" + cmd, args))

        return True

    while True:
        try:
            if not process_cmd():
                break
        except EOFError:
            break
        except:
            Tehbot.print_exc()


queue = Queue()
kbdthread = threading.Thread(target=kbdinput)

try:
    bot = Tehbot()
except:
    Tehbot.print_exc()
    sys.exit(-1)

if not bot.impl:
    sys.exit(-1)

try:
    bot.connect()
except:
    Tehbot.print_exc()


kbdthread.start()

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
        bot.process_once(0.05)

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
    except irc.client.ServerNotConnectedError:
        bot.restart_called = True
        break
    except:
        Tehbot.print_exc()

kbdthread.join()



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
