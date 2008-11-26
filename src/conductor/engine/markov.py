from __future__ import with_statement

from ..musicdb import MusicDB

class MarkovConductor:    
    
    def __init__(self, dbpath):
        self.musicdb = MusicDB(dbpath)
        
    def load(self):
        self.musicdb.load()
        
    def unload(self):
        self.musicdb.unload()
        
    def track_change(self, current, previous):
        track = self.musicdb.get_track(track_name=current["track"], 
                                       album_name=current["album"], 
                                       artist_name=current["artist"], 
                                       genre_name=current["genre"],
                                       add=True)
        track.played()
    
class MarkovChain:
    
    def __init__(self, songdb):
        self.musicdb = musicdb
    
    def create(self, fromfield, tofield):
        with self.musicdb.db:
            self.musicdb.db.execute("""
                CREATE TABLE IF NOT EXISTS after_%(fromfield)s_%(fromfield)s (
                    %(fromfield)s INTEGER,
                    %(tofield)s INTEGER,
                )""" % (fromfield, tofield))
    
    
        