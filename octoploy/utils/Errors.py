class MissingParam(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


class MissingVar(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


class ConfigError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


class SkipObject(Exception):
    """
    Indicates that the object in the current context should not be deployed
    """
    def __init__(self, msg: str):
        super().__init__(msg)
