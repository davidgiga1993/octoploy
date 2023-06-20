import os
from typing import Dict, List, Optional

from octoploy.config.YmlConfig import YmlConfig
from octoploy.processing.ValueLoader import ValueLoaderFactory
from octoploy.processing.YmlTemplateProcessor import YmlTemplateProcessor


class BaseConfig(YmlConfig):
    def __init__(self, path: Optional[str], external_vars: Dict[str, str] = None):
        super().__init__(path)
        self._external_vars = {}  # type: Dict[str, str]
        """
        External variables (for example from forEach loops)
        """
        if external_vars is not None:
            self._external_vars = external_vars

        self._replacements = {}  # type: Dict[str, str]
        """
        Caching field
        """

    def get_file(self, path: str) -> str:
        """
        Returns the path to a file inside the dir of the app/project
        :param path: Relative path
        :return: Path
        """
        base = os.path.dirname(os.path.abspath(self._path))
        return os.path.abspath(os.path.join(base, path))

    def get_template_processor(self) -> YmlTemplateProcessor:
        return YmlTemplateProcessor(self)

    def get_replacements(self) -> Dict[str, any]:
        """
        Returns all variables which are available for the yml files

        :return: Key, value map
        """
        if len(self._replacements) > 0:
            return self._replacements

        items = self.data.get('vars', {})
        new_items = {}
        for key, value in items.items():
            # Value can be a primitive or object
            if isinstance(value, dict):
                # Is an object, use a loader to load the value
                loader_name = value.get('loader')
                if loader_name is not None:
                    loader = ValueLoaderFactory.create(self, value['loader'])
                    new_values = loader.load(value)
                    new_items[key] = 'viaLoader'
                    for new_key, new_val in new_values.items():
                        new_items[key + new_key] = new_val
                    continue

        items.update(new_items)
        items.update(self._external_vars)
        return items

    def get_params(self) -> List[str]:
        """
        Returns all required parameters

        :return: Names
        """
        return self.data.get('params', [])
