import sys
sys.path.append(".")

import os
import math
import tagpy

from conductor.engine.markov import MarkovConductor
from utils import run_demo, read_chr, print_histogram

PLAYCMD = "play -q \"%s\""
PLAYPREV = False

class Library:
    def __init__(self, conductor):
        self.conductor = conductor
        self.tracks = {}
        self.desc_fields = ["title", "album", "artist", "genre"]
    
    def load_files(self, loadpath):
        for dirpath, dirnames, filenames in os.walk(loadpath):
            filenames.sort()
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
                    
                    self.tracks[self._desc_to_tuple(desc)] = path
                    self.conductor.touch_track(desc)
    
    def _desc_to_tuple(self, desc):
        return tuple(desc[field] for field in self.desc_fields)
    
    def _tuple_to_desc(self, t):
        return dict((self.desc_fields[index], value) for index, value in enumerate(t))
    
    def get_track_path(self, desc):
        return self.tracks[self._desc_to_tuple(desc)]
    
    def find_title(self, title):
        title_index = self.desc_fields.index("title")
        title_lower = title.lower()
        for track in self.tracks.iterkeys():
            if track[title_index].lower() == title_lower:
                return self._tuple_to_desc(track)

class SimpleConsolePlayer:
    def __init__(self):
        self.conductor = None
        self.library = None
        self.current_track = None
        self.previous_track = None
        
    def init(self, music_dirs):
        def calculate_weight_conservative(conductor, score, user_score):
            ease = lambda x, length, height: (math.tanh(x*(math.pi/length))+1)*(height/2)
            num_chains = len(conductor.chains)
            return ease(user_score, 10 * num_chains, 10) * math.pow(2, score)
        
        def calculate_weight_eager(conductor, score, user_score):
            return math.pow(1 + (1.0/len(conductor.chains)), user_score) * (math.sqrt(score) + 1)
        
        self.conductor = MarkovConductor("/tmp/conductor-demo.db",
                                         {"weight_function": calculate_weight_eager})
        self.conductor.load()
        self.conductor.init_chain("trackid", "trackid")
        self.conductor.init_chain("albumid", "albumid")
        self.conductor.init_chain("albumid", "trackid")
        self.conductor.init_chain("albumid", "artistid")
        self.conductor.init_chain("artistid", "artistid")
        self.conductor.init_chain("artistid", "trackid")
        self.conductor.init_chain("genreid", "genreid")
        
        self.library = Library(self.conductor)
        for dir in music_dirs:
            self.library.load_files(dir)
            
    def prompt_track(self):
        track = None
        while track is None:
            title = raw_input("Track title to play next: ")
            track = self.library.find_title(title)
            if not track:
                print "Sorry, that track could not be found. Please try again."
        
        return track

    def prompt_tracks(self):
        titles = raw_input("Track titles (title1, title2, ...) to play next: ").split(",")
        
        tracks = []
        for title in titles:
            title = title.strip()
            track = self.library.find_title(title)
            if track:
                tracks.append(track)
                
        return tracks
        
    def play_track(self, next, userchoice):
        self.previous_track = self.current_track
        self.current_track = next
        
        self.conductor.record_transition(self.previous_track, self.current_track, userchoice)
        print "%s -> %s" % (self.previous_track["title"] if self.previous_track else "[Start]", self.current_track["title"])
        print
        
        if self.previous_track and PLAYPREV and playcount == 0:
            os.system(PLAYCMD % self.library.get_track_path(self.previous_track))
        os.system(PLAYCMD % self.library.get_track_path(self.current_track))
    
    def run(self, args):
        self.init(args)
        
        self.previous_track = None
        self.current_track = None
        playcount = 0
        
        # Command line loop
        while True:               
            if playcount > 0:
                playcount -= 1
            elif self.current_track is not None:
                print "Please enter a key (G = Good, B = Bad): "
                cmd = read_chr().lower()
                
                if self.current_track is not None:
                    if cmd == "g":
                        # Rate "Good!"
                        print "User: that choice was GOOD!"
                        print
                        self.conductor.record_user_feedback(True)
                        
                    elif cmd == "b":
                        # Rate "Bad!"
                        print "User: that choice was BAD!"
                        print
                        self.conductor.record_user_feedback(False)
                        # Return to the previous track to try again.
                        self.current_track = self.previous_track
                        
                    elif cmd == "p":
                        # Play the next 10 tracks without pausing
                        playcount = 10
                        print "Playing %s tracks..." % playcount
                        
                    elif cmd == "c":
                        # Manually choose next track.
                        self.play_track(self.prompt_track(), userchoice=True)
                        continue
                    
                    elif cmd == "s":
                        # Manually choose next tracks.
                        for track in self.prompt_tracks():
                            self.play_track(track, userchoice=True)
                        continue
                    
                    elif cmd == "x":
                        # Forget about the previous track to simulate a session beginning.
                        self.previous_track = None
                        print "New session started."
                        continue
                    
                    elif cmd == "q":
                        # "Quit"
                        print "Bye!"
                        sys.exit()
                    
            curid = self.conductor.get_track(self.current_track).id if self.current_track else None
            scores = self.conductor.get_transitions_from_id(curid)
            print "---"
            print "%s -> ..." % (self.current_track["title"] if self.current_track else "[Start]")
            print_histogram(self.conductor, scores)
            print "---"
            
            self.play_track(self.conductor.choose_next_track(self.current_track), userchoice=False)
        
        self.conductor.unload()
    
if __name__ == "__main__":
    player = SimpleConsolePlayer()
    run_demo(player.run)