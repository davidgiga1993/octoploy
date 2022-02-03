from __future__ import annotations

import os
from typing import Optional, Dict, List

from octoploy.config.AppConfig import AppConfig
from octoploy.config.BaseConfig import BaseConfig
from octoploy.oc.Oc import Oc, K8, K8Api
from octoploy.processing.DataPreProcessor import DataPreProcessor, OcToK8PreProcessor
from octoploy.processing.YmlTemplateProcessor import YmlTemplateProcessor
from octoploy.utils.Errors import ConfigError


class RunMode:
    def __init__(self):
        self.out_file = None  # type: Optional[str]
        """
        Yml output file
        """

        self.dry_run = False
        """
        True if no OC should be called
        """

        self.plan = False
        """
        True if changes should be previewed
        """


class ProjectConfig(BaseConfig):
    """
    Project configuration
    """

    def __init__(self, config_root: str, path: str):
        super().__init__(path)
        self._config_root = config_root
        self._oc = None
        self._library = None  # type: Optional[ProjectConfig]

        inherit = self.data.get('inherit')
        if inherit is not None:
            # Use a library
            parent_dir = os.path.abspath(os.path.join(path, os.pardir, os.pardir))
            lib_dir = os.path.join(parent_dir, inherit)
            if not os.path.isdir(lib_dir):
                raise FileNotFoundError('Library not found: ' + lib_dir)
            self._library = ProjectConfig.load(lib_dir)
            if not self._library.is_library():
                raise ConfigError('Project ' + inherit + ' referenced as library but is not a library')

    @classmethod
    def load(cls, path: str) -> ProjectConfig:
        return ProjectConfig(path, os.path.join(path, '_root.yml'))

    def get_config_root(self) -> str:
        return self._config_root

    def is_library(self) -> bool:
        """
        Indicates if this collection is a library
        """
        return self.data.get('type', '') == 'library'

    def get_pre_processor(self) -> DataPreProcessor:
        """
        Returns the pre processor for the current config
        """
        mode = self._get_mode()
        if mode == 'k8':
            return OcToK8PreProcessor()
        return DataPreProcessor()

    def _get_mode(self) -> str:
        return self.data.get('mode', 'oc')

    def create_oc(self) -> K8Api:
        """
        Creates a new openshift / k8 client
        :return: Client
        """
        if self._oc is not None:
            return self._oc

        mode = self._get_mode()
        if mode == 'oc':
            oc = Oc()
        elif mode == 'k8':
            oc = K8()
        else:
            raise ValueError(f'Invalid mode: {mode}')
        self._oc = oc
        return oc

    def get_oc_project_name(self) -> Optional[str]:
        """
        Returns the name of the openshift project

        :return: Name or null for libraries
        """
        return self.data.get('project')

    def get_oc_context(self) -> Optional[str]:
        """
        Returns the configuration context name
        :return: Name
        """
        return self.data.get('context')

    def get_template_processor(self) -> YmlTemplateProcessor:
        root_processor = super().get_template_processor()
        if self._library is not None:
            processor = self._library.get_template_processor()
            root_processor.parent(processor)
        return root_processor

    def get_replacements(self) -> Dict[str, str]:
        """
        Returns all variables which are available for the yml files
        :return: Key, value map
        """
        items = super().get_replacements()
        name = self.get_oc_project_name()
        if name is not None:
            items.update({
                'OC_PROJECT': name
            })
        return items

    def load_app_configs(self) -> List[AppConfig]:
        """
        Loads all app configurations available in this project
        :return:
        """
        items = []
        for dir_item in os.listdir(self._config_root):
            path = os.path.join(self._config_root, dir_item)
            if not os.path.isdir(path):
                continue
            try:
                app_config = self.load_app_config(dir_item)
            except FileNotFoundError:
                # Index file missing
                continue

            if app_config.is_template() or not app_config.enabled():
                # Silently skip
                continue
            items.append(app_config)
        if self._library is not None:
            items.extend(self._library.load_app_configs())
        return items

    def load_app_config(self, name: str) -> AppConfig:
        folder_path = os.path.join(self._config_root, name)
        if not os.path.isdir(folder_path):
            if self._library is not None:
                return self._library.load_app_config(name)
            raise FileNotFoundError('App folder not found: ' + folder_path)

        index_file = os.path.join(folder_path, '_index.yml')
        if not os.path.isfile(index_file):
            # Index file missing
            raise FileNotFoundError('No index yml file found: ' + index_file)

        variables = self.get_replacements()
        return AppConfig(folder_path, index_file, variables)
