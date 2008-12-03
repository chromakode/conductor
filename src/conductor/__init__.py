import logging
_log = logging.getLogger("conductor")

# Create a "null handler" to prevent logging from affecting applications using this package. 

class NullHandler(logging.Handler):
    def emit(self, record):
        pass
_log.addHandler(NullHandler())