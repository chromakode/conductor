import sys
import tty

def read_chr():
    old_settings = tty.tcgetattr(sys.stdin.fileno())
    tty.setraw(sys.stdin, tty.TCSANOW)
    chr = sys.stdin.read(1)
    tty.tcsetattr(sys.stdin.fileno(), tty.TCSADRAIN, old_settings)
    
    return chr

def print_histogram(conductor, score_dict):
    max_score = max(score_dict.values())
    total = sum(score_dict.values())
    for id, score in score_dict.iteritems():
        print "%4d [%20.20s]: %5.2f (%5.2f) %s" % (id, conductor.musicdb.get_track_by_id(id)["name"], score, 100*score/total, "-"*int(50*(score/max_score)))