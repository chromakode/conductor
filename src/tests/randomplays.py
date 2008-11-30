import sys
sys.path.append(".")

import random
from conductor.engine.markov import MarkovConductor

c = MarkovConductor("/tmp/conductor-test.db")
c.load()

tracks = [{"track": "Blue",   "album": "Cold", "artist": "Colors",  "genre": "Electronic"},
          {"track": "Cyan",   "album": "Cold", "artist": "Colors",  "genre": "Electronic"},
          {"track": "Green",  "album": "Cold", "artist": "Colors",  "genre": "Electronic"},
          {"track": "Purple", "album": "Cold", "artist": "Colors",  "genre": "Electronic"},
          {"track": "One",    "album": "Low",  "artist": "Numbers", "genre": "Math Rock"}]

prev = None
for i in range(0, 200):
    cur = random.choice(tracks)
    print cur, prev
    c.record_track_change(prev, cur)
    prev = cur
    
c.unload()