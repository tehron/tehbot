import sys
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
            print Tehbot.ts()
            traceback.print_exc()


queue = Queue()
kbdthread = threading.Thread(target=kbdinput)
kbdthread.daemon = True
kbdthread.start()


try:
    bot = Tehbot()
    bot.connect()
except:
    print Tehbot.ts()
    traceback.print_exc()
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
        bot.process_once(0.01)

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
    except irc.client.ServerConnectionError as e:
        print "%s: %s" % (Tehbot.ts(), e)
        traceback.print_exc()
    except:
        print Tehbot.ts()
        traceback.print_exc()
