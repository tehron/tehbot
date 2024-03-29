from tehbot.plugins import *
import urllib.request, urllib.error, urllib.parse
import json
import re, traceback
import time
import locale
try:
    locale.setlocale(locale.LC_ALL, "US" if Plugin.is_windows() else "en_US")
except:
    pass

searchurl = "https://www.googleapis.com/youtube/v3/videos?key=%s&id=%s&part=snippet,contentDetails,statistics"
# regex = re.compile("youtube.com/watch(\?|\?.*&|\?.*&amp;)v=([0-9a-zA-Z+-_]{11})")
regex = re.compile("(?:https?:\/\/)?(?:www\.)?youtu\.?be(?:\.com)?\/?.*(?:watch|embed)?(?:.*v=|v\/|\/)([\w\-_]+)\&?")

class YoutubeHandler(ChannelHandler):
    def default_settings(self):
        return { "key" : None, "referer" : None }

    def values_to_set(self):
        return ChannelHandler.values_to_set(self) + [ "key", "referer" ]

    def execute(self, connection, event, extra):
        match = None
        try:
            match = regex.search(extra["msg"])
        except:
            traceback.print_exc()

        if match is None:
            return

        vid = match.group(1)

        req = urllib.request.Request(searchurl % (self.settings["key"], vid))
        req.add_header("Referer", self.settings["referer"])

        entry = None
        for i in range(3):
            try:
                print("Try %d to read YT info..." % (i + 1))
                resp = urllib.request.urlopen(req).read()
                resp = json.loads(resp)
                entry = resp["items"][0]
                break
            except:
                time.sleep(0.5)

        if entry is None:
            raise Exception("YT Error")

        name = entry["snippet"]["title"]

        try:
            duration = entry['contentDetails']['duration'][2:].lower()
        except:
            duration = "?"

        try:
            v = int(entry['statistics']['viewCount'])
            views = Plugin.grouped(v)
        except:
            views = "?"

        try:
            l = int(entry['statistics']['likeCount'])
            likes = Plugin.grouped(l)
        except:
            likes = "?"

        try:
            d = int(entry['statistics']['dislikeCount'])
            dislikes = Plugin.grouped(d)
        except:
            dislikes = "?"

        txt = "\x0303[YouTube]\x03 %s (%s) | Views: %s | Likes: +%s/-%s" % (name, duration, views, likes, dislikes)
        return txt
