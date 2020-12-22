from tehbot.plugins import *
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import json
import shlex

class TranslatePlugin(StandardCommand):
    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("words", metavar='W', nargs="+")
        self.parser.add_argument("-f", "--from-lang", default="auto")
        self.parser.add_argument("-t", "--to-lang", default="en")

    def commands(self):
        return ["translate", "tr"]

    def execute_parsed(self, connection, event, extra):
        if not self.pargs.words:
            return

        headers = { 'User-Agent' : 'Mozilla/5.0 (X11; Linux x86_64; rv:14.0) Gecko/20100101 Firefox/14.0.1' }
        data = {
                'client' : 'gtx',
                'sl' : Plugin.to_utf8(self.pargs.from_lang),
                'tl' : Plugin.to_utf8(self.pargs.to_lang),
                'dt' : 't',
                'q' : ' '.join(map(Plugin.to_utf8, self.pargs.words))
        }

        try:
            url = "https://translate.googleapis.com/translate_a/single?%s"
            url = url % urllib.parse.urlencode(data)
            req = urllib.request.Request(url, headers=headers)
            reply = json.load(urllib.request.urlopen(req, timeout=5))
            txt = reply[0][0][0]
            prefix = "[Translation %s->%s]" % (reply[2], self.pargs.to_lang)
            answer = "%s %s" % (Plugin.green(prefix), txt)
        except Exception as e:
            answer = "%s %s" % (Plugin.red("[Translation]"), str(e))

        return answer
