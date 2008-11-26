from itertools import izip

from conductor.engine import conductor

c = conductor.Conductor("conductor-test.db")

tracks = [{"name": "Blue",   "album": "Cold", "artist": "Colors"},
          {"name": "Cyan",   "album": "Cold", "artist": "Colors"},
          {"name": "Green",  "album": "Cold", "artist": "Colors"},
          {"name": "Purple", "album": "Cold", "artist": "Colors"}]

for cur, prev in izip(tracks, tracks[1:]):
    c.track_played(cur, previous = prev)