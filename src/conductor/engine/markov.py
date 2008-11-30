from __future__ import with_statement

import math
import random
import bisect

from ..musicdb import MusicDB

def weighted_choice(weight_dict):
    accum = 0
    choices = []
    for item, weight in weight_dict.iteritems():
        accum += weight
        choices.append(accum)
    
    rand = random.random() * accum
    index = bisect.bisect_right(choices, rand)
    
    return weight_dict.keys()[index]

class MarkovConductor:    
    
    def __init__(self, dbpath):
        self.musicdb = MusicDB(dbpath)
        self.chains = {}
        
    def load(self):
        self.musicdb.load()
        self.init()
        
        with self.musicdb.db:
            chains = self.musicdb.db.execute("SELECT * FROM chain").fetchall()
        
        for row in chains:
            self.init_chain(row["fromfield"], row["tofield"])
        
    def unload(self):
        self.musicdb.unload()
        
    def init(self):
        with self.musicdb.db:
            self.musicdb.db.execute("""
                CREATE TABLE IF NOT EXISTS chain (
                    fromfield TEXT NOT NULL,
                    tofield TEXT NOT NULL,
                    score INTEGER DEFAULT 0,
                    total INTEGER DEFAULT 0,
                    PRIMARY KEY (fromfield, tofield)
                )""")
    
    def init_chain(self, fromfield, tofield):
        if not (fromfield, tofield) in self.chains:
            chain = MarkovChain(self.musicdb, fromfield, tofield)
            chain.init()
            self.chains[(fromfield, tofield)] = chain
    
    def get_track(self, d):
        if d:
            return self.musicdb.get_track(track_name=d["track"],
                                          album_name=d["album"],
                                          artist_name=d["artist"],
                                          genre_name=d["genre"],
                                          add=True)
            
    def add_track(self, d):
        self.get_track(d)
        
    def track_change(self, previous, current):
        prevtrack = self.get_track(previous)
        track = self.get_track(current)
        
        track.record_play()
        if prevtrack:
            self.score_transition_by_id(prevtrack.id, track.id, amount=1)
    
    def score_transition(self, previous, current, amount=0, human_amount=0):
        prevtrack = self.get_track(previous)
        track = self.get_track(current)
        self.score_transition_by_id(prevtrack.id, track.id, amount, human_amount)
    
    def score_transition_by_id(self, fromid, toid, amount=0, human_amount=0):
        for chain in self.chains.values():
            chain.record_transition(fromid, toid, amount, human_amount)
        
    def get_next_track(self, fromtrack=None):
        fromid = self.get_track(fromtrack).id if fromtrack else None
        toid = self.choose_next_id(fromid)
        
        totrack = self.musicdb.get_track_by_id(toid)
        return {"track":  totrack["name"],
                "album":  totrack.album["name"],
                "artist": totrack.artist["name"],
                "genre":  totrack.genre["name"]}
        
    
    def choose_next_id(self, fromid=None):
        return weighted_choice(self.get_transitions_from_id(fromid))
    
    def get_transitions_from_id(self, fromid=None):
        def if_fromid(str):
            return str if fromid else ""
        
        with self.musicdb.db:
            sql = " ".join((
                "SELECT totrack.trackid AS totrackid,",
                        
                        # Sum chain scores for each destination track (0 if null)
                        # Scores are normalized by dividing by the total of all scores. Thus, the maximum possible value is 1.
                        #
                        # e.g. ifnull(transition_field_field.score, 0) / (SELECT SUM(score) FROM table WHERE from_field=fromtrack.field)
                        #
                        " + ".join(("ifnull(%(table)s.humanscore, 0) AS totalhumanscore, " +
                                    "ifnull( CAST(ifnull(%(table)s.score, 0) AS FLOAT)" +
                                    " / (SELECT MAX(10, MAX(score)) FROM %(table)s" +
                                    if_fromid(" WHERE %(fromfield_column)s=fromtrack.%(fromfield)s") + "), 0)")
                                   % {"table": c.table,
                                      "fromfield": c.fromfield,
                                      "fromfield_column": c.fromfield_column}
                                   for c in self.chains.values()),
                        "AS totalscore",
                                    
                    "FROM " + if_fromid("track fromtrack, ") + "track totrack",
                    
                        # Left join with each chain's matching edges
                        # (such that chain.from_field=fromtrack.fromfield and chain.to_field=totrack.tofield)
                        #
                        # e.g. LEFT JOIN transition_field_field ON (from_field=fromtrack.field AND to_field=totrack.field)
                        #
                        " ".join(("LEFT JOIN %(table)s ON (%(table)s.%(tofield_column)s=totrack.%(tofield)s" +
                                  if_fromid(" AND %(table)s.%(fromfield_column)s=fromtrack.%(fromfield)s") + ")")
                                 % {"table": c.table,
                                    "fromfield": c.fromfield,
                                    "fromfield_column": c.fromfield_column,
                                    "tofield_column": c.tofield_column,
                                    "tofield": c.tofield}
                                 for c in self.chains.values()),
                                    
                    if_fromid("WHERE fromtrack.trackid=%s" % fromid),
                ))
            
            scores = dict((row["totrackid"], math.exp(row["totalhumanscore"])*math.exp(row["totalscore"]*4)) for row in self.musicdb.db.execute(sql))
            return scores
    
