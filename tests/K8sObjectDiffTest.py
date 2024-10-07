from unittest import TestCase
from unittest.mock import patch

from octoploy.k8s.BaseObj import BaseObj
from octoploy.k8s.K8sObjectDiff import K8sObjectDiff
from octoploy.utils.Log import ColorFormatter
from tests.TestUtils import DummyK8sApi


class K8sObjectDiffTest(TestCase):

    @patch('builtins.print')
    def test_secret_masking(self, mock_print):
        api = DummyK8sApi()
        a = BaseObj({
            'kind': 'Secret',
            'apiVersion': 'v1',
            'data': {
                'a': '1'
            }
        })
        b = BaseObj({
            'kind': 'Secret',
            'apiVersion': 'v1',
            'data': {
                'a': '2'
            },
            'stringData': {
                'b': 'newField'
            }
        })

        K8sObjectDiff(api).print(a, b)

        stdout_lines = ''
        for args in mock_print.call_args_list:
            stdout_lines += ColorFormatter.decolorize(str(args.args[0])) + '\n'

        self.assertNotIn('1', stdout_lines)
        self.assertNotIn('2', stdout_lines)
        self.assertIn('~ data.a = *** -> ***', stdout_lines)
        self.assertIn('+ stringData.b = ***', stdout_lines)
        self.assertNotIn('newField', stdout_lines)

    @patch('builtins.print')
    def test_list_diff(self, mock_print):
        api = DummyK8sApi()
        a = BaseObj({
            'kind': 'ConfingMap',
            'apiVersion': 'v1',
            'spec': {
                'add': ['a', 'b'],
                'change': ['a', 'b', 'c'],
                'remove': ['a', 'b', 'c'],
            }
        })
        b = BaseObj({
            'kind': 'ConfingMap',
            'apiVersion': 'v1',
            'spec': {
                'add': ['a', 'b', 'c'],
                'change': ['a', 'c', 'd'],
                'remove': ['a', 'c'],
            }
        })

        K8sObjectDiff(api).print(a, b)

        stdout_lines = ''
        for args in mock_print.call_args_list:
            stdout_lines += ColorFormatter.decolorize(str(args.args[0])) + '\n'

        self.assertIn('+ spec.add.[2] = c', stdout_lines)
        self.assertIn('~ spec.change.[1] = b -> c', stdout_lines)
        self.assertIn('~ spec.change.[2] = c -> d', stdout_lines)
        self.assertIn('~ spec.remove.[1] = b -> c', stdout_lines)
        self.assertIn('- spec.remove.[2] = c', stdout_lines)

    def test_diff(self):
        api = DummyK8sApi()
        a = BaseObj({
            'kind': 'a',
            'apiVersion': 'v1',
            'metadata': {
                'annotations': {
                    'kubectl.kubernetes.io/last-applied-configuration': 'ignore',
                },
                'uid': '',
                'resourceVersion': '123',
            },
            'spec': {
                'field': 'value',
                'removed': 'value',
                'listItemAdd': ['a'],
                'listRemoved': ['a', 'b'],
                'listItemRemoved': ['a', 'b'],
                'listItemChanged': ['a', 'b'],
                'removedDict': {'a': 'hello'}
            }
        })
        b = BaseObj({
            'kind': 'a',
            'apiVersion': 'v1',
            'metadata': {
                'annotations': {
                    'newAnnotation': 'hello',
                },
            },
            'spec': {
                'field': 'otherValue',
                'listItemAdd': ['a', 'b'],
                'listAdded': ['a', 'b'],
                'listItemRemoved': ['a'],
                'listItemChanged': ['a', 'other'],
                'addedDict': {'a': 'hello'}
            }
        })

        K8sObjectDiff(api).print(a, b)

    def test_multiline_str(self):
        api = DummyK8sApi()
        a = BaseObj({
            'kind': 'a',
            'apiVersion': 'v1',
            'spec': {
                'field': '''
                    This is a multiline string
                    It has multiple lines
                    Yay''',
            }
        })
        b = BaseObj({
            'kind': 'a',
            'apiVersion': 'v1',
            'spec': {
                'field': '''
                    This is a multiline string
                    It has multiple lines, but some have been changed
                    or have been added
                    Yay''',
            }
        })

        K8sObjectDiff(api).print(a, b)
