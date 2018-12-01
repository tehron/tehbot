from tehbot.plugins import *
import tehbot.plugins as plugins
import urllib
import urllib2
import json
import shlex

class TranslatePlugin(StandardPlugin):
    def __init__(self):
        StandardPlugin.__init__(self)
        self.parser.add_argument("words", metavar='W', nargs="+")
        self.parser.add_argument("-f", "--from-lang", default="auto")
        self.parser.add_argument("-t", "--to-lang", default="en")

    def execute(self, connection, event, extra, dbconn):
        prefix = "[Translate]"
        try:
            pargs = self.parser.parse_args(extra["args"], decode=False)
            if self.parser.help_requested:
                return self.parser.format_help().strip()
        except Exception as e:
            return u"Error: %s" % str(e)

        if not pargs.words:
            return

        headers = { 'User-Agent' : 'Mozilla/5.0 (X11; Linux x86_64; rv:14.0) Gecko/20100101 Firefox/14.0.1' }
        data = {
                'client' : 'gtx',
                'sl' : pargs.from_lang,
                'tl' : pargs.to_lang,
                'dt' : 't',
                'q' : ' '.join(pargs.words)
        }

        try:
            url = "https://translate.googleapis.com/translate_a/single?%s"
            url = url % urllib.urlencode(data)
            print url
            req = urllib2.Request(url, headers=headers)
            reply = json.load(urllib2.urlopen(req, timeout=5))
            print reply
            txt = reply[0][0][0]
            answer = u"%s %s" % (plugins.green(prefix), txt)
        except Exception as e:
            answer = u"%s %s" % (plugins.red(prefix), unicode(e))

        return answer

register_plugin(["translate", "tr"], TranslatePlugin())
