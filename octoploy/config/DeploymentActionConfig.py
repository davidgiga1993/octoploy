from __future__ import annotations

from typing import TYPE_CHECKING

from octoploy.utils.Log import Log

if TYPE_CHECKING:
    from octoploy.config.Config import AppConfig

from octoploy.api.Oc import K8sApi


class DeploymentActionConfig(Log):
    """
    Configuration for a single user configurable deployment step
    """

    def __init__(self, app_config: AppConfig, data):
        super().__init__()
        self._data = data
        self._app_config = app_config

    def run(self, k8s: K8sApi):
        namespace = self._app_config.get_root().get_namespace_name()
        if self._data == 'deploy':
            k8s.rollout(self._app_config.get_name(), namespace=namespace)
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
