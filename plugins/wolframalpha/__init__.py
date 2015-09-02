import plugins
import wolframalpha
import settings

client = wolframalpha.Client(settings.wolframalpha_app_id)

def waquery(connection, channel, nick, cmd, args):
    if not args:
        return

    txt = "\x0303[Wolfram|Alpha]\x03 "

    try:
        res = None
        misc = []
        for p in client.query(args).pods:
            if p.id == "Input":
                inp = " | ".join(p.text.splitlines())
            elif p.id == "Result":
                res = "Result: " + p.text
                found = ""
            elif p.title and p.text:
                misc.append("%s: %s" % (p.title, " | ".join(p.text.splitlines())))
                found = ""

        txt += inp + "\n"
        txt += found

        if res:
            txt += res + "\n"

        if misc:
            txt += plugins.shorten(", ".join(misc), 300)

    except Exception:
        txt += "No results"

    plugins.say(connection, channel, txt)

plugins.register_pub_cmd("wa", waquery)
