from octoploy.api.Oc import K8sApi
from octoploy.config.Config import RootConfig, AppConfig, RunMode
from octoploy.k8s.BaseObj import BaseObj
from octoploy.state.StateTracking import StateTracking
from octoploy.utils.Log import Log


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

    def deploy_object(self, k8s_object: BaseObj):
        """
        Deploy the given object (if a deployment required, otherwise does nothing)
        :param k8s_object: Object which should be deployed
        """
        hash_val = k8s_object.get_hash()
        item_path = k8s_object.get_fqn()
        namespace = k8s_object.namespace

        current_object = self._api.get(item_path, namespace=namespace)
        if current_object is None:
            self._log_create(item_path)

        current_hash = None
        if current_object is not None:
            obj_state = self._state.get_state(self._app_config.get_name(), k8s_object)
            if obj_state is not None and obj_state.hash != '':
                current_hash = obj_state.hash
            else:  # Fallback to old hash location
                current_hash = current_object.get_annotation(self.HASH_ANNOTATION)

        if current_object is not None and current_hash is None:
            # Item has not been deployed with octoploy, but it does already exist
            self.log.warning(f'{item_path} has no state annotation, assuming no change required')
            self._state.visit(self._app_config.get_name(), k8s_object, hash_val)
            return

        if current_hash == hash_val:
            self._state.visit(self._app_config.get_name(), k8s_object, hash_val)
            self.log.debug(f"{item_path} hasn't changed")
            return

        if current_object is not None:
            self._log_update(item_path)

        if self._mode.plan:
            self._state.visit(self._app_config.get_name(), k8s_object, hash_val)
            return

        self._api.apply(k8s_object.as_string(), namespace=namespace)
        self._state.visit(self._app_config.get_name(), k8s_object, hash_val)

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
            self._log_delete(item_path)
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

    def _log_create(self, item_path: str):
        self._log_verb(item_path, 'created', 'creating')

    def _log_delete(self, item_path: str):
        self._log_verb(item_path, 'deleted', 'deleting')

    def _log_update(self, item_path: str):
        self._log_verb(item_path, 'updated', 'updating')

    def _log_verb(self, item_path: str, past_verb: str, progressive_verb: str):
        if self._mode.plan or self._mode.dry_run:
            self.log.info(f'{item_path} will be {past_verb}')
            return
        self.log.info(f'{progressive_verb} {item_path}')
