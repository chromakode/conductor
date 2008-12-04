import sys
sys.path.append(".")

import os

from conductor.engine.markov import MarkovConductor
from utils import run_demo, read_chr, print_histogram

PLAYCMD = "play -q %s trim 0.1 fade 0 .5 .75"

def load_files(c, path):
    for filename in os.listdir(path):
        if filename.endswith(".wav"):
            track = {"title":  filename,
                     "album":  "Test",
                     "artist": "Tester",
                     "genre":  "Sample"}
            c.touch_track(track)

def main(args):
    sample_path = args[0]
    
    c = MarkovConductor("/tmp/conductor-markov-demo.db")
    c.load()
    c.init_chain("trackid", "trackid")
    
    load_files(c, sample_path)
    
    prev = c.choose_next_track()
    c.record_transition(None, prev)
    cur = c.choose_next_track(prev)
    
    cmd = None
    playcount = 0
    while True:
        c.record_transition(prev, cur, False)
        
        if playcount == 0:
            os.system(PLAYCMD % os.path.join(sample_path, prev["title"]))
        os.system(PLAYCMD % os.path.join(sample_path, cur["title"]))
        
        print
        previd = c.get_track(prev).id
        curid = c.get_track(cur).id
        print "%s -> %s" % (previd, curid)
        print "---"
        scores = c.get_transitions_from_id(previd)
        print_histogram(c, scores)
        
        if playcount > 0:
            playcount -= 1
        else:
            cmd = read_chr().lower()
            if cmd == "g":
                c.record_user_feedback(True)
            elif cmd == "b":
                c.record_user_feedback(False)
            elif cmd == "p":
                playcount = 10
            elif cmd == "q":
                sys.exit()
        
        # If the last choice wasn't bad, continue to the next track
        if not cmd == "b":
            prev = cur
        
        cur = c.choose_next_track(prev)
        
    c.unload()
    
if __name__ == "__main__":
    run_demo(main)
