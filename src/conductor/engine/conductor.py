from songdb import SongDB

class MarkovConductor:
    
    def init(self, dbpath):
        self.songdb = SongDB(dbpath)
        
    def track_played(self, track, after):
        pass
    
class MarkovChain:
    
    def __init__(self, songdb):
        self.songdb = songdb
    
    def create(self, fromfield, tofield):
        with self.songdb.db:
            self.songdb.db.execute("""
                CREATE TABLE IF NOT EXISTS after_%(fromfield)s_%(fromfield)s (
                    %(fromfield) INTEGER,
                    %(tofield) INTEGER,
                )""")
            
        