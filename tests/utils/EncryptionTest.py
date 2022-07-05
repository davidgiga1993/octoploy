import os
from unittest import TestCase

from octoploy.utils.Encryption import Encryption


class EncryptionTest(TestCase):

    def test_encrypt_valid(self):
        os.environ['OCTOPLOY_KEY'] = 'key123'
        enc = Encryption()
        out = enc.encrypt('hello world')

        enc = Encryption()
        self.assertEqual('hello world', enc.decrypt(out))

    def test_wrong_key(self):
        os.environ['OCTOPLOY_KEY'] = 'asd123aopiksd'
        enc = Encryption()
        out = enc.encrypt('hello world')

        os.environ['OCTOPLOY_KEY'] = 'wrong key'
        enc = Encryption()
        self.assertRaises(ValueError, enc.decrypt, out)
