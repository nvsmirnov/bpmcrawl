__all__ = [
    'logger', 'logtofile',
    'debug', 'info', 'warning', 'error', 'critical', 'exception', 'debugall',
    'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL',
]

import logging
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL

logging.getLogger("urllib3").setLevel(logging.ERROR)
logger = logging.getLogger('bpmcrawl')
logger.propagate = False

# логирование по умолчанию
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(handler)


def debug(msg, *args, **kwargs):
    global logger
    logger.debug(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    global logger
    logger.info(msg, *args, **kwargs)


def warning(msg, *args, **kwargs):
    global logger
    logger.warning(msg, *args, **kwargs)


def error(msg, *args, **kwargs):
    global logger
    logger.error(msg, *args, **kwargs)


def critical(msg, *args, **kwargs):
    global logger
    logger.critical(msg, *args, **kwargs)


def exception(msg, *args, **kwargs):
    global logger
    logger.exception(msg, *args, **kwargs)


def debugall(msg, *args, **kwargs):
    global logger
    logger.log(DEBUGALL, msg, *args, **kwargs)


def logtofile(fname):
    """
    Задаёт файл журнала.
    Предыдущее назначение логирования удаляет.
    Значения None, "", "-" означают логирование в stdout.
    """
    global logger
    global handler
    debug('%s called' % (whoami()))
    fmt = handler.formatter
    oldhandler = handler
    if fname == None or fname == "" or fname == "-":
        handler = logging.StreamHandler()
    else:
        handler = logging.handlers.WatchedFileHandler(fname)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)-8s] %(message)s'))
    debug('directing log to %r' % (fname))
    logger.addHandler(handler)
    logger.removeHandler(oldhandler)
