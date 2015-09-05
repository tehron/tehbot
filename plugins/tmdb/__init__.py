print "TMDB init"
import plugins
import tmdbsimple as tmdb
import settings
tmdb.API_KEY = settings.tmdb_api_key

def movie(connection, channel, nick, cmd, args):
    """Shows information about movie from themoviedb.org"""
    if not args or not args.strip():
        return plugins.print_help(connection, channel, nick, None, cmd)

    args = args.strip()
    id = -1
    res = tmdb.Search().movie(query=args)
    if res["total_results"] > 0:
        id = res["results"][0]["id"]

    if id < 0:
        return plugins.say(connection, channel, "No such movie.")

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

    plugins.say(connection, channel, txt)
    plugins.say(connection, channel, plugins.split(movie_info["overview"]))

def tv(connection, channel, nick, cmd, args):
    """Shows information about tv series from themoviedb.org"""
    if not args or not args.strip():
        return plugins.print_help(nick, channel, None, cmd)

    args = args.strip()
    id = -1
    res = tmdb.Search().tv(query=args)
    if res["total_results"] > 0:
        id = res["results"][0]["id"]

    if id < 0:
        return plugins.say(connection, channel, "No such tv series.")

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

    plugins.say(connection, channel, txt)
    plugins.say(connection, channel, plugins.split(movie_info["overview"]))

plugins.register_cmd("movie", movie)
plugins.register_cmd("tv", tv)
