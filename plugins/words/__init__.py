import plugins
import random

def reverse(connection, channel, nick, cmd, args):
    """Gives back the string reversed"""
    print args,"->",args[::-1]
    txt = plugins.myfilter(args[::-1])

    plugins.say_nick(connection, channel, nick, txt)

def say(connection, channel, nick, cmd, args):
    print "say", args
    if not args:
        return
    plugins.say_nick(connection, channel, nick, plugins.myfilter(args))

def solve(connection, channel, nick, cmd, args):
    if not args:
        return
    if args == "https://www.sabrefilms.co.uk/revolutionelite/chall-for-tehron.php":
        plugins.say_nick(connection, channel, nick, "muffins")
    else:
        seq = ["nice try :P", "you wish", "haha", "ok. ...wait, aren't you %s?" % nick]
        plugins.say_nick(connection, channel, nick, random.choice(seq))

beers = 100
def beer(connection, channel, nick, cmd, args):
    global beers
    if beers == 0:
        return plugins.me(connection, channel, "has no beer left :(")

    if not args or not args.strip():
        plugins.me(connection, channel, "passes 1 of %d bottles of cold beer around to %s" % (beers, nick))
    else:
        recv = args.split()[0].strip()
        plugins.me(connection, channel, "and %s pass 1 of %d bottles of cold beer around to %s" % (nick, beers, recv))
    beers -= 1

plugins.register_pub_cmd("reverse", reverse)
plugins.register_pub_cmd("say", say)
plugins.register_pub_cmd("doublereverse", say)
plugins.register_pub_cmd("solve", solve)
plugins.register_pub_cmd("beer", beer)
