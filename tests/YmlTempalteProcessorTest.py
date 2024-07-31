from unittest import TestCase, mock

from octoploy.config.Config import AppConfig
from octoploy.k8s.BaseObj import BaseObj
from octoploy.processing.YmlTemplateProcessor import YmlTemplateProcessor


class YmlTemplateProcessorTest(TestCase):

    def test_keep(self):
        with mock.patch('builtins.open', mock.mock_open(read_data='''
name: hello
vars:
    MY_VAR: testVal
    IMAGE_NAME: image
''')):
            app_config = AppConfig('', '')

        proc = YmlTemplateProcessor(app_config)
        data = {
            'kind': 'Test',
            'apiVersion': 'v1',
            'root': {
                '1': '$',
                '2': '$$',
                '3': 'item$',
                '4': 'my$var',
                '5': '$item',
                '6': '${item',
                '7': '${',
                '8': '${nonExistent}',
                '9': '${nonExistent}Other${MY_VAR}',
            }}
        proc.process(BaseObj(data))
        self.assertEqual('$', data['root']['1'])
        self.assertEqual('$', data['root']['2'])
        self.assertEqual('item$', data['root']['3'])
        self.assertEqual('my$var', data['root']['4'])
        self.assertEqual('$item', data['root']['5'])
        self.assertEqual('${item', data['root']['6'])
        self.assertEqual('${', data['root']['7'])
        self.assertEqual('${nonExistent}', data['root']['8'])
        self.assertEqual('${nonExistent}OthertestVal', data['root']['9'])

    def test_replace(self):
        with mock.patch('builtins.open', mock.mock_open(read_data='''
name: hello
vars:
    MY_VAR: testVal
    IMAGE_NAME: image
    NUMBER: 10
    MY_OBJECT:
        someItem: 1
        someOtherItem: 2
''')):
            app_config = AppConfig('', '')

        proc = YmlTemplateProcessor(app_config)
        data = {
            'kind': 'Test',
            'apiVersion': 'v1',
            'root': {
                'item': '${APP_NAME}',
                'number': '${NUMBER}',
                'object': '${MY_OBJECT}',
                'list': [{
                    'other': '${APP_NAME}/${IMAGE_NAME}'
                }],
                'sub': {
                    'item2': '${MY_VAR}'
                }
            }}
        proc.process(BaseObj(data))
        self.assertEqual('hello', data['root']['item'])
        self.assertEqual(10, data['root']['number'])
        self.assertEqual('hello/image', data['root']['list'][0]['other'])
        self.assertEqual('testVal', data['root']['sub']['item2'])
        self.assertEqual({
            'someItem': 1,
            'someOtherItem': 2
        }, data['root']['object'])

    def test_params(self):
        with mock.patch('builtins.open', mock.mock_open(read_data='''
name: hello
vars:
    MY_VAR: testVal
''')):
            app_config = AppConfig('', '')

        proc = YmlTemplateProcessor(app_config)
        data = {
            'kind': 'Test',
            'apiVersion': 'v1',
            'root': {
                'item': '${APP_NAME}',
                'list': [{
                    'other': '${APP_NAME}'
                }],
                'sub': {
                    'item2': '${MY_VAR}'
                }
            }}
        proc.process(BaseObj(data))
        self.assertEqual('hello', data['root']['item'])
        self.assertEqual('hello', data['root']['list'][0]['other'])
        self.assertEqual('testVal', data['root']['sub']['item2'])

    def test_escaping(self):
        with mock.patch('builtins.open', mock.mock_open(read_data='''
name: hello
vars:
    MY_VAR: testVal
''')):
            app_config = AppConfig('', '')

        proc = YmlTemplateProcessor(app_config)
        data = {
            'kind': '$${APP_NAME}${APP_NAME}Test${APP_NAME}',
            'apiVersion': ''
        }
        proc.process(BaseObj(data))
        self.assertEqual('${APP_NAME}helloTesthello', data['kind'])

    def test_merge_var_inline(self):
        with mock.patch('builtins.open', mock.mock_open(read_data='''
name: hello
vars:
    MERGE_OBJ: 
        someKey: value
''')):
            app_config = AppConfig('', '')

        proc = YmlTemplateProcessor(app_config)
        data = {
            'kind': 'Test',
            'apiVersion': 'v1',
            'root': {
                'item': '${APP_NAME}',
                '_merge': '${MERGE_OBJ}',
            }}
        proc.process(BaseObj(data))
        self.assertEqual('hello', data['root']['item'])
        self.assertEqual('value', data['root']['someKey'])

    def test_merge_object_inline(self):
        with mock.patch('builtins.open', mock.mock_open(read_data='''
name: hello
''')):
            app_config = AppConfig('', '')

        proc = YmlTemplateProcessor(app_config)
        data = {
            'kind': 'Test',
            'apiVersion': 'v1',
            'root': {
                'item': '${APP_NAME}',
                '_merge': {
                    'someKey': 'value',
                },
            }}
        proc.process(BaseObj(data))
        self.assertEqual('hello', data['root']['item'])
        self.assertEqual('value', data['root']['someKey'])
