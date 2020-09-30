from tehbot.plugins import *
import requests
import lxml.html
import re
from datetime import datetime
from pony.orm import *

class RankkSolvedPoller(Poller):
    def __init__(self, db):
        Poller.__init__(self, db)
        self.url = "https://www.rankk.org/stats.py"
        self.sess = requests.Session()

    def prefix(self):
        return u"[Rankk Solvers]"

    def create_entities(self):
        class RankkSolvedPollerData(self.db.Entity):
            ts = Required(datetime)
            user = Required(str, max_len=32)
            chall_nr = Required(str, max_len=20)
            composite_key(user, chall_nr)

    def execute(self, connection, event, extra):
        r = self.sess.get(self.url)
        tree = lxml.html.fromstring(r.content)
        last_solve = tree.xpath("//li[@id='solved']")
        match = re.search(r'Solved: ([^ ]+) (\d+/\d+)', last_solve[0].text_content())
        user, chall_nr = match.groups()
        match = re.search(r'<tr><td class="td">%s</td><td class="td">([^<]+)</td><td class="td">\d*</td></tr' % chall_nr, r.text)
        chall_name = match.group(1) if match else None

        with db_session:
            if not select(x for x in self.db.RankkSolvedPollerData if x.user == user and x.chall_nr == chall_nr):
                self.db.RankkSolvedPollerData(ts=datetime.now(), user=user, chall_nr=chall_nr)
                if chall_name:
                    msg = "%s has just solved Level %s, %s." % (Plugin.bold(user), Plugin.bold(chall_nr), Plugin.bold(chall_name))
                else:
                    msg = "%s has just solved Level %s." % (Plugin.bold(user), Plugin.bold(chall_nr))
                return [("announce", (self.where(), Plugin.green(self.prefix()) + " " + msg))]
