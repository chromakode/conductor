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
    
    @property
    def table(self):
        return "transition_"+self.fromfield+"_"+self.tofield
    
    @property
    def fromfield_column(self):
        return "from_"+self.fromfield
    
    @property
    def tofield_column(self):
        return "to_"+self.tofield
    
    def init(self):
        with self.musicdb.db:
            self.musicdb.db.execute("""
                CREATE TABLE IF NOT EXISTS %(table)s (
                    %(fromfield_column)s INTEGER REFERENCES tracks(%(fromfield)s) NOT NULL,
                    %(tofield_column)s INTEGER REFERENCES tracks(%(tofield)s) NOT NULL,
                    score INTEGER DEFAULT 0,
                    UNIQUE (%(fromfield_column)s, %(tofield_column)s)
                )""" % {"table": self.table,
                        "fromfield": self.fromfield,
                        "fromfield_column": self.fromfield_column,
                        "tofield": self.tofield,
                        "tofield_column": self.tofield_column})
    
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
                    INTO %(table)s (%(fromfield_column)s, %(tofield_column)s)
                    VALUES (:fromid, :toid)
                """ % {"table": self.table, "fromfield_column": self.fromfield_column, "tofield_column": self.tofield_column},
                {"fromid": fromid, "toid": toid})
            
            # Increment the score of the transition by one
            self.musicdb.db.execute("""
                UPDATE %(table)s
                    SET score=score+1
                    WHERE %(fromfield_column)s=:fromid AND %(tofield_column)s=:toid
                """ % {"table": self.table, "fromfield_column": self.fromfield_column, "tofield_column": self.tofield_column},
                {"fromid": fromid, "toid": toid})
    