from tehbot.plugins import *
import tehbot.plugins as plugins
import tehbot.settings as settings
import re

class RegexReplaceHandler(plugins.ChannelHandler):
    regex = re.compile(r'^s/(.*?)/(.*?)(/(.+))?$', re.I)

    def execute(self):
        match = None
        try:
            match = self.regex.match(self.msg)
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
            user = self.nick

        try:
            regex = re.compile(search, re.I)
        except:
            return

        c = self.dbconn.execute("select message from Messages where server=? and channel=? and nick=? order by ts desc limit 2", (self.connection.name, self.target, user))
        res = c.fetchone()

        if user == self.nick:
            res = c.fetchone()

        if res is None:
            return

        msg = res[0]
        msg = regex.sub(replace, msg)
        msg = plugins.myfilter(msg)
        msg = plugins.shorten(msg, 450)
        return "%s: %s" % (user, msg)

plugins.register_channel_handler(RegexReplaceHandler())
