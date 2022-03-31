from unittest import TestCase

from octoploy.config.BaseConfig import BaseConfig
from octoploy.processing.ValueLoader import ValueLoaderFactory


class ValueLoaderTest(TestCase):

    def test_env(self):
        factory = ValueLoaderFactory()
        loader = factory.create(BaseConfig(None), 'env')
        items = loader.load({})
        self.assertTrue(len(items) > 0)

    def test_file(self):
        factory = ValueLoaderFactory()
        loader = factory.create(BaseConfig(None), 'file')
        items = loader.load({'file': __file__})
        self.assertIsNotNone(items.get(''))
        self.assertIn('class', items.get(''))

        items = loader.load({'file': __file__, 'conversion': 'base64'})
        self.assertNotIn('class', items.get(''))
