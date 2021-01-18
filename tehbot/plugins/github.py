from tehbot.plugins import *
import requests
import urllib.parse
import json

class GitHubPlugin(StandardCommand):
    """Searches for filenames or file contents on GitHub repositories."""

    def init(self):
        StandardCommand.init(self)
        self.parser.add_argument("-t", "--type", choices=["filename", "content"], default="filename")
        self.parser.add_argument("-r", "--repo", choices=["gwf3", "gdo6"], default="gwf3")
        self.parser.add_argument("search_term")
        self.sess = requests.Session()

    def commands(self):
        return ["gh", "github"]

    def repo(self, r):
        repos = {
                "gwf3" : "gizmore/gwf3",
                "gdo6" : "gizmore/gdo6"
                }
        return repos[r]

    def execute_parsed(self, connection, event, extra):
        prefix = "[GitHub|%s] " % self.pargs.repo

        if self.pargs.type == "filename":
            query = {"q" : "repo:%s filename:%s" % (self.repo(self.pargs.repo), self.pargs.search_term)}
        else:
            query = {"q" : "%s repo:%s" % ("+".join(self.pargs.search_term.split()), self.repo(self.pargs.repo))}
        r = self.sess.get("https://api.github.com/search/code?" + urllib.parse.urlencode(query), timeout=3)

        try:
            data = json.loads(r.content)
        except:
            return Plugin.red(prefix) + "JSON parse error"

        if data["total_count"] == 0:
            return Plugin.red(prefix) + "Found 0 matches"

        if data["total_count"] < 5:
            lst = []
            for i in range(data["total_count"]):
                it = data["items"][i]
                lst.append(it["repository"]["html_url"] + "/blob/master/" + urllib.parse.quote(it["path"]))
            txt = " | ".join(lst)
        else:
            txt = "Found %d matches" % data["total_count"]
            if data["total_count"] < 15:
                txt += ": "
                lst = []
                for i in range(data["total_count"]):
                    it = data["items"][i]
                    lst.append(it["name"])
                txt += ", ".join(lst)
        return Plugin.green(prefix) + txt
