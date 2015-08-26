#!/usr/bin/env python
stopme = False
reloadme = False

def kbdinput(tehbot):
    global stopme, reloadme
    channel = "#revolutionelite"
    while True:
        try:
            inp = raw_input().strip()
            if inp == "":
                continue
            if inp[0] == "/": # command mode
                tmp = inp[1:].split(" ")
                cmd = tmp[0].upper()
                args = tmp[1:]
                if cmd == "QUIT":
                    stopme = True
                elif cmd == "CHANNEL":
                    print "channel you're writing to: %s" % channel
                elif cmd == "RELOAD":
                    reloadme = True
        except EOFError:
            break


# main loop
import static
bot = static.Tehbot()

import threading
kbdthread = threading.Thread(target=kbdinput, args=(bot,))
kbdthread.daemon = True
kbdthread.start()

import sys
try:
    bot.connect()
except KeyboardInterrupt:
    bot.quit()

import plugins
if not plugins.is_windows():
    def sighandler(signum, frame):
        bot.reload()
        
    import signal
    signal.signal(signal.SIGHUP, sighandler)

import traceback
import irc.client

while True:
    try:
        if stopme:
            bot.quit()
        if reloadme:
            bot.reload()
        bot.reactor.process_once(0.2)
    except KeyboardInterrupt:
        bot.quit()
    except SystemExit:
        break
    except irc.client.ServerConnectionError as e:
        print e
    except:
        e = sys.exc_info()
        print "Exception handler in tehbot.py", e
        traceback.print_tb(e[2])
