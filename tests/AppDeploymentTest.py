import os
from unittest import TestCase

import yaml

from octoploy.config.Config import RootConfig, RunMode
from octoploy.deploy.AppDeploy import AppDeployment
from octoploy.utils.Errors import MissingParam
from octoploy.utils.Yml import Yml
from tests import TestUtils


class AppDeploymentTest(TestCase):

    def setUp(self) -> None:
        self._base_path = os.path.dirname(__file__)
        self._tmp_file = 'out.yml'
        self._mode = RunMode()
        self._mode.dry_run = True
        self._mode.out_file = self._tmp_file

    def tearDown(self) -> None:
        if os.path.isfile(self._tmp_file):
            os.remove(self._tmp_file)

    def test_inherit_vars(self):
        """
        Makes sure variables from the app are passed to the library
        and overrides conflicts with values from the app
        """
        self._deploy('app')
        with open(self._tmp_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        self.assertEqual('ABC', data['metadata']['name'])
        self.assertEqual('ABC-1', data['metadata']['REMAPPED'])
        self.assertEqual('ABC', data['metadata']['REMAPPED2'])
        self.assertEqual('DEF', data['metadata']['name2'])
        self.assertEqual('3', data['metadata']['base'])
        # Global variable should be passed down and should not be
        # overwritten by apps
        self.assertEqual('global', data['metadata']['GLOBAL_TEST'])

    def test_var_override(self):
        self._mode.var_override['globalVar'] = 'ext-override'
        self._deploy('app')
        with open(self._tmp_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        self.assertEqual('ext-override', data['metadata']['GLOBAL_TEST'])

    def test_cm_types(self):
        self._deploy('cm-types')

        with open(self._tmp_file) as f:
            content = f.read()
        # Make sure the "y" is quoted
        self.assertIn('"y"', content)

    def test_library(self):
        self._deploy('some-app', project='lib-usage')

        with open(self._tmp_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        self.assertEqual('paramValue', data['metadata']['name'])

    def test_var_loader(self):
        self._deploy('var-loader-app', project='lib-usage')

        with open(self._tmp_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        expected = '''-----BEGIN PRIVATE KEY-----
KEY STUFF
-----END PRIVATE KEY-----
'''
        self.assertEqual(expected, data['KEY'])

    def test_for_each(self):
        self._deploy('app-for-each')

        docs = Yml.load_docs(self._tmp_file)

        # We should have two instances
        self.assertEqual(2, len(docs))
        self.assertEqual('hello', docs[0]['metadata']['REMAPPED'])
        self.assertEqual('hello', docs[1]['metadata']['REMAPPED'])

    def test_params(self):
        prj_config = RootConfig.load(os.path.join(self._base_path, 'app_deploy_test_params'))
        app_config = prj_config.load_app_config('app-params')
        runner = AppDeployment(prj_config, app_config, self._mode)
        try:
            runner.deploy()
            self.fail('No exception raised for missing param')
        except MissingParam:
            pass

        external_params = {
            'SomeParam': 'input'
        }
        app_config._external_vars = external_params
        runner.deploy()

        with open(self._tmp_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        self.assertEqual('input', data['someObj']['param'])

    def test_secret_without_encryption(self):
        """
        Makes s ure secrets without encrypted values are not deployed
        """
        os.environ['OCTOPLOY_KEY'] = TestUtils.OCTOPLOY_KEY
        self._deploy('secrets')
        with open(self._tmp_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        self.assertTrue('plainText' not in data['stringData'])

    def test_decryption(self):
        os.environ['OCTOPLOY_KEY'] = TestUtils.OCTOPLOY_KEY
        self._deploy('secrets')
        with open(self._tmp_file) as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        self.assertEqual('hello world', data['stringData']['ref'])
        self.assertEqual('hello world', data['stringData']['field'])

    def _deploy(self, app: str, project: str = 'app_deploy_test'):
        prj_config = RootConfig.load(os.path.join(self._base_path, project))
        prj_config.initialize_state(self._mode)
        app_config = prj_config.load_app_config(app)
        runner = AppDeployment(prj_config, app_config, self._mode)
        runner.deploy()
