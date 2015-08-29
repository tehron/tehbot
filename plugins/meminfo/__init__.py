import plugins
import os
from subprocess import Popen, PIPE

def meminfo_win():
    info = Popen('tasklist /fo list /fi "pid eq %d"' % os.getpid(), shell=True, stdout=PIPE).communicate()[0]
    info = info.strip()
    minfo = info.splitlines()[-1]
    return minfo.split(":", 1)[-1].strip()

def meminfo(connection, channel, nick, cmd, args):
    if plugins.is_windows():
        minfo = meminfo_win()
    else:
        import resource
        minfo = "%d kB" % resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    plugins.say(connection, channel, "Current memory usage: %s" % minfo)

plugins.register_pub_cmd("meminfo", meminfo)
