from tehbot.plugins import *
import shlex
import urllib2
import urllib
import json
import re
import datetime

def ends_message():
    end = datetime.datetime(2015, 12, 11, 20)
    secs = (end - datetime.datetime.now()).seconds

    lst = []
    hours = secs / 3600
    if hours > 0:
        lst.append("%d hour%s" % (hours, "" if hours == 1 else "s"))
    secs -= 3600 * hours

    mins = secs / 60
    if mins > 0:
        lst.append("%d minute%s" % (mins, "" if mins == 1 else "s"))
    secs -= 60 * mins

    if secs > 0:
        lst.append("%d second%s" % (secs, "" if secs == 1 else "s"))

    return "CTF ends in %s." % (", ".join(lst))

class CtfPlugin(StandardCommand):
    """Shows rankings of HackThis!! CTF 2015"""

    def __init__(self):
        StandardCommand.__init__(self)
        group = self.parser.add_mutually_exclusive_group()
        group.add_argument("-u", "--user")
        group.add_argument("-r", "--rank", type=int)

    def commands(self):
        return "ctf"

    def execute_parsed(self, connection, event, extra, dbconn):
        if event.target.lower() != "#ctf":
            return

        prefix = "\x0303[HackThis!! CTF]\x03 "

        if self.pargs.user:
            user = Plugin.from_utf8(self.pargs.user)
        else:
            user = None
        rank = self.pargs.rank

        if user is not None:
            try:
                raw_data = urllib2.urlopen("http://ctf.hackthis.co.uk/ajax.php?action=stats", data="q=0").read()
            except:
                return "Network Error"

            try:
                data = json.loads(raw_data)
                if not data["status"]:
                    return "Status not ok"
            except:
                return "Unknown format in server reply"

            leaderboard = re.findall(r'"([^"]*)":(\d+)', raw_data)
            i = 1
            for name, solved in leaderboard:
                if name.lower() == user.lower():
                    return prefix + "%s has solved %s task%s and is at rank %d of %d. %s" % (name, solved, "" if int(solved) == 1 else "s", i, len(leaderboard), ends_message())
                i += 1

            return prefix + "%s not found in leaderboard." % (user)
        elif rank is not None and rank > 0:
            try:
                raw_data = urllib2.urlopen("http://ctf.hackthis.co.uk/ajax.php?action=stats", data="q=%d" % rank).read()
            except:
                return "Network Error"

            try:
                data = json.loads(raw_data)
                if not data["status"]:
                    return "Status not ok"
            except:
                return "Unknown format in server reply"

            leaderboard = re.findall(r'"([^"]*)":(\d+)', raw_data)
            if len(leaderboard) < rank:
                return "No one is at rank %d. %s" % (rank, ends_message())

            name, solved = leaderboard[-1]
            return prefix + "%s is at rank %d with %s solved task%s. %s" % (name, rank, solved, "" if int(solved) == 1 else "s", ends_message())
        else:
            try:
                raw_data = urllib2.urlopen("http://ctf.hackthis.co.uk/ajax.php?action=stats", data="q=10").read()
            except:
                return "Network Error"

            try:
                data = json.loads(raw_data)
                if not data["status"]:
                    return "Status not ok"
            except:
                return "Unknown format in server reply"

            leaderboard = re.findall(r'"([^"]*)":(\d+)', raw_data)
            return prefix + "Top 10: " + ", ".join("%s (%s)" % (a, b) for a, b in leaderboard) + ". " + ends_message()

class ConductPlugin(StandardCommand):
    def __init__(self):
        StandardCommand.__init__(self)
        self.conducts = [
                "Answers to all levels will be my own work, unless otherwise instructed.",
                "I will not share answers to any level.",
                "I will not participate in, condone or encourage unlawful activity, including any breach of copyright, defamation, or contempt of court.",
                "I will not 'spam' other HackThis!! members by posting the same message multiple times or posting a message that is unrelated to the discussion.",
                "As the HackThis!! community's first language is English, I will always post contributions in English to enable all to understand",
                "I will not use HackThis!! to advertise products or services for profit or gain.",
                "I will not use racist, sexist, homophobic, sexually explicit or abusive terms or images, or swear words or language that is likely to cause offence."
        ]
        self.parser.add_argument("nr", type=int, choices=range(1, len(self.conducts) + 1))

    def commands(self):
        return ["conduct", "rule"]

    def default_settings(self):
        return {
                "where" : { "Macak" : [ "#hackthis" ] }
                }

    def target_valid(self, name, ch):
        for network, channels in self.settings["where"].items():
            if network == name and ch in channels:
                return True

        return False

    def execute_parsed(self, connection, event, extra, dbconn):
        if not self.target_valid(connection.tehbot.name, event.target.lower()):
            return

        return self.conducts[self.pargs.nr - 1]
