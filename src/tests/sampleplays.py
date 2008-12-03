import sys
sys.path.append(".")

import logging
logging.basicConfig(level=logging.DEBUG)

from itertools import izip
from conductor.engine.markov import MarkovConductor

c = MarkovConductor("/tmp/conductor-test.db")
c.load()

tracks = [{"title": "Blue",   "album": "Cold", "artist": "Colors",  "genre": "Electronic"},
          {"title": "Cyan",   "album": "Cold", "artist": "Colors",  "genre": "Electronic"},
          {"title": "Green",  "album": "Cold", "artist": "Colors",  "genre": "Electronic"},
          {"title": "Purple", "album": "Cold", "artist": "Colors",  "genre": "Electronic"},
          {"title": "One",    "album": "Low",  "artist": "Numbers", "genre": "Math Rock"}]

for prev, cur in izip([None]+tracks, tracks):
    c.record_transition(prev, cur)
    
c.unload()