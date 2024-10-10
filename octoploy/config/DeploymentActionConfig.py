from __future__ import annotations

from typing import TYPE_CHECKING, List

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
            objects = self.get_rollout_objects(all_objects)
            if len(objects) == 0:
                self.log.warning(f'No objects to restart found')
                return

            for obj in objects:
                try:
                    k8s.rollout(obj.kind, obj.name, namespace=obj.namespace)
                except Exception as e:
                    if '(NotFound)' in str(e):
                        self.log.warning(f'Could not restart {obj.get_fqn()} in namespace {obj.namespace}: {e}')
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
    def get_rollout_objects(all_objects: List[BaseObj]) -> List[BaseObj]:
        out = []
        for obj in all_objects:
            if obj.is_kind('Deployment') \
                    or obj.is_kind('DaemonSet') \
                    or obj.is_kind('StatefulSet') \
                    or obj.is_kind('DeploymentConfig'):
                out.append(obj)
        return out
