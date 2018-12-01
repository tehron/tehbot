from tehbot.plugins import *
import tehbot.plugins as plugins
import tmdbsimple as tmdb

class MoviePlugin(StandardPlugin):
    """Shows information about movies from themoviedb.org"""

    def __init__(self):
        StandardPlugin.__init__(self)
        self.parser.add_argument("movie")

    def command(self, connection, event, extra, dbconn):
        tmdb.API_KEY = self.settings["tmdb_api_key"]

        id = -1
        res = tmdb.Search().movie(query=self.pargs.movie)
        if res["total_results"] > 0:
            id = res["results"][0]["id"]

        txt = "No such movie."
        if id != -1:
            movie = tmdb.Movies(id)
            movie_info = movie.info()
            txt = "\x02%s\x02" % movie_info["title"]
            if movie_info["title"] != movie_info["original_title"]:
                txt += " (%s)" % movie_info["original_title"]
            if movie_info["release_date"]:
                txt += " | \x02Released:\x02 %s" % movie_info["release_date"]
            if movie_info["vote_count"] > 0:
                txt += " | \x02Rating:\x02 %.1f/10" % movie_info["vote_average"]
            if movie_info["homepage"]:
                txt += " | \x02Homepage:\x02 %s" % movie_info["homepage"]

            txt += "\n" + plugins.split(movie_info["overview"])

        return txt

register_plugin("movie", MoviePlugin())

class TvPlugin(StandardPlugin):
    """Shows information about TV series from themoviedb.org"""

    def __init__(self):
        StandardPlugin.__init__(self)
        self.parser.add_argument("show")

    def command(self, connection, event, extra, dbconn):
        tmdb.API_KEY = self.settings["tmdb_api_key"]

        id = -1
        res = tmdb.Search().tv(query=self.pargs.show)
        if res["total_results"] > 0:
            id = res["results"][0]["id"]

        txt = "No such movie."
        if id != -1:
            movie = tmdb.TV(id)
            movie_info = movie.info()
            txt = "\x02%s\x02" % movie_info["name"]
            if movie_info["name"] != movie_info["original_name"]:
                txt += " (%s)" % movie_info["original_name"]
            if movie_info["first_air_date"]:
                txt += " | \x02First Aired:\x02 %s" % movie_info["first_air_date"]
            if movie_info["number_of_seasons"]:
                txt += " | \x02Nr. of Seasons:\x02 %d" % movie_info["number_of_seasons"]
            if movie_info["vote_count"] > 0:
                txt += " | \x02Rating:\x02 %.1f/10" % movie_info["vote_average"]
            if movie_info["homepage"]:
                txt += " | \x02Homepage:\x02 %s" % movie_info["homepage"]

            txt += "\n" + plugins.split(movie_info["overview"])

        return txt

register_plugin("tv", TvPlugin())
