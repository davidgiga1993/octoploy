import logging


class Log:
    def __init__(self, name: str = None):
        if not hasattr(self, 'log'):
            if name is None:
                name = __name__
            self.log = logging.getLogger(name)
