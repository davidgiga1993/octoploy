import yaml


class YmlConfig:
    def __init__(self, path: str):
        with open(path, 'r') as stream:
            self.data = yaml.safe_load(stream)
