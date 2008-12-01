import sys
sys.path.append(".")

import os
import tty

SAMPLEPATH = sys.argv[1]
PLAYCMD = "play -q %s trim 0.1 fade 0 .5 .75"

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

def load_files(c):
    for filename in os.listdir(SAMPLEPATH):
        if filename.endswith(".wav"):
            track = {"track":  os.path.join(SAMPLEPATH, filename),
                     "album":  "Test",
                     "artist": "Tester",
                     "genre":  "Sample"}
            c.touch_track(track)

def main():   
    c = MarkovConductor("/tmp/conductor-demo.db")
    c.load()
    c.init_chain("trackid", "trackid")
    c.init_chain("artistid", "artistid")
    
    load_files(c)
    
    prev = c.choose_next_track()
    c.record_transition(None, prev)
    cur = c.choose_next_track(prev)
    
    cmd = None
    playcount = 0
    while True:
        c.record_transition(prev, cur, False)
        
        if playcount == 0:
            os.system(PLAYCMD % prev["track"])
        os.system(PLAYCMD % cur["track"])
        
        print
        previd = c.get_track(prev).id
        curid = c.get_track(cur).id
        print "%s -> %s" % (previd, curid)
        print "---"
        scores = c.get_transitions_from_id(previd)
        print_histogram(scores)
        
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
    main()