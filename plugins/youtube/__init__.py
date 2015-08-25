print "youtube init"
import plugins
import urllib2
import json
import re, traceback
import locale
locale.setlocale(locale.LC_ALL, "US" if plugins.is_windows() else "en_US")

API_KEY = "your api key here"
REFERER = "your referer here"

searchurl = "https://www.googleapis.com/youtube/v3/videos?key=%s&id=%s&part=snippet,contentDetails"
regex = re.compile("youtube.com/watch(\?|\?.*&|\?.*&amp;)v=([0-9a-zA-Z+-_]{11})")

info_cache = {}

def extract_time(entry):
    try:        
        dur = entry['contentDetails']['duration']
        try:
            minutes = int(dur[2:4]) * 60
        except:
            minutes = 0
        try:
            hours = int(dur[:2]) * 60 * 60
        except:
            hours = 0

        secs = int(dur[5:7])
        print hours, minutes, secs
        video.duration = hours + minutes + secs
        return video.duration
    except Exception as e:
        print "Couldnt extract time: %s" % e

def yt_search(connection, channel, nick, cmd, args):
    if not args:
        return plugins.print_help(connection, channel, nick, None, cmd)

# format:
# [YouTube] | Title: Doom II Speedrun | Rate: 4.81/5.00 | Views: 260,638

def print_info(connection, channel, nick, msg):
    match = None
    try:
        match = regex.search(msg)
    except:
        traceback.print_exc()
        
    if match is None:
        return
    
    vid = match.group(2)
    #vid = "nw-z_FAyIVc"
    if vid in info_cache:
        txt = info_cache[vid] + " (cached)"
    else:
        req = urllib2.Request(searchurl % (API_KEY, vid))
        req.add_header("Referer", REFERER)
        resp = urllib2.urlopen(req).read()
        print resp
        resp = json.loads(resp)
        entry = resp["items"][0]
        name = entry["snippet"]["title"]
        duration = entry['contentDetails']['duration'][2:].lower()

        txt = "\x02[YouTube]\x0f %s (%s)" % (name, duration)
        info_cache[vid] = txt
        
    plugins.say(connection, channel, txt)

plugins.register_channel_handler(print_info)
plugins.register_pub_cmd("youtube", yt_search)
