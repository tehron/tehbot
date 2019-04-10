from tehbot.plugins import *
import tehbot.plugins as plugins
import urllib
import urllib2
import json
import shlex

class TranslatePlugin(StandardCommand):
    def __init__(self):
        StandardCommand.__init__(self)
        self.parser.add_argument("words", metavar='W', nargs="+")
        self.parser.add_argument("-f", "--from-lang", default="auto")
        self.parser.add_argument("-t", "--to-lang", default="en")

    def commands(self):
        return ["translate", "tr"]

    def execute_parsed(self, connection, event, extra, dbconn):
        prefix = "[Translate]"

        if not self.pargs.words:
            return

        headers = { 'User-Agent' : 'Mozilla/5.0 (X11; Linux x86_64; rv:14.0) Gecko/20100101 Firefox/14.0.1' }
        data = {
                'client' : 'gtx',
                'sl' : to_utf8(self.pargs.from_lang),
                'tl' : to_utf8(self.pargs.to_lang),
                'dt' : 't',
                'q' : ' '.join(map(to_utf8, self.pargs.words))
        }

        try:
            url = "https://translate.googleapis.com/translate_a/single?%s"
            url = url % urllib.urlencode(data)
            req = urllib2.Request(url, headers=headers)
            reply = json.load(urllib2.urlopen(req, timeout=5))
            txt = reply[0][0][0]
            answer = u"%s %s" % (plugins.green(prefix), txt)
        except Exception as e:
            answer = u"%s %s" % (plugins.red(prefix), unicode(e))

        return answer
