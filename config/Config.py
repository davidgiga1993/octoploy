from __future__ import annotations

import os

from config.AppConfig import AppConfig
from config.YmlConfig import YmlConfig
from oc.Oc import Oc


class RootConfig(YmlConfig):
    """
    Global configuration for all deployments
    """

    def __init__(self, config_root: str, path: str):
        super().__init__(path)
        self._config_root = config_root
        self._oc = None
        self._external_vars = {}

    @classmethod
    def load(cls, path: str) -> RootConfig:
        return RootConfig(path, os.path.join(path, '_root.yml'))

    def get_config_root(self) -> str:
        return self._config_root

    def create_oc(self) -> Oc:
        """
        Creates a new openshift client, preconfigured for this project
        :return: Client
        """
        if self._oc is not None:
            return self._oc

        oc = Oc()
        self._oc = oc
        return oc

    def get_project(self) -> str:
        """
        Returns the name of the openshift project
        :return:
        """
        return self.data['project']

    def load_app_config(self, name: str) -> AppConfig:
        folder_path = os.path.join(self._config_root, name)
        if not os.path.isdir(folder_path):
            raise FileNotFoundError('App folder not found: ' + folder_path)

        index_file = os.path.join(folder_path, '_index.yml')
        if not os.path.isfile(index_file):
            # Index file missing
            raise FileNotFoundError('No index yml file found: ' + index_file)
        return AppConfig(folder_path, index_file, self._external_vars)
