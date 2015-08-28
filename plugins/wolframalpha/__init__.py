import plugins
import wolframalpha
import settings

client = wolframalpha.Client(settings.wolframalpha_app_id)

def waquery(connection, channel, nick, cmd, args):
    if not args:
        return

    txt = "\x0303[Wolfram|Alpha]\x03 "

    try:
        for p in client.query(args).pods:
            if p.id == "Input":
                inp = p.text
            elif p.id == "Result":
                res = p.text
        txt += inp + "\n" + res
    except Exception:
        txt += "No results"
        
    plugins.say(connection, channel, txt)

plugins.register_pub_cmd("wa", waquery)
