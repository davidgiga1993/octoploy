from typing import Dict

from octoploy.processing.TreeWalker import TreeProcessor, TreeWalker
from octoploy.utils.Encryption import Encryption


class DecryptionProcessor(TreeProcessor):
    CRYPT_PREFIX = 'OctoCrypt!'

    def __init__(self):
        self.encryption = Encryption()

    def process(self, root: Dict[str, any]):
        walker = TreeWalker(self)
        walker.walk(root)

    def process_str(self, value: str, parent: Dict[str, any], key: str) -> str:
        if not value.startswith(self.CRYPT_PREFIX):
            return value
        payload = value.removeprefix(self.CRYPT_PREFIX)
        return self.encryption.decrypt(payload)
