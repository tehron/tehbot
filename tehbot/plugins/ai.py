from tehbot.plugins import *
import re
import random

class AiHandler(ChannelHandler):
    @staticmethod
    def decision_answers():
        return [
                "Yes",
                "No",
                "Sure",
                "Absolutely",
                "For sure",
                "No, you are!",
                "Will you ever get sick of this?",
                "Certainly not",
                "I haven't made up my mind yet."
                ]

    def initialize(self, dbconn):
        ChannelHandler.initialize(self, dbconn)

    def execute(self, connection, event, extra, dbconn):
        botname = connection.get_nickname()
        decide_regex = [
                re.compile(r'''^(?:ok(?:ay)?|hey|hay)\s+%s\s*,?\s*(?:is|are|can|has|was|were|should|do|does)\s+\S[\s\S]*\?''' % botname, re.I),
                ]
        regex = [
                re.compile(r'''^(?:ok(?:ay)?|hey|hay)\s+%s\s*,\s*(?P<what>.+?)\s*\??$''' % botname, re.I),
                ]
        solved_regex = [
                re.compile(r'''^(?:ok(?:ay)?|hey|hay)\s+%s\s*,?\s*has\s+(?P<who>\S+)\s+solved\s+(?P<chall>\S[\s\S]*?|"[^"]+"|'[^']+')(?:\s+on\s+(?P<site>\S[\s\S]*?|"[^"]+"|'[^']+'))?\s*\??$''' % botname, re.I),
                re.compile(r'''^(?:ok(?:ay)?|hey|hay)\s+%s\s*,?\s*did\s+(?P<who>\S+)\s+solve\s+(?P<chall>\S[\s\S]*?|"[^"]+"|'[^']+')(?:\s+on\s+(?P<site>\S[\s\S]*?|"[^"]+"|'[^']+'))?\s*\??$''' % botname, re.I)
                ]

        backend = self.settings.get("backend", "WolframAlphaPlugin")

        for r in solved_regex:
            match = r.search(extra["msg"])
            if match is not None:
                user = match.group(1)
                chall = match.group(2)
                site = match.group(3)

                chall = " ".join(Plugin.mysplit(chall))
                if site is not None:
                    site = " ".join(Plugin.mysplit(site))

                return [("solvers", (site, chall, False, user))]

        for r in decide_regex:
            match = r.search(extra["msg"])
            if match is not None:
                return random.choice(AiHandler.decision_answers())

        for r in regex:
            match = r.search(extra["msg"])
            if match is not None:
                what = match.group(1).strip()
                if not what:
                    return

                return [("extquery", (backend, what, 200))]
