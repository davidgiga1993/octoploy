import json
import os
from unittest import TestCase

import yaml

import octoploy.octoploy
from octoploy.config.Config import RunMode, RootConfig
from tests import TestUtils
from tests.TestUtils import DummyK8sApi


class StateTrackingTest(TestCase):

    def setUp(self) -> None:
        self._base_path = os.path.dirname(__file__)
        self._tmp_file = 'out.yml'
        self._mode = RunMode()
        self._dummy_api = DummyK8sApi()
        octoploy.octoploy.load_project = self._load_project

    def tearDown(self) -> None:
        self._dummy_api = None

    def _load_project(self, config_dir: str) -> RootConfig:
        def get_dummy_api():
            return self._dummy_api

        prj_config = RootConfig.load(os.path.join(self._base_path, config_dir))
        prj_config.get_state()._k8s_api = self._dummy_api
        prj_config.create_api = get_dummy_api
        return prj_config

    def test_create_new(self):
        self._dummy_api.respond(['get', 'DeploymentConfig/ABC', '-o', 'json'], '', error=Exception('NotFound'))
        self._dummy_api.respond(['get', 'ConfigMap/octoploy-state', '-o', 'json'], '{}')

        octoploy.octoploy._run_app_deploy('app_deploy_test', 'app', self._mode)

        self.assertEqual(4, len(self._dummy_api.commands))
        self.assertEqual(['get', 'ConfigMap/octoploy-state', '-o', 'json'], self._dummy_api.commands[0].args)
        state_update = self._dummy_api.commands[-1]
        self.assertEqual(['apply', '-f', '-'], state_update.args)
        self.assertEqual('''"apiVersion": "v1"
"data":
  "state": "- \\"apiVersion\\": \\"v1\\"\\n  \\"context\\": \\"ABC\\"\\n  \\"hash\\": \\"dbd4e8fa683fade0a76bcd94c92e2293\\"\\n  \\"kind\\": \\"DeploymentConfig\\"\\n  \\"name\\": \\"ABC\\"\\n  \\"namespace\\": \\"oc-project\\"\\n"
"kind": "ConfigMap"
"metadata":
  "name": "octoploy-state"
''', state_update.stdin)

    def test_deploy_all_then_app(self):
        """
        Deploys an entire folder, then a single app and makes
        sure the other objects don't get removed again from k8s
        """
        self._dummy_api.not_found_by_default()

        os.environ['OCTOPLOY_KEY'] = TestUtils.OCTOPLOY_KEY
        octoploy.octoploy._run_apps_deploy('app_deploy_test', self._mode)

        self.assertEqual(14, len(self._dummy_api.commands))
        self.assertEqual(['get', 'ConfigMap/octoploy-state', '-o', 'json'], self._dummy_api.commands[0].args)

        state_update = self._dummy_api.commands[-1]
        self.assertEqual(['apply', '-f', '-'], state_update.args)
        self.assertEqual('''"apiVersion": "v1"
"data":
  "state": "- \\"apiVersion\\": \\"v1\\"\\n  \\"context\\": \\"ABC\\"\\n  \\"hash\\": \\"dbd4e8fa683fade0a76bcd94c92e2293\\"\\n  \\"kind\\": \\"DeploymentConfig\\"\\n  \\"name\\": \\"ABC\\"\\n  \\"namespace\\": \\"oc-project\\"\\n- \\"apiVersion\\": \\"v1\\"\\n  \\"context\\": \\"entity-compare-api\\"\\n  \\"hash\\": \\"4b22586489a2acd974557528748319e5\\"\\n  \\"kind\\": \\"DeploymentConfig\\"\\n  \\"name\\": \\"8080\\"\\n  \\"namespace\\": \\"oc-project\\"\\n- \\"apiVersion\\": \\"v1\\"\\n  \\"context\\": \\"favorite-api\\"\\n  \\"hash\\": \\"9f183e7c1f686a996fe893b686e70e63\\"\\n  \\"kind\\": \\"DeploymentConfig\\"\\n  \\"name\\": \\"8081\\"\\n  \\"namespace\\": \\"oc-project\\"\\n- \\"apiVersion\\": \\"v1\\"\\n  \\"context\\": \\"cm-types\\"\\n  \\"hash\\": \\"a48eadd6d347e2591a3929df077aead7\\"\\n  \\"kind\\": \\"ConfigMap\\"\\n  \\"name\\": \\"config\\"\\n  \\"namespace\\": \\"oc-project\\"\\n- \\"apiVersion\\": \\"v1\\"\\n  \\"context\\": \\"ABC2\\"\\n  \\"hash\\": \\"ea23b547bb9a06ca79d3dc23c3d1d0dd\\"\\n  \\"kind\\": \\"Secret\\"\\n  \\"name\\": \\"secret\\"\\n  \\"namespace\\": \\"oc-project\\"\\n- \\"apiVersion\\": \\"v1\\"\\n  \\"context\\": \\"var-append\\"\\n  \\"hash\\": \\"e19d6902d55e14e99213b1d112acbde0\\"\\n  \\"kind\\": \\"ConfigMap\\"\\n  \\"name\\": \\"config\\"\\n  \\"namespace\\": \\"oc-project\\"\\n"
"kind": "ConfigMap"
"metadata":
  "name": "octoploy-state"
''', state_update.stdin)

        # Now deploy a single app
        current_state = yaml.safe_load(state_update.stdin)
        self._dummy_api.respond(['get', 'ConfigMap/octoploy-state', '-o', 'json'], json.dumps(current_state))
        self._dummy_api.respond(['get', 'DeploymentConfig/ABC', '-o', 'json'], '{}')
        self._dummy_api.commands = []
        octoploy.octoploy._run_app_deploy('app_deploy_test', 'app', self._mode)

        self.assertEqual(4, len(self._dummy_api.commands))
        state_update = self._dummy_api.commands[-1]
        new_state = yaml.safe_load(state_update.stdin)
        self.assertEqual(current_state, new_state)

    def test_removed_in_repo(self):
        self._dummy_api.respond(['get', 'DeploymentConfig/ABC', '-o', 'json'], '', error=Exception('NotFound'))
        self._dummy_api.respond(['get', 'ConfigMap/octoploy-state', '-o', 'json'], '''{
  "apiVersion": "v1",
  "data": {
    "state": "[{\\"apiVersion\\": \\"v1\\", \\"context\\": \\"ABC\\", \\"kind\\": \\"DeploymentConfig\\", \\"name\\": \\"ABC\\", \\"namespace\\": \\"oc-project\\"}]"
  },
  "kind": "ConfigMap",
  "metadata": {
    "name": "octoploy-state"
  }
}''')

        octoploy.octoploy._run_app_deploy('app_deploy_test_empty', 'app', self._mode)

        self.assertEqual(3, len(self._dummy_api.commands))
        self.assertEqual(['get', 'ConfigMap/octoploy-state', '-o', 'json'], self._dummy_api.commands[0].args)
        self.assertEqual(['delete', 'DeploymentConfig/ABC'], self._dummy_api.commands[1].args)

        state_update = self._dummy_api.commands[2]
        self.assertEqual(['apply', '-f', '-'], state_update.args)
        self.assertEqual('''"apiVersion": "v1"
"data":
  "state": "[]\\n"
"kind": "ConfigMap"
"metadata":
  "name": "octoploy-state"
''', state_update.stdin)
