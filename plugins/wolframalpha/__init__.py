import plugins
import wolframalpha
import settings
import prettytable

client = wolframalpha.Client(settings.wolframalpha_app_id)

def remove_empty_columns(table, nr_cols):
    t = [[] for n in range(len(table))]
    for i in range(nr_cols):
        keep = False
        for line in table:
            if line[i]:
                keep = True
                break
        if keep:
            for j in range(len(table)):
                t[j].append(table[j][i])
    return t

def format_table(s):
    table = [[y.strip() for y in x.strip().split("|")] for x in s.splitlines()]
    print table
    nr_cols = max(map(len, table))
    table = [[x[i] if i < len(x) else "" for i in range(nr_cols)] for x in table]
    print table
    table = remove_empty_columns(table, nr_cols)
    print table

    if len(table) < 2:
        s2 = " | ".join(table[0])
        return s2

    pt = prettytable.PrettyTable()
    pt.header = False

    for line in table:
        pt.add_row(line)
    s = pt.get_string()
    return s

def waquery(connection, channel, nick, cmd, args):
    if not args:
        return

    txt = "\x0303[Wolfram|Alpha]\x03 "

    try:
        res = None
        misc = []
        for p in client.query(args).pods:
            print p.id, p.text
            if p.id == "Input":
                inp = " | ".join(p.text.splitlines())
            elif p.id == "Result" and p.text:
                res = format_table(p.text)
            elif p.title and p.text:
                misc.append("%s\n%s" % (p.title, format_table(p.text)))
        print "done"

        txt += inp + "\n"

        if res:
            txt += res + "\n"
        elif misc:
            txt += "\n".join(misc)
        else:
            txt += "No results"
    except Exception as e:
        raise e
        txt = "Error: %s" % e

    plugins.say(connection, channel, plugins.shorten(txt, 450))

plugins.register_pub_cmd("wa", waquery)
