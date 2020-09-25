# -*- coding: utf-8 -*-
from tehbot.plugins import *
import irc.client
import model
import threading
import time
from random import randint, random
import os.path

#import gettext
#t = gettext.translation("Shadowlamb", os.path.dirname(__file__) + "/i18n")
#_ = t.gettext
_ = lambda x: x

class ShadowlambPlugin(StandardCommand):
    """What, you don't know what shadowlamb is??"""

    def __init__(self, db):
        StandardCommand.__init__(self, db)

    def commands(self):
        return "sl"

    def execute_parsed(self, connection, event, extra):
        if not self.is_privileged(extra):
            return self.request_priv(extra)

        return "Shadowlamb is teh greatest!"

class ShadowlambHandler(PrefixHandler):
    def command_prefix(self):
        #return "+"
        return u'\u00a5';

    def __init__(self, db):
        PrefixHandler.__init__(self, db)
        self.cmd2action = {
                "start" : self.start,
                "reset" : self.reset,
                "s" : self.status,
                "status" : self.status,
                "a" : self.attributes,
                "attributes" : self.attributes,
                "kw" : self.known_words,
                "known_words" : self.known_words,
                "kp" : self.known_places,
                "known_places" : self.known_places,
                "time" : self.show_time,
                "p" : self.party_status,
                "party" : self.party_status,
                }

    def init(self):
        PrefixHandler.init(self)
        #model.init()
        self.quit = False
        self.thread = threading.Thread(target=self.timerfunc)
        #self.thread.start()

    def deinit(self):
        self.quit = True
        #self.thread.join()

    def cmd(self, args):
        return u"\x02%s%s\x02" % (self.command_prefix(), args)

    def sltime(self):
        with model.db_session:
            return model.Shadowlamb[1].time

    def announce(self, msg):
        where = {"WeChall IRC" : ["#net-force"]}

        for network in where:
            for conn in self.tehbot.core.reactor.connections:
                if conn.name != network:
                    continue
                for ch in where[network]:
                    if ch in conn.channels:
                        plugins.say(conn, ch, msg)

    def player_age(self, player):
        d = self.sltime() - player.birthday
        years = d / 60 / 60 / 24 / 365
        return max(1, int(round(years)))

    def give_item(self, player, item):
        pi = model.PlayerItem(base=item, player=player)
        player.inventory += pi
        return [_("You received 1x%s" % item.name)]

    def give_word(self, player, word):
        if word in player.known_words:
            return []
        player.known_words += word
        return [_("You know a new Word: \x02%s\x02" % word.name)]

    def give_place(self, player, place):
        if place in player.known_places:
            return []
        player.known_places += place
        return [_("You know a new Place: \x02%s\x02" % place.name)]

    def party_push_action(self, party, action, target=None, eta=None):
        with_events = action is not model.PartyAction.delete

        party.last_action = party.action
        party.last_target = party.target
        party.last_eta = party.eta

        party.action = action
        if target is not None:
            party.target = target
        party.eta = self.sltime() + (eta or 0)

        #if with_events:
            #self.announce_party(party

    def timerfunc(self):
        while not self.quit:
            nxt = time.time() + 1
            while time.time() < nxt:
                time.sleep(0.1)

            with model.db_session:
                model.Shadowlamb[1].time += 1

    def start(self, connection, event, extra, msg_type):
        with model.db_session:
            genders = [to_utf8(g.name) for g in model.Gender.select()]
            races = [to_utf8(r.name) for r in model.Race.select(lambda x: not x.is_npc)]

        parser = plugins.ThrowingArgumentParser(prog="start", description=self.__doc__)
        parser.add_argument("gender", metavar="gender", choices=genders, help=", ".join(genders))
        parser.add_argument("race", metavar="race", choices=races, help=", ".join(races))

        try:
            pargs = parser.parse_args(extra["args"], decode=False)
            m = parser.get_help_msg()
            if m:
                return m.strip()
        except Exception as e:
            return u"Error: %s" % exc2str(e)

        def random_birthday(s):
            tm = time.gmtime(s)
            return time.mktime((tm.tm_year, randint(1, 12), randint(1, 31), randint(0, 23), randint(0, 59), randint(0, 61), 0, 1, -1))

        def random_value(val, p):
            rand = 1.0 + p * (2 * random() - 1)
            return val * rand

        with model.db_session:
            network_id = self.tehbot.settings.network_id(connection)
            r = model.Race.get(name=pargs.race)
            p = model.Player(
                    network_id=network_id,
                    nick=event.source.nick,
                    name=event.source.nick,
                    gender=model.Gender.get(name=pargs.gender),
                    race=r,
                    birthday = random_birthday(self.sltime() - random_value(r.age, 0.2) * 365 * 24 * 60 * 60),
                    height = random_value(r.height, 0.2),
                    own_weight = random_value(r.own_weight, 0.2),
                    options = {},
                    hp = 0,
                    mp = 0,
                    distance = 0,
                    xp = 0,
                    xp_level = 0,
                    karma = 0,
                    bad_karma = 0,
                    level = 0,
                    bounty = 0,
                    bounty_done = 0,
                    quests_done = 0,
                    nuyen = 0,
                    known_words = [],
                    known_spells = [],
                    known_places = "",
                    bank_nuyen = 0,
                    bank_items = "",
                    effects = "",
                    const_vars = "",
                    combat_ai = "",
                    game_ai = "",
                    feelings = model.Feelings(),
                    attributes = model.Attributes(),
                    skills = model.Skills(),
                    knowledge = model.Knowledge(),
                    lock = 0,
                    transport = 0,
                    stats = model.PlayerStats(),
                    equipment = model.Equipment(),
                    )
            p.init_player()
            party = model.Party(options={})
            p.party = party

        msgs = [
                _("Your character has been created with \x02Age\x02: %dyears, \x02Height\x02: %.2fm, \x02Weight\x02: %.2fkg.") % (self.player_age(p), p.height, p.own_weight),
                ]

        notices = [
                _("You wake up in a bright room... It seems like it is past noon...looks like you are in a hotel room."),
                _("What happened... You can`t remember anything.... Gosh, you even forgot your name."),
                _("You check your %s and find a pen from 'Renraku Inc.'. You leave your room and walk to the counter. Use %s to talk with the hotelier." % (self.cmd("inventory"), self.cmd("talk"))),
                _("Use %s to see all available commands. Check %s to browse the Shadowlamb help files. Use %s to see the help for a command or subject." % (self.cmd("commands"), self.cmd("help"), self.cmd("help <word>")))
                ]

        notices += self.give_item(p, model.Item.get(name="Pen"))
        notices += self.give_word(p, model.Word.get(name="Shadowrun"))
        notices += self.give_word(p, model.Word.get(name="Renraku"))
        notices += self.give_place(p, model.Place.get(name="Redmond_Hotel"))
        self.party_push_action(party, model.PartyAction.inside, "Redmond_Hotel")

        if msg_type == "notice":
            notices = msgs + notices
            msgs = []
        else:
            for m in msgs:
                if irc.client.is_channel(event.target):
                    plugins.say_nick(connection, event.target, event.source.nick, m)
                else:
                    plugins.say(connection, event.source.nick, m)

        for m in notices:
            plugins.notice(connection, event.source.nick, m)

        self.announce("Welcome a new player: %s the %s %s." % (p.fullname(), p.gender.name, p.race.name))
        return None

    def reset(self, args, player):
        parser = plugins.ThrowingArgumentParser(prog="reset")
        parser.add_argument("confirmation", nargs="?")

        try:
            pargs = parser.parse_args(args)
            if parser.help_requested:
                return parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % exc2str(e)

        if not pargs.confirmation:
            player.set_option("deletion_started", True)
            return "This will completely delete your character. Type %s to confirm." % self.cmd("reset i_am_sure")

        if not player.option("deletion_started"):
            return "Deletion not started yet. Type %s to start deletion." % self.cmd("reset")

        if "".join(pargs.confirmation) != "i_am_sure":
            player.set_option("deletion_started", False)
            return "Deletion aborted. Type %s to start deletion again." % self.cmd("reset")

        player.delete()
        return "Your character has been deleted. You may issue %s again." % self.cmd("start")

    def status(self, args, player):
        # male troll L0(0). HP:35/35, Atk:22.8, Def:0.1, Dmg:1.8-7.5, Arm(M/F):0/0, XP:0, Karma:0, ¥:50, Weight:0g/18.5kg.
        # female fairy L0(0). HP:10/10, MP:36/36, Atk:2.8, Def:1.5, Dmg:-0.2-2.5, Arm(M/F):0/0, XP:0, Karma:0, ¥:0, Weight:0g/3.5kg.
        # male gremlin L0(0). HP:30/30, Atk:20.6, Def:0.8, Dmg:1-5.5, Arm(M/F):0/0, XP:0, Karma:0, ¥:0, Weight:50g/12.5kg.
        attack, defense, min_dmg, max_dmg, marm, farm = player.combat_stats()
        return "%s %s L%d(%d): \x02HP\x02:%.2f/%.2f, \x02MP\x02:%.2f/%.2f, \x02Atk\x02:%.2f, " \
                u"\x02Def\x02:%.2f, \x02Dmg\x02:%.2f–%.2f, \x02Arm\x02(M/F):%.2f/%.2f, " \
                u"\x02XP\x02:%.2f, \x02Karma\x02:%d, \x02¥\x02:%.2f, \x02Weight\x02:%.2f/%.2fkg" % (
                player.gender.name,
                player.race.name,
                player.level,
                player.effective_level(),
                player.hp,
                player.max_hp(),
                player.mp,
                player.max_mp(),
                attack,
                defense,
                min_dmg,
                max_dmg,
                marm,
                farm,
                player.xp,
                player.karma,
                player.nuyen,
                player.weight(),
                player.max_weight(),
                )

    def attributes(self, args, player):
        # Your attributes: body:1(5), strength:0(4), quickness:2(3), wisdom:0(1), intelligence:0, luck:0, reputation:0(2), essence:6(5.5).
        # Your attributes: body:4, strength:3(4), quickness:1, wisdom:0(1), intelligence:0, luck:0, reputation:2, essence:5.5.
        lst = []
        attr = ["body", "magic", "strength", "quickness", "wisdom", "intelligence", "charisma", "luck", "reputation", "essence"]
        for a in attr:
            base = getattr(player.race.base_attributes, a)
            now = getattr(player, a)()
            if now >= 0:
                lst.append("\x02%s\x02:%g%s" % (a, base, "" if base == now else "(%g)" % now))

        return "Your attributes: %s." % ", ".join(lst)

    def known_words(self, args, player):
        words = []
        for w in player.known_words:
            words.append((w.id, "\x02%d\x02-%s" % (w.id, w.name)))
        return "Known Words: %s." % ", ".join(w[1] for w in sorted(words))

    def known_places(self, args, player):
        places = []
        for p in player.known_places:
            places.append((p.id, "\x02%d\x02-%s" % (p.id, p.name)))
        return "Known Places: %s." % ", ".join(p[1] for p in sorted(places))

    def show_time(self, args, player):
        now = time.gmtime(self.sltime())
        return time.strftime("It is %H:%M:%S, %Y-%m-%d in Shadowland", now)

    def party_status(self, args, player):
        if player.party.action == model.PartyAction.inside:
            return "You are \x02inside\x02 %s." % player.party.target

        return "hu!? should never get here"

    def execute(self, connection, event, extra):
        if not self.is_authed(extra):
            return self.request_auth(extra)

        cmd = extra["cmd"].lower()
        msg_type = "say_nick" if irc.client.is_channel(event.target) else "notice"

        with model.db_session:
            p = model.Player.get(name=event.source.nick, network_id=self.tehbot.settings.network_id(connection))

            if p is not None and not irc.client.is_channel(event.target):
                msg_type = p.option("msg_type", msg_type)

            if not self.cmd2action.has_key(cmd):
                return [(msg_type, "The command is not available for your current action or location. Try %s to see all currently available commands." % self.cmd("commands [--long]"))]

            if cmd == "start" and p:
                return [(msg_type, "Your character has been created already. You can type %s to start over." % self.cmd("reset"))]

            if cmd != "start" and not p:
                return [(msg_type, "You haven't started the game yet. Type %s to begin playing." % self.cmd("start"))]

            try:
                if cmd == "start":
                    res = self.start(connection, event, extra, msg_type)
                else:
                    res = self.cmd2action[cmd](extra["args"], p)
            except Exception as e:
                import traceback
                traceback.print_exc()
                return [(msg_type, u"Error: %s" % exc2str(e))]

            if isinstance(res, list):
                return [(msg_type, m) for m in res]
            if isinstance(res, basestring):
                return [(msg_type, res)]
