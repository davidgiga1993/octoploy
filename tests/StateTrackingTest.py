import json
import os
from typing import List
from unittest import TestCase

import yaml

import octoploy.octoploy
from octoploy.config.Config import RunMode, RootConfig
from octoploy.state.StateTracking import StateTracking, ObjectState
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

    def test_move(self):
        state = StateTracking(None)
        data = state._state

        obj = ObjectState()
        obj.update_from_key('a/b/c/d')
        self.assertEqual('a', obj.context)
        self.assertEqual('b', obj.namespace)
        self.assertEqual('c', obj.kind)
        self.assertEqual('d', obj.name)
        data['a'] = obj

        obj = ObjectState()
        obj.update_from_key('a/b/c')
        self.assertEqual('a', obj.context)
        self.assertEqual('b', obj.namespace)
        self.assertEqual('c', obj.kind)
        obj.name = 'name'
        data['b'] = obj

        obj = ObjectState()
        obj.update_from_key('a/b')
        self.assertEqual('a', obj.context)
        self.assertEqual('b', obj.namespace)
        obj.kind = 'Deployment'
        obj.name = 'name'
        data['c'] = obj

        obj = ObjectState()
        obj.update_from_key('a')
        self.assertEqual('a', obj.context)
        obj.namespace = 'unittest'
        obj.kind = 'Deployment'
        obj.name = 'name'
        data['d'] = obj
        init_state = dict(data)

        state.move('a/b/c/d', '1/2/3/4')
        self.assertEqual('1', data['a'].context)
        self.assertEqual('2', data['a'].namespace)
        self.assertEqual('3', data['a'].kind)
        self.assertEqual('4', data['a'].name)
        state.move('1/2/3/4', 'a/b/c/d')

        state.move('a/b/c', '1/2/3')
        self.assertEqual('1', data['a'].context)
        self.assertEqual('2', data['a'].namespace)
        self.assertEqual('3', data['a'].kind)
        self.assertEqual('d', data['a'].name)

        self.assertEqual('1', data['b'].context)
        self.assertEqual('2', data['b'].namespace)
        self.assertEqual('3', data['b'].kind)
        self.assertEqual('name', data['b'].name)
        state.move('1/2/3', 'a/b/c')

    def test_create_new(self):
        self._dummy_api.respond(['get', 'Deployment/ABC', '-o', 'json'], '', error=Exception('NotFound'))
        self._dummy_api.respond(['get', 'ConfigMap/octoploy-state', '-o', 'json'], '{}')

        octoploy.octoploy._run_app_deploy('app_deploy_test', 'app', self._mode)

        self.assertEqual(4, len(self._dummy_api.commands))
        self.assertEqual(['get', 'ConfigMap/octoploy-state', '-o', 'json'], self._dummy_api.commands[0].args)
        state_update = self._dummy_api.commands[-1]
        self.assertEqual(['apply', '-f', '-'], state_update.args)
        self.assertStateEqual([{"context": "ABC",
                                "hash": "e2e4634c5cd31a1b58da917e8b181b28",
                                "kind": "Deployment",
                                "name": "ABC",
                                "namespace": "oc-project",
                                }], state_update.stdin)

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
        self.assertStateEqual([
            {"context": "ABC",
             "hash": "e2e4634c5cd31a1b58da917e8b181b28",
             "kind": "Deployment",
             "name": "ABC",
             "namespace": "oc-project"},
            {"context": "entity-compare-api",
             "hash": "644921ab79abf165d8fb8304913ff1c7",
             "kind": "Deployment",
             "name": "8080",
             "namespace": "oc-project"},
            {"context": "favorite-api",
             "hash": "3005876d55a8c9af38a58a4227a377fc",
             "kind": "Deployment",
             "name": "8081",
             "namespace": "oc-project"},
            {"context": "cm-types",
             "hash": "1f4d778af0ea594402e656fd6139c584",
             "kind": "ConfigMap",
             "name": "config",
             "namespace": "oc-project"},
            {"context": "ABC2",
             "hash": "d6e8e8f4b59b77117ec4ad267be8dcae",
             "kind": "Secret",
             "name": "secret",
             "namespace": "oc-project"},
            {"context": "ABC2",
             "hash": "178859f1aa21598384610f352d314ae6",
             "kind": "Secret",
             "name": "plain-secret",
             "namespace": "oc-project"},
            {"context": "var-append",
             "hash": "24d921e38f585e26cdc247d8fddc260e",
             "kind": "ConfigMap",
             "name": "config",
             "namespace": "oc-project"},
        ], state_update.stdin)

        # Now deploy a single app
        current_state = yaml.safe_load(state_update.stdin)
        self._dummy_api.respond(['get', 'ConfigMap/octoploy-state', '-o', 'json'], json.dumps(current_state))
        self._dummy_api.respond(['get', 'Deployment/ABC', '-o', 'json'], '{}')
        self._dummy_api.commands = []
        octoploy.octoploy._run_app_deploy('app_deploy_test', 'app', self._mode)

        self.assertEqual(3, len(self._dummy_api.commands))
        state_update = self._dummy_api.commands[-1]
        new_state = yaml.safe_load(state_update.stdin)
        self.assertEqual(current_state, new_state)

    def test_deploy_all_twice(self):
        """
        Deploys an entire folder twice and validates that the objects don't get removed again from k8s
        """
        self._dummy_api.not_found_by_default()

        os.environ['OCTOPLOY_KEY'] = TestUtils.OCTOPLOY_KEY
        octoploy.octoploy._run_apps_deploy('app_deploy_test', self._mode)

        self.assertEqual(14, len(self._dummy_api.commands))
        self.assertEqual(['get', 'ConfigMap/octoploy-state', '-o', 'json'], self._dummy_api.commands[0].args)

        state_update = self._dummy_api.commands[-1]
        self.assertEqual(['apply', '-f', '-'], state_update.args)
        self.assertStateEqual([{"context": "ABC",
                                "hash": "e2e4634c5cd31a1b58da917e8b181b28",
                                "kind": "Deployment",
                                "name": "ABC",
                                "namespace": "oc-project"},
                               {"context": "entity-compare-api",
                                "hash": "644921ab79abf165d8fb8304913ff1c7",
                                "kind": "Deployment",
                                "name": "8080",
                                "namespace": "oc-project"},
                               {"context": "favorite-api",
                                "hash": "3005876d55a8c9af38a58a4227a377fc",
                                "kind": "Deployment",
                                "name": "8081",
                                "namespace": "oc-project"},
                               {"context": "cm-types",
                                "hash": "1f4d778af0ea594402e656fd6139c584",
                                "kind": "ConfigMap",
                                "name": "config",
                                "namespace": "oc-project"},
                               {"context": "ABC2",
                                "hash": "d6e8e8f4b59b77117ec4ad267be8dcae",
                                "kind": "Secret",
                                "name": "secret",
                                "namespace": "oc-project"},
                               {"context": "var-append",
                                "hash": "24d921e38f585e26cdc247d8fddc260e",
                                "kind": "ConfigMap",
                                "name": "config",
                                "namespace": "oc-project"},
                               {"context": "ABC2",
                                "hash": "178859f1aa21598384610f352d314ae6",
                                "kind": "Secret",
                                "name": "plain-secret",
                                "namespace": "oc-project"},
                               ], state_update.stdin)
        # Now deploy a single app
        current_state = yaml.safe_load(state_update.stdin)
        self._dummy_api.respond(['get', 'ConfigMap/octoploy-state', '-o', 'json'], json.dumps(current_state))
        self._dummy_api.respond(['get', 'Deployment/ABC', '-o', 'json'], '{}')
        self._dummy_api.respond(['get', 'Deployment/8080', '-o', 'json'], '{}')
        self._dummy_api.respond(['get', 'Deployment/8081', '-o', 'json'], '{}')
        self._dummy_api.respond(['get', 'ConfigMap/config', '-o', 'json'], '{}')
        self._dummy_api.respond(['get', 'Secret/secret', '-o', 'json'], '{}')
        self._dummy_api.commands = []
        octoploy.octoploy._run_apps_deploy('app_deploy_test', self._mode)

        self.assertEqual(8, len(self._dummy_api.commands))
        for x in range(7):
            self.assertEqual('get', self._dummy_api.commands[x].args[0])

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
        self.assertStateEqual([], state_update.stdin)

    def assertStateEqual(self, expected: List[any], data: str):
        k8s_object = yaml.safe_load(data)
        state = yaml.safe_load(k8s_object['data']['state'])
        self.assertEqual(len(expected), len(state))
        for entry in expected:
            found_match = False
            for existing in state:
                if entry == existing:
                    found_match = True
                    break
            self.assertTrue(found_match, f'{entry} not found in {state}')
