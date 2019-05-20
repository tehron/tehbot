import tehbot.plugins as plugins
import urllib2
import json
import re, traceback
import locale
try:
    locale.setlocale(locale.LC_ALL, "US" if plugins.is_windows() else "en_US")
except:
    pass

searchurl = "https://www.googleapis.com/youtube/v3/videos?key=%s&id=%s&part=snippet,contentDetails,statistics"
# regex = re.compile("youtube.com/watch(\?|\?.*&|\?.*&amp;)v=([0-9a-zA-Z+-_]{11})")
regex = re.compile("(?:https?:\/\/)?(?:www\.)?youtu\.?be(?:\.com)?\/?.*(?:watch|embed)?(?:.*v=|v\/|\/)([\w\-_]+)\&?")

info_cache = {}

class YoutubeHandler(plugins.ChannelHandler):
    def default_settings(self):
        return { "key" : None, "referer" : None }

    def config(self, args, dbconn):
        if args[0] == "modify":
            if args[1] == "set":
                if args[2] in ["key", "referer"]:
                    self.settings[args[2]] = args[3]
                    self.save(dbconn)
                    return "Okay"

        return plugins.ChannelHandler.config(self, args, dbconn)

    def execute(self, connection, event, extra, dbconn):
        match = None
        try:
            match = regex.search(extra["msg"])
        except:
            traceback.print_exc()

        if match is None:
            return

        vid = match.group(1)
        #vid = "nw-z_FAyIVc"
        if vid in info_cache:
            txt = info_cache[vid] + " (cached)"
        else:
            req = urllib2.Request(searchurl % (self.settings["key"], vid))
            req.add_header("Referer", self.settings["referer"])
            resp = urllib2.urlopen(req).read()
            resp = json.loads(resp)
            entry = resp["items"][0]
            name = entry["snippet"]["title"]

            try:
                duration = entry['contentDetails']['duration'][2:].lower()
            except:
                duration = "?"

            try:
                v = int(entry['statistics']['viewCount'])
                views = plugins.grouped(v)
            except:
                views = "?"

            try:
                l = int(entry['statistics']['likeCount'])
                likes = plugins.grouped(l)
            except:
                likes = "?"

            try:
                d = int(entry['statistics']['dislikeCount'])
                dislikes = plugins.grouped(d)
            except:
                dislikes = "?"

            txt = "\x0303[YouTube]\x03 %s (%s) | Views: %s | Likes: +%s/-%s" % (name, duration, views, likes, dislikes)
            info_cache[vid] = txt

        return txt
