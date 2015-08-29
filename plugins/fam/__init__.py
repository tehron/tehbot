import plugins

def fam(connection, channel, nick, cmd, args):
    """This help at fam"""
    plugins.say(connection, channel, ".quoet fom")

plugins.register_pub_cmd("fam", fam)
