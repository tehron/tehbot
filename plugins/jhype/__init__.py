import plugins
import random

max = 25

def jhype(connection, channel, nick, cmd, args):
    nr = random.randint(1, max)
    if args:
        what = args.split()[0].strip()
        if what == "bikini":
            nr = 2
        elif what == "latest":
            nr = max
        elif what == "naked":
            return plugins.say(connection, channel, "You're not old enough or have no age specified")
    plugins.say(connection, channel, "Picture of Jhype: https://www.sabrefilms.co.uk/store/j%d.jpg" % nr)

plugins.register_pub_cmd("jhype", jhype)
