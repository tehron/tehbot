from tehbot.plugins import *
import tehbot.plugins as plugins
import wolframalpha
import prettytable

class WolframAlphaPlugin(StandardPlugin):
    def __init__(self):
        StandardPlugin.__init__(self)
        self.parser.add_argument("query", nargs="+")

    def initialize(self, dbconn):
        StandardPlugin.initialize(self, dbconn)
        try:
            self.client = wolframalpha.Client(self.settings["wolframalpha_app_id"])
        except:
            self.settings["enabled"] = False

    @staticmethod
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

    @staticmethod
    def format_table(s):
        table = [[y.strip() for y in x.strip().split("|")] for x in s.splitlines()]
        nr_cols = max(map(len, table))
        table = [[x[i] if i < len(x) else "" for i in range(nr_cols)] for x in table]
        table = WolframAlphaPlugin.remove_empty_columns(table, nr_cols)

        if len(table) < 2:
            s2 = " | ".join(table[0])
            return s2

        pt = prettytable.PrettyTable()
        pt.header = False

        for line in table:
            pt.add_row(line)
        s = pt.get_string()
        return s

    def execute(self, connection, event, extra, dbconn):
        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % str(e)

        txt = "\x0303[Wolfram|Alpha]\x03 "

        try:
            res = None
            misc = []
            for p in self.client.query(" ".join(pargs.query)).pods:
                if p.id == "Input":
                    inp = " | ".join(p.text.splitlines())
                elif p.id == "Result" and p.text:
                    res = self.format_table(p.text)
                elif p.title and p.text:
                    misc.append("%s\n%s" % (p.title, self.format_table(p.text)))

            txt += inp + "\n"

            if res:
                txt += res + "\n"
            elif misc:
                txt += "\n".join(misc)
            else:
                raise NameError
        except (NameError, AttributeError):
            txt += "No results."
        except Exception as e:
            txt = "Error: %s" % e

        return plugins.shorten(txt, 450)

register_plugin(["wolframalpha", "wa"], WolframAlphaPlugin())
