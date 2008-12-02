from ..musicdb import MusicDB

def _lookup_descs(f):
    """Performs database lookups foe each track description in the arguments, and calls the decorated method with a list of database Track instances.""" 
    def f_tracks(self, fromdesc, todesc, *args, **kwargs):
        f(self, self.get_track(fromdesc), self.get_track(todesc), *args, **kwargs)
    return f_tracks

class Conductor:
    def __init__(self, dbpath):
        self.musicdb = MusicDB(dbpath)
        self.last_transition = None
    
    def get_track(self, desc):
        if desc:
            return self.musicdb.get_track(track_name=desc["title"],
                                          album_name=desc["album"],
                                          artist_name=desc["artist"],
                                          genre_name=desc["genre"],
                                          add=True)
                       
    def touch_track(self, d):
        """Ensure that the specified track exists within the database."""
        self.get_track(d)

    def record_transition(self, fromtrack, totrack, userchoice):
        """Called when a track transition occurs."""
        totrack.record_play()
        self.musicdb.history.record_transition(fromtrack.id if fromtrack else None, totrack.id, userchoice)
        self.last_transition = (fromtrack, totrack)
    
    def record_user_feedback(self, liked):
        """Called when a user likes or dislikes a transition."""
        self.musicdb.history.record_user_feedback(1 if liked else -1)