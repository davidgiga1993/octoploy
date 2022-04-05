from unittest import TestCase

from octoploy.utils.YmlWriter import YmlWriter


class YmlWriterTest(TestCase):
    def test_long_str(self):
        data = {
            'a': 'this is a very long string which should not be split up into strange multiple lines with backslash'
        }
        out_str = YmlWriter.dump(data)
        self.assertEqual('"a": "this is a very long string which should not be split up into strange multiple lines with backslash"\n', out_str)