from __future__ import with_statement

import logging
import datetime
from pysqlite2 import dbapi2 as sqlite3

_log = logging.getLogger("conductor.musicdb")

class MusicDB:
    
    def __init__(self, path):
        self.path = path
        self.db = None
        self.history = None
        
    def load(self):
        _log.info("Loading database file at %s.", self.path)
        
        self.db = sqlite3.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        self.db.row_factory = sqlite3.Row
        self._init_schema()
        self.history = MusicHistory(self)
        self.history.init()
        
    def unload(self):
        self.db.commit()
        self.execute("VACUUM")
        self.db.close()
        
    def execute(self, sql, *params):
        _log.debug("Executing SQL: {%s} %s", sql, repr(params))
        return self.db.execute(sql, *params)
    
    def _init_schema(self):
        _log.info("Initializing database schema.")
        
        with self.db:           
            self.execute("""
                CREATE TABLE IF NOT EXISTS artist (
                    artistid INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE
                )""")
            
            self.execute("""
                CREATE TABLE IF NOT EXISTS album (
                    albumid INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT
                )""")
            
            self.execute("""
                CREATE TABLE IF NOT EXISTS genre (
                    genreid INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT
                )""")
            
            self.execute("""
                CREATE TABLE IF NOT EXISTS track (
                    trackid INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    albumid INTEGER REFERENCES album(albumid) NOT NULL,
                    artistid INTEGER REFERENCES artist(artistid) NOT NULL,
                    genreid INTEGER REFERENCES genre(genreid),
                    lastplayed TIMESTAMP,
                    added TIMESTAMP,
                    playcount INTEGER DEFAULT 0,
                    UNIQUE(name, albumid, artistid)
                )""")
            
            # TODO: add indexes here?
            
    def _get_thing_id(self, selectsql, insertsql, add, params):
        with self.db:
            result = self.execute(selectsql, params).fetchone()
            
            if not result:
                if add:
                    id = self.execute(insertsql, params).lastrowid
                    result = self.execute(selectsql, params).fetchone()
                else:
                    return None
       
        return result
    
    def _get_thing_by_id(self, table, id_column, id, thingclass, *thingargs):
        row = self.execute("SELECT * FROM %(table)s WHERE %(id_column)s = :id"
                              % {"table": table, "id_column": id_column}, {"id": id}).fetchone()
        if row:
            return thingclass(self, row[id_column], row, *thingargs)
            
    def get_artist(self, artist_name, add=False):
        row = self._get_thing_id("SELECT * FROM artist WHERE name=:name",
                                 "INSERT INTO artist (name) VALUES (:name)",
                                 add, {"name": artist_name})
        if row:
            return Artist(self, row["artistid"], row)
    
    
    def get_album(self, album_name, add=False):
        with self.db:
            row = self._get_thing_id("SELECT * FROM album WHERE name=:name",
                                     "INSERT INTO album (name) VALUES (:name)",
                                     add, {"name": album_name})
        if row:
            return Album(self, row["albumid"], row)
        
    def get_genre(self, genre_name, add=False):
        row = self._get_thing_id("SELECT * FROM genre WHERE name=:name",
                                 "INSERT INTO genre (name) VALUES (:name)",
                                 add, {"name": genre_name})
        if row:
            return Genre(self, row["genreid"], row)
           
    def get_track(self, track_name, album_name, artist_name, genre_name=None, add=False):
        _log.info("Retrieving track info for \"%s\" from \"%s\" by \"%s\"...", track_name, album_name, artist_name)
        
        album = self.get_album(album_name, add)
        if not album:
            return None
        
        artist = self.get_artist(artist_name, add)
        if not artist:
            return None
        
        if genre_name:
            genre = self.get_genre(genre_name, add)
            if not genre:
                return None
        else:
            genre = None
        
        row = self._get_thing_id("SELECT * FROM track WHERE name = :name AND albumid = :album_id AND artistid = :artist_id",
                                 "INSERT INTO track (name, albumid, artistid, genreid, added) VALUES (:name, :album_id, :artist_id, :genre_id, :now)", 
                                 add, {"name": track_name,
                                       "album_id": album.id,
                                       "artist_id": artist.id,
                                       "genre_id": (genre.id if genre_name else None),
                                       "now": datetime.datetime.now()})
        if row:
            _log.info("Retrieved track info for \"%s\" from \"%s\" by \"%s\" (id %s).", track_name, album_name, artist_name, row["trackid"])
            return Track(self, row["trackid"], row, album, artist, genre)
        
    def get_track_by_id(self, track_id):
        _log.info("Retrieving track info with id %s...", track_id)
        
        track = self._get_thing_by_id("track", "trackid", track_id, Track)
        track.album = self._get_thing_by_id("album", "albumid", track["albumid"], Album)
        track.artist = self._get_thing_by_id("artist", "artistid", track["artistid"], Artist)
        track.genre = self._get_thing_by_id("genre", "genreid", track["genreid"], Genre)
        return track

class MusicHistory:
    def __init__(self, musicdb):
        self.musicdb = musicdb
    
    def init(self):
        with self.musicdb.db:
            self.musicdb.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    timestamp TIMESTAMP PRIMARY KEY,
                    fromtrackid INTEGER REFERENCES track(trackid),
                    totrackid INTEGER REFERENCES track(trackid),
                    userchoice BOOLEAN,
                    userscore INTEGER DEFAULT 0
                )""")
            
    def record_transition(self, fromtrackid, totrackid, userchoice):
        with self.musicdb.db:
            self.musicdb.execute("""
                INSERT
                    INTO history (timestamp, fromtrackid, totrackid, userchoice)
                    VALUES (:now, :fromtrackid, :totrackid, :userchoice)
                """, {"fromtrackid": fromtrackid,
                      "totrackid": totrackid,
                      "userchoice": userchoice,
                      "now": datetime.datetime.now()})
            
    def record_user_feedback(self, userscore):
        with self.musicdb.db:
            self.musicdb.execute("""
                UPDATE history
                    SET userscore=:userscore
                    WHERE timestamp=(SELECT MAX(timestamp) FROM history)
                """, {"userscore": userscore})

class Thing:
    def __init__(self, musicdb, id, row):
        self.musicdb = musicdb
        self.id = id
        self.row = row
        
    def __getitem__(self, key):
        return self.row[key]

class Artist(Thing): pass
class Album(Thing): pass
class Genre(Thing): pass

class Track(Thing):
    def __init__(self, musicdb, id, row, album=None, artist=None, genre=None):
        Thing.__init__(self, musicdb, id, row)
        self.album = album
        self.artist = artist
        self.genre = genre
        
    def record_play(self):
        with self.musicdb.db:
            self.musicdb.execute("UPDATE track SET playcount=playcount+1, lastplayed=:now WHERE trackid=:id;", 
                                    {"id": self.id, "now": datetime.datetime.now()})
