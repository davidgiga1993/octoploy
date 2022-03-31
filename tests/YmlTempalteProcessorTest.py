from unittest import TestCase, mock

from octoploy.config.Config import AppConfig
from octoploy.processing.YmlTemplateProcessor import YmlTemplateProcessor


class YmlTemplateProcessorTest(TestCase):

    def test_replace(self):
        with mock.patch('builtins.open', mock.mock_open(read_data='''
dc:
    name: hello
vars:
    MY_VAR: testVal
    IMAGE_NAME: image
    MY_OBJECT:
        someItem: 1
        someOtherItem: 2
''')):
            app_config = AppConfig('', '')

        proc = YmlTemplateProcessor(app_config)
        data = {'root': {
            'item': '${DC_NAME}',
            'object': '${MY_OBJECT}',
            'list': [{
                'other': '${DC_NAME}/${IMAGE_NAME}'
            }],
            'sub': {
                'item2': '${MY_VAR}'
            }
        }}
        proc.process(data)
        self.assertEqual('hello', data['root']['item'])
        self.assertEqual('hello/image', data['root']['list'][0]['other'])
        self.assertEqual('testVal', data['root']['sub']['item2'])
        self.assertEqual({
            'someItem': 1,
            'someOtherItem': 2
        }, data['root']['object'])

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

    def test_merge_inline(self):
        with mock.patch('builtins.open', mock.mock_open(read_data='''
dc:
    name: hello
vars:
    MERGE_OBJ: 
        someKey: value
''')):
            app_config = AppConfig('', '')

        proc = YmlTemplateProcessor(app_config)
        data = {'root': {
            'item': '${DC_NAME}',
            '_merge': '${MERGE_OBJ}',
        }}
        proc.process(data)
        self.assertEqual('hello', data['root']['item'])
        self.assertEqual('value', data['root']['someKey'])
