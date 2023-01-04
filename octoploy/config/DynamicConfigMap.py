import os
from typing import Dict


class ConfigMapObject:
    data: Dict
    disable_templating: bool = False

    def __init__(self, data: Dict, disable_templating: bool = False):
        self.data = data
        self.disable_templating = disable_templating


class DynamicConfigMap:
    def __init__(self, data):
        self._data = data
        self.name = data['name']
        self.files = data['files']
        self.disable_templating = data.get('disableTemplating', False)

    def build_object(self, config_root: str) -> ConfigMapObject:
        """
        Creates an configmap object out of this definition
        """
        config_data = {}
        data = {
            'kind': 'ConfigMap',
            'apiVersion': 'v1',
            'metadata': {
                'name': self.name
            },
            'data': config_data
        }

        for file_obj in self.files:
            file = file_obj['file']
            name = file_obj.get('name', os.path.basename(file))
            with open(os.path.join(config_root, file), 'r') as f:
                content = f.read()
            config_data[name] = content

        return ConfigMapObject(data, self.disable_templating)
