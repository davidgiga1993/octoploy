class MissingParam(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


class MissingVar(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


class ConfigError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
