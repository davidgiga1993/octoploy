from unittest import TestCase

from octoploy.utils.DictUtils import DictUtils


class DictUtilsTest(TestCase):
    def test_get(self):
        out = DictUtils.get({
            'a': {
                'b': {
                    'c': 1
                }
            }
        }, 'a.b.c')
        self.assertEqual(1, out)

    def test_get_missing(self):
        out = DictUtils.get({
            'a': {
                'b': {
                    'c': 1
                }
            }
        }, 'a.f')
        self.assertIsNone(out)

    def test_get_none(self):
        out = DictUtils.get(None, 'a.f')
        self.assertIsNone(out)

    def test_set(self):
        obj = {}
        DictUtils.set(obj, 'a.b.c', 1)
        self.assertEqual(1, DictUtils.get(obj, 'a.b.c'))

        obj = {}
        DictUtils.set(obj, 'a', 2)
        self.assertEqual(2, DictUtils.get(obj, 'a'))
