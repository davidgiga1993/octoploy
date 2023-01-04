import json
import os
from unittest import TestCase
from unittest.mock import patch

from octoploy.deploy.AppDeploy import AppDeployment

from octoploy.config.Config import RunMode, RootConfig
from tests.TestUtils import TestHelper, DummyK8sApi


class StateTrackingTest(TestCase):

    def setUp(self) -> None:
        self._base_path = os.path.dirname(__file__)
        self._tmp_file = 'out.yml'
        self._mode = RunMode()

    def test_create(self):
        dummy_api = DummyK8sApi()
        dummy_api.respond(['get', 'DeploymentConfig/ABC', '-o', 'json'], '', error=Exception('NotFound'))
        dummy_api.respond(['get', 'ConfigMap/octoploy-state', '-o', 'json'], '{}')

        def get_dummy_api():
            return dummy_api

        prj_config = RootConfig.load(os.path.join(self._base_path, 'app_deploy_test'))
        prj_config.get_state()._k8s_api = dummy_api
        prj_config.create_api = get_dummy_api
        prj_config.initialize_state(self._mode)

        self.assertEqual(1, len(dummy_api.commands))
        self.assertEqual(['get', 'ConfigMap/octoploy-state', '-o', 'json'], dummy_api.commands[0].args)

        app_config = prj_config.load_app_config('app')
        runner = AppDeployment(prj_config, app_config, self._mode)
        runner.deploy()
        prj_config.persist_state(self._mode)

        self.assertEqual(5, len(dummy_api.commands))
        state_update = dummy_api.commands[4]
        self.assertEqual(['apply', '-f', '-'], state_update.args)
        self.assertEqual('''"apiVersion": "v1"
"data":
  "state":
  - "apiVersion": "v1"
    "context": "ABC"
    "kind": "DeploymentConfig"
    "name": "ABC"
    "namespace": "oc-project"
"kind": "ConfigMap"
"metadata":
  "name": "octoploy-state"
''', state_update.stdin)
