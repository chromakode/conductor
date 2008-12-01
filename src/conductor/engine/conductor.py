from ..musicdb import MusicDB

class Conductor:
    def __init__(self, dbpath):
        self.musicdb = MusicDB(dbpath)
    
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
    
    @classmethod
    def _lookup_descs(cls, f):
        """Performs database lookups foe each track description in the arguments, and calls the decorated method with a list of database Track instances.""" 
        def f_tracks(self, *descs, **kwargs):
            f(self, *[self.get_track(desc) for desc in descs], **kwargs)
        return f_tracks
    
    def record_transition_like(self, previous, current):
        """Called when a user likes a transition."""
        self.score_transition(previous, current, human_amount=1)
        
    def record_transition_dislike(self, previous, current):
        """Called when a user dislikes a transition."""
        self.score_transition(previous, current, human_amount=-1)