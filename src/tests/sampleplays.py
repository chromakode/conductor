import sys
sys.path.append(".")

from itertools import izip
from conductor.engine.markov import MarkovConductor

c = MarkovConductor("/tmp/conductor-test.db")
c.load()

tracks = [{"track": "Blue",   "album": "Cold", "artist": "Colors",  "genre": "Electronic"},
          {"track": "Cyan",   "album": "Cold", "artist": "Colors",  "genre": "Electronic"},
          {"track": "Green",  "album": "Cold", "artist": "Colors",  "genre": "Electronic"},
          {"track": "Purple", "album": "Cold", "artist": "Colors",  "genre": "Electronic"},
          {"track": "One",    "album": "Low",  "artist": "Numbers", "genre": "Math Rock"}]

for prev, cur in izip([None]+tracks, tracks):
    c.record_transition(prev, cur)
    
c.unload()