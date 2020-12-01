from __future__ import annotations

import os
from typing import List, Dict

from config.ConfigMap import ConfigMap
from config.DeploymentActionConfig import DeploymentActionConfig
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

        project = self.get_project()
        oc = Oc()
        oc.project(project)
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
            raise FileNotFoundError('Config not found: ' + folder_path)
        return AppConfig.load(folder_path)


class AppConfig(YmlConfig):
    """
    Contains the configuration for the deployment of a single app
    """

    def __init__(self, config_root: str, path: str):
        super().__init__(path)
        self._config_root = config_root

    @classmethod
    def load(cls, folder_path: str) -> AppConfig:
        index_file = os.path.join(folder_path, '_index.yml')
        if not os.path.isfile(index_file):
            # Index file missing
            raise FileNotFoundError('No index yml file found: ' + index_file)
        return AppConfig(folder_path, index_file)

    def get_config_maps(self) -> List[ConfigMap]:
        """
        Returns additional config maps which should contain the content of a file
        """
        return [ConfigMap(data) for data in self.data.get('configmaps', [])]

    def enabled(self) -> bool:
        """
        True if this app is enabled
        """
        return self.data.get('enabled', False)

    def is_template(self) -> bool:
        """
        Indicates if this app is a template
        """
        return self.data.get('type', 'app') == 'template'

    def get_config_root(self) -> str:
        """
        Returns the path to the app config folder
        :return: Folder path
        """
        return self._config_root

    def get_pre_template_refs(self) -> List[str]:
        """
        Returns the name of the templates that should be applied before processing own objects

        :return: Template names
        """
        return self.data.get('applyTemplates', [])

    def get_post_template_refs(self) -> List[str]:
        """
        Returns the name of the templates that should be applied after processing own objects

        :return: Template names
        """
        return self.data.get('postApplyTemplates', [])

    def get_reload_actions(self) -> List[DeploymentActionConfig]:
        """
        Returns all actions that should be executed after a configuration change of the app
        """
        return [DeploymentActionConfig(self, x) for x in self.data.get('on-config-change', [])]

    def get_dc_name(self) -> str:
        """
        Returns the configured name of the deployment config
        :return: Name
        """
        return self.data['dc']['name']

    def get_replacements(self) -> Dict[str, str]:
        """
        Returns all variables which are available for the yml files
        :return: Key, value map
        """
        items = self.data.get('vars', {})
        items.update({
            'DC_NAME': self.get_dc_name()
        })
        return items
