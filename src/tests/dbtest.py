import sys
sys.path.append(".")

from conductor import musicdb
from utils import run_demo

def main(args):
    db = musicdb.MusicDB("/tmp/musicdb-test.db")
    db.load()
    
    print "Requesting album \"AL-1\"..." 
    al1 = db.get_album("AL-1", True)
    print al1.__dict__
    print
    
    print "Requesting track \"Track-1\" from \"AL-1\" by \"Test\"..." 
    t1 = db.get_track("Track-1", "AL-1", "AR-1", "Test", add=True)
    print t1.__dict__
    print
    
    print "Requesting track \"Track-2\" from \"AL-2\" by \"Test\"..."
    t2 = db.get_track("Track-2", "AL-2", "AR-1", "Test", add=True)
    print t2.__dict__
    print
    
    print "Requesting track \"Track-1\" from \"AL-1\" by \"Test\"..."
    t1_2 = db.get_track("Track-1", "AL-1", "AR-1", "Test", add=True)
    print "First request id: %s; Second request id: %s" % (t1.id, t1_2.id)
    print t1_2.__dict__
    print
    
    db.unload()
    
if __name__ == "__main__":
    run_demo(main)