from tehbot.plugins import *
import re
from pony.orm import *

class RegexReplaceHandler(ChannelHandler):
    regex = re.compile(r'^s/(.*?)/(.*?)(/(.+))?$', re.I)

    def execute(self, connection, event, extra):
        match = self.regex.match(extra["msg"])

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

        with db_session:
            msgs = select(m for m in self.db.Message if m.ircid == connection.tehbot.ircid and m.target == event.target and m.nick == user).order_by(desc(self.db.Message.ts))[:2]

        if not msgs:
            return

        if user == event.source.nick:
            m = msgs[1] if len(msgs) == 2 else None
        else:
            m = msgs[0]

        if m is None:
            return

        msg = m.message
        msg = regex.sub(replace, msg)
        msg = Plugin.myfilter(msg)
        msg = Plugin.shorten(msg, 450)
        return u"%s: %s" % (user, msg)
