import hashlib

from octoploy.api.Oc import K8sApi
from octoploy.config.Config import RootConfig, AppConfig, RunMode
from octoploy.k8s.BaseObj import BaseObj
from octoploy.state.StateTracking import StateTracking
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
    _root_config: RootConfig
    _app_config: AppConfig
    _api: K8sApi
    _state: StateTracking

    def __init__(self, root_config: RootConfig, k8sapi: K8sApi, app_config: AppConfig, mode: RunMode = RunMode()):
        super().__init__()
        self._root_config = root_config
        self._app_config = app_config
        self._api = k8sapi
        self._mode = mode
        self._state = root_config.get_state()

    def select_context(self):
        """
        Selects the cluster context
        """
        context = self._root_config.get_kubectl_context()
        if context is not None:
            self._api.switch_context(context)

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
        namespace = k8s_object.namespace
        if namespace is None:
            namespace = self._root_config.get_namespace_name()
        k8s_object.namespace = namespace  # Make sure the object points to the correct namespace

        item_path = f'{k8s_object.kind}/{k8s_object.name}'
        current_object = self._api.get(item_path, namespace=namespace)
        if current_object is None:
            self.log.info(f'{item_path} will be created')

        current_hash = None
        if current_object is not None:
            current_hash = current_object.get_annotation(self.HASH_ANNOTATION)

        if current_object is not None and current_hash is None:
            # Item has not been deployed with octoploy, but it does already exist
            self.log.warning(f'{item_path} has no state annotation, assuming no change required')
            self._api.annotate(item_path, self.HASH_ANNOTATION, hash_val, namespace=namespace)
            self._state.visit(self._app_config.get_name(), k8s_object)
            return

        if current_hash == hash_val:
            self.log.debug(f"{item_path} hasn't changed")
            return

        if current_object is not None:
            self.log.info(f'{item_path} will be updated')

        if self._mode.plan:
            self._state.visit(self._app_config.get_name(), k8s_object)
            return

        self._api.apply(str_repr, namespace=namespace)
        self._api.annotate(item_path, 'yml-hash', hash_val, namespace=namespace)
        self._state.visit(self._app_config.get_name(), k8s_object)

        if k8s_object.is_kind('ConfigMap'):
            self._reload_config()

    def delete_abandoned_objects(self):
        """
        Deletes all objects which are not anymore included in the
        current app config
        """
        abandoned = self._state.get_not_visited(self._app_config.get_name())
        for item in abandoned:
            namespace = item.namespace
            if namespace is None:
                namespace = self._root_config.get_namespace_name()
            item_path = item.kind + '/' + item.name
            self.log.info(f'{item_path} will be deleted')
            if self._mode.plan:
                continue

            self._api.delete(item_path, namespace=namespace)
            self._state.remove(item)

    def _reload_config(self):
        """
        Tries to reload the configuration for the app
        """
        reload_actions = self._app_config.get_reload_actions()
        for action in reload_actions:
            action.run(self._api)
