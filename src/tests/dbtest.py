import sys
sys.path.append(".")

from conductor import musicdb
from utils import run_demo

def main(args):
    db = musicdb.MusicDB("/tmp/musicdb-test.db")
    db.load()
    
    al1 = db.get_album("AL-1", True)
    print al1.__dict__
    
    t1 = db.get_track("Track-1", "AL-1", "AR-1", "Test", add=True)
    print t1.__dict__
    
    t2 = db.get_track("Track-2", "AL-2", "AR-1", "Test", add=True)
    print t2.__dict__
    
    t1_2 = db.get_track("Track-1", "AL-1", "AR-1", "Test", add=True)
    print t1.id == t1_2.id, t1_2.__dict__
    
    db.unload()
    
if __name__ == "__main__":
    run_demo(main)