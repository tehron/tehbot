# -*- coding: utf-8 -*-
from tehbot.plugins import *
import urllib
import urllib2
import time
import ssl
import lxml.html
import re

class HsSolvedPoller(Poller):
    def initialize(self):
        Poller.initialize(self, dbconn)
        with dbconn:
            dbconn.execute("create table if not exists HsPollerLastSolves(id integer, ts datetime, user text, challenge text)")
            dbconn.execute("create table if not exists HsPollerForum(id integer, ts datetime, title text, url text, who text)")

    def execute(self, connection, event, extra):
        url = "https://www.happy-security.de/index.php?modul=hacking-zone"

        try:
            reply = urllib2.urlopen(url, timeout=5)
        except (urllib2.URLError, ssl.SSLError):
            # ignore stupid SSL errors for RevEl
            return

        tree = lxml.html.parse(reply)

        last_solves = []
        for si in tree.xpath("//table[@class='mtable']/tr/td[2]"):
            match = re.search(ur'(.*?) eingesendet von .* zuletzt gelöst von (.*?) am (\d+\.\d+\.\d+ \d+:\d+) Uhr', " ".join(si.text_content().split()))
            if match is not None:
                ts = time.mktime(time.strptime(match.group(3).strip(), "%d.%m.%Y %H:%M"))
                who = match.group(2).strip()
                chall = match.group(1).strip()
                last_solves.append((ts, who, chall))

        msgs = []
        with dbconn:
            for ls in last_solves:
                c = dbconn.execute("select 1 from HsPollerLastSolves where ts=? and user=? and challenge=?", ls)
                if not c.fetchone():
                    dbconn.execute("insert into HsPollerLastSolves values(null, ?, ?, ?)", ls)
                    if time.time() - ls[0] < 86400:
                        msgs.append(Plugin.green("[Happy-Security Solutions]") + " %s has just solved %s." % (Plugin.bold(ls[1]), Plugin.bold(ls[2])))

        msg = u"\n".join(msgs)
        if msg:
            return [("announce", (self.where(), msg))]
