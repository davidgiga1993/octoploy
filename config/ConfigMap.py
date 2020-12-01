import os


class ConfigMap:
    def __init__(self, data):
        self._data = data
        self.name = data['name']
        self.files = data['files']

    def build_oc_obj(self, config_root: str):
        """
        Creates an openshift configmap object out of this definition
        :return: Object
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

        return data
