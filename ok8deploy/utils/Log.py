import logging
import sys


class ColorFormatter(logging.Formatter):
    grey = '\x1b[38;21m'
    yellow = '\x1b[33;21m'
    red = '\x1b[31;21m'
    bold_red = '\x1b[31;1m'
    reset = '\x1b[0m'
    format = '%(levelname)-.1s %(asctime)-.19s [%(name)s] %(message)s'

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class Log:
    log_level = logging.INFO

    def __init__(self, name: str = None):
        if not hasattr(self, 'log'):
            if name is None:
                name = self.__class__.__name__
            log = logging.getLogger(name)
            if not log.hasHandlers():
                handler = logging.StreamHandler(stream=sys.stdout)
                handler.setFormatter(ColorFormatter())
                log.addHandler(handler)
                log.setLevel(Log.log_level)
            self.log = log

    @classmethod
    def set_debug(cls):
        cls.log_level = logging.DEBUG
