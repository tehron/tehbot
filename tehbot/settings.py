import sqlite3
import json

class Settings:
    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        self.values[key] = value

    def init(self, dbconn):
        with dbconn:
            dbconn.execute("create table if not exists Settings(key text primary key, value text)")
        self.upgrade_database(dbconn)

    def database_version(self):
        return 1

    def upgrade_database(self, dbconn):
        with dbconn:
            while True:
                c = dbconn.execute("select value from Settings where key='DatabaseVersion'")
                res = c.fetchone()
                if res is not None:
                    version = int(res[0])
                else:
                    version = 0

                if version == self.database_version():
                    break

                if version == 0:
                    pass # no automatic db upgrade possible

                dbconn.execute("insert or replace into Settings values('DatabaseVersion', ?)", (str(version + 1),))

    def load(self, dbconn):
        self.values = {
                "botname" : "tehbot",
                "username" : "tehbot",
                "ircname" : "tehbot",
                "cmdprefix" : "?",
                "privpassword" : None,
                "nr_worker_threads" : 10,
                "connections" : { }
                }
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
            dbconn.execute("insert or replace into Settings values('tehbot', ?)", (val,))

    def value(self, key, connection=None):
        if connection is None:
            return self.values.get(key)
        params = self.values["connections"][connection.tehbot.ircid]
        v = params.get(key)
        return v if v is not None else self.values.get(key)

    def connections(self):
        return self.values["connections"]

    def connection_params(self, connection):
        return self.values["connections"][connection.tehbot.ircid]

    def connection_name(self, connection):
        return self.connection_params(connection).get("name", connection.tehbot.ircid)

    def channel_options(self, connection, channel):
        return self.connection_params(connection)["channel_options"].get(channel, { })
