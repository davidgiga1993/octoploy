import os

from octoploy.config.Config import RootConfig
from octoploy.utils.Log import Log


class BackupGenerator(Log):
    """
    Very crude backup implementation.
    """

    def __init__(self, config: RootConfig):
        super().__init__()
        self._config = config

    def create_backup(self, dir_name: str):
        if not os.path.exists(dir_name):
            os.mkdir(dir_name)

        oc = self._config.create_api()
        namespaces = oc.get_namespaces()
        apis = oc._exec(['api-resources', '--namespaced', '-o', 'name']).splitlines()
        for namespace in namespaces:
            namespace = namespace.split('/')[1]
            self.log.info(f'Backup up namespace {namespace}')
            for api in apis:
                try:
                    names = oc._exec(['get', api, '-o', 'name'], namespace=namespace).splitlines()
                except Exception:
                    continue
                self.log.info(f'Backing up api {api}')
                for item in names:
                    output = oc._exec(['get', item, '-o', 'yaml'], namespace=namespace)
                    file_name = namespace + '_' + item.replace('/', '_') + '.yaml'
                    with open(os.path.join(dir_name, file_name), 'w') as f:
                        f.write(output)
