import sys
sys.path.append(".")

import random

from conductor.engine.markov import MarkovConductor
from utils import run_demo

def main(args):
    c = MarkovConductor("/tmp/conductor-test.db")
    c.load()
    
    tracks = [{"title": "Blue",   "album": "Cold", "artist": "Colors",  "genre": "Electronic"},
              {"title": "Cyan",   "album": "Cold", "artist": "Colors",  "genre": "Electronic"},
              {"title": "Green",  "album": "Cold", "artist": "Colors",  "genre": "Electronic"},
              {"title": "Purple", "album": "Cold", "artist": "Colors",  "genre": "Electronic"},
              {"title": "One",    "album": "Low",  "artist": "Numbers", "genre": "Math Rock"}]
    
    prev = None
    for i in range(0, 200):
        cur = random.choice(tracks)
        print cur, prev
        c.record_transition(prev, cur)
        prev = cur
        
    c.unload()

if __name__ == "__main__":
    run_demo(main)