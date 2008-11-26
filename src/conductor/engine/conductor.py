from __future__ import with_statement

from conductor.musicdb import MusicDB

class MarkovConductor:
    
    def init(self, dbpath):
        self.musicdb = MusicDB(dbpath)
        
    def track_played(self, trackdata, afterdata):
        track = self.musicdb.get_track(**trackdata)
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
    
    
        