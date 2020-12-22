from tehbot.plugins import *
import tehbot.plugins as plugins
from urllib.parse import urlparse
import urllib.request, urllib.error, urllib.parse
from struct import unpack
from socket import AF_INET, inet_pton, getaddrinfo

class IsitupPlugin(StandardCommand):
    """Checks if a web server is up."""

    def __init__(self, db):
        StandardCommand.__init__(self, db)
        self.parser.add_argument("host", nargs="?", default="google.com")
        self.parser.add_argument("--no-follow", action="store_true")

    def commands(self):
        return "isitup"

    @staticmethod
    def _check(host):
        def is_ip4_private(ip):
            f = unpack('!I', inet_pton(AF_INET, ip))[0]
            private = (
                [ 2130706432, 4278190080 ], # 127.0.0.0,   255.0.0.0   http://tools.ietf.org/html/rfc3330
                [ 3232235520, 4294901760 ], # 192.168.0.0, 255.255.0.0 http://tools.ietf.org/html/rfc1918
                [ 2886729728, 4293918720 ], # 172.16.0.0,  255.240.0.0 http://tools.ietf.org/html/rfc1918
                [ 167772160,  4278190080 ], # 10.0.0.0,    255.0.0.0   http://tools.ietf.org/html/rfc1918
            ) 
            for net in private:
                if (f & net[1]) == net[0]:
                    return True
            return False

        try:
            ip = getaddrinfo(host, None, AF_INET)[0][4][0]
            return not is_ip4_private(ip)
        except:
            pass
        return False

    @staticmethod
    def isitup(prot, host, no_follow):
        if not IsitupPlugin._check(host):
            return False

        class MyRequest(urllib.request.Request):
            def __init__(self, url, method, **kwargs):
                urllib.request.Request.__init__(self, url, **kwargs)
                self.method = method

            def get_method(self):
                return self.method

        class MyHTTPRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, hdrs, newurl):
                if no_follow:
                    return None
                return urllib.request.HTTPRedirectHandler.redirect_request(self, req, fp, code, msg, hdrs, newurl)

        try:
            opener = urllib.request.build_opener(MyHTTPRedirectHandler)
            req = MyRequest("%s://%s" % (prot, host), "HEAD")
            res = opener.open(req, timeout=5)
            return 200 <= res.code < 300
        except urllib.error.HTTPError as e:
            return 200 <= e.code < 400
        except Exception as e:
            print(e)
        return False

    def execute_parsed(self, connection, event, extra):
        parts = urlparse(self.pargs.host)
        no_follow = self.pargs.no_follow

        if not parts.scheme:
            parts = urlparse("http://" + self.pargs.host)

        if not parts.scheme or not parts.netloc:
            return "Error: unparsable url"

        host = parts.netloc
        prot = parts.scheme

        if prot != "http" and prot != "https":
            return "Error: only scheme http and https supported"

        res = IsitupPlugin.isitup(prot, host, no_follow)

        prefix = "\x0303[Isitup]\x03 "
        msg = "%s is \x0303up \U0001f44d\x03." if res else "%s seems to be \x0304down \U0001f44e\x03."
        return prefix + msg % (prot + "://" + host)
