import plugins
import wolframalpha

APP_ID = "your api id here"

client = wolframalpha.Client(APP_ID)

def waquery(connection, channel, nick, cmd, args):
    if not args:
        return

    res = client.query(args)
    try:
        txt = next(res.results).text
    except StopIteration:
        txt = "No results"
    plugins.say(connection, channel, txt)

plugins.register_pub_cmd("wa", waquery)