class MarkovChain:
    
    def __init__(self, musicdb, fromfield, tofield):
        self.musicdb = musicdb
        self.fromfield = fromfield
        self.tofield = tofield
    
    @property
    def table(self):
        return "chain_"+self.fromfield+"_"+self.tofield
    
    @property
    def fromfield_column(self):
        return "from_"+self.fromfield
    
    @property
    def tofield_column(self):
        return "to_"+self.tofield
    
    def init(self):
        with self.musicdb.db:
            self.musicdb.db.execute("""
                INSERT OR IGNORE
                    INTO chain (fromfield, tofield)
                    VALUES (:fromfield, :tofield)
                """, {"fromfield": self.fromfield, "tofield": self.tofield})
                        
            self.musicdb.db.execute("""
                CREATE TABLE IF NOT EXISTS %(table)s (
                    %(fromfield_column)s INTEGER REFERENCES tracks(%(fromfield)s) NOT NULL,
                    %(tofield_column)s INTEGER REFERENCES tracks(%(tofield)s) NOT NULL,
                    score INTEGER DEFAULT 0,
                    humanscore INTEGER DEFAULT 0,
                    PRIMARY KEY (%(fromfield_column)s, %(tofield_column)s)
                )""" % {"table": self.table,
                        "fromfield": self.fromfield,
                        "fromfield_column": self.fromfield_column,
                        "tofield": self.tofield,
                        "tofield_column": self.tofield_column})
            
    def delete(self):
        with self.musicdb.db:
            self.musicdb.db.execute("DROP TABLE %(table)s" % {"table": self.table})
            
            self.musicdb.db.execute("""
                DELETE FROM chain
                WHERE fromfield=:fromfield, tofield=:tofield
                """, {"fromfield": self.fromfield, "tofield": self.tofield})
        
    def reset(self):
        with self.musicdb.db:
            self.musicdb.db.execute("DELETE FROM %(table)s" % {"table": self.table})
    
    def record_transition(self, fromtrackid, totrackid, amount=0, human_amount=0):
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
                    SET score=score+:amount, humanscore=humanscore+:human_amount
                    WHERE %(fromfield_column)s=:fromid AND %(tofield_column)s=:toid
                """ % {"table": self.table, "fromfield_column": self.fromfield_column, "tofield_column": self.tofield_column},
                {"fromid": fromid, "toid": toid, "amount": amount, "human_amount": human_amount})
    