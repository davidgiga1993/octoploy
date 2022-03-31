import yaml


# define a custom representer for strings
def quoted_presenter(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')


class YmlWriter:
    _INIT = False

    @classmethod
    def init(cls):
        if not cls._INIT:
            yaml.add_representer(str, quoted_presenter)
            cls._INIT = True

    @classmethod
    def dump(cls, data, default_flow_style: bool = True) -> str:
        cls.init()
        return yaml.dump(data, sort_keys=True, default_flow_style=default_flow_style)

    @classmethod
    def dump_all(cls, data, file):
        cls.init()
        yaml.dump_all(data, file, default_flow_style=False, sort_keys=True)
