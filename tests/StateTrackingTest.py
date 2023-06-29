import json
import os
from typing import List
from unittest import TestCase

import yaml

import octoploy.octoploy
from octoploy.config.Config import RunMode, RootConfig
from octoploy.state.StateMover import StateMover
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

    def _create_state_data(self):
        data = {}
        obj = ObjectState()
        obj.update_from_key('a/b/c.d/12')
        data[obj.get_key()] = obj
        self.assertEqual('a', obj.context)
        self.assertEqual('b', obj.namespace)
        self.assertEqual('c.d/12', obj.fqn)

        obj = ObjectState()
        obj.update_from_key('a/b/c')
        data[obj.get_key()] = obj
        self.assertEqual('a', obj.context)
        self.assertEqual('b', obj.namespace)
        self.assertEqual('c', obj.fqn)

        obj = ObjectState()
        obj.update_from_key('a/b/Deployment/name')
        data[obj.get_key()] = obj
        self.assertEqual('a', obj.context)
        self.assertEqual('b', obj.namespace)
        return data

    def test_move(self):
        root = self._load_project('app_deploy_test')
        mover = StateMover(root)
        state = StateTracking(root.create_api())
        data = state._state
        root._state = state

        def void(ignore):
            pass

        root.initialize_state = void
        data.update(self._create_state_data())

        self.assertEqual('a', data['a/b/c.d/12'].context)
        self.assertEqual('b', data['a/b/c.d/12'].namespace)
        self.assertEqual('c.d/12', data['a/b/c.d/12'].fqn)

        self.assertEqual('a', data['a/b/c'].context)
        self.assertEqual('b', data['a/b/c'].namespace)
        self.assertEqual('c', data['a/b/c'].fqn)

        self.assertEqual('a', data['a/b/Deployment/name'].context)
        self.assertEqual('b', data['a/b/Deployment/name'].namespace)

        mover.move('a/b/c.d/12', '1/2/3/4', None)
        self.assertEqual('1', data['1/2/3/4'].context)
        self.assertEqual('2', data['1/2/3/4'].namespace)
        self.assertEqual('3/4', data['1/2/3/4'].fqn)
        data = state._state = self._create_state_data()

        mover.move('a/b', '1/2', None)
        self.assertEqual('1', data['1/2/Deployment/name'].context)
        self.assertEqual('2', data['1/2/Deployment/name'].namespace)
        self.assertEqual('Deployment/name', data['1/2/Deployment/name'].fqn)

        self.assertEqual('1', data['1/2/c'].context)
        self.assertEqual('2', data['1/2/c'].namespace)
        self.assertEqual('c', data['1/2/c'].fqn)
        data = state._state = self._create_state_data()

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
                                "fqn": "Deployment/ABC",
                                "namespace": "oc-project",
                                }], state_update.stdin)

    def test_duplicate_kinds(self):
        self._dummy_api.respond(['get', 'Deployment/ABC', '-o', 'json'], '', error=Exception('NotFound'))
        self._dummy_api.respond(['get', 'ConfigMap/octoploy-state', '-o', 'json'], '{}')

        octoploy.octoploy._run_app_deploy('app_deploy_test_duplicate_kinds', 'app', self._mode)

        self.assertEqual(4, len(self._dummy_api.commands))
        self.assertEqual(['get', 'ConfigMap/octoploy-state', '-o', 'json'], self._dummy_api.commands[0].args)
        state_update = self._dummy_api.commands[-1]
        self.assertEqual(['apply', '-f', '-'], state_update.args)
        self.assertStateEqual([{"context": "app",
                                "hash": "aa859898df4ff9412857e720beeabfba",
                                "fqn": "ProviderConfig.kubernetes.crossplane.io/default",
                                "namespace": "oc-project",
                                },
                               {"context": "app",
                                "hash": "8652aee0d35b000096f2a263c6e3eb77",
                                "fqn": "ProviderConfig.grafana.crossplane.io/default",
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
             "fqn": "Deployment/ABC",
             "namespace": "oc-project"},
            {"context": "entity-compare-api",
             "hash": "644921ab79abf165d8fb8304913ff1c7",
             "fqn": "Deployment/8080",
             "namespace": "oc-project"},
            {"context": "favorite-api",
             "hash": "3005876d55a8c9af38a58a4227a377fc",
             "fqn": "Deployment/8081",
             "namespace": "oc-project"},
            {"context": "cm-types",
             "hash": "1f4d778af0ea594402e656fd6139c584",
             "fqn": "ConfigMap/config",
             "namespace": "oc-project"},
            {"context": "ABC2",
             "hash": "d6e8e8f4b59b77117ec4ad267be8dcae",
             "fqn": "Secret/secret",
             "namespace": "oc-project"},
            {"context": "var-append",
             "hash": "24d921e38f585e26cdc247d8fddc260e",
             "fqn": "ConfigMap/config",
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
                                "fqn": "Deployment/ABC",
                                "namespace": "oc-project"},
                               {"context": "entity-compare-api",
                                "hash": "644921ab79abf165d8fb8304913ff1c7",
                                "fqn": "Deployment/8080",
                                "namespace": "oc-project"},
                               {"context": "favorite-api",
                                "hash": "3005876d55a8c9af38a58a4227a377fc",
                                "fqn": "Deployment/8081",
                                "namespace": "oc-project"},
                               {"context": "cm-types",
                                "hash": "1f4d778af0ea594402e656fd6139c584",
                                "fqn": "ConfigMap/config",
                                "namespace": "oc-project"},
                               {"context": "ABC2",
                                "hash": "d6e8e8f4b59b77117ec4ad267be8dcae",
                                "fqn": "Secret/secret",
                                "namespace": "oc-project"},
                               {"context": "var-append",
                                "hash": "24d921e38f585e26cdc247d8fddc260e",
                                "fqn": "ConfigMap/config",
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
    "state": "[{\\"context\\": \\"ABC\\", \\"fqn\\": \\"DeploymentConfig/ABC\\", \\"namespace\\": \\"oc-project\\"}]"
  },
  "fqn": "ConfigMap",
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
