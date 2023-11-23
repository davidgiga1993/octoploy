from __future__ import annotations

import os
from typing import Optional, Dict, List

from octoploy.api.Oc import Oc, K8, K8sApi
from octoploy.config.AppConfig import AppConfig
from octoploy.config.BaseConfig import BaseConfig
from octoploy.processing import Constants
from octoploy.processing.DataPreProcessor import DataPreProcessor, OcToK8PreProcessor
from octoploy.processing.DecryptionProcessor import DecryptionProcessor
from octoploy.processing.NamespaceProcessor import NamespaceProcessor
from octoploy.processing.TreeWalker import TreeProcessor
from octoploy.processing.YmlTemplateProcessor import YmlTemplateProcessor
from octoploy.state.StateTracking import StateTracking
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

        self.var_override: Dict[str, str] = {}
        """
        Key/value pairs which should be passed to the templating engine.
        These value have priority over already defined values
        """

    def set_override_env(self, env: List[str]):
        """
        Parses a key=value list
        :param env: key=value strings
        """
        for entry in env:
            parts = entry.split('=', 1)
            if len(parts) < 2:
                raise ValueError(f'Could not parse {entry}')
            key = parts[0]
            value = parts[1]
            self.var_override[key] = value


class RootConfig(BaseConfig):
    """
    Root configuration for a project (aka a collection of apps inside a single context/namespace)
    """

    def __init__(self, config_root: str, path: str):
        super().__init__(path)
        self._config_root = config_root
        self._k8s_api = None
        self._library = None  # type: Optional[RootConfig]
        self._global_var_overrides: Dict[str, str] = {}

        inherit = self.data.get('inherit')
        if inherit is not None:
            # Use a library
            parent_dir = os.path.abspath(os.path.join(path, os.pardir, os.pardir))
            lib_dir = os.path.join(parent_dir, inherit)
            if not os.path.isdir(lib_dir):
                raise FileNotFoundError('Library not found: ' + lib_dir)
            self._library = RootConfig.load(lib_dir)
            if not self._library.is_library():
                raise ConfigError('Project ' + inherit + ' referenced as library but is not a library')

        state_name = self.data.get('stateName', '')
        self._state = StateTracking(self.create_api(), state_name)

    def get_var_overrides(self) -> Dict[str, str]:
        return self._global_var_overrides

    @classmethod
    def load(cls, path: str) -> RootConfig:
        return RootConfig(path, os.path.join(path, '_root.yml'))

    def get_state(self) -> StateTracking:
        return self._state

    def initialize_state(self, run_mode: RunMode):
        self._global_var_overrides = run_mode.var_override
        if run_mode.dry_run:
            return
        self._state.restore(self.get_namespace_name())

    def persist_state(self, run_mode: RunMode):
        if run_mode.dry_run or run_mode.plan:
            return
        self._state.store(self.get_namespace_name())

    def get_config_root(self) -> str:
        return self._config_root

    def is_library(self) -> bool:
        """
        Indicates if this collection is a library
        """
        return self.data.get('type', '') == 'library'

    def _get_mode(self) -> str:
        return self.data.get('mode', 'k8s')

    def create_api(self) -> K8sApi:
        """
        Creates a new openshift / k8s client.
        :return: Client
        """
        if self._k8s_api is not None:
            return self._k8s_api

        mode = self._get_mode()
        if mode == 'oc':
            k8s_api = Oc()
        elif mode == 'k8s' or mode == 'k8':
            k8s_api = K8()
        else:
            raise ValueError(f'Invalid mode: {mode}')

        context = self.get_kubectl_context()
        if context is not None:
            k8s_api.switch_context(context)
        self._k8s_api = k8s_api
        return k8s_api

    def get_namespace_name(self) -> Optional[str]:
        """
        Returns the namespace name of this project

        :return: Name or null for libraries or if the namespace should not be changed
        """
        namespace = self.data.get('namespace', self.data.get('project'))
        if namespace is None:
            # Maybe passed via commandline?
            return self._global_var_overrides.get(Constants.VAR_NAMESPACE)
        return namespace

    def get_kubectl_context(self) -> Optional[str]:
        """
        Returns the configuration context name.
        :return: Name or null if the current context should be used
        """
        return self.data.get('context')

    def get_pre_processor(self) -> DataPreProcessor:
        """
        Returns the pre-processor for the current config
        """
        mode = self._get_mode()
        if mode == 'k8s' or mode == 'k8s':
            return OcToK8PreProcessor()
        return DataPreProcessor()

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
        name = self.get_namespace_name()
        if name is not None:
            items.update({
                'OC_PROJECT': name,
                Constants.VAR_NAMESPACE: name
            })

        items.update(self._global_var_overrides)
        return items

    def get_yml_processors(self) -> List[TreeProcessor]:
        """
        Returns all yml processors which should be applied
        :return: Processors
        """
        return [DecryptionProcessor(), NamespaceProcessor(self)]

    def load_app_configs(self) -> List[AppConfig]:
        """
        Loads all app configurations available in this project
        :return:
        """
        items = []
        names = set()
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
            app_name = app_config.get_name()
            if app_name in names:
                raise ValueError(f'The app name {app_name} has already been used')
            names.add(app_name)
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
        return AppConfig(folder_path, index_file, variables, root=self)
