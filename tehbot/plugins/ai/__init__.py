from tehbot.plugins import *
import tehbot.plugins as plugins
import re
import pipes

class AiHandler(ChannelHandler):
    def execute(self, connection, event, extra, dbconn):
        botname = self.tehbot.settings.value("botname", connection)
        regex = [
                re.compile(r'''^ok(?:ay)?\s+%s,?\s*(?P<what>.*?)\s*\??$''' % botname, re.I),
                ]
        solved_regex = [
                re.compile(r'''^ok(?:ay)?\s+%s,?\s*has\s+(?P<who>\w+)\s+solved\s+(?P<chall>\w[\s\w]*?|"[^"]+"|'[^']+')(?:\s+on\s+(?P<site>\w[\s\w]*?|"[^"]+"|'[^']+'))?\s*\??$''' % botname, re.I),
                re.compile(r'''^ok(?:ay)?\s+%s,?\s*did\s+(?P<who>\w+)\s+solve\s+(?P<chall>\w[\s\w]*?|"[^"]+"|'[^']+')(?:\s+on\s+(?P<site>\w[\s\w]*?|"[^"]+"|'[^']+'))?\s*\??$''' % botname, re.I)
                ]

        for r in solved_regex:
            match = r.search(extra["msg"])
            if match is not None:
                user = match.group(1)
                chall = match.group(2)
                site = match.group(3)

                plugin = self.tehbot.cmd_handlers["solvers"]
                chall = " ".join(plugins.mysplit(chall))
                args = '-u %s %s' % (user, pipes.quote(chall))
                if site is not None:
                    site = " ".join(plugins.mysplit(site))
                    args = args + " -s %s" % pipes.quote(site)
                plugin.handle(connection, event, {"args":args}, dbconn)
                return

        for r in regex:
            match = r.search(extra["msg"])
            if match is not None:
                what = match.group(1)

                plugin = self.tehbot.cmd_handlers["ddg"]
                plugin.handle(connection, event, {"args":what}, dbconn)
                return

register_channel_handler(AiHandler())
