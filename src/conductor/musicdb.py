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
                CREATE TABLE IF NOT EXISTS artists (
                    artistid INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE
                )""")
            
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS albums (
                    albumid INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT
                )""")
            
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS genres (
                    genreid INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT
                )""")
            
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS tracks (
                    trackid INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    albumid INTEGER REFERENCES albums(albumid) NOT NULL,
                    artistid INTEGER REFERENCES artists(artistid) NOT NULL,
                    genreid INTEGER REFERENCES genres(genreid),
                    lastplayed TIMESTAMP,
                    playcount INTEGER DEFAULT 0
                )""")
            
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    trackid INTEGER PRIMARY KEY,
                    dateplayed DATE
                )""")
            
            # TODO: add indexes here?
            
    def _get_thing_id(self, selectsql, insertsql, add, **kwargs):
        with self.db:
            result = self.db.execute(selectsql, kwargs).fetchone()
            
            if result:
                id = result[0]
            else:
                if add:
                    id = self.db.execute(insertsql, kwargs).lastrowid
                else:
                    return None
       
        return id
            
    def get_artist(self, artist_name, add=False):
        artist_id = self._get_thing_id("SELECT artistid FROM artists WHERE name=:name",
                                       "INSERT INTO artists (name) VALUES (:name)",
                                       add, name=artist_name)
        if artist_id:
            return Artist(self, artist_id, artist_name)
    
    
    def get_album(self, album_name, add=False):
        album_id = self._get_thing_id("SELECT albumid FROM albums WHERE name=:name",
                                      "INSERT INTO albums (name) VALUES (:name)", 
                                      add, name=album_name)
        if album_id:
            return Album(self, album_id, album_name)
        
    def get_genre(self, genre_name, add=False):
        genre_id = self._get_thing_id("SELECT genreid FROM genres WHERE name=:name",
                                      "INSERT INTO genres (name) VALUES (:name)",
                                      add, name=genre_name)
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
        
        track_id = self._get_thing_id("SELECT trackid FROM tracks WHERE name = :name AND albumid = :album_id AND artistid = :artist_id",
                                      "INSERT INTO tracks (name, albumid, artistid, genreid) VALUES (:name, :album_id, :artist_id, :genre_id)", 
                                      add, name=track_name, album_id=album.id, artist_id=artist.id, genre_id=(genre.id if genre_name else None))
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
            self.musicdb.db.execute("UPDATE tracks SET playcount=playcount+1, lastplayed=:now WHERE trackid=:id;", 
                                    {"id": self.id, "now": datetime.datetime.now()})
