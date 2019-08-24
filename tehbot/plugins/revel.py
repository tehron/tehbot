from tehbot.plugins import *
import urllib
import urllib2
import time
import ssl

class RevelSolvedPoller(Poller):
    def prefix(self):
        return u"[Revolution Elite]"

    def datestamp(self, ts):
        return time.strftime('%Y%m%d%H%M%S', time.localtime(ts))

    def timestamp(self, datestamp):
        try:
            t = time.strptime(datestamp, '%Y%m%d%H%M%S')
            ts = time.mktime(t)
        except:
            ts = 0
        return ts

    def execute(self, connection, event, extra, dbconn):
        url = "https://www.revolutionelite.co.uk/w3ch4ll/solvers_revel.php?datestamp=%s"

        try:
            ts = self.settings["ts"]
        except:
            ts = 0

        try:
            reply = urllib2.urlopen(url % self.datestamp(ts), timeout=3)
        except (urllib2.URLError, ssl.SSLError):
            # ignore stupid SSL errors for RevEl
            return

        entries = []

        for entry in reply.readlines():
            try:
                uid, cid, solvedate, firstdate, views, options, timetaken, tries, username, challname, solvercount, challurl = map(lambda x: x.replace(r"\:", ":"), entry.split("::"))
                uid = int(uid)
                cid = int(cid)
                tssolve = self.timestamp(solvedate)
                ts1stsolve = self.timestamp(firstdate)
                views = int(views)
                tries = int(tries)
                solvercount = int(solvercount) - 1
                entries.append((tssolve, username, challname, solvercount))
            except:
                pass

        msgs = []
        for tssolve, username, challname, solvercount in sorted(entries):
            ts = tssolve

            msg = "%s has just solved %s." % (Plugin.bold(username), Plugin.bold(challname))
            if solvercount <= 0:
                msg += " This challenge has never been solved before!"
            else:
                msg += " This challenge has been solved %d time%s before." % (solvercount, "" if solvercount == 1 else "s")

            msgs.append(u"%s %s" % (Plugin.green(self.prefix()), msg))

        self.settings["ts"] = ts
        self.save(dbconn)

        msg = u"\n".join(msgs)
        if msg:
            return [("announce", (self.where(), msg))]
