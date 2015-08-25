import plugins
import random

slaps = [
    "pulls out {victim}'s eyeballs{howmuch} and plays baseball with them.",
    "slaps {victim} around{howmuch}{withitem}."
]
slaps_extra = [
    (plugins.me, "hops on a jet and flies away."),
    (plugins.say, "I pitty the fool that doesnt slap back!")
]
slapitems = open("plugins/slap/slaps.txt").read().splitlines()

#self.privmsg(target, "\001ACTION %s\001" % (action))
#self.send_raw("PRIVMSG %s :\001ACTION %s\001" % (target, action))
#self.send_raw("PRIVMSG %s :%s" % (target, text))
def actionAndText(target, action, text):
    a = "PRIVMSG %s :\001ACTION %s\001" % (target, action)
    a += "\r\n"
    a += "PRIVMSG %s :%s" % (target, text)
    print a
    plugins.conn.send_raw(a)

def slap(connection, channel, nick, cmd, args):
    if not args:
        return
    
    victim = args.split()[0][:25]
    if random.randint(0, len(slapitems)) == len(slapitems):
        slap = slaps[0]
    else:
        slap = slaps[1]
    txt = slap.format(victim=plugins.myfilter(victim), howmuch=random.choice(["", " a bit", " a little bit"]), withitem=random.choice(slapitems))
    plugins.me(connection, channel, txt)

    if random.random() < 0.25:
        func, txt = random.choice(slaps_extra)
        func(connection, channel, txt)

def slap2(connection, channel, victim):
    plugins.me(connection, channel, "slaps %s around a bit with a Piece of bacon" % victim)
    plugins.say(connection, channel, "Hey %s Eat some pork!" % victim)

def livinslap(connection, channel, nick, cmd, args):
    if args:
        plugins.say(connection, channel, "no")
        return
    else:
        slap2(connection, channel, "livinskull")

#plugins.register_channel_handler(reverse)
plugins.register_pub_cmd("slap", slap)
plugins.register_pub_cmd("livinslap", livinslap)
