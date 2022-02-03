from typing import Optional

import yaml


class YmlConfig:
    def __init__(self, path: Optional[str]):
        self.data = {}
        self._path = path
        if path is not None:
            with open(path, 'r') as stream:
                self.data = yaml.safe_load(stream)
