import sqlite3
import json

class Settings:
    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        self.values[key] = value

    def load(self, dbconn):
        self.values = {
                "botname" : "tehbot",
                "username" : "tehbot",
                "ircname" : "tehbot",
                "cmdprefix" : "?",
                "privpassword" : None,
                "nr_worker_threads" : 10,
                "logging" : {
                    "where" : { },
                    "wherenot" : { },
                    },
                "connections" : { }
                }
        dbconn.execute("create table if not exists Settings(key text primary key, value text)")
        c = dbconn.execute("select value from Settings where key='tehbot'")
        res = c.fetchone()
        if res is not None:
            dt = dict()
            try:
                dt = json.loads(res[0])
            except ValueError as e:
                print u"Internal Error: %s" % unicode(e)
            self.values.update(dt)

    def save(self, dbconn):
        try:
            val = json.dumps(self.values)
        except ValueError as e:
            print u"Internal Error: %s" % unicode(e)
            return

        with dbconn:
            dbconn.execute("create table if not exists Settings(key text primary key, value text)")
            dbconn.execute("insert or replace into Settings values('tehbot', ?)", (val,))


    def value(self, key, connection=None):
        try:
            params = self.values["connections"][connection.name]
            v = params[key]
        except:
            try:
                v = self.values[key]
            except:
                v = None
        return v

    def connections(self):
        return self.values["connections"]

    def connection_params(self, connection):
        return self.values["connections"][connection.name]

    def network_id(self, connection):
        p = self.connection_params(connection)
        return p["id"] if p.has_key("id") else connection.name

    def log_type(self, network, channel):
        where = self.values["logging"]["where"]
        wherenot = self.values["logging"]["wherenot"]

        typ = 0

        for n, ch in wherenot.items():
            if network == n and channel in ch:
                typ = 1
                break

        if where:
            typ = 0

            for n, ch in where.items():
                if network == n and channel in ch:
                    typ = 1
                    break

        return typ
