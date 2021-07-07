import hashlib

import yaml

from config.Config import ProjectConfig, AppConfig, RunMode
from oc.Oc import Oc, K8Api


class OcObjectDeployer:
    """
    Deploys single openshift objects
    """

    HASH_ANNOTATION = 'yml-hash'

    def __init__(self, root_config: ProjectConfig, oc: Oc, app_config: AppConfig, mode: RunMode = RunMode()):
        self._root_config = root_config  # type: ProjectConfig
        self._app_config = app_config  # type: AppConfig
        self._oc = oc  # type: K8Api
        self._mode = mode

    def select_project(self):
        """
        Selects the required openshift project
        """
        context = self._root_config.get_oc_context()
        if context is not None:
            self._oc.switch_context(context)
        self._oc.project(self._root_config.get_oc_project_name())

    def deploy_object(self, data: dict):
        """
        Deploy the given object (if a deployment required, otherwise does nothing)
        :param data: Data which should be deployed
        """

        # Sort the content so it's always reproducible
        str_repr = yaml.dump(data, sort_keys=True)
        # Sanity check
        if '${' in str_repr:
            raise ValueError('At least one variable could not been resolved: ' + str_repr)

        hash_val = hashlib.md5(str_repr.encode('utf-8')).hexdigest()

        item_name = data['kind'] + '/' + data['metadata']['name']
        description = self._oc.get(item_name)
        current_hash = None
        if description is not None:
            current_hash = description.get_annotation(self.HASH_ANNOTATION)

        if description is not None and current_hash is None:
            # Item has not been deployed yet with this script, assume both are the same
            print('Updating annotation of ' + item_name)
            self._oc.annotate(item_name, self.HASH_ANNOTATION, hash_val)
            return

        if current_hash == hash_val:
            print('No change in ' + item_name)
            return

        if self._mode.plan:
            print('Update required for ' + item_name)
            return

        print('Applying update ' + item_name + ' (item has changed)')
        self._oc.apply(str_repr)
        self._oc.annotate(item_name, 'yml-hash', hash_val)

        item_kind = data['kind'].lower()
        if item_kind == 'ConfigMap'.lower():
            self._reload_config()

    def _reload_config(self):
        """
        Tries to reload the configuration for the app
        """
        reload_actions = self._app_config.get_reload_actions()
        for action in reload_actions:
            action.run(self._oc)
