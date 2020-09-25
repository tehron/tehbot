from tehbot.plugins import *
import random
import os.path
import time
import datetime
import irc.client
from pony.orm import *

class SlapwarzPlugin(StandardCommand):
    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("victim")

    def commands(self):
        return "slap"

    def create_entities(self):
        class SlapwarzWord(self.db.Entity):
            word = Required(str, unique=True, max_len=128)
            type = Required(int)
            damage = Required(float)

        class SlapwarzSlap(self.db.Entity):
            ts = Required(datetime.datetime)
            who = Required(str)
            victim = Required(str)
            damage = Required(float)

    def init(self):
        StandardCommand.init(self)

        words = [
            (0, 0, 'hardly', 14),
            (1, 0, 'accidently', 15),
            (2, 0, 'sadly', 25),
            (3, 0, 'funnily', 28),
            (4, 0, 'hopefully', 29),
            (5, 0, 'immediately', 30),
            (6, 0, 'silently', 30),
            (7, 0, 'arbitarily', 32),
            (8, 0, 'weirdly', 32),
            (9, 0, 'mistakenly', 33),
            (10, 0, 'periodically', 33),
            (11, 0, 'grossly', 35),
            (12, 0, 'suddenly', 35),
            (13, 0, 'happily', 40),
            (14, 0, 'massively', 40),
            (15, 0, 'ruthlessly', 45),
            (16, 0, 'urgently', 50),
            (17, 0, 'sneakily', 52),
            (18, 0, 'quickly', 55),
            (19, 0, 'angrily', 60),
            (20, 0, 'viciously', 60),
            (21, 0, 'epicly', 70),

            (22, 1, 'totally fails at', 0),
            (23, 1, 'screws him/herself while slapping', 3),
            (24, 1, 'fails at', 5),
            (25, 1, 'fails a bit at', 8),
            (26, 1, 'misses' , 10),
            (27, 1, 'trolls', 10),
            (28, 1, 'wobbles' , 15),
            (29, 1, 'splashes', 16),
            (30, 1, 'faps', 18),
            (31, 1, 'clubs', 20),
            (32, 1, 'punches', 24),
            (33, 1, 'dangles' , 25),
            (34, 1, 'kicks', 25),
            (35, 1, 'debugs', 30),
            (36, 1, 'stamps', 30),
            (37, 1, 'cuffs' , 33),
            (38, 1, 'combats', 38),
            (39, 1, 'hits' , 39),
            (40, 1, 'blunts' , 40),
            (41, 1, 'brats' , 40),
            (42, 1, 'blats' , 45),
            (43, 1, 'tackles' , 45),
            (44, 1, 'cuts' , 50),
            (45, 1, 'dissects', 50),
            (46, 1, 'screws', 50),
            (47, 1, 'slaps' , 50),
            (48, 1, 'bangs' , 55),
            (49, 1, 'battles', 55),
            (50, 1, 'double slaps' , 55),
            (51, 1, 'triple slaps' , 58),
            (52, 1, 'blanches' , 59),
            (53, 1, 'disconnects' , 60),
            (54, 1, 'stomps on', 60),
            (55, 1, 'punishes' , 66),
            (56, 1, 'kills', 70),
            (57, 1, 'eliminates', 71),
            (58, 1, 'damages' , 75),
            (59, 1, 'eleminates' , 79),
            (60, 1, 'disables' , 80),
            (61, 1, 'destroys' , 90),
            (62, 1, 'naruto-runs', 84),

            (63, 2, 'a gay', 15),
            (64, 2, 'a tiny' , 15),
            (65, 2, 'a very small' , 20),
            (66, 2, 'a disgusting', 25),
            (67, 2, 'a rotten' , 25),
            (68, 2, 'a wonderful', 25),
            (69, 2, 'a drooling' , 27),
            (70, 2, 'a sharp', 29),
            (71, 2, 'a hot', 30),
            (72, 2, 'a small' , 30),
            (73, 2, 'a wild', 30),
            (74, 2, 'the frist', 30),
            (75, 2, 'a suspicous', 31),
            (76, 2, 'an electric', 33),
            (77, 2, 'a bloody', 35),
            (78, 2, 'a funny', 35),
            (79, 2, 'a gross', 35),
            (80, 2, 'a poison', 35),
            (81, 2, 'a living', 37),
            (82, 2, 'a' , 40),
            (83, 2, 'a flying', 40),
            (84, 2, 'a mysterious', 40),
            (85, 2, 'an amazing', 40),
            (86, 2, 'an awesome', 40),
            (87, 2, 'a grim', 50),
            (88, 2, 'a large' , 50),
            (89, 2, 'the first', 50),
            (90, 2, 'the one and only', 55),
            (91, 2, 'a huge' , 60),
            (92, 2, 'an unbelievable', 62),
            (93, 2, 'a dangerous', 65),
            (94, 2, 'a monster', 65),
            (95, 2, 'a hellish', 66),
            (96, 2, 'an unholy', 66),
            (97, 2, 'a sexy', 69),
            (98, 2, 'an enormous' , 70),
            (99, 2, 'a giant' , 80),
            (100, 2, 'an epic', 80),
            (101, 2, 'an evil' , 95),

            (102, 3, 'railgun' , 75), 
            (103, 3, 'vacuum cleaner' , 35),
            (104, 3, 'trout' , 25),
            (105, 3, 'monitor', 35),
            (106, 3, 'vacuum', 10),
            (107, 3, 'mouse', 13),
            (108, 3, 'used quote', 11),
            (109, 3, 'chainsaw', 60),
            (110, 3, 'rusty chainsaw', 65),
            (111, 3, 'book', 13),
            (112, 3, 'dictionary', 15),
            (113, 3, 'lightsabre', 78),
            (114, 3, 'toilet paper roll', 18),
            (115, 3, 'WC brush', 15),
            (116, 3, 'big fucking gun', 75),
            (117, 3, 'gravity gun', 65),
            (118, 3, 'frag grenade', 52),
            (119, 3, 'toy', 24),
            (120, 3, 'Deep Blue Computer', 36),
            (121, 3, 'garden gnome', 16),
            (122, 3, 'C64 home computer', 22),
            (123, 3, 'Amiga multimedia computer', 23),
            (124, 3, 'P5 microprocessor', 11),
            (125, 3, 'hadron collider', 50),
            (126, 3, 'hammer', 32),
            (127, 3, 'smithhammer', 38),
            (128, 3, 'pneumatic drill', 35),
            (129, 3, 'screwdriver', 24),
            (130, 3, 'mini elevator', 14),
            (131, 3, 'nunchaku', 45),
            (132, 3, 'ZX Spectrum home computer', 21),
            (133, 3, 'closet', 27),
            (134, 3, 'dandi', 19),
            (135, 3, 'gremlin', 23),
            (136, 3, 'dildo', 18),
            (137, 3, 'black hole', 96),
            (138, 3, 'space station', 74),
            (139, 3, 'comet', 54),
            (140, 3, 'doll', 23),
            (141, 3, 'tape', 17),
            (142, 3, 'strawberry', 12),
            (143, 3, 'sausage', 13),
            (144, 3, 'blog', 17),
            (145, 3, 'ninja', 51),
            (146, 3, 'steak', 20),
            (147, 3, 'sphere of healing', -20),
            (148, 3, 'mashup', 12),
            (149, 3, 'popcorn bucket', 18),
            #(150, 3, 'dictionary', 22),
            (151, 3, 'google translation', 17),
            (152, 3, 'eel', 19),
            (153, 3, 'shark', 37),
            (154, 3, 'iron', 25),
            (155, 3, 'skull', 18),
            (156, 3, 'deer', 22),
            (157, 3, 'painting', 15),
            (158, 3, 'rainbow', 12),
            (159, 3, 'pot of gold', 23),
            (160, 3, 'grim', 50),
            (161, 3, 'duck', 15),
            (162, 3, 'XBOX', 20),
            (163, 3, 'PS3', 19),
            (164, 3, 'unicorn', 35),
            #(165, 3, 'toilet paper roll', 13),
            (166, 3, 'flamethrower', 45),
            (167, 3, 'sabretooth', 21),
            (168, 3, 'CPU', 13),
            (169, 3, 'edge', 22),
            (170, 3, 'drone strike', 55),
            (171, 3, 'horse', 42),
            (172, 3, 'cactus', 33),
            (173, 3, 'puppy', 12),
            (174, 3, 'boar', 29),
            (175, 3, 'parrot', 27),
            (176, 3, 'link', 21),
            (177, 3, 'savoy', 24),
            (178, 3, 'sandwich', 22),
            (179, 3, 'wrench', 33),
            (180, 3, 'email', 10),
            (181, 3, 'bone', 13),
            (182, 3, 'hummingbird', 11),
            (183, 3, 'backup', 10),
            (184, 3, 'toilet', 39),
            (185, 3, 'tarball', 14),
            (186, 3, 'g-zip', 11),
            (187, 3, 'lighter', 18),
            (188, 3, 'beamer', 42),
            (189, 3, 'dongle', 17),
            (190, 3, 'flying spaghetti monster', 15),
            (191, 3, 'cake', 19),
        ]

        with db_session:
            if self.db.SlapwarzWord.select():
                return

            for id, type, word, damage in words:
                self.db.SlapwarzWord(word=word, type=type, damage=damage)

    def timeout(self):
        return 24 * 60 * 60

    def resolve_nick(self, users, arg):
        if arg in users:
            return arg

        for u in users:
            if u.lower().find(arg.lower()) > -1:
                return u

        return arg

    def execute_parsed(self, connection, event, extra):
        who = event.source.nick
        if irc.client.is_channel(event.target):
            users = [u for u,m in connection.tehbot.users[event.target]]
        else:
            users = []
        victim = self.resolve_nick(users, self.pargs.victim)
        when = time.time()

        words = []
        damages = []
        with db_session:
            ts = select(s.ts for s in self.db.SlapwarzSlap if s.who == who and s.victim == victim).order_by(desc(1)).first()
            last_slap = time.mktime(ts.timetuple()) if ts else 0

            for i in range(4):
                slapword = select(w for w in self.db.SlapwarzWord if w.type == i).random(1)[0]
                words.append(slapword.word)
                damages.append(slapword.damage)

            adverb, verb, adjective, item = words
            slaptext = "%s %s %s %s with %s %s" % (who, adverb, verb, victim, adjective, item)

            if irc.client.is_channel(event.target) and victim in [u for u,m in connection.tehbot.users[event.target]]:
                if when - last_slap < self.timeout():
                    msg = "%s (%s remaining, lost 5 points)" % (slaptext, Plugin.time2str(last_slap + self.timeout(), when))
                else:
                    dmg = round(reduce(lambda x,y: x * (y-10)/100, damages, 10000.0))
                    msg = "%s (%.0f damage)." % (slaptext, dmg)
                    self.db.SlapwarzSlap(ts=datetime.datetime.fromtimestamp(when), who=who, victim=victim, damage=dmg)
            else:
                msg = slaptext + "."

        return msg

class LivinSlapPlugin(StandardCommand):
    def slap2(self, victim):
        return [
                ("me", "slaps %s around a bit with a Piece of bacon" % victim),
                ("say", "Hey, %s, eat some pork!" % victim)
                ]

    def commands(self):
        return "livinslap"

    def execute_parsed(self, connection, event, extra):
        return self.slap2("livinskull")
