from tehbot.plugins import *
import tehbot.plugins as plugins
import re

class RegexReplaceHandler(ChannelHandler):
    regex = re.compile(r'^s/(.*?)/(.*?)(/(.+))?$', re.I)

    def execute(self, connection, event, extra, dbconn):
        match = None
        try:
            match = self.regex.match(extra["msg"])
        except:
            pass

        if match is None:
            return

        search = match.group(1)
        replace = match.group(2)

        try:
            user = match.group(4).strip()
        except:
            user = ""

        if user == "":
            user = event.source.nick

        try:
            regex = re.compile(search, re.I)
        except:
            return

        c = dbconn.execute("select message from Messages where server=? and channel=? and nick=? order by ts desc limit 2", (connection.name, event.target, user))
        res = c.fetchone()

        if user == event.source.nick:
            res = c.fetchone()

        if res is None:
            return

        msg = res[0]
        msg = regex.sub(replace, msg)
        msg = plugins.myfilter(msg)
        msg = plugins.shorten(msg, 450)
        return u"%s: %s" % (user, msg)

register_channel_handler(RegexReplaceHandler())
