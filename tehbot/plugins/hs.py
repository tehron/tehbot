# -*- coding: utf-8 -*-
from tehbot.plugins import *
import urllib
import urllib2
import ssl
import lxml.html
import re
from pony.orm import *
from datetime import datetime, timedelta

class HsPoller(Poller):
    @db_session
    def create_entities(self):
        class HsPollerLastSolves(self.db.Entity):
            ts = Required(datetime)
            user = Required(str)
            challenge = Required(str)

        class HsPollerForum(self.db.Entity):
            ts = Required(datetime)
            title = Required(str)
            url = Required(str)
            who = Required(str)

    def execute(self, connection, event, extra):
        url = "https://www.happy-security.de/index.php?modul=hacking-zone"

        try:
            reply = urllib2.urlopen(url, timeout=5)
        except (urllib2.URLError, ssl.SSLError):
            # ignore stupid SSL errors
            return

        tree = lxml.html.parse(reply)

        last_solves = []
        for si in tree.xpath("//table[@class='mtable']/tr/td[2]"):
            match = re.search(ur'(.*?) eingesendet von .* zuletzt gelöst von (.*?) am (\d+\.\d+\.\d+ \d+:\d+) Uhr', " ".join(si.text_content().split()))
            if match is not None:
                ts = datetime.strptime(match.group(3).strip(), "%d.%m.%Y %H:%M")
                who = match.group(2).strip()
                chall = match.group(1).strip()
                last_solves.append((ts, who, chall))

        msgs = []
        with db_session:
            for ts, who, chall in last_solves:
                if not select(s for s in self.db.HsPollerLastSolves if s.ts == ts and s.user == who and s.challenge == chall):
                    self.db.HsPollerLastSolves(ts=ts, user=who, challenge=chall)
                    if datetime.now() - ts < timedelta(days=2):
                        msgs.append(Plugin.green("[Happy-Security Solutions]") + " %s has just solved %s." % (Plugin.bold(who), Plugin.bold(chall)))

        msg = u"\n".join(msgs)
        if msg:
            return [("announce", (self.where(), msg))]
