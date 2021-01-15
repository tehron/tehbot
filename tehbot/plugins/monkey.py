from tehbot.plugins import *
from datetime import datetime
import irc.client
import random
from pony.orm import *

class MonkeyPlugin(StandardCommand):
    def commands(self):
        return "monkey"

    def create_entities(self):
        class MonkeyPhrase(self.db.Entity):
            insult = Required(str, unique=True, max_len=128)
            comeback = Required(str, unique=True, max_len=128)

        class MonkeyAttack(self.db.Entity):
            ts = Required(datetime)
            who = Required(str)
            victim = Required(str)
            insult = Required(str)
            comeback0 = Required(str)
            comeback1 = Required(str)
            comeback2 = Required(str)
            comeback3 = Required(str)
            lucky_idx = Required(int)
            comeback_ts = Optional(datetime)
            comeback = Optional(str)

    def init(self):
        StandardCommand.init(self)
        self.parser.add_argument("victim")
        self.parser.add_argument("-r", "--response", choices="abcd")

        with db_session:
            if self.db.MonkeyPhrase.select():
                return

            phrases = [
                    ('You fight like a dairy Farmer!', 'How appropriate. You fight like a cow!'),
                    ('This is the END for you, you gutter crawling cur!', "And I've got a little TIP for you, get the POINT?"),
                    ("I've spoken with apes more polite than you!", "I'm glad to hear you attended your family reunion!"),
                    ("Soon you'll be wearing my sword like a shish kebab!", "First you'd better stop waving it like a feather duster."),
                    ('People fall at my feet when they see me coming!', 'Even BEFORE they smell your breath?'),
                    ("I'm not going to take your insolence sitting down!", 'Your hemorrhoids are flaring up again eh?'),
                    ('I once owned a dog that was smarter than you.', 'He must have taught you everything you know.'),
                    ("Nobody's ever drawn blood from me and nobody ever will.", 'You run THAT fast?'),
                    ('Have you stopped wearing diapers yet?', 'Why? Did you want to borrow one?'),
                    ('There are no words for how disgusting you are.', 'Yes there are. You just never learned them.'),
                    ('You make me want to puke.', 'You make me think somebody already did.'),
                    ('My handkerchief will wipe up your blood!', 'So you got that job as janitor, after all.'),
                    ('I got this scar on my face during a mighty struggle!', "I hope now you've learned to stop picking your nose."),
                    ("I've heard you are a contemptible sneak.", "Too bad no one's ever heard of YOU at all."),
                    ("You're no match for my brains, you poor fool.", "I'd be in real trouble if you ever used them."),
                    ('You have the manners of a beggar.', "I wanted to make sure you'd feel comfortable with me.")
                    ]
            for insult, comeback in phrases:
                self.db.MonkeyPhrase(insult=insult, comeback=comeback)

    def response_time(self):
        return 5 * 60

    def execute_parsed(self, connection, event, extra):
        if not irc.client.is_channel(event.target):
            return

        when = datetime.now()
        who = event.source.nick
        users = [u for u,m in connection.tehbot.users[event.target]]
        if not self.pargs.victim in users:
            return "%s isn't here." % self.pargs.victim

        with db_session:
            if self.pargs.response:
                a = select(a for a in self.db.MonkeyAttack if a.who == self.pargs.victim and a.victim == who and not a.comeback_ts).order_by(desc(1)).first()
                if not a:
                    return "You did that already!"
                if (when - a.ts).total_seconds() >= self.response_time():
                    return "You're late for the party!"

                idx = "abcd".index(self.pargs.response)
                a.comeback_ts = when
                a.comeback = getattr(a, "comeback%d" % idx)

                if idx == a.lucky_idx:
                    return "Well played, %s!" % who
                return "Nah, %s wins!" % self.pargs.victim

            a = select(a for a in self.db.MonkeyAttack if a.who == who and a.victim == self.pargs.victim and not a.comeback_ts).order_by(desc(1)).first()
            r = select(a for a in self.db.MonkeyAttack if a.who == self.pargs.victim and a.victim == who and not a.comeback_ts).order_by(desc(1)).first()
            if (a and (when - a.ts).total_seconds() < self.response_time()) or (r and (when - r.ts).total_seconds() < self.response_time()):
                return "Finish what you've started first!"

            phrases = self.db.MonkeyPhrase.select_random(4)
            comebacks = [x.comeback for x in phrases]
            random.shuffle(comebacks)
            idx = comebacks.index(phrases[0].comeback)
            a = self.db.MonkeyAttack(ts=when, who=who, victim=self.pargs.victim, insult=phrases[0].insult, comeback0=comebacks[0], comeback1=comebacks[1], comeback2=comebacks[2], comeback3=comebacks[3], lucky_idx=idx)
            choices = ["%s) %s" % (x, y) for x, y in zip("abcd", comebacks)]
            return [("say", "%s: %s" % (self.pargs.victim, a.insult)), ("say", "%s: %s" % (self.pargs.victim, "Response: " + " ".join(choices)))]
