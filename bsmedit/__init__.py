from .version import __version__

def to_byte(xpm):
    return [x.encode('utf-8') for x in xpm]
