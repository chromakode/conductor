from __future__ import with_statement

import math
import random
import bisect

from conductor import Conductor, _lookup_descs

def weighted_choice(weight_dict):
    accum = 0
    choices = []
    for item, weight in weight_dict.iteritems():
        accum += weight
        choices.append(accum)
    
    rand = random.random() * accum
    index = bisect.bisect_right(choices, rand)
    
    return weight_dict.keys()[index]

class MarkovConductor(Conductor):    
    def __init__(self, dbpath):
        Conductor.__init__(self, dbpath)
        self.chains = {}
        self.weight_func = self._calculate_weight
        
    def load(self):
        self.musicdb.load()
        self.init()
        
        with self.musicdb.db:
            chains = self.musicdb.db.execute("SELECT * FROM chain").fetchall()
        
        for row in chains:
            # Note: we must convert the row values to ASCII strings (from unicode strings)
            self.init_chain(str(row["fromfield"]), str(row["tofield"]))
        
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
    
    @_lookup_descs
    def record_transition(self, fromtrack, totrack, userchoice=True):
        Conductor.record_transition(self, fromtrack, totrack, userchoice)
        self.score_transition(fromtrack, totrack, amount=1)
    
    def record_user_feedback(self, liked):
        """Called when a user likes or dislikes a transition."""
        Conductor.record_user_feedback(self, liked)
        self.score_transition(user_amount=(1 if liked else -1), *self.last_transition)
    
    def score_transition(self, fromtrack, totrack, amount=0, user_amount=0):
        """Change the inferred score/user score for a transition by a delta."""
        for chain in self.chains.values():
            chain.record_transition(fromtrack.id if fromtrack else None, totrack.id, amount, user_amount)
        
    def choose_next_track(self, fromtrack=None):
        """Determine the next track to play via Markov Chain calculation.
        
        Returns a dictionary containing the name, album, artist, and genre of the chosen track.
        
        """
        
        fromid = self.get_track(fromtrack).id if fromtrack else None
        toid = self.choose_next_id(fromid)
        
        totrack = self.musicdb.get_track_by_id(toid)
        return {"track":  totrack["name"],
                "album":  totrack.album["name"],
                "artist": totrack.artist["name"],
                "genre":  totrack.genre["name"] if totrack.genre else ""}
        
    
    def choose_next_id(self, fromid=None):
        return weighted_choice(self.get_transitions_from_id(fromid))
    
    def _calculate_weight(self, score, user_score):
        """Calculate a weighting based on an inferred score and user-specified score"""
        return math.exp(user_score) * math.exp(score*4)
    
    def get_transitions_from_id(self, fromid=None):
        """Determine the ids and scores of possible following tracks based on the current track id.
        
        Returns: a dictionary of the form { trackid: score, .. }
        
        """
        def if_fromid(truestr, falsestr=""):
            return truestr if fromid else falsestr
        
        with self.musicdb.db:
            sql = " ".join((
                "SELECT totrack.trackid AS totrackid,",
                        
                        # Sum chain scores for each destination track (0 if null)
                        # Scores are normalized by dividing by the total of all scores. Thus, the maximum possible value is 1.
                        #
                        # e.g. ifnull(transition_field_field.score, 0) / (SELECT SUM(score) FROM table WHERE from_field=fromtrack.field)
                        #
                        " + ".join(("ifnull(" +
                                        "CAST(ifnull(%(table)s.score, 0) AS FLOAT)" +
                                        " / (SELECT MAX(10, MAX(score)) FROM %(table)s" +
                                        " WHERE %(fromfield_column)s=" + if_fromid("fromtrack.%(fromfield)s", "-1") + ")" + 
                                    ", 0)")
                                   % {"table": c.table,
                                      "fromfield": c.fromfield,
                                      "fromfield_column": c.fromfield_column}
                                   for c in self.chains.values()),
                        "AS totalscore,",
                        
                        " + ".join(("ifnull(" + 
                                        "ifnull( MAX(-5, MIN(5, %(table)s.userscore)) , 0)"
                                    ", 0)")
                                   % {"table": c.table}
                                   for c in self.chains.values()),
                        "AS totaluserscore",
                                    
                    "FROM " + if_fromid("track fromtrack, ") + "track totrack",
                    
                        # Left join with each chain's matching edges
                        # (such that chain.from_field=fromtrack.fromfield and chain.to_field=totrack.tofield)
                        #
                        # e.g. LEFT JOIN transition_field_field ON (from_field=fromtrack.field AND to_field=totrack.field)
                        #
                        " ".join(("LEFT JOIN %(table)s ON (%(table)s.%(tofield_column)s=totrack.%(tofield)s" +
                                  " AND %(table)s.%(fromfield_column)s=" + if_fromid("fromtrack.%(fromfield)s", "-1") + ")")
                                 % {"table": c.table,
                                    "fromfield": c.fromfield,
                                    "fromfield_column": c.fromfield_column,
                                    "tofield_column": c.tofield_column,
                                    "tofield": c.tofield}
                                 for c in self.chains.values()),
                                    
                    if_fromid("WHERE fromtrack.trackid=%s" % fromid),
                ))
            
            scores = dict((row["totrackid"], self.weight_func(row["totalscore"], row["totaluserscore"])) for row in self.musicdb.db.execute(sql))
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
                    %(fromfield_column)s INTEGER REFERENCES track(%(fromfield)s),
                    %(tofield_column)s INTEGER REFERENCES track(%(tofield)s) NOT NULL,
                    score INTEGER DEFAULT 0,
                    userscore INTEGER DEFAULT 0,
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
    
    def record_transition(self, fromtrackid, totrackid, amount=0, user_amount=0):
        def get_field(trackid, field):
            return self.musicdb.get_track_by_id(trackid)[field];
       
        with self.musicdb.db:
            if fromtrackid:
                fromid = get_field(fromtrackid, self.fromfield)
            else:
                fromid = -1
                
            toid = get_field(totrackid, self.tofield)

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
                    SET score=score+:amount, userscore=userscore+:user_amount
                    WHERE %(fromfield_column)s=:fromid AND %(tofield_column)s=:toid
                """ % {"table": self.table, "fromfield_column": self.fromfield_column, "tofield_column": self.tofield_column},
                {"fromid": fromid, "toid": toid, "amount": amount, "user_amount": user_amount})
    