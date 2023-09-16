__all__ = [
    'ExBpmcrawlGeneric',
    'ExBpmcrawlPlaylistNotExists',
    'ExBpmcrawlJobPickupFailed',
    'ExBpmcrawlJobAlreadyExist',
]


class ExBpmcrawlGeneric(Exception):
    pass


class ExBpmcrawlPlaylistNotExists(ExBpmcrawlGeneric):
    pass


class ExBpmcrawlJobPickupFailed(ExBpmcrawlGeneric):
    pass


class ExBpmcrawlJobAlreadyExist(ExBpmcrawlGeneric):
    pass
