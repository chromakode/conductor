from __future__ import with_statement

import logging
import math
import random
import bisect

from conductor import Conductor

_log = logging.getLogger("conductor.markov")

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
    def __init__(self, dbpath, config={}):
        Conductor.__init__(self, dbpath)
        self.chains = {}
        
        # Configuration defaults
        config.update({"weight_func": self._calculate_weight,
                       "min_score_divisor": 10,
                       "default_score": 0,
                       "default_userscore": 0,
                       "min_userscore": -5,
                       "max_userscore": 5})
        self.config = config
        
    def load(self):
        _log.info("Loading MarkovConductor.")
        
        self.musicdb.load()
        self.init()
        
        with self.musicdb.db:
            chains = self.musicdb.execute("SELECT * FROM chain").fetchall()
        
        _log.info("Initializing chains.")
        for row in chains:
            # Note: we must convert the row values to ASCII strings (from unicode strings)
            self.init_chain(str(row["fromfield"]), str(row["tofield"]))
        
    def unload(self):
        self.musicdb.unload()
        
    def init(self):
        _log.info("Initializing schema.")
        
        with self.musicdb.db:
            self.musicdb.execute("""
                CREATE TABLE IF NOT EXISTS chain (
                    fromfield TEXT NOT NULL,
                    tofield TEXT NOT NULL,
                    score INTEGER DEFAULT 0,
                    total INTEGER DEFAULT 0,
                    PRIMARY KEY (fromfield, tofield)
                )""")
    
    def init_chain(self, fromfield, tofield):
        _log.info("Initializing chain: %s -> %s.", fromfield, tofield)
        if not (fromfield, tofield) in self.chains:
            self.musicdb.execute("""
                INSERT OR IGNORE
                    INTO chain (fromfield, tofield)
                    VALUES (:fromfield, :tofield)
                """, {"fromfield": fromfield, "tofield": tofield})
            
            chain = MarkovChain(self.musicdb, fromfield, tofield)
            chain.init()
            self.chains[fromfield, tofield] = chain
    
    def delete_chain(self, fromfield, tofield):
        if (fromfield, tofield) in self.chains:
            self.musicdb.execute("""
                DELETE FROM chain
                WHERE fromfield=:fromfield AND tofield=:tofield
                """, {"fromfield": fromfield, "tofield": tofield})
            
            self.chains[fromfield, tofield].delete()
            del self.chains[fromfield, tofield]
    
    def record_transition(self, fromtrack, totrack, userchoice=True):
        fromtrack, totrack = self._lookup_tracks(fromtrack, totrack)
        _log.info("Recording transition from track %s to %s.", fromtrack.id if fromtrack else "[No track]", totrack.id)
        
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
        fromtrack = self._lookup_tracks(fromtrack)[0]        
        fromid = fromtrack.id if fromtrack else None
        toid = self.choose_next_id(fromid)
        
        totrack = self.musicdb.get_track_by_id(toid)
        return self.get_desc(totrack)
    
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
        
        _log.info("Calculating transitions from track id %s...", fromid)
        with self.musicdb.db:
            sql = " ".join((
                "SELECT totrack.trackid AS totrackid,",
                        
                        # Sum chain scores for each destination track (0 if null)
                        # Scores are normalized by dividing by the total of all scores. Thus, the maximum possible value is 1.
                        #
                        # e.g. ifnull(transition_field_field.score, 0) / (SELECT SUM(score) FROM table WHERE from_field=fromtrack.field)
                        #
                        " + ".join(("CAST(ifnull(%(table)s.score, %(default_score)s) AS FLOAT)" +
                                    "/ ifnull(" +
                                        "(SELECT MAX(%(min_score_divisor)s, MAX(score)) FROM %(table)s" +
                                        " WHERE %(fromfield_column)s=" + if_fromid("fromtrack.%(fromfield)s", "-1") +
                                    "), 1)")
                                   % {"table": c.table,
                                      "fromfield": c.fromfield,
                                      "fromfield_column": c.fromfield_column,
                                      "min_score_divisor": self.config["min_score_divisor"],
                                      "default_score": self.config["default_score"]}
                                   for c in self.chains.values()),
                        "AS totalscore,",
                        
                        " + ".join(("ifnull(" + 
                                        "MAX(%(min_userscore)s, MIN(%(max_userscore)s, %(table)s.userscore))" +
                                    ", %(default_userscore)s)")
                                   % {"table": c.table,
                                      "min_userscore": self.config["min_userscore"],
                                      "max_userscore": self.config["max_userscore"],
                                      "default_userscore": self.config["default_userscore"]}
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
            
            scores = {}
            for row in self.musicdb.execute(sql):
                scores[row["totrackid"]] = self.config["weight_func"](row["totalscore"], row["totaluserscore"])
            
            _log.debug("Calculated scores for track id %s: %s.", fromid, repr(scores))
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
        _log.debug("Initializing chain schema: %s -> %s.", self.fromfield, self.tofield)
        with self.musicdb.db:                     
            self.musicdb.execute("""
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
        _log.debug("Deleting chain schema: %s -> %s.", self.fromfield, self.tofield)
        with self.musicdb.db:
            self.musicdb.execute("DROP TABLE %(table)s" % {"table": self.table})
        
    def reset(self):
        _log.debug("Clearing chain data: %s -> %s.", self.fromfield, self.tofield)
        with self.musicdb.db:
            self.musicdb.execute("DELETE FROM %(table)s" % {"table": self.table})
    
    def record_transition(self, fromtrackid, totrackid, amount=0, user_amount=0):
        def get_field(trackid, field):
            return self.musicdb.get_track_by_id(trackid)[field];
       
        _log.debug("Recording transition (%s -> %s) from track %s to %s.", self.fromfield, self.tofield, fromtrackid, totrackid)
       
        with self.musicdb.db:
            if fromtrackid:
                fromid = get_field(fromtrackid, self.fromfield)
            else:
                fromid = -1
                
            toid = get_field(totrackid, self.tofield)

            # "Touch" the transition entry to ensure that it exists
            self.musicdb.execute("""
                INSERT OR IGNORE
                    INTO %(table)s (%(fromfield_column)s, %(tofield_column)s)
                    VALUES (:fromid, :toid)
                """ % {"table": self.table, "fromfield_column": self.fromfield_column, "tofield_column": self.tofield_column},
                {"fromid": fromid, "toid": toid})
            
            # Increment the score of the transition by one
            self.musicdb.execute("""
                UPDATE %(table)s
                    SET score=score+:amount, userscore=userscore+:user_amount
                    WHERE %(fromfield_column)s=:fromid AND %(tofield_column)s=:toid
                """ % {"table": self.table, "fromfield_column": self.fromfield_column, "tofield_column": self.tofield_column},
                {"fromid": fromid, "toid": toid, "amount": amount, "user_amount": user_amount})
    