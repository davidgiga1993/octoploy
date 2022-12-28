import hashlib

import yaml

from octoploy.config.Config import ProjectConfig, AppConfig, RunMode
from octoploy.k8s.BaseObj import BaseObj
from octoploy.oc.Oc import K8sApi
from octoploy.utils.Log import Log
from octoploy.utils.YmlWriter import YmlWriter


class K8sObjectDeployer(Log):
    """
    Deploys k9s object
    """

    HASH_ANNOTATION = 'yml-hash'
    """
    Name of the annotation that stores the hash
    """

    def __init__(self, root_config: ProjectConfig, k8sapi: K8sApi, app_config: AppConfig, mode: RunMode = RunMode()):
        super().__init__()
        self._root_config = root_config  # type: ProjectConfig
        self._app_config = app_config  # type: AppConfig
        self._k8sapi = k8sapi  # type: K8sApi
        self._mode = mode

    def select_namespace(self):
        """
        Selects the required openshift project
        """
        context = self._root_config.get_kubectl_context()
        if context is not None:
            self._k8sapi.switch_context(context)
        namespace = self._root_config.get_namespace_name()
        if namespace is not None:
            self._k8sapi.set_namespace(namespace)

    def deploy_object(self, data: dict):
        """
        Deploy the given object (if a deployment required, otherwise does nothing)
        :param data: Data which should be deployed
        """

        # Sort the content so it's always reproducible
        str_repr = YmlWriter.dump(data)

        hash_val = hashlib.md5(str_repr.encode('utf-8')).hexdigest()

        k8s_object = BaseObj(data)
        # An object might be in a different namespace than the current context
        object_namespace = k8s_object.namespace
        if object_namespace is not None:
            self._k8sapi.set_namespace(object_namespace)

        item_name = k8s_object.kind + '/' + k8s_object.name
        description = self._k8sapi.get(item_name)
        current_hash = None
        if description is not None:
            current_hash = description.get_annotation(self.HASH_ANNOTATION)

        if description is not None and current_hash is None:
            # Item has not been deployed yet with this script, assume both are the same
            self.log.info('Updating annotation of ' + item_name)
            self._k8sapi.annotate(item_name, self.HASH_ANNOTATION, hash_val)
            return

        if current_hash == hash_val:
            self.log.debug('No change in ' + item_name)
            return

        if self._mode.plan:
            self.log.warning('Update required for ' + item_name)
            return

        self.log.info('Applying update ' + item_name + ' (item has changed)')
        self._k8sapi.apply(str_repr)
        self._k8sapi.annotate(item_name, 'yml-hash', hash_val)

        if object_namespace is not None:
            # Use project namespace as default again
            default_namespace = self._root_config.get_namespace_name()
            if default_namespace is not None:
                self._k8sapi.set_namespace(default_namespace)

        if k8s_object.is_kind('ConfigMap'):
            self._reload_config()

    def _reload_config(self):
        """
        Tries to reload the configuration for the app
        """
        reload_actions = self._app_config.get_reload_actions()
        for action in reload_actions:
            action.run(self._k8sapi)
