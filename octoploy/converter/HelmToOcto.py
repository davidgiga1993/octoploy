import os.path
import re
from typing import Dict

import yaml

from octoploy.utils.DictUtils import DictUtils


class HelmToOcto:
    """
    Converts a rendered helm chart (single yml file) to an octoploy project
    """

    MANAGED_BY = 'app.kubernetes.io/managed-by'

    def __init__(self, dest: str):
        self._filter = []
        self._dest = dest
        if not os.path.exists(dest):
            raise FileNotFoundError(f"Destination directory {dest} does not exist")

    def include(self, app_name: str):
        self._filter.append(app_name)

    def convert(self, source: str):
        with open(source) as f:
            data = yaml.load_all(f, Loader=yaml.FullLoader)
            for doc in data:
                if doc is None:
                    continue
                self._convert_doc(doc)

    def _convert_doc(self, doc: Dict[str, any]):
        app_name = 'misc'
        labels = DictUtils.get(doc, 'metadata.labels')
        if labels is not None:
            app_name = labels.get('app.kubernetes.io/component', app_name)
            if self.MANAGED_BY in labels:
                del labels[self.MANAGED_BY]

        if not self._include_app(app_name):
            return
        self._add_to_app(doc, app_name)

    def _add_to_app(self, doc: Dict[str, any], app_name: str):
        app_name = app_name.replace(' ', '-').lower()
        dest = os.path.join(self._dest, app_name)
        if not os.path.exists(dest):
            os.mkdir(dest)
            meta_data = {
                'name': app_name,
            }
            with open(os.path.join(dest, '_index.yml'), 'w') as f:
                yaml.dump(meta_data, f)

        kind = doc.get('kind')
        if kind is None:
            # Empty object?
            return

        file_name = re.sub(r'(?<!^)(?=[A-Z])', '-', kind).lower()
        file_path = os.path.join(dest, file_name + '.yml')
        data = [doc]
        if os.path.exists(file_path):
            # Append
            with open(file_path) as f:
                data = list(yaml.load_all(f, Loader=yaml.FullLoader))
            data.append(doc)

        with open(file_path, 'w') as f:
            yaml.dump_all(data, f)

    def _include_app(self, app_name: str) -> bool:
        if len(self._filter) == 0:
            return True
        return app_name in self._filter
