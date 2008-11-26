from __future__ import with_statement

import time
from pysqlite2 import dbapi2 as sqlite3

class SongDB:
    
    def __init__(self, path):
        self.path = path
        self.db = None
        
    def load(self):
        self.db = sqlite3.connect(self.path)
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
                    lastplayed DATE,
                    playcount INTEGER DEFAULT 0
                )""")
            
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    trackid INTEGER PRIMARY KEY,
                    dateplayed DATE
                )""")
            
            # TODO: add indexes here?
    
    def get_artist(self, artistname, add=False):
        with self.db:
            result = self.db.execute("""
                SELECT artistid FROM artists
                WHERE name = ?
                """, (artistname,)).fetchone()
            
            if result:
                artistid = result[0]
            else:
                if add:
                    artistid = self.db.execute("""
                        INSERT INTO artists (name) VALUES (?)
                        """, (artistname,)).lastrowid
                else:
                    return None
        
        return Artist(artistid, artistname)
    
    
    def get_album(self, albumname, add=False):
        with self.db:
            result = self.db.execute("""
                SELECT albumid FROM albums
                WHERE name = ?
                """, (albumname,)).fetchone()
            
            if result:
                albumid = result[0]
            else:
                if add:
                    albumid = self.db.execute("""
                        INSERT INTO albums (name) VALUES (?)
                        """, (albumname,)).lastrowid
                else:
                    return None
        
        return Album(albumid, albumname)
    
    def get_track(self, trackname, albumname, artistname, add=False):
        album = self.get_album(albumname, add)
        if not album:
            return None
        
        artist = self.get_artist(artistname, add)
        if not artist:
            return None
        
        with self.db:
            result = self.db.execute("""
                SELECT trackid FROM tracks
                WHERE name = ? AND albumid = ? AND artistid = ?
                """, (trackname, album.id, artist.id)).fetchone()
            
            if result:
                trackid = result[0]
            else:
                if add:
                    trackid = self.db.execute("""
                        INSERT INTO tracks (name, albumid, artistid) VALUES (?, ?, ?)
                        """, (trackname, album.id, artist.id)).lastrowid
                else:
                    return None
        
        return Track(trackid, album, album.artist)
        
class Artist:
    def __init__(self, id, name):
        self.id = id
        self.name = name

class Album:
    def __init__(self, id, name):
        self.id = id
        self.name = name

class Genre:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        
class Track:
    def __init__(self, id, name, album, artist):
        self.id = id
        self.name = name
        self.album = album
        self.artist = artist