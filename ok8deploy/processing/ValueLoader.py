from __future__ import annotations
from abc import abstractmethod
from typing import Dict

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from octoploy.config.BaseConfig import BaseConfig
from octoploy.utils.Cert import Cert
from octoploy.utils.Errors import ConfigError


class ValueLoader:
    def __init__(self, config: BaseConfig):
        self._config = config

    @abstractmethod
    def load(self, data: Dict) -> Dict[str, str]:
        pass


class PemLoader(ValueLoader):

    def load(self, data: Dict) -> Dict[str, str]:
        file = data['file']
        cert = Cert(self._config.get_file(file))
        return {
            '_PUBLIC': cert.cert,
            '_KEY': cert.key,
            '_CACERT': ''.join(cert.cacerts),
        }


class ValueLoaderFactory:

    @staticmethod
    def create(config: BaseConfig, loader_name: str) -> ValueLoader:
        if loader_name == 'pem':
            return PemLoader(config)
        raise ConfigError('Unknown loader ' + loader_name)
