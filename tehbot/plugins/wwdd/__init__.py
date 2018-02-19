from tehbot.plugins import *
import random

class WwddPlugin(Plugin):
    """What would dloser do?"""

    def __init__(self):
        Plugin.__init__(self)
        self.parser.add_argument("-a", "--add", metavar="what")

    def initialize(self, dbconn):
        with dbconn:
            dbconn.execute("create table if not exists WwddPlugin(id integer primary key, text varchar)")
            dbconn.executemany("insert or ignore into WwddPlugin values(?, ?)", [
                (1, "%s says: ... (can you feel the silence?)"),
                (2, "%s says: you're a moron!"),
                (3, "%s says: i really like this (in a really high voice)"),
                (4, "%s says: i love you (and dies)"),
                (5, "%s pukes"),
                (6, "%s says: i will give it. (but i won't)"),
                (7, "%s says: so helpful"),
            ])

    def execute(self, connection, event, extra, dbconn):
        try:
            pargs = self.parser.parse_args(extra["args"])
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % str(e)

        if pargs.add is None:
            c = dbconn.execute("select text from WwddPlugin order by random() limit 1")
            what = c.fetchone()

            if what is not None:
                return what[0] % "dloser"
            return

        what = pargs.add
        if not self.privileged(connection, event):
            return self.request_priv(extra)

        if what.find("%s") < 0:
            return "you forgot to add %s. that wouldn't have happened to dloser..."

        if dbconn.execute("select 1 from WwddPlugin where text like ?", ("%%%s%%" % what,)).fetchone() is not None:
            return "what has already been added!"

        with dbconn:
            dbconn.execute("insert into WwddPlugin values(null, ?)", (what,))

register_plugin("wwdd", WwddPlugin())
