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
                
    def get_transitions_from_id(self, fromid):
        with self.musicdb.db:
            sql = " ".join((
                "SELECT totrack.trackid as totrackid,",
                        
                        # Sum chain scores for each destination track (0 if null)
                        # Scores are normalized by dividing by the total of all scores. Thus, the maximum possible value is 1.
                        #
                        # e.g. ifnull(transition_field_field.score, 0)
                        #
                        " + ".join("CAST(ifnull(%(table)s.score, 0) AS FLOAT) / (SELECT SUM(score) FROM %(table)s WHERE %(fromfield_column)s=fromtrack.%(fromfield)s)"
                                   % {"table": c.table,
                                      "fromfield": c.fromfield,
                                      "fromfield_column": c.fromfield_column}
                                   for c in self.chains),
                        "AS totalscore",
                                    
                    "FROM track fromtrack, track totrack",
                    
                        # Left join with each chain's matching edges
                        # (such that chain.from_field=fromtrack.fromfield and chain.to_field=totrack.tofield)
                        #
                        # e.g. LEFT JOIN transition_field_field ON (from_field=fromtrack.field AND to_field=totrack.field)
                        #
                        " ".join("LEFT JOIN %(table)s ON (%(table)s.%(fromfield_column)s=fromtrack.%(fromfield)s AND %(table)s.%(tofield_column)s=totrack.%(tofield)s)"
                                 % {"table": c.table,
                                    "fromfield": c.fromfield,
                                    "fromfield_column": c.fromfield_column,
                                    "tofield_column": c.tofield_column,
                                    "tofield": c.tofield}
                                 for c in self.chains),
                                    
                    "WHERE",
                        "fromtrack.trackid=%s" % fromid,
                        "AND totalscore>0"
                ))
            
            scores = dict((row["totrackid"], row["totalscore"]) for row in self.musicdb.db.execute(sql))
            return scores
    
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
    