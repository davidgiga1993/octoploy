from unittest import TestCase

from octoploy.utils.Errors import MissingVar

from octoploy.config.AppConfig import AppConfig


class AppConfigTest(TestCase):
    def test_missing_name(self):
        config = AppConfig('', None)
        config.data = {
            'forEach': [
                {}
            ]
        }
        try:
            config.get_for_each()
            self.fail('No exception')
        except MissingVar:
            pass
