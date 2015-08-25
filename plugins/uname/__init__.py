import plugins
from subprocess import Popen, PIPE

def uname(connection, channel, nick, cmd, args):
    if plugins.is_windows():
        p = Popen(["ver"], stdout=PIPE, shell=True).communicate()[0].strip()
    else:
        p = Popen(["uname", "-a"], stdout=PIPE).communicate()[0].strip()
    plugins.say(connection, channel, "%s: %s" % (nick, p))

plugins.register_pub_cmd("uname", uname)
