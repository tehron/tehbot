import plugins

shotmap = {}

def shots(connection, channel, nick, cmd, args):
    plugins.say_nick(connection, channel, nick, "|~|")
    plugins.say_nick(connection, channel, nick, "+-+  Cheers, %s!" % nick)
    if not shotmap.has_key(nick):
        shotmap[nick] = 0
    shotmap[nick] += 1

def shoot(connection, channel, nick, cmd, args):
    if not shotmap.has_key(nick) or shotmap[nick] == 0:
        return plugins.say_nick(connection, channel, nick, "Your glass is empty!")

    shotmap[nick] -= 1
    plugins.say_nick(connection, channel, nick, "| |  AH!")
    plugins.say_nick(connection, channel, nick, "+-+  Want another one, %s?" % nick)

plugins.register_pub_cmd("shots", shots)
plugins.register_pub_cmd("shoot", shoot)
