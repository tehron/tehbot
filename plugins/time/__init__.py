import plugins
import datetime, time

def _time(connection, channel, nick, cmd, args):
    """Print the seconds since last chall"""
    last = time.mktime(datetime.date(2013, 10, 11).timetuple())
    plugins.say(connection, channel, "%d seconds since last chall" % int(time.time() - last))

plugins.register_pub_cmd("time", _time)
