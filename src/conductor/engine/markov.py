from __future__ import with_statement

from ..musicdb import MusicDB

class MarkovConductor:    
    
    def __init__(self, dbpath):
        self.musicdb = MusicDB(dbpath)
        self.chains = [MarkovChain(self.musicdb, "trackid", "trackid"),
                       MarkovChain(self.musicdb, "artistid", "artistid")]
        
    def load(self):
        self.musicdb.load()
        for chain in self.chains:
            chain.init()
        
    def unload(self):
        self.musicdb.unload()
        
    def track_change(self, current, previous):
        def get_track(d):
            if d:
                return self.musicdb.get_track(track_name=d["track"],
                                              album_name=d["album"],
                                              artist_name=d["artist"],
                                              genre_name=d["genre"],
                                              add=True)
        
        track = get_track(current)
        prevtrack = get_track(previous)
        
        track.record_play()
        if prevtrack:
            for chain in self.chains:
                chain.record_transition(prevtrack.id, track.id)
    
class MarkovChain:
    
    def __init__(self, musicdb, fromfield, tofield):
        self.musicdb = musicdb
        self.fromfield = fromfield
        self.tofield = tofield
    
    def init(self):
        with self.musicdb.db:
            self.musicdb.db.execute("""
                CREATE TABLE IF NOT EXISTS transition_%(fromfield)s_%(fromfield)s (
                    from_%(fromfield)s INTEGER REFERENCES tracks(%(fromfield)s) NOT NULL,
                    to_%(tofield)s INTEGER REFERENCES tracks(%(tofield)s) NOT NULL,
                    score INTEGER DEFAULT 0,
                    UNIQUE (from_%(fromfield)s, to_%(tofield)s)
                )""" % {"fromfield": self.fromfield, "tofield": self.tofield})
    
    def record_transition(self, fromtrackid, totrackid):
        with self.musicdb.db:
            row = self.musicdb.db.execute("""
                SELECT fromtrack.%(fromfield)s, totrack.%(tofield)s
                    FROM track fromtrack, track totrack
                    WHERE fromtrack.trackid=:fromtrackid AND totrack.trackid=:totrackid
                """ % {"fromfield": self.fromfield, "tofield": self.tofield},
                {"fromtrackid": fromtrackid, "totrackid": totrackid}).fetchone()
                
            # Tuple unpacking doesn't work on rows :(
            fromid, toid = row[0], row[1]
            
            # "Touch" the transition entry to ensure that it exists
            self.musicdb.db.execute("""
                INSERT OR IGNORE
                    INTO transition_%(fromfield)s_%(fromfield)s (from_%(fromfield)s, to_%(tofield)s) 
                    VALUES (:fromid, :toid)
                """ % {"fromfield": self.fromfield, "tofield": self.tofield},
                {"fromid": fromid, "toid": toid})
            
            # Increment the score of the transition by one
            self.musicdb.db.execute("""
                UPDATE transition_%(fromfield)s_%(fromfield)s
                    SET score=score+1
                    WHERE from_%(fromfield)s=:fromid AND to_%(tofield)s=:toid
                """ % {"fromfield": self.fromfield, "tofield": self.tofield},
                {"fromid": fromid, "toid": toid})
    