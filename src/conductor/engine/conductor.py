from musicdb import MusicDB

class Conductor:
    
    def init(self, dbpath):
        self.musicdb = MusicDB(dbpath)
        
    def track_played(self, track, after):
        pass