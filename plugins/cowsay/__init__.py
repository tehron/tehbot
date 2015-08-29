import plugins
from cowsay import cowsay

def mycowsay(connection, channel, nick, cmd, args):
    if not args or not args.strip():
        return

    plugins.say(connection, channel, cowsay(args.strip()))

plugins.register_op_cmd("cowsay", mycowsay)
