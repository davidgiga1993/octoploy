from typing import List

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

        self._to_be_deployed: List[BaseObj] = []

    def add_object(self, k8s_object: BaseObj):
        """
        Adds the given object to the deployment list
        :param k8s_object: Object which should be deployed
        """
        self._to_be_deployed.append(k8s_object)
        self._state.visit_only(self._app_config.get_name(), k8s_object)

    def execute(self):
        """
        Executes the deployment
        """
        self._delete_abandoned_objects()
        self._deploy_objects()

    def _deploy_objects(self):
        """
        Deploys the pending objects
        """
        for k8s_object in self._to_be_deployed:
            self._deploy_object(k8s_object)

    def _deploy_object(self, k8s_object: BaseObj):
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

        state_hash = None
        old_state_hash = None
        if current_object is not None:
            old_state_hash = current_object.get_annotation(self.HASH_ANNOTATION)
            obj_state = self._state.get_state(self._app_config.get_name(), k8s_object)
            if obj_state is not None and obj_state.hash != '':
                state_hash = obj_state.hash
            else:  # Fallback to old hash location
                state_hash = old_state_hash

        if current_object is not None and state_hash is None:
            # Item has not been deployed with octoploy, but it does already exist
            self.log.warning(f'{item_path} has no state, assuming no change required')
            self._state.visit(self._app_config.get_name(), k8s_object, hash_val)
            return

        if state_hash == hash_val:
            self.log.debug(f"{item_path} hasn't changed")
            return

        if current_object is not None:
            self._log_update(item_path)

        if self._mode.plan:
            return

        if old_state_hash is not None:
            # Migrate to new state format by removing the old one
            self._api.annotate(k8s_object.get_fqn(), self.HASH_ANNOTATION, None, namespace=k8s_object.namespace)

        self._api.apply(k8s_object.as_string(), namespace=namespace)

        # Update hash
        self._state.visit(self._app_config.get_name(), k8s_object, hash_val)

        if k8s_object.is_kind('ConfigMap'):
            self._reload_config()

    def _delete_abandoned_objects(self):
        """
        Deletes all objects which are not anymore included in the
        current app config
        """
        abandoned = self._state.get_not_visited(self._app_config.get_name())
        for item in abandoned:
            namespace = item.namespace

            self._log_delete(item.fqn)
            if self._mode.plan:
                continue

            self._api.delete(item.fqn, namespace=namespace)
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
