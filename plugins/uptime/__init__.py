import plugins

def get_uptime():
    if plugins.is_windows():
        import ctypes
        import time
        millis = ctypes.WinDLL("kernel32").GetTickCount64()
        days = millis / 86400000
        millis -= 86400000 * days
        hours = millis / 3600000
        millis -= 3600000 * hours
        mins = millis / 60000
        upstr = "%02d:%02d" % (hours, mins)
        if days != 0:
            upstr = "%d days, %s" % (days, upstr)
        return "%s up %s" % (time.strftime("%H:%M:%S"), upstr)
    else:
        from subprocess import Popen, PIPE
        return Popen(["uptime"], stdout=PIPE).communicate()[0].strip()

def uptime(connection, channel, nick, cmd, args):
    """Prints the uptime of tehbot's host."""
    up = get_uptime()
    plugins.say(connection, channel, "%s: %s" % (nick, up))

plugins.register_cmd("uptime", uptime)
