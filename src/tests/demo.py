import sys
sys.path.append(".")

import os
import tty

SAMPLEPATH = sys.argv[1]

from conductor.engine.markov import MarkovConductor

def read_chr():
    old_settings = tty.tcgetattr(sys.stdin.fileno())
    tty.setraw(sys.stdin, tty.TCSANOW)
    chr = sys.stdin.read(1)
    tty.tcsetattr(sys.stdin.fileno(), tty.TCSADRAIN, old_settings)
    
    return chr

c = MarkovConductor("/tmp/conductor-demo.db")
c.load()

for filename in os.listdir(SAMPLEPATH):
    if filename.endswith(".wav"):
        track = {"track":  os.path.join(SAMPLEPATH, filename),
                 "album":  "Test",
                 "artist": "Tester",
                 "genre":  "Sample"}
        c.add_track(track)

prev = None    
cur = c.get_next_track()
while True:
    os.system("play %s trim 0.1     fade 0 .5 1.5" % cur["track"])
    
    cmd = read_chr().lower()    
    if cmd == "g":
        c.track_change(prev, cur)
    elif cmd == "q":
        sys.exit()
    
    scores = c.get_transitions_from_id(c.get_track(cur).id)
    print "\n".join("%s:\t%s" % (id, score) for id, score in scores.iteritems())
    
    if not cmd == "b":
        prev = cur
    
    cur = c.get_next_track(cur)
    
c.unload()