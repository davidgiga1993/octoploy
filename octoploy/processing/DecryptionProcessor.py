from typing import Dict, Optional

from octoploy.k8s.BaseObj import BaseObj

from octoploy.k8s.SecretObj import SecretObj
from octoploy.processing.TreeWalker import TreeProcessor, TreeWalker
from octoploy.utils import Utils
from octoploy.utils.Encryption import Encryption
from octoploy.utils.Errors import SkipObject
from octoploy.utils.Log import Log


class DecryptionProcessor(TreeProcessor, Log):
    """
    Processes all objects, and replaces any encrypted placeholders.
    If skip_secrets is True, all secret object types wil lbe skipped
    """

    skip_secrets: bool = False
    """
    Indicates if all secrets should be skipped
    """

    deploy_plain_text: bool = False
    """
    Indicates if plain text secrets should be skipped
    """

    _secret_obj: Optional[SecretObj]

    def __init__(self):
        super().__init__(__name__)
        self.encryption = Encryption()

    def process(self, k8s_object: BaseObj):
        try:
            self._secret_obj = SecretObj(k8s_object.data)
        except ValueError:
            self._secret_obj = None

        walker = TreeWalker(self)
        walker.walk(k8s_object.data)

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
                if not DecryptionProcessor.deploy_plain_text:
                    raise SkipObject(
                        f'Secret {self._secret_obj.get_fqn()} contains plain text - '
                        f'use "octoploy encrypt" to encrypt your secrets')

            return value

        if DecryptionProcessor.skip_secrets and self._secret_obj is not None:
            # We should skip the secret
            raise SkipObject('Secrets should be skipped')

        payload = Utils.remove_prefix(value, Encryption.CRYPT_PREFIX)
        return self.encryption.decrypt(payload)
