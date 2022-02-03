from __future__ import annotations

from typing import TYPE_CHECKING

from octoploy.utils.Log import Log

if TYPE_CHECKING:
    from octoploy.config.Config import AppConfig

from octoploy.oc.Oc import K8Api


class DeploymentActionConfig(Log):
    """
    Configuration for a single user configurable deployment step
    """

    def __init__(self, app_config: AppConfig, data):
        self._data = data
        self._app_config = app_config

    def run(self, oc: K8Api):
        if self._data == 'deploy':
            oc.rollout(self._app_config.get_dc_name())
            return

        exec_config = self._data.get('exec', None)
        if exec_config is not None:
            cmd = exec_config['command']
            args = exec_config['args']

            dc_name = self._app_config.get_dc_name()
            log.info('Reloading via exec in pods of ' + dc_name)
            pods = oc.get_pods(dc_name=dc_name)
            for pod in pods:
                oc.exec(pod.name, cmd, args)
            return
