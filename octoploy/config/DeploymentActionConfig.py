from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from octoploy.k8s.BaseObj import BaseObj
from octoploy.utils.Log import Log

if TYPE_CHECKING:
    from octoploy.config.Config import AppConfig

from octoploy.api.Kubectl import K8sApi


class DeploymentActionConfig(Log):
    """
    Configuration for a single user configurable deployment step
    """

    def __init__(self, app_config: AppConfig, data):
        super().__init__()
        self._data = data
        self._app_config = app_config

    def run(self, k8s: K8sApi, all_objects: List[BaseObj]):
        namespace = self._app_config.get_root().get_namespace_name()
        if self._data == 'deploy':
            deployment_name = self._app_config.get_name()
            deployment_obj = self.get_deployment_object(deployment_name, all_objects)
            if deployment_obj is None:
                self.log.warning(f'Deployment object {deployment_name} not found')
                return

            try:
                k8s.rollout(deployment_name, namespace=deployment_obj.namespace)
            except Exception as e:
                if '(NotFound)' in str(e):
                    self.log.warning(f'Could not restart {deployment_name} {deployment_obj.namespace}:\n{e}')
                    return
            return

        exec_config = self._data.get('exec', None)
        if exec_config is not None:
            cmd = exec_config['command']
            args = exec_config['args']

            dc_name = self._app_config.get_name()
            self.log.info('Reloading via exec in pods of ' + dc_name)
            pods = k8s.get_pods(dc_name=dc_name, namespace=namespace)
            for pod in pods:
                k8s.exec(pod.name, cmd, args, namespace=namespace)
            return

    @staticmethod
    def get_deployment_object(deployment_name: str, all_objects: List[BaseObj]) -> Optional[BaseObj]:
        for obj in all_objects:
            if (obj.is_kind('Deployment') or obj.is_kind('DeploymentConfig')) \
                    and obj.name == deployment_name:
                return obj
        return None
