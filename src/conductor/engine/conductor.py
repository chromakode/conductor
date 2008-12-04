import logging
_log = logging.getLogger("conductor.conductor")

from ..musicdb import MusicDB, Track

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

    def get_desc(self, track):
        return {"title":  track["name"],
                "album":  track.album["name"],
                "artist": track.artist["name"],
                "genre":  track.genre["name"] if track.genre else ""}
            
    def _lookup_tracks(self, *tracks):
        return [self.get_track(track) for track in tracks 
                if not isinstance(track, Track)]
            
    def touch_track(self, d):
        """Ensure that the specified track exists within the database."""
        
        _log.info("Touching track \"%s\" from \"%s\" by \"%s\".", d["title"], d["album"], d["artist"])
        self.get_track(d)

    def record_transition(self, fromtrack, totrack, userchoice):
        """Called when a track transition occurs."""
        totrack.record_play()
        self.musicdb.history.record_transition(fromtrack.id if fromtrack else None, totrack.id, userchoice)
        self.last_transition = (fromtrack, totrack)
    
    def record_user_feedback(self, liked):
        """Called when a user likes or dislikes a transition."""
        self.musicdb.history.record_user_feedback(1 if liked else -1)