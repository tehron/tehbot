import plugins
import psutil
import os
import time

def format_time(ts):
    years = int(ts / 31536000)
    ts -= 31536000 * years
    days = int(ts / 86400)
    ts -= 86400 * days
    hours = int(ts / 3600)
    ts -= 3600 * hours
    mins = int(ts / 60)
    ts -= 60 * mins
    secs = int(ts)

    if days:
        out = "%dd %02d:%02d" % (days, hours, mins)
    elif mins >= 15:
        out = "%02d:%02d" % (hours, mins)
    else:
        out = "00:%02d:%02d" % (mins, secs)

    return out

def get_git_version():
    from subprocess import Popen, PIPE
    import re
    out, err = Popen(["git", "log", "-n", "1"], stdout=PIPE).communicate()
    return re.search(r'([0-9A-Fa-f]{40})', out).group(0)

def botstats(connection, target, nick, cmd, args):
    """Shows various information about tehbot"""
    txt = "\x0303[tehbot]\x03 "

    stats = []
    stats.append("Version: git %s" % get_git_version()[:10])

    proc = psutil.Process(os.getpid())
    stats.append("Running Time: %s" % format_time(time.time() - proc.create_time()))

    stats.append("Memory Usage: %d kB" % (proc.memory_info().rss / 1024))

    stats.append("Nr. of Threads: %d" % (proc.num_threads()))

    plugins.say(connection, target, txt + ", ".join(stats))

plugins.register_cmd("botstats", botstats)
