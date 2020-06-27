from __future__ import absolute_import
from tehbot.plugins import *
import wolframalpha
import prettytable

class WolframAlphaPlugin(StandardCommand):
    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("query", nargs="+")

    def commands(self):
        return ["wolframalpha", "wa"]

    def initialize(self, dbconn):
        StandardCommand.initialize(self, dbconn)
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

    def query(self, what):
        inp, res, misc = None, None, []

        for p in self.client.query(Plugin.to_utf8(what)).pods:
            if p.id == "Input":
                inp = " | ".join(p.text.splitlines())
            elif p.id == "Result" and p.text:
                res = self.format_table(p.text)
            elif p.title and p.text:
                misc.append("%s\n%s" % (p.title, self.format_table(p.text)))

        return (inp, res, misc)

    def result(self, what, prefix):
        fn = Plugin.green
        try:
            inp, res, misc = self.query(what)
            txt = inp + "\n"

            if res:
                txt += res + "\n"
            elif misc:
                txt += "\n".join(misc)
            else:
                raise NameError
        except (NameError, AttributeError):
            txt = "No results."
        except Exception as e:
            txt = unicode(e)
            fn = Plugin.red

        return Plugin.shorten(fn(prefix) + txt, 450)

    def execute_parsed(self, connection, event, extra):
        prefix = "[Wolfram|Alpha] "
        return self.result(" ".join(self.pargs.query), prefix)
