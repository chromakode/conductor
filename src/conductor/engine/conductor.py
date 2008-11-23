from songdb import SongDB

class Conductor:
    
    def init(self, dbpath):
        self.songdb = SongDB(dbpath)
        
    def track_played(self, track, after):
        pass