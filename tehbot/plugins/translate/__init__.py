from tehbot.plugins import *
import tehbot.plugins as plugins
import urllib
import urllib2
import lxml.html

class TranslatePlugin(Plugin):
    def execute(self):
        if not self.args:
            return

        headers = { 'User-Agent' : 'Mozilla/5.0 (X11; Linux x86_64; rv:14.0) Gecko/20100101 Firefox/14.0.1' }
        data = { 'sl' : 'auto', 'tl' : 'en', 'hl' : 'en', 'ie' : 'UTF-8', 'q' : plugins.to_utf8(self.args) }
        req = urllib2.Request("https://translate.google.com/", urllib.urlencode(data), headers)
        tree = lxml.html.parse(urllib2.urlopen(req))

        trans = tree.xpath("//span[@id='result_box']")
        if len(trans) > 0:
            txt = trans[0].text_content().strip()
            return "\x0303[Translation]\x03 %s" % txt

register_cmd("translate", TranslatePlugin())
