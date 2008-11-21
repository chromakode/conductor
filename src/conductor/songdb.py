from pysqlite2 import dbapi2 as sqlite3

class SongDB:
    
    def __init__(self, path):
        self.path = path
        self._db = None
        
    def connect(self):
        self._db = sqlite3.connect(self.path)
    
    def _init_schema(self):
        pass