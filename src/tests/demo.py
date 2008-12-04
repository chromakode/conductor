import sys
sys.path.append(".")

import os
import tagpy

from conductor.engine.markov import MarkovConductor
from utils import run_demo, read_chr, print_histogram

PLAYCMD = "play -q \"%s\""
PLAYPREV = False

class Library:
    def __init__(self, conductor):
        self.conductor = conductor
        self.tracks = {}
    
    def load_files(self, loadpath):
        for dirpath, dirnames, filenames in os.walk(loadpath):
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                ext = os.path.splitext(path)[1]
                if ext in (".mp3", ".ogg"):
                    print "Loading: %s" % path
                    f = tagpy.FileRef(path)
                    tag = f.tag()
                    
                    desc = {"title":  tag.title,
                            "album":  tag.album,
                            "artist": tag.artist,
                            "genre":  tag.genre}
                    
                    self.tracks[tuple(desc.values())] = path
                    self.conductor.touch_track(desc)
           
    def get_track_path(self, desc):
        return self.tracks[tuple(desc.values())]

def main(args):   
    c = MarkovConductor("/tmp/conductor-demo.db")
    c.load()
    c.init_chain("trackid", "trackid")
    c.init_chain("albumid", "albumid")
    c.init_chain("artistid", "artistid")
    
    library = Library(c)
    for dir in args:
        library.load_files(dir)
    
    prev = c.choose_next_track()
    c.record_transition(None, prev)
    cur = c.choose_next_track(prev)
    
    cmd = None
    playcount = 0
    while True:
        c.record_transition(prev, cur, False)
        
        if PLAYPREV and playcount == 0:
            os.system(PLAYCMD % library.get_track_path(prev))
        os.system(PLAYCMD % library.get_track_path(cur))
        
        print
        previd = c.get_track(prev).id
        print "%s -> %s" % (prev["title"], cur["title"])
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