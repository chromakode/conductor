from __future__ import with_statement

import datetime
from pysqlite2 import dbapi2 as sqlite3

class MusicDB:
    
    def __init__(self, path):
        self.path = path
        self.db = None
        
    def load(self):
        self.db = sqlite3.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        self._init_schema()
        
    def unload(self):
        self.db.commit()
        self.db.execute("VACUUM")
        self.db.close()
    
    def _init_schema(self):
        with self.db:           
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS artist (
                    artistid INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE
                )""")
            
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS album (
                    albumid INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT
                )""")
            
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS genre (
                    genreid INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT
                )""")
            
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS track (
                    trackid INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    albumid INTEGER REFERENCES album(albumid) NOT NULL,
                    artistid INTEGER REFERENCES artist(artistid) NOT NULL,
                    genreid INTEGER REFERENCES genre(genreid),
                    lastplayed TIMESTAMP,
                    added TIMESTAMP,
                    playcount INTEGER DEFAULT 0
                )""")
            
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    trackid INTEGER PRIMARY KEY,
                    dateplayed DATE
                )""")
            
            # TODO: add indexes here?
            
    def _get_thing_id(self, selectsql, insertsql, add, params):
        with self.db:
            result = self.db.execute(selectsql, params).fetchone()
            
            if result:
                id = result[0]
            else:
                if add:
                    id = self.db.execute(insertsql, params).lastrowid
                else:
                    return None
       
        return id
            
    def get_artist(self, artist_name, add=False):
        artist_id = self._get_thing_id("SELECT artistid FROM artist WHERE name=:name",
                                       "INSERT INTO artist (name) VALUES (:name)",
                                       add, {"name": artist_name})
        if artist_id:
            return Artist(self, artist_id, artist_name)
    
    
    def get_album(self, album_name, add=False):
        album_id = self._get_thing_id("SELECT albumid FROM album WHERE name=:name",
                                      "INSERT INTO album (name) VALUES (:name)", 
                                      add, {"name": album_name})
        if album_id:
            return Album(self, album_id, album_name)
        
    def get_genre(self, genre_name, add=False):
        genre_id = self._get_thing_id("SELECT genreid FROM genre WHERE name=:name",
                                      "INSERT INTO genre (name) VALUES (:name)",
                                      add, {"name": genre_name})
        if genre_id:
            return Genre(self, genre_id, genre_name)
           
    def get_track(self, track_name, album_name, artist_name, genre_name=None, add=False):
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
        
        track_id = self._get_thing_id("SELECT trackid FROM track WHERE name = :name AND albumid = :album_id AND artistid = :artist_id",
                                      "INSERT INTO track (name, albumid, artistid, genreid, added) VALUES (:name, :album_id, :artist_id, :genre_id, current_timestamp)", 
                                      add, {"name": track_name, "album_id": album.id, "artist_id": artist.id, "genre_id": (genre.id if genre_name else None)})
        if track_id:
            return Track(self, track_id, track_name, album, artist, genre)

class Thing:
    def __init__(self, musicdb, id, name):
        self.musicdb = musicdb
        self.id = id
        self.name = name

class Artist(Thing): pass
class Album(Thing): pass
class Genre(Thing): pass

class Track(Thing):
    def __init__(self, musicdb, id, name, album, artist, genre):
        Thing.__init__(self, musicdb, id, name)
        self.album = album
        self.artist = artist
        self.genre = genre
        
    def played(self):
        with self.musicdb.db:
            self.musicdb.db.execute("UPDATE track SET playcount=playcount+1, lastplayed=current_timestamp WHERE trackid=:id;", 
                                    {"id": self.id})
