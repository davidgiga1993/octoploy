from unittest import TestCase

from tests.TestUtils import DummyK8sApi

from octoploy.k8s.BaseObj import BaseObj
from octoploy.k8s.K8sObjectDiff import K8sObjectDiff


class K8sObjectDiffTest(TestCase):

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
