import plugins

def roulette(connection, channel, nick, msg):
    if msg.find("BANG") > -1 or msg.find("BOOM") > -1:
        plugins.say(connection, channel, "!roulette")

#plugins.register_channel_handler(roulette)
