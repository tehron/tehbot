from tehbot.plugins import *
import requests
import lxml.html
import re
from datetime import datetime
from pony.orm import *
from ast import literal_eval

class RankkPoller(Poller):
    def __init__(self, db):
        Poller.__init__(self, db)
        self.url = "https://www.rankk.org/stats.py"
        self.sess = requests.Session()

    def solvers_prefix(self):
        return u"[Rankk Solvers] "

    def users_prefix(self):
        return u"[Rankk Users] "

    def forum_prefix(self):
        return u"[Rankk Forum] "

    def create_entities(self):
        class RankkSolvedPollerData(self.db.Entity):
            ts = Required(datetime)
            user = Required(str, max_len=32)
            chall_nr = Required(str, max_len=20)
            composite_key(user, chall_nr)

        class RankkPollerUser(self.db.Entity):
            ts = Required(datetime)
            user = Required(str, max_len=32)

        class RankkPollerForum(self.db.Entity):
            ts = Required(datetime)
            user = Required(str, max_len=32)
            topic = Required(str, max_len=128)

    def execute(self, connection, event, extra):
        r = self.sess.get(self.url)
        tree = lxml.html.fromstring(r.content)
        last_solve = tree.xpath("//li[@id='solved']")
        match = re.search(r'Solved: ([^ ]+) (\d+/\d+)', last_solve[0].text_content())
        user, chall_nr = match.groups()
        match = re.search(r'<tr><td class="td">%s</td><td class="td">([^<]+)</td><td class="td">\d*</td></tr' % chall_nr, r.text)
        chall_name = Plugin.backslash_unescape(match.group(1)) if match else None
        latest_user = re.search(r'Newest: (.+)', tree.xpath("//li[@id='newest']")[0].text_content()).group(1)
        forum_user = re.search(r'Posted: (.+)', tree.xpath("//li[@id='posted']")[0].text_content()).group(1)
        forum_topic = re.search(r'Topic: (.+)', tree.xpath("//li[@id='topic']")[0].text_content()).group(1)

        msgs = []
        with db_session:
            if not select(x for x in self.db.RankkSolvedPollerData if x.user == user and x.chall_nr == chall_nr):
                self.db.RankkSolvedPollerData(ts=datetime.now(), user=user, chall_nr=chall_nr)
                if chall_name:
                    msg = "%s has just solved Level %s, %s." % (Plugin.bold(user), Plugin.bold(chall_nr), Plugin.bold(chall_name))
                else:
                    msg = "%s has just solved Level %s." % (Plugin.bold(user), Plugin.bold(chall_nr))
                msgs.append(Plugin.green(self.solvers_prefix()) + msg)
            if not select(x for x in self.db.RankkPollerUser if x.user == latest_user):
                self.db.RankkPollerUser(ts=datetime.now(), user=latest_user)
                msg = "%s just joined." % (Plugin.bold(user))
                msgs.append(Plugin.green(self.users_prefix()) + msg)
            if not select(x for x in self.db.RankkPollerForum if x.user == forum_user and x.topic == forum_topic):
                self.db.RankkPollerForum(ts=datetime.now(), user=forum_user, topic=forum_topic)
                msg = "New post in %s by %s." % (Plugin.bold(forum_topic), Plugin.bold(forum_user))
                msgs.append(Plugin.green(self.forum_prefix()) + msg)

        msg = u"\n".join(msgs)
        if msg:
            return [("announce", (self.where(), msg))]
