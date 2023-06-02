from __future__ import annotations

import base64
import os
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

    def _resolve_path(self, path: str) -> str:
        if os.path.isabs(path):
            return path
        return self._config.get_file(path)


class EnvLoader(ValueLoader):

    def load(self, data: Dict) -> Dict[str, str]:
        return dict(os.environ)


class FileLoader(ValueLoader):

    def load(self, data: Dict) -> Dict[str, str]:
        file = self._resolve_path(data['file'])
        encoding = data.get('encoding', 'utf-8')
        conversion = data.get('conversion')

        with open(file, 'rb') as f:
            content = f.read()

        if conversion is not None:
            if conversion == 'base64':
                return {'': base64.b64encode(content).decode('utf-8')}
            raise ValueError(f'Unknown conversion {conversion}')

        return {'': content.decode(encoding)}


class PemLoader(ValueLoader):

    def load(self, data: Dict) -> Dict[str, str]:
        file = self._resolve_path(data['file'])
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
        if loader_name == 'file':
            return FileLoader(config)
        if loader_name == 'env':
            return EnvLoader(config)
        raise ConfigError('Unknown loader ' + loader_name)
