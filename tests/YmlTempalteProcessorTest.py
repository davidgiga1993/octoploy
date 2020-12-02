from unittest import TestCase, mock

from config.Config import RootConfig, AppConfig
from processing.YmlTemplateProcessor import YmlTemplateProcessor


class YmlTemplateProcessorTest(TestCase):

    def test_replace(self):
        with mock.patch('builtins.open', mock.mock_open(read_data='''
dc:
    name: hello
vars:
    MY_VAR: testVal
''')):
            app_config = AppConfig('', '')

        proc = YmlTemplateProcessor(app_config)
        data = {'root': {
            'item': '${DC_NAME}',
            'list': [{
                'other': '${DC_NAME}'
            }],
            'sub': {
                'item2': '${MY_VAR}'
            }
        }}
        proc.process(data)
        self.assertEqual('hello', data['root']['item'])
        self.assertEqual('hello', data['root']['list'][0]['other'])
        self.assertEqual('testVal', data['root']['sub']['item2'])

    def test_params(self):
        with mock.patch('builtins.open', mock.mock_open(read_data='''
dc:
    name: hello
vars:
    MY_VAR: testVal
''')):
            app_config = AppConfig('', '')

        proc = YmlTemplateProcessor(app_config)
        data = {'root': {
            'item': '${DC_NAME}',
            'list': [{
                'other': '${DC_NAME}'
            }],
            'sub': {
                'item2': '${MY_VAR}'
            }
        }}
        proc.process(data)
        self.assertEqual('hello', data['root']['item'])
        self.assertEqual('hello', data['root']['list'][0]['other'])
        self.assertEqual('testVal', data['root']['sub']['item2'])
