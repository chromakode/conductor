from ..musicdb import MusicDB

def _lookup_descs(f):
    """Performs database lookups foe each track description in the arguments, and calls the decorated method with a list of database Track instances.""" 
    def f_tracks(self, *descs, **kwargs):
        f(self, *[self.get_track(desc) for desc in descs], **kwargs)
    return f_tracks

class Conductor:
    def __init__(self, dbpath):
        self.musicdb = MusicDB(dbpath)
        self.last_transition = None
    
    def get_track(self, desc):
        if desc:
            return self.musicdb.get_track(track_name=desc["track"],
                                          album_name=desc["album"],
                                          artist_name=desc["artist"],
                                          genre_name=desc["genre"],
                                          add=True)
            
    def touch_track(self, d):
        """Ensure that the specified track exists within the database."""
        self.get_track(d)

    def record_transition(self, fromtrack, totrack):
        """Called when a track transition occurs."""
        totrack.record_play()
        self.last_transition = (fromtrack, totrack)
    
    def record_transition_like(self):
        """Called when a user likes a transition."""
        pass
            
    def record_transition_dislike(self):
        """Called when a user dislikes a transition."""
        pass