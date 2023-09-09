__all__ = ['ExBpmcrawlGeneric', 'ExBpmcrawlPlaylistNotExists']

class ExBpmcrawlGeneric(Exception):
    pass

class ExBpmcrawlPlaylistNotExists(ExBpmCrawlGeneric):
    pass
