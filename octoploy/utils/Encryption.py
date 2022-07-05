import base64
import os

import Crypto.Hash.SHA256
from Crypto import Random
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA512


class AESCipher(object):

    def __init__(self, key):
        self.bs = AES.block_size
        salt = b'octoployPepper!!'
        dv = PBKDF2(key, salt, 64, count=100000, hmac_hash_module=SHA512)
        self.key = dv[:32]

    def encrypt(self, raw: str) -> str:
        raw_bytes = raw.encode('utf-8')
        # Append 32 bytes of message hash to detect successful decryption
        validation = Crypto.Hash.SHA256.SHA256Hash().new(raw_bytes).digest()
        raw_bytes += validation

        raw_bytes = self._pad(raw_bytes)
        iv = Random.new().read(self.bs)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(bytes(raw_bytes))).decode('utf-8')

    def decrypt(self, enc: str) -> str:
        enc = base64.b64decode(enc.encode('utf-8'))

        iv = enc[:self.bs]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        raw_bytes = self._unpad(cipher.decrypt(enc[self.bs:]))
        payload = raw_bytes[:-32]

        payload_hash = Crypto.Hash.SHA256.SHA256Hash().new(payload).digest()
        expected_hash = raw_bytes[-32:]
        if payload_hash != expected_hash:
            raise ValueError('Could not decrypt value')

        return payload.decode('utf-8')

    def _pad(self, s: bytes) -> bytearray:
        """
        Pads the argument to be a multiple of the block size
        :param s: Bytes
        :return: Padded bytes
        """
        s = bytearray(s)
        padding_count = (self.bs - len(s) % self.bs)
        for x in range(padding_count):
            s.append(padding_count)

        return s

    @staticmethod
    def _unpad(s: bytes) -> bytes:
        """
        Removes the padding
        :param s: Padded bytes
        :return: Raw bytes
        """
        return s[:-ord(s[len(s) - 1:])]


class Encryption:
    KEY_ENV = 'OCTOPLOY_KEY'

    def __init__(self):
        self._cipher = None

    def encrypt(self, raw: str) -> str:
        cipher = self._get_cipher()
        return cipher.encrypt(raw)

    def decrypt(self, enc: str) -> str:
        cipher = self._get_cipher()
        return cipher.decrypt(enc)

    def _get_cipher(self):
        if self._cipher is None:
            key = os.environ.get(self.KEY_ENV)
            if key is None:
                raise ValueError(f'Environment {self.KEY_ENV} is not defined. The key is required for '
                                 f'de/encryption')
            self._cipher = AESCipher(key)
        return self._cipher
