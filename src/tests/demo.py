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

def print_histogram(score_dict):
    max_score = max(score_dict.values())
    total = sum(score_dict.values())
    for id, score in score_dict.iteritems():
        print "%4d: %5.2f (%5.2f) %s" % (id, score, 100*score/total, "-"*int(50*(score/max_score)))
    
c = MarkovConductor("/tmp/conductor-demo.db")
c.load()
c.init_chain("trackid", "trackid")
c.init_chain("artistid", "artistid")

for filename in os.listdir(SAMPLEPATH):
    if filename.endswith(".wav"):
        track = {"track":  os.path.join(SAMPLEPATH, filename),
                 "album":  "Test",
                 "artist": "Tester",
                 "genre":  "Sample"}
        c.add_track(track)

prev = c.get_next_track()
cur = c.get_next_track(prev)
cmd = None
while True:
    os.system("play %s trim 0.1 fade 0 .5 .75" % prev["track"])
    os.system("play %s trim 0.1 fade 0 .5 .75" % cur["track"])
    
    print
    previd = c.get_track(prev).id
    curid = c.get_track(cur).id
    print "%s -> %s" % (previd, curid)
    print "---"
    scores = c.get_transitions_from_id(previd)
    print_histogram(scores)
    
    cmd = read_chr().lower()    
    if cmd == "g":
        c.score_transition(prev, cur, human_amount=1)
    elif cmd == "b":
        c.score_transition(prev, cur, human_amount=-1)
    elif cmd == "q":
        sys.exit()
    
    # If the last choice wasn't bad, continue to the next track
    if not cmd == "b":
        c.track_change(prev, cur)
        prev = cur
    
    cur = c.get_next_track(prev)
    
c.unload()