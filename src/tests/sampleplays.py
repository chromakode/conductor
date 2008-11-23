from conductor.engine import conductor

c = conductor.Conductor("conductor-test.db")

c.track_played(c.songdb.get_track("Blue", "Cold", "Colors"), after=c.songdb.get_track("Cyan", "Cold", "Colors"))
c.track_played(c.songdb.get_track("Cyan", "Cold", "Colors"), after=c.songdb.get_track("Green", "Cold", "Colors"))
c.track_played(c.songdb.get_track("Green", "Cold", "Colors"), after=c.songdb.get_track("Purple", "Cold", "Colors"))