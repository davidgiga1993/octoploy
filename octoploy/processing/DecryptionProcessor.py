from typing import Dict, Optional

from octoploy.k8s.SecretObj import SecretObj
from octoploy.processing.TreeWalker import TreeProcessor, TreeWalker
from octoploy.utils import Utils
from octoploy.utils.Encryption import Encryption
from octoploy.utils.Errors import SkipObject


class DecryptionProcessor(TreeProcessor):
    """
    Processes all objects, and replaces any encrypted placeholders.
    If skip_secrets is True, all secret object types wil lbe skipped
    """

    skip_secrets: bool = False
    """
    Indicates if all secrets should be skipped
    """

    _secret_obj: Optional[SecretObj]

    def __init__(self):
        self.encryption = Encryption()

    def process(self, root: Dict[str, any]):
        try:
            self._secret_obj = SecretObj(root)
        except ValueError:
            self._secret_obj = None

        walker = TreeWalker(self)
        walker.walk(root)

    def process_str(self, value: str, parent: Dict[str, any], key: str) -> str:
        if not value.startswith(Encryption.CRYPT_PREFIX):
            if self._secret_obj is None:
                # Not a secret object, simply pass through
                return value

            # The secret may contain non encrypted values
            # We'll ignore them for now since we don't want to change the behavior
            # of octoploy for existing projects.
            # Also, it may increase chances of accidentally storing them in vcs
            if key in self._secret_obj.base64_data or \
                    key in self._secret_obj.string_data:
                raise SkipObject('Secret contains plain text - use "octoploy encrypt" to encrypt your secrets')

            return value
        if DecryptionProcessor.skip_secrets and self._secret_obj is not None:
            # We should skip the secret
            raise SkipObject('Secrets should be skipped')

        payload = Utils.remove_prefix(value, Encryption.CRYPT_PREFIX)
        return self.encryption.decrypt(payload)
